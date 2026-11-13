"""Review-only speaker geometry and its orthographic SVG projection."""
from pathlib import Path
import json
import math

import numpy as np
import trimesh
from shapely.geometry import MultiPoint, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree
from trimesh.visual.material import PBRMaterial
from trimesh.visual import TextureVisuals


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets/devices/drafts/peripherals"
VIEW = np.array([.52, -.848, 0])
VIEW /= np.linalg.norm(VIEW)
RIGHT = np.cross([0, 0, 1], VIEW)
RIGHT /= np.linalg.norm(RIGHT)
UP = np.cross(VIEW, RIGHT)
LIGHT = np.array([-.3, -.65, .7])
LIGHT /= np.linalg.norm(LIGHT)
SECTIONS = 96
BODY_PROFILE = np.array([(-1.72, .48), (-1.69, .55), (-1.63, .61),
                         (-1.54, .65), (-1.43, .66), (1.31, .66)])
BODY_DISTANCE = np.r_[0, np.cumsum(np.linalg.norm(np.diff(BODY_PROFILE, axis=0), axis=1))]
WEAVE_COLUMNS, WEAVE_ROWS = 34, 44
STITCH_X, STITCH_Y = .014, .018


def lathe(profile, role):
    """Closed axial profiles share actual bevel, lip and cavity geometry."""
    vertices = np.array([[x, r * math.cos(t), r * math.sin(t)]
                         for x, r in profile
                         for t in np.linspace(0, 2 * math.pi, SECTIONS, endpoint=False)])
    faces = []
    for ring in range(len(profile) - 1):
        for j in range(SECTIONS):
            k = (j + 1) % SECTIONS
            faces.append([ring * SECTIONS + j, ring * SECTIONS + k,
                          (ring + 1) * SECTIONS + k, (ring + 1) * SECTIONS + j])
    return vertices, np.array(faces), role


def geometry():
    body = [(-1.72, 0), *BODY_PROFILE.tolist(), (1.31, 0)]
    # The lip returns inward and back along X to a genuinely recessed floor.
    cap = [(1.28, 0), (1.28, .65), (1.33, .685), (1.48, .685),
           (1.55, .66), (1.59, .60), (1.59, .53), (1.55, .49),
           (1.40, .49), (1.40, 0)]
    return [lathe(body, "fabric"), lathe(cap, "rubber")]


GEOMETRY = geometry()
POINTS = np.concatenate([g[0] for g in GEOMETRY])
BOUNDS = np.column_stack([POINTS @ RIGHT, POINTS @ UP])
SCALE = 90 / np.ptp(BOUNDS[:, 0])
CENTER = (BOUNDS.min(axis=0) + BOUNDS.max(axis=0)) / 2


def project(points):
    p = np.asarray(points)
    return np.column_stack([54 + SCALE * (p @ RIGHT - CENTER[0]),
                            56 - SCALE * (p @ UP - CENTER[1])])


def controls():
    # All marks lie on the recessed end plane, not on the front lip.
    result = []
    arc = np.linspace(math.radians(40), math.radians(320), 26)
    result.append([[1.408, .075 * math.sin(t), .28 + .075 * math.cos(t)] for t in arc])
    for y0, z0, y1, z1 in [(0, .39, 0, .29), (-.085, 0, .085, 0),
                           (0, -.085, 0, .085), (-.085, -.28, .085, -.28)]:
        result.append([[1.408, y0, z0], [1.408, y1, z1]])
    return [np.array(p) for p in result]


def color(stops, role, normal):
    base = np.array([int(stops["mid" if role == "fabric" else "housing"][i:i + 2], 16)
                     for i in (1, 3, 5)], dtype=float)
    shade = .64 + .42 * max(0, float(normal @ LIGHT))
    return "#" + "".join(f"{int(c):02x}" for c in np.clip(base * shade, 0, 255))


def visible_surfaces():
    surfaces = []
    for vertices, faces, role in GEOMETRY:
        for face in faces:
            p = vertices[face]
            normal = np.cross(p[1] - p[0], p[3] - p[0])
            length = np.linalg.norm(normal)
            if length < 1e-9 or normal @ VIEW <= 1e-8:
                continue
            normal /= length
            polygon = Polygon(project(p))
            if polygon.area > 1e-7:
                surfaces.append((polygon, normal, normal @ p[0], role))
    tree = STRtree([s[0] for s in surfaces])
    result = []
    def depth(surface, xy):
        _, n, distance, _ = surface
        x = (xy.x - 54) / SCALE + CENTER[0]
        y = (56 - xy.y) / SCALE + CENTER[1]
        return (distance - n @ RIGHT * x - n @ UP * y) / (n @ VIEW)
    for i, surface in enumerate(surfaces):
        polygon, normal, _, role = surface
        occluders = []
        for j in tree.query(polygon, predicate="intersects"):
            if i == j:
                continue
            other = surfaces[j]
            overlap = polygon.intersection(other[0])
            if overlap.area > 1e-6:
                point = overlap.representative_point()
                if depth(other, point) > depth(surface, point) + 1e-6:
                    occluders.append(other[0])
        visible = polygon.difference(unary_union(occluders)) if occluders else polygon
        if visible.area < 1e-6:
            continue
        shapes = [visible] if visible.geom_type == "Polygon" else list(visible.geoms)
        for shape in shapes:
            if shape.geom_type != "Polygon":
                continue
            path = ""
            for ring in [shape.exterior, *shape.interiors]:
                path += "M" + "L".join(f"{x:.3f} {y:.3f}" for x, y in ring.coords) + "Z"
            result.append((role, normal, path))
    return result


SURFACES = visible_surfaces()


def weave():
    """Follow the fabric's axial arc, including its rounded left shoulder."""
    for row in range(WEAVE_ROWS):
        t = row * 2 * math.pi / WEAVE_ROWS
        circumferential = np.array([0, -math.sin(t), math.cos(t)])
        for col in range(WEAVE_COLUMNS):
            distance = (col + .5 * (row % 2)) * BODY_DISTANCE[-1] / (WEAVE_COLUMNS - 1)
            if distance > BODY_DISTANCE[-1]:
                continue
            band = min(np.searchsorted(BODY_DISTANCE, distance, side="right") - 1, len(BODY_PROFILE) - 2)
            delta = BODY_PROFILE[band + 1] - BODY_PROFILE[band]
            along = delta / np.linalg.norm(delta)
            x, radius = BODY_PROFILE[band] + along * (distance - BODY_DISTANCE[band])
            normal = np.array([-along[1], along[0] * math.cos(t), along[0] * math.sin(t)])
            center = np.array([x, radius * math.cos(t), radius * math.sin(t)]) + .001 * normal
            axial = np.array([along[0], along[1] * math.cos(t), along[1] * math.sin(t)])
            yield center, axial, circumferential, normal


def speaker_svg(target):
    stops = target["stops"]
    outline = MultiPoint(project(GEOMETRY[0][0])).convex_hull
    body_clip = "M" + "L".join(f"{x:.3f} {y:.3f}" for x, y in outline.exterior.coords) + "Z"
    mesh = []
    for center, axial, circumferential, normal in weave():
        if normal @ VIEW <= .025:
            continue
        a, b = project([center, center + axial])
        c = project([center + circumferential])[0] - a
        d = b - a
        mesh.append(f'<use href="#fabric-stitch" transform="matrix({d[0]:.4f} {d[1]:.4f} {c[0]:.4f} {c[1]:.4f} {a[0]:.3f} {a[1]:.3f})"/>')
    body_svg, cap_svg = [], []
    for role, normal, path in SURFACES:
        fill = color(stops, role, normal)
        (body_svg if role == "fabric" else cap_svg).append(
            f'<path d="{path}" fill="{fill}" fill-rule="evenodd" stroke="{fill}" stroke-width=".30"/>')
    marks = []
    for p in controls():
        path = "M" + "L".join(f"{x:.3f} {y:.3f}" for x, y in project(p))
        marks.append(f'<path d="{path}"/>')
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108" fill="none">'
            '<desc>Orthographic projection of the review-only 3D speaker.</desc>'
            f'<defs><ellipse id="fabric-stitch" rx="{STITCH_X}" ry="{STITCH_Y}" fill="{stops["deep"]}" fill-opacity=".38"/>'
            f'<clipPath id="fabric-edge"><path d="{body_clip}"/></clipPath></defs>'
            + '<g id="fabric-body">' + "".join(body_svg) + '</g><g clip-path="url(#fabric-edge)">'
            + "".join(mesh) + '</g>' + "".join(cap_svg)
            + f'<g fill="none" stroke="{stops["light"]}" stroke-width=".65" stroke-linecap="round" stroke-linejoin="round">'
            + "".join(marks) + '</g></svg>')


def export_model(target):
    scene = trimesh.Scene()
    for vertices, quads, role in GEOMETRY:
        faces = np.vstack([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
        mesh = trimesh.Trimesh(vertices=vertices, faces=faces, process=True)
        mesh.update_faces(mesh.nondegenerate_faces())
        mesh.remove_unreferenced_vertices()
        tone = target["stops"]["mid" if role == "fabric" else "housing"]
        rgb = [int(tone[i:i + 2], 16) for i in (1, 3, 5)]
        mesh.visual = TextureVisuals(material=PBRMaterial(name=role, baseColorFactor=rgb + [255], roughnessFactor=.85))
        scene.add_geometry(mesh, node_name=role)
    for j, line in enumerate(controls()):
        for a, b in zip(line[:-1], line[1:]):
            mesh = trimesh.creation.cylinder(radius=.009, segment=[a, b], sections=8)
            mesh.visual = TextureVisuals(material=PBRMaterial(name="controls", baseColorFactor=[194, 206, 217, 255], roughnessFactor=.8))
            scene.add_geometry(mesh, node_name=f"control-{j}-{len(scene.geometry)}")
    vertices, faces = [], []
    for center, axial, circumferential, _ in weave():
        start = len(vertices)
        vertices.append(center)
        for k in range(10):
            q = k * 2 * math.pi / 10
            vertices.append(center + STITCH_X * math.cos(q) * axial - STITCH_Y * math.sin(q) * circumferential)
            faces.append([start, start + 1 + k, start + 1 + (k + 1) % 10])
    knit = trimesh.Trimesh(vertices=vertices, faces=faces, process=False)
    tones = target["stops"]
    rgb = [round(.62 * int(tones["mid"][i:i + 2], 16) + .38 * int(tones["deep"][i:i + 2], 16)) for i in (1, 3, 5)]
    knit.visual = TextureVisuals(material=PBRMaterial(name="fabric weave", baseColorFactor=rgb + [255], roughnessFactor=1))
    scene.add_geometry(knit, node_name="fabric weave")
    scene.export(OUT / "speaker-projection.glb")
    (OUT / "speaker-camera.json").write_text(json.dumps({"projection": "orthographic", "view": VIEW.tolist(),
        "right": RIGHT.tolist(), "up": UP.tolist(), "scale": SCALE, "center": CENTER.tolist()}, indent=2) + "\n")


if __name__ == "__main__":
    palettes = json.loads((ROOT / "assets/devices/generic_palettes.json").read_text())["palettes"]
    export_model(palettes[0])
    for target in palettes:
        (OUT / "variants" / f'generic-speaker_{target["id"]}.svg').write_text(speaker_svg(target), encoding="utf-8")
    print("Draft 3D speaker + 8 vector camera projections written; live assets untouched")
