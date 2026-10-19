"""Create isolated reviewed profiles for Pixel 4, 4a, 5 and 5a.

Unlike make_pixel_profiles.py this script only owns the six legacy profiles, so it
can be rerun without rewriting the actively developed Fold/newer-Pixel profiles.
Published body/display specifications come from Google's earlier-model hardware
spec page. Pixel 4/4a/5 fronts are subsequently traced from the installed Google
Android Emulator skins; Pixel 5a has no installed SDK skin and keeps its own
published-aspect parametric screen.
"""
from __future__ import annotations

import json
from copy import deepcopy
import math
from pathlib import Path


BASE = Path(__file__).resolve().parent
GOOGLE_SPECS = 'https://support.google.com/pixelphone/answer/16043605?hl=en'


def rgb(value: str) -> list[float]:
    value = value.lstrip('#')
    return [round(int(value[index:index + 2], 16) / 255, 5) for index in (0, 2, 4)]


def active_size(diagonal_in: float, aspect_h_over_w: float) -> list[float]:
    diagonal = diagonal_in * 25.4
    height = diagonal / math.sqrt(1 + (1 / aspect_h_over_w) ** 2)
    return [height / aspect_h_over_w, height]


def lens(kind: str, x: float, y: float, radius: float) -> dict:
    return {'kind': kind, 'center_mm': [x, y], 'radius_mm': radius, 'window': 0}


def finish(back: str, rail: str, button: str, fingerprint: str | None = None, *, back_rough: float | None = None) -> dict:
    result = {
        'back': {'rgb': rgb(back)},
        'rail': {'rgb': rgb(rail)},
        'bar': {'rgb': rgb('#090b0e')},
        'button': {'rgb': rgb(button)},
    }
    if back_rough is not None:
        result['back']['rough'] = back_rough
    if fingerprint:
        result['fingerprint'] = {'rgb': rgb(fingerprint)}
    return result


def materials(chosen: dict, *, unibody: bool) -> dict:
    return {
        'back': {'rgb': chosen['back']['rgb'], 'rough': chosen['back'].get('rough', .58 if unibody else .22)},
        'rail': {'rgb': chosen['rail']['rgb'], 'metal': .08 if unibody else .45,
                 'rough': .52 if unibody else .38},
        'bar': {'rgb': chosen['bar']['rgb'], 'rough': .16},
        'button': {'rgb': chosen['button']['rgb'], 'metal': .15, 'rough': .34},
        'fingerprint': {'rgb': chosen.get('fingerprint', chosen['back'])['rgb'], 'rough': .72},
        'black': {'rgb': [.006, .008, .011], 'rough': .5},
        'flash': {'rgb': [.88, .87, .78], 'rough': .3},
    }


def screen(resolution: list[int], diagonal: float, aspect: float, depth: float,
           radius: float, cutout: bool) -> dict:
    width, height = active_size(diagonal, aspect)
    cutouts = []
    if cutout:
        cutouts.append({'center_mm': [-width / 2 + 5.0, height / 2 - 5.0], 'radius_mm': 1.9})
    return {
        'object': 'Device screen', 'node': 'Device screen', 'panel': 'Body',
        'resolution': resolution, 'fit_box_mm': [width, height],
        'center_mm': [0, 0, depth / 2 + .035], 'corner_radius_mm': radius,
        'edge_curve_mm': 0, 'create_cutouts': cutout, 'cutouts': cutouts,
    }


def camera_square(cx: float, cy: float, size: float, radius: float, bump: float,
                  lenses: list[dict], flash: list[float], sensors: list[list[float]] | None = None) -> dict:
    return {
        'center_mm': [cx, cy], 'size_mm': [size, size, radius], 'bump_mm': bump,
        'roll_mm': .35, 'cover_depth_mm': .10, 'cover_roll_mm': .025,
        'windows': [[cx, cy, size - .8, size - .8, max(.8, radius - .35)]],
        'lenses': lenses, 'flash': [flash], 'sensors': sensors or [],
    }


def base_profile(*, model_id: str, name: str, body: list[float], resolution: list[int],
                 diagonal: float, aspect: float, screen_radius: float, cutout: bool,
                 edge_roll: list[float], finishes: dict, chosen: str, camera: dict,
                 buttons: list[dict], rear_details: list[dict], sources: list[str],
                 unibody: bool, bezel_cameras: list[list[float]] | None = None) -> dict:
    height, width, depth = body
    selected = finishes[chosen]
    profile = {
        'id': model_id, 'name': name, 'finish': chosen,
        'body_mm': {
            'height': height, 'width': width, 'depth': depth,
            # The build step replaces this average with four display-concentric
            # radii. It remains a safe seed for the pre-trace profile.
            'corner_radius': screen_radius + 3.0, 'edge_roll': edge_roll[1],
            'edge_roll_mm': edge_roll, 'front_curve': 0,
            **({'rear_style': 'unibody'} if unibody else {}),
        },
        'materials': materials(selected, unibody=unibody), 'finishes': finishes,
        'screen': screen(resolution, diagonal, aspect, depth, screen_radius, cutout),
        'camera': camera, 'buttons': buttons, 'rear_details': rear_details,
        'accuracy': {
            'body_dimensions': 'Google published metric dimensions',
            'screen_resolution': 'Google published panel resolution',
            'screen_geometry': ('Google Android Emulator skin trace with native panel aspect preserved'
                                if model_id in {'pixel-4', 'pixel-4-xl', 'pixel-4a', 'pixel-5'} else
                                'Published panel diagonal/aspect geometry; no matching Android SDK skin is installed'),
            'camera_geometry': ('Model-specific rear housing/lens placement proportioned from reviewed product '
                                'photography; optical stacks reuse the reviewed Pixel optics and are illustrative'),
            'buttons_and_rear_hardware': 'Model-specific placement reviewed against product photography',
            'finishes': 'Approximate sRGB appearance matched to named Google finishes; not measured material samples',
        },
        'sources': [GOOGLE_SPECS, *sources], 'status': 'reviewed legacy reference',
    }
    if bezel_cameras:
        profile['bezel_cameras'] = bezel_cameras
    if model_id in {'pixel-4', 'pixel-4-xl', 'pixel-4a', 'pixel-5'}:
        profile['reference_frame'] = f'research/skins/{model_id}/frame.png'
    return profile


def profiles() -> list[dict]:
    pixel4_finishes = {
        'Just Black': finish('#17191b', '#17191b', '#e6e7e3', back_rough=.16),
        'Clearly White': finish('#eeeeea', '#17191b', '#f28d59', back_rough=.56),
        'Oh So Orange': finish('#f3a185', '#17191b', '#f4d5d7', back_rough=.56),
    }
    p4_cam_x, p4_cam_y = 15.0, 49.2
    pixel4 = base_profile(
        model_id='pixel-4', name='Pixel 4', body=[147.1, 68.8, 8.2],
        resolution=[1080, 2280], diagonal=5.7, aspect=19 / 9,
        screen_radius=2.0, cutout=False, edge_roll=[1.75, .75],
        finishes=pixel4_finishes, chosen='Just Black', unibody=False,
        camera=camera_square(
            p4_cam_x, p4_cam_y, 27.2, 4.2, 1.2,
            [lens('main', p4_cam_x + 6.0, p4_cam_y + 4.6, 3.55),
             lens('telephoto', p4_cam_x - 6.0, p4_cam_y + 4.6, 3.25)],
            [p4_cam_x + .5, p4_cam_y - 7.3, 2.25],
            [[p4_cam_x - 6.8, p4_cam_y - 6.7, 1.2]],
        ),
        buttons=[
            {'name': 'Power', 'side': 'right', 'center_y_mm': 31.5, 'length_mm': 10.0,
             'width_mm': 2.3, 'thickness_mm': .55, 'radius_mm': .8, 'material': 'button'},
            {'name': 'Volume', 'side': 'right', 'center_y_mm': 13.0, 'length_mm': 18.0,
             'width_mm': 2.3, 'thickness_mm': .45, 'radius_mm': .8, 'material': 'rail'},
        ],
        rear_details=[],
        # Pixel 4 keeps its selfie/IR hardware in the forehead rather than a hole in the OLED.
        bezel_cameras=[[-18.0, 66.8, 4.13, 1.45], [-8.5, 66.8, 4.13, .85],
                       [9.0, 66.8, 4.13, .85], [19.0, 66.8, 4.13, 1.15]],
        sources=['https://blog.google/products-and-platforms/devices/pixel/pixel-4/',
                 'https://connecteddevices.co.za/products/google-pixel-4-64gb-just-black-special-import'],
    )

    pixel4a_finishes = {
        'Just Black': finish('#242628', '#242628', '#9fcac3', '#303235'),
        'Barely Blue': finish('#cbdcec', '#cbdcec', '#f0a174', '#bdcede'),
    }
    p4a_x, p4a_y = 19.1, 55.2
    pixel4a = base_profile(
        model_id='pixel-4a', name='Pixel 4a', body=[144.0, 69.4, 8.2],
        resolution=[1080, 2340], diagonal=5.81, aspect=19.5 / 9,
        screen_radius=4.4, cutout=True, edge_roll=[2.35, 1.0],
        finishes=pixel4a_finishes, chosen='Just Black', unibody=True,
        camera=camera_square(
            p4a_x, p4a_y, 18.4, 3.2, .9,
            [lens('main', p4a_x - 4.3, p4a_y - 4.2, 3.35)],
            [p4a_x + 4.5, p4a_y + 4.6, 2.0],
        ),
        buttons=[
            {'name': 'Power', 'side': 'right', 'center_y_mm': 29.5, 'length_mm': 9.5,
             'width_mm': 2.2, 'thickness_mm': .5, 'radius_mm': .8, 'material': 'button'},
            {'name': 'Volume', 'side': 'right', 'center_y_mm': 11.5, 'length_mm': 17.0,
             'width_mm': 2.2, 'thickness_mm': .42, 'radius_mm': .8, 'material': 'rail'},
        ],
        rear_details=[{'name': 'Rear fingerprint', 'center_mm': [0, 20.8], 'radius_mm': 4.15,
                       'depth_mm': .035, 'material': 'fingerprint'}],
        sources=['https://www.mobiel.nl/smartphone/google/pixel-4a',
                 'https://blog.google/intl/ja-jp/products/devices-services/2020_12_2020featuredrop/'],
    )
    # The installed Google skin measures a slightly larger active opening than
    # the nominal 5.81-inch diagonal calculation. Anchor the physical selfie
    # aperture to that traced opening rather than the pre-trace seed box.
    pixel4a['screen']['cutouts'][0]['center_mm'] = [-26.27, 62.74]

    pixel5_finishes = {
        'Just Black': finish('#25292a', '#25292a', '#333738', '#202425'),
        'Sorta Sage': finish('#a8bbb0', '#a8bbb0', '#82978c', '#93a79c'),
    }
    p5_x, p5_y = 16.8, 51.8
    pixel5 = base_profile(
        model_id='pixel-5', name='Pixel 5', body=[144.7, 70.4, 8.0],
        resolution=[1080, 2340], diagonal=6.0, aspect=19.5 / 9,
        screen_radius=5.0, cutout=True, edge_roll=[2.55, .95],
        finishes=pixel5_finishes, chosen='Sorta Sage', unibody=True,
        camera=camera_square(
            p5_x, p5_y, 24.0, 4.1, 1.0,
            [lens('main', p5_x - 5.3, p5_y - 3.7, 3.45),
             lens('ultrawide', p5_x + 5.3, p5_y - 3.7, 3.05)],
            [p5_x, p5_y + 6.0, 1.9], [[p5_x, p5_y - 8.0, .65]],
        ),
        buttons=[
            {'name': 'Power', 'side': 'right', 'center_y_mm': 29.5, 'length_mm': 9.5,
             'width_mm': 2.2, 'thickness_mm': .46, 'radius_mm': .8, 'material': 'button'},
            {'name': 'Volume', 'side': 'right', 'center_y_mm': 11.0, 'length_mm': 18.0,
             'width_mm': 2.2, 'thickness_mm': .42, 'radius_mm': .8, 'material': 'rail'},
        ],
        rear_details=[{'name': 'Rear fingerprint', 'center_mm': [0, 21.7], 'radius_mm': 4.15,
                       'depth_mm': .035, 'material': 'fingerprint'}],
        sources=['https://superbia.ru/catalog/mobile/google/google-pixel-5/8571-smartfon-google-pixel-5-8128gb-seryy.html'],
    )
    pixel5['screen']['cutouts'][0]['center_mm'] = [-26.58, 63.43]

    pixel5a_finishes = {
        'Mostly Black': finish('#293a32', '#293a32', '#727b53', '#25332c'),
    }
    p5a_x, p5a_y = 18.0, 59.6
    pixel5a = base_profile(
        model_id='pixel-5a', name='Pixel 5a', body=[156.2, 73.2, 8.8],
        resolution=[1080, 2400], diagonal=6.34, aspect=20 / 9,
        screen_radius=5.3, cutout=True, edge_roll=[2.45, .95],
        finishes=pixel5a_finishes, chosen='Mostly Black', unibody=True,
        camera=camera_square(
            p5a_x, p5a_y, 24.7, 4.1, 1.05,
            [lens('main', p5a_x - 5.5, p5a_y - 3.8, 3.5),
             lens('ultrawide', p5a_x + 5.5, p5a_y - 3.8, 3.05)],
            [p5a_x, p5a_y + 6.2, 1.95], [[p5a_x, p5a_y - 8.1, .65]],
        ),
        buttons=[
            {'name': 'Power', 'side': 'right', 'center_y_mm': 31.0, 'length_mm': 10.0,
             'width_mm': 2.3, 'thickness_mm': .48, 'radius_mm': .8, 'material': 'button'},
            {'name': 'Volume', 'side': 'right', 'center_y_mm': 11.5, 'length_mm': 18.5,
             'width_mm': 2.3, 'thickness_mm': .43, 'radius_mm': .8, 'material': 'rail'},
        ],
        rear_details=[{'name': 'Rear fingerprint', 'center_mm': [0, 34.0], 'radius_mm': 4.3,
                       'depth_mm': .035, 'material': 'fingerprint'}],
        sources=['https://www.backmarket.com/en-us/p/google-pixel-5a-5g-verizon',
                 'https://blog.google/products-and-platforms/devices/pixel/pixel5a-with-5g-new-google-phone/'],
    )
    # Pixel 4's coated black band surrounds a separate, inset glass back.
    pixel4['body_mm'].update(rear_style='inset_glass', rear_inset=.45)
    pixel4['materials']['rail'].update(metal=0, rough=.72)

    pixel4xl = deepcopy(pixel4)
    pixel4xl.update(id='pixel-4-xl', name='Pixel 4 XL', reference_frame='research/skins/pixel-4-xl/frame.png')
    pixel4xl['body_mm'].update(height=160.4, width=75.1)
    pixel4xl['screen'] = screen([1440, 3040], 6.3, 19 / 9, 8.2, 2.0, False)
    # The same optical module sits at the same inset from the larger enclosure.
    dx, dy = (75.1-68.8)/2, (160.4-147.1)/2
    pixel4xl['camera']['center_mm'][0] += dx
    pixel4xl['camera']['center_mm'][1] += dy
    for window in pixel4xl['camera']['windows']:
        window[0] += dx
        window[1] += dy
    for item in pixel4xl['camera']['lenses']:
        item['center_mm'][0] += dx
        item['center_mm'][1] += dy
    for item in pixel4xl['camera']['flash'] + pixel4xl['camera']['sensors']:
        item[0] += dx
        item[1] += dy
    for item in pixel4xl['bezel_cameras']:
        item[1] += dy
    for button in pixel4xl['buttons']:
        button['center_y_mm'] += dy

    # 4a 5G has two rear cameras, unlike the one-camera 4a, and a plastic housing.
    pixel4a5g = deepcopy(pixel5a)
    pixel4a5g.update(id='pixel-4a-5g', name='Pixel 4a (5G)', finish='Just Black')
    pixel4a5g['body_mm'].update(height=153.9, width=74.0, depth=8.2)
    pixel4a5g['screen'] = screen([1080, 2340], 6.2, 19.5 / 9, 8.2, 4.8, True)
    pixel4a5g['finishes'] = {
        'Just Black': finish('#242628', '#242628', '#b6d4cc', '#303235'),
        'Clearly White': finish('#e5e5df', '#e5e5df', '#b6d4cc', '#d1d2ce'),
    }
    pixel4a5g['materials'] = materials(pixel4a5g['finishes']['Just Black'], unibody=True)
    pixel4a5g['rear_details'][0]['center_mm'] = [0, 29.0]
    pixel4a5g['sources'] = [GOOGLE_SPECS, 'https://blog.google/products/pixel/new-pixel-5-4a-5g/']
    pixel4a5g['accuracy']['screen_geometry'] = 'Published 6.2-inch 19.5:9 panel geometry; no matching Android SDK skin is installed'
    pixel4a5g['accuracy']['body_variant'] = 'Sub-6 model, 8.2 mm depth; Verizon mmWave model is 8.5 mm'
    return [pixel4, pixel4xl, pixel4a, pixel4a5g, pixel5, pixel5a]


def main() -> None:
    for data in profiles():
        target = BASE / 'profiles' / f'{data["id"]}.json'
        target.write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
        print('Wrote', target.name)


if __name__ == '__main__':
    main()
