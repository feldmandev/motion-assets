"""Arduino logo and UNO mark outlines.

Artwork derived from "ArduinoUno.svg" on Wikimedia Commons by Philipp Henkel,
licensed CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). The
Arduino logo is a trademark of Arduino AG. Coordinates are in the source SVG's
viewBox units (285.2 x 209, y down); `to_mm` maps them onto the Uno board frame.
"""
from __future__ import annotations

import re

import shapely
import shapely.geometry as sg
from shapely import affinity

RING = "M167.1,56.3c1.1-1.2,1.9-2.2,2.9-3.1,3.7-3.3,7.9-4.6,12.7-2.5,4.5,1.9,7,6.6,6,11.4-.9,4.4-5.2,7.8-9.8,8-4.3.1-7.6-1.8-10.3-4.9-.4-.5-.8-1-1.3-1.6-.4.4-.7.8-.9,1.1-2.9,3.6-6.5,5.7-11.3,5.4-4.7-.3-9.1-4.7-9.4-9.4-.4-6,4.2-10.9,10.5-11,4.2,0,7.5,2.1,10.1,5.4.3.4.6.7.9,1.2Z"
HOLES = ["M156.7,53.1c-4.4,0-7.6,2.8-7.9,6.4-.3,3.2,2.2,6.4,5.7,7.2,3.5.7,6.2-.7,8.3-3.2,3.2-3.8,3.1-3.2,0-7-1.7-2.1-4-3.3-6.2-3.4Z", "M178.4,53c-.5,0-.9,0-1.3,0-3.7.7-6,3.2-7.8,6.4-.1.2-.1.7,0,.9,1.6,2.7,3.5,5.1,6.7,6.1,3,1,5.7.2,7.8-2.2,1.9-2.1,2.3-4.6,1.1-7.1-1.3-2.7-3.7-3.9-6.5-4.1h0Z"]
MINUS = "M159.8,60.7c0,0,0,.2-.2.2h-6.5c0,0-.2,0-.2-.2v-2c0,0,0-.2.2-.2h6.5c0,0,.2,0,.2.2v2Z"
PLUS = "M181.2,58.8c0,0,0-.2-.2-.2h-1.9c0,0-.2,0-.2-.2v-1.9c0,0,0-.2-.2-.2h-2c0,0-.2,0-.2.2v1.9c0,0,0,.2-.2.2h-1.9c0,0-.2,0-.2.2v2c0,0,0,.2.2.2h1.9c0,0,.2,0,.2.2v1.9c0,0,0,.2.2.2h2c0,0,.2,0,.2-.2v-1.9c0,0,0-.2.2-.2h1.9c0,0,.2,0,.2-.2v-2Z"
UNO_GLYPHS = ["M202.5,65.7c-1.2,0-2.2-.3-2.8-.8-.6-.5-1-1.1-1.2-1.8,0-.3-.1-.7-.2-1.1,0-.4,0-.8,0-1.3v-6.5h1.2v6.5c0,1.5.2,2.6.7,3.1.5.5,1.2.7,2.1.7s1.9-.2,2.3-.7c.5-.5.7-1.6.7-3.1v-6.5h1.2v6.5c0,1.4-.2,2.4-.5,3-.6,1.3-1.7,1.9-3.5,1.9h0Z", "M217.6,65.5h-1.2l-5.9-9.3v9.3h-1v-11.3h1.1l5.8,9.3v-9.3h1.2v11.3Z", "M224.6,53.9c.7,0,1.4.1,2,.4.6.3,1.1.7,1.6,1.2.4.5.8,1.2,1,1.9.2.7.4,1.6.4,2.5s-.1,1.7-.4,2.5c-.2.7-.6,1.4-1,1.9-.4.5-1,.9-1.6,1.2-.6.3-1.3.4-2,.4s-1.4-.1-2-.4c-.6-.3-1.1-.7-1.6-1.2-.4-.5-.8-1.2-1-1.9-.2-.7-.4-1.6-.4-2.5s.1-1.7.4-2.5.6-1.4,1-1.9,1-.9,1.6-1.2c.6-.3,1.3-.4,2-.4ZM224.6,64.6c.5,0,1-.1,1.4-.3s.8-.5,1.1-.9c.3-.4.6-.9.7-1.5.2-.6.3-1.2.3-2s0-1.4-.3-2c-.2-.6-.4-1.1-.7-1.5-.3-.4-.7-.7-1.1-.9-.4-.2-.9-.3-1.4-.3s-1,.1-1.4.3c-.4.2-.8.5-1.1.9-.3.4-.6.9-.7,1.5-.2.6-.3,1.2-.3,2s0,1.4.3,2c.2.6.4,1.1.7,1.5.3.4.7.7,1.1.9.4.2.9.3,1.4.3h0Z"]
UNO_DOTS = [[225.2, 50.7], [223.5, 50.7], [221.7, 50.7], [219.9, 50.7], [218.2, 50.7], [216.4, 50.7], [214.6, 50.7], [212.8, 50.7], [211.1, 50.7], [209.3, 50.7], [207.5, 50.7], [205.8, 50.7], [204.0, 50.7], [202.2, 50.7], [225.3, 69.3], [227.0, 68.9], [228.6, 68.3], [230.0, 67.4], [231.3, 66.2], [232.3, 64.8], [233.1, 63.3], [233.5, 61.6], [233.7, 59.9], [233.5, 58.2], [233.0, 56.5], [232.3, 55.0], [231.2, 53.6], [230.0, 52.5], [228.5, 51.6], [226.9, 51.0], [225.2, 50.7], [223.5, 50.7], [200.3, 69.1], [198.6, 68.8], [197.0, 68.1], [195.6, 67.2], [194.4, 66.0], [193.4, 64.7], [192.6, 63.1], [192.2, 61.5], [192.1, 59.8], [192.2, 58.1], [192.7, 56.5], [193.5, 54.9], [194.5, 53.6], [195.8, 52.5], [197.3, 51.6], [198.8, 51.0], [200.5, 50.7], [202.2, 50.7], [225.2, 69.3], [223.5, 69.3], [221.7, 69.3], [219.9, 69.3], [218.2, 69.3], [216.4, 69.3], [214.6, 69.3], [212.8, 69.3], [211.1, 69.3], [209.3, 69.3], [207.5, 69.3], [205.8, 69.3], [204.0, 69.3], [202.2, 69.3]]

UNITS_PER_MM = 3.4825
BOARD_X0 = 32.5
BOARD_Y1 = 198.75


def svg_path_rings(d: str, steps: int = 12) -> list[list[tuple[float, float]]]:
    """Flatten an SVG path (M/L/H/V/C/S/Z, absolute or relative) into point rings."""
    tokens = re.findall(r"[MmLlHhVvCcSsZz]|-?(?:\d+\.?\d*|\.\d+)(?:e-?\d+)?", d)
    rings: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    x = y = sx = sy = 0.0
    last_c2 = None
    cmd = ""
    i = 0

    def nums(n: int) -> list[float]:
        nonlocal i
        vals = [float(t) for t in tokens[i:i + n]]
        i += n
        return vals

    while i < len(tokens):
        if re.fullmatch(r"[A-Za-z]", tokens[i]):
            cmd = tokens[i]
            i += 1
            if cmd in "Zz":
                if cur:
                    rings.append(cur)
                cur = []
                x, y = sx, sy
                last_c2 = None
                continue
        rel = cmd.islower()
        c = cmd.upper()
        if c == "M":
            nx, ny = nums(2)
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            if cur:
                rings.append(cur)
            cur = [(x, y)]
            sx, sy = x, y
            cmd = "l" if rel else "L"
            last_c2 = None
        elif c == "L":
            nx, ny = nums(2)
            x, y = (x + nx, y + ny) if rel else (nx, ny)
            cur.append((x, y))
            last_c2 = None
        elif c == "H":
            (nx,) = nums(1)
            x = x + nx if rel else nx
            cur.append((x, y))
            last_c2 = None
        elif c == "V":
            (ny,) = nums(1)
            y = y + ny if rel else ny
            cur.append((x, y))
            last_c2 = None
        elif c in "CS":
            if c == "C":
                a1, b1, a2, b2, ex, ey = nums(6)
                if rel:
                    a1, b1, a2, b2, ex, ey = x + a1, y + b1, x + a2, y + b2, x + ex, y + ey
            else:
                a2, b2, ex, ey = nums(4)
                if rel:
                    a2, b2, ex, ey = x + a2, y + b2, x + ex, y + ey
                a1, b1 = (2 * x - last_c2[0], 2 * y - last_c2[1]) if last_c2 else (x, y)
            for k in range(1, steps + 1):
                t = k / steps
                u = 1 - t
                cur.append((
                    u ** 3 * x + 3 * u * u * t * a1 + 3 * u * t * t * a2 + t ** 3 * ex,
                    u ** 3 * y + 3 * u * u * t * b1 + 3 * u * t * t * b2 + t ** 3 * ey,
                ))
            x, y = ex, ey
            last_c2 = (a2, b2)
    if cur:
        rings.append(cur)
    return rings


def _poly(d: str) -> sg.Polygon:
    return sg.Polygon(svg_path_rings(d)[0]).buffer(0)


def to_mm(geom):
    """Source SVG units (y down) -> Uno board millimetres (origin lower-left, y up)."""
    geom = affinity.translate(geom, -BOARD_X0, -BOARD_Y1)
    return affinity.scale(geom, xfact=1 / UNITS_PER_MM, yfact=-1 / UNITS_PER_MM, origin=(0, 0))


def logo_mm() -> sg.base.BaseGeometry:
    """Infinity mark with the - and + signs, positioned as on the reference board."""
    ring = _poly(RING)
    for hole in HOLES:
        ring = ring.difference(_poly(hole))
    return to_mm(shapely.unary_union([ring, _poly(MINUS), _poly(PLUS)]).buffer(0))


def uno_letters_mm() -> sg.base.BaseGeometry:
    glyphs = []
    for d in UNO_GLYPHS:
        rings = svg_path_rings(d)
        geom = sg.Polygon(rings[0]).buffer(0)
        for extra in rings[1:]:
            geom = geom.symmetric_difference(sg.Polygon(extra).buffer(0))
        glyphs.append(geom)
    return to_mm(shapely.unary_union(glyphs))


def uno_dots_mm(radius: float = 0.7) -> sg.base.BaseGeometry:
    return to_mm(shapely.unary_union([sg.Point(x, y).buffer(radius, quad_segs=6) for x, y in UNO_DOTS]))
