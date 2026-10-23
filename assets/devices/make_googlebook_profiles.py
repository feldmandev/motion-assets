"""Generate the 5 official 2026 Googlebook laptop profiles."""
from make_device_branding import apply as apply_branding
import json
from pathlib import Path

BASE = Path(__file__).resolve().parent
PROFILES = BASE / 'profiles'

GLOW_BG_RY = [
    [0.259, 0.522, 0.957],
    [0.204, 0.659, 0.325],
    [0.984, 0.737, 0.016],
    [0.918, 0.263, 0.208],
]
GLOW_RY_BG = list(reversed(GLOW_BG_RY))


def hex_rgb(h):
    h = h.lstrip('#')
    return [round(int(h[i:i + 2], 16) / 255.0, 4) for i in (0, 2, 4)]


def make_finish(hex_col, logo_hex, keycap_hex='#ffffff', rough=0.30):
    rgb = hex_rgb(hex_col)
    l_rgb = hex_rgb(logo_hex)
    # Always keep keycap RGB at 1.0 so the baseColorTexture renders at 100% full
    # brightness without being dimmed by the glTF baseColorFactor tint.
    return {
        'back': {'rgb': rgb, 'metal': 0.12, 'rough': rough},
        'rail': {'rgb': rgb, 'metal': 0.18, 'rough': max(0.24, rough - 0.04)},
        'bar': {'rgb': rgb, 'metal': 0.22, 'rough': rough},
        'logo': {'rgb': l_rgb, 'metal': 0.65, 'rough': 0.18},
        'keycap': {'rgb': [1.0, 1.0, 1.0], 'metal': 0.04, 'rough': 0.44},
    }


SPECS = [
    {
        'id': 'googlebook-emulator',
        'name': 'Googlebook Emulator',
        'manufacturer': 'Google',
        'width': 312.0,
        'height': 218.0,
        'lid_depth': 4.8,
        'base_depth': 8.0,
        'corner_radius': 6.5,
        'screen_radius': 2.2,
        'screen_res': [2880, 1800],
        'screen_box': [302.4, 189.0],
        'screen_cy': 2.8,
        'finish': 'Titanium Silver',
        'finishes': {
            'Titanium Silver': make_finish('#d4d8dc', '#ffffff', rough=0.26),
            'Obsidian': make_finish('#202124', '#80868b', rough=0.30),
            'Porcelain': make_finish('#f1f3f4', '#5f6368', rough=0.28),
            'Hazel': make_finish('#808882', '#d2e3fc', rough=0.28),
        },
        'glowbar': {
            'center_mm': [0.0, 94.0],
            'size_mm': [42.0, 1.8],
            'colors': GLOW_BG_RY,
        },
        'rear_logo': {
            'kind': 'google_g',
            'center_mm': [0.0, 2.0],
            'width_mm': 32.0,
        },
        'hinge_style': 'center_bar',
        'deck_style': 'standard',
        'ports': {
            'left': [
                {'type': 'usb_c', 'z': 22.0},
                {'type': 'usb_c', 'z': 36.0},
                {'type': 'audio', 'z': 52.0},
            ],
            'right': [
                {'type': 'usb_c', 'z': 22.0},
                {'type': 'usb_a', 'z': 38.0},
            ],
        },
    },
    {
        'id': 'googlebook-acer-14',
        'name': 'Acer Googlebook 14',
        'manufacturer': 'Acer',
        'width': 312.0,
        'height': 222.9,
        'lid_depth': 5.2,
        'base_depth': 8.7,
        'corner_radius': 6.8,
        'screen_radius': 2.0,
        'screen_res': [2880, 1800],
        'screen_box': [302.4, 189.0],
        'screen_cy': 3.8,
        'finish': 'Elemental Blue',
        'finishes': {
            'Elemental Blue': make_finish('#2b3c4e', '#6c8299', rough=0.32),
            'Steel Gray': make_finish('#8e949c', '#c0c6cc', rough=0.28),
            'Pure Silver': make_finish('#d4d8dc', '#f0f3f6', rough=0.26),
        },
        'glowbar': {
            'center_mm': [112.0, 96.5],
            'size_mm': [39.3, 1.8],
            'colors': GLOW_BG_RY,
        },
        'rear_logo': {
            'kind': 'acer',
            'center_mm': [-110.8, 96.5],
            'width_mm': 28.5,
        },
        'hinge_style': 'convertible_dual',
        'deck_style': 'standard',
        'ports': {
            'left': [
                {'type': 'battery_led', 'z': 18.0},
                {'type': 'usb_c', 'z': 26.0},
                {'type': 'usb_c', 'z': 38.0},
                {'type': 'hdmi', 'z': 54.0},
            ],
            'right': [
                {'type': 'kensington', 'z': 16.0},
                {'type': 'usb_a', 'z': 28.0},
                {'type': 'audio', 'z': 44.0},
            ],
        },
    },
    {
        'id': 'googlebook-asus-14',
        'name': 'ASUS Googlebook 14',
        'manufacturer': 'ASUS',
        'width': 310.9,
        'height': 212.8,
        'lid_depth': 5.0,
        'base_depth': 8.6,
        'corner_radius': 7.5,
        'screen_radius': 2.8,
        'screen_res': [2880, 1800],
        'screen_box': [301.6, 188.5],
        'screen_cy': 2.6,
        'finish': 'Dusk Ash',
        'finishes': {
            'Dusk Ash': make_finish('#484c50', '#85898d', rough=0.30),
            'Star Black': make_finish('#1f2124', '#55585d', rough=0.32),
            'Cool Silver': make_finish('#c8ccd0', '#eceff2', rough=0.26),
        },
        'glowbar': {
            'center_mm': [0.0, 83.7],
            'size_mm': [39.3, 1.8],
            'colors': GLOW_RY_BG,
        },
        'rear_logo': {
            'kind': 'asus',
            'center_mm': [0.0, 1.0],
            'width_mm': 44.0,
        },
        'hinge_style': 'center_bar',
        'deck_style': 'standard',
        'ports': {
            'left': [
                {'type': 'usb_c', 'z': 22.0},
                {'type': 'hdmi', 'z': 36.0},
                {'type': 'usb_a', 'z': 52.0},
                {'type': 'audio', 'z': 66.0},
            ],
            'right': [
                {'type': 'usb_c', 'z': 25.0},
                {'type': 'status_leds', 'z': 36.0},
            ],
        },
    },
    {
        'id': 'googlebook-dell-xps',
        'name': 'Dell XPS Googlebook',
        'manufacturer': 'Dell',
        'width': 296.9,
        'height': 200.66,
        'lid_depth': 4.8,
        'base_depth': 7.9,
        'corner_radius': 5.6,
        'screen_radius': 1.5,
        'screen_res': [2560, 1600],
        'screen_box': [288.8, 180.5],
        'screen_cy': 2.3,
        'finish': 'Platinum',
        'finishes': {
            'Platinum': make_finish('#dcdfe2', '#8d9299', rough=0.26),
            'Graphite': make_finish('#3a3d40', '#6c7075', rough=0.30),
            'Shimmer': make_finish('#b8b1a3', '#7d776b', rough=0.28),
            'Sky': make_finish('#bcc6d0', '#7e8894', rough=0.28),
        },
        'glowbar': {
            'center_mm': [0.0, 90.0],
            'size_mm': [39.2, 1.7],
            'colors': GLOW_RY_BG,
        },
        'rear_logo': {
            'kind': 'xps',
            'center_mm': [0.0, 1.0],
            'width_mm': 44.0,
        },
        'hinge_style': 'dual_wide',
        'deck_style': 'dell_chiclet',
        'ports': {
            'left': [
                {'type': 'usb_c', 'z': 26.0},
            ],
            'right': [
                {'type': 'usb_c', 'z': 26.0},
            ],
        },
    },
    {
        'id': 'googlebook-hp-14',
        'name': 'HP Googlebook 14',
        'manufacturer': 'HP',
        'width': 311.1,
        'height': 216.6,
        'lid_depth': 4.4,
        'base_depth': 6.5,
        'corner_radius': 6.8,
        'screen_radius': 2.2,
        'screen_res': [2880, 1800],
        'screen_box': [302.0, 188.75],
        'screen_cy': 2.7,
        'finish': 'Atmospheric Blue',
        'finishes': {
            'Atmospheric Blue': make_finish('#4a576d', '#8a99b3', rough=0.30),
            'Glacier Silver': make_finish('#d4d8dd', '#a0a6ae', rough=0.26),
            'Ceramic White': make_finish('#f0f2f5', '#959aa0', rough=0.28),
        },
        'glowbar': {
            'center_mm': [0.0, 94.3],
            'size_mm': [39.2, 1.8],
            'colors': GLOW_RY_BG,
        },
        'rear_logo': {
            'kind': 'hp_slash',
            'center_mm': [0.0, 2.0],
            'width_mm': 36.0,
        },
        'hinge_style': 'dual',
        'deck_style': 'standard',
        'ports': {
            'left': [
                {'type': 'usb_c', 'z': 24.0},
                {'type': 'audio', 'z': 38.0},
            ],
            'right': [
                {'type': 'usb_c', 'z': 24.0},
                {'type': 'usb_a', 'z': 40.0},
            ],
        },
    },
    {
        'id': 'googlebook-lenovo-15',
        'name': 'Lenovo Googlebook 15',
        'manufacturer': 'Lenovo',
        'width': 341.0,
        'height': 236.0,
        'lid_depth': 5.6,
        'base_depth': 10.35,
        'corner_radius': 7.2,
        'screen_radius': 2.0,
        'top_lip_mm': [98.0, 3.6],
        'screen_res': [2880, 1800],
        'screen_box': [330.0, 206.25],
        'screen_cy': 3.2,
        'finish': 'Cloud Grey',
        'finishes': {
            'Cloud Grey': make_finish('#8b9097', '#52575d', rough=0.28),
            'Celestial White': make_finish('#e8eaed', '#90969d', rough=0.26),
            'Abyss Blue': make_finish('#283545', '#556578', rough=0.30),
        },
        'glowbar': {
            'center_mm': [0.0, 109.6],
            'size_mm': [58.0, 1.8],
            'colors': GLOW_BG_RY,
        },
        'rear_logo': {
            'kind': 'lenovo',
            'center_mm': [0.0, 3.5],
            'width_mm': 60.0,
        },
        'hinge_style': 'center_bar',
        'deck_style': 'lenovo_15',
        'ports': {
            'left': [
                {'type': 'hdmi', 'z': 25.0},
                {'type': 'usb_c', 'z': 40.0},
                {'type': 'audio', 'z': 54.0},
            ],
            'right': [
                {'type': 'microsd', 'z': 22.0},
                {'type': 'usb_a', 'z': 36.0},
                {'type': 'usb_c', 'z': 52.0},
            ],
        },
    },
]


def main():
    for s in SPECS:
        w, h = s['width'], s['height']
        ld, bd = s['lid_depth'], s['base_depth']
        default_finish = s['finishes'][s['finish']]
        materials = {
            'back': dict(default_finish['back']),
            'rail': dict(default_finish['rail']),
            'bar': dict(default_finish['bar']),
            'logo': dict(default_finish['logo']),
            'keycap': dict(default_finish['keycap']),
            'black': {'rgb': [0.012, 0.014, 0.018], 'rough': 0.42},
            'flash': {'rgb': [0.88, 0.87, 0.82], 'rough': 0.4},
        }
        hinge_axis = [0.0, 0.0, 0.0]
        base_center = [0.0, -bd / 2, h / 2]
        lid_center = [0.0, h / 2, -ld / 2]
        webcam_y = s['screen_box'][1] / 2 + 2.6
        profile = {
            'id': s['id'],
            'name': s['name'],
            'manufacturer': s['manufacturer'],
            'form_factor': 'laptop',
            'body_mm': {
                'width': w,
                'height': h,
                'depth': ld,
                'base_depth_mm': bd,
                'closed_depth_mm': round(ld + bd, 2),
                'corner_radius': s['corner_radius'],
                'edge_roll_mm': [0.55, 0.45],
                'front_curve': 0,
                **({'top_lip_mm': s['top_lip_mm']} if 'top_lip_mm' in s else {}),
            },
            'finish': s['finish'],
            'materials': materials,
            'finishes': s['finishes'],
            'status': 'official',
            'sources': [
                'https://googlebook.google/',
                'https://googlebook.google/compare/',
            ],
            'accuracy': {
                'body_dimensions': 'Published metric Googlebook specifications from googlebook.google',
                'screen_geometry': 'Published 16:10 display active area and resolution',
                'camera_geometry': 'Top bezel 1080p webcam + dual-mic array + lid LED Glowbar measured from official renders',
                'finishes': 'Official Googlebook launch finishes sampled from product renders',
                'hinge': 'Articulated clamshell X-axis hinge rotating lid 0 to 90 degrees flush onto keyboard base',
            },
            'glowbar': s['glowbar'],
            'rear_logo': s['rear_logo'],
            'hinge_style': s['hinge_style'],
            'deck_style': s['deck_style'],
            'ports': s['ports'],
            'panels': [
                {
                    'name': 'Lid',
                    'center_mm': lid_center,
                    'body_mm': {
                        'width': w,
                        'height': h,
                        'depth': ld,
                        'corner_radius': s['corner_radius'],
                        'edge_roll_mm': [0.55, 0.45],
                        'front_curve': 0,
                    },
                    'buttons': False,
                },
                {
                    'name': 'Base',
                    'center_mm': base_center,
                    'body_mm': {
                        'width': w,
                        'height': bd,
                        'depth': h,
                        'corner_radius': s['corner_radius'],
                        'edge_roll_mm': [0.55, 0.45],
                        'front_curve': 0,
                    },
                    'buttons': False,
                },
            ],
            'screen': {
                'panel': 'Lid',
                'object': 'Device screen',
                'node': 'Device screen',
                'resolution': s['screen_res'],
                'fit_box_mm': s['screen_box'],
                'center_mm': [0.0, s['screen_cy'], ld / 2 + 0.14],
                'frame_center_mm': [0.0, s['screen_cy']],
                'corner_radius_mm': s['screen_radius'],
                'create_cutouts': True,
                'cutouts': [
                    {'center_mm': [0.0, webcam_y], 'radius_mm': 1.15},
                ],
            },
            'articulation': {
                'animation': 'Fold',
                'axis': 'X',
                'axis_mm': hinge_axis,
                'moving_panel': 'Lid',
                'fixed_panel': 'Base',
                'pivots': {
                    'Lid': 'Fold pivot | Lid',
                    'Base': 'Fold pivot | Base',
                },
                'open_degrees': 0,
                'closed_degrees': 90,
                'duration_seconds': 1.0,
                'closed_body_mm': {
                    'width': w,
                    'height': round(ld + bd, 2),
                    'depth': h,
                },
            },
        }
        apply_branding(profile)
        out_path = PROFILES / f"{s['id']}.json"
        out_path.write_text(json.dumps(profile, indent=2) + '\n', encoding='utf-8')
        print('Wrote', out_path)


if __name__ == '__main__':
    main()
