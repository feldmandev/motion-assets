"""Generate Apple profiles from sourced device dimensions and accessory drawings."""
import copy
from make_device_branding import apply as apply_branding
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent


def rgb(color):
    return [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]


def generation(model_id):
    try:
        return int(model_id.split('-')[1].rstrip('e'))
    except (ValueError, IndexError):
        return None


# Millimetres from the top chassis datum to each control centre, read from Apple's accessory
# dimensional drawings.  Plus/Max drawings retain the same control datum as their smaller sibling
# unless Apple publishes a different value.
CONTROL_DATUMS = {
    'iphone-11': {'ring':23.39, 'volume_up':36.09, 'volume_down':49.20, 'side':42.65},
    'iphone-11-pro': {'ring':24.72, 'volume_up':37.64, 'volume_down':51.37, 'side':44.61},
    'iphone-11-pro-max': {'ring':24.72, 'volume_up':37.64, 'volume_down':51.37, 'side':44.61},
    'iphone-12-mini': {'ring':23.37, 'volume_up':36.68, 'volume_down':50.68, 'side':43.68},
    'iphone-12': {'ring':25.99, 'volume_up':39.31, 'volume_down':53.31, 'side':46.31},
    'iphone-12-pro': {'ring':25.99, 'volume_up':39.31, 'volume_down':53.31, 'side':46.31},
    'iphone-12-pro-max': {'ring':33.34, 'volume_up':46.65, 'volume_down':60.65, 'side':53.65},
    'iphone-13-mini': {'ring':23.37, 'volume_up':36.68, 'volume_down':50.68, 'side':43.68},
    'iphone-13': {'ring':32.23, 'volume_up':45.53, 'volume_down':59.53, 'side':52.53},
    'iphone-13-pro': {'ring':32.22, 'volume_up':45.53, 'volume_down':59.53, 'side':52.53},
    'iphone-13-pro-max': {'ring':32.22, 'volume_up':45.53, 'volume_down':59.53, 'side':52.53},
    'iphone-14': {'ring':31.98, 'volume_up':45.43, 'volume_down':59.63, 'side':52.53},
    'iphone-14-plus': {'ring':31.98, 'volume_up':45.43, 'volume_down':59.63, 'side':52.53},
    'iphone-14-pro': {'ring':31.14, 'volume_up':44.59, 'volume_down':58.79, 'side':55.54},
    'iphone-14-pro-max': {'ring':31.14, 'volume_up':44.59, 'volume_down':58.79, 'side':55.54},
    'iphone-15': {'ring':32.83, 'volume_up':46.27, 'volume_down':60.47, 'side':53.37},
    'iphone-15-plus': {'ring':32.83, 'volume_up':46.27, 'volume_down':60.47, 'side':53.37},
    'iphone-15-pro': {'action':31.67, 'volume_up':45.22, 'volume_down':59.42, 'side':56.17},
    'iphone-15-pro-max': {'action':31.67, 'volume_up':45.22, 'volume_down':59.42, 'side':56.17},
    'iphone-16': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.33, 'camera':96.23},
    'iphone-16-plus': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.33, 'camera':109.48},
    'iphone-16-pro': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.33, 'camera':98.19},
    'iphone-16-pro-max': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.33, 'camera':111.62},
    'iphone-16e': {'action':31.20, 'volume_up':45.43, 'volume_down':59.63, 'side':52.53},
    'iphone-17': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.32, 'camera':98.20},
    'iphone-17-pro': {'action':34.28, 'volume_up':48.43, 'volume_down':62.63, 'side':55.53, 'camera':98.40},
    'iphone-17-pro-max': {'action':34.28, 'volume_up':48.43, 'volume_down':62.63, 'side':55.53, 'camera':111.82},
    'iphone-17e': {'action':31.20, 'volume_up':45.43, 'volume_down':59.63, 'side':52.53},
    'iphone-18-pro': {'action':34.28, 'volume_up':48.43, 'volume_down':62.63, 'side':55.53, 'camera':98.40},
    'iphone-18-pro-max': {'action':34.28, 'volume_up':48.43, 'volume_down':62.63, 'side':55.53, 'camera':111.82},
    'iphone-air': {'action':34.08, 'volume_up':48.23, 'volume_down':62.43, 'side':55.33, 'camera':104.77},
}


# Width/height and Y centre of the physical rear Apple mark from the recent drawings.  Older
# drawings depict the mark without a dimensioned keepout, so those keep the measured visual size.
LOGO_DATUMS = {
    'iphone-16': (15.75, 19.34, 72.19),
    'iphone-16-plus': (16.66, 20.46, 78.72),
    'iphone-16-pro': (16.32, 20.04, 73.12),
    'iphone-16-pro-max': (17.26, 21.20, 79.73),
    'iphone-17': (15.75, 19.34, 73.18),
    'iphone-17-pro': (16.32, 20.04, 95.30),
    'iphone-17-pro-max': (16.32, 20.04, 102.01),
    'iphone-18-pro': (16.32, 20.04, 91.20),
    'iphone-18-pro-max': (16.32, 20.04, 97.51),
    'iphone-air': (15.29, 18.70, 77.19),
}


def controls(device, body):
    model_id = device['id']
    gen = generation(model_id)
    datum = CONTROL_DATUMS.get(model_id)
    has_action = (model_id in {'iphone-15-pro','iphone-15-pro-max','iphone-air'} or
                  (gen is not None and gen >= 16 and model_id != 'iphone-duo'))
    has_camera = (model_id in {'iphone-air','iphone-duo'} or
                  (gen is not None and gen >= 16 and model_id not in {'iphone-16e','iphone-17e'}))
    if datum is None:
        # 11-14 drawings use the same top-to-control pattern but not the newer named datum table.
        datum = {'ring':body['height']*.212, 'volume_up':body['height']*.303,
                 'volume_down':body['height']*.400, 'side':body['height']*.375}
        if has_action:
            datum['action'] = body['height']*.230
        if has_camera:
            datum['camera'] = body['height']*.66

    def y(key):
        return body['height']/2-datum[key]

    result = [
        {'name':'Side button','side':'right','center_y_mm':y('side'),'length_mm':15.8,
         'width_mm':2.55,'thickness_mm':.45,'radius_mm':1.15},
        {'name':'Volume up','side':'left','center_y_mm':y('volume_up'),'length_mm':10.0,
         'width_mm':2.55,'thickness_mm':.45,'radius_mm':1.15},
        {'name':'Volume down','side':'left','center_y_mm':y('volume_down'),'length_mm':10.0,
         'width_mm':2.55,'thickness_mm':.45,'radius_mm':1.15},
    ]
    if model_id != 'iphone-duo':
        key = 'action' if has_action else 'ring'
        result.append({'name':'Action button' if has_action else 'Ring/Silent switch', 'side':'left',
                       'center_y_mm':y(key),'length_mm':9.0 if has_action else 5.5,
                       'width_mm':2.55,'thickness_mm':.45,'radius_mm':1.15})
    if has_camera and 'camera' in datum:
        result.append({'name':'Camera Control','side':'right','center_y_mm':y('camera'),
                       'length_mm':17.5,'width_mm':2.15,'thickness_mm':.16,
                       'radius_mm':1.0,'material':'black','inset_mm':.115})
    return result


def material_family(model_id):
    gen = generation(model_id)
    if '-pro' in model_id and gen is not None and gen <= 14:
        return 'stainless'
    if ('-pro' in model_id and gen in {15,16}) or model_id in {'iphone-air','iphone-duo'}:
        return 'titanium'
    if '-pro' in model_id and gen is not None and gen >= 17:
        return 'aluminum-unibody'
    return 'aluminum'


def subtle_logo_color(back):
    luminance = .2126*back[0]+.7152*back[1]+.0722*back[2]
    return ([min(1, value*.72+.20) for value in back] if luminance < .35 else
            [max(.12, value*.62) for value in back])


def profile(device):
    body = dict(device['body_mm'])
    front = device['front']
    camera = device['camera_geometry']
    gen = generation(device['id'])
    if device.get('edge_roll_mm'):
        edge_roll = device['edge_roll_mm']
    elif front.get('edge_style') == 'rounded':
        edge_roll = [2.0, 1.0]
    elif (gen is not None and gen >= 15) or device['id'] in {'iphone-air','iphone-duo'}:
        edge_roll = [.70, .58]
    else:
        edge_roll = [.30, .30]
    body.update(corner_radius=device.get('body_radius_mm',front['body_radius_mm']),
                edge_roll_mm=edge_roll, front_curve=0)
    family = material_family(device['id'])
    bar_is_metal = family == 'aluminum-unibody' or device['id'] in {'iphone-air','iphone-duo'}
    finishes = {}
    for color in device['colors']:
        back = rgb(color['hex'])
        rail = rgb(color.get('rail_hex', color['hex']))
        finishes[color['name']] = {'back': {'rgb': back}, 'rail': {'rgb': rail},
                                   'bar': {'rgb': rail if bar_is_metal else back},
                                   'logo': {'rgb': subtle_logo_color(back)}}
    rail_rough = {'stainless':.17, 'titanium':.31, 'aluminum-unibody':.34}.get(family, .30)
    materials = {'back': {'rgb': [0,0,0], 'rough': .38 if '-pro' in device['id'] else .25},
                 'rail': {'rgb': [0,0,0], 'metal': 1, 'rough': rail_rough},
                 'bar': {'rgb': [0,0,0], 'metal': 1 if bar_is_metal else 0,
                         'rough': .30 if bar_is_metal else .25},
                 'logo': {'rgb': [.22,.22,.22], 'metal': .92, 'rough': .18},
                 'black': {'rgb': [.007,.009,.012], 'rough': .5},
                 'flash': {'rgb': [.88,.87,.82], 'rough': .4}}
    finish = next(iter(finishes))
    for role, values in finishes[finish].items():
        materials[role].update(values)
    sw, sh = front['active_mm']
    cutouts = []
    if front.get('cutout'):
        cut = front['cutout']
        cw,ch = cut['size_mm']
        cutouts.append({'size_mm':[cw,ch], 'radius_mm':cut.get('radius_mm',ch/2),
                        'center_mm':[cut.get('x_mm',0),sh/2-cut['top_mm']-ch/2]})
        if cut.get('type', front.get('kind')) == 'notch':
            # A notch joins the bezel with concave shoulders; it is not a floating capsule.
            r, shoulder = min(1.6, ch/3), .7
            ch += .6
            points = [(-cw/2-shoulder,ch/2),(-cw/2-shoulder,ch/2-.6)]
            for cx,cy,a,b,rad in [(-cw/2-shoulder,ch/2-.6-shoulder,90,0,shoulder),
                                  (-cw/2+r,-ch/2+r,180,270,r),
                                  (cw/2-r,-ch/2+r,270,360,r),
                                  (cw/2+shoulder,ch/2-.6-shoulder,180,90,shoulder)]:
                points.extend((cx+rad*math.cos(math.radians(a+(b-a)*i/12)),
                               cy+rad*math.sin(math.radians(a+(b-a)*i/12))) for i in range(13))
            points.append((cw/2+shoulder,ch/2))
            cutouts[-1].update(size_mm=[cw,ch], radius_mm=r, outline_mm=points,
                               center_mm=[0,sh/2-(ch/2-.6)])
    screen = {'object':'Device screen', 'node':'Device screen', 'resolution':device['native_px'],
              'fit_box_mm':[sw,sh], 'center_mm':[0,front.get('center_y_mm',0),body['depth']/2+.035],
              'corner_radius_mm':device.get('display_radius_mm',front['display_radius_mm']), 'edge_curve_mm':0,
              'create_cutouts':True, 'cutouts':cutouts}
    if front.get('display_outline_mm'):
        screen['outline_mm'] = front['display_outline_mm']
    w,h,r = camera['island_mm']
    left,top = camera['inset_mm']
    # Rear-view left is positive X in the front-oriented model coordinates.
    cx,cy = body['width']/2-left-w/2,body['height']/2-top-h/2
    # 11-14 stores total back-glass -> camera-glass protrusion; 15+ stores the additional height
    # from the camera plateau to the camera glass as a separate drawing dimension.
    newer_depth_semantics = ((gen is not None and gen >= 15) or device['id'] == 'iphone-air')
    if camera.get('lens_bump_semantics') == 'total_from_body':
        optical_bump = max(0, camera['lens_bump_mm']-camera['plate_bump_mm'])
    else:
        optical_bump = (camera['lens_bump_mm'] if newer_depth_semantics else
                        max(0,camera['lens_bump_mm']-camera['plate_bump_mm']))
    spec = {'center_mm':[cx,cy], 'size_mm':[w,h,r], 'bump_mm':camera['plate_bump_mm'],
            'optical_bump_mm':optical_bump,
            'lens_ring_mm':camera.get('lens_ring_mm', .65), 'roll_mm':.18,
            'windows':[], 'lenses':[], 'flash':[], 'sensors':[], 'local_pupil':True,
            'integrated_plateau':camera.get('integrated_plateau', False)}
    for index,lens in enumerate(camera['lenses']):
        lx,ly = lens['center_from_top_left_mm']
        x,y = body['width']/2-left-lx,body['height']/2-top-ly
        radius = lens['diameter_mm']/2-spec['lens_ring_mm']
        spec['windows'].append([x,y,2*radius,2*radius,radius])
        spec['lenses'].append({'kind':lens.get('kind','main' if index==0 else 'ultrawide' if index==1 else 'main'),
                               'center_mm':[x,y], 'radius_mm':radius*.80, 'window':index})
    for field,target in [('flash','flash'),('sensors','sensors')]:
        dots = camera.get(field,[])
        if isinstance(dots,dict):
            dots = [dots]
        for dot in dots:
            x,y = dot['center_from_top_left_mm']
            center = [body['width']/2-left-x,body['height']/2-top-y]
            if dot.get('size_mm'):
                spec[target].append({'center_mm':center, 'size_mm':dot['size_mm'],
                                     'radius_mm':dot.get('radius_mm', min(dot['size_mm'])/2),
                                     'kind':dot.get('kind', field)})
            else:
                spec[target].append([*center,dot['diameter_mm']/2])

    if '-pro' in device['id'] and gen in {12,13,14} and not spec['sensors']:
        # LiDAR + rear mic are visible hardware on 12/13/14 Pro but absent from the older parsed
        # accessory keepout table.  Their layout follows the later Apple Pro camera drawings.
        spec['sensors'] = [[cx-.205*w, cy-.282*h, 3.15],
                           [cx-.335*w, cy-.221*h, .40]]

    # Narrow dual/single-camera layouts put the flash on the rear glass beside the camera pill.
    if spec['flash'] and any(abs(fx-cx)+fr > w/2 or abs(fy-cy)+fr > h/2
                             for fx,fy,fr in spec['flash']):
        spec['flash_surface'] = 'body'
    def outside_plateau(item):
        if isinstance(item, dict):
            sx, sy = item['center_mm']; sw, sh = item['size_mm']
            return abs(sx-cx)+sw/2 > w/2 or abs(sy-cy)+sh/2 > h/2
        sx, sy, sr = item
        return abs(sx-cx)+sr > w/2 or abs(sy-cy)+sr > h/2

    if spec['sensors'] and any(outside_plateau(item) for item in spec['sensors']):
        spec['sensor_surface'] = 'body'

    buttons = controls(device, body)
    logo_width, logo_height, logo_top = LOGO_DATUMS.get(
        device['id'], (11.5, 14.1, body['height']/2))
    rear_logo = {'kind':'apple', 'center_mm':[0, body['height']/2-logo_top],
                 'width_mm':logo_width, 'height_mm':logo_height, 'material':'logo'}
    result = {'id':device['id'], 'name':device['name'], 'manufacturer':'Apple',
            'body_mm':body,'screen':screen,'camera':spec,'buttons':buttons,
            'rear_logo':rear_logo,
            'finish':finish,'materials':materials,'finishes':finishes,'status':device['status'],
            'sources':device['sources'], 'accuracy':dict(device.get('accuracy',{}), body_dimensions='Apple published metric dimensions', screen_geometry=front.get('radius_status',front.get('radii_status','Apple drawing active area; corners approximate')), camera_geometry=camera.get('status',camera.get('measurement_status','Apple drawing dimensions where supplied; corner curvature and optics approximate')), controls='Apple dimensional-drawing control centerlines across the generated slab catalog', finishes=device.get('color_status','Official finish names; approximate sRGB materials'))}
    if front.get('body_outline_mm'):
        result['body_outline_mm'] = front['body_outline_mm']
    return result


def fold_profiles(device):
    """Use the existing articulated two-panel export for the sourced Duo dimensions."""
    opened, closed = device['body_mm'], device['closed_body_mm']
    # Apple publishes the complete open/closed envelopes. Two 82 mm leaves plus the measured
    # 0.6 mm centre seam reproduce the 164.6 mm open width; the closed hinge cover accounts for
    # the remaining 2.1 mm of the 84.1 mm closed width.
    gap = device.get('open_gap_mm', .6)
    pw = (opened['width']-gap)/2
    hinge_cover = closed['width']-pw
    closed_panel_x = hinge_cover/2
    panel_device = copy.deepcopy(device)
    panel_device['body_mm'] = dict(opened, width=pw)
    base = profile(panel_device)
    radius = base['body_mm']['corner_radius']
    cover_px = device['cover_native_px']
    cover_w, cover_h = device['front'].get('cover_active_mm', [
        cover_px[0]/device.get('cover_ppi', 460)*25.4,
        cover_px[1]/device.get('cover_ppi', 460)*25.4,
    ])
    cover_cutouts = []
    if device['front'].get('cover_cutout'):
        cut = device['front']['cover_cutout']
        right, top = cut['center_from_top_right_mm']
        entry = {'radius_mm': cut.get('radius_mm', cut.get('diameter_mm', 5.6)/2),
                 'center_mm': [cover_w/2-right, cover_h/2-top]}
        if cut.get('size_mm'):
            entry['size_mm'] = cut['size_mm']
        cover_cutouts.append(entry)
    cover = {'object':'Cover screen','node':'Cover screen','panel':'Cover half',
             'resolution':cover_px,'fit_box_mm':[cover_w,cover_h],
             # The cover OLED is physically on the rear face of the moving leaf when open.
             # Folding that leaf 180 degrees brings this same surface to the front.
             'center_mm':[0,device['front'].get('cover_center_y_mm', 0),-opened['depth']/2-.035],
             'corner_radius_mm':device['front'].get('cover_display_radius_mm', radius-2.5),
             'edge_curve_mm':0,'create_cutouts':True,'cutouts':cover_cutouts,
             'rotation_deg':[0,180,0], 'glass_border_mm':1,'frame_glass_border_mm':1,
             'frame_center_mm':[closed_panel_x,device['front'].get('cover_center_y_mm', 0)]}
    # Controls live on the two exterior rails. They therefore remain reachable when the leaves
    # overlap: the cover leaf's left edge becomes the closed phone's right edge after rotation.
    cover_buttons = copy.deepcopy(device.get('cover_buttons', [
        {'name':'Volume up','side':'left','center_y_mm':24.0,'length_mm':10.0},
        {'name':'Volume down','side':'left','center_y_mm':11.5,'length_mm':10.0},
    ]))
    camera_buttons = copy.deepcopy(device.get('camera_buttons', [
        {'name':'Side button | Touch ID','side':'right','center_y_mm':22.0,'length_mm':15.0},
        {'name':'Camera Control','side':'right','center_y_mm':-22.0,'length_mm':14.0},
    ]))
    for state in ('folded','unfolded'):
        result = copy.deepcopy(base)
        result.pop('screen')
        camera = result.pop('camera')
        rear_logo = result.pop('rear_logo', None)
        result.pop('buttons', None)
        result['id'] = device['id']+'-'+state
        result['name'] = device['name']+' \u00b7 '+state
        result['body_mm'] = dict(base['body_mm'], **(opened if state=='unfolded' else closed))
        panel_body = dict(base['body_mm'])
        centers = ([[ -(pw+gap)/2,0,0],[(pw+gap)/2,0,0]] if state=='unfolded' else
                   [[closed_panel_x,0,(closed['depth']-opened['depth'])/2],
                    [closed_panel_x,0,-(closed['depth']-opened['depth'])/2]])
        result['panels'] = []
        for index,name in enumerate(('Cover half','Camera half')):
            pb = copy.deepcopy(panel_body)
            if state == 'unfolded':
                pb['corner_radii_mm'] = [2,2,radius,radius] if index==0 else [radius,radius,2,2]
            else:
                pb['corner_radii_mm'] = [radius]*4
            panel = {'name':name,'body_mm':pb,'center_mm':centers[index]}
            if index == 0:
                panel['button_specs'] = cover_buttons
                if state == 'folded':
                    panel['rotation_deg'] = [0,180,0]
            else:
                panel['button_specs'] = camera_buttons
                panel['camera'] = camera
                panel['rear_logo'] = rear_logo or {'kind':'apple','height_mm':11.5,'center_mm':[0,0]}
            result['panels'].append(panel)
        screen = copy.deepcopy(cover)
        if state=='unfolded':
            screen['frame_file'] = 'cover-frame.svg'
            screen['frame_body_mm'] = dict(result['body_mm'],**closed)
            inner = copy.deepcopy(base['screen'])
            inner.update(object='Inner screen',node='Inner screen',panel='Inner display',
                         resolution=device['native_px'],fit_box_mm=device['front']['active_mm'],
                         center_mm=[0,0,opened['depth']/2+.035],cutouts=[],foldable_surface=True)
            result['screens'] = [inner,screen]
            axis_z = (closed['depth']-opened['depth'])/2
            result['articulation'] = {'animation':'Fold','axis':'Y','axis_mm':[0,0,axis_z],
                'moving_panel':'Cover half','fixed_panel':'Camera half',
                'pivots':{'Cover half':'Fold pivot | Cover half','Camera half':'Fold pivot | Camera half'},
                'open_degrees':0,'closed_degrees':180,'duration_seconds':1,
                'open_gap_mm':gap,'closed_gap_mm':closed['depth']-2*opened['depth'],
                'closed_body_mm':closed,'companion_profile':device['id']+'-folded'}
        else:
            result['screens'] = [screen]
            axis_z = (closed['depth']-opened['depth'])/2
        # The closed hinge shell keeps the published 84.1 mm outer envelope, but overlaps the
        # enclosure by 0.6 mm so there is no render gap at their rounded boundary.
        static_overlap = 2.4 if state == 'folded' else 0
        hinge_mesh_width = hinge_cover+static_overlap
        result['hinge'] = {'center_mm':[0 if state=='unfolded' else -closed['width']/2+hinge_mesh_width/2,0,0],
            'size_mm':[hinge_mesh_width,opened['height']-5,opened['depth']-.6 if state=='unfolded' else closed['depth']],
            'radius_mm':.7,'spine_width_mm':closed['depth'],'spine_depth_mm':1.8,
            # With the 3.05 mm pivot height, -1.7 mm gives a 4.75 mm reach. At 180° the
            # half-angle barrel therefore spans 2*4.75 + 1.8 = the published 11.3 mm depth.
            'spine_center_x_mm':0,'spine_center_z_mm':-opened['depth']/2+.9,
            'closed_spine_center_x_mm':pw-opened['width']/2,'closed_spine_center_z_mm':axis_z}
        result['accuracy']['hinge'] = ('Apple published open/closed envelopes and Grade 5 titanium hinge cover; '
            'panel seam, pivot axis and barrel cross-section are reconstructed to match those envelopes.')
        result['accuracy']['buttons'] = ('Control identities follow Apple technical specifications; rail positions '
            'are visually placed from Apple external-buttons artwork because Apple does not publish offsets.')
        yield result


def main():
    count = 0
    for filename in ('iphone-11-14.json','iphone-15-18.json'):
        path = BASE/'research'/filename
        if not path.exists():
            continue
        data = json.loads(path.read_text(encoding='utf-8'))
        for device in data['devices'] if isinstance(data,dict) else data:
            results = fold_profiles(device) if device.get('closed_body_mm') else [profile(device)]
            for result in results:
                apply_branding(result)
                (BASE/'profiles'/f"{result['id']}.json").write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
                count += 1
    print(f'Generated {count} Apple profiles')


if __name__ == '__main__':
    main()
