"""Import a finalized icon/gallery snapshot and its procedural model provenance.

Only public artwork, generated model data and source/reference JSON are imported.
Downloaded photos, renders, caches, logs and repository history are not copied.
"""
import argparse
import base64
import gzip
import hashlib
import json
from pathlib import Path
import re
import shutil

from catalog import ROOT, write_json


def public_json(value):
    if isinstance(value, dict):
        return {key: public_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [public_json(item) for item in value]
    if isinstance(value, str):
        return re.sub(r"[A-Za-z]:[\\/](?:Users|home)[^\n\"<>]*", "[local reference path omitted]", value)
    return value


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--icons", type=Path, required=True)
    parser.add_argument("--models", type=Path, required=True)
    args = parser.parse_args()
    target = ROOT / "assets/devices"
    text = (args.icons / "gallery.html").read_text(encoding="utf-8")
    start = text.index("const devices=") + len("const devices=")
    devices, length = json.JSONDecoder().raw_decode(text[start:])
    source_catalog = json.loads((args.icons.parent / "tmp/ref5/all_phones/catalog.json").read_text(encoding="utf-8"))
    source_icons = {(entry["model"], variant["color"]): Path(variant["path"])
                    for entry in source_catalog for variant in entry["variants"]}
    for path in sorted(args.icons.rglob("*")):
        if not path.is_file() or path.suffix not in {".svg", ".png"}:
            continue
        relative = path.relative_to(args.icons)
        if relative.parts[0] not in {"pixel", "samsung", "oneplus", "oppo", "nothing", "xiaomi", "redmi", "poco", "honor", "motorola", "apple", "generic"}:
            continue
        destination = target / "icons" / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, destination)
    for device in devices:
        # Keep the source distinction, not a claim that every Pixel-family icon is extracted.
        device["provenance"] = "mixed-vendor-and-derived" if device["brand"] == "pixel" else "drawn-from-references"
        device["license"] = "LicenseRef-Device-Artwork"
        for variant in device["variants"]:
            source = source_icons.get((device["model"], variant["color"]))
            if source is None:
                candidates = list(args.icons.rglob(f"ic_{device['model']}_{variant['color']}_icon.svg"))
                if len(candidates) != 1:
                    raise ValueError(f"Cannot resolve SVG: {device['model']}/{variant['color']}")
                source = candidates[0]
            preview = target / "previews" / f"{device['model']}_{variant['color']}.png"
            preview.parent.mkdir(parents=True, exist_ok=True)
            preview.write_bytes(base64.b64decode(variant.pop("src").split(",", 1)[1]))
            variant["svg"] = (target / "icons" / source.relative_to(args.icons)).relative_to(ROOT).as_posix()
            variant["preview"] = preview.relative_to(ROOT).as_posix()
    model_files = {}
    profile_cache = {path.stem: public_json(json.loads(path.read_text(encoding="utf-8"))) for path in (args.models / "profiles").glob("*.json")}
    for path in sorted((args.icons / "model_data").glob("*.js")):
        script = path.read_text(encoding="utf-8")
        start = script.index("={", script.index("window.__DEVICE_MODEL_DATA__[")) + 1
        data, _ = json.JSONDecoder().raw_decode(script[start:])
        glb = base64.b64decode(data.pop("glb"))
        if glb[:4] != b"glTF":
            raise ValueError(f"Invalid GLB: {path.name}")
        compressed = gzip.compress(glb, compresslevel=9, mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        payload = target / "models" / f"{data['id']}.{digest[:12]}.glb.gz"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_bytes(compressed)
        relative = payload.relative_to(ROOT).as_posix()
        model_files[relative] = {"sha256": digest, "bytes": len(compressed), "glbSha256": hashlib.sha256(glb).hexdigest()}
        data["glbUrl"] = relative
        data["sha256"] = digest
        matches = [key for key in profile_cache if data["id"] == key or data["id"].startswith(key + "-")]
        if not matches:
            raise ValueError(f"Missing procedural source profile: {data['id']}")
        profile = profile_cache[max(matches, key=len)]
        data["provenance"] = {"kind": "procedural-estimate", "profile": f"assets/devices/profiles/{profile['id']}.json",
                              "accuracy": profile.get("accuracy", {}), "sources": profile.get("sources", [])}
        for index, frame in enumerate(data.get("frames", [])):
            svg = base64.b64decode(frame["image"].split(",", 1)[1])
            output = target / "frames" / f"{data['id']}-{index}.svg"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(svg)
            frame["image"] = output.relative_to(ROOT).as_posix()
        write_json(target / "models" / (data["id"] + ".json"), public_json(data))
    for name, profile in profile_cache.items():
        write_json(target / "profiles" / (name + ".json"), profile)
    for path in sorted((args.models / "research").glob("*.json")):
        # Reference measurements/manifests only: never the neighboring downloaded photographs.
        write_json(target / "provenance/research" / path.name, public_json(json.loads(path.read_text(encoding="utf-8"))))
    for name in ["SOURCES.md", "OLDER_MODELS.md", "NEW_BRANDS.md", "APPLE_MODELS.md", "MONOCHROME.md", "RADIUS_STYLE_NOTES.txt"]:
        path = args.icons / name
        if path.exists():
            output = target / "provenance" / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(public_json(path.read_text(encoding="utf-8")), encoding="utf-8")
    write_json(target / "catalog.json", devices)
    write_json(target / "models-manifest.json", {"schemaVersion": 1, "release": "v0.1.0",
        "archive": "motion-assets-models-0.1.0.zip", "files": model_files})
    # Preserve the existing viewer UI while removing embedded icon and model payloads.
    catalog_start = text.index("const devices=") + len("const devices=")
    _, catalog_length = json.JSONDecoder().raw_decode(text[catalog_start:])
    preview_catalog = json.loads(json.dumps(devices))
    for device in preview_catalog:
        for variant in device["variants"]:
            variant["src"] = variant["preview"]
    text = text[:catalog_start] + json.dumps(preview_catalog, separators=(",", ":"), ensure_ascii=False) + text[catalog_start + catalog_length:]
    text = text.replace('Open supported Pixel, Googlebook, and iPhone models to rotate the 3D model, inspect the exact frame, or switch fold states.', "Open a supported device to rotate its 3D model, inspect its exported frame, or switch fold states.")
    a = text.index("function loadModelScript(id)")
    b = text.index("function availableStates()", a)
    text = text[:a] + """function loadModelScript(id){
 if(window.__DEVICE_MODEL_DATA__[id])return Promise.resolve(window.__DEVICE_MODEL_DATA__[id]);
 if(loadedScripts.has(id))return loadedScripts.get(id);
 const promise=fetch('assets/devices/models/'+encodeURIComponent(id)+'.json?v=0.1.0').then(r=>{if(!r.ok)throw new Error('Model metadata unavailable');return r.json()}).then(async data=>{await Promise.all((data.frames||[]).map(async frame=>{const response=await fetch(frame.image);if(!response.ok)throw new Error('Frame unavailable');const bytes=new Uint8Array(await response.arrayBuffer());frame.image='data:image/svg+xml;base64,'+btoa(Array.from(bytes,b=>String.fromCharCode(b)).join(''));}));window.__DEVICE_MODEL_DATA__[id]=data;return data;});
 loadedScripts.set(id,promise);return promise;
}
""" + text[b:]
    text = text.replace("activeDevice=d;activeState=defaultState(d);", "activeDevice=d;activeModel=null;activeState=defaultState(d);")
    needle = "const bytes=Uint8Array.from(atob(data.glb),c=>c.charCodeAt(0));"
    if needle not in text:
        raise ValueError("Viewer GLB loader changed; update import transform")
    text = text.replace(needle, "const response=await fetch(data.glbUrl);if(!response.ok)throw new Error('Model payload missing; run tools/fetch_models.py');const packed=await response.arrayBuffer();const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',packed))].map(b=>b.toString(16).padStart(2,'0')).join('');if(digest!==data.sha256)throw new Error('Model checksum mismatch');const bytes=new Uint8Array(await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer());")
    text = text.replace("function loadViewer(data){", "async function loadViewer(data){")
    text = text.replace("function showTab(", "async function showTab(")
    text = text.replace("if(is3d)loadViewer(activeModel)", "if(is3d)await loadViewer(activeModel)")
    text = text.replace("if(activeTab==='3d')loadViewer(data)", "if(activeTab==='3d')await loadViewer(data)")
    text = text.replace("viewer.orientation=activeDevice?.kind==='tablet'?", "viewer.orientation=['generic_phone','generic_tablet','generic_pc'].includes(activeDevice?.model)?'0deg 0deg 0deg':activeDevice?.kind==='tablet'?")
    (ROOT / "gallery/devices.html").write_text(text, encoding="utf-8")
    print(f"Imported {len(devices)} families and {len(model_files)} lazy models; photos/renders/history excluded")


if __name__ == "__main__":
    main()
