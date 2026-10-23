"""Build the icon-first gallery with lazy 3D/frame review controls."""
import base64
import json
import re
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CATALOG = json.loads((ROOT / 'tmp/ref5/all_phones/catalog.json').read_text(encoding='utf-8'))
MODEL_BASE = ROOT.parent / 'home/home-android/demo-video/device-models'
MODEL_DATA_DIR = ROOT / 'device_icons_svg/model_data'


def data_uri(path: Path, mime: str) -> str:
    return f'data:{mime};base64,' + base64.b64encode(path.read_bytes()).decode()


def icon_model_group(model: str) -> str | None:
    special = {
        'pixel_fold': 'pixel-fold',
        'pixel_9_fold': 'pixel-9-pro-fold',
        'pixel_10_fold': 'pixel-10-pro-fold',
        'pixel_11_fold': 'pixel-11-pro-fold',
        'apple_iphone_duo': 'iphone-duo',
        'generic_googlebook': 'googlebook-emulator',
    }
    if model in special:
        return special[model]
    if model.startswith(('googlebook_', 'galaxy_', 'generic_', 'oneplus_', 'honor_', 'nothing_', 'xiaomi_')):
        return model.replace('_', '-')
    if model.startswith('apple_iphone_'):
        return 'iphone-' + model.removeprefix('apple_iphone_').replace('_', '-')
    if not model.startswith('pixel_'):
        return None
    parts = model.split('_')[1:]
    if not parts or not parts[0].isdigit():
        return None
    generation, suffix = parts[0], parts[1:]
    if suffix and suffix[0] == 'a':
        return f'pixel-{generation}a' + ('-' + '-'.join(suffix[1:]) if len(suffix) > 1 else '')
    return f'pixel-{generation}' + ('-' + '-'.join(suffix) if suffix else '')


def build_model_data() -> dict[str, dict]:
    """Write one classic script per GLB so file:// galleries can lazy-load models without fetch/CORS."""
    groups: dict[str, dict] = {}
    MODEL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    expected = set()
    if not MODEL_BASE.exists():
        return groups

    profile_paths = sorted((MODEL_BASE / 'profiles').glob('pixel-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('iphone-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('googlebook-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('galaxy-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('oneplus-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('honor-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('nothing-*.json'))
    profile_paths += sorted((MODEL_BASE / 'profiles').glob('xiaomi-*.json'))
    for profile_path in profile_paths:
        profile = json.loads(profile_path.read_text(encoding='utf-8'))
        output = MODEL_BASE / 'exports' / profile_path.stem
        glb = output / 'model.glb'
        metadata_path = output / 'device.json'
        if not (glb.exists() and metadata_path.exists()):
            continue
        metadata = json.loads(metadata_path.read_text(encoding='utf-8'))
        suffix = re.search(r'-(folded|unfolded)$', profile_path.stem)
        state = profile.get('state') or (suffix.group(1) if suffix else 'default')
        group = re.sub(r'-(?:folded|unfolded)$', '', profile_path.stem)
        frames = []
        for screen in metadata.get('screens', []):
            filename = screen.get('frame_file', 'frame.svg')
            frame_path = output / filename
            if frame_path.exists():
                frames.append({
                    'name': screen['node'],
                    'file': filename,
                    'image': data_uri(frame_path, 'image/svg+xml'),
                })
        payload = {
            'id': profile_path.stem,
            'name': profile['name'],
            'state': state,
            'glb': base64.b64encode(glb.read_bytes()).decode(),
            'screens': metadata.get('screens', []),
            'body_mm': metadata.get('body_mm') or profile.get('body_mm'),
            'icon_morph': {'windows': len(profile.get('camera', {}).get('windows', [])),
                           'kind': profile.get('form_factor')},
            'articulation': metadata.get('articulation'),
            'robot_motion': metadata.get('robot_motion'),
            'panels': profile.get('panels', []),
            'frames': frames,
            'slots': profile.get('material_objects', {role: role for role in profile.get('materials', {})}),
            'finishes': [
                {'name': name, 'materials': settings}
                for name, settings in profile.get('finishes', {}).items()
            ],
        }
        target = MODEL_DATA_DIR / f'{profile_path.stem}.js'
        target.write_text(
            'window.__DEVICE_MODEL_DATA__=window.__DEVICE_MODEL_DATA__||{};'
            f'window.__DEVICE_MODEL_DATA__[{json.dumps(profile_path.stem)}]={json.dumps(payload, separators=(",", ":"))};\n',
            encoding='utf-8',
        )
        expected.add(target.name)
        group_info = groups.setdefault(group, {'states': {}, 'hasFrame': False})
        group_info['states'][state] = profile_path.stem
        group_info['hasFrame'] = group_info['hasFrame'] or bool(frames)
        if metadata.get('articulation'):
            group_info['articulated'] = True

    # Generic payloads are maintained separately from the vendor profile exporters.
    for script in MODEL_DATA_DIR.glob('generic-*.js'):
        source = script.read_text(encoding='utf-8')
        marker = f'window.__DEVICE_MODEL_DATA__[{json.dumps(script.stem)}]='
        if marker in source:
            payload, _ = json.JSONDecoder().raw_decode(source.split(marker, 1)[1])
            groups[script.stem] = {'states': {'default': script.stem}, 'hasFrame': bool(payload.get('frames'))}
    for stale in MODEL_DATA_DIR.glob('*.js'):
        if stale.name not in expected and not stale.name.startswith('generic-'):
            stale.unlink()
    # Duo's unfolded GLB contains the real Fold animation.  Keep a single gallery
    # model loaded from that articulated asset instead of swapping to the static
    # folded companion, which would lose the physical hinge motion.
    duo = groups.get('iphone-duo')
    if duo and duo.get('states', {}).get('unfolded'):
        duo['states'] = {'default': duo['states']['unfolded']}
        duo['articulated'] = True
    return groups


PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Device gallery</title>
<style>
:root{color-scheme:light;--surface:#fdf7ff;--container:#f3edf7;--high:#eae3ef;--text:#1d1b20;--muted:#49454f;--primary:#65558f;--outline:#79747e;--focus:#65558f;--stage:#eee7f2;--menu-bg:rgba(243,237,247,.92);--menu-hover:#e7e0ec;--menu-selected:#e8def8;--menu-selected-text:#1d192b}
:root[data-theme=dark]{color-scheme:dark;--surface:#141218;--container:#211f26;--high:#2b2930;--text:#e6e0e9;--muted:#cac4d0;--primary:#d0bcff;--outline:#938f99;--focus:#d0bcff;--stage:#111318;--menu-bg:rgba(43,41,48,.94);--menu-hover:#35323a;--menu-selected:#4f378b;--menu-selected-text:#eaddff}
@media(prefers-color-scheme:dark){:root:not([data-theme=light]){color-scheme:dark;--surface:#141218;--container:#211f26;--high:#2b2930;--text:#e6e0e9;--muted:#cac4d0;--primary:#d0bcff;--outline:#938f99;--focus:#d0bcff;--stage:#111318;--menu-bg:rgba(43,41,48,.94);--menu-hover:#35323a;--menu-selected:#4f378b;--menu-selected-text:#eaddff}}
*{box-sizing:border-box}body{margin:0;background:var(--surface);color:var(--text);font-family:Roboto,"Segoe UI",Arial,sans-serif}main{max-width:1500px;margin:auto;padding:24px}header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:24px}h1{font-size:28px;font-weight:500;letter-spacing:-.5px;margin:0}header p{margin:8px 0 0;color:var(--muted);font-size:14px}.filters{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px}.field{display:flex;flex-direction:column;min-width:0;background:var(--high);border-radius:12px 12px 4px 4px;padding:8px 12px 4px;border-bottom:1px solid var(--outline)}.field span{font-size:12px;color:var(--primary);margin-bottom:2px}select,input{width:100%;font:inherit;font-size:14px;color:var(--text);background:transparent;border:0;min-height:30px;outline:0}select option{background:var(--container);color:var(--text)}.field:focus-within{outline:2px solid var(--focus);outline-offset:2px}input::placeholder{color:var(--muted)}.theme{width:125px;flex-shrink:0}.search{grid-column:span 3}.status{display:flex;justify-content:space-between;align-items:center;gap:16px;margin:20px 0;color:var(--muted);font-size:13px}button{font:inherit;font-weight:500;border:0;border-radius:999px;min-height:38px;padding:0 17px;background:var(--high);color:var(--primary);cursor:pointer}button:hover{filter:brightness(.98)}button:focus-visible{outline:2px solid var(--focus);outline-offset:3px}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(168px,1fr));gap:16px}.card{background:var(--container);border-radius:24px;padding:16px;min-width:0;display:flex;flex-direction:column;align-items:center}.card>img{width:140px;height:180px;max-width:100%;object-fit:contain}.brand{font-size:11px;color:var(--primary);margin-top:10px;letter-spacing:.6px;text-transform:uppercase}.card h2{font-size:15px;line-height:21px;font-weight:500;text-align:center;margin:6px 0 12px;min-height:42px}.card .field{width:100%;margin-top:auto;background:var(--high)}.provisional{font-size:11px;color:var(--primary);margin:-7px 0 9px}.card-actions{width:100%;display:flex;gap:6px;flex-wrap:wrap;margin:10px 0 0}.card-actions button{flex:1 1 48px;min-height:32px;padding:0 10px;font-size:12px;background:transparent;border:1px solid color-mix(in srgb,var(--outline) 65%,transparent)}.card-actions .primary-action{background:var(--high);border-color:transparent}.model-dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:var(--primary);margin-right:5px;vertical-align:1px}.empty{text-align:center;color:var(--muted);padding:64px 16px}.foot{font-size:12px;line-height:20px;color:var(--muted);margin:24px 0 0}[hidden]{display:none!important}.card img.monochrome{filter:none}[data-theme="dark"] .card img.monochrome{filter:invert(1)}@media(prefers-color-scheme:dark){:root:not([data-theme="light"]) .card img.monochrome{filter:invert(1)}}
.field.motion-enhanced{background:transparent;border-bottom:0;border-radius:0;padding:0;overflow:visible}.field.motion-enhanced:focus-within{outline:0}.field.motion-enhanced>span:first-child{display:none}select.motion-native{display:none!important}.motion-select{position:relative;width:100%;min-width:0}.motion-select.open{z-index:80}.motion-select-btn{display:flex;align-items:center;gap:10px;width:100%;min-width:0;height:48px;padding:0 11px 0 14px;background:var(--high);border:1px solid color-mix(in srgb,var(--outline) 55%,transparent);border-radius:18px;color:var(--text);font-family:inherit;text-align:left;cursor:pointer;transition:border-color .15s,transform .15s}.motion-select-btn:hover{border-color:var(--outline);filter:none}.motion-select-btn:active{transform:scale(.97)}.motion-select-btn:focus-visible{outline:2px solid var(--focus);outline-offset:2px}.motion-select-btn[aria-expanded="true"]{border-color:var(--primary)}.motion-field{flex:1;min-width:0;display:flex;flex-direction:column;align-items:flex-start;gap:2px}.motion-field-label{font-size:11px;line-height:1;color:var(--muted)}.motion-select-btn[aria-expanded="true"] .motion-field-label{color:var(--primary)}.motion-field-value{font-size:14px;line-height:1.25;color:var(--text);max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.motion-chevron{width:18px;height:18px;flex:none;color:var(--muted);transition:transform .16s cubic-bezier(.4,0,.2,1),color .16s}.motion-select-btn[aria-expanded="true"] .motion-chevron{transform:rotate(180deg);color:var(--primary);transition-duration:.21s}.motion-menu{position:absolute;top:calc(100% + 4px);left:0;width:max-content;min-width:100%;max-width:min(85vw,360px);max-height:320px;overflow:auto;background:var(--menu-bg);backdrop-filter:blur(18px) saturate(1.25);-webkit-backdrop-filter:blur(18px) saturate(1.25);border:1px solid color-mix(in srgb,var(--outline) 55%,transparent);border-radius:20px;padding:6px;box-shadow:0 8px 28px rgba(0,0,0,.28);z-index:90;transform-origin:top left;opacity:0;pointer-events:none;will-change:transform,opacity,filter,clip-path;scrollbar-width:none;-ms-overflow-style:none}.motion-menu::-webkit-scrollbar{display:none;width:0}.motion-menu.open{opacity:1;pointer-events:auto}.motion-option{display:flex;align-items:center;gap:8px;width:100%;min-height:44px;padding:10px 13px;background:none;border:0;border-radius:14px;color:var(--text);font:inherit;font-size:14px;font-weight:400;cursor:pointer;text-align:left}.motion-option+.motion-option{margin-top:2px}.motion-option:hover,.motion-option.focused{background:var(--menu-hover);filter:none}.motion-option.selected{background:var(--menu-selected);color:var(--menu-selected-text)}.motion-option-text{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.motion-check{width:18px;flex:none;text-align:center;font-size:16px;opacity:0}.motion-option.selected .motion-check{opacity:1}.motion-select.motion-compact .motion-select-btn{height:42px;border-radius:16px;padding-left:12px}.motion-select.motion-compact .motion-option{min-height:40px;padding:9px 12px}.card .field.motion-enhanced{width:100%;margin-top:auto;background:transparent}.detail-controls .motion-select{width:auto;min-width:140px;flex:0 1 190px}.detail-controls .motion-menu{max-width:min(70vw,320px)}
dialog{padding:0;border:0;border-radius:28px;background:var(--container);color:var(--text);width:min(900px,calc(100vw - 32px));max-height:calc(100vh - 32px);box-shadow:0 24px 70px #0007}dialog::backdrop{background:#0009}.detail-shell{padding:18px}.detail-head{display:flex;align-items:center;gap:12px}.detail-head h2{flex:1;font-size:20px;font-weight:500;margin:0}.detail-head button{min-width:40px;padding:0 12px}.tabs{display:flex;gap:8px;margin:14px 0}.tabs button[aria-selected=true]{background:var(--primary);color:var(--surface)}.stage{position:relative;height:min(62vh,620px);min-height:330px;border-radius:22px;background:var(--stage);overflow:hidden;display:grid;place-items:center}.stage model-viewer{width:100%;height:100%;--poster-color:transparent;transition:opacity .2s ease,transform .28s ease}.stage model-viewer.state-changing{opacity:.16;transform:perspective(900px) rotateY(12deg) scaleX(.82)}.frame-view{width:72%;height:72%;object-fit:contain;padding:12px;border-radius:18px;background-color:#78909c;background-image:repeating-conic-gradient(#78909c 0% 25%,#b8c8cf 0% 50%);background-size:26px 26px}.detail-controls{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-top:12px}.detail-controls button{min-height:34px;padding:0 13px}.detail-controls select{width:auto;min-width:140px;background:var(--high);border-radius:12px;padding:3px 10px}.detail-status{margin:10px 2px 0;color:var(--muted);font-size:12px}.fold-button{background:var(--primary)!important;color:var(--surface)!important}.stage.fold-pulse{animation:foldPulse .5s ease}@keyframes foldPulse{0%,100%{transform:perspective(1200px) rotateY(0)}50%{transform:perspective(1200px) rotateY(8deg) scaleX(.92)}}
@media(max-width:700px){main{padding:16px}.filters{grid-template-columns:repeat(2,minmax(0,1fr))}.search{grid-column:span 1}.grid{grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}.card{padding:12px}.card>img{height:155px}h1{font-size:24px}.stage{min-height:300px;height:58vh}}@media(max-width:500px){.grid{grid-template-columns:repeat(2,minmax(0,1fr))}.card>img{height:180px}header{align-items:flex-start}.theme{width:100px}.detail-shell{padding:12px}.detail-controls .motion-select{min-width:120px;max-width:48%}}@media(prefers-reduced-motion:no-preference){.card{animation:appear .18s ease-out}@keyframes appear{from{opacity:.3;transform:translateY(4px)}to{opacity:1;transform:translateY(0)}}}
dialog.icon-morph-loading,dialog.icon-morphing{outline:0;overflow:visible;background:transparent;box-shadow:none}dialog.icon-morph-loading .stage,dialog.icon-morphing .stage{overflow:visible;background:transparent}dialog.icon-morph-loading .detail-head,dialog.icon-morph-loading .tabs,dialog.icon-morph-loading .detail-controls,dialog.icon-morph-loading .detail-status,dialog.icon-morphing .detail-head,dialog.icon-morphing .tabs,dialog.icon-morphing .detail-controls,dialog.icon-morphing .detail-status{visibility:hidden}
dialog.icon-morph-loading::backdrop{background:transparent}dialog.icon-morphing::backdrop{background:rgb(0 0 0 / var(--morph-backdrop,0))}
</style></head><body><main>
<header><div><h1>Device gallery</h1><p>Icons first. Open supported Pixel, Googlebook, and iPhone models to rotate the 3D model, inspect the exact frame, or switch fold states.</p></div><div class="field theme"><span>Appearance</span><select id="theme"><option value="system">System</option><option value="light">Light</option><option value="dark">Dark</option></select></div></header>
<div class="filters">
<div class="field"><span>Brand</span><select id="brand"><option value="">All brands</option><option value="pixel">Google Pixel / Googlebook</option><option value="samsung">Samsung</option><option value="oneplus">OnePlus</option><option value="oppo">OPPO</option><option value="nothing">Nothing / CMF</option><option value="xiaomi">Xiaomi</option><option value="redmi">Redmi</option><option value="poco">POCO</option><option value="honor">HONOR</option><option value="motorola">Motorola</option><option value="apple">Apple</option><option value="generic">Generic</option></select></div>
<div class="field"><span>Device type</span><select id="kind"><option value="">All devices</option><option value="phone">Phones</option><option value="tablet">Tablets</option><option value="laptop">Laptops</option><option value="pc">PCs</option></select></div>
<div class="field"><span>Model</span><select id="model"><option value="">All models</option></select></div>
<div class="field"><span>Sort</span><select id="sort"><option value="brand">By brand</option><option value="name">Model name</option><option value="colors">Most colors</option></select></div>
<label class="field search"><span>Search</span><input id="search" type="search" placeholder="Search phones, tablets, or laptops…"></label>
<div class="field"><span>Color selection</span><select id="colorMode"><option value="original">Default colors</option><option value="vibrant">Vibrant colors</option><option value="dark">Dark colors</option><option value="light">Light colors</option><option value="monochrome">Monochrome</option></select></div>
</div>
<div class="status"><span id="count" role="status" aria-live="polite"></span><button id="reset" type="button">Reset filters</button></div>
<div id="grid" class="grid"></div><p id="empty" class="empty" hidden>No matching devices. Try another search or reset the filters.</p>
<p class="foot"><span class="model-dot"></span>3D controls appear only where a reviewed/provisional model export exists. Drawn icons and extracted vendor assets are identified in the collection’s source notes.</p>
</main>
<dialog id="detail"><div class="detail-shell"><div class="detail-head"><h2 id="detailTitle"></h2><button id="detailClose" aria-label="Close">Close</button></div><div class="tabs"><button id="tab3d" aria-selected="true">3D model</button><button id="tabFrame" aria-selected="false">Frame</button></div><div id="stage" class="stage"><model-viewer id="viewer" camera-controls orientation="0deg 90deg 0deg" camera-orbit="155deg 78deg auto" min-camera-orbit="auto 0deg auto" max-camera-orbit="auto 180deg auto" environment-image="data:application/octet-stream;base64,__ENVIRONMENT__#.hdr" exposure="1.05" tone-mapping="neutral" shadow-intensity="0.7" shadow-softness="0.9" interaction-prompt="none"></model-viewer><img id="frameView" class="frame-view" hidden alt="Device frame"></div><div class="detail-controls"><button data-orbit="0deg 90deg auto">Front</button><button data-orbit="180deg 90deg auto">Rear</button><button data-orbit="90deg 90deg auto">Side</button><button data-orbit="155deg 78deg auto">Reset</button><button id="spin">Spin</button><button id="fold" class="fold-button" hidden>Unfold</button><select id="viewerFinish" aria-label="3D finish"></select><select id="frameSelect" aria-label="Frame" hidden></select></div><p id="detailStatus" class="detail-status">Choose 3D or frame.</p></div></dialog>
<script type="module">__MODEL_VIEWER__</script><script>
const devices=__DATA__,modelDataPrefix='__MODEL_DATA_PREFIX__';
const brand=document.getElementById('brand'),kind=document.getElementById('kind'),model=document.getElementById('model'),sort=document.getElementById('sort'),search=document.getElementById('search'),colorMode=document.getElementById('colorMode'),grid=document.getElementById('grid'),count=document.getElementById('count');
function pixelOrder(d){if(d.model==='pixel_fold')return[7,5];const match=/^pixel_(\d+)(?:_(.*))?$/.exec(d.model);if(!match)return[100,0];const ranks={'':0,xl:1,pro:1,pro_xl:2,fold:3,a:4,a_5g:5};return[Number(match[1]),ranks[match[2]||'']??6];}
devices.sort((a,b)=>{if(a.brand!=='pixel'||b.brand!=='pixel')return 0;const x=pixelOrder(a),y=pixelOrder(b);return x[0]-y[0]||x[1]-y[1];});
const brandNames={pixel:'Google Pixel',samsung:'Samsung',oneplus:'OnePlus',oppo:'OPPO',nothing:'Nothing / CMF',xiaomi:'Xiaomi',redmi:'Redmi',poco:'POCO',honor:'HONOR',motorola:'Motorola',apple:'Apple',generic:'Generic'};
const selectedColors=new Map(),loadedScripts=new Map();window.__DEVICE_MODEL_DATA__=window.__DEVICE_MODEL_DATA__||{};
const nice=s=>s.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase());
function label(d){return d.label.replace(/ \(provisional\)$/,'').replace(/\b(cmf|ce|fe|xl|lte|cn|gt|mix|xps|hp|asus)\b/gi,s=>s.toUpperCase()).replace(/\b[saefxgv]\d+e?\b/gi,s=>s.toUpperCase()).replace(/\b(\d+[ts]|[45]g)\b/gi,s=>s.toUpperCase()).replace(/\b(phone|pad|tab|pro|ultra|plus|edge|lite|go|mi|moto|razr|signature|magic\d*|magicpad|note|max|mini|robot|se|neo|groove|fold|flip)\b/g,s=>s[0].toUpperCase()+s.slice(1));}
const motionDropdowns=new Set(),MOTION_REDUCED=matchMedia('(prefers-reduced-motion: reduce)').matches,MOTION_OPEN_MS=250,MOTION_CLOSE_MS=180,MOTION_FULL_CLIP='inset(0px 0px 0px 0px round 20px)';
let motionMenuId=0;
function motionCollapsedClip(dd){const m=dd.menu.getBoundingClientRect(),b=dd.btn.getBoundingClientRect();const left=Math.max(0,Math.round(b.left-m.left)),right=Math.max(0,Math.round(m.right-b.right));const radius=getComputedStyle(dd.btn).borderBottomLeftRadius||'18px';return`inset(0px ${right}px 100% ${left}px round ${radius})`;}
function motionOpen(dd){if(dd.anim)dd.anim.cancel();dd.isOpen=true;dd.root.classList.add('open');dd.menu.classList.add('open');dd.btn.setAttribute('aria-expanded','true');if(MOTION_REDUCED)return;dd.seq=(dd.seq||0)+1;const seq=dd.seq;dd.anim=dd.menu.animate([{clipPath:motionCollapsedClip(dd),opacity:'0',filter:'blur(16px)',easing:'cubic-bezier(0.333,0.117,0.667,0.45)'},{clipPath:MOTION_FULL_CLIP,opacity:'1',filter:'blur(1px)',transform:'scaleY(1)',offset:.55,easing:'ease-out'},{clipPath:MOTION_FULL_CLIP,opacity:'1',filter:'blur(0px)',transform:'scaleY(1.03)',offset:.78,easing:'ease-out'},{clipPath:MOTION_FULL_CLIP,opacity:'1',filter:'blur(0px)',transform:'scaleY(1)'}],{duration:MOTION_OPEN_MS});dd.anim.onfinish=()=>{if(dd.seq===seq)dd.anim=null;};}
function motionClose(dd){if(!dd.isOpen)return;dd.isOpen=false;dd.btn.setAttribute('aria-expanded','false');dd.menu.querySelectorAll('.focused').forEach(el=>el.classList.remove('focused'));if(dd.anim)dd.anim.cancel();if(MOTION_REDUCED){dd.menu.classList.remove('open');dd.root.classList.remove('open');return;}dd.seq=(dd.seq||0)+1;const seq=dd.seq;dd.anim=dd.menu.animate([{clipPath:MOTION_FULL_CLIP,opacity:'1',filter:'blur(0px)',transform:'scaleY(1)'},{clipPath:motionCollapsedClip(dd),opacity:'0',filter:'blur(12px)'}],{duration:MOTION_CLOSE_MS,easing:'cubic-bezier(0.3,0,0.3,1)'});dd.anim.onfinish=()=>{if(dd.seq===seq){dd.menu.classList.remove('open');dd.root.classList.remove('open');dd.anim=null;}};}
function motionHideNow(dd){if(dd.anim)dd.anim.cancel();dd.anim=null;dd.isOpen=false;dd.btn.setAttribute('aria-expanded','false');dd.menu.classList.remove('open');dd.root.classList.remove('open');}
function closeMotionMenus(except=null){for(const dd of [...motionDropdowns]){if(!dd.root.isConnected){motionDropdowns.delete(dd);continue;}if(dd!==except)motionClose(dd);}}
function disposeMotionSelects(container){for(const select of container.querySelectorAll('select.motion-native')){const dd=select.__motionDropdown;if(!dd)continue;if(dd.anim)dd.anim.cancel();motionDropdowns.delete(dd);select.__motionDropdown=null;}}
function paintMotionMenu(dd){for(const item of dd.menu.children){const on=Number(item.dataset.index)===dd.select.selectedIndex;item.classList.toggle('selected',on);item.classList.remove('focused');item.setAttribute('aria-selected',String(on));}}
function syncMotionSelect(select){const dd=select.__motionDropdown;if(!dd)return;dd.root.hidden=select.hidden;if(select.hidden)motionHideNow(dd);const signature=[...select.options].map(o=>`${o.value}\u241f${o.textContent}\u241f${o.disabled}`).join('\u241e');if(signature!==dd.signature){dd.signature=signature;dd.menu.replaceChildren();[...select.options].forEach((option,index)=>{const item=document.createElement('button');item.type='button';item.className='motion-option';item.setAttribute('role','option');item.dataset.index=String(index);item.disabled=option.disabled;const text=document.createElement('span');text.className='motion-option-text';text.textContent=option.textContent;const check=document.createElement('span');check.className='motion-check';check.setAttribute('aria-hidden','true');check.textContent='✓';item.append(text,check);dd.menu.append(item);});}const option=select.selectedOptions[0];dd.value.textContent=option?.textContent||'';dd.btn.setAttribute('aria-label',dd.label+(option?' · '+option.textContent:''));paintMotionMenu(dd);}
function enhanceSelect(select,labelText,compact=false){if(select.__motionDropdown){syncMotionSelect(select);return select.__motionDropdown;}const root=document.createElement('div');root.className='motion-select'+(compact?' motion-compact':'');const btn=document.createElement('button');btn.type='button';btn.className='motion-select-btn';btn.setAttribute('aria-haspopup','listbox');btn.setAttribute('aria-expanded','false');const field=document.createElement('span');field.className='motion-field';const fieldLabel=document.createElement('span');fieldLabel.className='motion-field-label';fieldLabel.textContent=labelText;const value=document.createElement('span');value.className='motion-field-value';field.append(fieldLabel,value);const chevron=document.createElementNS('http://www.w3.org/2000/svg','svg');chevron.setAttribute('viewBox','0 0 24 24');chevron.setAttribute('aria-hidden','true');chevron.classList.add('motion-chevron');const chevronPath=document.createElementNS('http://www.w3.org/2000/svg','path');chevronPath.setAttribute('d','M7 10l5 5 5-5');chevronPath.setAttribute('fill','none');chevronPath.setAttribute('stroke','currentColor');chevronPath.setAttribute('stroke-width','2');chevronPath.setAttribute('stroke-linecap','round');chevronPath.setAttribute('stroke-linejoin','round');chevron.append(chevronPath);btn.append(field,chevron);const menu=document.createElement('div');menu.className='motion-menu';menu.id='motion-menu-'+(++motionMenuId);menu.setAttribute('role','listbox');menu.setAttribute('aria-label',labelText);btn.setAttribute('aria-controls',menu.id);root.append(btn,menu);select.classList.add('motion-native');select.insertAdjacentElement('afterend',root);select.closest('.field')?.classList.add('motion-enhanced');const dd={select,root,btn,menu,value,label:labelText,isOpen:false,active:-1,signature:null,anim:null,seq:0};select.__motionDropdown=dd;motionDropdowns.add(dd);const highlight=()=>{const kids=menu.children;for(let i=0;i<kids.length;i++)kids[i].classList.toggle('focused',i===dd.active);kids[dd.active]?.scrollIntoView({block:'nearest'});};const open=()=>{closeMotionMenus(dd);motionOpen(dd);dd.active=select.selectedIndex;highlight();};btn.addEventListener('click',event=>{event.stopPropagation();dd.isOpen?motionClose(dd):open();});btn.addEventListener('keydown',event=>{const opens=['ArrowDown','ArrowUp','Enter',' '];if(!dd.isOpen&&opens.includes(event.key)){event.preventDefault();open();return;}if(!dd.isOpen)return;const n=menu.children.length;if(event.key==='ArrowDown'){event.preventDefault();dd.active=Math.min(n-1,dd.active+1);highlight();}else if(event.key==='ArrowUp'){event.preventDefault();dd.active=Math.max(0,dd.active-1);highlight();}else if(event.key==='Home'){event.preventDefault();dd.active=0;highlight();}else if(event.key==='End'){event.preventDefault();dd.active=n-1;highlight();}else if(event.key==='Enter'&&dd.active>=0){event.preventDefault();menu.children[dd.active].click();}else if(event.key==='Escape'){event.preventDefault();motionClose(dd);}});menu.addEventListener('click',event=>{event.stopPropagation();const item=event.target.closest('.motion-option');if(!item||item.disabled)return;select.selectedIndex=Number(item.dataset.index);syncMotionSelect(select);motionClose(dd);select.dispatchEvent(new Event('change',{bubbles:true}));btn.focus({preventScroll:true});});select.addEventListener('change',()=>syncMotionSelect(select));syncMotionSelect(select);return dd;}
document.addEventListener('click',()=>closeMotionMenus());document.addEventListener('keydown',event=>{if(event.key==='Escape')closeMotionMenus();});
function available(){return devices.filter(d=>(!brand.value||d.brand===brand.value)&&(!kind.value||d.kind===kind.value));}
function refreshModels(){const previous=model.value;model.replaceChildren(new Option('All models',''));available().forEach(d=>model.add(new Option(label(d),d.model)));model.value=[...model.options].some(o=>o.value===previous)?previous:'';syncMotionSelect(model);}
function preferred(d){if(colorMode.value==='monochrome'){const mono=d.variants.find(v=>v.color==='monochrome');if(mono)return mono.color;}const remembered=selectedColors.get(d.model);if(remembered)return remembered;const patterns={vibrant:/blue|blu|grn|green|pink|pnk|red|orange|violet|purple|coral|sage|seafoam|sunny|burgundy|teal|lavender|yellow/i,dark:/black|blk|dark|graphite|space|charcoal/i,light:/white|silver|slv|milk|cream|beige|beg|sand/i};const p=patterns[colorMode.value];return(p&&d.variants.find(v=>p.test(v.color))||d.variants[0]).color;}
function action(text,cls,fn){const b=document.createElement('button');b.type='button';b.textContent=text;if(cls)b.className=cls;b.onclick=fn;return b;}
function render(){let list=available().filter(d=>(!model.value||d.model===model.value)&&label(d).toLowerCase().includes(search.value.toLowerCase().trim()));if(sort.value==='name')list.sort((a,b)=>label(a).localeCompare(label(b),undefined,{numeric:true}));if(sort.value==='colors')list.sort((a,b)=>b.variants.length-a.variants.length);disposeMotionSelects(grid);grid.replaceChildren();list.forEach(d=>{const card=document.createElement('article');card.className='card';const img=document.createElement('img');img.alt=label(d);img.loading='lazy';const color=preferred(d);img.classList.toggle('monochrome',color==='monochrome');img.src=d.variants.find(v=>v.color===color).src;const b=document.createElement('span');b.className='brand';b.textContent=d.kind==='laptop'?'Googlebook':brandNames[d.brand];const title=document.createElement('h2');title.textContent=label(d);card.append(img,b,title);if(d.provisional){const p=document.createElement('span');p.className='provisional';p.textContent='Provisional prelaunch';card.append(p);}const field=document.createElement('div');field.className='field';const caption=document.createElement('span');caption.textContent='Color';const select=document.createElement('select');select.setAttribute('aria-label',label(d)+' color');d.variants.forEach(v=>select.add(new Option(nice(v.color),v.color)));select.value=color;select.onchange=()=>{selectedColors.set(d.model,select.value);img.classList.toggle('monochrome',select.value==='monochrome');img.src=d.variants.find(v=>v.color===select.value).src;};field.append(caption,select);card.append(field);enhanceSelect(select,'Color',true);if(d.model3d){const actions=document.createElement('div');actions.className='card-actions';actions.append(action('Rotate','primary-action',()=>openDetail(d,'3d',false,select.value,img)));if(d.model3d.hasFrame)actions.append(action('Frame','',()=>openDetail(d,'frame',false,select.value)));if(d.model3d.articulated||(d.model3d.states.folded&&d.model3d.states.unfolded))actions.append(action('Fold / unfold','',()=>openDetail(d,'3d',true,select.value)));card.append(actions);}grid.append(card);});const modelCount=list.filter(d=>d.model3d).length;count.textContent=list.length+' models · '+list.reduce((n,d)=>n+d.variants.length,0)+' color variants'+(modelCount?' · '+modelCount+' with 3D':'');document.getElementById('empty').hidden=list.length!==0;}
brand.onchange=kind.onchange=()=>{refreshModels();render();};model.onchange=sort.onchange=render;search.oninput=render;colorMode.onchange=()=>{selectedColors.clear();render();};document.getElementById('theme').onchange=e=>{if(e.target.value==='system')delete document.documentElement.dataset.theme;else document.documentElement.dataset.theme=e.target.value;};document.getElementById('reset').onclick=()=>{brand.value='';kind.value='phone';model.value='';sort.value='brand';search.value='';colorMode.value='original';selectedColors.clear();refreshModels();[brand,kind,model,sort,colorMode].forEach(syncMotionSelect);render();};refreshModels();[[document.getElementById('theme'),'Appearance'],[brand,'Brand'],[kind,'Device type'],[model,'Model'],[sort,'Sort'],[colorMode,'Color selection']].forEach(([select,name])=>enhanceSelect(select,name));render();

__FOLD_CENTERING__
__ICON_MORPH__
const detail=document.getElementById('detail'),viewer=document.getElementById('viewer'),frameView=document.getElementById('frameView'),stage=document.getElementById('stage'),viewerFinish=document.getElementById('viewerFinish'),frameSelect=document.getElementById('frameSelect'),foldButton=document.getElementById('fold'),status=document.getElementById('detailStatus');
customElements.whenDefined('model-viewer').then(()=>{customElements.get('model-viewer').minimumRenderScale=1;});
enhanceSelect(viewerFinish,'Finish',true);enhanceSelect(frameSelect,'Frame',true);
let activeDevice=null,activeModel=null,activeState='default',activeTab='3d',modelUrl=null,loadToken=0,autoFoldAfterOpen=false,requestedFinishColor='',foldProgress=0,foldFrame=0,openingIcon=null,viewerLoadId=0;
function loadModelScript(id){if(window.__DEVICE_MODEL_DATA__[id])return Promise.resolve(window.__DEVICE_MODEL_DATA__[id]);if(loadedScripts.has(id))return loadedScripts.get(id);const promise=new Promise((resolve,reject)=>{const script=document.createElement('script');script.src=modelDataPrefix+id+'.js?v=__MODEL_DATA_VERSION__';script.onload=()=>window.__DEVICE_MODEL_DATA__[id]?resolve(window.__DEVICE_MODEL_DATA__[id]):reject(new Error('Model data missing'));script.onerror=()=>reject(new Error('Could not load '+id));document.head.append(script)});loadedScripts.set(id,promise);return promise;}
function availableStates(){return activeDevice?activeDevice.model3d.states:{};}
function defaultState(d){return d.model3d.states.unfolded?'unfolded':d.model3d.states.default?'default':d.model3d.states.folded?'folded':Object.keys(d.model3d.states)[0];}
async function openDetail(d,tab='3d',animateFold=false,color='',icon=null){cancelIconMorph();openingIcon=tab==='3d'&&!animateFold?icon:null;detail.classList.toggle('icon-morph-loading',!!openingIcon);activeModel=null;viewer.style.visibility='hidden';activeDevice=d;activeState=defaultState(d);autoFoldAfterOpen=animateFold;requestedFinishColor=color||preferred(d);document.getElementById('detailTitle').textContent=label(d);if(!detail.open)detail.showModal();showTab(tab);await setState(activeState);}
function showTab(tab){cancelIconMorph();if(tab!=='3d')detail.classList.remove('icon-morph-loading');openingIcon=tab==='3d'?openingIcon:null;activeTab=tab;const is3d=tab==='3d';viewer.hidden=!is3d;frameView.hidden=is3d;document.getElementById('tab3d').setAttribute('aria-selected',is3d);document.getElementById('tabFrame').setAttribute('aria-selected',!is3d);document.querySelectorAll('[data-orbit],#spin').forEach(el=>el.hidden=!is3d);frameSelect.hidden=is3d||!activeModel||activeModel.frames.length<2;syncMotionSelect(frameSelect);if(activeModel){if(is3d)loadViewer(activeModel);else showFrame();}}
async function setState(stateName){if(!activeDevice)return;const id=availableStates()[stateName];if(!id)return;activeState=stateName;const token=++loadToken;cancelIconMorph();viewer.style.visibility='hidden';status.textContent='Loading '+(stateName==='default'?'3D model':stateName+' model')+'…';try{const data=await loadModelScript(id);if(token!==loadToken)return;activeModel=data;populateModelControls();if(activeTab==='3d')loadViewer(data);else showFrame();updateFoldButton();}catch(error){if(token===loadToken){openingIcon=null;detail.classList.remove('icon-morph-loading');viewer.style.visibility='';status.textContent=error.message;loadedScripts.delete(id);}}}
function finishKey(value){return String(value||'').toLowerCase().replace(/[^a-z0-9]/g,'')}
function finishAliases(value){const key=finishKey(value);const aliases={blk:['obsidian','black','charcoal'],beg:['porcelain','beige','cream'],blu:['bay','blue','frost'],blue:['bay','blue','frost','indigo'],grn:['wintergreen','lemongrass','aloe','green','sage','pistachio','olive'],gry:['hazel','gray','grey','fog'],pnk:['peony','rose','pink','coral','hibiscus','canyon'],ppl:['iris','violet','purple'],slv:['silver']};return [key,...(aliases[key]||[]).map(finishKey)]}
function populateModelControls(){const previous=viewerFinish.selectedOptions[0]?.textContent;viewerFinish.replaceChildren();(activeModel.finishes||[]).forEach((f,i)=>viewerFinish.add(new Option(f.name,i)));const wanted=finishAliases(requestedFinishColor);let match=[...viewerFinish.options].find(o=>wanted.includes(finishKey(o.textContent)))||[...viewerFinish.options].find(o=>o.textContent===previous);viewerFinish.value=match?match.value:'0';viewerFinish.hidden=viewerFinish.options.length<2;frameSelect.replaceChildren();activeModel.frames.forEach((f,i)=>frameSelect.add(new Option(f.name,i)));frameSelect.hidden=activeTab==='3d'||frameSelect.options.length<2;syncMotionSelect(viewerFinish);syncMotionSelect(frameSelect);}
function activeMotion(){return activeModel?.articulation||activeModel?.robot_motion;}
function foldDuration(){return activeMotion()?.duration_seconds||activeMotion()?.duration||1;}
function setFold(progress){if(!activeMotion())return;foldProgress=Math.max(0,Math.min(1,Number(progress)));viewer.animationName=activeMotion().animation;viewer.play({repetitions:1});viewer.currentTime=(activeModel.robot_motion?.glb_time_start_seconds??Math.max(0,viewer.duration-foldDuration()))+foldProgress*foldDuration();viewer.pause();if(activeModel.articulation)recenterFold(viewer,activeModel,foldProgress);updateFoldButton();}
function animateFold(target){if(!activeMotion())return;cancelAnimationFrame(foldFrame);const start=foldProgress,end=Math.max(0,Math.min(1,Number(target))),started=performance.now(),length=Math.max(260,Math.abs(end-start)*(activeModel.robot_motion?foldDuration()*1000:900));const tick=now=>{const t=Math.min(1,(now-started)/length);const eased=t*t*(3-2*t);setFold(start+(end-start)*eased);if(t<1)foldFrame=requestAnimationFrame(tick)};foldFrame=requestAnimationFrame(tick);}
function updateFoldButton(){const articulated=!!activeMotion();const states=availableStates();const canFold=articulated||(states.folded&&states.unfolded);foldButton.hidden=!canFold;if(!canFold)return;foldButton.textContent=activeModel?.robot_motion?(foldProgress<.5?'Deploy camera':'Stow camera'):articulated?(foldProgress<.5?'Fold':'Unfold'):(activeState==='folded'?'Unfold':'Fold');}
function loadViewer(data){cancelIconMorph();viewerLoadId++;viewer.style.visibility='hidden';viewer.orientation=['generic-phone','generic-tablet','generic-pc'].includes(data.id)?'0deg 0deg 0deg':activeDevice?.kind==='tablet'?'90deg 0deg 90deg':'0deg 90deg 0deg';viewer.__foldCenter=null;viewer.hidden=false;frameView.hidden=true;viewer.classList.add('state-changing');status.textContent='Loading '+data.name+'…';if(modelUrl)URL.revokeObjectURL(modelUrl);const bytes=Uint8Array.from(atob(data.glb),c=>c.charCodeAt(0));modelUrl=URL.createObjectURL(new Blob([bytes],{type:'model/gltf-binary'}));viewer.src=modelUrl;}
function selectedFinish(){return activeModel?.finishes?.[Number(viewerFinish.value)]||activeModel?.finishes?.[0]||null;}
function applyViewerFinish(){if(!viewer.model||!activeModel)return;const finish=selectedFinish();if(!finish)return;for(const[role,settings]of Object.entries(finish.materials)){const material=viewer.model.materials.find(m=>m.name===activeModel.slots[role]);if(!material||!settings.rgb)continue;const linear=settings.rgb.map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);material.pbrMetallicRoughness.setBaseColorFactor([...linear,1]);if(settings.rough!==undefined)material.pbrMetallicRoughness.setRoughnessFactor(settings.rough);}}
async function screenChecker(){if(!viewer.model||!activeModel)return;for(const material of viewer.model.materials.filter(m=>m.name.startsWith('Device screen |'))){const screen=activeModel.screens.find(s=>s.material===material.name);if(!screen)continue;const canvas=document.createElement('canvas');canvas.width=720;canvas.height=Math.round(720*screen.resolution[1]/screen.resolution[0]);const ctx=canvas.getContext('2d'),cell=90;for(let y=0;y<canvas.height/cell;y++)for(let x=0;x<8;x++){ctx.fillStyle=(x+y)%2?'#aed1e5':'#447893';ctx.fillRect(x*cell,y*cell,cell,cell);}const texture=await viewer.createTexture(canvas.toDataURL());material.pbrMetallicRoughness.setBaseColorFactor([1,1,1,1]);material.pbrMetallicRoughness.baseColorTexture.setTexture(texture);}}
viewer.addEventListener('load',async()=>{if(!activeModel||!detail.open)return;const loadedId=viewerLoadId,loadedModel=activeModel;applyViewerFinish();if(activeMotion()){viewer.animationName=activeMotion().animation;await viewer.updateComplete;if(loadedId!==viewerLoadId||!detail.open)return;viewer.play({repetitions:1});viewer.currentTime=activeModel.robot_motion?.glb_time_start_seconds||0;viewer.pause();foldProgress=0;}for(const material of viewer.model.materials.filter(m=>/clear.*cover|cover.*clear/i.test(m.name))){material.setTransmissionFactor(0);material.setAlphaMode('BLEND');material.pbrMetallicRoughness.setBaseColorFactor([.02,.025,.03,.07]);}await screenChecker().catch(e=>console.warn('screen texture',e));if(loadedId!==viewerLoadId||loadedModel!==activeModel||!detail.open||activeTab!=='3d')return;viewer.cameraOrbit=activeDevice?.kind==='laptop'?'28deg 68deg auto':'155deg 78deg auto';viewer.cameraTarget='auto auto auto';viewer.updateFraming();viewer.jumpCameraToGoal();viewer.classList.remove('state-changing');const icon=openingIcon;openingIcon=null;if(icon){const variant=activeDevice.variants.find(v=>v.color===requestedFinishColor);await startIconMorph(viewer,icon,variant?.sourceSvg,activeModel,detail,stage).catch(error=>{cancelIconMorph();console.warn('Icon morph',error);});if(loadedId!==viewerLoadId||!detail.open||activeTab!=='3d')return;}detail.classList.remove('icon-morph-loading');viewer.style.visibility='';updateFoldButton();status.textContent=(activeModel.robot_motion?'Camera stowed - use Deploy camera to animate':activeModel.articulation?'Unfolded · use Fold to animate the real hinge':activeState==='default'?'3D model':nice(activeState))+' · drag to orbit · right-drag or two-finger drag to pan · scroll or pinch to zoom';if(autoFoldAfterOpen&&activeModel.articulation){autoFoldAfterOpen=false;setTimeout(()=>animateFold(1),350);}else if(autoFoldAfterOpen&&activeState==='folded'){autoFoldAfterOpen=false;setTimeout(toggleFold,350);}});
viewer.addEventListener('error',()=>{cancelIconMorph();openingIcon=null;detail.classList.remove('icon-morph-loading');viewer.style.visibility='';viewer.classList.remove('state-changing');status.textContent='Could not load this model.'});
function frameImage(frame,finish){if(!finish)return frame.image;const rail=finish.materials?.rail?.rgb;if(!rail)return frame.image;const color='#'+rail.map(v=>Math.round(v*255).toString(16).padStart(2,'0')).join('');return'data:image/svg+xml;base64,'+btoa(atob(frame.image.split(',')[1]).replace(/--device-color:#[0-9a-f]{6}/g,'--device-color:'+color));}
function showFrame(){if(!activeModel?.frames?.length){frameView.removeAttribute('src');status.textContent='No frame export for this profile.';return;}const frame=activeModel.frames[Number(frameSelect.value)||0];frameView.src=frameImage(frame,selectedFinish());frameView.alt=activeDevice?label(activeDevice)+' '+frame.name+' frame':frame.name;status.textContent=frame.name+' · exact exported frame mask';}
async function toggleFold(){if(activeMotion()){animateFold(foldProgress<.5?1:0);return;}const target=activeState==='folded'?'unfolded':'folded';stage.classList.remove('fold-pulse');void stage.offsetWidth;stage.classList.add('fold-pulse');await setState(target);}
document.getElementById('tab3d').onclick=()=>showTab('3d');document.getElementById('tabFrame').onclick=()=>showTab('frame');viewerFinish.onchange=()=>{applyViewerFinish();if(activeTab==='frame')showFrame();};frameSelect.onchange=showFrame;foldButton.onclick=toggleFold;document.querySelectorAll('[data-orbit]').forEach(button=>button.onclick=()=>viewer.cameraOrbit=button.dataset.orbit);document.getElementById('spin').onclick=()=>{const enabled=viewer.hasAttribute('auto-rotate');viewer.toggleAttribute('auto-rotate',!enabled);document.getElementById('spin').textContent=enabled?'Spin':'Stop spin';};document.getElementById('detailClose').onclick=()=>detail.close();detail.addEventListener('close',()=>{if(detail.open)return;cancelIconMorph();detail.classList.remove('icon-morph-loading');openingIcon=null;viewerLoadId++;viewer.style.visibility='';closeMotionMenus();cancelAnimationFrame(foldFrame);foldProgress=0;loadToken++;viewer.src=null;viewer.removeAttribute('auto-rotate');document.getElementById('spin').textContent='Spin';if(modelUrl)URL.revokeObjectURL(modelUrl);modelUrl=null;activeDevice=activeModel=null;});
</script></body></html>'''


def main() -> None:
    model_groups = build_model_data()
    model_viewer = ''
    environment = ''
    if MODEL_BASE.exists():
        model_viewer = (MODEL_BASE / 'vendor/model-viewer.min.js').read_text(encoding='utf-8').replace('</script', '<\\/script')
        environment = base64.b64encode((MODEL_BASE.parent / 'pixel-10-pro-model/source/studio_small_09_1k.hdr').read_bytes()).decode()

    for embedded, target, model_prefix in [
        (True, ROOT / 'device_icons_svg/gallery.html', 'model_data/'),
        (False, ROOT / 'tmp/ref5/gallery_preview.html', '../../device_icons_svg/model_data/'),
    ]:
        data = []
        for device in CATALOG:
            entry = {k: device[k] for k in ('model', 'brand', 'kind', 'label')}
            entry['provisional'] = device.get('provisional', False)
            entry['variants'] = []
            for variant in device['variants']:
                src = data_uri(Path(variant['thumb']), 'image/png') if embedded else variant['thumb']
                entry['variants'].append({'color': variant['color'], 'src': src,
                    'sourceSvg': Path(variant['path']).read_text(encoding='utf-8') if Path(variant['path']).exists() else ''})
            mono = ROOT / 'tmp/ref5/all_phones' / f'ic_{device["model"]}_monochrome_icon.png'
            if mono.exists():
                src = data_uri(mono, 'image/png') if embedded else mono.as_posix()
                entry['variants'].append({'color': 'monochrome', 'src': src})
            group = icon_model_group(device['model'])
            if group and group in model_groups:
                entry['model3d'] = model_groups[group]
            data.append(entry)
        target.write_text(
            PAGE.replace('__DATA__', json.dumps(data, separators=(',', ':')))
                .replace('__MODEL_DATA_VERSION__', str(time.time_ns()))
                .replace('__MODEL_VIEWER__', model_viewer)
                .replace('__ENVIRONMENT__', environment)
                .replace('__MODEL_DATA_PREFIX__', model_prefix)
                .replace('__ICON_MORPH__', (ROOT/'tmp/ref5/gallery_icon_morph.js').read_text(encoding='utf-8'))
                .replace('__FOLD_CENTERING__', (MODEL_BASE/'fold_centering.js').read_text(encoding='utf-8')),
            encoding='utf-8',
        )
    modeled = sum(1 for d in data if d.get('model3d'))
    print(f'Built combined gallery: {len(CATALOG)} icon models, {modeled} with 3D/frame review controls, {len(model_groups)} 3D families.')


if __name__ == '__main__':
    main()
