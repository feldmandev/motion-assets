"""Logo-only Samsung tablet placement postpass; preserve camera/body and mono artwork."""
import hashlib
import json
import re
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
import generate_brand_svgs as brands
paths=re.compile(r'<path\b[^>]*?/?>')
changes=[]
for path in (ROOT/'device_icons_svg/samsung/tablets').glob('*.svg'):
 if 'monochrome' in path.stem:continue
 model=next((k for k in sorted(brands.TABLET_WORDMARKS,key=len,reverse=True) if path.stem.startswith('ic_'+k+'_')),None)
 if model is None:continue
 g=brands.TABLETS[model];a=g['aspect'];BW,BH=(46,46/a) if a>=1 else (46*a,46);X0,Y0=54-BW/2,54-BH/2
 before=path.read_text();old=paths.findall(before)[-1];color=re.search(r'fill="([^"]+)"',old)[1]
 new=brands.tablet_wordmark(g['wm_position'],X0,Y0,BW,BH,color);after=before.replace(old,new,1)
 assert before.replace(old,'',1)==after.replace(new,'',1)
 if after!=before:path.write_text(after,encoding='utf-8')
 changes.append({'model':model,'path':path.relative_to(ROOT).as_posix(),'logo_fill':color,'reference_position':g['wm_position'],'non_logo_sha256':hashlib.sha256(before.replace(old,'',1).encode()).hexdigest()})
(ROOT/'tmp/ref5/tablet-logo-placement-changes.json').write_text(json.dumps(changes,indent=2))
print('Verified',len(changes),'colored tablet logo variants; body/camera bytes preserved; monochrome untouched')
