"""Opt-in measured Pixel rail surfaces; no device/finish defaults or build hook.

Call apply_pixel_rail_details(profile, root) after enclosure/screen deformation,
before export. See research/pixel-rail-details-production.json for the contract.
Coordinates are millimetres in root space (X right, Y up, Z front).
"""
import bmesh
import bpy
from mathutils import Vector

MM = .001
OFFSET = .003 * MM


def _role_material(profile, role):
    return bpy.data.materials[profile.get('material_objects', {}).get(role, role)]


def _detail_material(profile, role, spec):
    """Clone the selected finish, retaining runtime palette/material-role metadata."""
    mat = _role_material(profile, spec['color_role']).copy()
    mat.name = role
    shader = mat.node_tree.nodes['Principled BSDF']
    if 'finish_role' in spec:
        finish = _role_material(profile, spec['finish_role']).node_tree.nodes['Principled BSDF']
        for key in ('Metallic', 'Roughness'):
            shader.inputs[key].default_value = finish.inputs[key].default_value
    for key, socket in (('metal', 'Metallic'), ('rough', 'Roughness')):
        if key in spec:
            shader.inputs[socket].default_value = spec[key]
    overrides = dict(profile.get('materials', {}).get(role, {}))
    overrides.update(profile.get('finishes', {}).get(profile.get('finish'), {}).get(role, {}))
    if 'rgb' in overrides:
        shader.inputs['Base Color'].default_value = tuple(
            v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in overrides['rgb']) + (1,)
    for key, socket in (('metal', 'Metallic'), ('rough', 'Roughness')):
        if key in overrides:
            shader.inputs[socket].default_value = overrides[key]
    roles = profile.setdefault('material_objects', {key: key for key in profile.get('materials', {})})
    roles[role] = mat.name
    for palette in profile.get('finishes', {}).values():
        if role not in palette:
            palette[role] = {'rgb': list(palette[spec['color_role']]['rgb'])}
    return mat


def _antenna_mesh(source, rail_index, seam, mat):
    """Clip actual aluminum only; cavity/port material faces are never copied."""
    axis = 1 if seam['edge'] in ('left', 'right') else 0
    edge_axis = 1-axis
    positive = seam['edge'] in ('right', 'top')
    edge = (max if positive else min)(v.co[edge_axis] for v in source.vertices)
    boundary = edge + (-1 if positive else 1)*seam['inset_mm']*MM
    center, half = seam['center_axis_mm']*MM, seam['width_mm']*MM/2
    bm = bmesh.new()
    try:
        bm.from_mesh(source)
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.material_index != rail_index], context='FACES')
        # Large front/back n-gons must be triangulated before clipping narrow seams.
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        planes = ((axis, center-half, 1), (axis, center+half, -1),
                  (edge_axis, boundary, 1 if positive else -1))
        for dim, value, sign in planes:
            point = Vector((0, 0, 0)); point[dim] = value
            normal = Vector((0, 0, 0)); normal[dim] = sign
            bmesh.ops.bisect_plane(bm, geom=list(bm.verts)+list(bm.edges)+list(bm.faces),
                                  dist=1e-9, plane_co=point, plane_no=normal)
            # Float32 cut vertices can land several nanometres beyond the plane.
            outside = [v for v in bm.verts if sign*(v.co[dim]-value) < -1e-7]
            bmesh.ops.delete(bm, geom=outside, context='VERTS')
        if not bm.faces:
            raise ValueError('Empty measured antenna patch: '+seam['id'])
        bm.normal_update()
        for vertex in bm.verts:
            vertex.co += vertex.normal*OFFSET
        for face in bm.faces:
            face.material_index = 0
        mesh = bpy.data.meshes.new('Antenna seam | '+seam['id'])
        bm.to_mesh(mesh)
        mesh.materials.append(mat)
        return mesh
    finally:
        bm.free()


def apply_pixel_rail_details(profile, root):
    """Apply explicit per-profile data; profiles without rail_details are untouched.

    Old strips are removed by exact name only after every new patch is nonempty.
    No enclosure vertices, cavity slots, optics, glass, ports or UVs are changed.
    Returns patch counts for the parent's post-build verification.
    """
    details = profile.get('rail_details')
    if not details:
        return {'applied': False, 'reason': 'no measured rail_details'}
    if not profile['id'].startswith('pixel-'):
        raise ValueError('rail_details requires an explicitly opted-in Pixel profile')
    bpy.context.view_layer.update()
    objects = {obj.name: obj for obj in (root, *root.children_recursive)}
    seams = [dict(seam, inset_mm=seam['inset_mm'] if 'inset_mm' in seam
                  else profile['body_mm']['front_rail_mm'])
             for seam in details.get('antenna_breaks', [])]
    if len({s['id'] for s in seams}) != len(seams):
        raise ValueError('Measured antenna IDs must be unique')
    for seam in seams:
        if seam['edge'] not in ('left', 'right', 'top', 'bottom') or min(seam['width_mm'], seam['inset_mm']) <= 0:
            raise ValueError('Invalid measured antenna: '+seam['id'])
    replacement = details.get('replace_objects', [])
    if replacement and (not seams or len(seams) != details['replacement_verified_count']):
        raise ValueError('Old antenna strips require the complete measured replacement set')
    old_objects = [objects[name] for name in replacement]
    # Resolve camera objects/material slots before replacing any old strips.
    camera = details.get('camera_sidewall')
    if camera:
        housing = objects[camera['object']]
        face_index = list(housing.data.materials).index(_role_material(profile, camera['face_material']))
    mats = {role: _detail_material(profile, role, spec) for role, spec in details.get('materials', {}).items()}
    patches, sources = [], {}
    try:
        for seam in seams:
            name = seam.get('enclosure', details.get('enclosure'))
            enclosure = objects[name]
            if name not in sources:
                rail_index = list(enclosure.data.materials).index(_role_material(profile, details['rail_material']))
                source = bpy.data.meshes.new_from_object(enclosure.evaluated_get(bpy.context.evaluated_depsgraph_get()))
                source.transform(root.matrix_world.inverted() @ enclosure.matrix_world)
                sources[name] = source, rail_index
            source, rail_index = sources[name]
            patches.append((seam, enclosure, _antenna_mesh(source, rail_index, seam, mats[seam['material']])))
    except Exception:
        for _, _, mesh in patches:
            bpy.data.meshes.remove(mesh)
        raise
    finally:
        for source, _ in sources.values():
            bpy.data.meshes.remove(source)
    result = {'applied': True, 'antenna_breaks': [], 'removed_objects': replacement}
    for seam, enclosure, mesh in patches:
        obj = bpy.data.objects.new('Antenna seam | '+seam['id'], mesh)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = enclosure.parent or root
        obj.matrix_basis = obj.parent.matrix_world.inverted() @ root.matrix_world
        obj['material_role'] = seam['material']
        result['antenna_breaks'].append({'id': seam['id'], 'polygons': len(mesh.polygons)})
    for obj in old_objects:
        bpy.data.objects.remove(obj, do_unlink=True)
    if camera:
        # Restrict assignment to the original face role; black cavity slots stay intact.
        side_index = len(housing.data.materials)
        housing.data.materials.append(mats[camera['material']])
        normal_matrix = (root.matrix_world.inverted() @ housing.matrix_world).to_3x3().inverted().transposed()
        count = 0
        for face in housing.data.polygons:
            normal = (normal_matrix @ face.normal).normalized()
            if face.material_index == face_index and abs(normal.z) < .9999:
                face.material_index = side_index
                count += 1
        result['camera_sidewall_polygons'] = count
    return result
