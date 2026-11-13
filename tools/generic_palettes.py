"""Shared generic finishes: one tonal ramp per palette, applied to SVG and 3D tones.

Each graphite tone is placed on the graphite ramp by relative luminance and
replaced with the same ramp position in the target palette, so every generic
artwork and material uses exactly the values in assets/devices/generic_palettes.json.
"""
import json
import re

from catalog import ROOT

PALETTE_FILE = ROOT / "assets/devices/generic_palettes.json"
_DATA = json.loads(PALETTE_FILE.read_text(encoding="utf-8"))
ROLES = _DATA["roles"]
PALETTES = _DATA["palettes"]
BASE = PALETTES[0]
assert BASE["id"] == "graphite"


def _rgb(value):
    value = value.lstrip("#")
    return [int(value[i:i + 2], 16) / 255 for i in (0, 2, 4)]


def _hex(rgb):
    return "#" + "".join(f"{round(max(0, min(1, c)) * 255):02x}" for c in rgb)


def _linear(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def _encode(c):
    return c * 12.92 if c <= .0031308 else 1.055 * c ** (1 / 2.4) - .055


def _luminance(rgb):
    r, g, b = map(_linear, rgb)
    return .2126 * r + .7152 * g + .0722 * b


def _mix(a, b, t):
    # Interpolate in linear light so mid-ramp tones keep their brightness.
    return [_encode(_linear(x) + (_linear(y) - _linear(x)) * t) for x, y in zip(a, b)]


def palette(ident):
    return next(p for p in PALETTES if p["id"] == ident)


def map_hex(value, target, force=False):
    """Return the target-palette tone at the graphite ramp position of value."""
    if target["id"] == BASE["id"] and not force:
        return value.lower()
    source = [_rgb(BASE["stops"][role]) for role in ROLES]
    dest = [_rgb(target["stops"][role]) for role in ROLES]
    levels = [_luminance(c) for c in source]
    level = _luminance(_rgb(value))
    if level >= levels[0]:
        return _hex(_mix(dest[0], [1, 1, 1], (level - levels[0]) / max(1e-6, 1 - levels[0])))
    if level <= levels[-1]:
        return _hex(_mix(dest[-1], [0, 0, 0], (levels[-1] - level) / levels[-1]))
    for i in range(len(levels) - 1):
        if levels[i] >= level >= levels[i + 1]:
            return _hex(_mix(dest[i], dest[i + 1], (levels[i] - level) / (levels[i] - levels[i + 1])))
    raise AssertionError(value)


def recolor_svg(svg, tones, target, force=False):
    """Replace only the listed graphite tones; glass, lenses and flashes stay fixed."""
    mapping = {tone.lower(): map_hex(tone, target, force) for tone in tones}
    return re.sub(r"#[0-9a-fA-F]{6}\b", lambda m: mapping.get(m[0].lower(), m[0]), svg)


def generic_materials(kind):
    """Recolorable generic surfaces: slot role -> (material, graphite color, metal, rough)."""
    materials = {"back": ("Body", [146, 163, 179], .15, .45)}
    if kind == "pc":
        materials.update(stand=("Stand", [99, 117, 138], .15, .45), foot=("Foot", [99, 117, 138], .15, .45))
    else:
        materials["bar"] = ("Camera housing", [83, 103, 123], .15, .45)
    return materials


def model_finishes(materials):
    """3D finishes for a generic GLB whose material base colors are the graphite values.

    materials maps slot role -> (glb material name, stored base color 0-255, metal, rough).
    The viewer linearizes finish rgb, so Graphite stores the sRGB encoding of the GLB's
    own factor and remains a no-op; other palettes store their mapped sRGB tone.
    """
    slots = {role: name for role, (name, *_ ) in materials.items()}
    finishes = []
    for target in PALETTES:
        result = {}
        for role, (_, color, metal, rough) in materials.items():
            stored = [c / 255 for c in color[:3]]
            if target["id"] == BASE["id"]:
                rgb = [_encode(c) for c in stored]
            else:
                rgb = _rgb(map_hex(_hex(stored), target))
            result[role] = {"rgb": [round(c, 4) for c in rgb], "metal": metal, "rough": rough}
        finishes.append({"name": target["name"], "palette": target["id"], "materials": result})
    return slots, finishes
