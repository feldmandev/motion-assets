"""Refresh only branding meshes/materials in existing procedural exports."""
import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
import bpy
sys.path.insert(0,str(Path(__file__).resolve().parent))
from geometry import material, rear_mark, hinge_mark
from build import add_glb_iridescence
BASE=Path(__file__).resolve().parent

def geometry_signature(path):
 raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0];data=json.loads(raw[20:20+length]);binary=raw[28+length:];out={}
 branding_meshes={n.get('mesh') for n in data['nodes'] if any(t in n.get('name','').lower() for t in ('logo','google g'))}
 for mesh_index,mesh in enumerate(data['meshes']):
  if mesh_index in branding_meshes:continue
  name=mesh.get('name','')
  if any(x in name.lower() for x in (' mark ','logo','google g')):continue
  hashes=[]
  for primitive in mesh['primitives']:
   a=data['accessors'][primitive['attributes']['POSITION']];v=data['bufferViews'][a['bufferView']];start=v.get('byteOffset',0)+a.get('byteOffset',0);stride=v.get('byteStride',12)
   positions=b''.join(binary[start+i*stride:start+i*stride+12] for i in range(a['count']))
   hashes.append(hashlib.sha256(positions).hexdigest())
  out[name]=hashes
 return out

def refresh(ident):
 path=BASE/'profiles'/(ident+'.json');profile=json.loads(path.read_text());output=BASE/'exports'/ident
 before=geometry_signature(output/'model.glb')
 bpy.ops.wm.open_mainfile(filepath=str(output/'model.blend'))
 root=bpy.data.objects.get(profile.get('root',profile['name']))
 assert root is not None, ident
 for obj in list(root.children_recursive):
  if not profile.get('asset') and obj.name.startswith(('Samsung logo |','Apple logo |','Google logo |','OnePlus logo |','Device logo |')):bpy.data.objects.remove(obj,do_unlink=True)
 slot=profile.get('material_objects',{}).get('logo','logo');mat=bpy.data.materials.get(slot)
 settings=profile['materials']['logo'] if 'materials' in profile else profile['finishes'][profile['finish']]['logo']
 if mat is None:mat=material(slot,settings['rgb'],settings.get('metal',.5),settings.get('rough',.28))
 shader=mat.node_tree.nodes.get('Principled BSDF');shader.inputs['Base Color'].default_value=tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in settings['rgb'])+(1,)
 shader.inputs['Metallic'].default_value=settings.get('metal',.5);shader.inputs['Roughness'].default_value=settings.get('rough',.28)
 for obj in root.children_recursive:
  if obj.name.startswith('Front Samsung logo |'):
   obj.data.materials.clear();obj.data.materials.append(mat)
 panels=profile.get('panels',[{'name':'Body','body_mm':profile['body_mm'],'rear_logo':profile.get('rear_logo')}])
 for panel in panels:
  logo=panel.get('rear_logo')
  if not logo:continue
  parent=bpy.data.objects.get(panel['name']) or root
  rear_mark(profile,logo,panel['body_mm'],{'logo':mat,'black':mat},parent)
 hinge_mark(profile,{'logo':mat,'black':mat})
 if 'material_objects' in profile:profile['material_objects']['logo']=mat.name
 metadata_path=output/'device.json'
 metadata=json.loads(metadata_path.read_text())
 metadata['material_slots']=profile.get('material_objects',{role:role for role in profile.get('materials',{})})
 metadata['accuracy']=profile['accuracy']
 metadata_path.write_text(json.dumps(metadata,indent=2)+'\n')
 bpy.context.preferences.filepaths.save_version=0
 bpy.ops.wm.save_as_mainfile(filepath=str(output/'model.blend'))
 if profile.get('asset'):
  raw=(output/'model.glb').read_bytes();size=struct.unpack_from('<I',raw,12)[0];data=json.loads(raw[20:20+size])
  target=next(m for m in data['materials'] if m['name']==slot)
  target['pbrMetallicRoughness']['baseColorFactor']=list(shader.inputs['Base Color'].default_value)
  chunk=json.dumps(data,separators=(',',':')).encode();chunk+=b' '*((-len(chunk))%4);tail=raw[20+size:]
  (output/'model.glb').write_bytes(struct.pack('<III',0x46546c67,2,20+len(chunk)+len(tail))+struct.pack('<II',len(chunk),0x4e4f534a)+chunk+tail)
  print('BRANDING FINISHED',ident,'original asset geometry/binary preserved',flush=True)
  return
 # Preserve the export's existing optics, screen maps and articulation.
 for m in bpy.data.materials:
  if not m.use_nodes:continue
  shader=next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'),None);result=next((n for n in m.node_tree.nodes if n.type=='OUTPUT_MATERIAL'),None)
  if shader and result:m.node_tree.links.new(shader.outputs['BSDF'],result.inputs['Surface'])
 bpy.ops.object.select_all(action='DESELECT')
 for obj in [root,*root.children_recursive]:obj.select_set(True)
 bpy.ops.export_scene.gltf(filepath=str(output/'model.glb'),export_format='GLB',use_selection=True,export_extras=True,export_yup=True)
 add_glb_iridescence(output/'model.glb',foldable=bool(profile.get('articulation')))
 after=geometry_signature(output/'model.glb');assert before==after,(ident,'non-brand geometry changed')
 path.write_text(json.dumps(profile,indent=2)+'\n')
 print('BRANDING FINISHED',ident,'non-logo geometry unchanged',flush=True)

if __name__=='__main__':
 args=sys.argv[sys.argv.index('--')+1:]
 for ident in args:refresh(ident)
