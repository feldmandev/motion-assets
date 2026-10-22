"""Samsung Z family: published envelopes/pixels, icon-measured cameras, estimated rigid hinges."""
import copy
from make_device_branding import apply as apply_branding
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
DOCUMENTS = BASE.parents[3]/'documents'
sys.path.insert(0, str(DOCUMENTS))
from generate_galaxy_svgs import FOLDS, FLIPS, SAMPLED, fitted_island
from make_samsung_profiles import logo_contours, rgb

PRESS = 'https://api.samsungmobilepress.com/press-releases/'
SOURCES = {
3: PRESS+'the-next-chapter-in-mobile-innovation-unfold-your-world-with-galaxy-z-fold3-5g-and-galaxy-z-flip3-5g',
4: 'https://www.samsung.com/hk/news/product/galaxyzfold4zflip4/',
5: PRESS+'samsung-galaxy-z-flip5-and-galaxy-z-fold5-delivering-flexibility-and-versatility-without-compromise',
6: PRESS+'samsung-galaxy-z-fold6-and-z-flip6-elevate-galaxy-ai-to-new-heights',
7: 'https://www.samsungmobilepress.com/articles/samsung-galaxy-z-fold7-raising-the-bar-for-smartphones',
8: 'https://news.samsung.com/de/samsung-galaxy-z-fold8-ultra-fold8-und-flip8-fur-jeden-lifestyle-ein-faltbares-gerat',
}
FLIP7 = 'https://www.samsungmobilepress.com/articles/samsung-galaxy-z-flip7-a-pocket-sized-ai-powerhouse-with-a-new-edge-to-edge-flexwindow'
TRI = 'https://www.samsungmobilepress.com/articles/introducing-galaxy-z-trifold-the-shape-of-whats-next-in-mobile-innovation'
# W/H/D open, W/H/D closed (maximum for wedge generations), inner WxH pixels/diagonal,
# cover WxH pixels/diagonal, estimated chassis outer radius, minimum closed depth.
SPECS = {
'z_fold3': ([128.1,158.2,6.4],[67.1,158.2,16.0],[1768,2208],7.6,[832,2268],6.2,7.0,14.4),
'z_fold4': ([130.1,155.1,6.3],[67.1,155.1,15.8],[1812,2176],7.6,[904,2316],6.2,7.0,14.2),
'z_fold5': ([129.9,154.9,6.1],[67.1,154.9,13.4],[1812,2176],7.6,[904,2316],6.2,7.0,13.4),
'z_fold6': ([132.6,153.5,5.6],[68.1,153.5,12.1],[1856,2160],7.6,[968,2376],6.3,4.5,12.1),
'z_fold7': ([143.2,158.4,4.2],[72.8,158.4,8.9],[1968,2184],8.0,[1080,2520],6.5,7.0,8.9),
'z_fold8': ([161.4,123.9,4.5],[81.9,123.9,9.7],[2448,1848],7.6,[1248,1972],5.5,8.0,9.7),
'z_fold8_ultra': ([143.2,158.4,4.1],[72.8,158.4,8.9],[2256,2504],8.0,[1080,2520],6.5,7.0,8.9),
'z_flip3': ([72.2,166.0,6.9],[72.2,86.4,17.1],[1080,2640],6.7,[512,260],1.9,8.5,15.9),
'z_flip4': ([71.9,165.2,6.9],[71.9,84.9,17.1],[1080,2640],6.7,[512,260],1.9,8.5,15.9),
'z_flip5': ([71.9,165.1,6.9],[71.9,85.1,15.1],[1080,2640],6.7,[720,748],3.4,8.5,15.1),
'z_flip6': ([71.9,165.1,6.9],[71.9,85.1,14.9],[1080,2640],6.7,[720,748],3.4,8.5,14.9),
'z_flip7': ([75.2,166.7,6.5],[75.2,85.5,13.7],[1080,2520],6.9,[948,1048],4.1,9.5,13.7),
'z_flip7_fe': ([71.9,165.1,6.9],[71.9,85.1,14.9],[1080,2640],6.7,[720,748],3.4,8.5,14.9),
'z_flip8': ([75.4,166.9,6.1],[75.4,85.7,13.1],[1080,2520],6.9,[948,1048],4.1,9.5,13.1),
'z_trifold': ([214.1,159.2,4.2],[75.0,159.2,12.9],[2160,1584],10.0,[1080,2520],6.5,6.5,12.9),
}
# Official standard + online-exclusive finishes; sampled hues come from the icon sources.
EXTRA_COLORS = {
'z_fold3': {'Phantom Black':'#252629'},
'z_fold4': {'Burgundy':'#5f3b43'},
'z_fold5': {'Gray':'#83858a','Blue':'#5a7691'},
'z_fold6': {'Crafted Black':'#252629','White':'#ededeb'},
'z_fold8': {'Graphite':'#343337','Cream':'#eee9db','Lavender':'#c4b6d8'},
'z_fold8_ultra': {'Cream':'#eee9db'},
'z_flip3': {'Phantom Black':'#252629','White':'#eeefeb'},
'z_flip5': {'Gray':'#85888a','Blue':'#6d8fa9','Green':'#637969','Yellow':'#e5d677'},
}


def body(dimensions, radius):
    return dict(zip(('width','height','depth'), dimensions), corner_radius=radius,
                edge_roll_mm=[.25,.20], front_rail_mm=.45, rear_inset=.45)


def base_profile(key, state):
    opened, closed, _, _, _, _, radius, _ = SPECS[key]
    palette = {n.replace('_',' ').title().replace('Jetblack','Jet Black'):v[1] for n,v in SAMPLED[key].items()}
    palette.update(EXTRA_COLORS.get(key, {}))
    if key=='z_flip7':
        palette['Coralred'] = palette.pop('Coral Red')
        palette['Jetblack'] = palette.pop('Jet Black')
    finishes = {}
    for name, color in palette.items():
        c = rgb(color)
        finishes[name] = {'back':{'rgb':c,'rough':.32},
            'rail':{'rgb':[v*.82+.08 for v in c],'metal':.85,'rough':.27},
            'bar':{'rgb':c,'metal':.55,'rough':.3},'logo':{'rgb':[v*.5 for v in c]}}
    finish = next(iter(finishes))
    materials = dict(copy.deepcopy(finishes[finish]), black={'rgb':[.006,.008,.011],'rough':.35},
                     flash={'rgb':[.88,.86,.76],'rough':.35})
    model = key.replace('z_', 'Z ',1).replace('trifold','TriFold').replace('fold','Fold').replace('flip','Flip').replace('_ultra',' Ultra').replace('_fe',' FE')
    source = TRI if key=='z_trifold' else FLIP7 if key.startswith('z_flip7') else SOURCES[int(key[6])]
    return {'id':'galaxy-'+key.replace('_','-')+'-'+state,'name':'Galaxy '+model+' · '+state,
        'manufacturer':'Samsung','form_factor':'phone','state':state,'status':'provisional',
        'body_mm':body(opened if state=='unfolded' else closed,radius),'finish':finish,
        'materials':materials,'finishes':finishes,'sources':[source],
        'accuracy':{'body_dimensions':'Published Samsung chassis dimensions excluding camera modules. Historical Fold3/4 and Flip3/4 thickness range retained in published_spec; closed wedge angle inferred from that range.',
          'screen_resolution':'Published native panel pixels; orientation follows portrait cover/inner in the physical open chassis. ADB feed maps through full native UVs.',
          'screen_geometry':'Active full rectangle from published diagonal/native aspect, fitted within chassis. Rounded corners, bezels, cover folder contour, camera cutouts are photo estimates; not CAD.',
          'camera_geometry':'Lens and flash centres/diameters from source icon measurements of Samsung artwork. Samsung-specific individual rings/capsule, no Pixel bar. Protrusions and optical internals are estimates.',
          'finishes':'Official standard and online-exclusive finish names; approximate sampled sRGB. Bespoke combinations and special editions excluded.',
          'hinge':'Rigid articulated panels with physically positioned axes; external barrel dimensions/curves estimated. Internal multi-link and flexible OLED bend not simulated.',
          'omissions':'Ports, grille perforations, antenna seams and internal hinge linkages.'},
        'published_spec':{'open_mm':opened,'closed_mm':closed,'closed_min_depth_mm':SPECS[key][7]},
        'buttons':[{'name':'Volume','side':'right','center_y_mm':16,'length_mm':19,'width_mm':2.1,'thickness_mm':.3,'radius_mm':1},
                   {'name':'Power','side':'right','center_y_mm':-4,'length_mm':11,'width_mm':2.1,'thickness_mm':.3,'radius_mm':1}]}


def screen(name, resolution, diagonal, dimensions, center, radius, panel):
    scale = min(diagonal*25.4/math.hypot(*resolution),
                (dimensions['width']-3)/resolution[0],(dimensions['height']-3)/resolution[1])
    size = [v*scale for v in resolution]
    return {'object':name,'node':name,'panel':panel,'resolution':resolution,'fit_box_mm':size,
            'center_mm':center,'corner_radius_mm':min(radius,min(size)/2),
            'create_cutouts':True,'cutouts':[], 'foldable_surface':True}


def folder_outline(width,height,radius):
    points = [[-width/2,-height/2],[width/2,-height/2],[width/2,height/2],
              [width*.10,height/2],[width*.10,height*.25],[-width/2,height*.25]]
    rounded = []
    for i,p in enumerate(points):
        prev,nxt = points[i-1],points[(i+1)%len(points)]
        r = min(radius,math.dist(prev,p)*.45,math.dist(nxt,p)*.45)
        before = [v+(u-v)*r/math.dist(prev,p) for u,v in zip(prev,p)]
        after = [v+(u-v)*r/math.dist(nxt,p) for u,v in zip(nxt,p)]
        for step in range(9):
            t = step/8
            rounded.append([(1-t)**2*a+2*t*(1-t)*v+t*t*b for a,v,b in zip(before,p,after)])
    return rounded


def camera(key, panel_body):
    w,h = panel_body['width'],panel_body['height']
    if key in FOLDS:
        g = FOLDS[key]; ref_w = SPECS[key][1][0]
        xy = lambda x,y: [w/2-x*ref_w,h/2-y*ref_w]
        circles = [(xy(x,y),d*ref_w) for x,y,d in g['lenses']]
        flash = [*xy(*g['flash'][:2]),g['flash'][2]*ref_w/2]
        x0,y0,x1,y1 = fitted_island(g,0,0,ref_w,margin=.035)
        cw,ch = x1-x0,y1-y0
        center = [w/2-(x0+x1)/2,h/2-(y0+y1)/2]
        bump = .65 if key in ('z_fold3','z_fold4') else .8
    else:
        g = FLIPS[key]; full_h = SPECS[key][0][1]
        # Icon y is normalized to its 50-unit open body; x/lens diameters to 30-unit width.
        xy = lambda x,y: [w/2-(x-39)*w/30, h/2-(y-29)*full_h/50]
        circles = [(xy(x,y),g['d']*w/30) for x,y in g['lenses']]
        flash = [*xy(*g['flash'][:2]),g['flash'][2]*w/60]
        cw,ch,center,bump = 1,1,[0,0],0
    windows = [[*p,d-.8,d-.8,(d-.8)/2] for p,d in circles]
    return {'center_mm':center,'size_mm':[cw,ch,min(cw,ch)/2], 'bump_mm':bump,
            'ring_material':'black' if g.get('ring')=='dark' else 'rail',
            'optical_bump_mm':.8 if key.endswith(('3','4')) else 1.1,'lens_ring_mm':.4,
            'roll_mm':.15,'integrated_plateau':bool(bump),'windows':windows,
            'lenses':[{'kind':('ultrawide','main','telephoto')[i], 'center_mm':p,
                       'radius_mm':d*.29,'window':i} for i,(p,d) in enumerate(circles)],
            'flash':[flash],'flash_surface':'housing' if key in FOLDS and FOLDS[key].get('island_flash') else 'body','sensors':[]}


def joint(name, axis, position, degrees, anchor, moving_anchor, closed_depth, length, start=0,end=1):
    return {'moving_panel':name,'axis':axis,'axis_mm':position,'closed_degrees':degrees,
            'fixed_anchor_mm':anchor,'moving_anchor_mm':moving_anchor,
            'spine_width_mm':closed_depth,'spine_depth_mm':1.2,'length_mm':length,
            'spine_pivot':'Fold pivot | Hinge spine '+name,'start_fraction':start,'end_fraction':end}


def articulation(data, joints, fixed, regions):
    primary = joints[0]
    data['articulation'] = dict(animation='Fold',axis=primary['axis'],axis_mm=primary['axis_mm'],
        moving_panel=primary['moving_panel'],fixed_panel=fixed,
        pivots={p['name']:'Fold pivot | '+p['name'] for p in data['panels']},
        open_degrees=0,closed_degrees=primary['closed_degrees'],duration_seconds=1.0,
        closed_body_mm=body(SPECS[data['source_key']][1],data['body_mm']['corner_radius']),
        companion_profile=data['id'].replace('-unfolded','-folded'),joints=joints)
    data['screens'][0]['panel_regions_mm'] = regions


def two_panel(key, state):
    data = base_profile(key,state); data['source_key'] = key
    opened, closed, inner_px, inner_diag, cover_px, cover_diag, radius, min_depth = SPECS[key]
    flip = key in FLIPS
    long_dim = opened[1] if flip else opened[0]
    gap = .4
    span = (long_dim-gap)/2
    depth = opened[2]
    axis_z = closed[2]/2-depth/2
    wedge = closed[2]-min_depth
    degrees = 180+math.degrees(math.asin(wedge/span)) if wedge else 180
    panel_body = body([opened[0],span,depth] if flip else [span,opened[1],depth], radius)
    centers = [[0,span/2+gap/2,0],[0,-span/2-gap/2,0]] if flip else [[-span/2-gap/2,0,0],[span/2+gap/2,0,0]]
    names = ['Cover half','Camera half']
    data['panels'] = [{'name':n,'body_mm':copy.deepcopy(panel_body),'center_mm':c,'buttons':i==(0 if flip else 1)}
                      for i,(n,c) in enumerate(zip(names,centers))]
    for i,p in enumerate(data['panels']):
        p['body_mm']['corner_radii_mm'] = ([1, radius,radius,1] if i==0 else [radius,1,1,radius]) if flip else ([1,1,radius,radius] if i==0 else [radius,radius,1,1])
    camera_panel = data['panels'][0 if flip else 1]
    camera_panel['camera'] = camera(key,panel_body)
    camera_panel['camera']['flash_offset_mm'] = .07
    if flip:
        # The exterior display and dual cameras share the upper leaf.
        camera_panel['body_mm']['rear_style'] = 'inset_glass'
        glass_height = opened[1]*12/50 if FLIPS[key]['cover']=='strip' else span-.9
        camera_panel['rear_glass_region_mm'] = [0,span/2-.45-glass_height/2,opened[0]-.9,glass_height]
        camera_panel['rear_glass_region_radii_mm'] = [.5,radius-.45,radius-.45,.5]
    else:
        camera_panel['rear_logo'] = {'kind':'samsung','center_mm':[0,-panel_body['height']*.4], 'contours_mm':logo_contours(span*.28)}
    inner = screen('Inner screen',inner_px,inner_diag,body(opened,radius),[0,0,depth/2+.04],radius-1.5,'Inner display')
    # Fold3–6 have UDC, not a black punched hole in the active OLED.
    if flip or key in ('z_fold7','z_fold8','z_fold8_ultra'):
        inner['cutouts'] = [{'center_mm':[0 if flip else inner['fit_box_mm'][0]/4,inner['fit_box_mm'][1]/2-5], 'radius_mm':1.35}]
    cover_body = panel_body
    cover = screen('Cover screen',cover_px,cover_diag,cover_body,[0,0,-depth/2-.09],5 if flip else radius-1.5,'Cover half')
    cover.update(rotation_deg=[0,180,0],frame_file='cover-frame.svg',frame_body_mm=body(closed,radius),frame_center_mm=[0,0])
    if not flip:
        cover['cutouts'] = [{'center_mm':[0,cover['fit_box_mm'][1]/2-4.5],'radius_mm':1.35}]
        cover['glass_border_mm'] = .65
    else:
        style = FLIPS[key]['cover']
        cover['center_mm'][:2] = [-7,span/2-17] if style=='strip' else [0,-1]
        cover['glass_border_mm'] = .6
        if style=='folder':
            cover['frame_use_outline'] = True
            # Native framebuffer bounding rectangle; opaque upper-left camera exclusion.
            sw,sh = cover['fit_box_mm']
            cover['outline_mm'] = folder_outline(sw,sh,cover['corner_radius_mm'])
        elif style=='full':
            camera_panel['camera']['flash_offset_mm'] = .17
            # Rear-view X reverses at the cover screen's Y=180° mapping.
            cover['cutouts'] = [{'center_mm':[-p[0]-cover['center_mm'][0],p[1]-cover['center_mm'][1]],'radius_mm':d/2+.35}
                                for p,d in [(l['center_mm'],w[2]+.8) for l,w in zip(camera_panel['camera']['lenses'],camera_panel['camera']['windows'])]]
            fx,fy,fr = camera_panel['camera']['flash'][0]
            cover['cutouts'].append({'center_mm':[-fx-cover['center_mm'][0],fy-cover['center_mm'][1]],'radius_mm':fr+.25})
    if state=='unfolded':
        cover['frame_center_mm'] = [-cover['center_mm'][0],cover['center_mm'][1]]
        data['screens'] = [inner,cover]
        axis = 'X' if flip else 'Y'
        # Closed spine reaches the published envelope beyond the two flat leaf outlines.
        anchor = closed[1]-long_dim/2-.6 if flip else long_dim/2-closed[0]+.6
        a = [0,anchor,-depth/2+.6] if flip else [anchor,0,-depth/2+.6]
        b = [0,-anchor,-depth/2+.6] if flip else [-anchor,0,-depth/2+.6]
        j = joint('Cover half',axis,[0,0,axis_z],degrees,a,b,closed[2],opened[0]-5 if flip else opened[1]-5)
        regions = {'Cover half':[-1e4,0,1e4,1e4],'Camera half':[-1e4,-1e4,1e4,0]} if flip else {'Cover half':[-1e4,-1e4,0,1e4],'Camera half':[0,-1e4,1e4,1e4]}
        articulation(data,[j],'Camera half',regions)
    else:
        # Closed companion is the same physical leaf transform as the animation endpoint.
        angle = math.radians(degrees); c,s = math.cos(angle),math.sin(angle)
        target = -(closed[1]-span)/2 if flip else (closed[0]-span)/2
        shift = centers[1][1 if flip else 0]-target
        for i,p in enumerate(data['panels']):
            x,y,z = centers[i]
            if i==0:
                if flip: y,z = y*c-(z-axis_z)*s,axis_z+y*s+(z-axis_z)*c
                else: x,z = x*c+(z-axis_z)*s,axis_z-x*s+(z-axis_z)*c
                p['rotation_deg'] = [degrees,0,0] if flip else [0,degrees,0]
            p['center_mm'] = [x if flip else x-shift,y-shift if flip else y,z-axis_z]
        data['screens'] = [cover]
        cover['frame_center_mm'] = [-cover['center_mm'][0],cover['center_mm'][1]]
    return data


def trifold(state):
    key = 'z_trifold'; data = base_profile(key,state); data['source_key'] = key
    # Samsung publishes three different leaf thicknesses; centre carries the cover screen.
    widths = [71.15,71.4,71.15]; depths = [3.9,4.2,4.0]
    centers = [[-71.475,0,.15],[0,0,0],[71.475,0,.1]]
    names = ['Left half','Cover half','Camera half']
    data['panels'] = [{'name':n,'body_mm':body([w,159.2,d],6.5),'center_mm':c,'buttons':i==2}
        for i,(n,w,d,c) in enumerate(zip(names,widths,depths,centers))]
    data['panels'][2]['camera'] = camera(key,data['panels'][2]['body_mm'])
    for i,p in enumerate(data['panels']):
        p['body_mm']['corner_radii_mm'] = [1,1,6.5,6.5] if i==0 else [6.5,6.5,1,1] if i==2 else [1,1,1,1]
    opened,closed,ip,di,cp,dc,_,_ = SPECS[key]
    inner = screen('Inner screen',ip,di,body(opened,6.5),[0,0,2.15],5,'Inner display')
    inner['cutouts'] = [{'center_mm':[inner['fit_box_mm'][0]/2-8,inner['fit_box_mm'][1]/2-5],'radius_mm':1.35}]
    cover = screen('Cover screen',cp,dc,data['panels'][1]['body_mm'],[0,0,-2.19],5,'Cover half')
    cover.update(rotation_deg=[0,180,0],frame_file='cover-frame.svg',frame_body_mm=body(closed,6.5),frame_center_mm=[0,0],glass_border_mm=.65)
    cover['cutouts'] = [{'center_mm':[0,cover['fit_box_mm'][1]/2-4.5],'radius_mm':1.35}]
    if state=='unfolded':
        data['screens'] = [inner,cover]
        joints = [joint('Left half','Y',[-35.75,0,2.2],180,[-36.9,0,-1.5],[-34.6,0,-1.2],8.35,154.2,0,.5),
                  joint('Camera half','Y',[35.75,0,4.45],-180,[36.9,0,-1.5],[34.6,0,-1.3],12.9,154.2,.5,1)]
        articulation(data,joints,'Cover half',{'Left half':[-1e4,-1e4,-35.75,1e4],
            'Cover half':[-35.75,-1e4,35.75,1e4],'Camera half':[35.75,-1e4,1e4,1e4]})
    else:
        data['panels'][0].update(center_mm=[-.025,0,-.10],rotation_deg=[0,180,0])
        data['panels'][1]['center_mm'] = [0,0,-4.35]
        data['panels'][2].update(center_mm=[.025,0,4.45],rotation_deg=[0,-180,0])
        data['screens'] = [cover]
    data['accuracy']['hinge'] += ' Two independent inward hinges close left first, then camera leaf, with clearance for the three unequal published leaf thicknesses.'
    return data


def profiles():
    result = []
    for key in SPECS:
        opened, closed = [trifold(state) if key=='z_trifold' else two_panel(key,state)
                          for state in ('unfolded','folded')]
        fixed = opened['articulation']['fixed_panel']
        op = next(p for p in opened['panels'] if p['name']==fixed)['center_mm']
        cp = next(p for p in closed['panels'] if p['name']==fixed)['center_mm']
        offset = [a-b for a,b in zip(op,cp)]
        closed['static_hinges'] = []
        for j in opened['articulation']['joints']:
            angle = math.radians(j['closed_degrees']); c,s = math.cos(angle),math.sin(angle)
            x,y,z = [a-b for a,b in zip(j['moving_anchor_mm'],j['axis_mm'])]
            rotated = [x,y*c-z*s,y*s+z*c] if j['axis']=='X' else [x*c+z*s,y,-x*s+z*c]
            moving = [a+b for a,b in zip(rotated,j['axis_mm'])]
            fixed_anchor = j['fixed_anchor_mm']
            closed['static_hinges'].append({'axis':j['axis'],
                'center_mm':[(a+b)/2-o for a,b,o in zip(fixed_anchor,moving,offset)],
                'rotation_degrees':j['closed_degrees']/2,
                'span_mm':math.dist(fixed_anchor,moving)+j['spine_depth_mm'],
                'length_mm':j['length_mm'],'depth_mm':j['spine_depth_mm']})
        result.extend([opened,closed])
    return result


if __name__=='__main__':
    items = profiles()
    for item in items:
        apply_branding(item)
        (BASE/'profiles'/f"{item['id']}.json").write_text(json.dumps(item,indent=2)+'\n',encoding='utf-8')
    (BASE/'research/samsung-fold-specs.json').write_text(json.dumps({
        'models':[{k:p[k] for k in ('id','published_spec','sources','accuracy')} for p in items if p['state']=='unfolded'],
        'camera_measurements':'documents/generate_galaxy_svgs.py FOLDS/FLIPS; colours galaxy_colors.json',
        'catalog_mapping':'galaxy-z-NAME => galaxy-z-NAME-unfolded + galaxy-z-NAME-folded'},indent=2)+'\n')
    print('Generated',len(items),'Samsung folding profiles')
