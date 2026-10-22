"""Repeatable logo-fill-only postpass; never regenerate geometry or previews."""
import hashlib
import json
import re
import sys
from pathlib import Path

from svgelements import Path as SVGPath

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from generate_galaxy_s25_s26_svgs import logo_tone

PATH_RE = re.compile(r'<path\b[^>]*?/?>')
FLAT = {'#fff', '#ffffff', '#111', '#111111', '#000', '#000000', '#000000ff', '#ffffffff'}
LOWER_G = {'pixel_4', 'pixel_4_xl', 'pixel_4_a', 'pixel_4_a_5g', 'pixel_5', 'pixel_5_a'}


def marks(svg, brand, kind, model):
    paths = PATH_RE.findall(svg)
    if brand == 'samsung':
        return [] if model.startswith('galaxy_z_') else paths[-1:]
    if brand == 'pixel' and kind != 'laptop':
        result = []
        for p in paths:
            d = re.search(r'\bd="([^"]*)"', p)[1]
            fill = re.search(r'\bfill="([^"]*)"', p)
            if len(d) < 400 or not fill or not fill[1].startswith('#'):
                continue
            x0, y0, x1, y1 = SVGPath(d).bbox()
            w, h = x1 - x0, y1 - y0
            if 2 < w < 14 and .85 < w / h < 1.15 and 45 <= (y0 + y1) / 2 <= 76:
                result.append(p)
        return result
    return [p for p in paths if 'fill-rule="evenodd"' in p]


def tint_pixel(svg):
    """Use after a Pixel finish recolor, including when a template is already tinted."""
    found = marks(svg, 'pixel', 'phone', '')
    assert len(found) == 1, 'Expected one extracted G'
    return tint(svg, found[0])


def tint(svg, mark):
    # g1/body is the retained body palette; its middle stop is the finish RGB.
    body_path = next(p for p in PATH_RE.findall(svg.split('</defs>')[-1]) if 'fill="url(#' in p)
    gid = re.search(r'fill="url\(#([^)]+)\)"', body_path)[1]
    body = re.search(r'<(?:linear|radial)Gradient\b[^>]*\bid="' + gid + r'"[^>]*>(.*?)</(?:linear|radial)Gradient>', svg, re.S)
    stops = re.findall(r'stop-color="(#[0-9a-fA-F]{6})"', body[1])
    mid = stops[len(stops) // 2] if len(stops) > 2 else stops[0]
    new = re.sub(r'\bfill="[^"]*"', f'fill="{logo_tone(mid)}"', mark, count=1)
    return svg.replace(mark, new, 1)


def lower_pixel(svg):
    mark, = marks(svg, 'pixel', 'phone', '')
    # Transform only the mark; preserve the extracted path and its stylized size.
    body = next((p for p in PATH_RE.findall(svg.split('</defs>')[-1]) if 'fill="url(#' in p), PATH_RE.findall(svg)[0])
    _, y0, _, y1 = SVGPath(re.search(r'\bd="([^"]*)"', body)[1]).bbox()
    _, g0, _, g1 = SVGPath(re.search(r'\bd="([^"]*)"', mark)[1]).bbox()
    dy = y0 + .8 * (y1 - y0) - (g0 + g1) / 2
    bare = re.sub(r'\s+transform="[^"]*"', '', mark)
    new = re.sub(r'\s*/>$', f' transform="translate(0 {dy:.4f})"/>', bare)
    return svg.replace(mark, new, 1)


def main():
    prior = json.loads((HERE / 'logo-changes.json').read_text())
    protected = {c['path']: c['after_sha256'] for c in prior}
    report_path = HERE / 'logo-tone-changes.json'
    previous = json.loads(report_path.read_text()) if report_path.exists() else []
    completed = {c['path']: c for c in previous}
    audit = json.loads((HERE / 'logo-audit.json').read_text())
    families = sorted(audit['families'], key=lambda f: -len(f['model']))
    colors = {v['path']: color for f in families for color, v in f['variants'].items()}
    changes, pending = [], []
    for path in sorted((ROOT / 'device_icons_svg').rglob('*.svg')):
        if '_app_' in path.name:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel in protected:
            expected = protected[rel]
            assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, rel
            continue
        family = next((f for f in families if path.name.startswith('ic_' + f['model'] + '_')), None)
        if not family:
            continue
        monochrome = 'monochrome' in path.name
        if monochrome and family['model'] not in LOWER_G:
            continue
        before = path.read_bytes()
        svg = before.decode('utf8')
        found = marks(svg, family['brand'], path.parent.name.rstrip('s'), family['model'])
        if len(found) != 1:
            continue
        mark = found[0]
        old_fill = re.search(r'\bfill="([^"]*)"', mark)[1]
        lower = family['model'] in LOWER_G
        if old_fill.lower() not in FLAT and rel not in completed and not lower:
            continue
        needs_tint = old_fill.lower() in FLAT or completed.get(rel, {}).get('before_fill', '').lower() in FLAT
        after = tint(svg, mark) if not monochrome and rel not in protected and needs_tint else svg
        if lower:
            after = lower_pixel(after)
        if after == svg:
            if rel in completed:
                completed[rel]['after_sha256'] = hashlib.sha256(before).hexdigest()
            continue
        new = marks(after, family['brand'], path.parent.name.rstrip('s'), family['model'])[0]
        # Remove only the logo fill attribute, retaining every other byte, including geometry.
        nonlogo = svg.replace(mark, '', 1)
        assert nonlogo == after.replace(new, '', 1), rel
        assert re.search(r'\bd="([^"]*)"', mark)[1] == re.search(r'\bd="([^"]*)"', new)[1], rel
        pending.append((path, after.encode('utf8')))
        record = dict(path=rel, model=family['model'], color=colors.get(rel, 'default'), before_fill=old_fill,
                      fill=re.search(r'\bfill="([^"]*)"', new)[1],
                      before_sha256=hashlib.sha256(before).hexdigest(),
                      after_sha256=hashlib.sha256(after.encode('utf8')).hexdigest(),
                      non_logo_sha256=hashlib.sha256(nonlogo.encode('utf8')).hexdigest(),
                      placement='G center at 80% of body height' if lower else 'inherited',
                      reason='Authorized restrained finish-tinted default from retained body palette; explicit reference fills retained')
        changes.append(record)
        completed.setdefault(rel, record)
        completed[rel]['after_sha256'] = record['after_sha256']
    for path, data in pending:
        path.write_bytes(data)
    for rel, expected in protected.items():
        assert hashlib.sha256((ROOT / rel).read_bytes()).hexdigest() == expected, rel
    report_path.write_text(json.dumps(list(completed.values()), indent=2) + '\n', encoding='utf8')
    print(f'Changed {len(changes)} SVGs; {len(completed)} completion records; all prior reference fixes preserved exactly.')


if __name__ == '__main__':
    main()
