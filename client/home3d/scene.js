import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {resources,furniture,roomStructure} from './meshes.js';
import {dimensions,placement,hitPlacement,hostOf,boundedActors,clamp,editIntent} from './model.js';
export {createDistrictScene,districtHomes} from '../district3d/scene.js';

/** One WebGL context while a home is open; no save/network API is owned by the renderer. */
export function createHomeScene(element,actions={}){
  const renderer=new T.WebGLRenderer({antialias:true,alpha:false,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(globalThis.devicePixelRatio||1,1.6));
  renderer.setClearColor('#eee2cd');renderer.outputColorSpace=T.SRGBColorSpace;
  renderer.shadowMap.enabled=true;renderer.shadowMap.type=T.PCFShadowMap;renderer.shadowMap.autoUpdate=false;
  const canvas=renderer.domElement;canvas.className='home3d-canvas';canvas.tabIndex=0;canvas.setAttribute('aria-label','Nhà 3D. Kéo để xoay, cuộn hoặc chụm để thu phóng. Chạm sàn để đi.');
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(38,1,.1,100),R=resources(),world=new T.Group(),actors=new T.Group();
  scene.add(world,actors,new T.HemisphereLight('#fff6e0','#a7ad9b',2.4));
  const sun=new T.DirectionalLight('#ffe1ac',3.2);sun.position.set(4,10,7);sun.castShadow=true;sun.shadow.mapSize.set(1024,1024);sun.shadow.camera.left=-12;sun.shadow.camera.right=12;sun.shadow.camera.top=12;sun.shadow.camera.bottom=-12;sun.shadow.normalBias=.05;scene.add(sun);
  const fill=new T.DirectionalLight('#cadfeb',.6);fill.position.set(-5,5,-3);scene.add(fill);
  const controls=new OrbitControls(camera,canvas);controls.enableDamping=false;controls.enablePan=false;controls.minPolarAngle=.3;controls.maxPolarAngle=Math.PI*.47;controls.minDistance=3;controls.maxDistance=30;
  const ray=new T.Raycaster(),pointer=new T.Vector2(),plane=new T.Plane(),hitPoint=new T.Vector3(),normal=new T.Vector3();
  const objects=new Map(),actorSlots=[],wallMaterials={back:new Set(),side:new Set()},selection=new T.BoxHelper(new T.Object3D(),'#e7ae4c');selection.visible=false;scene.add(selection);
  let container=element,data=null,key='',roomKey='',closed=false,raf=0,press=null,drag=null,visible=true;
  for(let i=0;i<28;i++){
    const material=new T.SpriteMaterial({transparent:true,alphaTest:.06,depthWrite:false}),sprite=new T.Sprite(material);
    sprite.center.set(.5,0);sprite.visible=false;actors.add(sprite);
    const nameMaterial=new T.SpriteMaterial({transparent:true,depthWrite:false}),label=new T.Sprite(nameMaterial);label.visible=false;actors.add(label);
    actorSlots.push({sprite,label,id:'',art:'',name:'',version:0,x:0,z:0,toX:0,toZ:0,fromX:0,fromZ:0,start:0,height:1.7});
  }
  const usable=()=>!closed&&visible&&container?.isConnected&&document.visibilityState!=='hidden'&&(()=>{const dialogs=document.querySelectorAll('dialog[open]');return !dialogs.length||dialogs[dialogs.length-1]===container.closest('dialog');})();
  function invalidate(){if(!raf&&usable())raf=requestAnimationFrame(draw);}
  function draw(now){
    raf=0;if(!usable())return;let moving=false;
    if(data){const {width:w,depth:d}=dimensions(data.room);fadeWall('back',camera.position.z< -d/2);fadeWall('side',camera.position.x< -w/2);}
    for(const a of actorSlots){if(!a.sprite.visible)continue;const t=Math.min(1,(now-a.start)/155);a.x=a.fromX+(a.toX-a.fromX)*t;a.z=a.fromZ+(a.toZ-a.fromZ)*t;a.sprite.position.set(a.x,.025,a.z);a.label.position.set(a.x,a.height+.14,a.z);if(t<1&&(Math.abs(a.toX-a.fromX)+Math.abs(a.toZ-a.fromZ)>.003))moving=true;}
    renderer.render(scene,camera);if(moving)invalidate();
  }
  function fadeWall(side,covered){for(const material of wallMaterials[side]){const opacity=covered?.35:1;if(material.opacity===opacity)continue;material.opacity=opacity;material.transparent=covered;material.depthWrite=!covered;material.needsUpdate=true;}}
  function resize(){if(closed||!container)return;const w=container.clientWidth||500,h=container.clientHeight||380;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();invalidate();}
  function resetCamera(){if(!data)return;const {width:w,depth:d}=dimensions(data.room),dist=Math.max(w,d)*1.7;camera.position.set(dist*.55,dist*.72,dist*.88);controls.target.set(0,.35,0);controls.maxDistance=Math.max(15,dist*2);controls.update();invalidate();}
  function attach(el){container=el;if(canvas.parentNode!==el)el.append(canvas);observer.disconnect();observer.observe(el);resize();}
  function findItem(object){for(let o=object;o;o=o.parent)if(o.userData.uid)return objects.get(o.userData.uid);return null;}
  function cast(event,withActors=false){const r=canvas.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,1-(event.clientY-r.top)/r.height*2);ray.setFromCamera(pointer,camera);return ray.intersectObjects(withActors?[world,actors]:world.children,true).filter(h=>!h.object.userData.architectureOnly&&(!h.object.userData.wall||h.object.material.opacity===1));}
  function pointFor(event,it,allowHost=true){
    const hits=cast(event);let host=null;
    if(it?.spot==='top'&&allowHost){for(const hit of hits){const o=findItem(hit.object);if(o&&!o.mate&&o.id!==data.held?.uid&&(o.it.surface||o.it.ledge)){host=o;hitPoint.copy(hit.point);break;}if(hit.object.userData.host){host=hostOf(data.room,hit.object.userData.host,data.items);if(host){hitPoint.copy(hit.point);break;}}}}
    if(!host){const {depth:d}=dimensions(data.room);normal.set(0,it?.spot==='wall'?0:1,it?.spot==='wall'?1:0);plane.set(normal,it?.spot==='wall'?d/2-.1:0);if(!ray.ray.intersectPlane(plane,hitPoint))return null;}
    return {point:{x:hitPoint.x,y:hitPoint.y,z:hitPoint.z},q:it?hitPlacement(data.room,it,hitPoint,{host,all:data.items,f:data.held?.f||0}):null};
  }
  function down(e){
    if(e.isPrimary===false){cancel();return;} // a second finger belongs to pinch/orbit, not furniture
    if(e.button!==0||!data||data.busy)return;
    canvas.focus({preventScroll:true});press={x:e.clientX,y:e.clientY,id:e.pointerId};
    actions.interacting?.(true);
    if(data.edit&&!data.held&&(!data.remote||data.coop)){
      const hits=cast(e),o=hits.length?findItem(hits[0].object):null;
      if(o&&!o.mate&&!o.pinned){drag={item:o,moved:false};if(e.pointerType!=='touch')controls.enabled=false;canvas.setPointerCapture?.(e.pointerId);}
    }
  }
  function move(e){
    if(!drag||!press||press.id!==e.pointerId)return;
    if(Math.hypot(e.clientX-press.x,e.clientY-press.y)<9&&!drag.moved)return;
    const p=pointFor(e,drag.item.it);if(!p)return;drag.moved=true;controls.enabled=false;drag.q={...p.q,f:drag.item.q.f||0,...(drag.item.q.face?{face:drag.item.q.face}:{})};
    const mesh=objects.get(drag.item.id)?.mesh;if(mesh){const at=placement(data.room,{...drag.item,q:drag.q},data.items);mesh.position.set(at.x,at.y,at.z);selection.setFromObject(mesh);selection.visible=true;invalidate();}
  }
  function up(e){
    if(!press||press.id!==e.pointerId)return;
    const was=drag,tap=Math.hypot(e.clientX-press.x,e.clientY-press.y)<9;press=null;drag=null;controls.enabled=true;actions.interacting?.(false);
    if(was?.moved){actions.move?.(was.item.id,was.q);return;}
    if(!tap||data.busy)return;
    if(data.edit&&data.held){const it=data.held.it,p=pointFor(e,it);if(p&&editIntent(data,null,p.point)?.type==='place')actions.place?.(p.q);return;}
    const hits=cast(e,!data.edit).filter(h=>h.object.visible),o=hits.length?findItem(hits[0].object):null,actorUid=hits[0]?.object.userData.actorUid||'';
    if(data.edit){const intent=editIntent(data,o,null);if(intent?.type==='select')actions.select?.(intent.uid);return;}
    const p=pointFor(e,null);if(p){const {width:w,depth:d}=dimensions(data.room);actions.walk?.([clamp((p.point.x+w/2)/w,0,1),clamp((p.point.z+d/2)/d,0,1)],o?.id||actorUid);}
  }
  function cancel(){if(drag){key='';update(data);}press=null;drag=null;controls.enabled=true;actions.interacting?.(false);}
  function keydown(e){if(['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','Delete','Backspace','f','F','r','R','PageUp','PageDown'].includes(e.key)){actions.key?.(e);}}
  function onVisibility(){if(!usable()&&raf){cancelAnimationFrame(raf);raf=0;}else{syncActors();invalidate();}}
  function contextLost(e){e.preventDefault();actions.fallback?.('Thiết bị vừa mất kết nối đồ họa. Đã mở lại phòng minh họa.');}
  function svgTexture(a,actor){
    const version=++a.version,img=new Image(),svg=`<svg xmlns="http://www.w3.org/2000/svg" width="192" height="256" viewBox="${actor.viewBox||'-55 -165 110 170'}">${actor.art}</svg>`;
    img.onload=()=>{if(closed||a.version!==version)return;const texture=new T.Texture(img);texture.colorSpace=T.SRGBColorSpace;texture.needsUpdate=true;a.sprite.material.map?.dispose();a.sprite.material.map=texture;a.sprite.material.needsUpdate=true;invalidate();};
    img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(svg);
  }
  function nameTexture(a,name){
    a.label.material.map?.dispose();a.label.material.map=null;a.label.visible=!!name;if(!name)return;
    const c=document.createElement('canvas');c.width=256;c.height=48;const ctx=c.getContext('2d');ctx.fillStyle='rgba(255,248,230,.92)';ctx.beginPath();ctx.roundRect(0,3,256,42,18);ctx.fill();ctx.fillStyle='#604c40';ctx.textAlign='center';ctx.font='600 22px sans-serif';ctx.fillText(name.slice(0,22),128,31,236);
    const texture=new T.CanvasTexture(c);texture.colorSpace=T.SRGBColorSpace;a.label.material.map=texture;a.label.material.needsUpdate=true;a.label.scale.set(1.5,.28,1);
  }
  function syncActors(){
    if(!data||!usable())return;
    const source=actions.actors?.()||{},list=boundedActors(source.people,source.children,source.pets),{width:w,depth:d}=dimensions(data.room),now=performance.now();let changed=false;
    // Stable slots by id; actor data is sampled at 6 Hz, never allocated by the animation frame.
    for(const a of actorSlots)if(a.id&&!list.some(x=>x.id===a.id)){a.id='';a.sprite.visible=false;a.label.visible=false;a.version++;a.art='';a.name='';a.sprite.material.map?.dispose();a.sprite.material.map=null;a.label.material.map?.dispose();a.label.material.map=null;changed=true;}
    for(const actor of list){
      let a=actorSlots.find(s=>s.id===actor.id);const fresh=!a;if(!a)a=actorSlots.find(s=>!s.id);if(!a)break;
      a.id=actor.id;a.sprite.visible=true;a.sprite.userData.actorUid=actor.id.startsWith('baby:')?actor.id:'';a.height=actor.height||1.7;const x=(actor.at?.[0]??.5)*w-w/2,z=(actor.at?.[1]??.8)*d-d/2;
      if(fresh){a.x=x;a.z=z;}
      if(fresh||Math.abs(a.toX-x)+Math.abs(a.toZ-z)>.003){a.fromX=a.x;a.fromZ=a.z;a.toX=x;a.toZ=z;a.start=actions.calm?.()?now-200:now;changed=true;}
      if(a.art!==actor.art){a.art=actor.art;svgTexture(a,actor);changed=true;}
      const name=actor.name||'';if(a.name!==name){a.name=name;nameTexture(a,name);changed=true;}a.label.visible=!!name;
      a.sprite.scale.set(actor.width||a.height*.7,a.height,1);a.sprite.position.set(a.x,.025,a.z);a.label.position.set(a.x,a.height+.14,a.z);
    }
    if(changed)invalidate();
  }
  function update(next){
    if(closed||!next)return;data=next;
    const signature=JSON.stringify([data.scope,data.room,data.parts,data.items.map(o=>[o.id,o.k,o.it,o.q,o.color,o.mate])]);
    if(signature!==key){
      key=signature;world.clear();objects.clear();
      world.add(roomStructure(data.room,data.parts,R,data.scope));
      for(const o of data.items){const mesh=furniture(o.it,o.color,R),at=placement(data.room,o,data.items);mesh.position.set(at.x,at.y,at.z);mesh.scale.x=o.q.f?-1:1;mesh.rotation.y=o.q.face==='back'?Math.PI:0;mesh.userData.uid=o.id;objects.set(o.id,{...o,mesh});world.add(mesh);}
      wallMaterials.back.clear();wallMaterials.side.clear();world.traverse(o=>{if(o.userData.wall)wallMaterials[o.userData.wall].add(o.material);});R.prune(world);
      renderer.shadowMap.needsUpdate=true;
    }else for(const o of data.items){const old=objects.get(o.id);if(old){old.pinned=o.pinned;const at=placement(data.room,o,data.items);old.mesh.position.set(at.x,at.y,at.z);}}
    const identity=data.scope+':'+data.room.id;
    if(identity!==roomKey){roomKey=identity;resetCamera();for(const a of actorSlots){a.id='';a.sprite.visible=false;a.label.visible=false;}}
    const selected=objects.get(data.selected);selection.visible=!!selected;if(selected)selection.setFromObject(selected.mesh);
    canvas.setAttribute('aria-label',`${data.room.name||'Phòng'} 3D. ${data.edit?'Chạm đồ để chọn, kéo đồ để dời.':'Chạm sàn để đi, chạm đồ để dùng.'} Kéo chỗ trống để xoay; cuộn hoặc chụm để thu phóng.`);
    syncActors();invalidate();
  }
  function cameraAction(action){if(action==='reset')resetCamera();else if(action==='in'||action==='out'){camera.position.sub(controls.target).multiplyScalar(action==='in'?.85:1.18).add(controls.target);controls.update();invalidate();}}
  const observer=new ResizeObserver(resize),intersection=globalThis.IntersectionObserver?new IntersectionObserver(entries=>{visible=entries[0]?.isIntersecting!==false;onVisibility();}):null;
  controls.addEventListener('change',invalidate);canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',cancel);canvas.addEventListener('keydown',keydown);canvas.addEventListener('webglcontextlost',contextLost);document.addEventListener('visibilitychange',onVisibility);
  attach(element);intersection?.observe(element);const timer=setInterval(syncActors,155);
  let wasUsable=usable();const modalObserver=new MutationObserver(()=>{const next=usable();if(next!==wasUsable){wasUsable=next;onVisibility();}});
  modalObserver.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['open']});
  function dispose(){
    if(closed)return;closed=true;clearInterval(timer);if(raf)cancelAnimationFrame(raf);observer.disconnect();intersection?.disconnect();modalObserver.disconnect();document.removeEventListener('visibilitychange',onVisibility);
    for(const [type,fn] of [['pointerdown',down],['pointermove',move],['pointerup',up],['pointercancel',cancel],['keydown',keydown],['webglcontextlost',contextLost]])canvas.removeEventListener(type,fn);
    controls.dispose();for(const a of actorSlots){a.version++;for(const sprite of [a.sprite,a.label]){sprite.material.map?.dispose();sprite.material.dispose();}}
    selection.geometry.dispose();selection.material.dispose();R.dispose();world.clear();actors.clear();scene.clear();sun.shadow.map?.dispose();renderer.renderLists.dispose();renderer.dispose();renderer.forceContextLoss();canvas.remove();objects.clear();
  }
  return {attach,detach:()=>canvas.remove(),update,cameraAction,dispose,stats:()=>({objects:objects.size,actors:actorSlots.filter(a=>a.sprite.visible).length,geometries:renderer.info.memory.geometries,textures:renderer.info.memory.textures,closed})};
}
