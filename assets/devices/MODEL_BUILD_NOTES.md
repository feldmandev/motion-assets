# Procedural model recipes

The neighboring Blender builders and per-profile sources/accuracy notes preserve the original procedural recipes, including the Samsung legacy slab hooks in `make_samsung_legacy_profiles.py`.

To export an existing profile with Blender 5.2.2:

```sh
blender --background --python-exit-code 1 --python assets/devices/build.py -- assets/devices/profiles/galaxy-tab-s7.json
```

The optional review tools require Pillow. Geometry uses Shapely in Blender. External SDK skin traces, downloaded vendor photos, local drawing-generator inputs, and the separately reviewed Pixel 10 Pro Blender source are not distributed. Some specialized/profile-regeneration paths require those inputs; use the supplied profiles and verified release payloads for the complete catalog. Local paths in source/reference JSON have been omitted; source URLs and accuracy labels remain.

The published generic GLBs are regenerated independently with `tools/generate_generic_models.py`, without private/reference images. Downloaded research photos, rendered contact sheets, `.blend` caches and the large standalone review page are intentionally excluded.
