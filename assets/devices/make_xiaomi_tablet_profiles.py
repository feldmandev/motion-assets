"""Four Xiaomi tablets: official chassis/pixels, photoestimated small geometry."""
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DOCUMENTS = BASE
RESEARCH = BASE / 'research/xiaomi-tablet-measurements.json'
DATA = json.loads(RESEARCH.read_text())
COLORS = json.loads((DOCUMENTS / 'brand_colors.json').read_text())


def rgb(value):
    return [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]


def make(key):
    row = DATA['models'][key]
    w, h, d = row['body_mm']
    rx, ry = row['resolution_portrait']
    scale = row['diagonal_inches']*25.4/math.hypot(rx, ry)
    sw, sh = rx*scale, ry*scale
    radius = row['estimated_corner_radius_mm']

    # Measurements use a portrait rear view, origin at its top-left.
    def pos(x, y):
        return [w/2-x, h/2-y]

    finishes = {}
    for color, palette in COLORS[row['gallery_model']].items():
        back = rgb(palette[1])
        finishes[color.replace('_', ' ').title()] = {
            'back': {'rgb': back, 'metal': .65, 'rough': .43},
            'rail': {'rgb': back, 'metal': .8, 'rough': .32},
            'bar': {'rgb': [.045, .05, .055], 'metal': .55, 'rough': .28},
            'logo': {'rgb': [v*.48 for v in back], 'metal': .25, 'rough': .44},
            'contact': {'rgb': [.62, .64, .65], 'metal': .8, 'rough': .3},
            'lens_rim': {'rgb': [.14, .16, .18], 'metal': .7, 'rough': .25},
        }
    default = next(iter(finishes))
    materials = {**finishes[default],
                 'black': {'rgb': [.007, .009, .012], 'rough': .4},
                 'flash': {'rgb': [.88, .86, .77], 'rough': .35}}
    x, y, cw, ch = row['camera_bounds_mm']
    center = pos(x+cw/2, y+ch/2)
    bump = row['estimated_bump_mm']
    lenses = [{'kind': 'main' if i == 0 else 'depth',
               'center_mm': pos(*point), 'radius_mm': 2.4 if i == 0 else 1.35,
               'window': 0} for i, point in enumerate(row['active_lens_centers_mm'])]
    details = []
    # Physical rings and the decorative blank circle sit on the same glass island.
    for i, point in enumerate(row['active_lens_centers_mm']):
        details.append({'name': f'Camera aperture collar {i}', 'center_mm': pos(*point),
                        'radius_mm': 4.4 if i == 0 else 3.5,
                        'depth_mm': bump+.035, 'material': 'lens_rim'})
    sensors = []
    for i, point in enumerate(row['decorative_circle_centers_mm']):
        details.append({'name': f'Decorative camera circle rim {i}',
                        'center_mm': pos(*point), 'radius_mm': 3.8,
                        'depth_mm': bump+.035, 'material': 'lens_rim'})
        sensors.append([*pos(*point), 3.55])
    lx, ly = row['logo_center_mm']
    for i in range(3):
        details.append({'name': f'Keyboard contact {i}', 'center_mm': pos(lx, ly+18+i*5.3),
                        'radius_mm': 1.1, 'depth_mm': .045, 'material': 'contact'})
    logo_width = row['logo_length_mm']
    # Source coordinates are X right/Y down; rear_mark mirrors both axes.
    # Map to bottom-to-top in portrait and upright left-to-right in landscape.
    contours = [[[round(y*logo_width, 5), round(-x*logo_width, 5)] for x, y in contour]
                for contour in DATA['wordmark']['normalized_contours']]
    profile = {
        'id': key, 'name': row['name'], 'manufacturer': 'Xiaomi',
        'gallery_model': row['gallery_model'], 'form_factor': 'tablet', 'kind': 'tablet',
        'status': 'provisional', 'finish': default,
        'body_mm': {'width': w, 'height': h, 'depth': d, 'corner_radius': radius,
                    'edge_roll': .28, 'front_rail_mm': .4, 'rear_style': 'unibody'},
        'materials': materials, 'finishes': finishes,
        'screen': {'object': 'Device screen', 'node': 'Device screen', 'panel': 'Body',
                   'resolution': [rx, ry], 'fit_box_mm': [sw, sh],
                   'center_mm': [0, 0, d/2+.035],
                   'corner_radius_mm': radius-min((w-sw)/2, (h-sh)/2),
                   'create_cutouts': True,
                   'cutouts': [{'center_mm': [w/2-(w-sw)/4, 0], 'radius_mm': 1.1}]},
        'camera': {'center_mm': center, 'size_mm': [cw, ch, 5.0],
                   'bump_mm': bump, 'roll_mm': .18, 'integrated_plateau': True,
                   'skip_source_pupil': True, 'optical_bump_mm': 0,
                   'windows': [[*center, cw-1.4, ch-1.4, 4.3]],
                   'lenses': lenses, 'sensors': sensors,
                   'flash': [[*pos(*row['flash_center_mm']), .85]], 'flash_offset_mm': .06},
        'rear_details': details,
        'rear_logo': {'kind': 'xiaomi_wordmark', 'surface_offset_mm': .06,
                      'center_mm': pos(lx, ly), 'contours_mm': contours},
        'buttons': [{'name': 'Volume', 'side': 'right', 'center_y_mm': h/2-31,
                     'length_mm': 20, 'width_mm': 2, 'thickness_mm': .3, 'radius_mm': .8}],
        'accuracy': DATA['accuracy'],
        'sources': [row['spec_url'], row['rear_render_url']],
        'rear_reference': {k: v for k, v in row.items() if k not in
                           ('name', 'gallery_model', 'body_mm', 'resolution_portrait', 'diagonal_inches')},
    }
    return profile


if __name__ == '__main__':
    selected = sys.argv[1:] or list(DATA['models'])
    for key in selected:
        profile = make(key)
        (BASE / 'profiles' / (key+'.json')).write_text(json.dumps(profile, indent=2)+'\n')
    print('Generated', len(selected), 'Xiaomi tablet profiles')
