const dialog=document.getElementById('viewer-dialog');
const viewer=document.getElementById('viewer');
const viewerFinish=document.getElementById('viewer-finish');
const viewerFoldControls=document.getElementById('viewer-fold-controls');
const viewerFold=document.getElementById('viewer-fold');
let activeDevice=null, modelUrl=null, foldFrame=0;
function foldDuration(){
  const fallback=activeDevice?.articulation?.duration_seconds||1;
  return fallback;
}
function setFold(progress){
  if(!activeDevice?.articulation) return;
  const value=Math.max(0,Math.min(1,Number(progress)));
  viewer.animationName=activeDevice.articulation.animation;
  viewer.pause();
  viewer.currentTime=Math.max(0,viewer.duration-foldDuration())+value*foldDuration();
  recenterFold(viewer,activeDevice,value);
  viewerFold.value=value;
}
function animateFold(target){
  if(!activeDevice?.articulation) return;
  cancelAnimationFrame(foldFrame);
  const start=Number(viewerFold.value);
  const end=Number(target);
  const started=performance.now();
  const length=Math.max(180,Math.abs(end-start)*700);
  const tick=now=>{
    const t=Math.min(1,(now-started)/length);
    const eased=t*t*(3-2*t);
    setFold(start+(end-start)*eased);
    if(t<1) foldFrame=requestAnimationFrame(tick);
  };
  foldFrame=requestAnimationFrame(tick);
}
async function openViewer(device,index){
  activeDevice=device;
  viewer.__foldCenter=null;
  cancelAnimationFrame(foldFrame);
  document.getElementById('viewer-title').textContent=device.name;
  document.getElementById('viewer-status').textContent='Loading 3D model…';
  viewerFinish.replaceChildren(...device.finishes.map((finish,i)=>new Option(finish.name,i)));
  viewerFinish.value=selected[device.id]||index;
  viewerFoldControls.hidden=!device.articulation;
  viewerFold.value=0;
  viewer.orientation=device.form_factor==='tablet'?'90deg 0deg 90deg':'0deg 90deg 0deg';
  viewer.cameraOrbit='155deg 78deg auto';
  dialog.showModal();
  await customElements.whenDefined('model-viewer');
  customElements.get('model-viewer').minimumRenderScale=1;
  if(modelUrl) URL.revokeObjectURL(modelUrl);
  if(device.glb){
    const bytes=Uint8Array.from(atob(device.glb),c=>c.charCodeAt(0));
    modelUrl=URL.createObjectURL(new Blob([bytes],{type:'model/gltf-binary'}));
    viewer.src=modelUrl;
  }else{
    modelUrl=null;
    viewer.src=device.glb_url;
  }
}
function applyViewerFinish(){
  if(!viewer.model||!activeDevice) return;
  const finish=activeDevice.finishes[Number(viewerFinish.value)];
  for(const [role,settings] of Object.entries(finish.materials)){
    const material=viewer.model.materials.find(m=>m.name===activeDevice.slots[role]);
    const linear=settings.rgb.map(v=>v<=.04045?v/12.92:((v+.055)/1.055)**2.4);
    if(material){material.pbrMetallicRoughness.setBaseColorFactor([...linear,1]);if(settings.rough!==undefined)material.pbrMetallicRoughness.setRoughnessFactor(settings.rough);}
  }
}
viewer.addEventListener('load',async()=>{
  applyViewerFinish();
  if(activeDevice?.articulation){
    viewer.animationName=activeDevice.articulation.animation;
    viewer.pause();
    viewer.currentTime=0;
    viewerFold.value=0;
  }
  // Raster transmission cannot resolve the nested lens glass behind this cover.
  // A thin alpha surface keeps the black backing and optics visible in WebGL.
  if(!viewer.originalGltfJson?.asset?.extras?.opticsTreatment)for(const material of viewer.model.materials.filter(m=>/clear.*cover|cover.*clear/i.test(m.name))){
    material.setTransmissionFactor(0);
    material.setAlphaMode('BLEND');
    material.pbrMetallicRoughness.setBaseColorFactor([.02,.025,.03,.07]);
  }
  // A square grid makes bezel width, corner clipping and the native aspect visible.
  const materials=viewer.model.materials.filter(m=>m.name.startsWith('Device screen |'));
  for(const material of materials){
    const screen=activeDevice.screens.find(s=>s.material===material.name);
    if(activeDevice.articulation){
      material.pbrMetallicRoughness.setBaseColorFactor([.07,.16,.22,1]);
      material.setEmissiveFactor([.07,.16,.22]);
    }
    const canvas=document.createElement('canvas');canvas.width=1080;
    canvas.height=Math.round(1080*screen.resolution[1]/screen.resolution[0]);
    const ctx=canvas.getContext('2d');
    const cell=canvas.width/8;
    for(let y=0;y<canvas.height/cell;y++)for(let x=0;x<8;x++){
      ctx.fillStyle=(x+y)%2?'#aed1e5':'#447893';ctx.fillRect(x*cell,y*cell,cell,cell);
    }
    const texture=await viewer.createTexture(canvas.toDataURL());
    material.pbrMetallicRoughness.setBaseColorFactor([1,1,1,1]);
    material.pbrMetallicRoughness.baseColorTexture.setTexture(texture);
    if(!activeDevice.articulation){material.emissiveTexture.setTexture(texture);material.setEmissiveFactor([1,1,1]);}
  }
  document.getElementById('viewer-status').textContent='Drag to orbit · scroll or pinch to zoom · pan with right/middle drag';
});
viewer.addEventListener('error',()=>{document.getElementById('viewer-status').textContent='Could not load this model.'});
viewerFinish.addEventListener('change',applyViewerFinish);
viewerFold.addEventListener('input',()=>setFold(viewerFold.value));
document.querySelectorAll('[data-fold]').forEach(button=>button.onclick=()=>animateFold(button.dataset.fold));
document.querySelectorAll('[data-orbit]').forEach(button=>button.onclick=()=>{viewer.cameraOrbit=button.dataset.orbit});
document.getElementById('viewer-close').onclick=()=>dialog.close();
dialog.addEventListener('close',()=>{cancelAnimationFrame(foldFrame);viewer.src=null;if(modelUrl)URL.revokeObjectURL(modelUrl);modelUrl=null});
