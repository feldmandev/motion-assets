Apple silicon Mac collection
===========================

Mac mini, Mac Studio, MacBook Air, MacBook Pro and MacBook Neo chip/size families from M1 onward.
The source catalogue contains 50 entries across 12 physical chassis designs, checked
against Apple's model identification and technical specification pages on 2026-10-25.

Canonical artwork: apple/pcs and apple/laptops. Each official finish has an SVG and
PNG, plus a tintable monochrome version. Mac mini and Mac Studio icons show only
the front. MacBook icons show an open display and a
keyboard projected into the deck's perspective. Logos appear on the actual visible
branded surface, rather than being added to the front of a MacBook display.

Procedural source in ../home/home-android/demo-video/device-models:
research/apple-mac-catalog.json, make_mac_profiles.py, apple_mac_geometry.py,
build_macs.py and verify_macs.py. Published body dimensions, finish names, display
resolutions and port types are sourced; curves, optical materials, keyboard details
and exact port positions are visual estimates rather than Apple CAD.

Regenerate artwork and append/update only the Mac catalogue entries:
python tmp/ref5/build_mac_icons.py

Build the local gallery after generating model exports:
python tmp/ref5/build_combined_gallery.py

Primary inventories:
https://support.apple.com/en-us/102852 (Mac mini)
https://support.apple.com/en-us/102231 (Mac Studio)
https://support.apple.com/en-us/102869 (MacBook Air)
https://support.apple.com/en-us/108052 (MacBook Pro)
Per-device technical specifications and reference URLs are retained in the source catalogue.
