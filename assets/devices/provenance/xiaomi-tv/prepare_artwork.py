"""Normalize the user-supplied logos for consistent vector import."""
from pathlib import Path
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parent / 'logo-sources'
ET.register_namespace('', 'http://www.w3.org/2000/svg')
for source, output, color in (
    ('prime-original.svg', 'prime-monochrome.svg', '#222222'),
    ('netflix-original.svg', 'netflix.svg', '#d81f26'),
):
    tree = ET.parse(root / source)
    for node in tree.getroot().iter():
        node.attrib.pop('style', None)
        node.attrib.pop('class', None)
        if node.tag.rsplit('}', 1)[-1] in ('path', 'polygon', 'rect', 'circle', 'ellipse'):
            node.set('fill', color)
    tree.write(root / output, encoding='unicode')

(root / 'sources.txt').write_text(
    'Prime Video, supplied by the user; all shapes converted to one dark color:\n'
    'https://upload.wikimedia.org/wikipedia/commons/1/11/Amazon_Prime_Video_logo.svg\n'
    'Netflix, supplied by the user:\n'
    'https://upload.wikimedia.org/wikipedia/commons/0/08/Netflix_2015_logo.svg\n'
    'YouTube official vector artwork, converted from the supplied AI/PDF:\n'
    'https://brand.youtube/youtube-logo\n'
    'https://www.gstatic.com/marketing-cms/52/7d/637fef5a4788a97747e6feabc4aa/youtube-logo.zip\n',
    encoding='utf-8',
)
