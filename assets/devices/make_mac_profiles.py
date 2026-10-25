"""Create Apple silicon Mac profiles from the compact, sourced hardware catalogue."""
import copy
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import box

BASE = Path(__file__).resolve().parent
RESEARCH = BASE/'research' if (BASE/'research').exists() else BASE/'provenance/research'
FRONT_CALIBRATION = json.loads((RESEARCH/'mac-model-front-calibration.json').read_text())['chassis']
COLORS = {'Silver':'#c8cace','Space Gray':'#777980','Space Black':'#34363b',
          'Gold':'#d5baa0','Starlight':'#d9d2c5','Midnight':'#303b49','Sky Blue':'#b9c9d4',
          'Blush':'#e2bdc3','Citrus':'#dedda8','Indigo':'#7280a6'}


def rgb(value):
    return [round(int(value[i:i+2],16)/255,5) for i in (1,3,5)]


def finishes(names):
    result = {}
    for name in names:
        color = rgb(COLORS[name])
        dark = name in ('Midnight','Space Black')
        result[name] = {
            'back':{'rgb':color,'metal':.8,'rough':.33},
            'rail':{'rgb':color,'metal':.8,'rough':.28},
            'trackpad':{'rgb':[v*.96 for v in color],'metal':.15,'rough':.34},
            'logo':{'rgb':[v*.24 if not dark else v*.32 for v in color],'metal':.55,'rough':.19},
            'keycap':{'rgb':[1,1,1],'rough':.42},
        }
    return result


def keyboard_texture(touchbar, neo=False):
    rows = [list('`1234567890-=')+['delete'], ['tab']+list('QWERTYUIOP[]')+['\\'],
            ['caps']+list("ASDFGHJKL;'")+['return'], ['shift']+list('ZXCVBNM,./')+['shift'],
            ['fn','ctrl','option','cmd','space','cmd','option','◀','▲','▼','▶']]
    if not touchbar: rows.insert(0,['esc']+[f'F{i}' for i in range(1,13)]+['◉'])
    image = Image.new('RGB',(1644,640),'#f2f2f2' if neo else '#141519')
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',15)
    for row_index,labels in enumerate(rows):
        weights = [3.9 if label=='space' else 1.7 if label in ('delete','tab','caps','return','shift')
                   else 1.25 if label in ('cmd','option') else 1 for label in labels]
        cursor = 0
        for label,weight in zip(labels,weights):
            x=(cursor+weight/2)/sum(weights)*image.width
            y=(row_index+.5)/len(rows)*image.height
            if label!='space':draw.text((x,y),label,font=font,fill='#383940' if neo else '#eeeeef',anchor='mm')
            cursor += weight
    path=BASE/'textures'/('mac-keyboard-neo.png' if neo else 'mac-keyboard-touchbar.png' if touchbar else 'mac-keyboard-function.png')
    image.save(path)


def make_profile(device, chassis):
    row=copy.deepcopy(device)
    spec=copy.deepcopy(chassis)
    spec.update({key:row[key] for key in ('kind','family','chassis_id','dimensions_mm','ports')})
    spec['touchbar']='touch-bar' in spec.get('keyboard','')
    spec['notch']=row.get('display',{}).get('notch',False)
    colors=finishes(row['finishes'])
    if row['chassis_id'] in ('macbook-air-13-wedge','macbook-pro-13-touchbar'):
        for values in colors.values():
            values['bezel_mark']={'rgb':[v*.65 for v in values['rail']['rgb']],'metal':.25,'rough':.35}
    if row['family']=='macbook-neo':
        for values in colors.values():values['keycap']['rgb']=[v*.27+.7 for v in values['back']['rgb']]
    name=row['finishes'][0]
    mats=copy.deepcopy(colors[name])
    mats.update(black={'rgb':[.008,.009,.012],'rough':.45},
                flash={'rgb':[.88,.90,.87],'rough':.3})
    dims=row['dimensions_mm']
    profile={
        'id':row['id'],'name':row['name'],'manufacturer':'Apple','form_factor':row['kind'],
        'body_mm':{'width':dims['width'],'height':dims['height'],'depth':dims['depth'],
                   'corner_radius':spec['corner_radius_mm'],'edge_roll_mm':[1.1,1.1]},
        'finish':name,'finishes':colors,'materials':mats,'status':'published specifications; illustrative geometry',
        'apple_mac':spec,'sources':row['sources'],
        'accuracy':{
            'body_dimensions':'Published Apple width, depth and closed height; physical envelope is recorded in apple_mac.dimensions_mm.',
            'camera_geometry':'Camera aperture, port placement, socket internals and vent depths are illustrative photo estimates.',
            'screen_geometry':'Native resolution and physical display extent from published pixel density; rounded corners and notch dimensions estimated from product imagery.',
            'finishes':'Official finish names; approximate sRGB aluminum, glass and finish-toned reflective Apple inlays.',
            'branding':'Apple vector contour on the centered top desktop face or exterior laptop lid; no Apple mark on the laptop display bezel.',
            'detail_geometry':'Published port types/count; socket size, curved enclosure sections, keyboard layout, grille, feet and split lid/base thickness estimated.',
        },
    }
    if row['kind']=='pc':
        profile['screens']=[]
        return profile
    w,h=dims['width'],dims['depth']
    front=FRONT_CALIBRATION[row['chassis_id']]
    lh=front['lid_height_mm']
    hinge_offset=h-lh
    spec.update(lid_height_mm=lh,hinge_offset_mm=hinge_offset,
                camera_below_screen_top_mm=front.get('camera_below_screen_top_mm'))
    if spec['notch']:
        spec['display'].update({key:front[key] for key in ('notch_width_mm','notch_height_mm')})
    ld=spec['lid_depth_mm']
    bd=dims['height']-ld-.6
    r=spec['corner_radius_mm']
    profile['body_mm']={'width':w,'height':lh,'depth':ld,'base_depth_mm':bd,'base_length_mm':h,
                        'closed_depth_mm':dims['height'],'corner_radius':r,'edge_roll_mm':[.35,.2]}
    profile['panels']=[
        {'name':'Lid','center_mm':[0,lh/2+.6,hinge_offset-ld/2],
         'body_mm':{'width':w,'height':lh,'depth':ld,'corner_radius':r},'buttons':False},
        {'name':'Base','center_mm':[0,-bd/2,h/2],
         'body_mm':{'width':w,'height':bd,'depth':h,'corner_radius':r},'buttons':False},
    ]
    display=row['display']
    sw,sh=display['width_mm'],display['height_mm']
    scale=min(sw/display['resolution'][0],sh/display['resolution'][1])
    sw,sh=scale*display['resolution'][0],scale*display['resolution'][1]
    sr=display['corner_radius_mm']
    cy=(lh-sh)/2-front['screen_top_mm']
    spec['screen_center_y_mm']=cy
    screen={'object':'Device screen','node':'Device screen','panel':'Lid',
            'resolution':display['resolution'],'fit_box_mm':[sw,sh],
            'center_mm':[0,cy,ld/2+.14],'frame_center_mm':[0,cy],
            'corner_radius_mm':sr,'create_cutouts':False,'cutouts':[]}
    if display['notch'] or row['family']=='macbook-neo':
        shape=box(-sw/2+sr,-sh/2+sr,sw/2-sr,sh/2-sr).buffer(sr,quad_segs=24)
        # Apple's modern MacBook panels round only the upper display corners.
        shape=shape.union(box(-sw/2,-sh/2,sw/2,0))
        screen['corner_radii_mm']=[0,sr,sr,0]
        if display['notch']:
            nw,nh=front['notch_width_mm'],front['notch_height_mm']
            notch=box(-nw/2+1.1,sh/2-nh+1.1,nw/2-1.1,sh/2+5).buffer(1.1,quad_segs=12)
            shape=shape.difference(notch)
        screen['outline_mm']=[list(point) for point in shape.exterior.coords[:-1]]
        screen['outline_samples']=4096
        screen['mesh_cutouts']=True
        screen['frame_use_outline']=True
    profile['screen']=screen
    profile['articulation']={
        'animation':'Fold','axis':'X','axis_mm':[0,.6,hinge_offset],'moving_panel':'Lid','fixed_panel':'Base',
        'pivots':{'Lid':'Fold pivot | Lid','Base':'Fold pivot | Base'},
        'open_degrees':0,'closed_degrees':90,'duration_seconds':1,
        'closed_body_mm':{'width':w,'height':dims['height'],'depth':h},
    }
    profile['accuracy']['hinge']='One rigid X-axis clamshell joint; 0.6 mm clearance above base; opens/closes lid without changing screen UVs. Hinge mechanism illustrative.'
    profile['accuracy']['front_frame']='Independent lid height, display placement and notch width fitted to primary Apple front artwork; base footprint and native OLED aspect retained. Photo estimates, not CAD.'
    if 'bezel_mark' in mats:
        profile['accuracy']['front_wordmark']='Legacy bottom-bezel wordmark uses an approximate sans-serif outline and finish-tinted material; modern notched models omit it.'
    profile['sources']=list(dict.fromkeys(profile['sources']+[front['reference_image'],front['source_specs']]))
    return profile


def main():
    catalog=json.loads((RESEARCH/'apple-mac-catalog.json').read_text())
    for touchbar in (False,True):keyboard_texture(touchbar)
    keyboard_texture(False,True)
    for row in catalog['devices']:
        profile=make_profile(row,catalog['chassis'][row['chassis_id']])
        (BASE/'profiles'/f'{row["id"]}.json').write_text(json.dumps(profile,indent=2)+'\n',encoding='utf-8')
    print(f'Wrote {len(catalog["devices"])} Apple silicon Mac profiles')


if __name__=='__main__':main()
