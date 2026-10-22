"""Draw Galaxy S25 / S26 series device icons in the Pixel Tips icon style.

These are NOT vendor extractions. They are drawn from measurements of Samsung's
official renders (design.samsung.com S26 design story, Samsung newsroom and
GSMArena official images), using the Pixel Tips conventions:

  * 108x108 viewport, 30x50 body at (39, 29)
  * body: vertical 3-stop linear gradient (0 / 0.48 / 1, y 36.73 -> 74.07)
  * camera hardware: horizontal metal gradient; lens glass: tinted -> near-black
  * flat brand mark near the bottom (here the SAMSUNG wordmark, Wikimedia Commons outline)

Geometry is in fractions of the real body width W, measured from the renders
(camera centres/diameters are measured from the top-left of the back).
Body colours are sampled top/mid/bottom from the official colour renders,
then rendered with richer Pixel-style gradients.
"""
import os
import re

from svgelements import Matrix, Path

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "device_icons_svg", "samsung", "phones")

X0, Y0, BW, BH = 39.0, 29.0, 30.0, 50.0
GRAD_Y1, GRAD_Y2 = 36.73, 74.07

# ---------------------------------------------------------------------------- colour helpers


def rgb(h):
    h = h.lstrip("#")
    return [int(h[i:i + 2], 16) for i in (0, 2, 4)]


def hexc(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return hexc([a[i] + (b[i] - a[i]) * t for i in range(3)])


def lum(h):
    r, g, b = (v / 255 for v in rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def logo_tone(mid):
    """Restrained printed/metal tone carrying the retained back-finish hue."""
    muted = mix(mid, hexc([lum(mid) * 255] * 3), .55)
    return mix(muted, "#000000", .28) if lum(mid) >= .50 else mix(muted, "#ffffff", .32)


def pixel_palette(top, mid, bot):
    """Keep sampled hues, with richer colour and a clearer Pixel-style light falloff."""
    def vibrant(h):
        grey = lum(h) * 255
        return hexc([grey + (v - grey) * 1.28 for v in rgb(h)])

    top, mid, bot = map(vibrant, (top, mid, bot))
    return mix(top, "#ffffff", .22), mid, mix(bot, "#000000", .18 if lum(mid) > .85 else .30)


def f(v):
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


# ---------------------------------------------------------------------------- shapes


def rounded_rect(x, y, w, h, r):
    r = min(r, w / 2, h / 2)
    return (f"M{f(x + r)},{f(y)}H{f(x + w - r)}A{f(r)},{f(r)} 0 0 1 {f(x + w)},{f(y + r)}"
            f"V{f(y + h - r)}A{f(r)},{f(r)} 0 0 1 {f(x + w - r)},{f(y + h)}"
            f"H{f(x + r)}A{f(r)},{f(r)} 0 0 1 {f(x)},{f(y + h - r)}"
            f"V{f(y + r)}A{f(r)},{f(r)} 0 0 1 {f(x + r)},{f(y)}Z")


def circle(cx, cy, r):
    return (f"M{f(cx - r)},{f(cy)}A{f(r)},{f(r)} 0 1 1 {f(cx + r)},{f(cy)}"
            f"A{f(r)},{f(r)} 0 1 1 {f(cx - r)},{f(cy)}Z")


# SAMSUNG wordmark (Wikimedia Commons "Samsung wordmark.svg"), flattened to absolute coordinates.
_WM_D = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "samsung_wordmark_path.txt")).read().strip()
_WM_M = Matrix("translate(558.9328,88.5098)") * Matrix("matrix(12.944053,0,0,-12.944053,-540.03625,1620.0233)")


def wordmark(cx, cy, width):
    p = Path(_WM_D) * _WM_M
    x0, y0, x1, y1 = p.bbox()
    s = width / (x1 - x0)
    p = p * Matrix(f"translate({-(x0 + x1) / 2},{-(y0 + y1) / 2})") * Matrix(f"scale({s})") * Matrix(f"translate({cx},{cy})")
    d = p.d()
    return re.sub(r"-?\d+\.\d+", lambda m: f(float(m.group())), d)


# ---------------------------------------------------------------------------- model geometry
# lenses: (cx, cy, outer d) in W; island: (x0, y0, x1, y1) capsule in W; flash: (cx, cy, d)

MODELS = {
    "s25": dict(r=0.145, lenses=[(.180, .181, .203), (.180, .410, .203), (.180, .640, .203)],
                flash=(.40, .29, .042), island=None, wm=.33),
    "s25_plus": dict(r=0.145, lenses=[(.170, .171, .191), (.170, .386, .191), (.170, .602, .191)],
                     flash=(.38, .275, .04), island=None, wm=.31),
    "s25_ultra": dict(r=0.09, lenses=[(.185, .184, .208), (.185, .419, .208), (.185, .654, .208),
                                      (.401, .184, .120), (.401, .420, .120)],
                      flash=(.401, .302, .038), island=None, wm=.31),
    "s25_edge": dict(r=0.145, lenses=[(.191, .191, .188), (.191, .425, .188)],
                     flash=(.191, .593, .05), island=(.046, .046, .336, .758), island_kind="metal", wm=.31),
    "s25_fe": dict(r=0.145, lenses=[(.175, .175, .181), (.175, .396, .181), (.175, .616, .181)],
                   flash=(.39, .27, .04), island=None, wm=.31),
    "s26": dict(r=0.145, lenses=[(.197, .192, .190), (.197, .415, .190), (.197, .640, .190)],
                flash=(.40, .30, .045), island=(.047, .042, .347, .790), island_kind="body", wm=.33),
    "s26_plus": dict(r=0.145, lenses=[(.183, .176, .180), (.183, .389, .180), (.183, .604, .180)],
                     flash=(.377, .275, .042), island=(.043, .036, .323, .744), island_kind="body", wm=.31),
    "s26_ultra": dict(r=0.095, lenses=[(.195, .188, .197), (.195, .420, .197), (.195, .652, .197),
                                       (.427, .191, .115), (.427, .423, .115)],
                      flash=(.416, .305, .038), island=(.045, .035, .345, .805), island_kind="body", wm=.30),
    "s26_fe": dict(r=0.145, lenses=[(.173, .172, .178), (.173, .391, .178), (.173, .611, .178)],
                   flash=(.42, .27, .04), island=(.040, .035, .306, .748), island_kind="body", wm=.31),
}

# ---------------------------------------------------------------------------- colours (top, mid, bottom)
S25_COLORS = {
    "icyblue": ("#e8eefa", "#c8cede", "#b9c2d3"), "mint": ("#eaf9e6", "#cbdbd0", "#bdcfc3"),
    "navy": ("#436193", "#14264b", "#061532"), "silver_shadow": ("#d6d7db", "#919296", "#6e6e70"),
    "pinkgold": ("#faece3", "#e4d2c6", "#ddcbbd"), "coralred": ("#fd8f8e", "#f26f74", "#eb6269"),
    "blueblack": ("#5b5f6a", "#2a2e39", "#1c202b"),
}
S26_COLORS = {
    "white": ("#ffffff", "#f8f7fc", "#f2f2f4"), "sky_blue": ("#e0ebf5", "#c8d8e5", "#bed1df"),
    "cobalt_violet": ("#8888a4", "#484864", "#343450"), "black": ("#585b60", "#2b2e33", "#1d2025"),
    "pink_gold": ("#fef1e9", "#eddfd4", "#ead9cf"), "silver_shadow": ("#d9d9db", "#9e9ea0", "#828385"),
}
COLORS = {
    "s25": S25_COLORS,
    "s25_plus": S25_COLORS,
    "s25_ultra": {
        "titanium_whitesilver": ("#f3f3f5", "#ccccce", "#bebec0"), "titanium_gray": ("#e3deda", "#a49f9b", "#8e8985"),
        "titanium_silverblue": ("#d0d4e0", "#989eae", "#858a9d"), "titanium_black": ("#5e5f63", "#27282c", "#18191d"),
        "titanium_pinkgold": ("#faece3", "#e4d2c6", "#ddcbbd"), "titanium_jadegreen": ("#d7ddcf", "#9fa597", "#8c9284"),
        "titanium_jetblack": ("#5d6069", "#27282c", "#18191d"),
    },
    "s25_edge": {
        "titanium_silver": ("#f8f8f8", "#d3d3d3", "#c1c1c1"), "titanium_icyblue": ("#edf4ff", "#cdd3e1", "#bdc6d7"),
        "titanium_jetblack": ("#61646d", "#292a2e", "#1a1b1f"),
    },
    "s25_fe": {
        "white": ("#fcfbfc", "#f8f7f8", "#f6f4f5"), "icyblue": ("#e7e8fa", "#dbdcee", "#d4d3e5"),
        "navy": ("#465376", "#303d60", "#2a375a"), "jetblack": ("#3f4045", "#2d2e33", "#28292e"),
    },
    "s26": S26_COLORS,
    "s26_plus": S26_COLORS,
    "s26_ultra": {
        "white": ("#ffffff", "#fbfbfd", "#f7f8fa"), "sky_blue": ("#e6f0f9", "#d2e0ea", "#c9dbe8"),
        "cobalt_violet": ("#a1a2b7", "#5d5d79", "#414260"), "black": ("#696d70", "#393c41", "#262b2f"),
        "pink_gold": ("#fcf2e9", "#eee0d5", "#e9dacd"), "silver_shadow": ("#d8d9db", "#9d9ea0", "#808183"),
    },
    "s26_fe": {
        "pistachio": ("#e9f8f5", "#c3d6d2", "#b5c8c2"), "blueberry": ("#797fa3", "#383e62", "#2a3054"),
        "graphite": ("#565a60", "#2c3036", "#22262d"),
    },
}


# ---------------------------------------------------------------------------- drawing


# Rear wordmark hues observed in Samsung Mobile Press S25 product renders.
# Explicit finish exceptions: reflective lettering is not uniformly black or white.
LOGO_FILLS = {
    "s25": {"icyblue": "#b6c9e3", "mint": "#a8bcb3", "navy": "#687b9d", "silver_shadow": "#a2a5af"},
    "s25_ultra": {"titanium_silverblue": "#858b9a", "titanium_black": "#181c25",
                  "titanium_gray": "#878580", "titanium_whitesilver": "#d8dfe0"},
}


def build(model, color):
    g = MODELS[model]
    top, mid, bot = pixel_palette(*COLORS[model][color])
    k = BW  # 1 W in icon units
    defs, paths = [], []

    def lin(gid, x1, y1, x2, y2, stops):
        st = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(x1)}" y1="{f(y1)}" '
                    f'x2="{f(x2)}" y2="{f(y2)}">{st}</linearGradient>')
        return f"url(#{gid})"

    # body
    body = lin("body", 54, GRAD_Y1, 54, GRAD_Y2, [(0, top), (0.48, mid), (1, bot)])
    paths.append((rounded_rect(X0, Y0, BW, BH, g["r"] * k), body))

    dark_body = lum(mid) < 0.35

    # camera island
    if g["island"]:
        ix0, iy0, ix1, iy1 = (X0 + g["island"][0] * k, Y0 + g["island"][1] * k,
                              X0 + g["island"][2] * k, Y0 + g["island"][3] * k)
        if g.get("island_kind") == "metal":
            # S25 Edge: polished titanium capsule
            fill = lin("island", ix1, 0, ix0, 0, [(0, mix(mid, "#ffffff", .55)), (1, mix(top, "#ffffff", .2))])
            paths.append((rounded_rect(ix0, iy0, ix1 - ix0, iy1 - iy0, (ix1 - ix0) / 2), fill))
            inner = 0.01 * k
            paths.append((rounded_rect(ix0 + inner, iy0 + inner, ix1 - ix0 - 2 * inner, iy1 - iy0 - 2 * inner,
                                       (ix1 - ix0) / 2 - inner),
                          lin("islandin", ix1, 0, ix0, 0, [(0, mix(mid, "#ffffff", .25)), (1, top)])))
        else:
            # S26 "Ambient Island": body-coloured, lifted a little lighter, with a soft rim
            rim = lin("islandrim", ix1, 0, ix0, 0, [(0, mix(mid, "#ffffff", .30 if dark_body else .45)),
                                                    (1, mix(top, "#ffffff", .15))])
            paths.append((rounded_rect(ix0, iy0, ix1 - ix0, iy1 - iy0, (ix1 - ix0) / 2), rim))
            inner = 0.01 * k
            fill = lin("island", 54, iy0, 54, iy1, [(0, mix(top, "#ffffff", .12)), (1, mix(mid, top, .5))])
            paths.append((rounded_rect(ix0 + inner, iy0 + inner, ix1 - ix0 - 2 * inner, iy1 - iy0 - 2 * inner,
                                       (ix1 - ix0) / 2 - inner), fill))

    # lens hardware: metal ring + glass (Pixel g2 / g3 roles)
    ring_light = mix(top, "#ffffff", .35) if not dark_body else mix(top, "#ffffff", .25)
    ring_dark = mix(bot, "#000000", .55)
    glass_tint = "#3b4a6b"
    for i, (cx, cy, d) in enumerate(g["lenses"]):
        cx, cy, r = X0 + cx * k, Y0 + cy * k, d * k / 2
        if not g["island"]:
            ring = lin(f"ring{i}", cx + r, cy, cx - r, cy, [(0, ring_light), (1, ring_dark)])
            paths.append((circle(cx, cy, r), ring))
        rg = r if g["island"] else r * 0.80
        glass = lin(f"glass{i}", cx + rg, cy, cx - rg, cy, [(0, glass_tint), (1, "#111215")])
        paths.append((circle(cx, cy, rg), glass))

    # flash
    fx, fy, fd = g["flash"]
    paths.append((circle(X0 + fx * k, Y0 + fy * k, fd * k / 2 + 0.25), mix(mid, "#000000", .3)))
    paths.append((circle(X0 + fx * k, Y0 + fy * k, fd * k / 2), "#f1e8cc"))

    # SAMSUNG wordmark, centred at 79 % of the back's height (measured)
    # Samsung's rear wordmark is dark/black on light finishes. Using the darkest
    # gradient stop here made silver/cream phones incorrectly render a white logo.
    wm_fill = LOGO_FILLS.get(model, {}).get(color) or logo_tone(mid)
    paths.append((wordmark(54, Y0 + 0.79 * BH, g["wm"] * k), wm_fill))

    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">',
           f"<defs>{''.join(defs)}</defs>"]
    svg += [f'<path d="{d}" fill="{fill}"/>' for d, fill in paths]
    svg.append("</svg>\n")
    return "".join(svg)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    n = 0
    for model, colors in COLORS.items():
        if model in ("s25_plus", "s26_plus"):
            continue  # The current Plus geometry is generated by generate_galaxy_svgs.py.
        for color in colors:
            with open(os.path.join(OUT, f"ic_galaxy_{model}_{color}_icon.svg"), "w", encoding="utf-8") as fh:
                fh.write(build(model, color))
            n += 1
    print(f"wrote {n} icons to {OUT}")
