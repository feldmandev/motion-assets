"""Build deterministic module catalogs and a SHA-256 inventory."""
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    shapes = []
    for path in sorted((ROOT / "assets/shapes/original").glob("*.svg")):
        svg = ET.parse(path).getroot()
        shapes.append({"id": re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-"), "name": path.stem,
            "svg": path.relative_to(ROOT).as_posix(), "largeSvg": "assets/shapes/1024/" + path.name,
            "viewBox": svg.get("viewBox"), "paths": [node.get("d") for node in svg.iter() if node.tag.endswith("}path")]})
    write_json(ROOT / "assets/shapes/catalog.json", shapes)
    fonts = []
    from fontTools.ttLib import TTFont
    for path in sorted((ROOT / "assets/fonts").glob("*.ttf")):
        font = TTFont(path, recalcTimestamp=False)
        font.flavor = "woff2"
        font.save(path.with_suffix(".woff2"))
        fonts.append({"id": "feldman" if path.name == "FeldmanFont.ttf" else path.stem.split("-")[0].lower(),
            "name": font["name"].getDebugName(1), "file": path.relative_to(ROOT).as_posix(), "license": "OFL-1.1",
            "axes": [{"tag": axis.axisTag, "min": axis.minValue, "default": axis.defaultValue, "max": axis.maxValue}
                     for axis in font["fvar"].axes] if "fvar" in font else []})
    write_json(ROOT / "assets/fonts/catalog.json", fonts)
    inventory = {}
    for name in ["LICENSE", "ATTRIBUTION.md"]:
        data = (ROOT / name).read_bytes()
        inventory[name] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    for base in [ROOT / "assets", ROOT / "integrations", ROOT / "LICENSES"]:
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix not in {".glb", ".gz", ".pyc"} and "__pycache__" not in path.parts:
                data = path.read_bytes()
                inventory[path.relative_to(ROOT).as_posix()] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    version = json.loads((ROOT / "package.json").read_text())["version"]
    write_json(ROOT / "manifest.json", {"schemaVersion": 1, "version": version,
        "repository": "https://github.com/feldmandev/motion-assets", "modules": ["shapes", "devices", "fonts", "symbols"],
        "files": inventory})
    print(f"Manifest {version}: {len(inventory)} files, {len(shapes)} shapes, {len(fonts)} fonts")


if __name__ == "__main__":
    main()
