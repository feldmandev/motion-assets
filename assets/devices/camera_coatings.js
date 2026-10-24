// Camera coating colors and studio lobes from the reviewed Pixel optics viewer.
// The bundled model-viewer is pinned; correlatedObjects exposes its Three materials/textures.
async function applyCameraCoatings(viewer){
  const objects=facade=>facade[Object.getOwnPropertySymbols(facade).find(s=>s.description==='correlatedObjects')];
  if(!viewer.__cameraCoatingTextures){
    const images={"outer":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAABCAIAAAC+O+cgAAAAjUlEQVR4nHWMgRHAIAgDcdwu0ik6q+khBBDb88SQvBnX/QCTZwKwOXWqp5OmCds56GOKy3CW5ibhoDlFy48PiHQyWLuFbOaSruxQue8fMvUOVn1EOkubehEEQKwA6yTJpwdxt8JGZukObyppNhDnEwjD2l392hlBjJqnPtfW3EtOeNuG33+DZlfnN33GC/C2XiyHWPhRAAAAAElFTkSuQmCC","inner":"data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAQAAAAABCAIAAAC+O+cgAAAAiElEQVR4nJ2P0RGAIAxDy6bu4hrOSj2gaRMOf9QTm+Slnu2+nu7d3edZw5jUZxN+yZEakryMZu8ewIqITB+DfTlnaSwxY4dNe6rE1h1UANXBC/cWycKScVYLFEXRkG7AxSRSirAEN5IWSbZ5WrT1aKVaP67WTubRUZeUbymDvF8WnL6rJn5JzBffJE058p/Y/gAAAABJRU5ErkJggg=="};
    viewer.__cameraCoatingTextures={};
    for(const [name,url] of Object.entries(images)){
      const texture=await viewer.createTexture(url);
      viewer.__cameraCoatingTextures[name]=[...objects(texture)][0];
    }
  }
  for(const facade of viewer.model.materials){
    if(!/element [12] coating|curved internal optical coating|Pixel front optics \| coated glass|Apple optical glass|Robot optical glass|^Lens [12]$/.test(facade.name))continue;
    const texture=viewer.__cameraCoatingTextures[/element 2/.test(facade.name)?'inner':'outer'];
    for(const material of objects(facade)){
      material.transmission=0;material.transparent=true;material.opacity=1;
      material.blending=2;material.side=0;material.depthWrite=false;
      material.onBeforeCompile=shader=>{
        shader.uniforms.cameraCoating={value:texture};
        shader.fragmentShader='uniform sampler2D cameraCoating;\n'+shader.fragmentShader;
        shader.fragmentShader=shader.fragmentShader.replace('#include <opaque_fragment>',`
          vec3 coatingV=normalize(vViewPosition);
          vec3 coatingR=inverseTransformDirection(reflect(-coatingV,normal),viewMatrix);
          float coatingCosine=clamp(abs(dot(normal,coatingV)),.001,1.);
          float coatingLight=.045
            +12.*exp((dot(coatingR,normalize(vec3(-.8,.8,-1.)))-1.)/.14)
            +24.*exp((dot(coatingR,normalize(vec3(.35,-.2,-1.)))-1.)/.0025)
            +12.*exp((dot(coatingR,normalize(vec3(.6,.1,-1.)))-1.)/.0015)
            +1.5*exp((dot(coatingR,normalize(vec3(-1.,-.6,-.5)))-1.)/.045)
            +4.*exp((dot(coatingR,normalize(vec3(.4,.4,1.)))-1.)/.14)
            +12.*exp((dot(coatingR,normalize(vec3(-.15,.1,1.)))-1.)/.003);
          outgoingLight=texture2D(cameraCoating,vec2(coatingCosine,.5)).rgb*coatingLight;
          diffuseColor.a=1.;
          #include <opaque_fragment>`);
      };
      material.customProgramCacheKey=()=> 'reviewed-camera-coating-v1';
      material.needsUpdate=true;
    }
  }
}
