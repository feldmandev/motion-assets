"""Generate high-resolution keyboard textures for all official 2026 Googlebook models."""
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
from draw_vector_icons import draw_vector_icon

BASE = Path(__file__).resolve().parent
TEXTURES_DIR = BASE / 'textures'
TEXTURES_DIR.mkdir(exist_ok=True)

def get_font(size, bold=True):
    font_paths = [
        'C:/Windows/Fonts/segoeuib.ttf' if bold else 'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
        'C:/Windows/Fonts/segoeui.ttf',
        'C:/Windows/Fonts/arial.ttf',
    ]
    for fp in font_paths:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size)
            except Exception:
                pass
    return ImageFont.load_default()

ROW_WEIGHTS = [0.56, 1.0, 1.0, 1.0, 1.0, 1.06]
ROW_LAYOUTS = [
    [1.05] + [1.0] * 12 + [1.15],
    [0.85] + [1.0] * 12 + [1.55],
    [1.35] + [1.0] * 12 + [1.05],
    [1.65] + [1.0] * 11 + [1.85],
    [2.10] + [1.0] * 10 + [2.30],
    [1.15, 1.05, 1.05, 1.05, 4.85, 1.05, 1.05, 1.05, 1.05, 1.05],
]

KEY_LABELS = [
    # Row 0: Function row
    ['esc', '←', '→', 'icon:refresh', 'icon:fullscreen', 'icon:overview', 'icon:bright_down', 'icon:bright_up', 'icon:mic', 'icon:vol_mute', 'icon:vol_down', 'icon:vol_up', 'icon:lock', 'icon:power'],
    # Row 1: Number row
    ['~\n`', '!\n1', '@\n2', '#\n3', '$\n4', '%\n5', '^\n6', '&\n7', '*\n8', '(\n9', ')\n0', '_\n-', '+\n=', 'backspace'],
    # Row 2: QWERTY
    ['tab', 'Q', 'W', 'E', 'R', 'T', 'Y', 'U', 'I', 'O', 'P', '{\n[', '}\n]', '|\n\\'],
    # Row 3: Home row
    ['icon:search', 'A', 'S', 'D', 'F', 'G', 'H', 'J', 'K', 'L', ':\n;', '"\n\'', 'enter'],
    # Row 4: Shift row
    ['shift', 'Z', 'X', 'C', 'V', 'B', 'N', 'M', '<\n,', '>\n.', '?\n/', 'shift'],
    # Row 5: Bottom row
    ['ctrl', 'alt', 'icon:gemini', 'fn', '', 'alt', 'ctrl', '◄', ('▲', '▼'), '►'],
]

def generate_keyboard_texture(width_mm, height_mm, deck_style, bg_color, text_color, out_path, img_w=2048, img_h=1024):
    if deck_style == 'dell_chiclet':
        margin_x = 13.5
    elif deck_style == 'lenovo_15':
        margin_x = 34.0
    else:
        margin_x = 19.5

    kb_w = width_mm - 2 * margin_x
    kb_z0 = -height_mm / 2 + 16.5
    kb_z1 = 7.5
    kb_d = kb_z1 - kb_z0
    gap = 1.05 if deck_style == 'dell_chiclet' else 1.25

    total_w = sum(ROW_WEIGHTS)
    z_cursor = kb_z0

    im = Image.new('RGBA', (img_w, img_h), bg_color)
    draw = ImageDraw.Draw(im)

    font_base = get_font(54, bold=True)
    font_fn = get_font(36, bold=True)
    font_small = get_font(30, bold=True)
    font_sub = get_font(26, bold=True)

    for r_idx, (rw, cols) in enumerate(zip(ROW_WEIGHTS, ROW_LAYOUTS)):
        rh = (kb_d - gap * 5) * (rw / total_w)
        z0 = z_cursor
        z1 = z0 + rh
        z_cursor = z1 + gap

        col_sum = sum(cols)
        n_cols = len(cols)
        avail_w = kb_w - gap * (n_cols - 1)
        x_cursor = -kb_w / 2

        for c_idx, cw_weight in enumerate(cols):
            kw = avail_w * (cw_weight / col_sum)
            x0 = x_cursor
            x1 = x0 + kw
            x_cursor = x1 + gap

            # Map to image coordinates
            px0 = int(round((x0 - (-kb_w / 2)) / kb_w * img_w))
            px1 = int(round((x1 - (-kb_w / 2)) / kb_w * img_w))
            py0 = int(round((z0 - kb_z0) / kb_d * img_h))
            py1 = int(round((z1 - kb_z0) / kb_d * img_h))

            inset_x = max(2, int((px1 - px0) * 0.05))
            inset_y = max(2, int((py1 - py0) * 0.06))
            k_rect = [px0 + inset_x, py0 + inset_y, px1 - inset_x, py1 - inset_y]

            label = KEY_LABELS[r_idx][c_idx]

            if r_idx == 5 and c_idx == n_cols - 2:
                # Split arrow keys
                mid_py = (py0 + py1) // 2
                sub_gap = int(round(0.65 / kb_d * img_h))
                rect_up = [px0 + inset_x, py0 + inset_y, px1 - inset_x, mid_py - sub_gap // 2]
                rect_dn = [px0 + inset_x, mid_py + sub_gap // 2, px1 - inset_x, py1 - inset_y]
                
                cx_u = (rect_up[0] + rect_up[2]) // 2
                cy_u = (rect_up[1] + rect_up[3]) // 2
                draw.polygon([(cx_u, cy_u - 9), (cx_u - 10, cy_u + 7), (cx_u + 10, cy_u + 7)], fill=text_color)
                
                cx_d = (rect_dn[0] + rect_dn[2]) // 2
                cy_d = (rect_dn[1] + rect_dn[3]) // 2
                draw.polygon([(cx_d, cy_d + 9), (cx_d - 10, cy_d - 7), (cx_d + 10, cy_d - 7)], fill=text_color)
            else:
                if not label:
                    continue
                cx = (k_rect[0] + k_rect[2]) // 2
                cy = (k_rect[1] + k_rect[3]) // 2

                if isinstance(label, str) and label.startswith('icon:'):
                    icon_name = label.split(':', 1)[1]
                    icon_size = 36 if r_idx == 0 else 44
                    draw_vector_icon(draw, icon_name, cx, cy, icon_size, text_color)
                elif '\n' in label:
                    top_l, bot_l = label.split('\n')
                    draw.text((cx, cy - int((py1 - py0) * 0.22)), top_l, fill=text_color, font=font_sub, anchor='mm')
                    draw.text((cx, cy + int((py1 - py0) * 0.22)), bot_l, fill=text_color, font=font_base, anchor='mm')
                elif r_idx == 0:
                    if label in ('←', '→'):
                        if label == '←':
                            draw.line([(cx + 12, cy), (cx - 10, cy)], fill=text_color, width=3)
                            draw.polygon([(cx - 13, cy), (cx - 4, cy - 8), (cx - 4, cy + 8)], fill=text_color)
                        else:
                            draw.line([(cx - 12, cy), (cx + 10, cy)], fill=text_color, width=3)
                            draw.polygon([(cx + 13, cy), (cx + 4, cy - 8), (cx + 4, cy + 8)], fill=text_color)
                    else:
                        draw.text((cx, cy), label, fill=text_color, font=font_fn, anchor='mm')
                elif label in ('◄', '►'):
                    if label == '◄':
                        draw.polygon([(cx - 9, cy), (cx + 8, cy - 10), (cx + 8, cy + 10)], fill=text_color)
                    else:
                        draw.polygon([(cx + 9, cy), (cx - 8, cy - 10), (cx - 8, cy + 10)], fill=text_color)
                elif len(label) > 1:
                    draw.text((cx, cy), label, fill=text_color, font=font_small, anchor='mm')
                else:
                    draw.text((cx, cy), label, fill=text_color, font=font_base, anchor='mm')

    im.save(out_path, format='PNG')
    print('Generated keyboard texture:', out_path.name)

MODELS = [
    {
        'id': 'googlebook-emulator',
        'width': 312.0,
        'height': 218.0,
        'deck_style': 'standard',
        'bg': (20, 22, 26, 255),
        'text': (255, 255, 255, 255),
    },
    {
        'id': 'googlebook-acer-14',
        'width': 312.0,
        'height': 222.9,
        'deck_style': 'standard',
        'bg': (20, 22, 26, 255),
        'text': (255, 255, 255, 255),
    },
    {
        'id': 'googlebook-asus-14',
        'width': 310.9,
        'height': 212.8,
        'deck_style': 'standard',
        'bg': (22, 24, 28, 255),
        'text': (255, 255, 255, 255),
    },
    {
        'id': 'googlebook-dell-xps',
        'width': 296.9,
        'height': 200.66,
        'deck_style': 'dell_chiclet',
        'bg': (30, 32, 36, 255),
        'text': (255, 255, 255, 255),
    },
    {
        'id': 'googlebook-hp-14',
        'width': 311.1,
        'height': 216.6,
        'deck_style': 'standard',
        'bg': (22, 25, 30, 255),
        'text': (255, 255, 255, 255),
    },
    {
        'id': 'googlebook-lenovo-15',
        'width': 341.0,
        'height': 236.0,
        'deck_style': 'lenovo_15',
        'bg': (24, 27, 33, 255),
        'text': (255, 255, 255, 255),
    },
]

def main():
    for m in MODELS:
        out = TEXTURES_DIR / f"kb_{m['id']}.png"
        generate_keyboard_texture(m['width'], m['height'], m['deck_style'], m['bg'], m['text'], out)

if __name__ == '__main__':
    main()
