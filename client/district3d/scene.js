import * as T from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';
import {DISTRICTS,districtStep,customerPoint} from './model.js';
import {districtArchitecture,createResidenceKit} from './architecture.js';
export {districtHomes} from './model.js';

/** A public courtyard: six reusable customers and a bounded set of real room peers. */
export function createDistrictScene(host,options={}){
  const theme=DISTRICTS[options.group]||DISTRICTS.rent,renderer=new T.WebGLRenderer({antialias:true,powerPreference:'low-power'});
  renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.5));renderer.outputColorSpace=T.SRGBColorSpace;renderer.setClearColor('#cfdfd4');
  const canvas=renderer.domElement;canvas.tabIndex=0;canvas.setAttribute('aria-label',theme.name+' 3D. WASD hoặc cần tròn để đi, kéo để xoay, chạm nhà để xem.');host.append(canvas);
  const scene=new T.Scene(),camera=new T.PerspectiveCamera(42,1,.1,120),controls=new OrbitControls(camera,canvas);
  camera.position.set(19,22,25);controls.target.set(0,0,0);controls.minDistance=9;controls.maxDistance=52;controls.minPolarAngle=.28;controls.maxPolarAngle=1.25;controls.enablePan=false;controls.enableDamping=false;controls.update();
  scene.add(new T.HemisphereLight('#fff5de','#799a86',2.6));const sun=new T.DirectionalLight('#ffe1ab',3);sun.position.set(-12,25,9);scene.add(sun);
  const geometries=new Set(),materials=new Map(),textures=new Map(),disposers=[],doors=[],houses=[],keys=new Set();
  let disposed=false,raf=0,last=0,peerMotionUntil=0,suspended=false,input={x:0,y:0},position={x:0,y:10},direction='se',people=[],goal=null,down=null;
  const material=color=>{if(!materials.has(color))materials.set(color,new T.MeshStandardMaterial({color,roughness:1}));return materials.get(color);};
  function mesh(geo,color,x,y,z,parent=scene){geometries.add(geo);const m=new T.Mesh(geo,material(color));m.position.set(x,y,z);parent.add(m);return m;}
  const box=(w,h,d,c,x,y,z,p)=>mesh(new T.BoxGeometry(w,h,d),c,x,y,z,p);
  box(21,.2,34,'#97b991',0,-.2,0);box(6.2,.08,32,'#c6b38e',0,-.05,0);
  for(const side of [-1,1]){box(.17,.12,32,'#e9dcc1',side*3.25,0,0);box(1,.04,32,'#e5d7b7',side*3.85,-.01,0);}
  function tree(x,z,i){
    mesh(new T.CylinderGeometry(.14,.24,1.55,6),'#8d6845',x,.77,z);
    mesh(new T.IcosahedronGeometry(1.08,1),['#77a75b','#55935b','#8eb45c'][i%3],x,1.98,z);
    mesh(new T.IcosahedronGeometry(.75,1),'#9bbf6f',x+.4,2.4,z+.1);
    mesh(new T.CylinderGeometry(.7,.8,.15,12),'#d3c3a0',x,.03,z);
  }
  const homes=(options.homes||[]).slice(0,8),plans=districtArchitecture(options.group,homes),residences=createResidenceKit(material,geometries);
  for(let i=0;i<8;i++){
    const side=i%2?1:-1,z=Math.floor(i/2)*8-12,x=side*6.6,home=homes[i],g=residences.build(plans[i]);g.position.set(x,0,z);scene.add(g);
    if(side<0)g.rotation.y=Math.PI/2;else g.rotation.y=-Math.PI/2;
    houses.push(g);if(home){g.traverse(o=>{if(o.isMesh)o.userData.home=home;});doors.push(g);}
    tree(side*4.35,z+3.5,i);
  }
  // Shared seating and lamps are static meshes; no shadow-map redraws or animated foliage.
  for(const side of [-1,1])for(const z of [-8,8]){
    box(.75,.12,2,'#9b7651',side*4.05,.55,z);box(.1,.6,2,'#9b7651',side*4.4,.85,z);
    mesh(new T.CylinderGeometry(.055,.08,2.8,6),'#4f6860',side*3.5,1.4,z+1.7);
    mesh(new T.SphereGeometry(.22,8,6),'#fff0b2',side*3.5,2.87,z+1.7);
  }
  function batch(parent,cloneMaterials=false){
    const buckets=new Map();for(const m of [...parent.children])if(m.isMesh){m.updateMatrix();const geo=m.geometry.clone().applyMatrix4(m.matrix);let b=buckets.get(m.material);if(!b)buckets.set(m.material,b={parts:[],home:m.userData.home});b.parts.push(geo);parent.remove(m);}
    for(const [mat,b]of buckets){const geometry=mergeGeometries(b.parts,false);for(const p of b.parts)p.dispose();if(!geometry)continue;geometries.add(geometry);const paint=cloneMaterials?mat.clone():mat;if(cloneMaterials)materials.set('house-'+materials.size,paint);const m=new T.Mesh(geometry,paint);m.userData.home=b.home;parent.add(m);}
  }
  for(const house of houses)batch(house,true);batch(scene);
  const actors=[];
  for(let i=0;i<25;i++){
    const m=new T.SpriteMaterial({transparent:true,alphaTest:.07,depthWrite:false}),s=new T.Sprite(m);s.center.set(.5,0);s.scale.set(1.6,2.05,1);s.visible=false;scene.add(s);actors.push(s);
    const shadow=mesh(new T.CircleGeometry(.43,12),'#91a18b',0,.025,0);shadow.rotation.x=-Math.PI/2;shadow.visible=false;s.userData.shadow=shadow;
  }
  function actor(slot,person,point,moving,t){
    const sprite=actors[slot];if(!sprite)return;
    const frame=moving?1+Math.floor(t*7)%2:0,dir=person.direction||'se',id=person.pid||'npc'+slot,key=id+':'+dir+':'+frame+':'+(person.fc||'');
    let tex=textures.get(key);
    if(!tex){const art=options.avatar?.(person,dir,frame);if(art){tex=new T.CanvasTexture(art);tex.colorSpace=T.SRGBColorSpace;textures.set(key,tex);}}
    if(tex){sprite.material.map=tex;sprite.material.needsUpdate=sprite.userData.key!==key;sprite.userData.key=key;sprite.visible=true;}
    sprite.position.set(point.x,moving?Math.sin(t*12)*.035:0,point.y);sprite.userData.shadow.visible=sprite.visible;sprite.userData.shadow.position.set(point.x,.025,point.y);
  }
  const visible=()=>{
    if(disposed||document.hidden||!host.isConnected)return false;
    const dialog=host.closest('dialog'),dialogs=document.querySelectorAll('dialog[open]');
    return !!dialog?.open&&dialogs[dialogs.length-1]===dialog;
  };
  function wake(){if(!raf&&visible())raf=requestAnimationFrame(draw);}
  function draw(ms){
    raf=0;if(!visible())return;const t=ms/1000;if(last&&t-last<1/30){wake();return;}const dt=last?Math.min(.05,t-last):0;last=t;
    let v={x:input.x+(keys.has('d')||keys.has('arrowright')?1:0)-(keys.has('a')||keys.has('arrowleft')?1:0),y:input.y+(keys.has('s')||keys.has('arrowdown')?1:0)-(keys.has('w')||keys.has('arrowup')?1:0)};
    if(goal&&!v.x&&!v.y){const dx=goal.x-position.x,dy=goal.y-position.y,n=Math.hypot(dx,dy);if(n<.12)goal=null;else v={x:dx/n,y:dy/n};}else if(v.x||v.y)goal=null;
    const next=districtStep(position,v,dt),moving=Math.hypot(next.x-position.x,next.y-position.y)>.001;
    if(moving)direction=v.y<0?(v.x<0?'nw':'ne'):(v.x<0?'sw':'se');position=next;
    options.onMove?.({...position,direction,moving,phase:moving?'walk':'idle'});
    actor(0,{...(options.player||{pid:'self'}),direction},position,moving,t);
    for(let i=0;i<6;i++){const p=customerPoint(i,options.reduced?0:t);actor(i+1,{pid:'customer'+i,npc:i,direction:i%2?'sw':'ne'},p,!options.reduced,t);}
    for(let i=7;i<actors.length;i++){const p=people[i-7];if(p){const target=p.activity||{},old=actors[i].position,k=1-Math.exp(-12*dt);actor(i,{...p,direction:target.direction},{x:old.x+(target.x-old.x)*k,y:old.z+(target.y-old.z)*k},target.moving,t);}else{actors[i].visible=false;actors[i].userData.shadow.visible=false;}}
    const eye=new T.Vector3(position.x,1.1,position.y),delta=eye.clone().sub(camera.position),distance=delta.length();ray.set(camera.position,delta.normalize());ray.far=distance-.1;
    const cover=new Set(ray.intersectObjects(houses,true).map(h=>h.object.parent));ray.far=Infinity;
    for(const house of houses)for(const object of house.children){const target=cover.has(house)?.35:1;if(object.material.opacity!==target){object.material.opacity=target;object.material.transparent=target<1;object.material.depthWrite=target===1;object.material.needsUpdate=true;}}
    renderer.render(scene,camera);if(moving||goal||ms<peerMotionUntil||!options.reduced)wake();
    if(textures.size>180){const used=new Set(actors.filter(s=>s.visible).map(s=>s.material.map));for(const [key,tex]of textures){if(textures.size<=120)break;if(!used.has(tex)){tex.dispose();textures.delete(key);}}}
  }
  function listen(node,type,fn,opts){node.addEventListener(type,fn,opts);disposers.push(()=>node.removeEventListener(type,fn,opts));}
  const ray=new T.Raycaster(),plane=new T.Plane(new T.Vector3(0,1,0),0),hit=new T.Vector3();
  listen(canvas,'pointerdown',e=>{down={x:e.clientX,y:e.clientY};canvas.focus({preventScroll:true});});
  listen(canvas,'pointerup',e=>{if(!down||Math.hypot(e.clientX-down.x,e.clientY-down.y)>6)return;down=null;const r=canvas.getBoundingClientRect();ray.setFromCamera(new T.Vector2((e.clientX-r.left)/r.width*2-1,1-(e.clientY-r.top)/r.height*2),camera);const house=ray.intersectObjects(doors,true)[0]?.object.userData.home;if(house){options.onHome?.(house);return;}if(ray.ray.intersectPlane(plane,hit)){goal={x:Math.max(-2.8,Math.min(2.8,hit.x)),y:Math.max(-14,Math.min(14,hit.z))};wake();}});
  listen(canvas,'keydown',e=>{const k=e.key.toLowerCase();if(['w','a','s','d','arrowup','arrowdown','arrowleft','arrowright'].includes(k)){e.preventDefault();keys.add(k);wake();}});listen(canvas,'keyup',e=>keys.delete(e.key.toLowerCase()));
  const stop=()=>{keys.clear();input={x:0,y:0};goal=null;last=0;options.onMove?.({...position,direction,moving:false,phase:'idle'});};
  const syncVisibility=()=>{
    if(!visible()){
      if(!suspended)stop();suspended=true;cancelAnimationFrame(raf);raf=0;
    }else if(suspended){suspended=false;last=0;wake();}
  };
  listen(canvas,'blur',stop);listen(window,'blur',stop);listen(document,'visibilitychange',syncVisibility);controls.addEventListener('change',wake);
  // Modal changes do not resize the canvas. Observe their open/removal lifecycle
  // so a covered scene neither consumes frames nor waits for input to resume.
  const modalObserver=new MutationObserver(syncVisibility);modalObserver.observe(document.body,{subtree:true,childList:true,attributes:true,attributeFilter:['open']});
  const resize=()=>{const w=host.clientWidth||600,h=host.clientHeight||440;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();wake();},observer=new ResizeObserver(resize);observer.observe(host);resize();
  return {setPeople(rows){people=(rows||[]).slice(0,18);peerMotionUntil=performance.now()+500;wake();},setInput(x,y){if(!visible())return;input={x,y};wake();},getPosition:()=>({...position}),dispose(){if(disposed)return;disposed=true;cancelAnimationFrame(raf);observer.disconnect();modalObserver.disconnect();controls.dispose();for(const off of disposers)off();for(const a of actors)a.material.dispose();for(const t of textures.values())t.dispose();for(const g of geometries)g.dispose();for(const m of materials.values())m.dispose();renderer.dispose();renderer.forceContextLoss();canvas.remove();}};
}
