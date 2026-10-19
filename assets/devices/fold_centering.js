// Keep the projected body bounds centered while the articulated panels move.
function recenterFold(viewer,device,progress){
  if(!device.articulation||!device.panels?.length)return;
  // When laptop is folding, do not move it! The base rests stationary on the surface.
  if(device.form_factor==='laptop'||device.kind==='laptop'||device.id?.startsWith('googlebook'))return;
  const last=viewer.__foldCenter;
  const previous=last?.id===device.id?last.progress:0;
  const joints=device.articulation.joints||[device.articulation];
  function points(value){
    const result=[];
    for(const panel of device.panels){
      const body=panel.body_mm;
      for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1]){
        let px=panel.center_mm[0]+x*body.width/2;
        let py=panel.center_mm[1]+y*body.height/2;
        let pz=panel.center_mm[2]+z*body.depth/2;
        for(const joint of joints){
          if(panel.name!==joint.moving_panel)continue;
          const fraction=Math.max(0,Math.min(1,(value-(joint.start_fraction||0))/((joint.end_fraction??1)-(joint.start_fraction||0))));
          const angle=fraction*joint.closed_degrees*Math.PI/180,c=Math.cos(angle),s=Math.sin(angle),axis=joint.axis_mm;
          if(joint.axis==='X'){
            const dy=py-axis[1],dz=pz-axis[2];
            py=axis[1]+dy*c-dz*s;pz=axis[2]+dy*s+dz*c;
          }else{
            const dx=px-axis[0],dz=pz-axis[2];
            px=axis[0]+dx*c+dz*s;pz=axis[2]-dx*s+dz*c;
          }
        }
        result.push([px/1000,py/1000,pz/1000]);
      }
    }
    return result;
  }
  const oldPoints=points(previous),newPoints=points(progress);
  const orbit=viewer.getCameraOrbit(),target=viewer.getCameraTarget();
  const st=Math.sin(orbit.theta),ct=Math.cos(orbit.theta),sp=Math.sin(orbit.phi),cp=Math.cos(orbit.phi);
  const right=[ct,0,-st],up=[-cp*st,sp,-cp*ct],back=[sp*st,cp,sp*ct];
  const position=[target.x,target.y,target.z];
  function projection(vertices,center){
    const xs=[],ys=[];
    for(const p of vertices){
      const d=p.map((v,i)=>v-center[i]);
      const depth=orbit.radius-d.reduce((sum,v,i)=>sum+v*back[i],0);
      xs.push(d.reduce((sum,v,i)=>sum+v*right[i],0)/depth);
      ys.push(d.reduce((sum,v,i)=>sum+v*up[i],0)/depth);
    }
    return[(Math.min(...xs)+Math.max(...xs))/2,(Math.min(...ys)+Math.max(...ys))/2];
  }
  const anchor=projection(oldPoints,position);
  // Iterating accounts for perspective without changing zoom, viewing angle or user pan.
  for(let i=0;i<3;i++){
    const center=projection(newPoints,position);
    for(let j=0;j<3;j++)position[j]+=(right[j]*(center[0]-anchor[0])+up[j]*(center[1]-anchor[1]))*orbit.radius;
  }
  viewer.cameraTarget=position.map(v=>v+'m').join(' ');
  viewer.updateComplete.then(()=>viewer.jumpCameraToGoal());
  viewer.__foldCenter={id:device.id,progress};
}
