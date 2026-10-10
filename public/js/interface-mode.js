/** Renderer preference belongs to the authenticated save; never to a browser-wide cache. */
import {stylesheet} from './lazy.js';
import {setIconRenderer} from './icons.js';
import {kindOf} from './scenes/vocabulary.js';

export const newInterface=state=>state?.settings?.newInterface!==false;
export const interfacePromptDue=state=>newInterface(state)&&state?.settings?.interfacePromptSeen!==true;

/** A full page restart releases the old canvas, listeners and styles after the server confirms the choice. */
const saving=new WeakMap();
export function saveInterface(env,enabled){
  if(saving.has(env.api))return saving.get(env.api);
  const changed=newInterface(env.api.state)!==enabled;
  const request=(async()=>{
    const result=await env.cmd('settings',{newInterface:enabled,interfacePromptSeen:true},{quiet:true});
    if(!result)return false;
    if(changed)location.reload();
    return true;
  })();
  saving.set(env.api,request);
  return request.finally(()=>saving.delete(env.api));
}

/** Decide only after bootstrap, so a different account on this device gets its own saved choice. */
export async function loadInterface(state){
  if(globalThis.document?.documentElement)document.documentElement.dataset.game=newInterface(state)?'isometric':'classic';
  if(newInterface(state)){
    const [iso]=await Promise.all([import('./iso-boot.js'),stylesheet('/css/isometric.css'),stylesheet('/css/cozy-reference.css')]);
    return {iso,World:null};
  }
  const [{BobaWorld},{classicIcon}]=await Promise.all([import('./boba-world.js'),import('./classic-icons.js')]);
  setIconRenderer(classicIcon);
  return {iso:null,World:BobaWorld};
}

export function loadCareerScene(state,id){
  return newInterface(state)?Promise.resolve():import(`./scenes/${kindOf(id)}.js`).catch(()=>{});
}

let offering=null;
/** One decision per account, before the tutorial and automatic announcement cards. Escape keeps the new look. */
export function promptInterface(env){
  if(!interfacePromptDue(env.api.state))return Promise.resolve(true);
  if(offering)return offering;
  const back=document.activeElement,dialog=document.createElement('dialog');
  dialog.id='interfacePrompt';dialog.className='confirm-dialog';
  dialog.setAttribute('aria-modal','true');dialog.setAttribute('aria-labelledby','interfacePromptTitle');
  dialog.setAttribute('aria-describedby','interfacePromptDescription');
  dialog.innerHTML='<h2 id="interfacePromptTitle">Bạn có muốn quay về giao diện cũ?</h2>'+
    '<p id="interfacePromptDescription">Bạn đang dùng giao diện mới 2.5D. Có thể đổi bất cứ lúc nào trong Cài đặt → Giao diện. Tài khoản và tiến trình của bạn luôn được giữ nguyên.</p>'+
    '<div class="row wrap space-top"><button type="button" class="btn big" data-interface="legacy">Về giao diện cũ</button><button type="button" class="btn primary big" data-interface="new">Giữ giao diện mới</button></div><p role="status" aria-live="polite"></p>';
  let resolve,busy=false;
  offering=new Promise(done=>{resolve=done;});
  const buttons=()=>[...dialog.querySelectorAll('button')].filter(b=>!b.disabled);
  const choose=async enabled=>{
    if(busy)return;busy=true;
    for(const button of dialog.querySelectorAll('button'))button.disabled=true;
    const status=dialog.querySelector('[role="status"]');status.textContent='Đang lưu lựa chọn…';
    try{
      if(await saveInterface(env,enabled)){
        dialog.close();dialog.remove();offering=null;back?.isConnected&&back.focus({preventScroll:true});resolve(enabled);return;
      }
    }catch(error){console.warn('interface preference:',error);}
    busy=false;for(const button of dialog.querySelectorAll('button'))button.disabled=false;
    status.textContent='Chưa lưu được lựa chọn. Kiểm tra kết nối rồi thử lại nhé.';
    dialog.querySelector(enabled?'[data-interface="new"]':'[data-interface="legacy"]').focus();
  };
  dialog.addEventListener('click',event=>{
    const button=event.target.closest('button[data-interface]');
    if(button&&dialog.contains(button))return choose(button.dataset.interface==='new');
  });
  dialog.addEventListener('cancel',event=>{event.preventDefault();return choose(true);});
  dialog.addEventListener('keydown',event=>{
    if(event.key!=='Tab')return;
    const list=buttons(),first=list[0],last=list.at(-1),active=document.activeElement;
    if(!first){event.preventDefault();return;}
    if(event.shiftKey&&(active===first||!dialog.contains(active))){event.preventDefault();last.focus();}
    else if(!event.shiftKey&&(active===last||!dialog.contains(active))){event.preventDefault();first.focus();}
  });
  document.body.append(dialog);dialog.showModal();dialog.querySelector('[data-interface="new"]').focus();
  return offering;
}
