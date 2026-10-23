"""Share existing icon logo tones with matching procedural model finishes."""
import json
import re
from pathlib import Path
BASE=Path(__file__).resolve().parent
DOCUMENTS=BASE.parents[3]/'documents'
ALIASES={'blk':['obsidian','black','charcoal'],'beg':['porcelain','beige','cream'],'blu':['bay','blue','frost'],'blue':['bay','blue','frost','indigo','isai blue'],'grn':['wintergreen','lemongrass','aloe','green','sage','pistachio','olive','jade'],'gry':['hazel','gray','grey','fog','moonstone'],'pnk':['peony','rose','pink','coral','hibiscus','canyon','berry'],'ppl':['iris','violet','purple','lavender'],'slv':['silver']}
def key(s):return re.sub('[^a-z0-9]','',s.lower())
def model_id(s):
 special={'pixel_fold':'pixel-fold','pixel_9_fold':'pixel-9-pro-fold','pixel_10_fold':'pixel-10-pro-fold','pixel_11_fold':'pixel-11-pro-fold','apple_iphone_duo':'iphone-duo'}
 if s in special:return special[s]
 if s.startswith('apple_iphone_'):return 'iphone-'+s.removeprefix('apple_iphone_').replace('_','-')
 if s.startswith('pixel_'):return s.replace('_a','a').replace('_','-')
 return s.replace('_','-')
def main():
 source=json.loads((DOCUMENTS/'tmp/ref5/logo-colors.json').read_text())['models'];groups={model_id(k):v for k,v in source.items()};palettes={};unmatched=[]
 for path in sorted((BASE/'profiles').glob('*.json')):
  p=json.loads(path.read_text());pid=re.sub('-(folded|unfolded)$','',p['id']);icons=groups.get(pid)
  if not icons or p.get('hinge_logo'):continue
  finishes=list(p['finishes']);colors={}
  for color,fill in icons.items():
   exact=[f for f in finishes if key(f)==key(color)]
   aliases=[f for f in finishes if key(f) in {key(v) for v in ALIASES.get(color,[])}]
   match=exact or aliases
   if len(match)==1:colors[match[0]]=fill
  if colors:palettes[pid]=colors
  for f in finishes:
   if f not in colors:unmatched.append([p['id'],f])
 out={'source':'Documents existing colored icon logo fills; inherited/photo-estimated tones, not measured physical materials','palettes':palettes,'unmatched_kept_profile_tone':unmatched}
 (BASE/'research/device-logo-palettes.json').write_text(json.dumps(out,indent=2)+'\n');print(len(palettes),'families;',sum(map(len,palettes.values())),'finish logo colors;',len(unmatched),'unmatched states/finishes keep their profile tones')
if __name__=='__main__':main()
