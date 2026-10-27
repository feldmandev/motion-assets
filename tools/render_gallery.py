"""Refresh the imported device viewer's lightweight catalog from public assets."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def main():
    catalog = json.loads((ROOT / "assets/devices/catalog.json").read_text(encoding="utf-8"))
    for device in catalog:
        for variant in device["variants"]:
            variant["src"] = variant["preview"]
    page = ROOT / "gallery/devices.html"
    text = page.read_text(encoding="utf-8")
    if '<option value="arduino">Arduino</option>' not in text:
        text = text.replace(
            '<option value="apple">Apple</option><option value="generic">Generic</option>',
            '<option value="apple">Apple</option><option value="arduino">Arduino</option><option value="generic">Generic</option>',
        )
    if '<option value="peripheral">Peripherals</option>' not in text:
        text = text.replace(
            '<option value="remote">Remotes</option></select>',
            '<option value="remote">Remotes</option><option value="peripheral">Peripherals</option></select>',
        )
    if "arduino:'Arduino'" not in text:
        text = text.replace(
            "apple:'Apple',generic:'Generic'",
            "apple:'Apple',arduino:'Arduino',generic:'Generic'",
        )
    start = text.index("const devices=") + len("const devices=")
    _, count = json.JSONDecoder().raw_decode(text[start:])
    text = text[:start] + json.dumps(catalog, separators=(",", ":"), ensure_ascii=False) + text[start + count:]
    page.write_text(text, encoding="utf-8")
    version = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))["version"]
    shell = ROOT / "gallery/index.html"
    shell.write_text(
        re.sub(
            r"(devices\.html|gallery\.js)(?:\?v=[\d.]+)?",
            lambda match: f"{match[1]}?v={version}",
            shell.read_text(encoding="utf-8"),
        ),
        encoding="utf-8",
    )
    print(f"Gallery: {len(catalog)} device families")


if __name__ == "__main__":
    main()
