"""Draw Galaxy S / A / Z Fold / Z Flip / TriFold device icons in the Pixel Tips icon style.

NOT vendor extractions: drawn from measurements of Samsung's official renders
(GSMArena official images, Samsung newsroom, design.samsung.com).

  * phones: 108x108 viewport, 30x50 body at (39, 29), 3-stop vertical body gradient
  * folds: closed back (no hinge bar - it reads as an S Pen)
  * flips: unfolded back (cover glass, hinge seam, coloured lower panel)
  * colours: galaxy_colors.json, sampled top/mid/bottom from the official colour renders
    (every sample checked against a crop of the exact pixel column it came from),
    then rendered with richer Pixel-style gradients; older backfill uses representative render hues
  * geometry: lens centres/diameters in fractions of real body width W, measured from renders
"""
import json
import os

import generate_galaxy_s25_s26_svgs as base
from generate_galaxy_s25_s26_svgs import circle, f, lum, mix, rounded_rect, wordmark

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "device_icons_svg", "samsung")
SAMPLED = json.load(open(os.path.join(ROOT, "galaxy_colors.json")))

GLASS_TINT = "#3b4a6b"

# housing (S21 / S22 contour-cut camera housing) metal tones: (light, dark)
TONES = {
    "rose_champagne": ("#e5d3cd", "#bba5a0"),
    "silver": ("#f1f2f4", "#b4b8bd"), "gold": ("#ecd2bb", "#b8937a"), "rosegold": ("#f3d2c8", "#c39789"),
    "black": ("#45464a", "#141416"), "white": ("#fafaf8", "#d4d5d3"),
}


def L(cx, cys, d):
    return [(cx, cy, d) for cy in cys]


# ------------------------------------------------------------------------------------------- phones
# kind: phone. housing=(x1, y1, r) contour cut from the top-left corner; tone per colour in HOUSING.
# ring: "body" (frame-coloured metal), "dark", or None (glass sits in the housing / island)
# island=kind (body | metal | glass): a capsule fitted around the lens column (+ flash if island_flash)
PHONES = {
    # Older backs retain their square glass, fingerprint pads and horizontal bars.
    "s6": dict(r=.145, lenses=[], ring=None, chip=(.385, .22, .23, .24, .055), flash=(.70, .27, .032), sensor=(.67, .32, .065, .065)),
    "s6_edge": dict(r=.145, lenses=[], ring=None, chip=(.385, .22, .23, .24, .055), flash=(.70, .27, .032), sensor=(.67, .32, .065, .065)),
    "s6_edge_plus": dict(r=.145, lenses=[], ring=None, chip=(.395, .21, .21, .22, .05), flash=(.685, .255, .03), sensor=(.655, .30, .06, .06)),
    "s7": dict(r=.145, lenses=[], ring=None, chip=(.39, .225, .22, .23, .055), flash=(.68, .275, .032), sensor=(.65, .33, .06, .055)),
    "s7_edge": dict(r=.145, lenses=[], ring=None, chip=(.40, .22, .20, .21, .05), flash=(.67, .265, .03), sensor=(.64, .315, .06, .055)),
    "s8": dict(r=.145, lenses=[], ring=None, chip=(.405, .205, .19, .21, .05), flash=(.33, .255, .03), sensor=(.31, .31, .055, .055), fingerprint=(.65, .215, .18, .20)),
    "s8_plus": dict(r=.145, lenses=[], ring=None, chip=(.41, .20, .18, .20, .05), flash=(.33, .25, .03), sensor=(.31, .305, .055, .055), fingerprint=(.65, .21, .17, .19)),
    "s9": dict(r=.145, lenses=[], ring=None, chip=(.405, .22, .19, .22, .05), flash=(.685, .265, .03), sensor=(.66, .32, .055, .055), fingerprint=(.41, .49, .18, .16)),
    "s9_plus": dict(r=.145, lenses=[], ring=None, chip=(.405, .21, .19, .39, .085), flash=(.685, .27, .03), sensor=(.66, .325, .055, .055), fingerprint=(.41, .65, .18, .16)),
    "s10e": dict(r=.145, lenses=[], ring=None, chip=(.235, .22, .53, .17, .065), flash=(.685, .305, .027)),
    "s10": dict(r=.145, lenses=[], ring=None, chip=(.16, .23, .68, .17, .065), flash=(.71, .315, .027), sensor=(.77, .295, .04, .04)),
    "s10_plus": dict(r=.145, lenses=[], ring=None, chip=(.18, .22, .64, .16, .06), flash=(.70, .30, .027), sensor=(.76, .28, .04, .04)),
    "s10_5g": dict(r=.145, lenses=[], ring=None, chip=(.13, .22, .74, .16, .06), flash=(.76, .30, .025)),
    "s10_lite": dict(r=.145, module=(.075, .08, .43, .58, .065), lenses=L(.195, (.19, .35, .51), .12), ring=None, flash=(.34, .18, .032)),
    "s20": dict(r=.145, module=(.07, .07, .405, .59, .065), lenses=L(.185, (.18, .35, .52), .125), ring=None, flash=(.325, .18, .033)),
    "s20_plus": dict(r=.145, module=(.07, .07, .425, .59, .065), lenses=L(.18, (.18, .35, .52), .125) + [(.325, .35, .06)], ring=None, flash=(.325, .18, .033)),
    "s20_ultra": dict(r=.145, module=(.075, .07, .42, .61, .055), lenses=[(.18, .17, .11), (.18, .34, .15), (.38, .34, .045)], periscope=(.18, .515, .095, .11), ring=None, flash=(.38, .17, .032)),
    "s20_fe": dict(r=.145, module=(.07, .07, .40, .59, .07), lenses=L(.18, (.18, .35, .52), .125), ring=None, flash=(.32, .18, .032)),
    "s21": dict(r=0.145, housing=(.335, .64, .1), lenses=L(.21, (.145, .327, .512), .15), ring=None, flash=(.43, .125, .035)),
    "s21_plus": dict(r=0.145, housing=(.31, .60, .095), lenses=L(.20, (.139, .312, .485), .14), ring=None, flash=(.41, .12, .033)),
    "s21_ultra": dict(r=0.09, housing=(.50, .75, .1), lenses=L(.226, (.158, .379), .157) + [(.407, .171, .11), (.407, .396, .11)],
                      periscope=(.227, .60, .14, .157), ring=None, flash=(.41, .285, .034)),
    "s21_fe": dict(r=0.145, housing=(.33, .65, .1), lenses=L(.207, (.135, .323, .51), .13), ring=None, flash=(.42, .12, .033)),
    "s22": dict(r=0.145, housing=(.32, .70, .1), lenses=L(.192, (.142, .347, .553), .15), ring=None, flash=(.41, .13, .036)),
    "s22_plus": dict(r=0.145, housing=(.31, .67, .095), lenses=L(.189, (.133, .326, .518), .145), ring=None, flash=(.40, .12, .034)),
    "s22_ultra": dict(r=0.09, lenses=L(.211, (.151, .37, .59), .175) + [(.381, .163, .12), (.381, .385, .12)], ring="dark",
                      flash=(.381, .274, .034)),
    "s23": dict(r=0.145, lenses=L(.209, (.163, .394, .625), .165), ring="body", flash=(.37, .13, .036)),
    "s23_plus": dict(r=0.145, lenses=L(.196, (.148, .363, .578), .155), ring="body", flash=(.35, .12, .034)),
    "s23_ultra": dict(r=0.09, lenses=L(.212, (.143, .378, .613), .17) + [(.395, .164, .115), (.395, .398, .115)], ring="body",
                      flash=(.395, .281, .034)),
    "s23_fe": dict(r=0.145, lenses=L(.213, (.154, .37, .585), .152), ring="dark", flash=(.37, .13, .036)),
    "s24": dict(r=0.145, lenses=L(.177, (.177, .404, .632), .164), ring="body", flash=(.36, .26, .036)),
    "s24_plus": dict(r=0.145, lenses=L(.167, (.164, .391, .618), .157), ring="body", flash=(.35, .25, .034)),
    "s24_ultra": dict(r=0.09, lenses=L(.188, (.173, .404, .635), .169) + [(.402, .175, .102), (.402, .406, .102)], ring="body",
                      flash=(.402, .29, .034)),
    "s24_fe": dict(r=0.145, lenses=L(.222, (.154, .382, .609), .162), ring="body", flash=(.38, .2, .036)),
    "s25_plus": dict(r=0.145, lenses=L(.207, (.154, .382, .61), .19), ring="dark", flash=(.40, .27, .04)),
    "s26_plus": dict(r=0.145, lenses=L(.20, (.162, .381, .60), .18), ring="dark", flash=(.39, .28, .042),
                     island="body"),
    "a34": dict(r=0.145, lenses=L(.204, (.153, .346, .539), .132), ring="body", flash=(.34, .12, .034)),
    "a35": dict(r=0.145, lenses=L(.207, (.155, .374, .591), .144), ring="body", flash=(.34, .16, .034)),
    "a36": dict(r=0.145, lenses=L(.229, (.17, .362, .555), .15), ring=None, flash=(.45, .17, .036),
                island="glass"),
    "a37": dict(r=0.145, lenses=L(.221, (.17, .362, .555), .148), ring=None, flash=(.45, .17, .036),
                island="glass"),
    "a54": dict(r=0.145, lenses=L(.21, (.155, .375, .595), .14), ring="body", flash=(.34, .13, .034)),
    "a55": dict(r=0.145, lenses=L(.212, (.158, .378, .596), .145), ring="body", flash=(.34, .155, .034)),
    "a56": dict(r=0.145, lenses=L(.229, (.17, .361, .552), .15), ring=None, flash=(.45, .17, .036),
                island="glass"),
    "a57": dict(r=0.145, lenses=L(.213, (.178, .369, .56), .145), ring=None, flash=(.45, .17, .036),
                island="glass"),
}

HOUSING = {
    "s21": {"phantom_pink": "rosegold", "phantom_violet": "gold", "phantom_white": "silver", "phantom_gray": "black"},
    "s21_plus": {"phantom_violet": "rose_champagne", "phantom_silver": "silver", "phantom_black": "black", "phantom_pink": "rosegold",
                 "phantom_gold": "gold", "phantom_red": "gold"},
    "s21_ultra": {"phantom_silver": "silver", "phantom_black": "black", "phantom_titanium": "black", "phantom_navy": "black",
                  "phantom_brown": "black"},
    "s22": {"phantom_white": "white", "pink_gold": "rosegold", "phantom_black": "black", "green": "body", "graphite": "black",
            "cream": "white", "sky_blue": "white", "violet": "rosegold", "bora_purple": "body"},
    "s22_plus": {"phantom_white": "white", "phantom_black": "black", "green": "body", "pink_gold": "rosegold",
                 "graphite": "black", "cream": "white", "sky_blue": "white", "violet": "rosegold"},
}

# ------------------------------------------------------------------------------------------- folds
# closed back; geometry in fractions of the closed body width; aspect = width / height (real, closed)
FOLDS = {
    "z_fold3": dict(island_flash=True, aspect=67.1 / 158.2, lenses=L(.25, (.26, .476, .693), .19), ring=None, flash=(.25, .83, .05),
                    island="metal"),
    "z_fold4": dict(island_flash=True, aspect=67.1 / 155.1, lenses=L(.24, (.24, .463, .685), .2), ring=None, flash=(.24, .82, .05),
                    island="metal"),
    "z_fold5": dict(aspect=67.1 / 154.9, lenses=L(.20, (.24, .466, .692), .17), ring="body", flash=(.40, .21, .045)),
    "z_fold6": dict(aspect=68.1 / 153.5, lenses=L(.229, (.229, .468, .707), .19), ring="body", flash=(.42, .20, .045)),
    "z_fold7": dict(aspect=72.8 / 158.4, lenses=L(.245, (.228, .461, .693), .19), ring="dark", flash=(.44, .30, .045),
                    island="body"),
    "z_fold8_ultra": dict(aspect=72.8 / 158.4, lenses=L(.235, (.24, .47, .70), .19), ring="dark", flash=(.43, .33, .045),
                          island="body"),
    "z_fold8": dict(island_flash=True, aspect=0.62, height=46, lenses=L(.215, (.21, .43), .165), ring="dark", flash=(.215, .555, .04),
                    island="metal"),
    "z_trifold": dict(aspect=75 / 159.2, lenses=L(.21, (.20, .42, .64), .19), ring="dark", flash=(.46, .21, .045),
                      island="body"),
}

# ------------------------------------------------------------------------------------------- flips
# unfolded back; cover: "strip" (Flip3/4), "folder" (Flip5/6/7 FE), "full" (Flip7/8)
FLIPS = {
    "z_flip3": dict(cover="strip", screen=(47.5, 31.6, 58.0, 35.6), lenses=[(43.9, 33.3), (43.9, 37.9)], d=2.9,
                    flash=(43.9, 43.0, 1.0), ring="body"),
    "z_flip4": dict(cover="strip", screen=(47.5, 31.6, 58.0, 36.2), lenses=[(43.9, 33.3), (43.9, 37.9)], d=2.9,
                    flash=(43.9, 43.4, 1.0), ring="body"),
    "z_flip5": dict(cover="folder", lenses=[(44.0, 34.0), (49.2, 34.0)], d=3.3, flash=(53.0, 34.0, 1.0), ring="body"),
    "z_flip6": dict(cover="folder", lenses=[(44.1, 34.1), (49.6, 34.1)], d=3.6, flash=(53.6, 34.1, 1.0), ring="body"),
    "z_flip7_fe": dict(cover="folder", lenses=[(44.1, 34.1), (49.6, 34.1)], d=3.6, flash=(53.6, 34.1, 1.0), ring="body"),
    "z_flip7": dict(cover="full", lenses=[(44.2, 34.2), (50.0, 34.2)], d=4.0, flash=(54.4, 34.2, 1.1), ring="metal"),
    "z_flip8": dict(cover="full", lenses=[(44.2, 34.2), (50.0, 34.2)], d=4.0, flash=(54.4, 34.2, 1.1), ring="metal"),
}


# ------------------------------------------------------------------------------------------- drawing
class Doc:
    def __init__(self):
        self.defs, self.paths, self.n = [], [], 0

    def lin(self, x1, y1, x2, y2, stops):
        self.n += 1
        gid = f"g{self.n}"
        st = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        self.defs.append(f'<linearGradient id="{gid}" gradientUnits="userSpaceOnUse" x1="{f(x1)}" y1="{f(y1)}" '
                         f'x2="{f(x2)}" y2="{f(y2)}">{st}</linearGradient>')
        return f"url(#{gid})"

    def clip(self, d):
        self.n += 1
        cid = f"c{self.n}"
        self.defs.append(f'<clipPath id="{cid}"><path d="{d}"/></clipPath>')
        return cid

    def add(self, d, fill, clip=None):
        self.paths.append((d, fill, clip))

    def svg(self):
        out = ['<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">',
               f"<defs>{''.join(self.defs)}</defs>"]
        for d, fill, clip in self.paths:
            c = f' clip-path="url(#{clip})"' if clip else ""
            out.append(f'<path d="{d}" fill="{fill}"{c}/>')
        out.append("</svg>\n")
        return "".join(out)


def ring_colors(kind, top, mid, bot):
    if kind == "body":
        return mix(top, "#ffffff", .3), mix(mid, "#000000", .35)
    if kind == "metal":
        return "#d9dbde", "#4a4c50"
    return mix(bot, "#3a3b3f", .6), "#0c0c0e"  # dark


def ring_geometry(d, ring):
    """(outer radius, glass radius). A dark bezel is part of the measured dark blob (d = outer);
    a light metal ring is not (d = glass)."""
    r = d / 2
    if ring == "dark":
        return r, r * 0.85
    return r / 0.86, r


def lens(doc, cx, cy, d, ring, top, mid, bot):
    r = d / 2
    if ring:
        light, dark = ring_colors(ring, top, mid, bot)
        ro, rg = ring_geometry(d, ring)
        doc.add(circle(cx, cy, ro), doc.lin(cx + ro, cy, cx - ro, cy, [(0, light), (1, dark)]))
    else:
        rg = r
    doc.add(circle(cx, cy, rg), doc.lin(cx + rg, cy, cx - rg, cy, [(0, GLASS_TINT), (1, "#111215")]))


def flash(doc, cx, cy, d, mid):
    doc.add(circle(cx, cy, d / 2 + 0.25), mix(mid, "#000000", .3))
    doc.add(circle(cx, cy, d / 2), "#f1e8cc")


def island(doc, x0, y0, x1, y1, kind, top, mid, bot):
    w, h = x1 - x0, y1 - y0
    dark_body = lum(mid) < 0.35
    if kind == "glass":  # A-series black glass pill with a frame-coloured rim
        doc.add(rounded_rect(x0, y0, w, h, w / 2), doc.lin(x1, 0, x0, 0, [(0, mix(top, "#ffffff", .3)), (1, mix(mid, "#000000", .3))]))
        i = w * 0.08
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, w / 2 - i), doc.lin(0, y0, 0, y1, [(0, "#2a2c31"), (1, "#0e0f11")]))
    elif kind == "metal":
        doc.add(rounded_rect(x0, y0, w, h, w / 2), doc.lin(x1, 0, x0, 0, [(0, mix(mid, "#ffffff", .5)), (1, mix(bot, "#000000", .25))]))
        i = w * 0.09
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, w / 2 - i), doc.lin(x1, 0, x0, 0, [(0, mix(mid, "#ffffff", .2)), (1, top)]))
    else:  # body-coloured raised island
        doc.add(rounded_rect(x0, y0, w, h, w / 2), doc.lin(x1, 0, x0, 0, [(0, mix(mid, "#ffffff", .30 if dark_body else .45)),
                                                                          (1, mix(top, "#ffffff", .15))]))
        i = w * 0.06
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, w / 2 - i), doc.lin(0, y0, 0, y1, [(0, mix(top, "#ffffff", .12)), (1, mix(mid, top, .5))]))


def outer_r(d, ring):
    return d / 2 * 1.08 if not ring else ring_geometry(d, ring)[0]


def fitted_island(g, X0, Y0, k, margin=0.065):
    """Capsule that encloses the lens column (and the flash when it sits inside the island)."""
    xs0, xs1, ys0, ys1 = [], [], [], []
    for cx, cy, d in g["lenses"]:
        ro = outer_r(d, g["ring"])
        xs0.append(cx - ro); xs1.append(cx + ro); ys0.append(cy - ro); ys1.append(cy + ro)
    if g.get("island_flash"):
        fx, fy, fd = g["flash"]
        ys1.append(fy + fd)
    m = margin
    return X0 + (min(xs0) - m) * k, Y0 + (min(ys0) - m) * k, X0 + (max(xs1) + m) * k, Y0 + (max(ys1) + m) * k


def body_fill(doc, y_top, y_bot, top, mid, bot):
    h = y_bot - y_top
    return doc.lin(54, y_top + h * .1546, 54, y_top + h * .9014, [(0, top), (0.48, mid), (1, bot)])


def wm_fill(mid, bot):
    # Judge the real back finish, not the intentionally darkened bottom gradient.
    return base.logo_tone(mid)


def build_phone(model, g, top, mid, bot, housing_tone=None):
    top, mid, bot = base.pixel_palette(top, mid, bot)
    X0, Y0, BW, BH, k = 39.0, 29.0, 30.0, 50.0, 30.0
    doc = Doc()
    bpath = rounded_rect(X0, Y0, BW, BH, g["r"] * k)
    doc.add(bpath, body_fill(doc, Y0, Y0 + BH, top, mid, bot))
    for key in ("module", "chip"):
        if g.get(key):
            x, y, w, h, r = g[key]
            if key == "chip":
                doc.add(rounded_rect(X0 + x*k - .25, Y0 + y*k - .25, w*k + .5, h*k + .5, r*k + .25), mix(top, "#ffffff", .25))
            doc.add(rounded_rect(X0 + x*k, Y0 + y*k, w*k, h*k, r*k),
                    doc.lin(X0 + (x+w)*k, Y0 + y*k, X0 + x*k, Y0 + (y+h)*k, [(0, GLASS_TINT), (1, "#111215")]))
    for key in ("fingerprint", "sensor"):
        if g.get(key):
            x, y, w, h = g[key]
            doc.add(rounded_rect(X0 + x*k, Y0 + y*k, w*k, h*k, min(w, h)*k*.25), mix(mid, "#000000", .32 if key == "fingerprint" else .65))
    if g.get("housing"):
        hx1, hy1, hr = g["housing"]
        if housing_tone in (None, "body"):
            light, dark = mix(top, "#ffffff", .25), mix(mid, "#000000", .15)
        else:
            light, dark = TONES[housing_tone]
        cid = doc.clip(bpath)
        doc.add(rounded_rect(X0 - 4, Y0 - 4, hx1 * k + 4, hy1 * k + 4, hr * k),
                doc.lin(X0 + hx1 * k, Y0, X0, Y0 + hy1 * k, [(0, light), (1, dark)]), cid)
    if g.get("island"):
        island(doc, *fitted_island(g, X0, Y0, k), g["island"], top, mid, bot)
    for cx, cy, d in g["lenses"]:
        lens(doc, X0 + cx * k, Y0 + cy * k, d * k, None if g.get("island") else g["ring"], top, mid, bot)
    if g.get("periscope"):
        cx, cy, w, h = g["periscope"]
        x, y = X0 + (cx - w / 2) * k, Y0 + (cy - h / 2) * k
        doc.add(rounded_rect(x - .3, y - .3, w * k + .6, h * k + .6, w * k * .3), "#0b0b0d")
        doc.add(rounded_rect(x, y, w * k, h * k, w * k * .28), doc.lin(x + w * k, 0, x, 0, [(0, GLASS_TINT), (1, "#111215")]))
    fx, fy, fd = g["flash"]
    flash(doc, X0 + fx * k, Y0 + fy * k, fd * k, mid)
    wm_y = .54 if model == "s9_plus" else .45 if model == "s9" else .34 if model.startswith(("s6", "s7", "s8")) else .79
    doc.add(wordmark(54, Y0 + wm_y * BH, g.get("wm", .31) * k), wm_fill(mid, bot))
    return doc.svg()


def build_fold(model, g, top, mid, bot):
    top, mid, bot = base.pixel_palette(top, mid, bot)
    H = g.get("height", 52.0)
    BW = round(H * g["aspect"] * 1.12, 2)  # Pixel Tips widens folds by the same ~12 %
    X0 = 54 - BW / 2
    Y0 = 54 - H / 2
    k = BW
    doc = Doc()
    doc.add(rounded_rect(X0, Y0, BW, H, 0.11 * k), body_fill(doc, Y0, Y0 + H, top, mid, bot))
    if g.get("island"):
        island(doc, *fitted_island(g, X0, Y0, k), g["island"], top, mid, bot)
    for cx, cy, d in g["lenses"]:
        lens(doc, X0 + cx * k, Y0 + cy * k, d * k, None if g.get("island") else g["ring"], top, mid, bot)
    fx, fy, fd = g["flash"]
    flash(doc, X0 + fx * k, Y0 + fy * k, fd * k, mid)
    return doc.svg()


def build_flip(model, g, top, mid, bot):
    top, mid, bot = base.pixel_palette(top, mid, bot)
    X0, Y0, BW, BH = 39.0, 29.0, 30.0, 50.0
    doc = Doc()
    bpath = rounded_rect(X0, Y0, BW, BH, 3.6)
    doc.add(bpath, body_fill(doc, Y0, Y0 + BH, top, mid, bot))
    glass = lambda y0, y1: doc.lin(X0, y0, X0 + BW, y1, [(0, "#30343d"), (1, "#111316")])
    if g["cover"] == "strip":
        strip = f"M{f(X0)},{f(Y0)}H{f(X0 + BW)}V{f(Y0 + 12)}H{f(X0)}Z"
        doc.add(strip, glass(Y0, Y0 + 12), doc.clip(bpath))
        sx0, sy0, sx1, sy1 = g["screen"]
        doc.add(rounded_rect(sx0, sy0, sx1 - sx0, sy1 - sy0, 0.8), "#1f2226")
    else:
        # The colored frame surrounds the glass; its top corners are concentric with the body.
        left, right, glass_top, bottom = X0 + .55, X0 + BW - .55, Y0 + .55, Y0 + BH / 2 - .45
        radius = 3.6 - .55
        top_half = (f"M{f(left + radius)},{f(glass_top)}H{f(right - radius)}A{f(radius)},{f(radius)} 0 0 1 {f(right)},{f(glass_top + radius)}"
                    f"V{f(bottom - .55)}Q{f(right)},{f(bottom)} {f(right - .55)},{f(bottom)}H{f(left + .55)}"
                    f"Q{f(left)},{f(bottom)} {f(left)},{f(bottom - .55)}V{f(glass_top + radius)}"
                    f"A{f(radius)},{f(radius)} 0 0 1 {f(left + radius)},{f(glass_top)}Z")
        doc.add(top_half, glass(glass_top, bottom))
        if g["cover"] == "folder":
            # Flex Window "folder" shape: full width below the cameras, notched up on the right
            x0, x1, yb = X0 + 1.7, X0 + BW - 1.7, Y0 + BH / 2 - 1.7
            d = (f"M{f(x0 + 1.5)},{f(Y0 + 8.4)}H54.8Q55.8,37.4 55.8,36.4V{f(Y0 + 3.7)}"
                 f"Q55.8,{f(Y0 + 2.6)} 56.9,{f(Y0 + 2.6)}H{f(x1 - 1.5)}A1.5,1.5 0 0 1 {f(x1)},{f(Y0 + 4.1)}"
                 f"V{f(yb - 1.5)}A1.5,1.5 0 0 1 {f(x1 - 1.5)},{f(yb)}H{f(x0 + 1.5)}A1.5,1.5 0 0 1 {f(x0)},{f(yb - 1.5)}"
                 f"V{f(Y0 + 9.9)}A1.5,1.5 0 0 1 {f(x0 + 1.5)},{f(Y0 + 8.4)}Z")
            doc.add(d, doc.lin(x0, Y0 + 3, x1, yb, [(0, "#323741"), (1, "#191c21")]))
    # hinge seam
    doc.add(f"M{f(X0)},{f(53.9)}H{f(X0 + BW)}V{f(54.1)}H{f(X0)}Z", mix(mid, "#000000", .25))
    for cx, cy in g["lenses"]:
        lens(doc, cx, cy, g["d"], g["ring"], top, mid, bot)
    fx, fy, fd = g["flash"]
    flash(doc, fx, fy, fd, mid)
    return doc.svg()


def write(folder, model, color, svg):
    d = os.path.join(OUT, "phones")
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, f"ic_galaxy_{model}_{color}_icon.svg"), "w", encoding="utf-8") as fh:
        fh.write(svg)


def main():
    n = 0
    # S25 / S26 base, Ultra, Edge, FE from the original generator; S25+/S26+ re-measured here
    for model, colors in base.COLORS.items():
        if model in ("s25_plus", "s26_plus"):
            continue
        for color in colors:
            write("s_series", model, color, base.build(model, color))
            n += 1
    for model, colors in SAMPLED.items():
        for color, (top, mid, bot) in colors.items():
            if model in PHONES:
                folder = "a_series" if model.startswith("a") else "s_series"
                svg = build_phone(model, PHONES[model], top, mid, bot, HOUSING.get(model, {}).get(color))
            elif model in FOLDS:
                folder, svg = "z_fold", build_fold(model, FOLDS[model], top, mid, bot)
            elif model in FLIPS:
                folder, svg = "z_flip", build_flip(model, FLIPS[model], top, mid, bot)
            else:
                raise KeyError(model)
            write(folder, model, color, svg)
            n += 1
    print(f"wrote {n} icons to {OUT}")


if __name__ == "__main__":
    main()
