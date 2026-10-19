# Motion assets

Shared shapes, device illustrations and screen-mapped 3D models, variable fonts,
and Material Symbols for Motion Android, Qt and Web, Seamless, and Documents.

## Modules

| Module | Contents |
| --- | --- |
| `assets/shapes` | Original and 1024px SVG exports, stable IDs, view boxes and paths. |
| `assets/devices` | Device/finish catalog, SVG icons, PNG previews, frames, model metadata, profiles and provenance. |
| `assets/fonts` | Feldman Font, Google Sans Flex and Fredoka, TTF/WOFF2, axes and OFL notices. |
| `assets/symbols` | Rounded, Outlined and Sharp variable fonts, codepoints and legacy ligature names, pinned to one Google commit. |

`manifest.json` records the version, size and SHA-256 of every distributable file.
Device models are procedural estimates, **not vendor CAD**. Device artwork has
mixed provenance, including vendor extractions; see [ATTRIBUTION.md](ATTRIBUTION.md).
The code license does not relicense vendor artwork or logos.

## Gallery

The unified gallery browses all four modules. Devices retain the existing finish,
rotate, fold/unfold, exact frame and screen-checker controls. Only the selected
model is downloaded and decompressed; filenames include a content hash.

```sh
python -m pip install -r requirements.txt
python tools/validate.py
python tools/fetch_models.py
python tools/build.py --models
python -m http.server 8000 --directory build/site
```

Open `http://localhost:8000`. The gallery uses HTTP so that lazy model downloads
and checksum verification work consistently. Large GLBs live in the pinned
GitHub Release model archive, not in Git history. `fetch_models.py` verifies each
compressed payload against `assets/devices/models-manifest.json`.

## Use in Motion

Each consumer keeps `motion-assets.lock.json` and a copy of
`tools/sync_consumer.py` as `scripts/update_motion_assets.py`:

```sh
python scripts/update_motion_assets.py --target android --version v0.1.0
python scripts/update_motion_assets.py --update
```

Targets are `android`, `qt` and `web`. The updater validates all selected hashes
before writing files. Normal builds use the checked-in, pinned assets and need
no network access. The existing font/resource names and Kotlin APIs remain
unchanged. Shapes are exposed as shared SVG/catalog resources; native platform
rounded-polygon animation code remains native.

The Web package can also consume `@feldmandev/motion-assets` from this Git repo
at a release tag; its package exports expose catalogs and individual files.
Module ZIPs are available in Releases so a font consumer need not fetch 3D models.

For local development, pass `--source ../motion-assets` to the updater. Update
the lock only after validating a new asset release. The reusable consumer
workflow checks for releases and opens an update PR in each consumer repo.

## Material Symbols updates

```sh
python tools/update_symbols.py --latest
python tools/catalog.py
python tools/validate.py
python tools/export_symbol.py home --style rounded --fill 1 --output build/home.svg
```

The scheduled workflow resolves Google's upstream commit first, downloads all
three font/codepoint pairs from that exact commit, retains legacy ligatures,
generates Android names, and validates the result. It opens a PR containing the
new pinned revision and a patch version bump. Merging the PR publishes immutable
module archives; apps update through their own reviewed dependency PRs. No
application silently replaces its fonts while running.

The workflow uses GitHub's built-in token, without saved personal credentials.
Repository policy must allow Actions to create pull requests; otherwise the
update branch is still available and the workflow reports the denied PR action.

## Updating device artwork and models

`tools/import_devices.py --help` imports a finalized catalog/export snapshot.
It keeps `sources[]` and `accuracy{}`, reference JSON and source notes, strips
local reference paths, and excludes downloaded photos and large review renders.
`tools/generate_generic_models.py` builds the three authored generic models and
file-gallery compatibility payloads; install `requirements-models.txt` for it.
`tools/render_gallery.py` refreshes the lightweight device catalog in the viewer.

The Blender recipe files and legacy slab hooks are retained with the device
profiles. External SDK traces, vendor image downloads and the separately reviewed
Pixel 10 Pro source scene are not bundled. Rebuilding from profiles can therefore
require those documented inputs; the shipped model archive is the verified
snapshot, not a promise of byte-identical regeneration on every Blender version.

Always run `tools/catalog.py` then `tools/validate.py` before publication. The
validator checks inventory hashes, SVGs, fonts, catalog links and common private
path/credential patterns. Imports do not copy source-repository Git history.
