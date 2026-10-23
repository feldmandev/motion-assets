"""Validate HONOR linkage at every exported frame and render review poses."""
import json
import math
import struct
import sys
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

BASE = Path(__file__).resolve().parent
OUT = BASE/'exports/honor-robot-phone'


def world_mesh(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = BVHTree.FromPolygons([obj.matrix_world @ v.co for v in mesh.vertices],
                                 [list(p.vertices) for p in mesh.polygons], epsilon=1e-8)
    evaluated.to_mesh_clear()
    return result


def contains(tree, point, obj):
    location, normal, _, distance = tree.find_nearest(point)
    if location is None or distance < 1e-7 or (point-location).dot(normal) >= 0:
        return False
    # Confirm with solid angle: nearest-face normals alone misclassify concave rails.
    mesh = obj.data
    mesh.calc_loop_triangles()
    vertices = np.array([obj.matrix_world @ v.co for v in mesh.vertices], dtype=np.float64)
    triangles = vertices[[list(t.vertices) for t in mesh.loop_triangles]] - np.array(point)
    a, b, c = triangles[:, 0], triangles[:, 1], triangles[:, 2]
    la, lb, lc = (np.linalg.norm(v, axis=1) for v in (a, b, c))
    numerator = np.einsum('ij,ij->i', a, np.cross(b, c))
    denominator = la*lb*lc + np.einsum('ij,ij->i', a, b)*lc + np.einsum('ij,ij->i', b, c)*la + np.einsum('ij,ij->i', c, a)*lb
    return abs(np.arctan2(numerator, denominator).sum()) > math.pi


def verify():
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'model.blend'))
    scene = bpy.context.scene
    root = next(o for o in bpy.data.objects if o.get('device_id') == 'honor-robot-phone')
    names = ['Robot flip hinge', 'Robot pan motor', 'Robot pitch motor', 'Robot optical roll motor']
    nodes = [bpy.data.objects[n] for n in names]
    local = [n.location.copy() for n in nodes]
    static = [bpy.data.objects[n] for n in ['Body', 'Robot fixed rear island',
              'Robot fixed hinge mount', 'Robot fixed hinge foundation']]
    matrices = [n.matrix_world.copy() for n in static]
    attachment_error, static_error, link_tip_error = 0, 0, 0
    sampled = {}
    intersections = []
    poses = []
    enclosure = bpy.data.objects['Aluminum enclosure']
    obstacles = [enclosure, *[bpy.data.objects[name] for name in
                 ['Rear glass', 'Front black glass', 'Robot fixed rear island', 'Robot recessed dock floor',
                  'Robot shutter guide rail', 'Robot shutter guide rail.001',
                  'Robot fixed hinge foundation', 'Robot fixed hinge mount']]]
    fixed_trees = [(obj.name, world_mesh(obj)) for obj in obstacles]
    moving = [obj for parent in [nodes[0], bpy.data.objects['Robot dock shutter']]
              for obj in parent.children_recursive if obj.type == 'MESH']
    mount_contacts = {}
    for a, b in [('Aluminum enclosure', 'Robot fixed hinge foundation'),
                 ('Robot fixed hinge foundation', 'Robot fixed hinge mount'),
                 ('Robot fixed hinge mount', 'Robot flip axle')]:
        mount_contacts[f'{a} -> {b}'] = bool(world_mesh(bpy.data.objects[a]).overlap(world_mesh(bpy.data.objects[b])))
    assert all(mount_contacts.values()), mount_contacts
    for frame in range(1, 122):
        scene.frame_set(frame)
        bpy.context.view_layer.update()
        for node, offset in zip(nodes, local):
            attachment_error = max(attachment_error,
                                   (node.matrix_world.translation-node.parent.matrix_world @ offset).length/.001)
        for obj, matrix in zip(static, matrices):
            static_error = max(static_error, max(abs(obj.matrix_world[i][j]-matrix[i][j]) for i in range(4) for j in range(4)))
        sampled[frame] = {name: bpy.data.objects[name].matrix_world.copy()
                          for name in names+['Robot dock shutter', 'Robot optical axis']}
        tip = bpy.data.objects['Robot dogleg segment 2'].matrix_world @ Vector((0, .005, 0))
        on_pitch_axle = nodes[2].matrix_world @ Vector((.0115, 0, 0))
        link_tip_error = max(link_tip_error, (tip-on_pitch_axle).length/.001)
        # Intended bearing/foot contact is excluded; check moving head and dogleg against body.
        for obj in moving:
            name = obj.name
            tree = world_mesh(obj)
            for obstacle, fixed in fixed_trees:
                if name == 'Robot sliding dock cover' and obstacle.startswith('Robot shutter guide rail'):
                    continue  # The lid runs in its guide rails.
                if name == 'Robot flip axle' and obstacle in ['Robot fixed hinge mount', 'Robot fixed hinge foundation']:
                    continue  # Axle journals seat inside the mounting ears.
                fixed_obj = bpy.data.objects[obstacle]
                if fixed.overlap(tree) or contains(fixed, obj.matrix_world @ obj.data.vertices[0].co, fixed_obj) or contains(
                        tree, fixed_obj.matrix_world @ fixed_obj.data.vertices[0].co, obj):
                    intersections.append({'frame': frame, 'object': name, 'obstacle': obstacle})
        if frame in [1, 19, 40, 64, 85, 103, 121]:
            axis = bpy.data.objects['Robot optical axis']
            poses.append({'frame': frame, 'camera_center_mm': [v/.001 for v in nodes[-1].matrix_world.translation],
                          'optical_forward': list((axis.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized())})
    result = {'frames_checked': 121, 'max_attachment_error_mm': attachment_error,
              'max_link_mesh_tip_to_pitch_axle_error_mm': link_tip_error,
              'max_static_transform_error': static_error, 'body_surface_intersections': intersections,
              'poses': poses, 'stationary_obstacles_checked': [obj.name for obj in obstacles],
              'moving_meshes_checked': [obj.name for obj in moving], 'mount_contacts': mount_contacts,
              'intentional_mating_contacts': ['Robot sliding dock cover / Robot shutter guide rails',
                                             'Robot flip axle / fixed hinge mount and foundation journals'],
              'scope': 'All moving meshes versus enclosure, rear/front glass, island, floor, guides, foundation and mount; surface crossings plus solid-angle containment probes for connected closed meshes. Shutter/guide and axle/support mating contacts excluded. Bearing fits and motor internals are simplified, not OEM mechanical certification.'}
    (OUT/'robot-verification.json').write_text(json.dumps(result, indent=2)+'\n')
    assert attachment_error < 1e-4, result
    assert link_tip_error < 1e-4, result
    assert static_error < 1e-8, result
    assert not intersections, intersections[:10]
    assert poses[0]['optical_forward'][2] < -.999
    assert poses[-1]['optical_forward'][2] > .999
    binary = (OUT/'model.glb').read_bytes()
    length = struct.unpack_from('<I', binary, 12)[0]
    gltf = json.loads(binary[20:20+length])
    clips = gltf.get('animations', [])
    assert len(clips) == 1 and clips[0]['name'] == 'Robot deploy', [c['name'] for c in clips]
    targets = {gltf['nodes'][c['target']['node']]['name'] for c in clips[0]['channels']}
    assert len(clips[0]['channels']) == 5 and set(names+['Robot dock shutter']) == targets, targets
    times = [(gltf['accessors'][s['input']]['min'][0], gltf['accessors'][s['input']]['max'][0])
             for s in clips[0]['samplers']]
    assert all(abs(start-1/30) < 1e-6 and abs(end-121/30) < 1e-6 for start, end in times), times
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(OUT/'model.glb'))
    imported_error = 0
    for frame, matrices in sampled.items():
        bpy.context.scene.frame_set(frame)
        bpy.context.view_layer.update()
        for name, expected in matrices.items():
            actual = bpy.data.objects[name].matrix_world
            imported_error = max(imported_error, max(abs(actual[i][j]-expected[i][j])
                                                     for i in range(4) for j in range(4)))
    result['glb'] = {'clip': clips[0]['name'], 'channels': len(clips[0]['channels']),
                     'time_start_seconds': times[0][0], 'time_end_seconds': times[0][1],
                     'motion_duration_seconds': times[0][1]-times[0][0],
                     'animated_nodes': sorted(targets), 'reimported_frames_checked': 121,
                     'max_transform_component_error': imported_error}
    (OUT/'robot-verification.json').write_text(json.dumps(result, indent=2)+'\n')
    assert imported_error < 2e-5, result['glb']
    print(json.dumps(result))
    bpy.ops.wm.open_mainfile(filepath=str(OUT/'model.blend'))
    return bpy.context.scene


def renders(scene):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.render.resolution_x = 900
    scene.render.resolution_y = 900
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world = bpy.data.worlds.new('Robot review world')
    scene.world.color = (.2, .2, .2)
    scene.view_settings.view_transform = 'AgX'
    camera = scene.camera
    camera.data.ortho_scale = .185
    target = Vector((0, .022, -.006))
    camera.location = (.16, .07, -.35)
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    for name, pos, power, size in [('Robot key', (.08, .18, -.2), 8, .18),
                                    ('Robot fill', (-.2, .08, -.08), 6, .15),
                                    ('Robot rim', (.06, .08, .15), 12, .13)]:
        data = bpy.data.lights.new(name, 'AREA')
        data.energy, data.shape, data.size = power, 'DISK', size
        obj = bpy.data.objects.new(name, data)
        scene.collection.objects.link(obj)
        obj.location = pos
        obj.rotation_euler = (target-obj.location).to_track_quat('-Z', 'Y').to_euler()
    for frame in [1, 19, 40, 64, 85, 103, 121]:
        scene.frame_set(frame)
        scene.render.filepath = str(OUT/f'robot-pose-{frame:03}.png')
        bpy.ops.render.render(write_still=True)
    # Close inspection of the deployed chain from the display-facing side.
    camera.data.ortho_scale = .09
    target = Vector((.015, .087, 0))
    camera.location = (.1, .10, .28)
    camera.rotation_euler = (target-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.render.filepath = str(OUT/'robot-deployed-front.png')
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if '--output' in args:
        OUT = Path(args[args.index('--output')+1]).resolve()
    scene = verify()
    if '--renders' in sys.argv:
        renders(scene)
