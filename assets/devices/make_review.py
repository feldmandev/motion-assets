"""Offline review gallery with bundled model-viewer and embedded GLB assets."""
import base64
import io
import json
import sys
from pathlib import Path
from PIL import Image

BASE = Path(__file__).resolve().parent


def image(path):
    thumbnail = Image.open(path).convert('RGBA')
    thumbnail.thumbnail((360,420),Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    thumbnail.save(buffer,format='WEBP',quality=85)
    if '--linked' in sys.argv:
        linked_path = path.with_suffix('.webp')
        linked_path.write_bytes(buffer.getvalue())
        return linked_path.as_posix()
    return 'data:image/webp;base64,'+base64.b64encode(buffer.getvalue()).decode()


def main():
    devices = []
    profile_paths = sorted([
        *(BASE/'profiles').glob('pixel-*.json'),
        *(BASE/'profiles').glob('iphone-*.json'),
        *(BASE/'profiles').glob('galaxy-*.json'),
        *(BASE/'profiles').glob('oneplus-*.json'),
    ])
    available = {path.stem for path in profile_paths
                 if (BASE/'exports'/path.stem/'device.json').exists()
                 and (BASE/'exports'/path.stem/'model.glb').exists()}
    for path in profile_paths:
        profile = json.loads(path.read_text())
        output = BASE/'exports'/path.stem
        # Profile generation can legitimately get ahead of Blender exports while a family is
        # being reviewed. Keep the shared gallery usable instead of failing the whole build.
        if not (output/'device.json').exists() or not (output/'model.glb').exists():
            continue
        # The folded export is a dimensional/reference companion. When an articulated open GLB
        # exists, show one device card and let the Fold control drive the actual hinge instead of
        # presenting open/closed as unrelated models.
        if path.stem.endswith('-folded') and path.stem[:-7]+'-unfolded' in available:
            continue
        metadata = json.loads((output/'device.json').read_text())
        devices.append({'id':path.stem,'name':profile['name'],'finish':profile['finish'],
                        'manufacturer':profile.get('manufacturer','Google'),
                        'form_factor':profile.get('form_factor','phone'),
                        'status':metadata['status'],'body':profile['body_mm'],
                        'screens':metadata['screens'], 'sources':profile['sources'],
                        'articulation':metadata.get('articulation'),
                        'panels':profile.get('panels',[]),
                        'reference':image(BASE/profile['reference_frame']) if profile.get('reference_frame') else None,
                        'glb':base64.b64encode((output/'model.glb').read_bytes()).decode(),
                        'slots':profile.get('material_objects', {role:role for role in profile.get('materials', {})}),
                        'views':{name:image(output/f'{name}.png') for name in ['front','rear','rear-angle','cover-front'] if (output/f'{name}.png').exists()},
                        'frames':[{'name':screen['node'],'file':screen.get('frame_file','frame.svg'),
                                   'image':'data:image/svg+xml;base64,'+base64.b64encode((output/screen.get('frame_file','frame.svg')).read_bytes()).decode()}
                                  for screen in metadata['screens']],
                        'finishes':[{'name':name,'rgb':settings['back']['rgb'],'materials':settings,
                                     'image':image(output/f'finish-{index}.png')}
                                    for index,(name,settings) in enumerate(profile['finishes'].items())]})
    html = '''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Device model gallery</title><style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#111417;color:#e4e7eb}body{margin:0;padding:28px;max-width:1440px;margin:auto}h1{font-size:28px;margin:0 0 8px}p{color:#aeb6bf;line-height:1.5;max-width:950px}header{margin-bottom:24px}.controls{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}label{display:grid;gap:6px;color:#bbc3cb;font-size:12px}select,input{background:#252b32;color:#e4e7eb;border:1px solid #414a55;border-radius:12px;padding:11px;font:inherit;min-width:130px}input{min-width:200px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:16px}.card{background:#1d2228;border-radius:20px;overflow:hidden;padding:16px}.card img{display:block;width:100%;height:275px;object-fit:contain;background:#14181d;border-radius:12px}h2{font-size:17px;font-weight:600;margin:15px 0 7px}.tag{font-size:11px;color:#c4c9d1;background:#303740;padding:4px 8px;border-radius:20px}.info{font-size:12px;color:#aab4bf;margin:12px 0;line-height:1.6}.links{display:flex;gap:12px;flex-wrap:wrap;font-size:12px;margin-top:15px}a{color:#a9c9ff;text-decoration:none}.finish{width:100%;margin-top:12px}.count{color:#a9c9ff;margin-left:auto;align-self:center;font-size:13px}button{font:inherit;border:0;background:#37465c;color:#e4edff;padding:10px 14px;border-radius:12px}details{margin-top:12px;font-size:12px;line-height:1.6;color:#aeb6bf}@media(max-width:600px){body{padding:16px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}.card{padding:10px}.card img{height:210px}h2{font-size:14px}.links{gap:8px}select{min-width:0;width:100%}.controls label{flex:1 1 120px}.controls label:first-child{flex-basis:100%}.controls input{box-sizing:border-box;min-width:0;width:100%}}
.card img.frame-image{background-color:#758d99;background-image:repeating-conic-gradient(#758d99 0% 25%,#b9c9d0 0% 50%);background-size:24px 24px;box-sizing:border-box;padding:20px}dialog{background:#14181d;color:#e4e7eb;border:1px solid #414a55;border-radius:20px;width:min(900px,calc(100vw - 48px));padding:16px}dialog::backdrop{background:#000b}.viewer-head{display:flex;align-items:center;gap:12px}.viewer-head h2{flex:1}model-viewer{display:block;width:100%;height:min(65vh,650px);min-height:300px;--poster-color:transparent}.viewer-controls{display:flex;gap:10px;flex-wrap:wrap;align-items:center}.fold-controls{display:flex;align-items:center;gap:8px;flex:1 1 100%;padding-top:4px}.fold-controls input{min-width:160px;flex:1}.rotate{width:100%;margin-top:12px}#viewer-status{font-size:12px;color:#aeb6bf}
</style><body><header><h1>Device model gallery</h1><p>Reviewed procedural phone models with published chassis/display dimensions, model-specific camera and enclosure geometry, replaceable screen surfaces, exported frames, finishes, and articulated folding where supported. Pixel reference artwork and Apple dimensional sources stay attached to each model for review. <a href="research/camera-measurements.html">Pixel camera measurements</a>.</p>
<div class="controls"><label>Find a model<input id="search" placeholder="Pixel 8 Pro, iPhone 18 Pro, Duo…"></label><label>Devices<select id="family"><option value="">All</option><option value="Google">Google Pixel</option><option value="Apple">Apple iPhone</option><option value="Samsung">Samsung Galaxy</option><option value="OnePlus">OnePlus</option><option value="fold">Foldables</option></select></label><label>View<select id="view"><option value="rear-angle">Angled rear / colors</option><option value="rear">Rear · default finish</option><option value="front">Front / inner screen</option><option value="reference">Reference artwork</option><option value="cover-front">Exterior screen</option><option value="frame">Main SVG frame</option><option value="cover-frame">Exterior SVG frame</option></select></label><span id="count" class="count"></span></div></header><main id="grid" class="grid"></main>
<dialog id="viewer-dialog"><div class="viewer-head"><h2 id="viewer-title"></h2><button id="viewer-close" aria-label="Close 3D view">Close</button></div><model-viewer id="viewer" camera-controls orientation="0deg 90deg 0deg" camera-orbit="155deg 78deg auto" min-camera-orbit="auto 0deg auto" max-camera-orbit="auto 180deg auto" environment-image="data:application/octet-stream;base64,__ENVIRONMENT__#.hdr" exposure="1.05" tone-mapping="neutral" shadow-intensity="0.7" shadow-softness="0.9" interaction-prompt="none"></model-viewer><p id="viewer-status">Drag to orbit · scroll or pinch to zoom · pan with right/middle drag</p><div class="viewer-controls"><button data-orbit="0deg 90deg auto">Front</button><button data-orbit="180deg 90deg auto">Rear</button><button data-orbit="90deg 90deg auto">Side</button><button data-orbit="155deg 78deg auto">Reset</button><select id="viewer-finish" aria-label="3D finish"></select><div id="viewer-fold-controls" class="fold-controls" hidden><button data-fold="0">Open</button><input id="viewer-fold" type="range" min="0" max="1" step="0.01" value="0" aria-label="Fold amount"><button data-fold="1">Fold</button></div></div></dialog>
<script type="module">__MODEL_VIEWER__</script><script>const devices=__DATA__;const grid=document.getElementById('grid');const selected={};
function frameImage(frame,finish){const color='#'+finish.materials.rail.rgb.map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('');return 'data:image/svg+xml;base64,'+btoa(atob(frame.image.split(',')[1]).replace(/--device-color:#[0-9a-f]{6}/g,'--device-color:'+color));}
function render(){const query=document.getElementById('search').value.toLowerCase();const family=document.getElementById('family').value;const view=document.getElementById('view').value;const filtered=devices.filter(d=>(view!=='reference'||d.reference)&&d.name.toLowerCase().includes(query)&&(!family||(family==='fold'?Boolean(d.articulation):d.manufacturer===family)));grid.replaceChildren();document.getElementById('count').textContent=filtered.length+' models';for(const d of filtered){const card=document.createElement('article');card.className='card';const index=selected[d.id]||0;const photo=document.createElement('img');photo.alt=d.name+' '+view;photo.classList.toggle('frame-image',view==='frame'||view==='cover-frame');const cover=d.frames.find(f=>f.name==='Cover screen')||d.frames[0];photo.src=view==='reference'?d.reference:view==='frame'?frameImage(d.frames[0],d.finishes[index]):view==='cover-frame'?frameImage(cover,d.finishes[index]):view==='rear-angle'&&index?d.finishes[index].image:d.views[view]||d.views.front;card.append(photo);const title=document.createElement('h2');title.textContent=d.name;card.append(title);const tag=document.createElement('span');tag.className='tag';tag.textContent=d.status;card.append(tag);const info=document.createElement('div');info.textContent=d.body.height+' × '+d.body.width+' × '+d.body.depth+' mm · '+d.screens.map(s=>s.node+': '+s.resolution.join(' × ')).join(' / ');info.className='info';card.append(info);const finish=document.createElement('select');finish.className='finish';finish.setAttribute('aria-label',d.name+' finish');d.finishes.forEach((f,i)=>{const option=document.createElement('option');option.value=i;option.textContent=f.name;finish.append(option)});finish.value=index;finish.disabled=!['rear-angle','frame','cover-frame'].includes(view);finish.onchange=()=>{selected[d.id]=Number(finish.value);render()};card.append(finish);const rotate=document.createElement('button');rotate.className='rotate';rotate.textContent='Rotate in 3D';rotate.onclick=()=>openViewer(d,index);card.append(rotate);const links=document.createElement('div');links.className='links';for(const [label,file] of [['GLB','model.glb'],['Blender','model.blend'],...d.frames.map(f=>[f.name==='Cover screen'?'Exterior frame':'Main frame',f.file]),['Metadata','device.json']]){const a=document.createElement('a');a.textContent=label;a.href='exports/'+d.id+'/'+file;links.append(a)}card.append(links);const details=document.createElement('details');const summary=document.createElement('summary');summary.textContent='References';details.append(summary);for(const url of d.sources){const a=document.createElement('a');a.textContent=new URL(url).hostname;a.href=url;a.target='_blank';details.append(a,document.createElement('br'))}card.append(details);grid.append(card)}}for(const id of ['search','family','view'])document.getElementById(id).addEventListener('input',render);render();console.log('Device gallery loaded:',devices.length,'models');
__VIEWER_CODE__
</script></body></html>'''
    filename = 'review-preview.html' if '--linked' in sys.argv else 'review.html'
    (BASE/filename).write_text(html.replace('__DATA__',json.dumps(devices)).replace('__MODEL_VIEWER__',(BASE/'vendor/model-viewer.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')).replace('__ENVIRONMENT__',base64.b64encode((BASE.parent/'pixel-10-pro-model/source/studio_small_09_1k.hdr').read_bytes()).decode()).replace('__VIEWER_CODE__',(BASE/'fold_centering.js').read_text(encoding='utf-8')+'\n'+(BASE/'review_viewer.js').read_text(encoding='utf-8')),encoding='utf-8')
    print(f'Wrote review.html: {len(devices)} profiles')


if __name__ == '__main__':
    main()
