"""Generate procedural 3D models, profiles, and 2D vector/raster icons for peripheral devices."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import math
import re
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

import numpy as np
from PIL import Image
import resvg_py
import shapely
from shapely import affinity
import shapely.geometry as sg
import trimesh
from trimesh.visual import TextureVisuals
from trimesh.visual.material import PBRMaterial

ROOT = Path(__file__).resolve().parents[1]
DEVICES = ROOT / "assets" / "devices"
sys.path.insert(0, str(DEVICES))
import optics  # noqa: E402
import arduino_brand as brand  # noqa: E402


def pbr(name: str, rgb: tuple[float, float, float], rough: float = 0.4, metal: float = 0.0) -> PBRMaterial:
    return PBRMaterial(
        name=name,
        baseColorFactor=[int(round(c * 255)) for c in (*rgb, 1.0)],
        roughnessFactor=rough,
        metallicFactor=metal,
    )


def styled(mesh: trimesh.Trimesh, material: PBRMaterial) -> trimesh.Trimesh:
    mesh.visual = TextureVisuals(material=material)
    return mesh


def extrude_poly(poly: sg.Polygon, height: float) -> trimesh.Trimesh:
    """Extrude a 2D Shapely polygon (with optional interior holes) along +Z from 0 to height."""
    tris = shapely.constrained_delaunay_triangles(poly)
    verts = []
    faces = []
    vert_map: dict[tuple[float, float, float], int] = {}

    def v_idx(x: float, y: float, z: float) -> int:
        key = (round(x, 5), round(y, 5), round(z, 5))
        if key not in vert_map:
            vert_map[key] = len(verts)
            verts.append([x, y, z])
        return vert_map[key]

    for tri in tris.geoms:
        coords = list(tri.exterior.coords)[:3]
        if len(coords) < 3:
            continue
        (x0, y0), (x1, y1), (x2, y2) = coords
        cross = (x1 - x0) * (y2 - y0) - (y1 - y0) * (x2 - x0)
        if abs(cross) < 1e-9:
            continue
        if cross < 0:
            (x1, y1), (x2, y2) = (x2, y2), (x1, y1)
        # Top face (+Z normal)
        t0, t1, t2 = v_idx(x0, y0, height), v_idx(x1, y1, height), v_idx(x2, y2, height)
        faces.append([t0, t1, t2])
        # Bottom face (-Z normal)
        b0, b1, b2 = v_idx(x0, y0, 0.0), v_idx(x1, y1, 0.0), v_idx(x2, y2, 0.0)
        faces.append([b0, b2, b1])

    def add_ring_walls(ring_coords: list[tuple[float, float]], ccw: bool) -> None:
        pts = list(ring_coords)
        if pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(pts) < 3:
            return
        area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts)))
        if (area > 0) != ccw:
            pts = list(reversed(pts))
        n = len(pts)
        for i in range(n):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % n]
            b0, b1 = v_idx(x0, y0, 0.0), v_idx(x1, y1, 0.0)
            t0, t1 = v_idx(x0, y0, height), v_idx(x1, y1, height)
            faces.append([b0, b1, t1])
            faces.append([b0, t1, t0])

    add_ring_walls(list(poly.exterior.coords), ccw=True)
    for interior in poly.interiors:
        add_ring_walls(list(interior.coords), ccw=False)

    return trimesh.Trimesh(vertices=np.array(verts, dtype=np.float64), faces=np.array(faces, dtype=np.int64), process=True)


def make_box(
    sx: float,
    sy: float,
    sz: float,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
) -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=(sx, sy, sz))
    box.apply_translation((cx, cy, cz))
    return box


def make_rounded_prism(
    width: float,
    height: float,
    depth: float,
    radius: float,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
) -> trimesh.Trimesh:
    r = max(0.05, min(radius, min(width, height) * 0.48))
    poly = sg.box(-width / 2 + r, -height / 2 + r, width / 2 - r, height / 2 - r).buffer(r, quad_segs=12)
    mesh = extrude_poly(poly, depth)
    mesh.apply_translation((cx, cy, cz - depth / 2.0))
    return mesh


def make_cylinder_z(
    radius: float,
    length: float,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
    sections: int = 28,
) -> trimesh.Trimesh:
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    cyl.apply_translation((cx, cy, cz))
    return cyl


def make_cylinder_x(
    radius: float,
    length: float,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
    sections: int = 28,
) -> trimesh.Trimesh:
    cyl = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    rot = trimesh.transformations.rotation_matrix(math.pi / 2.0, [0.0, 1.0, 0.0])
    cyl.apply_transform(rot)
    cyl.apply_translation((cx, cy, cz))
    return cyl


def make_annulus_z(
    r_outer: float,
    r_inner: float,
    height: float,
    cx: float = 0.0,
    cy: float = 0.0,
    cz: float = 0.0,
    quad_segs: int = 20,
) -> trimesh.Trimesh:
    outer = sg.Point(cx, cy).buffer(r_outer, quad_segs=quad_segs)
    inner = sg.Point(cx, cy).buffer(r_inner, quad_segs=quad_segs)
    ring = outer.difference(inner)
    mesh = extrude_poly(ring, height)
    mesh.apply_translation((0.0, 0.0, cz - height / 2.0))
    return mesh


def uno_board_coords_2d(cx_off: float = -34.3, cy_off: float = -26.7) -> list[tuple[float, float]]:
    """Authentic Arduino Uno R3 stepped PCB outline in millimeters (68.6 x 53.4 mm)."""
    pts_mm = [
        (0.0, 0.0),
        (66.04, 0.0),
        (66.04, 2.54),
        (68.58, 5.08),
        (68.58, 37.85),
        (66.04, 40.39),
        (66.04, 52.07),
        (64.77, 53.34),
        (0.0, 53.34),
    ]
    return [(x + cx_off, y + cy_off) for x, y in pts_mm]


def uno_mounting_holes_2d(cx_off: float = -34.3, cy_off: float = -26.7) -> list[tuple[float, float]]:
    """Official Arduino Uno R3 4 mounting holes in millimeters."""
    holes_mm = [
        (13.97, 2.54),
        (15.24, 50.80),
        (66.04, 7.62),
        (66.04, 35.56),
    ]
    return [(x + cx_off, y + cy_off) for x, y in holes_mm]


def extrude_x(poly: sg.Polygon, x0: float, x1: float) -> trimesh.Trimesh:
    """Extrude a profile drawn in (y, z) along +X from x0 to x1."""
    mesh = extrude_poly(poly, x1 - x0)
    v = mesh.vertices.copy()
    mesh.vertices = np.column_stack([v[:, 2] + x0, v[:, 0], v[:, 1]])
    return mesh


def rounded_rect(x0: float, y0: float, x1: float, y1: float, r_bl: float, r_br: float, r_tr: float, r_tl: float) -> sg.Polygon:
    """Axis-aligned rectangle with an individual radius per corner (bottom-left, bottom-right, top-right, top-left)."""
    poly = sg.box(x0, y0, x1, y1)
    for (cx, cy, sx, sy, r) in ((x0, y0, 1, 1, r_bl), (x1, y0, -1, 1, r_br), (x1, y1, -1, -1, r_tr), (x0, y1, 1, -1, r_tl)):
        if r <= 0:
            continue
        corner = sg.box(min(cx, cx + sx * r), min(cy, cy + sy * r), max(cx, cx + sx * r), max(cy, cy + sy * r))
        arc = sg.Point(cx + sx * r, cy + sy * r).buffer(r, quad_segs=10)
        poly = poly.difference(corner).union(corner.intersection(arc))
    return poly


def make_cone_z(radius: float, height: float, cx: float, cy: float, z0: float, sections: int = 4, spin: float = 45.0) -> trimesh.Trimesh:
    cone = trimesh.creation.cone(radius=radius, height=height, sections=sections)
    cone.apply_transform(trimesh.transformations.rotation_matrix(math.radians(spin), [0, 0, 1]))
    cone.apply_translation((cx, cy, z0))
    return cone


# Board-frame layout in millimetres (origin lower-left, y up), shared by the 3D model and the icon.
HEADERS = {
    "hdr_d_hi": (18.9, 10, 50.80),
    "hdr_d_lo": (46.4, 8, 50.80),
    "hdr_pwr": (28.4, 8, 2.54),
    "hdr_an": (51.4, 6, 2.54),
}
RESET_POS = (6.6, 49.6)
ICSP2_POS = (19.6, 45.5)
ICSP_POS = (65.8, 28.6)
USB_X = (-6.5, 9.5)
USB_CY = 38.9
U16_POS = (20.2, 35.2)
LEDS = [("L", 28.1, 41.9), ("TX", 28.1, 37.3), ("RX", 28.1, 34.7), ("ON", 60.3, 37.2)]
REG_POS = (7.8, 17.7)
DC_X = (-1.8, 11.8)
DC_CY = 7.8
CAPS = [(18.7, 9.3), (26.3, 9.3)]
DIP_POS = (47.0, 19.2)
BOARD_OFFSET = (-34.3, -26.7)  # board mm -> model mm (model is centred on the PCB)
ICON_SCALE = 1.22  # icon units per board mm
ICON_ORIGIN = (54.0 - 31.04 * ICON_SCALE, 54.0 + 26.67 * ICON_SCALE)  # icon position of board (0, 0)


def build_arduino_uno_r3_scene() -> tuple[trimesh.Scene, dict[str, PBRMaterial]]:
    cx_off = -34.3
    cy_off = -26.7
    pcb_thickness = 1.6
    z_top = pcb_thickness / 2.0
    z_bot = -pcb_thickness / 2.0

    mats = {
        "pcb": pbr("Arduino PCB", (0.0, 0.506, 0.518), rough=0.34, metal=0.05),
        "silkscreen": pbr("PCB silkscreen", (0.94, 0.96, 0.96), rough=0.42, metal=0.0),
        "metal": pbr("Connector shield", (0.74, 0.77, 0.80), rough=0.42, metal=0.7),
        "metal_dark": pbr("Connector sleeve", (0.45, 0.47, 0.50), rough=0.55, metal=0.6),
        "pin_silver": pbr("Tinned IC leads", (0.78, 0.80, 0.83), rough=0.38, metal=0.8),
        "gold": pbr("USB gold contacts", (0.86, 0.69, 0.25), rough=0.24, metal=0.88),
        "plastic": pbr("Header & jack housing", (0.11, 0.12, 0.14), rough=0.42, metal=0.04),
        "ic_body": pbr("IC package", (0.15, 0.16, 0.18), rough=0.48, metal=0.05),
        "cavity": pbr("Port & header cavity", (0.03, 0.035, 0.04), rough=0.75, metal=0.0),
        "usb_tongue": pbr("USB-B insulator", (0.86, 0.84, 0.78), rough=0.6, metal=0.0),
        "switch": pbr("Reset switch body", (0.86, 0.86, 0.84), rough=0.4, metal=0.1),
        "reset_cap": pbr("Reset button actuator", (0.66, 0.16, 0.14), rough=0.36, metal=0.05),
        "led_green": pbr("Power ON LED", (0.62, 0.95, 0.70), rough=0.22, metal=0.0),
        "led_amber": pbr("Status L LED", (0.98, 0.86, 0.45), rough=0.22, metal=0.0),
        "led_white": pbr("Status TX/RX LED", (0.93, 0.95, 0.96), rough=0.22, metal=0.0),
        "smd_tan": pbr("LED end pads", (0.78, 0.70, 0.50), rough=0.5, metal=0.0),
    }

    groups: dict[str, list[trimesh.Trimesh]] = {k: [] for k in mats}
    footprints: list[tuple[str, sg.base.BaseGeometry]] = []

    def X(v: float) -> float:
        return v + cx_off

    def Y(v: float) -> float:
        return v + cy_off

    def reg(name: str, geom: sg.base.BaseGeometry) -> None:
        footprints.append((name, geom))

    def reg_box(name: str, x0: float, y0: float, x1: float, y1: float) -> None:
        reg(name, sg.box(x0, y0, x1, y1))

    # 1. PCB with corner fillet and four mounting holes
    board_poly = sg.Polygon(uno_board_coords_2d(cx_off, cy_off)).buffer(-0.45, join_style=2).buffer(0.45, quad_segs=10)
    holes = uno_mounting_holes_2d(cx_off, cy_off)
    for hx, hy in holes:
        board_poly = board_poly.difference(sg.Point(hx, hy).buffer(1.6, quad_segs=20))
        reg("hole", sg.Point(hx, hy).buffer(2.3))
    pcb_mesh = extrude_poly(board_poly, pcb_thickness)
    pcb_mesh.apply_translation((0.0, 0.0, -pcb_thickness / 2.0))
    groups["pcb"].append(pcb_mesh)
    for hx, hy in holes:
        groups["pin_silver"].append(make_annulus_z(2.3, 1.62, 0.08, hx, hy, z_top + 0.04))
        groups["pin_silver"].append(make_annulus_z(2.3, 1.62, 0.08, hx, hy, z_bot - 0.04))
        groups["pin_silver"].append(make_annulus_z(1.72, 1.58, pcb_thickness + 0.08, hx, hy, 0.0))

    # 2. Silkscreen: official infinity mark and UNO with its dotted outline (no other markings)
    def add_silk(geom: sg.base.BaseGeometry) -> None:
        for g in geom.geoms if hasattr(geom, "geoms") else [geom]:
            if g.is_empty or g.geom_type != "Polygon" or g.area < 0.005:
                continue
            mesh = extrude_poly(g, 0.05)
            mesh.apply_translation((0.0, 0.0, z_top))
            groups["silkscreen"].append(mesh)

    shift = lambda g: affinity.translate(g, cx_off, cy_off)  # noqa: E731
    logo = brand.logo_mm()
    uno_text = brand.uno_letters_mm()
    uno_dots = brand.uno_dots_mm()
    for g in (logo, uno_text, uno_dots):
        add_silk(shift(g))
    reg("logo", sg.box(*logo.bounds))
    reg("uno", sg.box(*uno_dots.bounds))

    # 3. USB Type-B receptacle (matched to Uno photos): 12.0 x 10.9 mm stamped shell with rounded bends,
    #    rear flap with rounded top/side bends, cream insulator face with the B-shaped socket and tongue,
    #    square latch windows near the back of each side and shell legs down through the board.
    usb_x0, usb_x1 = X(USB_X[0]), X(USB_X[1])
    usb_cy = Y(USB_CY)
    usb_h = 10.9
    half = 6.0
    wall = 0.3
    bend = 1.0

    def shell_profile(shrink: float = 0.0) -> sg.Polygon:
        return rounded_rect(usb_cy - half + shrink, z_top, usb_cy + half - shrink, z_top + usb_h - shrink, 0.45, 0.45, bend, bend)

    outer = shell_profile()
    inner = outer.buffer(-wall, join_style=2)
    body_x1 = usb_x1 - bend
    groups["metal"].append(extrude_x(outer.difference(inner), usb_x0, body_x1))
    slices = 8
    for k in range(slices):
        xa = body_x1 + bend * k / slices
        xb = body_x1 + bend * (k + 1) / slices
        dx = (xa + xb) / 2 - body_x1
        groups["metal"].append(extrude_x(shell_profile(bend - math.sqrt(max(bend * bend - dx * dx, 0.0))), xa, xb))
    cav_z = z_top + usb_h / 2.0
    socket_w, socket_h, chamfer = 8.45, 7.78, 1.3
    sy0, sy1 = usb_cy - socket_w / 2, usb_cy + socket_w / 2
    sz0, sz1 = cav_z - socket_h / 2, cav_z + socket_h / 2
    socket = sg.Polygon([(sy0, sz0), (sy1, sz0), (sy1, sz1 - chamfer), (sy1 - chamfer, sz1), (sy0 + chamfer, sz1), (sy0, sz1 - chamfer)])
    depth = 9.0
    groups["usb_tongue"].append(extrude_x(inner.difference(socket), usb_x0 + 0.15, usb_x0 + depth))
    groups["usb_tongue"].append(extrude_x(inner.buffer(-0.001), usb_x0 + depth, body_x1))
    groups["cavity"].append(extrude_x(socket.difference(socket.buffer(-0.08, join_style=2)), usb_x0 + 0.15, usb_x0 + depth))
    tongue = sg.box(usb_cy - 2.8, cav_z - 1.2, usb_cy + 2.8, cav_z + 1.4)
    groups["usb_tongue"].append(extrude_x(tongue, usb_x0 + 1.2, usb_x0 + depth))
    for k in (-1.5, -0.5, 0.5, 1.5):
        groups["gold"].append(make_box(6.0, 0.6, 0.08, usb_x0 + 4.6, usb_cy + k * 1.25, cav_z + 1.44))
        groups["gold"].append(make_box(6.0, 0.6, 0.08, usb_x0 + 4.6, usb_cy + k * 1.25, cav_z - 1.24))
    for side in (-1, 1):
        groups["cavity"].append(make_box(1.3, 0.06, 1.3, body_x1 - 1.6, usb_cy + side * (half + 0.03), z_top + usb_h * 0.62))
        for lx in (X(1.5), body_x1 - 1.2):
            groups["metal"].append(make_box(1.8, wall, pcb_thickness + 1.6, lx, usb_cy + side * (half - wall / 2), z_top - (pcb_thickness + 1.6) / 2))
    for dy in (-3.0, -1.0, 1.0, 3.0):
        groups["pin_silver"].append(make_box(0.5, 0.5, pcb_thickness + 1.4, body_x1 - 2.0, usb_cy + dy * 0.83, z_top - (pcb_thickness + 1.4) / 2))
    reg_box("usb", usb_x0, usb_cy - half, usb_x1, usb_cy + half)

    # 4. DC barrel jack (matched to Uno photos): squared front block with the bore, lower rear body with a
    #    rounded (half-cylinder) top and a flat sleeve lug on the board-edge side.
    dc_len = 13.4
    dc_x0 = X(DC_X[0])
    dc_x1 = dc_x0 + dc_len
    dc_cy = Y(DC_CY)
    dc_w = 9.0
    front_len = 3.6
    bore_z = z_top + 5.6
    front_p = sg.box(dc_cy - dc_w / 2 + 0.5, z_top + 0.5, dc_cy + dc_w / 2 - 0.5, z_top + 11.0 - 0.5).buffer(0.5, quad_segs=6)
    rear_p = shapely.unary_union([
        sg.box(dc_cy - dc_w / 2, z_top, dc_cy + dc_w / 2, z_top + 6.0),
        sg.Point(dc_cy, z_top + 6.0).buffer(dc_w / 2, quad_segs=24).intersection(sg.box(dc_cy - dc_w, z_top + 6.0, dc_cy + dc_w, z_top + 20)),
    ])
    bore = sg.Point(dc_cy, bore_z).buffer(3.2, quad_segs=24)
    groups["plastic"].append(extrude_x(front_p.difference(bore), dc_x0, dc_x0 + front_len))
    groups["plastic"].append(extrude_x(rear_p.difference(bore), dc_x0 + front_len, dc_x0 + 9.5))
    groups["plastic"].append(extrude_x(rear_p, dc_x0 + 9.5, dc_x1))
    groups["cavity"].append(extrude_x(bore.buffer(0.001), dc_x0 + 9.45, dc_x0 + 9.5))
    groups["metal_dark"].append(make_cylinder_x(1.0, 7.0, dc_x0 + 6.0, dc_cy, bore_z, sections=24))
    groups["cavity"].append(make_box(5.5, 0.6, 0.5, dc_x0 + 6.3, dc_cy, bore_z - 3.0))
    # sleeve lug: flat plate against the board-edge side wall, legs into the board
    lug_side = sg.box(dc_x0 + 7.0, z_bot - 1.4, dc_x0 + 10.4, z_top + 4.6).buffer(-0.4).buffer(0.4, quad_segs=4)
    side_mesh = extrude_poly(lug_side, 0.35)
    v = side_mesh.vertices.copy()
    side_mesh.vertices = np.column_stack([v[:, 0], dc_cy - dc_w / 2 - 0.37 + v[:, 2], v[:, 1]])
    side_mesh.invert()  # swapping y/z mirrors the extrusion; restore outward normals
    groups["pin_silver"].append(side_mesh)
    reg_box("dc", dc_x0, dc_cy - dc_w / 2 - 0.4, dc_x1, dc_cy + dc_w / 2)

    # 5. Female headers: solid base, perforated body, contacts at the bottom of each socket
    header_h = 8.5
    base_h = 1.4

    def add_female_header(first_pin: float, count: int, y_mm: float, name: str) -> None:
        pin_xs_mm = [first_pin + i * 2.54 for i in range(count)]
        x_min, x_max = X(min(pin_xs_mm)) - 1.27, X(max(pin_xs_mm)) + 1.27
        hy = Y(y_mm)
        body = sg.box(x_min, hy - 1.27, x_max, hy + 1.27)
        sockets = [sg.box(X(p) - 0.55, hy - 0.55, X(p) + 0.55, hy + 0.55) for p in pin_xs_mm]
        perforated = body.difference(shapely.unary_union(sockets))
        base = make_box(x_max - x_min, 2.54, base_h, (x_min + x_max) / 2, hy, z_top + base_h / 2)
        upper = extrude_poly(perforated, header_h - base_h)
        upper.apply_translation((0.0, 0.0, z_top + base_h))
        groups["plastic"].extend([base, upper])
        for p in pin_xs_mm:
            groups["pin_silver"].append(make_box(0.5, 0.8, 2.6, X(p), hy, z_top + base_h + 1.3))
            groups["pin_silver"].append(make_box(0.6, 0.6, 1.5, X(p), hy, z_bot - 0.75))
        reg_box(name, x_min, hy - 1.27, x_max, hy + 1.27)

    for name, (first, count, y_mm) in HEADERS.items():
        add_female_header(first, count, y_mm, name)

    # 6. ATmega328P in a DIP-28 socket
    dip_cx, dip_cy = X(DIP_POS[0]), Y(DIP_POS[1])
    socket_len = 36.6
    groups["plastic"].append(make_box(socket_len, 9.8, 2.6, dip_cx, dip_cy, z_top + 1.3))
    reg_box("dip", dip_cx - socket_len / 2, dip_cy - 4.9, dip_cx + socket_len / 2, dip_cy + 4.9)
    body_len = 34.8
    groups["ic_body"].append(make_box(body_len, 7.4, 3.4, dip_cx, dip_cy, z_top + 2.6 + 1.7))
    groups["cavity"].append(make_cylinder_z(1.15, 0.3, dip_cx - body_len / 2 + 0.05, dip_cy, z_top + 2.6 + 3.4, sections=24))
    for i in range(14):
        lx = dip_cx + (i - 6.5) * 2.54
        for sign in (-1.0, 1.0):
            groups["pin_silver"].append(make_box(0.5, 0.9, 0.3, lx, dip_cy + sign * 4.15, z_top + 2.6 + 1.5))
            groups["pin_silver"].append(make_box(0.5, 0.3, 1.9, lx, dip_cy + sign * 4.5, z_top + 2.6 + 0.65))
            groups["pin_silver"].append(make_box(0.5, 0.5, 1.4, lx, dip_cy + sign * 3.81, z_bot - 0.7))

    # 7. Two 2x3 ICSP headers with tapered gold pins
    def add_icsp_header(cx_mm: float, cy_mm: float, vertical: bool, name: str) -> None:
        cols, rows = (2, 3) if vertical else (3, 2)
        bw, bd = cols * 2.54, rows * 2.54
        hx, hy = X(cx_mm), Y(cy_mm)
        groups["plastic"].append(make_box(bw, bd, 2.5, hx, hy, z_top + 1.25))
        for r in range(rows):
            for c in range(cols):
                px = hx + (c - (cols - 1) / 2.0) * 2.54
                py = hy + (r - (rows - 1) / 2.0) * 2.54
                groups["pin_silver"].append(make_box(0.64, 0.64, 5.0, px, py, z_top + 3.0))
                groups["pin_silver"].append(make_cone_z(0.46, 0.8, px, py, z_top + 5.5))
                groups["pin_silver"].append(make_box(0.6, 0.6, 1.2, px, py, z_bot - 0.6))
        reg_box(name, hx - bw / 2, hy - bd / 2, hx + bw / 2, hy + bd / 2)

    add_icsp_header(*ICSP_POS, True, "icsp_r")
    add_icsp_header(*ICSP2_POS, False, "icsp_u")

    # 8. Reset tactile switch
    rst_cx, rst_cy = X(RESET_POS[0]), Y(RESET_POS[1])
    groups["switch"].append(make_box(8.0, 5.8, 2.6, rst_cx, rst_cy, z_top + 1.3))
    for sy in (-1.9, 0.0, 1.9):
        groups["pin_silver"].append(make_box(1.0, 1.0, 0.4, rst_cx - 4.5, rst_cy + sy, z_top + 0.2))
    groups["reset_cap"].append(make_cylinder_z(1.8, 1.6, rst_cx, rst_cy, z_top + 2.6 + 0.8, sections=32))
    reg_box("reset", rst_cx - 5.1, rst_cy - 2.9, rst_cx + 4.0, rst_cy + 2.9)

    # 9. ATmega16U2 and SOT-223 regulator as plain black packages
    u2_cx, u2_cy = X(U16_POS[0]), Y(U16_POS[1])
    groups["ic_body"].append(make_box(5.2, 5.2, 0.95, u2_cx, u2_cy, z_top + 0.475))
    reg_box("u2", u2_cx - 2.6, u2_cy - 2.6, u2_cx + 2.6, u2_cy + 2.6)
    reg_cx, reg_cy = X(REG_POS[0]), Y(REG_POS[1])
    groups["ic_body"].append(make_box(3.7, 6.6, 1.5, reg_cx, reg_cy, z_top + 0.75))
    reg_box("regulator", reg_cx - 1.9, reg_cy - 3.3, reg_cx + 1.9, reg_cy + 3.3)

    # 10. SMD electrolytic capacitors: light can with a black polarity segment
    def add_smd_cap(cap_x: float, cap_y: float, name: str) -> None:
        ccx, ccy = X(cap_x), Y(cap_y)
        base = sg.Polygon([(ccx - 3.3, ccy - 3.3), (ccx + 3.3, ccy - 3.3), (ccx + 3.3, ccy + 3.3), (ccx - 2.5, ccy + 3.3), (ccx - 3.3, ccy + 2.5)])
        base_mesh = extrude_poly(base, 0.9)
        base_mesh.apply_translation((0.0, 0.0, z_top))
        groups["plastic"].append(base_mesh)
        can_h = 5.0
        groups["metal"].append(make_cylinder_z(3.1, can_h, ccx, ccy, z_top + 0.9 + can_h / 2, sections=48))
        groups["usb_tongue"].append(make_cylinder_z(2.7, 0.25, ccx, ccy, z_top + 0.9 + can_h + 0.1, sections=48))
        stripe = sg.Point(ccx, ccy).buffer(2.7, quad_segs=24).intersection(sg.box(ccx - 3.0, ccy - 3.0, ccx + 3.0, ccy - 1.7))
        stripe_mesh = extrude_poly(stripe, 0.05)
        stripe_mesh.apply_translation((0.0, 0.0, z_top + 0.9 + can_h + 0.22))
        groups["ic_body"].append(stripe_mesh)
        reg_box(name, ccx - 3.3, ccy - 3.3, ccx + 3.3, ccy + 3.3)

    for idx, (cap_x, cap_y) in enumerate(CAPS):
        add_smd_cap(cap_x, cap_y, f"cap{idx + 1}")

    # 11. Status LEDs: pale package with tan end pads
    led_mat = {"L": "led_amber", "TX": "led_white", "RX": "led_white", "ON": "led_green"}
    for label, lx_mm, ly_mm in LEDS:
        lx, ly = X(lx_mm), Y(ly_mm)
        groups["smd_tan"].append(make_box(2.4, 1.3, 0.5, lx, ly, z_top + 0.25))
        groups[led_mat[label]].append(make_box(1.5, 1.3, 0.6, lx, ly, z_top + 0.3))
        reg_box("led", lx - 1.3, ly - 0.8, lx + 1.3, ly + 0.8)

    # Self-check: report any footprint overlaps so collisions are visible when regenerating.
    allowed = {("logo", "uno")}
    problems = []
    for i, (na, ga) in enumerate(footprints):
        for nb, gb in footprints[i + 1:]:
            if (na, nb) in allowed or (nb, na) in allowed:
                continue
            area = ga.intersection(gb).area
            if area > 0.05:
                problems.append(f"{na} x {nb}: {area:.2f} mm2")
    if problems:
        print("Footprint overlaps:", *problems, sep="\n  ")

    rot_x = trimesh.transformations.rotation_matrix(-math.pi / 2.0, [1.0, 0.0, 0.0])  # board lies flat, top face up
    scene = trimesh.Scene()
    for key, mesh_list in groups.items():
        if not mesh_list:
            continue
        combined = trimesh.util.concatenate(mesh_list)
        combined.apply_transform(rot_x)
        combined.apply_scale(0.001)  # glTF units are metres; the model is authored in mm
        scene.add_geometry(styled(combined, mats[key]), node_name=key, geom_name=key)

    return scene, mats


def _poly_path(geom: sg.base.BaseGeometry, tx, ty) -> str:
    polys = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for poly in polys:
        if poly.geom_type != "Polygon":
            continue
        for ring in [poly.exterior, *poly.interiors]:
            pts = list(ring.coords)[:-1]
            out.append("M" + "L".join(f"{tx(x):.2f},{ty(y):.2f}" for x, y in pts) + "Z")
    return "".join(out)


def generate_arduino_svg(monochrome: bool = False) -> str:
    """Top-down Uno icon in the same gradient style as the phone icons, without text."""
    scale = ICON_SCALE
    ox, oy = ICON_ORIGIN

    def tx(x: float) -> float:
        return ox + x * scale

    def ty(y: float) -> float:
        return oy - y * scale

    def rbox(x0: float, y0: float, x1: float, y1: float, r: float = 0.5):
        return sg.box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, quad_segs=4)

    board = sg.Polygon(uno_board_coords_2d(0.0, 0.0)).buffer(-1.8, join_style=1).buffer(1.8, quad_segs=8)
    usb = rbox(USB_X[0], USB_CY - 5.9, USB_X[1], USB_CY + 5.9, 0.6)
    dc = rbox(DC_X[0], DC_CY - 4.4, DC_X[1], DC_CY + 4.4, 0.9)
    headers = []
    hole_boxes = []
    for first, count, y_mm in HEADERS.values():
        x0 = first - 1.27
        headers.append(rbox(x0, y_mm - 1.27, x0 + count * 2.54, y_mm + 1.27, 0.3))
        for k in range(count):
            px = first + k * 2.54
            hole_boxes.append(sg.box(px - 0.55, y_mm - 0.55, px + 0.55, y_mm + 0.55))
    icsp_boxes = [
        rbox(ICSP2_POS[0] - 3.81, ICSP2_POS[1] - 2.54, ICSP2_POS[0] + 3.81, ICSP2_POS[1] + 2.54, 0.4),
        rbox(ICSP_POS[0] - 2.54, ICSP_POS[1] - 3.81, ICSP_POS[0] + 2.54, ICSP_POS[1] + 3.81, 0.4),
    ]
    icsp_pins = []
    for cx, cy, cols, rows in ((*ICSP2_POS, 3, 2), (*ICSP_POS, 2, 3)):
        for r in range(rows):
            for c in range(cols):
                px = cx + (c - (cols - 1) / 2) * 2.54
                py = cy + (r - (rows - 1) / 2) * 2.54
                icsp_pins.append(sg.box(px - 0.6, py - 0.6, px + 0.6, py + 0.6))
    dip = rbox(DIP_POS[0] - 18.4, DIP_POS[1] - 3.2, DIP_POS[0] + 18.4, DIP_POS[1] + 3.2, 0.6)
    u16 = rbox(U16_POS[0] - 3.0, U16_POS[1] - 3.0, U16_POS[0] + 3.0, U16_POS[1] + 3.0, 0.4)
    reg_box_ = rbox(REG_POS[0] - 1.9, REG_POS[1] - 3.3, REG_POS[0] + 1.9, REG_POS[1] + 3.3, 0.3)
    reset = rbox(RESET_POS[0] - 4.0, RESET_POS[1] - 2.9, RESET_POS[0] + 4.0, RESET_POS[1] + 2.9, 0.6)
    reset_cap = sg.Point(*RESET_POS).buffer(1.8, quad_segs=10)
    caps = [sg.Point(cx, cy).buffer(3.3, quad_segs=14) for cx, cy in CAPS]
    cap_stripes = [c.intersection(sg.box(cx - 4, cy - 4, cx + 4, cy - 1.9)) for c, (cx, cy) in zip(caps, CAPS)]
    leds = {"L": "#f6df8e", "TX": "#e9eef0", "RX": "#e9eef0", "ON": "#aaf1b8"}
    logo = brand.logo_mm()
    uno_text = brand.uno_letters_mm()
    uno_dots = brand.uno_dots_mm(0.9)
    mark = shapely.unary_union([logo, uno_text, uno_dots])

    if monochrome:
        body = shapely.unary_union([board, usb, dc])
        cut = shapely.unary_union([*headers, dip, u16, reg_box_, reset, *caps, *icsp_boxes, mark])
        d = _poly_path(body.difference(cut), tx, ty)
        return (
            '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108" data-morph-unsupported="true">'
            f'<title>Arduino Uno R3 monochrome</title><path fill-rule="evenodd" d="{d}" fill="#000"/></svg>'
        )

    defs = (
        '<linearGradient id="gb" gradientUnits="userSpaceOnUse" x1="54" y1="21" x2="54" y2="87">'
        '<stop offset="0" stop-color="#22b0b4"/><stop offset="0.5" stop-color="#00868b"/><stop offset="1" stop-color="#00555a"/></linearGradient>'
        '<linearGradient id="gu" gradientUnits="userSpaceOnUse" x1="0" y1="38" x2="0" y2="62">'
        '<stop offset="0" stop-color="#eceff1"/><stop offset="1" stop-color="#9ba5ad"/></linearGradient>'
        '<linearGradient id="gk" gradientUnits="userSpaceOnUse" x1="0" y1="21" x2="0" y2="87">'
        '<stop offset="0" stop-color="#3a4048"/><stop offset="1" stop-color="#15181c"/></linearGradient>'
    )

    def path(geom, fill, extra=""):
        d = _poly_path(geom, tx, ty)
        return f'<path d="{d}" fill="{fill}"{extra}/>' if d else ""

    parts = [
        path(board, "url(#gb)"),
        path(usb, "url(#gu)"),
        path(dc, "url(#gk)"),
        path(shapely.unary_union(headers), "url(#gk)"),
        path(shapely.unary_union(hole_boxes), "#06080a"),
        path(shapely.unary_union(icsp_boxes), "url(#gk)"),
        path(shapely.unary_union(icsp_pins), "#c9ced3"),
        path(dip, "url(#gk)"),
        path(u16, "url(#gk)"),
        path(reg_box_, "url(#gk)"),
        path(reset, "#eeeeec"),
        path(reset_cap, "#a82823"),
        path(shapely.unary_union(caps), "#e4e6e7"),
        path(shapely.unary_union(cap_stripes), "#6a737b"),
    ]
    for (label, lx, ly), fill in zip(LEDS, leds.values()):
        parts.append(path(rbox(lx - 1.2, ly - 0.7, lx + 1.2, ly + 0.7, 0.25), fill))
    parts.append(path(mark, "#ffffff"))
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108" data-morph-unsupported="true">'
        f"<title>Arduino Uno R3 Teal</title><defs>{defs}</defs>" + "".join(parts) + "</svg>"
    )


def write_svg_and_preview(svg_text: str, svg_path: Path, preview_path: Path | None = None) -> None:
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(svg_text, encoding="utf-8")
    if preview_path is not None:
        png = bytes(resvg_py.svg_to_bytes(svg_string=svg_text, width=432, height=432))
        image = Image.open(io.BytesIO(png)).convert("RGBA")
        bbox = image.getbbox()
        if bbox:
            image = image.crop(bbox)
        image.thumbnail((120, 170), Image.Resampling.LANCZOS)
        thumb = Image.new("RGBA", (140, 180))
        thumb.alpha_composite(image, ((140 - image.width) // 2, (180 - image.height) // 2))
        preview_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(preview_path)


def main() -> None:
    model_id = "arduino-uno-r3"
    catalog_model = "arduino_uno_r3"
    name = "Arduino Uno R3"

    scene, mats = build_arduino_uno_r3_scene()
    raw = scene.export(file_type="glb")
    with tempfile.NamedTemporaryFile(suffix=".glb", delete=False) as handle:
        temp = Path(handle.name)
        temp.write_bytes(raw)
    optics.apply_glb(temp)
    glb = temp.read_bytes()
    temp.unlink()

    models_dir = DEVICES / "models"
    profiles_dir = DEVICES / "profiles"
    for old in models_dir.glob(f"{model_id}.*.glb.gz"):
        old.unlink()

    digest = hashlib.sha256(glb).hexdigest()
    gz = gzip.compress(glb, compresslevel=9, mtime=0)
    gz_digest = hashlib.sha256(gz).hexdigest()
    gz_name = f"{model_id}.{gz_digest[:12]}.glb.gz"
    (models_dir / gz_name).write_bytes(gz)

    peripheral_meta = {
        "category": "microcontroller",
        "architecture": "avr-atmega328p",
        "transports": ["usb", "serial"],
        "usb": {
            "vendorIds": [9025, 10755],
            "productIds": [67, 1, 579],
            "matches": [
                {"vendorId": 9025, "productId": 67, "name": "Arduino Uno R3"},
                {"vendorId": 9025, "productId": 1, "name": "Arduino Uno"},
                {"vendorId": 9025, "productId": 579, "name": "Arduino Uno R3"},
                {"vendorId": 10755, "productId": 67, "name": "Arduino Uno R3"},
            ],
            "namePatterns": ["Arduino Uno", "ATmega328P", "ATmega16U2"],
        },
        "pins": {
            "digital": 14,
            "pwm": [3, 5, 6, 9, 10, 11],
            "analog": 6,
            "voltage": 5.0,
        },
    }

    finishes = [
        {
            "name": "Teal",
            "materials": {
                "pcb": {"rgb": [0.0, 0.506, 0.518], "rough": 0.34, "metal": 0.05},
                "silkscreen": {"rgb": [0.94, 0.96, 0.96], "rough": 0.42, "metal": 0.0},
                "metal": {"rgb": [0.79, 0.82, 0.85], "rough": 0.22, "metal": 0.88},
                "pin_silver": {"rgb": [0.78, 0.80, 0.83], "rough": 0.38, "metal": 0.8},
                "plastic": {"rgb": [0.11, 0.12, 0.14], "rough": 0.42, "metal": 0.04},
            },
        }
    ]

    profile = {
        "id": model_id,
        "name": name,
        "manufacturer": "Arduino",
        "form_factor": "peripheral",
        "status": "published hardware dimensions; procedural component geometry",
        "body_mm": {
            "width": 68.6,
            "height": 15.0,
            "depth": 53.4,
            "pcb_thickness": 1.6,
        },
        "finish": "Teal",
        "finishes": {item["name"]: item["materials"] for item in finishes},
        "materials": finishes[0]["materials"],
        "screens": [],
        "peripheral": peripheral_meta,
        "sources": [
            "https://docs.arduino.cc/hardware/uno-rev3/",
            "https://store.arduino.cc/products/arduino-uno-rev3",
        ],
        "accuracy": {
            "body_dimensions": "Published Arduino Uno R3 PCB outline (68.6 x 53.4 mm) and four mounting holes.",
            "component_geometry": "Procedural USB-B port, DC barrel jack, ATmega328P DIP-28 socket, 2.54 mm female headers, ICSP headers, crystal, reset switch and SMD status LEDs.",
            "finishes": "Classic Arduino teal solder mask with white silkscreen, brushed nickel connectors and matte black headers.",
        },
    }
    (profiles_dir / f"{model_id}.json").write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    metadata = {
        "id": model_id,
        "name": name,
        "state": "default",
        "glbUrl": f"assets/devices/models/{gz_name}",
        "sha256": gz_digest,
        "body_mm": profile["body_mm"],
        "screens": [],
        "frames": [],
        "slots": {
            "pcb": "Arduino PCB",
            "silkscreen": "PCB silkscreen",
            "metal": "Connector shield",
            "pin_silver": "Tinned pins & pads",
            "plastic": "Header & jack housing",
        },
        "finishes": finishes,
        "articulation": None,
        "panels": [],
        "orientation": "0deg 0deg 0deg",
        "introOrbit": "0deg 0deg",
        # Planar icon morph: world (x, z) in metres -> icon (x, y); the model starts flattened onto the PCB top.
        "icon_morph": {
            "mode": "planar",
            "viewBox": 108,
            "scale": ICON_SCALE * 1000.0,
            "originX": ICON_ORIGIN[0] - BOARD_OFFSET[0] * ICON_SCALE,
            "originY": ICON_ORIGIN[1] + BOARD_OFFSET[1] * ICON_SCALE,
            "planeY": 0.0008,
        },
        "exposure": 0.8,
        "cameraOrbit": "-22deg 50deg auto",
        "orbits": {
            "front": "0deg 62deg auto",
            "back": "180deg 62deg auto",
            "side": "-90deg 80deg auto",
            "angle": "-22deg 50deg auto",
            "reset": "-22deg 50deg auto",
        },
        "peripheral": peripheral_meta,
        "provenance": {
            "kind": "procedural-peripheral-board",
            "profile": f"assets/devices/profiles/{model_id}.json",
            "sources": profile["sources"],
            "accuracy": profile["accuracy"],
        },
    }
    (models_dir / f"{model_id}.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    icons_dir = DEVICES / "icons" / "arduino" / "peripherals"
    previews_dir = DEVICES / "previews"
    teal_svg_path = icons_dir / "ic_arduino_uno_r3_teal_icon.svg"
    mono_svg_path = icons_dir / "ic_arduino_uno_r3_monochrome_icon.svg"
    teal_prev_path = previews_dir / "arduino_uno_r3_teal.png"

    write_svg_and_preview(generate_arduino_svg(monochrome=False), teal_svg_path, teal_prev_path)
    write_svg_and_preview(generate_arduino_svg(monochrome=True), mono_svg_path, None)

    catalog_path = DEVICES / "catalog.json"
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    catalog_entry = {
        "model": catalog_model,
        "brand": "arduino",
        "kind": "peripheral",
        "label": name,
        "variants": [
            {
                "color": "teal",
                "sourceSvg": generate_arduino_svg(monochrome=False),
                "svg": "assets/devices/icons/arduino/peripherals/ic_arduino_uno_r3_teal_icon.svg",
                "preview": "assets/devices/previews/arduino_uno_r3_teal.png",
            }
        ],
        "monochrome": "assets/devices/icons/arduino/peripherals/ic_arduino_uno_r3_monochrome_icon.svg",
        "sources": profile["sources"],
        "accuracy": profile["accuracy"],
        "model3d": {
            "states": {"default": model_id},
            "hasFrame": False,
        },
        "peripheral": peripheral_meta,
    }

    replaced = False
    for idx, item in enumerate(catalog):
        if item.get("model") == catalog_model:
            catalog[idx] = catalog_entry
            replaced = True
            break
    if not replaced:
        catalog.append(catalog_entry)
    catalog_path.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")

    manifest_path = DEVICES / "models-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key in list(manifest["files"]):
        if key.startswith(f"assets/devices/models/{model_id}."):
            del manifest["files"][key]
    manifest["files"][f"assets/devices/models/{gz_name}"] = {
        "bytes": len(gz),
        "sha256": gz_digest,
        "uncompressedBytes": len(glb),
        "uncompressedSha256": digest,
    }
    manifest["files"] = dict(sorted(manifest["files"].items()))
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"Generated {model_id}: {gz_name} ({len(gz):,} bytes compressed, {len(glb):,} bytes GLB)")


if __name__ == "__main__":
    main()
