/* Service worker: web push (payload-less "tickle" → fetch text from the game
 * server with the player's own cookie) and a friendly offline page. */
const OFFLINE=`<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Mất kết nối · Phố Có Chuyện</title><body style="margin:0;min-height:100vh;display:grid;place-items:center;background:#fff7ec;color:#3b2a22;font:16px/1.6 system-ui,sans-serif;text-align:center;padding:24px"><div><div style="font-size:48px">🏮</div><h1 style="margin:.2em 0">Mất kết nối</h1><p>Kiểm tra mạng rồi tải lại trang nhé.<br>Tiến trình đã xác nhận vẫn được lưu trên máy chủ.</p><p style="opacity:.7">You are offline. Check your connection and reload — your saved progress is safe.</p></div></body></html>`;

self.addEventListener('install',()=>self.skipWaiting());
// Navigation preload: the page request starts while this worker boots (~100 ms on a slow phone),
// instead of after it. Only navigations pass through here; assets never do.
self.addEventListener('activate',event=>event.waitUntil((async()=>{
  try{await self.registration.navigationPreload?.enable();}catch{/* unsupported */}
  await self.clients.claim();
})()));

self.addEventListener('fetch',event=>{
  if(event.request.mode!=='navigate')return;
  event.respondWith((async()=>{
    try{return (await event.preloadResponse)||await fetch(event.request);}
    catch{return new Response(OFFLINE,{headers:{'Content-Type':'text/html; charset=utf-8'}});}
  })());
});

/** Minimal copy of the page's English layer (exact strings, then patterns). */
async function translator(){
  let pack={strings:{},patterns:[]};
  try{const r=await fetch('/i18n/en.json',{credentials:'same-origin'});if(r.ok)pack=await r.json();}catch{}
  const pats=(pack.patterns||[]).map(([s,o])=>{try{return [new RegExp('^'+s+'$','u'),o];}catch{return null;}}).filter(Boolean);
  const tr=(text,depth=0)=>{
    const key=String(text||'').trim();if(!key||depth>3)return text;
    if(pack.strings[key])return pack.strings[key];
    for(const [re,out] of pats){const m=key.match(re);if(m)return out.replace(/\$(\d)/g,(_,i)=>tr(m[Number(i)]||'',depth+1));}
    return text;
  };
  return tr;
}

self.addEventListener('push',event=>{
  event.waitUntil((async()=>{
    let items=[],lang='vi';
    try{const r=await fetch('/api/push/pending',{credentials:'include',cache:'no-store'});if(r.ok){const d=await r.json();items=d.items||[];lang=d.lang||'vi';}}catch{}
    if(!items.length)items=[{title:'Phố Có Chuyện',body:'Có tin mới ở Phố nghề.',url:'/?social=inbox',tag:'mnl'}];
    const tr=lang==='en'?await translator():(s=>s);
    const top=items[0],more=items.length>1?(lang==='en'?` (+${items.length-1} more)`:` (+${items.length-1} tin nữa)`):'';
    top.title=tr(top.title);top.body=tr(top.body);
    await self.registration.showNotification(top.title,{body:top.body+more,icon:'/icons/icon-192.png',badge:'/icons/badge-72.png',tag:top.tag||'mnl',renotify:true,data:{url:top.url||'/'}});
  })());
});

self.addEventListener('notificationclick',event=>{
  event.notification.close();
  const url=new URL(event.notification.data?.url||'/',self.location.origin).href;
  event.waitUntil((async()=>{
    const all=await self.clients.matchAll({type:'window',includeUncontrolled:true});
    for(const client of all){
      if(client.url.startsWith(self.location.origin)){await client.focus();client.postMessage({type:'open',url});return;}
    }
    await self.clients.openWindow(url);
  })());
});
