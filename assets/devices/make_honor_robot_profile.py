"""Estimated MWC promotional HONOR Robot Phone; not production/OEM CAD."""
import json
from pathlib import Path

from svgelements import Path as SvgPath
from make_device_branding import apply as apply_branding, tone

BASE = Path(__file__).resolve().parent
DOCUMENTS = BASE


def make():
    colors = json.loads((DOCUMENTS/'brand_colors.json').read_text())['honor_robot_phone']
    logo = json.loads((DOCUMENTS/'brand_logos.json').read_text())['honor']
    path = SvgPath(logo['d'])
    x0, y0, x1, y1 = path.bbox()
    scale = 19/(x1-x0)
    contours = []
    for sub in path.as_subpaths():
        points = []
        for segment in sub:
            if segment.__class__.__name__ in ('Move', 'Close'):
                continue
            count = 1 if segment.__class__.__name__ == 'Line' else 12
            for i in range(count+1):
                p = segment.point(i/count)
                point = [(p.x-(x0+x1)/2)*scale, (p.y-(y0+y1)/2)*scale]
                if not points or points[-1] != point:
                    points.append(point)
        if len(points) > 2:
            contours.append(points)
    finishes = {}
    for name, palette in colors.items():
        c = [int(palette[1][i:i+2], 16)/255 for i in (1, 3, 5)]
        finishes[name.title()] = {
            'back': {'rgb': c, 'metal': .12, 'rough': .42},
            'rail': {'rgb': c, 'metal': .8, 'rough': .25},
            'bar': {'rgb': [.055, .062, .08], 'metal': .15, 'rough': .22},
            'logo': {'rgb': tone(c), 'metal': .45, 'rough': .3},
            'arm': {'rgb': [min(1, v*.45+.12) for v in c], 'metal': .8, 'rough': .28},
        }
    profile = {
        'id': 'honor-robot-phone', 'name': 'HONOR Robot Phone (MWC promotional estimate)',
        'manufacturer': 'HONOR', 'form_factor': 'phone',
        'status': 'estimated prelaunch promotional design; not OEM CAD', 'finish': 'White',
        'body_mm': {'width': 76.5, 'height': 163.8, 'depth': 8.9,
                    'corner_radius': 8.2, 'edge_roll': .55, 'front_rail_mm': .45},
        'finishes': finishes,
        'materials': {**finishes['White'],
                      'black': {'rgb': [.008, .01, .015], 'rough': .34},
                      'flash': {'rgb': [.92, .9, .78], 'rough': .35}},
        'screen': {'object': 'Screen', 'resolution': [1260, 2750],
                   'fit_box_mm': [71.48, 156.0], 'corner_radius_mm': 6.1,
                   'center_mm': [0, 0, 4.47],
                   'cutouts': [{'center_mm': [0, 73.7], 'radius_mm': 1.25}]},
        'buttons': [{'name': 'Power', 'length_mm': 10, 'center_y_mm': 10},
                    {'name': 'Volume', 'length_mm': 19, 'center_y_mm': 34}],
        'robot_arm': {'anchor_mm': [17.5, 77.5, -1.5], 'stem_mm': 5.5,
                      'head_offset_mm': [0, -24, 0], 'head_size_mm': [19, 18, 9],
                      'island_center_mm': [0, 57.5], 'island_size_mm': [70, 45, 6],
                      'shutter_travel_mm': -28},
        'robot_logo': {'center_mm': [0, -58], 'contours_mm': contours},
        'accuracy': {
            'body_dimensions': '76.5 x 163.8 x 8.9 mm is an estimated scale, not a published measurement. HONOR global spec page had empty dimension values on 2026-10-23.',
            'screen_geometry': '71.48 x 156 mm opening, 6.1 mm corners and 1260 x 2750 texture canvas are estimates, not confirmed panel size or native resolution.',
            'camera_geometry': 'Reconstruction of MWC promotional TVC and transparent gimbal render. Top-edge flip anchor, pan base, dogleg side bracket, pitch motor and optical-axis roll stay connected. A recessed rear pocket accommodates the stowed mechanism inside the chassis. Link lengths, hidden axes, cavity depth, bump depths and motor internals are estimated; not OEM CAD.',
            'motion': 'Stowed rear-facing camera swings outward behind body before rising above top edge. Head faces display side when deployed. Shutter clears before flip; tracking angles return to neutral for stow. Timing and clearances are illustrative.',
            'branding': 'HONOR vector outline from Documents brand_logos.json; lower rear placement/size estimated from collection icon. Finish-aware tones use make_device_branding.tone/apply. MWC footage also shows an alpha symbol, omitted to preserve requested collection HONOR branding.',
            'finishes': 'Black/White collection names and existing swatches; approximate reflective arm/rail and satin rear, not calibrated materials.',
            'omissions': 'Hidden actuator gearing, flex cables, seals, production camera specifications, ports and tiny inscriptions omitted. Promotional reference differs from subsequent commercial product; this profile deliberately describes the MWC design.'
        },
        'sources': ['https://www.honor.com/global/events/honor-robot-phone/',
                    'https://www-file.honor.com/content/dam/honor/common/events/2026/honor-robot-phone-2026/video/video-tvc-pc-all.mp4',
                    'https://www-file.honor.com/content/dam/honor/common/events/2026/honor-robot-phone-2026/imgs/section-gimbal/honorrobotphone-gimbal-phone-1@2x.jpg',
                    'https://www.honor.com/global/phones/honor-robot-phone/spec/',
                    'Documents notes/src/main/assets/device-icons/catalog.json: honor_robot_phone',
                    'Documents brand_colors.json and brand_logos.json'],
    }
    return apply_branding(profile)


if __name__ == '__main__':
    (BASE/'profiles/honor-robot-phone.json').write_text(json.dumps(make(), indent=2)+'\n', encoding='utf-8')
    print('Wrote estimated HONOR Robot Phone profile')
