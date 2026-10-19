"""Validate exactly the distributable inventory, including privacy checks."""
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / "manifest.json").read_text())
    forbidden = [r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----", r"gh[pousr]_[A-Za-z0-9]{30,}",
        r"github_pat_[A-Za-z0-9_]{30,}", r"AKIA[A-Z0-9]{16}", r"(?:[A-Za-z]:[\\/](?:Users|home)[\\/])",
        r"(?<!\d)(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3})(?!\d)"]
    errors = []
    public_files = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for name in filter(None, public_files):
        path = ROOT / name
        if path.suffix in {".json", ".js", ".md", ".txt", ".py", ".kt", ".svg", ".css", ".html", ".yml"}:
            contents = path.read_text(encoding="utf-8")
            if any(re.search(pattern, contents) for pattern in forbidden):
                errors.append(f"Private data pattern in public source: {name}")
    for name, entry in manifest["files"].items():
        path = ROOT / name
        if not path.resolve().is_relative_to(ROOT):
            errors.append(f"Unsafe asset path: {name}")
            continue
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
            errors.append(f"Inventory mismatch: {name}")
        if path.suffix in {".json", ".js", ".md", ".txt", ".py", ".kt", ".svg", ".css"}:
            text = data.decode("utf-8")
            for pattern in forbidden:
                if re.search(pattern, text):
                    errors.append(f"Private data pattern in: {name}")
                    break
        if path.suffix == ".svg":
            svg = ET.fromstring(data)
            for node in svg.iter():
                if node.tag.rsplit("}", 1)[-1] in {"script", "foreignObject"} or any(key.lower().startswith("on") for key in node.attrib):
                    errors.append(f"Active SVG content: {name}")
        if path.suffix in {".ttf", ".woff2"}:
            font = TTFont(io.BytesIO(data))
            if not font.getBestCmap():
                errors.append(f"Empty font: {name}")
    shapes = json.loads((ROOT / "assets/shapes/catalog.json").read_text())
    for shape in shapes:
        if not (ROOT / shape["svg"]).is_file() or not (ROOT / shape["largeSvg"]).is_file():
            errors.append(f"Missing shape export: {shape['id']}")
    devices = json.loads((ROOT / "assets/devices/catalog.json").read_text())
    if len({device["model"] for device in devices}) != len(devices):
        errors.append("Duplicate device IDs")
    for device in devices:
        for variant in device["variants"]:
            for key in ["svg", "preview"]:
                if key in variant and not (ROOT / variant[key]).is_file():
                    errors.append(f"Missing {key}: {device['model']}/{variant['color']}")
        for model in device.get("model3d", {}).get("states", {}).values():
            if not (ROOT / "assets/devices/models" / (model + ".json")).is_file():
                errors.append(f"Missing model metadata: {model}")
    symbols = json.loads((ROOT / "assets/symbols/catalog.json").read_text())
    upstream = json.loads((ROOT / "assets/symbols/upstream.json").read_text())
    if symbols["revision"] != upstream["ref"]:
        errors.append("Symbols font/catalog revision mismatch")
    for style, names in symbols["styles"].items():
        font = TTFont(ROOT / f"assets/symbols/material_symbols_{style}.ttf")
        if set(names.values()) - set(font.getBestCmap()):
            errors.append(f"Names without glyphs: {style}")
    if errors:
        raise SystemExit("\n".join(errors))
    print(f"Validated {len(manifest['files'])} assets; {len(devices)} device families; {len(shapes)} shapes; fonts and Symbols agree.")


if __name__ == "__main__":
    main()
