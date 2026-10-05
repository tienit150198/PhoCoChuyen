import Phaser from 'phaser';
// These are the game's existing wardrobe and scene vocabulary, shipped beside this bundle.
// @ts-ignore JavaScript public modules are intentionally runtime imports.
import {figure,defaultLook} from '/js/v4/look.js';
// @ts-ignore The illustrated atlas adapter preserves the game's actual wardrobe.
import {getCharacterStamp,preloadIllustratedCharacters} from '/js/isometric/character-art.js';
// @ts-ignore The catalogue scene family mapping remains the source of truth.
import {kindOf,wordsFor} from '/js/scenes/index.js';
import {activeTasks,advanceRoute,CAMERA_ZOOM,canvasDescription,cameraWorldPoint,defaultCamera,effectFrameState,findRoute,followCamera,gestureIsDrag,groundCacheRegion,inside,interpolateRoute,isWalkable,landmarkPlaneGeometry,makeNavigation,moveOnGround,nearestReachableHotspot,nearestWalkable,normalizeMovementInput,presenceDirection,project,publicTownPlayers,resizedCamera,roomAppearance,townBuildingArt,townBuildings,townGarden,townLandmarks,townNavigation,townRoads,unproject,WORK_FOOD_SHELF,WORK_WINDOW,workWindowAnchors} from './model';
import type {Building,Career,Facing,Navigation,Point,Rect,RemotePlayer,RoomAppearance} from './model';
import {islandCoastline,islandOverviewCamera,SEA_COLOR,TOWN_ZOOM} from './island';

export type WorldMode = 'town' | 'work';
interface Hotspot extends Point {id:string;label:string;approach:Point;point:Point;z:number;range:number}
type PublicState = {current?:string;focus?:string;careers?:Record<string,any>;journey?:any;settings?:any;[key:string]:any};
type Content = {catalogue?:Career[];npcs?:any[];[key:string]:any};
const FONT='"Trebuchet MS", "Segoe UI", sans-serif';
const COLORS={grass:0xb6c598,grassLight:0xc2cda8,road:0xe7d3b5,edge:0xc5ac89,ink:0x6e5141,cream:0xfff3da,roof:0xb86c4e,sage:0x8ba77a,water:0x98bfb8};
const asHex=(s:string|undefined,fallback=COLORS.sage)=>s&&/^#[0-9a-f]{6}$/i.test(s)?parseInt(s.slice(1),16):fallback;
const px=(p:Point,z=0):Point=>{const q=project(p);return {x:q.x,y:q.y-z};};
const noOp=()=>{};
const CHARACTER_SCALE=.65;
const ASSETS:Record<string,string>=Object.fromEntries(['grocery','home','cafe','tree','bench','counter','shelf','desk','crates','interior-shop','interior-office','interior-cafe','interior-home'].map(kind=>[kind,'/icons/isometric/'+kind+'.webp']));
Object.assign(ASSETS,{pharmacy:'/icons/cozy-v2/pharmacy.webp','mother-baby':'/icons/cozy-v2/mother-baby.webp',garage:'/icons/cozy-v2/garage.webp',pho:'/icons/cozy-v2/pho.webp',pond:'/icons/cozy-v2/leisure-lake.webp',pool:'/icons/cozy-v2/leisure-pool.webp',boat:'/icons/cozy-v2/boat.webp'});
const assetURL=(path:string)=>(window as any).__mnlBoot?.asset?.(path)||path;

/** Phaser owns the scene and draw list; server mechanics stay in the existing DOM modules. */
export class PhaserWorld {
  readonly canvas:HTMLCanvasElement;
  readonly onInteract:(id:string)=>void;
  readonly ready:Promise<void>;
  mode:WorldMode='town';
  career='mother_baby';
  state:PublicState|null=null;
  game:Content|null=null;
  c:any={};
  player:Point & {path:Point[];goal:Point|null;look:number}={x:6.2,y:6.2,path:[],goal:null,look:1};
  hotspots:Hotspot[]=[];
  remotePlayers:RemotePlayer[]=[];
  direction:Facing='se';
  reduced=false;
  width=1200;
  height=790;
  pending:(()=>void)|null=null;
  currentArea='main';
  private engine:Phaser.Game;
  private stage?:DioramaScene;
  private resolveReady:()=>void=noOp;
  private rejectReady:(e:unknown)=>void=noOp;
  private _paused=false;
  private destroyed=false;
  private visible=true;
  private resizeObserver:ResizeObserver;
  private visibleObserver?:IntersectionObserver;
  private modalObserver:MutationObserver;
  private listeners:Array<()=>void>=[];
  private pointers=new Map<number,{start:Point;last:Point;drag:boolean}>();
  private pinch:{distance:number;zoom:number;world:Point}|null=null;
  private keys=new Set<string>();
  private movementInput:Point={x:0,y:0};
  private remoteSignature='';
  private speechTimer:ReturnType<typeof setTimeout>|null=null;
  private _fx:any=null;
  private fxCanvas:HTMLCanvasElement;
  private fxContext:CanvasRenderingContext2D;
  private layoutSignature='';
  private cachedPreview=new Map<string,string>();
  private lastInput=0;
  private fxPaintAt=-Infinity;

  constructor(canvas:HTMLCanvasElement,onInteract:(id:string)=>void){
    this.canvas=canvas;this.onInteract=onInteract;
    this.ready=new Promise((resolve,reject)=>{this.resolveReady=resolve;this.rejectReady=reject;});
    this.fxCanvas=document.createElement('canvas');this.fxCanvas.width=900;this.fxCanvas.height=700;this.fxContext=this.fxCanvas.getContext('2d')!;
    const rect=canvas.getBoundingClientRect();this.width=Math.round(rect.width)||1200;this.height=Math.round(rect.height)||790;
    canvas.style.touchAction='none';canvas.tabIndex=0;canvas.setAttribute('aria-label',canvasDescription('town',''));
    const owner=this;
    this.engine=new Phaser.Game({type:Phaser.CANVAS,canvas,width:this.width,height:this.height,backgroundColor:'#ede3ce',transparent:false,
      audio:{noAudio:true},input:{keyboard:false,mouse:false,touch:false,gamepad:false},fps:{target:60,forceSetTimeOut:false},
      render:{antialias:true,roundPixels:false,pixelArt:false},scale:{mode:Phaser.Scale.NONE,autoCenter:Phaser.Scale.NO_CENTER},
      scene:[new DioramaScene(owner)],callbacks:{postBoot(game){game.events.once(Phaser.Core.Events.DESTROY,()=>owner.disposeObservers());}}});
    this.resizeObserver=new ResizeObserver(()=>this.resize());this.resizeObserver.observe(canvas.parentElement||canvas);
    if(typeof IntersectionObserver==='function'){this.visibleObserver=new IntersectionObserver(entries=>{this.visible=entries[entries.length-1]?.isIntersecting??true;this.wake();});this.visibleObserver.observe(canvas);}
    this.modalObserver=new MutationObserver(()=>{if(document.querySelector('dialog[open]'))this.clearMovementControls();this.wake();});this.modalObserver.observe(document.body,{subtree:true,attributes:true,attributeFilter:['open']});
    this.listen(canvas,'pointerdown',this.pointerDown as EventListener);
    this.listen(canvas,'pointermove',this.pointerMove as EventListener);
    this.listen(canvas,'pointerup',this.pointerUp as EventListener);
    this.listen(canvas,'pointercancel',this.pointerCancel as EventListener);
    this.listen(canvas,'wheel',this.wheel as EventListener,{passive:false});
    this.listen(canvas,'keydown',this.keydown as EventListener);
    this.listen(canvas,'keyup',this.keyup as EventListener);
    this.listen(canvas,'blur',()=>{this.clearMovementControls();this.pointers.clear();this.pinch=null;this.wake();});
    this.listen(window,'blur',()=>{this.clearMovementControls();this.pointers.clear();this.pinch=null;this.wake();});
    this.listen(document,'visibilitychange',()=>this.wake());
    this.listen(document,'close',()=>this.wake(),true);
    this.listen(window,'pagehide',()=>{this.clearMovementControls();this.engine.loop.sleep();});
    this.listen(window,'pageshow',()=>this.wake());
    if(new URLSearchParams(location.search).has('isometricdebug'))(window as any).__isoWorld=this;
  }
  private listen(target:EventTarget,event:string,handler:EventListener,options?:AddEventListenerOptions|boolean){target.addEventListener(event,handler,options);this.listeners.push(()=>target.removeEventListener(event,handler,options));}
  get paused(){return this._paused;}
  set paused(value:boolean){this._paused=!!value;if(this._paused){this.clearMovementControls();this.pointers.clear();this.pinch=null;}this.wake();}
  setMovementInput(x:number,y:number){this.movementInput=this.shouldSleep()||!!document.querySelector('dialog[open]')?{x:0,y:0}:normalizeMovementInput(x,y);this.wake();}
  getPresence(){return this.mode==='town'?{x:this.player.x,y:this.player.y,direction:this.direction}:null;}
  setRemotePlayers(peers:unknown){const players=publicTownPlayers(peers),signature=JSON.stringify(players);if(signature===this.remoteSignature)return;this.remoteSignature=signature;this.remotePlayers=players;this.stage?.syncRemotePlayers();if(this.mode==='town')this.wake();}
  private clearMovementControls(){this.keys.clear();this.movementInput={x:0,y:0};}
  get time(){return performance.now()/1000;}
  get ctx(){return this.fxContext;}
  get fx(){return this._fx;}
  set fx(value:any){
    this._fx=value;
    // Happenings calls start/finish after rendering public state. Wake on those calls too.
    if(value)for(const name of ['start','finish','clear']){const fn=value[name];if(typeof fn==='function')value[name]=(...args:any[])=>{const result=fn.apply(value,args);this.fxPaintAt=-Infinity;this.wake();return result;};}
    this.wake();
  }
  boot(stage:DioramaScene){this.stage=stage;this.resize();stage.rebuild();this.resolveReady();this.wake();}
  update(state:PublicState,content:Content){
    if(this.destroyed)return;this.state=state;this.game=content;this.career=state.current||state.focus||this.career;this.c=state.careers?.[this.career]||{};this.reduced=!!(state.settings?.reduceMotion||state.settings?.reduced_motion);
    const work=this.mode==='work'?[this.career,this.currentArea,roomAppearance(this.c,this.career),this.c.life?.shop_name,this.c.open,activeTasks(this.c).map(t=>[t.id,t.npc,t.status]),this.c.event?.id,this.c.event?.stage,(this.c.ops?.staff||[]).map((s:any)=>[s.id,s.status,s.name]),this.c.upgrades?.includes('assistant'),this.c.ops?.security?.current_case?.status]:[];
    const signature=JSON.stringify([this.mode,(content.catalogue||[]).map(c=>[c.id,c.short,c.name,c.place,c.station,c.color,c.category,c.playable]),work]);
    this.updateCanvasLabel();
    const changed=signature!==this.layoutSignature;
    if(changed){this.layoutSignature=signature;this.stage?.rebuild();}
    const lookChanged=this.stage?.refreshPlayer();if(changed||lookChanged)this.wake();
  }
  private updateCanvasLabel(){const meta=this.game?.catalogue?.find(c=>c.id===this.career);this.canvas.setAttribute('aria-label',canvasDescription(this.mode,String(this.c.life?.shop_name||meta?.place||meta?.short||this.career)));}
  setMode(mode:WorldMode){if(mode!==this.mode){this.clearMovementControls();this.mode=mode;this.currentArea='main';this.player.path=[];this.pending=null;this.layoutSignature='';this.stage?.rebuild();this.resetCamera();this.updateCanvasLabel();document.dispatchEvent(new CustomEvent('mnl:iso-mode',{bubbles:true,detail:{mode}}));}this.wake();}
  scene(){return {id:'iso-'+kindOf(this.career),areas:[{id:'main',name:'Nơi làm việc',main:true}]};}
  words(){return wordsFor(this.career);}
  isPortrait(){return this.width<=620;}
  areaIds(){return ['main'];}
  enterArea(id:string){this.currentArea=id==='main'?id:'main';this.wake();}
  project(x:number,y:number,z=0){return px({x,y},z);}
  unproject(x:number,y:number){return unproject({x,y});}
  plan(){
    const spots:Record<string,any>={};for(const h of this.hotspots){const at=px(h),go=px(h.approach);spots[h.id]=[[at.x,at.y],h.range,[[go.x,go.y]]];}
    const point=(p:Point)=>{const q=px(p);return [q.x,q.y];};
    spots.door ||= [point({x:9,y:6}),45,[point({x:8.7,y:6})]];
    const anchors=workWindowAnchors();
    return {spots,customers:[point({x:7.7,y:5.8}),point({x:8,y:7}),point({x:5.9,y:7.1}),point({x:4.8,y:7})],home:point({x:6.5,y:6}),floor:[-640,0,640,600],blocks:[],kx:64,ky:32,
      anchors:{door:point({x:9,y:6}),out:point({x:11,y:8}),street:point({x:10,y:8}),shelf:point({x:2.2,y:2.8}),till:point({x:7,y:4.9}),table:point({x:7.5,y:6.4}),window:[anchors.window.x,anchors.window.y],glass:[anchors.glass.x,anchors.glass.y],car:point({x:10,y:7})}};
  }
  resize(){
    if(this.destroyed)return;
    const r=this.canvas.parentElement?.getBoundingClientRect()||this.canvas.getBoundingClientRect(),w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));
    // ResizeObserver can update owner dimensions while Phaser is still preloading.
    // Once its scene exists, the bitmap must catch up even if CSS size is unchanged.
    const surfaceMatches=this.canvas.width===w&&this.canvas.height===h&&this.engine.scale.width===w&&this.engine.scale.height===h;
    if(!r.width||!r.height||w===this.width&&h===this.height&&surfaceMatches)return;
    const camera=this.stage?.cameras.main,next=camera?this.stage?.islandOverview?islandOverviewCamera(w,h):resizedCamera(this.mode,{width:this.width,height:this.height,scrollX:camera.scrollX,scrollY:camera.scrollY,zoom:camera.zoom},w,h):null;
    this.width=w;this.height=h;
    if(this.stage&&camera){this.engine.scale.resize(w,h);camera.setSize(w,h);if(!this.stage.cameraSet)this.resetCamera();else if(next)camera.setScroll(next.scrollX,next.scrollY).setZoom(next.zoom);}
    this.wake();
  }
  resetCamera(){this.stage?.resetCamera();this.wake();}
  recenter(){this.resetCamera();}
  overviewIsland(){this.setMode('town');this.clearMovementControls();this.player.path=[];this.player.goal=null;this.pending=null;this.stage?.overviewIsland();this.wake();}
  overview(){this.overviewIsland();}
  focusCareer(id:string){this.setMode('town');const building=this.stage?.buildings.find(b=>b.id===id);if(building){this.stage!.resetCamera();const p=px(building.at,65);this.stage!.cameras.main.centerOn(p.x,p.y);this.stage!.highlight('career:'+id);this.wake();}}
  private zoomRange(){return this.mode==='town'?TOWN_ZOOM:CAMERA_ZOOM;}
  setZoom(value:number){const camera=this.stage?.cameras.main;if(camera&&this.stage){this.stage.islandOverview=false;const range=this.zoomRange();camera.setZoom(Phaser.Math.Clamp(value,range.min,range.max));this.wake();}}
  zoomBy(factor:number){this.setZoom((this.stage?.cameras.main.zoom||1)*factor);}
  debug(){return {mode:this.mode,career:this.career,paused:this.paused,movementInput:{...this.movementInput},remotePlayers:this.remotePlayers.length,loopRunning:this.engine.loop.running,loopSleeping:!this.engine.loop.running,hidden:document.hidden,covered:!!document.querySelector('dialog[open]:not(.drawer)'),visible:this.visible,paths:this.player.path.length,hotspots:this.hotspots.length,sceneActive:this.stage?.sys.isActive(),sceneChildren:this.stage?.children.length,groundTextures:this.engine.textures.exists('iso-ground'),camera:this.stage?{x:this.stage.cameras.main.scrollX,y:this.stage.cameras.main.scrollY,zoom:this.stage.cameras.main.zoom}:null};}
  say(text:string,npc:string|null=null){if(!text)return;this.stage?.say(String(text),npc);if(this.speechTimer)clearTimeout(this.speechTimer);this.speechTimer=setTimeout(()=>{this.speechTimer=null;this.stage?.clearSpeech();this.wake();},Math.min(9000,Math.max(3500,text.length*48)));this.wake();}
  celebrate(){this.stage?.celebrate();this.wake();}
  pet(){this.say(this.words().cat_line||'Mướp rất vui khi có bạn ở đây.');this.stage?.celebrate(true);this.wake();}
  go(id:string,callback:()=>void=noOp){
    const h=this.hotspots.find(h=>h.id===id);if(!h||!this.stage){callback();return;}
    const route=findRoute(this.stage.navigation,this.player,h.approach);if(!route.length){callback();return;}this.player.path=route;this.player.goal=h.approach;this.pending=callback;this.stage.highlight(id);this.wake();
  }
  snapshot(){const copy=document.createElement('canvas');copy.width=1080;copy.height=Math.max(1,Math.round(1080*this.canvas.height/this.canvas.width));const ctx=copy.getContext('2d')!;ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.drawImage(this.canvas,0,0,copy.width,copy.height);return copy.toDataURL('image/webp',.78);}
  preview(career:string){
    const cached=this.cachedPreview.get(career);if(cached)return cached;
    const out=document.createElement('canvas');out.width=640;out.height=430;const ctx=out.getContext('2d')!;ctx.imageSmoothingEnabled=true;ctx.imageSmoothingQuality='high';ctx.fillStyle='#ede3ce';ctx.fillRect(0,0,640,430);
    const meta=this.game?.catalogue?.find(c=>c.id===career),variant=townBuildingArt(meta||{id:career},['cafe_bakery','milk_tea','restaurant','pho'].includes(career)?'cafe':career==='grocery'?'grocery':'home'),source=this.stage?.artSource(variant);if(source){const w=Math.min(330,330*source.width/source.height),h=w*source.height/source.width;ctx.drawImage(source,320-w/2,345-h,w,h);}
    ctx.fillStyle='#fff3da';ctx.fillRect(75,352,490,52);ctx.font='700 22px '+FONT;ctx.textAlign='center';ctx.fillStyle='#6e5141';ctx.fillText(this.game?.catalogue?.find(c=>c.id===career)?.place||this.game?.catalogue?.find(c=>c.id===career)?.short||career,320,384,460);
    const image=out.toDataURL('image/webp',.8);this.cachedPreview.set(career,image);return image;
  }
  wake(){if(this.destroyed||!this.engine)return;if(this.shouldSleep()){this.clearMovementControls();this.engine.loop.sleep();return;}this.stage?.requestRender();this.engine.loop.wake();}
  shouldSleep(){return this._paused||document.hidden||!this.visible||!!document.querySelector('dialog[open]:not(.drawer)');}
  step(dt:number){
    if(this.shouldSleep()){this.clearMovementControls();this.engine.loop.sleep();return;}
    const stage=this.stage;if(!stage)return;
    if(stage.islandOverview&&(this.keys.size||this.movementInput.x||this.movementInput.y||this.player.path.length))stage.resetCamera();
    let moving=false;const before={x:this.player.x,y:this.player.y};
    if(this.keys.size||this.movementInput.x||this.movementInput.y){let sx=this.movementInput.x,sy=this.movementInput.y;if(this.keys.has('a')||this.keys.has('arrowleft'))sx--;if(this.keys.has('d')||this.keys.has('arrowright'))sx++;if(this.keys.has('w')||this.keys.has('arrowup'))sy--;if(this.keys.has('s')||this.keys.has('arrowdown'))sy++;
      const next=moveOnGround(stage.navigation,this.player,normalizeMovementInput(sx,sy),dt);this.player.path=[];this.player.goal=null;this.pending=null;moving=Math.hypot(next.x-this.player.x,next.y-this.player.y)>1e-8;Object.assign(this.player,next);
    }else if(this.player.path.length){const next=advanceRoute(this.player,this.player.path,2.9*dt);Object.assign(this.player,next.point);this.player.path=next.path;moving=true;if(next.arrived){this.player.goal=null;const cb=this.pending;this.pending=null;cb?.();}}
    if(moving&&![...this.pointers.values()].some(p=>p.drag)){const camera=stage.cameras.main,view=followCamera({width:this.width,height:this.height,scrollX:camera.scrollX,scrollY:camera.scrollY,zoom:camera.zoom},px(this.player,55),dt);camera.setScroll(view.scrollX,view.scrollY);}
    if(moving)this.direction=presenceDirection(before,this.player,this.direction);
    stage.positionPlayer(moving);
    const remoteMoving=stage.stepRemotePlayers(this.time);
    const ev=this._fx?.ev,effect=effectFrameState(ev,this.time,this.reduced);
    if(effect.clear){this._fx?.clear?.();this.paintFx();}
    else if(this.mode==='work'&&this._fx&&(effect.needsFrames||stage.renderRequested||this.time-this.fxPaintAt>.2&&ev?.end!=null)){this.paintFx();}
    const active=moving||remoteMoving||this.keys.size>0||!!(this.movementInput.x||this.movementInput.y)||this.pointers.size>0||effect.needsFrames||stage.hasEffects();
    if(!active&&stage.settle())this.engine.loop.sleep();
  }
  private paintFx(){const ctx=this.fxContext;ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,this.fxCanvas.width,this.fxCanvas.height);ctx.setTransform(.5,0,0,.5,425,125);this._fx?.draw?.(this);this.fxPaintAt=this.time;this.stage?.refreshFx(this.fxCanvas);}
  private local(e:PointerEvent|WheelEvent):Point{const r=this.canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
  private worldPoint(p:Point):Point{return cameraWorldPoint(p,this.stage!.cameras.main);}
  private pointerDown=(e:PointerEvent)=>{if(this._paused||!this.stage)return;e.preventDefault();this.canvas.focus({preventScroll:true});this.canvas.setPointerCapture?.(e.pointerId);const p=this.local(e);this.pointers.set(e.pointerId,{start:p,last:p,drag:false});this.lastInput=this.time;if(this.pointers.size===2){const pts=[...this.pointers.values()].map(p=>p.last),mid={x:(pts[0].x+pts[1].x)/2,y:(pts[0].y+pts[1].y)/2};this.pinch={distance:Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y),zoom:this.stage.cameras.main.zoom,world:this.worldPoint(mid)};for(const p of this.pointers.values())p.drag=true;}this.wake();};
  private pointerMove=(e:PointerEvent)=>{const pointer=this.pointers.get(e.pointerId);if(!pointer||!this.stage)return;const p=this.local(e),old=pointer.last;pointer.last=p;
    if(this.pointers.size>=2&&this.pinch){this.stage.islandOverview=false;const pts=[...this.pointers.values()].map(p=>p.last),mid={x:(pts[0].x+pts[1].x)/2,y:(pts[0].y+pts[1].y)/2},dist=Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y),range=this.zoomRange();this.stage.cameras.main.setZoom(Phaser.Math.Clamp(this.pinch.zoom*dist/Math.max(1,this.pinch.distance),range.min,range.max));const after=this.worldPoint(mid);this.stage.cameras.main.scrollX+=this.pinch.world.x-after.x;this.stage.cameras.main.scrollY+=this.pinch.world.y-after.y;
    }else if(pointer.drag||gestureIsDrag(pointer.start,p)){this.stage.islandOverview=false;pointer.drag=true;this.stage.cameras.main.scrollX-=(p.x-old.x)/this.stage.cameras.main.zoom;this.stage.cameras.main.scrollY-=(p.y-old.y)/this.stage.cameras.main.zoom;this.canvas.style.cursor='grabbing';}this.lastInput=this.time;this.wake();};
  private pointerUp=(e:PointerEvent)=>{const pointer=this.pointers.get(e.pointerId);this.pointers.delete(e.pointerId);this.pinch=null;this.canvas.style.cursor='grab';if(pointer&&!pointer.drag&&!gestureIsDrag(pointer.start,this.local(e))&&!this._paused&&this.stage)this.tap(this.worldPoint(this.local(e)));this.wake();};
  private pointerCancel=(e:PointerEvent)=>{this.pointers.delete(e.pointerId);this.pinch=null;this.canvas.style.cursor='grab';this.wake();};
  private wheel=(e:WheelEvent)=>{if(!this.stage||this._paused)return;e.preventDefault();this.stage.islandOverview=false;const p=this.local(e),before=this.worldPoint(p),camera=this.stage.cameras.main,range=this.zoomRange();camera.setZoom(Phaser.Math.Clamp(camera.zoom*Math.exp(-e.deltaY*.0013),range.min,range.max));const after=this.worldPoint(p);camera.scrollX+=before.x-after.x;camera.scrollY+=before.y-after.y;this.lastInput=this.time;this.wake();};
  private keydown=(e:KeyboardEvent)=>{const key=e.key.toLowerCase(),target=e.target as HTMLElement|null;if(target?.matches('input,textarea,select,[contenteditable="true"]')||this.shouldSleep())return;if(['arrowleft','arrowright','arrowup','arrowdown','w','a','s','d'].includes(key)){e.preventDefault();this.keys.add(key);this.wake();}if(key==='e'&&!e.repeat&&!e.ctrlKey&&!e.altKey&&!e.metaKey&&!document.querySelector('dialog[open]')&&this.stage){e.preventDefault();const h=nearestReachableHotspot(this.stage.navigation,this.player,this.hotspots);if(h){this.stage.highlight(h.id);this.go(h.id,()=>this.onInteract(h.id));}this.wake();}if(key==='home'){e.preventDefault();this.resetCamera();}};
  private keyup=(e:KeyboardEvent)=>{this.keys.delete(e.key.toLowerCase());this.wake();};
  private tap(point:Point){if(this.mode==='work'&&this._fx?.tap?.(point)){this.wake();return;}const h=this.stage!.hitTest(point);if(h){this.stage!.highlight(h.id);this.go(h.id,()=>this.onInteract(h.id));return;}const ground=unproject(point);if(isWalkable(this.stage!.navigation,ground)){this.player.path=findRoute(this.stage!.navigation,this.player,ground);this.pending=null;this.player.goal=ground;this.stage!.mark(ground);this.wake();}}
  destroy(){if(this.destroyed)return;this.destroyed=true;if(this.speechTimer)clearTimeout(this.speechTimer);this.player.path=[];this.pending=null;this.clearMovementControls();this.disposeObservers();this._fx?.clear?.();this.engine.destroy(false);this.engine.loop.wake();this.cachedPreview.clear();if((window as any).__isoWorld===this)delete (window as any).__isoWorld;}
  private disposeObservers(){this.resizeObserver?.disconnect();this.visibleObserver?.disconnect();this.modalObserver?.disconnect();for(const remove of this.listeners.splice(0))remove();}
}

class DioramaScene extends Phaser.Scene {
  readonly owner:PhaserWorld;
  buildings:Building[]=[];
  navigation:Navigation=makeNavigation({bounds:{x0:0,y0:0,x1:10,y1:9},roads:[{x0:0,y0:0,x1:10,y1:9}],obstacles:[],step:.25});
  cameraSet=false;
  private _islandOverview=false;
  get islandOverview(){return this._islandOverview;}
  set islandOverview(value:boolean){this._islandOverview=value;const stage=this.owner.canvas.closest<HTMLElement>('#stage');if(stage)stage.dataset.islandOverview=value?'true':'false';}
  renderRequested=true;
  private settledFrames=0;
  private actor?:Phaser.GameObjects.Image;
  private actorKey='';
  private actorDirection:Facing='se';
  private actorWalkFrame=0;
  private background?:Phaser.GameObjects.Graphics;
  private groundCache?:Phaser.GameObjects.Image;
  private groundRegion?:Rect;
  private groundScale=0;
  private marker?:Phaser.GameObjects.Image;
  private speech?:Phaser.GameObjects.Container;
  private speechTarget:string|null=null;
  private fxImage?:Phaser.GameObjects.Image;
  private fxTexture?:Phaser.Textures.CanvasTexture;
  private effects:Phaser.GameObjects.GameObject[]=[];
  private staticObjects:Phaser.GameObjects.GameObject[]=[];
  private hits:Array<{hotspot:Hotspot;rect?:Phaser.Geom.Rectangle;object?:Phaser.GameObjects.Container;footprint?:Rect}>=[];
  private placards:Array<{tag:Phaser.GameObjects.Container;size:number;mounted?:boolean}>=[];
  private selected?:Phaser.GameObjects.Image;
  private imageById=new Map<string,Phaser.GameObjects.Image>();
  private previousMode:WorldMode|null=null;
  private previousCareer='';
  private remoteActors=new Map<string,{peer:RemotePlayer;at:Point;from:Point;path:Point[];started:number;image:Phaser.GameObjects.Image;tag:Phaser.GameObjects.Text;texture:string}>();
  private npcArt:Array<{image:Phaser.GameObjects.Image;look:any;gender:string;uniformColor:string;texture:string;seed:number}>=[];
  private requestedAssets=new Set<string>();
  private artRefreshQueued=false;
  private characterRevision=0;
  constructor(owner:PhaserWorld){super({key:'Diorama'});this.owner=owner;}
  preload(){this.queueAssets(['grocery','home','cafe','tree','bench']);}
  create(){this.load.on(Phaser.Loader.Events.COMPLETE,this.assetsReady);preloadIllustratedCharacters(this.charactersReady);this.owner.boot(this);}
  private queueAssets(kinds:string[]){let queued=false;for(const kind of kinds){if(!ASSETS[kind]||this.textures.exists('art-'+kind)||this.requestedAssets.has(kind))continue;this.requestedAssets.add(kind);this.load.image('art-'+kind,assetURL(ASSETS[kind]));queued=true;}return queued;}
  private ensureAssets(kinds:string[]){if(this.queueAssets(kinds)&&!this.load.isLoading())this.load.start();}
  private assetsReady=()=>{if(!this.sys.isActive())return;this.owner['cachedPreview'].clear();this.queueArtRefresh();};
  private charactersReady=()=>{if(!this.sys.isActive())return;this.characterRevision++;this.queueArtRefresh();};
  private queueArtRefresh(){if(this.artRefreshQueued)return;this.artRefreshQueued=true;queueMicrotask(()=>{this.artRefreshQueued=false;if(!this.sys.isActive())return;this.rebuild();this.owner.wake();});}
  update(_time:number,delta:number){this.cacheGround();this.owner.step(Math.min(.06,delta/1000));}
  requestRender(){this.renderRequested=true;this.settledFrames=0;}
  settle(){if(this.renderRequested){this.renderRequested=false;this.settledFrames=0;return false;}return ++this.settledFrames>=2;}
  hasEffects(){return this.effects.length>0||this.tweens.getTweens().length>0;}
  lineClear(a:Point,b:Point){return findClear(this.navigation,a,b);}
  rebuild(){
    if(!this.sys.isActive())return;
    for(const object of this.staticObjects)object.destroy();this.staticObjects=[];for(const key of new Set(this.npcArt.map(n=>n.texture)))if(this.textures.exists(key))this.textures.remove(key);this.npcArt=[];this.groundCache=undefined;this.groundRegion=undefined;this.hits=[];this.placards=[];this.imageById.clear();this.marker?.destroy();this.marker=undefined;this.selected?.destroy();this.selected=undefined;this.clearSpeech();
    const changed=this.previousMode!==this.owner.mode||this.owner.mode==='work'&&this.previousCareer!==this.owner.career;
    this.previousMode=this.owner.mode;this.previousCareer=this.owner.career;this.cameras.main.setBackgroundColor(this.owner.mode==='town'?SEA_COLOR:'#ede3ce');this.background=this.add.graphics().setDepth(-10000);this.staticObjects.push(this.background);
    if(this.owner.mode==='town')this.town();else this.work();
    if(changed||!isWalkable(this.navigation,this.owner.player)){const home=this.owner.mode==='town'?{x:6.2,y:6.2}:{x:6.4,y:6.4};const at=nearestWalkable(this.navigation,home)||home;Object.assign(this.owner.player,at,{path:[],goal:null});this.owner.pending=null;this.resetCamera(false);}
    this.refreshPlayer();this.positionPlayer(false);this.syncRemotePlayers();if(this.fxImage)this.fxImage.setVisible(this.owner.mode==='work');this.requestRender();
  }
  /** Cache only the visible ground plus a pan margin, avoiding a giant whole-map bitmap. */
  private cacheGround(){
    if(!this.background)return;
    const camera=this.cameras.main,cx=camera.scrollX+camera.width/2,cy=camera.scrollY+camera.height/2,halfW=camera.width/camera.zoom/2,halfH=camera.height/camera.zoom/2;
    if(this.owner.mode==='town')for(const sign of this.placards){sign.tag.setVisible(camera.zoom>=.18);const scale=sign.mounted?1:Phaser.Math.Clamp(10/(sign.size*camera.zoom),1,2.2);if(Math.abs(sign.tag.scaleX-scale)>.001)sign.tag.setScale(scale);}
    const view={x0:cx-halfW,y0:cy-halfH,x1:cx+halfW,y1:cy+halfH};
    const cache=groundCacheRegion(view,camera.zoom);
    if(this.groundRegion&&this.groundScale>=cache.scale*.9&&view.x0>=this.groundRegion.x0&&view.y0>=this.groundRegion.y0&&view.x1<=this.groundRegion.x1&&view.y1<=this.groundRegion.y1)return;
    const region=cache.region,canvas=document.createElement('canvas');canvas.width=cache.width;canvas.height=cache.height;
    const cacheCamera=new Phaser.Cameras.Scene2D.Camera(0,0,canvas.width,canvas.height);cacheCamera.setScene(this).setScroll(cache.scroll.x,cache.scroll.y).setZoom(cache.scale);cacheCamera.preRender();
    this.background.setVisible(true);
    // Phaser's public graphics Canvas compositor accepts an explicit context and camera.
    (this.background as any).renderCanvas(this.game.renderer,this.background,cacheCamera,null,canvas.getContext('2d'),false);
    this.background.setVisible(false);cacheCamera.destroy();if(this.groundCache){const old=this.groundCache;old.destroy();this.staticObjects=this.staticObjects.filter(o=>o!==old);}if(this.textures.exists('iso-ground'))this.textures.remove('iso-ground');this.textures.addCanvas('iso-ground',canvas)!.setFilter(Phaser.Textures.FilterMode.LINEAR);
    this.groundCache=this.add.image(region.x0,region.y0,'iso-ground').setOrigin(0,0).setScale(1/cache.scale).setDepth(-10000);this.staticObjects.push(this.groundCache);this.groundRegion=region;this.groundScale=cache.scale;this.requestRender();
  }
  resetCamera(focusPlayer=true){const view=defaultCamera(this.owner.mode,this.owner.width,this.owner.height);if(focusPlayer&&this.owner.mode==='town'){const p=px(this.owner.player,55);view.scrollX=p.x-this.owner.width/2;view.scrollY=p.y-this.owner.height/2;}this.islandOverview=false;this.cameras.main.setZoom(view.zoom).setScroll(view.scrollX,view.scrollY);this.cameraSet=true;this.requestRender();}
  overviewIsland(){const view=islandOverviewCamera(this.owner.width,this.owner.height);this.islandOverview=true;this.cameras.main.setZoom(view.zoom).setScroll(view.scrollX,view.scrollY);this.cameraSet=true;this.requestRender();}
  private polygon(points:Point[],fill:number,alpha=1,stroke?:number,width=1){const g=this.background!;g.fillStyle(fill,alpha);g.fillPoints(points,true);if(stroke!==undefined){g.lineStyle(width,stroke,1);g.strokePoints(points,true);}}
  private floorRect(r:Rect,color:number,alpha=1,z=0){this.polygon([px({x:r.x0,y:r.y0},z),px({x:r.x1,y:r.y0},z),px({x:r.x1,y:r.y1},z),px({x:r.x0,y:r.y1},z)],color,alpha);}
  private town(){
    this.buildings=townBuildings(this.owner.game?.catalogue||[]);this.navigation=townNavigation(this.buildings);const b=this.navigation.bounds,roads=townRoads(this.buildings);
    this.islandGround();
    // Rounded moss patches, worn shoulders and uneven paving soften the shared road grid.
    const ground=this.background!;
    for(let x=.6;x<b.x1;x+=1.8)for(let y=.6;y<b.y1;y+=1.7){const p={x:x+Math.sin(y*3)*.4,y:y+Math.cos(x*2)*.3};if(roads.some(r=>inside(p,r)))continue;const q=px(p),seed=Math.round(x*11+y*7);ground.fillStyle([0x97b778,0xa9be83,0xc4cf93][Math.abs(seed)%3],.36);ground.fillEllipse(q.x,q.y,100+Math.sin(x+y)*42,48+Math.cos(x-y)*17);if(seed%3===0){ground.fillStyle(seed%2?0xf2dca5:0xf5eec8,.75);for(let k=0;k<4;k++)ground.fillCircle(q.x+Math.sin(k*2+seed)*28,q.y+Math.cos(k*3+seed)*12,2);}}
    for(const road of roads){this.floorRect({x0:road.x0-.12,y0:road.y0-.12,x1:road.x1+.12,y1:road.y1+.12},0xa7af88,.5);this.floorRect({x0:road.x0-.035,y0:road.y0-.035,x1:road.x1+.035,y1:road.y1+.035},0xc8b28f);this.floorRect(road,0xe7d7ba);}
    for(let x=0;x<b.x1;x+=.54)for(let y=0;y<b.y1;y+=.54){const p={x:x+.27,y:y+.27};if(!roads.some(r=>inside(p,r)))continue;const q=px(p),seed=Math.round(x*29+y*17);ground.fillStyle(seed%3?0xf2e5cb:0xdac5a6,.43);ground.fillRoundedRect(q.x-19+Math.sin(seed)*3,q.y-7,35,13,4);if(seed%5===0){ground.lineStyle(1,0xc4ad89,.3);ground.lineBetween(q.x-15,q.y+6,q.x+12,q.y+6);}}
    this.owner.hotspots=[];
    for(const building of this.buildings){const foot=px(building.at);ground.fillStyle(0x7e906b,.2);ground.fillEllipse(foot.x,foot.y-24,370+building.slot%3*20,160+building.slot%2*30);
      const kind=townBuildingArt(building.meta,building.variant);this.ensureAssets([kind]);const key=this.textures.exists('art-'+kind)?'art-'+kind:'art-'+building.variant;
      const texture=this.textures.get(key),source=texture.getSourceImage() as HTMLImageElement|HTMLCanvasElement;
      const image=this.add.image(foot.x,foot.y,key).setOrigin(.5,1).setDisplaySize(355,355*source.height/source.width).setDepth(foot.y);this.staticObjects.push(image);this.imageById.set('career:'+building.id,image);
      const title=String(building.meta.place||building.meta.short||building.meta.name||building.id),door=px(building.door),sign=this.facadeSign(title,image,kind,asHex(building.meta.color,0xa57952));
      const h:Hotspot={id:'career:'+building.id,label:title,...building.at,approach:building.door,point:door,z:0,range:50};this.owner.hotspots.push(h);
      this.hits.push({hotspot:h,rect:image.getBounds()},{hotspot:h,object:sign});
      if(building.slot%4===0)this.lamp({x:building.footprint.x1-.1,y:building.footprint.y1-.15});
      if(building.slot%5===2)this.flower({x:building.footprint.x0+.35,y:building.footprint.y1-.1},0xc8ab86);
    }
    for(const prop of townGarden(this.buildings))this.vegetation(prop.kind,prop.at,prop.size);
    // The triangular commons at the entrance gives the street a lived-in focal point.
    const common=px({x:9.7,y:9.7});ground.fillStyle(0xa0bb82,.8);ground.fillEllipse(common.x,common.y,660,306);this.landmarks();this.vegetation('flowers',{x:7.4,y:9},.8);this.bench({x:11.8,y:8.4});
    this.placard('PHỐ CÓ CHUYỆN',{x:12.9,y:12.9},17,230,0x856448,76);
  }
  private islandGround(){
    const ground=this.background!;
    this.polygon(islandCoastline(6).map(p=>px(p)),0x85c8c8,.75);
    this.polygon(islandCoastline(3.3).map(p=>px(p)),0xa9d8cf,.8);
    this.polygon(islandCoastline(1.3).map(p=>px(p,-8)),0x5aadae,.22);
    const coast=islandCoastline(),shore=coast.map(p=>px(p));this.polygon(shore,0xecd7aa,1,0xc1bb89,3);
    this.polygon(islandCoastline(-.5).map(p=>px(p)),0xf3e4bd,.78);
    this.polygon(islandCoastline(-1.15).map(p=>px(p)),COLORS.grass,1,0xaebd8d,2);
    const foam=islandCoastline(.8).map(p=>px(p));ground.lineStyle(3,0xe4f4e7,.65);ground.strokePoints(foam,true);
    // All water highlights are baked into the viewport ground cache, with no wave loop.
    const waterMarks=islandCoastline(4.5);for(let i=0;i<coast.length;i+=4){const p=px(waterMarks[i]);ground.lineStyle(2,0xe0f1df,.32);ground.beginPath();ground.moveTo(p.x-20,p.y);ground.lineTo(p.x-5,p.y+2);ground.lineTo(p.x+18,p.y-1);ground.strokePath();}
    const plants=islandCoastline(-2.6);for(let i=3;i<plants.length;i+=7){const at=plants[i];this.vegetation(i%3?'palm':'rocks',at,.82+(i%4)*.09);const p=px(at);ground.fillStyle(0x829773,.28);ground.fillEllipse(p.x,p.y,93,35);if(i%2)this.vegetation('shrubs',{x:at.x+.7,y:at.y+.25},.8);}
    const stones=islandCoastline(-.25);for(let i=5;i<stones.length;i+=7){const p=px(stones[i]);ground.fillStyle(i%2?0xb7b694:0xc4c09e,.95);ground.fillEllipse(p.x,p.y,20+i%4*5,9+i%3*2);ground.lineStyle(1,0x8d9b84,.48);ground.strokeEllipse(p.x,p.y,20+i%4*5,9+i%3*2);}
    // Static inland groves reserve future districts without loading more gameplay.
    for(const grove of [{x:-25,y:29},{x:-13,y:15},{x:62,y:28},{x:66,y:45},{x:-5,y:43},{x:33,y:-6},{x:43,y:57},{x:53,y:6}]){
      for(let i=0;i<19;i++){const angle=i*2.4,radius=1.1+Math.sqrt(i)*1.6,at={x:grove.x+Math.cos(angle)*radius,y:grove.y+Math.sin(angle)*radius*.72},p=px(at);
        ground.fillStyle(i%2?0x9cb384:0xa9bb8d,.34);ground.fillEllipse(p.x,p.y,410,160);this.vegetation(['banyan','banana','bamboo','flamboyant','shrubs','flowers'][i%6],at,.95+(i%4)*.14);
      }
    }
    // A small fictional timber pier follows the southern shore, outside navigation.
    this.floorRect({x0:13.7,y0:61,x1:15,y1:68},0xa38258);for(let y=61;y<68;y+=.45)this.floorRect({x0:13.73,y0:y,x1:14.98,y1:y+.39},0xd1ac78);for(const at of [{x:13.7,y:61.2},{x:15,y:61.2},{x:13.7,y:67.6},{x:15,y:67.6}]){const p=px(at);ground.fillStyle(0x947148);ground.fillEllipse(p.x,p.y,10,6);}
  }
  private work(){
    this.buildings=[];this.owner.hotspots=[];const family=kindOf(this.owner.career),meta=this.owner.game?.catalogue?.find(c=>c.id===this.owner.career),primary=asHex(meta?.color,COLORS.sage),wood=0xb78b64,appearance=roomAppearance(this.owner.c,this.owner.career);
    const bounds={x0:.25,y0:.25,x1:9.75,y1:8.75};this.floorRect({x0:0,y0:0,x1:10,y1:9},0xb99873);
    // Two back walls, open front and a tiled wood floor form a genuine cutaway.
    this.polygon([px({x:0,y:0}),px({x:10,y:0}),px({x:10,y:0},190),px({x:0,y:0},190)],asHex(appearance.wall),1,0xd2b995,2);
    this.polygon([px({x:0,y:0}),px({x:0,y:9}),px({x:0,y:9},190),px({x:0,y:0},190)],asHex(appearance.wallSide),1,0xc7ae89,2);
    for(let x=0;x<10;x++)for(let y=0;y<9;y++)this.floorRect({x0:x+.018,y0:y+.018,x1:x+.98,y1:y+.98},(x+y)%2?0xf4e4c7:0xe9d8b8);
    this.roomBackdrop(family,appearance);
    const obstacles:Rect[]=[];
    const prop=(id:string,label:string,r:Rect,height:number,color:number,approach:Point,detail:'shelf'|'desk'|'counter'|'crate'|'board'|'door'|'plant'='counter')=>{
      obstacles.push(r);const p={x:(r.x0+r.x1)/2,y:r.y1},foot=px(p),image=this.prop(r,height,color,detail),bounds=image.getBounds();const h:Hotspot={id,label,...p,approach,point:foot,z:height,range:45};this.owner.hotspots.push(h);this.hits.push({hotspot:h,rect:bounds});const tag=this.label(label,image.x,bounds.y-14,13,176,0x8c7156);tag.setDepth(image.depth+.6);return image;
    };
    const words=this.owner.words(),office=family==='office',food=['cafe','kitchen','pho','comtam','teabar'].includes(family),farm=family==='farm',classroom=family==='classroom',home=['home','flat','nursery','lodging'].includes(family),service=family==='service';
    prop('shelf',words.shelf||'Kệ hàng',{x0:.6,y0:1.3,x1:1.7,y1:4.3},120,wood,{x:2.2,y:3},'shelf');
    prop('warehouse',words.warehouse||'Kho',{x0:.65,y0:6.2,x1:1.7,y1:7.5},67,0xbc9874,{x:2.15,y:6.8},'crate');
    prop('workbench',String(meta?.station||'Bàn làm việc'),{x0:3.25,y0:1.4,x1:5.65,y1:2.7},62,primary,{x:4.5,y:3.25},office?'desk':farm?'crate':'counter');
    prop('counter',words.counter||'Quầy bàn giao',{x0:6.8,y0:3.3,x1:8.7,y1:4.6},64,primary,{x:7.8,y:5.2},office?'desk':'counter');
    prop('evidence',words.evidence||'Phiếu công việc',{x0:7.4,y0:.65,x1:8.8,y1:1.65},58,0xc6a781,{x:7.9,y:2.15},'board');
    prop('board',words.board||'Chuyện phố',{x0:2.6,y0:.4,x1:3.15,y1:1.15},104,0xb9926d,{x:3.5,y:1.3},'board');
    prop('door',this.owner.c.open?words.door_open:words.door_closed,{x0:9.1,y0:5.6,x1:9.7,y1:6.5},100,0x987b5a,{x:8.65,y:6.15},'door');
    // Family props carry visual context; every task still opens its original module.
    if(food){this.cup({x:4.2,y:2.4},66,0xf1cf89);this.cup({x:4.85,y:2.1},66,0xc38b69);this.bread({x:3.6,y:2.25},67);this.prop(WORK_FOOD_SHELF,128,0xb1b9a0,'shelf');obstacles.push(WORK_FOOD_SHELF);}
    else if(classroom){this.prop({x0:5.8,y0:5.8,x1:6.8,y1:6.6},38,0xd7b166,'desk');this.prop({x0:3.5,y0:5.7,x1:4.5,y1:6.5},38,0xcc9d7f,'desk');obstacles.push({x0:5.8,y0:5.8,x1:6.8,y1:6.6},{x0:3.5,y0:5.7,x1:4.5,y1:6.5});}
    else if(farm){for(let i=0;i<3;i++)this.flower({x:3.35+i*.65,y:2.2},0xdaae79,65);this.tree({x:9.3,y:2.1},.6,0);}
    else if(home){this.prop({x0:3,y0:5.1,x1:4.7,y1:6.3},38,0xa1b292,'counter');obstacles.push({x0:3,y0:5.1,x1:4.7,y1:6.3});}
    else if(service){this.prop({x0:4.7,y0:5,x1:5.7,y1:6},46,0xd2ae96,'counter');obstacles.push({x0:4.7,y0:5,x1:5.7,y1:6});}
    this.window(WORK_WINDOW,WORK_WINDOW.z);this.tree({x:8.9,y:8.1},.56,1);this.cat({x:2.4,y:7.8});
    this.savedRoomDetails(appearance,obstacles,primary);
    this.operationsStation('ops:finance',words.finance||'Sổ thu chi',{x:9.3,y:2},85,{x:9.15,y:2.7},'ledger');
    this.operationsStation('ops:property',words.property||'Mặt bằng',{x:0,y:5.5},105,{x:2.4,y:5.8},'property');
    this.operationsStation('ops:security',words.security||'An ninh',{x:1,y:.8},110,{x:2,y:.7},'security');
    const catAt={x:2.4,y:7.8},catPixel=px(catAt);const pet:Hotspot={id:'pet',label:words.pet||'Chơi với Mướp',...catAt,approach:{x:3,y:7.7},point:catPixel,z:30,range:40};this.owner.hotspots.push(pet);this.hits.push({hotspot:pet,rect:new Phaser.Geom.Rectangle(catPixel.x-35,catPixel.y-48,70,58)});
    this.navigation=makeNavigation({bounds,roads:[bounds],obstacles,step:.25});
    const tasks=activeTasks(this.owner.c),seen=new Set<string>();let slot=0;
    for(const task of tasks){if(!task.npc||seen.has(task.npc)||slot>=4)continue;seen.add(task.npc);const at=[{x:7.6,y:6.3},{x:5.4,y:7.25},{x:4,y:7.45},{x:8.5,y:7.5}][slot++];this.person('npc:'+task.npc,this.owner.game?.npcs?.find(n=>n.id===task.npc)?.display_name||'Khách',at,slot);}
    const staff=(this.owner.c.ops?.staff||[]).filter((s:any)=>s.status==='hired');staff.slice(0,3).forEach((s:any,i:number)=>this.person('staff:'+s.id,s.name||'Nhân viên',{x:6.1+i*.75,y:2.6},i+4));
    if(this.owner.c.event&&this.owner.c.event.stage!=='resolved')this.person('event','Chuyện mới',{x:3,y:4.7},8);
    if(this.owner.c.upgrades?.includes('assistant')&&!staff.length)this.person('assistant','Bạn phụ việc',{x:6.4,y:2.9},5);
    if(['reported','result'].includes(this.owner.c.ops?.security?.current_case?.status))this.person('officer','Công an khu phố',{x:8.9,y:7.9},7);
    const name=String(this.owner.c.life?.shop_name||meta?.place||meta?.short||'Nơi làm việc');this.placard(name,{x:1.4,y:8.85},18,320,primary,54);
  }
  private operationsStation(id:string,label:string,at:Point,z:number,approach:Point,icon:string){
    const foot=px(at),point=px(at,z);this.roomIcon(icon,at,z,.43);
    const tag=this.label(label,point.x,point.y-42,11,140,0x93815e);tag.setDepth(foot.y+.3);
    const h:Hotspot={id,label,...at,approach,point,z,range:42};this.owner.hotspots.push(h);this.hits.push({hotspot:h,rect:new Phaser.Geom.Rectangle(point.x-77,point.y-62,154,66)});
  }
  private savedRoomDetails(appearance:RoomAppearance,obstacles:Rect[],primary:number){
    for(const decor of appearance.decor){
      if(decor.footprint)obstacles.push(decor.footprint);
      if(decor.id==='plant')this.flower(decor.at,0x9eb483,decor.z);
      if(decor.id==='lamp')this.roomIcon('lamp',decor.at,decor.z,decor.z?.45:.75);
      if(decor.id==='seat'){const r=decor.footprint||{x0:decor.at.x-.35,y0:decor.at.y-.15,x1:decor.at.x+.35,y1:decor.at.y+.15};const image=this.prop(r,decor.z?15:33,primary,'bench');if(decor.z){image.y-=decor.z;image.setDepth(px(decor.at).y+.2);}}
      if(decor.id==='rug')this.rug(decor.at);
      if(decor.id==='poster')this.roomIcon('poster',decor.at,decor.z,.66);
    }
    if(appearance.tier!=='cozy'){const bench={x0:3.05,y0:7.85,x1:4.55,y1:8.4};this.prop(bench,35,primary,'bench');obstacles.push(bench);}
    if(appearance.tier==='garden')for(const at of [{x:5.95,y:8.25},{x:6.65,y:8.25}]){this.flower(at,0xd4ac84);obstacles.push({x0:at.x-.23,y0:at.y-.23,x1:at.x+.23,y1:at.y+.23});}
    if(appearance.tools.includes('shelf')){const shelf={x0:.65,y0:4.75,x1:1.7,y1:5.65};this.prop(shelf,75,0xbc9874,'shelf');obstacles.push(shelf);}
    if(appearance.tools.includes('workbench'))this.roomIcon('check', {x:4.45,y:2.45},67,.45);
    if(appearance.tools.includes('board'))this.roomIcon('poster',{x:8.9,y:.2},128,.53);
    if(appearance.gearTier)this.roomIcon('gear-'+appearance.gearTier,{x:5.15,y:2.2},67,.45);
    if(appearance.needsRepair)this.roomIcon('repair',{x:3.65,y:2.5},66,.45);
    const installed:Record<string,{at:Point;z:number;scale:number}>={camera:{at:{x:1.8,y:.1},z:150,scale:.5},bell:{at:{x:9.45,y:5.6},z:113,scale:.38},lock:{at:{x:1.6,y:6.7},z:50,scale:.38},light:{at:{x:9.5,y:6.5},z:125,scale:.52}};
    for(const id of appearance.security){const item=installed[id];this.roomIcon(id,item.at,item.z,item.scale);}
  }
  private roomIcon(kind:string,at:Point,z:number,scale:number){
    return this.artObject(kind==='light'?'lamp':kind,at,z,82*scale);
  }
  private rug(at:Point){
    const key='illustrated-room-rug';this.textureObject(key,336,192,ctx=>{
      const diamond=(inset:number,color:string)=>{ctx.fillStyle=color;ctx.beginPath();ctx.moveTo(168,10+inset);ctx.lineTo(326-inset*2,94);ctx.quadraticCurveTo(331-inset*2,97,326-inset*2,101);ctx.lineTo(168,182-inset);ctx.lineTo(10+inset*2,101);ctx.quadraticCurveTo(5+inset*2,97,10+inset*2,94);ctx.closePath();ctx.fill();};
      diamond(0,'#987d8a');diamond(5,'#ceacb9');diamond(10,'#ebcbd0');diamond(17,'#c6a1b2');ctx.strokeStyle='#f3ddd1';ctx.lineWidth=1;for(let y=47;y<149;y+=5){ctx.beginPath();ctx.moveTo(94+Math.abs(97-y),y);ctx.lineTo(244-Math.abs(97-y),y);ctx.stroke();}
    });const point=px(at,1),image=this.add.image(point.x,point.y,key).setDisplaySize(168,96).setDepth(-4999);this.staticObjects.push(image);
  }
  private label(text:string,x:number,y:number,size:number,maxWidth:number,color:number){
    const t=this.add.text(0,0,text,{fontFamily:FONT,fontSize:size+'px',fontStyle:'bold',color:'#654a39',align:'center',wordWrap:{width:maxWidth,useAdvancedWrap:true},lineSpacing:2}).setOrigin(.5,.5);
    const width=Math.min(maxWidth+20,t.width+24),height=t.height+15,g=this.add.graphics();g.fillStyle(0x694d39,.18);g.fillRoundedRect(-width/2+2,-height/2+4,width,height,7);g.fillStyle(color,1);g.fillRoundedRect(-width/2-2,-height/2-2,width+4,height+4,6);g.fillStyle(COLORS.cream,1);g.fillRoundedRect(-width/2,-height/2,width,height,4);g.lineStyle(1,0xd0b89a,.8);g.lineBetween(-width/2+8,height/2-3,width/2-8,height/2-3);g.fillStyle(0x947557);for(const side of [-1,1])g.fillCircle(side*(width/2-6),0,1.3);const container=this.add.container(x,y,[g,t]);this.staticObjects.push(container);return container;
  }
  private placard(text:string,at:Point,size:number,maxWidth:number,color:number,height=42){const p=px(at),post=this.add.graphics().setDepth(p.y+.3);post.fillStyle(0x8b6d4c);post.fillRoundedRect(p.x-4,p.y-height,8,height,2);post.fillStyle(0xc6aa7d);post.fillRect(p.x-1,p.y-height,2,height-3);post.fillStyle(0x71583e,.13);post.fillEllipse(p.x+3,p.y+1,26,8);this.staticObjects.push(post);const tag=this.label(text,p.x,p.y-height,size,maxWidth,color);tag.setDepth(p.y+.4);this.placards.push({tag,size});return tag;}
  private facadeSign(text:string,image:Phaser.GameObjects.Image,kind:string,color:number){
    const anchor:Record<string,[number,number]>={grocery:[.35,.33],cafe:[.34,.32],home:[.35,.47],pharmacy:[.38,.36],'mother-baby':[.38,.4],garage:[.44,.31],pho:[.36,.35]};
    const [x,y]=anchor[kind]||anchor.home,tag=this.label(text,image.x+(x-.5)*image.displayWidth,image.y-(1-y)*image.displayHeight,17,170,color);
    tag.setRotation(.24).setDepth(image.depth+.4);tag.setData('buildingSign',true);this.placards.push({tag,size:17,mounted:true});return tag;
  }
  private textureObject(key:string,width:number,height:number,draw:(ctx:CanvasRenderingContext2D)=>void){if(!this.textures.exists(key)){const c=document.createElement('canvas');c.width=width;c.height=height;const ctx=c.getContext('2d')!;ctx.imageSmoothingEnabled=true;draw(ctx);this.textures.addCanvas(key,c)!.setFilter(Phaser.Textures.FilterMode.LINEAR);}return key;}
  private characterTexture(prefix:string,look:any,gender:string,direction:Facing,uniformColor:string,walkFrame=0){
    const stamp=getCharacterStamp({look,gender,direction,uniformColor,walkFrame,onReady:this.charactersReady}),key=prefix+'-'+JSON.stringify([look,gender,direction,uniformColor,walkFrame,this.characterRevision]);
    if(!this.textures.exists(key))this.textures.addCanvas(key,stamp.canvas)!.setFilter(Phaser.Textures.FilterMode.LINEAR);return key;
  }
  syncRemotePlayers(){
    if(!this.sys.isActive())return;const peers=this.owner.mode==='town'?publicTownPlayers(this.owner.remotePlayers,this.navigation):[],present=new Set(peers.map(p=>p.pid));
    for(const [pid,actor] of this.remoteActors)if(!present.has(pid)){actor.image.destroy();actor.tag.destroy();if(this.textures.exists(actor.texture))this.textures.remove(actor.texture);this.remoteActors.delete(pid);}
    for(const peer of peers){
      const look={...defaultLook(peer.gender),...peer.look},key=this.characterTexture('iso-peer-'+peer.pid,look,peer.gender,peer.direction,'#8ba77a');
      let actor=this.remoteActors.get(peer.pid);
      if(!actor){const image=this.add.image(0,0,key).setOrigin(.5,1).setScale(CHARACTER_SCALE),tag=this.add.text(0,0,peer.name,{fontFamily:FONT,fontSize:'13px',color:'#654a39',backgroundColor:'#fff3da',padding:{x:6,y:3}}).setOrigin(.5,1);actor={peer,at:{x:peer.x,y:peer.y},from:{x:peer.x,y:peer.y},path:[],started:0,image,tag,texture:key};this.remoteActors.set(peer.pid,actor);}
      else{
        if(actor.texture!==key){const old=actor.texture;actor.image.setTexture(key);actor.texture=key;if(this.textures.exists(old))this.textures.remove(old);}
        if(Math.hypot(actor.peer.x-peer.x,actor.peer.y-peer.y)>1e-5){actor.from={...actor.at};actor.path=this.owner.reduced?[]:findRoute(this.navigation,actor.at,peer);actor.started=this.owner.time;if(!actor.path.length)actor.at={x:peer.x,y:peer.y};}
        actor.peer=peer;actor.tag.setText(peer.name);
      }
    }
    this.stepRemotePlayers(this.owner.time);this.requestRender();
  }
  stepRemotePlayers(now:number){
    let active=false;
    for(const actor of this.remoteActors.values()){
      let moving=false;
      if(actor.path.length){const progress=Math.min(1,(now-actor.started)/.24);actor.at=interpolateRoute(actor.from,actor.path,progress);moving=progress<1;if(!moving)actor.path=[];active||=moving;}
      const walkFrame=moving&&!this.owner.reduced?1+Math.floor(now*7)%2:0,key=this.characterTexture('iso-peer-'+actor.peer.pid,{...defaultLook(actor.peer.gender),...actor.peer.look},actor.peer.gender,actor.peer.direction,'#8ba77a',walkFrame);if(key!==actor.texture){const old=actor.texture;actor.image.setTexture(key);actor.texture=key;if(this.textures.exists(old))this.textures.remove(old);}
      const point=px(actor.at);actor.image.setPosition(point.x,point.y).setDepth(point.y+.5);actor.tag.setPosition(point.x,point.y-112).setDepth(point.y+.7).setVisible(this.cameras.main.zoom>=.22);
    }
    return active;
  }
  artSource(kind:string){if(['pharmacy','mother-baby','garage','pho'].includes(kind)&&!this.textures.exists('art-'+kind))kind=kind==='pho'?'cafe':'home';return this.textures.get(this.artTexture(kind)).getSourceImage() as HTMLImageElement|HTMLCanvasElement;}
  private artTexture(kind:string,variant:string|number=0){this.ensureAssets([kind]);if(this.textures.exists('art-'+kind))return 'art-'+kind;const key='illustrated-detail-'+kind+'-'+variant,size:Record<string,[number,number]>={lamp:[192,512],window:[384,360],cat:[384,300],cup:[256,300],bread:[384,260],pond:[512,320],pool:[512,320],boat:[512,360]};const [width,height]=size[kind]||[384,384];return this.textureObject(key,width,height,ctx=>drawIllustratedDetail(ctx,kind,String(variant)));}
  private artObject(kind:string,p:Point,z:number,width:number,variant:string|number=0){
    const key=this.artTexture(kind,variant),source=this.textures.get(key).getSourceImage() as HTMLImageElement|HTMLCanvasElement,point=px(p,z),image=this.add.image(point.x,point.y,key).setOrigin(.5,1).setDisplaySize(width,width*source.height/source.width).setDepth(px(p).y+.2);this.staticObjects.push(image);return image;
  }
  private roomBackdrop(family:string,appearance:RoomAppearance){
    const type=family==='office'?'office':['cafe','kitchen','pho','comtam','teabar'].includes(family)?'cafe':['home','flat','nursery','lodging','service'].includes(family)?'home':'shop',kind='interior-'+type;this.ensureAssets([kind,'counter','shelf','desk','crates']);if(!this.textures.exists('art-'+kind))return;
    const original=this.textures.get('art-'+kind).getSourceImage() as HTMLImageElement,key=appearance.theme==='boba'?'art-'+kind:'illustrated-'+kind+'-'+appearance.theme;
    if(!this.textures.exists(key))this.textureObject(key,original.width,original.height,ctx=>{
      ctx.drawImage(original,0,0);const pixels=ctx.getImageData(0,0,original.width,original.height),rgb=appearance.wall.slice(1).match(/../g)!.map(v=>parseInt(v,16));
      // Recolour plaster only, preserving painted light, dark wood, tiles and every small detail.
      for(let y=0;y<original.height*.7;y++)for(let x=0;x<original.width;x++){if(y/original.height>.43+.25*Math.abs(x/original.width-.5)*2)continue;const i=(y*original.width+x)*4,r=pixels.data[i],g=pixels.data[i+1],b=pixels.data[i+2];if(pixels.data[i+3]<24||r<155||g<128||b<80||r-g>55||g-b>75||b>g+10)continue;const light=(r*.3+g*.6+b*.1)/215;for(let c=0;c<3;c++)pixels.data[i+c]=Math.min(255,rgb[c]*light);}
      ctx.putImageData(pixels,0,0);
    });const image=this.add.image(32,608,key).setOrigin(.5,1).setDisplaySize(1216,1216*original.height/original.width).setDepth(-5000);this.staticObjects.push(image);
  }
  private prop(r:Rect,height:number,color:number,kind:string){
    const w=r.x1-r.x0,d=r.y1-r.y0,center=px({x:(r.x0+r.x1)/2,y:(r.y0+r.y1)/2}),bottom=(r.x1+r.y1)*32,width=Math.min(kind==='shelf'?175:270,(w+d)*64+10),image=this.artObject(kind==='crate'?'crates':kind,{x:(r.x0+r.x1)/2,y:(r.y0+r.y1)/2},0,width,color%3);image.setPosition(center.x,bottom).setDepth(bottom);if(d>w)image.setFlipX(true);return image;
  }
  private tree(p:Point,size:number,variant:number){return this.artObject('tree',p,0,190*size,variant);}
  private vegetation(kind:string,p:Point,size=1){
    const frames=['banyan','flamboyant','palm','banana','bamboo','flowers','shrubs','rocks'],index=frames.indexOf(kind),key='art-vegetation';this.ensureAssets(['vegetation']);
    if(index<0||!this.textures.exists(key))return this.tree(p,size,0);
    const texture=this.textures.get(key),source=texture.getSourceImage() as HTMLImageElement,width=source.width/4,height=source.height/2,name=String(index);
    if(!texture.has(name))texture.add(name,0,index%4*width,Math.floor(index/4)*height,width,height);
    const point=px(p),image=this.add.image(point.x,point.y,key,name).setOrigin(.5,.93).setDisplaySize(210*size,210*size*height/width).setDepth(point.y+.2);this.staticObjects.push(image);return image;
  }
  private flower(p:Point,color:number,z=0){return this.artObject('plant',p,z,59,color%3);}
  private bench(p:Point){return this.artObject('bench',p,0,125);}
  private lamp(p:Point){return this.artObject('lamp',p,0,52);}
  private window(p:Point,z:number){const image=this.artObject('window',p,z,110);image.setOrigin(.5,.5).setDepth(-100);return image;}
  private cup(p:Point,z:number,color:number){return this.artObject('cup',p,z,24,color%3);}
  private bread(p:Point,z:number){return this.artObject('bread',p,z,45);}
  private cat(p:Point){return this.artObject('cat',p,0,62);}
  private landmarks(){
    for(const landmark of townLandmarks()){
      const r=landmark.footprint,g=landmarkPlaneGeometry(r),source=this.artSource(landmark.kind),key='island-landmark-'+landmark.kind+'-'+this.textures.exists('art-'+landmark.kind);
      this.textureObject(key,Math.ceil(g.width),Math.ceil(g.height),ctx=>{ctx.setTransform(g.a/source.width,g.b/source.width,g.c/source.height,g.d/source.height,g.e,0);const y0=landmark.kind==='pool'?source.height*.22:0,h=landmark.kind==='pool'?source.height*.74:source.height;ctx.drawImage(source,0,y0,source.width,h,0,0,source.width,source.height);});
      const image=this.add.image(g.x,g.y,key).setOrigin(0,0).setDepth(g.depth-.5);this.staticObjects.push(image);
      if(landmark.kind==='boat'){this.floorRect(r,0x7aaeb5);this.artObject('bench',{x:11.8,y:11.9},0,80);}
      const point=px(landmark.at),h:Hotspot={id:landmark.id,label:landmark.label,...landmark.at,approach:landmark.approach,point,z:0,range:70};this.owner.hotspots.push(h);this.hits.push({hotspot:h,footprint:r});
      const tag=this.placard(landmark.label,landmark.approach,14,190,0x668574);this.hits.push({hotspot:h,object:tag});
    }
  }
  private person(id:string,label:string,p:Point,seed:number){
    const gender=seed%2?'female':'male',look=defaultLook(gender);look.top=['ao_thun_xanh','ao_len','ao_so_mi','ao_thun_kem'][seed%4];look.hair=seed%2?'toc_bui':'toc_ngan';
    const uniformColor=this.owner.game?.catalogue?.find(c=>c.id===this.owner.career)?.color||'#8ba77a',key=this.characterTexture('iso-person-'+seed,look,gender,'se',uniformColor),f=px(p),image=this.add.image(f.x,f.y,key).setOrigin(.5,1).setScale(CHARACTER_SCALE).setDepth(f.y);this.staticObjects.push(image);this.npcArt.push({image,look,gender,uniformColor,texture:key,seed});
    this.navigation.obstacles.push({x0:p.x-.27,y0:p.y-.2,x1:p.x+.27,y1:p.y+.2});const approach=nearestWalkable(this.navigation,{x:p.x-.6,y:p.y+.35});if(!approach)return;
    const h:Hotspot={id,label,...p,approach,point:f,z:100,range:42};this.owner.hotspots.push(h);this.hits.push({hotspot:h,rect:new Phaser.Geom.Rectangle(f.x-38,f.y-108,76,118)});const tag=this.label(label,f.x,f.y-119,12,136,0x879771);tag.setDepth(f.y+.4);
  }
  refreshPlayer(walkFrame=0){
    const F=figure(this.owner.state),uniformColor=this.owner.mode==='work'?this.owner.game?.catalogue?.find(c=>c.id===this.owner.career)?.color||'#8ba77a':'#8ba77a',key=this.characterTexture('iso-player',F.L,F.g||'none',this.owner.direction,uniformColor,walkFrame);this.actorDirection=this.owner.direction;this.actorWalkFrame=walkFrame;
    if(key===this.actorKey)return false;this.actor?.destroy();this.actor=this.add.image(0,0,key).setOrigin(.5,1).setScale(CHARACTER_SCALE);if(this.actorKey&&this.textures.exists(this.actorKey))this.textures.remove(this.actorKey);this.actorKey=key;return true;
  }
  positionPlayer(moving:boolean){const walkFrame=moving&&!this.owner.reduced?1+Math.floor(this.owner.time*7)%2:0;if(this.actorDirection!==this.owner.direction||this.actorWalkFrame!==walkFrame)this.refreshPlayer(walkFrame);if(!this.actor)return;const f=px(this.owner.player);this.actor.setPosition(f.x,f.y).setDepth(f.y+.5);if(this.speech){const target=this.speechTarget?this.owner.hotspots.find(h=>h.id===this.speechTarget):null,at=target?px(target,138):{x:f.x,y:f.y-138};this.speech.setPosition(at.x,at.y);} }
  hitTest(point:Point){const ground=unproject(point),hits=this.hits.filter(h=>h.rect?.contains(point.x,point.y)||h.footprint&&inside(ground,h.footprint)||h.object?.visible&&h.object.getBounds().contains(point.x,point.y)).sort((a,b)=>b.hotspot.point.y-a.hotspot.point.y);return hits[0]?.hotspot;}
  highlight(id:string){
    this.selected?.destroy();const h=this.owner.hotspots.find(h=>h.id===id);if(!h)return;const f=px(h.approach),key='illustrated-selection';this.textureObject(key,160,80,ctx=>{ctx.strokeStyle='#f7d391';ctx.lineWidth=7;ctx.beginPath();ctx.ellipse(80,40,65,27,0,0,Math.PI*2);ctx.stroke();ctx.strokeStyle='#aa875a';ctx.lineWidth=1;ctx.beginPath();ctx.ellipse(80,40,69,31,0,0,Math.PI*2);ctx.stroke();});this.selected=this.add.image(f.x,f.y,key).setScale(.5).setDepth(f.y-1);this.requestRender();
  }
  mark(p:Point){this.marker?.destroy();const f=px(p),key='illustrated-marker';this.textureObject(key,80,40,ctx=>{ctx.fillStyle='#a48763';ctx.beginPath();ctx.ellipse(40,20,25,12,0,0,Math.PI*2);ctx.fill();ctx.fillStyle='#f6d89b';ctx.beginPath();ctx.ellipse(40,18,21,9,0,0,Math.PI*2);ctx.fill();});this.marker=this.add.image(f.x,f.y,key).setScale(.5).setDepth(f.y-.1);this.requestRender();}
  say(text:string,npc:string|null){
    this.clearSpeech();const target=npc?this.owner.hotspots.find(h=>h.id==='npc:'+npc||npc==='event'&&h.id==='event'):null;this.speechTarget=target?.id||null;const at=px(target||this.owner.player,138),label=this.add.text(0,0,text,{fontFamily:FONT,fontSize:'15px',color:'#654a39',wordWrap:{width:240},lineSpacing:4,align:'center'}).setOrigin(.5,.5),w=label.width+28,h=label.height+24,bg=this.add.graphics();bg.fillStyle(0xc8ab86);bg.fillRoundedRect(-w/2-2,-h/2-2,w+4,h+4,13);bg.fillStyle(COLORS.cream);bg.fillRoundedRect(-w/2,-h/2,w,h,11);bg.fillTriangle(-8,h/2-1,8,h/2-1,0,h/2+13);this.speech=this.add.container(at.x,at.y,[bg,label]).setDepth(20000);this.requestRender();
  }
  clearSpeech(){this.speech?.destroy();this.speech=undefined;this.speechTarget=null;}
  celebrate(pet=false){if(this.owner.reduced)return;const at=px(this.owner.player,80);for(let i=0;i<(pet?5:14);i++){const p=this.add.rectangle(at.x,at.y,4+i%3*2,4+i%3*2,[0xe1b88c,0xc78262,0x93ad7a,0xe0c882][i%4]).setDepth(15000);this.effects.push(p);this.tweens.add({targets:p,x:at.x+Math.sin(i*1.7)*70,y:at.y-35-Math.cos(i*2)*60,alpha:0,scale:.3,duration:700+i%3*100,onComplete:()=>{p.destroy();this.effects=this.effects.filter(e=>e!==p);}});}this.requestRender();}
  refreshFx(canvas:HTMLCanvasElement){if(!this.fxTexture){this.fxTexture=this.textures.addCanvas('iso-live-fx',canvas)!;this.fxTexture.setFilter(Phaser.Textures.FilterMode.LINEAR);this.fxImage=this.add.image(-850,-250,'iso-live-fx').setOrigin(0,0).setScale(2).setDepth(11000);}this.fxTexture.refresh();this.fxImage!.setVisible(this.owner.mode==='work');}
}

// Pure continuous navigation checks are shared with the regression suite.
import {lineClear as findClear} from './model';

/** Small missing props use shaded, smooth drawings; illustrated sprites take precedence. */
function drawIllustratedDetail(c:CanvasRenderingContext2D,kind:string,variant:string){
  c.scale(c.canvas.width/384,c.canvas.height/384);
  const ellipse=(x:number,y:number,rx:number,ry:number,fill:string|CanvasGradient,stroke?:string)=>{c.beginPath();c.ellipse(x,y,rx,ry,0,0,Math.PI*2);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=2;c.stroke();}};
  const shape=(points:number[][],fill:string|CanvasGradient,stroke='#88674a')=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.closePath();c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=3;c.lineJoin='round';c.stroke();}};
  const round=(x:number,y:number,w:number,h:number,r:number,fill:string|CanvasGradient,stroke?:string)=>{c.beginPath();c.roundRect(x,y,w,h,r);c.fillStyle=fill;c.fill();if(stroke){c.strokeStyle=stroke;c.lineWidth=3;c.stroke();}};
  const line=(points:number[][],stroke:string,width=3)=>{c.beginPath();points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.strokeStyle=stroke;c.lineWidth=width;c.lineCap='round';c.lineJoin='round';c.stroke();};
  const gradient=(top:string,bottom:string)=>{const g=c.createLinearGradient(40,30,310,380);g.addColorStop(0,top);g.addColorStop(1,bottom);return g;};
  const wood=gradient('#d5ab77','#8d613e'),paper=gradient('#fff5da','#e0c594');
  ellipse(192,369,118,14,'#665b4021');
  if(kind==='plant'||kind==='tree'){
    shape([[128,266],[256,266],[239,367],[146,367]],gradient('#e2c299','#aa805a'));ellipse(192,266,66,20,'#f0d5af','#a17b55');ellipse(192,265,56,14,'#705941');
    for(let i=0;i<13;i++){const angle=i*2.4,base=125+i%4*20,x=192+Math.sin(angle)*(45+i%3*25),y=110+Math.cos(angle)*75;line([[192,275],[192+Math.sin(angle)*27,base+37],[x,y]],'#698258',5);c.save();c.translate(x,y);c.rotate(angle);ellipse(0,0,15+i%3*3,37,gradient(i%2?'#b0bd77':'#8aaa6b','#4f7a53'),'#698254');line([[0,-27],[0,25]],'#bdd295',1.7);c.restore();}
    for(const [x,y] of [[168,311],[210,322],[191,340]]){ellipse(x,y,6,6,'#8fa68a');ellipse(x+7,y,5,5,'#a8ba9c');}return;
  }
  if(kind==='pond'||kind==='pool'){
    if(kind==='pool'){shape([[23,233],[200,125],[365,217],[192,373]],'#e7d5b6');shape([[43,239],[202,146],[342,219],[190,350]],'#94bcb5');shape([[53,234],[202,158],[329,220],[190,335]],gradient('#c2d6c0','#71a4a0'),'#81aaa0');for(let i=0;i<5;i++)line([[87+i*31,218-i*7],[231+i*20,284-i*10]],'#e9f1d5',2);line([[294,205],[294,170],[276,161],[264,169],[264,190]],'#f3eee0',7);}
    else{ellipse(191,279,171,91,'#8ca87b','#718f66');ellipse(191,264,157,78,gradient('#bad5b9','#74aba3'),'#b7c9a0');for(let i=0;i<24;i++){const a=i*.58,x=192+Math.cos(a)*164,y=277+Math.sin(a)*87;ellipse(x,y,10+i%3*4,6+i%2*3,gradient('#d0cfaa','#8f9e81'),'#a9b494');}ellipse(111,258,19,8,'#8caa72');ellipse(151,285,16,7,'#9ab57f');ellipse(132,256,5,3,'#e5c6bd');}
    for(let i=0;i<9;i++){const x=97+i*21,y=220+Math.sin(i*1.9)*35;line([[x,y],[x+21,y+1],[x+31,y]],'#e1efda85',2);}return;
  }
  if(kind==='boat'){
    ellipse(189,311,179,68,gradient('#b7d2c4','#7bada5'));shape([[56,265],[278,241],[344,294],[121,354]],wood);for(let i=0;i<7;i++)line([[77+i*32,273-i*3],[123+i*32,341-i*8]],'#735237',3);
    c.beginPath();c.moveTo(96,199);c.quadraticCurveTo(174,291,299,205);c.quadraticCurveTo(257,319,96,199);c.fillStyle=gradient('#cd9868','#7d5439');c.fill();c.strokeStyle='#7b573f';c.lineWidth=4;c.stroke();ellipse(195,218,78,18,'#e2bb87','#946b45');line([[130,226],[251,200]],'#8b643e',12);line([[176,197],[282,277]],'#b89260',8);return;
  }
  if(kind==='window'){
    round(44,46,296,302,10,wood,'#876347');round(67,70,249,248,5,gradient('#d7e7cd','#92b5a0'),'#715b43');line([[191,72],[191,317]],'#9d784f',13);line([[69,192],[314,192]],'#9d784f',13);line([[80,82],[82,304]],'#f3ead18c',4);line([[98,107],[156,88]],'#f7f2df9c',13);round(29,333,329,33,7,paper,'#9b784c');return;
  }
  if(kind==='lamp'||kind==='light'){
    ellipse(193,370,66,13,'#a68a5c');round(181,96,22,274,10,wood,'#76583d');c.beginPath();c.moveTo(188,113);c.bezierCurveTo(184,44,309,37,311,113);c.strokeStyle='#73947d';c.lineWidth=16;c.stroke();shape([[271,109],[348,109],[359,179],[258,179]],gradient('#d9e0b5','#648b72'),'#57765e');ellipse(308,180,50,17,'#f4e4ab','#6e8870');return;
  }
  if(kind==='cat'){
    c.save();c.translate(190,275);ellipse(0,34,92,49,gradient('#d4b689','#ac855f'),'#9a7855');ellipse(-32,-23,64,61,gradient('#e4c999','#b89269'),'#9a7855');shape([[-89,-58],[-78,-103],[-52,-68]],'#d4b18a');shape([[-12,-72],[23,-99],[23,-43]],'#d4b18a');ellipse(-55,-26,6,10,'#5e5942');ellipse(-15,-26,6,10,'#5e5942');ellipse(-35,-3,5,3,'#b98778');line([[-36,1],[-43,8],[-52,7]],'#795b45',2);line([[-5,7],[43,0]],'#d9c7a5',2);c.beginPath();c.moveTo(80,48);c.bezierCurveTo(124,46,134,-12,95,-7);c.strokeStyle='#ba976b';c.lineWidth=23;c.stroke();c.restore();return;
  }
  if(kind==='cup'){
    round(86,168,195,169,32,paper,'#ac8d66');c.beginPath();c.ellipse(278,239,47,54,0,-1.4,1.4);c.strokeStyle='#ccb38a';c.lineWidth=15;c.stroke();ellipse(183,165,99,29,'#efd6a5','#a98a62');ellipse(183,164,84,20,variant==='1'?'#805d48':'#c19e70');line([[128,211],[128,307]],'#fff8e3',8);return;
  }
  if(kind==='bread'){
    c.save();c.translate(190,248);c.rotate(-.24);ellipse(0,0,158,85,gradient('#edc47d','#b87941'),'#a97343');for(let x=-80;x<=90;x+=52){c.beginPath();c.moveTo(x-10,-46);c.quadraticCurveTo(x+10,-13,x+23,27);c.strokeStyle='#f5d8a2';c.lineWidth=19;c.stroke();}c.restore();return;
  }
  if(kind==='camera'){round(53,102,249,116,18,gradient('#d2dbc0','#779885'),'#6c8170');ellipse(281,161,44,43,'#566b61','#d7ddbf');ellipse(281,161,29,28,'#93bcb6','#405e55');line([[155,218],[155,321],[94,337]],'#9b7954',19);return;}
  if(kind==='bell'){c.beginPath();c.moveTo(86,296);c.bezierCurveTo(139,259,102,108,191,106);c.bezierCurveTo(281,108,245,259,297,296);c.closePath();c.fillStyle=gradient('#efd08d','#b2925b');c.fill();c.strokeStyle='#a78752';c.lineWidth=4;c.stroke();ellipse(191,294,105,24,'#dcc088','#a78752');ellipse(191,326,20,25,'#b79a68');round(180,76,22,33,7,'#c0a775');return;}
  if(kind==='lock'){round(106,59,168,200,68,gradient('#e1d3a4','#a1946e'),'#9c9068');round(132,92,116,169,43,'#ede4c6');round(85,207,213,137,18,gradient('#e9c47d','#baa261'),'#998250');ellipse(191,255,11,13,'#806c43');round(187,260,9,25,3,'#806c43');return;}
  if(kind==='door'){round(65,31,254,340,11,wood,'#72573e');round(88,55,205,276,7,paper,'#9b784e');for(const y of [88,187])round(111,y,158,71,4,'#e9d0a6','#bb986a');ellipse(274,219,8,9,'#a08c57');return;}
  if(kind==='bench'){line([[76,219],[76,354]],'#8b6845',13);line([[289,217],[289,353]],'#8b6845',13);for(let i=0;i<4;i++)round(52,98+i*36,282,28,7,wood,'#927048');round(41,257,301,49,8,wood,'#927048');return;}
  if(kind==='shelf'||kind==='counter'||kind==='desk'||kind==='crates'){round(37,91,310,267,14,wood,'#8a6749');for(let i=0;i<3;i++){round(57,123+i*71,268,58,5,paper,'#9c7852');for(let j=0;j<5;j++)round(74+j*48,134+i*71,31,39,5,gradient(j%2?'#b6c098':'#dfb28f','#9d8860'),'#a89671');}return;}
  round(76,62,232,290,14,wood,'#8d6848');round(93,81,198,249,7,paper,'#b7946c');
  if(kind==='security'){shape([[122,127],[192,103],[261,128],[247,229],[192,270],[138,229]],gradient('#adc8a1','#73977b'));line([[155,180],[181,210],[232,149]],'#fff0bd',11);}
  else if(kind==='property'){shape([[119,170],[192,110],[270,170]],'#b67d56');round(138,174,111,102,4,'#c7d7b4','#91a082');round(181,217,29,60,3,'#89a789');}
  else if(kind==='poster'){round(116,110,152,186,4,'#a7bea2');shape([[116,271],[177,187],[268,272]],'#719679');ellipse(230,149,17,17,'#ead298');}
  else if(kind==='check')line([[136,210],[175,244],[247,153]],'#7d9e78',15);
  else if(kind==='repair'){round(181,126,19,100,8,'#b0875c');ellipse(190,261,12,12,'#b0875c');}
  else if(kind.startsWith('gear-')){round(121,173,144,99,12,'#a2b99e','#72927b');for(let i=0;i<Number(kind.slice(-1));i++)ellipse(147+i*36,225,11,11,'#ead095');}
  else{line([[194,117],[194,289]],'#ceb899',2);for(let y=137;y<284;y+=29){line([[119,y],[176,y]],'#b2a17e',3);line([[214,y],[267,y]],'#b2a17e',3);}}
}
