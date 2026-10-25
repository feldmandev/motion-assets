"""Draw Apple silicon Mac icons from the shared, source-backed Mac catalogue."""
import io
import json
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image
import resvg_py

ROOT = Path(__file__).resolve().parents[2]
MODELS = ROOT.parent / 'home/home-android/demo-video/device-models'
CATALOG = MODELS / 'research/apple-mac-catalog.json'
APPLE = json.loads((ROOT / 'brand_logos.json').read_text())['apple']['d']
COLORS = {
    'Silver': '#cbd0d4', 'Space Gray': '#737780', 'Space Grey': '#737780',
    'Space Black': '#35383e', 'Gold': '#d8bda5', 'Midnight': '#374457',
    'Starlight': '#dbd2c1', 'Sky Blue': '#a9c3d5',
    'Blush': '#d8b9c4', 'Citrus': '#d7d49a', 'Indigo': '#8993b4',
}


def mix(color, target, amount):
    a = [int(color[i:i+2], 16) for i in (1, 3, 5)]
    b = [int(target[i:i+2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(x+(y-x)*amount):02x}' for x, y in zip(a, b))


def rect(x, y, w, h, r):
    br, tr, tl, bl = r if isinstance(r, list) else [r]*4
    return f'M{x+tl},{y}H{x+w-tr}Q{x+w},{y} {x+w},{y+tr}V{y+h-br}Q{x+w},{y+h} {x+w-br},{y+h}H{x+bl}Q{x},{y+h} {x},{y+h-bl}V{y+tl}Q{x},{y} {x+tl},{y}Z'


def path(d, fill):
    return f'<path d="{d}" fill="{fill}" data-morph-unsupported="true"/>'


def svg(device, chassis, color, monochrome=False):
    base = COLORS[color]
    defs = (f'<linearGradient id="metal" x1="0" y1="0" x2="1" y2=".45">'
            f'<stop stop-color="{mix(base,"#ffffff",.35)}"/>'
            f'<stop offset=".48" stop-color="{base}"/>'
            f'<stop offset="1" stop-color="{mix(base,"#000000",.19)}"/></linearGradient>'
            f'<linearGradient id="top" x2=".7" y2="1"><stop stop-color="{mix(base,"#ffffff",.38)}"/>'
            f'<stop offset="1" stop-color="{base}"/></linearGradient>'
            '<linearGradient id="display" x1="0" y1="1" x2=".9" y2="0">'
            '<stop stop-color="#244c7a"/><stop offset=".5" stop-color="#5aaed1"/>'
            '<stop offset="1" stop-color="#b2d8e3"/></linearGradient>')
    holes = []
    parts = []
    logo_cutout = ''
    notch_restore = ''
    if device['kind'] == 'pc':
        dims = device['dimensions_mm']
        height = max(15, min(42, 84 * dims['height']/dims['width']))
        front_only = device['family']=='mac-mini'
        y = (54 if front_only else 58)-height/2
        shell = rect(12,y,84,height,1.5) if front_only else f'M12,{y-15}Q12,{y-22} 19,{y-22}H89Q96,{y-22} 96,{y-15}V{y+height-4}Q96,{y+height+2} 90,{y+height+2}H18Q12,{y+height+2} 12,{y+height-4}Z'
        parts.append(path(shell, 'url(#metal)'))
        if not front_only:
            top = f'M19,{y-22}H89Q96,{y-22} 96,{y-15}V{y-2}Q96,{y+3} 90,{y+3}H18Q12,{y+3} 12,{y-2}V{y-15}Q12,{y-22} 19,{y-22}Z'
            parts.append(path(top, 'url(#top)'))
            logo_color = mix(base, '#000000', .58)
            parts.append(f'<path d="{APPLE}" fill="{logo_color}" transform="translate(49,{y-16}) scale(10,6)" data-morph-unsupported="true"/>')
            logo_cutout = f'<path d="{APPLE}" fill="black" transform="translate(49,{y-16}) scale(10,6)"/>'
        foot = rect(18, y+height, 72, 4.5 if height > 23 else 1.2, 1)
        if front_only and height>23:
            foot = f'M18,{y+height}H90L86,{y+height+4.5}H22Z'
        parts.append(path(foot, '#25282b'))
        shell += foot
        for port in chassis.get('ports', {}).get('front', []):
            px = 12+84*port['u']
            py = y+height*port.get('v', .58)
            typ = port['type']
            if typ in ('usb_c', 'thunderbolt'):
                cut = rect(px-1.05, py-3, 2.1, 6, 1.0)
            elif typ in ('sd', 'sdxc'):
                cut = rect(px-4.0, py-.55, 8, 1.1, .3)
            elif typ in ('audio', 'headphone'):
                cut = rect(px-1.2, py-1.2, 2.4, 2.4, 1.2)
            elif typ in ('led', 'status_led'):
                parts.append(path(rect(px-.5, py-.5, 1, 1, .5), '#f0f1ed'))
                continue
            else:
                continue
            parts.append(path(cut, '#25282b'))
            holes.append(cut)
        if not chassis.get('ports', {}).get('front'):
            parts.append(path(rect(86, y+height*.55, 1.2, 1.2, .6), '#eff0ec'))
        if height > 23:
            for x in range(23, 87, 3):
                bottom_x = 54+(x-54)*.88
                fin = f'M{x},{y+height+1}H{x+.55}L{bottom_x+.55},{y+height+3.5}H{bottom_x}Z' if front_only else rect(x,y+height+1.3,.7,1.8,.3)
                parts.append(path(fin, '#596168'))
    else:
        profile = json.loads((MODELS/'profiles'/f'{device["id"]}.json').read_text())
        lid = next(panel['body_mm'] for panel in profile['panels'] if panel['name']=='Lid')
        display = profile['apple_mac']['display']
        notched = display.get('notch', False)
        scale = 72/lid['width']
        height = lid['height']*scale
        radius = lid['corner_radius']*scale
        sw, sh = (value*scale for value in profile['screen']['fit_box_mm'])
        cx, cy = profile['screen']['center_mm'][:2]
        sx, sy = 54+cx*scale-sw/2, 20+height/2-cy*scale-sh/2
        outer = rect(18, 20, 72, height, radius)
        glass = rect(18.2, 20.2, 71.6, height-.4, max(.2, radius-.2))
        corners = profile['screen'].get('corner_radii_mm', [profile['screen']['corner_radius_mm']]*4)
        screen = rect(sx, sy, sw, sh, [value*scale for value in corners])
        deck = f'M18,{20+height-.3}H90L102,82Q103,84 98,85H10Q5,84 6,82Z'
        lip_bottom = 85 if chassis.get('shape') == 'wedge' else 86 if device['family'] == 'macbook-air' else 87
        lip = f'M6,82H102V84Q102,{lip_bottom} 96,{lip_bottom}H12Q6,{lip_bottom} 6,84Z'
        parts.extend([path(outer, 'url(#metal)'), path(glass, '#20242a'), path(screen, 'url(#display)')])
        if notched:
            nw, nh = display['notch_width_mm']*scale, display['notch_height_mm']*scale
            notch = rect(54-nw/2, sy-.2, nw, nh+.2, min(.3, nh/3))
            parts.append(path(notch, '#20242a'))
            notch_restore = path(notch, 'white')
        parts.extend([path(deck, 'url(#top)'), path(lip, 'url(#metal)')])
        deck_depth = 84-(20+height)
        key_y, key_h = 21.5+height, deck_depth*.43
        def projected(u0,y0,u1,y1):
            w0 = 72+24*(y0-20-height)/deck_depth
            w1 = 72+24*(y1-20-height)/deck_depth
            return f'M{54+(u0-.5)*w0},{y0}L{54+(u1-.5)*w0},{y0}L{54+(u1-.5)*w1},{y1}L{54+(u0-.5)*w1},{y1}Z'
        keyboard_width = min(274,lid['width']-30)/lid['width']
        left,right = (1-keyboard_width)/2,(1+keyboard_width)/2
        keys = projected(left,key_y,right,key_y+key_h)
        neo = device['family']=='macbook-neo'
        parts.append(path(keys, mix(base,'#000000',.2) if neo else '#343940'))
        holes.extend([screen, keys])
        for row in range(6):
            spans = [(col/12+.007,(col+1)/12-.007) for col in range(12)]
            if row==5:spans=[(.015,.09),(.11,.185),(.205,.28),(.30,.69),(.71,.785),(.805,.88),(.90,.985)]
            for u0,u1 in spans:
                key = projected(left+u0*keyboard_width,key_y+(row+.15)*key_h/6,
                                left+u1*keyboard_width,key_y+(row+.8)*key_h/6)
                parts.append(path(key,mix(base,'#ffffff',.65) if neo else '#68737b'))
        if 'touchbar' in device['chassis_id']:
            parts.append(path(projected(left+.03,20.5+height,right-.03,21.1+height),'#28333c'))
        tp_mm = 159 if lid['width']>345 else 147 if lid['width']>335 else 130 if device['family']=='macbook-pro' else 121
        tp = tp_mm/lid['width']
        trackpad = projected((1-tp)/2,20+height+deck_depth*.66,(1+tp)/2,20+height+deck_depth*.96)
        parts.append(path(trackpad, mix(base, '#000000', .10)))
        camera_y = sy+nh/2 if notched else 20+(sy-20)/2
        parts.append(path(rect(53.75, camera_y-.25, .5, .5, .25), '#111a22'))
        if monochrome:
            shell = outer + deck + lip
            holes.append(trackpad)
    if monochrome:
        defs = f'<mask id="cutouts"><path d="{shell}" fill="white"/>'+''.join(path(h, 'black') for h in holes)+logo_cutout+notch_restore+'</mask>'
        parts = [f'<path d="{shell}" fill="currentColor" mask="url(#cutouts)"/>']
    title = escape(device['name'] + (' monochrome' if monochrome else ' '+color))
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108"><title>{title}</title><defs>{defs}</defs>'+''.join(parts)+'</svg>'


def write_artwork(text, target):
    target.write_text(text, encoding='utf-8')
    png = bytes(resvg_py.svg_to_bytes(svg_string=text, width=432, height=432))
    target.with_suffix('.png').write_bytes(png)
    image = Image.open(io.BytesIO(png)).convert('RGBA')
    image = image.crop(image.getbbox())
    image.thumbnail((120, 170), Image.Resampling.LANCZOS)
    thumb = Image.new('RGBA', (140, 180))
    thumb.alpha_composite(image, ((140-image.width)//2, (180-image.height)//2))
    out = ROOT / 'tmp/ref5/all_phones' / (target.stem+'.png')
    thumb.save(out)
    return out


def main():
    data = json.loads(CATALOG.read_text(encoding='utf-8'))
    path = ROOT / 'tmp/ref5/all_phones/catalog.json'
    catalog = json.loads(path.read_text(encoding='utf-8'))
    ids = {d['icon_id'] for d in data['devices']}
    catalog = [d for d in catalog if d['model'] not in ids]
    count = 0
    for device in data['devices']:
        folder = ROOT / 'device_icons_svg/apple' / ('pcs' if device['kind']=='pc' else 'laptops')
        folder.mkdir(parents=True, exist_ok=True)
        chassis = data['chassis'][device['chassis_id']]
        variants = []
        for color in device['finishes']:
            key = color.lower().replace(' ', '_')
            target = folder / f'ic_{device["icon_id"]}_{key}_icon.svg'
            thumb = write_artwork(svg(device, chassis, color), target)
            variants.append({'color': key, 'path': str(target), 'thumb': thumb.as_posix()})
            count += 1
        target = folder / f'ic_{device["icon_id"]}_monochrome_icon.svg'
        write_artwork(svg(device, chassis, device['finishes'][0], True), target)
        catalog.append({'model': device['icon_id'], 'brand': 'apple', 'kind': device['kind'],
                        'label': device['name'], 'variants': variants})
    path.write_text(json.dumps(catalog, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f'Wrote {len(ids)} Mac families, {count} color icons and {len(ids)} monochrome icons')


if __name__ == '__main__':
    main()
