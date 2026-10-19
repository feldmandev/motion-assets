"""Fetch optional model payloads from their pinned release and verify each file."""
import argparse
import hashlib
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a previously downloaded release archive")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "assets/devices/models-manifest.json").read_text())
    if all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == entry["sha256"] for name, entry in manifest["files"].items()):
        print("All model payloads already match the manifest")
        return
    if args.archive:
        data = args.archive.read_bytes()
    else:
        url = f"https://github.com/feldmandev/motion-assets/releases/download/{manifest['release']}/{manifest['archive']}"
        with urlopen(Request(url, headers={"User-Agent": "motion-assets"}), timeout=180) as response:
            data = response.read()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name, entry in manifest["files"].items():
            target = (ROOT / name).resolve()
            if not target.is_relative_to(ROOT / "assets/devices/models"):
                raise ValueError("Unsafe model path")
            payload = archive.read(name)
            if hashlib.sha256(payload).hexdigest() != entry["sha256"] or len(payload) != entry["bytes"]:
                raise ValueError(f"Model integrity check failed: {name}")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    print(f"Verified {len(manifest['files'])} model payloads")


if __name__ == "__main__":
    main()
