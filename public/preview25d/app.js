import {SPAWN,SHOPS,move,route,advance,walkable} from './model.js';
import {createMovementController} from '../js/isometric-movement.js';
import {getCharacterStamp,preloadIllustratedCharacters} from '../js/isometric/character-art.js';
const $=id=>document.getElementById(id),canvas=$('scene'),ctx=canvas.getContext('2d'),stage=$('stage'),dialog=$('conversation'),background=new Image();
const look={top:'ao_quen',bottom:'quan_xam',uniform:true,acc:'tui_cheo'};
let player={...SPAWN},input={x:0,y:0},path=[],pending=null,direction='se',walking=false,walkTime=0,raf=0,last=0,ready=false,failed=false,view={width:1,height:1,scale:1,x:0,y:0},activeShop=SHOPS[0],saidHello=false;
const reduced=matchMedia('(prefers-reduced-motion: reduce)').matches;
const distance=(a,b)=>Math.hypot(a.x-b.x,a.y-b.y);
function viewport(){
 const r=stage.getBoundingClientRect(),dpr=Math.min(2,devicePixelRatio||1);canvas.width=Math.round(r.width*dpr);canvas.height=Math.round(r.height*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
 const scale=Math.max(r.width/1024,r.height/1536);view={width:r.width,height:r.height,scale,x:(r.width-1024*scale)/2,y:(r.height-1536*scale)/2};
 // Landscape is a closer view of the shopfronts and lane, centred on the walker.
 if(r.width/r.height>1)view.y=Math.max(r.height-1536*scale,Math.min(0,r.height*.7-player.y*scale));
 paint();
}
function toScreen(p){return {x:view.x+p.x*view.scale,y:view.y+p.y*view.scale};}
function paint(){
 if(!ready)return;
 ctx.clearRect(0,0,view.width,view.height);ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(background,view.x,view.y,1024*view.scale,1536*view.scale);
 const at=toScreen(player),height=(194+(player.y-1000)*.04)*view.scale,frame=walking&&!reduced?1+Math.floor(walkTime*7)%2:0;
 const art=getCharacterStamp({look,gender:'male',direction,walkFrame:frame,uniformColor:'#4f8b81',onReady:wake});
 ctx.fillStyle='#573f352e';ctx.beginPath();ctx.ellipse(at.x,at.y-2*view.scale,39*view.scale,13*view.scale,0,0,Math.PI*2);ctx.fill();
 const bob=walking&&!reduced?Math.sin(walkTime*14)*1.7*view.scale:0;
 ctx.drawImage(art.canvas,at.x-height*.375,at.y-height+bob,height*.75,height);
 if(path.length){const target=toScreen(path.at(-1));ctx.strokeStyle='#fff5c9d9';ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(target.x,target.y,12*view.scale,6*view.scale,0,0,Math.PI*2);ctx.stroke();}
 const bubble=toScreen({x:365,y:629});$('greeting').style.left=`${bubble.x}px`;$('greeting').style.top=`${bubble.y}px`;$('greeting').hidden=saidHello||dialog.open;
 const nearest=[...SHOPS].sort((a,b)=>distance(a.at,player)-distance(b.at,player))[0],near=distance(nearest.at,player)<115;
 $('talk').querySelector('span').textContent=path.length&&pending?'Đang tới tiệm…':near?`Trò chuyện · ${nearest.name}`:'Ghé tiệm Cô Ba';
 stage.dataset.x=player.x.toFixed(2);stage.dataset.y=player.y.toFixed(2);stage.dataset.moving=String(walking);
}
function tick(time){
 raf=0;if(!ready||document.hidden||dialog.open)return;const dt=Math.min(.04,last?(time-last)/1000:.016);last=time;
 const before={...player};
 if(input.x||input.y){path=[];pending=null;player=move(player,input,dt);}
 else if(path.length){const step=advance(player,path,180*dt);player=step.point;path=step.path;if(!path.length&&pending){const shop=pending;pending=null;walking=false;paint();openTalk(shop);return;}}
 walking=distance(before,player)>.01;
 if(walking){walkTime+=dt;const dx=player.x-before.x,dy=player.y-before.y;direction=dy<0?(dx<0?'nw':'ne'):(dx<0?'sw':'se');}
 if(view.width/view.height>1)view.y=Math.max(view.height-1536*view.scale,Math.min(0,view.height*.7-player.y*view.scale));
 paint();if(input.x||input.y||path.length)raf=requestAnimationFrame(tick);else last=0;
}
function wake(){if(!ready||document.hidden||dialog.open||raf)return;last=0;raf=requestAnimationFrame(tick);}
function stop(){input={x:0,y:0};path=[];pending=null;walking=false;control.reset();if(raf)cancelAnimationFrame(raf);raf=0;last=0;paint();}
const stick=$('stick'),knob=$('knob'),control=createMovementController({onInput:(x,y)=>{input={x,y};if(x||y){path=[];pending=null;}wake();},onVisual:({x,y})=>{knob.style.transform=`translate(-50%,-50%) translate(${x*29}px,${y*29}px)`;},capturePointer:id=>stick.setPointerCapture(id),releasePointer:id=>stick.releasePointerCapture(id)});
for(const [event,fn] of [['pointerdown',e=>control.pointerDown(e,stick.getBoundingClientRect())],['pointermove',control.pointerMove],['pointerup',control.pointerUp],['pointercancel',control.pointerUp],['lostpointercapture',control.pointerUp]])stick.addEventListener(event,e=>{if(!ready||dialog.open)return;if(fn(e)){e.preventDefault();e.stopPropagation();}});
window.addEventListener('keydown',e=>{if(!ready||dialog.open||e.target.closest('input,textarea,select'))return;if(e.key.toLowerCase()==='e'){e.preventDefault();goTalk();return;}if(control.keyDown(e))e.preventDefault();});
window.addEventListener('keyup',e=>{if(control.keyUp(e))e.preventDefault();});
window.addEventListener('blur',stop);document.addEventListener('visibilitychange',()=>{if(document.hidden)stop();else wake();});
function go(shop){if(!ready||dialog.open)return;control.reset();const next=route(player,shop.at);if(!next.length)return;path=next;pending=shop;$('hint').textContent=`Đang ghé ${shop.place.toLowerCase()}…`;wake();}
function goTalk(){const near=SHOPS.find(s=>distance(s.at,player)<115);if(near)openTalk(near);else go(SHOPS[0]);}
$('talk').addEventListener('click',goTalk);
let pressed=null;
canvas.addEventListener('pointerdown',e=>{pressed={x:e.clientX,y:e.clientY};});
canvas.addEventListener('pointerup',e=>{
 if(!ready||dialog.open||!pressed)return;const start=pressed;pressed=null;if(Math.hypot(e.clientX-start.x,e.clientY-start.y)>12)return;
 const r=canvas.getBoundingClientRect(),p={x:(e.clientX-r.left-view.x)/view.scale,y:(e.clientY-r.top-view.y)/view.scale};
 const shop=SHOPS.find(s=>distance(p,s.hit)<s.hit.r);if(shop){go(shop);return;}
 if(!walkable(p)){$('hint').textContent='Chạm phần đường lát đá để đi dạo nhé';return;}
 control.reset();pending=null;path=route(player,p);$('hint').textContent='Đi dạo một chút, ghé tiệm làm quen';wake();
});canvas.addEventListener('pointercancel',()=>{pressed=null;});
function answers(items){$('answers').replaceChildren();for(const [label,fn] of items){const button=document.createElement('button');button.type='button';button.textContent=label;button.addEventListener('click',fn);$('answers').append(button);}}
function reply(line){$('line').textContent=line;answers([['Cháu đi dạo tiếp nhé',closeTalk]]);}
function openTalk(shop){
 stop();activeShop=shop;saidHello=true;$('speaker').textContent=shop.name;$('place').textContent=shop.place;
 $('portrait').style.backgroundPosition=shop.id==='grocery'?'-69px -223px':'-282px -266px';
 $('line').textContent=shop.id==='grocery'?'Cháu mới tới đảo hả? Cứ đi dạo thong thả nhé. Cần gì thì ghé cô, tiệm mình lúc nào cũng mở cửa!':'Gió biển hôm nay mát quá ha! Đi dạo mỏi chân thì ghé chú, có cà phê thơm và một chỗ ngồi nhìn ra biển.';
 answers(shop.id==='grocery'?[['Cô kể về phố mình đi',()=>reply('Sáng nghe tiếng chổi quét sân, trưa thơm mùi cà phê, chiều mọi người lại ra bờ biển. Phố nhỏ thôi mà ngày nào cũng có chuyện để kể.')],['Cháu chào cô ạ',()=>reply('Ngoan quá! Cứ xem đây như nhà nhé. Khi nào quay lại, kể cô nghe cháu đã đi những đâu nha.')]]:[['Cho cháu ngắm biển chút',()=>reply('Cứ thong thả nhé. Ở đây không cần vội, nghe tiếng gió với nhìn thuyền về cũng đủ vui rồi.')],['Cháu đi dạo tiếp nhé',closeTalk]]);
 dialog.showModal();control.enable(false);$('greeting').hidden=true;
}
function closeTalk(){dialog.close();control.enable(true);$('hint').textContent=`Bạn vừa làm quen với ${activeShop.name}. Đi dạo tiếp nhé!`;canvas.focus({preventScroll:true});wake();}
$('closeTalk').addEventListener('click',closeTalk);dialog.addEventListener('cancel',e=>{e.preventDefault();closeTalk();});
$('reset').addEventListener('click',()=>{stop();player={...SPAWN};saidHello=false;direction='se';$('hint').textContent='Kéo cần tròn hoặc chạm đường để đi dạo';viewport();});
new ResizeObserver(viewport).observe(stage);
function showError(){if(failed)return;failed=true;$('loading').replaceChildren();const text=document.createElement('b');text.textContent='Chưa tải được góc phố';const retry=document.createElement('button');retry.textContent='Thử tải lại';retry.addEventListener('click',()=>location.reload());$('loading').append(text,retry);}
preloadIllustratedCharacters(()=>{if(ready)wake();});
background.onload=()=>{ready=true;$('loading').hidden=true;viewport();wake();};background.onerror=showError;background.src='./scene.webp';
window.addEventListener('pagehide',()=>{stop();control.destroy();});
if(matchMedia('(pointer:fine)').matches)$('hint').textContent='W A S D / phím mũi tên · Chạm đường để đi · E để trò chuyện';
