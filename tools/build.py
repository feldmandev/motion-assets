"""Create independent, versioned module archives and the gallery site."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def archive(path, files, base=ROOT):
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as output:
        for file in sorted(files):
            info = zipfile.ZipInfo(file.relative_to(base).as_posix(), (2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            output.writestr(info, file.read_bytes())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", action="store_true", help="Include downloaded/generated model payloads in the gallery")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text())
    out = ROOT / "build/dist"
    out.mkdir(parents=True, exist_ok=True)
    notices = [ROOT / "LICENSE", ROOT / "ATTRIBUTION.md", ROOT / "manifest.json", *[p for p in (ROOT / "LICENSES").rglob("*") if p.is_file()]]
    for module in manifest["modules"]:
        files = [ROOT / name for name in manifest["files"] if name.startswith(f"assets/{module}/") or (module == "symbols" and name.startswith("integrations/"))]
        archive(out / f"motion-assets-{module}-{manifest['version']}.zip", set(files + notices))
    models = [p for p in (ROOT / "assets/devices/models").glob("*.glb.gz")]
    if models:
        archive(out / f"motion-assets-models-{manifest['version']}.zip", models)
    site = ROOT / "build/site"
    if site.exists():
        # Fixed build output only; never a supplied or computed source directory.
        shutil.rmtree(site)
    shutil.copytree(ROOT / "gallery", site)
    for name in manifest["files"]:
        if name.startswith("assets/"):
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
    if args.models:
        model_manifest = json.loads((ROOT / "assets/devices/models-manifest.json").read_text())
        for name, entry in model_manifest["files"].items():
            source = ROOT / name
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Fetch model payloads before building site: {name}")
            target = site / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    shutil.copy2(ROOT / "manifest.json", site / "manifest.json")
    shutil.copy2(ROOT / "ATTRIBUTION.md", site / "ATTRIBUTION.md")
    archive(out / f"motion-assets-gallery-{manifest['version']}.zip", [p for p in site.rglob("*") if p.is_file()], site)
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob("*.zip"))}
    (out / "SHA256SUMS").write_text("".join(f"{digest}  {name}\n" for name, digest in hashes.items()))
    print(f"Built {len(hashes)} archives and build/site; model payloads {'included' if args.models else 'optional'}")


if __name__ == "__main__":
    main()
