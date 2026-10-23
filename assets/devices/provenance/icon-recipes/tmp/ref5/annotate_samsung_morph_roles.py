"""Apply the reviewed Samsung slab/tablet map; never regenerate artwork.

Run with --apply after SVG generation. Geometry/profile/mesh changes require a
new review of samsung-morph-role-map.json. Default mode verifies without edits.
"""
import argparse
import io
import json
import re
import struct
import subprocess
from pathlib import Path

from annotate_morph_roles import ATTR, FRAMEWORK, HERE, NS, ROOT, annotate, paths, sha


def mesh_inventory(path):
    with path.open("rb") as stream:
        header = stream.read(20)
        assert header[:4] == b"glTF" and header[16:20] == b"JSON", path
        doc = json.loads(stream.read(struct.unpack_from("<I", header, 12)[0]))
    return [{"name": node.get("name", ""), "materials": [
        doc["materials"][p["material"]]["name"]
        for p in doc["meshes"][node["mesh"]]["primitives"]]}
        for node in doc["nodes"] if "mesh" in node]


def targets(role, meshes):
    """Match the existing renderer, including its material-based bar/logo slots."""
    name = lambda n: n["name"].lower().replace("_", " ")
    if role == "body":
        selected = [n for n in meshes if re.match(r"^(body |aluminum enclosure|rear glass)", name(n))]
    elif role in ("bar", "bar-fill"):
        selected = [n for n in meshes if n["materials"] == ["bar"] and not re.search(r"lens rim|dial side bridge", name(n))]
    elif role == "logo":
        selected = [n for n in meshes if n["materials"] == ["logo"]]
    elif role.startswith("glass-"):
        index = int(role.split("-")[-1])
        selected = [n for n in meshes if re.fullmatch(rf"(black optical backing|optical well|continuous camera cover) {index}", name(n))]
    elif role.startswith("ring-"):
        selected = [n for n in meshes if name(n) == "camera lens rim " + role.split("-")[-1]]
    elif role.startswith("sensor-"):
        selected = [n for n in meshes if name(n) == "rear sensor " + role.split("-")[-1]]
    elif role.startswith(("flash-", "flash-rim-")):
        selected = [n for n in meshes if name(n) == "flash " + role.split("-")[-1]]
    else:
        raise AssertionError("Unreviewed Samsung role: " + role)
    return selected


def check_structure(data, entry):
    root, _, drawable = paths(data)
    for node in root.iter():
        if "transform" in node.attrib or node.get("stroke", "none") != "none":
            affected = [p for p in node.iter() if p in drawable]
            assert affected and all(entry["roles"][drawable.index(p)] == "!transform-or-stroke" for p in affected), "Transform/stroke must remain unsupported"
    assert all(n.get("fill") != "none" for n in drawable)
    clips = list(root.iter(NS + "clipPath"))
    assert len(clips) == entry["body_clip_count"]
    body = drawable[entry["roles"].index("body")]
    allowed = set()
    for clip in clips:
        assert len(clip) == 1 and clip[0].tag == NS + "path" and clip[0].get("d") == body.get("d"), "Only reviewed body clips allowed"
        allowed.add("url(#" + clip.get("id") + ")")
    assert all(n.get("clip-path") in allowed for n in root.iter() if "clip-path" in n.attrib)


def check_renderer(models):
    # Exercise the actual role resolver without launching a gallery or WebGL build.
    script = r"""
const fs=require('fs'),vm=require('vm'),crypto=require('crypto');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('function iconMorphRoles('),end=source.indexOf('function cancelIconMorph(');
if(start<0||end<start)throw Error('Renderer role resolver moved; review required');
const context={};vm.createContext(context);vm.runInContext(source.slice(start,end),context);
const models=JSON.parse(fs.readFileSync(0,'utf8')),accepted=[],rejected=[];
for(const entry of Object.values(models)){
  const paths=entry.roles.map(role=>{
    const attrs=role.startsWith('!')?{'data-morph-unsupported':role.slice(1)}:{'data-morph-role':role};
    return {hasAttribute:key=>key in attrs,getAttribute:key=>attrs[key]??null,ownerSVGElement:{hasAttribute:()=>false}};
  });
  const roles=context.iconMorphRoles(paths,{id:entry.id});
  if(Boolean(roles)!==entry.supported)throw Error('Resolver disagrees: '+entry.id);
  if(!roles){rejected.push(entry.id);continue;}
  const primary=[roles.body,roles.bar,roles.logo,...roles.glass,...roles.rings,...roles.flashes,...roles.sensors].filter(i=>i!==undefined);
  const covered=new Set(primary.flatMap(i=>[i,...(roles.layers[i]||[])]));
  if(covered.size!==paths.length)throw Error('Unconsumed source path: '+entry.id);
  accepted.push(entry.id);
}
process.stdout.write(JSON.stringify({renderer_sha256:crypto.createHash('sha256').update(source).digest('hex'),accepted,rejected,all_supported_paths_consumed:true}));
"""
    result = subprocess.run(["node", "-e", script, str(HERE / "gallery_icon_morph.js")],
                            input=json.dumps(models), text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", type=Path, default=HERE / "samsung-morph-role-report.json")
    args = parser.parse_args()
    import resvg_py
    from PIL import Image

    mapping = json.loads((HERE / "samsung-morph-role-map.json").read_text())
    renderer_check = check_renderer(mapping["models"])
    files = sorted((ROOT / "device_icons_svg/samsung").glob("*/*.svg"))
    frozen = {p: sha(p.read_bytes()) for p in files if "monochrome" in p.name or p.name.startswith("ic_galaxy_z_")}
    groups = {model: [] for model in mapping["models"]}
    for path in files:
        if path in frozen:
            continue
        model = next((m for m in sorted(groups, key=len, reverse=True) if path.name.startswith("ic_" + m + "_")), None)
        assert model, f"Unreviewed Samsung model: {path}"
        groups[model].append(path)
    report = {"coordinate_contract": mapping["coordinate_contract"], "notes": mapping["notes"],
              "rgba_baseline": "Original SVG bytes with only data-morph-role/unsupported attributes removed; compared to annotated bytes, including on reruns.",
              "render_size": [216, 216], "supported_ids": [], "models": {}, "files": [],
              "excluded_families": mapping["excluded_families"], "unsupported_families": {},
              "renderer_role_check": renderer_check}
    changed = 0
    for model, entry in mapping["models"].items():
        assert groups[model], model
        profile_bytes = (FRAMEWORK / entry["profile"]).read_bytes()
        assert sha(profile_bytes) == entry["profile_sha256"], f"Profile changed: {model}"
        profile = json.loads(profile_bytes)
        assert profile["form_factor"] in ("phone", "tablet") and not profile.get("articulation") and not profile.get("robot_motion")
        meshes = mesh_inventory(FRAMEWORK / entry["export"])
        assert meshes == entry["mesh_inventory"], f"Mesh names/materials changed: {model}"
        for role, expected in entry["mesh_targets"].items():
            assert targets(role, meshes) == expected and expected, (model, role)
        if entry["supported"]:
            assert not any(role.startswith("!") for role in entry["roles"])
            assert {r for r in entry["roles"] if r.startswith("glass-")} == {f"glass-{i}" for i in range(len(profile["camera"]["windows"]))}
            report["supported_ids"].append(profile["id"])
        for reason in entry["unsupported"]:
            report["unsupported_families"].setdefault(reason, []).append(profile["id"])
        report["models"][model] = {"id": profile["id"], "supported": entry["supported"],
            "variants": len(groups[model]), "roles": entry["roles"], "unsupported": entry["unsupported"],
            "mesh_targets": entry["mesh_targets"], "camera_index_evidence": entry["camera_index_evidence"]}
        for path in groups[model]:
            before = path.read_bytes()
            check_structure(before, entry)
            after, clean, painted, definitions = annotate(before, entry)
            assert annotate(after, entry)[0] == after, "Non-idempotent postpass"
            def pixels(data):
                return Image.open(io.BytesIO(resvg_py.svg_to_bytes(svg_string=data.decode("utf-8"), width=216, height=216))).convert("RGBA").tobytes()
            before_pixels, after_pixels = pixels(clean), pixels(after)
            assert before_pixels == after_pixels, f"RGBA changed: {path}"
            assert ATTR.sub(b"", after) == ATTR.sub(b"", before), "Non-metadata byte change"
            if args.apply and before != after:
                assert path.read_bytes() == before, f"Concurrent edit: {path}"
                path.write_bytes(after)
                changed += 1
            report["files"].append({"path": path.relative_to(ROOT).as_posix(), "model": model,
                "before_sha256": sha(before), "after_sha256": sha(after), "nonmetadata_sha256": sha(clean),
                "rgba_before_sha256": sha(before_pixels), "rgba_after_sha256": sha(after_pixels),
                "byte_geometry_equal": True, "xml_equal": True, "idempotent": True,
                "drawable_paths": painted, "definition_paths": definitions})
    assert all(sha(p.read_bytes()) == digest for p, digest in frozen.items()), "Excluded SVG changed"
    report["preserved_files"] = {p.relative_to(ROOT).as_posix(): digest for p, digest in frozen.items()}
    report["summary"] = {"models": len(groups), "supported_models": len(report["supported_ids"]),
        "unsupported_models": len(groups) - len(report["supported_ids"]), "svgs": len(report["files"]),
        "changed": changed, "applied": args.apply, "all_bytes_xml_rgba_idempotence_verified": True,
        "monochrome_unchanged": sum("monochrome" in p.name for p in frozen),
        "colored_articulated_unchanged": sum("monochrome" not in p.name for p in frozen)}
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"]))


if __name__ == "__main__":
    main()
