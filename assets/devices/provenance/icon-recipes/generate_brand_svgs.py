"""Draw device backs from official references in the Pixel Tips icon style.

These are drawn icons, not vendor extractions. Original Nothing Settings Glyph vectors are
retained separately; Phone (1)/(2) icons use manually fitted light layouts. Drawn from official renders:
  * colours: brand_colors.json, sampled from each official colour render and checked against
    a crop of the sampled pixel column; rendered with richer Pixel-style gradients.
    Older tablet backfill uses representative official-render hues (see OLDER_MODELS.md).
  * geometry: camera modules / lenses / flash measured from the renders in fractions of body width W
"""
import json
import math
import os
import re

from generate_galaxy_s25_s26_svgs import circle, f, logo_tone, lum, mix, pixel_palette, rounded_rect, wordmark
from generate_galaxy_svgs import GLASS_TINT, Doc, body_fill, flash, lens

ROOT = os.path.dirname(os.path.abspath(__file__))
COLORS = json.load(open(os.path.join(ROOT, "brand_colors.json")))


# element helpers (all coordinates in W = body width; y from the top of the back)
def mod(x0, y0, x1, y1, r=.25, kind="body"):  # r: corner radius as a fraction of the shorter side
    return ("mod", x0, y0, x1, y1, r, kind)


def circ(cx, cy, d, kind="metal"):
    return ("mod", cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2, .5, kind)


def pill(x0, y0, x1, y1, kind="dark"):
    return ("mod", x0, y0, x1, y1, .5, kind)


def ln(cx, cy, d, ring=None):
    return ("lens", cx, cy, d, ring)


def fl(cx, cy, d=.045):
    return ("flash", cx, cy, d)


def peri(cx, cy, w, h):
    return ("peri", cx, cy, w, h)


def honor_cam(style, cx=.5, cy=.46, d=.8):
    return ("honor_cam", style, cx, cy, d)


def arc(cx, cy, r, a0, a1):  # Glyph LED arc, angles in degrees (0 = right, 90 = down)
    return ("arc", cx, cy, r, a0, a1)


def strip(pts):  # Glyph LED strip along a polyline
    return ("strip", pts)


def dot(cx, cy, d, color=None):
    return ("dot", cx, cy, d, color)


def led(cx, cy, d):  # single Glyph LED
    return ("led", cx, cy, d)


def seg(x, y0, y1, n, red_last=False, width=.06):  # vertical segmented Glyph bar / LED strip
    return ("seg", x, y0, y1, n, red_last, width)


def matrix(cx, cy, size, shape, n=13):  # Glyph Matrix dot display
    return ("matrix", cx, cy, size, shape, n)


def redsq(cx, cy, grey=False):
    return ("redsq", cx, cy, grey)


def screw(cx, cy):
    return ("screw", cx, cy)


def dial(cx, cy, d):  # CMF accessory point
    return ("dial", cx, cy, d)


def panel(y0):  # CMF two-tone lower panel
    return ("panel", y0)


def quad(cx, cy, step, d, ring="dark"):
    return [ln(cx - step, cy - step, d, ring), ln(cx + step, cy - step, d, ring),
            ln(cx - step, cy + step, d, ring), ln(cx + step, cy + step, d, ring)]


# Geometry measured on the reference back renders in tmp/ref5/gsm and tmp/ref5/latest.
# Camera units use the stylized width; back artwork retains the reference aspect ratio.
PHONES = {
    "apple_iphone_18_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5968, .18), wide_panel=True, el=[mod(.055, .055, .945, .63, .23, "apple_camera"), ln(.23, .215, .205), ln(.23, .47, .205), ln(.465, .3425, .205), fl(.80, .215, .07), circ(.80, .47, .055, "dark")]),
    "apple_iphone_18_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.608, .18), wide_panel=True, el=[mod(.055, .055, .945, .63, .23, "apple_camera"), ln(.23, .215, .205), ln(.23, .47, .205), ln(.465, .3425, .205), fl(.80, .215, .07), circ(.80, .47, .055, "dark")]),
    "apple_iphone_17e": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[ln(.195, .17, .235), fl(.415, .17, .05)]),
    "apple_iphone_17_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.6243, .18), wide_panel=True, back_panel=(.055, .67, .945, 1.61, .11, "pixel_panel"), el=[mod(.055, .055, .945, .63, .23, "apple_camera"), ln(.23, .215, .205), ln(.23, .47, .205), ln(.465, .3425, .205), fl(.80, .215, .07), circ(.80, .47, .055, "dark")]),
    "apple_iphone_17_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.6353, .18), wide_panel=True, back_panel=(.055, .67, .945, 1.61, .11, "pixel_panel"), el=[mod(.055, .055, .945, .63, .23, "apple_camera"), ln(.23, .215, .205), ln(.23, .47, .205), ln(.465, .3425, .205), fl(.80, .215, .07), circ(.80, .47, .055, "dark")]),
    "apple_iphone_17": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.4892, .18), el=[pill(.06, .06, .36, .58, "apple_camera"), ln(.21, .21, .21), ln(.21, .43, .21), fl(.465, .32, .05)]),
    "apple_iphone_air": dict(camera_width=30, aspect=.6, r=.2593, logo=("apple", .5, 0.4942, .18), wide_panel=True, el=[mod(.055, .055, .945, .43, .5, "apple_camera"), ln(.225, .235, .235), fl(.49, .235, .05)]),
    "apple_iphone_16e": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[ln(.195, .17, .235), fl(.415, .17, .05)]),
    "apple_iphone_16_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.4891, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_16_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.4888, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_16_plus": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.4892, .18), el=[pill(.06, .06, .36, .58, "apple_camera"), ln(.21, .21, .21), ln(.21, .43, .21), fl(.465, .32, .05)]),
    "apple_iphone_16": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.4891, .18), el=[pill(.06, .06, .36, .58, "apple_camera"), ln(.21, .21, .21), ln(.21, .43, .21), fl(.465, .32, .05)]),
    "apple_iphone_15_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_15_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_15_plus": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_15": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_14_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_14_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_14_plus": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_14": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_se_2022": dict(logo_fills={'#cb3346': '#49494a', '#e8e3d8': '#777879', '#303d50': '#3d3d3f'}, camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .5, .18), el=[ln(.165, .13, .145), fl(.345, .13, .045)]),
    "apple_iphone_13_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_13_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .65, .65, .24, "apple_camera"), ln(.23, .23, .22), ln(.23, .485, .22), ln(.49, .3575, .22), fl(.515, .17, .055), circ(.515, .545, .045, "dark")]),
    "apple_iphone_13": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_13_mini": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .56, .56, .24, "apple_camera"), ln(.22, .22, .205), ln(.40, .40, .205), fl(.425, .185, .05)]),
    "apple_iphone_12_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .575, .575, .24, "apple_camera"), ln(.21, .21, .185), ln(.21, .435, .185), ln(.43, .3225, .185), fl(.45, .16, .055), circ(.45, .475, .045, "dark")]),
    "apple_iphone_12_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .575, .575, .24, "apple_camera"), ln(.21, .21, .185), ln(.21, .435, .185), ln(.43, .3225, .185), fl(.45, .16, .055), circ(.45, .475, .045, "dark")]),
    "apple_iphone_12": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.07, .07, .55, .55, .24, "apple_camera"), ln(.215, .215, .18), ln(.215, .42, .18), fl(.405, .215, .05)]),
    "apple_iphone_12_mini": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.07, .07, .55, .55, .24, "apple_camera"), ln(.215, .215, .18), ln(.215, .42, .18), fl(.405, .215, .05)]),
    "apple_iphone_se_2020": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .5, .18), el=[ln(.165, .13, .145), fl(.345, .13, .045)]),
    "apple_iphone_11_pro": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .575, .575, .24, "apple_camera"), ln(.21, .21, .185), ln(.21, .435, .185), ln(.43, .3225, .185), fl(.45, .16, .055)]),
    "apple_iphone_11_pro_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.065, .065, .575, .575, .24, "apple_camera"), ln(.21, .21, .185), ln(.21, .435, .185), ln(.43, .3225, .185), fl(.45, .16, .055)]),
    "apple_iphone_11": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, 0.5, .18), el=[mod(.07, .07, .55, .55, .24, "apple_camera"), ln(.215, .215, .18), ln(.215, .42, .18), fl(.405, .215, .05)]),
    "apple_iphone_xs": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .43, .18), el=[pill(.085, .075, .28, .565, "dark"), fl(.1825, .32, .045)]),
    "apple_iphone_xs_max": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .43, .18), el=[pill(.085, .075, .28, .565, "dark"), fl(.1825, .32, .045)]),
    "apple_iphone_xr": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .43, .18), el=[ln(.185, .17, .20), fl(.185, .37, .045)]),
    "apple_iphone_x": dict(camera_width=30, aspect=.6, r=.15, logo=("apple", .5, .43, .18), el=[pill(.085, .075, .28, .565, "dark"), fl(.1825, .32, .045)]),
    "apple_iphone_duo": dict(width=36, camera_width=36, aspect=.72, r=.15, logo=("apple", .5, .53, .18), provisional=True, provisional_note='<title>iPhone Duo - provisional prelaunch design</title><desc>Drawn from Apple announced rear images, with stylized proportions. Availability October 23, 2026. Source: https://www.apple.com/iphone-duo/</desc>', el=[pill(.045, .058, .875, .388, "apple_camera"), ln(.215, .223, .23), ln(.505, .223, .23), fl(.735, .265, .045)]),
    "nothing_cmf_phone_1": dict(camera_width=30, finish="nothing", aspect=77/164, r=0.15, el=[pill(.04, .055, .29, .485, "body"), ln(.165, .18, .17, "dark"), ln(.165, .365, .17, "dark"), fl(.355, .225, .04),
        screw(.355, .045), screw(.945, .53), screw(.055, .60), screw(.055, 1.91), dial(.89, 1.94, .23)]),
    "nothing_cmf_phone_2_pro": dict(camera_width=28, finish="nothing", aspect=78/164, r=0.15, el=[panel(1.04), pill(.26, .09, .45, .40, "metal"), ln(.145, .135, .19, "metal"), ln(.355, .20, .105, "metal"), ln(.145, .405, .19, "metal"), fl(.355, .335, .045),
        screw(.36, .04), screw(.055, .72), screw(.955, .72), screw(.055, 1.95), dial(.865, 1.93, .20)]),
    "nothing_phone_1": dict(camera_width=28, finish="nothing", aspect=75.8/159.2, r=0.15, el=[pill(.075, .045, .295, .475, "metal"), ln(.185, .165, .14), ln(.185, .355, .14), fl(.36, .25, .04),
        ("manual_glyph", "nothing_phone_1")]),
    "nothing_phone_2": dict(camera_width=28, finish="nothing", aspect=76.4/162.1, r=0.15, el=[pill(.07, .03, .34, .55, "metal"), ln(.205, .175, .17), ln(.205, .405, .17), fl(.405, .33, .04),
        ("manual_glyph", "nothing_phone_2"), redsq(.91, .35)]),
    "nothing_phone_2a": dict(camera_width=28, finish="nothing", aspect=76.3/161.7, r=0.158, el=[("2a_back",), circ(.50, .46, .76, "body"), pill(.255, .33, .745, .575, "dark"), ln(.375, .455, .17), ln(.625, .455, .17), fl(.825, .265, .035),
        arc(.50, .46, .435, 198, 250), arc(.50, .46, .435, -22, 22), arc(.50, .46, .435, 137, 157), redsq(.94, .855)]),
    "nothing_phone_2a_plus": dict(camera_width=28, finish="nothing", aspect=76.3/161.7, r=0.158, el=[("2a_back",), circ(.50, .46, .76, "metal"), pill(.255, .33, .745, .575, "dark"), ln(.375, .455, .17), ln(.625, .455, .17), fl(.80, .265, .035),
        arc(.50, .46, .435, 198, 250), arc(.50, .46, .435, -22, 22), arc(.50, .46, .435, 137, 157), redsq(.94, .855, grey=True)]),
    "nothing_phone_3": dict(camera_width=28, finish="nothing", aspect=75.6/160.6, r=0.15, el=[("3_back",), circ(.14, .19, .18, "dark"), peri(.14, .19, .09, .075), circ(.505, .175, .27, "body"), fl(.505, .19, .045), matrix(.81, .19, .29, "circle", 25),
        ln(.20, .47, .17, "metal"), ln(.505, .47, .17, "metal"), redsq(.39, .565)]),
    "nothing_phone_3a": dict(camera_width=28, finish="nothing", aspect=77.5/163.5, r=0.15, el=[("3a_back",), circ(.5, .465, .76, "body"), pill(.205, .34, .795, .59, "metal"), pill(.245, .365, .755, .565, "dark"),
        ln(.335, .465, .15), ln(.50, .465, .09), ln(.675, .465, .15), fl(.43, .21, .04), arc(.5, .465, .435, 198, 250), arc(.5, .465, .435, -15, 30), arc(.5, .465, .435, 134, 155), redsq(.93, .88)]),
    "nothing_phone_3a_pro": dict(camera_width=28, finish="nothing", aspect=77.5/163.5, r=0.15, el=[("3a_back",), circ(.5, .465, .72, "metal"), circ(.5, .465, .69, "body"), ln(.34, .30, .115), ln(.34, .49, .13),
        mod(.47, .405, .66, .615, .22, "dark"), peri(.565, .51, .115, .125), circ(.515, .23, .125, "dark"), fl(.515, .23, .065), arc(.5, .465, .435, 198, 250), arc(.5, .465, .435, -15, 30), arc(.5, .465, .435, 134, 155), redsq(.93, .88, grey=True)]),
    "nothing_phone_3a_lite": dict(camera_width=26, finish="nothing", aspect=78/164, r=0.15, el=[("3a_lite_back",), ln(.14, .135, .155, "metal"), ln(.36, .205, .125, "metal"), ln(.14, .42, .155, "metal"), fl(.355, .375, .035), redsq(.95, .30),
        screw(.92, .09), screw(.045, .595), screw(.94, .595), screw(.045, 1.92), led(.90, 1.96, .045)]),
    "nothing_phone_4a": dict(camera_width=30, finish="nothing", aspect=77.6/164, r=0.15, el=[("4a_back",), pill(.17, .16, .83, .54, "camera"), pill(.225, .21, .795, .49, "camera_metal"),
        pill(.26, .26, .57, .44, "dark"), ln(.35, .35, .13), ln(.495, .35, .12), ln(.67, .35, .17), fl(.60, .13, .04),
        seg(.935, .245, .57, 7, red_last=True, width=.045)]),
    "nothing_phone_4a_pro": dict(camera_width=28, finish="nothing", aspect=76.6/163.7, r=0.15, wide_panel=True, el=[mod(.04, .04, .96, .91, .27, "pixel_panel"),
        ln(.23, .265, .22), pill(.12, .45, .56, .685, "dark"), ln(.23, .5675, .16), ln(.435, .5675, .09), matrix(.76, .35, .40, "circle"),
        fl(.455, .32, .035), pill(.68, .655, .92, .705, "body"), ("4a_pro_back",), redsq(.925, .55)]),
    "nothing_phone_4b": dict(camera_width=30, finish="nothing", aspect=78.2/164.4, r=0.15, wide_panel=True, el=[mod(.04, .04, .96, .81, .23, "pixel_panel"),
        ln(.18, .16, .19), ln(.18, .40, .19), pill(.36, .195, .55, .285, "body"), fl(.415, .24, .035), dot(.50, .24, .035, "#1b1c1f"),
        seg(.84, .255, .515, 5, red_last=True, width=.055)]),
    # Provisional proportions measured from angled official teasers; not final dimensions.
    "oneplus_16": dict(camera_width=30, aspect=.474, provisional=True, logo=("oneplus", .5, .52, .17), r=0.15, el=[mod(.07, .065, .66, .675, .27, "body"),
        pill(.125, .12, .36, .615, "dark"), ln(.245, .245, .15), ln(.245, .505, .15), ln(.495, .245, .17), circ(.495, .505, .19, "dark"), fl(.495, .505, .075)]),
    "oneplus_15": dict(camera_width=30, aspect=76.7/161.4, logo=("oneplus", .5, .52, .17), r=0.158, el=[mod(.07, .07, .64, .63, .25, "body"),
        pill(.14, .14, .355, .565, "dark"), ln(.245, .25, .145), ln(.245, .465, .145), ln(.49, .25, .145), circ(.49, .48, .20, "dark"), fl(.49, .48, .065)]),
    "oneplus_15r": dict(camera_width=30, aspect=77/163.4, logo=("oneplus", .5, .52, .17), r=0.15, el=[mod(.075, .065, .505, .62, .28, "dark"),
        pill(.14, .13, .335, .575, "dark"), ln(.235, .245, .145), ln(.235, .465, .145), fl(.425, .245, .065)]),
    "oneplus_15t": dict(camera_width=30, aspect=71.8/150.6, logo=("oneplus", .5, .52, .17), r=0.16, el=[mod(.08, .07, .585, .585, .27, "body"),
        pill(.14, .13, .335, .54, "dark"), ln(.235, .245, .145), ln(.235, .445, .145), pill(.405, .265, .52, .455, "dark"), fl(.463, .325, .055)]),
    "oneplus_13": dict(logo_fills={'#1e2d4a': '#6b7da6'}, camera_width=30, aspect=76.5/162.9, logo=("oneplus", .5, .52, .16), r=0.15, el=[circ(.37, .39, .65, "metal")] + quad(.37, .39, .115, .145)[:3] + [circ(.485, .505, .18, "dark"), fl(.485, .505, .05)]),
    "oneplus_13r": dict(camera_width=30, aspect=75.8/161.7, logo=("oneplus", .5, .52, .16), r=0.15, el=[circ(.37, .39, .61, "metal")] + quad(.37, .39, .115, .145)[:3] + [circ(.485, .505, .18, "dark"), fl(.485, .505, .06)]),
    "oneplus_nord_6": dict(camera_width=30, aspect=77.5/162.5, logo=("oneplus", .5, .52, .17), r=0.155, el=[mod(.095, .065, .59, .595, .23, "body"),
        ln(.22, .22, .18), ln(.22, .47, .18), circ(.46, .21, .14, "dark"), fl(.46, .21, .065), dot(.46, .48, .10, "#1b1c1f")]),
    "oneplus_nord_5": dict(camera_width=30, aspect=77/163.4, logo=("oneplus", .5, .52, .17), r=0.15, el=[pill(.095, .065, .32, .72, "metal"), pill(.115, .085, .30, .70, "camera_dark"),
        ln(.21, .22, .13), ln(.21, .425, .13), fl(.21, .625, .06)]),
    "oneplus_nord_ce6": dict(camera_width=30, aspect=77.5/162.5, logo=("oneplus", .5, .52, .17), r=0.15, el=[mod(.075, .065, .56, .605, .26, "body"),
        ln(.235, .205, .185), ln(.235, .465, .185), pill(.395, .15, .49, .315, "dark"), fl(.443, .20, .045)]),
    "oneplus_nord_ce6_lite": dict(camera_width=30, aspect=76/166, logo=("oneplus", .5, .5, .17), r=0.15, el=[pill(.10, .08, .375, .78, "body"),
        ln(.235, .215, .18), ln(.235, .425, .18), circ(.235, .635, .18, "dark"), dot(.235, .635, .025, "#111215"), mod(.427, .175, .46, .26, .5, "metal"), fl(.444, .215, .027)]),
    "oppo_find_x9s": dict(camera_width=30, aspect=73.93/156.98, logo=("oppo", .5, .81, .3), r=0.15, el=[mod(.065, .065, .63, .66, .25, "metal"),
        ln(.23, .235, .21), ln(.23, .495, .21), pill(.405, .135, .565, .40, "dark"), ln(.485, .205, .115), fl(.485, .515, .07)]),
    "oppo_find_x9s_pro": dict(camera_width=30, aspect=71.72/150.46, logo=("oppo", .5, .81, .3), r=0.16, el=[mod(.065, .065, .64, .67, .25, "body"),
        ln(.23, .23, .21), circ(.23, .51, .23, "dark"), peri(.23, .51, .13, .14), pill(.41, .12, .57, .395, "dark"),
        dot(.49, .175, .075, "#111215"), ln(.49, .30, .115), circ(.49, .515, .16, "metal"), fl(.82, .52, .065)]),
    "oppo_reno16_f": dict(camera_width=30, aspect=74.93/158.16, logo=("oppo", .5, .81, .3), r=0.15, el=[mod(.065, .065, .595, .635, .27, "body"),
        ln(.22, .215, .205), ln(.22, .49, .205), ln(.465, .235, .12), fl(.465, .485, .065)]),
    "oppo_find_x10": dict(camera_width=30, aspect=74.3/156.5, logo=("oppo", .5, .86, .3), r=0.15, el=[mod(.08, .065, .63, .665, .25, "body"),
        ln(.25, .24, .205), ln(.25, .525, .205), pill(.425, .14, .60, .415, "dark"), ln(.505, .32, .115), fl(.825, .515, .065)]),
    "oppo_find_x10_pro_max": dict(camera_width=30, aspect=76.6/161.3, logo=("oppo", .5, .86, .3), r=0.15, el=[mod(.075, .065, .67, .685, .24, "body"), mod(.09, .08, .655, .67, .25, "dark"),
        ln(.24, .235, .19), ln(.515, .265, .135), circ(.245, .54, .24, "dark"), peri(.245, .54, .12, .13), dot(.81, .22, .09, "#111215"), fl(.815, .545, .07)]),
    "oppo_find_x10_e": dict(camera_width=30, aspect=73.9/157, logo=("oppo", .5, .86, .3), r=0.15, el=[mod(.085, .065, .66, .65, .25, "metal"),
        ln(.24, .235, .195), ln(.24, .51, .195), pill(.42, .155, .58, .41, "dark"), ln(.50, .235, .11), fl(.50, .505, .065)]),
    "oppo_find_x9": dict(camera_width=30, aspect=73.9/157, logo=("oppo", .5, .86, .3), r=0.15, el=[mod(.07, .065, .655, .665, .25, "metal"),
        ln(.24, .22, .21), ln(.24, .495, .21), pill(.425, .125, .57, .40, "dark"), ln(.497, .21, .095), circ(.50, .52, .16, "metal"), fl(.50, .52, .055)]),
    "oppo_find_x9_pro": dict(camera_width=30, aspect=76.5/161.3, logo=("oppo", .5, .86, .3), r=0.16, el=[mod(.075, .065, .655, .685, .25, "metal"),
        ln(.25, .22, .215), peri(.25, .51, .16, .17), pill(.435, .125, .58, .40, "dark"), ln(.505, .21, .095), circ(.50, .52, .16, "metal"), fl(.50, .52, .055)]),
    "oppo_find_x9_ultra": dict(camera_width=30, aspect=77/163.2, logo=("oppo", .5, .81, .3), r=0.15, el=[circ(.50, .53, .79, "metal"), circ(.50, .53, .735, "dark"),
        ln(.50, .28, .135), ln(.745, .54, .135), ln(.50, .775, .135), circ(.25, .54, .19, "dark"), peri(.25, .54, .11, .145), fl(.13, .13, .07)]),
    "oppo_find_n5": dict(camera_width=30, aspect=74.4/160.9, logo=("oppo", .5, .82, .3), r=0.15, el=[circ(.505, .47, .71, "metal"), circ(.505, .47, .65, "dark"),
        peri(.345, .375, .11, .145), ln(.625, .375, .145), ln(.375, .60, .145), fl(.635, .60, .055)]),
    "oppo_find_n6": dict(camera_width=30, aspect=74.5/159.9, logo=("oppo", .5, .82, .3), r=0.15, el=[circ(.50, .455, .74, "metal"), circ(.50, .455, .67, "dark"),
        peri(.325, .345, .11, .145), ln(.64, .355, .145), ln(.325, .61, .145), ln(.64, .61, .145), fl(.13, .12, .06)]),
    "oppo_reno16": dict(camera_width=30, aspect=72.4/151.2, logo=("oppo", .5, .86, .3), r=0.15, el=[mod(.075, .065, .625, .675, .25, "body"),
        ln(.22, .235, .22), ln(.22, .52, .22), ln(.485, .255, .135), fl(.485, .425, .065)]),
    "oppo_reno16_pro": dict(camera_width=30, aspect=72.4/151.2, logo=("oppo", .5, .81, .3), r=0.15, el=[mod(.07, .065, .625, .66, .25, "body"),
        ln(.225, .23, .21), ln(.225, .49, .21), ln(.475, .24, .125), fl(.475, .49, .065)]),
    "oppo_reno15": dict(camera_width=30, aspect=72.4/151.2, logo=("oppo", .5, .81, .3), r=0.15, el=[mod(.065, .06, .60, .665, .25, "body"),
        ln(.22, .225, .20), ln(.22, .485, .20), ln(.46, .365, .11), fl(.46, .19, .065)]),
    "oppo_reno15_pro": dict(camera_width=30, aspect=76.5/161.2, logo=("oppo", .5, .81, .3), r=0.15, el=[mod(.065, .06, .60, .665, .25, "body"),
        ln(.22, .225, .20), ln(.22, .485, .20), ln(.46, .365, .11), fl(.46, .19, .065)]),
    # Xiaomi / Redmi / POCO / Honor / Motorola, official-reference backfill.
    'xiaomi_17_pro': dict(r=.145, aspect=.6, el=[mod(.07, .08, .93, .67, .2, "metal"), mod(.09, .105, .91, .645, .18, "dark"), ln(.23, .26, .19), ln(.23, .505, .19), mod(.44, .14, .87, .61, .18, "dark"), pill(.13, .755, .33, .84), fl(.42, .80, .065)]),
    'xiaomi_17_pro_max': dict(r=.145, aspect=.6, el=[mod(.07, .08, .93, .67, .2, "metal"), mod(.09, .105, .91, .645, .18, "dark"), ln(.23, .26, .19), ln(.23, .505, .19), mod(.44, .14, .87, .61, .18, "dark"), pill(.13, .755, .33, .84), fl(.42, .80, .065)]),
    'xiaomi_14_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .66, .67, .17, "dark"), ln(.23, .23, .19), ln(.23, .49, .19), ln(.49, .49, .17), fl(.49, .23, .065)]),
    'xiaomi_15_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .66, .67, .17, "dark"), ln(.23, .23, .19), ln(.49, .23, .17), ln(.23, .49, .19), circ(.49, .49, .18, "dark"), fl(.75, .32, .06)]),
    'xiaomi_15s_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .66, .67, .17, "dark"), ln(.23, .23, .19), ln(.49, .23, .17), ln(.23, .49, .19), circ(.49, .49, .18, "dark"), fl(.75, .32, .06)]),
    'xiaomi_17_max': dict(r=.145, aspect=.6, el=[mod(.07, .07, .66, .67, .17, "dark"), ln(.23, .23, .19), ln(.49, .23, .17), ln(.23, .49, .19), circ(.49, .49, .18, "dark"), fl(.75, .32, .06)]),
    'xiaomi_mi_10_ultra': dict(r=.145, aspect=.6, el=[mod(.09, .08, .37, 1.06, .22, "camera_dark"), mod(.09, .08, .37, .265, .22, "metal"), peri(.23, .1725, .17, .095), ln(.23, .485, .20), ln(.23, .70, .16), ln(.23, .915, .16), fl(.425, .49, .055)]),
    'xiaomi_mi_11_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .60, .66, .22, "body"), ln(.245, .255, .245), peri(.245, .49, .16, .13), ln(.465, .255, .095), fl(.465, .735, .07)]),
    'xiaomi_mix_4': dict(r=.145, aspect=.6, el=[mod(.07, .08, .59, .74, .15, "dark"), ln(.255, .285, .24), peri(.24, .57, .12, .13), ln(.47, .285, .09), fl(.47, .565, .04)]),
    'xiaomi_mix_flip': dict(r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .80, .5, "dark"), ln(.19, .19, .18), ln(.19, .42, .17), fl(.19, .60, .04), mod(.025, .83, .975, .85, .1, "band")]),
    'xiaomi_mix_fold_4': dict(r=.145, aspect=.6, width=27, el=[mod(.06, .07, .94, .68, .19, "dark"), ln(.23, .235, .18), ln(.48, .235, .18), ln(.23, .49, .18), ln(.48, .49, .18), fl(.77, .52, .04)]),
    'xiaomi_mi_10': dict(r=.145, aspect=.6, el=[pill(.12, .12, .29, .72), ln(.205, .235, .14), ln(.205, .45, .09), ln(.205, .62, .10), ln(.205, .9, .14), fl(.205, 1.075, .07)]),
    'xiaomi_mi_10_pro': dict(r=.145, aspect=.6, el=[pill(.12, .12, .29, .72), ln(.205, .235, .14), ln(.205, .45, .09), ln(.205, .62, .10), ln(.205, .9, .14), fl(.205, 1.075, .07)]),
    'xiaomi_mi_11': dict(r=.145, aspect=.6, el=[mod(.07, .07, .51, .62, .24, "body"), pill(.10, .10, .32, .58), ln(.21, .235, .19), ln(.21, .46, .13), ln(.41, .22, .09), fl(.41, .395, .055)]),
    'xiaomi_mi_11_ultra': dict(r=.145, aspect=.6, el=[mod(.065, .075, .935, .60, .18, "camera_dark"), ln(.23, .235, .21), ln(.46, .235, .185), peri(.23, .445, .135, .12), pill(.595, .155, .63, .31, "metal"), fl(.6125, .2325, .025), mod(.70, .135, .89, .535, .16, "dark")]),
    'xiaomi_11t': dict(r=.145, aspect=.6, el=[mod(.07, .08, .48, .66, .2, "dark"), pill(.10, .105, .31, .62), ln(.205, .24, .16), ln(.205, .52, .16), ln(.39, .25, .075), fl(.39, .45, .05)]),
    'xiaomi_11t_pro': dict(r=.145, aspect=.6, el=[mod(.07, .08, .48, .66, .2, "dark"), pill(.10, .105, .31, .62), ln(.205, .24, .16), ln(.205, .52, .16), ln(.39, .25, .075), fl(.39, .45, .05)]),
    'xiaomi_12': dict(r=.145, aspect=.6, el=[mod(.07, .07, .43, .70, .17, "body"), ln(.25, .255, .245), ln(.19, .51, .075), ln(.19, .625, .075), fl(.34, .54, .06)]),
    'xiaomi_12_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .43, .70, .17, "body"), ln(.25, .255, .245), ln(.19, .51, .075), ln(.19, .625, .075), fl(.34, .54, .06)]),
    'xiaomi_12t': dict(r=.145, aspect=.6, el=[mod(.07, .07, .43, .70, .14, "metal"), mod(.09, .09, .41, .39, .12, "dark"), ln(.25, .24, .21), ln(.185, .475, .09), ln(.185, .61, .09), fl(.33, .54, .055)]),
    'xiaomi_12t_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .43, .70, .14, "metal"), mod(.09, .09, .41, .39, .12, "dark"), ln(.25, .24, .21), ln(.185, .475, .09), ln(.185, .61, .09), fl(.33, .54, .055)]),
    'xiaomi_13': dict(r=.145, aspect=.6, el=[mod(.075, .07, .555, .59, .2, "dark"), ln(.215, .215, .12), ln(.215, .44, .12), ln(.405, .24, .075), fl(.41, .46, .06)]),
    'xiaomi_13_pro': dict(r=.145, aspect=.6, el=[mod(.07, .065, .57, .615, .19, "dark"), ln(.215, .22, .15), ln(.435, .24, .11), ln(.215, .455, .155), fl(.68, .33, .055)]),
    'xiaomi_13t': dict(r=.145, aspect=.6, el=[mod(.065, .07, .61, .62, .12, "dark"), pill(.10, .11, .34, .58), ln(.22, .235, .19), ln(.22, .46, .19), ln(.46, .215, .12), fl(.46, .46, .065)]),
    'xiaomi_13t_pro': dict(r=.145, aspect=.6, el=[mod(.065, .07, .61, .62, .12, "dark"), pill(.10, .11, .34, .58), ln(.22, .235, .19), ln(.22, .46, .19), ln(.46, .215, .12), fl(.46, .46, .065)]),
    'xiaomi_13_ultra': dict(r=.145, aspect=.6, el=[circ(.50, .49, .86, "metal"), circ(.50, .49, .81, "dark"), ln(.33, .31, .15), ln(.69, .33, .15), ln(.32, .64, .15), ln(.69, .65, .15), fl(.43, .79, .035), fl(.54, .79, .035)]),
    'xiaomi_14': dict(r=.145, aspect=.6, el=[mod(.075, .07, .62, .64, .18, "dark"), ln(.24, .235, .19), ln(.47, .245, .17), ln(.24, .48, .18), fl(.71, .34, .055)]),
    'xiaomi_15': dict(r=.145, aspect=.6, el=[mod(.075, .07, .62, .64, .18, "dark"), ln(.24, .235, .19), ln(.47, .245, .17), ln(.24, .48, .18), fl(.71, .34, .055)]),
    'xiaomi_14t': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_14t_pro': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_15t': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_15t_pro': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_17': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_17t': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_17t_pro': dict(r=.145, aspect=.6, el=[mod(.075, .075, .63, .64, .2, "body"), ln(.235, .235, .19), ln(.47, .235, .18), ln(.235, .48, .19), fl(.47, .48, .07)]),
    'xiaomi_14_ultra': dict(r=.145, aspect=.6, el=[circ(.5, .50, .86, "metal"), circ(.5, .50, .815, "dark"), ln(.325, .32, .155), ln(.685, .32, .155), ln(.325, .66, .155), ln(.685, .66, .155), fl(.445, .8, .03), fl(.55, .8, .03)]),
    'xiaomi_15_ultra': dict(r=.145, aspect=.6, el=[circ(.5, .50, .86, "metal"), circ(.5, .50, .815, "dark"), ln(.325, .32, .155), ln(.685, .32, .155), ln(.325, .66, .155), ln(.685, .66, .155), fl(.445, .8, .03), fl(.55, .8, .03)]),
    'xiaomi_17_ultra': dict(r=.145, aspect=.6, el=[circ(.5, .50, .86, "metal"), circ(.5, .50, .815, "dark"), ln(.325, .40, .22), ln(.35, .715, .105), ln(.67, .715, .105), fl(.45, .17, .035), fl(.53, .17, .035)]),
    'xiaomi_18_pro_cn': dict(r=.145, aspect=.6, el=[mod(.07, .08, .93, .67, .2, "metal"), mod(.09, .105, .91, .645, .18, "dark"), ln(.23, .26, .19), peri(.23, .505, .14, .16), pill(.44, .14, .87, .61), pill(.13, .755, .33, .84), fl(.42, .80, .065)]),
    'xiaomi_18_pro_max_cn': dict(r=.145, aspect=.6, el=[mod(.07, .08, .93, .67, .2, "metal"), mod(.09, .105, .91, .645, .18, "dark"), ln(.23, .26, .19), peri(.23, .505, .14, .16), pill(.44, .14, .87, .61), pill(.13, .755, .33, .84), fl(.42, .80, .065)]),
    'redmi_note_13_5g': dict(r=.145, aspect=.6, el=[ln(.23, .23, .23), ln(.23, .52, .23), ln(.49, .22, .105), fl(.49, .40, .055)]),
    'redmi_note_13_pro_5g': dict(r=.145, aspect=.6, el=[mod(.07, .08, .62, .68, .10, "body"), ln(.23, .23, .23), ln(.23, .52, .23), ln(.49, .22, .105), fl(.49, .40, .055)]),
    'redmi_note_13_pro_plus_5g': dict(r=.145, aspect=.6, el=[ln(.23, .23, .23), ln(.23, .52, .23), ln(.49, .22, .105), fl(.49, .40, .055)]),
    'redmi_note_14': dict(r=.145, aspect=.6, el=[ln(.23, .23, .23), ln(.23, .52, .23), ln(.49, .23, .105), fl(.49, .42, .055)]),
    'redmi_note_14_5g': dict(r=.145, aspect=.6, el=[mod(.07, .075, .62, .65, .16, "body"), ln(.235, .235, .22), ln(.465, .235, .19), ln(.235, .48, .16), fl(.465, .48, .055)]),
    'redmi_note_14_pro': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_14_pro_5g': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_14_pro_plus_5g': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "dark"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_15': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_15_5g': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_15_pro': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_15_pro_5g': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'redmi_note_15_pro_plus_5g': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.355, .25, .21), ln(.645, .25, .175), circ(.355, .535, .18, "dark"), circ(.645, .535, .18, "dark"), fl(.645, .535, .08)]),
    'poco_f2_pro': dict(r=.145, aspect=.6, el=[circ(.5, .43, .55, "dark"), ln(.385, .31, .105), ln(.615, .31, .105), ln(.385, .55, .105), ln(.615, .55, .105), fl(.5, .81, .07)]),
    'poco_f3': dict(r=.145, aspect=.6, el=[mod(.07, .075, .48, .70, .28, "body"), pill(.105, .105, .345, .66), ln(.225, .24, .19), ln(.225, .52, .19), ln(.225, .375, .055), fl(.405, .45, .055)]),
    'poco_f4': dict(r=.145, aspect=.6, el=[mod(.065, .07, .46, .76, .13, "dark"), circ(.265, .31, .36, "dark"), ln(.265, .205, .085), ln(.185, .365, .075), ln(.345, .365, .075), fl(.25, .63, .055)]),
    'poco_f4_gt': dict(r=.145, aspect=.6, el=[mod(.075, .07, .37, .70, .16, "dark"), ln(.225, .22, .13), ln(.225, .39, .08), ln(.225, .56, .13), fl(.46, .37, .07)]),
    'poco_f5': dict(r=.145, aspect=.6, el=[ln(.24, .25, .24), ln(.24, .555, .24), ln(.48, .24, .10), fl(.48, .44, .055)]),
    'poco_f5_pro': dict(r=.145, aspect=.6, el=[mod(.07, .07, .47, .77, .17, "dark"), ln(.24, .23, .18), ln(.24, .48, .18), ln(.24, .665, .09), fl(.385, .43, .06)]),
    'poco_f6': dict(r=.145, aspect=.6, el=[ln(.25, .25, .26), ln(.25, .56, .26), circ(.57, .40, .145, "dark"), fl(.57, .40, .065)]),
    'poco_f6_pro': dict(r=.145, aspect=.6, el=[mod(.06, .07, .94, .65, .13, "dark"), ln(.23, .235, .17), ln(.455, .235, .17), ln(.23, .48, .17), circ(.455, .48, .17, "dark"), fl(.455, .48, .085)]),
    'poco_x6_pro': dict(r=.145, aspect=.6, el=[mod(.06, .07, .94, .65, .13, "dark"), ln(.23, .235, .17), ln(.455, .235, .17), ln(.23, .48, .17), circ(.455, .48, .17, "dark"), fl(.455, .48, .085)]),
    'poco_f7': dict(r=.145, aspect=.6, el=[pill(.08, .08, .40, .70, "body"), ln(.24, .255, .24), ln(.24, .515, .24), fl(.52, .37, .055)]),
    'poco_f7_pro': dict(r=.145, aspect=.6, el=[mod(.055, .075, .945, .675, .1, "dark"), circ(.35, .37, .535, "metal"), circ(.35, .37, .49, "dark"), ln(.255, .265, .13), ln(.445, .265, .13), ln(.255, .48, .13), fl(.725, .255, .075)]),
    'poco_f7_ultra': dict(r=.145, aspect=.6, el=[mod(.055, .075, .945, .675, .1, "dark"), circ(.35, .37, .535, "metal"), circ(.35, .37, .49, "dark"), ln(.255, .265, .13), ln(.445, .265, .13), ln(.255, .48, .13), fl(.725, .255, .075)]),
    'poco_f8_pro': dict(r=.145, aspect=.6, el=[mod(.065, .07, .935, .69, .17, "metal"), ln(.235, .245, .18), ln(.48, .245, .18), ln(.235, .50, .18), circ(.48, .50, .18, "dark"), fl(.355, .37, .045)]),
    'poco_f8_ultra': dict(r=.145, aspect=.6, el=[mod(.065, .07, .935, .69, .17, "metal"), ln(.235, .245, .18), ln(.48, .245, .18), ln(.235, .50, .18), circ(.48, .50, .18, "dark"), fl(.355, .37, .045), circ(.765, .40, .22, "body"), circ(.765, .40, .155, "metal")]),
    'poco_x7': dict(r=.145, aspect=.6, el=[mod(.19, .08, .81, .70, .26, "body"), ln(.35, .25, .18), ln(.65, .25, .18), ln(.35, .53, .18), circ(.65, .53, .18, "dark"), fl(.65, .53, .08)]),
    'poco_x7_pro': dict(r=.145, aspect=.6, el=[ln(.235, .245, .23), ln(.235, .535, .23), fl(.48, .37, .055)]),
    'poco_x8_pro': dict(r=.145, aspect=.6, el=[ln(.235, .24, .225), ln(.235, .52, .225), fl(.475, .37, .055)]),
    'poco_x8_pro_max': dict(r=.145, aspect=.6, el=[ln(.235, .24, .225), ln(.235, .52, .225), fl(.475, .37, .055)]),
    'honor_30_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.075, .075, .44, .72, .16, "dark"), ln(.235, .225, .14), ln(.235, .41, .13), peri(.235, .59, .105, .09), fl(.37, .255, .045)]),
    'honor_magic3_pro_plus': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.14, .11, .86, .78, .32, "metal"), circ(.5, .445, .69, "dark"), ln(.32, .29, .14), ln(.67, .29, .14), ln(.32, .58, .14), peri(.67, .58, .12, .10), fl(.5, .74, .04)]),
    'honor_magic4_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.5, .49, .83, "metal"), circ(.5, .49, .765, "dark"), ln(.5, .49, .24), ln(.50, .235, .13), ln(.255, .46, .13), ln(.745, .46, .13), fl(.50, .775, .05)]),
    'honor_magic5': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.5, .47, .75, "body"), ln(.5, .245, .17), ln(.34, .54, .17), ln(.66, .54, .17), fl(.5, .71, .055)]),
    'honor_magic5_pro': dict(logo=('honor', 0.5, 0.78, 0.25), r=.145, aspect=.6, el=[circ(.5, .47, .75, "body"), ln(.5, .245, .17), ln(.34, .54, .17), ln(.66, .54, .17), fl(.5, .71, .055)]),
    'honor_magic6_pro': dict(logo=('honor', 0.5, 0.80, 0.25), r=.145, aspect=.6, el=[mod(.115, .10, .885, .86, .37, "metal"), circ(.5, .475, .69, "body"), ln(.5, .315, .22), ln(.35, .59, .18), ln(.65, .59, .18), fl(.275, .30, .045)]),
    'honor_magic7': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.5, .49, .81, "metal"), circ(.5, .49, .755, "dark"), ln(.34, .33, .17), ln(.66, .33, .17), ln(.34, .66, .17), ln(.66, .66, .17), fl(.5, .185, .045)]),
    'honor_magic7_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.5, .49, .81, "metal"), circ(.5, .49, .755, "dark"), ln(.34, .33, .17), ln(.66, .33, .17), ln(.34, .66, .17), ln(.66, .66, .17), fl(.5, .185, .045)]),
    'honor_magic8_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.5, .49, .82, "metal"), circ(.5, .49, .755, "dark"), ln(.5, .285, .195), ln(.325, .61, .19), ln(.675, .61, .19), fl(.735, .31, .045)]),
    'honor_90': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[circ(.26, .25, .35, "metal"), circ(.26, .25, .33, "dark"), ln(.26, .18, .09), ln(.26, .33, .09), circ(.26, .665, .35, "metal"), circ(.26, .665, .33, "dark"), ln(.26, .59, .09), fl(.26, .735, .065)]),
    'honor_200': dict(logo=('honor', 0.14, 0.85, 0.25, -90), r=.145, aspect=.6, el=[mod(.075, .07, .455, .80, .48, "metal"), mod(.095, .09, .435, .78, .48, "dark"), ln(.27, .22, .12), ln(.195, .435, .12), ln(.27, .65, .12), fl(.36, .445, .04)]),
    'honor_200_pro': dict(logo=('honor', 0.14, 0.85, 0.25, -90), r=.145, aspect=.6, el=[mod(.075, .07, .455, .80, .48, "metal"), mod(.095, .09, .435, .78, .48, "dark"), ln(.27, .22, .12), ln(.195, .435, .12), ln(.27, .65, .12), fl(.36, .445, .04)]),
    'honor_400': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.075, .07, .51, .755, .43, "body"), ln(.255, .25, .235), ln(.255, .56, .235), circ(.445, .405, .115, "dark"), fl(.445, .405, .06)]),
    'honor_400_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.075, .07, .60, .825, .43, "body"), ln(.23, .245, .21), ln(.45, .435, .21), ln(.23, .635, .21), fl(.17, .43, .055)]),
    'honor_600': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.075, .075, .925, .61, .23, "body"), ln(.235, .225, .18), ln(.235, .45, .18), fl(.445, .25, .055), circ(.445, .425, .075, "dark")]),
    'honor_600_pro': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.075, .075, .925, .61, .23, "body"), ln(.235, .225, .18), ln(.235, .45, .18), ln(.45, .345, .18), fl(.80, .22, .055), circ(.80, .46, .075, "dark")]),
    'honor_magic_v2': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, width=27, el=[mod(.07, .07, .49, .83, .13, "metal"), mod(.095, .095, .465, .81, .11, "dark"), ln(.255, .23, .17), ln(.255, .45, .17), ln(.255, .67, .17), fl(.41, .65, .05)]),
    'honor_magic_v3': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, width=27, el=[honor_cam('v3', .5, .46, .78), peri(.62, .31, .15, .14), ln(.345, .61, .17), ln(.655, .61, .17), fl(.5, .61, .05)]),
    'honor_magic_v5': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, width=27, el=[honor_cam('v5', .5, .46, .84), peri(.63, .30, .17, .145), ln(.34, .61, .175), ln(.66, .61, .175), fl(.5, .61, .055)]),
    'honor_magic_v6': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, width=27, el=[honor_cam('v6', .5, .46, .84), peri(.64, .32, .17, .145), ln(.34, .35, .16), ln(.35, .62, .17), fl(.55, .61, .055)]),
    'honor_robot_phone': dict(logo=('honor', 0.5, 0.85, 0.25), r=.145, aspect=.6, el=[mod(.065, .07, .935, .66, .19, "dark"), mod(.115, .11, .465, .61, .18, "metal"), peri(.29, .42, .22, .21), ln(.62, .27, .12), ln(.62, .50, .11), fl(.81, .27, .055)]),
    'motorola_edge_plus_2020': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[pill(.075, .12, .315, .78, "body"), ln(.195, .235, .15), ln(.195, .445, .15), ln(.195, .65, .15), fl(.365, .66, .05)]),
    'motorola_edge_20_pro': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .405, .78, .14, "body"), peri(.215, .21, .13, .12), ln(.215, .41, .16), ln(.215, .62, .16), fl(.34, .67, .045)]),
    'motorola_edge_30_ultra': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.065, .07, .49, .585, .17, "body"), ln(.26, .235, .235), ln(.205, .46, .13), ln(.385, .46, .11), fl(.44, .22, .045)]),
    'motorola_edge_40_pro': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.065, .07, .585, .64, .19, "body"), ln(.245, .245, .21), ln(.245, .49, .21), ln(.465, .29, .12), fl(.465, .48, .07)]),
    'motorola_edge_50_ultra': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.065, .07, .615, .64, .22, "body"), ln(.24, .245, .21), ln(.475, .245, .21), peri(.24, .49, .15, .13), fl(.49, .455, .05)]),
    'motorola_edge_60_pro': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .64, .68, .23, "body"), ln(.24, .235, .19), circ(.48, .235, .19, "dark"), fl(.48, .235, .08), ln(.24, .50, .19), ln(.48, .50, .19)]),
    'motorola_signature': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .65, .685, .23, "body"), ln(.245, .235, .20), ln(.495, .235, .20), peri(.245, .50, .15, .145), circ(.495, .50, .20, "dark"), fl(.495, .50, .08)]),
    'motorola_edge_70_pro': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .63, .675, .23, "body"), ln(.24, .235, .195), ln(.475, .235, .195), ln(.24, .50, .195), circ(.475, .50, .195, "dark"), fl(.475, .50, .08)]),
    'motorola_edge_2026': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .63, .675, .23, "body"), ln(.24, .235, .195), ln(.475, .235, .195), ln(.24, .50, .195), ln(.475, .50, .16)]),
    'motorola_moto_g_stylus_2026': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .63, .675, .23, "body"), ln(.24, .235, .195), circ(.475, .235, .195, "dark"), fl(.475, .235, .08), ln(.24, .50, .195), circ(.475, .50, .195, "dark")]),
    'motorola_moto_g_power_2026': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.07, .07, .59, .645, .23, "body"), ln(.24, .235, .19), ln(.24, .49, .19), circ(.445, .235, .12, "dark"), fl(.445, .235, .06), circ(.445, .49, .12, "dark")]),
    'motorola_razr_fold': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, width=27, el=[mod(.07, .07, .64, .68, .23, "body"), ln(.245, .235, .195), ln(.49, .235, .195), peri(.245, .50, .14, .145), circ(.49, .50, .195, "dark"), fl(.49, .50, .08)]),
    'motorola_razr_5g': dict(logo=('motorola', 0.5, 0.62, 0.13), r=.145, aspect=.6, el=[mod(.025, .025, .975, .805, .17, "dark"), mod(.10, .295, .90, .73, .16, "dark"), pill(.32, .06, .69, .25, "metal"), ln(.525, .155, .115), fl(.375, .155, .045), mod(.025, .82, .975, .85, .15, "metal")]),
    'motorola_razr_ultra_2026': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .79, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),
    'motorola_razr_plus_2026': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .79, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),
    'motorola_razr_2026': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .79, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),

    'motorola_edge_30_pro': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[pill(.07, .075, .39, .84, "body"), ln(.23, .245, .22), ln(.23, .53, .22), ln(.23, .73, .10), fl(.43, .45, .05)]),
    'motorola_razr_40': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, el=[mod(.055, .07, .945, .385, .22, "dark"), ln(.205, .205, .15), ln(.385, .205, .14), fl(.165, .32, .035), mod(.525, .105, .905, .345, .17, "dark"), mod(.025, .82, .975, .85, .15, "metal")]),
    'motorola_razr_40_ultra': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .79, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),
    'motorola_razr_50': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.035, .035, .965, .78, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),
    'motorola_razr_50_ultra': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .81, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .84, .975, .86, .15, "band")]),
    'motorola_razr_60': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.035, .035, .965, .78, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .82, .975, .85, .15, "band")]),
    'motorola_razr_60_ultra': dict(logo=('motorola', 0.5, 0.74, 0.13), r=.145, aspect=.6, wide_panel=True, el=[mod(.025, .025, .975, .81, .5, "dark"), ln(.205, .21, .17), ln(.40, .21, .16), fl(.565, .21, .04), mod(.025, .84, .975, .86, .15, "band")]),

    'motorola_edge_70_pro_plus': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.065, .07, .635, .65, .16, "body"), ln(.225, .225, .21), ln(.475, .225, .21), ln(.225, .475, .21), circ(.475, .475, .21, "dark"), fl(.475, .475, .077)]),
    'motorola_edge_70_max': dict(logo=('motorola', 0.5, 0.53, 0.13), r=.145, aspect=.6, el=[mod(.065, .07, .64, .67, .16, "body"), ln(.225, .225, .22), ln(.475, .225, .21), ln(.225, .485, .22), circ(.475, .485, .21, "dark"), fl(.475, .485, .077)]),

}

# tablets: (aspect w/h, elements); landscape unless aspect < 1
TABLETS = {
    "oneplus_pad": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=258.03/189.41, el=[circ(.5, .10, .085, "metal"), ln(.5, .10, .066)]),
    "oneplus_pad_go": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=255.12/188.04, el=[mod(0, 0, 1, .15, 0, "band"), circ(.5, .085, .075, "metal"), ln(.5, .085, .055)]),
    "oneplus_pad_2": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=268.66/195.06, el=[circ(.5, .095, .075, "metal"), ln(.5, .095, .055)]),
    "oneplus_pad_pro": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=268.66/195.06, el=[circ(.5, .095, .075, "metal"), ln(.5, .095, .055)]),
    "oneplus_pad_2025_cn": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=1.54, el=[circ(.5, .105, .10, "dark"), ln(.5, .118, .025), fl(.5, .087, .012)]),
    "oneplus_pad_2_2025_cn": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=1.38, el=[pill(.844, .028, .972, .092), ln(.93, .06, .03), fl(.868, .06, .014)]),
    "oneplus_pad_2_pro": dict(r=.065, logo=("oneplus", .5, .52, .055), aspect=289.61/209.66, el=[pill(.844, .028, .972, .092), ln(.93, .06, .03), fl(.868, .06, .014)]),
    "oneplus_pad_3": dict(r=0.065, logo=("oneplus", 0.5, 0.52, 0.05), aspect=289.61 / 209.66, el=[pill(.846, .026, .975, .09, "metal"), ln(.94, .057, .025), fl(.878, .057, .014)]),
    "oneplus_pad_3_pro": dict(r=0.065, logo=("oneplus", 0.5, 0.5, 0.04), aspect=289.7 / 209.8, el=[pill(.8475, .0275, .975, .0875, "metal"), ln(.94, .056, .025), fl(.88, .056, .014)]),
    "oneplus_pad_4": dict(r=0.065, logo=("oneplus", 0.5, 0.5, 0.04), aspect=289.71 / 209.76, el=[pill(.8475, .0275, .975, .0875, "metal"), ln(.94, .056, .025), fl(.88, .056, .014)]),
    "oneplus_pad_go_2": dict(r=0.065, logo=("oneplus", 0.5, 0.52, 0.08), aspect=192.8 / 266, el=[circ(.12, .08, .1, "metal"), ln(.12, .08, .065, "dark")]),
    "oneplus_pad_lite": dict(r=0.065, logo=("oneplus", 0.5, 0.55, 0.05), aspect=254.9 / 166.5, el=[circ(.5, .07, .07, "metal"), ln(.5, .07, .045, "dark")]),
    "oppo_pad_6": dict(r=0.065, logo=("oppo", 0.5, 0.5, 0.09), aspect=266.9 / 193.4, el=[pill(.86, .03, .97, .09, "dark"), ln(.89, .06, .04, "metal"), fl(.94, .06, .02)]),
    "oppo_pad_5_pro": dict(r=0.065, aspect=289.7 / 208.8, el=[pill(.86, .03, .97, .09, "dark"), ln(.89, .06, .04, "metal"), fl(.94, .06, .02)]),
    "oppo_pad_mini": dict(r=0.085, aspect=194.4 / 132.4, el=[pill(.84, .03, .97, .10, "dark"), ln(.88, .065, .045, "metal"), fl(.93, .065, .022)]),
    "galaxy_tab_s11": dict(r=0.065, aspect=253.8 / 165.3, wm=True, el=[ln(.94, .06, .05, "dark"), fl(.94, .12, .018)]),
    "galaxy_tab_s6": dict(r=.065, aspect=244.5/159.5, wm=True, el=[pill(.865, .025, .975, .08), ln(.89, .0525, .035), ln(.95, .0525, .035)]),
    "galaxy_tab_s6_lite_2020": dict(r=.065, aspect=244.5/154.3, wm=True, el=[ln(.955, .045, .043, "dark")]),
    "galaxy_tab_s6_lite_2022": dict(r=.065, aspect=244.5/154.3, wm=True, el=[ln(.955, .045, .043, "dark")]),
    "galaxy_tab_s6_lite_2024": dict(r=.065, aspect=244.5/154.3, wm=True, el=[ln(.955, .045, .043, "dark")]),
    "galaxy_tab_s7": dict(r=.065, aspect=253.8/165.3, wm=True, el=[pill(.49, .025, .975, .082), ln(.95, .053, .038), ln(.90, .053, .038), fl(.85, .053, .015)]),
    "galaxy_tab_s7_plus": dict(r=.065, aspect=285/185, wm=True, el=[pill(.53, .023, .976, .076), ln(.952, .05, .034), ln(.907, .05, .034), fl(.86, .05, .014)]),
    "galaxy_tab_s7_fe": dict(r=.065, aspect=284.8/185, wm=True, el=[ln(.954, .049, .038, "dark")]),
    "galaxy_tab_s8": dict(r=.065, aspect=253.8/165.3, wm=True, el=[pill(.49, .025, .975, .082), ln(.95, .053, .038), ln(.90, .053, .038), fl(.85, .053, .015)]),
    "galaxy_tab_s8_plus": dict(r=.065, aspect=285/185, wm=True, el=[pill(.53, .023, .976, .076), ln(.952, .05, .034), ln(.907, .05, .034), fl(.86, .05, .014)]),
    "galaxy_tab_s8_ultra": dict(r=.065, aspect=326.4/208.6, wm=True, el=[pill(.59, .022, .977, .072), ln(.955, .047, .032), ln(.913, .047, .032), fl(.87, .047, .013)]),
    "galaxy_tab_s9": dict(r=.065, aspect=254.3/165.8, wm=True, el=[pill(.50, .035, .88, .063), ln(.948, .049, .046, "dark"), fl(.896, .049, .014)]),
    "galaxy_tab_s9_plus": dict(r=.065, aspect=285.4/185.4, wm=True, el=[pill(.53, .035, .835, .063), ln(.948, .049, .042, "dark"), ln(.896, .049, .042, "dark"), fl(.848, .049, .014)]),
    "galaxy_tab_s9_ultra": dict(r=.065, aspect=326.4/208.6, wm=True, el=[pill(.58, .032, .85, .058), ln(.954, .045, .039, "dark"), ln(.906, .045, .039, "dark"), fl(.862, .045, .013)]),
    "galaxy_tab_s9_fe": dict(r=.065, aspect=254.3/165.8, wm=True, el=[ln(.95, .049, .045, "dark")]),
    "galaxy_tab_s9_fe_plus": dict(r=.065, aspect=285.4/185.4, wm=True, el=[ln(.948, .049, .041, "dark"), ln(.896, .049, .041, "dark")]),
    "galaxy_tab_s10_plus": dict(r=.065, aspect=285.4/185.4, wm=True, el=[pill(.53, .035, .835, .063), ln(.948, .049, .042, "dark"), ln(.896, .049, .042, "dark"), fl(.848, .049, .014)]),
    "galaxy_tab_s10_ultra": dict(r=.065, aspect=326.4/208.6, wm=True, el=[pill(.58, .032, .85, .058), ln(.954, .045, .039, "dark"), ln(.906, .045, .039, "dark"), fl(.862, .045, .013)]),
    "galaxy_tab_s10_fe": dict(r=.065, aspect=254.3/165.8, wm=True, el=[ln(.95, .049, .045, "dark")]),
    "galaxy_tab_s10_fe_plus": dict(r=.065, aspect=300.6/194.7, wm=True, el=[ln(.953, .046, .041, "dark")]),
    "galaxy_tab_s11_ultra": dict(r=0.065, aspect=326.3 / 208.5, wm=True, el=[ln(.88, .05, .04, "dark"), ln(.93, .05, .04, "dark"), fl(.84, .05, .015)]),
    "galaxy_tab_s12_plus": dict(r=0.065, aspect=289.5 / 187.8, wm=True, el=[ln(.94, .06, .045, "dark"), fl(.90, .06, .015)]),
    "galaxy_tab_s12_ultra": dict(r=0.065, aspect=326.3 / 208.5, wm=True, el=[ln(.88, .05, .04, "dark"), ln(.93, .05, .04, "dark"), fl(.84, .05, .015)]),
    "galaxy_tab_s10_lite": dict(r=0.065, aspect=254.3 / 165.8, wm=True, el=[ln(.95, .06, .05, "dark")]),
    "galaxy_tab_a11": dict(r=0.065, aspect=124.7 / 211, wm=True, el=[ln(.12, .08, .1, "dark")]),
    "galaxy_tab_a11_plus": dict(r=0.065, aspect=257.1 / 168.7, wm=True, el=[ln(.95, .06, .045, "dark")]),
    # Additional vendor tablets, 2020 onward.
    'xiaomi_pad_5': dict(r=.065, aspect=1.55, el=[pill(.80, .028, .97, .13, "metal"), ln(.93, .077, .045), circ(.858, .077, .045, "dark"), fl(.86, .11, .014)]),
    'xiaomi_pad_7_ultra': dict(r=.065, aspect=1.50, el=[mod(.81, .03, .97, .11, .25, "body"), pill(.83, .044, .96, .096), ln(.933, .07, .044), fl(.865, .07, .018)]),
    'xiaomi_pad_7s_pro_12_5': dict(r=.065, aspect=1.50, el=[mod(.81, .03, .97, .11, .25, "body"), pill(.83, .044, .96, .096), ln(.933, .07, .044), fl(.865, .07, .018)]),
    'xiaomi_pad_9': dict(r=.065, aspect=1.50, el=[mod(.82, .028, .975, .11, .22, "body"), pill(.847, .04, .965, .093), ln(.94, .066, .044), fl(.874, .066, .017)]),
    'xiaomi_pad_9_pro_max': dict(r=.065, aspect=1.50, el=[mod(.845, .026, .975, .096, .22, "body"), pill(.866, .038, .966, .086), ln(.946, .063, .035), fl(.887, .063, .015)]),
    'xiaomi_pad_6': dict(r=.065, aspect=1.56, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_6s_pro_12_4': dict(r=.065, aspect=1.47, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_7': dict(r=.065, aspect=1.46, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_7_pro': dict(r=.065, aspect=1.46, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_8': dict(r=.065, aspect=1.46, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_8_pro': dict(r=.065, aspect=1.46, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'xiaomi_pad_mini': dict(r=.065, aspect=1.54, el=[pill(.78, .03, .97, .13, "body"), ln(.928, .08, .055)]),
    'redmi_pad': dict(r=.065, aspect=1.59, el=[mod(.80, .03, .97, .11, .12, "dark"), ln(.935, .07, .044)]),
    'redmi_pad_se': dict(r=.065, aspect=1.59, el=[mod(.79, .03, .97, .115, .18, "body"), mod(.845, .04, .96, .105, .2, "dark"), ln(.935, .072, .045)]),
    'redmi_pad_se_8_7': dict(r=.065, aspect=1.59, el=[ln(.945, .07, .06, "dark")]),
    'redmi_pad_pro': dict(r=.065, aspect=1.59, el=[ln(.935, .075, .065), circ(.83, .075, .065, "dark"), fl(.83, .075, .025)]),
    'redmi_pad_2': dict(r=.065, aspect=1.59, el=[pill(.80, .035, .97, .12), ln(.932, .077, .045), fl(.86, .077, .018)]),
    'redmi_pad_2_pro': dict(r=.065, aspect=1.59, el=[ln(.935, .075, .065), circ(.83, .075, .065, "dark"), fl(.83, .075, .025)]),
    'redmi_pad_2_9_7': dict(r=.065, aspect=1.59, el=[pill(.80, .035, .97, .12, "body"), ln(.933, .077, .048)]),
    'poco_pad': dict(r=.065, aspect=1.58, el=[ln(.935, .075, .065), circ(.83, .075, .065, "dark"), fl(.83, .075, .025)]),
    'poco_pad_m1': dict(r=.065, aspect=1.58, el=[ln(.935, .075, .065), circ(.83, .075, .065, "dark"), fl(.83, .075, .025)]),
    'poco_pad_x1': dict(r=.065, aspect=1.46, el=[mod(.79, .03, .97, .145, .22, "metal"), mod(.805, .043, .957, .13, .22, "dark"), ln(.925, .077, .043), fl(.845, .095, .018)]),
    'poco_pad_c1': dict(r=.065, aspect=1.58, el=[pill(.79, .035, .97, .12, "body"), ln(.932, .077, .048)]),
    'honor_pad_8': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[pill(.875, .03, .975, .085), ln(.948, .0575, .025)]),
    'honor_pad_9': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[circ(.5, .065, .055, "dark"), ln(.5, .065, .029)]),
    'honor_pad_10': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[circ(.94, .065, .075, "metal"), ln(.925, .07, .035), fl(.957, .065, .013)]),
    'honor_pad_v9': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[ln(.94, .06, .055), circ(.855, .06, .055, "metal"), fl(.855, .06, .015)]),
    'honor_pad_20': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[ln(.94, .065, .055)]),
    'honor_pad_20_pro': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[ln(.94, .065, .055)]),
    'honor_magicpad_2': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[circ(.94, .065, .055, "dark"), ln(.94, .075, .025), fl(.94, .047, .012)]),
    'honor_magicpad_3': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[mod(.865, .025, .976, .105, .28, "metal"), ln(.947, .065, .032), ln(.901, .065, .032), fl(.90, .089, .012)]),
    'honor_magicpad_4': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.56, el=[mod(.865, .025, .976, .105, .28, "metal"), ln(.947, .065, .032), ln(.901, .065, .032), fl(.90, .089, .012)]),
    'motorola_moto_tab_g70': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.5852760736196319, el=[mod(0, 0, 1, .19, 0, "band"), ln(.94, .067, .041), fl(.90, .067, .013)]),
    'motorola_moto_pad_2026': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.56, el=[mod(0, 0, 1, .13, 0, "band"), mod(.83, .025, .972, .12, .2, "body"), ln(.94, .065, .04)]),

    'honor_pad_v6': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.6, el=[mod(.866, .027, .975, .086, .16, "metal"), mod(.875, .035, .966, .079, .15, "dark"), ln(.945, .057, .029), fl(.895, .057, .013)]),
    'honor_magicpad_13': dict(logo=('honor', 0.5, 0.52, 0.11), r=.065, aspect=1.48, el=[ln(.94, .06, .047), circ(.866, .06, .047, "dark"), fl(.866, .06, .019)]),

    'motorola_moto_tab_g62': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.6, el=[mod(0, 0, 1, .16, 0, "band"), ln(.952, .049, .034)]),
    'motorola_moto_pad_60_pro': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.6, el=[mod(0, 0, 1, .13, 0, "band"), mod(.843, .025, .975, .097, .16, "body"), ln(.945, .061, .043), circ(.884, .061, .042, "metal"), fl(.884, .061, .015)]),
    'motorola_moto_pad_60_neo': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.6, el=[mod(0, 0, 1, .13, 0, "band"), mod(.846, .027, .978, .096, .18, "body"), ln(.946, .061, .042)]),
    'motorola_moto_pad_70': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.6, el=[mod(0, 0, 1, .13, 0, "band"), ln(.947, .055, .039)]),
    'motorola_moto_pad_70_pro': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.5, el=[pill(.742, .028, .975, .111, "body"), ln(.94, .069, .049), fl(.874, .069, .014)]),
    'motorola_moto_pad_70_groove': dict(logo=('motorola', 0.5, 0.5, 0.08), r=.065, aspect=1.5, el=[circ(.50, .333, .48, "metal"), circ(.50, .333, .425, "band"), circ(.50, .333, .36, "body"), ln(.955, .05, .035)]),

}



def module(doc, x0, y0, x1, y1, r, kind, top, mid, bot, bottom_r=None):
    w, h = x1 - x0, y1 - y0
    rr = r * min(w, h)
    if kind == "apple_camera":
        if lum(mid) > .22:
            light, dark = mix(mid, "#000000", .14), mix(mid, "#000000", .24)
        else:
            light, dark = mix(mid, "#ffffff", .24), mix(mid, "#ffffff", .14)
        shape = rounded_rect(x0, y0, w, h, rr)
        if bottom_r is not None:
            br = bottom_r
            shape = (f"M{f(x0 + rr)},{f(y0)}H{f(x1 - rr)}A{f(rr)},{f(rr)} 0 0 1 {f(x1)},{f(y0 + rr)}"
                     f"V{f(y1 - br)}A{f(br)},{f(br)} 0 0 1 {f(x1 - br)},{f(y1)}"
                     f"H{f(x0 + br)}A{f(br)},{f(br)} 0 0 1 {f(x0)},{f(y1 - br)}"
                     f"V{f(y0 + rr)}A{f(rr)},{f(rr)} 0 0 1 {f(x0 + rr)},{f(y0)}Z")
        doc.add(shape, doc.lin(x0, y0, x1, y1, [(0, light), (1, dark)]))
    elif kind == "dark":
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x1, y0, x0, y0, [(0, GLASS_TINT), (1, "#111215")]))
    elif kind == "camera_dark":
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x0, y0, x1, y1, [(0, "#535b66"), (1, "#363e48")]))
    elif kind == "band":
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x0, y0, x1, y1, [(0, mix(mid, "#000000", .12)), (1, mix(mid, "#000000", .28))]))
    elif kind in ("camera", "camera_metal", "pixel_panel"):
        # Pixel-style metal: a distinct fill, without layered bevels or shadows.
        light = mix(mid, "#ffffff", .45)
        dark = mix(mid, "#7c889b", .6 if lum(mid) < .2 else .45)
        if kind == "pixel_panel":
            if lum(mid) > .75:
                light, dark = mix(mid, "#000000", .16), mix(mid, "#000000", .24)
            else:
                light, dark = mix(mid, "#ffffff", .34), mix(mid, "#ffffff", .24)
        elif kind == "camera_metal":
            light, dark = mix(light, "#ffffff", .3), mix(dark, "#ffffff", .2)
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x0, y0, x1, y1, [(0, light), (1, dark)]))
    elif kind == "glass":  # transparent upper back window, with a thin frame rather than a raised island
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x1, y0, x0, y1, [(0, mix(top, "#ffffff", .14)), (1, mix(mid, "#000000", .07))]))
        i = min(w, h) * .025
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, rr - i),
                doc.lin(x0, y0, x0, y1, [(0, mix(top, "#ffffff", .08)), (1, mid)]))
    elif kind == "metal":
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x1, y0, x0, y1, [(0, mix(top, "#ffffff", .55)), (1, mix(mid, "#6b6e73", .45))]))
        i = min(w, h) * .02
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, max(rr - i, 0)),
                doc.lin(x0, y0, x1, y1, [(0, mix(top, "#ffffff", .35)), (1, mix(mid, "#9a9da2", .35))]))
    else:  # body-coloured raised module
        light = lum(mid) > .35
        doc.add(rounded_rect(x0, y0, w, h, rr), doc.lin(x1, y0, x0, y1, [(0, mix(mid, "#ffffff", .22 if light else .16)), (1, mix(mid, "#000000", .06))]))
        i = min(w, h) * .015
        doc.add(rounded_rect(x0 + i, y0 + i, w - 2 * i, h - 2 * i, max(rr - i, 0)),
                doc.lin(0, y0, 0, y1, [(0, mix(top, "#ffffff", .15)), (1, mix(mid, top, .5))]))


def draw_elements(doc, els, X0, Y0, k, top, mid, bot, body_width=None, camera_width=None):
    kx = body_width if body_width is not None else k
    reference_k = k
    for e in els:
        k = reference_k if e[0].endswith("_back") or e[0] in ("screw", "dial", "panel", "led") else (camera_width or reference_k)
        if e[0] == "mod":
            _, x0, y0, x1, y1, r, kind = e
            # Circular housings stay circular; rectangular bars follow the body width.
            if r == .5 and abs((x1 - x0) - (y1 - y0)) < 1e-9:
                cx, d = X0 + (x0 + x1) / 2 * kx, (x1 - x0) * k
                module(doc, cx - d / 2, Y0 + y0 * k, cx + d / 2, Y0 + y1 * k, r, kind, top, mid, bot)
            else:
                module(doc, X0 + x0 * kx, Y0 + y0 * k, X0 + x1 * kx, Y0 + y1 * k, r, kind, top, mid, bot)
        elif e[0] == "lens":
            _, cx, cy, d, ring = e
            # A black camera capsule is one glass shape, as in Pixel Tips.
            if any(m[0] == "mod" and m[5] == .5 and m[6] == "dark" and
                   max(m[3] - m[1], m[4] - m[2]) > 1.3 * min(m[3] - m[1], m[4] - m[2]) and
                   m[1] <= cx - d / 2 and m[2] <= cy - d / 2 and
                   m[3] >= cx + d / 2 and m[4] >= cy + d / 2 for m in els):
                continue
            if any(m[0] == "mod" and m[1] <= cx - d / 2 and m[2] <= cy - d / 2 and
                   m[3] >= cx + d / 2 and m[4] >= cy + d / 2 for m in els):
                ring = None
            lens(doc, X0 + cx * kx, Y0 + cy * k, d * k, ring, top, mid, bot)
        elif e[0] == "flash":
            _, cx, cy, d = e
            flash(doc, X0 + cx * kx, Y0 + cy * k, d * k, mid)
        elif e[0] == "honor_cam":
            _, style, cx, cy, d = e
            x, y, size = X0 + cx * kx, Y0 + cy * k, d * k
            r = size / 2
            metal = doc.lin(x - r, y - r, x + r, y + r,
                            [(0, mix(top, "#ffffff", .62)), (.5, mix(mid, "#c9a35a", .28)), (1, mix(bot, "#000000", .38))])
            dark = doc.lin(x + r, y - r, x - r, y + r, [(0, "#313740"), (1, "#0d0f12")])
            if style in ("v3", "v5"):
                # HONOR calls both V3 and V5 housings an octagonal dome. V5's is broader
                # and softer, with a thicker jewellery-like rim in the official renders.
                cut = r * (.34 if style == "v3" else .27)
                pts = [(x-r+cut, y-r), (x+r-cut, y-r), (x+r, y-r+cut), (x+r, y+r-cut),
                       (x+r-cut, y+r), (x-r+cut, y+r), (x-r, y+r-cut), (x-r, y-r+cut)]
                outer = "M" + "L".join(f"{f(px)},{f(py)}" for px, py in pts) + "Z"
                doc.add(outer, metal)
                inset = size * (.075 if style == "v3" else .065)
                ir = r - inset
                if style == "v3":
                    # Magic V3: faceted/octagonal metal jewellery around a circular black glass disk.
                    doc.add(circle(x, y, ir), dark)
                else:
                    icut = cut * .78
                    inner_pts = [(x-ir+icut, y-ir), (x+ir-icut, y-ir), (x+ir, y-ir+icut), (x+ir, y+ir-icut),
                                 (x+ir-icut, y+ir), (x-ir+icut, y+ir), (x-ir, y+ir-icut), (x-ir, y-ir+icut)]
                    inner = "M" + "L".join(f"{f(px)},{f(py)}" for px, py in inner_pts) + "Z"
                    doc.add(inner, dark)
            else:
                # Magic V6 moved to a large circular module with a sculpted metallic rim.
                doc.add(circle(x, y, r), metal)
                doc.add(circle(x, y, r * .86), mix(mid, "#c9a35a", .18))
                doc.add(circle(x, y, r * .78), dark)
        elif e[0] == "manual_glyph":
            nothing_element(doc, e, X0, Y0, kx, top, mid, bot)
        elif e[0] in ("arc", "strip", "led", "seg", "matrix", "redsq", "screw", "camera_screw", "dial", "panel", "dot", "4a_back", "3a_back", "3a_lite_back", "4a_pro_back", "2a_back", "3_back", "cmf2_back"):
            if e[0] in ("led", "seg", "matrix", "redsq", "screw", "camera_screw", "dial", "dot"):
                e = (e[0], (e[1] - .5) * kx / k + .5, *e[2:])
            if e[0] in ("panel", "screw", "dial"):
                raw(doc, f'<g data-detail="{e[0]}">')
            if e[0] == "panel":
                # CMF's two-tone shell reaches both sides of the wider icon.
                e = ("panel", e[1] * k / kx)
                k = kx
            if e[0].endswith("_back"):
                raw(doc, '<g data-detail="rear-contour">')
            nothing_element(doc, e, X0 + (kx - k) / 2, Y0, k, top, mid, bot)
            if e[0].endswith("_back"):
                raw(doc, "</g>")
            if e[0] in ("panel", "screw", "dial"):
                raw(doc, "</g>")
        elif e[0] == "peri":
            _, cx, cy, w, h = e
            if any(m[0] == "mod" and m[5] == .5 and m[6] == "dark" and
                   max(m[3] - m[1], m[4] - m[2]) > 1.3 * min(m[3] - m[1], m[4] - m[2]) and
                   m[1] <= cx - w / 2 and m[2] <= cy - h / 2 and
                   m[3] >= cx + w / 2 and m[4] >= cy + h / 2 for m in els):
                continue
            x, y = X0 + cx * kx - w / 2 * k, Y0 + (cy - h / 2) * k
            doc.add(rounded_rect(x, y, w * k, h * k, w * k * .2),
                    doc.lin(x + w * k, 0, x, 0, [(0, GLASS_TINT), (1, "#111215")]))
        elif e[0] == "glyph":
            # Preserve Nothing's original paths and aspect ratio; measured on the reference back.
            _, name, x0, y0, width = e
            with open(os.path.join(ROOT, "device_icons_svg", "nothing", name + "_glyph_layout.svg"), encoding="utf-8") as fh:
                svg = fh.read()
            vw = float(re.search(r'viewBox="0 0 ([\d.]+)', svg)[1])
            paths = re.findall(r'<path d="([^"]+)"', svg)
            scale = width * k / vw
            # Align the camera light independently of the full-back preview layout.
            if name == "nothing_phone_1":
                camera = re.match(r'.*?Z', paths[0])[0]
                paths[0] = paths[0][len(camera):]
                camera_x = X0 + .185 * kx - 15.36 * scale
                dy, camera_paths = 0, [camera]
            else:
                # The Settings preview includes a lower camera arc absent from the back render.
                camera_paths, paths = [paths[1]], paths[2:]
                camera_x = X0 + .205 * kx - 28.6 * scale
                dy = -.025 * k
            raw(doc, f'<g transform="translate({f(camera_x)} {f(Y0 + y0 * k + dy)}) scale({scale})" fill="{GLYPH_ON}" stroke="{glyph_edge(mid)}" stroke-width="{.12 / scale}" paint-order="stroke" fill-rule="evenodd">' +
                ''.join(f'<path d="{d}"/>' for d in camera_paths) + '</g>')
            raw(doc, f'<g transform="translate({f(X0 + (kx - k) / 2 + x0 * k)} {f(Y0 + y0 * k)}) scale({scale})" fill="{GLYPH_ON}" stroke="{glyph_edge(mid)}" stroke-width="{.25 / scale}" paint-order="stroke" fill-rule="evenodd">' +
                ''.join(f'<path d="{d}"/>' for d in paths) + '</g>')


import math

GLYPH_ON = "#fbfbfb"


def glyph_edge(mid):
    """LED strips are bright white; a thin darker edge keeps them visible on light bodies."""
    return mix(mid, "#000000", .28) if lum(mid) > .55 else mix(mid, "#ffffff", .15)


def raw(doc, svg):
    doc.paths.append((None, svg, None))


def nothing_element(doc, e, X0, Y0, k, top, mid, bot):
    P = lambda x, y: (X0 + x * k, Y0 + y * k)
    w = (.07 if e[0] == "arc" and e[3] == .435 else .05) * k
    edge = glyph_edge(mid)

    def stroke(d, width=w):
        raw(doc, f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="{f(width + .2)}" stroke-linecap="round" stroke-linejoin="round"/>')
        raw(doc, f'<path d="{d}" fill="none" stroke="{GLYPH_ON}" stroke-width="{f(width)}" stroke-linecap="round" stroke-linejoin="round"/>')

    kind = e[0]
    if kind == "manual_glyph":
        # Phone (1)/(2): clipped coil sides, not a generic circular ring.
        # Paths are fitted to the icon silhouette; camera halo retains lens clearance.
        def glyph_path(d, width=.045):
            raw(doc, f'<g transform="translate({f(X0)} {f(Y0)}) scale({k})">')
            raw(doc, f'<path d="{d}" fill="none" stroke="{edge}" stroke-width="{width + .007}" stroke-linecap="round" stroke-linejoin="round"/>')
            raw(doc, f'<path d="{d}" fill="none" stroke="{GLYPH_ON}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')
            raw(doc, '</g>')
        if e[1] == "nothing_phone_1":
            glyph_path('M.31,.15A.125,.125 0 0 0 .06,.15V.325A.125,.125 0 0 0 .31,.325V.28')
            glyph_path('M.925,.73Q.5,.25 .075,.73V1.14Q.5,1.62 .925,1.14V.94')
            glyph_path('M.67,.28L.86,.065')
        else:
            glyph_path('M.335,.163A.13,.13 0 0 0 .075,.163V.27')
            glyph_path('M.075,.325V.378A.13,.13 0 0 0 .335,.378V.33')
            for d in ('M.075,.73Q.18,.615 .34,.575',
                      'M.40,.56Q.69,.50 .925,.73',
                      'M.075,.80V1.10',
                      'M.075,1.16Q.24,1.35 .46,1.38',
                      'M.53,1.38Q.76,1.35 .925,1.16',
                      'M.925,.95V1.10'):
                glyph_path(d)
            glyph_path('M.67,.28L.75,.19')
            glyph_path('M.79,.145L.86,.065')
        glyph_path('M.5,1.45V1.56')
        nothing_element(doc, led(.5, 1.61, .026), X0, Y0, k, top, mid, bot)
    elif kind in ("2a_back", "3_back", "cmf2_back"):
        bright = doc.lin(0, .8, 0, 2.08, [(0, mix(top, "#ffffff", .15)), (1, bot)])
        edge = mix(mid, "#000000", .12)
        raw(doc, f'<g transform="translate({f(X0)} {f(Y0)}) scale({k})" stroke="{edge}" stroke-width=".012">')
        if kind == "2a_back":
            # A quiet S-shaped cable contour, without the blocky lower ornaments.
            contour = doc.lin(0, 1, 0, 2, [(0, mix(mid, top, .18)), (1, mix(mid, bot, .12))])
            raw(doc, f'<path d="M.09,1.04H.62C.99,1.04 .99,1.51 .62,1.51H.40L.23,1.70V2.03" fill="none" stroke="{contour}" stroke-width=".07" stroke-linecap="round" stroke-linejoin="round"/>')
        elif kind == "3_back":
            # Asymmetric upper tiles, centre spine and semicircular coil on the right.
            raw(doc, f'<path d="M.06,.12Q.06,.055 .14,.055H.25Q.34,.055 .34,.16Q.34,.25 .23,.31L.16,.335H.06Z" fill="{bright}"/>'
                     f'<path d="M.36,.665H.665V1.555H.36Z" fill="{bright}"/>'
                     f'<path d="M.67,.37C.84,.37 .97,.50 .97,.67C.97,.84 .84,.965 .67,.965Z" fill="{bright}"/>'
                     '<path d="M.06,.36H.955M.67,.05V.36M.36,.36V1.855M.665,.37V1.555" fill="none"/>'
                     f'<path d="{rounded_rect(.395, 1.89, .24, .22, .065)}" fill="{bright}"/>')
        else:
            # Visible accessory screws have metal rims and diagonal slots.
            for x, y in ((.36, .04), (.055, .60), (.955, .60), (.055, 1.95)):
                raw(doc, f'<path d="{circle(x, y, .036)}" fill="{bright}"/>'
                         f'<path d="M{x - .019},{y + .019}L{x + .019},{y - .019}" fill="none" stroke-width=".016"/>')
            raw(doc, f'<path d="{circle(.865, 2.00, .10)}" fill="none"/>'
                     '<path d="M.04,1.04H.96" fill="none"/>')
        raw(doc, '</g>')
    elif kind in ("3a_back", "3a_lite_back", "4a_pro_back"):
        bright = doc.lin(0, .9, 0, 2.05, [(0, mix(top, "#ffffff", .12)), (1, bot)])
        edge = mix(mid, "#000000", .12)
        raw(doc, f'<g transform="translate({f(X0)} {f(Y0)}) scale({k})" stroke="{edge}" stroke-width=".012">')
        if kind == "3a_back":
            # Two restrained wiring contours instead of filled ribbon shapes.
            contour = doc.lin(0, 1, 0, 2, [(0, mix(mid, top, .18)), (1, mix(mid, bot, .12))])
            raw(doc, f'<path d="M.12,1.08H.60Q.85,1.08 .85,1.32V1.57M.41,1.23V1.62Q.41,1.79 .62,1.79H.70" fill="none" stroke="{contour}" stroke-width=".055" stroke-linecap="round" stroke-linejoin="round"/>')
        elif kind == "3a_lite_back":
            panel_fill = doc.lin(0, .335, 0, 1.765, [(0, mix(mid, top, .18)), (1, mix(mid, bot, .25))])
            raw(doc, f'<path d="{rounded_rect(.27, .335, .68, 1.43, .11)}" fill="{panel_fill}"/>'
                     '<path d="M.535,.405V.375H.705V.405M.59,1.765V1.80H.79V1.765" fill="none" stroke-linecap="round"/>')
        else:
            # Plain metal lower back: only its recessed round Glyph button.
            raw(doc, f'<path d="{circle(.15, 2.00, .085)}" fill="{bright}"/>')
        raw(doc, '</g>')
    elif kind == "4a_back":
        # Only the two prominent lower-back contours; omit the small chassis details.
        main = "M.10,.99Q.10,.79 .25,.79H.65Q.91,.79 .91,1.02V1.91Q.91,2.02 .79,2.02H.56Q.39,2.02 .39,1.86V1.45Q.39,1.33 .26,1.26L.18,1.21Q.10,1.17 .10,1.06Z"
        bright = doc.lin(0, .8, 1, 1.9,
                         [(0, mix(top, "#ffffff", .18)), (1, mix(bot, "#000000", .08))])
        edge = mix(mid, "#000000", .12)
        raw(doc, f'<g transform="translate({f(X0)} {f(Y0)}) scale({k})">'
                 f'<path d="{main}" fill="{bright}" stroke="{edge}" stroke-width=".012"/>'
                 f'<path d="{rounded_rect(.54, 1.28, .23, .58, .05)}" fill="none" stroke="{edge}" stroke-width=".012"/>'
                 '</g>')
    elif kind == "arc":
        _, cx, cy, r, a0, a1 = e
        (x, y), R = P(cx, cy), r * k
        p0 = (x + R * math.cos(math.radians(a0)), y + R * math.sin(math.radians(a0)))
        p1 = (x + R * math.cos(math.radians(a1)), y + R * math.sin(math.radians(a1)))
        large = 1 if (a1 - a0) % 360 > 180 else 0
        stroke(f"M{f(p0[0])},{f(p0[1])}A{f(R)},{f(R)} 0 {large} 1 {f(p1[0])},{f(p1[1])}")
    elif kind == "strip":
        pts = [P(x, y) for x, y in e[1]]
        stroke("M" + "L".join(f"{f(x)},{f(y)}" for x, y in pts))
    elif kind == "dot":
        _, cx, cy, d, color = e
        x, y = P(cx, cy)
        if color:
            doc.add(circle(x, y, d * k / 2), color)
        else:
            doc.add(circle(x, y, d * k / 2 + .25), edge)
            doc.add(circle(x, y, d * k / 2), GLYPH_ON)
    elif kind == "led":
        _, cx, cy, d = e
        x, y = P(cx, cy)
        doc.add(circle(x, y, d * k / 2 + .3), edge)
        doc.add(circle(x, y, d * k / 2), GLYPH_ON)
    elif kind == "seg":
        _, x, y0, y1, n, red_last, width = e
        bw = width * k * 1.25
        (xa, ya), (_, yb) = P(x, y0), P(x, y1)
        doc.add(rounded_rect(xa - bw / 2 - .12, ya - .12, bw + .24, yb - ya + .24, bw / 2), edge)
        gap = .18
        sh = (yb - ya - gap * (n - 1)) / n
        for i in range(n):
            col = "#d71921" if red_last and i == n - 1 else GLYPH_ON
            doc.add(rounded_rect(xa - bw / 2, ya + i * (sh + gap), bw, sh, min(bw, sh) * .3), col)
    elif kind == "matrix":
        _, cx, cy, size, shape, n = e
        (x, y), S = P(cx, cy), size * k
        fill = doc.lin(x + S / 2, y - S / 2, x - S / 2, y + S / 2, [(0, "#3a3c41"), (1, "#0d0e10")])
        if shape == "circle":
            doc.add(circle(x, y, S / 2), fill)
        else:
            doc.add(rounded_rect(x - S / 2, y - S / 2, S, S, S * .2), fill)
        pitch = S / n
        heights = [0, 1, 0, 3, 1, 0, 4, 1, 2, 0, 1, 0, 0]
        for i in range(n):
            for j in range(n):
                px, py = x + (i - (n - 1) / 2) * pitch, y + (j - (n - 1) / 2) * pitch
                if shape == "circle" and math.hypot(px - x, py - y) > S / 2 - pitch * .32:
                    continue
                amplitude = heights[min(12, i * 13 // n)] * n / 13
                lit = abs(j - (n - 1) / 2) <= max(.5, amplitude)
                doc.add(circle(px, py, pitch * (.38 if lit else .32)), GLYPH_ON if lit else "#2c2e33")
    elif kind == "redsq":
        _, cx, cy, grey = e
        x, y = P(cx, cy)
        s_ = .05 * k
        doc.add(rounded_rect(x - s_ / 2, y - s_ / 2, s_, s_, s_ * .1), "#c9cacc" if grey else "#d71921")
    elif kind in ("screw", "camera_screw"):
        _, cx, cy = e
        x, y = P(cx, cy)
        doc.add(circle(x, y, .028 * k), mix(mid, "#000000", .45))
    elif kind == "dial":
        _, cx, cy, d = e
        x, y = P(cx, cy)
        doc.add(circle(x, y, d * k / 2 + .18), mix(mid, "#000000", .5))
        doc.add(circle(x, y, d * k / 2), doc.lin(x + d * k / 2, y, x - d * k / 2, y,
                                                 [(0, mix(mid, "#ffffff", .2)), (1, mix(mid, "#000000", .15))]))
    elif kind == "panel":
        y0 = Y0 + e[1] * k
        cid = doc.clip(rounded_rect(X0, Y0, k, 50, .09 * k))
        col = mix(mid, "#000000", .12) if lum(mid) > .4 else mix(mid, "#ffffff", .1)
        fill = doc.lin(54, y0, 54, Y0 + 50, [(0, col), (1, mix(bot, "#000000", .08))])
        doc.add(f"M{f(X0)},{f(y0)}H{f(X0 + k)}V{f(Y0 + 50)}H{f(X0)}Z", fill, cid)


# ---------------------------------------------------------------- brand logos (traced from user-supplied artwork)
LOGOS = json.load(open(os.path.join(ROOT, "brand_logos.json")))


def logo_path(name, cx, cy, width):
    lg = LOGOS[name]
    h = width / lg["aspect"]
    x0, y0 = cx - width / 2, cy - h / 2
    return re.sub(r"(-?[\d.]+),(-?[\d.]+)",
                  lambda m: f"{f(x0 + float(m[1]) * width)},{f(y0 + float(m[2]) * width)}", lg["d"])


def draw_logo(doc, spec, X0, Y0, BW, BH, mid, col=None):
    """spec: (brand, centre x in W, centre y in H, width in W[, rotation])."""
    name, cxw, cyh, ww = spec[:4]
    col = col or (mix(mid, "#000000", .2) if lum(mid) > .45 else mix(mid, "#ffffff", .28))
    cx, cy = X0 + cxw * BW, Y0 + cyh * BH
    rotation = f' transform="rotate({spec[4]} {f(cx)} {f(cy)})"' if len(spec) > 4 else ""
    raw(doc, f'<path d="{logo_path(name, cx, cy, ww * BW)}" fill="{col}" fill-rule="evenodd"{rotation}/>')


class GDoc(Doc):
    def svg(self):
        out = ['<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">',
               f"<defs>{''.join(self.defs)}</defs>"]
        for d, fill, clip in self.paths:
            if d is None:
                out.append(fill)
                continue
            c = f' clip-path="url(#{clip})"' if clip else ""
            out.append(f'<path d="{d}" fill="{fill}"{c}/>')
        out.append("</svg>\n")
        return "".join(out)


def build_phone(g, top, mid, bot):
    # Explicit finish samples override the generic tone-on-tone treatment.
    logo_color = g.get("logo_fills", {}).get(mid)
    top, mid, bot = pixel_palette(top, mid, bot)
    BH = 50.0
    BW = g.get("width", 30.0)  # Shared 30 x 50 slabs; closed book folds are narrower.
    k = BH * g["aspect"]  # Keep camera circles and back artwork uniformly scaled.
    X0, Y0 = 54 - BW / 2, 29.0
    doc = GDoc()
    if g.get("provisional"):
        raw(doc, g.get("provisional_note", '<title>OnePlus 16 - provisional prelaunch design</title><desc>Drawn from official OnePlus teaser images. Body proportions, colors and camera placement are estimates pending final specifications. Source: https://www.oneplus.com/cn/oneplus-16-launch</desc>'))
    body = rounded_rect(X0, Y0, BW, BH, g["r"] * BW)
    fill = body_fill(doc, Y0, Y0 + BH, top, mid, bot)
    if g.get("finish") == "nothing":
        fill = doc.lin(X0 + BW * .12, Y0 + 7, X0 + BW * .88, Y0 + BH - 3,
                       [(0, mix(top, "#ffffff", .14)), (.42, mid), (1, mix(bot, "#000000", .10 if lum(mid) > .8 else .20))])
    doc.add(body, fill)
    raw(doc, f'<g clip-path="url(#{doc.clip(body)})">')
    if g.get("back_panel"):
        x0, y0, x1, y1, r, kind = g["back_panel"]
        module(doc, X0 + x0 * BW, Y0 + y0 * k, X0 + x1 * BW, Y0 + y1 * k, r, kind, top, mid, bot)
    if g.get("logo"):
        logo_base = mid
        if g.get("back_panel", (None,))[-1] == "pixel_panel":
            logo_base = mix(mid, "#000000", .18) if lum(mid) > .75 else mix(mid, "#ffffff", .32)
        draw_logo(doc, g["logo"], X0, Y0, BW, BH, logo_base, logo_color)
    elements = g["el"]
    if g.get("wide_panel"):
        _, x0, y0, x1, y1, r, kind = elements[0]
        margin = x0 * BW
        r = min(r, (g["r"] * BW - margin) / min(BW - 2 * margin, y1 * k - margin))
        bottom_r = g.get("panel_bottom_r")
        if bottom_r is not None:
            r = (g["r"] * BW - margin) / min(BW - 2 * margin, y1 * k - margin)
            bottom_r *= BW
        module(doc, X0 + margin, Y0 + margin, X0 + BW - margin, Y0 + y1 * k, r, kind, top, mid, bot, bottom_r)
        elements = elements[1:]
    draw_elements(doc, elements, X0, Y0, k, top, mid, bot, BW, g.get("camera_width"))
    raw(doc, '</g>')
    return doc.svg()


# Official rear wordmark fits shared with the procedural tablet profiles.
# Values: reference center u/v, width fraction, reference orientation.
TABLET_WORDMARKS = {'galaxy_tab_s6': [0.5, 0.493, 0.195, 'portrait'],
 'galaxy_tab_s6_lite_2020': [0.5, 0.49, 0.2, 'portrait'],
 'galaxy_tab_s6_lite_2022': [0.5, 0.49, 0.2, 'portrait'],
 'galaxy_tab_s6_lite_2024': [0.5, 0.49, 0.2, 'portrait'],
 'galaxy_tab_s7_fe': [0.113, 0.084, 0.107, 'landscape'],
 'galaxy_tab_s8': [0.127, 0.095, 0.112, 'landscape'],
 'galaxy_tab_s7_plus': [0.126, 0.084, 0.105, 'landscape'],
 'galaxy_tab_s8_plus': [0.126, 0.084, 0.105, 'landscape'],
 'galaxy_tab_s8_ultra': [0.096, 0.081, 0.098, 'landscape'],
 'galaxy_tab_s9': [0.12, 0.1, 0.108, 'landscape'],
 'galaxy_tab_s9_plus': [0.117, 0.089, 0.103, 'landscape'],
 'galaxy_tab_s9_ultra': [0.105, 0.089, 0.096, 'landscape'],
 'galaxy_tab_s9_fe': [0.12, 0.094, 0.108, 'landscape'],
 'galaxy_tab_s9_fe_plus': [0.114, 0.085, 0.105, 'landscape'],
 'galaxy_tab_s10_fe': [0.119, 0.099, 0.108, 'landscape'],
 'galaxy_tab_s10_fe_plus': [0.119, 0.099, 0.108, 'landscape'],
 'galaxy_tab_s10_lite': [0.116, 0.1, 0.108, 'landscape'],
 'galaxy_tab_s11': [0.115, 0.099, 0.108, 'landscape'],
 'galaxy_tab_s11_ultra': [0.096, 0.081, 0.094, 'landscape'],
 'galaxy_tab_s12_plus': [0.105, 0.089, 0.104, 'landscape'],
 'galaxy_tab_s12_ultra': [0.096, 0.078, 0.094, 'landscape'],
 'galaxy_tab_a11': [0.5, 0.5, 0.22, 'portrait'],
 'galaxy_tab_a11_plus': [0.115, 0.098, 0.108, 'landscape'],
 'galaxy_tab_s10_plus': [0.117, 0.087, 0.103, 'landscape'],
 'galaxy_tab_s10_ultra': [0.105, 0.091, 0.096, 'landscape'],
 'galaxy_tab_s7': [0.129, 0.097, 0.112, 'landscape']}

for _model, _placement in TABLET_WORDMARKS.items():
    TABLETS[_model]["wm_position"] = _placement

def tablet_wordmark(spec, X0, Y0, BW, BH, color):
    u, v, width, reference = spec
    rotate = 0
    if reference == "portrait" and BW >= BH:
        u, v, width, rotate = 1-v, u, width*BH, 90
    elif reference == "landscape" and BW < BH:
        u, v, width, rotate = v, 1-u, width*BH, -90
    else:
        width *= BW
    cx, cy = X0+u*BW, Y0+v*BH
    transform = f' transform="rotate({rotate} {f(cx)} {f(cy)})"' if rotate else ""
    return f'<path d="{wordmark(cx, cy, width)}" fill="{color}"{transform}/>'


def build_tablet(g, top, mid, bot):
    top, mid, bot = pixel_palette(top, mid, bot)
    a = g["aspect"]
    if a >= 1:   # landscape, Pixel Tablet footprint (46 wide)
        BW, BH = 46.0, 46.0 / a
    else:        # portrait
        BH, BW = 46.0, 46.0 * a
    X0, Y0 = 54 - BW / 2, 54 - BH / 2
    k = BW
    doc = GDoc()
    body = rounded_rect(X0, Y0, BW, BH, min(BW, BH) * g["r"])
    doc.add(body, body_fill(doc, Y0, Y0 + BH, top, mid, bot))
    raw(doc, f'<g clip-path="url(#{doc.clip(body)})">')
    if g.get("logo"):
        draw_logo(doc, g["logo"], X0, Y0, BW, BH, mid)
    draw_elements(doc, g["el"], X0, Y0, k, top, mid, bot)
    if g.get("wm"):  # small SAMSUNG wordmark at the top-left of the back
        if g.get("wm_position"):
            raw(doc, tablet_wordmark(g["wm_position"], X0, Y0, BW, BH, logo_tone(mid)))
        else:
            doc.add(wordmark(X0 + .11 * k, Y0 + .06 * k, .12 * k), logo_tone(mid))
    raw(doc, '</g>')
    return doc.svg()


GLOW_BG_RY = ["#4285f4", "#34a853", "#fbbc05", "#ea4335"]
GLOW_RY_BG = ["#ea4335", "#fbbc05", "#34a853", "#4285f4"]

LAPTOPS = {
    "googlebook_acer_14": dict(
        aspect=312.0 / 222.9, r=.048,
        glowbar=(.1409, .0670, .1260, .0115, GLOW_BG_RY),
        logo=("acer", .855, .0670, .095),
        hinges=((.105, .195), (.805, .895)),
    ),
    "googlebook_asus_14": dict(
        aspect=310.9 / 212.8, r=.052,
        glowbar=(.5000, .1068, .1265, .0115, GLOW_RY_BG),
        logo=("asus", .500, .495, .155),
    ),
    "googlebook_dell_xps": dict(
        aspect=296.9 / 200.66, r=.042,
        glowbar=(.5000, .0520, .1320, .0115, GLOW_RY_BG),
        logo=("xps", .500, .495, .155),
    ),
    "googlebook_hp_14": dict(
        aspect=311.1 / 216.6, r=.050,
        glowbar=(.5004, .0644, .1261, .0115, GLOW_RY_BG),
        logo=("hp_slash", .500, .490, .115),
    ),
    "googlebook_lenovo_15": dict(
        aspect=341.0 / 236.0, r=.048,
        top_lip=(.355, .645, .022),
        glowbar=(.5000, .0420, .1730, .0115, GLOW_BG_RY),
        logo=("lenovo", .500, .485, .185),
    ),
    "googlebook_emulator": dict(
        aspect=312.0 / 218.0, r=.050,
        glowbar=(.5000, .0560, .1300, .0115, GLOW_BG_RY),
        logo=("google_g", .500, .495, .110),
    ),
}

# Open-clamshell (front view) details: logo shown on the display, as at boot.
# screen_logo: (logo name, width as a fraction of the display width)
LAPTOP_OPEN = {
    "googlebook_acer_14": dict(screen_logo=("acer", .30)),
    "googlebook_asus_14": dict(screen_logo=("asus", .34)),
    "googlebook_dell_xps": dict(screen_logo=("xps", .24)),
    "googlebook_hp_14": dict(screen_logo=("hp_slash", .17)),
    "googlebook_lenovo_15": dict(screen_logo=("lenovo", .38), no_scoop=True),
    "googlebook_emulator": dict(screen_logo=("google_color", .20)),
}

# Official 4-colour Google "G" (48 x 48 artboard)
GOOGLE_G_COLOR = (
    ("#ea4335", "M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"),
    ("#4285f4", "M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"),
    ("#fbbc05", "M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"),
    ("#34a853", "M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"),
)


def laptop_body_path(X0, Y0, BW, BH, R, top_lip=None):
    if not top_lip:
        return rounded_rect(X0, Y0, BW, BH, R)
    lx0_f, lx1_f, lh_f = top_lip
    lx0 = X0 + lx0_f * BW
    lx1 = X0 + lx1_f * BW
    lh = lh_f * BH
    lr = min(lh * .75, .8)
    return (
        f"M{f(X0 + R)},{f(Y0)}"
        f"L{f(lx0 - lr)},{f(Y0)}"
        f"Q{f(lx0)},{f(Y0)} {f(lx0 + lr * .5)},{f(Y0 - lh * .5)}"
        f"Q{f(lx0 + lr)},{f(Y0 - lh)} {f(lx0 + 2 * lr)},{f(Y0 - lh)}"
        f"L{f(lx1 - 2 * lr)},{f(Y0 - lh)}"
        f"Q{f(lx1 - lr)},{f(Y0 - lh)} {f(lx1 - lr * .5)},{f(Y0 - lh * .5)}"
        f"Q{f(lx1)},{f(Y0)} {f(lx1 + lr)},{f(Y0)}"
        f"L{f(X0 + BW - R)},{f(Y0)}"
        f"A{f(R)},{f(R)} 0 0 1 {f(X0 + BW)},{f(Y0 + R)}"
        f"L{f(X0 + BW)},{f(Y0 + BH - R)}"
        f"A{f(R)},{f(R)} 0 0 1 {f(X0 + BW - R)},{f(Y0 + BH)}"
        f"L{f(X0 + R)},{f(Y0 + BH)}"
        f"A{f(R)},{f(R)} 0 0 1 {f(X0)},{f(Y0 + BH - R)}"
        f"L{f(X0)},{f(Y0 + R)}"
        f"A{f(R)},{f(R)} 0 0 1 {f(X0 + R)},{f(Y0)}Z"
    )


def build_laptop(g, top, mid, bot):
    """Clean, smooth laptop icon matching phone/tablet icon detail level and visual weight."""
    top, mid, bot = pixel_palette(top, mid, bot)
    a = g["aspect"]
    BW, BH = 48.0, 48.0 / a
    X0, Y0 = 54 - BW / 2, 54 - BH / 2
    R = min(BW, BH) * g["r"]
    doc = GDoc()
    body = laptop_body_path(X0, Y0, BW, BH, R, g.get("top_lip"))
    doc.add(body, body_fill(doc, Y0, Y0 + BH, top, mid, bot))
    raw(doc, f'<g clip-path="url(#{doc.clip(body)})">')
    if g.get("glowbar"):
        cx_f, cy_f, gw_f, gh_f, cols = g["glowbar"]
        gw, gh = gw_f * BW, gh_f * BW
        gx0 = X0 + cx_f * BW - gw / 2
        gy0 = Y0 + cy_f * BH - gh / 2
        g_fill = doc.lin(gx0, gy0, gx0 + gw, gy0, [
            (0, cols[0]), (.33, cols[1]), (.67, cols[2]), (1, cols[3])
        ])
        doc.add(rounded_rect(gx0, gy0, gw, gh, gh / 2), g_fill)
    if g.get("logo"):
        draw_logo(doc, g["logo"], X0, Y0, BW, BH, mid)
    if g.get("hinges"):
        h_col = mix(bot, "#000000", .28) if lum(mid) > .4 else mix(bot, "#ffffff", .22)
        hh = .028 * BH
        for hx0_f, hx1_f in g["hinges"]:
            hx0 = X0 + hx0_f * BW
            hw = (hx1_f - hx0_f) * BW
            doc.add(rounded_rect(hx0, Y0 + BH - hh, hw, hh + .4, .3), h_col)
    raw(doc, '</g>')
    return doc.svg()


def main():
    n = 0
    for model, colors in COLORS.items():
        brand = model.split("_")[0]
        if model in PHONES:
            kind, build, g = "phones", build_phone, PHONES[model]
        elif model in LAPTOPS:
            kind, build, g = "laptops", build_laptop, LAPTOPS[model]
        else:
            kind, build, g = "tablets", build_tablet, TABLETS[model]
        if brand == "galaxy":
            folder = os.path.join(ROOT, "device_icons_svg", "samsung", "tablets")
        elif model in LAPTOPS:
            folder = os.path.join(ROOT, "device_icons_svg", "pixel", "laptops")
        else:
            folder = os.path.join(ROOT, "device_icons_svg", brand, kind)
        os.makedirs(folder, exist_ok=True)
        for color, (top, mid, bot) in colors.items():
            with open(os.path.join(folder, f"ic_{model}_{color}_icon.svg"), "w", encoding="utf-8") as fh:
                fh.write(build(g, top, mid, bot))
            n += 1
    print("wrote", n)


if __name__ == "__main__":
    main()

