"""Verify generated iPhone profiles and their exported GLB/frame assets."""
import json
import math
import struct
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path(__file__).resolve().parent


def rounded_distance(point, rectangle):
    x, y, width, height, radius = rectangle
    qx = abs(point[0]-x)-(width/2-radius)
    qy = abs(point[1]-y)-(height/2-radius)
    return math.hypot(max(qx, 0), max(qy, 0))+min(max(qx, qy), 0)-radius


def research_devices():
    devices = {}
    for filename in ('iphone-11-14.json', 'iphone-15-18.json'):
        raw = json.loads((BASE/'research'/filename).read_text(encoding='utf-8'))
        for device in raw['devices'] if isinstance(raw, dict) else raw:
            devices[device['id']] = device
    return devices


def base_id(profile_id):
    return profile_id.removesuffix('-folded').removesuffix('-unfolded')


def expected_controls(profile_id):
    if profile_id.startswith('iphone-duo-'):
        return {'Volume up', 'Volume down', 'Side button | Touch ID', 'Camera Control'}
    if profile_id == 'iphone-air':
        return {'Side button', 'Volume up', 'Volume down', 'Action button', 'Camera Control'}
    suffix = profile_id.split('iphone-', 1)[1]
    number_text = suffix.split('-', 1)[0].rstrip('e')
    generation = int(number_text)
    pro = '-pro' in profile_id
    action = generation >= 16 or generation == 15 and pro
    camera_control = (generation >= 16 and profile_id not in {'iphone-16e', 'iphone-17e'} and
                      not profile_id.startswith('iphone-duo-'))
    names = {'Side button', 'Volume up', 'Volume down',
             'Action button' if action else 'Ring/Silent switch'}
    if camera_control:
        names.add('Camera Control')
    return names


def gltf_from_glb(path):
    raw = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', raw)
    assert magic == 0x46546C67 and version == 2 and length == len(raw), path
    json_size, json_type = struct.unpack_from('<II', raw, 12)
    assert json_type == 0x4E4F534A
    return raw, json.loads(raw[20:20+json_size])


def camera_specs(profile):
    if 'camera' in profile:
        return [profile['camera']]
    return [panel['camera'] for panel in profile.get('panels', []) if 'camera' in panel]


def verify(profile_path, research):
    profile = json.loads(profile_path.read_text(encoding='utf-8'))
    pid = profile['id']
    output = BASE/'exports'/pid
    assert output.is_dir(), (pid, 'missing export directory')
    metadata = json.loads((output/'device.json').read_text(encoding='utf-8'))
    raw, gltf = gltf_from_glb(output/'model.glb')
    names = {node.get('name', '') for node in gltf.get('nodes', [])}

    source = research[base_id(pid)]
    if not pid.startswith('iphone-duo-'):
        assert profile['body_mm']['width'] == source['body_mm']['width']
        assert profile['body_mm']['height'] == source['body_mm']['height']
        assert profile['body_mm']['depth'] == source['body_mm']['depth']
        assert profile['screen']['resolution'] == source['native_px']
        assert profile['screen']['fit_box_mm'] == source['front']['active_mm']
    else:
        expected_body = source['body_mm'] if pid.endswith('-unfolded') else source['closed_body_mm']
        for dimension in ('width', 'height', 'depth'):
            assert profile['body_mm'][dimension] == expected_body[dimension], (pid, dimension)

    # Every slab has a real Apple silhouette; Duo carries it on the camera half.
    if 'panels' in profile:
        assert any(panel.get('rear_logo', {}).get('kind') == 'apple' for panel in profile['panels'])
    else:
        assert profile.get('rear_logo', {}).get('kind') == 'apple'
    assert any(name.startswith('Apple logo |') for name in names), (pid, 'missing Apple rear mark')

    # Physical controls must match the generation. Duo splits controls across its two leaf rails.
    if 'panels' in profile:
        control_specs = [button for panel in profile['panels'] for button in panel.get('button_specs', [])]
    else:
        control_specs = profile.get('buttons', [])
    control_names = {button['name'] for button in control_specs}
    assert control_names == expected_controls(pid), (pid, control_names, expected_controls(pid))
    assert control_names <= names, (pid, 'control missing from GLB', control_names-names)

    # Published panel dimensions survive export. Bounds are local, so this also works for the
    # statically rotated folded Duo leaf.
    enclosure_count = 0
    for index, node in enumerate(gltf['nodes']):
        if not node.get('name', '').startswith('Aluminum enclosure'):
            continue
        enclosure_count += 1
        parent = next(parent for parent in gltf['nodes'] if index in parent.get('children', []))
        expected = next((panel['body_mm'] for panel in profile.get('panels', [])
                         if panel['name'] == parent['name']), profile['body_mm'])
        primitive = gltf['meshes'][node['mesh']]['primitives'][0]
        bounds = gltf['accessors'][primitive['attributes']['POSITION']]
        assert abs(bounds['max'][0]-bounds['min'][0]-expected['width']*.001) < 1e-6
        assert abs(bounds['max'][2]-bounds['min'][2]-expected['height']*.001) < 1e-6
        assert abs(bounds['max'][1]-bounds['min'][1]-(expected['depth']-.05)*.001) < 1e-6
    assert enclosure_count == (2 if 'panels' in profile else 1), (pid, enclosure_count)

    # Runtime screen metadata, frame geometry and UVs must preserve native aspect.
    assert metadata['screens']
    for screen in metadata['screens']:
        width, height = screen['size_mm']
        px, py = screen['resolution']
        assert abs(width/height-px/py) < 1e-10, (pid, screen['node'], 'screen aspect')
        frame_path = output/screen.get('frame_file', 'frame.svg')
        assert frame_path.exists(), (pid, 'missing frame', frame_path.name)
        ET.parse(frame_path)
        node_names = screen.get('nodes') or [screen['node']]
        for node_name in node_names:
            node = next(node for node in gltf['nodes'] if node.get('name') == node_name)
            primitive = gltf['meshes'][node['mesh']]['primitives'][0]
            assert 'TEXCOORD_0' in primitive['attributes'], (pid, node_name, 'missing screen UV')

    cameras = camera_specs(profile)
    local_pupils = {name for name in names if '| local pupil' in name}
    source_pupils = {name for name in names if '| deep pupil' in name}
    lens_count = sum(len(camera['lenses']) for camera in cameras)
    assert not source_pupils, (pid, 'Pixel pupil leaked into iPhone export', source_pupils)
    assert len(local_pupils) == lens_count, (pid, 'local pupil count', len(local_pupils), lens_count)
    for camera in cameras:
        cx, cy = camera['center_mm']
        cw, ch, cr = camera['size_mm']
        plateau = [cx, cy, cw, ch, cr]
        assert camera['optical_bump_mm'] > 0, (pid, 'camera glass has no protrusion')
        if camera['bump_mm'] > .01:
            assert 'Camera housing' in names, (pid, 'missing camera plateau')
        for lens in camera['lenses']:
            window = camera['windows'][lens['window']]
            margin = -rounded_distance(lens['center_mm'], window)-lens['radius_mm']*1.02
            assert margin > .08, (pid, 'lens meets optical window', margin)
        for flash in camera.get('flash', []):
            fx, fy, fr = flash
            if camera.get('flash_surface') != 'body':
                assert rounded_distance((fx, fy), plateau)+fr <= .12, (pid, 'flash outside plateau')
        for sensor in camera.get('sensors', []):
            if camera.get('sensor_surface') != 'body':
                if isinstance(sensor, dict):
                    sx, sy = sensor['center_mm']; sw, sh = sensor['size_mm']
                    outside = max(rounded_distance((sx+dx, sy+dy), plateau)
                                  for dx in (-sw/2, sw/2) for dy in (-sh/2, sh/2))
                    assert outside <= .18, (pid, 'sensor outside plateau')
                else:
                    sx, sy, sr = sensor
                    assert rounded_distance((sx, sy), plateau)+sr <= .18, (pid, 'sensor outside plateau')

    # Every Pro generation from 12 onward has LiDAR plus its small rear mic on the camera plateau.
    if '-pro' in pid and not pid.startswith('iphone-11-'):
        assert len(cameras[0].get('sensors', [])) >= 2, (pid, 'LiDAR/rear mic missing')

    if pid == 'iphone-duo-unfolded':
        assert metadata.get('articulation') == profile['articulation']
        assert 'Rear microphone 0' in names, (pid, 'horizontal rear microphone missing')
        animation = next((item for item in gltf.get('animations', [])
                          if item.get('name') == profile['articulation']['animation']), None)
        assert animation is not None, (pid, 'Fold animation missing')
        assert 'Fold pivot | Hinge spine' in names and 'Hinge spine | articulated' in names
        inner = next(screen for screen in metadata['screens'] if screen['node'] == 'Inner screen')
        assert len(inner.get('nodes', [])) == 2, (pid, 'inner OLED not split over pivots')

    result = {'id': pid, 'glb_bytes': len(raw), 'objects': len(gltf.get('nodes', [])),
              'screens': len(metadata['screens']), 'lenses': lens_count,
              'controls': sorted(control_names), 'apple_logo': True}
    (output/'iphone-geometry-checks.json').write_text(json.dumps(result, indent=2)+'\n',
                                                      encoding='utf-8')
    return result


if __name__ == '__main__':
    profiles = sorted((BASE/'profiles').glob('iphone-*.json'))
    assert len(profiles) == 33, f'Expected 33 iPhone profiles, found {len(profiles)}'
    research = research_devices()
    results = [verify(path, research) for path in profiles]
    (BASE/'iphone-verification.json').write_text(json.dumps(results, indent=2)+'\n', encoding='utf-8')
    print(f'Passed {len(results)} iPhone profiles: source dimensions, controls, Apple mark, '
          'screen UV/aspect, camera containment and GLB structure')
