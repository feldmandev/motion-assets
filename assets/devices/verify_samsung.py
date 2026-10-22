"""Check Samsung export structure, native screen aspect, and camera clearance."""
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path(__file__).resolve().parent

def verify(path):
 p=json.loads(path.read_text());out=BASE/'exports'/p['id'];meta=json.loads((out/'device.json').read_text());body=p['body_mm'];camera=p['camera']
 for axis in ('width','height','depth'):
  assert abs(meta['body_mm'][axis]-body[axis])<1e-6,(p['id'],axis)
 screen=meta['screens'][0];w,h=screen['size_mm'];px,py=screen['resolution']
 assert abs(w/h-px/py)<1e-6,p['id']
 assert w<body['width'] and h<body['height'],p['id']
 windows=camera['windows'];ring=camera.get('lens_ring_mm',0)
 for i,(x,y,ww,wh,rr) in enumerate(windows):
  assert abs(x)+ww/2+ring<body['width']/2,(p['id'],'camera x',i)
  assert abs(y)+wh/2+ring<body['height']/2,(p['id'],'camera y',i)
  for j,(xx,yy,www,hhh,_) in enumerate(windows[:i]):
   assert math.hypot(x-xx,y-yy)>(ww+www)/2+2*ring,(p['id'],'camera overlap',i,j)
  for fx,fy,fr in camera.get('flash',[]):
   assert math.hypot(x-fx,y-fy)>ww/2+ring+fr,(p['id'],'flash collision',i)
 raw=(out/'model.glb').read_bytes();magic,version,length=struct.unpack_from('<III',raw)
 assert magic==0x46546c67 and version==2 and length==len(raw),p['id']
 size=struct.unpack_from('<I',raw,12)[0];gltf=json.loads(raw[20:20+size]);names=[n.get('name','') for n in gltf['nodes']]
 if ring:
  for i in range(len(windows)):
   node=next(n for n in gltf['nodes'] if n.get('name')==f'Camera lens rim {i}')
   bounds=gltf['accessors'][gltf['meshes'][node['mesh']]['primitives'][0]['attributes']['POSITION']]
   inner=node.get('translation',[0,0,0])[1]+bounds['max'][1]
   surface=-body['depth']/2-(0 if i in camera.get('body_windows',[]) else camera['bump_mm'])
   assert inner>=surface*.001-1e-7,(p['id'],'floating lens rim',i)
 if p.get('rear_logo',{}).get('kind')=='samsung':assert sum(n.startswith('Samsung logo |') for n in names)==7,p['id']
 ET.parse(out/'frame.svg')
 for name in ('rear','rear-angle','front','side','end'):
  assert (out/f'{name}.png').is_file(),(p['id'],'missing review',name)
 for index in range(len(p.get('finishes',{}))):
  assert (out/f'finish-{index}.png').is_file(),(p['id'],'missing finish',index)
 return {'id':p['id'],'checks':'body dimensions, native screen aspect, lens/flash clearance, exported lens rim seating, wordmark nodes when specified, GLB structure, SVG XML, review and finish images'}

if __name__=='__main__':
 results=[verify(p) for p in sorted((BASE/'profiles').glob('galaxy-*.json')) if (BASE/'exports'/p.stem/'model.glb').exists()]
 (BASE/'samsung-verification.json').write_text(json.dumps(results,indent=2));print('Passed',len(results),'Samsung models')
