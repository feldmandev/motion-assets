"""OnePlus profiles from official metric specifications and rear product renders."""
from make_device_branding import apply as apply_branding
import json
import math
import sys
from pathlib import Path
from svgelements import Path as SvgPath
BASE=Path(__file__).resolve().parent
DOCUMENTS=BASE
COLORS=json.loads((DOCUMENTS/'brand_colors.json').read_text())
LOGO=json.loads((DOCUMENTS/'brand_logos.json').read_text())['oneplus']
# Portrait chassis axes; tablets are displayed landscape by the review/gallery.
MODELS={
 '13':(76.5,162.9,8.5,6.82,1440,3168,9.4,'https://www.oneplus.com/us/13/specs'),
 '13r':(75.8,161.7,8,6.78,1264,2780,9.4,'https://www.oneplus.in/13r/specs'),
 'pad':(189.41,258.03,6.54,11.61,2000,2800,11,'https://www.oneplus.com/us/oneplus-pad/specs'),
 'pad-2':(195.06,268.66,6.49,12.1,2120,3000,10,'https://www.oneplus.com/uk/oneplus-pad-2/specs'),
 'pad-3':(209.66,289.61,5.97,13.2,2400,3392,10,'https://www.oneplus.com/uk/oneplus-pad-3/specs'),
 'pad-go':(188.04,255.12,6.89,11.35,1720,2408,11,'https://www.oneplus.com/uk/oneplus-pad-go/specs'),
 '12':(75.8,164.3,9.15,6.82,1440,3168,8.5,'https://www.oneplus.com/us/12/specs'),
 '12r':(75.3,163.3,8.8,6.78,1264,2780,8.5,'https://www.oneplus.com/my/12r/specs'),
 '11':(74.1,163.1,8.53,6.7,1440,3216,8,'https://www.oneplus.com/us/11/specs'),
 '11r':(74.3,163.4,8.7,6.74,1240,2772,8,'https://www.oneplus.in/11r/specs'),
 'pad-lite':(166.46,254.91,7.39,11,1200,1920,8,'https://www.oneplus.com/uk/oneplus-pad-lite/specs'),
}
IMAGES={
 '13':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/phones/13/specs/13-blue.png',
 '13r':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/phones/13r/specs/13R-Trail.png',
 'pad':'https://oasis.opstatics.com/content/dam/oasis/page/2023/pad/pad-specs1.png',
 'pad-2':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/product/rainbow/specgrey.png',
 'pad-3':'https://www.oneplus.com/content/dam/oneplus/2025/specs/pad3/images/Pad3_Erhai_Blue_1080x1080.png',
 'pad-go':'https://oasis.opstatics.com/content/dam/oasis/page/2023/bluey/bluey-spec.png',
 '12':'https://oasis.opstatics.com/content/dam/oasis/page/2023/cn/12/12-black.png',
 '12r':'https://oasis.opstatics.com/content/dam/oasis/page/2024/global/product/aston/aston_blue.png',
 '11':'https://oasis.opstatics.com/content/dam/oasis/page/2023/na/oneplus-11/specs/green-img.png',
 '11r':'https://oasis.opstatics.com/content/dam/oasis/page/2023/in/oneplus-10t/specs/10r-blue.png',
 'pad-lite':'https://www.oneplus.com/content/dam/oneplus/2025/specs/pad-lite/images/Aero_Blue.png',
}
# Existing Documents swatches where available; 11R colors sampled/estimated
# from the official silver/black renders. No changes to the shared color source.
EXTRA_COLORS={
 '12':{'Silky Black':'#18191B','Flowy Emerald':'#1C3630'},
 '12r':{'Iron Gray':'#2B2D31','Cool Blue':'#47708C'},
 '11':{'Titan Black':'#151618','Eternal Green':'#1A2C25'},
 '11r':{'Sonic Black':'#27292D','Galactic Silver':'#BAC8D0'},
}
# Pixels in the corresponding 1080-square official composites; rear widths
# are partly occluded. Published body height supplies the metric scale.
PHONE_REFS={
 '12':([200,122,0,958],[210,170,488,448],[(298,260),(397,260),(298,357),(397,357)],37),
 '12r':([200,120,0,960],[213,172,466,423],[(295,250),(384,250),(295,341),(384,341)],32),
 '11':([201,121,0,959],[214,170,460,406],[(294,243),(392,243),(294,328),(392,328)],33),
 '11r':([205,121,0,958],[214,168,454,408],[(291,243),(382,243),(291,331),(382,331)],34),
}
def rgb(h):return [int(h[i:i+2],16)/255 for i in (1,3,5)]
def logo_contours(width,landscape):
 out=[]
 for sub in SvgPath(LOGO['d']).as_subpaths():
  points=[]
  for seg in sub:
   if seg.__class__.__name__ in ('Move','Close'):continue
   n=1 if seg.__class__.__name__=='Line' else 12
   for i in range(n+1):
    p=seg.point(i/n);x=(p.x-.5)*width;y=(p.y-.5/LOGO['aspect'])*width
    point=[y,-x] if landscape else [x,y]
    if not points or points[-1]!=point:points.append(point)
  if len(points)>2:out.append(points)
 return out

def make(key,row):
 w,h,d,diag,px,py,r,url=row;tablet=key.startswith('pad')
 finishes={}
 palettes=COLORS['oneplus_'+key.replace('-','_')] if key not in EXTRA_COLORS else {name:[color,color,color] for name,color in EXTRA_COLORS[key].items()}
 for name,palette in palettes.items():
  c=rgb(palette[1]);dark=sum(c)/3<.5
  bar=[.025,.03,.04] if key=='pad-3' else [.72,.74,.77] if key=='13' else [v*.82 for v in c]
  finishes[name.replace('_',' ').title()]={'back':{'rgb':c,'metal':.6 if tablet else .15,'rough':.4},'rail':{'rgb':c,'metal':.8,'rough':.3},'bar':{'rgb':bar,'metal':.75,'rough':.3},'logo':{'rgb':[min(1,v*1.5+.1) if dark else v*.6 for v in c],'rough':.45},'band':{'rgb':[min(1,v*1.14) for v in c],'metal':.5,'rough':.35}}
 default=next(iter(finishes));m={**finishes[default],'black':{'rgb':[.008,.011,.016],'rough':.4},'flash':{'rgb':[.85,.84,.76],'rough':.4}}
 scale=diag*25.4/math.hypot(px,py);sw,sh=px*scale,py*scale
 bezel=min((w-sw)/2,(h-sh)/2)
 def xy(u,v):return [w*(.5-v),h*(u-.5)] if tablet else [w*(.5-u),h*(.5-v)]
 windows=[];lenses=[]
 if not tablet:
  # Bounds measured in the 1080-square official composite. Height is unobscured;
  # rear width inferred from published aspect because the front overlaps it.
  bounds=[194,120,588,960] if key=='13' else [201,119,597,958]
  housing=[213,164,482,433] if key=='13' else [225,156,482,413]
  sx=h/(bounds[3]-bounds[1]);cx=(housing[0]+housing[2])/2;cy=(housing[1]+housing[3])/2
  center=[w/2-(cx-bounds[0])*sx,h/2-(cy-bounds[1])*sx]
  diameter=(housing[2]-housing[0])*sx
  camera={'center_mm':center,'size_mm':[diameter,diameter,diameter/2],'bump_mm':2.4 if key=='13' else 2.0,'roll_mm':.35,'integrated_plateau':True,'skip_source_pupil':True,'optical_bump_mm':.15,'lens_ring_mm':.22,'windows':windows,'lenses':lenses,'flash':[],'flash_offset_mm':.25}
  # Three real cameras and one black flash surround, with room inside the rim.
  coords=[(302,250),(395,250),(302,344),(395,344)] if key=='13' else [(303,232),(393,232),(303,319),(393,319)]
  for i,(x,y) in enumerate(coords):
   pos=[w/2-(x-bounds[0])*sx,h/2-(y-bounds[1])*sx];wr=(36 if key=='13' else 33)*sx
   windows.append([*pos,wr*2,wr*2,wr])
   if i<3:lenses.append({'kind':'main' if i==0 else 'ultrawide','center_mm':pos,'radius_mm':wr*.48,'window':i})
   else:camera['flash'].append([*pos,wr*.36])
  camera['sensors']=[[*[center[0]-diameter*.36,center[1]],.45]]
  camera['sensor_surface']='camera'
  camera_ref={'reference':f'research/oneplus/{key}.png','body_bounds_px':bounds,'housing_bounds_px':housing,'scale_mm_per_px':sx,'uncertainty_mm':.8,'note':'Composite has rear width partly occluded; published chassis aspect used for width. Protrusion estimated, not measured.'}
  cutouts=[{'center_mm':[0,h/2-6.2],'radius_mm':1.35}]
  if key in PHONE_REFS:
   bounds,housing,coords,wr_px=PHONE_REFS[key]
   sx=h/(bounds[3]-bounds[1]);bounds=[bounds[0],bounds[1],bounds[0]+w/sx,bounds[3]]
   def pos(x,y):return [w/2-(x-bounds[0])*sx,h/2-(y-bounds[1])*sx]
   center=pos((housing[0]+housing[2])/2,(housing[1]+housing[3])/2);diameter=(housing[2]-housing[0])*sx
   camera.update(center_mm=center,size_mm=[diameter,diameter,diameter/2],bump_mm=2.4 if key=='12' else 2.0,windows=[],lenses=[],flash=[],sensors=[])
   for i,(x,y) in enumerate(coords):
    at=pos(x,y);wr=wr_px*sx
    camera['windows'].append([*at,wr*2,wr*2,wr])
    if i<3:camera['lenses'].append({'kind':'periscope' if key=='12' and i==2 else 'main' if i==0 else 'ultrawide','center_mm':at,'radius_mm':wr*.46,'window':i})
    elif key in ('12','12r'):camera['sensors']=[[*at,1.0]]
    else:camera['flash']=[[*at,wr*.38]]
   if key in ('12','12r'):camera['flash']=[[*pos(245,190),1.6]]
   camera_ref={'reference':f'research/oneplus/{key}.png','body_bounds_px':bounds,'housing_bounds_px':housing,'lens_centers_px':coords[:3],'scale_mm_per_px':sx,'uncertainty_mm':.9,'note':'Rear width inferred from published aspect because front overlaps it. Circular dial and side bridge photoestimated; bump/roll/radii not measured.'}
   cutouts=[{'center_mm':[-w/2+8.0 if key=='11' else 0,h/2-6.2],'radius_mm':1.35}]
 else:
  # Rear positions measured in landscape orientation from the bare upper part
  # of the official composite. Pad 3 moves its camera to a corner capsule.
  cx,cy=xy(.914,.077) if key=='pad-3' else xy(.5,.112 if key!='pad-go' else .092)
  size=[17.0,36.5,8.5] if key=='pad-3' else [26,26,13] if key in ('pad','pad-2') else [22,22,11]
  if key=='pad-3':pos=xy(.94,.077);wr=4.1;flash=[[*xy(.878,.077),1.0]]
  else:pos=[cx,cy];wr=8 if key in ('pad','pad-2') else 7;flash=[]
  windows.append([*pos,2*wr,2*wr,wr]);lenses.append({'kind':'main','center_mm':pos,'radius_mm':wr*.4,'window':0})
  camera={'center_mm':[cx,cy],'size_mm':size,'bump_mm':1.2,'roll_mm':.18,'integrated_plateau':True,'skip_source_pupil':True,'optical_bump_mm':.1,'lens_ring_mm':.25,'windows':windows,'lenses':lenses,'flash':flash,'flash_offset_mm':.1}
  cutouts=[{'center_mm':[-w/2+max(2,(w-sw)/4),0],'radius_mm':1.2}]
  camera_ref={'reference':f'research/oneplus/{key}.png','orientation':'landscape','housing_size_mm':size[:2],'center_normalized':[.914,.077] if key=='pad-3' else [.5,.112 if key!='pad-go' else .092],'uncertainty_mm':1.2,'note':'Official composite render, approximate front-on fitting; protrusion estimated.'}
  if key=='pad-lite':
   cx,cy=xy(.5,.12);wr=8.7;size=[21,21,10.5]
   camera.update(center_mm=[cx,cy],size_mm=size,windows=[ [cx,cy,wr*2,wr*2,wr] ],lenses=[{'kind':'main','center_mm':[cx,cy],'radius_mm':2.3,'window':0}])
   camera_ref.update(housing_size_mm=size[:2],center_normalized=[.5,.12],body_bounds_px=[133,150,946,681],housing_bounds_px=[506,179,574,247],note='Official composite: lower rear obscured by front; metric width gives scale. Single camera centered on long edge; no flash. Depth and radii estimated.')
 name='OnePlus '+(key.replace('pad','Pad').replace('-',' ').replace('lite','Lite') if tablet else key.upper().replace('R','R'))
 p={'id':'oneplus-'+key,'name':name,'manufacturer':'OnePlus','form_factor':'tablet' if tablet else 'phone','status':'provisional','finish':default,
  'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':r,'edge_roll':.55 if key in ('13','pad','pad-go') else .3,'front_rail_mm':.4},'materials':m,'finishes':finishes,
  'screen':{'object':'Device screen','node':'Device screen','panel':'Body','resolution':[px,py],'fit_box_mm':[sw,sh],'center_mm':[0,0,d/2+.035],'corner_radius_mm':max(1,r-bezel),'create_cutouts':True,'cutouts':cutouts},
  'camera':camera,'buttons':[{'name':'Power','side':'right','center_y_mm':h/2-44,'length_mm':10,'width_mm':2,'thickness_mm':.3,'radius_mm':.8},{'name':'Volume','side':'right','center_y_mm':h/2-23,'length_mm':18,'width_mm':2,'thickness_mm':.3,'radius_mm':.8}],
  'rear_logo':{'kind':'oneplus','surface_offset_mm':.08,'center_mm':xy(.5,.52) if tablet else [0,-4],'contours_mm':logo_contours(13 if tablet else 12,tablet)},
  'accuracy':{'body_dimensions':'OnePlus official metric chassis dimensions. OnePlus 13 uses 8.5 mm glass chassis; Midnight Ocean leather is 8.9 mm and remains an approximate finish on that chassis.','screen_geometry':'Published full diagonal and native pixel aspect; concentric estimated corners. Bezel camera estimated from product render.','camera_geometry':'Official rear-render fit, measurements below. Bump depth, roll, glass and optical internals illustrative; not OEM CAD.','finishes':'Official finish names, approximate existing collection sRGB swatches; not calibrated physical materials.','omissions':'Ports, speaker holes, alert slider, antenna seams and microscopic inscriptions omitted.'},'sources':[url,IMAGES[key]],'rear_reference':camera_ref}
 if key=='pad-go':p['rear_details']=[{'name':'Upper contrasting rear band','center_mm':xy(.5,.09),'size_mm':[w*.18-1,h-1,10],'depth_mm':.15,'material':'band'}]
 if key in PHONE_REFS or key=='pad-lite':
  p['gallery_model']='oneplus_'+key.replace('-','_')
  p['accuracy']['body_dimensions']='Official metric chassis dimensions. Corner radii and edge rolls are photoestimates, not measured CAD.'
  p['accuracy']['branding']='OnePlus contour from Documents brand_logos.json; finish-tinted mark, size/placement photoestimated from official rear render; make_device_branding applied before export.'
  if key=='11r':p['accuracy']['body_dimensions']+=' Standard glass 8.70 mm chassis; thicker Solar Red variant excluded.'
  if key in PHONE_REFS:
   logo_y={'12':570,'12r':550,'11':540,'11r':550}[key]
   p['rear_logo']['center_mm']=pos(bounds[0]+w/sx/2,logo_y)
   p['body_mm'].update(edge_roll=1.2,front_curve=.7)
   p['screen']['edge_curve_mm']=.7
   if key in ('11','11r'):p['buttons'][1]['side']='left'
   # Low bridge under the dial, stopping below its optical face; existing
   # rear-detail primitives avoid a change to shared geometry.
   left=w/2-.7;right=center[0]
   p['rear_details']=[{'name':'Camera dial side bridge','center_mm':[(left+right)/2,center[1]],'size_mm':[left-right,diameter,1],'depth_mm':camera['bump_mm']-.6,'material':'bar'}]
   for settings in p['finishes'].values():
    if key in ('11','11r'):settings['bar']={'rgb':[.035,.04,.045],'metal':.75,'rough':.3}
   p['materials']['bar']=p['finishes'][default]['bar'].copy()
  else:
   p['rear_details']=[{'name':'Upper rear band','center_mm':xy(.5,.117),'size_mm':[w*.234-1,h-1,3],'depth_mm':.04,'material':'band'}]
 return p
if __name__=='__main__':
 selected=sys.argv[1:] or list(MODELS)
 for key in selected:
  row=MODELS[key]
  p=apply_branding(make(key,row));(BASE/'profiles'/(p['id']+'.json')).write_text(json.dumps(p,indent=2))
 measurements='oneplus-focused-measurements.json' if sys.argv[1:] else 'oneplus-model-measurements.json'
 (BASE/'research'/measurements).write_text(json.dumps({key:make(key,MODELS[key])['rear_reference'] for key in selected},indent=2))
 print('Generated',len(selected),'OnePlus profiles')
