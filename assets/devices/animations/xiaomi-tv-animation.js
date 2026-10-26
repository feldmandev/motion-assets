import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';

const clamp = x => Math.max(0, Math.min(1, x));
const ease = x => {const t = clamp(x); return t*t*t*(t*(t*6-15)+10);};
const mix = (a,b,t) => a+(b-a)*t;
const fit = (r,a) => {const h=Math.min(r.height,r.width/a),w=h*a; return {x:r.x+(r.width-w)/2,y:r.y+(r.height-h)/2,width:w,height:h};};

// The same Blender camera samples drive Three, Filament and Qt Quick 3D.
export function tvPose(data, seconds, origin, target, viewport) {
  const intro=data.introDuration,formation=ease(seconds/intro);
  const cameraSeconds=clamp((seconds-intro)/(data.duration-intro))*data.duration;
  const f=cameraSeconds/data.duration*(data.frames.length-1),i=Math.floor(f);
  const a=data.frames[i],b=data.frames[Math.min(i+1,data.frames.length-1)],p=a.map((v,j)=>mix(v,b[j],f-i));
  const icon=fit(origin,1),r=data.remoteRect,bounds=data.iconBounds;
  const body={x:icon.x+icon.width*bounds[0]/108,y:icon.y+icon.height*bounds[1]/108,width:icon.width*bounds[2]/108,height:icon.height*bounds[3]/108};
  const first={width:body.width/r[2],height:body.height/r[3]};
  first.x=body.x-r[0]*first.width;first.y=body.y-r[1]*first.height;
  const rect={};
  for(const key of ['x','y','width','height'])rect[key]=mix(first[key],target[key],formation);
  const half=data.near*18/p[4]/data.sourceAspect,aspect=rect.width/rect.height;
  return {eye:[p[0],p[2],-p[1]],pitch:p[3]-Math.PI/2,
    left:(-1-2*rect.x/rect.width)*half*aspect,right:(2*(viewport.width-rect.x)/rect.width-1)*half*aspect,
    bottom:(1-2*(viewport.height-rect.y)/rect.height)*half,top:(1+2*rect.y/rect.height)*half,
    morph:formation,remoteScale:[1,1,1],tvWidth:(data.screenHeight*target.width/target.height-data.screenWidth)/data.widthTargetDelta};
}

export async function startTvTransition(config, bridge) {
  const data=await fetch(new URL('./xiaomi-tv-transition.json',import.meta.url)).then(r=>r.json());
  const response=await fetch(new URL('../../../'+data.glbUrl,import.meta.url));
  if(!response.ok)throw Error('Animation model unavailable');
  const packed=await response.arrayBuffer();
  const digest=[...new Uint8Array(await crypto.subtle.digest('SHA-256',packed))].map(b=>b.toString(16).padStart(2,'0')).join('');
  if(digest!==data.sha256)throw Error('Animation checksum mismatch');
  const raw=await new Response(new Blob([packed]).stream().pipeThrough(new DecompressionStream('gzip'))).arrayBuffer();
  const gltf=await new GLTFLoader().parseAsync(raw,'');
  const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,preserveDrawingBuffer:!!config.capture});
  renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.setSize(innerWidth,innerHeight);
  const resize=()=>renderer.setSize(innerWidth,innerHeight);addEventListener('resize',resize);
  renderer.toneMapping=THREE.LinearToneMapping;
  const host=document.getElementById('scene'),icon=document.getElementById('icon');
  host.prepend(renderer.domElement);icon.style.display='none';
  const scene=new THREE.Scene(),camera=new THREE.PerspectiveCamera();
  const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(new RoomEnvironment(),.04).texture;pmrem.dispose();
  scene.add(new THREE.HemisphereLight(0xf4f0fa,0x162233,1.2));
  const key=new THREE.DirectionalLight(0xffffff,3);key.position.set(-30,60,40);scene.add(key,gltf.scene);
  const remote=gltf.scene.getObjectByName('TVRemote'),wide=[],iconMeshes=[],stageMeshes=[],screens=[],morphUniform={value:0};
  gltf.scene.traverse(node=>{if(!node.isMesh)return;
    if(node.morphTargetDictionary?.Icon===undefined)stageMeshes.push(node);
    if(node.morphTargetInfluences?.length)(node.morphTargetDictionary?.Icon!==undefined?iconMeshes:wide).push(node);
    if(node.morphTargetDictionary?.Icon!==undefined){
      const wasArray=Array.isArray(node.material),materials=wasArray?node.material:[node.material];
      node.material=materials.map(original=>{const material=original.clone(),setting=data.iconMaterials.find(m=>m.name===original.name);
        material.onBeforeCompile=shader=>{
          shader.uniforms.iconMorph=morphUniform;if(config.capture)material.userData.debugShader=shader;
          setting.colors.forEach((rgb,i)=>{shader.uniforms['iconColor'+i]={value:new THREE.Color().setRGB(...rgb,THREE.SRGBColorSpace)};});
          shader.vertexShader='varying vec2 iconUv;\n'+shader.vertexShader;
          shader.vertexShader=shader.vertexShader.replace('#include <uv_vertex>','#include <uv_vertex>\niconUv=uv;');
          shader.fragmentShader='varying vec2 iconUv; uniform float iconMorph; uniform vec3 iconColor0,iconColor1,iconColor2,iconColor3;\n'+shader.fragmentShader;
          shader.fragmentShader=shader.fragmentShader.replace('#include <color_fragment>',`#include <color_fragment>
            float gx=iconUv.x;
            vec3 flatColor=mix(iconColor0,iconColor1,clamp(gx/.43,0.,1.));
            flatColor=mix(flatColor,iconColor2,clamp((gx-.43)/.21,0.,1.));
            flatColor=mix(flatColor,iconColor3,clamp((gx-.64)/.36,0.,1.));
            diffuseColor.rgb=mix(flatColor,diffuseColor.rgb,iconMorph)*iconMorph;`);
          shader.fragmentShader=shader.fragmentShader.replace('#include <lights_physical_fragment>','#include <lights_physical_fragment>\nmaterial.specularColor*=iconMorph;material.specularF90*=iconMorph;');
          shader.fragmentShader=shader.fragmentShader.replace('#include <emissivemap_fragment>','#include <emissivemap_fragment>\ntotalEmissiveRadiance=flatColor*(1.-iconMorph)+totalEmissiveRadiance*iconMorph;');
        };material.customProgramCacheKey=()=>original.name+'-tv-icon-v1';return material;});
      if(!wasArray)node.material=node.material[0];
    }
    if(node.name===data.screenNode||node.material.name===data.screenMaterial){node.material=new THREE.MeshBasicMaterial({color:'black',toneMapped:false});screens.push(node.material);}
  });
  if(config.capture)window.tvVisualDebug={morphUniform,iconMeshes,stageMeshes};
  let texture=null,image=null,begin=null,raf=0,disposed=false;
  const origin=config.origin||{x:innerWidth/2-54,y:innerHeight/2-54,width:108,height:108};
  async function bind() {if(!bridge.snapshot()||image===bridge.snapshot())return;
    image=bridge.snapshot();const next=await new THREE.TextureLoader().loadAsync(image);
    if(disposed){next.dispose();return;}texture?.dispose();texture=next;texture.colorSpace=THREE.SRGBColorSpace;texture.flipY=false;
    for(const material of screens){material.color.set('white');material.map=texture;material.needsUpdate=true;}
  }
  function draw(seconds) {
    const target=bridge.target()||fit({x:0,y:0,width:innerWidth,height:innerHeight},16/9);
    const pose=tvPose(data,seconds,origin,target,{width:innerWidth,height:innerHeight});
    camera.position.fromArray(pose.eye);camera.rotation.set(pose.pitch,0,0);
    camera.projectionMatrix.makePerspective(pose.left,pose.right,pose.top,pose.bottom,data.near,400);
    camera.projectionMatrixInverse.copy(camera.projectionMatrix).invert();
    for(const node of stageMeshes)node.visible=seconds>=data.introDuration;
    morphUniform.value=pose.morph;for(const node of iconMeshes)node.morphTargetInfluences[0]=1-pose.morph;
    remote.scale.fromArray(pose.remoteScale);for(const node of wide)node.morphTargetInfluences[0]=pose.tvWidth;
    renderer.domElement.style.opacity=1;host.style.opacity=1;bridge.fade(0);
    renderer.render(scene,camera);
  }
  bridge.onReady(bind);await bind();draw(0);await renderer.compileAsync(scene,camera);
  let prepared=false;
  function tick(now) {
    if(disposed||bridge.done())return;
    if(begin===null){
      if(!bridge.ready()){raf=requestAnimationFrame(tick);return;}
      if(bridge.snapshot()&&!texture){bind().then(()=>{if(!disposed)raf=requestAnimationFrame(tick);}).catch(()=>bridge.complete());return;}
      if(!prepared){prepared=true;bridge.prepared();}
      if(!bridge.visible()){raf=requestAnimationFrame(tick);return;}
      begin=now;
    }
    const seconds=(now-begin)/1000;draw(seconds);
    if(seconds>=data.duration)bridge.handoff();
    if(seconds>=data.duration){bridge.complete();return;}
    raf=requestAnimationFrame(tick);
  }
  window.setSeamlessBackProgress=progress=>{cancelAnimationFrame(raf);draw(data.duration*(1-clamp(progress)));};
  if(config.capture){window.renderTransitionFrame=seconds=>draw(seconds);window.transitionReady=true;}
  else raf=requestAnimationFrame(tick);
  return ()=>{removeEventListener('resize',resize);disposed=true;cancelAnimationFrame(raf);texture?.dispose();scene.environment?.dispose();
    gltf.scene.traverse(node=>{if(node.isMesh){node.geometry.dispose();for(const m of Array.isArray(node.material)?node.material:[node.material])m.dispose();}});
    renderer.dispose();};
}
