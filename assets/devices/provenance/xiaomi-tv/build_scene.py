"""Blender-first Xiaomi remote / TV transition study. Run with Blender --background --python."""
import bpy
import bmesh
import math
import json
from pathlib import Path
from mathutils import Vector, Matrix

OUT = Path(__file__).resolve().parent
OUT.mkdir(exist_ok=True)
for folder in ('frames', 'stills'):
    (OUT / folder).mkdir(exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = 'BLENDER_EEVEE'
scene.render.resolution_x = 1280
scene.render.resolution_y = 720
scene.render.resolution_percentage = 100
scene.render.fps = 30
scene.frame_start = 1
scene.frame_end = 225
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGB'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.world = bpy.data.worlds.new('Pearl studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.72, .75, .8, 1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .65
world_nodes = scene.world.node_tree.nodes
world_links = scene.world.node_tree.links
world_nodes['Background'].inputs[1].default_value = .22
camera_background = world_nodes.new('ShaderNodeBackground')
camera_background.inputs[0].default_value = (.92, .95, 1, 1)
camera_background.inputs[1].default_value = 2.5
light_path = world_nodes.new('ShaderNodeLightPath')
world_mix = world_nodes.new('ShaderNodeMixShader')
world_links.new(light_path.outputs['Is Camera Ray'], world_mix.inputs[0])
world_links.new(world_nodes['Background'].outputs[0], world_mix.inputs[1])
world_links.new(camera_background.outputs[0], world_mix.inputs[2])
world_links.new(world_mix.outputs[0], world_nodes['World Output'].inputs[0])
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = .01

def linear(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4

def mat(name, color, rough=.35, metal=0, morph=False):
    m = bpy.data.materials.new(name)
    m.diffuse_color = tuple(linear(c) for c in color) + (1,)
    m.use_nodes = True
    nodes, links = m.node_tree.nodes, m.node_tree.links
    p = nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = m.diffuse_color
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    if morph:
        e = nodes.new('ShaderNodeEmission')
        e.inputs[0].default_value = m.diffuse_color
        mix = nodes.new('ShaderNodeMixShader')
        mix.name = 'Icon to dimensional material'
        links.new(e.outputs[0], mix.inputs[1])
        links.new(p.outputs[0], mix.inputs[2])
        links.new(mix.outputs[0], nodes.get('Material Output').inputs['Surface'])
        for f, v in ((1, 0), (5, .05), (33, 1)):
            mix.inputs[0].default_value = v
            mix.inputs[0].keyframe_insert('default_value', frame=f)
    return m

graphite = mat('Graphite | soft ABS', (.16, .175, .19), .31, morph=True)
face = mat('Front face | satin charcoal', (.215, .23, .24), .32, morph=True)
rubber = mat('Buttons | dark silicone', (.105, .12, .14), .43, morph=True)
ringmat = mat('Navigation | brushed graphite', (.24, .26, .28), .3, .15, True)
seam = mat('Housing parting line', (.045, .05, .06), .55, morph=True)
white = mat('Warm white legends', (.86, .88, .87), .43, morph=True)
red = mat('Netflix red', (.847, .122, .149), .5, morph=True)
blue = mat('Prime blue', (.08, .46, .68), .45, morph=True)
silver = mat('HDMI | nickel', (.55, .58, .63), .23, .85)
gold = mat('HDMI | contact gold', (.76, .55, .21), .25, .8)
glass = mat('IR window', (.045, .065, .085), .13)
label_font = bpy.data.fonts.load('C:/Windows/Fonts/arial.ttf')
bold_font = bpy.data.fonts.load('C:/Windows/Fonts/arialbd.ttf')
condensed_font = bpy.data.fonts.load('C:/Windows/Fonts/arialnb.ttf')
symbol_font = bpy.data.fonts.load(str(OUT / 'remote-symbols.ttf'))
navigation_font = bpy.data.fonts.load(str(OUT / 'navigation-symbols.ttf'))

def empty(name):
    obj = bpy.data.objects.new(name, None)
    scene.collection.objects.link(obj)
    return obj

remote = empty('REMOTE | dimensional icon rig')
stick = empty('TV STICK | plugged into TV HDMI')
tv = empty('TV | screen reveal')

def outline(w, h, r, steps=16):
    pts = []
    for sx, sy, a in ((1, -1, -90), (1, 1, 0), (-1, 1, 90), (-1, -1, 180)):
        for i in range(steps + 1):
            t = math.radians(a + 90 * i / steps)
            pts.append((sx * (w / 2 - r) + r * math.cos(t), sy * (h / 2 - r) + r * math.sin(t)))
    return pts

def slab(name, w, h, d, r, loc, material, parent=None, bevel=.04):
    pts = []
    for point in outline(w, h, r):
        if not pts or math.dist(point, pts[-1]) > .000001:
            pts.append(point)
    if math.dist(pts[0], pts[-1]) < .000001:
        pts.pop()
    n = len(pts)
    verts = [(x, y, z) for z in (-d / 2, d / 2) for x, y in pts]
    faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
    faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.parent = parent
    obj.data.materials.append(material)
    for p in mesh.polygons:
        p.use_smooth = len(p.vertices) == 4
    if bevel:
        mod = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
        mod.width = bevel
        mod.segments = 4
        mod = obj.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
        mod.keep_sharp = True
    return obj

def disc(name, x, y, r, material, z=.82, d=.15, parent=remote):
    return slab(name, r * 2, r * 2, d, r, (x, y, z), material, parent, .025)

def line(name, points, material=white, width=.043, parent=remote, z=.94):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.bevel_depth = width
    curve.bevel_resolution = 3
    spline = curve.splines.new('POLY')
    spline.points.add(len(points) - 1)
    for p, (x, y) in zip(spline.points, points):
        p.co = (x, y, z, 1)
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.parent = parent
    obj.data.materials.append(material)
    return obj

def text(name, body, loc, size, material, parent=remote):
    curve = bpy.data.curves.new(name, 'FONT')
    curve.body = body
    curve.font = condensed_font if 'Netflix' in name or 'YouTube / legend' in name else bold_font if 'legend' in name or 'TV+' in name else label_font
    curve.align_x = 'CENTER'
    curve.align_y = 'CENTER'
    curve.size = size
    curve.extrude = .001
    if parent == remote and ('legend' in name or name.startswith('TV+ /')):
        curve.offset = .008
    if name == 'TV+ / Xiaomi':
        curve.offset = .002
    curve.resolution_u = 8
    obj = bpy.data.objects.new(name, curve)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.parent = parent
    obj.data.materials.append(material)
    return obj

def glyph(name, code, x, y, size, material, z=.94):
    obj = text(name, chr(code), (x, y, z), 1, material)
    obj.data.font = navigation_font if name.startswith(('Back /', 'Home /', 'Volume /')) else symbol_font
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.context.view_layer.update()
    bpy.ops.object.convert(target='MESH')
    obj = bpy.context.object
    points = [v.co for v in obj.data.vertices]
    low = Vector((min(p.x for p in points), min(p.y for p in points), 0))
    high = Vector((max(p.x for p in points), max(p.y for p in points), 0))
    scale = size / max(high.x - low.x, high.y - low.y)
    for vert in obj.data.vertices:
        vert.co.x = (vert.co.x - (low.x + high.x) / 2) * scale
        vert.co.y = (vert.co.y - (low.y + high.y) / 2) * scale
    return obj

# Import actual logo outlines, then fit their complete geometry inside a key.
def artwork(filename, name, x, y, width, material=None):
    before = set(bpy.data.objects)
    bpy.ops.import_curve.svg(filepath=str(OUT / 'logo-sources' / filename))
    objects = [obj for obj in bpy.data.objects if obj not in before and obj.type == 'CURVE']
    assert objects, filename
    bpy.ops.object.select_all(action='DESELECT')
    colors = {}
    for obj in objects:
        colors[obj.name] = tuple(obj.data.materials[0].diffuse_color[:3])
        obj.select_set(True)
    names = [obj.name for obj in objects]
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.object.convert(target='MESH')
    objects = [bpy.data.objects[n] for n in names]
    points = [obj.matrix_world @ vertex.co for obj in objects for vertex in obj.data.vertices]
    x0, x1 = min(v.x for v in points), max(v.x for v in points)
    y0, y1 = min(v.y for v in points), max(v.y for v in points)
    scale = width / (x1 - x0)
    for i, obj in enumerate(objects):
        color = colors[obj.name]
        fitted = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
        obj.parent = remote
        obj.location, obj.rotation_euler, obj.scale = (0, 0, 0), (0, 0, 0), (1, 1, 1)
        for vertex, co in zip(obj.data.vertices, fitted):
            vertex.co = ((co.x - (x0+x1)/2) * scale + x, (co.y - (y0+y1)/2) * scale + y, .914)
        ink = material or (youtube_red if color[0] > .5 and color[1] < .2 else white if min(color) > .9 else mark_black)
        obj.data.materials.clear()
        obj.data.materials.append(ink)
        obj.name = name + ' / official mark %02d' % i
        obj['Artwork width cm'] = width
    bpy.ops.object.select_all(action='DESELECT')

mark_black = mat('Logo ink | charcoal', (.133, .133, .133), .5, morph=True)
youtube_red = mat('YouTube official red', (1, 0, .2), .5, morph=True)

# Shallow front/rear arcs terminate before the side midpoint; short vertical rails join them.
HALF_WIDTH = 1.775
FRONT_CROWN = .62
BACK_CROWN = .72
FRONT_RISE = .26
BACK_RISE = .34
SIDE_RADIUS = .08

def front_height(x, y):
    return FRONT_CROWN - FRONT_RISE * (x / HALF_WIDTH) ** 2

def back_height(x, y):
    return -BACK_CROWN + BACK_RISE * (x / HALF_WIDTH) ** 2

# Plan-view corner rounding and depth fillets are independent.
PLAN_CORNER_RADIUS = .55
END_DEPTH_RADIUS = .16
y_samples = {-6.0, -3.0, 0.0, 3.0, 6.0}
for radius in (PLAN_CORNER_RADIUS, END_DEPTH_RADIUS):
    for i in range(17):
        y = 8.7 - radius + radius * math.sin(math.pi / 2 * i / 16)
        y_samples.update((-y, y))
rings = []
for y in sorted(y_samples):
    plan_t = max(0, min(1, (abs(y) - (8.7 - PLAN_CORNER_RADIUS)) / PLAN_CORNER_RADIUS))
    width = HALF_WIDTH - PLAN_CORNER_RADIUS + PLAN_CORNER_RADIUS * math.sqrt(max(0, 1 - plan_t**2))
    depth_t = max(0, min(1, (abs(y) - (8.7 - END_DEPTH_RADIUS)) / END_DEPTH_RADIUS))
    depth_scale = .90 + .10 * math.sqrt(max(0, 1 - depth_t**2))
    rings.append((y, width, depth_scale))

section = []
r = SIDE_RADIUS
edge_x = HALF_WIDTH - r
upper = front_height(edge_x, 0)
lower = back_height(edge_x, 0)
# Right upper rail and its shoulder.
for i in range(7):
    section.append((HALF_WIDTH, (upper - r) * i / 6))
for i in range(1, 17):
    t = math.pi / 2 * i / 16
    section.append((edge_x + r * math.cos(t), upper - r + r * math.sin(t)))
# Shallow face arc, then left shoulder and straight side.
for i in range(1, 65):
    x = edge_x - 2 * edge_x * i / 64
    section.append((x, front_height(x, 0)))
for i in range(1, 17):
    t = math.pi / 2 + math.pi / 2 * i / 16
    section.append((-edge_x + r * math.cos(t), upper - r + r * math.sin(t)))
for i in range(1, 9):
    section.append((-HALF_WIDTH, upper - r + (lower + r - upper + r) * i / 8))
# The rear arc starts below the side midpoint, rather than at the seam.
for i in range(1, 17):
    t = math.pi + math.pi / 2 * i / 16
    section.append((-edge_x + r * math.cos(t), lower + r + r * math.sin(t)))
for i in range(1, 65):
    x = -edge_x + 2 * edge_x * i / 64
    section.append((x, back_height(x, 0)))
for i in range(1, 17):
    t = math.pi * 1.5 + math.pi / 2 * i / 16
    section.append((edge_x + r * math.cos(t), lower + r + r * math.sin(t)))
for i in range(1, 6):
    section.append((HALF_WIDTH, (lower + r) * (1 - i / 6)))
verts, faces = [], []
count = len(section)
for y, width, depth_scale in rings:
    verts.extend((x * width / HALF_WIDTH, y, z * depth_scale) for x, z in section)

for j in range(len(rings) - 1):
    for i in range(count):
        faces.append((j * count + i, (j + 1) * count + i, (j + 1) * count + (i + 1) % count, j * count + (i + 1) % count))
faces += [tuple(range(count)), tuple(reversed(range((len(rings) - 1) * count, len(rings) * count)))]
mesh = bpy.data.meshes.new('Pronounced transverse arcs; straight length and minimal end radii')
mesh.from_pydata(verts, [], faces)
mesh.update()
housing = bpy.data.objects.new('Remote / continuous curved housing', mesh)
scene.collection.objects.link(housing)
housing.parent = remote
mesh.materials.append(graphite)
mesh.materials.append(face)
for poly in mesh.polygons:
    poly.use_smooth = len(poly.vertices) == 4
    poly.material_index = int(poly.center.z > 0)
boundary = outline(3.55, 17.4, PLAN_CORNER_RADIUS, 24)
line('Remote / horizontal shell joint', boundary + boundary[:1], seam, .009, z=0)
slab('Remote / IR cap', 1.20, .08, .24, .035, (0, 8.715, 0), glass, remote, .025)
cover_points = outline(2.70, 8.1, .4)
cover = line('Remote / battery cover seam', cover_points + cover_points[:1], seam, .009, z=0)
for pt in cover.data.splines[0].points:
    pt.co.y -= 3.65
    pt.co.z = back_height(pt.co.x, pt.co.y) - .003

coral = mat('Reference warm power and microphone', (.79, .38, .28), .5, morph=True)
micblue = mat('Reference microphone blue', (.16, .48, .77), .4, morph=True)
details_before = set(remote.children)
disc('Power', 0, 7.60, .36, rubber)
glyph('Power / authentic symbol', 0xf8c7, 0, 7.60, .46, coral)
disc('Voice microphone', 0, 6.40, .36, rubber)
slab('Microphone / blue capsule', .18, .32, .012, .055, (0, 6.46, .94), micblue, remote, .004)
line('Microphone / warm cradle', [(.21 * math.cos(t), 6.40 + .21 * math.sin(t)) for t in [math.pi + i * math.pi / 24 for i in range(25)]], coral)
line('Microphone / stem', [(0, 6.19), (0, 6.12)], coral)
disc('D-pad / dark recess', 0, 4.03, 1.39, seam, .737, .075)
disc('D-pad / navigation ring', 0, 4.03, 1.34, rubber, .825, .17)
disc('D-pad / center seam', 0, 4.03, .64, seam, .927, .018)
disc('D-pad / OK', 0, 4.03, .59, rubber, .95, .09)
for name, x in (('Xiaomi TV+', -.98), ('Back', 0), ('Home', .98)):
    disc(name, x, 1.52, .35, rubber)
text('TV+ / Xiaomi', 'xiaomi', (-.98, 1.61, .94), .16, white)
text('TV+ / TV', 'TV+', (-.98, 1.41, .94), .24, white)
glyph('Back / authentic symbol', 0xe5c4, 0, 1.52, .41, white)
glyph('Home / filled symbol', 0xe9b2, .98, 1.52, .41, white)
for name, x in (('Netflix', -.79), ('Prime', .79)):
    slab(name + ' / shortcut', 1.37, .65, .17, .26, (x, .35, .82), white, remote, .04)
artwork('netflix.svg', 'Netflix', -.79, .35, 1.25, red)
artwork('prime-monochrome.svg', 'Prime', .79, .35, 1.25, mark_black)
for name, x in (('YouTube', -.79), ('Apps', .79)):
    slab(name + ' / shortcut', 1.37, .65, .17, .26, (x, -.70, .82), white, remote, .04)
artwork('youtube-official.svg', 'YouTube', -.79, -.70, 1.25)
text('Apps / legend', 'APPS', (.48, -.70, .914), .21, rubber)
for x in (.98, 1.10, 1.22, 1.34):
    for y in (-.82, -.70, -.58):
        slab('Apps / grid', .09, .09, .01, .01, (x, y, .918), ringmat, remote, 0)
slab('Volume / rocker', .7, 2.12, .20, .34, (0, -2.54, .84), rubber, remote, .05)
glyph('Volume / rounded plus', 0xe145, 0, -2.00, .36, white, z=.96)
glyph('Volume / rounded minus', 0xe15b, 0, -3.09, .36, white, z=.96)
text('Xiaomi / subtle brand', 'xiaomi', (0, -7.44, .69), .36, seam)
# Conform the complete button/legend meshes to the horizontal crown. This keeps
# the large navigation ring and app keys seated, rather than floating on a tangent.
detail_names = [obj.name for obj in set(remote.children) - details_before]
bpy.ops.object.select_all(action='DESELECT')
for name in detail_names:
    bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active = bpy.data.objects[detail_names[0]]
bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
bpy.ops.object.convert(target='MESH')
for name in detail_names:
    obj = bpy.data.objects[name]
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    ink_z = None
    if ' / official mark ' in name:
        bm.normal_update()
        bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.z < 0])
        ink_z = .910 if obj.data.materials[0] == white else .908
    elif name.startswith(('Power /', 'Microphone /', 'Back /', 'Home /', 'TV+ /')):
        ink_z = .897
    elif name.startswith('Volume /') and name != 'Volume / rocker':
        ink_z = .942
    elif 'legend' in name or name.startswith(('Prime / smile', 'Apps / grid')):
        ink_z = .907
    elif name == 'YouTube / red badge':
        ink_z = .908
    elif name == 'YouTube / filled play':
        ink_z = .910
    elif name == 'Xiaomi / subtle brand':
        ink_z = .742
    if ink_z is not None:
        bm.normal_update()
        bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.normal.z < .1], context='FACES')
        for vert in bm.verts:
            vert.co.z = ink_z - obj.location.z
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=.000001)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    if any(edge.calc_length() > .15 for edge in bm.edges):
        bmesh.ops.subdivide_edges(bm, edges=list(bm.edges), cuts=5, use_grid_fill=True)
    bmesh.ops.triangulate(bm, faces=list(bm.faces))
    for vert in bm.verts:
        x = vert.co.x + obj.location.x
        vert.co.z += front_height(x, 0) - .74
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.verts.ensure_lookup_table()
    bm.verts.index_update()
    fresh_mesh = bpy.data.meshes.new(name + ' / curved surface')
    fresh_mesh.from_pydata([tuple(v.co) for v in bm.verts], [], [[v.index for v in f.verts] for f in bm.faces])
    for material in obj.data.materials:
        fresh_mesh.materials.append(material)
    obj.data = fresh_mesh
    bm.free()
    for poly in obj.data.polygons:
        poly.use_smooth = True

# Reference stick: domed ends, matte upper body and glossy lower third.
stickmat = mat('Stick | matte charcoal', (.12, .125, .13), .30)
stickgloss = mat('Stick | piano black cap', (.022, .026, .03), .12)
stickbody = slab('Stick / matte body and glossy lower third', 3.0, 9.2, 1.42, 1.10, (0, 0, 0), stickmat, stick, .30)
stickbody.modifiers['Soft manufactured edges'].segments = 10
bpy.context.view_layer.objects.active = stickbody
for modifier in list(stickbody.modifiers):
    bpy.ops.object.modifier_apply(modifier=modifier.name)
bm = bmesh.new()
bm.from_mesh(stickbody.data)
bmesh.ops.bisect_plane(bm, geom=list(bm.verts) + list(bm.edges) + list(bm.faces), dist=.00001, plane_co=(0, -1.24, 0), plane_no=(0, 1, 0))
bm.to_mesh(stickbody.data)
bm.free()
stickbody.data.materials.append(stickgloss)
for poly in stickbody.data.polygons:
    poly.material_index = int(poly.center.y < -1.2399)
brand = text('Stick / vertical Xiaomi', 'xiaomi', (0, .83, .724), .53, ringmat, stick)
brand.rotation_euler.z = -math.pi / 2
led = mat('Stick | white status LED', (.94, .98, 1), .2)
led.node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (.7, .85, 1, 1)
led.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 2
slab('Stick / status light', .075, .31, .018, .035, (0, -3.5, .731), led, stick, .008)
slab('Stick / HDMI metal', 1.39, 1.48, .46, .15, (0, 5.26, .03), silver, stick, .035)
slab('Stick / HDMI tongue', 1.1, .09, .2, .06, (0, 6.0, .03), seam, stick, .01)
for i in range(9):
    slab('Stick / HDMI contact %02d' % i, .06, .015, .07, .007, (-.44 + i * .11, 6.047, .015), gold, stick, .003)
port = slab('Stick / micro USB', .8, .29, .04, .1, (1.475, .35, 0), seam, stick, .01)
port.rotation_euler = (0, math.pi / 2, 0)

# Screen-mapped generic television. Local XY face becomes the upright XZ screen.
tv.location = (0, 120, 1.45)
tv.rotation_euler = (math.pi / 2, 0, 0)
tvbody = mat('TV | satin aluminum', (.11, .125, .145), .25, .55)
tvblack = mat('TV | reflective dark metal bezel', (.28, .30, .32), .16, .90)
slab('TV / enclosure', 72, 40.5, 1.2, .68, (0, 0, 0), tvbody, tv, .18)
slab('TV / bezel', 72, 40.5, .10, .68, (0, 0, .65), tvblack, tv, .01)
screenmat = bpy.data.materials.new('TV | replaceable screen artwork')
screenmat.use_nodes = True
n, links = screenmat.node_tree.nodes, screenmat.node_tree.links
n.clear()
output = n.new('ShaderNodeOutputMaterial')
emission = n.new('ShaderNodeEmission')
emission.inputs['Strength'].default_value = .85
links.new(emission.outputs[0], output.inputs[0])
tex = n.new('ShaderNodeTexCoord')
separate = n.new('ShaderNodeSeparateXYZ')
links.new(tex.outputs['Generated'], separate.inputs[0])
def mathnode(op, a, b=None):
    nd = n.new('ShaderNodeMath')
    nd.operation = op
    if isinstance(a, (float, int)):
        nd.inputs[0].default_value = a
    else:
        links.new(a, nd.inputs[0])
    if b is not None:
        if isinstance(b, (float, int)):
            nd.inputs[1].default_value = b
        else:
            links.new(b, nd.inputs[1])
    return nd.outputs[0]
ywave = mathnode('SINE', mathnode('MULTIPLY', separate.outputs['Y'], 5.3))
phase = mathnode('ADD', mathnode('MULTIPLY', separate.outputs['X'], 6.7), mathnode('MULTIPLY', ywave, 1.5))
val = mathnode('ADD', mathnode('MULTIPLY', mathnode('SINE', phase), .5), .5)
ramp = n.new('ShaderNodeValToRGB')
links.new(val, ramp.inputs[0])
colors = [(0, (.014, .023, .12, 1)), (.28, (.055, .09, .42, 1)), (.50, (.21, .13, .57, 1)), (.68, (.15, .46, .68, 1)), (.82, (.12, .72, .72, 1)), (1, (.55, .87, .80, 1))]
ramp.color_ramp.elements.remove(ramp.color_ramp.elements[1])
for i, (position, color) in enumerate(colors):
    elem = ramp.color_ramp.elements[0] if i == 0 else ramp.color_ramp.elements.new(position)
    elem.position, elem.color = position, color
ramp.color_ramp.interpolation = 'EASE'
links.new(ramp.outputs[0], emission.inputs[0])
screen = slab('TV / SCREEN — replace material to insert UI', 71.44, 39.94, .035, .4, (0, 0, .72), screenmat, tv, 0)
uv = screen.data.uv_layers.new(name='Screen UV 0–1')
for loop in screen.data.loops:
    co = screen.data.vertices[loop.vertex_index].co
    uv.data[loop.index].uv = (co.x / 71.44 + .5, co.y / 39.94 + .5)
text('TV / Xiaomi', 'xiaomi', (0, -20.11, .73), .18, ringmat, tv)
# The connector and socket share a TV-local coordinate frame and remain attached.
slab('TV / rear HDMI housing', 4.8, 10, 1.9, .35, (-33.5, -13, -1.30), graphite, tv, .16)
socket = slab('TV / HDMI socket surround', .84, 1.76, .10, .16, (-35.94, -13, -1.30), silver, tv, .025)
socket.rotation_euler.y = math.pi / 2
opening = slab('TV / HDMI socket opening', .59, 1.50, .12, .12, (-36.00, -13, -1.30), seam, tv, .02)
opening.rotation_euler.y = math.pi / 2
stick.parent = tv
stick.location = (-40.70, -13, -1.33)
stick.rotation_euler = (0, 0, -math.pi / 2)
stick['Connection'] = 'HDMI axis is TV-local +X. Metal plug enters side socket at X=-36.0; 1.3 cm insertion.'
socket['Connector insertion cm'] = 1.3
label = text('TV / HDMI label', 'HDMI', (-34.7, -11.6, -2.27), .23, white, tv)
label.rotation_euler.y = math.pi

def area(name, loc, power, size, color, target=(0, 0, 0), size_y=None):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = power * (.32 if name.startswith('Rim') else .18)
    data.shape = 'RECTANGLE'
    data.size = size
    data.size_y = size_y or size
    data.color = color
    obj = bpy.data.objects.new(name, data)
    scene.collection.objects.link(obj)
    obj.location = loc
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj
area('Key | long softbox', (-12, 3, 20), 10500, 15, (1, .96, .91), size_y=28)
area('Rim | cool strip', (8, 7, 10), 6500, 4, (.72, .86, 1), size_y=25)
area('Fill | overhead', (0, -18, 24), 6000, 18, (1, 1, 1))
area('Stick | port reflection', (-48, 110, -2), 6500, 7, (.8, .89, 1), (-41, 121, -12), 16)
area('TV | edge softbox', (-45, 82, 32), 20000, 32, (.85, .91, 1), (0, 120, 0), 50)

camera_data = bpy.data.cameras.new('Product camera')
camera = bpy.data.objects.new('CAMERA | icon → orbit → glide → screen', camera_data)
scene.collection.objects.link(camera)
scene.camera = camera
camera_data.sensor_width = 36
camera_data.clip_start = .025
camera_data.clip_end = 1000
camera_data.lens = 55
camera_data.dof.use_dof = False

def smooth(t):
    t = max(0, min(1, t))
    return t * t * t * (t * (t * 6 - 15) + 10)

# Per-frame camera keys preserve the arc exactly and eliminate Bezier overshoot.
for f in range(1, 226):
    materialize = smooth((f - 1) / 32)
    remote.scale = (.65 + .35 * materialize, .65 + .35 * materialize, .012 + .988 * materialize)
    remote.keyframe_insert('scale', frame=f)
    t = max(0, min(1, (f - 1) / 92))
    theta = math.pi / 2 * (3*t*t - 2*t*t*t)
    # Hermite radius ends with forward speed, matching the following glide.
    h00, h01, h11 = 2*t**3 - 3*t**2 + 1, -2*t**3 + 3*t**2, t**3 - t**2
    radius = h00 * 65 + h01 * 24 + h11 * (-.6 * 92)
    camera.location = (0, -radius * math.sin(theta), 1.45 + radius * math.cos(theta))
    camera.rotation_euler = (theta, 0, 0)
    if f >= 93:
        g = max(0, min(1, (f - 93) / 112))
        h00, h10, h01 = 2*g**3 - 3*g**2 + 1, g**3 - 2*g**2 + g, -2*g**3 + 3*g**2
        camera.location = (0, h00 * -24 + h10 * (.6 * 112) + h01 * 29.34, 1.45)
        camera.rotation_euler = (math.pi / 2, 0, 0)
    camera_data.lens = 55 - 10 * smooth((f - 58) / 147)
    camera.keyframe_insert('location', frame=f)
    camera.keyframe_insert('rotation_euler', frame=f)
    camera_data.keyframe_insert('lens', frame=f)

for f, name in ((1, '01  ICON / ROTATE IMMEDIATELY'), (33, '02  FULL DEPTH'), (93, '03  90 DEGREES / CONTINUOUS GLIDE'), (160, '04  CONNECTED TV REVEAL'), (205, '05  TV FILLS VIEWPORT')):
    scene.timeline_markers.new(name, frame=f)
scene['Brief'] = 'Reference-matched curved remote and stick. Face-on icon → dimensional remote → 90 degree orbit → glide toward TV. Stick remains physically plugged into TV HDMI.'
scene['Reference library'] = 'https://github.com/feldmandev/motion-assets'
scene['Product reference'] = 'https://www.mi.com/global/product/xiaomi-tv-stick-4k/'
scene['Accuracy'] = 'Photo-matched procedural study, estimated dimensions; not vendor CAD. Reference: reference.png. Pronounced width-wise face arcs with straight side rails; constant along length with 1.6 mm depth fillets and 5.5 mm outline corner radii.'
scene['Edit screen'] = 'Replace the material on TV / SCREEN — replace material to insert UI. Local XY, front +Z.'

# Two editable inspection scenes keep the reference models and physical connection
# easy to review without scrubbing the animation or detaching its stick.
def review_scene(name, roots, positions, camera_position, target, ortho):
    review = bpy.data.scenes.new(name)
    review.world = scene.world
    review.render.engine = 'BLENDER_EEVEE'
    review.render.resolution_x = review.render.resolution_y = 1280
    review.render.resolution_percentage = 100
    review.view_settings.view_transform = 'AgX'
    review.unit_settings.system = 'METRIC'
    review.unit_settings.scale_length = .01
    for root, position in zip(roots, positions):
        copies = {}
        for original in [root] + list(root.children_recursive):
            copied = original.copy()
            copied.animation_data_clear()
            review.collection.objects.link(copied)
            copies[original] = copied
        for original, copied in copies.items():
            copied.parent = copies.get(original.parent)
        copies[root].location = position
        copies[root].rotation_euler = (0, 0, 0)
        copies[root].scale = (1, 1, 1)
    for light in [obj for obj in scene.objects if obj.type == 'LIGHT']:
        review.collection.objects.link(light)
    camera_review = bpy.data.objects.new(name + ' / camera', bpy.data.cameras.new(name))
    review.collection.objects.link(camera_review)
    review.camera = camera_review
    camera_review.location = camera_position
    camera_review.rotation_euler = (Vector(target) - camera_review.location).to_track_quat('-Z', 'Y').to_euler()
    if name.startswith('02'):
        direction = (Vector(target) - camera_review.location).normalized()
        right = direction.cross(Vector((0, 1, 0))).normalized()
        up = right.cross(direction)
        camera_review.rotation_euler = Matrix((right, up, -direction)).transposed().to_euler()
    camera_review.data.type = 'ORTHO'
    camera_review.data.ortho_scale = ortho
    camera_review.data.clip_end = 1000
    review.frame_set(110)
    return review

products = review_scene('02 / Reference models', [remote, stick], [(-2.6, 0, 0), (2.6, -3.6, 0)], (10, -3, 44), (0, 0, 0), 21)
profile = review_scene('03 / Curved remote profile', [remote], [(0, 0, 0)], (25, -5, 6.7), (0, 0, 0), 20)
cross_section = review_scene('04 / Across-width curvature', [remote], [(0, 0, 0)], (0, -30, .1), (0, 0, .1), 4.8)
cross_section.render.resolution_y = 640
connected_camera = bpy.data.objects.new('CAMERA | Connected TV inspection', bpy.data.cameras.new('Connected TV inspection'))
scene.collection.objects.link(connected_camera)
connected_camera.location = (-95, -20, 65)
connected_camera.rotation_euler = (Vector((0, 120, 1.45)) - connected_camera.location).to_track_quat('-Z', 'Y').to_euler()
connected_camera.data.type = 'ORTHO'
connected_camera.data.ortho_scale = 93
connection_camera = bpy.data.objects.new('CAMERA | HDMI connection detail', bpy.data.cameras.new('HDMI connection detail'))
scene.collection.objects.link(connection_camera)
connection_camera.location = (-53, 139, -1)
connection_camera.rotation_euler = (Vector((-38, 121.3, -11.55)) - connection_camera.location).to_track_quat('-Z', 'Y').to_euler()
connection_camera.data.type = 'ORTHO'
connection_camera.data.ortho_scale = 18

scene.frame_set(110)
bpy.ops.object.select_all(action='DESELECT')
for screen_ui in bpy.data.screens:
    for ar in screen_ui.areas:
        if ar.type == 'VIEW_3D':
            ar.spaces.active.region_3d.view_perspective = 'CAMERA'
            ar.spaces.active.shading.type = 'RENDERED'
            ar.spaces.active.overlay.show_overlays = False
scene.render.filepath = str(OUT / 'frames' / 'frame_')
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT / 'xiaomi-remote-to-tv.blend'))

# Matching vector icons are authored beside this scene from the same layout.
exec(compile((OUT / 'build_icons.py').read_text(encoding='utf-8'), str(OUT / 'build_icons.py'), 'exec'))

notes = {
    'fps': 30, 'frames': 225, 'seconds': 7.5, 'resolution': [1280, 720],
    'beats': {'materialize': [1, 33], 'orbit': [1, 93], 'glide': [93, 205], 'screen_hold': [205, 225]},
    'references': ['https://github.com/feldmandev/motion-assets', 'https://www.mi.com/global/product/xiaomi-tv-stick-4k/', 'https://www.mi.com/us/product/xiaomi-tv-stick-4k/specs/'],
    'accuracy': 'Photo-matched visual study. Remote estimated 174 × 35.5 × 13 mm. Generic 16:9 TV with equal 2.8 mm reflective metal bezels and concentric 6.8/4 mm corner radii. Not vendor CAD.',
    'camera': 'Pitch rotation starts at frame 1; 90 degrees at frame 93 with a continuous glide. TV exactly fills the final viewport, occluding the attached stick.',
    'connection': 'Stick parented to TV with HDMI plug seated 1.3 cm into rear side-facing socket.',
    'screen': 'Replaceable screen material and UV-mapped surface. No app integration or repository publication.'
}
(OUT / 'shot.json').write_text(json.dumps(notes, indent=2), encoding='utf-8')

# Export after saving the animated source: glTF's static export otherwise samples
# the first animation frame. Freeze geometry and physical shading, convert cm to m.
scene.frame_set(78)
remote.animation_data_clear()
remote.scale = (.01, .01, .01)
for material in bpy.data.materials:
    if material.use_nodes:
        nodes = material.node_tree.nodes
        if nodes.get('Principled BSDF') and nodes.get('Material Output'):
            material.node_tree.links.new(nodes['Principled BSDF'].outputs[0], nodes['Material Output'].inputs['Surface'])
bpy.ops.object.select_all(action='DESELECT')
for obj in [remote] + list(remote.children_recursive):
    obj.select_set(True)
bpy.context.view_layer.objects.active = remote
bpy.ops.export_scene.gltf(filepath=str(OUT / 'xiaomi-tv-remote.glb'), use_selection=True, use_active_scene=True, export_format='GLB', export_animations=False, export_current_frame=True, export_cameras=False, export_lights=False, export_extras=True)
# Export a standalone stick, then restore its exact seated transform for assembly.
stick_location, stick_rotation = stick.location.copy(), stick.rotation_euler.copy()
stick.parent = None
stick.location = (0, 0, 0)
stick.rotation_euler = (0, 0, 0)
stick.scale = (.01, .01, .01)
bpy.ops.object.select_all(action='DESELECT')
for obj in [stick] + list(stick.children_recursive):
    obj.select_set(True)
bpy.context.view_layer.objects.active = stick
bpy.ops.export_scene.gltf(filepath=str(OUT / 'xiaomi-tv-stick.glb'), use_selection=True, use_active_scene=True, export_format='GLB', export_animations=False, export_current_frame=True)
stick.parent = tv
stick.location, stick.rotation_euler, stick.scale = stick_location, stick_rotation, (1, 1, 1)
tv.location = (0, 0, 0)
tv.rotation_euler = (0, 0, 0)
tv.scale = (.01, .01, .01)
# glTF cannot carry procedural shader graphs. Use a plain blue screen in this
# interchange export; the .blend retains the editable procedural screen and UVs.
screenmat.node_tree.nodes.get('Emission').inputs['Color'].default_value = (.025, .075, .2, 1)
for link in list(screenmat.node_tree.nodes.get('Emission').inputs['Color'].links):
    screenmat.node_tree.links.remove(link)
bpy.ops.object.select_all(action='DESELECT')
for obj in [tv] + list(tv.children_recursive):
    obj.select_set(True)
bpy.context.view_layer.objects.active = tv
bpy.ops.export_scene.gltf(filepath=str(OUT / 'xiaomi-tv-connected.glb'), use_selection=True, use_active_scene=True, export_format='GLB', export_animations=False, export_current_frame=True)
print('SCENE_READY', OUT)
