"""Dedicated estimated HONOR robot linkage. All coordinates local in millimetres."""
import math

import bpy
from mathutils import Vector
from geometry import MM, disk, material, slab, subtract


def pivot(name, parent, position):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = tuple(v*MM for v in position)
    obj.rotation_mode = 'XYZ'
    return obj


def link(name, start, end, width, depth, mat, parent):
    delta = Vector(end)-Vector(start)
    obj = slab(name, width, delta.length, depth, min(width/2, 1.1),
               (Vector(start)+Vector(end))/2, mat, parent, .25)
    obj.rotation_euler = Vector((0, 1, 0)).rotation_difference(delta.normalized()).to_euler()
    return obj


def create_robot_arm(profile, root):
    spec = profile['robot_arm']
    mats = {k: bpy.data.materials[k] for k in ('arm', 'bar', 'rail', 'black', 'flash', 'logo')}
    glass = material('Robot optical glass', [.028, .052, .085], .45, .13)
    iris = material('Robot iris', [.055, .09, .13], .7, .25)
    body = bpy.data.objects['Body']
    depth = profile['body_mm']['depth']
    back = -depth/2
    ix, iy = spec['island_center_mm']
    iw, ih, radius = spec['island_size_mm']
    # Fixed island/dock; the protective shutter alone slides across its surface.
    island = slab('Robot fixed rear island', iw, ih, 2.4, radius, (ix, iy, back-1.2), mats['bar'], body, .4)
    cavity = slab('Robot dock cavity tool', 30.8, 43.2, 4, 3.2,
                  (17.5, 57.5, back-1.2), None, body, .08)
    subtract(island, cavity)
    exit_tool = slab('Robot island hinge exit tool', 14, 8, 5, .8,
                     (17.5, 79.5, back-1.2), None, body, .08)
    subtract(island, exit_tool)
    # The mechanism occupies a pocket inside the phone, rather than floating above a solid back.
    for name in ['Aluminum enclosure', 'Rear glass']:
        shell = bpy.data.objects[name]
        cutter = slab('Robot chassis pocket tool', 30.8, 43.2, 22.5, 3.2,
                      (17.5, 57.5, -8.75), None, body, .08)
        subtract(shell, cutter)
        notch = slab('Robot hinge exit tool', 14, 8, 22.5, .8,
                     (17.5, 79.5, -8.75), None, body, .08)
        subtract(shell, notch)
    # Seat the liner against the pocket base at z=2.5; its visible face must not be coplanar.
    slab('Robot recessed dock floor', 30, 42, .12, 3, (17.5, 57.5, 2.44), mats['black'], body, .035)
    for y in [35.8, 79.2]:
        rail = slab('Robot shutter guide rail', 68, .8, 1.2, .35, (0, y, -7.4), mats['rail'], body, .12)
        if y > 70:
            notch = slab('Robot guide hinge exit tool', 14, 2, 4, .35,
                         (17.5, y, -7.4), None, body, .08)
            subtract(rail, notch)
    for i, (x, y, r) in enumerate([(-10, 65, 3.3), (-10, 48, 3.0)]):
        disk(f'Robot fixed lens collar {i}', x, y, -6.95, r+.35, .35, mats['rail'], body)
        disk(f'Robot fixed optical glass {i}', x, y, -7.15, r, .1, glass, body)
        disk(f'Robot fixed pupil {i}', x, y, -7.22, r*.42, .05, mats['black'], body)
    disk('Robot flash rim', -24, 65, -7.0, 2.0, .2, mats['rail'], body)
    disk('Robot flash', -24, 65, -7.13, 1.5, .1, mats['flash'], body)
    anchor = spec['anchor_mm']
    # Side ears hold the axle; a central slot clears the rotating foot.
    foundation = slab('Robot fixed hinge foundation', 12, 6, 3, 1,
         (anchor[0], anchor[1], 1.5), mats['arm'], body, .25)
    mount = slab('Robot fixed hinge mount', 12, 6, 3.5, 1, anchor, mats['arm'], body, .25)
    for part in [foundation, mount]:
        clearance = slab('Robot hinge foot clearance tool', 9.4, 8, 12, .1,
                         (anchor[0], anchor[1], -5.25), None, body, .04)
        subtract(part, clearance)
    fold = pivot('Robot flip hinge', body, anchor)
    barrel = disk('Robot flip axle', 0, 0, 0, 2.1, 13, mats['rail'], fold)
    barrel.rotation_euler[1] = math.pi/2
    stem = spec['stem_mm']
    slab('Robot flip foot', 9, stem+1, 3.5, .8, (0, -stem/2, 0), mats['arm'], fold, .25)
    pan = pivot('Robot pan motor', fold, (0, -stem, 0))
    hub = disk('Robot pan bearing', 0, 0, 0, 3.6, 2.2, mats['rail'], pan)
    hub.rotation_euler[0] = math.pi/2
    # A connected dogleg from pan base to the side of the pitch motor, not a floating head.
    joints = [(0, 0, 0), (5.5, -3, 0), (11.5, -8.5, 0), (11.5, -18.5, 0)]
    for i, (a, b) in enumerate(zip(joints, joints[1:])):
        link(f'Robot dogleg segment {i}', a, b, 4.2, 3.2, mats['arm'], pan)
    pitch = pivot('Robot pitch motor', pan, (0, -18.5, 0))
    bearing = disk('Robot side pitch bearing', 10.8, 0, 0, 3.0, 3.8, mats['rail'], pitch)
    bearing.rotation_euler[1] = math.pi/2
    slab('Robot pitch carrier', 19.5, 17, .4, 3.0, (0, 0, 3.6), mats['arm'], pitch, .1)
    roll = pivot('Robot optical roll motor', pitch, (0, 0, 0))
    disk('Robot rear roll bearing', 0, 0, 3.3, 6, .4, mats['rail'], roll)
    w, h, d = spec['head_size_mm']
    head = slab('Robot camera head', w, h, d, 3.2, (0, 0, -1.3), mats['arm'], roll, .65)
    slab('Robot head black face', w-2.5, h-2.5, .25, 2.4, (0, 0, -1.3-d/2-.05), mats['black'], roll, .08)
    disk('Robot main optical rim', 0, 0, -6.0, 6.25, .25, mats['rail'], roll)
    disk('Robot main optical glass', 0, 0, -6.18, 5.8, .12, glass, roll)
    disk('Robot main iris', 0, 0, -6.27, 3.6, .06, iris, roll)
    disk('Robot main pupil', 0, 0, -6.32, 2.4, .035, mats['black'], roll)
    optical = pivot('Robot optical axis', roll, (0, 0, -6.35))
    # A thin protective sliding lid has a true opening over the stowed camera face.
    shutter = pivot('Robot dock shutter', body, (0, 0, 0))
    cover = slab('Robot sliding dock cover', 30.5, 43, .4, 3.2,
                 (17.5, 57.5, -8.0), mats['bar'], shutter, .1)
    hole = slab('Robot shutter lens opening tool', 16.8, 16, 2, 2.5,
                (17.5, anchor[1]-stem-18.5, -8.0), None, shutter, .08)
    subtract(cover, hole)
    # Preserve holes in the Documents HONOR vector by an even-odd planar fill.
    from shapely.geometry import Polygon
    from shapely.ops import triangulate
    shape = Polygon()
    for contour in profile['robot_logo']['contours_mm']:
        shape = shape.symmetric_difference(Polygon(contour).buffer(0))
    vertices, faces = [], []
    cx, cy = profile['robot_logo']['center_mm']
    fill = shape.buffer(1e-7)
    for tri in triangulate(shape):
        if not fill.covers(tri):
            continue
        points = list(tri.exterior.coords)[:3]
        offset = len(vertices)
        vertices.extend(((-x+cx)*MM, (-y+cy)*MM, (back-.08)*MM) for x, y in points)
        faces.append((offset+2, offset+1, offset))
    mesh = bpy.data.meshes.new('HONOR vector inlay')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mats['logo'])
    obj = bpy.data.objects.new('HONOR finish-aware inlay', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = body

    # Stowed -> shutter clear -> outward flip -> upright -> expressive tracking -> neutral.
    poses = [(1, 'stowed', 0, 0, 0, 0, 0),
             (19, 'dock open', 0, 0, 0, 0, 1),
             (40, 'outward clearance', 65, 0, 0, 0, 1),
             (64, 'rising', 125, 0, 0, 0, 1),
             (85, 'deployed neutral', 180, 0, 0, 0, 1),
             (103, 'tracking', 180, 28, -12, 10, 1),
             (121, 'deployed', 180, 0, 0, 0, 1)]
    animated = [(fold, 0, 2), (pan, 1, 3), (pitch, 0, 4), (roll, 2, 5)]
    for frame, label, flip, yaw, tilt, spin, slide in poses:
        values = (frame, label, flip, yaw, tilt, spin, slide)
        for node, axis, index in animated:
            node.rotation_euler[axis] = math.radians(values[index])
            node.keyframe_insert(data_path='rotation_euler', frame=frame, group='Robot deploy')
        shutter.location.x = spec['shutter_travel_mm']*MM*slide
        shutter.keyframe_insert(data_path='location', frame=frame, group='Robot deploy')
    # NLA strips with one shared name produce one combined GLB clip.
    for node in [fold, pan, pitch, roll, shutter]:
        action = node.animation_data.action
        for layer in action.layers:
            for strip in layer.strips:
                for bag in strip.channelbags:
                    for curve in bag.fcurves:
                        for key in curve.keyframe_points:
                            key.interpolation = 'LINEAR'
        track = node.animation_data.nla_tracks.new()
        track.name = 'Robot deploy'
        strip = track.strips.new('Robot deploy', 1, action)
        strip.action_slot = node.animation_data.action_slot
        node.animation_data.action = None
    scene = bpy.context.scene
    scene.render.fps = 30
    scene.frame_start, scene.frame_end = 1, 121
    scene.frame_set(1)
    root['robot_animation'] = 'Robot deploy'
    root['design_status'] = profile['status']
    profile['robot_motion'] = {
        'animation': 'Robot deploy', 'fps': 30, 'frame_start': 1, 'frame_end': 121,
        'duration_seconds': 4, 'stowed_frame': 1, 'deployed_frame': 121,
        'glb_time_start_seconds': 1/30, 'glb_time_end_seconds': 121/30,
        'deployed_progress': 1, 'progress': '0 stowed; 1 deployed; reverse same clip to stow',
        'body_fixed': True, 'island_fixed': True,
        'joints': [{'node': n.name, 'parent': n.parent.name, 'axis': 'XYZ'[axis],
                    'local_position_mm': [v/MM for v in n.location]}
                   for n, axis, _ in animated],
        'shutter_node': shutter.name, 'optical_axis_node': optical.name,
        'optical_forward_local': [0, 0, -1],
        'keyframes': [{'frame': f, 'time_seconds': (f-1)/30, 'pose': name,
                       'flip_deg': a, 'pan_deg': b, 'pitch_deg': c, 'roll_deg': d,
                       'shutter_open': s} for f, name, a, b, c, d, s in poses],
        'limitations': 'Reconstructed promotional geometry; estimated hidden pivots and clearances, not validated production mechanical envelope.'
    }
