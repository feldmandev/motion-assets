"""Shared optical appearance, applied without altering device geometry or animation."""
import copy
import hashlib
import json
import math
import re
import struct
from pathlib import Path

BASE = Path(__file__).resolve().parent
ASSETS = BASE / 'textures' / 'optics'
IMAGES = {name: (ASSETS / name).read_bytes() for name in (
    'flash-diffuser.png', 'flash-diffuser-normal.png', 'front-specular-mask.png', 'coating-thickness.png')}
REVISION = 'catalog-optics-3-' + hashlib.sha256(b''.join(IMAGES.values())).hexdigest()[:12]


def role(name):
    name = re.sub(r'\.\d{3}$', '', name)
    if name in ('flash', 'Frosted flash diffuser', 'Catalog flash diffuser'):
        return 'flash'
    if name == 'Catalog front optical aperture':
        return 'front_aperture'
    if name == 'Pixel front optics | coated glass':
        return 'front'
    if 'element 1 coating' in name or 'curved internal optical coating' in name or name in ('Apple optical glass', 'Robot optical glass', 'Lens 1', 'Lens 2'):
        return 'outer'
    if 'element 2 coating' in name or 'internal prism optic' in name:
        return 'inner'
    if name in ('Continuous clear optical cover', 'Camera pill | antireflective clear cover'):
        return 'cover'
    return None


def geometry_signature(document, binary):
    """Hash original attributes, topology, transforms, skins and articulation; UVs may change."""
    digest = hashlib.sha256()
    for key in ('nodes', 'scenes', 'scene', 'skins', 'animations'):
        digest.update(json.dumps(document.get(key), sort_keys=True).encode())
    for mesh in document.get('meshes', []):
        digest.update(mesh.get('name', '').encode())
        for primitive in mesh['primitives']:
            digest.update(str(primitive.get('mode', 4)).encode())
            attributes = {k: v for k, v in primitive['attributes'].items() if not k.startswith('TEXCOORD') and k != 'TANGENT'}
            if 'indices' in primitive:
                attributes['indices'] = primitive['indices']
            for key, index in sorted(attributes.items()):
                accessor = document['accessors'][index]
                view = document['bufferViews'][accessor['bufferView']]
                digest.update(key.encode())
                digest.update(json.dumps(accessor, sort_keys=True).encode())
                offset = view.get('byteOffset', 0)
                digest.update(binary[offset:offset + view['byteLength']])
            digest.update(json.dumps(primitive.get('targets'), sort_keys=True).encode())
    return digest.hexdigest()


def read_glb(path):
    raw = path.read_bytes()
    length, kind = struct.unpack_from('<II', raw, 12)
    if kind != 0x4E4F534A:
        raise ValueError('Expected a GLB JSON chunk')
    document = json.loads(raw[20:20+length])
    binary_length, binary_kind = struct.unpack_from('<II', raw, 20+length)
    if binary_kind != 0x004E4942 or 28+length+binary_length != len(raw):
        raise ValueError('Expected one embedded GLB binary buffer')
    return raw, document, bytearray(raw[28+length:])


def apply_glb(path, backup_dir=None):
    path = Path(path)
    # Read just the header for the common, already-updated case.
    with path.open('rb') as stream:
        header = stream.read(20)
        document = json.loads(stream.read(struct.unpack_from('<I', header, 12)[0]))
    stamp = document.get('asset', {}).get('extras', {}).get('opticsTreatment', {})
    if stamp.get('revision') == REVISION:
        return {'id': path.parent.name, 'status': 'unchanged', **stamp}
    raw, document, binary = read_glb(path)
    original_geometry = geometry_signature(document, binary)
    if stamp and backup_dir:
        source = Path(backup_dir) / path.parent.name / (stamp['sourceSha256'] + '.glb')
        raw, document, binary = read_glb(source)
        if geometry_signature(document, binary) != original_geometry:
            raise ValueError('Geometry changed after the earlier optical update; rebuild this export first')
    source_hash = hashlib.sha256(raw).hexdigest()
    if backup_dir:
        backup = Path(backup_dir) / path.parent.name / (source_hash + '.glb')
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(raw)
    original_binary = bytes(binary)
    original_nodes = copy.deepcopy(document.get('nodes'))
    materials = document.setdefault('materials', [])
    textures = {}
    extensions = set(document.get('extensionsUsed', []))

    def append(data):
        binary.extend(b'\0' * (-len(binary) % 4))
        view = {'buffer': 0, 'byteOffset': len(binary), 'byteLength': len(data)}
        binary.extend(data)
        views = document.setdefault('bufferViews', [])
        views.append(view)
        return len(views)-1

    def texture(name):
        if name not in textures:
            images = document.setdefault('images', [])
            images.append({'name': 'Optics | ' + name, 'mimeType': 'image/png', 'bufferView': append(IMAGES[name])})
            entries = document.setdefault('textures', [])
            entries.append({'source': len(images)-1})
            textures[name] = len(entries)-1
        return {'index': textures[name], 'texCoord': 0}

    def positions(primitive):
        accessor = document['accessors'][primitive['attributes']['POSITION']]
        if accessor['componentType'] != 5126 or accessor.get('sparse'):
            raise ValueError('Unsupported position accessor')
        view = document['bufferViews'][accessor['bufferView']]
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', 12)
        return [struct.unpack_from('<fff', binary, offset+i*stride) for i in range(accessor['count'])]

    def project_uv(primitive):
        points = positions(primitive)
        lower = [min(p[i] for p in points) for i in range(3)]
        extent = [max(p[i] for p in points)-lower[i] for i in range(3)]
        axes = sorted(range(3), key=lambda i: extent[i], reverse=True)[:2]
        if min(extent[i] for i in axes) <= 0:
            raise ValueError('Degenerate optical surface')
        uv = b''.join(struct.pack('<ff', *((p[i]-lower[i])/extent[i] for i in axes)) for p in points)
        accessors = document.setdefault('accessors', [])
        accessors.append({'bufferView': append(uv), 'componentType': 5126, 'count': len(points), 'type': 'VEC2'})
        primitive['attributes']['TEXCOORD_0'] = len(accessors)-1
        primitive['attributes'].pop('TANGENT', None)

    # Material isolation is essential: the generic black material also covers bodies and sensors.
    front_indices = set()
    skipped_front = []
    for node in document.get('nodes', []):
        name = node.get('name', '').lower()
        if 'mesh' not in node or not any(token in name for token in ('selfie aperture', 'bezel selfie camera', 'webcam')):
            continue
        mesh = document['meshes'][node['mesh']]
        if any(role(materials[p['material']].get('name', '')) == 'front' for p in mesh['primitives'] if 'material' in p):
            continue
        for primitive in mesh['primitives']:
            if 'material' not in primitive or materials[primitive['material']].get('name') != 'black':
                continue
            points = positions(primitive)
            dimensions = sorted(max(p[i] for p in points)-min(p[i] for p in points) for i in range(3))
            if dimensions[-2] <= 0 or dimensions[-1]/dimensions[-2] > 1.12:
                skipped_front.append(node.get('name'))
                continue
            material = copy.deepcopy(materials[primitive['material']])
            material['name'] = 'Catalog front optical aperture'
            materials.append(material)
            primitive['material'] = len(materials)-1
            front_indices.add(len(materials)-1)
            project_uv(primitive)

    # Notebook indicator LEDs can share the material called "flash". Treat only flash nodes.
    flash_indices = set()
    flash_clones = {}
    for node in document.get('nodes', []):
        if 'mesh' not in node or 'flash' not in node.get('name', '').lower():
            continue
        for primitive in document['meshes'][node['mesh']]['primitives']:
            original = primitive.get('material')
            if original is None or role(materials[original].get('name', '')) != 'flash':
                continue
            if original not in flash_clones:
                clone = copy.deepcopy(materials[original])
                clone['name'] = 'Catalog flash diffuser'
                materials.append(clone)
                flash_clones[original] = len(materials)-1
            primitive['material'] = flash_clones[original]
            flash_indices.add(primitive['material'])
    counts = {}
    for index, material in enumerate(materials):
        kind = 'front_aperture' if index in front_indices else role(material.get('name', ''))
        if kind == 'flash' and index not in flash_indices:
            continue
        if not kind:
            continue
        counts[kind] = counts.get(kind, 0)+1
        material.setdefault('extras', {})['opticsRole'] = kind
        ext = material.setdefault('extensions', {})
        pbr = material.setdefault('pbrMetallicRoughness', {})
        if kind == 'cover':
            pbr.update(baseColorFactor=[1, 1, 1, 0], metallicFactor=0, roughnessFactor=.04)
            material['alphaMode'] = 'BLEND'
            ext.pop('KHR_materials_transmission', None)
        elif kind == 'flash':
            pbr.update(baseColorFactor=[1, 1, 1, 1], metallicFactor=0, roughnessFactor=.36,
                       baseColorTexture=texture('flash-diffuser.png'))
            material['normalTexture'] = {**texture('flash-diffuser-normal.png'), 'scale': 1}
            material.pop('alphaMode', None)
            material.pop('emissiveFactor', None)
            for key in ('KHR_materials_transmission', 'KHR_materials_iridescence', 'KHR_materials_emissive_strength'):
                ext.pop(key, None)
        elif kind == 'inner':
            pbr.update(baseColorFactor=[.001, .0012, .0018, 1], metallicFactor=0, roughnessFactor=.12)
            ext.pop('KHR_materials_transmission', None)
            ext.pop('KHR_materials_iridescence', None)
            material.pop('emissiveFactor', None)
        else:
            aperture = kind == 'front_aperture'
            pbr.update(baseColorFactor=[.001, .001, .0015, 1] if aperture else [1, 1, 1, 1],
                       metallicFactor=0, roughnessFactor=.09 if aperture else .045)
            ext['KHR_materials_ior'] = {'ior': 1.5}
            ext['KHR_materials_iridescence'] = {'iridescenceFactor': .9, 'iridescenceIor': 1.45,
                'iridescenceThicknessMinimum': 150., 'iridescenceThicknessMaximum': 235.,
                'iridescenceThicknessTexture': texture('coating-thickness.png')}
            ext['KHR_materials_specular'] = {'specularFactor': .5, 'specularColorFactor': [.434, .405, 1.]}
            if aperture:
                ext.pop('KHR_materials_transmission', None)
                ext['KHR_materials_specular']['specularTexture'] = texture('front-specular-mask.png')
                ext['KHR_materials_iridescence']['iridescenceTexture'] = texture('front-specular-mask.png')
            else:
                ext['KHR_materials_transmission'] = {'transmissionFactor': 1}
            material.pop('alphaMode', None)
        extensions.update(ext)
    for mesh in document.get('meshes', []):
        for primitive in mesh['primitives']:
            if primitive.get('material') in flash_indices or role(materials[primitive.get('material', 0)].get('name', '')) in ('outer', 'front'):
                project_uv(primitive)
    if geometry_signature(document, binary) != original_geometry or document.get('nodes') != original_nodes:
        raise AssertionError('Optical update altered geometry or articulation')
    assert binary[:len(original_binary)] == original_binary
    stamp = {'revision': REVISION, 'sourceSha256': source_hash, 'geometrySha256': original_geometry,
             'materials': counts, 'preservedFrontShapes': skipped_front}
    document.setdefault('asset', {}).setdefault('extras', {})['opticsTreatment'] = stamp
    document['extensionsUsed'] = sorted(extensions)
    document['buffers'][0]['byteLength'] = len(binary)
    binary.extend(b'\0' * (-len(binary) % 4))
    data = json.dumps(document, separators=(',', ':')).encode()
    data += b' ' * (-len(data) % 4)
    result = struct.pack('<III', 0x46546C67, 2, 28+len(data)+len(binary))
    result += struct.pack('<II', len(data), 0x4E4F534A)+data+struct.pack('<II', len(binary), 0x004E4942)+binary
    temporary = path.with_suffix('.optics.tmp')
    temporary.write_bytes(result)
    temporary.replace(path)
    return {'id': path.parent.name, 'status': 'updated', 'geometryPreserved': True, **stamp}


def apply_blender():
    """Future builds receive the shared PBR optics before saving their editable BLEND."""
    import bpy
    flash_clones = {}
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        if 'flash' in obj.name.lower():
            for index, material in enumerate(obj.data.materials):
                if material and role(material.name) == 'flash' and material.name != 'Catalog flash diffuser':
                    if material not in flash_clones:
                        clone = material.copy()
                        clone.name = 'Catalog flash diffuser'
                        flash_clones[material] = clone
                    obj.data.materials[index] = flash_clones[material]
        if not any(token in obj.name.lower() for token in ('selfie aperture', 'bezel selfie camera', 'webcam')):
            continue
        dimensions = sorted(obj.dimensions)
        if dimensions[-2] <= 0 or dimensions[-1]/dimensions[-2] > 1.12:
            continue
        for index, material in enumerate(obj.data.materials):
            if material and material.name == 'black':
                clone = material.copy()
                clone.name = 'Catalog front optical aperture'
                obj.data.materials[index] = clone
    flash_materials = {material for obj in bpy.data.objects if obj.type == 'MESH' and 'flash' in obj.name.lower()
                       for material in obj.data.materials if material and role(material.name) == 'flash'}
    for material in bpy.data.materials:
        kind = role(material.name)
        if not kind or not material.use_nodes:
            continue
        shader = next((n for n in material.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if not shader:
            continue
        if kind == 'flash' and material not in flash_materials:
            continue
        output = next((n for n in material.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)
        if output:
            material.node_tree.links.new(shader.outputs['BSDF'], output.inputs['Surface'])
        if kind in ('outer', 'front', 'front_aperture'):
            aperture = kind == 'front_aperture'
            shader.inputs['Base Color'].default_value = (.001,.001,.0015,1) if aperture else (1, 1, 1, 1)
            shader.inputs['Thin Film Thickness'].default_value = 103
            shader.inputs['Thin Film IOR'].default_value = 1.38
            shader.inputs['Roughness'].default_value = .045
            shader.inputs['Transmission Weight'].default_value = 0 if aperture else 1
            if aperture:
                texture = material.node_tree.nodes.new('ShaderNodeTexImage')
                texture.image = bpy.data.images.load(str(ASSETS/'front-specular-mask.png'), check_existing=False)
                texture.image.pack()
                weight = material.node_tree.nodes.new('ShaderNodeMath')
                weight.operation = 'MULTIPLY'
                weight.inputs[1].default_value = .5
                material.node_tree.links.new(texture.outputs['Alpha'], weight.inputs[0])
                material.node_tree.links.new(weight.outputs[0], shader.inputs['Specular IOR Level'])
                thickness = material.node_tree.nodes.new('ShaderNodeMath')
                thickness.operation = 'MULTIPLY'
                thickness.inputs[1].default_value = 103
                material.node_tree.links.new(texture.outputs['Alpha'], thickness.inputs[0])
                material.node_tree.links.new(thickness.outputs[0], shader.inputs['Thin Film Thickness'])
        elif kind == 'flash':
            nodes, links = material.node_tree.nodes, material.node_tree.links
            color = nodes.new('ShaderNodeTexImage')
            color.image = bpy.data.images.load(str(ASSETS/'flash-diffuser.png'), check_existing=True)
            color.image.pack()
            links.new(color.outputs['Color'], shader.inputs['Base Color'])
            normal = nodes.new('ShaderNodeTexImage')
            normal.image = bpy.data.images.load(str(ASSETS/'flash-diffuser-normal.png'), check_existing=True)
            normal.image.colorspace_settings.name = 'Non-Color'
            normal.image.pack()
            mapping = nodes.new('ShaderNodeNormalMap')
            links.new(normal.outputs['Color'], mapping.inputs['Color'])
            links.new(mapping.outputs['Normal'], shader.inputs['Normal'])
            shader.inputs['Transmission Weight'].default_value = 0
            shader.inputs['Metallic'].default_value = 0
            shader.inputs['Roughness'].default_value = .36
        elif kind == 'inner':
            shader.inputs['Base Color'].default_value = (.001,.0012,.0018,1)
            shader.inputs['Metallic'].default_value = 0
            shader.inputs['Transmission Weight'].default_value = 0
            shader.inputs['Roughness'].default_value = .12
        elif kind == 'cover':
            shader.inputs['Alpha'].default_value = 0
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        mesh = obj.data
        optical_slots = {i for i, material in enumerate(mesh.materials) if material and
                         (material in flash_materials or role(material.name) == 'front_aperture')}
        if not optical_slots:
            continue
        lower = [min(v.co[i] for v in mesh.vertices) for i in range(3)]
        extent = [max(v.co[i] for v in mesh.vertices)-lower[i] for i in range(3)]
        axes = sorted(range(3), key=lambda i: extent[i], reverse=True)[:2]
        if min(extent[i] for i in axes) <= 0:
            continue
        uv = mesh.uv_layers.active or mesh.uv_layers.new(name='Optical UV')
        for polygon in mesh.polygons:
            if polygon.material_index not in optical_slots:
                continue
            for loop in polygon.loop_indices:
                point = mesh.vertices[mesh.loops[loop].vertex_index].co
                uv.data[loop].uv = tuple((point[i]-lower[i])/extent[i] for i in axes)


def verify_glb(path, backup_dir):
    """Check the finished file against its untouched pre-treatment geometry and binary data."""
    _, document, binary = read_glb(Path(path))
    stamp = document['asset']['extras']['opticsTreatment']
    if stamp['revision'] != REVISION:
        raise AssertionError('Outdated optical treatment')
    source = Path(backup_dir)/Path(path).parent.name/(stamp['sourceSha256']+'.glb')
    _, original, original_binary = read_glb(source)
    signature = geometry_signature(document, binary)
    if signature != geometry_signature(original, original_binary) or signature != stamp['geometrySha256']:
        raise AssertionError('Geometry or articulation differs from the original')
    if binary[:len(original_binary)] != original_binary:
        raise AssertionError('Original geometry/animation bytes differ')
    for mesh in document['meshes']:
        for primitive in mesh['primitives']:
            material = document['materials'][primitive['material']]
            if material.get('extras', {}).get('opticsRole') == 'flash':
                if 'TEXCOORD_0' not in primitive['attributes'] or 'normalTexture' not in material or 'baseColorTexture' not in material['pbrMetallicRoughness']:
                    raise AssertionError('Flash diffuser has incomplete texture mapping')
    return {'id': Path(path).parent.name, 'status': 'verified', 'geometryPreserved': True, **stamp}
