"""Generate brand-neutral, screen-mapped generic device estimates.

Uses only procedural geometry and the authored generic artwork, with no photos.
The compatibility JS exports can be imported by the original file:// gallery.
"""
import base64
import gzip
import hashlib
import json
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import trimesh
from catalog import ROOT, write_json


def rounded(width, height, depth, radius, name, color, y=0, z=0):
    points = []
    for cx, cy, angle in [(width / 2 - radius, height / 2 - radius, 0),
                          (-width / 2 + radius, height / 2 - radius, 90),
                          (-width / 2 + radius, -height / 2 + radius, 180),
                          (width / 2 - radius, -height / 2 + radius, 270)]:
        for a in np.linspace(angle, angle + 90, 13):
            points.append([cx + radius * math.cos(math.radians(a)), cy + radius * math.sin(math.radians(a))])
    count = len(points)
    vertices = [[x, py + y, zz + z] for zz in [-depth / 2, depth / 2] for x, py in points]
    faces = []
    for i in range(1, count - 1):
        faces.extend([[0, i + 1, i], [count, count + i, count + i + 1]])
    for i in range(count):
        j = (i + 1) % count
        faces.extend([[i, j, count + j], [i, count + j, count + i]])
    mesh = trimesh.Trimesh(vertices=np.array(vertices) * .001, faces=faces, process=False)
    # The front screen material is a stable replacement target for live streaming.
    uv = np.array([[(v[0] + width / 2) / width, (v[1] - y + height / 2) / height] for v in vertices])
    material = trimesh.visual.material.PBRMaterial(name=name, baseColorFactor=color, metallicFactor=.15, roughnessFactor=.45)
    mesh.visual = trimesh.visual.TextureVisuals(uv=uv, material=material)
    return mesh


def main():
    folder = ROOT / "assets/devices"
    catalog = json.loads((folder / "catalog.json").read_text())
    model_manifest = json.loads((folder / "models-manifest.json").read_text())
    for ident, label, kind, width, height, depth, radius, bezel, pixels in [
        ("generic_phone", "Generic phone", "phone", 72, 152, 7.8, 14, 3, [1080, 2400]),
        ("generic_tablet", "Generic tablet", "tablet", 245, 165, 6.5, 14, 5, [1600, 1000]),
        ("generic_pc", "Generic PC", "pc", 320, 210, 12, 30, 12, [1920, 1080]),
    ]:
        model_id = ident.replace("_", "-")
        scene = trimesh.Scene()
        scene.add_geometry(rounded(width, height, depth, radius, "Body", [146, 163, 179, 255]), node_name="Body")
        sw, sh = width - 2 * bezel, height - 2 * bezel
        sr = radius - bezel
        screen_name = "Device screen | replace texture at runtime"
        scene.add_geometry(rounded(sw, sh, .15, sr, screen_name, [43, 69, 94, 255], z=depth / 2 + .1), node_name="Device screen")
        if kind == "pc":
            scene.add_geometry(rounded(30, 58, 18, 8, "Stand", [99, 117, 138, 255], y=-height / 2 - 23, z=-3), node_name="Stand")
            scene.add_geometry(rounded(110, 12, 60, 5, "Foot", [99, 117, 138, 255], y=-height / 2 - 52), node_name="Foot")
        else:
            camera_width = width * (.3167 if kind == "phone" else .1354)
            camera_height = camera_width * (17.6 / 9.5 if kind == "phone" else 12 / 6.5)
            inset = width * (.08333 if kind == "phone" else .03125)
            camera_x = -width / 2 + inset + camera_width / 2
            camera_y = height / 2 - inset - camera_height / 2
            bar = rounded(camera_width, camera_height, 1.5, camera_width / 2, "Camera housing", [83, 103, 123, 255], y=camera_y, z=-depth / 2 - .6)
            bar.apply_translation([camera_x * .001, 0, 0])
            scene.add_geometry(bar, node_name="Camera housing")
            for index, offset in enumerate([camera_height / 2 - camera_width / 2, -camera_height / 2 + camera_width / 2]):
                lens_radius = camera_width * (.35263 if kind == "phone" else .32308)
                lens = rounded(lens_radius * 2, lens_radius * 2, .3, lens_radius, f"Lens {index + 1}", [24, 40, 57, 255], y=camera_y + offset, z=-depth / 2 - 1.5)
                lens.apply_translation([camera_x * .001, 0, 0])
                scene.add_geometry(lens, node_name=f"Lens {index + 1}")
        glb = scene.export(file_type="glb")
        packed = gzip.compress(glb, compresslevel=9, mtime=0)
        digest = hashlib.sha256(packed).hexdigest()
        payload = folder / "models" / f"{model_id}.{digest[:12]}.glb.gz"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(packed)
        relative = payload.relative_to(ROOT).as_posix()
        model_manifest["files"][relative] = {"sha256": digest, "bytes": len(packed), "glbSha256": hashlib.sha256(glb).hexdigest()}
        frame = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><defs><mask id="screen"><rect width="{width}" height="{height}" rx="{radius}" fill="white"/><rect x="{bezel}" y="{bezel}" width="{sw}" height="{sh}" rx="{sr}" fill="black"/></mask></defs><rect width="{width}" height="{height}" rx="{radius}" fill="#63758a" mask="url(#screen)"/></svg>'
        ET.fromstring(frame)
        frame_path = folder / "frames" / f"{model_id}-0.svg"
        frame_path.parent.mkdir(parents=True, exist_ok=True)
        frame_path.write_text(frame)
        profile = {"id": model_id, "name": label, "accuracy": {"geometry": "Brand-neutral procedural illustration, not measured hardware or vendor CAD."}, "sources": [{"kind": "original", "description": "Motion generic device artwork and authored screen mapping"}]}
        write_json(folder / "profiles" / (model_id + ".json"), profile)
        data = {"id": model_id, "name": label, "state": "default", "glbUrl": relative, "sha256": digest,
            "screens": [{"node": "Device screen", "nodes": ["Device screen"], "material": screen_name, "resolution": pixels,
                "size_mm": [sw, sh], "center_mm": [0, 0, depth / 2 + .1], "rotation_deg": [0, 0, 0], "corner_radius_mm": sr}],
            "frames": [{"name": "Device screen", "file": frame_path.name, "image": frame_path.relative_to(ROOT).as_posix()}],
            "adaptive": True, "slots": {}, "finishes": [],
            "provenance": {"kind": "procedural-estimate", "profile": f"assets/devices/profiles/{model_id}.json", **{key: profile[key] for key in ["accuracy", "sources"]}}}
        write_json(folder / "models" / (model_id + ".json"), data)
        entry = next(device for device in catalog if device["model"] == ident)
        entry["model3d"] = {"states": {"default": model_id}, "hasFrame": True}
        legacy = json.loads(json.dumps(data))
        legacy["glb"] = base64.b64encode(glb).decode()
        legacy["frames"][0]["image"] = "data:image/svg+xml;base64," + base64.b64encode(frame.encode()).decode()
        for key in ["glbUrl", "sha256"]:
            legacy.pop(key)
        compatibility = ROOT / "build/legacy-model-data" / (model_id + ".js")
        compatibility.parent.mkdir(parents=True, exist_ok=True)
        compatibility.write_text("window.__DEVICE_MODEL_DATA__=window.__DEVICE_MODEL_DATA__||{};\nwindow.__DEVICE_MODEL_DATA__[" + json.dumps(model_id) + "]=" + json.dumps(legacy, separators=(",", ":")) + ";\n")
    write_json(folder / "catalog.json", catalog)
    write_json(folder / "models-manifest.json", model_manifest)
    print("Generated three generic screen-mapped models, frames and legacy compatibility payloads")


if __name__ == "__main__":
    main()
