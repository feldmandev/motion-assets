"""Blender entry point: reviewed device asset -> screen-ready BLEND/GLB/SVG/JSON."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
MM = .001


SKIN_TRACES = BASE/'research'/'skins'


def load_trace(trace_id):
    path = SKIN_TRACES/trace_id/'trace.json'
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    data['id'] = trace_id
    return data


def fit_outline(points, width, height):
    """Scale a traced outline about its bounding-box centre to exactly width x height (mm) and
    centre it on the origin. Traced sizes differ from published ones by ~0.1-0.3% (pixel rounding)."""
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    cx, cy = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
    sx, sy = width/(max(xs)-min(xs)), height/(max(ys)-min(ys))
    return [[(x-cx)*sx, (y-cy)*sy] for x, y in points]


def traced_screen(spec, trace, keep_center=False):
    """Screen opening from Google's artwork: size/position and, unless opted out, traced corners."""
    x, y, w, h = trace['screen_rect_mm']
    spec['fit_box_mm'] = [w, h]
    if 'screen_cutouts_mm' in trace:
        spec['cutouts'] = trace['screen_cutouts_mm']
    if spec.get('trace_outline', True) and not spec.get('keep_reviewed_corner_shape'):
        spec['outline_mm'] = fit_outline(trace['screen_outline_mm'], w, h)
        # Infer the circular arc from the actual traced opening, rather than the old seed radius.
        # For an arc point at distances u/v from its corner, r = u + v + sqrt(2*u*v).
        from statistics import median
        radii = []
        for sign_x, sign_y in ((1,-1), (1,1), (-1,1), (-1,-1)):
            candidates = []
            for px, py in spec['outline_mm']:
                u, v = w/2-sign_x*px, h/2-sign_y*py
                if .12 < u < w/4 and .12 < v < w/4:
                    radius = u+v+math.sqrt(2*u*v)
                    if radius < w/3:
                        candidates.append(radius)
            if candidates:
                radii.append(median(candidates))
        if radii:
            spec['corner_radius_mm'] = median(radii)
        spec['frame_trace'] = trace
    else:
        # Some emulator skins have a noticeably squarer screen mask than the physical OLED.
        # Keep the skin's measured size/position, but let the reviewed corner radius generate
        # both the 3D screen and the exported frame opening.
        spec.pop('outline_mm', None)
        spec.pop('frame_trace', None)
    if not keep_center:
        spec['center_mm'] = [x, y, spec['center_mm'][2]]


def apply_trace(profile):
    """Replace estimated silhouettes and screens with outlines traced from the SDK skins."""
    import geometry  # noqa: F401  (adds the vendored shapely path)
    from shapely.geometry import Polygon, box
    pid = profile['id']
    trace = load_trace(pid)
    if not trace:
        # Open Fold without its own skin: still take the cover screen and its frame from the
        # closed-front artwork (traced or derived).
        folded = load_trace(pid.replace('-unfolded', '-folded')) if pid.endswith('-unfolded') else None
        for spec in profile.get('screens', []) if folded else []:
            if spec['object'] == 'Cover screen':
                traced_screen(spec, folded, keep_center=True)
        return
    body = profile['body_mm']
    if 'panels' not in profile:
        # The chassis and display have independent contours in Google's artwork.
        profile['body_outline_mm'] = fit_outline(trace['body_outline_mm'], body['width'], body['height'])
        traced_screen(profile['screen'], trace)
        return
    profile['body_outline_mm'] = fit_outline(trace['body_outline_mm'], body['width'], body['height'])
    outline = Polygon(profile['body_outline_mm'])
    folded = load_trace(pid.replace('-unfolded', '-folded'))
    for panel in profile['panels']:
        px, py = panel['center_mm'][:2]
        if pid.endswith('-unfolded'):
            half = outline.intersection(box(-1e3, -1e3, 0, 1e3) if px < 0 else box(0, -1e3, 1e3, 1e3))
        else:
            half = outline
        pb = panel['body_mm']
        panel['outline_mm'] = fit_outline(list(half.exterior.coords)[:-1], pb['width'], pb['height'])
    for spec in profile['screens']:
        if spec.get('panel') == 'Inner display':
            traced_screen(spec, trace)
        elif pid.endswith('-folded'):
            panel = next(p for p in profile['panels'] if p['name'] == spec['panel'])
            traced_screen(spec, trace)
            spec['center_mm'][0] -= panel['center_mm'][0]
            spec['center_mm'][1] -= panel['center_mm'][1]
        elif folded:
            # Rear-facing cover screen: keep its mirrored placement, take the traced shape.
            traced_screen(spec, folded, keep_center=True)


def screen_outline(width, height, radius):
    points = []
    for x, y, start in [(width/2-radius, -height/2+radius, -90),
                        (width/2-radius, height/2-radius, 0),
                        (-width/2+radius, height/2-radius, 90),
                        (-width/2+radius, -height/2+radius, 180)]:
        for step in range(33):
            angle = math.radians(start + step * 90/32)
            points.append(((x + radius*math.cos(angle))*MM,
                           (y + radius*math.sin(angle))*MM, 0))
    return points


def sync_slab_body_corners(profile):
    """Match each slab-phone chassis corner to the display corner plus its adjacent bezel.

    A rounded rectangle offset outward by a bezel keeps the same corner centre and increases its
    radius by that inset. Screens can be slightly off-centre, so derive all four corners from the
    local horizontal/vertical bezel rather than assuming one global border width. Imported assets
    and foldables keep their reviewed/model-specific enclosure geometry.
    """
    if profile.get('manufacturer') == 'Apple' or 'asset' in profile or 'panels' in profile or 'screen' not in profile or profile.get('body_outline_mm'):
        return
    body = profile['body_mm']
    spec = profile['screen']
    px, py = spec['resolution']
    box_w, box_h = spec['fit_box_mm']
    scale = min(box_w/px, box_h/py)
    width, height = px*scale, py*scale
    cx, cy = spec['center_mm'][:2]
    left = body['width']/2 + cx - width/2
    right = body['width']/2 - cx - width/2
    top = body['height']/2 - cy - height/2
    bottom = body['height']/2 + cy - height/2
    if min(left, right, top, bottom) < 0:
        raise ValueError('Screen must fit inside the device body')

    screen_radii = spec.get('corner_radii_mm', [spec['corner_radius_mm']]*4)
    bezels = [min(right, bottom), min(right, top), min(left, top), min(left, bottom)]
    limit = min(body['width'], body['height'])/2
    radii = [min(limit, radius+bezel) for radius, bezel in zip(screen_radii, bezels)]
    body['corner_radii_mm'] = radii
    body['corner_radius'] = sum(radii)/len(radii)
    # A skin trace previously supplied an independent body contour. Remove it so geometry.py uses
    # these display-derived radii while preserving the published body width and height.
    profile.pop('body_outline_mm', None)


def prepare_screen(spec, body, screen_image=None):
    px, py = spec['resolution']
    box_w, box_h = spec['fit_box_mm']
    if min(px, py, box_w, box_h) <= 0:
        raise ValueError('Screen dimensions must be positive')
    scale = min(box_w/px, box_h/py)
    width, height = px*scale, py*scale
    radius = spec['corner_radius_mm']
    cx, cy, cz = spec['center_mm']
    if spec.get('foldable_surface') and spec.get('rotation_deg', [0,0,0])[1] == 180:
        # Ten microns above the rear glass caused depth-buffer speckles while orbiting.
        cz -= .05
        spec['center_mm'][2] = cz
    if not 0 <= radius <= min(width, height)/2:
        raise ValueError('Screen radius exceeds screen bounds')
    if abs(cx)+width/2 >= body['width']/2 or abs(cy)+height/2 >= body['height']/2:
        raise ValueError('Screen must fit inside the device body')

    screen = bpy.data.objects.get(spec['object'])
    curve = spec.get('edge_curve_mm', 0)
    if curve:
        # Rounded row boundaries plus a gently rolled display edge. UVs still cover the full feed.
        points, faces = [], []
        columns = 48
        middle = height/2-radius
        levels = sorted(set([-middle+2*middle*row/96 for row in range(97)]+[
            sign*(middle+radius*math.sin(step*math.pi/64))
            for sign in [-1,1] for step in range(33)]))
        boundary = spec.get('outline_mm')
        if boundary:
            low, high = min(p[1] for p in boundary), max(p[1] for p in boundary)
            levels = sorted(set([max(low, min(high, y)) for y in levels]+[p[1] for p in boundary]))
        rows = len(levels)-1
        for y in levels:
            if boundary:
                crossings = [ax+(y-ay)*(bx-ax)/(by-ay)
                             for (ax, ay), (bx, by) in zip(boundary, boundary[1:]+boundary[:1])
                             if ay != by and min(ay, by) <= y <= max(ay, by)]
                left, right = min(crossings), max(crossings)
            else:
                corner_y = max(0, abs(y)-(height/2-radius))
                extent = width/2-radius + math.sqrt(max(0, radius**2-corner_y**2))
                left, right = -extent, extent
            for column in range(columns+1):
                x = left + (right-left)*column/columns
                drop = curve*max(0, (abs(x)-(width/2-curve*2))/(curve*2))**2
                points.append((x*MM, y*MM, -drop*MM))
        for row in range(rows):
            for column in range(columns):
                index = row*(columns+1)+column
                faces.append((index, index+1, index+columns+2, index+columns+1))
        # The front glass and rail must follow the OLED curve, otherwise their
        # flat faces hide the rolled display edges and create a thick false bezel.
        support_width = curve*2
        if body.get('front_glass_inset_mm'):
            # Include one OLED face span: its interpolation can begin sagging
            # before the analytic curve starts, especially at traced corners.
            support_width += max((max(points[i][0] for i in face)-min(points[i][0] for i in face))/MM
                                 for face in faces)
        for part in screen.parent.children:
            if not part.name.startswith(('Front black glass', 'Aluminum enclosure')):
                continue
            if body.get('front_glass_inset_mm'):
                import bmesh
                bm = bmesh.new()
                bm.from_mesh(part.data)
                # Split the broad caps at the support ramp's four X boundaries;
                # deforming only the perimeter would also sink the flat centre.
                for edge in (-width/2, -width/2+support_width, width/2-support_width, width/2):
                    geom = list(bm.verts)+list(bm.edges)+list(bm.faces)
                    if part.name.startswith('Aluminum enclosure'):
                        geom = [item for item in geom if all(v.co.z > 0 for v in
                                ([item] if isinstance(item, bmesh.types.BMVert) else item.verts))]
                    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-9,
                                          plane_co=((cx+edge)*MM-part.location.x, 0, 0), plane_no=(1, 0, 0))
                bm.to_mesh(part.data)
                bm.free()
            for vertex in part.data.vertices:
                if part.name.startswith('Aluminum enclosure') and vertex.co.z <= 0:
                    continue
                x = abs((vertex.co.x+part.location.x)/MM-cx) if body.get('front_glass_inset_mm') else abs(vertex.co.x/MM)
                fraction = min(1, max(0,(x-(width/2-support_width))/support_width))
                # A linear support ramp lies below every OLED parabola chord,
                # including the narrower rows at its traced corners.
                drop = curve*(fraction if body.get('front_glass_inset_mm') else fraction**2)
                vertex.co.z -= drop*MM
    elif spec.get('outline_mm'):
        from geometry import traced_ring
        points = [(x*MM, y*MM, 0) for x, y in traced_ring(spec['outline_mm'], 0, 400)]
        faces = [tuple(range(len(points)))]
    else:
        points = screen_outline(width, height, radius)
        faces = [tuple(range(len(points)))]
    if spec.get('mesh_cutouts'):
        from geometry import screen_mesh_with_cutouts
        points, faces = screen_mesh_with_cutouts(points, spec['cutouts'])
    material = bpy.data.materials.new('Device screen | replace texture at runtime')
    material.use_nodes = True
    shader = material.node_tree.nodes['Principled BSDF']
    fallback = (.07, .16, .22) if spec.get('foldable_surface') else (.006, .008, .012)
    shader.inputs['Base Color'].default_value = fallback + (1,)
    shader.inputs['Roughness'].default_value = .22
    shader.inputs['Specular IOR Level'].default_value = .3
    if spec.get('foldable_surface'):
        shader.inputs['Emission Color'].default_value = fallback + (1,)
        shader.inputs['Emission Strength'].default_value = .35
    if screen_image:
        texture = material.node_tree.nodes.new('ShaderNodeTexImage')
        texture.image = bpy.data.images.load(str(screen_image.resolve()))
        image_width, image_height = texture.image.size
        if abs((image_width/image_height)/(px/py)-1) > .001:
            raise ValueError('Screen image aspect must match the device; do not stretch an ADB capture')
        texture.image.colorspace_settings.name = 'sRGB'
        texture.image.pack()
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Base Color'])
        material.node_tree.links.new(texture.outputs['Color'], shader.inputs['Emission Color'])
        shader.inputs['Emission Strength'].default_value = 1
    actual_nodes = []
    if spec.get('object_parts'):
        # A foldable inner OLED is one logical surface split at the hinge. Both halves keep UVs in
        # the full-screen coordinate space and share one material, but each is parented to its
        # physical panel so the same texture bends with the hardware animation.
        from shapely.geometry import Polygon, box
        polygon = Polygon([(x/MM+cx, y/MM+cy) for x, y, _ in points]).buffer(0)
        axis_x = spec.get('fold_axis_x_mm', 0)
        parts = spec['object_parts'] if spec.get('part_regions_mm') else sorted(spec['object_parts'], key=lambda name: spec['part_parent_centers_mm'][name][0])
        for index, object_name in enumerate(parts):
            clip = box(*spec['part_regions_mm'][object_name]) if spec.get('part_regions_mm') else (box(-1e4, -1e4, axis_x, 1e4) if index == 0 else box(axis_x, -1e4, 1e4, 1e4))
            clipped = polygon.intersection(clip)
            if clipped.geom_type != 'Polygon':
                clipped = max(clipped.geoms, key=lambda shape: shape.area)
            coords = list(clipped.exterior.coords)[:-1]
            parent_center = spec['part_parent_centers_mm'][object_name]
            split_points = [((x-parent_center[0])*MM, (y-parent_center[1])*MM,
                             (cz-parent_center[2])*MM) for x, y in coords]
            mesh = bpy.data.meshes.new(f'{spec["object"]} surface | {index}')
            mesh.from_pydata(split_points, [], [tuple(range(len(split_points)))])
            mesh.update()
            uv = mesh.uv_layers.new(name='Screen UV')
            for loop in mesh.loops:
                gx, gy = coords[loop.vertex_index]
                uv.data[loop.index].uv = ((gx-cx)/width+.5, (gy-cy)/height+.5)
            part = bpy.data.objects[object_name]
            part.data = mesh
            part.location = (0, 0, 0)
            part.rotation_euler = (0, 0, 0)
            part.scale = (1, 1, 1)
            mesh.materials.append(material)
            part['role'] = 'screen'
            actual_nodes.append(part.name)
        screen = bpy.data.objects[actual_nodes[0]]
    else:
        mesh = bpy.data.meshes.new('Screen surface | native aspect')
        mesh.from_pydata(points, [], faces)
        mesh.update()
        uv = mesh.uv_layers.new(name='Screen UV')
        for loop in mesh.loops:
            x, y, _ = points[loop.vertex_index]
            uv.data[loop.index].uv = (x/(width*MM)+.5, y/(height*MM)+.5)
        screen.data = mesh
        screen.name = spec.get('node', 'Device screen')
        screen.location = tuple(value*MM for value in spec['center_mm'])
        screen.rotation_euler = tuple(math.radians(value) for value in spec.get('rotation_deg', [0,0,0]))
        screen.scale = (1, 1, 1)
        mesh.materials.append(material)
        screen['role'] = 'screen'
        actual_nodes.append(screen.name)
    for index, cutout in enumerate(spec['cutouts']):
        # The old imported asset already supplies its physical front camera.
        if spec.get('create_cutouts'):
            from geometry import disk, slab
            cutout_mat = bpy.data.materials.get('black')
            front_sign = -1 if spec.get('rotation_deg', [0,0,0])[1] == 180 else 1
            x = cx+front_sign*cutout['center_mm'][0]
            y = cy+cutout['center_mm'][1]
            if spec.get('object_parts'):
                object_name = min(spec['object_parts'],
                    key=lambda name: (math.dist(spec['part_parent_centers_mm'][name][:2], [x,y])
                        if spec.get('part_regions_mm') else abs(spec['part_parent_centers_mm'][name][0]-x)))
                parent_center = spec['part_parent_centers_mm'][object_name]
                parent = bpy.data.objects[object_name].parent
                disk(f'{spec["object"]} | selfie aperture {index}', x-parent_center[0], y-parent_center[1],
                     cz-parent_center[2]+front_sign*.025, cutout['radius_mm'], .025, cutout_mat, parent)
            else:
                if cutout.get('size_mm'):
                    cw, ch = cutout['size_mm']
                    slab(f'{screen.name} | sensor aperture {index}', cw, ch, .025,
                         cutout['radius_mm'], (x, y, cz+front_sign*.025),
                         cutout_mat, screen.parent, .005, points=cutout.get('outline_mm'))
                else:
                    disk(f'{screen.name} | selfie aperture {index}', x, y, cz+front_sign*.025,
                         cutout['radius_mm'], .025, cutout_mat, screen.parent)
    if not spec.get('object_parts') and screen.parent:
        # A static folded companion can rotate an entire panel (iPhone Duo's cover leaf is 180°
        # from its open pose). Resolve the exported screen centre from the actual hierarchy so
        # metadata stays correct for translated *and* rotated parents.
        bpy.context.view_layer.update()
        point = screen.matrix_world.translation/MM
        global_center = [point.x, point.y, point.z]
    else:
        offset = spec.get('parent_center_mm', [0, 0, 0])
        global_center = [value+shift for value, shift in zip(spec['center_mm'], offset)]
    return screen, material, width, height, global_center, actual_nodes


# Anti-reflective lens coatings. Phone camera lenses show strong purple/magenta reflections that
# turn green/amber at grazing angles: thin-film interference in their multi-layer AR stacks.
# A single high-index film of the right thickness reproduces that angle-dependent colour shift.
# Only the front lens surface gets a visible AR tint: a light blue-green reflection that shifts
# with viewing angle while the glass stays transparent (inner elements and sensor stay visible).
# Inner elements and the cover glass keep the source asset's subtle coatings; stacking strong
# films on every layer looks foggy. Cycles (thin film) and three.js (KHR_materials_iridescence)
# use different thin-film models, so each has its own thickness, tuned by rendering.
# (material name, Blender thickness nm, Blender film IOR, GLB thickness nm, GLB iridescence factor)
LENS_COATINGS = [
    # name, Blender film thickness nm, Blender film IOR, GLB role
    ('element 1 coating', 320.0, 1.70, 'outer'),      # outer lens surface: AR sheen
    ('element 2 coating', 165.0, 1.72, 'inner'),
    ('curved internal optical coating', 320.0, 1.70, 'outer'),
    ('internal prism optic', 165.0, 1.72, 'inner'),
    ('Continuous clear optical cover', 0.0, 1.22, 'cover'),   # clear cover glass
    ('antireflective clear cover', 0.0, 1.22, 'cover'),
]
# GLB (three.js) roles. three.js renders stacked transmissive layers from a blurred buffer that
# cannot see other transparent layers, which turns a lens stack into fog, and alpha-blended glass
# only tints uniformly. So exactly one layer, the outer lens surface, is clear refractive glass
# carrying a partial-strength iridescent reflection (blue-violet head-on, warm at grazing angles,
# tuned by screenshots of the real viewer); the inner element is dark glossy glass seen through
# it, and the cover glass is invisible.
GLB_OUTER_IRIDESCENCE = {'iridescenceFactor': .28, 'iridescenceIor': 1.6,
                         'iridescenceThicknessMinimum': 360.0, 'iridescenceThicknessMaximum': 360.0}


def coating_for(name):
    return next((c for c in LENS_COATINGS if c[0] in name), None)


def apply_lens_coatings():
    """Set the Principled thin film on every lens/cover coating material (Cycles/EEVEE)."""
    for mat in bpy.data.materials:
        if mat.use_nodes and any(name in mat.name for name in ('Optical outer rim', 'Optical barrel', 'baffle ridge', 'iris retainer ring')):
            node = mat.node_tree.nodes['Principled BSDF']
            node.inputs['Base Color'].default_value = (.0015, .0018, .0022, 1)
            node.inputs['Metallic'].default_value = 0
            node.inputs['Roughness'].default_value = .5
            node.inputs['Specular IOR Level'].default_value = .03
            node.inputs['Coat Weight'].default_value = 0
        if mat.use_nodes and 'internal prism optic' in mat.name:
            node = mat.node_tree.nodes['Principled BSDF']
            node.inputs['Base Color'].default_value = (.001, .001, .001, 1)
            node.inputs['Metallic'].default_value = 0
            node.inputs['Roughness'].default_value = .6
            node.inputs['Specular IOR Level'].default_value = 0
            node.inputs['Coat Weight'].default_value = 0
        coating = coating_for(mat.name)
        if not (coating and mat.use_nodes):
            continue
        for node in mat.node_tree.nodes:
            if node.type == 'BSDF_PRINCIPLED':
                node.inputs['Thin Film Thickness'].default_value = coating[1]
                node.inputs['Thin Film IOR'].default_value = coating[2]


def add_glb_iridescence(path, foldable=False):
    """The glTF exporter drops Principled thin film; write it as KHR_materials_iridescence so
    model-viewer/three.js shows the same view-dependent colour while rotating."""
    import struct
    raw = path.read_bytes()
    json_len, _ = struct.unpack_from('<II', raw, 12)
    gltf = json.loads(raw[20:20+json_len])
    from optics import REVISION
    if gltf.get('asset', {}).get('extras', {}).get('opticsTreatment', {}).get('revision') == REVISION:
        return 0
    changed = 0
    for mat in gltf.get('materials', []):
        if mat.get('name', '').startswith('Device screen |'):
            mat.setdefault('pbrMetallicRoughness', {})['roughnessFactor'] = .22
            extensions = mat.setdefault('extensions', {})
            extensions.pop('KHR_materials_unlit', None)
            extensions['KHR_materials_specular'] = {'specularFactor': .6}
        if foldable and mat.get('name', '').startswith('Device screen |'):
            # Folded views expose the OLED from steep angles and occasionally from its back face.
            # Keep both sides renderable and give the exported material a lit fallback so WebGL
            # never flashes the old near-black placeholder while the runtime texture is created.
            mat['doubleSided'] = True
            pbr = mat.setdefault('pbrMetallicRoughness', {})
            pbr['baseColorFactor'] = [.07, .16, .22, 1]
            mat['emissiveFactor'] = [.07, .16, .22]
            changed += 1
        coating = coating_for(mat.get('name', ''))
        if not coating:
            continue
        role = coating[3]
        ext = mat.setdefault('extensions', {})
        for key in ('KHR_materials_transmission', 'KHR_materials_clearcoat', 'KHR_materials_iridescence',
                    'KHR_materials_specular'):
            ext.pop(key, None)
        mat.pop('alphaMode', None)
        if role == 'outer':
            mat['pbrMetallicRoughness'] = {'baseColorFactor': [.05, .09, .18, 1], 'metallicFactor': 0,
                                           'roughnessFactor': 0}
            ext['KHR_materials_transmission'] = {'transmissionFactor': 1}
            ext['KHR_materials_ior'] = {'ior': 1.5}
            ext['KHR_materials_iridescence'] = dict(GLB_OUTER_IRIDESCENCE)
        elif role == 'inner':
            mat['pbrMetallicRoughness'] = {'baseColorFactor': [.015, .018, .022, 1], 'metallicFactor': 0,
                                           'roughnessFactor': .06}
        else:
            mat['pbrMetallicRoughness'] = {'baseColorFactor': [1, 1, 1, 0], 'metallicFactor': 0,
                                           'roughnessFactor': 0}
            mat['alphaMode'] = 'BLEND'
        changed += 1
    if not changed:
        from optics import apply_glb
        apply_glb(path, BASE/'.optics-backup')
        return 0
    used = gltf.setdefault('extensionsUsed', [])
    for name in ('KHR_materials_iridescence', 'KHR_materials_specular'):
        if name not in used:
            used.append(name)
    data = json.dumps(gltf, separators=(',', ':')).encode()
    data += b' '*((4-len(data) % 4) % 4)
    rest = raw[20+json_len:]
    total = 12+8+len(data)+len(rest)
    path.write_bytes(struct.pack('<III', 0x46546C67, 2, total)+struct.pack('<II', len(data), 0x4E4F534A)+data+rest)
    from optics import apply_glb
    apply_glb(path, BASE/'.optics-backup')
    return changed


def configure_fold_animation(profile, root):
    """Keyframe the named cover-panel pivot so the GLB carries one real open→closed Fold clip."""
    articulation = profile.get('articulation')
    if not articulation:
        return
    if articulation.get('joints'):
        configure_multi_hinge_animation(profile, root)
        return
    pivot = bpy.data.objects[articulation['pivots'][articulation['moving_panel']]]
    scene = bpy.context.scene
    scene.render.fps = 24
    start = 1
    end = start + round(articulation.get('duration_seconds', 1.0)*scene.render.fps)
    scene.frame_start, scene.frame_end = start, end
    pivot.rotation_mode = 'XYZ'
    axis_index = {'X': 0, 'Y': 1, 'Z': 2}[articulation['axis']]
    pivot.rotation_euler[axis_index] = math.radians(articulation.get('open_degrees', 0))
    pivot.keyframe_insert(data_path='rotation_euler', index=axis_index, frame=start)
    pivot.rotation_euler[axis_index] = math.radians(articulation['closed_degrees'])
    pivot.keyframe_insert(data_path='rotation_euler', index=axis_index, frame=end)
    if pivot.animation_data and pivot.animation_data.action:
        action = pivot.animation_data.action
        action.name = articulation['animation']
        spine = bpy.data.objects.get('Fold pivot | Hinge spine')
        if spine and 'hinge' in profile:
            spine.animation_data_create()
            spine.animation_data.action = action
            # One shared, multi-slot action exports the panel and barrel as one Fold clip.
            spine.animation_data.action_slot = action.slots.new('OBJECT', spine.name)
            hinge = profile['hinge']
            for frame in range(start, end+1):
                fraction = (frame-start)/(end-start)
                angle = math.radians(articulation['closed_degrees'])*fraction/2
                # Bridge the two rear-edge anchors instead of swinging a full-width barrel
                # through the panels. The ellipse retracts when open and spans the closed depth.
                panel_angle = angle*2
                anchor_x = hinge['closed_spine_center_x_mm']
                anchor_z = hinge['spine_center_z_mm']
                reach = articulation['axis_mm'][2]-anchor_z
                moving_x = -anchor_x*math.cos(panel_angle)-reach*math.sin(panel_angle)
                moving_z = articulation['axis_mm'][2]+anchor_x*math.sin(panel_angle)-reach*math.cos(panel_angle)
                span = 2*abs(anchor_x*math.cos(angle)+reach*math.sin(angle))+hinge['spine_depth_mm']
                spine.rotation_euler[axis_index] = angle
                spine.location.x = (anchor_x+moving_x)*MM/2
                spine.location.z = (anchor_z+moving_z)*MM/2
                spine.scale.x = span/hinge['spine_width_mm']
                spine.keyframe_insert(data_path='rotation_euler', index=axis_index, frame=frame)
                spine.keyframe_insert(data_path='location', frame=frame)
                spine.keyframe_insert(data_path='scale', frame=frame)
        # Viewer playback supplies easing; keep the barrel at exactly half the panel angle.
        for layer in action.layers:
            for strip in layer.strips:
                for channelbag in strip.channelbags:
                    for curve in channelbag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
    scene.frame_set(start)
    root['fold_animation'] = articulation['animation']
    root['fold_axis'] = articulation['axis']
    root['fold_axis_mm'] = articulation['axis_mm']


def configure_multi_hinge_animation(profile, root):
    """Explicit Samsung axis/topology option; legacy Pixel/Duo animation stays unchanged."""
    from mathutils import Matrix
    articulation = profile['articulation']
    scene = bpy.context.scene
    scene.render.fps = 24
    scene.frame_start, scene.frame_end = 1, 25
    action = bpy.data.actions.new(articulation['animation'])
    for joint in articulation['joints']:
        pivot = bpy.data.objects[articulation['pivots'][joint['moving_panel']]]
        spine = bpy.data.objects[joint['spine_pivot']]
        for obj in (pivot, spine):
            obj.rotation_mode = 'XYZ'
            obj.animation_data_create()
            obj.animation_data.action = action
            obj.animation_data.action_slot = action.slots.new('OBJECT', obj.name)
        axis_index = {'X':0, 'Y':1}[joint['axis']]
        axis = Vector(joint['axis_mm'])
        fixed_anchor = Vector(joint['fixed_anchor_mm'])
        moving_anchor = Vector(joint['moving_anchor_mm'])
        for frame in range(1, 26):
            fraction = max(0, min(1, ((frame-1)/24-joint.get('start_fraction',0)) /
                (joint.get('end_fraction',1)-joint.get('start_fraction',0))))
            angle = math.radians(joint['closed_degrees'])*fraction
            pivot.rotation_euler[axis_index] = angle
            pivot.keyframe_insert(data_path='rotation_euler', index=axis_index, frame=frame)
            moving = axis + Matrix.Rotation(angle, 3, joint['axis']) @ (moving_anchor-axis)
            spine.location = (fixed_anchor+moving)*MM/2
            spine.rotation_euler[axis_index] = angle/2
            span = (moving-fixed_anchor).length + joint['spine_depth_mm']
            spine.scale[1 if joint['axis']=='X' else 0] = span/joint['spine_width_mm']
            for path in ('rotation_euler','location','scale'):
                spine.keyframe_insert(data_path=path, frame=frame)
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in bag.fcurves:
                    for key in curve.keyframe_points:
                        key.interpolation = 'LINEAR'
    scene.frame_set(1)
    root['fold_animation'] = articulation['animation']
    root['fold_axis'] = articulation['axis']
    root['fold_axis_mm'] = articulation['axis_mm']


def build(profile_path, output, screen_image=None, finish=None):
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    if finish:
        selected = profile['finishes'][finish]
        profile['finish'] = finish
        if 'materials' in profile:
            for name, settings in selected.items():
                profile['materials'][name].update(settings)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if 'asset' in profile:
        asset = (profile_path.parent / profile['asset']).resolve()
        if not asset.is_file():
            raise FileNotFoundError(asset)
        with bpy.data.libraries.load(str(asset), link=False) as (source, target):
            target.objects = source.objects
        root = bpy.data.objects[profile['root']]
        trace = load_trace(profile['id'])
        if trace and 'screen' in profile:  # reviewed asset keeps its geometry; frame comes from the skin
            traced_screen(profile['screen'], trace)
        for obj in [root, *root.children_recursive]:
            bpy.context.scene.collection.objects.link(obj)
        for obj in list(bpy.data.objects):
            if obj != root and obj not in root.children_recursive:
                bpy.data.objects.remove(obj, do_unlink=True)
        if finish:
            for role, settings in selected.items():
                shader = bpy.data.materials[profile['material_objects'][role]].node_tree.nodes['Principled BSDF']
                shader.inputs['Base Color'].default_value = tuple(value/12.92 if value <= .04045
                    else ((value+.055)/1.055)**2.4 for value in settings['rgb'])+(1,)
        if 'logo' in profile.get('material_objects', {}):
            shader = bpy.data.materials[profile['material_objects']['logo']].node_tree.nodes['Principled BSDF']
            color = profile['finishes'][profile['finish']]['logo']['rgb']
            shader.inputs['Base Color'].default_value = tuple(value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4 for value in color)+(1,)
        if profile['id'] == 'pixel-10-pro':
            from pixel_imported_front import calibrate_imported_pixel_front
            calibrate_imported_pixel_front(profile, root, trace)
    else:
        from geometry import create_device
        apply_trace(profile)
        sync_slab_body_corners(profile)
        root = create_device(profile)
    if profile.get('robot_arm'):
        from robot_geometry import create_robot_arm
        create_robot_arm(profile, root)
    if profile.get('nothing_glyphs'):
        from nothing_geometry import create_glyphs
        create_glyphs(profile, root)
    parts = [root, *root.children_recursive]
    body = profile['body_mm']
    screens = []
    for spec in profile.get('screens', [profile['screen']] if 'screen' in profile else []):
        screens.append((spec, *prepare_screen(spec, body, screen_image)))
    if profile['id'].startswith('pixel-'):
        from pixel_front_optics import enhance_pixel_front_optics
        enhance_pixel_front_optics(profile)
        from pixel_rear_optics import enhance_pixel_rear_optics
        enhance_pixel_rear_optics(profile)
    if profile.get('rail_details'):
        from pixel_rail_details import apply_pixel_rail_details
        apply_pixel_rail_details(profile, root)
    configure_fold_animation(profile, root)
    root['device_id'] = profile['id']
    root['accuracy'] = profile['accuracy']['camera_geometry']

    camera_data = bpy.data.cameras.new('Device front | orthographic')
    camera_data.type = 'ORTHO'
    camera_data.sensor_fit = 'VERTICAL'
    camera_data.ortho_scale = body['height']*MM
    camera_data.clip_start = .001
    camera = bpy.data.objects.new('Device front | orthographic', camera_data)
    bpy.context.scene.collection.objects.link(camera)
    camera.location = (0, 0, .5)
    bpy.context.scene.camera = camera
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.render.resolution_y = screens[0][0]['resolution'][1] if screens else 1080
    scene.render.resolution_x = round(scene.render.resolution_y*body['width']/body['height'])
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = True
    scene.view_settings.view_transform = 'Standard'

    output.mkdir(parents=True, exist_ok=True)
    bpy.context.preferences.filepaths.save_version = 0
    for image in bpy.data.images:
        if image.source == 'FILE' and image.users:
            image.pack()
    rail_name = profile.get('material_objects', {}).get('rail', 'rail')
    rail_material = bpy.data.materials.get(rail_name)
    if profile.get('form_factor', 'phone') == 'phone' and rail_material and rail_material.use_nodes:
        shader = rail_material.node_tree.nodes.get('Principled BSDF')
        if shader and shader.inputs['Metallic'].default_value > .5:
            shader.inputs['Roughness'].default_value = max(.1, min(.25, shader.inputs['Roughness'].default_value*.65))
    apply_lens_coatings()
    from optics import apply_blender
    apply_blender()
    bpy.ops.wm.save_as_mainfile(filepath=str(output/'model.blend'))

    # GLB cannot represent Cycles RGB dispersion / layered shader closures.
    # Keep those in the BLEND; export the same meshes with their base PBR shader.
    for mat in bpy.data.materials:
        if not mat.use_nodes:
            continue
        nodes = mat.node_tree.nodes
        shader = next((node for node in nodes if node.type == 'BSDF_PRINCIPLED'), None)
        result = next((node for node in nodes if node.type == 'OUTPUT_MATERIAL'), None)
        if shader and result:
            mat.node_tree.links.new(shader.outputs['BSDF'], result.inputs['Surface'])
            stamp = next((node for node in nodes if node.type == 'TEX_IMAGE'), None)
            if mat.name.startswith('Graphite G') and stamp:
                mat.node_tree.links.new(stamp.outputs['Alpha'], shader.inputs['Alpha'])
    bpy.ops.object.select_all(action='DESELECT')
    parts = [root, *root.children_recursive]
    for obj in parts:
        obj.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(output/'model.glb'), export_format='GLB',
                              export_animation_mode='NLA_TRACKS' if profile.get('robot_arm') else 'ACTIONS',
                              use_selection=True, export_extras=True, export_yup=True)
    add_glb_iridescence(output/'model.glb', foldable=bool(profile.get('articulation')))

    screen_metadata = []
    for spec, screen, material, width, height, center, actual_nodes in screens:
        cx, cy, cz = center
        radius = spec['corner_radius_mm']
        frame_body = spec.get('frame_body_mm',body)
        frame_cx, frame_cy = spec.get('frame_center_mm',[cx,cy])
        left = frame_body['width']/2 + frame_cx - width/2
        top = frame_body['height']/2 - frame_cy - height/2
        rail = profile['finishes'][profile['finish']]['rail']['rgb']
        if spec.get('frame_trace'):
            skin_bounds = write_skin_frame(output, spec)
        else:
            skin_bounds = None
            write_frame(output, spec, frame_body, left, top, width, height, rail)
        effective_rotation = list(spec.get('rotation_deg', [0,0,0]))
        if not spec.get('object_parts'):
            # Static folded companions may rotate the entire panel as well as the display mesh.
            # Report the world-facing side so renderers/viewers choose the actual visible face.
            bpy.context.view_layer.update()
            normal = screen.matrix_world.to_3x3() @ Vector((0,0,1))
            effective_rotation[1] = 0 if normal.z >= 0 else 180
        screen_metadata.append({'node': spec.get('node', screen.name), 'nodes': actual_nodes,
                   'material': material.name,
                   'resolution': spec['resolution'], 'size_mm': [width, height],
                   'center_mm': center, 'corner_radius_mm': radius,
                   'rotation_deg': effective_rotation,
                   'edge_curve_mm': spec.get('edge_curve_mm', 0),
                   'frame_bounds_mm': [left, top, width, height],
                   'frame_screen_px': skin_bounds,
                   'frame_file': spec.get('frame_file','frame.svg'), 'frame_body_mm': frame_body,
                   'cutouts': spec['cutouts'],
                   'uv': 'u right, v up; full image maps to [0,1] without cropping',
                   'input': 'Use raycast screen UV times actual stream size; reject cutouts and rounded corners'})
    metadata = {
        'id': profile['id'], 'name': profile['name'], 'finish': profile['finish'],
        'body_mm': body, 'screen': screen_metadata[0] if screen_metadata else None, 'screens': screen_metadata,
        'finishes': profile.get('finishes', {}), 'status': profile.get('status', 'reviewed reference'),
        'material_slots': profile.get('material_objects', {role:role for role in profile.get('materials', {})}),
        'coordinates': {'blend': 'metres; X right, Y up, front +Z',
                        'glb': 'metres; X right, Y front, Z down (Blender glTF Y-up conversion)',
                        'frame': 'millimetres; top-left origin, X right, Y down'},
        'accuracy': profile['accuracy'], 'sources': profile['sources'],
        'export': {'blend': 'Reviewed optical shaders; replaceable screen',
                   'glb': 'PBR approximation of optical shaders; replace screen material with unlit video texture'},
        'checks': {'screen_aspect_error': max((abs(item['size_mm'][0]/item['size_mm'][1] -
                        item['resolution'][0]/item['resolution'][1]) for item in screen_metadata), default=0),
                   'model_objects': len(parts)}
    }
    if 'camera_measurement' in profile:
        metadata['camera_measurement'] = profile['camera_measurement']
    if profile.get('articulation'):
        metadata['articulation'] = profile['articulation']
    if profile.get('robot_motion'):
        metadata['robot_motion'] = profile['robot_motion']
    (output/'device.json').write_text(json.dumps(metadata, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(metadata['checks']))


def write_frame(output, spec, body, left, top, width, height, rail):
    radius = spec['corner_radius_mm']
    cutouts = ''
    for cut in spec['cutouts']:
        cx = left+width/2+cut['center_mm'][0]
        cy = top+height/2-cut['center_mm'][1]
        if cut.get('outline_mm'):
            points = ' '.join(f'{cx+x},{cy-y}' for x,y in cut['outline_mm'])
            cutouts += f'<polygon points="{points}" fill="#07090c"/>'
        elif cut.get('size_mm'):
            cw, ch = cut['size_mm']
            cutouts += f'<rect x="{cx-cw/2}" y="{cy-ch/2}" width="{cw}" height="{ch}" rx="{cut["radius_mm"]}" fill="#07090c"/>'
        else:
            cutouts += f'<circle cx="{cx}" cy="{cy}" r="{cut["radius_mm"]}" fill="#07090c"/>'
    from geometry import outline
    silhouettes = []
    front_roll = body.get('edge_roll_mm', [body.get('edge_roll', .55)]*2)[1]
    glass_inset = max(body.get('front_rail_mm', .7), front_roll*.95)
    for inset in (0, glass_inset):
        radii = body.get('corner_radii_mm',[body['corner_radius']]*4)
        points = outline(body['width']-2*inset,body['height']-2*inset,[max(.1,r-inset) for r in radii],32)
        path = 'M'+' L'.join(f'{body["width"]/2+x:.5f},{body["height"]/2-y:.5f}' for x,y in points)+' Z'
        silhouettes.append(f'<path d="{path}"')
    if spec.get('frame_glass_border_mm'):
        border = spec['frame_glass_border_mm']
        points = outline(width+2*border,height+2*border,radius+border,32)
        path = 'M'+' L'.join(f'{left+width/2+x:.5f},{top+height/2-y:.5f}' for x,y in points)+' Z'
        silhouettes[1] = f'<path d="{path}"'
    color = '#'+''.join(f'{round(value*255):02x}' for value in rail)
    opening = f'<rect x="{left}" y="{top}" width="{width}" height="{height}" rx="{radius}" fill="black"/>'
    if spec.get('frame_use_outline') and spec.get('outline_mm'):
        points = ' '.join(f'{left+width/2+x},{top+height/2-y}' for x,y in spec['outline_mm'])
        opening = f'<polygon points="{points}" fill="black"/>'
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {body['width']} {body['height']}">
<defs><mask id="opening"><rect width="100%" height="100%" fill="white"/>
{opening}</mask></defs>
{silhouettes[0]} fill="{color}" style="--device-color:{color};fill:var(--device-color)" mask="url(#opening)"/>
{silhouettes[1]} fill="#101215" mask="url(#opening)"/>{cutouts}</svg>'''
    filename = spec.get('frame_file', 'frame.svg')
    (output/filename).write_text(svg, encoding='utf-8')


def write_skin_frame(output, spec):
    """Device frame = Google's emulator artwork with a transparent screen opening (PNG, cropped by
    research/trace_skins.py), plus an SVG wrapper. Returns the screen rectangle in frame pixels."""
    import base64
    import shutil
    trace = spec['frame_trace']
    source = SKIN_TRACES/trace['id']/trace['frame']
    stem = Path(spec.get('frame_file', 'frame.svg')).stem
    shutil.copyfile(source, output/f'{stem}.png')
    x0, y0, x1, y1 = trace['frame_crop_px']
    w, h = x1-x0, y1-y0
    screen = trace['frame_screen_px']
    data = base64.b64encode(source.read_bytes()).decode()
    scale = trace['mm_per_px']
    bounds = ' '.join(map(str, screen))
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w*scale:.3f}mm" height="{h*scale:.3f}mm" '
           f'viewBox="0 0 {w} {h}" data-screen="{bounds}">\n'
           f'<image width="{w}" height="{h}" href="data:image/png;base64,{data}"/>\n</svg>\n')
    (output/f'{stem}.svg').write_text(svg, encoding='utf-8')
    return screen

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('profile', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--screen-image', type=Path)
    parser.add_argument('--finish', help='Named finish from the profile')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    profile = args.profile.resolve()
    build(profile, (args.output or BASE/'exports'/profile.stem).resolve(), args.screen_image, args.finish)
