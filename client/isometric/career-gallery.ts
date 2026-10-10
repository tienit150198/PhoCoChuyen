import {CAREER_ART} from './career-art';
// Same renderer as the game; this page only creates in-memory example state.
// @ts-ignore Runtime module is built separately; never bundle a second Phaser copy.
import {PhaserWorld} from '/js/isometric/phaser-world.js';

type Career={id:string;short?:string;name?:string;place?:string;focus?:string;color?:string};
const byId=<T extends HTMLElement=HTMLElement>(id:string)=>document.getElementById(id)! as T;
const select=byId<HTMLSelectElement>('career'),search=byId<HTMLInputElement>('search');
let catalogue:Career[]=[],content:any,current='',mode:'outside'|'inside'='outside',world:any=null,loading:Promise<any>|null=null;
let selectionVersion=0;
const held=new Map<number,{x:number;y:number}>();
function updateInput(){let x=0,y=0;for(const p of held.values()){x+=p.x;y+=p.y;}world?.setMovementInput(x,y);}
function clearInput(){held.clear();world?.setMovementInput(0,0);}
const title=(c:Career)=>c.short||c.name||c.id;
function status(text:string){byId('status').textContent=text;}
function fitRoom(){
  if(!world)return;
  world.resize();world.resetCamera();
  // The gallery starts with the complete cutaway visible; the game keeps its
  // closer playing camera. Pinch/wheel/buttons still allow a detailed view.
  world.setZoom(Math.max(.24,Math.min(.8,(world.width||1200)/1510,(world.height||760)/980)));
}
function filter(){
  const normalized=(v:string)=>v.normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/gi,'d').toLowerCase();
  const term=normalized(search.value);let count=0;
  for(const c of catalogue){const node=byId('card-'+c.id),show=normalized([c.id,title(c),c.place,c.focus].join(' ')).includes(term);node.hidden=!show;if(show)count++;}
  byId('count').textContent=`${count} / ${catalogue.length} nghề`;
}
function fixture(id:string){return {current:id,focus:id,settings:{reduceMotion:matchMedia('(prefers-reduced-motion: reduce)').matches},profile:{name:'Khách xem thử',gender:'female'},journey:{name:'Khách xem thử',gender:'female'},careers:{[id]:{open:true,upgrades:[],theme:'boba',life:{shop_name:catalogue.find(c=>c.id===id)?.place},tasks:[]}}};}
async function showInside(version:number){
  byId('interior').hidden=false;byId('exterior').hidden=true;status('Đang dựng cảnh…');
  if(!world&&!loading){
    world=new PhaserWorld(byId<HTMLCanvasElement>('scene'),(id:string)=>{
      const spot=world.hotspots.find((h:any)=>h.id===id);
      status(spot?`Đã đến ${spot.label}. Đây là bản xem thử cảnh; thao tác nghề thực hiện trong game.`:'Đã đến điểm tương tác.');
    });
    world.mode='work';world.update(fixture(current),content);
    const created=world;loading=created.ready.then(()=>created);
  }
  await loading;
  if(version!==selectionVersion||mode!=='inside')return;
  world.paused=false;world.update(fixture(current),content);world.setMode('work');fitRoom();
  status('Cảnh đã sẵn sàng. Chạm mặt sàn để đi; chạm đồ nghề để tới điểm thao tác.');
}
async function choose(id:string,view=mode){
  const c=catalogue.find(c=>c.id===id);if(!c)return;
  clearInput();
  const version=++selectionVersion;current=id;mode=view;select.value=id;byId('viewer').hidden=false;
  document.body.classList.add('viewing');
  byId('scene-title').textContent=c.place||title(c);byId('scene-kind').textContent=title(c);
  byId('description').textContent=c.focus||'';
  byId('position').textContent=`${catalogue.indexOf(c)+1} / ${catalogue.length}`;
  for(const item of catalogue)byId('card-'+item.id).classList.toggle('active',item.id===id);
  byId('outside').setAttribute('aria-pressed',String(mode==='outside'));byId('inside').setAttribute('aria-pressed',String(mode==='inside'));
  const picture=byId<HTMLImageElement>('building');picture.src=`/icons/careers-v1/${id}.webp`;picture.alt=`Mặt ngoài ${title(c)}`;
  history.replaceState(null,'',`#${encodeURIComponent(id)}/${mode}`);
  if(mode==='inside')await showInside(version);else{if(world)world.paused=true;byId('interior').hidden=true;byId('exterior').hidden=false;status('Mặt tiền riêng của nghề. Chọn “Vào bên trong” để thử đường đi.');}
}
function safely(promise:Promise<any>){promise.catch(error=>{console.error(error);byId('error').hidden=false;byId('error').textContent='Chưa mở được cảnh. Tải lại trang để thử lại.';status('Không mở được cảnh.');});}
function moveChoice(delta:number){const i=catalogue.findIndex(c=>c.id===current);safely(choose(catalogue[(i+delta+catalogue.length)%catalogue.length].id));}
function wire(){
  search.addEventListener('input',filter);select.addEventListener('change',()=>safely(choose(select.value)));
  byId('outside').addEventListener('click',()=>safely(choose(current,'outside')));byId('inside').addEventListener('click',()=>safely(choose(current,'inside')));
  byId('all').addEventListener('click',()=>{selectionVersion++;clearInput();if(world)world.paused=true;byId('viewer').hidden=true;document.body.classList.remove('viewing');history.replaceState(null,'',location.pathname);byId('collection-title').scrollIntoView({block:'start',behavior:'auto'});});
  byId('previous').addEventListener('click',()=>moveChoice(-1));byId('next').addEventListener('click',()=>moveChoice(1));
  byId('zoom-in').addEventListener('click',()=>world?.zoomBy(1.15));byId('zoom-out').addEventListener('click',()=>world?.zoomBy(1/1.15));byId('center').addEventListener('click',fitRoom);
  const reset=clearInput;
  for(const button of Array.from(document.querySelectorAll<HTMLButtonElement>('#walk-pad button'))){
    button.addEventListener('pointerdown',e=>{e.preventDefault();button.setPointerCapture(e.pointerId);held.set(e.pointerId,{x:Number(button.dataset.x),y:Number(button.dataset.y)});updateInput();});
    for(const event of ['pointerup','pointercancel','lostpointercapture'])button.addEventListener(event,e=>{held.delete((e as PointerEvent).pointerId);updateInput();});
  }
  window.addEventListener('blur',reset);document.addEventListener('visibilitychange',()=>{if(document.hidden)reset();});
  window.addEventListener('pagehide',()=>{selectionVersion++;reset();world?.destroy();world=null;loading=null;});
  window.addEventListener('pageshow',()=>{if(mode==='inside'&&current&&!byId('viewer').hidden&&!world)safely(choose(current,'inside'));});
}
async function boot(){
  const response=await fetch('/api/content?part=core',{credentials:'omit'});if(!response.ok)throw new Error(`Catalogue ${response.status}`);
  content=await response.json();catalogue=(content.catalogue||[]).filter((c:Career)=>Object.prototype.hasOwnProperty.call(CAREER_ART,c.id));
  if(!catalogue.length)throw new Error('Catalogue empty');
  const fragment=document.createDocumentFragment();
  for(const c of catalogue){
    const option=new Option(title(c),c.id);select.add(option);
    const card=document.createElement('button');card.type='button';card.className='card';card.id='card-'+c.id;card.setAttribute('aria-label',`Xem ${title(c)}`);
    const img=document.createElement('img');img.loading='lazy';img.decoding='async';img.src=`/icons/careers-v1/${c.id}.webp`;img.alt='';img.width=320;img.height=320;
    const h=document.createElement('h3');h.textContent=title(c);const p=document.createElement('p');p.textContent=c.place||'';
    const small=document.createElement('small');small.textContent='Xem mặt ngoài & vào bên trong →';card.append(img,h,p,small);
    card.addEventListener('click',()=>{safely(choose(c.id,'outside'));byId('viewer').scrollIntoView({block:'start',behavior:'auto'});});fragment.append(card);
  }
  byId('gallery').append(fragment);wire();filter();
  const [id,view]=decodeURIComponent(location.hash.slice(1)).split('/');
  if(catalogue.some(c=>c.id===id))await choose(id,view==='inside'?'inside':'outside');
}
safely(boot());
