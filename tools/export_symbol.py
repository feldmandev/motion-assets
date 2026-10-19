"""Export an SVG from the pinned variable font, with the requested axes."""
import argparse
import json
from pathlib import Path
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name")
    parser.add_argument("--style", choices=["rounded", "outlined", "sharp"], default="rounded")
    parser.add_argument("--fill", type=float, choices=[0, 1], default=1)
    parser.add_argument("--weight", type=float, default=400)
    parser.add_argument("--grade", type=float, default=0)
    parser.add_argument("--size", type=float, default=24)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    catalog = json.loads((ROOT / "assets/symbols/catalog.json").read_text())
    codepoint = catalog["styles"][args.style][args.name]
    font = TTFont(ROOT / f"assets/symbols/material_symbols_{args.style}.ttf")
    axes = {"FILL": args.fill, "wght": args.weight, "GRAD": args.grade, "opsz": args.size}
    for axis in font["fvar"].axes:
        if not axis.minValue <= axes[axis.axisTag] <= axis.maxValue:
            raise ValueError(f"{axis.axisTag} outside font range")
    glyphs = font.getGlyphSet(location=axes)
    pen = SVGPathPen(glyphs)
    glyphs[font.getBestCmap()[codepoint]].draw(pen)
    units = font["head"].unitsPerEm
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 {units} {units}"><path transform="translate(0 {units}) scale(1 -1)" fill="currentColor" d="{pen.getCommands()}"/></svg>\n')


if __name__ == "__main__":
    main()
