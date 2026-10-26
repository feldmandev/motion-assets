# Xiaomi TV Stick, remote and connected-TV study

Three standalone model/icon families accompany the complete 7.5-second animation.
The animation uses the final Seamless geometry morph: 68 remote parts form from a
simplified flat pose during the first 1.15 seconds, followed by the authored camera
rotation and glide toward the connected TV. The gallery offers play, pause, replay
and time scrubbing. Its gradient screen is replaceable illustrative artwork.

The curved remote and stick are photo-derived procedural estimates, not Xiaomi
CAD. The TV is an illustrative assembly, not an identified Xiaomi TV product.
App logos and vendor marks retain their original rights. Material Symbols retain
their Apache-2.0 terms; see the shared Symbols module. No proprietary fonts are
redistributed. The Blender source expects locally installed Arial-family fonts.

The remote's simplified SVG wraps the final GPU-rendered transparent icon so its
first animation pose matches; it is not a newly traced vector illustration.
Stick and TV icons are vector drawings. The full-detail remote remains present in
the standalone GLB and the physical endpoint of the morph.

The original Blender/icon authoring scripts and prepared vector artwork are in
`xiaomi-tv/`; the existing morph postpass is in `xiaomi-tv/continuous/`. The runtime
camera samples, material colors and compressed-model checksum are recorded in
`../animations/xiaomi-tv-transition.json`. Fine dimensions, intake/port shapes and
optical finishes are approximate. Source references are retained in
`xiaomi-tv-sources.json`; publication checks are in `xiaomi-tv-verification.json`.

References:

- https://www.mi.com/global/product/xiaomi-tv-stick-4k/
- https://www.mi.com/us/product/xiaomi-tv-stick-4k/specs/
