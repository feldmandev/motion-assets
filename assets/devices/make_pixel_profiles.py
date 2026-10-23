"""Create editable Pixel profiles from published specs and explicit visual estimates."""
import copy
import json
from make_device_branding import apply as apply_branding
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = 'https://support.google.com/pixelphone/answer/7158570?hl=en'

# Photo-informed silhouette and fit-box estimates (not manufacturer CAD).
# Body radius, screen radius, minimum side inset, top/bottom inset, camera top offset.
SIDES = {
    'Pixel 6': [3.4, 1.0], 'Pixel 6 Pro': [3.4, 1.6], 'Pixel 6a': [2.8, .9],
    'Pixel 7': [3.0, .9], 'Pixel 7 Pro': [3.2, 1.6], 'Pixel 7a': [2.8, .9],
    'Pixel 8': [3.0, 1.2], 'Pixel 8 Pro': [2.2, .9], 'Pixel 8a': [3.0, 1.2],
    'Pixel 9': [.75, .75], 'Pixel 9 Pro': [.75, .75], 'Pixel 9 Pro XL': [.75, .75], 'Pixel 9a': [1.0, .8],
    'Pixel 10': [.75, .75], 'Pixel 10 Pro XL': [.75, .75], 'Pixel 10a': [1.0, .8],
}

SHAPES = {
    'Pixel 6': (6.0, 5.0, 2.7, 2.8, 28.5),
    'Pixel 6 Pro': (5.8, 4.8, 1.8, 2.4, 28.5),
    'Pixel 6a': (6.5, 5.2, 2.8, 3.0, 24.0),
    'Pixel 7': (7.0, 5.5, 2.3, 2.3, 27.0),
    'Pixel 7 Pro': (7.0, 5.7, 1.6, 2.0, 27.0),
    'Pixel 7a': (7.0, 5.5, 2.6, 2.8, 22.0),
    'Pixel 8': (12.0, 9.8, 1.6, 1.8, 24.5),
    'Pixel 8 Pro': (12.5, 10.0, 1.5, 1.8, 25.0),
    'Pixel 8a': (14.0, 11.0, 2.4, 2.7, 23.5),
    'Pixel 9': (12.6, 10.1, 1.5, 1.8, 25.5),
    'Pixel 9 Pro': (12.6, 10.1, 1.5, 1.6, 25.5),
    'Pixel 9 Pro XL': (13.5, 11.0, 1.5, 1.7, 26.0),
    'Pixel 9a': (12.0, 9.5, 2.0, 2.4, 21.0),
    'Pixel 10': (12.6, 10.1, 1.5, 1.8, 25.5),
    'Pixel 10 Pro': (11.8, 10.0, 1.5, 1.6, 25.5),
    'Pixel 10 Pro XL': (13.5, 11.0, 1.5, 1.7, 26.0),
    'Pixel 10a': (13.2, 10.6, 2.0, 2.4, 20.0),
    'Pixel 11': (12.3, 10.5, 1.5, 1.8, 25.0),
    'Pixel 11 Pro': (12.2, 10.7, 1.2, 1.4, 25.5),
    'Pixel 11 Pro XL': (13.0, 11.5, 1.2, 1.4, 26.0),
}

# Approximate sRGB finishes, not calibrated manufacturer material samples.
COLORS = {
    'Obsidian': '#333a3d', 'Stormy Black': '#41464a', 'Charcoal': '#444b4a',
    'Kinda Coral': '#edb49e', 'Sorta Seafoam': '#c0d3c8', 'Cloudy White': '#e1dfd7',
    'Sorta Sunny': '#ecd9b6', 'Chalk': '#dce1dd', 'Sage': '#aabdaf',
    'Snow': '#e6e6df', 'Lemongrass': '#dce6b3', 'Hazel': '#9ea99c',
    'Sea': '#a9c9e2', 'Coral': '#f47a66', 'Rose': '#dcbdb5', 'Mint': '#c4dfcd',
    'Porcelain': '#e0e0d5', 'Bay': '#91b3d9', 'Aloe': '#a8c781',
    'Wintergreen': '#b3c9b1', 'Peony': '#efafbf', 'Rose Quartz': '#d6bdc3',
    'Iris': '#b0accb', 'Indigo': '#626d99', 'Frost': '#c4dbe3',
    'Moonstone': '#969ca7', 'Jade': '#b5bd99', 'Lavender': '#b5b1d6',
    'Berry': '#ce647b', 'Fog': '#d9ddd6', 'Isai Blue': '#344b90', 'Olive': '#8d947d',
    'Canyon': '#e99482', 'Pistachio': '#c4ce9e', 'Hibiscus': '#db7e99'
}


def rgb(value):
    return [round(int(value[index:index+2], 16)/255, 5) for index in (1, 3, 5)]


def lens(kind, x, y, radius, window=0):
    return {'kind': kind, 'center_mm': [x, y], 'radius_mm': radius, 'window': window}


def camera(model, body):
    width, height = body['width'], body['height']
    generation = int(model.split()[1].rstrip('a'))
    pro = 'Pro' in model
    y = height/2-SHAPES[model][4]
    spec = {'center_mm': [0, y], 'size_mm': [width, 21.6, .7], 'bump_mm': 2.8,
            'roll_mm': .45, 'windows': [], 'lenses': [], 'flash': [[-width*.34, y, 2.0]]}
    if generation == 6:
        bar_height = 15.6 if model.endswith('a') else 20.5 if pro else 18.8
        spec['size_mm'][1] = bar_height
        spec['size_mm'][2] = .6
        # The visor's top and bottom edges are fully rounded (pill cross-section): the edge roll
        # is close to half the protrusion, and the black glass sits on the flat face between them.
        spec['roll_mm'] = 1.0 if model.endswith('a') else 1.3
        spec['cover_depth_mm'] = .12
        spec['cover_roll_mm'] = .025
        spec['side_wrap_mm'] = 4.5 if model.endswith('a') else 5.0
        spec['windows'] = [[0, y, width-.3, bar_height-2*spec['roll_mm'], .3]]
        spec['lenses'] = [lens('main', width*.29, y, 2.7), lens('ultrawide', width*.10, y, 2.1)]
        if pro:
            spec['lenses'] = [lens('ultrawide',width*.29,y,2.1),lens('main',width*.10,y,2.7)]
            spec['lenses'].append(lens('periscope', -width*.12, y, 2.7))
        elif model.endswith('a'):
            spec['lenses'] = [lens('main',width*.29,y,2.4),lens('ultrawide',width*.10,y,2.1)]
        spec['bump_mm'] = 2.1 if model.endswith('a') else 3.0
        spec['flash'][0][2] = 2.5
    elif generation == 7 and pro:
        spec['size_mm'][1] = 21.0
        spec['windows'] = [[width*.20, y, width*.43, 13.8, 6.9],
                           [-width*.18, y, 12.4, 12.4, 6.2]]
        spec['lenses'] = [lens('ultrawide', width*.30, y, 3.7),
                          lens('main', width*.095, y, 4.6),
                          lens('periscope', -width*.18, y, 3.6, 1)]
        spec['flash'][0][0] = -width*.37
    elif model == 'Pixel 7a':
        spec.update(size_mm=[width,17.0,2.2], bump_mm=1.9, roll_mm=.9,
                    windows=[[12.5,y,27.0,12.2,6.1]],
                    lenses=[lens('ultrawide',20.0,y,3.0),lens('main',5.5,y,3.6)],
                    flash=[[-20.5,y,2.7]])
    elif generation in (7, 8) and not pro:
        spec['windows'] = [[width*.16, y, width*.49, 13.8, 6.9]]
        spec['lenses'] = [lens('ultrawide', width*.30, y, 3.7), lens('main', width*.04, y, 4.6)]
        spec['bump_mm'] = 1.9 if model.endswith('a') else 2.8
        if model.endswith('a'):
            spec['size_mm'][1] = 15.2 if generation == 7 else 17.8
        elif generation == 7:
            spec['size_mm'][1] = 19.8
    elif model.endswith('a'):
        x = 13.0 if generation == 10 else 13.5
        spec.update(center_mm=[x, y], size_mm=[28.0, 18.0, 9.0],
                    bump_mm=.15 if generation == 10 else .65, roll_mm=.05,
                    windows=[[x, y, 27.4, 17.4, 8.7]],
                    lenses=[lens('ultrawide', x+6.5, y, 3.0), lens('main', x-6.5, y, 3.4)],
                    flash=[[x-23.0, y, 2.9]])
        spec['flash_surface'] = 'body'
        if generation == 9:
            spec['size_mm'] = [31.0,17.5,8.75]
            spec['windows'] = [[x,y,30.3,16.8,8.4]]
            spec['bump_mm'] = .55
        else:
            spec['size_mm'] = [30.7,19.8,9.9]
            spec['windows'] = [[x,y,30.1,19.2,9.6]]
    else:
        if generation == 8:
            spec['windows'] = [[width*.086, y, width*.68, 17.6, 8.8]]
        else:
            spec['size_mm'] = [width*.90, 22.4, 11.2]
            spec['windows'] = [[width*.092, y, width*.678, 19.8, 9.9]]
        spec['bump_mm'] = 3.6
        if generation == 9 and not pro:
            spec['windows'] = [[width*.16, y, width*.54, 17.6, 8.8]]
            spec['lenses'] = [lens('ultrawide', width*.30, y, 3.8), lens('main', width*.075, y, 5.0)]
        else:
            spec['lenses'] = [lens('ultrawide', width*.311, y, 3.8),
                              lens('main', width*.097, y, 5.5),
                              lens('periscope', -width*.085, y, 3.8 if pro else 2.9)]
        if pro:
            spec['flash'] = [[-width*.333, y+4.7, 3.0]]
            spec['sensors'] = [[-width*.333, y-4.5, 3.05]]
    if generation in (7, 8) and spec['size_mm'][0] >= width-.5:
        # Full-width bars meet the rounded side rails: bend their ends down over the back roll.
        spec['side_wrap_mm'] = SIDES.get(model, [.55])[0]+1.5
    return spec


def screen(model, body, resolution, diagonal, panel='Body', node='Device screen'):
    # Fold diagonals remain an anchor; slabs use photo-informed fit boxes.
    px, py = resolution
    scale = diagonal*25.4/(px*px+py*py)**.5
    active = [px*scale, py*scale]
    shape = SHAPES.get(model)
    inset = shape[2] if shape else 1.5
    if shape:
        scale = min((body['width']-2*inset)/px, (body['height']-2*shape[3])/py)
        active = [px*scale, py*scale]
    else:
        active = [min(active[0], body['width']-2*inset), min(active[1], body['height']-2*inset)]
    curve = body.get('front_curve', 0)
    return {'object': node, 'node': node, 'panel': panel, 'resolution': resolution,
            'fit_box_mm': active, 'center_mm': [0, 0, body['depth']/2+.035],
            'corner_radius_mm': shape[1] if shape else max(2, body['corner_radius']-inset),
            'edge_curve_mm': curve, 'create_cutouts': True,
            'cutouts': [{'center_mm': [0, active[1]/2-5.1], 'radius_mm': 1.5}]}


def profile(model, dimensions, resolution, diagonal, colors, sources):
    generation = int(model.split()[1].rstrip('a'))
    pro = 'Pro' in model
    radius = SHAPES[model][0]
    body = dict(zip(['height', 'width', 'depth'], dimensions))
    body.update(corner_radius=radius, edge_roll=1.6 if pro and generation <= 7 else .55,
                front_curve=1.0 if pro and generation <= 7 else 0)
    # Side cross-section: (back, front) edge fillet radii, mm. Pixel 6-8 have rounded sides that
    # flow into curved back glass (6/7 Pro also curve the front); Pixel 9/10 have flat sides.
    body['edge_roll_mm'] = SIDES.get(model, [.55, .55])
    finishes = {}
    for color in colors:
        back = rgb(COLORS[color])
        rail = [round(value*.65+.20, 5) for value in back]
        bar = rgb('#15191d') if generation == 6 or model=='Pixel 9a' else rail
        finishes[color] = {'back': {'rgb': back}, 'rail': {'rgb': rail}, 'bar': {'rgb': bar}}
        if generation == 6:
            upper = {'Stormy Black':'#707375','Kinda Coral':'#e7947e','Sorta Seafoam':'#e3e9b6',
                     'Cloudy White':'#b7b9b7','Sorta Sunny':'#e3c19a','Charcoal':'#555b5c',
                     'Chalk':'#d7dad4','Sage':'#a1b3a5'}
            finishes[color]['upper'] = {'rgb': rgb(upper[color])}
    chosen = colors[0]
    mats = {'back': {'rgb': finishes[chosen]['back']['rgb'], 'rough': .42 if pro or model.endswith('a') else .18},
            'rail': {'rgb': finishes[chosen]['rail']['rgb'], 'metal': 1, 'rough': .18 if pro else .36},
            'bar': {'rgb': finishes[chosen]['bar']['rgb'], 'metal': .6 if generation != 6 else .05, 'rough': .3},
            'black': {'rgb': [.007,.009,.012], 'rough': .5},
            'flash': {'rgb': [.85,.84,.77], 'rough': .33}}
    if generation == 6:
        mats['upper'] = {'rgb': finishes[chosen]['upper']['rgb'], 'rough': .18}
    return {'id': model.lower().replace(' ', '-'), 'name': model, 'finish': chosen,
            'body_mm': body, 'materials': mats, 'finishes': finishes,
            'screen': screen(model, body, resolution, diagonal), 'camera': camera(model, body),
            'accuracy': {'body_dimensions': 'Google published metric dimensions',
                         'screen_resolution': 'Google published panel resolution',
                         'screen_geometry': 'Photo-informed fit box with exact native pixel aspect; bezels, radii, cutouts and edge curves estimated',
                         'camera_geometry': 'Provisional photo-informed blockout; shared reviewed optics are illustrative, not device-specific optical prescriptions',
                         'finishes': 'Approximate sRGB colors and roughness, not calibrated measured materials'},
            'sources': list(dict.fromkeys([SOURCE, *sources])), 'status': 'provisional'}


def apply_skin_measurements(data, measurements):
    key = data['id']
    if key not in measurements or key == 'pixel-8a':
        return
    measured = measurements[key]
    scale = measured['mm_per_pixel']
    radii = [r*scale for r in measured['body_radii_px']]
    data['reference_frame'] = measured['reference_frame']
    data['accuracy']['screen_geometry'] = 'Screen fit and corner radius measured from Google emulator artwork; native pixel aspect preserved. Skin artwork is a reference, not physical CAD.'
    if 'panels' not in data:
        if 'asset' not in data:
            data['body_mm']['corner_radius'] = sum(radii)/4
        screens = [data['screen']]
    else:
        data['body_mm']['corner_radius'] = sum(radii)/4 if data['state']=='unfolded' else sum(radii[:2])/2
        if data['state']=='folded':
            data['body_mm']['corner_radii_mm'] = radii
        closed = measurements[key.replace('-unfolded','-folded')]
        cr = [r*closed['mm_per_pixel'] for r in closed['body_radii_px']]
        outer,hinge = sum(cr[:2])/2,sum(cr[2:])/2
        for index,panel in enumerate(data['panels']):
            panel['body_mm']['corner_radius'] = outer
            panel['body_mm']['corner_radii_mm'] = ([outer,outer,hinge,hinge]
                if data['state']=='folded' or index==1 else [hinge,hinge,outer,outer])
            if 'camera' in panel and 'Pro Fold' in data['name']:
                cam=panel['camera']
                inset=panel['body_mm']['width']/2-cam['center_mm'][0]-cam['size_mm'][0]/2
                cam['size_mm'][2]=outer-inset
        screens = data['screens']
    for screen in screens:
        node = screen.get('node',screen['object'])
        source = measurements[key.replace('-unfolded','-folded')] if node=='Cover screen' else measured
        factor = source['mm_per_pixel']
        good = [r for r,error in zip(source['screen_radii_px'],source['screen_fit_error_px']) if error<3]
        if not good:
            continue
        screen['corner_radius_mm'] = sum(good)/len(good)*factor
        screen['fit_box_mm'] = source['screen_size_mm']
        cx,cy = source['screen_center_mm']
        if node=='Cover screen':
            cx -= .3
            if data['state']=='unfolded':
                cx = -cx
            screen['glass_border_mm'] = 1.8 if key.startswith('pixel-fold') else 1.5
            screen['frame_glass_border_mm'] = screen['glass_border_mm']
            closed = measurements[key.replace('-unfolded','-folded')]
            frame_radii = [r*closed['mm_per_pixel'] for r in closed['body_radii_px']]
            if 'frame_body_mm' in screen:
                screen['frame_body_mm']['corner_radii_mm'] = frame_radii
                screen['frame_body_mm']['corner_radius'] = sum(frame_radii[:2])/2
                screen['frame_center_mm'] = [.3-cx,cy]
        screen['center_mm'][:2] = [cx,cy]
        if screen['cutouts']:
            screen['cutouts'][0]['center_mm'][1] = screen['fit_box_mm'][1]/2-4.0


def apply_front_measurements(data, measurements):
    measured = measurements.get(data['id'], {})
    data['body_mm'].update(measured.get('body_mm', {}))
    for panel in data.get('panels', []):
        panel['body_mm'].update(measured.get('panels', {}).get(panel['name'], {}))
    for role, values in measured.get('materials', {}).items():
        data.setdefault('materials', {}).setdefault(role, {}).update(values)
    for spec in data.get('screens', [data['screen']] if 'screen' in data else []):
        spec.update(copy.deepcopy(measured.get('screens', {}).get(spec.get('node', spec['object']), {})))
    for name in ('bezel_cameras', 'bezel_windows', 'rail_details'):
        if name in measured:
            data[name] = copy.deepcopy(measured[name])
    for name, roles in measured.get('finishes', {}).items():
        data['finishes'][name].update(copy.deepcopy(roles))
    data['accuracy'].update(measured.get('accuracy', {}))
    data['sources'] = list(dict.fromkeys(data['sources'] + measured.get('sources', [])))


def apply_camera_measurements(data, measurements):
    key = data['id'].removesuffix('-folded').removesuffix('-unfolded')
    if key not in measurements or 'asset' in data:
        return
    measured = measurements[key]
    panel = next((p for p in data.get('panels', []) if 'camera' in p), data)
    cam, body = panel['camera'], panel['body_mm']
    old_x, old_y = cam['center_mm']
    old_w, old_h, old_r = cam['size_mm']
    width = body['width'] if key in ('pixel-6-pro', 'pixel-7-pro', 'pixel-7a') else measured['width_mm']
    height = measured['height_mm']
    top_gap = measured['top_gap_mm']
    x = old_x
    if 'pro-fold' in key:
        x = body['width']/2-top_gap-width/2
    elif key in ('pixel-9a', 'pixel-10a'):
        bx0, _, bx1, _ = measured['body_bounds_px']
        cx0, _, cx1, _ = measured['bar_bounds_px']
        x = ((bx0+bx1-cx0-cx1)/2)*measured['scale_mm_per_px']
    y = body['height']/2-top_gap-height/2
    sx, sy = width/old_w, height/old_h
    for window in cam['windows']:
        window[0] = x+(window[0]-old_x)*sx
        window[1] = y+(window[1]-old_y)*sy
        window[2] *= sx
        window[3] *= sy
        window[4] *= min(sx, sy)
    for item in cam['lenses']:
        lx, ly = item['center_mm']
        item['center_mm'] = [x+(lx-old_x)*sx, y+(ly-old_y)*sy]
    for items in (cam.get('flash', []), cam.get('sensors', [])):
        for point in items:
            point[:2] = [x+(point[0]-old_x)*sx, y+(point[1]-old_y)*sy]
    radius = body['corner_radius']-top_gap if 'pro-fold' in key else old_r*min(sx, sy)
    cam['center_mm'] = [x, y]
    cam['size_mm'] = [width, height, radius]
    if measured['protrusion_mm'] is not None:
        cam['bump_mm'] = measured['protrusion_mm']
    data['camera_measurement'] = measured
    data['accuracy']['camera_geometry'] = ('Housing width, height and top gap scaled from official rear artwork; '
        'pixel bounds and uncertainty in camera_measurement. Optical internals remain illustrative. '+measured['depth_status'])


def pixel11_profiles():
    """2026 slabs: metric specs and camera proportions from Google's launch artwork."""
    launch = 'https://blog.google/products-and-platforms/devices/pixel/google-pixel-11-pro-xl/'
    rows = [
        ('Pixel 11', [152.8,72.0,8.6], [1080,2424], 6.3,
         ['Frost','Pistachio','Hibiscus','Obsidian']),
        ('Pixel 11 Pro', [152.7,71.9,8.4], [1280,2856], 6.3,
         ['Canyon','Olive','Fog','Obsidian']),
        ('Pixel 11 Pro XL', [162.7,76.5,8.5], [1344,2992], 6.8,
         ['Canyon','Olive','Fog','Obsidian']),
    ]
    result = []
    for name, dimensions, resolution, diagonal, colors in rows:
        pro = 'Pro' in name
        source = 'https://store.google.com/gb/product/pixel_11'+('_pro' if pro else '')+'_specs?hl=en-GB'
        data = profile(name, dimensions, resolution, diagonal, colors, [source, launch])
        # The front metal ledge and rear shoulder have distinct cross-sections.
        data['body_mm']['edge_roll_mm'] = [.65,.30]
        data['body_mm']['front_rail_mm'] = 1.10
        data['status'] = 'provisional'
        # Rear photo pixel bounds: base body x327..633 y13..664, bar x341..621 y69..173.
        # Pro XL is oblique: height603 px, camera95 px, top gap49 px; horizontal foreshortening.
        width = dimensions[1]
        bar_w = 66.0 if not pro else 66.4 if 'XL' not in name else 70.7
        bar_h = 24.4 if not pro else 24.0 if 'XL' not in name else 25.5
        gap = 13.1 if not pro else 13.0 if 'XL' not in name else 13.2
        y = dimensions[0]/2-gap-bar_h/2
        scale = width/72
        cam = data['camera']
        cam.update(center_mm=[0,y], size_mm=[bar_w,bar_h,bar_h/2],
                   bump_mm=2.16 if not pro else 3.3, roll_mm=.25,
                   windows=[[0,y,bar_w-1.0,bar_h-1.0,(bar_h-1.0)/2]],
                   lenses=[lens('ultrawide',21.0*scale,y,2.7 if not pro else 3.2),
                           lens('main',6.0*scale,y,3.5 if not pro else 4.5),
                           lens('periscope',-8.0*scale,y,3.0 if not pro else 3.5)],
                   flash=[[-22.0*scale,y,3.0]], sensors=[], cover_depth_mm=.06, skip_source_pupil=True)
        for color, finish in data['finishes'].items():
            # Base Frost reads pale lavender in the official rear render; Pro Fog is pale green-grey.
            if color == 'Frost': finish['back']['rgb'] = rgb('#b9bacf')
            if color == 'Fog': finish['back']['rgb'] = rgb('#cbd6ce')
            finish['rail']['rough'] = .48 if pro and color=='Obsidian' else .18 if pro else .36
            finish['bar']['rough'] = finish['rail']['rough']
        for role, values in data['finishes'][colors[0]].items():
            data['materials'][role].update(values)
        data['accuracy']['camera_geometry'] = ('Camera capsule proportions estimated from official launch images: '
            'edge-to-edge black glass, three optics and in-glass flash. Base protrusion estimated as 60% '
            'of previous 3.6 mm baseline per Google thickness reduction; Pro protrusion estimated. '
            'HiLight represented in its unlit state. Optical internals illustrative, not manufacturer CAD.')
        data['accuracy']['screen_geometry'] = ('Native resolution aspect preserved; concentric display/body corners '
            'and thin symmetric bezels estimated from official front artwork, not a measured CAD outline.')
        data['reference_images'] = ['research/images/Pixel-11ProXL_Family-Shot.webp' if pro
                                    else 'research/images/NFG_Cubs_Frost.webp']
        result.append(data)
    return result


def main():
    old = json.loads((BASE/'research/pixel-6-8.json').read_text(encoding='utf-8-sig'))
    new = json.loads((BASE/'research/pixel-9-10.json').read_text(encoding='utf-8-sig'))
    profiles = pixel11_profiles()
    for item in old['models']:
        profiles.append(profile(item['id'], [item['body_mm'][key] for key in ['height','width','depth']],
                                item['display']['resolution_px'], item['display']['diagonal_in'],
                                item['colors'], [item['imagery']]))
    diagonals = {'Pixel 9': 6.3, 'Pixel 9 Pro': 6.3, 'Pixel 9 Pro XL': 6.8, 'Pixel 9a': 6.3,
                 'Pixel 10': 6.3, 'Pixel 10 Pro': 6.3, 'Pixel 10 Pro XL': 6.8, 'Pixel 10a': 6.3}
    for item in new['devices']:
        if item['model'] == 'Pixel 10 Pro':
            # Keep the reviewed imported asset as the authoritative first profile.
            continue
        profiles.append(profile(item['model'], item['bodyMm'], item['displayResolutionPx'],
                                diagonals[item['model']], item['colors'],
                                [item['googleStoreProductUrl'], *item.get('regionalColorSources',[])]))
    folds = json.loads((BASE/'research/pixel-fold.json').read_text(encoding='utf-8-sig'))
    for item in folds['models']:
        name = item['name'].split(' (')[0]
        original = name == 'Pixel Fold'
        dimensions = item['dimensions_mm']
        if original:
            dimensions = {'folded': {'height':139.7,'width':79.5,'depth':12.1},
                          'unfolded': {'height':139.7,'width':158.7,'depth':5.8}}
        for state in ['folded', 'unfolded']:
            data = profile('Pixel 9 Pro', [dimensions[state][key] for key in ['height','width','depth']],
                           [1080,2424], 6.3, item['colors'], item['official_refs'])
            data.update(id=name.lower().replace(' ', '-')+'-'+state, name=name+' · '+state,
                        state=state, status='provisional')
            data.pop('camera'); data.pop('screen')
            envelope = data['body_mm']
            outer_radius = 11.8 if original else 13.0 if '9 Pro' in name else 13.5
            envelope.update(corner_radius=outer_radius, edge_roll=.45)
            if state == 'folded':
                panel_width = envelope['width']-.6
                panel_depth = dimensions['unfolded']['depth']
                separation = envelope['depth']-panel_depth
                centers = [[.3,0,separation/2],[.3,0,-separation/2]]
            else:
                panel_width = envelope['width']/2-.3
                panel_depth = envelope['depth']
                centers = [[-envelope['width']/4-.15,0,0],[envelope['width']/4+.15,0,0]]
            panel_body = dict(envelope, width=panel_width, depth=panel_depth)
            data['panels'] = [{'name':'Cover half','body_mm':copy.deepcopy(panel_body),'center_mm':centers[0]},
                              {'name':'Camera half','body_mm':copy.deepcopy(panel_body),'center_mm':centers[1]}]
            # BR/TR/TL/BL: the hinge corners are almost square, not four outer corners.
            hinge_radius = 1.6
            for index, panel in enumerate(data['panels']):
                panel['body_mm']['corner_radii_mm'] = ([outer_radius,outer_radius,hinge_radius,hinge_radius]
                    if state == 'folded' or index == 1 else [hinge_radius,hinge_radius,outer_radius,outer_radius])
                panel['buttons'] = index == 1
            y = envelope['height']/2-(23 if original else 21.8)
            if original:
                cam = {'center_mm':[0,y], 'size_mm':[panel_width*.84,20.2,4], 'bump_mm':2.4,
                       'windows':[[11,y,29,13.8,6.9],[-11,y,11,11,5.5]],
                       'lenses':[lens('ultrawide',18.8,y,3.1),lens('main',5,y,4.1),lens('periscope',-11,y,3.1,1)],
                       'flash':[[panel_width*.36,y+3.1,1.8]], 'sensors':[[panel_width*.36,y-3.6,1.8]]}
            else:
                # Outer camera corner shares the phone corner's centre.
                camera_x = 8.5
                camera_w, camera_h = 47.5, 35.0
                side_inset = panel_width/2-(camera_x+camera_w/2)
                top_inset = envelope['height']/2-(y+camera_h/2)
                camera_radius = outer_radius-side_inset
                y += top_inset-side_inset
                cam = {'center_mm':[camera_x,y], 'size_mm':[camera_w,camera_h,camera_radius], 'bump_mm':3.0,
                       'windows':[[14.5,y+8,31.5,14,7],[14.5,y-8,31.5,14,7]],
                       'lenses':[lens('main',7.2,y+8,4.2),lens('ultrawide',22,y-8,3.5,1),
                                 lens('periscope',7.2,y-8,3.1,1)],
                       'flash':[[-9,y+8,2.1]], 'sensors':[[-9,y-8, .6]]}
            data['panels'][1]['camera'] = cam
            if '11 Pro' in name:
                for finish in data['finishes'].values():
                    finish['bar']['rgb'] = finish['back']['rgb'][:]
                data['materials']['bar'].update(rgb=data['finishes'][data['finish']]['bar']['rgb'], metal=.3, rough=.35)
                inset = 4.0
                cam_x = panel_width/2-inset-20.0
                cam_y = envelope['height']/2-inset-19.0
                data['panels'][1]['camera'] = {
                    'center_mm':[cam_x,cam_y], 'size_mm':[40.0,38.0,outer_radius-inset],
                    'bump_mm':2.5, 'roll_mm':.45,
                    'windows':[[cam_x,cam_y+9,36,16,8],[cam_x,cam_y-9,36,16,8]],
                    'lenses':[lens('ultrawide',cam_x-10,cam_y+9,3.0),
                              lens('main',cam_x+9,cam_y-9,4.2,1),
                              lens('telephoto',cam_x-6,cam_y-9,3.1,1)],
                    'flash':[[cam_x+10,cam_y+9,3.1]]}
            hinge_x = -envelope['width']/2+1 if state == 'folded' else 0
            open_gap = max(0, envelope['width']-2*panel_width) if state == 'unfolded' else .6
            fixed_right = open_gap/2+panel_width
            spine_half_width = max(.75, min(2.0, dimensions['folded']['width']-fixed_right))
            closed_left = fixed_right-dimensions['folded']['width']
            spine_center_x = closed_left+spine_half_width
            spine_depth = 2.0 if original else 1.8
            data['hinge'] = {
                'center_mm':[hinge_x,0,0],
                'size_mm':[2,envelope['height']-5,envelope['depth']-(2.4 if state=='folded' else .6)],
                'radius_mm':.7,
                'spine_width_mm':dimensions['folded']['depth'],
                'closed_spine_center_x_mm':closed_left+spine_depth/2,
                'closed_spine_center_z_mm':panel_depth/2+max(.05, dimensions['folded']['depth']-2*panel_depth)/2,
                'spine_depth_mm':spine_depth,
                'spine_center_x_mm':0,
                'spine_center_z_mm':-panel_depth/2+spine_depth/2,
            }
            if state == 'unfolded':
                # The moving cover half closes around a long-edge Y axis just outside the inner
                # display plane. At 180 degrees its front face lands across the published closed
                # inter-panel gap, so the rear cover display becomes the outside/front display.
                closed_gap = max(.05, dimensions['folded']['depth']-2*panel_depth)
                axis_z = panel_depth/2+closed_gap/2
                data['articulation'] = {
                    'animation':'Fold', 'axis':'Y', 'axis_mm':[0,0,axis_z],
                    'moving_panel':'Cover half', 'fixed_panel':'Camera half',
                    'pivots':{'Cover half':'Fold pivot | Cover half',
                              'Camera half':'Fold pivot | Camera half'},
                    'open_degrees':0, 'closed_degrees':180, 'duration_seconds':1.0,
                    'open_gap_mm':open_gap,
                    'closed_gap_mm':closed_gap,
                    'closed_body_mm':{key:dimensions['folded'][key] for key in ('height','width','depth')},
                    'companion_profile':name.lower().replace(' ', '-')+'-folded',
                }
            if state == 'folded':
                res = sorted(item['displays']['outer']['resolution_px'])
                diag = item['displays']['outer']['diagonal_in']
                cover = screen(name, panel_body, res, diag, 'Cover half', 'Cover screen')
                cover['corner_radius_mm'] = 7.4 if original else 10.0 if '9 Pro' in name else 11.3
                cover['center_mm'][0] = 1.6 if original else 1.2 if '9 Pro' in name else .8
                if not original:
                    fit_height = envelope['height']-(4.8 if '9 Pro' in name else 4.0)
                    cover['fit_box_mm'] = [fit_height*res[0]/res[1], fit_height]
                    cover['center_mm'][0] = 1.2 if '9 Pro' in name else .8
                data['screens'] = [cover]
            else:
                res = [2208,1840] if original else [2076,2152]
                diag = item['displays']['inner']['diagonal_in']
                inner = screen(name, envelope, res, diag, 'Inner display', 'Inner screen')
                inner['corner_radius_mm'] = 4.8 if original else 9.7 if '9 Pro' in name else 11.3
                if not original:
                    fit_height = envelope['height']-(6.4 if '9 Pro' in name else 4.0)
                    inner['fit_box_mm'] = [fit_height*res[0]/res[1],fit_height]
                inner['center_mm'][2] = panel_depth/2+.04
                # Original Fold camera is in the top bezel, not a hole through the OLED.
                inner['cutouts'] = [] if original else [{'center_mm':[inner['fit_box_mm'][0]/2-8,inner['fit_box_mm'][1]/2-6], 'radius_mm':1.5}]
                data['screens'] = [inner]
                cover_res = sorted(item['displays']['outer']['resolution_px'])
                cover = screen(name, panel_body, cover_res,
                               item['displays']['outer']['diagonal_in'], 'Cover half', 'Cover screen')
                cover['corner_radius_mm'] = 7.4 if original else 10.0 if '9 Pro' in name else 11.3
                cover['center_mm'][0] = -1.6 if original else -1.2 if '9 Pro' in name else -.8
                if not original:
                    fit_height = envelope['height']-(4.8 if '9 Pro' in name else 4.0)
                    cover['fit_box_mm'] = [fit_height*cover_res[0]/cover_res[1],fit_height]
                    cover['center_mm'][0] = -1.2 if '9 Pro' in name else -.8
                cover['center_mm'][2] = -panel_depth/2-.035
                cover['rotation_deg'] = [0,180,0]
                cover['frame_file'] = 'cover-frame.svg'
                cover['frame_body_mm'] = dict(dimensions['folded'], corner_radius=outer_radius,
                    corner_radii_mm=[outer_radius,outer_radius,hinge_radius,hinge_radius])
                cover['frame_center_mm'] = [.3-cover['center_mm'][0],0]
                data['screens'].append(cover)
                if original:
                    data['bezel_cameras'] = [[57,66,panel_depth/2+.025,1.4]]
            if state == 'folded':
                envelope['corner_radii_mm'] = [outer_radius,outer_radius,hinge_radius,hinge_radius]
            cover['glass_border_mm'] = 1.8 if original else 1.5
            cover['frame_glass_border_mm'] = cover['glass_border_mm']
            if state == 'unfolded':
                for display in data['screens']:
                    display['foldable_surface'] = True
                data['accuracy']['hinge'] = ('Animated rigid-panel hinge with a measured open/closed thickness axis; '
                    'half-angle barrel and hinge leaves remain an estimated mechanism; the flexible OLED is split at the crease.')
            else:
                data['accuracy']['hinge'] = 'Static closed companion profile retained for dimensional/reference checks.'
            profiles.append(data)
    for item in profiles:
        if item['id'] == 'pixel-8' and 'Mint' not in item['finishes']:
            mint = profile('Pixel 8',[150.5,70.8,8.9],[1080,2400],6.2,['Mint'],[])
            item['finishes']['Mint'] = mint['finishes']['Mint']
    measurements = json.loads((BASE/'research/skin-measurements.json').read_text())
    camera_measurements = json.loads((BASE/'research/camera-measurements.json').read_text())
    front_measurements = json.loads((BASE/'research/pixel-front-measurements.json').read_text())
    for item in profiles:
        apply_skin_measurements(item, measurements)
        apply_camera_measurements(item, camera_measurements)
        apply_branding(item)
        apply_front_measurements(item, front_measurements)
        (BASE/'profiles'/f'{item["id"]}.json').write_text(json.dumps(item, indent=2)+'\n', encoding='utf-8')
    reviewed_path = BASE/'profiles/pixel-10-pro.json'
    reviewed = json.loads(reviewed_path.read_text(encoding='utf-8'))
    reviewed['screen']['fit_box_mm'] = [69.0,149.6]
    apply_skin_measurements(reviewed, measurements)
    reviewed['material_objects'] = {'back':'Obsidian | silky matte glass',
                                   'rail':'Obsidian | polished aluminum',
                                   'bar':'Camera bar | satin gunmetal aluminum'}
    reviewed['finishes'] = profile('Pixel 10 Pro',[152.8,72,8.6],[1280,2856],6.3,
                                   ['Obsidian','Moonstone','Jade','Porcelain'],[])['finishes']
    apply_branding(reviewed)
    apply_front_measurements(reviewed, front_measurements)
    reviewed_path.write_text(json.dumps(reviewed, indent=2)+'\n', encoding='utf-8')
    print(f'Wrote {len(profiles)} procedural profiles; kept reviewed Pixel 10 Pro asset profile')


if __name__ == '__main__':
    main()
