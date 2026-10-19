"""Sync a pinned Motion asset release into existing Android, Qt or Web paths.

Copy this standalone script to a consumer's scripts/update_motion_assets.py.
Normal runs use that consumer's lock; --update explicitly selects the latest
published release. --source supports an offline, verified local checkout.
"""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

REPOSITORY = "feldmandev/motion-assets"


def read_url(url):
    with urlopen(Request(quote(url, safe=":/%?=&"), headers={"User-Agent": "motion-assets-consumer"}), timeout=120) as response:
        return response.read()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--target", choices=["android", "qt", "web"])
    parser.add_argument("--version", help="Immutable release tag, for example v0.1.0")
    parser.add_argument("--update", action="store_true")
    parser.add_argument("--source", type=Path, help="Read files from this local checkout instead of GitHub")
    args = parser.parse_args()
    root = args.root.resolve()
    lock_file = root / "motion-assets.lock.json"
    previous = json.loads(lock_file.read_text()) if lock_file.exists() else {}
    target = args.target or previous.get("target")
    if not target:
        parser.error("A first sync requires --target")
    version = args.version or previous.get("version")
    if args.update:
        version = json.loads(read_url(f"https://api.github.com/repos/{REPOSITORY}/releases/latest"))["tag_name"]
    if args.source:
        manifest_data = (args.source / "manifest.json").read_bytes()
        version = "v" + json.loads(manifest_data)["version"]
    else:
        if not version or not version.startswith("v") or any(c not in "v0123456789.-" for c in version):
            parser.error("Use a pinned release version")
        manifest_data = read_url(f"https://raw.githubusercontent.com/{REPOSITORY}/{version}/manifest.json")
    digest = hashlib.sha256(manifest_data).hexdigest()
    if not args.update and not args.version and not args.source and previous.get("manifestSha256") != digest:
        raise ValueError("Release manifest changed; refusing an unreviewed replacement")
    manifest = json.loads(manifest_data)
    if "v" + manifest["version"] != version:
        raise ValueError("Version/tag mismatch")
    aliases = {
        "android": {
            "assets/fonts/FeldmanFont.ttf": "motion/src/main/res/font/feldman_font.ttf",
            "assets/symbols/material_symbols_rounded.ttf": "motion/src/main/res/font/material_symbols_rounded.ttf",
            "integrations/android/MotionSymbols.kt": "motion/src/main/java/com/feldman/motion/symbols/MotionSymbols.kt",
            "integrations/android/MotionIcons.kt": "motion/src/main/java/com/feldman/motion/symbols/MotionIcons.kt",
        },
        "qt": {
            "assets/fonts/FeldmanFont.ttf": "src/fonts/FeldmanFont.ttf",
            "assets/symbols/material_symbols_rounded.ttf": "src/fonts/material_symbols_rounded.ttf",
        },
        "web": {
            "assets/fonts/FeldmanFont.woff2": "src/fonts/feldman_font.woff2",
            "assets/symbols/material_symbols_rounded.woff2": "src/fonts/material_symbols_rounded.woff2",
        },
    }[target]
    base = {"android": "motion/src/main/assets/motion", "qt": "src/assets/motion", "web": "src/assets/motion"}[target]
    for name in manifest["files"]:
        if name.startswith("assets/shapes/"):
            aliases[name] = base + "/" + name
        if name == "assets/symbols/catalog.json":
            aliases[name] = base + "/" + name
        if name.startswith("LICENSES/") or name in {"assets/fonts/OFL.txt", "LICENSE", "ATTRIBUTION.md"}:
            aliases[name] = base + "/licenses/" + name.rsplit("/", 1)[-1]
    # Validate every selected payload before changing any consumer file.
    prepared = []
    for source, destination in sorted(aliases.items()):
        entry = manifest["files"][source]
        data = (args.source / source).read_bytes() if args.source else read_url(f"https://raw.githubusercontent.com/{REPOSITORY}/{version}/{source}")
        if hashlib.sha256(data).hexdigest() != entry["sha256"] or len(data) != entry["bytes"]:
            raise ValueError(f"Asset checksum mismatch: {source}")
        path = (root / destination).resolve()
        if not path.is_relative_to(root):
            raise ValueError("Unsafe consumer path")
        prepared.append((path, data))
    for path, data in prepared:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    lock = {"repository": REPOSITORY, "version": version, "manifestSha256": digest, "target": target,
        "files": {destination: {"source": source, "sha256": manifest["files"][source]["sha256"]} for source, destination in sorted(aliases.items())}}
    lock_file.write_text(json.dumps(lock, indent=2) + "\n")
    print(f"Synced {len(prepared)} verified {target} assets from {version}")


if __name__ == "__main__":
    main()
