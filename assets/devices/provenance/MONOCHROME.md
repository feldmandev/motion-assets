# Monochrome device icons

One `ic_<model>_monochrome_icon.svg` is generated for every phone and tablet model, beside its color SVGs in `vendor/phones/` or `vendor/tablets/`.

The monochrome SVG uses a single `currentColor` fill, black by default. Camera glass, lenses, logos and Glyph marks are transparent cutouts; camera housings and back panels use thin cutout contours. It retains the current geometry and provisional source metadata. These are derived versions of the collection artwork, not additional vendor-app extractions.

For an inline SVG, set CSS `color` to tint it. An external `<img>` uses its own default color; to choose a fixed export color, set `color` on the SVG root. The cutouts remain transparent.

Regenerate after changing color artwork: `python tmp/ref5/generate_monochrome.py`, then `python tmp/ref5/build_gallery.py`. The gallery offers ?Monochrome? and a per-phone Monochrome choice. Rebuild the normal model catalog first if phone models were added or removed.

Camera housings use one cutout contour: nested bevel/rim paths are suppressed rather than exported as paired rings. Phone 3 omits its decorative back tiles and spine in monochrome, retaining its camera placement, flash and Glyph Matrix silhouette. Rebuild the standalone page with `python tmp/ref5/build_monochrome_gallery.py`.

Pixel 6-8 bars use full-width cutout lines above and below, separating the top, camera bar and lower body into three parts. Camera and flash cutouts remain inside the bar; the top finish panel stays solid. CMF variants omit decorative panel seams and accessory screws, and retain a single dial contour.

The standalone page includes all 285 phones and 84 tablets, with a device-type dropdown. Run `python tmp/ref5/generate_monochrome.py --tablets` to refresh just tablets.
