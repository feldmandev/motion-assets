"""Check actual exported Mac envelopes, socket inventory, native display UVs and hinge endpoints."""
import argparse
import json
from pathlib import Path
import struct
import xml.etree.ElementTree as ET

import numpy as np
from shapely.geometry import Point, Polygon

BASE=Path(__file__).resolve().parent
TYPES={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
DTYPES={5126:'<f4',5125:'<u4',5123:'<u2',5121:'u1',5122:'<i2',5120:'i1'}


def quat_matrix(q):
    x,y,z,w=q
    return np.array([[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w),0],
                     [2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w),0],
                     [2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y),0],[0,0,0,1]],dtype=float)


def verify(path):
    profile=json.loads(path.read_text())
    output=BASE/'exports'/path.stem
    meta=json.loads((output/'device.json').read_text())
    raw=(output/'model.glb').read_bytes()
    length=struct.unpack_from('<I',raw,12)[0]
    gltf=json.loads(raw[20:20+length]);binary=28+length
    def accessor(index):
        item=gltf['accessors'][index];view=gltf['bufferViews'][item['bufferView']]
        dtype=np.dtype(DTYPES[item['componentType']]);n=TYPES[item['type']]
        offset=binary+view.get('byteOffset',0)+item.get('byteOffset',0)
        return np.ndarray((item['count'],n),dtype=dtype,buffer=raw,offset=offset,
                          strides=(view.get('byteStride',n*dtype.itemsize),dtype.itemsize)).copy()
    parents={child:i for i,node in enumerate(gltf['nodes']) for child in node.get('children',[])}
    def world(index,rotations=None):
        node=gltf['nodes'][index]
        if 'matrix' in node:m=np.array(node['matrix']).reshape(4,4).T
        else:
            m=quat_matrix((rotations or {}).get(index,node.get('rotation',[0,0,0,1])))
            m[:3,:3]=m[:3,:3]@np.diag(node.get('scale',[1,1,1]));m[:3,3]=node.get('translation',[0,0,0])
        return world(parents[index],rotations)@m if index in parents else m
    def points(index,rotations=None):
        node=gltf['nodes'][index];values=[]
        for primitive in gltf['meshes'][node['mesh']]['primitives']:
            array=accessor(primitive['attributes']['POSITION'])
            values.extend((world(index,rotations)@np.c_[array,np.ones(len(array))].T).T[:,:3])
        # Blender millimetres: glTF stores X right, Y front, Z down.
        result=np.array(values)*1000
        return result[:,[0,2,1]]*np.array([1,-1,1])
    named={node.get('name'):i for i,node in enumerate(gltf['nodes'])}
    count=0
    for mesh in gltf['meshes']:
        for primitive in mesh['primitives']:
            for key,index in primitive['attributes'].items():
                array=accessor(index)
                assert np.isfinite(array).all(),(path.stem,'nonfinite',key)
                if key=='POSITION':
                    assert np.abs(array).max()<2,(path.stem,'corrupt position bounds')
                    count+=len(array)
    spec=profile['apple_mac'];dims=spec['dimensions_mm']
    expected_ports=sum(p['type']!='led' for ports in spec['ports'].values() for p in ports)
    if spec.get('side_speaker_slits'):expected_ports+=1
    wells=[name for name in named if name and name.startswith('Port well | ')]
    assert len(wells)==expected_ports,(path.stem,'socket inventory',len(wells),expected_ports)
    marks=[name for name in named if name and name.startswith('Apple logo | ')]
    assert len(marks)==2,(path.stem,'Apple contour/leaf count',marks)
    logo=np.concatenate([points(named[name]) for name in marks])
    logo_axes=[0,2] if spec['kind']=='pc' else [0,1]
    logo_size=np.ptp(logo[:,logo_axes],axis=0)
    logo_aspect=float(logo_size[0]/logo_size[1])
    assert abs(logo_aspect-.8140366730675098)<.001,(path.stem,'Apple mark flattened',logo_aspect)
    result={'finite_position_vertices':count,'sockets':len(wells),'apple_mark_parts':len(marks),
            'apple_mark_aspect':logo_aspect}
    if spec['kind']=='pc':
        enclosure=points(named['Mac aluminum enclosure'])
        foot_name='Mac mini recessed circular foot' if dims['width']<150 else 'Mac rubber bottom foot'
        if spec['family']=='mac-studio':foot_name='Mac Studio circular bottom foot'
        foot=points(named[foot_name])
        total=np.r_[enclosure,foot]
        if spec['family']=='mac-studio':
            total=np.r_[total,points(named['Mac Studio perforated bottom intake'])]
        actual=np.ptp(total,axis=0)
        expected=np.array([dims['width'],dims['height'],dims['depth']])
        error=float(np.max(np.abs(actual-expected)))
        assert error<.08,(path.stem,'desktop external envelope',actual,expected)
        assert meta['screens']==[] and meta['screen'] is None
        normal_error=0.0;planar_triangles=0
        shell_index=named['Mac aluminum enclosure'];matrix=world(shell_index)
        for primitive in gltf['meshes'][gltf['nodes'][shell_index]['mesh']]['primitives']:
            positions=accessor(primitive['attributes']['POSITION'])
            xyz=(matrix@np.c_[positions,np.ones(len(positions))].T).T[:,:3]*1000
            xyz=xyz[:,[0,2,1]]*np.array([1,-1,1])
            normals=(np.linalg.inv(matrix[:3,:3]).T@accessor(primitive['attributes']['NORMAL']).T).T
            normals=normals[:,[0,2,1]]*np.array([1,-1,1])
            for triangle in accessor(primitive['indices']).reshape(-1,3):
                face=xyz[triangle]
                if np.max(np.abs(face[:,2]-dims['depth']/2))<.002:
                    planar_triangles+=1
                    normal_error=max(normal_error,float(np.max(np.abs(normals[triangle]-np.array([0,0,1])))))
        assert planar_triangles and normal_error<.002,(path.stem,'planar socket-wall shading',normal_error)
        result.update(enclosure_xyz_mm=actual.tolist(),envelope_error_mm=error,
                      flat_front_triangles=planar_triangles,flat_front_normal_error=normal_error)
        return result
    screen_spec=profile['screen'];screen=meta['screens'][0]
    assert screen['resolution']==screen_spec['resolution']
    ratio=screen['resolution'][0]/screen['resolution'][1]
    assert abs(screen['size_mm'][0]/screen['size_mm'][1]-ratio)<1e-10
    screen_index=named[screen['node']]
    primitives=gltf['meshes'][gltf['nodes'][screen_index]['mesh']]['primitives']
    for primitive in primitives:
        uv=accessor(primitive['attributes']['TEXCOORD_0'])
        assert np.max(np.abs(uv.min(axis=0)))<.0001
        assert np.max(np.abs(uv.max(axis=0)-1))<.0001
        if spec.get('notch'):
            # glTF reverses Blender's V: the top edge has V=0.
            probe=np.array([.5,spec['display']['notch_height_mm']/screen['size_mm'][1]/2])
            indices=accessor(primitive['indices']).reshape(-1,3)
            for triangle in indices:
                assert not Polygon(uv[triangle]).contains(Point(probe)),(path.stem,'OLED fills camera notch')
    animation=next(a for a in gltf.get('animations',[]) if a.get('name')=='Fold')
    rotations={}
    for channel in animation['channels']:
        if channel['target']['path']=='rotation':
            rotations[channel['target']['node']]=accessor(animation['samplers'][channel['sampler']]['output'])[-1]
    closed=points(screen_index,rotations)
    assert np.ptp(closed[:,1])<.02,(path.stem,'closed display not horizontal')
    top_key=max(points(index)[:,1].max() for name,index in named.items() if name and name.startswith('Mac keycaps |'))
    gap=float(closed[:,1].min()-top_key)
    assert gap>.15,(path.stem,'closed OLED collides with keyboard',gap)
    lid=points(named['MacBook aluminum lid'])
    assert abs(np.ptp(lid[:,0])-dims['width'])<.02
    assert abs(np.ptp(lid[:,1])-spec['lid_height_mm'])<.02
    base=points(named['MacBook aluminum base'])
    assert abs(np.ptp(base[:,0])-dims['width'])<.02
    assert abs(np.ptp(base[:,2])-dims['depth'])<.02
    closed_lid=points(named['MacBook aluminum lid'],rotations)
    assert abs(closed_lid[:,2].max()-base[:,2].max())<.03,(path.stem,'closed front edges misalign')
    shroud=points(named['MacBook hinge shroud'])
    hinge_gap=float(closed_lid[:,1].min()-shroud[:,1].max())
    assert hinge_gap>.15,(path.stem,'closed lid intersects hinge shroud',hinge_gap)
    actual_screen=points(screen_index)
    top_bezel=float(lid[:,1].max()-actual_screen[:,1].max())
    bottom_bezel=float(actual_screen[:,1].min()-lid[:,1].min())
    expected_top=profile['body_mm']['height']/2-screen_spec['center_mm'][1]-screen['size_mm'][1]/2
    assert abs(top_bezel-expected_top)<.02,(path.stem,'front top border differs from profile')
    assert min(top_bezel,bottom_bezel)>0
    frame=ET.fromstring((output/'frame.svg').read_bytes())
    assert frame.tag.endswith('svg')
    left,top,fw,fh=screen['frame_bounds_mm']
    assert min(left,top)>0 and left+fw<dims['width'] and top+fh<spec['lid_height_mm'],(path.stem,'frame opening outside lid')
    if spec.get('notch'):
        opening=next(node for node in frame.iter() if node.tag.endswith('polygon') and node.attrib.get('fill')=='black')
        polygon=Polygon([tuple(map(float,point.split(','))) for point in opening.attrib['points'].split()])
        bounds=screen['frame_bounds_mm']
        assert not polygon.contains(Point(bounds[0]+bounds[2]/2,bounds[1]+spec['display']['notch_height_mm']/2))
    result.update(native_aspect_error=abs(screen['size_mm'][0]/screen['size_mm'][1]-ratio),
                  uv_full_extent=True,notch_geometry_checked=bool(spec.get('notch')),
                  closed_screen_keyboard_clearance_mm=gap,fold_clip=True,
                  lid_height_mm=float(np.ptp(lid[:,1])),top_bezel_mm=top_bezel,bottom_bezel_mm=bottom_bezel,
                  published_base_footprint_preserved=True,closed_front_edges_aligned=True,
                  closed_lid_hinge_clearance_mm=hinge_gap)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('ids',nargs='*');args=parser.parse_args()
    paths=[BASE/'profiles'/f'{pid}.json' for pid in args.ids] if args.ids else sorted((BASE/'profiles').glob('mac*.json'))
    report={'passed':0,'failures':[],'models':{}}
    for path in paths:
        try:
            report['models'][path.stem]=verify(path);report['passed']+=1;print('PASS',path.stem,flush=True)
        except Exception as error:
            report['failures'].append({'id':path.stem,'error':repr(error)});print('FAIL',path.stem,repr(error),flush=True)
    (BASE/'research/mac-model-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print('RESULT',report['passed'],'passed',len(report['failures']),'failed')
    if report['failures']:raise SystemExit(1)


if __name__=='__main__':main()
