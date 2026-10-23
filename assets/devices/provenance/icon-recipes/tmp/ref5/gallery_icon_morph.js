// Geometry bridge for reviewed SVG path roles. Uses the gallery's pinned
// model-viewer Three.js scene; no second renderer and no icon/model crossfade.
let iconMorph = null;
function iconMorphRoles(paths,data){
  if(data.articulation||data.robot_motion||/-fold(?:-|$)/.test(data.id))return null;
  if(paths.some(p=>p.hasAttribute('data-morph-unsupported'))||paths[0]?.ownerSVGElement.hasAttribute('data-morph-unsupported'))return null;
  if(paths.some(p=>p.hasAttribute('data-morph-role'))){
    const tagged=new Map();
    for(let i=0;i<paths.length;i++){
      const role=paths[i].getAttribute('data-morph-role');
      if(!role)return null;
      if(!tagged.has(role))tagged.set(role,[]);tagged.get(role).push(i);
    }
    const one=name=>tagged.get(name)?.length===1?tagged.get(name)[0]:undefined;
    const layers={};
    const surface=name=>{const indices=tagged.get(name);if(!indices?.length)return undefined;layers[indices[0]]=indices.slice(1);return indices[0];};
    const indexed=prefix=>{const result=[];for(const [key,indices] of tagged)if(new RegExp(`^${prefix}-[0-9]+$`).test(key)){result[Number(key.split('-').at(-1))]=indices[0];layers[indices[0]]=indices.slice(1);}return result;};
    const roles={body:one('body'),bar:one('bar'),logo:one('logo'),glass:indexed('glass'),rings:indexed('ring'),flashes:indexed('flash'),sensors:indexed('sensor'),bridge:surface('bridge'),band:one('rear-band'),insert:one('rear-insert'),layers};
    if(roles.bar!==undefined)layers[roles.bar]=tagged.get('bar-fill')||[];
    const rims=tagged.get('flash-rim-0');
    if(rims?.length&&roles.flashes[0]!==undefined){layers[rims[0]]=[...rims.slice(1),roles.flashes[0]];roles.flashes[0]=rims[0];}
    const known=/^(body|bar|bar-fill|logo|bridge|rear-band|rear-insert|glass-\d+|ring-\d+|flash-\d+|flash-rim-0|sensor-\d+)$/;
    if([...tagged.keys()].some(k=>!known.test(k))||roles.body===undefined||!roles.glass.length||Array.from(roles.glass).some(i=>i===undefined))return null;
    return roles;
  }
  const fill=i=>paths[i]?.getAttribute('fill');
  if(data.id.startsWith('pixel-')&&paths.length===4)return {body:0,bar:1,glass:[2],logo:3};
  // These generators have explicit, stable path ordering. Refuse other layouts
  // rather than guessing which camera, logo, or decorative path a mesh represents.
  const count=data.icon_morph?.windows;
  if(data.id.startsWith('galaxy-')&&fill(0)==='url(#body)'&&count){
    const rings=[],glass=[];
    for(let i=0;i<count;i++){
      const ring=paths.findIndex(p=>p.getAttribute('fill')===`url(#ring${i})`);
      const lens=paths.findIndex(p=>p.getAttribute('fill')===`url(#glass${i})`);
      if(ring<0||lens<0)return null;rings.push(ring);glass.push(lens);
    }
    if(paths.length!==2*count+4)return null;
    return {body:0,rings,glass,flash:paths.length-3,logo:paths.length-1,layers:{[paths.length-3]:[paths.length-2]}};
  }
  return null;
}
function cancelIconMorph(){
  if(!iconMorph)return;
  const morph=iconMorph;iconMorph=null;
  cancelAnimationFrame(morph.frame);
  morph.restore();morph.resolve();
}
async function startIconMorph(viewer,icon,source,data,dialog,stage){
  if(!source||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
  const svg=new DOMParser().parseFromString(source,'image/svg+xml').documentElement;
  const paths=[...svg.querySelectorAll('path')].filter(node=>!node.closest('defs'));
  const roles=iconMorphRoles(paths,data);
  if(!roles||paths.some(p=>p.closest('[transform]')||p.getAttribute('fill')==='none'||(p.closest('[stroke]')&&p.closest('[stroke]').getAttribute('stroke')!=='none')))return;
  const scene=viewer[Object.getOwnPropertySymbols(viewer).find(key=>key.description==='scene')];
  if(!scene?.queueRender)throw new Error('Pinned model-viewer scene bridge unavailable');
  const host=document.createElement('div');
  host.style.cssText='position:fixed;left:-10000px;top:0;width:108px;height:108px;pointer-events:none';
  host.append(document.importNode(svg,true));document.body.append(host);
  const shapes=[...host.querySelectorAll('path')].filter(node=>!node.closest('defs'));
  const boxes=shapes.map(path=>path.getBBox());
  const body=boxes[roles.body];
  const center=scene.boundingBox.getCenter(scene.position.clone());
  const entries=[],resources=[];
  let resolve;
  const done=new Promise(finish=>resolve=finish);
  const oldStyle=viewer.getAttribute('style'),oldOrbit=viewer.cameraOrbit;
  const oldControls=viewer.cameraControls;
  const oldShadow=viewer.shadowIntensity,oldVisibility=icon.style.visibility;
  const morph={frame:0,resolve,restore:()=>{
    for(const entry of entries){entry.node.geometry=entry.originalGeometry;entry.node.material=entry.originalMaterial;entry.node.frustumCulled=entry.frustumCulled;entry.geometry.dispose();entry.material.dispose();}
    for(const texture of resources)texture.dispose();
    host.remove();icon.style.visibility=oldVisibility;
    if(oldStyle===null)viewer.removeAttribute('style');else viewer.setAttribute('style',oldStyle);
    viewer.cameraOrbit=oldOrbit;viewer.shadowIntensity=oldShadow;viewer.cameraControls=oldControls;viewer.jumpCameraToGoal();
    dialog.classList.remove('icon-morphing','icon-morph-loading');dialog.style.removeProperty('--morph-backdrop');scene.queueRender();
  }};
  iconMorph=morph;
  // Rasterize fills, not whole icons: the camera bar and logo remain the same
  // model surfaces throughout. Their gradients become their selected finish.
  async function fillTexture(index){
    const box=boxes[index],copy=svg.cloneNode(true);
    copy.setAttribute('viewBox',`${box.x} ${box.y} ${box.width} ${box.height}`);
    copy.setAttribute('width','256');copy.setAttribute('height','512');
    copy.setAttribute('preserveAspectRatio','none');
    [...copy.children].filter(node=>node.localName!=='defs').forEach(node=>node.remove());
    const rect=document.createElementNS('http://www.w3.org/2000/svg','rect');
    rect.setAttribute('x',box.x);rect.setAttribute('y',box.y);
    rect.setAttribute('width',box.width);rect.setAttribute('height',box.height);
    rect.setAttribute('fill',shapes[index].getAttribute('fill'));copy.append(rect);
    const layers=roles.layers?.[index];
    for(const layer of layers||[])copy.append(paths[layer].cloneNode(true));
    const facade=await viewer.createTexture('data:image/svg+xml,'+encodeURIComponent(new XMLSerializer().serializeToString(copy)));
    const objects=facade[Object.getOwnPropertySymbols(facade).find(key=>key.description==='correlatedObjects')];
    const texture=[...objects][0];
    if(!texture?.isTexture)throw new Error('Pinned model-viewer texture bridge unavailable');
    if(iconMorph!==morph){texture.dispose();return null;}
    resources.push(texture);return texture;
  }
  try{
    const textures=await Promise.all(shapes.map((_,index)=>fillTexture(index)));
    if(iconMorph!==morph)return;
    scene.updateMatrixWorld(true);
    const meshList=[];let unsupportedPrimitive=false;
    scene.traverse(node=>{if(node.isMesh){if(!node.geometry?.attributes.position||Array.isArray(node.material))unsupportedPrimitive=true;else meshList.push(node);}});
    if(unsupportedPrimitive)return cancelIconMorph();
    const nameOf=node=>node.name.toLowerCase().replaceAll('_',' ');
    const slots=data.slots||{};
    const boundsOf=nodes=>{
      const bounds=scene.boundingBox.clone().makeEmpty();
      for(const node of nodes){node.geometry.computeBoundingBox();bounds.union(node.geometry.boundingBox.clone().applyMatrix4(node.matrixWorld));}
      return bounds;
    };
    const bodyNodes=meshList.filter(node=>/^(body |aluminum enclosure|rear glass)/.test(nameOf(node)));
    if(!bodyNodes.length)return cancelIconMorph();
    const bodyBounds=boundsOf(bodyNodes),height=bodyBounds.max.y-bodyBounds.min.y;
    const bodyCenter=bodyBounds.getCenter(center.clone());
    const parts=[],assignment=new Map();
    function part(index,nodes,reshape=true){
      if(index===undefined||!nodes.length)return null;
      const bounds=boundsOf(nodes),box=boxes[index];
      if(!box?.width||!box.height||bounds.max.x-bounds.min.x<1e-7||bounds.max.y-bounds.min.y<1e-7)return null;
      const item={index,nodes,bounds,box,reshape};parts.push(item);
      for(const node of nodes)assignment.set(node,item);
      return item;
    }
    const bodyPart=part(roles.body,bodyNodes);
    const barPart=part(roles.bar,meshList.filter(node=>node.material.name===(slots.bar||'bar')&&!/lens rim|dial side bridge/.test(nameOf(node))));
    const glassParts=roles.glass.map((index,i)=>part(index,meshList.filter(node=>{
      const name=nameOf(node);
      return roles.glass.length===1&&data.id.startsWith('pixel-')?
        /black optical backing|optical well|continuous camera cover|camera pill|camera window/.test(name):
        new RegExp(`^(black optical backing|optical well|continuous camera cover) ${i}$`).test(name);
    })));
    const ringParts=[];
    (roles.rings||[]).forEach((index,i)=>ringParts.push(part(index,meshList.filter(node=>nameOf(node)===`camera lens rim ${i}`))));
    const logoPart=part(roles.logo,meshList.filter(node=>node.material.name===(slots.logo||'logo')),false);
    part(roles.flash,meshList.filter(node=>/^flash |dual led/.test(nameOf(node))));
    const extraParts=[];
    (roles.flashes||[]).forEach((index,i)=>extraParts.push(part(index,meshList.filter(node=>nameOf(node)===`flash ${i}`))));
    (roles.sensors||[]).forEach((index,i)=>extraParts.push(part(index,meshList.filter(node=>nameOf(node)===`rear sensor ${i}`))));
    if(roles.bridge!==undefined)extraParts.push(part(roles.bridge,meshList.filter(node=>nameOf(node)==='camera dial side bridge')));
    if(roles.band!==undefined)extraParts.push(part(roles.band,meshList.filter(node=>/^upper (contrasting )?rear band$/.test(nameOf(node)))));
    if(roles.insert!==undefined)extraParts.push(part(roles.insert,meshList.filter(node=>nameOf(node)==='rear glass')));
    if(!bodyPart||glassParts.some(p=>!p)||ringParts.some(p=>!p)||extraParts.some(p=>!p)||(roles.bar!==undefined&&!barPart)||(roles.logo!==undefined&&!logoPart))return cancelIconMorph();
    // Sample each real outline, including the inner glass. A convex hull of the
    // physical part supplies its destination radius (Seamless's paired rays).
    function hull(points){
      points.sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
      const half=list=>{const out=[];for(const p of list){while(out.length>1){const a=out[out.length-2],b=out[out.length-1];if((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0])>0)break;out.pop();}out.push(p);}return out.slice(0,-1);};
      return half(points).concat(half([...points].reverse()));
    }
    function radiusAt(points,angle){
      const x=Math.cos(angle),y=Math.sin(angle);let best=Infinity;
      for(let i=0;i<points.length;i++){
        const a=points[i],b=points[(i+1)%points.length],dx=b[0]-a[0],dy=b[1]-a[1],den=x*dy-y*dx;
        if(Math.abs(den)<1e-10)continue;
        const r=(a[0]*dy-a[1]*dx)/den,t=(a[0]*y-a[1]*x)/den;
        if(r>0&&t>=0&&t<=1)best=Math.min(best,r);
      }
      return Number.isFinite(best)?best:.5/Math.max(Math.abs(x),Math.abs(y));
    }
    const radial=(values,angle)=>{const n=((angle/(2*Math.PI)+1)%1)*256,i=Math.floor(n);return values[i]+(values[(i+1)%256]-values[i])*(n-i);};
    for(const item of parts){
      const {bounds,box}=item;item.width=bounds.max.x-bounds.min.x;item.height=bounds.max.y-bounds.min.y;item.center=bounds.getCenter(center.clone());
      if(!item.reshape)continue;
      const length=shapes[item.index].getTotalLength();
      const source=Array.from({length:256},(_,i)=>{const p=shapes[item.index].getPointAtLength(length*i/256);return [.5-(p.x-box.x)/box.width,.5-(p.y-box.y)/box.height];});
      const points=[],point=center.clone();
      for(const node of item.nodes){const attr=node.geometry.attributes.position;for(let i=0;i<attr.count;i++){point.fromBufferAttribute(attr,i).applyMatrix4(node.matrixWorld);points.push([(point.x-item.center.x)/item.width,(point.y-item.center.y)/item.height]);}}
      const target=hull(points);
      item.radii=Array.from({length:256},(_,i)=>radiusAt(target,i*2*Math.PI/256));
      item.sourceRadii=Array.from({length:256},(_,i)=>radiusAt(source,i*2*Math.PI/256));
      item.factors=item.radii.map((r,i)=>item.sourceRadii[i]/Math.max(r,1e-6));
    }
    function mapPoint(item,x,y,reshape=true){
      const nx=(x-item.center.x)/item.width,ny=(y-item.center.y)/item.height;
      const factor=reshape&&item.factors?radial(item.factors,Math.atan2(ny,nx)):1;
      return [bodyCenter.x-(item.box.x+item.box.width/2-body.x-body.width/2)/body.height*height+nx*factor*item.box.width/body.height*height,
        bodyCenter.y-(item.box.y+item.box.height/2-body.y-body.height/2)/body.height*height+ny*factor*item.box.height/body.height*height];
    }
    const progress={value:0};
    for(const node of meshList){
      const name=nameOf(node),originalGeometry=node.geometry,originalMaterial=node.material;
      let item=assignment.get(node),detail=false;
      if(!item){
        const camera=/camera|optical|flash|lens|telephoto|autofocus|temperature/.test(name)&&!/selfie|device screen|camera control/.test(name);
        const middle=boundsOf([node]).getCenter(center.clone());
        item=camera?glassParts.reduce((a,b)=>middle.distanceToSquared(a.center)<middle.distanceToSquared(b.center)?a:b):bodyPart;
        detail=camera||!/enclosure|rear glass|front.*glass|device screen|^body /.test(name);
      }
      const geometry=node.geometry=originalGeometry.clone(),material=node.material=originalMaterial.clone();
      const attribute=geometry.attributes.position,goal=attribute.array.slice(),start=new Float32Array(goal.length),uv=new Float32Array(attribute.count*2);
      const inverse=node.matrixWorld.clone().invert(),point=center.clone(),middle=boundsOf([node]).getCenter(center.clone());
      for(let i=0;i<attribute.count;i++){
        point.fromBufferAttribute(attribute,i).applyMatrix4(node.matrixWorld);
        let mappedPart=item;
        // The housing's cutout has clearance around its glass. Both edges must
        // follow the glass contour or the rim clips it as volume develops.
        if(item===barPart)for(const glass of glassParts){
          const nx=(point.x-glass.center.x)/glass.width,ny=(point.y-glass.center.y)/glass.height;
          const edge=radial(glass.radii,Math.atan2(ny,nx));
          if(Math.hypot(nx,ny)<=edge+.00015/Math.min(glass.width,glass.height)){mappedPart=glass;break;}
        }
        let [x,y]=mapPoint(mappedPart,detail?middle.x:point.x,detail?middle.y:point.y,!detail);
        // Reviewed generated groups clip their bridge/band artwork to the body.
        // Keep those perimeter vertices on that same silhouette in the flat pose.
        const nx=(x-bodyCenter.x)/(body.width/body.height*height),ny=(y-bodyCenter.y)/height;
        const distance=Math.hypot(nx,ny),edge=radial(bodyPart.sourceRadii,Math.atan2(ny,nx));
        if(distance>edge){x=bodyCenter.x+(x-bodyCenter.x)*edge/distance;y=bodyCenter.y+(y-bodyCenter.y)*edge/distance;}
        // Keep overlapping surfaces in the SVG's authored paint order.
        const layer=item===bodyPart?(node.material.name===(slots.back||'back')?1:0):2+item.index;
        point.set(x,y,bodyCenter.z-height*.0002*layer).applyMatrix4(inverse);
        start.set([point.x,point.y,point.z],i*3);
        const box=item.box;
        uv.set([.5-(x-(bodyCenter.x-(box.x+box.width/2-body.x-body.width/2)/body.height*height))/(box.width/body.height*height),
          .5-(y-(bodyCenter.y-(box.y+box.height/2-body.y-body.height/2)/body.height*height))/(box.height/body.height*height)],i*2);
      }
      // Prepare the geometry once; only uniforms and placement change per frame.
      attribute.array.set(start);geometry.computeVertexNormals();
      geometry.setAttribute('iconMorphNormal',geometry.attributes.normal.clone());
      attribute.array.set(goal);geometry.setAttribute('normal',originalGeometry.attributes.normal.clone());
      geometry.setAttribute('iconMorphPosition',new attribute.constructor(start,3));
      geometry.setAttribute('iconMorphUv',new attribute.constructor(uv,2));
      const previousCompile=originalMaterial.onBeforeCompile;
      material.onBeforeCompile=(shader,renderer)=>{
        previousCompile.call(material,shader,renderer);
        for(const [source,chunk] of [[shader.vertexShader,'begin_vertex'],[shader.vertexShader,'beginnormal_vertex'],[shader.fragmentShader,'tonemapping_fragment']]){
          if(source.split(`#include <${chunk}>`).length!==2)throw new Error('Pinned model-viewer morph shader changed: '+chunk);
        }
        shader.uniforms.iconMorphProgress=progress;shader.uniforms.iconMorphMap={value:textures[item.index]};
        shader.vertexShader='uniform float iconMorphProgress; attribute vec3 iconMorphPosition; attribute vec3 iconMorphNormal; attribute vec2 iconMorphUv; varying vec2 vIconMorphUv;\n'+shader.vertexShader
          .replace('#include <begin_vertex>','#include <begin_vertex>\ntransformed=mix(iconMorphPosition,transformed,iconMorphProgress);vIconMorphUv=iconMorphUv;')
          .replace('#include <beginnormal_vertex>','#include <beginnormal_vertex>\nobjectNormal=mix(iconMorphNormal,objectNormal,iconMorphProgress);');
        shader.fragmentShader='uniform float iconMorphProgress; uniform sampler2D iconMorphMap; varying vec2 vIconMorphUv;\n'+shader.fragmentShader.replace('#include <tonemapping_fragment>','#include <tonemapping_fragment>\ngl_FragColor.rgb=mix(texture2D(iconMorphMap,vIconMorphUv).rgb,gl_FragColor.rgb,iconMorphProgress);');
      };
      material.customProgramCacheKey=()=>originalMaterial.uuid+'-icon-morph';material.needsUpdate=true;
      entries.push({node,geometry,material,originalGeometry,originalMaterial,frustumCulled:node.frustumCulled});
      node.frustumCulled=false;
    }
    const from=icon.getBoundingClientRect(),to=stage.getBoundingClientRect();
    const orbit=viewer.getCameraOrbit(),fov=viewer.getFieldOfView()*Math.PI/180;
    // Gallery thumbnails are cropped into a 140x180 transparent canvas, not
    // the SVG's 108x108 viewBox. Measure the displayed image's painted bounds.
    const canvas=document.createElement('canvas');canvas.width=icon.naturalWidth;canvas.height=icon.naturalHeight;
    const context=canvas.getContext('2d');context.drawImage(icon,0,0);
    const pixels=context.getImageData(0,0,canvas.width,canvas.height).data;
    let left=canvas.width,top=canvas.height,right=0,bottom=0;
    for(let y=0;y<canvas.height;y++)for(let x=0;x<canvas.width;x++)if(pixels[(y*canvas.width+x)*4+3]){left=Math.min(left,x);right=Math.max(right,x+1);top=Math.min(top,y);bottom=Math.max(bottom,y+1);}
    const fit=Math.min(from.width/canvas.width,from.height/canvas.height),sourceHeight=(bottom-top)*fit;
    const sourceX=from.left+from.width/2+((left+right)/2-canvas.width/2)*fit,sourceY=from.top+from.height/2+((top+bottom)/2-canvas.height/2)*fit;
    const startScale=sourceHeight/(height*to.height/(2*orbit.radius*Math.tan(fov/2)));
    const ease=t=>t*t*t*(t*(t*6-15)+10),mix=(a,b,t)=>a+(b-a)*t;
    dialog.classList.add('icon-morphing');dialog.classList.remove('icon-morph-loading');viewer.shadowIntensity=0;viewer.cameraControls=false;
    viewer.style.cssText=`position:fixed;left:${to.left}px;top:${to.top}px;width:${to.width}px;height:${to.height}px;max-width:none;max-height:none;z-index:2;visibility:hidden;transition:none;transform-origin:50% 50%;`;
    function render(t){
      const p=ease(t),turn=ease(Math.max(0,(t-.35)/.65));progress.value=p;
      viewer.shadowIntensity=oldShadow*p;
      dialog.style.setProperty('--morph-backdrop',String(.6*p));
      viewer.style.transform=`translate(${mix(sourceX-to.left-to.width/2,0,p)}px,${mix(sourceY-to.top-to.height/2,0,p)}px) scale(${mix(startScale,1,p)})`;
      viewer.cameraOrbit=`${mix(180,orbit.theta*180/Math.PI,turn)}deg ${mix(90,orbit.phi*180/Math.PI,turn)}deg ${orbit.radius}m`;
      viewer.jumpCameraToGoal();scene.queueRender();
    }
    render(0);
    // Wait for the pinned renderer to finish the prepared pose, not merely two
    // browser frames (shader compilation and camera updates may take longer).
    await viewer.updateComplete;
    const renderCount=scene.renderCount,deadline=performance.now()+3000;scene.queueRender();
    await new Promise((finish,reject)=>{
      const ready=()=>{
        if(iconMorph!==morph||scene.renderCount>renderCount&&!scene.shouldRender())return finish();
        if(performance.now()>deadline)return reject(new Error('Icon morph frame was not rendered'));
        requestAnimationFrame(ready);
      };requestAnimationFrame(ready);
    });
    if(iconMorph!==morph)return;
    viewer.style.visibility='visible';icon.style.visibility='hidden';
    const started=performance.now();
    const tick=now=>{
      if(iconMorph!==morph)return;
      const t=Math.min(1,(now-started)/1000);render(t);
      if(t<1)morph.frame=requestAnimationFrame(tick);else cancelIconMorph();
    };
    morph.frame=requestAnimationFrame(tick);await done;
  }catch(error){if(iconMorph===morph)cancelIconMorph();throw error;}
}
