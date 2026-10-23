"""Focused Nothing slabs: official specs and front-on official rear-render fits."""
import json
import math
from pathlib import Path
from make_device_branding import apply as apply_branding, tone

BASE = Path(__file__).resolve().parent
COLORS = json.loads((BASE.parents[3]/'documents/brand_colors.json').read_text())
# width, height, depth, full rectangle diagonal, native pixels, estimated chassis radius.
MODELS = {
    '2': (76.4,162.1,8.6,6.7,1080,2412,10.3),
    '3': (75.59,160.6,8.99,6.67,1260,2800,10.0),
    '3a': (77.5,163.52,8.35,6.77,1080,2392,9.8),
    '3a-pro': (77.5,163.52,8.39,6.77,1080,2392,9.8),
    '4a': (77.45,163.8,8.55,6.78,1224,2720,10.5),
}
REFS = {
    '2': ('2-0.jpg',[796,209,1250,1164]),
    '3': ('3-6.jpg',[604,142,1449,1910]),
    '3a': ('3a-ref-6.jpg',[589,137,1461,1907]),
    '3a-pro': ('3a-pro-ref-5.jpg',[576,137,1459,1907]),
    '4a': ('4a-7.jpg',[599,147,1448,1903]),
}


def rgb(color):
    return [int(color[i:i+2],16)/255 for i in (1,3,5)]


def make(key):
    w,h,d,diagonal,px,py,r = MODELS[key]
    gallery = 'nothing_phone_'+key.replace('-','_')
    finishes = {}
    for name,palette in COLORS[gallery].items():
        c = rgb(palette[1]); light = sum(c)/3>.55
        finishes[name.replace('_',' ').title()] = {
            'back': {'rgb':c,'rough':.36},
            'rail': {'rgb':rgb(palette[2]),'metal':.65 if key in ('2','3') else .2,'rough':.29},
            'bar': {'rgb':rgb(palette[2]) if key in ('3a-pro','4a') else [.09,.10,.11],'metal':.35,'rough':.28},
            'logo': {'rgb':tone(c),'rough':.45},
            'decor': {'rgb':[v*.95 if light else min(1,v*1.06) for v in c],'rough':.5},
            'seam': {'rgb':[v*.86 for v in c],'rough':.55},
            'glyph': {'rgb':[.94,.94,.89] if light else [.75,.77,.76],'rough':.38},
        }
    finish = next(iter(finishes))
    mats = dict(finishes[finish])
    mats.update(black={'rgb':[.008,.01,.014],'rough':.32},flash={'rgb':[.88,.87,.78],'rough':.4},
                red={'rgb':[.55,.025,.035],'rough':.4},matrix={'rgb':[.09,.10,.10],'rough':.6})
    def xy(u,v): return [w*(.5-u),h*(.5-v)]
    details = []; glyphs = []
    def slab(name,u,v,ww,hh,rr,material='decor',depth=.04):
        details.append({'name':name,'center_mm':xy(u,v),'size_mm':[ww,hh,rr],'material':material,'depth_mm':depth})
    def disk(name,u,v,rr,material='decor',depth=.04):
        details.append({'name':name,'center_mm':xy(u,v),'radius_mm':rr,'material':material,'depth_mm':depth})
    def stroke(name,points,width,material='glyph'):
        glyphs.append({'name':name,'points_mm':[xy(u,v) for u,v in points],'width_mm':width,'material':material})
    def arc(name,u,v,radius,start,end,width,material='glyph'):
        points = [(u+radius/w*math.cos(math.radians(a)),v+radius/h*math.sin(math.radians(a)))
                  for a in [start+(end-start)*i/80 for i in range(81)]]
        stroke(name,points,width,material)
    camera = {'center_mm':xy(.5,.22),'size_mm':[1,1,.5],'bump_mm':0,'roll_mm':.2,
              'integrated_plateau':True,'skip_source_pupil':True,'optical_bump_mm':.55,
              'lens_ring_mm':.32,'ring_material':'bar','windows':[],'lenses':[],'flash':[],
              'flash_surface':'body','flash_offset_mm':.08}
    def lens(u,v,radius,kind='main',pupil=None):
        pos = xy(u,v);i=len(camera['windows'])
        ww,hh,rr = (radius*1.7,radius*2.1,1.4) if kind=='periscope' and key=='3a-pro' else (radius*2,radius*2,radius)
        camera['windows'].append([*pos,ww,hh,rr])
        camera['lenses'].append({'kind':kind,'center_mm':pos,'radius_mm':pupil or radius*.47,'window':i})
    if key=='2':
        lens(.193,.09,6.3);lens(.193,.19,6.3,'ultrawide')
        camera['flash']=[[*xy(.405,.158),1.7]]
        # Wireless-coil ring split into the characteristic unequal diffusers.
        for n,(a,b) in enumerate([(218,244),(262,320),(35,63),(81,171)]):
            points=[(.50+33/w*math.cos(math.radians(a+(b-a)*i/80)),
                     .50+40/h*math.sin(math.radians(a+(b-a)*i/80))) for i in range(81)]
            stroke('Glyph coil arc '+str(n),points,1.75)
        stroke('Glyph coil left straight',[(.076,.37),(.076,.50)],1.75)
        stroke('Glyph coil right straight',[(.924,.505),(.924,.59)],1.75)
        stroke('Glyph charging stem',[(.50,.817),(.50,.955)],1.8)
        disk('Glyph charging dot',.50,.973,1.0,'glyph',.065)
        stroke('Glyph upper diagonal',[(.86,.065),(.86,.08),(.69,.18)],1.7)
        # Camera capsule C: two semicircular ends and straight outer side.
        arc('Glyph camera upper',.193,.09,9.4,180,360,1.6)
        stroke('Glyph camera outside',[(.193-9.4/w,.09),(.193-9.4/w,.19)],1.6)
        arc('Glyph camera lower',.193,.19,9.4,0,180,1.6)
        for i in range(3):
            stroke('Coil trace '+str(i),[(.5+(29+i*.7)/w*math.cos(a*math.pi/180),
                                        .5+(36+i*.7)/h*math.sin(a*math.pi/180)) for a in range(360)],.12,'seam')
        slab('Lower connector cover',.5,.88,54,26,6)
    elif key=='3':
        lens(.135,.106,6.6,'periscope',2.8);lens(.195,.239,6.4);lens(.50,.239,6.4,'ultrawide')
        camera['flash']=[[*xy(.24,.063),1.8]]
        disk('Glyph Matrix black cover',.802,.09,10.4,'black',.045)
        glyphs.append({'name':'Glyph Matrix inactive dot array','matrix':True,'center_mm':xy(.802,.09),'pitch_mm':.77,'material':'matrix'})
        slab('Upper central circular plate',.50,.09,20.0,20.0,10)
        slab('Long central rear plate',.50,.52,22,89,1.4)
        slab('Lower left rear plate',.205,.73,20,52,1.7)
        slab('Camera recording square',.383,.296,3.4,3.4,.1,'red')
        disk('Rear Glyph button',.86,.50,5.8)
    elif key in ('3a','3a-pro'):
        if key=='3a':
            camera.update(center_mm=xy(.50,.218),size_mm=[43,18,9],bump_mm=1.6,optical_bump_mm=.15,ring_material='black')
            lens(.32,.218,5.4);lens(.50,.218,4.0,'ultrawide');lens(.68,.218,5.5)
            camera['flash']=[[*xy(.85,.081),2.25]]
            center=(.5,.218);rr=30.5
        else:
            camera.update(center_mm=xy(.50,.218),size_mm=[52,52,26],bump_mm=3.2,optical_bump_mm=.15)
            lens(.327,.127,4.8,'ultrawide');lens(.327,.218,5.8);lens(.54,.226,6.3,'periscope',2.6)
            camera['flash']=[[*xy(.50,.10),2.8]];camera['flash_surface']='camera'
            center=(.5,.218);rr=29.5
        arc('Glyph upper left',*center,rr,201,246,2.1)
        arc('Glyph lower left',*center,rr,139,157,2.1)
        arc('Glyph right',*center,rr,-11,32,2.1)
        slab('Rear midline seam',.5,.419,w-8,.28,.12,'seam')
        slab('Lower transparent circuit panel',.60,.655,24,64,9)
        slab('Lower circuit seam',.70,.665,.20,42,.08,'seam')
        slab('Recording indicator',.923,.403,4.3,4.3,.1,'red' if key=='3a' else 'decor')
    else:
        camera.update(center_mm=xy(.48,.16),size_mm=[46,19.5,9.75],bump_mm=2.0,optical_bump_mm=.15)
        lens(.31,.16,5.0);lens(.45,.16,3.5,'periscope',1.6);lens(.63,.16,5.9,'ultrawide')
        camera['flash']=[[*xy(.545,.061),2.0]]
        slab('Camera surround organic plate',.49,.163,62,34,17,'decor',.10)
        # Six white diffusers and the seventh, red recording indicator.
        for i in range(6):slab('Glyph Bar segment '+str(i),.928,.10+i*.0208,3.4,2.9,.45,'glyph',.065)
        slab('Recording indicator',.928,.225,3.4,3.3,.15,'red')
        slab('Lower rear circuit cover',.48,.65,56,91,13)
        slab('Lower circuit seam',.65,.79,.20,41,.08,'seam')
    # A few low-contrast seams/screws communicate the transparent construction.
    for i,(u,v) in enumerate([(.09,.045),(.91,.045),(.09,.96),(.88,.96)]):
        disk('Rear fastener '+str(i),u,v,.65,'seam')
    # Reconstructed restrained dot-matrix NOTHING wordmark, vertically near lower left.
    letters=['10001/11001/10101/10011/10001','01110/10001/10001/10001/01110',
             '11111/00100/00100/00100/00100','10001/10001/11111/10001/10001',
             '111/010/010/010/111','10001/11001/10101/10011/10001','01110/10000/10111/10001/01110']
    contours=[];cursor=0
    for letter in letters:
        rows=letter.split('/')
        for row,line in enumerate(rows):
            for col,value in enumerate(line):
                if value=='1':
                    x=row*.30;y=cursor+col*.30;s=.19
                    contours.append([[x,y],[x+s,y],[x+s,y+s],[x,y+s]])
        cursor+=(len(rows[0])+1)*.30
    scale=diagonal*25.4/math.hypot(px,py);sw,sh=px*scale,py*scale
    bezel=min((w-sw)/2,(h-sh)/2)
    p={'id':'nothing-phone-'+key,'gallery_model':gallery,'name':'Nothing Phone ('+key.replace('-pro',') Pro')+('' if key.endswith('-pro') else ')'),
       'manufacturer':'Nothing','form_factor':'phone','status':'provisional','finish':finish,
       'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':r,'edge_roll':.65 if key=='2' else .28,'front_rail_mm':.4},
       'materials':mats,'finishes':finishes,
       'screen':{'object':'Device screen','node':'Device screen','panel':'Body','resolution':[px,py],'fit_box_mm':[sw,sh],
                 'center_mm':[0,0,d/2+.035],'corner_radius_mm':r-bezel,'create_cutouts':True,
                 'cutouts':[{'center_mm':[0,h/2-6.2],'radius_mm':1.4}]},
       'camera':camera,'rear_details':details,'nothing_glyphs':glyphs,
       'rear_logo':{'kind':'nothing','center_mm':xy(.115,.81),'surface_offset_mm':.085,'contours_mm':contours},
       'buttons':[{'name':name,'side':side,'center_y_mm':h*(.5-v),'length_mm':length,'width_mm':2,'thickness_mm':.35,'radius_mm':.6}
                  for name,side,v,length in [('Power','right',.31,10),('Volume up','left',.25,7),('Volume down','left',.31,7)]+([] if key=='2' else [('Essential key','right',.43,7)])],
       'accuracy':{'body_dimensions':'Official metric chassis dimensions. Radius and edge roll photoestimated; not OEM CAD.',
                   'screen_geometry':'Official full-rectangle diagonal and native pixel aspect. Centered punch hole, bezels and corner radius photoestimated.',
                   'camera_geometry':'Camera centers and outer clear windows fitted to front-on official rear render. Bumps, optical internals, glass and rings approximate; not manufacturer CAD.',
                   'glyphs':'Photo-fitted physical strip paths and widths, unlit diffuse surfaces. Phone 3 Matrix is a simplified inactive circular dot array; Phone 4a six white zones plus red indicator. No invented lit symbols.',
                   'finishes':'Official finish names; existing Documents sRGB palette, finish-tinted logo retained via make_device_branding. Uncalibrated PBR approximation.',
                   'branding':'Restrained reconstructed dot-matrix NOTHING mark, estimated size and position; tiny regulatory text omitted.',
                   'omissions':'Transparent internals reduced to low-contrast plates, coil traces and fasteners. Ports, antenna seams, microscopic circuits, actual translucency and programmable Glyph lighting omitted.'},
       'sources':['https://nothing.tech/products/phone-'+key],
       'rear_reference':{'file':'research/nothing/'+REFS[key][0],'body_bounds_px':REFS[key][1],
                         'uncertainty_mm':1.0,'bump_uncertainty_mm':.8,'note':'Photo fit, not measured CAD. Rear X mirrored into front-view model coordinates.'}}
    return apply_branding(p)


if __name__=='__main__':
    sources=json.loads((BASE/'research/nothing/image-urls.json').read_text())
    more=json.loads((BASE/'research/nothing/3a-urls.json').read_text())
    refs={'2':sources['2'][0],'3':sources['3'][6],'4a':sources['4a'][7],
          '3a':more['3a'][6],'3a-pro':more['3a-pro'][5]}
    measurements={}
    for key in MODELS:
        p=make(key);p['sources'].append(refs[key])
        if key=='2':p['sources'].append('https://no.nothing.tech/pages/phone-2')
        if key in ('3a','3a-pro'):p['sources'].append('https://nl.nothing.tech/products/phone-'+key)
        if key=='4a':p['sources'].extend(['https://support.nothing.tech/hc/en-us/categories/40129777015569-Nothing-Phone-4a','https://prtimes.jp/main/html/rd/p/000000054.000082566.html'])
        (BASE/'profiles'/(p['id']+'.json')).write_text(json.dumps(p,indent=2)+'\n')
        measurements[p['id']]={'gallery_model':p['gallery_model'],'sources':p['sources'],'reference':p['rear_reference'],
                              'body_mm':p['body_mm'],'screen':p['screen'],'camera':p['camera'],'glyphs':p['nothing_glyphs']}
        for glyph in measurements[p['id']]['glyphs']:
            if 'points_mm' in glyph:
                glyph['centerline_length_mm']=round(sum(math.dist(a,b) for a,b in zip(glyph['points_mm'],glyph['points_mm'][1:])),3)
        if key=='4a':
            measurements[p['id']]['glyph_bar']={'white_segments':6,'red_indicator':1,'segment_mm':[3.4,2.9],'pitch_mm':round(p['body_mm']['height']*.0208,3)}
    (BASE/'research/nothing-measurements.json').write_text(json.dumps(measurements,separators=(',',':'))+'\n')
    print('Generated five Nothing profiles')
