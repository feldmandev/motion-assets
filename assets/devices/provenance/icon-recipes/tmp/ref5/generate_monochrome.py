"""Derive one tintable, camera-cutout SVG from each phone's current artwork."""
from pathlib import Path
import copy, io, json, re, sys
import xml.etree.ElementTree as ET
from fontTools.svgLib.path import parse_path
from fontTools.pens.boundsPen import BoundsPen
from PIL import Image
import resvg_py

ROOT = Path(__file__).resolve().parents[2]
NS = 'http://www.w3.org/2000/svg'
ET.register_namespace('', NS)
CATALOG = json.loads((ROOT / 'tmp/ref5/all_phones/catalog.json').read_text())

def brightness(color):
    if not color.startswith('#'): return 0
    color = color[1:]
    if len(color) == 3: color = ''.join(c * 2 for c in color)
    return sum(int(color[i:i+2], 16) * weight for i, weight in zip((0, 2, 4), (.2126, .7152, .0722)))

def convert(source):
    original = ET.fromstring(source.read_text(encoding='utf-8'))
    gradients = {g.get('id'): [s.get('stop-color', '#000000') for s in g] for g in original.iter(f'{{{NS}}}linearGradient')}
    root = ET.Element(f'{{{NS}}}svg', {k: original.get(k) for k in ('width', 'height', 'viewBox')})
    defs = ET.SubElement(root, f'{{{NS}}}defs')
    for d in original.findall(f'{{{NS}}}defs'):
        for child in d:
            if child.tag.endswith('clipPath'): defs.append(copy.deepcopy(child))
    mask = ET.SubElement(defs, f'{{{NS}}}mask', {'id': 'phone-cutouts', 'maskUnits': 'userSpaceOnUse', 'x': '0', 'y': '0', 'width': '108', 'height': '108', 'style': 'mask-type:luminance'})
    paths = list(original.iter(f'{{{NS}}}path'))
    bounds = {}
    for path in paths:
        pen = BoundsPen(None); parse_path(path.get('d', ''), pen)
        bounds[id(path)] = pen.bounds
    first = True
    outline_boxes = []
    pixel_bars = []
    pixel_flash = False
    body_box = None
    def visit(node):
        nonlocal first, body_box, pixel_flash
        tag = node.tag.split('}')[-1]
        if tag in ('defs', 'title', 'desc'): return None
        out = copy.deepcopy(node)
        for key in ('opacity', 'fill-opacity', 'stroke-opacity', 'filter'): out.attrib.pop(key, None)
        if tag == 'g' and source.stem.startswith(('ic_nothing_phone_3_', 'ic_nothing_phone_3a_lite_')) and 'scale(' in node.get('transform', ''):
            return None  # Back tiles/spine overwhelm the simple monochrome silhouette.
        if tag == 'g' and source.stem.startswith('ic_nothing_') and node.get('data-detail') == 'rear-contour':
            return None  # Decorative transparent-back wiring is not a camera or Glyph aperture.
        if tag == 'path' and node.get('data-detail') == 'visor-panel':
            return None
        if source.stem.startswith('ic_nothing_phone_4a_') and node.get('data-detail') == 'glyph-backing':
            return None  # Keep the seven Glyph apertures separate in the tintable mask.
        if tag == 'g' and source.stem.startswith(('ic_nothing_cmf_', 'ic_nothing_phone_3a_lite_')):
            if node.get('data-detail') in ('panel', 'screw'):
                return None  # Accessory seams and screws crowd the camera silhouette.
            if node.get('data-detail') == 'dial':
                out[:] = [copy.deepcopy(node[0])]
                out[0].set('fill', 'none'); out[0].set('stroke', '#000000'); out[0].set('stroke-width', '.55')
                if source.stem.startswith('ic_nothing_cmf_phone_1_'):
                    out.set('transform', 'translate(-.5 0)')  # Keep the dial ring clear of the rounded body edge.
                return out
        if tag in ('g', 'svg'):
            if re.match(r'ic_pixel_[678](?:_|a_)', source.stem):
                out.attrib.pop('clip-path', None)  # Bar cuts already fit the body; avoid clipping the mask edges.
            out[:] = []
            for child in node:
                transformed = visit(child)
                if transformed is not None: out.append(transformed)
            return out
        fill = node.get('fill', '#000000')
        if first:
            first = False; body_box = bounds.get(id(node)); out.set('fill', '#ffffff'); return out
        box = bounds.get(id(node))
        area = (box[2]-box[0])*(box[3]-box[1]) if box else 0
        colors = gradients.get(fill.removeprefix('url(#').removesuffix(')'), [])
        dark_glass = colors and min(map(brightness, colors)) < 55 and max(map(brightness, colors)) < 155
        if box and re.match(r'ic_nothing_phone_3a_(?!pro_|lite_)', source.stem) and colors and not dark_glass and area > 45 and (box[2]-box[0]) > 2*(box[3]-box[1]):
            return None  # The glass capsule itself is the cutout; omit its close-fitting metal bevel.
        if box and re.match(r'ic_nothing_phone_4a_(?!pro_)', source.stem) and outline_boxes and not colors and area < 5 and box[3] < outline_boxes[0][1] + .3:
            out.set('transform', 'translate(0 -.85)')  # Flash clears the mono housing stroke.
        if source.stem.startswith(('ic_xiaomi_12t_', 'ic_xiaomi_12t_pro_')) and dark_glass and area > 45:
            return None  # The upper glass tile is not the round camera aperture.
        if re.match(r'ic_pixel_[678](?:_|a_)', source.stem) and box:
            if abs(box[0] - body_box[0]) < .1 and abs(box[2] - body_box[2]) < .1 and 2 < box[3] - box[1] < (body_box[3] - body_box[1]) / 2:
                if box[1] <= body_box[1] + .1:
                    return None  # Two-tone top finish is part of the solid body.
                if box in pixel_bars: return None  # Extraction may include a base fill.
                pixel_bars.append(box)
                return ET.Element(f'{{{NS}}}path', {'d': f'M{box[0]},{box[1]}H{box[2]}M{box[0]},{box[3]}H{box[2]}', 'fill': 'none', 'stroke': '#000000', 'stroke-width': '.55'})
        if box and any(b[0] <= box[0] and b[1] <= box[1] and b[2] >= box[2] and b[3] >= box[3] for b in pixel_bars):
            if not colors and area < 8: pixel_flash = True
            if source.stem.startswith('ic_pixel_8_pro_') and colors:
                b = pixel_bars[0]
                return ET.Element(f'{{{NS}}}rect', {'x': '42', 'y': str(b[1]+1.67), 'width': '18.5', 'height': str(b[3]-b[1]-3.34), 'rx': '2.9', 'fill': '#000000'})
            out.set('fill', '#000000')
            if box[0] < body_box[0]+3:
                out.set('transform', f'translate({body_box[0]+3-box[0]} 0)')
            return out
        # Large metal/back panels become thin cutout contours; glass, logos,
        # flashes, lenses and Glyph marks become solid transparent cutouts.
        inner_lenses = False
        if box and dark_glass and area > 45:
            for inner in paths[paths.index(node)+1:]:
                ib = bounds[id(inner)]
                ic = gradients.get(inner.get('fill', '').removeprefix('url(#').removesuffix(')'), [])
                if ib and ic and min(map(brightness, ic)) < 55 and max(map(brightness, ic)) < 155:
                    ia = (ib[2]-ib[0])*(ib[3]-ib[1])
                    if 5 < ia < area*.6 and box[0] <= ib[0] and box[1] <= ib[1] and box[2] >= ib[2] and box[3] >= ib[3]:
                        inner_lenses = True; break
        if area > 45 and colors and (not dark_glass or inner_lenses):
            for outer in outline_boxes:
                centred = abs((box[0]+box[2]-outer[0]-outer[2])/2) < .65 and abs((box[1]+box[3]-outer[1]-outer[3])/2) < .65
                nested = outer[0] <= box[0] and outer[1] <= box[1] and outer[2] >= box[2] and outer[3] >= box[3]
                same_housing = (box[2]-box[0])/(outer[2]-outer[0]) > .7 and (box[3]-box[1])/(outer[3]-outer[1]) > .7
                if centred and nested and same_housing:
                    return None  # One contour for the housing, not both bevel layers.
            outline_boxes.append(box)
            out.set('fill', 'none'); out.set('stroke', '#000000'); out.set('stroke-width', '.55'); out.set('stroke-linejoin', 'round')
        else:
            if fill != 'none': out.set('fill', '#000000')
            if 'stroke' in out.attrib: out.set('stroke', '#000000')
        return out
    for child in original:
        transformed = visit(child)
        if transformed is not None: mask.append(transformed)
    if pixel_bars and not pixel_flash:
        b = pixel_bars[0]
        ET.SubElement(mask, f'{{{NS}}}circle', {'cx': str(body_box[2]-3.75), 'cy': str((b[1]+b[3])/2), 'r': '.8', 'fill': '#000000'})
    for child in original:
        if child.tag.split('}')[-1] in ('title', 'desc'): root.append(copy.deepcopy(child))
    ET.SubElement(root, f'{{{NS}}}desc').text = 'Derived monochrome artwork: currentColor fill with transparent camera, logo and detail cutouts. Silhouette retained; details simplified.'
    ET.SubElement(root, f'{{{NS}}}rect', {'width': '108', 'height': '108', 'fill': 'currentColor', 'mask': 'url(#phone-cutouts)'})
    prefix = source.stem + '-'
    for node in root.iter():
        for key, value in list(node.attrib.items()):
            if key == 'id': node.set(key, prefix + value)
            elif 'url(#' in value: node.set(key, value.replace('url(#', 'url(#' + prefix))
    return ET.tostring(root, encoding='unicode') + '\n'

def source_variant(device):
    # A light finish separates dark camera glass from finish-colored housings.
    return next((v for v in device['variants'] if re.search(r'white|silver|slv|chalk|cloud|starlight|beige|beg|sand|gold|cream|yellow', v['color'])), device['variants'][0])

if __name__ == '__main__':
    sample = '--sample' in sys.argv
    phones = CATALOG
    if '--tablets' in sys.argv: phones = [d for d in phones if d['kind'] == 'tablet']
    models = [arg for arg in sys.argv[1:] if not arg.startswith('--')]
    if models: phones = [d for d in phones if d['model'] in models]
    if sample:
        names = ['pixel_8_pro', 'galaxy_s25', 'oneplus_15', 'oppo_find_x9', 'nothing_phone_3a', 'xiaomi_mi_11_ultra', 'redmi_note_14_pro', 'poco_f7_pro', 'honor_magic7_pro', 'motorola_razr_40', 'apple_iphone_11', 'apple_iphone_17_pro_max']
        phones = [d for d in phones if d['model'] in names]
    samples = []
    for d in phones:
        source = Path(source_variant(d)['path']); svg = convert(source)
        target = source.parent / f'ic_{d["model"]}_monochrome_icon.svg'
        if sample:
            target = ROOT / 'tmp/ref5/monochrome_samples' / target.name; target.parent.mkdir(exist_ok=True)
        target.write_text(svg, encoding='utf-8'); ET.fromstring(svg)
        png = resvg_py.svg_to_bytes(svg_string=svg, width=648, height=648)
        im = Image.open(io.BytesIO(png)).convert('RGBA'); assert im.getbbox(), target
        assert im.getextrema()[:3] == ((0,0),(0,0),(0,0)), target
        im = im.crop(im.getbbox()); im.thumbnail((120,170),Image.Resampling.LANCZOS)
        thumb = Image.new('RGBA',(140,180)); thumb.alpha_composite(im,((140-im.width)//2,(180-im.height)//2))
        thumb.save(target.with_suffix('.png') if sample else ROOT / 'tmp/ref5/all_phones' / (target.stem+'.png'))
        samples.append({'label': d['label'], 'svg': svg})
    if sample:
        html = '<!doctype html><html><head><style>body{margin:0;font-family:Segoe UI,sans-serif;color:#65558f}.grid{display:grid;grid-template-columns:repeat(4,1fr);gap:12px}.card{text-align:center;background:#eee8f1;border-radius:20px;padding:12px}.card svg{width:100%;height:170px}.label{font-size:13px;color:#25212c}</style></head><body><div class="grid">'
        for d in samples: html += '<div class="card">'+d['svg'].replace('viewBox="0 0 108 108"','viewBox="30 24 48 60"')+'<div class="label">'+d['label']+'</div></div>'
        html += '</div></body></html>'
        (ROOT / 'tmp/ref5/monochrome_samples/preview.html').write_text(html,encoding='utf-8')
    print('Rendered and verified', len(phones), 'monochrome devices' + (' (sample)' if sample else ''))

