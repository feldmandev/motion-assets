"""Focused checks on exported geometry, pixel aspect and optical clearances."""
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent

LEGACY_EXPECTED = {
    'pixel-4': {'body': [147.1, 68.8, 8.2], 'resolution': [1080, 2280], 'lenses': 2,
                'screen_cutouts': 0, 'fingerprint': False},
    'pixel-4-xl': {'body': [160.4, 75.1, 8.2], 'resolution': [1440, 3040], 'lenses': 2,
                   'screen_cutouts': 0, 'fingerprint': False},
    'pixel-4a-5g': {'body': [153.9, 74.0, 8.2], 'resolution': [1080, 2340], 'lenses': 2,
                    'screen_cutouts': 1, 'fingerprint': True},
    'pixel-4a': {'body': [144.0, 69.4, 8.2], 'resolution': [1080, 2340], 'lenses': 1,
                 'screen_cutouts': 1, 'fingerprint': True},
    'pixel-5': {'body': [144.7, 70.4, 8.0], 'resolution': [1080, 2340], 'lenses': 2,
                'screen_cutouts': 1, 'fingerprint': True},
    'pixel-5a': {'body': [156.2, 73.2, 8.8], 'resolution': [1080, 2400], 'lenses': 2,
                 'screen_cutouts': 1, 'fingerprint': True},
}


def rounded_distance(point, rectangle):
    x, y, width, height, radius = rectangle
    qx = abs(point[0]-x)-(width/2-radius)
    qy = abs(point[1]-y)-(height/2-radius)
    return math.hypot(max(qx,0),max(qy,0))+min(max(qx,qy),0)-radius


def verify(profile_path):
    profile = json.loads(profile_path.read_text())
    output = BASE/'exports'/profile_path.stem
    metadata = json.loads((output/'device.json').read_text())
    raw = (output/'model.glb').read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    assert magic == 0x46546c67 and version == 2 and length == len(raw)
    size, chunk_type = struct.unpack_from('<II',raw,12)
    gltf = json.loads(raw[20:20+size])
    binary_offset = 28+size
    legacy = LEGACY_EXPECTED.get(profile['id'])
    if profile['id'].startswith('iphone-duo-'):
        expected_body = [117.8, 164.6, 5.2] if profile['id'].endswith('-unfolded') else [117.8, 84.1, 11.3]
        body = profile['body_mm']
        assert [body[k] for k in ('height','width','depth')] == expected_body
        assert any(panel.get('rear_logo', {}).get('kind') == 'apple' for panel in profile['panels'])
        cover = next(screen for screen in profile['screens'] if screen['node'] == 'Cover screen')
        assert cover['resolution'] == [1398, 2034]
        cover_camera = cover['cutouts'][0]
        assert 'size_mm' not in cover_camera and abs(cover_camera['radius_mm']-3.0) < 1e-8
        camera = next(panel['camera'] for panel in profile['panels'] if 'camera' in panel)
        assert camera.get('integrated_plateau') is True
        assert abs(camera['bump_mm']-1.65) < 1e-8
        assert abs(camera['bump_mm']+camera['optical_bump_mm']-2.25) < 1e-8
        microphone = next(item for item in camera['sensors'] if isinstance(item, dict)
                          and item.get('kind') == 'microphone')
        assert microphone['size_mm'][0] > microphone['size_mm'][1]
        # The .8 mm metal ring extends .7 mm toward the body from the optical plane.  Keeping the
        # optical rise below that guarantees the ring physically overlaps/seats into the plateau.
        assert 0 < camera['optical_bump_mm'] < .7, 'Duo lens ring no longer seats in camera plateau'
        if profile['id'].endswith('-unfolded'):
            inner = next(screen for screen in profile['screens'] if screen['node'] == 'Inner screen')
            assert inner['resolution'] == [2670, 1878] and not inner['cutouts']
    if legacy:
        body = profile['body_mm']
        assert [body[k] for k in ('height', 'width', 'depth')] == legacy['body']
        assert profile['screen']['resolution'] == legacy['resolution']
        assert len(profile['screen']['cutouts']) == legacy['screen_cutouts']
        assert len(profile['camera']['lenses']) == legacy['lenses']
        assert {button['name'] for button in profile.get('buttons', [])} == {'Power', 'Volume'}
        has_fingerprint = any(item.get('name') == 'Rear fingerprint'
                              for item in profile.get('rear_details', []))
        assert has_fingerprint == legacy['fingerprint']
    triangles = sum(gltf['accessors'][item['indices']]['count']//3
                    for mesh in gltf['meshes'] for item in mesh['primitives'])
    if legacy:
        names = {node.get('name') for node in gltf['nodes']}
        assert {'Power', 'Volume'} <= names
        assert ('Rear fingerprint' in names) == legacy['fingerprint']
        if profile['id'] in ('pixel-4', 'pixel-4-xl'):
            assert sum(name is not None and name.startswith('Inner bezel selfie camera')
                       for name in names) == len(profile['bezel_cameras'])
    for index, node in enumerate(gltf['nodes']):
        if not (node.get('name','').startswith('Aluminum enclosure') or node.get('name') == 'Body | aluminum enclosure'):
            continue
        parent = next(parent for parent in gltf['nodes'] if index in parent.get('children',[]))
        expected = next((panel['body_mm'] for panel in profile.get('panels',[]) if panel['name']==parent['name']),profile['body_mm'])
        primitive = gltf['meshes'][node['mesh']]['primitives'][0]
        bounds = gltf['accessors'][primitive['attributes']['POSITION']]
        for axis, dimension in [(0,'width'),(2,'height')]:
            assert abs(bounds['max'][axis]-bounds['min'][axis]-expected[dimension]*.001)<1e-6
        assert abs(bounds['max'][1]-bounds['min'][1]-(expected['depth']-.05)*.001)<1e-6
    profile_screens = profile.get('screens', [profile['screen']] if 'screen' in profile else [])
    for screen_index, screen in enumerate(metadata['screens']):
        w, h = screen['size_mm']; px, py = screen['resolution']
        assert screen['resolution'] == profile_screens[screen_index]['resolution'], 'Native resolution changed'
        assert abs(w/h-px/py) < 1e-10
        if 'Fold' in profile['name'] and screen['node'] == 'Cover screen':
            assert px < py and h > w, (profile['id'], 'cover screen must be portrait')
            assert h > profile['body_mm']['height']*.9, (profile['id'], 'cover screen shrunk')
        frame = ET.parse(output/screen.get('frame_file','frame.svg')).getroot()
        if screen.get('frame_screen_px'):
            # Google emulator artwork frame: the screen rectangle must be transparent and its
            # aspect must equal the panel resolution.
            from PIL import Image
            png = Image.open(output/(Path(screen.get('frame_file','frame.svg')).stem+'.png'))
            sx, sy, sw, sh = screen['frame_screen_px']
            assert (sw, sh) == tuple(screen['resolution']) or (sh, sw) == tuple(screen['resolution'])
            assert png.getpixel((sx+sw//2, sy+sh//2))[3] == 0, 'Screen opening must be transparent'
            assert png.getpixel((sx-2, sy+sh//2))[3] == 255, 'Bezel must be opaque'
            fw, fh = map(float, frame.attrib['viewBox'].split()[2:])
            assert (fw, fh) == png.size
            if profile.get('state')=='unfolded' and screen['node']=='Cover screen':
                assert fw < fh, 'Cover frame must be the closed device'
        else:
            paths = frame.findall('{http://www.w3.org/2000/svg}path')
            assert len(paths)==2 and '--device-color:' in paths[0].attrib['style'], 'Missing colored rail / inner black bezel'
            frame_w, frame_h = map(float,frame.attrib['viewBox'].split()[2:])
            expected_frame = screen.get('frame_body_mm',profile['body_mm'])
            assert abs(frame_w-expected_frame['width'])<1e-8
            assert abs(frame_h-expected_frame['height'])<1e-8
            if profile.get('state')=='unfolded' and screen['node']=='Cover screen':
                assert frame_w < profile['body_mm']['width']*.6, 'Cover frame includes the other half'
        node_names = screen.get('nodes') or [screen['node']]
        widths = []
        for node_name in node_names:
            node = next(node for node in gltf['nodes'] if node.get('name') == node_name)
            primitive = gltf['meshes'][node['mesh']]['primitives'][0]
            bounds = gltf['accessors'][primitive['attributes']['POSITION']]
            widths.append(bounds['max'][0]-bounds['min'][0])
            # GLB Y-up: display height is exported along Z, curvature along Y.
            assert abs(bounds['max'][2]-bounds['min'][2]-h*.001) < 1e-6
            assert 'TEXCOORD_0' in primitive['attributes']
            if len(node_names) == 1:
                values = []
                for attribute, components in [('POSITION',3), ('TEXCOORD_0',2)]:
                    accessor = gltf['accessors'][primitive['attributes'][attribute]]
                    view = gltf['bufferViews'][accessor['bufferView']]
                    start = binary_offset+view.get('byteOffset',0)+accessor.get('byteOffset',0)
                    values.append([struct.unpack_from('<'+'f'*components,raw,start+i*view.get('byteStride',components*4))
                                   for i in range(accessor['count'])])
                positions, uvs = values
                assert len(positions) == len(uvs)
                for (x,_,z),(u,v) in zip(positions,uvs):
                    assert abs(u-(x-bounds['min'][0])/(w*.001)) < 1e-5, 'Screen U mapping stretched'
                    assert abs(v-(z-bounds['min'][2])/(h*.001)) < 1e-5, 'Screen V mapping stretched'
        if len(node_names) == 1:
            assert abs(widths[0]-w*.001) < 1e-6
        else:
            assert abs(sum(widths)-w*.001) < 1e-6, (profile['id'], 'split screen width changed', widths, w)
    if 'panels' not in profile:
        body = metadata['body_mm']; screen = metadata['screens'][0]
        trace_path = BASE/'research'/'skins'/profile['id']/'trace.json'
        trace = json.loads(trace_path.read_text()) if trace_path.exists() else None
        if trace and 'derived_from' not in trace:
            from shapely.geometry import MultiPoint, Polygon
            points = trace['body_outline_mm']
            xs, ys = [p[0] for p in points], [p[1] for p in points]
            cx, cy = (min(xs)+max(xs))/2, (min(ys)+max(ys))/2
            expected = Polygon([((x-cx)*body['width']/(max(xs)-min(xs)),
                                 (y-cy)*body['height']/(max(ys)-min(ys))) for x,y in points]).convex_hull
            enclosure_name = 'Body | aluminum enclosure' if profile.get('asset') else 'Aluminum enclosure'
            node = next(node for node in gltf['nodes'] if node.get('name') == enclosure_name)
            primitive = gltf['meshes'][node['mesh']]['primitives'][0]
            accessor = gltf['accessors'][primitive['attributes']['POSITION']]
            view = gltf['bufferViews'][accessor['bufferView']]
            start = binary_offset+view.get('byteOffset',0)+accessor.get('byteOffset',0)
            vertices = [struct.unpack_from('<fff',raw,start+i*view.get('byteStride',12))
                        for i in range(accessor['count'])]
            actual = MultiPoint([(x*1000,-z*1000) for x,_,z in vertices]).convex_hull
            # The convex envelope excludes subpixel rail notches. Allow 0.10 mm for the
            # 320-point perimeter resampling and float32 export, not a different corner shape.
            error = actual.exterior.hausdorff_distance(expected.exterior)
            assert error < .10, (profile['id'], 'enclosure differs from official contour (mm)', error)
        else:
            # Without a traced chassis, retain the display-plus-bezel fallback check.
            w, h = screen['size_mm']; cx, cy = screen['center_mm'][:2]
            left = body['width']/2 + cx - w/2
            right = body['width']/2 - cx - w/2
            top = body['height']/2 - cy - h/2
            bottom = body['height']/2 + cy - h/2
            radius = screen['corner_radius_mm']
            limit = min(body['width'], body['height'])/2
            expected = [min(limit, radius+bezel) for bezel in
                        [min(right,bottom), min(right,top), min(left,top), min(left,bottom)]]
            actual = body.get('corner_radii_mm', [body['corner_radius']]*4)
            assert max(abs(a-b) for a,b in zip(actual, expected)) < 1e-8, (
                profile['id'], 'body corners do not follow display + bezel', actual, expected)
    if profile.get('articulation'):
        articulation = profile['articulation']
        assert metadata.get('articulation') == articulation
        node_indices = {node.get('name'): index for index, node in enumerate(gltf['nodes'])}
        for panel, pivot in articulation['pivots'].items():
            assert pivot in node_indices, (profile['id'], 'missing fold pivot', panel, pivot)
            extras = gltf['nodes'][node_indices[pivot]].get('extras', {})
            assert extras.get('role') == 'fold-pivot' and extras.get('panel') == panel
        moving_index = node_indices[articulation['pivots'][articulation['moving_panel']]]
        animation = next((item for item in gltf.get('animations', [])
                          if item.get('name') == articulation['animation']), None)
        assert animation is not None, (profile['id'], 'missing Fold animation')
        channels = [channel for channel in animation['channels']
                    if channel['target'].get('node') == moving_index and channel['target'].get('path') == 'rotation']
        assert channels, (profile['id'], 'Fold animation does not rotate moving pivot')
        spine_index = node_indices['Fold pivot | Hinge spine']
        spine_channels = {channel['target']['path'] for channel in animation['channels']
                          if channel['target'].get('node') == spine_index}
        assert {'translation','rotation','scale'} <= spine_channels, (profile['id'], 'hinge spine is static')
        assert abs(profile['hinge']['spine_width_mm']-articulation['closed_body_mm']['depth'])<1e-8
        scale_channel = next(channel for channel in animation['channels']
                             if channel['target'].get('node') == spine_index and channel['target']['path']=='scale')
        scale_accessor = gltf['accessors'][animation['samplers'][scale_channel['sampler']]['output']]
        scale_view = gltf['bufferViews'][scale_accessor['bufferView']]
        scale_start = binary_offset+scale_view.get('byteOffset',0)+scale_accessor.get('byteOffset',0)
        first_scale = struct.unpack_from('<fff',raw,scale_start)
        last_scale = struct.unpack_from('<fff',raw,scale_start+(scale_accessor['count']-1)*scale_view.get('byteStride',12))
        assert first_scale[0] < .4, (profile['id'], 'hinge retains closed thickness while open')
        assert abs(last_scale[0]-1)<1e-5, (profile['id'], 'closed hinge no longer spans phone depth')

        sampler = animation['samplers'][channels[0]['sampler']]
        times = gltf['accessors'][sampler['input']]
        assert times.get('max') and abs(times['max'][0]-articulation['duration_seconds']) < .05
        axis = articulation['axis_mm']
        pivot_translation = gltf['nodes'][moving_index].get('translation', [0,0,0])
        expected_translation = [axis[0]*.001, axis[2]*.001, -axis[1]*.001]
        assert max(abs(a-b) for a,b in zip(pivot_translation, expected_translation)) < 1e-7
        inner = next(screen for screen in metadata['screens'] if screen['node'] == 'Inner screen')
        assert len(inner.get('nodes', [])) == 2, (profile['id'], 'inner OLED must be split across both pivots')
        assert any(node.get('name') == 'Hinge spine | articulated' for node in gltf['nodes'])
        materials = {material.get('name'): material for material in gltf.get('materials', [])}
        for screen in metadata['screens']:
            screen_material = materials[screen['material']]
            assert screen_material.get('doubleSided') is True
            assert 'KHR_materials_unlit' in screen_material.get('extensions', {}), 'OLED lighting varies with hinge angle'
            fallback = screen_material.get('pbrMetallicRoughness', {}).get('baseColorFactor', [0,0,0,1])
            assert sum(fallback[:3]) > .2, (profile['id'], 'fold screen fallback is still black')
    cameras = [profile['camera']] if 'camera' in profile else [panel['camera'] for panel in profile.get('panels',[]) if 'camera' in panel]
    measured = profile.get('camera_measurement')
    if measured:
        cam = cameras[0]
        body = next((p['body_mm'] for p in profile.get('panels', []) if 'camera' in p), profile['body_mm'])
        scale = measured['scale_mm_per_px']
        bar = measured['bar_bounds_px']
        image_body = measured['body_bounds_px']
        tolerance = measured['rear_measurement_uncertainty_mm']
        assert abs(cam['size_mm'][1]-(bar[3]-bar[1])*scale) <= tolerance
        gap = body['height']/2-cam['center_mm'][1]-cam['size_mm'][1]/2
        assert abs(gap-(bar[1]-image_body[1])*scale) <= tolerance
        assert metadata['camera_measurement'] == measured
    margins = []
    for camera in cameras:
        if camera.get('side_wrap_mm'):
            node = next(node for node in gltf['nodes'] if node.get('name','').startswith('Camera housing'))  # the bar itself wraps
            primitive = gltf['meshes'][node['mesh']]['primitives'][0]
            accessor = gltf['accessors'][primitive['attributes']['POSITION']]
            view = gltf['bufferViews'][accessor['bufferView']]
            start = binary_offset+view.get('byteOffset',0)+accessor.get('byteOffset',0)
            points = [struct.unpack_from('<fff',raw,start+i*view.get('byteStride',12)) for i in range(accessor['count'])]
            edge = max(abs(p[0]) for p in points)
            middle_z = min(p[1] for p in points)
            for side in (-1,1):
                edge_z = min(p[1] for p in points if p[0]*side>edge-.00002)
                assert edge_z-middle_z>camera['bump_mm']*.0004, 'Visor end does not wrap into side rail'
        if 'Pro Fold' in profile['name']:
            panel = profile['panels'][1]['body_mm']
            x,y = camera['center_mm']; w,h,r = camera['size_mm']
            body_r = panel['corner_radius']
            assert abs((x+w/2-r)-(panel['width']/2-body_r))<1e-8
            assert abs((y+h/2-r)-(panel['height']/2-body_r))<1e-8, 'Camera and body corners are not concentric'
        if profile['id']=='pixel-7a':
            assert (camera['size_mm'][1]-camera['windows'][0][3])/2 >= 2.0
        for item in camera['lenses']:
            window = camera['windows'][item['window']]
            x, y = item['center_mm']; radius = item['radius_mm']
            if item['kind'] == 'periscope':
                # Check the clear aperture, not an invented circular periscope hole.
                margin = -max(rounded_distance((x+dx,y+dy),window)
                              for dx in [-radius*.79,radius*.79] for dy in [-radius*1.05,radius*1.05])
            else:
                margin = -rounded_distance((x,y),window)-radius*1.02
            assert margin > .1, (profile['id'],'lens meets cover edge',margin)
            margins.append(margin)
        for index, item in enumerate(camera['lenses']):
            for other in camera['lenses'][index+1:]:
                distance = math.dist(item['center_mm'],other['center_mm'])
                assert distance-item['radius_mm']-other['radius_mm'] > .3
    result = {'id':profile['id'],'screen_aspect':True,'exported_screen_bounds':True,'enclosure_bounds':True,
              'camera_clearance_mm': min(margins) if margins else None,
              'triangles':triangles,'glb_bytes':len(raw)}
    (output/'geometry-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    paths = sorted((BASE/'profiles').glob('pixel-*.json'))
    paths += sorted((BASE/'profiles').glob('iphone-duo-*.json'))
    results = [verify(path) for path in paths]
    (BASE/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
    print(f'Passed {len(results)} profiles: screen aspect, GLB bounds/UVs, lens clearance')
