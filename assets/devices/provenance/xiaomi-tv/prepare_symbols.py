"""Use the same Material Symbols outlines in the model and its vector icon."""
import json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools import subset
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.transformPen import TransformPen

out = Path(__file__).resolve().parent
source = out.parents[2] / 'symbols'
font = TTFont(source / 'material_symbols_rounded.ttf')
axes = {a.axisTag: {'FILL': 1, 'wght': 700, 'GRAD': 0, 'opsz': 24}.get(a.axisTag, a.defaultValue) for a in font['fvar'].axes}
font = instantiateVariableFont(font, axes, inplace=True)
codes = {'home': 0xe9b2, 'back': 0xe5c4, 'power': 0xf8c7, 'add': 0xe145, 'remove': 0xe15b}
subsetter = subset.Subsetter()
subsetter.populate(unicodes=list(codes.values()))
subsetter.subset(font)
font.save(out / 'remote-symbols.ttf')

navigation_axes = dict(axes, wght=550)
navigation = instantiateVariableFont(TTFont(source / 'material_symbols_rounded.ttf'), navigation_axes, inplace=True)
navigation_subset = subset.Subsetter()
navigation_subset.populate(unicodes=[code for name, code in codes.items() if name != 'power'])
navigation_subset.subset(navigation)
navigation.save(out / 'navigation-symbols.ttf')
glyphs = font.getGlyphSet()
paths = {}
for name, code in codes.items():
    active_font = font if name == 'power' else navigation
    glyphs = active_font.getGlyphSet()
    glyph = glyphs[active_font.getBestCmap()[code]]
    bounds = BoundsPen(glyphs)
    glyph.draw(bounds)
    x0, y0, x1, y1 = bounds.bounds
    scale = 1 / max(x1 - x0, y1 - y0)
    pen = SVGPathPen(glyphs)
    glyph.draw(TransformPen(pen, (scale, 0, 0, -scale, -(x0 + x1) * scale / 2, (y0 + y1) * scale / 2)))
    paths[name] = pen.getCommands()
(out / 'symbol-paths.json').write_text(json.dumps(paths), encoding='utf-8')
labels = {}
for name, word, filename, width, height in (
    ('netflix', 'NETFLIX', 'arialnb.ttf', 10.5, 2.9),
    ('prime', 'prime video', 'arialbd.ttf', 10.6, 2.05),
    ('youtube', 'YouTube', 'arialnb.ttf', 8.2, 2.3),
    ('apps', 'APPS', 'arialbd.ttf', 4.8, 2.1),
    ('tvplus', 'TV+', 'arialbd.ttf', 4.3, 2.2),
    ('tvbrand', 'xiaomi', 'arialbd.ttf', 4.8, 1.1),
    ('brand', 'xiaomi', 'arialbd.ttf', 10.4, 2.9),
):
    label_font = TTFont(Path('C:/Windows/Fonts') / filename)
    label_glyphs = label_font.getGlyphSet()
    cmap = label_font.getBestCmap()
    bounds = BoundsPen(label_glyphs)
    x = 0
    for character in word:
        glyph_name = cmap[ord(character)]
        label_glyphs[glyph_name].draw(TransformPen(bounds, (1, 0, 0, 1, x, 0)))
        x += label_font['hmtx'][glyph_name][0]
    x0, y0, x1, y1 = bounds.bounds
    sx, sy = width / (x1 - x0), -height / (y1 - y0)
    pen = SVGPathPen(label_glyphs)
    x = 0
    for character in word:
        glyph_name = cmap[ord(character)]
        label_glyphs[glyph_name].draw(TransformPen(pen, (sx, 0, 0, sy, (x - (x0 + x1) / 2) * sx, -(y0 + y1) * sy / 2)))
        x += label_font['hmtx'][glyph_name][0]
    labels[name] = pen.getCommands()
(out / 'label-paths.json').write_text(json.dumps(labels), encoding='utf-8')
print('Prepared matching outlined symbols for Blender and SVG.')
