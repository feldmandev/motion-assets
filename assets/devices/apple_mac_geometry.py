"""Apple silicon Mac enclosures; dimensions are published, detail positions are photo estimates."""
import math
from pathlib import Path

import bpy
from mathutils import Vector

from geometry import MM, slab, _slab_xz, subtract, apple_mark, material, outline


def _group(name, parent, center=(0, 0, 0)):
    obj = bpy.data.objects.new(name, None)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    obj.location = tuple(v*MM for v in center)
    return obj


def _cylinder(name, radius, depth, center, mat, parent, axis='Y'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=radius*MM, depth=depth*MM)
    obj = bpy.context.object
    obj.name = name
    obj.parent = parent
    obj.location = tuple(v*MM for v in center)
    obj.rotation_euler = (math.pi/2, 0, 0) if axis == 'Y' else (0, math.pi/2, 0) if axis == 'X' else (0, 0, 0)
    obj.data.materials.append(mat)
    for face in obj.data.polygons:
        face.use_smooth = len(face.vertices) == 4
    return obj


def _port(shell, parent, mats, name, center, size, outward):
    """Cut an actual shallow socket, with its dark back below the enclosure face."""
    width, height = size
    radius = min(height/2, width/2) if any(kind in name for kind in ('audio','power_button')) else min(height/2, width/2, .65)
    normal = Vector(outward)
    rotation = normal.to_track_quat('Z', 'Y').to_euler()
    for host in shell if isinstance(shell, (tuple, list)) else [shell]:
        cutter = slab('Mac socket tool', width, height, 4.0, radius,
                      tuple(center[i]-outward[i] for i in range(3)), None, parent, .05)
        cutter.rotation_euler = rotation
        subtract(host, cutter)
    well = slab('Port well | '+name, width-.08, height-.08, .12, max(.05, radius-.04),
                tuple(center[i]-outward[i]*2.85 for i in range(3)), mats['black'], parent, .025)
    well.rotation_euler = rotation
    if 'usb' in name.lower() or 'thunderbolt' in name.lower():
        tongue = slab('Port tongue | '+name, max(.55, width*(.25 if height>width else .62)),
                      max(.35, height*(.62 if height>width else .25)), .28,
                      min(.15, height*.1), tuple(center[i]-outward[i]*2.3 for i in range(3)),
                      mats['connector'], parent, .04)
        tongue.rotation_euler = rotation


def _vent(name, width, height, center, parent, mats, outward=(0, 0, -1), pitch=3, shell=None, perforated=False, hole_radius=.55):
    """One recessed grille; separated metal ribs expose the black cavity between them."""
    rotation = Vector(outward).to_track_quat('Z', 'Y').to_euler()
    holder = _group(name, parent, center)
    holder.rotation_euler = rotation
    if shell:
        for host in shell if isinstance(shell,(tuple,list)) else [shell]:
            cutter = slab('Exhaust recess tool', width, height, 3, 1.2,
                          tuple(center[i]-outward[i] for i in range(3)), None, parent, .05)
            cutter.rotation_euler = rotation
            subtract(host, cutter)
    slab(name+' | dark recess', width, height, .18, min(2, height/2), (0, 0, -1.5),
         mats['black'], holder, .04)
    vertices, faces = [], []
    if perforated:
        nx,ny=int(width/pitch),int(height/pitch)
        for row in range(ny):
            for col in range(nx):
                cx=(col-(nx-1)/2)*pitch;cy=(row-(ny-1)/2)*pitch
                start=len(vertices)
                for inner in (False,True):
                    for i in range(8):
                        angle=i*math.pi/4;co,si=math.cos(angle),math.sin(angle)
                        radius=hole_radius if inner else pitch/2/max(abs(co),abs(si))
                        vertices.append(((cx+radius*co)*MM,(cy+radius*si)*MM,-.02*MM))
                faces.extend((start+i,start+(i+1)%8,start+8+(i+1)%8,start+8+i) for i in range(8))
    for i in range(int(width/pitch)):
        if perforated:break
        x = -width/2+(i+.5)*pitch
        start = len(vertices)
        vertices.extend(((x-.38)*MM, y*MM, z*MM)
                        for y,z in [(-height/2,-.5),(height/2,-.5),(height/2,-.02),(-height/2,-.02)])
        vertices.extend(((x+.38)*MM, y*MM, z*MM)
                        for y,z in [(-height/2,-.5),(height/2,-.5),(height/2,-.02),(-height/2,-.02)])
        faces.extend(tuple(start+j for j in face) for face in [(0,1,2,3),(4,7,6,5),(0,4,5,1),(3,2,6,7),(1,5,6,2)])
    mesh = bpy.data.meshes.new(name+' | ribs')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mats['rail'] if perforated else mats['black'])
    ribs = bpy.data.objects.new(name+' | metal ribs', mesh)
    bpy.context.scene.collection.objects.link(ribs)
    ribs.parent = holder


def _desktop(profile, root, mats):
    spec = profile['apple_mac']
    dims = spec['dimensions_mm']
    w,d,h = (dims[k] for k in ('width','depth','height'))
    compact = w<150
    studio = spec['family'] == 'mac-studio'
    base_h = spec['base_foot_height_mm']
    base_polymer = material('Mac base | charcoal polymer', (.045,.050,.055), rough=.55)
    shell = _slab_xz('Mac aluminum enclosure', w, d, h-base_h,
                     spec['corner_radius_mm'], (0, base_h/2, 0), mats['rail'], root, (1.1, 1.1))
    if compact:
        _cylinder('Mac mini recessed circular foot', 52, base_h, (0, -h/2+base_h/2, 0), base_polymer, root)
        # Radial fins are visible through the undercut between foot and aluminum.
        for number in range(48):
            angle = 2*math.pi*number/48
            fin = _slab_xz('Intake fin', 1.0, 8.0, 4.0, .25,
                           (54*math.sin(angle), -h/2+base_h/2, 54*math.cos(angle)), base_polymer, root, .15)
            fin.rotation_euler[1] = angle
    else:
        _slab_xz('Mac rubber bottom foot', w-14, d-14, base_h, 28,
                 (0, -h/2+base_h/2, 0), mats['black'], root, .5)
    logo_parent = _group('Apple top mark datum', root, (0, h/2, 0))
    apple_mark({'width_mm': spec['top_logo_width_mm'], 'height_mm':spec['top_logo_width_mm']/.8140366730675098,
                'surface_offset_mm': .035},
               {'depth': 0}, mats['logo'], logo_parent)
    # Rear-mark coordinates become a top mark, upright when viewed from the front.
    for obj in logo_parent.children:
        for vertex in obj.data.vertices:
            x,y,z = vertex.co
            vertex.co = (-x, -z, -y)
    inset = None
    if spec['family']=='mac-mini' and not compact:
        cutter = slab('Mac mini rear insert tool',w-24,h-7,1.5,4,(0,0,-d/2+.4),None,root,.05)
        subtract(shell,cutter)
        inset = slab('Mac mini black rear I/O insert',w-24,h-7,.25,4,(0,0,-d/2+.08),mats['black'],root,.05)
    for face, ports in spec.get('ports', {}).items():
        if face=='bottom':
            for i,port in enumerate(ports):
                x=(port['u']-.5)*w;z=(port['v']-.5)*d
                _port(shell,root,mats,f'bottom | {port["type"]} | {i}',(x,-h/2+base_h,z),
                      (port['width_mm'],port['height_mm']),(0,-1,0))
            continue
        if face not in ('front', 'rear'):
            continue
        sign = 1 if face == 'front' else -1
        for i, port in enumerate(ports):
            kind = port['type']
            x = (port['u']-.5)*w*(1 if face == 'front' else -1)
            y = (.5-port['v'])*h
            center = (x, y, sign*d/2)
            if kind == 'led':
                lamp = _cylinder('Power indicator', .65, .08, center, mats['flash'], root, 'Z')
                lamp.location.z += sign*.06*MM
            else:
                _port([shell,inset] if inset and face=='rear' else shell, root, mats, f'{face} | {kind} | {i}', center,
                      (port['width_mm'], port['height_mm']), (0, 0, sign))
    if studio:
        vent=spec['rear_vent']
        _vent('Mac Studio rear exhaust',w*(vent['right']-vent['left']),h*(vent['bottom']-vent['top']),
              (0,h*(.5-(vent['top']+vent['bottom'])/2),-d/2),root,mats,pitch=2.3,shell=shell,perforated=True)
    elif not compact:
        _vent('Mac mini rear exhaust', 75, 8, (0, -h/2+7, -d/2+.05), root, mats, pitch=3.0,shell=[shell,inset])
    return root


def _keyboard(profile, parent, mats, width, depth, base_depth, touchbar, shell):
    """Combined chamfered US keycaps with one label texture, rather than text objects."""
    kw = min(274, width-30)
    row_h = 16.4
    rear = -depth/2+17
    rows = [list('`1234567890-=')+['delete'], ['tab']+list('QWERTYUIOP[]')+['\\'],
            ['caps']+list("ASDFGHJKL;'")+['return'], ['shift']+list('ZXCVBNM,./')+['shift'],
            ['fn','ctrl','option','cmd','space','cmd','option','◀','▲','▼','▶']]
    if not touchbar:
        rows.insert(0, ['esc']+[f'F{i}' for i in range(1,13)]+['◉'])
    else:
        _slab_xz('Touch Bar', kw-4, 8.5, .20, 1.4, (0, base_depth/2-.10, rear+4), mats['black'], parent, .05)
        rear += 13
    total_depth = len(rows)*row_h
    cutter = _slab_xz('Mac keyboard pocket tool', kw+4.2, total_depth+4.2, .8, 3.2,
                      (0,base_depth/2-.1,rear+total_depth/2), None, parent, .02)
    subtract(shell, cutter)
    _slab_xz('Mac keyboard recess', kw+4, total_depth+4, .16, 3,
             (0, base_depth/2-.12, rear+total_depth/2), mats['black'], parent, .03)
    vertices, faces = [], []
    for row_index, labels in enumerate(rows):
        weights = [3.9 if label=='space' else 1.7 if label in ('delete','tab','caps','return','shift')
                   else 1.25 if label in ('cmd','option') else 1 for label in labels]
        unit = kw/sum(weights)
        cursor = -kw/2
        for label, weight in zip(labels, weights):
            x0,x1 = cursor+.9,cursor+weight*unit-.9
            z0,z1 = rear+row_index*row_h+.7,rear+(row_index+1)*row_h-.7
            cursor += weight*unit
            start = len(vertices)
            for inset,y in [(0,base_depth/2-.08),(.23,base_depth/2+.10)]:
                ring = outline(x1-x0-2*inset,z1-z0-2*inset,.9)
                vertices.extend(((x+(x0+x1)/2)*MM,y*MM,(z+(z0+z1)/2)*MM) for x,z in ring)
            count = len(ring)
            faces.extend((start+i,start+(i+1)%count,start+count+(i+1)%count,start+count+i) for i in range(count))
            faces.append(tuple(start+count+i for i in reversed(range(count))))
    neo=profile['apple_mac']['family']=='macbook-neo'
    path = Path(__file__).parent/'textures'/('mac-keyboard-neo.png' if neo else 'mac-keyboard-touchbar.png' if touchbar else 'mac-keyboard-function.png')
    mat = mats['keycap']
    node = mat.node_tree.nodes.new('ShaderNodeTexImage')
    node.image = bpy.data.images.load(str(path), check_existing=True)
    mat.node_tree.links.new(node.outputs['Color'], mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'])
    mesh = bpy.data.meshes.new('Mac keycaps')
    mesh.from_pydata(vertices, [], faces)
    mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='Key labels')
    for face in mesh.polygons:
        for loop in face.loop_indices:
            x,y,z = vertices[mesh.loops[loop].vertex_index]
            uv.data[loop].uv = (x/MM/kw+.5, 1-(z/MM-rear)/total_depth)
    obj = bpy.data.objects.new('Mac keycaps | US layout', mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent


def _laptop(profile, root, mats):
    spec = profile['apple_mac']
    body = profile['body_mm']
    w,lh,ld,bd = body['width'],body['height'],body['depth'],body['base_depth_mm']
    h=body['base_length_mm']
    panels = {}
    for panel in profile['panels']:
        pivot = _group(profile['articulation']['pivots'][panel['name']], root,
                       profile['articulation']['axis_mm'])
        pivot['role'] = 'fold-pivot'
        pivot['panel'] = panel['name']
        pivot['axis'] = 'X'
        axis = profile['articulation']['axis_mm']
        panels[panel['name']] = _group(panel['name'], pivot,
                                      [v-axis[i] for i,v in enumerate(panel['center_mm'])])
    lid,base = panels['Lid'],panels['Base']
    slab('MacBook aluminum lid', w,lh,ld,body['corner_radius'],(0,0,0),mats['rail'],lid,(.35,.2))
    glass = slab('MacBook black cover glass',w-1.1,lh-1.1,.18,body['corner_radius']-.55,
                 (0,0,ld/2+.015),mats['black'],lid,.04)
    apple_mark({'width_mm':spec['top_logo_width_mm'],'height_mm':spec['top_logo_width_mm']/.8140366730675098,
                'surface_offset_mm':.035},
               {'depth':ld},mats['logo'],lid)
    screen = profile['screen']
    sw,sh = screen['fit_box_mm']
    cx,cy = screen['center_mm'][:2]
    contour = list(screen.get('outline_mm') or outline(sw,sh,screen.get('corner_radii_mm',screen['corner_radius_mm'])))
    if sum(x*y1-x1*y for (x,y),(x1,y1) in zip(contour,contour[1:]+contour[:1])) < 0:
        contour.reverse()
    count = len(contour)
    vertices = [((x+cx)*MM,(y+cy)*MM,z*MM)
                for z in (ld/2-.5,ld/2+.5) for x,y in contour]
    faces = [tuple(reversed(range(count))),tuple(range(count,2*count))]
    faces += [(i,(i+1)%count,count+(i+1)%count,count+i) for i in range(count)]
    mesh = bpy.data.meshes.new('Mac display opening tool');mesh.from_pydata(vertices,[],faces);mesh.update()
    cutter = bpy.data.objects.new('Mac display opening tool',mesh)
    bpy.context.scene.collection.objects.link(cutter);cutter.parent=lid
    # A real opening removes nearly coplanar black triangles behind the OLED.
    # This preserves the measured borders without WebGL depth-buffer flicker.
    subtract(glass,cutter)
    slab(screen['object'],1,1,.01,.1,(0,0,0),mats['black'],lid,.002)
    screen['parent_center_mm'] = next(p['center_mm'] for p in profile['panels'] if p['name']=='Lid')
    shell = _slab_xz('MacBook aluminum base',w,h,bd,body['corner_radius'],(0,0,0),mats['back'],base,(.5,.2))
    wedge = spec['shape']=='wedge'
    if wedge:
        for vertex in shell.data.vertices:
            x,y,z = vertex.co/MM
            fraction = (bd/2-z)/bd
            local_depth = .55+(bd-.55)*(y+h/2)/h
            vertex.co.z = (bd/2-fraction*local_depth)*MM
        shell.data.update()
    _keyboard(profile,base,mats,w,h,bd,spec.get('touchbar',False),shell)
    tp_w,tp_h = (159,99) if w>345 else (147,92) if w>335 else (130,81) if spec['family']=='macbook-pro' else (121,79)
    cutter = _slab_xz('Mac trackpad pocket tool',tp_w+1,tp_h+1,.8,3.7,
                      (0,bd/2-.1,h*.25),None,base,.02)
    subtract(shell,cutter)
    _slab_xz('MacBook trackpad pocket floor',tp_w+1,tp_h+1,.10,3.7,
             (0,bd/2-.45,h*.25),mats['black'],base,.02)
    _slab_xz('MacBook glass trackpad',tp_w,tp_h,.20,3.2,
             (0,bd/2-.15,h*.25),mats['trackpad'],base,.05)
    if spec.get('speaker_grilles')=='beside-keyboard':
        strip = (w-min(274,w-30))/2-10
        for sign in (-1,1):
            _vent('MacBook speaker grille',strip,76,(sign*(w/2-5-strip/2),bd/2,-h*.2),
                  base,mats,outward=(0,1,0),pitch=1.2,shell=shell,perforated=True,hole_radius=.18)
    for face,ports in spec.get('ports',{}).items():
        if face not in ('left','right'):continue
        sign = -1 if face=='left' else 1
        for i,port in enumerate(ports):
            z = h/2-port['u']*h
            y = 0
            if wedge:
                thickness = .55+(bd-.55)*port['u']
                y = bd/2-thickness/2
            _port(shell,base,mats,f'{face} | {port["type"]} | {i}',(sign*w/2,y,z),
                  (port['width_mm'],port['height_mm']),(sign,0,0))
    if spec.get('side_speaker_slits'):
        # The right slit has a product close-up. The inferred left slit would
        # overlap two documented USB-C sockets, so do not invent that placement.
        slit=spec['side_speaker_slits']['right']
        u=(slit['u_start']+slit['u_end'])/2
        _port(shell,base,mats,'right speaker slit',(w/2,0,h/2-u*h),
              ((slit['u_end']-slit['u_start'])*h,slit['height_mm']),(1,0,0))
    _slab_xz('MacBook hinge shroud',w*.72,5.2,3.0,1.4,(0,-1.1,spec['hinge_offset_mm']+2.8),mats['black'],root,.2)
    _slab_xz('MacBook opener lip',48,2.2,.25,.9,(0,bd/2+.02,h/2-.6),mats['rail'],base,.08)
    for x in (-w/2+25,w/2-25):
        for z in (-h/2+22,h/2-22):
            if wedge:
                bottom = bd/2-(.55+(bd-.55)*(.5-z/h))
            else:bottom = -bd/2
            _cylinder('MacBook rubber foot',5.5,.45,(x,bottom-.15,z),mats['black'],base)
    sy = screen['center_mm'][1]+screen['fit_box_mm'][1]/2-(spec['camera_below_screen_top_mm'] if spec.get('notch') else -4.2)
    _cylinder('MacBook front camera',1.10,.08,(0,sy,ld/2+.19),mats['black'],lid,'Z')
    if 'bezel_mark' in mats:
        text=bpy.data.curves.new('Legacy MacBook bezel wordmark','FONT')
        text.body='MacBook Air' if spec['family']=='macbook-air' else 'MacBook Pro'
        text.align_x='CENTER';text.align_y='CENTER';text.size=2.6*MM
        mark=bpy.data.objects.new('Legacy MacBook bezel wordmark',text)
        bpy.context.scene.collection.objects.link(mark);mark.parent=lid
        mark.location=(0,(-lh/2+4.2)*MM,(ld/2+.13)*MM)
        text.materials.append(mats['bezel_mark'])
        bpy.ops.object.select_all(action='DESELECT');mark.select_set(True)
        bpy.context.view_layer.objects.active=mark;bpy.ops.object.convert(target='MESH')
    return root


def create_mac_device(profile, root, mats):
    mats['connector'] = material('Mac connector tongue',(.19,.20,.21),.45,.35)
    if profile['apple_mac']['kind']=='pc':
        _desktop(profile,root,mats)
    else:
        _laptop(profile,root,mats)
    # Boolean cuts subdivide a long planar wall into triangles. Smoothing those
    # triangles together with a rounded socket lip produces diagonal reflections
    # across the entire chassis. Keep machined planes flat and fillets smooth.
    for obj in root.children_recursive:
        if obj.type=='MESH':
            obj.data.update()
            for face in obj.data.polygons:
                face.use_smooth=max(abs(v) for v in face.normal)<.9999
    return root
