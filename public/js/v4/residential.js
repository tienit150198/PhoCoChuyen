import {escapeHTML as esc} from '../icons.js';
import {figure,defaultLook} from './look.js';
import {getCharacterStamp,preloadIllustratedCharacters} from '../isometric/character-art.js';
import {leisurePresence} from '../isometric/leisure-presence.js';
import {createMovementController} from '../isometric-movement.js';
import {stylesheet} from '../lazy.js';
const NAMES={rent:'Xóm trọ',apartment:'Khu căn hộ',townhouse:'Phố nhà liền kề',villa:'Vườn biệt thự'};
let active=null,openSequence=0;
export async function openResidential(env,group='rent'){
  if(!Object.hasOwn(NAMES,group))return;const sequence=++openSequence;active?.close();env.closeSheet?.();
  await stylesheet('/css/residential.css');if(sequence!==openSequence)return;
  const dialog=document.createElement('dialog');dialog.className='residential';dialog.setAttribute('aria-label',NAMES[group]);
  dialog.innerHTML=`<header><div><small>KHU NHÀ TRÊN ĐẢO</small><h2>${NAMES[group]}</h2></div><button type="button" class="icon-btn" data-close aria-label="Ra phố">✕</button></header><div class="residential-stage"><p role="status">Đang mở khu nhà 3D…</p></div><aside><p class="residential-status" role="status">Khách đi dạo là NPC. Người chơi trong cùng khu sẽ xuất hiện khi có kết nối.</p><div class="residential-actions"><button type="button" class="btn primary" data-home>Vào nhà của tôi</button><button type="button" class="btn cream" data-market>Xem nhà · thuê & mua</button><button type="button" class="btn cream" data-guests>Mời bạn về nhà</button></div><div class="residential-list" aria-label="Nhà trong khu"></div></aside><div class="residential-controls"><div class="residential-stick" role="group" aria-label="Cần di chuyển"><span></span></div><p>Chạm đất để đi · Chạm nhà để xem<br>Kéo để xoay · Chụm để thu phóng</p></div>`;
  document.body.append(dialog);dialog.showModal();
  const host=dialog.querySelector('.residential-stage'),status=dialog.querySelector('.residential-status'),stick=dialog.querySelector('.residential-stick'),knob=stick.firstElementChild;
  let scene=null,dead=false,off=()=>{},control=null;
  const close=()=>{if(dead)return;dead=true;off();control?.destroy();scene?.dispose();leisurePresence.clear();dialog.remove();if(active?.dialog===dialog)active=null;env.renderMain?.();};
  active={dialog,close};dialog.addEventListener('cancel',e=>{e.preventDefault();close();});dialog.querySelector('[data-close]').onclick=close;
  const act=async(action,data={})=>{close();await env.act(action,data);};
  dialog.querySelector('[data-home]').onclick=()=>act('jrEnterHome');dialog.querySelector('[data-market]').onclick=()=>act('house',{group});dialog.querySelector('[data-guests]').onclick=()=>act('homeGuests');
  function choose(home){
    if(home.status==='current'){void act('jrEnterHome');return;}
    void act('house',{group,...(home.status==='listing'?{view:'rentals'}:home.status==='model'&&home.kind!=='rent'?{kind:home.kindId}:{})});
  }
  try{
    await env.api.more?.();
    const [module,rentals]=await Promise.all([import('./home-3d-scene.js'),env.api.json('/api/rentals',{retry:false}).catch(()=>null)]);
    if(dead)return;
    const homes=module.districtHomes(group,env.api.content,env.api.state,rentals);
    const list=dialog.querySelector('.residential-list');list.innerHTML=homes.map((h,i)=>`<button type="button" data-house="${i}"><b>${esc(h.name)}</b><small>${esc(h.label)}</small></button>`).join('')+(rentals?.next_offset!=null?'<button type="button" data-more-rentals>Xem thêm trong chợ thuê nhà →</button>':'');
    list.onclick=e=>{if(e.target.closest('[data-more-rentals]')){void act('house',{group,view:'rentals'});return;}const b=e.target.closest('[data-house]');if(b)choose(homes[+b.dataset.house]);};
    host.replaceChildren();const me=figure(env.api.state),npcLooks=Array.from({length:6},(_,i)=>({...defaultLook(i%2?'female':'male'),top:['ao_quen','ao_thun','ao_somi'][i%3]}));
    const atlasReady=new Promise(resolve=>{preloadIllustratedCharacters(resolve);setTimeout(resolve,1800);});await atlasReady;if(dead)return;
    scene=module.createDistrictScene(host,{group,homes,player:{pid:'self',look:me.L,gender:me.g},reduced:!!env.api.state?.settings?.reduceMotion,
      onHome:choose,onMove:p=>leisurePresence.publish({kind:'homes-'+group,...p,action:null}),
      avatar:(p,direction,walkFrame)=>getCharacterStamp({look:p.look||npcLooks[p.npc%6]||me.L,gender:p.gender||(p.npc%2?'female':'male'),direction,walkFrame}).canvas});
    off=leisurePresence.subscribe('homes-'+group,rows=>{scene.setPeople(rows);status.textContent=`${rows.length} người chơi cùng khu · 6 khách NPC đang đi dạo${rentals===null?' · Chưa tải được tin cho thuê.':''}`;});
    control=createMovementController({onInput:(x,y)=>scene.setInput(x,y),onVisual:({x,y})=>{knob.style.transform=`translate(${x*27}px,${y*27}px)`;},capturePointer:id=>stick.setPointerCapture(id),releasePointer:id=>stick.releasePointerCapture(id)});
    stick.addEventListener('pointerdown',e=>{e.preventDefault();control.pointerDown(e,stick.getBoundingClientRect());});
    stick.addEventListener('pointermove',e=>control.pointerMove(e));for(const event of ['pointerup','pointercancel','lostpointercapture'])stick.addEventListener(event,e=>control.pointerUp(e));
  }catch(error){if(!dead){host.innerHTML='<p role="status">Thiết bị chưa mở được cảnh 3D. Bạn vẫn có thể vào nhà hoặc mở danh sách thuê và mua bên dưới.</p>';console.warn('Khu nhà 3D:',error);}}
}
