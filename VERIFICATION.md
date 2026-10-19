# Initial snapshot verification

Validated on 2026-10-19:

- Inventory/privacy scan: 3,954 files; 382 device families; 35 shapes; 3 fonts.
- All three Symbols styles agree with their codepoint maps and pinned upstream revision; 4,301 names per style.
- Android consumer: `:motion:compileDebugKotlin` passed. Existing library warnings remain.
- Qt consumer: MSVC/Qt 6.8.2 CMake configure and standalone shared-resource compilation passed; a full Qt application build was not needed for this resource-only integration.
- Web consumer: JavaScript syntax and npm package inspection passed; runtime font URLs use WOFF2.
- Browser: 382 cards, 35 shapes, 3 font previews, Symbols search/style rendering; generic-phone GLB loaded and generic-tablet landscape frame loaded. Checked desktop and 390x844 layout without horizontal overflow.
- A deliberately corrupted payload was refused before writing any consumer files.
- Module/gallery archives and model payload SHA-256 checks passed.

Models retain estimated accuracy and source metadata. These checks do not establish vendor-CAD accuracy or grant rights to vendor artwork.
