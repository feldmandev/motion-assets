# HONOR Magic V3 housing correction ? ready

Owned model key: `PHONES["honor_magic_v3"]`.

Owned output paths (all ready):
- `device_icons_svg/honor/phones/ic_honor_magic_v3_black_icon.svg`
- `device_icons_svg/honor/phones/ic_honor_magic_v3_green_icon.svg`
- `device_icons_svg/honor/phones/ic_honor_magic_v3_reddish_brown_icon.svg`
- `device_icons_svg/honor/phones/ic_honor_magic_v3_monochrome_icon.svg`

Generator changes: only this PHONES entry and the existing v3 housing contour within draw_elements. No framework, body, logo, palette, or other-model changes.

Official sources:
- https://www.honor.com/global/phones/honor-magic-v3/
- https://www-file.honor.com/content/dam/honor/global/products/smartphone/honor-magic-v3/imgs/section-design/img4@2x.webp (straight rear, downloaded as ref-1.webp)
- https://www-file.honor.com/content/dam/honor/global/products/smartphone/honor-magic-v3/imgs/section-design/img3@2x.webp (housing closeup, downloaded as ref-0.webp)

Approximate visual measurements from the straight rear (image pixels, not hardware CAD): body width ~1210 px, metal housing ~800 px; ratio ~0.66. Housing top gap ~130 px/~0.11 body width; center ~0.44 body width below body top. Closeup metal bounding width ~800 px; circular inner glass ~695 px/~0.87 housing diameter. Long flat sides in the old artwork do not match the deeper, softly joined diagonal cuts in the official render.

Fit: body width 27, camera reference scale 30. Housing d=.594 =>17.82/27=.660 body width (old .78*30/27=.867). Housing cy=.396=>11.88/27=.440; top gap=(11.88-8.91)/27=.110. Outer diagonal cut=.29 housing diameter with quadratic rounding at joins (.2 adjacent edge). Circular inner radius=.435 diameter =>glass diameter=.87 housing diameter. Camera contents scaled by ~.76 about the housing center, preserving their arrangement; this is required to fit the smaller housing. No added detail, lens rearrangement, recolor, or logo/body change.

Verification: XML parsed and every local url reference resolves for all four SVGs; resvg rendered each at 108 and 864 pixels with nonempty output. Compared all three color body paths, body gradients, and logos with before snapshots: unchanged. Magic V5/V6 generator output is byte-identical before/after. Mono generated only for this key using tmp/ref5/generate_monochrome.py convert(black_svg), loaded with importlib; helper not edited. Visually inspected contact-verification.png against official rear and every color/mono. No collection/gallery/catalog/preview rebuild; no push.

Review artifacts: contact-verification.png; official-rear-crop.png; official-housing.png; generator-diff.patch. Before snapshots are in this folder. Parent can regenerate only the four thumbnails and include these SVGs in its snapshot.
