"""Vector counterparts to the reference-matched Blender geometry."""
from pathlib import Path

OUT = Path(__file__).resolve().parent
import json
import xml.etree.ElementTree as ET
ET.register_namespace('', 'http://www.w3.org/2000/svg')
symbols = json.loads((OUT / 'symbol-paths.json').read_text())
labels = json.loads((OUT / 'label-paths.json').read_text())
remote_svg = '<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">'
remote_svg += '<defs><linearGradient id="body"><stop stop-color="#101519"/><stop offset=".18" stop-color="#252d33"/><stop offset=".48" stop-color="#4b5359"/><stop offset=".68" stop-color="#3a434a"/><stop offset="1" stop-color="#10161b"/></linearGradient><radialGradient id="key"><stop stop-color="#242a30"/><stop offset="1" stop-color="#14191f"/></radialGradient></defs>'
remote_svg += '<g transform="translate(54 54) scale(.46 -.46)"><rect x="-17.75" y="-87" width="35.5" height="174" rx="5.5" fill="url(#body)"/>'
for x, y, r in ((0,76,3.6),(0,64,3.6),(-9.8,15.2,3.5),(0,15.2,3.5),(9.8,15.2,3.5)):
    remote_svg += f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#key)" stroke="#0e1318" stroke-width=".22"/>'
remote_svg += '<circle cy="40.3" r="13.9" fill="#101419"/><circle cy="40.3" r="13.4" fill="url(#key)"/><circle cy="40.3" r="6.4" fill="#0d1115"/><circle cy="40.3" r="5.9" fill="#242a30"/>'
for key, x, y, size, color in (('power',0,76,4.6,'#cb806b'),('back',0,15.2,4.1,'#c9ced0'),('home',9.8,15.2,4.1,'#c9ced0')):
    remote_svg += f'<path d="{symbols[key]}" transform="translate({x} {y}) scale({size} {-size})" fill="{color}"/>'
remote_svg += '<rect x="-.9" y="63.2" width="1.8" height="3.2" rx=".85" fill="#3785c6"/><path d="M-2.1 64A2.1 2.1 0 0 1 2.1 64M0 61.9V61.2" fill="none" stroke="#cb806b" stroke-width=".86" stroke-linecap="round"/>'
for x in (-14.75,1.05):
    for y in (.25,-10.25):
        remote_svg += f'<rect x="{x}" y="{y}" width="13.7" height="6.5" rx="2.6" fill="#e1e4e2"/>'
for key, x, y, color in (('apps',4.8,-7,'#424b50'),('tvbrand',-9.8,16,'#c9ced0'),('tvplus',-9.8,14.1,'#c9ced0'),('brand',0,-74.4,'#11181c')):
    remote_svg += f'<path d="{labels[key]}" transform="translate({x} {y}) scale(1 -1)" fill="{color}" stroke="{color}" stroke-width=".08" stroke-linejoin="round"/>'
for filename, x, y in (('netflix.svg', -7.9, 3.5), ('prime-monochrome.svg', 7.9, 3.5), ('youtube-official.svg', -7.9, -7)):
    artwork_root = ET.parse(OUT / 'logo-sources' / filename).getroot()
    box = [float(v) for v in artwork_root.get('viewBox').split()]
    width = 12.5
    height = width * box[3] / box[2]
    artwork_root.set('x', str(-width/2))
    artwork_root.set('y', str(-height/2))
    artwork_root.set('width', str(width))
    artwork_root.set('height', str(height))
    remote_svg += f'<g transform="translate({x} {y}) scale(1 -1)">' + ET.tostring(artwork_root, encoding='unicode') + '</g>'

for x in (9.8,11,12.2,13.4):
    for y in (-8.2,-7,-5.8):
        remote_svg += f'<rect x="{x-.45}" y="{y-.45}" width=".9" height=".9" rx=".1" fill="#5e676d"/>'
remote_svg += '<rect x="-3.5" y="-36" width="7" height="21.2" rx="3.4" fill="url(#key)" stroke="#10151a" stroke-width=".22"/>'
for key, y in (('add', -20), ('remove', -30.9)):
    remote_svg += f'<path d="{symbols[key]}" transform="translate(0 {y}) scale(3.6 -3.6)" fill="#c9ced0"/>'
remote_svg += '</g></svg>'
(OUT / 'xiaomi-tv-remote-icon.svg').write_text(remote_svg, encoding='utf-8')

stick_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108">
<defs><linearGradient id="matte"><stop stop-color="#111518"/><stop offset=".28" stop-color="#303438"/><stop offset=".65" stop-color="#353a3e"/><stop offset="1" stop-color="#101417"/></linearGradient><linearGradient id="gloss"><stop stop-color="#040607"/><stop offset=".17" stop-color="#080c0e"/><stop offset=".24" stop-color="#3c4449"/><stop offset=".30" stop-color="#11171a"/><stop offset=".65" stop-color="#040608"/><stop offset="1" stop-color="#1e2429"/></linearGradient><linearGradient id="metal"><stop stop-color="#838a8e"/><stop offset=".25" stop-color="#e0e3e4"/><stop offset="1" stop-color="#bbc1c5"/></linearGradient><clipPath id="body"><rect x="44.5" y="27" width="19" height="58.2" rx="7"/></clipPath></defs>
<rect x="49.6" y="18.1" width="8.8" height="10.5" rx=".6" fill="url(#metal)"/>
<rect x="44.5" y="27" width="19" height="58.2" rx="7" fill="url(#matte)"/>
<g clip-path="url(#body)"><rect x="44.5" y="63.9" width="19" height="21.3" fill="url(#gloss)"/><path d="M44.5 63.9H63.5" stroke="#080c10" stroke-width=".25"/></g>
<text x="54" y="48.5" transform="rotate(90 54 48.5)" text-anchor="middle" dominant-baseline="central" font-family="Arial,sans-serif" font-weight="600" font-size="5.3" fill="#757c80">xiaomi</text>
<rect x="53.7" y="77.4" width=".6" height="2" rx=".25" fill="#f7fcff"/>
</svg>'''
(OUT / 'xiaomi-tv-stick-icon.svg').write_text(stick_svg, encoding='utf-8')

connected_svg = '''<svg xmlns="http://www.w3.org/2000/svg" width="108" height="108" viewBox="0 0 108 108"><defs><linearGradient id="screen" x2="1" y2="1"><stop stop-color="#142752"/><stop offset=".45" stop-color="#5c5895"/><stop offset=".72" stop-color="#438d9c"/><stop offset="1" stop-color="#92c5c3"/></linearGradient><linearGradient id="stick"><stop stop-color="#31383f"/><stop offset="1" stop-color="#0c1117"/></linearGradient></defs><rect x="17" y="61.4" width="13" height="4.2" rx="1.7" fill="url(#stick)"/><rect x="28" y="62" width="3" height="3" fill="#a3adb5"/><rect x="28" y="34" width="65" height="36.5625" rx="1.5" fill="#3b4249"/><rect x="28.5" y="34.5" width="64" height="35.5625" rx="1" fill="url(#screen)"/><rect x="60" y="70.75" width="1" height=".35" fill="#c8d8de"/></svg>'''
(OUT / 'xiaomi-tv-connected-icon.svg').write_text(connected_svg, encoding='utf-8')
