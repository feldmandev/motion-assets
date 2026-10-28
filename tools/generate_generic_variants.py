"""Generate the shared shared-palette finishes for every generic device.

Scoped and fast: recolors the authored graphite artwork, renders previews, and
writes catalog variants plus 3D finishes. No GLB geometry is regenerated; the
finishes recolor existing named materials at runtime. Graphite files are kept
byte-for-byte. --drafts also writes the review-only peripheral drafts.
"""
import argparse
import base64
import gzip
import hashlib
import io
import json
import re

import cairosvg
from PIL import Image

from catalog import ROOT, write_json
from generic_palettes import BASE, PALETTES, generic_materials, map_hex, model_finishes, recolor_svg

DEVICES = ROOT / "assets/devices"
# Body tones only; screen glass, lens wells, glints and flashes stay fixed.
GENERIC = {
    "generic_phone": {"base": "graphite", "folder": "phones", "model": "generic-phone",
        "tones": ["#d3dee7", "#adbfce", "#859caf", "#5f768e", "#eef3f5", "#d5e3ec", "#53677b"]},
    "generic_tablet": {"base": "graphite", "folder": "tablets", "model": "generic-tablet",
        "tones": ["#c6ced5", "#a9b5c0", "#75838f", "#53677b"]},
    "generic_pc": {"base": "graphite", "folder": "pcs", "model": "generic-pc",
        "tones": ["#e0e7ee", "#c2ced9", "#9cabbc", "#63758a", "#74869b", "#5e7186"]},
    # The Googlebook's gray is its existing Titanium Silver; the Google bar stays.
    "generic_googlebook": {"base": "titanium_silver", "folder": "laptops", "model": "generic-googlebook",
        "tones": ["#e4e8ec", "#d3d8dd", "#81858b", "#a9adb1"]},
}
DRAFTS = DEVICES / "drafts/peripherals"


def render(svg, size):
    """Rasterize, crop to ink, and fit into size (w, h) like the existing previews."""
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=1200)
    image = Image.open(io.BytesIO(png)).convert("RGBA")
    return image.crop(image.getbbox())


def preview(svg):
    image = render(svg, None)
    scale = min(120 / image.width, 170 / image.height)
    image = image.resize((round(image.width * scale), round(image.height * scale)), Image.LANCZOS)
    canvas = Image.new("RGBA", (140, 180))
    canvas.alpha_composite(image, ((140 - image.width) // 2, (180 - image.height) // 2))
    return canvas


def save_png(image, path):
    buffer = io.BytesIO()
    image.save(buffer, "PNG", optimize=True)
    path.write_bytes(buffer.getvalue())


def devices(manifest):
    catalog = json.loads((DEVICES / "catalog.json").read_text(encoding="utf-8"))
    touched = [DEVICES / "catalog.json", DEVICES / "generic_palettes.json"]
    for entry in catalog:
        spec = GENERIC.get(entry["model"])
        if not spec:
            continue
        base = next(v for v in entry["variants"] if v["color"] == spec["base"])
        source = (ROOT / base["svg"]).read_text(encoding="utf-8")
        icon_png = ROOT / base["svg"].replace(".svg", ".png")
        variants = [base]
        for target in PALETTES[1:]:
            stem = f"{entry['model']}_{target['id']}"
            svg = recolor_svg(source, spec["tones"], target)
            svg_path = DEVICES / "icons/generic" / spec["folder"] / f"ic_{stem}_icon.svg"
            svg_path.write_text(svg, encoding="utf-8", newline="\n")
            preview_path = DEVICES / "previews" / f"{stem}.png"
            save_png(preview(svg), preview_path)
            touched += [svg_path, preview_path]
            if icon_png.exists():
                size = Image.open(icon_png).size
                png_path = svg_path.with_suffix(".png")
                save_png(render(svg, None).resize(size, Image.LANCZOS), png_path)
                touched.append(png_path)
            variants.append({"color": target["id"], "sourceSvg": svg,
                "svg": svg_path.relative_to(ROOT).as_posix(), "preview": preview_path.relative_to(ROOT).as_posix()})
        entry["variants"] = variants
        model_path = DEVICES / "models" / f"{spec['model']}.json"
        if entry["model"] == "generic_googlebook":
            # Own model metadata on the shared GLB, so the branded Googlebook Emulator
            # keeps only its official finishes.
            model = json.loads((DEVICES / "models/googlebook-emulator.json").read_text(encoding="utf-8"))
            model.update(id=spec["model"], name="Generic Googlebook")
            silver = next(f for f in model["finishes"] if f["name"] == "Titanium Silver")
            finishes = [dict(silver, palette=BASE["id"])]
            for target in PALETTES[1:]:
                materials = {}
                for role, settings in silver["materials"].items():
                    settings = dict(settings)
                    if role != "keycap":
                        tone = "#" + "".join(f"{round(c * 255):02x}" for c in settings["rgb"])
                        settings["rgb"] = [round(int(map_hex(tone, target)[i:i + 2], 16) / 255, 4) for i in (1, 3, 5)]
                    materials[role] = settings
                finishes.append({"name": target["name"], "palette": target["id"], "materials": materials})
            model["finishes"] = finishes
            entry["model3d"]["states"]["default"] = spec["model"]
        else:
            model = json.loads(model_path.read_text(encoding="utf-8"))
            model["slots"], model["finishes"] = model_finishes(generic_materials(entry["kind"]))
        write_json(model_path, model)
        touched.append(model_path)
    write_json(DEVICES / "catalog.json", catalog)
    for path in touched:
        data = path.read_bytes()
        manifest["files"][path.relative_to(ROOT).as_posix()] = {"sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
    write_json(ROOT / "manifest.json", manifest)
    print(f"Generic variants: {len(GENERIC)} devices x {len(PALETTES)} palettes; {len(touched)} files")
    return catalog


# Review-only peripheral drafts. The speaker follows the reference compact JBL
# box; the other five keep their v2 silhouettes and recolor body/pad tones.
SPEAKER = """<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108" fill="none">
<defs><linearGradient id="spk-fabric" gradientUnits="userSpaceOnUse" x1="54" y1="33" x2="54" y2="81"><stop stop-color="{highlight}"/><stop offset=".22" stop-color="{light}"/><stop offset=".62" stop-color="{mid}"/><stop offset="1" stop-color="{dark}"/></linearGradient><linearGradient id="spk-cap" gradientUnits="userSpaceOnUse" x1="54" y1="29" x2="54" y2="85"><stop stop-color="{housing}"/><stop offset=".5" stop-color="{deep}"/><stop offset="1" stop-color="{housing}"/></linearGradient><radialGradient id="spk-light" gradientUnits="userSpaceOnUse" cx="34" cy="38" r="44"><stop stop-color="#ffffff" stop-opacity=".32"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient></defs>
<desc>Generic compact speaker after the JBL Go reference: rounded fabric-wrapped box, dark rubber top and bottom caps with top buttons, cord loop at the upper right, broad outlined JBL front mark and slim light accents.</desc>
<path d="M82 42C88 38 91 29 95 23c2.4-3.6 7.6-1.8 6 2.6C98.6 32 92.5 41 86 46" stroke="{deep}" stroke-width="3.4" stroke-linecap="round"/>
<rect x="31" y="29.5" width="46" height="8" rx="3.2" fill="url(#spk-cap)"/><rect x="31" y="76.5" width="46" height="8" rx="3.2" fill="url(#spk-cap)"/>
<g stroke="{highlight}" stroke-width="1.1" stroke-linecap="round" stroke-opacity=".85"><path d="M38.5 31.6h4M65.5 31.6h4M67.5 29.6v4"/></g><path d="M52.4 30v3.4l3.1-1.7z" fill="{highlight}" fill-opacity=".85"/>
<rect x="20" y="33" width="68" height="48" rx="14" fill="url(#spk-fabric)"/>
<rect x="20" y="33" width="68" height="48" rx="14" fill="url(#spk-light)"/>
<rect x="33" y="33" width="42" height="4.6" rx="2.3" fill="url(#spk-cap)"/><rect x="33" y="76.4" width="42" height="4.6" rx="2.3" fill="url(#spk-cap)"/>
<rect x="37" y="38.8" width="34" height="1.5" rx=".75" fill="#f6f8fb" fill-opacity=".92"/><rect x="37" y="73.7" width="34" height="1.5" rx=".75" fill="#f6f8fb" fill-opacity=".92"/>
<g transform="translate(54 57) scale(1.14) translate(-52.5 -57.5)" stroke-linecap="round" stroke-linejoin="round">
<g stroke="{highlight}" stroke-width="4.4"><path d="M33.6 48.2h5.8l-2.9 6.2zM44.5 48.5V64a3.5 3.5 0 01-3.5 3.5h-4.5M50.5 48.5v18h5.1a4.5 4.5 0 000-9h-5.1h4.7a4.5 4.5 0 000-9zM64 48.5v18h7.5v-3"/><circle cx="36.5" cy="58" r="1.7"/></g>
<g stroke="{deep}" stroke-width="2.4"><path d="M33.6 48.2h5.8l-2.9 6.2zM44.5 48.5V64a3.5 3.5 0 01-3.5 3.5h-4.5M50.5 48.5v18h5.1a4.5 4.5 0 000-9h-5.1h4.7a4.5 4.5 0 000-9zM64 48.5v18h7.5v-3"/><circle cx="36.5" cy="58" r="1.7"/></g>
</g>
</svg>
"""
BODY = ["#e0e7ee", "#c2ced9", "#9cabbc", "#63758a", "#53677b", "#344b63"]
GLASS = ["#7897ae", "#4c6d89", "#304c68", "#1b3049"]
# (label, v2 file, recolored tones, pad/tip tones forced onto the ramp)
PERIPHERALS = [
    ("Speaker", None, [], []),
    ("Car", "generic-car.svg", BODY[:4], []),
    ("Over-ear", "headphones-over-ear.svg", BODY, GLASS),
    ("On-ear", "headphones-on-ear.svg", BODY, GLASS),
    ("In-ear", "headphones-in-ear.svg", BODY, GLASS),
    ("Watch", "generic-watch.svg", BODY, []),
]


def peripheral(label, source, tones, pads, target):
    if source is None:
        return SPEAKER.format(**target["stops"])
    svg = (DRAFTS / source).read_text(encoding="utf-8")
    if label == "Car":
        # Tires stay neutral rubber; only the body and hubs take the finish.
        head, tire, tail = re.split(r'(<linearGradient id="car-tire".*?</linearGradient>)', svg, flags=re.S)
        return recolor_svg(head, tones, target) + tire + recolor_svg(tail, tones, target)
    return recolor_svg(recolor_svg(svg, tones, target), pads, target, force=True)


def unique_ids(svg, suffix):
    ids = re.findall(r'\bid="([^"]+)"', svg)
    for ident in ids:
        svg = re.sub(rf'(id="|url\(#|href="#){re.escape(ident)}(["\)])', rf"\g<1>{ident}-{suffix}\2", svg)
    return svg


def drafts(catalog):
    out = DRAFTS / "variants"
    out.mkdir(exist_ok=True)
    old = DRAFTS / "preview.html"
    if old.exists() and not (DRAFTS / "preview-r2.html").exists():
        old.rename(DRAFTS / "preview-r2.html")
    rows = []
    phone = next(d for d in catalog if d["model"] == "generic_phone")
    pc = next(d for d in catalog if d["model"] == "generic_pc")
    for label, source, tones, pads in PERIPHERALS:
        cells = []
        for target in PALETTES:
            svg = peripheral(label, source, tones, pads, target)
            name = (source or "generic-speaker.svg").replace(".svg", f"_{target['id']}.svg")
            (out / name).write_text(svg, encoding="utf-8", newline="\n")
            cells.append(svg)
        rows.append((label, cells))
    for label, device in [("Generic phone", phone), ("Generic PC", pc)]:
        rows.append((label, [v["sourceSvg"] for v in device["variants"]]))
    head = "".join(f'<div class="h"><span class="sw" style="background:{p["stops"]["mid"]}"></span>{p["name"]}<code>{p["id"]}</code></div>' for p in PALETTES)
    body = []
    for r, (label, cells) in enumerate(rows):
        body.append(f'<div class="t">{label}</div>')
        for c, svg in enumerate(cells):
            svg = unique_ids(re.sub(r"<desc>.*?</desc>\n?", "", svg, flags=re.S), f"{r}-{c}")
            svg = re.sub(r'<svg ([^>]*?)width="[^"]*" height="[^"]*"', r'<svg class="big" \1', svg, count=1)
            # The 40px copy reuses the same artwork instead of duplicating it.
            art = f"art-{r}-{c}"
            fill = ' fill="none"' if re.match(r'<svg [^>]*fill="none"', svg) else ""
            svg = re.sub(r"(<svg [^>]*>)(.*)</svg>", rf'\1<g id="{art}"{fill}>\2</g></svg>', svg, count=1, flags=re.S)
            box = re.search(r'viewBox="([^"]+)"', svg)[1]
            small = f'<svg class="small" viewBox="{box}"><use href="#{art}"/></svg>'
            svg = re.sub(r">\s+<", "><", svg)
            body.append(f'<div class="c">{svg}{small}</div>')
    grid = "<div></div>" + head + "".join(body)
    packed = base64.b64encode(gzip.compress(grid.encode(), compresslevel=9, mtime=0)).decode()
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Generic shared-palette review</title><style>
html,body{{margin:0;padding:0;background:transparent;color:var(--foreground,inherit);font-family:var(--font-sans,system-ui,sans-serif)}}
.g{{display:grid;grid-template-columns:minmax(52px,auto) repeat({len(PALETTES)},minmax(0,1fr));gap:4px;align-items:center}}
.h{{font-size:11px;font-weight:600;display:flex;flex-direction:column;align-items:center;gap:2px;text-align:center}}
.h code{{font-family:var(--font-mono,monospace);font-size:9px;font-weight:400;opacity:.6}}
.sw{{width:14px;height:14px;border-radius:50%;border:1px solid color-mix(in srgb,currentColor 25%,transparent)}}
.t{{font-size:11px;opacity:.75}}
.c{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:4px 0;border-radius:calc(var(--radius,10px) * .8);background:color-mix(in srgb,currentColor 5%,transparent);min-width:0}}
.c svg{{display:block}}.big{{width:clamp(30px,7vw,64px);height:clamp(30px,7vw,64px)}}.small{{width:40px;height:40px}}
@media (max-width:560px){{.small{{display:none}}}}
</style></head><body><div class="g" id="g"></div><script>
// The inline SVG grid is stored gzip-compressed to keep this self-contained page small.
const z=Uint8Array.from(atob("{packed}"),c=>c.charCodeAt(0));
new Response(new Blob([z]).stream().pipeThrough(new DecompressionStream("gzip"))).text().then(t=>document.getElementById("g").innerHTML=t);
</script></body></html>
"""
    (DRAFTS / "preview.html").write_text(html, encoding="utf-8", newline="\n")
    print(f"Drafts: {len(PERIPHERALS)} peripherals x {len(PALETTES)} palettes; preview {DRAFTS / 'preview.html'}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--drafts", action="store_true", help="Also write review-only peripheral drafts")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    catalog = devices(manifest)
    if args.drafts:
        drafts(catalog)


if __name__ == "__main__":
    main()
