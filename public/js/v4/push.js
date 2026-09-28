/** Web push + service worker registration (PWA install, offline page). */
const b64=s=>{const p='='.repeat((4-s.length%4)%4),raw=atob((s+p).replace(/-/g,'+').replace(/_/g,'/'));return Uint8Array.from(raw,c=>c.charCodeAt(0));};

export const pushSupported=()=>'serviceWorker' in navigator&&'PushManager' in window&&'Notification' in window;
export const isIOS=()=>/iphone|ipad|ipod/i.test(navigator.userAgent)||(navigator.platform==='MacIntel'&&navigator.maxTouchPoints>1);
export const isStandalone=()=>matchMedia('(display-mode: standalone)').matches||navigator.standalone===true;

let registration=null;
export async function registerWorker(){
  if(!('serviceWorker' in navigator)||!isSecureContext)return null;
  try{registration=await navigator.serviceWorker.register('/sw.js',{scope:'/'});}catch{registration=null;}
  return registration;
}

export async function pushState(api){
  if(!api.push?.enabled)return {available:false,reason:'server'};
  if(!pushSupported())return {available:false,reason:isIOS()&&!isStandalone()?'ios_install':'browser'};
  if(Notification.permission==='denied')return {available:false,reason:'denied'};
  const reg=registration||await navigator.serviceWorker.getRegistration('/');
  const sub=reg?await reg.pushManager.getSubscription():null;
  return {available:true,subscribed:Boolean(sub)};
}

export async function enablePush(api,prefs={}){
  if(!pushSupported())throw new Error(isIOS()&&!isStandalone()?'Trên iPhone/iPad: bấm Chia sẻ → “Thêm vào MH chính”, mở game từ biểu tượng rồi bật thông báo.':'Trình duyệt này chưa hỗ trợ thông báo đẩy.');
  const permission=await Notification.requestPermission();
  if(permission!=='granted')throw new Error('Bạn chưa cho phép thông báo trong trình duyệt.');
  const reg=registration||await registerWorker();
  if(!reg)throw new Error('Không đăng ký được service worker (cần HTTPS).');
  await navigator.serviceWorker.ready;
  let sub=await reg.pushManager.getSubscription();
  if(!sub)sub=await reg.pushManager.subscribe({userVisibleOnly:true,applicationServerKey:b64(api.push.key)});
  const tz=-new Date().getTimezoneOffset();
  return api.post('/api/push/subscribe',{subscription:sub.toJSON(),prefs:{social:true,daily:false,hour:19,tz,...prefs}});
}

export async function disablePush(api){
  const reg=registration||await navigator.serviceWorker?.getRegistration('/');
  const sub=reg?await reg.pushManager.getSubscription():null;
  const out=await api.post('/api/push/unsubscribe',{subscription:sub?sub.toJSON():null});
  if(sub)await sub.unsubscribe().catch(()=>{});
  return out;
}

/** Messages from the service worker (notification clicks while the game is open). */
export function listenWorker(onOpen){
  navigator.serviceWorker?.addEventListener('message',e=>{if(e.data?.type==='open')onOpen(e.data.url);});
}
