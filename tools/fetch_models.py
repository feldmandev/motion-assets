"""Fetch optional model payloads from their pinned release and verify each file."""
import argparse
import gzip
import hashlib
import io
import json
import math
from pathlib import Path
import struct
from urllib.request import Request, urlopen
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def verify_positions(payload, name):
    """Reject invalid vertex data even when a damaged export has a valid checksum."""
    raw = gzip.decompress(payload)
    json_length = struct.unpack_from('<I', raw, 12)[0]
    gltf = json.loads(raw[20:20+json_length])
    binary_start = 28+json_length
    positions = {primitive['attributes']['POSITION']
                 for mesh in gltf.get('meshes', []) for primitive in mesh['primitives']}
    for index in positions:
        accessor = gltf['accessors'][index]
        view = gltf['bufferViews'][accessor['bufferView']]
        start = binary_start+view.get('byteOffset', 0)+accessor.get('byteOffset', 0)
        stride = view.get('byteStride', 12)
        for vertex in range(accessor['count']):
            values = struct.unpack_from('<fff', raw, start+vertex*stride)
            if any(not math.isfinite(value) or value < accessor['min'][axis]-1e-5
                   or value > accessor['max'][axis]+1e-5 for axis, value in enumerate(values)):
                raise ValueError(f"Invalid model vertex bounds: {name}, accessor {index}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, help="Use a previously downloaded release archive")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "assets/devices/models-manifest.json").read_text())
    if all((ROOT / name).is_file() and hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == entry["sha256"] for name, entry in manifest["files"].items()):
        for name in manifest['files']:
            verify_positions((ROOT / name).read_bytes(), name)
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
            verify_positions(payload, name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
    print(f"Verified {len(manifest['files'])} model payloads")


if __name__ == "__main__":
    main()
