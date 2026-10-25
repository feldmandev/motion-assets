// Single dielectric AR film: unpolarized Fresnel interference at RGB wavelengths.
// Reflection uses the viewer's HDR environment; there is no emitted or painted color.
async function applyCameraCoatings(viewer){
  const objects=facade=>facade[Object.getOwnPropertySymbols(facade).find(s=>s.description==='correlatedObjects')];
  const gltf=viewer.originalGltfJson;
  for(const facade of viewer.model.materials){
    if(!/element [12] coating|curved internal optical coating|Pixel front optics \| coated glass|Apple optical glass|Robot optical glass|^Lens [12]$/.test(facade.name))continue;
    const index=gltf.materials.findIndex(m=>m.name===facade.name);
    const primitive=gltf.meshes.flatMap(m=>m.primitives).find(p=>p.material===index);
    const bounds=gltf.accessors[primitive.attributes.POSITION];
    const extent=bounds.min.map((v,i)=>bounds.max[i]-v),axis=extent.indexOf(Math.min(...extent));
    for(const material of objects(facade)){
      material.transmission=0;material.transparent=true;material.opacity=1;
      material.blending=2;material.side=0;material.depthWrite=false;
      material.onBeforeCompile=shader=>{
        shader.uniforms.coatingAxis={value:[0,1,2].map(i=>i===axis?1:0)};
        shader.uniforms.coatingThickness={value:/element 2/.test(facade.name)?114:100};
        shader.vertexShader='uniform vec3 coatingAxis; varying float coatingFace;\n'+shader.vertexShader.replace('#include <beginnormal_vertex>',`#include <beginnormal_vertex>
          // Ground lens edges are blackened; only the polished optical face reflects.
          coatingFace=smoothstep(.25,.75,abs(dot(normal,coatingAxis)));`);
        shader.fragmentShader='uniform float coatingThickness; varying float coatingFace;\n'+shader.fragmentShader;
        shader.fragmentShader=shader.fragmentShader.replace('#include <opaque_fragment>',`
          vec3 coatingV=normalize(vViewPosition);
          float ci=clamp(abs(dot(normal,coatingV)),.001,1.);
          float nf=1.38,ns=1.7;
          float cf=sqrt(1.-(1.-ci*ci)/(nf*nf)),cs=sqrt(1.-(1.-ci*ci)/(ns*ns));
          vec2 a=vec2((ci-nf*cf)/(ci+nf*cf),(nf*ci-cf)/(nf*ci+cf));
          vec2 b=vec2((nf*cf-ns*cs)/(nf*cf+ns*cs),(ns*cf-nf*cs)/(ns*cf+nf*cs));
          vec3 phase=cos(12.5663706144*nf*coatingThickness*cf/vec3(610.,550.,460.));
          vec3 rs=(a.x*a.x+b.x*b.x+2.*a.x*b.x*phase)/(1.+a.x*a.x*b.x*b.x+2.*a.x*b.x*phase);
          vec3 rp=(a.y*a.y+b.y*b.y+2.*a.y*b.y*phase)/(1.+a.y*a.y*b.y*b.y+2.*a.y*b.y*phase);
          vec3 coatingR=inverseTransformDirection(reflect(-coatingV,normal),viewMatrix);
          vec3 incident=textureCubeUV(envMap,envMapRotation*coatingR,.045).rgb*envMapIntensity;
          outgoingLight=incident*.5*(rs+rp)*coatingFace;
          diffuseColor.a=1.;
          #include <opaque_fragment>`);
      };
      material.customProgramCacheKey=()=> 'dielectric-camera-film-v3';
      material.needsUpdate=true;
    }
  }
}
