"""Remaining Samsung slabs. Run normally for profiles; in Blender with -- --build for exports.

The Blender-only hooks add legacy bezel hardware and preserve independently estimated
chassis corners on rectangular/early Infinity displays. Shared builders stay untouched.
"""
import copy
from make_device_branding import apply as apply_branding
import json
import math
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
if '--build' not in sys.argv:
    from make_samsung_profiles import DOCUMENTS, finish_name, logo_contours, rgb
    from generate_galaxy_svgs import PHONES, HOUSING, TONES, SAMPLED, fitted_island
    from generate_galaxy_s25_s26_svgs import MODELS, COLORS

# Width, height, thickness (mm); full rectangle diagonal (in); native portrait pixels;
# photo-estimated chassis and display corner radii (mm). No industrial CAD is claimed.
DEVICES = {
    'a34': (78.1,161.3,8.2,6.6,1080,2340,10,6.5),
    'a35': (78,161.7,8.2,6.6,1080,2340,10,6.5),
    'a36': (78.2,162.9,7.4,6.7,1080,2340,10,7),
    'a37': (78.2,162.9,7.4,6.7,1080,2340,10,7),
    'a54': (76.7,158.2,8.2,6.4,1080,2340,10,6),
    'a55': (77.4,161.1,8.2,6.6,1080,2340,10,6.5),
    'a56': (77.5,162.2,7.4,6.7,1080,2340,10,7),
    'a57': (76.8,161.5,6.9,6.7,1080,2340,10,7.5),
    's6': (70.5,143.4,6.8,5.1,1440,2560,9,.3),
    's6_edge': (70.1,142.1,7,5.1,1440,2560,9,.3),
    's6_edge_plus': (75.8,154.4,6.9,5.7,1440,2560,9,.3),
    's7': (69.6,142.4,7.9,5.1,1440,2560,9,.3),
    's7_edge': (72.6,150.9,7.7,5.5,1440,2560,9,.3),
    's8': (68.1,148.9,8,5.8,1440,2960,10,7),
    's8_plus': (73.4,159.5,8.1,6.2,1440,2960,10,7),
    's9': (68.7,147.7,8.5,5.8,1440,2960,10,7),
    's9_plus': (73.8,158.1,8.5,6.2,1440,2960,10,7),
    's10': (70.4,149.9,7.8,6.1,1440,3040,10,8),
    's10_5g': (77.1,162.6,7.94,6.7,1440,3040,10,8),
    's10_lite': (75.6,162.5,8.1,6.7,1080,2400,10,7),
    's10_plus': (74.1,157.6,7.8,6.4,1440,3040,10,8),
    's10e': (69.9,142.2,7.9,5.8,1080,2280,10,7.5),
    's20': (69.1,151.7,7.9,6.2,1440,3200,10,8),
    's20_fe': (74.5,159.8,8.4,6.5,1080,2400,10,7),
    's20_plus': (73.7,161.9,7.8,6.7,1440,3200,10,8),
    's20_ultra': (76,166.9,8.8,6.9,1440,3200,10,8),
    's21': (71.2,151.7,7.9,6.2,1080,2400,10,8),
    's21_fe': (74.5,155.7,7.9,6.4,1080,2340,10,7),
    's21_plus': (75.6,161.5,7.8,6.7,1080,2400,10,8),
    's21_ultra': (75.6,165.1,8.9,6.8,1440,3200,8,6),
    's22': (70.6,146,7.6,6.1,1080,2340,10,8),
    's22_plus': (75.8,157.4,7.6,6.6,1080,2340,10,8),
    's22_ultra': (77.9,163.3,8.9,6.8,1440,3088,2.5,1),
    's23': (70.9,146.3,7.6,6.1,1080,2340,10,8),
    's23_fe': (76.5,158,8.2,6.4,1080,2340,10,6.5),
    's23_plus': (76.2,157.8,7.6,6.6,1080,2340,10,8),
    's23_ultra': (78.1,163.4,8.9,6.8,1440,3088,2.5,1),
    's24_fe': (77.3,162,8,6.7,1080,2340,10,7),
    's25_edge': (75.6,158.2,5.8,6.7,1440,3120,10,8),
    's25_fe': (76.6,161.3,7.4,6.7,1080,2340,10,8),
    's26_fe': (76.9,161.6,7.4,6.7,1080,2340,10,8),
}

# Grouped manufacturer announcements/specification sheets; regional finish availability varies.
SOURCES = {
    's6': 'https://www.samsungmobilepress.com/articles/beautifully-crafted-from-metal-and-glass-samsung-galaxy-s6-and-galaxy-s6-edge-define-whats-next-in-mobility',
    's6_edge_plus': 'https://api.samsungmobilepress.com/press-releases/samsung-stays-ahead-of-the-curve-with-bold-big-screen-smartphones',
    's7': 'https://news.samsung.com/us/samsung-introduces-galaxy-s7-galaxy-s7-edge-center-new-mobile-world/',
    's8': 'https://news.samsung.com/es/samsung-presenta-samsung-galaxy-s8-un-smartphone-sin-limites',
    's9': 'https://news.samsung.com/uk/built-for-the-way-we-communicate-today-samsung-galaxy-s9-and-s9',
    's10': 'https://news.samsung.com/uk/samsung-raises-the-bar-with-galaxy-s10-more-screen-cameras-and-choices',
    's10_lite': 'https://api.samsungmobilepress.com/press-releases/samsung-brings-galaxy-to-more-people-introducing-galaxy-s10-lite-and-note10-lite',
    's20': 'https://www.samsungsvc.co.kr/solution/25670',
    's20_fe': 'https://news.samsung.com/us/samsung-galaxy-s20-fe-fan-edition-accessible-price-point-favorite-features/',
    's21': 'https://news.samsung.com/tw/samsung-galaxy-s21%EF%B8%B1s21',
    's21_ultra': 'https://news.samsung.com/es/samsung-galaxy-s21-ultra-5g-una-experiencia-movil-epica-en-todos-los-sentidos',
    's21_fe': 'https://news.samsung.com/in/samsung-unveils-galaxy-s21-fe-5g-in-india-at-effective-price-of-inr-49999',
    's22': 'https://www.samsung.com/uk/support/mobile-devices/enjoy-the-epic-standard-of-smartphone-experiences-with-the-galaxy-s22-series/',
    's23': 'https://images.samsung.com/is/content/samsung/assets/global/ir/docs/2023_3Q_Interim_Report.pdf',
    's23_fe': 'https://www.samsung.com/africa_en/support/mobile-devices/specifications-for-the-new-galaxy-s23-fe/',
    's24_fe': 'https://api.samsungmobilepress.com/press-releases/galaxy-s24-series-expands-with-s24-fe-a-premium-experience-that-makes-full-galaxy-ai-capabilities-attainable-for-more-users',
    's25_edge': 'https://news.samsung.com/global/meet-the-samsung-galaxy-s25-edge-an-engineering-marvel-of-new-slim-hardware-innovation',
    's25_fe': 'https://news.samsung.com/global/meet-samsung-galaxy-s25-fe-the-gateway-to-the-galaxy-ai-and-flagship-essentials',
    's26_fe': 'https://news.samsung.com/uk/samsung-galaxy-s26-fe-delivering-the-latest-flagship-experience-focused-on-what-matters-most',
    'a34': 'https://news.samsung.com/be_fr/les-samsung-galaxy-a54-5g-et-galaxy-a34-5g-lexperience-samsung-galaxy-absolue-pour-tout-le-monde',
    'a35': 'https://api.samsungmobilepress.com/press-releases/samsung-galaxy-a55-5g-and-galaxy-a35-5g-awesome-innovations-and-security-engineered-for-everyone',
    'a36': 'https://news.samsung.com/ph/samsung-marks-a-step-forward-with-ai-for-everyone-by-introducing-new-galaxy-a56-5g-and-galaxy-a36-5g',
    'a37': 'https://www.samsungmobilepress.com/articles/samsung-galaxy-a57-a37-5g-pro-features-awesome-price',
}
SOURCE_GROUPS = {
    's6_edge':'s6', 's7_edge':'s7', 's8_plus':'s8', 's9_plus':'s9',
    's10e':'s10', 's10_plus':'s10', 's10_5g':'s10', 's20_plus':'s20',
    's20_ultra':'s20', 's21_plus':'s21', 's22_plus':'s22', 's22_ultra':'s22',
    's23_plus':'s23', 's23_ultra':'s23', 'a54':'a34', 'a55':'a35', 'a56':'a36', 'a57':'a37',
}
EARLY = {'s6','s6_edge','s6_edge_plus','s7','s7_edge'}
BEZEL_SELFIE = EARLY | {'s8','s8_plus','s9','s9_plus'}
CURVES = {'s6_edge':1.5,'s6_edge_plus':1.6,'s7_edge':1.7,'s8':1.7,'s8_plus':1.8,
          's9':1.5,'s9_plus':1.6,'s10':1.3,'s10_plus':1.4,'s10_5g':1.4,
          's20':.55,'s20_plus':.6,'s20_ultra':.65,'s21_ultra':.9,
          's22_ultra':1,'s23_ultra':.65}


def palette(key):
    values = SAMPLED.get(key, COLORS.get(key))
    result = {}
    for name, stops in values.items():
        label = finish_name(name)
        # Existing icon keys shorten these published names.
        label = {'Icy Blue':'Icyblue', 'Titanium Icy Blue':'Titanium Icyblue',
                 'Jet Black':'Jetblack', 'Titanium Jet Black':'Titanium Jetblack',
                 'Light Violet':'Awesome Lavender', 'Graygreen':'Awesome Graygreen'}.get(label,label)
        if key in ('a37','a57') and not label.startswith('Awesome '):
            label = 'Awesome '+label
        c = rgb(stops[1])
        rail = [v*.75+.14 for v in c]
        tone = HOUSING.get(key, {}).get(name)
        bar = rgb(TONES[tone][1]) if tone and tone != 'body' else [v*.92+.04 for v in c]
        if tone and tone!='body':
            light=rgb(TONES[tone][0])
            bar=[(a+b)/2 for a,b in zip(light,bar)]
            rail=bar[:]
        if PHONES.get(key,{}).get('module') or PHONES.get(key,{}).get('chip') or PHONES.get(key,{}).get('island') == 'glass':
            bar = [.018,.022,.03]
        result[label] = {'back':{'rgb':c,'rough':.2 if key in BEZEL_SELFIE else .36},
                         'rail':{'rgb':rail,'metal':.8,'rough':.27},
                         'bar':{'rgb':bar,'metal':.55,'rough':.27},
                         'logo':{'rgb':[.62,.64,.68] if sum(c)<1.1 else [.13,.14,.16]}}
        if key in EARLY:
            result[label]['front_bezel'] = {'rgb':c,'rough':.22}
    return result


def make(key):
    w,h,d,diag,px,py,r,sr = DEVICES[key]
    g = copy.deepcopy(PHONES.get(key, MODELS.get(key)))
    scale = diag*25.4/math.hypot(px,py)
    sw,sh = px*scale,py*scale
    xy = lambda x,y: [w/2-x*w,h/2-y*w]
    finishes = palette(key)
    selected = next(iter(finishes))
    materials = copy.deepcopy(finishes[selected])
    materials.update(black={'rgb':[.006,.008,.011],'rough':.4},
                     flash={'rgb':[.86,.84,.73],'rough':.4},
                     front_sensor={'rgb':[.035,.047,.069],'rough':.23},
                     front_speaker={'rgb':[.09,.095,.105],'rough':.65})
    cam = {'center_mm':[0,0],'size_mm':[1,1,.5],'bump_mm':0,
           'optical_bump_mm':1.25,'lens_ring_mm':.35,'windows':[], 'lenses':[],
           'flash':[[*xy(*g['flash'][:2]),g['flash'][2]*w/2]],
           'sensors':[], 'flash_surface':'body','sensor_surface':'body' if key in BEZEL_SELFIE else 'housing',
           'skip_source_pupil':True}
    if g.get('module') or g.get('chip'):
        x,y,cw,ch,cr = g.get('module',g.get('chip'))
        cam.update(center_mm=xy(x+cw/2,y+ch/2),size_mm=[cw*w,ch*w,cr*w],
                   bump_mm=.75 if key.startswith(('s7','s8','s9')) else 1.3,
                   optical_bump_mm=.18,lens_ring_mm=0,roll_mm=.12,integrated_plateau=True)
        cam['flash_surface'] = 'body' if key in BEZEL_SELFIE else 'housing'
    elif g.get('housing'):
        cw,ch,cr = g['housing']
        cam.update(center_mm=xy(cw/2,ch/2),size_mm=[cw*w,ch*w,cr*w],
                   bump_mm=1.1,optical_bump_mm=.35,lens_ring_mm=.28,
                   roll_mm=.15,integrated_plateau=True)
    elif g.get('island'):
        if isinstance(g['island'],str):
            x0,y0,x1,y1 = fitted_island(g,0,0,1,margin=.045)
        else:
            x0,y0,x1,y1 = g['island']
        cw,ch = (x1-x0)*w,(y1-y0)*w
        cam.update(center_mm=xy((x0+x1)/2,(y0+y1)/2),size_mm=[cw,ch,cw/2],
                   bump_mm=.8,optical_bump_mm=.5,lens_ring_mm=.25,
                   roll_mm=.15,integrated_plateau=True)
        if key == 's25_edge':
            cam['flash_surface'] = 'housing'

    def window(x,y,ww,wh,rr,kind='main'):
        center = xy(x,y)
        cam['windows'].append([*center,ww*w,wh*w,rr*w])
        cam['lenses'].append({'kind':kind,'center_mm':center,
                              'radius_mm':min(ww,wh)*w*.29,
                              'window':len(cam['windows'])-1})

    if key in BEZEL_SELFIE:
        x,y,cw,ch,cr = g['chip']
        if key == 's9_plus':
            for cy in (y+ch*.27,y+ch*.73):
                window(x+cw/2,cy,cw*.82,cw*.82,cw*.2)
        else:
            window(x+cw/2,y+ch/2,cw*.83,ch*.83,cr*.8)
    elif key in ('s10','s10e','s10_plus','s10_5g'):
        # Individual lens centres within the measured horizontal cover; photo estimates.
        xs = {'s10e':(.34,.53),'s10':(.27,.44,.60),
              's10_plus':(.28,.44,.59),'s10_5g':(.23,.39,.55)}[key]
        cy = g['chip'][1]+g['chip'][3]/2
        for index,x in enumerate(xs):
            window(x,cy,.115,.115,.0575,'main' if index==1 else 'ultrawide')
        if key == 's10_5g':
            cam['sensors'].append([*xy(.66,cy),w*.023])
    else:
        for index,(x,y,diam) in enumerate(g['lenses']):
            if ('ultra' in key and index == (2 if key=='s20_ultra' else 2 if key=='s21_ultra' else 3)):
                cam['sensors'].append([*xy(x,y),diam*w/2])
                continue
            if key == 's20_plus' and index == 3:
                cam['sensors'].append([*xy(x,y),diam*w/2])
                continue
            glass = diam-2*cam['lens_ring_mm']/w
            kind = 'main' if index==1 else 'ultrawide'
            if key in ('s22_ultra','s23_ultra') and index==2:
                kind='periscope'
            window(x,y,glass,glass,glass/2,kind)
        if g.get('periscope'):
            x,y,ww,wh = g['periscope']
            window(x,y,ww,wh,min(ww,wh)*.24,'periscope')
    for name in ('sensor','fingerprint'):
        if g.get(name):
            x,y,ww,wh = g[name]
            cam['sensors'].append({'kind':name,'center_mm':xy(x+ww/2,y+wh/2),
                                   'size_mm':[ww*w,wh*w],'radius_mm':min(ww,wh)*w*.25})

    cuts=[]
    if key == 'a34':
        cuts=[{'center_mm':[0,sh/2-1.8],'radius_mm':2.5,'size_mm':[5,7]}]
    elif key not in BEZEL_SELFIE:
        if key in ('s10','s10e','s10_plus','s10_5g'):
            capsule = key in ('s10_plus','s10_5g')
            cuts=[{'center_mm':[sw/2-(9 if capsule else 5),sh/2-5.5],
                   'radius_mm':2.1,**({'size_mm':[12 if key=='s10_5g' else 10,4.2]} if capsule else {})}]
        else:
            cuts=[{'center_mm':[0,sh/2-3.8],'radius_mm':1.4}]
    source = SOURCES[SOURCE_GROUPS.get(key,key)]
    p = {'id':'galaxy-'+key.replace('_','-'),
         'name':'Galaxy '+key[0].upper()+key[1:].replace('_edge_plus',' edge+').replace('_edge',' edge').replace('_plus','+').replace('_ultra',' Ultra').replace('_fe',' FE').replace('_lite',' Lite').replace('_5g',' 5G'),
         'manufacturer':'Samsung','form_factor':'phone','status':'provisional','finish':selected,
         'body_mm':{'width':w,'height':h,'depth':d,'corner_radius':r,
                    'edge_roll_mm':[1.15 if key in CURVES else .35,.25],
                    'front_rail_mm':.4,'rear_inset':.4},
         'materials':materials,'finishes':finishes,
         'screen':{'object':'Device screen','node':'Device screen','panel':'Body',
                   'resolution':[px,py],'fit_box_mm':[sw,sh],'center_mm':[0,0,d/2+.035],
                   'corner_radius_mm':sr,'edge_curve_mm':CURVES.get(key,0),
                   'create_cutouts':True,'cutouts':cuts},
         'camera':cam,'buttons':[
             {'name':'Volume','side':'left' if key in BEZEL_SELFIE or key.startswith('s10') and key!='s10_lite' else 'right',
              'center_y_mm':h/2-36,'length_mm':21,'width_mm':2.4,'thickness_mm':.35,'radius_mm':1},
             {'name':'Power','side':'right','center_y_mm':h/2-60,'length_mm':12,
              'width_mm':2.4,'thickness_mm':.35,'radius_mm':1}],
         'rear_logo':{'kind':'samsung','center_mm':[0,h*(.16 if key.startswith(('s6','s7','s8')) else -.04 if key=='s9_plus' else .05 if key=='s9' else -.405)],
                      'contours_mm':logo_contours(w*.28)},
         'accuracy':{
             'body_dimensions':'Samsung published chassis dimensions. Corner radii, edge rolls and curvature are photo estimates, not CAD.',
             'screen_resolution':'Samsung native resolution. Active rectangle calculated from rounded published full diagonal and native aspect; physical bezel widths therefore approximate.',
             'screen_geometry':'Model-specific flat/dual-edge display, rectangular/rounded corners, bezel selfie or Infinity-O aperture. Radii, hole positions and curve depth are photo estimates.',
             'camera_geometry':'Model-specific rear layout scaled from generate_galaxy_svgs.PHONES / base MODELS official-render measurements. Internal optics, radii and protrusions illustrative; early cover internal lens positions estimated from photographs. Laser/ToF/heart-rate/fingerprint features distinguished from imaging lenses.',
             'finishes':'Published finish names; approximate sampled sRGB and material response. S21+ Phantom Violet uses muted rose champagne camera housing.',
             'omissions':'USB/headphone ports, speaker perforations, antenna seams and S Pen silo omitted. Legacy capacitive navigation marks and bezel hardware simplified.'},
         'sources':[source], 'samsung_legacy':{'key':key,'independent_corners':key in BEZEL_SELFIE,
                                             'dark_rings':g.get('ring')=='dark',
                                             'contour_cut':bool(g.get('housing')) and key!='s21_fe'}}
    if key in ('s8','s8_plus','s9','s9_plus','s10','s10_plus','s10e','s10_5g'):
        p['buttons'].append({'name':'Bixby','side':'left','center_y_mm':h/2-64,
                             'length_mm':10,'width_mm':2.4,'thickness_mm':.35,'radius_mm':1})
    if key in BEZEL_SELFIE:
        top=(h+sh)/4
        p['samsung_legacy']['front_details']=[
            {'name':'Bezel earpiece','center_mm':[0,top+2],'size_mm':[10,1.1],'radius_mm':.5,'material':'front_speaker'},
            {'name':'Bezel selfie camera','center_mm':[w*.24,top+1.5],'radius_mm':1.7,'material':'front_sensor'},
            {'name':'Bezel proximity sensor','center_mm':[-w*.21,top+1.5],'size_mm':[3.8,1.3],'radius_mm':.6,'material':'front_sensor'}]
        if key in EARLY:
            p['samsung_legacy']['front_details'] += [
                {'name':'Home button rim','center_mm':[0,-top],'size_mm':[16,5.9],'radius_mm':2.8,'material':'rail'},
                {'name':'Home fingerprint button','center_mm':[0,-top],'size_mm':[14.6,4.7],'radius_mm':2.2,'material':'front_bezel','rise_mm':.07}]
        else:
            p['samsung_legacy']['front_details'].append(
                {'name':'Bezel iris camera','center_mm':[-w*.31,top+1.5],'radius_mm':1.3,'material':'front_sensor'})
    if key=='s26_fe':
        p['sources'].append('https://www.samsung.com/uk/smartphones/galaxy-s/galaxy-s26-fe-graphite-256gb-sm-s741bzkgeub/')
    return p


def validate_profile(p):
    """Check source profiles before paying the Blender startup/render cost."""
    b,s,c=p['body_mm'],p['screen'],p['camera']
    w,h=s['fit_box_mm']; px,py=s['resolution']
    assert w<b['width'] and h<b['height'] and abs(w/h-px/py)<1e-10,p['id']
    for i,win in enumerate(c['windows']):
        x,y,ww,wh,r=win; ring=c['lens_ring_mm']
        assert abs(x)+ww/2+ring<b['width']/2 and abs(y)+wh/2+ring<b['height']/2,(p['id'],i,'bounds')
        for other in c['windows'][:i]:
            xx,yy,www,hhh,_=other
            assert abs(x-xx)>(ww+www)/2+2*ring or abs(y-yy)>(wh+hhh)/2+2*ring,(p['id'],i,'overlap')
        for fx,fy,fr in c['flash']:
            assert math.hypot(x-fx,y-fy)>max(ww,wh)/2+ring+fr,(p['id'],i,'flash')
    return p


def install_blender_details():
    import bpy
    import geometry
    import build
    original_create,original_sync=geometry.create_device,build.sync_slab_body_corners

    def sync(profile):
        if not profile.get('samsung_legacy',{}).get('independent_corners'):
            original_sync(profile)

    def create(profile):
        root=original_create(profile)
        spec=profile.get('samsung_legacy',{})
        body=profile['body_mm']; parent=next(o for o in root.children if o.name=='Body')
        if spec.get('key') in ('s22_ultra','s23_ultra'):
            # Narrow corner arcs leave no central vertices on the enclosure's front cap.
            # Sample its long edges before the shared screen builder rolls the sides, so
            # the flat middle retains the published thickness instead of sinking with them.
            import bmesh
            for obj in parent.children:
                glass=obj.name.startswith('Front black glass')
                if not glass and not obj.name.startswith('Aluminum enclosure'):
                    continue
                mesh=bmesh.new(); mesh.from_mesh(obj.data)
                edges=[edge for edge in mesh.edges
                       if abs(edge.verts[0].co.x-edge.verts[1].co.x)>.02
                       and abs(edge.verts[0].co.y-edge.verts[1].co.y)<1e-8
                       and (glass or all(v.co.z>0 for v in edge.verts))]
                bmesh.ops.subdivide_edges(mesh,edges=edges,cuts=64,use_grid_fill=False)
                mesh.to_mesh(obj.data); mesh.free(); obj.data.update()
        if spec.get('dark_rings'):
            for obj in parent.children:
                if obj.name.startswith('Camera lens rim'):
                    obj.data.materials[0]=bpy.data.materials['front_sensor']
        if spec.get('key') in EARLY:
            glass=next(o for o in parent.children if o.name.startswith('Front black glass'))
            glass.data.materials[0]=bpy.data.materials['front_bezel']
            sh=profile['screen']['fit_box_mm'][1]
            for index,contour in enumerate(profile['rear_logo']['contours_mm']):
                mesh=bpy.data.meshes.new(f'Front wordmark {index}')
                mesh.from_pydata([(x*.001,(-y+(body['height']+sh)/4-3)*.001,
                                  (body['depth']/2+.06)*.001) for x,y in contour],[],[tuple(range(len(contour)))])
                mesh.materials.append(bpy.data.materials['logo'])
                obj=bpy.data.objects.new(f'Front Samsung logo | {index}',mesh)
                bpy.context.scene.collection.objects.link(obj); obj.parent=parent
        for item in spec.get('front_details',[]):
            x,y=item['center_mm']; z=body['depth']/2+.055+item.get('rise_mm',0)
            mat=bpy.data.materials[item['material']]
            if item.get('size_mm'):
                ww,hh=item['size_mm']
                geometry.slab(item['name'],ww,hh,.045,item['radius_mm'],(x,y,z),mat,parent,.01)
            else:
                geometry.disk(item['name'],x,y,z,item['radius_mm'],.045,mat,parent)
        # Clip contour-cut housings to the same enclosure outline as the source icon;
        # the top/side boundaries meet the rail rather than forming a detached island.
        key=spec.get('key')
        if spec.get('contour_cut'):
            housing=bpy.data.objects.get('Camera housing')
            if housing:
                cw,ch,cr=profile['camera']['size_mm']
                # Rear-view left/top and bottom-right corners, mirrored into model X.
                radii=[.05,body['corner_radius'],.05,cr]
                replacement=geometry.slab('Contour-cut housing',cw,ch,profile['camera']['bump_mm'],radii,
                    (*profile['camera']['center_mm'],-body['depth']/2-profile['camera']['bump_mm']/2),
                    bpy.data.materials['bar'],parent,.15)
                for wx,wy,ww,wh,wr in profile['camera']['windows']:
                    cutter=geometry.slab('Contour camera cutter',ww,wh,profile['camera']['bump_mm']+.4,wr,
                        (wx,wy,-body['depth']/2-profile['camera']['bump_mm']/2-.15),None,parent,.03)
                    geometry.subtract(replacement,cutter)
                bpy.data.objects.remove(housing,do_unlink=True)
                replacement.name='Camera housing'
        return root

    build.sync_slab_body_corners=sync
    geometry.create_device=create


def verify_exports():
    import struct
    from verify_samsung import verify as verify_slab
    from verify_pixels import verify as verify_geometry, rounded_distance
    from PIL import Image, ImageDraw
    results=[]
    for key in DEVICES:
        path=BASE/'profiles'/f"galaxy-{key.replace('_','-')}.json"
        p=json.loads(path.read_text()); out=BASE/'exports'/p['id']
        result=verify_slab(path)
        if key not in BEZEL_SELFIE:
            result.update(verify_geometry(path))
        else:
            # The Pixel slab check assumes concentric body/display corners. Early Samsung
            # rectangular displays have independent chassis corners; check actual mesh bounds.
            raw=(out/'model.glb').read_bytes()
            size=struct.unpack_from('<I',raw,12)[0]; gltf=json.loads(raw[20:20+size])
            nodes={n.get('name'):n for n in gltf['nodes']}
            def bounds(name):
                node=nodes[name]
                primitive=gltf['meshes'][node['mesh']]['primitives'][0]
                return gltf['accessors'][primitive['attributes']['POSITION']],primitive
            enclosure,_=bounds('Aluminum enclosure'); b=p['body_mm']
            for axis,expected in enumerate((b['width'],b['depth']-.05,b['height'])):
                assert abs(enclosure['max'][axis]-enclosure['min'][axis]-expected*.001)<1e-6,(p['id'],'enclosure',axis)
            screen,primitive=bounds('Device screen'); sw,sh=p['screen']['fit_box_mm']
            assert abs(screen['max'][0]-screen['min'][0]-sw*.001)<1e-6,p['id']
            assert abs(screen['max'][2]-screen['min'][2]-sh*.001)<1e-6,p['id']
            assert 'TEXCOORD_0' in primitive['attributes'] and not p['screen']['cutouts'],p['id']
            assert 'Bezel selfie camera' in nodes and 'Bezel earpiece' in nodes,p['id']
            assert ('Home fingerprint button' in nodes)==(key in EARLY),p['id']
            for lens in p['camera']['lenses']:
                win=p['camera']['windows'][lens['window']]
                assert -rounded_distance(lens['center_mm'],win)-lens['radius_mm']*1.02>.1,p['id']
            result.update(screen_aspect=True,exported_screen_bounds=True,enclosure_bounds=True,
                          triangles=sum(gltf['accessors'][primitive['indices']]['count']//3
                                        for mesh in gltf['meshes'] for primitive in mesh['primitives']),
                          glb_bytes=len(raw),
                          corner_check='Independent legacy chassis/display corners retained; Pixel concentric-corner assertion inapplicable')
            (out/'geometry-checks.json').write_text(json.dumps(result,indent=2)+'\n')
        meta=json.loads((out/'device.json').read_text())
        assert list(meta['finishes'])==list(p['finishes']),(p['id'],'finish names')
        results.append(result)
    (BASE/'research/samsung-legacy-verification.json').write_text(json.dumps(results,indent=2)+'\n')
    # All-model front/rear contact sheet plus larger representative hardware views.
    sheet=Image.new('RGB',(1400,6*166),'#22252a'); draw=ImageDraw.Draw(sheet)
    for index,key in enumerate(DEVICES):
        pid='galaxy-'+key.replace('_','-'); x=(index%7)*200; y=(index//7)*166
        draw.text((x+5,y+3),pid,fill='white')
        for col,view in enumerate(('front','rear')):
            im=Image.open(BASE/'exports'/pid/f'{view}.png').convert('RGBA')
            im.thumbnail((98,142)); sheet.paste(im,(x+col*100+(100-im.width)//2,y+20),im)
    sheet.save(BASE/'research/samsung-legacy-contact.png')
    cases=[('s6_edge','front'),('s6_edge','end'),('s9_plus','front'),('s9_plus','rear'),
           ('s10e','front'),('s10_plus','front'),('s20_ultra','rear-angle'),('s21_ultra','rear-angle'),
           ('s21_plus','finish-0'),('s22_ultra','rear-angle'),('a34','front'),('a57','rear-angle'),
           ('s23_ultra','rear-angle'),('s25_edge','rear-angle'),('s25_edge','side'),('s26_fe','rear-angle')]
    sheet=Image.new('RGB',(960,4*300),'#22252a'); draw=ImageDraw.Draw(sheet)
    for index,(key,view) in enumerate(cases):
        x=(index%4)*240; y=(index//4)*300
        draw.text((x+5,y+4),key+' / '+view,fill='white')
        im=Image.open(BASE/'exports'/('galaxy-'+key.replace('_','-'))/f'{view}.png').convert('RGBA')
        im.thumbnail((235,275)); sheet.paste(im,(x+(240-im.width)//2,y+22+(275-im.height)//2),im)
    sheet.save(BASE/'research/samsung-legacy-details.png')
    print(f'Passed {len(results)} exports; wrote two diagnostic contact sheets')


def main():
    if '--verify' in sys.argv:
        verify_exports()
        return
    if '--build' in sys.argv:
        keys=list(DEVICES)
        if '--from' in sys.argv:
            keys=keys[keys.index(sys.argv[sys.argv.index('--from')+1]):]
        if '--only' in sys.argv:
            keys=sys.argv[sys.argv.index('--only')+1].split(',')
        profiles=[validate_profile(json.loads((BASE/'profiles'/f"galaxy-{key.replace('_','-')}.json").read_text())) for key in keys]
        install_blender_details()
        from build_pixels import build,review
        for p in profiles:
            output=BASE/'exports'/p['id']
            build(BASE/'profiles'/f"{p['id']}.json",output)
            review(output,finishes=True)
            print('FINISHED '+p['id'],flush=True)
        return
    profiles=[validate_profile(make(key)) for key in DEVICES]
    for p in profiles:
        apply_branding(p)
        (BASE/'profiles'/f"{p['id']}.json").write_text(json.dumps(p,indent=2)+'\n')
    research={'checked':'2026-10-18','units':'mm; diagonal inches; portrait native pixels',
              'build_command':'blender.exe -b -t 4 --python make_samsung_legacy_profiles.py -- --build',
              'source_geometry':str(DOCUMENTS/'generate_galaxy_svgs.py'),
              'source_palettes':str(DOCUMENTS/'galaxy_colors.json'),
              'estimates':'Chassis/display radii, edge curvature, bezel/selfie/control positions, protrusions and optical internals are photo estimates. Full display rectangle derives from rounded published diagonal.',
              'body_dimension_order':['width','height','depth'],
              'models':[{'id':p['id'],'body_mm':list(DEVICES[key][:3]),
                         'diagonal_in':DEVICES[key][3],'resolution':p['screen']['resolution'],
                         'imaging_lenses':len(p['camera']['lenses']),'finishes':list(p['finishes']),
                         'sources':p['sources']} for key,p in zip(DEVICES,profiles)],'pending':[]}
    (BASE/'research/samsung-legacy-specs.json').write_text(json.dumps(research,indent=2)+'\n')
    print(f'Validated {len(profiles)} source profiles; {sum(len(p["finishes"]) for p in profiles)} finishes',flush=True)


if __name__=='__main__':
    main()
