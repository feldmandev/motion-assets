"""Apply device-specific rear branding after profile generation (before export)."""
import json
from pathlib import Path
BASE=Path(__file__).resolve().parent
DOCUMENTS=BASE
G=json.loads((DOCUMENTS/'brand_logos.json').read_text())['google_g']
LEGACY={'pixel-4','pixel-4-xl','pixel-4a','pixel-4a-5g','pixel-5','pixel-5a'}

def tone(back):
 # Preserve the chassis hue in the reflective/printed mark, with a moderate
 # contrast step. Physical material samples are not available.
 light=sum(a*b for a,b in zip(back,[.2126,.7152,.0722]))>.45
 return [v*.60 if light else v*.55+.16 for v in back]

def contours(width):
 from svgelements import Path as SvgPath
 path=SvgPath(G['d']);x0,y0,x1,y1=path.bbox();scale=width/(x1-x0);out=[]
 for sub in path.as_subpaths():
  points=[]
  for seg in sub:
   if seg.__class__.__name__ in ('Move','Close'):continue
   n=1 if seg.__class__.__name__=='Line' else 16
   for i in range(n+1):
    v=seg.point(i/n);point=[(v.x-(x0+x1)/2)*scale,(v.y-(y0+y1)/2)*scale]
    if not points or points[-1]!=point:points.append(point)
  if len(points)>2:out.append(points)
 return out

def apply_palette(profile):
 path=BASE/'research/device-logo-palettes.json'
 if not path.exists():return profile
 pid=profile['id'].removesuffix('-folded').removesuffix('-unfolded')
 colors=json.loads(path.read_text())['palettes'].get(pid,{})
 if profile.get('hinge_logo'):return profile
 for finish,fill in colors.items():
  if finish in profile['finishes']:
   profile['finishes'][finish].setdefault('logo',{})['rgb']=[int(fill[i:i+2],16)/255 for i in (1,3,5)]
 if colors and 'materials' in profile and 'logo' in profile['materials']:
  profile['materials']['logo'].update(profile['finishes'][profile['finish']]['logo'])
 return profile


def apply(profile):
 ident=profile['id'];pixel=ident.startswith('pixel-')
 if not pixel:
  if ident.startswith(('galaxy-z-flip','galaxy-z-trifold')):
   from make_samsung_profiles import logo_contours
   axis='Y' if 'trifold' in ident else 'X'
   opened=bool(profile.get('articulation'))
   joint=profile['articulation']['joints'][-1] if opened else profile['static_hinges'][-1]
   shape=logo_contours(20)
   if axis=='Y':shape=[[[-y,x] for x,y in c] for c in shape]
   parent=joint['spine_pivot'] if opened else 'Closed hinge spine.001' if 'trifold' in ident else 'Closed hinge spine'
   profile['hinge_logo']={'kind':'samsung','parent_node':parent,'body_depth_mm':joint.get('spine_depth_mm',joint.get('depth_mm')),'center_mm':[0,0],'surface_offset_mm':.08,'contours_mm':shape}
   for settings in profile['finishes'].values():
    settings['logo']={'rgb':tone(settings['rail']['rgb']),'metal':.45,'rough':.3}
   profile['materials']['logo']=profile['finishes'][profile['finish']]['logo'].copy()
   profile['accuracy']['branding']='Centered SAMSUNG on exterior hinge, parallel to hinge axis; blank rear panels preserved. Approximately20mm word length from official Mobile Press hinge views; placement/material are visual estimates.'
   source='https://api.samsungmobilepress.com/media-assets/'+ident.removesuffix('-unfolded').removesuffix('-folded')
   if source not in profile['sources']:profile['sources'].append(source)
  return apply_palette(profile)
 profile['manufacturer']='Google'
 for finish,settings in profile['finishes'].items():
  settings['logo']={'rgb':tone(settings['back']['rgb']),'metal':.5,'rough':.26}
 if profile.get('asset'):
  profile['material_objects']['logo']='Graphite G inlay'
 else:
  logo={'kind':'google_g','surface_offset_mm':.08,'center_mm':[0,-profile['body_mm']['height']*.30 if ident in LEGACY else 0],'contours_mm':contours(5.5 if ident in LEGACY else 10)}
  if 'panels' in profile:
   next(p for p in profile['panels'] if p['name']=='Camera half')['rear_logo']=logo
  else:profile['rear_logo']=logo
  profile['materials']['logo']=profile['finishes'][profile['finish']]['logo'].copy()
 profile['accuracy']['branding']='Google G contour retained from reference artwork. Legacy Pixel4/4a/5/5a lower rear placement (approximately80%height); Pixel6 onward and folds centered on rear/camera leaf. Size, position and finish-tinted material are photo estimates, not manufacturer CAD.'
 return apply_palette(profile)

if __name__=='__main__':
 for path in sorted((BASE/'profiles').glob('*.json')):
  p=apply(json.loads(path.read_text()));path.write_text(json.dumps(p,indent=2)+'\n')
 print('Updated device branding profiles')
