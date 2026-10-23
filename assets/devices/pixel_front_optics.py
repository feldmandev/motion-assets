"""Opt-in Pixel selfie detail; retain each measured aperture and its existing parent.

Call enhance_pixel_front_optics(profile) after prepare_screen, before fold animation.
No import-time Blender dependency. Optical internals are an illustrative shallow
stack inside the old disk, not measured lens prescriptions or new OLED cutouts.
"""
import math

MM = .001
SEGMENTS = 64


def aperture_mesh(radius_mm, depth_mm=.025, front_sign=1):
    """Return local metre vertices, faces and material slots (well/rim/glass/lens).

    Pixel 9 SDK artwork resolves an optic approximately .32 of the aperture
    radius and an inner annulus around .55-.65. Keep the complete black well.
    Depth is deliberately compressed into the existing aperture's envelope.
    """
    if radius_mm <= 0 or depth_mm <= 0 or front_sign not in (-1, 1):
        raise ValueError('Positive aperture dimensions and a +/-1 front sign required')
    vertices, faces, slots = [], [], []

    def surface(rings, materials):
        previous = None
        for index, (radius, z) in enumerate(rings):
            ring = []
            for step in range(SEGMENTS if radius else 1):
                angle = step*2*math.pi/SEGMENTS
                ring.append(len(vertices))
                vertices.append((radius*radius_mm*MM*math.cos(angle),
                                 radius*radius_mm*MM*math.sin(angle),
                                 z*depth_mm*MM*front_sign))
            if previous is not None:
                for step in range(SEGMENTS):
                    nxt = (step+1) % SEGMENTS
                    if len(previous) == 1:
                        face = (previous[0], ring[nxt], ring[step])
                    elif len(ring) == 1:
                        face = (previous[step], previous[nxt], ring[0])
                    else:
                        face = (previous[step], previous[nxt], ring[nxt], ring[step])
                    faces.append(face if front_sign == 1 else tuple(reversed(face)))
                    slots.append(materials[index-1])
            previous = ring

    # Closed black well with a narrow graphite annulus, not a bright metal bezel.
    surface([(0, -.5), (1, -.5), (1, .5), (.70, .5), (.66, .38),
             (.57, .38), (.48, -.28), (0, -.28)], [0, 0, 0, 0, 1, 0, 0])
    # A dark deeper element and exactly one transmissive cover; no glossy sphere.
    surface([(0, -.26), (.32, -.26), (.32, -.17), (.24, -.12), (0, -.10)],
            [3, 3, 3, 3])
    surface([(0, -.04), (.36, -.04), (.36, 0), (.27, .035), (0, .06)],
            [2, 2, 2, 2])
    return vertices, faces, slots


def enhance_pixel_front_optics(profile):
    """Replace known Pixel camera disks; calling this opts in.

    Resolve names from each prepared screen spec, including split inner screens
    and rear-facing covers. Pixel 4 profiles identify their single visible RGB
    camera; concealed IR hardware does not receive extra visible pupils.
    """
    if not profile['id'].startswith('pixel-'):
        return []
    import bpy
    from geometry import material

    targets = []
    for spec in profile.get('screens', [profile['screen']] if 'screen' in profile else []):
        if not spec.get('create_cutouts'):
            continue
        prefix = spec['object'] if spec.get('object_parts') else spec.get('node', spec['object'])
        sign = -1 if spec.get('rotation_deg', [0, 0, 0])[1] == 180 else 1
        for index, cutout in enumerate(spec['cutouts']):
            if cutout.get('size_mm') or cutout.get('outline_mm'):
                continue
            targets.append((f'{prefix} | selfie aperture {index}', cutout['radius_mm'], sign, None))
    # The imported 10 Pro has this named front pair, not a generated selfie disk.
    # Its old coating would sit above the new lens; retire it after replacement.
    imported_selfie = profile['id'] == 'pixel-10-pro' and profile.get('asset')
    if imported_selfie:
        spec = profile['screen']
        cutout = spec['cutouts'][0]
        cx, cy, cz = spec['center_mm']
        x, y = cutout['center_mm']
        targets.append(('Selfie camera | black aperture', cutout['radius_mm'], 1,
                        (cx+x, cy+y, cz+.025)))
    # Original Fold's inner camera is in its upper bezel, outside the OLED.
    if profile['id'] in ('pixel-fold-unfolded', 'pixel-4', 'pixel-4-xl') and len(profile.get('bezel_cameras', [])) == 1:
        targets.append(('Inner bezel selfie camera', profile['bezel_cameras'][0][3], 1, None))
    if not targets:
        return []

    materials = []
    for name, rgb, metal, rough in (
        ('well', (.025, .027, .030), 0, .52),
        ('annulus', (.085, .090, .100), .12, .32),
        ('coated glass', (.65, .67, .72), 0, .10),
        ('deep lens', (.055, .035, .095), 0, .17),
    ):
        full_name = f'Pixel front optics | {name}'
        mat = bpy.data.materials.get(full_name)
        if mat is None:
            mat = material(full_name, rgb, metal, rough)
            if name == 'coated glass':
                shader = mat.node_tree.nodes['Principled BSDF']
                shader.inputs['Transmission Weight'].default_value = .85
                shader.inputs['IOR'].default_value = 1.46
                shader.inputs['Coat Weight'].default_value = .25
        materials.append(mat)

    changed = []
    for name, radius, sign, center in targets:
        obj = bpy.data.objects[name]
        old_mesh = obj.data
        depth = (max(v.co.z for v in old_mesh.vertices)-min(v.co.z for v in old_mesh.vertices))/MM
        vertices, faces, slots = aperture_mesh(radius, depth, sign)
        mesh = bpy.data.meshes.new(f'{name} | shallow optical stack')
        mesh.from_pydata(vertices, [], faces)
        mesh.update()
        for mat in materials:
            mesh.materials.append(mat)
        for face, slot in zip(mesh.polygons, slots):
            face.material_index = slot
            face.use_smooth = len(face.vertices) == 4
        obj.data = mesh
        if center is not None:
            obj.location = tuple(value*MM for value in center)
        if old_mesh.users == 0:
            bpy.data.meshes.remove(old_mesh)
        changed.append(name)
    if imported_selfie:
        old_coating = bpy.data.objects.get('Selfie lens coating')
        if old_coating is not None:
            bpy.data.objects.remove(old_coating, do_unlink=True)
    return changed
