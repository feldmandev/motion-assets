"""Millimetre-based enclosure and camera components, using the reviewed Pixel optics."""
import math
import re
from pathlib import Path

import sys

import bpy
import bmesh
from mathutils import Vector

# shapely (polygon offsetting for traced outlines) is vendored for Blender's Python; appended so
# Blender's own numpy stays first.
_VENDOR = str(Path(__file__).resolve().parent/'vendor'/'py')
if _VENDOR not in sys.path:
    sys.path.append(_VENDOR)

MM = .001


def material(name, rgb, metal=0, rough=.3):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    shader = mat.node_tree.nodes['Principled BSDF']
    shader.inputs['Base Color'].default_value = tuple(
        value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4 for value in rgb) + (1,)
    shader.inputs['Metallic'].default_value = metal
    shader.inputs['Roughness'].default_value = rough
    return mat


def outline(width, height, radius, steps=32):
    radii = radius if isinstance(radius, (list, tuple)) else [radius]*4
    points = []
    for radius, (sx, sy, start) in zip(radii, [(1,-1,-90),(1,1,0),(-1,1,90),(-1,-1,180)]):
        radius = min(radius, width/2, height/2)
        x, y = sx*(width/2-radius), sy*(height/2-radius)
        for step in range(steps+1):
            angle = math.radians(start+step*90/steps)
            points.append((x+radius*math.cos(angle), y+radius*math.sin(angle)))
    return points


OUTLINE_POINTS = 320


def traced_ring(points, inset=0.0, count=OUTLINE_POINTS):
    """Inset a traced outline (mm) and resample it to `count` points by arc length.

    Every ring starts on the ray from the centroid along +X, so rings of different insets
    line up vertex-for-vertex and can be bridged into a rolled edge."""
    from shapely.geometry import LineString, Point, Polygon
    poly = Polygon(points).buffer(0)
    if inset:
        poly = poly.buffer(-inset, quad_segs=24, join_style='round')
        if poly.geom_type != 'Polygon':
            poly = max(poly.geoms, key=lambda g: g.area)
    ring = list(poly.exterior.coords)[:-1]
    if not Polygon(ring).exterior.is_ccw:
        ring.reverse()
    cx, cy = poly.centroid.x, poly.centroid.y
    hit = LineString([(cx, cy), (cx+1e4, cy)]).intersection(poly.exterior)
    hx, hy = (hit.x, hit.y) if hit.geom_type == 'Point' else (max(hit.geoms, key=lambda p: p.x).x, cy)
    line = LineString(ring+[ring[0]])
    start = line.project(Point(hx, hy))
    points = [line.interpolate((start+i*line.length/count) % line.length).coords[0] for i in range(count)]
    # Arc-length samples can miss the outline's extremes by a few hundredths of a millimetre;
    # rescale so the ring keeps the polygon's exact bounding box (published dimensions).
    x0, y0, x1, y1 = poly.bounds
    px = [p[0] for p in points]; py = [p[1] for p in points]
    sx = (x1-x0)/(max(px)-min(px)); sy = (y1-y0)/(max(py)-min(py))
    mx, my = (max(px)+min(px))/2, (max(py)+min(py))/2
    return [((x-mx)*sx+(x0+x1)/2, (y-my)*sy+(y0+y1)/2) for x, y in points]


def screen_mesh_with_cutouts(points, cutouts):
    """Triangulate a flat screen in metres, excluding profile apertures in millimetres."""
    from shapely.geometry import Point, Polygon
    from shapely.ops import triangulate
    surface = Polygon([(x/MM, y/MM) for x, y, _ in points])
    for cutout in cutouts:
        surface = surface.difference(Point(*cutout['center_mm']).buffer(cutout['radius_mm'], quad_segs=32))
    vertices, faces, indices = [], [], {}
    for triangle in triangulate(surface):
        if not surface.covers(triangle):
            continue
        face = []
        for x, y in list(triangle.exterior.coords)[:3]:
            key = (x, y)
            if key not in indices:
                indices[key] = len(vertices)
                vertices.append((x*MM, y*MM, 0))
            face.append(indices[key])
        faces.append(tuple(face))
    return vertices, faces


def slab(name, width, height, depth, radius, center, mat, parent, roll=.12, points=None):
    """Rounded-edge slab. With `points` (traced outline in the parent's mm coordinates,
    already relative to `center`), the outline replaces the width/height/radius rectangle."""
    radii = radius if isinstance(radius, (list, tuple)) else [radius]*4
    # `roll` is the edge fillet radius: one value for both faces, or (back, front). Large back
    # rolls give the rounded "pebble" sides of Pixel 6-8; flat-sided phones use small rolls.
    back_roll, front_roll = roll if isinstance(roll, (list, tuple)) else (roll, roll)
    limit = depth-.0002
    if back_roll+front_roll > limit:
        back_roll, front_roll = (back_roll*limit/(back_roll+front_roll), front_roll*limit/(back_roll+front_roll))
    if points is None:
        back_roll = min(back_roll, min(radii)-.0001)
        front_roll = min(front_roll, min(radii)-.0001)
    profiles = []
    for half, r in [(-1, back_roll), (1, front_roll)]:
        steps = 16 if r > 1 else 8
        for step in range(steps+1):
            angle = (step/steps)*math.pi/2
            if half < 0:
                angle -= math.pi/2
            profiles.append((r*(1-math.cos(angle)), half*(depth/2-r)+r*math.sin(angle)))
    vertices = []
    for inset, z in profiles:
        ring = (traced_ring(points, inset) if points is not None else
                outline(width-2*inset, height-2*inset, [max(.01,r-inset) for r in radii]))
        vertices.extend((x*MM, y*MM, z*MM) for x, y in ring)
    count = len(vertices)//len(profiles)
    faces = [tuple(reversed(range(count)))]
    for ring in range(len(profiles)-1):
        for index in range(count):
            faces.append((ring*count+index, ring*count+(index+1)%count,
                          (ring+1)*count+(index+1)%count, (ring+1)*count+index))
    faces.append(tuple(range((len(profiles)-1)*count, len(profiles)*count)))
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = tuple(value*MM for value in center)
    if mat:
        mesh.materials.append(mat)
    for face in mesh.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def disk(name, x, y, z, radius, depth, mat, parent):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius*MM,
                                      depth=depth*MM, location=(0, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = (x*MM, y*MM, z*MM)
    if mat:
        obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


# Use the same Apple outline as the SVG collection, extruded as a shallow rear inlay.
_APPLE_MARK_PATH = 'M0.968154,0.418733 C0.886531,0.468705 0.836313,0.557114 0.835191,0.652814 C0.835516,0.761121 0.900336,0.858820 1.000000,0.901218 C0.980776,0.963244 0.952325,1.022022 0.915603,1.075578 C0.863059,1.151218 0.808117,1.226850 0.724522,1.226850 C0.640927,1.226850 0.619426,1.178284 0.523088,1.178284 C0.429140,1.178284 0.395698,1.228446 0.319265,1.228446 C0.242831,1.228446 0.189493,1.158380 0.128184,1.072394 C0.047199,0.951938 0.002691,0.810673 0.000000,0.665549 C-0.000000,0.426696 0.155257,0.300108 0.308117,0.300108 C0.389331,0.300108 0.457007,0.353446 0.507963,0.353446 C0.556529,0.353446 0.632169,0.296916 0.724522,0.296916 C0.820949,0.294429 0.912289,0.340099 0.968154,0.418733 L0.968154,0.418733 Z M0.680735,0.195806 C0.721446,0.147916 0.744492,0.087506 0.746022,0.024669 C0.746091,0.016385 0.745290,0.008117 0.743632,0.000000 C0.673702,0.006831 0.609035,0.040161 0.562897,0.093154 C0.521794,0.139137 0.497880,0.197933 0.495220,0.259551 C0.495251,0.267045 0.496052,0.274516 0.497610,0.281846 C0.503123,0.282888 0.508720,0.283422 0.514331,0.283441 C0.579462,0.278259 0.639614,0.246580 0.680735,0.195806 L0.680735,0.195806 Z'

def _sample_svg_quadratics(path, steps=8):
    """Sample the Apple outline into contours for the rear inlay."""
    tokens = re.findall(r'[MmLlCcQqTtZz]|[-+]?(?:\d*\.\d+|\d+\.?\d*)', path)
    contours, contour = [], []
    i = 0; cmd = None; current = (0.0, 0.0); start = current; last_control = None
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]; i += 1
            if cmd in 'Zz':
                if contour:
                    contours.append(contour); contour = []
                current = start; last_control = None
                continue
        if cmd in 'Mm':
            x, y = map(float, tokens[i:i+2]); i += 2
            current = (current[0]+x, current[1]+y) if cmd == 'm' else (x, y)
            start = current; contour = [current]; last_control = None
            cmd = 'l' if cmd == 'm' else 'L'
        elif cmd in 'Cc':
            x1,y1,x2,y2,x,y = map(float, tokens[i:i+6]); i += 6
            if cmd == 'c':
                x1+=current[0]; y1+=current[1]; x2+=current[0]; y2+=current[1]
                x+=current[0]; y+=current[1]
            x0,y0 = current
            for step in range(1, steps+1):
                t=step/steps; u=1-t
                contour.append((u*u*u*x0+3*u*u*t*x1+3*u*t*t*x2+t*t*t*x,
                                u*u*u*y0+3*u*u*t*y1+3*u*t*t*y2+t*t*t*y))
            current=(x,y); last_control=(x2,y2)
        elif cmd in 'Qq':
            cx, cy, x, y = map(float, tokens[i:i+4]); i += 4
            control = ((current[0]+cx, current[1]+cy) if cmd == 'q' else (cx, cy))
            end = ((current[0]+x, current[1]+y) if cmd == 'q' else (x, y))
            x0, y0 = current
            for step in range(1, steps+1):
                t = step/steps; u = 1-t
                contour.append((u*u*x0+2*u*t*control[0]+t*t*end[0],
                                u*u*y0+2*u*t*control[1]+t*t*end[1]))
            current, last_control = end, control
        elif cmd in 'Tt':
            x, y = map(float, tokens[i:i+2]); i += 2
            control = (2*current[0]-last_control[0], 2*current[1]-last_control[1]) if last_control else current
            end = ((current[0]+x, current[1]+y) if cmd == 't' else (x, y))
            x0, y0 = current
            for step in range(1, steps+1):
                t = step/steps; u = 1-t
                contour.append((u*u*x0+2*u*t*control[0]+t*t*end[0],
                                u*u*y0+2*u*t*control[1]+t*t*end[1]))
            current, last_control = end, control
        elif cmd in 'Ll':
            x, y = map(float, tokens[i:i+2]); i += 2
            current = (current[0]+x, current[1]+y) if cmd == 'l' else (x, y)
            contour.append(current); last_control = None
        else:
            raise ValueError(f'Unsupported Apple mark SVG command: {cmd}')
    if contour:
        contours.append(contour)
    return contours


def apple_mark(spec, body, mat, parent):
    """Add the dimensioned glossy Apple rear inlay."""
    contours = _sample_svg_quadratics(_APPLE_MARK_PATH)
    xs = [x for contour in contours for x, _ in contour]
    ys = [y for contour in contours for _, y in contour]
    scale_y = spec.get('height_mm', 11.5)/(max(ys)-min(ys))
    scale_x = spec.get('width_mm', (max(xs)-min(xs))*scale_y)/(max(xs)-min(xs))
    mid_x, mid_y = (max(xs)+min(xs))/2, (max(ys)+min(ys))/2
    center_x, center_y = spec.get('center_mm', [0,0])
    depth = spec.get('surface_offset_mm', .08)
    for index, contour in enumerate(contours):
        # Rear-view artwork must be mirrored into the front-oriented model coordinates.
        points = [(-(x-mid_x)*scale_x+center_x, -(y-mid_y)*scale_y+center_y) for x, y in contour]
        count = len(points)
        vertices = [(x*MM, y*MM, (-body['depth']/2-depth)*MM) for x, y in points]
        vertices += [(x*MM, y*MM, (-body['depth']/2-.002)*MM) for x, y in points]
        faces = [tuple(reversed(range(count))), tuple(range(count, 2*count))]
        faces += [(i, (i+1)%count, count+(i+1)%count, count+i) for i in range(count)]
        faces = [tuple(reversed(face)) for face in faces]
        mesh = bpy.data.meshes.new(f'Apple mark {index}')
        mesh.from_pydata(vertices, [], faces); mesh.update(); mesh.materials.append(mat)
        obj = bpy.data.objects.new(f'Apple logo | {index}', mesh)
        bpy.context.scene.collection.objects.link(obj); obj.parent = parent
        for face in mesh.polygons:
            face.use_smooth = len(face.vertices) == 4


def cylinder_y(name, x, y, z, radius_x, length, mat, parent, radius_z=None):
    """Elliptical cylinder along +Y, used for the exposed long-edge Fold hinge spine."""
    radius_z = radius_x if radius_z is None else radius_z
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=MM, depth=length*MM,
                                      location=(0, 0, 0), rotation=(math.pi/2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = (x*MM, y*MM, z*MM)
    # Local Z becomes world Y after the 90° X rotation, so local Y is the world-depth radius.
    obj.scale = (radius_x, radius_z, 1)
    if mat:
        obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def subtract(obj, cutter):
    bpy.context.view_layer.update()
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new('Optical opening', 'BOOLEAN')
    modifier.operation = 'DIFFERENCE'
    modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def load_optics():
    asset = Path(__file__).parent.parent/'pixel-10-pro-model/Pixel-10-Pro-Obsidian.blend'
    with bpy.data.libraries.load(str(asset), link=False) as (source, target):
        target.objects = [name for name in source.objects if name.startswith(('Lens ', 'Telephoto |'))]
    # These source meshes are not linked into the output scene.
    return target.objects


def clone_optics(prototypes, kind, x, y, face_z, radius, bump, parent, index,
                 skip_source_pupil=True):
    prefix = 'Telephoto |' if kind == 'periscope' else 'Lens 2 |' if kind == 'main' else 'Lens 1 |'
    anchor = Vector((-6.1 if kind == 'periscope' else 7 if kind == 'main' else 22.4, 50.9, -7.89))*MM
    reference_radius = 5.5 if kind == 'main' else 3.8
    xy_scale = radius/reference_radius
    for prototype in prototypes:
        if not prototype.name.startswith(prefix):
            continue
        # These deep pupil meshes retain transforms from the source camera hierarchy.
        # Opt-in profiles omit them to avoid stray dots on the rear shell.
        if skip_source_pupil and 'deep pupil' in prototype.name.lower():
            continue
        obj = prototype.copy()
        obj.data = prototype.data.copy()
        obj.parent = parent
        obj.name = f'Camera {index} | {prototype.name}'
        obj.location = (0, 0, 0)
        obj.rotation_euler = (0, 0, 0)
        obj.scale = (1, 1, 1)
        for vertex, original in zip(obj.data.vertices, prototype.data.vertices):
            # Unlinked source barrels retain local transforms but have stale world matrices.
            source_matrix = prototype.matrix_basis
            point = source_matrix @ original.co - anchor
            vertex.co = (point.x*xy_scale+x*MM, point.y*xy_scale+y*MM,
                         point.z*(bump/3.6)+face_z*MM)
        bpy.context.scene.collection.objects.link(obj)


def camera_assembly(spec, body, materials, parent, prototypes):
    width, height, radius = spec['size_mm']
    x, y = spec['center_mm']
    bump = spec['bump_mm']
    back_z = -body['depth']/2
    face_z = back_z-bump
    housing = None
    if bump > .01:
        housing = slab('Camera housing', width, height, bump, radius,
                       (x, y, back_z-bump/2), materials['bar'], parent, spec.get('roll_mm', .45))
    optical_face_z = face_z-spec.get('optical_bump_mm', 0)
    for number, window in enumerate(spec['windows']):
        # A secondary lens outside the island seats directly on the rear enclosure.
        window_face_z = back_z if number in spec.get('body_windows', []) else face_z
        window_optical_z = window_face_z-spec.get('optical_bump_mm', 0)
        wx, wy, ww, wh, wr = window
        if spec.get('lens_ring_mm'):
            # Keep the visible outer edge of the metal rim 0.10 mm proud of the camera glass,
            # but extend its barrel inward until it actually seats on the camera plateau/body.
            # A fixed 0.8 mm rim leaves a large air gap on recent iPhones whose camera-glass
            # stand-off is 1.7-2.7 mm, making the lenses look like they float above the island.
            optical_bump = max(0, spec.get('optical_bump_mm', 0))
            ring_lip = .10
            ring_depth = max(.8, optical_bump+ring_lip)
            ring_z = window_optical_z-ring_lip+ring_depth/2
            ring = slab(f'Camera lens rim {number}', ww+2*spec['lens_ring_mm'],
                        wh+2*spec['lens_ring_mm'], ring_depth, wr+spec['lens_ring_mm'],
                               (wx, wy, ring_z), materials[spec.get('ring_material','rail')], parent, .10)
            # Cut the opening through the full collar depth.  The old 1.2 mm cutter became too
            # shallow as soon as the collar was long enough to bridge modern camera stand-offs.
            ring_tool = slab('Lens rim opening tool', ww, wh, ring_depth+.4, wr,
                             (wx, wy, ring_z), None, parent, .02)
            subtract(ring, ring_tool)
        # Coordinates are local front-view X/Y; rear-view reference X is mirrored in profiles.
        if housing:
            cutter = slab('Camera cavity tool', ww, wh, bump+.4, wr,
                          (wx, wy, back_z-bump/2-.15), None, parent, .03)
            subtract(housing, cutter)
        # Camera islands with a raised plateau need the dark well immediately behind its front
        # face. Putting that surface down at the phone's rear glass makes the metal lens ring and
        # clear lens stack read as separate floating pieces in oblique views.
        well_z = window_face_z+.04 if spec.get('integrated_plateau') else back_z-.02
        slab(f'Optical well {number}', ww-.1, wh-.1, .08, max(.05, wr-.05),
             (wx, wy, well_z), materials['black'], parent, .02)
        backing = slab(f'Black optical backing {number}', ww-.1, wh-.1, .035,
                       max(.05, wr-.05), (wx, wy, window_optical_z+.14), materials['black'], parent, .006)
        for index, lens in enumerate(spec['lenses']):
            if lens['window'] != number:
                continue
            lx, ly = lens['center_mm']
            lr = lens['radius_mm']
            if lens['kind'] == 'periscope':
                hole = slab('Periscope opening tool', lr*1.58, lr*2.1, .6, .5,
                            (lx, ly, window_optical_z+.14), None, parent, .02)
            else:
                hole = disk('Lens opening tool', lx, ly, window_optical_z+.14, lr*1.02,
                            .6, None, parent)
            subtract(backing, hole)
            if spec.get('local_pupil'):
                # Apple lenses use a shallow dark optical stack, rather than the borrowed
                # Pixel lens meshes with their large domed reflections.
                disk(f'Camera {index} | optical glass', lx, ly, window_optical_z+.035,
                     ww*.47, .04, materials['iphone_lens'], parent)
                disk(f'Camera {index} | iris', lx, ly, window_optical_z+.008,
                     lr*.69, .018, materials['iphone_iris'], parent)
                disk(f'Camera {index} | local pupil', lx, ly, window_optical_z-.006,
                     lr*.46, .012, materials['black'], parent)
            else:
                clone_optics(prototypes, lens['kind'], lx, ly, window_optical_z, lr,
                             max(spec.get('optical_bump_mm', 0), .8), parent, index,
                             skip_source_pupil=spec.get('skip_source_pupil', True))
        cover_depth = spec.get('cover_depth_mm', .10)
        if not spec.get('local_pupil'):
            slab(f'Continuous camera cover {number}', ww-.1, wh-.1, cover_depth, max(.05, wr-.05),
                 (wx, wy, window_optical_z+cover_depth/2-.025), materials['cover'], parent,
                 spec.get('cover_roll_mm', .025))
    for index, flash in enumerate(spec.get('flash', [])):
        fx, fy, fr = flash
        flash_z = back_z-.025 if spec.get('flash_surface')=='body' else face_z-.015
        flash_z -= spec.get('flash_offset_mm',0)
        disk(f'Flash {index}', fx, fy, flash_z, fr, .04, materials['flash'], parent)
    for index, sensor in enumerate(spec.get('sensors', [])):
        sensor_z = back_z-.025 if spec.get('sensor_surface') == 'body' else face_z-.02
        if isinstance(sensor, dict) and sensor.get('size_mm'):
            sx, sy = sensor['center_mm']; sw, sh = sensor['size_mm']
            slab(f'Rear {sensor.get("kind", "sensor")} {index}', sw, sh, .06,
                 sensor.get('radius_mm', min(sw,sh)/2), (sx, sy, sensor_z),
                 materials['black'], parent, .02)
        else:
            sx, sy, sr = sensor
            disk(f'Rear sensor {index}', sx, sy, sensor_z, sr, .06, materials['black'], parent)
    if spec.get('side_wrap_mm'):
        # Split the surfaces into strips before bending: an unsplit cap would
        # triangulate across the whole visor and flatten the curved ends.
        wrap = spec['side_wrap_mm']
        flat = width/2-wrap
        for obj in parent.children:
            if not obj.name.startswith(('Camera housing', 'Optical well',
                                        'Black optical backing', 'Continuous camera cover')):
                continue
            mesh = bmesh.new()
            mesh.from_mesh(obj.data)
            for side in (-1, 1):
                for step in range(1, 25):
                    px = (x+side*(flat+wrap*math.sin(step*math.pi/50)))*MM-obj.location.x
                    bmesh.ops.bisect_plane(mesh, geom=list(mesh.verts)+list(mesh.edges)+list(mesh.faces),
                                          plane_co=(px,0,0), plane_no=(1,0,0), dist=1e-9)
            for vertex in mesh.verts:
                distance = abs((vertex.co.x+obj.location.x)/MM-x)
                t = min(1, max(0, (distance-flat)/wrap))
                vertex.co.z += bump*(1-math.sqrt(max(0,1-t*t)))*MM
            mesh.to_mesh(obj.data)
            mesh.free()
            obj.data.update()


def rear_mark(profile, logo, body, mats, parent):
    """Place a rear inlay above the glass surface; shared by builds and branding refreshes."""
    depth = body['depth']
    if logo and logo.get('kind') == 'apple':
        apple_mark(logo, body, mats.get(logo.get('material', 'logo'), mats['black']), parent)
    elif logo and 'contours_mm' in logo:
        for index, contour in enumerate(logo['contours_mm']):
            cx, cy = logo['center_mm']
            vertices = [((-x+cx)*MM, (-y+cy)*MM, (-depth/2-logo.get('surface_offset_mm',.08))*MM) for x,y in contour]
            mesh = bpy.data.meshes.new(f'{profile.get("manufacturer", "Device")} mark {index}')
            mesh.from_pydata(vertices, [], [tuple(reversed(range(len(vertices))))])
            mesh.materials.append(mats.get('logo', mats['black']))
            obj = bpy.data.objects.new(f'{profile.get("manufacturer", "Device")} logo | {index}', mesh)
            bpy.context.scene.collection.objects.link(obj); obj.parent = parent


def hinge_mark(profile, mats):
    spec = profile.get('hinge_logo')
    if spec:
        parent = bpy.data.objects[spec['parent_node']]
        rear_mark(profile, spec, {'depth':spec['body_depth_mm']}, mats, parent)


def create_device(profile):
    root = bpy.data.objects.new(profile['name'], None)
    bpy.context.scene.collection.objects.link(root)
    finish = profile['materials']
    mats = {key: material(key, value['rgb'], value.get('metal', 0), value.get('rough', .3))
            for key, value in finish.items()}
    mats['black'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0
    if profile['id'].startswith('pixel-'):
        mats['front_glass'] = material('Pixel front cover glass', finish['black']['rgb'], rough=.16)
        glass_shader = mats['front_glass'].node_tree.nodes['Principled BSDF']
        glass_shader.inputs['IOR'].default_value = 1.46
        glass_shader.inputs['Coat Weight'].default_value = .2
    prototypes = load_optics()
    cover = bpy.data.materials.get('Camera pill | antireflective clear cover')
    # This material is loaded with the optics only when referenced; otherwise construct the same cover.
    if cover is None:
        cover = material('Continuous clear optical cover', (.999, .999, .999), rough=.008)
        shader = cover.node_tree.nodes['Principled BSDF']
        shader.inputs['Transmission Weight'].default_value = 1
        shader.inputs['IOR'].default_value = 1.48
        shader.inputs['Thin Film Thickness'].default_value = 100
        shader.inputs['Thin Film IOR'].default_value = 1.22
    mats['cover'] = cover
    if profile.get('manufacturer') == 'Apple':
        mats['iphone_lens'] = material('Apple optical glass', (.018,.028,.044), .25, .16)
        mats['iphone_iris'] = material('Apple optical iris', (.032,.054,.068), .4, .22)
    if profile.get('form_factor') == 'laptop':
        return create_laptop_device(profile, root, mats)
    articulation = profile.get('articulation')
    panel_objects = {}
    for panel in profile.get('panels', [{'name': 'Body', 'body_mm': profile['body_mm'], 'center_mm': [0, 0, 0]}]):
        body = panel['body_mm']
        parent = bpy.data.objects.new(panel['name'], None)
        bpy.context.scene.collection.objects.link(parent)
        if articulation:
            joint = next((j for j in articulation.get('joints', []) if j['moving_panel']==panel['name']), articulation)
            axis = joint['axis_mm']
            pivot_name = articulation['pivots'][panel['name']]
            pivot = bpy.data.objects.new(pivot_name, None)
            bpy.context.scene.collection.objects.link(pivot)
            pivot.parent = root
            pivot.location = tuple(value*MM for value in axis)
            pivot['role'] = 'fold-pivot'
            pivot['panel'] = panel['name']
            pivot['axis'] = joint['axis']
            parent.parent = pivot
            parent.location = tuple((value-axis[index])*MM for index, value in enumerate(panel['center_mm']))
        else:
            parent.parent = root
            parent.location = tuple(value*MM for value in panel['center_mm'])
            parent.rotation_euler = tuple(math.radians(value) for value in panel.get('rotation_deg', [0,0,0]))
        panel_objects[panel['name']] = parent
        width, height, depth, radius = (body[key] for key in ['width', 'height', 'depth', 'corner_radius'])
        radii = body.get('corner_radii_mm', [radius]*4)
        # Traced outline (Google emulator artwork) relative to this panel's centre, when available.
        pts = panel.get('outline_mm', profile.get('body_outline_mm') if 'panels' not in profile else None)
        ring = (lambda inset: traced_ring(pts, inset)) if pts else None
        rolls = body.get('edge_roll_mm', [body.get('edge_roll', .55)]*2)
        back_roll, front_roll = rolls
        slab('Aluminum enclosure', width, height, depth-.05, radii, (0, 0, 0),
             mats['rail'], parent, rolls, points=pts)
        back_face = -(depth-.05)/2

        def rear_shell(name, offset, mat, extra=0.0):
            """Glass that follows the rounded back edge: same outline (slightly proud) and fillet."""
            shell_pts = traced_ring(pts, -offset) if pts else None
            d = 2*back_roll+extra
            return slab(name, width+2*offset, height+2*offset, d, [r+offset for r in radii],
                        (0, 0, back_face-offset+d/2), mat, parent, (back_roll, back_roll), points=shell_pts)
        cover_half = panel['name']=='Cover half'
        cover_screen = next((s for s in profile.get('screens',[]) if s.get('panel')==panel['name']
                             and s.get('glass_border_mm')),None)
        inset = .7 if cover_half else body.get('rear_inset', .8)
        if panel.get('rear_glass_region_mm'):
            slab('Rear glass',width-2*inset,height-2*inset,.25,[max(.2,r-inset) for r in radii],
                 (0,0,-depth/2+.1),mats['back'],parent,.08)
            cx,cy,gw,gh = panel['rear_glass_region_mm']
            slab('Exterior black cover glass',gw,gh,.26,
                 panel['rear_glass_region_radii_mm'],(cx,cy,-depth/2+.095),mats['black'],parent,.08)
        elif cover_screen and cover_screen.get('rotation_deg',[0,0,0])[1]==180:
            sw,sh = cover_screen['fit_box_mm']; border = cover_screen['glass_border_mm']
            sx,sy = cover_screen['center_mm'][:2]
            # Explicit glass contours are offsets from the screen centre in panel axes;
            # rear-facing cover profiles already mirror X independently of the OLED.
            glass_pts = cover_screen.get('glass_outline_mm')
            if glass_pts is None:
                glass_pts = traced_ring(cover_screen['outline_mm'], -border) if cover_screen.get('outline_mm') else None
            slab('Rear cover glass',sw+2*border,sh+2*border,.25,cover_screen['corner_radius_mm']+border,
                 (sx,sy,-depth/2+.1),mats.get('front_glass',mats['black']),parent,.08,points=glass_pts)
        elif body.get('rear_style') == 'unibody' and not cover_half:
            # Pixel 4a/5/5a use a coated one-piece rear shell instead of the inset
            # glass panel used by the glass-backed Pixels. Keep the shell continuous
            # into the rolled side profile so the rear does not read as a glass insert.
            rear_shell('Rear unibody shell', .02, mats['back'])
        elif back_roll > 1 and not cover_half and body.get('rear_style') != 'inset_glass':
            rear_shell('Rear glass', .03, mats['back'])
        else:
            slab('Rear glass', width-2*inset, height-2*inset, .25, [max(.2,r-inset) for r in radii],
                 (0, 0, -depth/2+.1), mats['black'] if cover_half else mats['back'], parent, .08,
                 points=ring(inset) if ring else None)
        if 'upper' in mats:
            if back_roll > 1:
                upper = rear_shell('Two-tone upper rear glass', .06, mats['upper'])
            else:
                upper = slab('Two-tone upper rear glass', width-2*inset, height-2*inset, .05,
                             radius-inset, (0, 0, -depth/2-.025), mats['upper'], parent, .012,
                             points=ring(inset) if ring else None)
            cam = profile['camera']
            bottom = cam['center_mm'][1]+cam['size_mm'][1]/2
            cutter = slab('Upper panel trim tool', width+4, height+bottom*2, depth+4, .1,
                          (0, bottom-(height+bottom*2)/2, 0), None, parent, .02)
            subtract(upper, cutter)
        curve = body.get('front_curve', 0)
        glass_depth = max(.25, curve*2+.02)
        if cover_screen and cover_screen.get('rotation_deg',[0,0,0])[1]==0:
            sw,sh = cover_screen['fit_box_mm']; border = cover_screen['glass_border_mm']
            sx,sy = cover_screen['center_mm'][:2]
            glass_pts = cover_screen.get('glass_outline_mm')
            if glass_pts is None:
                glass_pts = traced_ring(cover_screen['outline_mm'], -border) if cover_screen.get('outline_mm') else None
            slab('Front black glass',sw+2*border,sh+2*border,glass_depth,cover_screen['corner_radius_mm']+border,
                 (sx,sy,depth/2-glass_depth/2),mats.get('front_glass',mats['black']),parent,.08,points=glass_pts)
        else:
            if body.get('front_glass_inset_mm'):
                from shapely.geometry import Polygon
                side_inset, top_inset = body['front_glass_inset_mm']
                contour = pts or outline(width, height, radii)

                def front_ring(rx, ry, amount):
                    # Elliptical erosion retains the independent body trace while
                    # allowing narrow side metal and a wider top/bottom strip.
                    if not amount:
                        return traced_ring(contour)
                    shape = Polygon([(x/rx, y/ry) for x, y in contour]).buffer(
                        -amount, quad_segs=24, join_style='round')
                    return traced_ring([(x*rx, y*ry) for x, y in shape.exterior.coords])

                # Change only the enclosure's front rings. The side retains its
                # deep fillet; the top has a shallow fillet and a metal landing.
                enclosure = next(obj for obj in parent.children if obj.name.startswith('Aluminum enclosure'))
                top_roll = body['front_roll_top_mm']
                steps = 16 if front_roll > 1 else 8
                count = len(front_ring(front_roll, top_roll, 0))
                start = len(enclosure.data.vertices)-(steps+1)*count
                for step in range(steps+1):
                    angle = step/steps*math.pi/2
                    front = front_ring(front_roll, top_roll, 1-math.cos(angle))
                    for index, (x, y) in enumerate(front):
                        ax, ay = front[index-1]; bx, by = front[(index+1)%count]
                        # Support radius of the elliptical fillet along the normal.
                        radius = math.hypot(front_roll*(by-ay), top_roll*(bx-ax))/math.hypot(bx-ax, by-ay)
                        z = (depth-.05)/2-radius*(1-math.sin(angle))
                        enclosure.data.vertices[start+step*count+index].co = (x*MM, y*MM, z*MM)
                enclosure.data.update()
                slab('Front black glass', width-2*side_inset, height-2*top_inset, glass_depth, radii,
                     (0, 0, depth/2-glass_depth/2), mats.get('front_glass', mats['black']), parent, .02,
                     points=front_ring(side_inset, top_inset, 1))
            else:
                # The front glass stops where the front edge starts to roll over.
                rail = max(body.get('front_rail_mm', .7), front_roll*.95)
                glass_points = ring(rail) if ring else None
                if body.get('front_glass_insets_mm'):
                    from shapely.geometry import Polygon
                    left, top, right, bottom = body['front_glass_insets_mm']
                    rx, ry = (left+right)/2, (top+bottom)/2
                    contour = pts or outline(width, height, radii)
                    # Offset the independent chassis contour by the measured side
                    # and end widths, retaining the asymmetric glass placement.
                    shape = Polygon([(x/rx, y/ry) for x,y in contour]).buffer(-1, quad_segs=24)
                    glass_points = [(x*rx+(left-right)/2, y*ry+(bottom-top)/2)
                                    for x,y in shape.exterior.coords]
                slab('Front black glass', width-2*rail, height-2*rail, glass_depth, [max(.2,r-rail) for r in radii],
                     (0, 0, depth/2-glass_depth/2), mats.get('front_glass', mats['black']), parent, max(.08, curve),
                     points=glass_points)
        if 'camera' in panel or 'camera' in profile and len(profile.get('panels', [])) == 0:
            camera_assembly(panel.get('camera', profile.get('camera')), body, mats, parent, prototypes)
        for detail in panel.get('rear_details', profile.get('rear_details', [])):
            dx, dy = detail['center_mm']
            detail_depth = detail.get('depth_mm', .04)
            detail_mat = mats.get(detail.get('material', 'fingerprint'), mats['back'])
            if 'size_mm' in detail:
                dw, dh, dr = detail['size_mm']
                slab(detail.get('name', 'Rear detail'), dw, dh, detail_depth, dr,
                     (dx, dy, -depth/2-detail_depth/2), detail_mat, parent, .005)
            else:
                disk(detail.get('name', 'Rear detail'), dx, dy, -depth/2-.015,
                     detail['radius_mm'], detail_depth, detail_mat, parent)
        logo = panel.get('rear_logo')
        if logo is None and 'panels' not in profile:
            logo = profile.get('rear_logo')
        rear_mark(profile, logo, body, mats, parent)
        for screen in profile.get('screens', [profile['screen']] if 'screen' in profile else []):
            if screen.get('panel', 'Body') != panel['name']:
                continue
            placeholder = slab(screen['object'], 1, 1, .01, .1, (0, 0, 0), mats['black'], parent, .002)
            # Screen center is local to its panel; export metadata resolves the global center.
            screen['parent_center_mm'] = panel['center_mm']
        if panel.get('buttons', True):
            button_specs = panel.get('button_specs', profile.get('buttons'))
            if button_specs:
                for spec in button_specs:
                    side = -1 if spec.get('side') == 'left' else 1
                    role = spec.get('material', 'rail')
                    thickness = spec.get('thickness_mm', .5)
                    button = slab(spec['name'], spec.get('width_mm', 2.5), spec['length_mm'],
                                  thickness, min(spec.get('radius_mm', 1.0), spec['length_mm']/2),
                                  (side*(width/2+thickness*.3-spec.get('inset_mm', 0)), spec['center_y_mm'], 0),
                                  mats.get(role, mats['rail']), parent, min(.12, thickness*.24))
                    button.rotation_euler[1] = math.pi/2
            else:
                for name, y, length in [('Power', height*.18, 10), ('Volume', height*.035, 20)]:
                    button = slab(name, 2.5, length, .5, 1.2, (width/2+.15, y, 0), mats['rail'], parent, .12)
                    button.rotation_euler[1] = math.pi/2
        if articulation and not articulation.get('joints'):
            inner_x = width/2-.35 if panel['center_mm'][0] < articulation['axis_mm'][0] else -width/2+.35
            slab(f'Hinge leaf | {panel["name"]}', .7, height-8, .42, .28,
                 (inner_x, 0, -depth/2+.23), mats['rail'], parent, .12)
    for hinge in profile.get('static_hinges', []):
        parent = bpy.data.objects.new('Closed hinge spine', None)
        bpy.context.scene.collection.objects.link(parent)
        parent.parent = root
        parent.location = tuple(v*MM for v in hinge['center_mm'])
        parent.rotation_euler[0 if hinge['axis']=='X' else 1] = math.radians(hinge['rotation_degrees'])
        barrel = cylinder_y('Closed hinge barrel',0,0,0,hinge['span_mm']/2,
                           hinge['length_mm'],mats['rail'],parent,hinge['depth_mm']/2)
        if hinge['axis']=='X':
            from mathutils import Matrix
            barrel.data.transform(Matrix.Rotation(math.pi/2,4,'Z') @ barrel.matrix_basis)
            barrel.matrix_basis = Matrix.Identity(4)
    for joint in articulation.get('joints', []) if articulation else []:
        spine_pivot = bpy.data.objects.new(joint['spine_pivot'], None)
        bpy.context.scene.collection.objects.link(spine_pivot)
        spine_pivot.parent = root
        spine_pivot['role'] = 'hinge-spine-pivot'
        barrel = cylinder_y(joint['spine_pivot']+' barrel', 0, 0, 0, joint['spine_width_mm']/2,
                           joint['length_mm'], mats['rail'], spine_pivot, joint['spine_depth_mm']/2)
        if joint['axis']=='X':
            # Rotate the mesh rather than the animation pivot's scale axes.
            transform = barrel.matrix_basis.copy()
            from mathutils import Matrix
            barrel.data.transform(Matrix.Rotation(math.pi/2,4,'Z') @ transform)
            barrel.matrix_basis = Matrix.Identity(4)
    if 'hinge' in profile and not (articulation and articulation.get('joints')):
        hinge = profile['hinge']
        if articulation:
            spine_pivot = bpy.data.objects.new('Fold pivot | Hinge spine', None)
            bpy.context.scene.collection.objects.link(spine_pivot)
            spine_pivot.parent = root
            spine_pivot.location = (hinge['spine_center_x_mm']*MM, 0, hinge['spine_center_z_mm']*MM)
            spine_pivot['role'] = 'hinge-spine-pivot'
            # Wide and shallow when open, the barrel turns half the panel angle to become
            # the full-depth outside bridge when closed. It stays behind the inner OLED.
            cylinder_y('Hinge spine | articulated', 0, 0, 0, hinge['spine_width_mm']/2,
                       hinge['size_mm'][1], mats['rail'], spine_pivot, hinge['spine_depth_mm']/2)
        else:
            slab('Hinge spine | estimated', *hinge['size_mm'], hinge['radius_mm'],
                 hinge['center_mm'], mats['rail'], root, .2)
    hinge_mark(profile, mats)
    if profile.get('form_factor') == 'laptop':
        return create_laptop_device(profile, root, mats)
    for screen in profile.get('screens', []):
        if screen.get('panel') == 'Inner display':
            body = profile['body_mm']
            if articulation:
                screen['object_parts'] = []
                screen['part_parent_centers_mm'] = {}
                screen['part_regions_mm'] = {} if screen.get('panel_regions_mm') else None
                for panel_name in screen.get('panel_regions_mm', ('Cover half', 'Camera half')):
                    placeholder = slab(f'{screen["object"]} | {panel_name}', 1, 1, .01, .1,
                                       (0, 0, 0), mats['black'], panel_objects[panel_name], .002)
                    screen['object_parts'].append(placeholder.name)
                    source = next(panel for panel in profile['panels'] if panel['name'] == panel_name)
                    screen['part_parent_centers_mm'][placeholder.name] = source['center_mm']
                    if screen.get('panel_regions_mm'):
                        screen['part_regions_mm'][placeholder.name] = screen['panel_regions_mm'][panel_name]
                crease_width = max(.45, articulation.get('open_gap_mm', .6))
                if not articulation.get('joints'):
                    slab('Inner display crease', crease_width, body['height']-1.0, .035, .18,
                     (articulation['axis_mm'][0], 0, profile['panels'][0]['body_mm']['depth']/2+.012),
                     mats['black'], root, .008)
            else:
                slab('Inner display perimeter frame', body['width']-.4, body['height']-.4,
                     .08, body['corner_radius']-.2, (0,0,body['depth']/2-.015), mats['black'], root, .02,
                     points=traced_ring(profile['body_outline_mm'], .35) if profile.get('body_outline_mm') else None)
                slab(screen['object'], 1, 1, .01, .1, (0, 0, 0), mats['black'], root, .002)
    for x, y, z, radius in profile.get('bezel_cameras', []):
        disk('Inner bezel selfie camera', x, y, z, radius, .03, mats['black'], root)
    if profile.get('bezel_windows'):
        sensor_mat = material('Pixel forehead sensor cover', (.028,.032,.038), rough=.3)
        for index, window in enumerate(profile['bezel_windows']):
            w, h, radius = window['size_mm']
            slab(f'Front sensor window {index}', w, h, .03, radius,
                 window['center_mm'], sensor_mat, root, .005)
    return root


def _laptop_lip_outline(width, height, radius, lip_w, lip_h, steps=24):
    """Counter-clockwise lid outline with a top-center camera reverse notch lip."""
    points = []
    # Bottom-right corner
    for step in range(steps + 1):
        a = math.radians(-90 + step * 90 / steps)
        points.append((width / 2 - radius + radius * math.cos(a), -height / 2 + radius + radius * math.sin(a)))
    # Top-right corner
    for step in range(steps + 1):
        a = math.radians(0 + step * 90 / steps)
        points.append((width / 2 - radius + radius * math.cos(a), height / 2 - radius + radius * math.sin(a)))
    # Top edge from right to left, with smooth camera lip protrusion around x in [-lip_w/2, +lip_w/2]
    r_lip = min(lip_h * 0.9, 2.2)
    for i in range(41):
        t = i / 40.0
        x = (lip_w / 2 + r_lip * 2) * (1 - 2 * t)
        ax = abs(x)
        if ax >= lip_w / 2 + r_lip:
            y = height / 2
        elif ax <= lip_w / 2 - r_lip:
            y = height / 2 + lip_h
        else:
            u = (lip_w / 2 + r_lip - ax) / (2 * r_lip)
            y = height / 2 + lip_h * (u * u * (3 - 2 * u))
        points.append((x, y))
    # Top-left corner
    for step in range(steps + 1):
        a = math.radians(90 + step * 90 / steps)
        points.append((-width / 2 + radius + radius * math.cos(a), height / 2 - radius + radius * math.sin(a)))
    # Bottom-left corner
    for step in range(steps + 1):
        a = math.radians(180 + step * 90 / steps)
        points.append((-width / 2 + radius + radius * math.cos(a), -height / 2 + radius + radius * math.sin(a)))
    return points


def _build_oem_logo(logo_spec, lid_depth, mat, parent):
    """Build a 3D rear lid logo from brand_logos.json using Blender's 2D Curve fill."""
    import json
    logos_path = Path(__file__).resolve().parents[4] / 'documents' / 'brand_logos.json'
    if not logos_path.exists():
        return
    logos = json.loads(logos_path.read_text(encoding='utf-8'))
    kind = logo_spec['kind']
    if kind not in logos:
        return
    entry = logos[kind]
    d_str = entry['d']
    aspect = entry['aspect']
    logo_w = logo_spec['width_mm']
    logo_h = logo_w / aspect
    cx, cy = logo_spec['center_mm']

    curve_data = bpy.data.curves.new(f'Lid logo curve | {kind}', type='CURVE')
    curve_data.dimensions = '2D'
    curve_data.fill_mode = 'BOTH'
    curve_data.extrude = 0.03 * MM
    curve_data.resolution_u = 8

    tokens = re.findall(r'[MLCZ]|-?\d+(?:\.\d+)?', d_str)
    i = 0
    spline = None
    pts = []

    def tx(nx, ny):
        # Mirror X and flip Y from SVG top-down [0,1]x[0,1/aspect] to rear-facing model mm
        return (-(nx - 0.5) * logo_w + cx) * MM, (-(ny - 0.5 / aspect) * logo_w + cy) * MM

    def flush_spline(points_list):
        if len(points_list) < 3:
            return
        sp = curve_data.splines.new('POLY')
        sp.use_cyclic_u = True
        sp.points.add(len(points_list) - 1)
        for idx, (px, py) in enumerate(points_list):
            sp.points[idx].co = (px, py, 0.0, 1.0)

    cur = (0.0, 0.0)
    while i < len(tokens):
        cmd = tokens[i]
        i += 1
        if cmd == 'M':
            if pts:
                flush_spline(pts)
                pts = []
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            cur = (nx, ny)
            pts.append(tx(nx, ny))
        elif cmd == 'L':
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            i += 2
            cur = (nx, ny)
            pts.append(tx(nx, ny))
        elif cmd == 'C':
            x1, y1 = float(tokens[i]), float(tokens[i + 1])
            x2, y2 = float(tokens[i + 2]), float(tokens[i + 3])
            x3, y3 = float(tokens[i + 4]), float(tokens[i + 5])
            i += 6
            x0, y0 = cur
            for step in range(1, 9):
                t = step / 8.0
                u = 1.0 - t
                bx = u**3 * x0 + 3 * u**2 * t * x1 + 3 * u * t**2 * x2 + t**3 * x3
                by = u**3 * y0 + 3 * u**2 * t * y1 + 3 * u * t**2 * y2 + t**3 * y3
                pts.append(tx(bx, by))
            cur = (x3, y3)
        elif cmd == 'Z':
            flush_spline(pts)
            pts = []
    if pts:
        flush_spline(pts)

    curve_obj = bpy.data.objects.new(f'Lid logo | {kind}', curve_data)
    bpy.context.scene.collection.objects.link(curve_obj)
    bpy.ops.object.select_all(action='DESELECT')
    curve_obj.select_set(True)
    bpy.context.view_layer.objects.active = curve_obj
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.view_layer.objects.active
    mesh_obj.parent = parent
    mesh_obj.location = (0, 0, (-lid_depth / 2 - 0.025) * MM)
    if mat:
        mesh_obj.data.materials.append(mat)


def _slab_xz(name, width_x, length_z, thickness_y, radius, center_xyz, mat, parent, roll=0.1):
    """Create a horizontal slab in the XZ plane with its top face pointing along +Y."""
    cx, cy, cz = center_xyz
    obj = slab(name, width_x, length_z, thickness_y, radius, (0, 0, 0), mat, parent, roll)
    obj.rotation_euler = (-math.pi / 2, 0, 0)
    obj.location = (cx * MM, cy * MM, cz * MM)
    return obj


def _add_rounded_keycap(bm, x0, x1, z0, z1, y_bot, y_top, uv_layer, kb_w, kb_z0, kb_d, r=1.05, top_inset=0.24):
    """Add a rounded-corner chiclet keycap prism with 3D chamfered sides and UV texture mapping."""
    kw = x1 - x0
    kd = z1 - z0
    rad = min(r, kw * 0.28, kd * 0.28)
    steps = 3
    bot_pts = []
    top_pts = []
    corners = [
        (x1 - rad, z0 + rad, -90),
        (x1 - rad, z1 - rad, 0),
        (x0 + rad, z1 - rad, 90),
        (x0 + rad, z0 + rad, 180),
    ]
    for cx, cz, start_deg in corners:
        for s in range(steps + 1):
            a = math.radians(start_deg + s * 90.0 / steps)
            ca, sa = math.cos(a), math.sin(a)
            bx = cx + rad * ca
            bz = cz + rad * sa
            trad = max(0.2, rad - top_inset)
            tx = cx + trad * ca
            tz = cz + trad * sa
            bot_pts.append(bm.verts.new((bx * MM, y_bot, bz * MM)))
            top_pts.append(bm.verts.new((tx * MM, y_top, tz * MM)))
    n = len(top_pts)

    # Top face: Material Index 0 (texture)
    face_top = bm.faces.new(tuple(reversed(top_pts)))
    face_top.material_index = 0
    if uv_layer:
        for loop in face_top.loops:
            vx = loop.vert.co.x / MM
            vz = loop.vert.co.z / MM
            u = (vx - (-kb_w / 2.0)) / kb_w
            v = (kb_z0 + kb_d - vz) / kb_d
            loop[uv_layer].uv = (u, v)

    # 3D Chamfered Side walls: Material Index 1 (solid darker shading)
    for i in range(n):
        j = (i + 1) % n
        face_side = bm.faces.new((bot_pts[i], top_pts[i], top_pts[j], bot_pts[j]))
        face_side.material_index = 1
        if uv_layer:
            for loop in face_side.loops:
                loop[uv_layer].uv = (0.001, 0.001)


def _build_keycap_matrix(width, height, base_depth, deck_style, mat, parent, profile_id=''):
    """Create a single combined 3D mesh for all 6 rows of rounded chiclet laptop keycaps with textures."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')

    if deck_style == 'dell_chiclet':
        margin_x = 13.5
    elif deck_style == 'lenovo_15':
        margin_x = 34.0
    else:
        margin_x = 19.5

    kb_w = width - 2 * margin_x
    kb_z0 = -height / 2 + 16.5
    kb_z1 = 7.5
    kb_d = kb_z1 - kb_z0
    gap = 1.05 if deck_style == 'dell_chiclet' else 1.25

    # Substantial 1.13 mm physical keycap thickness rising out of the well floor
    y_bot = (base_depth / 2 - 1.35) * MM
    y_top = (base_depth / 2 - 0.22) * MM

    row_weights = [0.56, 1.0, 1.0, 1.0, 1.0, 1.06]
    total_w = sum(row_weights)
    z_cursor = kb_z0

    row_layouts = [
        [1.05] + [1.0] * 12 + [1.15],
        [0.85] + [1.0] * 12 + [1.55],
        [1.35] + [1.0] * 12 + [1.05],
        [1.65] + [1.0] * 11 + [1.85],
        [2.10] + [1.0] * 10 + [2.30],
        [1.15, 1.05, 1.05, 1.05, 4.85, 1.05, 1.05, 1.05, 1.05, 1.05],
    ]

    for r_idx, (rw, cols) in enumerate(zip(row_weights, row_layouts)):
        rh = (kb_d - gap * 5) * (rw / total_w)
        z0 = z_cursor
        z1 = z0 + rh
        z_cursor = z1 + gap

        col_sum = sum(cols)
        n_cols = len(cols)
        avail_w = kb_w - gap * (n_cols - 1)
        x_cursor = -kb_w / 2
        for c_idx, cw_weight in enumerate(cols):
            kw = avail_w * (cw_weight / col_sum)
            x0 = x_cursor
            x1 = x0 + kw
            x_cursor = x1 + gap

            # Bottom row second-to-last column is split Up / Down half-height arrow keys
            if r_idx == 5 and c_idx == n_cols - 2:
                sub_gap = 0.65
                half_h = (rh - sub_gap) / 2.0
                _add_rounded_keycap(bm, x0, x1, z0, z0 + half_h, y_bot, y_top, uv_layer, kb_w, kb_z0, kb_d, r=0.85, top_inset=0.20)
                _add_rounded_keycap(bm, x0, x1, z0 + half_h + sub_gap, z1, y_bot, y_top, uv_layer, kb_w, kb_z0, kb_d, r=0.85, top_inset=0.20)
            else:
                rad = 0.95 if r_idx == 0 else 1.25
                _add_rounded_keycap(bm, x0, x1, z0, z1, y_bot, y_top, uv_layer, kb_w, kb_z0, kb_d, r=rad, top_inset=0.24)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new('Keyboard keycaps')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    # Material 0: Keycap top face with keyboard layout texture & backlight emission
    if mat:
        tex_path = Path(__file__).resolve().parent / 'textures' / f'kb_{profile_id}.png'
        if tex_path.exists():
            img = bpy.data.images.load(str(tex_path))
            img.colorspace_settings.name = 'sRGB'
            bsdf = mat.node_tree.nodes.get('Principled BSDF')
            if bsdf:
                tex_node = mat.node_tree.nodes.new('ShaderNodeTexImage')
                tex_node.image = img
                mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
                mat.node_tree.links.new(tex_node.outputs['Color'], bsdf.inputs['Emission Color'])
                bsdf.inputs['Emission Strength'].default_value = 0.35
        mesh.materials.append(mat)

    # Material 1: 3D Chamfered side walls with distinct dark matte shading for high-relief depth
    side_rgb = [0.035, 0.038, 0.042]
    mat_side = material('Keyboard keycap sides', side_rgb, metal=0.04, rough=0.55)
    mesh.materials.append(mat_side)

    obj = bpy.data.objects.new('Keyboard keycaps', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def _build_lenovo_communications_bar(width, height, lid_depth, mats, parent):
    """Build the signature Lenovo reverse notch / easy-open communications bar handle."""
    bar_w = 96.0
    bar_h = 4.8
    # Center the bar so its bottom 1.8 mm is embedded inside the lid top edge,
    # and its top 3.0 mm cleanly protrudes with rounded corners.
    cy = height / 2.0 + 0.6
    # 1. Main reverse notch handle body (clean smooth protrusion above top edge)
    slab('Communications bar handle', bar_w, bar_h, lid_depth - 0.20, 2.2,
         (0.0, cy, -0.10), mats['rail'], parent, (0.35, 0.25))
    # 2. Rear anodized accent strip on back of communications bar
    slab('Communications bar rear accent', bar_w - 6.0, bar_h - 1.2, 0.22, 1.2,
         (0.0, cy, -lid_depth / 2.0 + 0.02), mats['back'], parent, 0.05)
    # 3. Front glass bezel extending display glass into the reverse notch
    slab('Communications bar front bezel', bar_w - 4.0, bar_h - 0.8, 0.32, 1.2,
         (0.0, cy, lid_depth / 2.0 - 0.32), mats['black'], parent, 0.05)
    # 4. Subtle physical privacy shutter slider
    shutter_mat = mats.get('logo', mats['rail'])
    slab('Privacy shutter slider', 7.5, 1.8, 0.25, 0.6,
         (0.0, cy + 0.7, lid_depth / 2.0 - 0.08), shutter_mat, parent, 0.04)
    slab('Privacy shutter dot', 1.8, 1.2, 0.28, 0.4,
         (0.0, cy + 0.7, lid_depth / 2.0 - 0.05), mats['black'], parent, 0.02)
    # 5. Centered 1080p webcam lens
    disk('Webcam aperture', 0.0, cy - 0.2, lid_depth / 2.0 - 0.08, 1.15, 0.06, mats['black'], parent)
    disk('Webcam lens element', 0.0, cy - 0.2, lid_depth / 2.0 - 0.05, 0.50, 0.06, mats.get('rail', mats['black']), parent)
    # 6. Dual mic pinholes
    for sx in (-15.0, 15.0):
        disk(f'Mic pinhole | {int(sx):+d}', sx, cy + 0.1, lid_depth / 2.0 - 0.08, 0.40, 0.06, mats['black'], parent)



def _build_lenovo_bottom_grips(width, height, base_depth, mat, parent):
    """Add the Pixelbook Go-inspired ribbed wavy grip pads on the bottom chassis."""
    pad_w = width - 75.0
    pad_h = 24.0
    for sz in (-height / 3.2, height / 3.4):
        _slab_xz(f'Textured grip pad | {sz:+0.1f}', pad_w, pad_h, 0.35, 3.2,
                 (0.0, -base_depth / 2 - 0.08, sz), mat, parent, 0.08)


def _build_sculpted_trackpad(tp_w, tp_h, base_depth, tp_cz, mats, profile, parent):
    """Build a precision 3D glass trackpad slab with sloped chamfered sides,
    polished CNC diamond-cut metal rim, and deep recessed perimeter well."""
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new('UVMap')
    r = 3.6
    # 0.67 mm of solid physical glass thickness recessed 0.18 mm below palmrest
    y_bot = (base_depth / 2 - 1.05) * MM
    y_top = (base_depth / 2 - 0.38) * MM
    top_inset = 0.35
    steps = 4
    corners = [
        (tp_w / 2 - r, -tp_h / 2 + r, -90),
        (tp_w / 2 - r, tp_h / 2 - r, 0),
        (-tp_w / 2 + r, tp_h / 2 - r, 90),
        (-tp_w / 2 + r, -tp_h / 2 + r, 180),
    ]
    bot_pts = []
    top_pts = []
    for cx, cz, start_deg in corners:
        for s in range(steps + 1):
            a = math.radians(start_deg + s * 90.0 / steps)
            ca, sa = math.cos(a), math.sin(a)
            bx = cx + r * ca
            bz = cz + r * sa
            tx = cx + (r - top_inset) * ca
            tz = cz + (r - top_inset) * sa
            bot_pts.append(bm.verts.new((bx * MM, y_bot, (tp_cz + bz) * MM)))
            top_pts.append(bm.verts.new((tx * MM, y_top, (tp_cz + tz) * MM)))

    # Material 0: Top satin glass face with subtle specular reflection
    face_top = bm.faces.new(tuple(reversed(top_pts)))
    face_top.material_index = 0
    for loop in face_top.loops:
        loop[uv_layer].uv = (0.5, 0.5)

    # Material 1: Sloped chamfered glass sides catching rim specular highlights
    n = len(top_pts)
    for i in range(n):
        j = (i + 1) % n
        face_side = bm.faces.new((bot_pts[i], top_pts[i], top_pts[j], bot_pts[j]))
        face_side.material_index = 1
        for loop in face_side.loops:
            loop[uv_layer].uv = (0.001, 0.001)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new('Glass trackpad')
    bm.to_mesh(mesh)
    bm.free()
    mesh.update()

    tp_mat_top = material('Glass trackpad surface', [
        v * 1.02 for v in profile['materials']['rail']['rgb']
    ], metal=0.08, rough=0.18)
    mesh.materials.append(tp_mat_top)

    side_glass_rgb = [v * 0.70 for v in profile['materials']['rail']['rgb']]
    tp_mat_side = material('Glass trackpad chamfer', side_glass_rgb, metal=0.35, rough=0.20)
    mesh.materials.append(tp_mat_side)

    obj = bpy.data.objects.new('Glass trackpad', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def _build_palmrest_branding(width, height, base_depth, deck_style, oem, mat, parent):
    """Add laser-etched Googlebook branding to left palmrest and OEM/Dolby to right palmrest."""
    font_path = 'C:/Windows/Fonts/segoeui.ttf'
    font = bpy.data.fonts.load(font_path) if Path(font_path).exists() else None

    tp_cz = (11.5 + height / 2 - 6.0) / 2.0
    y_pos = (base_depth / 2 + 0.015) * MM

    # Left palmrest: Googlebook wordmark
    gx = -width / 2 + 30.0
    text_data = bpy.data.curves.new('Palmrest Googlebook', type='FONT')
    text_data.body = 'Googlebook'
    if font:
        text_data.font = font
    text_data.size = 0.0036  # 3.6 mm cap-height
    text_data.extrude = 0.00003  # 0.03 mm slight 3D relief
    text_obj = bpy.data.objects.new('Palmrest Googlebook', text_data)
    bpy.context.scene.collection.objects.link(text_obj)
    bpy.context.view_layer.objects.active = text_obj
    text_obj.select_set(True)
    bpy.ops.object.convert(target='MESH')
    mesh_obj = bpy.context.view_layer.objects.active
    mesh_obj.rotation_euler = (-math.pi / 2, 0, 0)
    mesh_obj.location = (gx * MM, y_pos, tp_cz * MM)
    mesh_obj.parent = parent
    if mat:
        mesh_obj.data.materials.append(mat)

    # Right palmrest for Lenovo: Dolby Atmos
    if oem == 'Lenovo':
        rx = width / 2 - 36.0
        da_data = bpy.data.curves.new('Palmrest Dolby Atmos', type='FONT')
        da_data.body = 'Dolby Atmos'
        if font:
            da_data.font = font
        da_data.size = 0.0028
        da_data.extrude = 0.00002
        da_obj = bpy.data.objects.new('Palmrest Dolby Atmos', da_data)
        bpy.context.scene.collection.objects.link(da_obj)
        bpy.context.view_layer.objects.active = da_obj
        da_obj.select_set(True)
        bpy.ops.object.convert(target='MESH')
        da_mesh = bpy.context.view_layer.objects.active
        da_mesh.rotation_euler = (-math.pi / 2, 0, 0)
        da_mesh.location = (rx * MM, y_pos, tp_cz * MM)
        da_mesh.parent = parent
        if mat:
            da_mesh.data.materials.append(mat)


def _build_ports(width, height, base_depth, ports_spec, mats, parent):
    """Build accurate per-model side I/O ports for the laptop base."""
    w, h = width, height
    mat_black = mats.get('black')
    mat_logo = mats.get('logo', mats.get('rail'))
    mat_led = mats.get('flash')

    for side_name, side_sign in (('left', -1), ('right', 1)):
        ports = ports_spec.get(side_name, [])
        for p in ports:
            ptype = p['type']
            pz = -h / 2 + p['z']
            x_edge = side_sign * (w / 2)

            if ptype == 'usb_c':
                _slab_xz(f'USB-C cavity | {side_name} | {p["z"]}',
                         1.6, 8.4, 2.6, 1.2,
                         (x_edge - side_sign * 0.7, 0.0, pz), mat_black, parent, 0.08)
                _slab_xz(f'USB-C tongue | {side_name} | {p["z"]}',
                         1.0, 5.6, 0.6, 0.2,
                         (x_edge - side_sign * 0.5, 0.0, pz), mat_logo, parent, 0.04)

            elif ptype == 'usb_a':
                _slab_xz(f'USB-A cavity | {side_name} | {p["z"]}',
                         1.8, 13.5, 4.6, 0.4,
                         (x_edge - side_sign * 0.8, 0.0, pz), mat_black, parent, 0.06)
                _slab_xz(f'USB-A tongue | {side_name} | {p["z"]}',
                         1.4, 12.0, 1.6, 0.2,
                         (x_edge - side_sign * 0.7, 0.8, pz), mat_black, parent, 0.04)

            elif ptype == 'hdmi':
                _slab_xz(f'HDMI cavity | {side_name} | {p["z"]}',
                         2.0, 14.5, 4.4, 0.6,
                         (x_edge - side_sign * 0.9, 0.0, pz), mat_black, parent, 0.06)

            elif ptype == 'audio':
                _slab_xz(f'Audio jack | {side_name} | {p["z"]}',
                         1.6, 3.6, 3.6, 1.75,
                         (x_edge - side_sign * 0.7, 0.0, pz), mat_black, parent, 0.15)
                _slab_xz(f'Audio rim | {side_name} | {p["z"]}',
                         0.4, 4.4, 4.4, 2.15,
                         (x_edge - side_sign * 0.2, 0.0, pz), mat_logo, parent, 0.08)

            elif ptype == 'microsd':
                _slab_xz(f'MicroSD slot | {side_name} | {p["z"]}',
                         1.4, 11.5, 1.4, 0.4,
                         (x_edge - side_sign * 0.6, 0.0, pz), mat_black, parent, 0.04)

            elif ptype == 'kensington':
                _slab_xz(f'Kensington slot | {side_name} | {p["z"]}',
                         1.6, 6.8, 3.0, 0.6,
                         (x_edge - side_sign * 0.7, 0.0, pz), mat_black, parent, 0.05)

            elif ptype in ('battery_led', 'status_leds'):
                _slab_xz(f'LED indicator | {side_name} | {p["z"]}',
                         0.6, 1.0, 1.0, 0.45,
                         (x_edge - side_sign * 0.2, 0.0, pz), mat_led, parent, 0.05)


def create_laptop_device(profile, root, mats):
    """Build an articulated clamshell Googlebook with Lid, Glowbar, OEM logo, and Keyboard Base."""
    # Clear generic phone panels and build dedicated articulated laptop structure
    for child in list(root.children_recursive):
        bpy.data.objects.remove(child, do_unlink=True)

    articulation = profile['articulation']
    axis = articulation['axis_mm']
    body = profile['body_mm']
    w, h = body['width'], body['height']
    ld = body['depth']
    bd = body['base_depth_mm']
    r = body['corner_radius']

    pivots = {}
    panel_objs = {}
    for panel in profile['panels']:
        pname = panel['name']
        pivot = bpy.data.objects.new(articulation['pivots'][pname], None)
        bpy.context.scene.collection.objects.link(pivot)
        pivot.parent = root
        pivot.location = tuple(v * MM for v in axis)
        pivot['role'] = 'fold-pivot'
        pivot['panel'] = pname
        pivot['axis'] = articulation['axis']
        pivots[pname] = pivot

        p_obj = bpy.data.objects.new(pname, None)
        bpy.context.scene.collection.objects.link(p_obj)
        p_obj.parent = pivot
        p_obj.location = tuple((v - axis[i]) * MM for i, v in enumerate(panel['center_mm']))
        panel_objs[pname] = p_obj

    lid_obj = panel_objs['Lid']
    base_obj = panel_objs['Base']

    # 1. Lid Assembly — strictly separated Z layers so WebGL depth buffer never Z-fights while orbiting:
    #   Rear lid shell back face:  z = -ld/2 - 0.10 mm
    #   Aluminum enclosure:        z in [-ld/2, +ld/2 - 0.50 mm]
    #   Front black glass:         z in [+ld/2 - 0.55 mm, +ld/2 - 0.15 mm]
    #   Device screen:             z = +ld/2 + 0.14 mm
    slab('Aluminum enclosure', w, h, ld - 0.50, r, (0, 0, -0.25),
         mats['rail'], lid_obj, (0.50, 0.35))
    slab('Rear lid shell', w - 1.0, h - 1.0, 0.24, max(0.5, r - 0.5),
         (0, 0, -ld / 2 + 0.02), mats['back'], lid_obj, 0.06)
    slab('Front black glass', w - 1.2, h - 1.2, 0.40, max(0.5, r - 0.6),
         (0, 0, ld / 2 - 0.35), mats['black'], lid_obj, 0.05)

    # Signature reverse notch communications bar / easy-open handle on Lenovo Googlebook
    if 'top_lip_mm' in body:
        _build_lenovo_communications_bar(w, h, ld, mats, lid_obj)

    # Screen placeholder on Lid
    screen_spec = profile['screen']
    slab(screen_spec['object'], 1, 1, 0.01, 0.1, (0, 0, 0), mats['black'], lid_obj, 0.002)
    screen_spec['parent_center_mm'] = [0.0, h / 2, -ld / 2]

    # 4-color LED Glowbar on rear of Lid (-Z)
    if 'glowbar' in profile:
        gb = profile['glowbar']
        gx, gy = gb['center_mm']
        gw, gh = gb['size_mm']
        slab('Glowbar housing', gw + 0.8, gh + 0.8, 0.14, (gh + 0.8) / 2,
             (gx, gy, -ld / 2 - 0.14), mats['black'], lid_obj, 0.03)
        seg_w = gw / 4.0
        for idx, col_rgb in enumerate(gb['colors']):
            seg_mat = material(f'Glowbar LED {idx}', col_rgb, metal=0.0, rough=0.15)
            bsdf = seg_mat.node_tree.nodes['Principled BSDF']
            bsdf.inputs['Emission Color'].default_value = tuple(col_rgb) + (1.0,)
            bsdf.inputs['Emission Strength'].default_value = 1.8
            sx = gx - gw / 2 + seg_w * (idx + 0.5)
            rad = gh / 2 if idx in (0, 3) else 0.15
            slab(f'Glowbar LED | {idx}', seg_w + 0.05, gh, 0.16, rad,
                 (sx, gy, -ld / 2 - 0.18), seg_mat, lid_obj, 0.03)

    # 3D OEM logo on rear of Lid (-Z)
    if 'rear_logo' in profile:
        _build_oem_logo(profile['rear_logo'], ld + 0.24, mats.get('logo', mats['rail']), lid_obj)

    # 2. Base / Keyboard Deck Assembly:
    # Deck top face at y = bd/2 - 0.10 mm (root y = -0.10 mm)
    deck_obj = _slab_xz('Base aluminum deck', w, h, bd - 0.20, r, (0, -0.10, 0), mats['back'], base_obj, (0.60, 0.40))

    deck_style = profile.get('deck_style', 'standard')
    if deck_style == 'dell_chiclet':
        well_w = w - 24.5
    elif deck_style == 'lenovo_15':
        well_w = w - 65.5
    else:
        well_w = w - 36.5

    kb_center_z = (-h / 2 + 16.5 + 7.5) / 2.0
    kb_depth_z = 7.5 - (-h / 2 + 16.5) + 2.6

    if deck_style == 'lenovo_15':
        tp_w = 150.0
        tp_h = 95.0
    else:
        tp_w = 126.0
        tp_h = 82.0
    tp_cz = (11.5 + h / 2 - 6.0) / 2.0

    # Boolean difference: cut physical keyboard well and trackpad pockets into the unibody aluminum deck
    cut_kb = _slab_xz('_cut_kb', well_w + 1.2, kb_depth_z + 1.2, 3.2, 2.6,
                      (0, bd / 2, kb_center_z), mats['back'], base_obj, 0.0)
    mod_kb = deck_obj.modifiers.new('WellCut', 'BOOLEAN')
    mod_kb.object = cut_kb
    mod_kb.operation = 'DIFFERENCE'
    mod_kb.solver = 'EXACT'
    bpy.context.view_layer.objects.active = deck_obj
    bpy.ops.object.modifier_apply(modifier='WellCut')
    bpy.data.objects.remove(cut_kb)

    cut_tp = _slab_xz('_cut_tp', tp_w + 1.8, tp_h + 1.8, 3.2, 4.2,
                      (0, bd / 2 + 0.10, tp_cz), mats['back'], base_obj, 0.0)
    mod_tp = deck_obj.modifiers.new('TrackpadCut', 'BOOLEAN')
    mod_tp.object = cut_tp
    mod_tp.operation = 'DIFFERENCE'
    mod_tp.solver = 'EXACT'
    bpy.context.view_layer.objects.active = deck_obj
    bpy.ops.object.modifier_apply(modifier='TrackpadCut')
    bpy.data.objects.remove(cut_tp)

    # Deep recessed keyboard well pocket floor
    well_mat = material('Keyboard well floor', [
        max(0.012, v * 0.28) for v in profile['materials']['back']['rgb']
    ], metal=0.08, rough=0.70)
    _slab_xz('Keyboard well', well_w + 1.1, kb_depth_z + 1.1, 0.20, 2.4,
             (0, bd / 2 - 1.50, kb_center_z), well_mat, base_obj, 0.05)

    _build_keycap_matrix(w, h, bd, deck_style, mats.get('keycap', mats['black']), base_obj, profile.get('id', ''))

    if deck_style == 'lenovo_15':
        _build_lenovo_bottom_grips(w, h, bd, well_mat, base_obj)

    # Precision 3D glass trackpad sitting in a recessed well pocket.
    # NOTE: the previous solid "chamfer rim" slab had its top face only 0.035 mm above
    # the glass top, covering the whole pad and causing striped depth-fighting at
    # oblique angles. The pocket floor now sits fully BELOW the glass (glass bottom is
    # bd/2 - 1.05 mm, floor top is bd/2 - 1.15 mm) so no two faces are near-coplanar.
    _slab_xz('Trackpad well recess', tp_w + 1.2, tp_h + 1.2, 0.20, 4.0,
             (0, bd / 2 - 1.25, tp_cz), well_mat, base_obj, 0.04)

    # 3. 3D Sculpted Glass Trackpad Slab with sloped chamfered sides (0.67 mm thickness, recessed 0.18 mm)
    _build_sculpted_trackpad(tp_w, tp_h, bd, tp_cz, mats, profile, base_obj)

    # Front opener lip chamfer (CNC milled scoop matching chassis aluminum, omitted on Lenovo with top lip handle)
    if 'top_lip_mm' not in body:
        chamfer_mat = material('Front opener chamfer', [
            v * 0.90 for v in profile['materials']['rail']['rgb']
        ], metal=profile['materials']['rail'].get('metal', 0.2), rough=0.26)
        _slab_xz('Front opener chamfer', 50.0, 1.6, 0.35, 1.0,
                 (0, bd / 2 - 0.28, h / 2 - 0.35), chamfer_mat, base_obj, 0.10)

    # Palmrest internal branding ("Googlebook" / "Dolby Atmos")
    _build_palmrest_branding(w, h, bd, deck_style, profile.get('manufacturer', ''), mats.get('logo', mats['rail']), base_obj)

    # Physical hinge barrels centered exactly along the mechanical pivot seam:
    # In base_obj: rear edge is at Z = -h/2, top deck is at Y = bd/2
    hinge_style = profile.get('hinge_style', 'center_bar')
    hz = -h / 2 + 1.8
    hy = bd / 2 - 1.2
    if hinge_style == 'convertible_dual':
        for sx in (-106.0, 106.0):
            _slab_xz(f'Convertible hinge | {sx:+.0f}', 28.0, 4.8, 2.4, 1.1,
                     (sx, hy, hz), mats['logo'], base_obj, 0.4)
    elif hinge_style == 'dual':
        for sx in (-98.0, 98.0):
            _slab_xz(f'Hinge barrel | {sx:+.0f}', 30.0, 4.6, 2.4, 1.1,
                     (sx, hy, hz), mats['rail'], base_obj, 0.4)
    elif hinge_style == 'dual_wide':
        for sx in (-82.0, 82.0):
            _slab_xz(f'Hinge barrel | {sx:+.0f}', 26.0, 4.4, 2.4, 1.1,
                     (sx, hy, hz), mats['logo'], base_obj, 0.4)
    else:
        _slab_xz('Center hinge barrel', w * 0.58, 4.6, 2.4, 1.1,
                 (0, hy, hz), mats['rail'], base_obj, 0.4)

    # Model-specific side I/O ports
    _build_ports(w, h, bd, profile.get('ports', {}), mats, base_obj)

    # Bottom rubber feet
    for fx in (-w / 2 + 28.0, w / 2 - 28.0):
        for fz in (-h / 2 + 22.0, h / 2 - 22.0):
            _slab_xz('Rubber foot', 26.0, 6.5, 0.6, 2.5,
                     (fx, -bd / 2 - 0.20, fz), mats['black'], base_obj, 0.20)

    return root


