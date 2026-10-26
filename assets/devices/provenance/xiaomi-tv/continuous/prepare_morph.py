"""Add an icon pose to the approved remote; keep its physical endpoint unchanged."""
from pathlib import Path
import json, struct, math, array, copy
from PIL import Image

out=Path(__file__).resolve().parent
source=out.parent/'runtime'
raw=(source/'xiaomi-tv-transition.glb').read_bytes()
length=struct.unpack_from('<I',raw,12)[0]
j=json.loads(raw[20:20+length]); binary=bytearray(raw[28+length:])
d=json.loads((source/'xiaomi-tv-transition.json').read_text())
accessors=j['accessors']; views=j['bufferViews']
def read(index):
    a=accessors[index];width={'VEC2':2,'VEC3':3}[a['type']];count=a['count']*width
    start=views[a['bufferView']].get('byteOffset',0)+a.get('byteOffset',0) if 'bufferView' in a else 0
    result=list(struct.unpack_from('<'+'f'*count,binary,start)) if 'bufferView' in a else [0.0]*count
    if 'sparse' in a:
        s=a['sparse'];indices=s['indices'];values=s['values'];fmt={5121:'B',5123:'H',5125:'I'}[indices['componentType']]
        ids=struct.unpack_from('<'+fmt*s['count'],binary,views[indices['bufferView']].get('byteOffset',0)+indices.get('byteOffset',0))
        data=struct.unpack_from('<'+'f'*(s['count']*width),binary,views[values['bufferView']].get('byteOffset',0)+values.get('byteOffset',0))
        for k,i in enumerate(ids):result[i*width:(i+1)*width]=data[k*width:(k+1)*width]
    return result
def append(values,kind):
    while len(binary)%4:binary.append(0)
    start=len(binary);data=array.array('f',values).tobytes();binary.extend(data)
    view=len(views);views.append(dict(buffer=0,byteOffset=start,byteLength=len(data)))
    width={'VEC2':2,'VEC3':3}[kind]
    a=dict(bufferView=view,componentType=5126,count=len(values)//width,type=kind)
    if kind=='VEC3':a.update(min=[min(values[k::3]) for k in range(3)],max=[max(values[k::3]) for k in range(3)])
    accessors.append(a);return len(accessors)-1
remote=[]
for n in j['nodes']:
    if n.get('name','').startswith('Remote /') and 'mesh' in n:
        for p in j['meshes'][n['mesh']]['primitives']:remote.append((n['name'],p))
groups={}
def group(name):
    for term in ('Prime / official','YouTube / official','Netflix / official','Apps / grid'):
        if term in name:return term
    return name
for name,p in remote:
    xyz=read(p['attributes']['POSITION']);g=groups.setdefault(group(name),[[],[]]);g[0].extend(xyz[0::3]);g[1].extend(xyz[2::3])
glyphs={}
for family,selected in [('YouTube',('mark 00','mark 01')),('Apps',('grid','grid.001','grid.003','grid.004'))]:
    positions=[read(p['attributes']['POSITION']) for name,p in remote if name.startswith('Remote / '+family+' /') and name.endswith(selected)]
    xs=[v for xyz in positions for v in xyz[0::3]];zs=[v for xyz in positions for v in xyz[2::3]]
    glyphs[family]=((min(xs)+max(xs))/2,(min(zs)+max(zs))/2)
wide=17.4*32/80/3.55
accent_materials={}
for name,p in remote:
    if name.endswith('/ shortcut'):
        material=copy.deepcopy(j['materials'][p['material']])
        material['name']+=' / icon '+name.split('/')[1].strip()
        p['material']=len(j['materials']);j['materials'].append(material)
        accent_materials[p['material']]={'Netflix':[.76,.22,.26],'Prime':[.28,.57,.76],
            'YouTube':[.83,.86,.90],'Apps':[.62,.67,.73]}[name.split('/')[1].strip()]
for name,p in remote:
    xyz=read(p['attributes']['POSITION']);normal=read(p['attributes']['NORMAL'])
    xs,zs=groups[group(name)];cx=(min(xs)+max(xs))/2;cz=(min(zs)+max(zs))/2
    body=any(s in name for s in ('continuous curved housing','horizontal shell joint','battery cover','IR cap','shortcut','Volume / rocker'))
    scale=wide if body else 1.35 if 'D-pad' in name or 'official' in name else 1.15
    ink=any(term in name for term in ('official','authentic symbol','filled symbol','rounded plus','rounded minus','legend','grid','TV+ /','subtle brand','Microphone /'))
    layer=4 if ink else 2
    if 'continuous curved housing' in name or 'battery cover' in name or 'horizontal shell' in name:layer=0
    if 'dark recess' in name:layer=1
    if 'D-pad / OK' in name:layer=3
    if 'YouTube / official mark 00' in name:layer=3
    if 'YouTube / official mark 01' in name:layer=5
    hidden=any(term in name for term in ('Prime / official','Netflix / official','Apps / legend',
        'TV+ /','subtle brand','horizontal shell joint','battery cover seam','IR cap'))
    if 'YouTube / official mark' in name and not name.endswith(('mark 00','mark 01')):hidden=True
    if 'Apps / grid' in name and name not in ('Remote / Apps / grid','Remote / Apps / grid.001','Remote / Apps / grid.003','Remote / Apps / grid.004'):hidden=True
    halfx=(max(xs)-min(xs))*scale/2;halfz=(max(zs)-min(zs))*(1 if body else scale)/2
    radius=min(halfx,halfz,.48 if 'shortcut' in name else 1.45)
    flat=[];normals=[];uv=[]
    for i in range(0,len(xyz),3):
        x,y,z=xyz[i:i+3]
        tx=cx*wide+(x-cx)*scale;tz=cz+(z-cz)*(1 if body else scale)
        for family in ('YouTube','Apps'):
            if name.startswith('Remote / '+family+' /') and ('official' in name or 'grid' in name):
                gx,gz=glyphs[family];bx,bz=groups['Remote / '+family+' / shortcut']
                tx=(min(bx)+max(bx))/2*wide+(x-gx)*scale
                tz=(min(bz)+max(bz))/2+(z-gz)*scale
        if 'continuous curved housing' in name or 'shortcut' in name:
            dx=tx-cx*wide;dz=tz-cz
            qx=max(abs(dx)-(halfx-radius),0);qz=max(abs(dz)-(halfz-radius),0);distance=math.hypot(qx,qz)
            if distance>radius:
                tx=cx*wide+math.copysign(halfx-radius+qx*radius/distance,dx)
                tz=cz+math.copysign(halfz-radius+qz*radius/distance,dz)
        if hidden:tx=cx*wide;tz=cz
        flat.extend((tx-x,.75+layer*.06+y*.02-y,tz-z))
        # The icon is unlit; interpolate its front-facing normal with the original.
        normals.extend((-normal[i],1-normal[i+1],-normal[i+2]))
        uv.extend((x/3.55+.5,-z/17.4+.5))
    p['targets']=[{'POSITION':append(flat,'VEC3'),'NORMAL':append(normals,'VEC3')}]
    p['attributes']['TEXCOORD_0']=append(uv,'VEC2')
    mesh=next(m for m in j['meshes'] if p in m['primitives']);mesh['weights']=[1];mesh.setdefault('extras',{})['targetNames']=['Icon']

# Bring the connected TV closer. Keep the stick/connector mesh sizes unchanged.
tvscale=.65;oldcenter=[0,1.45,-120];newcenter=[0,1.45,-70]
for n in j['nodes']:
    name=n.get('name','')
    if 'mesh' not in n or not name.startswith(('Television /','Connector /')):continue
    for p in j['meshes'][n['mesh']]['primitives']:
        pos=read(p['attributes']['POSITION'])
        if name.startswith('Television /'):
            pos=[newcenter[k%3]+(v-oldcenter[k%3])*tvscale for k,v in enumerate(pos)]
        else:
            shift=[36*(1-tvscale),13*(1-tvscale),50+1.33*(1-tvscale)]
            pos=[v+shift[k%3] for k,v in enumerate(pos)]
        p['attributes']['POSITION']=append(pos,'VEC3')
        for target in p.get('targets',[]):
            target['POSITION']=append([v*tvscale for v in read(target['POSITION'])],'VEC3')
d.update(introDuration=1.15,iconBounds=[38,14,32,80],near=5,screenHeight=d['screenHeight']*tvscale,
         screenWidth=d['screenWidth']*tvscale,outerWidth=72*tvscale,widthTargetDelta=72*tvscale,
         screenCenter=[0,70-.72*tvscale,1.45],remoteBodyHeight=17.4)
end_y=d['screenCenter'][1]-d['screenHeight']/(2*(18/45/d['sourceAspect']))
for i,f in enumerate(d['frames']):
    if i>=92:
        t=max(0,min(1,(i-92)/112));f[1]=(2*t**3-3*t*t+1)*-24+(t**3-2*t*t+t)*(.6*112)+(-2*t**3+3*t*t)*end_y
    f[5:8]=[1,1,1]
height=2*(66.45-.85)*(18/55/d['sourceAspect']);w=6.96/(height*d['sourceAspect']);h=17.4/height
d['remoteRect']=[.5-w/2,.5-h/2,w,h]
def srgb(v):return 12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055
material_ids=sorted({p['material'] for _,p in remote});d['iconMaterials']=[]
for index in material_ids:
    m=j['materials'][index];pbr=m.get('pbrMetallicRoughness',{});rgb=[srgb(v) for v in pbr.get('baseColorFactor',[1,1,1])[:3]]
    body='Front face' in m['name'] or 'Graphite | soft ABS' in m['name']
    colors=[[.055,.075,.095],[.26,.30,.34],[.22,.26,.30],[.055,.075,.095]] if body else [rgb]*4
    if index in accent_materials:colors=[accent_materials[index]]*4
    record=dict(name=m['name'],finish=rgb,colors=colors,offsets=[0,.43,.64,1],metal=pbr.get('metallicFactor',1),rough=pbr.get('roughnessFactor',1),gradient=f'icon-gradient-{index}.png')
    d['iconMaterials'].append(record)
    image=Image.new('RGB',(256,4))
    for x in range(256):
        t=x/255;k=next((k for k in range(3) if t<=record['offsets'][k+1]),2);a=record['offsets'][k];b=record['offsets'][k+1];u=(t-a)/(b-a)
        color=tuple(round(255*(colors[k][c]+(colors[k+1][c]-colors[k][c])*u)) for c in range(3))
        for y in range(4):image.putpixel((x,y),color)
    image.save(out/record['gradient'])
j['buffers'][0]['byteLength']=len(binary)
payload=json.dumps(j,separators=(',',':')).encode();payload+=b' '*((-len(payload))%4);binary+=b'\0'*((-len(binary))%4)
glb=struct.pack('<III',0x46546c67,2,28+len(payload)+len(binary))+struct.pack('<II',len(payload),0x4e4f534a)+payload+struct.pack('<II',len(binary),0x004e4942)+binary
(out/'xiaomi-tv-transition.glb').write_bytes(glb);(out/'xiaomi-tv-transition.json').write_text(json.dumps(d,separators=(',',':')))
print('Prepared continuous icon geometry; remote physical POSITION accessors unchanged.',len(glb),flush=True)
