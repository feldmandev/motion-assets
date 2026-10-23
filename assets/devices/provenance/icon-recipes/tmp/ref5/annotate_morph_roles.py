"""Apply reviewed Apple/OnePlus path roles without serializing or redrawing SVGs.

Run with --apply to write attributes; otherwise verify the proposed postpass.
The companion JSON pins actual geometry, explicit path roles and profile indices.
Run this again after generating SVGs. Changed geometry requires a mapping review.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import struct
import xml.etree.ElementTree as ET


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
FRAMEWORK = ROOT.parent / "home/home-android/demo-video/device-models"
ATTR = re.compile(rb' data-morph-(?:role|unsupported)="[^"]*"')
PATH = re.compile(rb'<path\b[^>]*>')
NS = "{http://www.w3.org/2000/svg}"
ROLES = re.compile(r'body|bar|bar-fill|logo|rear-insert|bridge|rear-band|(?:glass|ring|flash|flash-rim|sensor)-\d+')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def paths(data):
    root = ET.fromstring(data)
    definitions = {id(n) for d in root.findall(NS + "defs") for n in d.iter()}
    all_paths = list(root.iter(NS + "path"))
    drawable = [n for n in all_paths if id(n) not in definitions]
    # This postpass is intentionally only for the reviewed path-only artwork.
    assert not any(n.tag in {NS + t for t in ("rect", "circle", "ellipse", "line", "polyline", "polygon", "use", "text", "image")} for n in root.iter())
    return root, all_paths, drawable


def geometry_hash(data):
    root, _, _ = paths(data)
    # Include hierarchy/clip/transform and stroke geometry, but allow finish colors.
    fields = ("d", "transform", "clip-path", "fill-rule", "stroke-width", "stroke-linecap", "stroke-linejoin", "stroke-dasharray", "viewBox")
    signature = [(n.tag, {k: n.get(k) for k in fields if k in n.attrib}, n.get("fill") == "none", "stroke" in n.attrib)
                 for n in root.iter() if n.tag in {NS + t for t in ("svg", "g", "clipPath", "path")}]
    return sha(json.dumps(signature, sort_keys=True).encode())


def coordinate_hash(profile):
    camera = profile.get("camera", {})
    return sha(json.dumps({"body": profile["body_mm"], "camera": {k: camera.get(k) for k in ("windows", "flash", "sensors")}}, sort_keys=True).encode())


def mesh_names(path):
    with path.open("rb") as stream:
        header = stream.read(20)
        assert header[:4] == b"glTF" and header[16:20] == b"JSON", path
        doc = json.loads(stream.read(struct.unpack_from("<I", header, 12)[0]))
    return [n.get("name", "") for n in doc["nodes"] if "mesh" in n]


def annotate(data, entry):
    clean = ATTR.sub(b"", data)
    assert geometry_hash(clean) in entry["geometry_sha256"], "Unreviewed geometry; update the explicit map first"
    _, all_paths, drawable = paths(clean)
    assert len(drawable) == len(entry["roles"]), "Missing or extra drawable paths"
    roles = dict(zip(map(id, drawable), entry["roles"]))
    annotations = []
    for node in all_paths:
        role = roles.get(id(node), "!definition-path")
        if node in drawable and node.get("fill") == "none":
            index = drawable.index(node)
            assert str(index) in entry.get("stroke_roles", {}), "Stroke requires a dedicated reviewed mapping"
            assert entry["stroke_roles"][str(index)] == role
        if role.startswith("!"):
            value = role[1:]
            assert value in entry["unsupported"] or value == "definition-path"
            attr = ' data-morph-unsupported="' + value + '"'
        else:
            assert ROLES.fullmatch(role), role
            attr = ' data-morph-role="' + role + '"'
        annotations.append(attr.encode())
    matches = list(PATH.finditer(clean))
    assert len(matches) == len(all_paths), "XML and byte path inventories differ"
    result = bytearray()
    end = 0
    for match, attr in zip(matches, annotations):
        insert = match.end() - (2 if match.group().endswith(b"/>") else 1)
        result.extend(clean[end:insert])
        result.extend(attr)
        end = insert
    result.extend(clean[end:])
    result = bytes(result)
    assert ATTR.sub(b"", result) == clean, "Non-metadata byte change"
    # XML equality also proves geometry, paints, element order and coordinates unchanged.
    after_root, after_paths, after_drawable = paths(result)
    assert len(after_paths) == len(all_paths) and len(after_drawable) == len(drawable)
    for node in after_root.iter():
        node.attrib.pop("data-morph-role", None)
        node.attrib.pop("data-morph-unsupported", None)
    assert ET.tostring(after_root) == ET.tostring(ET.fromstring(clean))
    assert all(("data-morph-role" in p.attrib) != ("data-morph-unsupported" in p.attrib) for p in paths(result)[1])
    return result, clean, len(drawable), len(all_paths) - len(drawable)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path, default=HERE / "morph-role-report.json")
    args = parser.parse_args()
    import resvg_py
    from PIL import Image

    mapping = json.loads((HERE / "morph-role-map.json").read_text())
    models = mapping["models"]
    files = sorted(p for brand in ("apple", "oneplus") for kind in ("phones", "tablets")
                   for p in (ROOT / "device_icons_svg" / brand / kind).glob("*.svg")
                   if "monochrome" not in p.name)
    groups = {model: [] for model in models}
    for path in files:
        model = next((m for m in sorted(models, key=len, reverse=True) if path.name.startswith("ic_" + m + "_")), None)
        assert model, f"Unmapped model: {path}"
        groups[model].append(path)
    report = {"coordinate_contract": mapping["coordinate_contract"], "render_size": [216, 216],
              "mapping_notes": mapping["notes"],
              "definition_paths": "Non-painted clip paths: explicit unsupported definition-path; never morph targets.",
              "models": {}, "files": [], "pending": []}
    monochrome = {p: sha(p.read_bytes()) for brand in ("apple", "oneplus") for kind in ("phones", "tablets")
                  for p in (ROOT / "device_icons_svg" / brand / kind).glob("*monochrome*.svg")}
    changed = 0
    for model, entry in models.items():
        if not groups[model]:
            report["pending"].append(model)
            continue
        if entry["profile"]:
            profile = json.loads((FRAMEWORK / entry["profile"]).read_text())
            assert coordinate_hash(profile) == entry["coordinate_sha256"], f"Profile coordinates changed: {model}"
            names = mesh_names(FRAMEWORK / entry["export"])
            for role, targets in entry["mesh_targets"].items():
                assert all(target in names for target in targets), (model, role, targets)
        report["models"][model] = {k: v for k, v in entry.items() if k != "geometry_sha256"}
        report["models"][model]["variants"] = len(groups[model])
        report["models"][model]["role_paths"] = {role: [i for i, r in enumerate(entry["roles"]) if r == role] for role in dict.fromkeys(entry["roles"])}
        for path in groups[model]:
            before = path.read_bytes()
            after, clean, painted, definitions = annotate(before, entry)
            assert annotate(after, entry)[0] == after, "Postpass is not idempotent"
            def pixels(data):
                png = resvg_py.svg_to_bytes(svg_string=data.decode("utf-8"), width=216, height=216)
                return Image.open(io.BytesIO(png)).convert("RGBA").tobytes()
            before_pixels, after_pixels = pixels(before), pixels(after)
            assert before_pixels == after_pixels, f"Rendered pixels changed: {path}"
            if args.apply and before != after:
                assert path.read_bytes() == before, f"Concurrent source edit: {path}"
                path.write_bytes(after)
                changed += 1
            report["files"].append({"path": path.relative_to(ROOT).as_posix(), "model": model,
                                    "before_sha256": sha(before), "after_sha256": sha(after),
                                    "nonmetadata_sha256": sha(clean), "xml_equal": True,
                                    "rgba_before_sha256": sha(before_pixels), "rgba_after_sha256": sha(after_pixels),
                                    "drawable_paths": painted, "definition_paths": definitions,
                                    "unsupported_drawable_paths": sum(r.startswith("!") for r in entry["roles"])})
    report["summary"] = {"models": len(report["models"]), "svgs": len(files), "changed": changed,
                         "drawable_paths": sum(f["drawable_paths"] for f in report["files"]),
                         "unsupported_drawable_paths": sum(f["unsupported_drawable_paths"] for f in report["files"]),
                         "applied": args.apply, "all_bytes_xml_pixels_verified": True}
    assert all(sha(p.read_bytes()) == digest for p, digest in monochrome.items()), "Monochrome changed during postpass"
    report["summary"]["monochrome_unchanged"] = len(monochrome)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))
    print("Report:", args.report)


if __name__ == "__main__":
    main()
