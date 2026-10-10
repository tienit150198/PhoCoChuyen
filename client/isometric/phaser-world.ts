import Phaser from 'phaser';
import {installPerformanceProbe} from './performance-probe';
import {SpatialIndex,coversPlayer,fadeAlpha} from './visibility';
import type {AlphaMask,OccludingShape} from './visibility';
// These are the game's existing wardrobe and scene vocabulary, shipped beside this bundle.
// @ts-ignore JavaScript public modules are intentionally runtime imports.
import {figure,defaultLook} from '/js/v4/look.js';
// @ts-ignore The illustrated atlas adapter preserves the game's actual wardrobe.
import {getCharacterStamp,preloadIllustratedCharacters} from '/js/isometric/character-art.js';
// @ts-ignore The catalogue scene family mapping remains the source of truth.
import {kindOf,wordsFor} from '/js/scenes/vocabulary.js';
import {activeTasks,advanceRoute,CAMERA_ZOOM,canvasDescription,cameraWorldPoint,defaultCamera,effectFrameState,findRoute,followCamera,gestureIsDrag,groundCacheRegion,inside,interpolateRoute,isWalkable,landmarkPlaneGeometry,landmarkSpritePlacement,makeNavigation,moveOnGround,nearestReachableHotspot,nearestWalkable,normalizeMovementInput,presenceDirection,project,publicTownPlayers,resizedCamera,roomAppearance,townBuildingArt,townBuildings,townGarden,townLandmarks,townNavigation,townRoads,unproject,WORK_FOOD_SHELF,WORK_WINDOW,workWindowAnchors} from './model';
import type {Building,Career,Facing,Navigation,Point,Rect,RemotePlayer,RoomAppearance} from './model';
import {insideIsland,islandCoastline,islandOverviewCamera,SEA_COLOR,TOWN_ZOOM} from './island';
import {TextureFrames} from './texture-frames';
import {facadeTextLines,FACADE_SIGNS} from './building-art';
import {ISOMETRIC_ASSETS as ASSETS} from './asset-manifest';
import {careerFacadeTextureKey,careerFacadeSize,drawCareerFacade} from './career-facade';
import {StaticLodCache} from './static-lod';
import {wayfindingMount} from './sign-placement';
import {CIVIC_ASSETS,CIVIC_FACADES,amenityPlacement} from './amenity-art';
import type {AmenityArt} from './amenity-art';
import {walkingPose} from './model';
import {townDistricts,townAmenities,townTrails,townScenery,townShopLots} from './model';
import {drawNeighbourhoodGround,drawCivicProp} from './town-scenery';
import {workActorPositions,workEventAnchors,workLayout,workNavigation} from './work-layout';
import type {WorkFixture} from './work-layout';
import {drawWorkArchitecture,workFurnitureElevation} from './work-architecture';
import type {ArchitectureInk} from './work-architecture';

export type WorldMode = 'town' | 'work';
type StaticVisual=Phaser.GameObjects.Image|Phaser.GameObjects.Text|Phaser.GameObjects.Container;
type Occluder=OccludingShape&{image:Phaser.GameObjects.Image;sign?:Phaser.GameObjects.Container;alpha:number;target:number};
interface Hotspot extends Point {id:string;label:string;approach:Point;interactionPoint?:Point;point:Point;z:number;range:number}
type PublicState = {current?:string;focus?:string;careers?:Record<string,any>;journey?:any;settings?:any;[key:string]:any};
type Content = {catalogue?:Career[];npcs?:any[];[key:string]:any};
const FONT='"Be Vietnam Pro", "Segoe UI", sans-serif';
const COLORS={grass:0xb6c598,grassLight:0xc2cda8,road:0xe7d3b5,edge:0xc5ac89,ink:0x6e5141,cream:0xfff3da,roof:0xb86c4e,sage:0x8ba77a,water:0x98bfb8};
const asHex=(s:string|undefined,fallback=COLORS.sage)=>s&&/^#[0-9a-f]{6}$/i.test(s)?parseInt(s.slice(1),16):fallback;
const px=(p:Point,z=0):Point=>{const q=project(p);return {x:q.x,y:q.y-z};};
const noOp=()=>{};
const CHARACTER_SCALE=.65;
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
  treasure:Array<Point&{id:string}>=[];
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
  walkDistance=0;
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
  residentShops:Array<{id:string;name:string;kind?:string;target?:string;ownerName?:string;career?:string}>=[];
  townDistricts(){return townDistricts();}
  townAmenities(){return townAmenities();}
  focusDistrict(id:string){
    const d=townDistricts().find(d=>d.id===id);if(!d||this.mode!=='town'||!this.stage)return false;
    const p=px({x:(d.bounds.x0+d.bounds.x1)/2,y:(d.bounds.y0+d.bounds.y1)/2},90),zoom=this.width<=620?.44:.62;
    this.stage.browseCamera();this.stage.cameras.main.setZoom(zoom).setScroll(p.x-this.width/2,p.y-this.height/2);this.stage.requestRender();this.wake();return true;
  }
  setResidentShops(value:unknown){
    const seen=new Set<string>(),shops=Array.isArray(value)?value.filter(s=>s&&typeof s.id==='string'&&s.id.length<=160&&!seen.has(s.id)&&(seen.add(s.id),true)).slice(0,8).map(s=>({id:s.id,name:String(s.name||'Quán hàng xóm').slice(0,80),kind:s.kind,target:s.target,ownerName:String(s.ownerName||'').slice(0,24),career:s.career})):[];
    if(JSON.stringify(shops)===JSON.stringify(this.residentShops))return;this.residentShops=shops;if(this.mode==='town'){this.stage?.refreshResidentShops();this.wake();}
  }

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
    if(new URLSearchParams(location.search).has('isometricdebug')){(window as any).__isoWorld=this;this.listeners.push(installPerformanceProbe(this.engine,canvas,()=>this.debug()));}
  }
  private listen(target:EventTarget,event:string,handler:EventListener,options?:AddEventListenerOptions|boolean){target.addEventListener(event,handler,options);this.listeners.push(()=>target.removeEventListener(event,handler,options));}
  get paused(){return this._paused;}
  get cameraMode(){return this.stage?.cameraMode||'follow';}
  set paused(value:boolean){this._paused=!!value;if(this._paused){this.clearMovementControls();this.pointers.clear();this.pinch=null;}this.wake();}
  setMovementInput(x:number,y:number){this.movementInput=this.shouldSleep()||!!document.querySelector('dialog[open]')?{x:0,y:0}:normalizeMovementInput(x,y);this.wake();}
  getPresence(){return this.mode==='town'?{x:this.player.x,y:this.player.y,direction:this.direction}:null;}
  correctPresence(at:Point){if(this.mode!=='town'||!this.stage||!isWalkable(this.stage.navigation,at))return;Object.assign(this.player,at,{path:[],goal:null});this.pending=null;this.stage.positionPlayer(false);if(this.cameraMode==='follow')this.recenter();this.wake();}
  setTreasure(value:unknown){
    const rows=Array.isArray(value)?value.filter(c=>c&&typeof c.id==='string'&&Number.isFinite(c.x)&&Number.isFinite(c.y)).slice(0,5).map(c=>({id:c.id,x:c.x,y:c.y})):[];
    if(JSON.stringify(rows)===JSON.stringify(this.treasure))return;this.treasure=rows;this.stage?.syncTreasure();this.wake();
  }
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
    const anchors=workEventAnchors(this.hotspots);
    return {spots,customers:[point({x:7.7,y:5.8}),point({x:8,y:7}),point({x:5.9,y:7.1}),point({x:4.8,y:7})],home:point({x:6.5,y:6}),floor:[-640,0,640,600],blocks:[],kx:64,ky:32,
      anchors};
  }
  resize(){
    if(this.destroyed)return;
    const r=this.canvas.parentElement?.getBoundingClientRect()||this.canvas.getBoundingClientRect(),w=Math.max(1,Math.round(r.width)),h=Math.max(1,Math.round(r.height));
    // ResizeObserver can update owner dimensions while Phaser is still preloading.
    // Once its scene exists, the bitmap must catch up even if CSS size is unchanged.
    const surfaceMatches=this.canvas.width===w&&this.canvas.height===h&&this.engine.scale.width===w&&this.engine.scale.height===h;
    if(!r.width||!r.height||w===this.width&&h===this.height&&surfaceMatches)return;
    const camera=this.stage?.cameras.main;
    // A manual view keeps its world center and chosen zoom, including when the
    // viewport crosses the phone breakpoint. Following keeps the usual fit.
    const next=camera?this.stage?.islandOverview?islandOverviewCamera(w,h):this.stage?.cameraMode==='browse'?
      {scrollX:camera.scrollX+(this.width-w)/2,scrollY:camera.scrollY+(this.height-h)/2,zoom:camera.zoom}:
      resizedCamera(this.mode,{width:this.width,height:this.height,scrollX:camera.scrollX,scrollY:camera.scrollY,zoom:camera.zoom},w,h):null;
    this.width=w;this.height=h;
    if(this.stage&&camera){this.engine.scale.resize(w,h);camera.setSize(w,h);if(!this.stage.cameraSet)this.resetCamera();else if(next)camera.setScroll(next.scrollX,next.scrollY).setZoom(next.zoom);}
    this.wake();
  }
  resetCamera(){this.stage?.resetCamera();this.wake();}
  recenter(){this.resetCamera();}
  overviewIsland(){this.setMode('town');this.clearMovementControls();this.player.path=[];this.player.goal=null;this.pending=null;this.stage?.overviewIsland();this.wake();}
  overview(){this.overviewIsland();}
  focusCareer(id:string){this.setMode('town');const building=this.stage?.buildings.find(b=>b.id===id);if(building){this.stage!.browseCamera();const p=px(building.at,65),view=defaultCamera(this.mode,this.width,this.height);this.stage!.cameras.main.setZoom(view.zoom).centerOn(p.x,p.y);this.stage!.highlight('career:'+id);this.wake();}}
  private zoomRange(){return this.mode==='town'?TOWN_ZOOM:CAMERA_ZOOM;}
  setZoom(value:number){const camera=this.stage?.cameras.main;if(camera&&this.stage){this.stage.browseCamera();const range=this.zoomRange();camera.setZoom(Phaser.Math.Clamp(value,range.min,range.max));this.wake();}}
  zoomBy(factor:number){this.setZoom((this.stage?.cameras.main.zoom||1)*factor);}
  debug(){return {mode:this.mode,career:this.career,cameraMode:this.cameraMode,paused:this.paused,movementInput:{...this.movementInput},remotePlayers:this.remotePlayers.length,loopRunning:this.engine.loop.running,loopSleeping:!this.engine.loop.running,hidden:document.hidden,covered:!!document.querySelector('dialog[open]:not(.drawer)'),visible:this.visible,paths:this.player.path.length,hotspots:this.hotspots.length,sceneActive:this.stage?.sys.isActive(),sceneChildren:this.stage?.children.length,groundTextures:this.engine.textures.exists('iso-ground'),occluded:this.stage?.occludedCount||0,player:{x:this.player.x,y:this.player.y},camera:this.stage?{x:this.stage.cameras.main.scrollX,y:this.stage.cameras.main.scrollY,zoom:this.stage.cameras.main.zoom}:null};}
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
    let moving=false;const before={x:this.player.x,y:this.player.y};
    if(this.keys.size||this.movementInput.x||this.movementInput.y){let sx=this.movementInput.x,sy=this.movementInput.y;if(this.keys.has('a')||this.keys.has('arrowleft'))sx--;if(this.keys.has('d')||this.keys.has('arrowright'))sx++;if(this.keys.has('w')||this.keys.has('arrowup'))sy--;if(this.keys.has('s')||this.keys.has('arrowdown'))sy++;
      const next=moveOnGround(stage.navigation,this.player,normalizeMovementInput(sx,sy),dt);this.player.path=[];this.player.goal=null;this.pending=null;moving=Math.hypot(next.x-this.player.x,next.y-this.player.y)>1e-8;Object.assign(this.player,next);
    }else if(this.player.path.length){const next=advanceRoute(this.player,this.player.path,170*dt,'screen',stage.navigation);Object.assign(this.player,next.point);this.player.path=next.path;moving=true;if(next.arrived){this.player.goal=null;const cb=this.pending;this.pending=null;cb?.();}}
    if(moving&&stage.cameraMode==='follow'){const camera=stage.cameras.main,view=followCamera({width:this.width,height:this.height,scrollX:camera.scrollX,scrollY:camera.scrollY,zoom:camera.zoom},px(this.player,55),dt);camera.setScroll(view.scrollX,view.scrollY);}
    if(moving){this.direction=presenceDirection(before,this.player,this.direction);const delta=project({x:this.player.x-before.x,y:this.player.y-before.y});this.walkDistance+=Math.hypot(delta.x,delta.y);}
    stage.positionPlayer(moving);
    const fading=stage.updateOcclusion(dt);
    const remoteMoving=stage.stepRemotePlayers(this.time);
    const ev=this._fx?.ev,effect=effectFrameState(ev,this.time,this.reduced);
    if(effect.clear){this._fx?.clear?.();this.paintFx();}
    else if(this.mode==='work'&&this._fx&&(effect.needsFrames||stage.renderRequested||this.time-this.fxPaintAt>.2&&ev?.end!=null)){this.paintFx();}
    // Phaser advances its pending image queue on Scene UPDATE, even while the view is still.
    const active=fading||moving||remoteMoving||this.keys.size>0||!!(this.movementInput.x||this.movementInput.y)||this.pointers.size>0||effect.needsFrames||stage.hasEffects()||stage.load.isLoading();
    if(!active&&stage.settle())this.engine.loop.sleep();
  }
  private paintFx(){const ctx=this.fxContext;ctx.setTransform(1,0,0,1,0,0);ctx.clearRect(0,0,this.fxCanvas.width,this.fxCanvas.height);ctx.setTransform(.5,0,0,.5,425,125);this._fx?.draw?.(this);this.fxPaintAt=this.time;this.stage?.refreshFx(this.fxCanvas);}
  private local(e:PointerEvent|WheelEvent):Point{const r=this.canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
  private worldPoint(p:Point):Point{return cameraWorldPoint(p,this.stage!.cameras.main);}
  private pointerDown=(e:PointerEvent)=>{if(this._paused||!this.stage)return;e.preventDefault();this.canvas.focus({preventScroll:true});this.canvas.setPointerCapture?.(e.pointerId);const p=this.local(e);this.pointers.set(e.pointerId,{start:p,last:p,drag:false});this.lastInput=this.time;if(this.pointers.size===2){this.stage.browseCamera();const pts=[...this.pointers.values()].map(p=>p.last),mid={x:(pts[0].x+pts[1].x)/2,y:(pts[0].y+pts[1].y)/2};this.pinch={distance:Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y),zoom:this.stage.cameras.main.zoom,world:this.worldPoint(mid)};for(const p of this.pointers.values())p.drag=true;}this.wake();};
  private pointerMove=(e:PointerEvent)=>{const pointer=this.pointers.get(e.pointerId);if(!pointer||!this.stage)return;const p=this.local(e),old=pointer.last;pointer.last=p;
    if(this.pointers.size>=2&&this.pinch){this.stage.browseCamera();const pts=[...this.pointers.values()].map(p=>p.last),mid={x:(pts[0].x+pts[1].x)/2,y:(pts[0].y+pts[1].y)/2},dist=Math.hypot(pts[1].x-pts[0].x,pts[1].y-pts[0].y),range=this.zoomRange();this.stage.cameras.main.setZoom(Phaser.Math.Clamp(this.pinch.zoom*dist/Math.max(1,this.pinch.distance),range.min,range.max));const after=this.worldPoint(mid);this.stage.cameras.main.scrollX+=this.pinch.world.x-after.x;this.stage.cameras.main.scrollY+=this.pinch.world.y-after.y;
    }else if(pointer.drag||gestureIsDrag(pointer.start,p)){this.stage.browseCamera();pointer.drag=true;this.stage.cameras.main.scrollX-=(p.x-old.x)/this.stage.cameras.main.zoom;this.stage.cameras.main.scrollY-=(p.y-old.y)/this.stage.cameras.main.zoom;this.canvas.style.cursor='grabbing';}this.lastInput=this.time;this.wake();};
  private pointerUp=(e:PointerEvent)=>{const pointer=this.pointers.get(e.pointerId);this.pointers.delete(e.pointerId);this.pinch=null;this.canvas.style.cursor='grab';if(pointer&&!pointer.drag&&!gestureIsDrag(pointer.start,this.local(e))&&!this._paused&&this.stage)this.tap(this.worldPoint(this.local(e)));this.wake();};
  private pointerCancel=(e:PointerEvent)=>{this.pointers.delete(e.pointerId);this.pinch=null;this.canvas.style.cursor='grab';this.wake();};
  private wheel=(e:WheelEvent)=>{if(!this.stage||this._paused)return;e.preventDefault();this.stage.browseCamera();const p=this.local(e),before=this.worldPoint(p),camera=this.stage.cameras.main,range=this.zoomRange();camera.setZoom(Phaser.Math.Clamp(camera.zoom*Math.exp(-e.deltaY*.0013),range.min,range.max));const after=this.worldPoint(p);camera.scrollX+=before.x-after.x;camera.scrollY+=before.y-after.y;this.lastInput=this.time;this.wake();};
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
  cameraMode:'follow'|'browse'='follow';
  private _islandOverview=false;
  get islandOverview(){return this._islandOverview;}
  set islandOverview(value:boolean){this._islandOverview=value;const stage=this.owner.canvas.closest<HTMLElement>('#stage');if(stage)stage.dataset.islandOverview=value?'true':'false';}
  renderRequested=true;
  private settledFrames=0;
  private staticIndex=new SpatialIndex<StaticVisual>(384);
  private shownStatics=new Set<StaticVisual>();
  private visibilityView='';
  private staticLod=new StaticLodCache({maxEntries:1024});
  private lodTextures=new Set<string>();
  private originalFrames=new WeakMap<Phaser.GameObjects.Image,Phaser.Textures.Frame>();
  private signZoom=-1;
  private occluderIndex=new SpatialIndex<Occluder>();
  private occluders:Occluder[]=[];
  private fadingOccluders=new Set<Occluder>();
  private alphaMasks=new Map<string,AlphaMask>();
  private occlusionPosition='';
  occludedCount=0;
  private actorRing?:Phaser.GameObjects.Image;
  private actor?:Phaser.GameObjects.Image;
  private actorKey='';
  private actorDirection:Facing='se';
  private actorWalkFrame=0;
  private background?:Phaser.GameObjects.Graphics;
  private terrainChunks=new Map<string,{graphics:Phaser.GameObjects.Graphics;bounds:Rect}>();
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
  private hits:Array<{hotspot:Hotspot;rect?:Phaser.Geom.Rectangle;object?:Phaser.GameObjects.Container|Phaser.GameObjects.Image;footprint?:Rect}>=[];
  private placards:Array<{tag:Phaser.GameObjects.Container;size:number;mounted?:boolean}>=[];
  private signMounts=new Map<Phaser.GameObjects.Container,Point>();
  private selected?:Phaser.GameObjects.Image;
  private imageById=new Map<string,Phaser.GameObjects.Image>();
  private treasureObjects:Phaser.GameObjects.Container[]=[];
  private previousMode:WorldMode|null=null;
  private previousCareer='';
  private remoteActors=new Map<string,{peer:RemotePlayer;at:Point;from:Point;path:Point[];started:number;image:Phaser.GameObjects.Image;tag:Phaser.GameObjects.Text;texture:string}>();
  private npcArt:Array<{image:Phaser.GameObjects.Image;look:any;gender:string;uniformColor:string;texture:string;seed:number}>=[];
  private requestedAssets=new Set<string>();
  private assetWakeQueued=false;
  private artRefreshQueued=false;
  private characterRevision=0;
  private characterFrames=new TextureFrames(key=>{if(this.textures.exists(key))this.textures.remove(key);});
  constructor(owner:PhaserWorld){super({key:'Diorama'});this.owner=owner;}
  preload(){this.queueAssets(['grocery','home','cafe','tree','bench']);}
  create(){this.load.on(Phaser.Loader.Events.COMPLETE,this.assetsReady);preloadIllustratedCharacters(this.charactersReady);this.events.once(Phaser.Scenes.Events.CREATE,()=>this.owner.boot(this));document.fonts?.load('700 17px "Be Vietnam Pro"','Phố Có Chuyện').then(()=>{if(this.sys.isActive())this.queueArtRefresh();}).catch(()=>{});this.events.once(Phaser.Scenes.Events.SHUTDOWN,()=>{this.characterFrames.clear();for(const key of this.lodTextures)this.textures.remove(key);this.lodTextures.clear();this.staticLod.dispose();});}
  private queueAssets(kinds:string[]){let queued=false;for(const kind of kinds){if(!ASSETS[kind]||this.textures.exists('art-'+kind)||this.requestedAssets.has(kind))continue;this.requestedAssets.add(kind);this.load.image('art-'+kind,assetURL(ASSETS[kind]));queued=true;}return queued;}
  private ensureAssets(kinds:string[]){
    if(!this.queueAssets(kinds))return;
    if(!this.load.isLoading())this.load.start();
    if(this.assetWakeQueued)return;
    this.assetWakeQueued=true;
    // Waking a sleeping Phaser loop can tick synchronously; finish rebuilding first.
    queueMicrotask(()=>{this.assetWakeQueued=false;if(this.sys.isActive())this.owner.wake();});
  }
  private assetsReady=()=>{if(!this.sys.isActive())return;this.owner['cachedPreview'].clear();this.queueArtRefresh();};
  private charactersReady=()=>{if(!this.sys.isActive())return;this.characterRevision++;this.queueArtRefresh();};
  private queueArtRefresh(){if(this.artRefreshQueued)return;this.artRefreshQueued=true;queueMicrotask(()=>{this.artRefreshQueued=false;if(!this.sys.isActive())return;this.rebuild();this.owner.wake();});}
  update(_time:number,delta:number){this.cacheGround();this.owner.step(Math.min(.06,delta/1000));this.syncStaticVisibility();}
  requestRender(){this.renderRequested=true;this.settledFrames=0;}
  settle(){if(this.renderRequested){this.renderRequested=false;this.settledFrames=0;return false;}return ++this.settledFrames>=2;}
  hasEffects(){return this.effects.length>0||this.tweens.getTweens().length>0;}
  lineClear(a:Point,b:Point){return findClear(this.navigation,a,b);}
  rebuild(){
    if(!this.sys.isActive())return;
    this.terrainChunks.clear();this.occluderIndex.clear();this.occluders=[];this.fadingOccluders.clear();this.occlusionPosition='';this.occludedCount=0;this.actorRing?.setVisible(false);this.staticIndex.clear();this.shownStatics.clear();this.visibilityView='';this.signZoom=-1;this.signMounts.clear();
    for(const object of this.staticObjects)object.destroy();this.staticObjects=[];this.residentObjects=[];for(const seed of new Set(this.npcArt.map(n=>n.seed)))this.characterFrames.release('iso-person-'+seed);this.npcArt=[];this.groundCache=undefined;this.groundRegion=undefined;this.hits=[];this.placards=[];this.imageById.clear();this.marker?.destroy();this.marker=undefined;this.selected?.destroy();this.selected=undefined;this.clearSpeech();
    const modeChanged=this.previousMode!==this.owner.mode,changed=modeChanged||this.owner.mode==='work'&&this.previousCareer!==this.owner.career;
    this.previousMode=this.owner.mode;this.previousCareer=this.owner.career;this.cameras.main.setBackgroundColor(this.owner.mode==='town'?SEA_COLOR:'#ede3ce');this.background=this.add.graphics().setDepth(-10000);this.staticObjects.push(this.background);
    if(this.owner.mode==='town')this.town();else this.work();
    if(changed||!isWalkable(this.navigation,this.owner.player)){const home=this.owner.mode==='town'?{x:6.2,y:6.2}:{x:6.4,y:6.4};const at=nearestWalkable(this.navigation,home)||home;Object.assign(this.owner.player,at,{path:[],goal:null});this.owner.pending=null;if(modeChanged||!this.cameraSet||this.cameraMode==='follow')this.resetCamera(false);}
    this.treasureObjects=[];this.syncTreasure();this.reindexStatics();this.refreshPlayer();this.positionPlayer(false);this.updateOcclusion(1/60);this.syncRemotePlayers();if(this.fxImage)this.fxImage.setVisible(this.owner.mode==='work');this.requestRender();
  }
  syncTreasure(){
    for(const object of this.treasureObjects){this.staticObjects=this.staticObjects.filter(o=>o!==object);object.destroy();}
    this.treasureObjects=[];this.hits=this.hits.filter(h=>!h.hotspot.id.startsWith('treasure:'));this.owner.hotspots=this.owner.hotspots.filter(h=>!h.id.startsWith('treasure:'));
    if(this.owner.mode==='town')for(const chest of this.owner.treasure||[]){
      if(!isWalkable(this.navigation,chest))continue;
      const at=px(chest),g=this.add.graphics();
      g.fillStyle(0x4b3225,.22).fillEllipse(0,0,58,19);
      const poly=(points:number[][],color:number)=>{g.fillStyle(color).lineStyle(2.5,0x67412a);const p=points.map(([x,y])=>new Phaser.Geom.Point(x,y));g.fillPoints(p,true).strokePoints(p,true);};
      poly([[-26,-27],[7,-34],[28,-23],[-6,-15]],0xeec371);
      poly([[-26,-27],[-6,-15],[-6,6],[-26,-6]],0x9b5b31);
      poly([[-6,-15],[28,-23],[28,-2],[-6,6]],0xbf7c36);
      g.lineStyle(5,0xf4c958).lineBetween(3,-30,3,1).lineBetween(19,-26,19,-3);
      g.fillStyle(0xffe7a0).fillRoundedRect(6,-16,9,10,2);
      const box=this.add.container(at.x,at.y,[g]).setDepth(at.y+.1).setSize(58,45);
      const h:Hotspot={id:'treasure:'+chest.id,label:'Mở rương · 10.000 xu',x:chest.x,y:chest.y,z:0,point:at,approach:chest,range:1.2};
      this.owner.hotspots.push(h);this.hits.push({hotspot:h,object:box,footprint:{x0:chest.x-.3,x1:chest.x+.3,y0:chest.y-.3,y1:chest.y+.3}});this.staticObjects.push(box);this.treasureObjects.push(box);
    }
    this.reindexStatics();this.requestRender();
  }
  /** Cache only the visible ground plus a pan margin, avoiding a giant whole-map bitmap. */
  private cacheGround(){
    if(!this.background)return;
    const camera=this.cameras.main,cx=camera.scrollX+camera.width/2,cy=camera.scrollY+camera.height/2,halfW=camera.width/camera.zoom/2,halfH=camera.height/camera.zoom/2;
    if(this.owner.mode==='town'&&this.signZoom!==camera.zoom){
      this.signZoom=camera.zoom;
      for(const sign of this.placards){const scale=sign.mounted?1:Phaser.Math.Clamp(10/(sign.size*camera.zoom),1,2.2);if(Math.abs(sign.tag.scaleX-scale)>.001)sign.tag.setScale(scale);}
      this.reindexStatics();
    }
    const view={x0:cx-halfW,y0:cy-halfH,x1:cx+halfW,y1:cy+halfH};
    const cache=groundCacheRegion(view,camera.zoom);
    if(this.groundRegion&&this.groundScale>=cache.scale*.9&&view.x0>=this.groundRegion.x0&&view.y0>=this.groundRegion.y0&&view.x1<=this.groundRegion.x1&&view.y1<=this.groundRegion.y1)return;
    const region=cache.region,canvas=document.createElement('canvas');canvas.width=cache.width;canvas.height=cache.height;
    const cacheCamera=new Phaser.Cameras.Scene2D.Camera(0,0,canvas.width,canvas.height);cacheCamera.setScene(this).setScroll(cache.scroll.x,cache.scroll.y).setZoom(cache.scale);cacheCamera.preRender();
    this.background.setVisible(true);
    // Phaser's public graphics Canvas compositor accepts an explicit context and camera.
    (this.background as any).renderCanvas(this.game.renderer,this.background,cacheCamera,null,canvas.getContext('2d'),false);
    for(const {graphics,bounds} of this.terrainChunks.values()){
      if(bounds.x1<region.x0||bounds.x0>region.x1||bounds.y1<region.y0||bounds.y0>region.y1)continue;
      (graphics as any).renderCanvas(this.game.renderer,graphics,cacheCamera,null,canvas.getContext('2d'),false);
    }
    this.background.setVisible(false);cacheCamera.destroy();if(this.groundCache){const old=this.groundCache;old.destroy();this.staticObjects=this.staticObjects.filter(o=>o!==old);}if(this.textures.exists('iso-ground'))this.textures.remove('iso-ground');
    // A read-only canvas source needs no CanvasTexture pixel buffer. Avoid its full
    // getImageData readback every time the camera crosses the cached region.
    const texture=this.textures.create('iso-ground',canvas)!;texture.add('__BASE',0,0,0,canvas.width,canvas.height);texture.setFilter(Phaser.Textures.FilterMode.LINEAR);
    this.groundCache=this.add.image(region.x0,region.y0,'iso-ground').setOrigin(0,0).setScale(1/cache.scale).setDepth(-10000);this.staticObjects.push(this.groundCache);this.groundRegion=region;this.groundScale=cache.scale;this.requestRender();
  }
  browseCamera(){this.cameraMode='browse';this.islandOverview=false;}
  resetCamera(focusPlayer=true){const view=defaultCamera(this.owner.mode,this.owner.width,this.owner.height);if(focusPlayer&&this.owner.mode==='town'){const p=px(this.owner.player,55);view.scrollX=p.x-this.owner.width/2;view.scrollY=p.y-this.owner.height/2;}this.cameraMode='follow';this.islandOverview=false;this.cameras.main.setZoom(view.zoom).setScroll(view.scrollX,view.scrollY);this.cameraSet=true;this.requestRender();}
  overviewIsland(){const view=islandOverviewCamera(this.owner.width,this.owner.height);this.cameraMode='browse';this.islandOverview=true;this.cameras.main.setZoom(view.zoom).setScroll(view.scrollX,view.scrollY);this.cameraSet=true;this.requestRender();}
  private polygon(points:Point[],fill:number,alpha=1,stroke?:number,width=1){const g=this.background!;g.fillStyle(fill,alpha);g.fillPoints(points,true);if(stroke!==undefined){g.lineStyle(width,stroke,1);g.strokePoints(points,true);}}
  /** Paving and grass are baked by neighbourhood so panning does not repaint the whole island. */
  private terrainAt(p:Point){
    const x=Math.floor(p.x/7)*7,y=Math.floor(p.y/7)*7,key=x+':'+y;
    let chunk=this.terrainChunks.get(key);if(!chunk){
      const a=px({x,y}),left=px({x,y:y+7}),right=px({x:x+7,y}),bottom=px({x:x+7,y:y+7}),graphics=this.add.graphics().setVisible(false);
      chunk={graphics,bounds:{x0:left.x-100,y0:a.y-50,x1:right.x+100,y1:bottom.y+50}};this.terrainChunks.set(key,chunk);this.staticObjects.push(graphics);
    }return chunk.graphics;
  }
  private floorRect(r:Rect,color:number,alpha=1,z=0){this.polygon([px({x:r.x0,y:r.y0},z),px({x:r.x1,y:r.y0},z),px({x:r.x1,y:r.y1},z),px({x:r.x0,y:r.y1},z)],color,alpha);}
  private town(){
    this.buildings=townBuildings(this.owner.game?.catalogue||[]);this.navigation=townNavigation(this.buildings);
    this.islandGround();const ground=this.background!;
    const streetDoors=[...this.buildings.map(b=>({id:b.id,district:b.neighbourhood||'market',at:b.door})),...townShopLots().map((lot,index)=>({id:'resident-lot-'+index,district:'resident',at:lot.door}))];
    drawNeighbourhoodGround(ground,townDistricts(),townTrails(),streetDoors,this.navigation);
    this.owner.hotspots=[];
    for(const building of this.buildings){
      const foot=px(building.at);ground.fillStyle(0x7e906b,.18).fillEllipse(foot.x,foot.y-24,340,148);
      const kind=townBuildingArt(building.meta,building.variant);this.ensureAssets([kind]);const key=this.careerArt(building.id,kind,this.textures.exists('art-'+kind)?'art-'+kind:'art-'+building.variant);
      const source=this.textures.get(key).getSourceImage() as HTMLImageElement|HTMLCanvasElement;
      const width=building.neighbourhood==='garden'?375:building.neighbourhood==='office'?340:355;
      const image=this.add.image(foot.x,foot.y,key).setOrigin(.5,1).setDisplaySize(width,width*source.height/source.width).setDepth(foot.y);this.staticObjects.push(image);this.imageById.set('career:'+building.id,image);
      const title=String(building.meta.place||building.meta.short||building.meta.name||building.id),door=px(building.door),sign=this.facadeSign(title,image,kind,asHex(building.meta.color,0xa57952));
      const h:Hotspot={id:'career:'+building.id,label:title,...building.at,approach:building.door,point:door,z:0,range:50};this.owner.hotspots.push(h);
      this.hits.push({hotspot:h,object:image},{hotspot:h,object:sign});
      if(building.slot%4===0)this.lamp({x:building.footprint.x1+.3,y:building.footprint.y1+.6});
    }
    for(const prop of townGarden(this.buildings))this.vegetation(prop.kind,prop.at,prop.size);
    for(const prop of townScenery()){
      if(prop.kind==='gazebo'){this.artObject('gazebo',prop.at,0,470);continue;}
      if(prop.kind==='bench'){this.bench(prop.at);continue;}if(prop.kind==='lamp'){this.lamp(prop.at);continue;}
      if(prop.kind==='crates'){this.artObject('crates',prop.at,0,130);continue;}
      const key='civic-'+prop.kind;this.textureObject(key,256,256,ctx=>drawCivicProp(ctx,prop.kind));const at=px(prop.at),width=prop.kind==='playground'?240:prop.kind==='pergola'?210:130;
      const image=this.add.image(at.x,at.y,key).setOrigin(.5,.94).setDisplaySize(width,width).setDepth(at.y+.2);this.staticObjects.push(image);
    }
    this.refreshResidentShops();this.amenities();this.landmarks();
    for(const d of townDistricts()){
      const h:Hotspot={id:'district:'+d.id,label:d.name,...d.at,approach:d.at,point:px(d.at),z:0,range:50};this.owner.hotspots.push(h);
      // District names belong to the guide/overview; a second board at each
      // crossroads hid nearby service entrances and duplicated their markers.
    }
  }
  private residentObjects:Phaser.GameObjects.GameObject[]=[];
  refreshResidentShops(){
    if(this.owner.mode!=='town')return;
    const old=new Set(this.residentObjects);for(const object of old)object.destroy();this.staticObjects=this.staticObjects.filter(o=>!old.has(o));this.placards=this.placards.filter(p=>!old.has(p.tag));
    this.occluders=this.occluders.filter(o=>!old.has(o.image));this.occluderIndex.clear();for(const o of this.occluders)this.occluderIndex.add(o,o.bounds);for(const o of this.fadingOccluders)if(old.has(o.image))this.fadingOccluders.delete(o);this.occlusionPosition='';
    this.residentObjects=[];this.hits=this.hits.filter(h=>!h.hotspot.id.startsWith('resident:'));this.owner.hotspots=this.owner.hotspots.filter(h=>!h.id.startsWith('resident:'));
    const before=this.staticObjects.length;
    townShopLots().forEach((lot,index)=>{
      const shop=this.owner.residentShops[index],kind=shop?.career?townBuildingArt({id:shop.career},'grocery'):'market';
      const image=this.artObject(kind,lot.at,0,215);
      if(shop?.career){const width=image.displayWidth,height=image.displayHeight;image.setTexture(this.careerArt(shop.career,kind,image.texture.key)).setDisplaySize(width,height);}
      if(!shop)return;
      const sign=this.facadeSign(shop.name,image,kind,0x9e7e55);
      const h:Hotspot={id:'resident:'+shop.id,label:shop.name,...lot.at,approach:lot.door,point:px(lot.door),z:0,range:45};this.owner.hotspots.push(h);this.hits.push({hotspot:h,object:image},{hotspot:h,object:sign});
    });
    this.residentObjects=this.staticObjects.slice(before);this.reindexStatics();this.requestRender();
  }
  private reindexStatics(){
    this.staticIndex.clear();this.shownStatics.clear();this.visibilityView='';
    if(this.owner.mode!=='town')return;
    for(const item of this.staticObjects){
      if(item===this.groundCache||!(item instanceof Phaser.GameObjects.Image||item instanceof Phaser.GameObjects.Container||item instanceof Phaser.GameObjects.Text))continue;
      const r=item.getBounds();if(!r.width||!r.height)continue;
      this.staticIndex.add(item,{x0:r.left,y0:r.top,x1:r.right,y1:r.bottom});this.shownStatics.add(item);
    }
  }
  private syncStaticVisibility(){
    if(this.owner.mode!=='town')return;
    const c=this.cameras.main,key=[c.scrollX,c.scrollY,c.zoom,c.width,c.height].join(':');if(key===this.visibilityView)return;this.visibilityView=key;
    const cx=c.scrollX+c.width/2,cy=c.scrollY+c.height/2,hw=c.width/c.zoom/2+48,hh=c.height/c.zoom/2+48;
    const visible=new Set(this.staticIndex.query({x0:cx-hw,y0:cy-hh,x1:cx+hw,y1:cy+hh}));
    if(c.zoom<.18)for(const sign of this.placards)visible.delete(sign.tag);
    for(const item of this.shownStatics)if(!visible.has(item))item.setVisible(false);
    for(const item of visible){if(!item.visible)item.setVisible(true);if(item instanceof Phaser.GameObjects.Image)this.staticImageLod(item,c.zoom);}
    this.shownStatics=visible;
  }
  private staticImageLod(image:Phaser.GameObjects.Image,zoom:number){
    let frame=this.originalFrames.get(image);if(!frame){frame=image.frame;this.originalFrames.set(image,frame);}
    if(frame.rotated||frame.trimmed)return;
    const width=image.displayWidth,height=image.displayHeight;
    const raster=this.staticLod.get({source:frame.source.image as CanvasImageSource,frameId:frame.name,x:frame.cutX,y:frame.cutY,width:frame.cutWidth,height:frame.cutHeight},width,height,zoom);
    if(raster&&!this.textures.exists(raster.key)){
      // These textures are immutable: avoid CanvasTexture's unnecessary RGBA readback.
      const texture=this.textures.create(raster.key,raster.canvas)!;texture.add('__BASE',0,0,0,raster.width,raster.height);texture.setFilter(Phaser.Textures.FilterMode.LINEAR);this.lodTextures.add(raster.key);
    }
    const key=raster?.key||frame.texture.key,name=raster?'__BASE':frame.name;
    if(image.texture.key!==key||image.frame.name!==name)image.setTexture(key,name).setDisplaySize(width,height);
  }
  private registerOccluder(image:Phaser.GameObjects.Image,sign?:Phaser.GameObjects.Container){
    const existing=this.occluders.find(entry=>entry.image===image);
    if(existing){if(sign)existing.sign=sign;return;}
    const frame=image.frame,key=image.texture.key+':'+frame.name;
    let mask=this.alphaMasks.get(key);
    if(!mask){
      // Downsample once per source/frame. No canvas reads while the player walks.
      const cv=document.createElement('canvas');cv.width=64;cv.height=64;
      const ctx=cv.getContext('2d',{willReadFrequently:true})!;
      try{ctx.drawImage(frame.source.image as CanvasImageSource,frame.cutX,frame.cutY,frame.cutWidth,frame.cutHeight,0,0,64,64);
        const rgba=ctx.getImageData(0,0,64,64).data,alpha=new Uint8Array(64*64);for(let i=0;i<alpha.length;i++)alpha[i]=rgba[i*4+3];
        mask={width:64,height:64,alpha};this.alphaMasks.set(key,mask);
      }catch{return;}
    }
    const r=image.getBounds(),entry:Occluder={image,sign,alpha:1,target:1,depth:image.depth,mask,bounds:{x0:r.left,y0:r.top,x1:r.right,y1:r.bottom}};
    this.occluders.push(entry);this.occluderIndex.add(entry,entry.bounds);
  }
  updateOcclusion(dt:number){
    if(!this.actor||this.owner.mode!=='town'){this.actorRing?.setVisible(false);return false;}
    const p=px(this.owner.player),signature=p.x+':'+p.y;
    if(signature!==this.occlusionPosition){
      this.occlusionPosition=signature;
      for(const entry of this.fadingOccluders)entry.target=1;
      const candidates=this.occluderIndex.query({x0:p.x-14,y0:p.y-80,x1:p.x+14,y1:p.y-25});
      this.occludedCount=0;
      for(const entry of candidates)if(coversPlayer({...p,depth:this.actor.depth},entry)){entry.target=.35;this.fadingOccluders.add(entry);this.occludedCount++;}
    }
    let active=false;
    for(const entry of this.fadingOccluders){
      const alpha=fadeAlpha(entry.alpha,entry.target,dt,this.owner.reduced);
      if(alpha!==entry.alpha){entry.alpha=alpha;entry.image.setAlpha(alpha);entry.sign?.setAlpha(alpha);}
      active ||=alpha!==entry.target;
      if(alpha===1&&entry.target===1)this.fadingOccluders.delete(entry);
    }
    if(!this.actorRing){
      const key=this.textureObject('player-foot-ring',96,48,ctx=>{ctx.lineWidth=4;ctx.strokeStyle='#fff6cf';ctx.beginPath();ctx.ellipse(48,24,36,15,0,0,Math.PI*2);ctx.stroke();ctx.lineWidth=2;ctx.strokeStyle='#698467';ctx.stroke();});
      this.actorRing=this.add.image(p.x,p.y,key).setScale(.5);
    }
    // A marker above the roof reads as a character standing on that roof.
    // Keep real sprite depth and reveal the player only through the faded obstacle.
    this.actorRing.setPosition(p.x,p.y-2).setDepth(this.actor.depth-.1).setAlpha(.65).setVisible(this.occludedCount===0);
    return active;
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
    for(const grove of [{x:-4,y:5},{x:5,y:-4},{x:-4,y:18},{x:18,y:-4},{x:-25,y:29},{x:-13,y:15},{x:62,y:28},{x:66,y:45},{x:-5,y:43},{x:33,y:-6},{x:43,y:57},{x:53,y:6}]){
      for(let i=0;i<19;i++){const angle=i*2.4,radius=1.1+Math.sqrt(i)*1.6,at={x:grove.x+Math.cos(angle)*radius,y:grove.y+Math.sin(angle)*radius*.72},p=px(at);
        if(!insideIsland(at)||this.navigation.roads.some(r=>inside(at,r)))continue;
        ground.fillStyle(i%2?0x9cb384:0xa9bb8d,.34);ground.fillEllipse(p.x,p.y,410,160);this.vegetation(['banyan','banana','bamboo','flamboyant','shrubs','flowers'][i%6],at,.95+(i%4)*.14);
      }
    }
    // A small fictional timber pier follows the southern shore, outside navigation.
    this.floorRect({x0:13.7,y0:61,x1:15,y1:68},0xa38258);for(let y=61;y<68;y+=.45)this.floorRect({x0:13.73,y0:y,x1:14.98,y1:y+.39},0xd1ac78);for(const at of [{x:13.7,y:61.2},{x:15,y:61.2},{x:13.7,y:67.6},{x:15,y:67.6}]){const p=px(at);ground.fillStyle(0x947148);ground.fillEllipse(p.x,p.y,10,6);}
  }
  private work(){
    this.buildings=[];this.owner.hotspots=[];
    const family=kindOf(this.owner.career),meta=this.owner.game?.catalogue?.find(c=>c.id===this.owner.career),primary=asHex(meta?.color,COLORS.sage),appearance=roomAppearance(this.owner.c,this.owner.career),layout=workLayout(family,this.owner.career),words=this.owner.words(),ground=this.background!;
    const shade=(color:number,factor:number)=>Phaser.Display.Color.GetColor(Math.min(255,(color>>16)*factor),Math.min(255,(color>>8&255)*factor),Math.min(255,(color&255)*factor));
    // Authored alcoves, cutaways and equipment partitions are static ink on the
    // existing ground cache. They never cover actors or intercept input/paths.
    const architecture=layout.architecture!,ink:ArchitectureInk={
      polygon:(points,color,alpha=1)=>this.polygon(points,color,alpha),
      line:(from,to,color,width,alpha=1)=>{ground.lineStyle(width,color,alpha);ground.lineBetween(from.x,from.y,to.x,to.y);},
    };
    drawWorkArchitecture(architecture,ink,'base',asHex(appearance.wall));
    for(const zone of layout.floors){
      const r=zone.footprint;this.floorRect(r,zone.accent);
      if(['plank','tile','checker','mat','stone'].includes(zone.pattern)){
        const dx=zone.pattern==='plank'?1.7:zone.pattern==='mat'?.58:.85,dy=zone.pattern==='plank'?.38:dx;
        for(let y=r.y0,row=0;y<r.y1;y+=dy,row++)for(let x=r.x0,col=0;x<r.x1;x+=dx,col++){
          const tone=zone.pattern==='checker'||zone.pattern==='mat'?(row+col)%2?zone.color:shade(zone.accent,1.06):shade(zone.color,1-((row*3+col*7)%5)*.008);
          this.floorRect({x0:x+.014,y0:y+.014,x1:Math.min(r.x1,x+dx)-.014,y1:Math.min(r.y1,y+dy)-.014},tone);
        }
      }else if(zone.pattern==='carpet'){
        this.floorRect({x0:r.x0+.05,y0:r.y0+.05,x1:r.x1-.05,y1:r.y1-.05},zone.color);
        for(let y=r.y0+.12;y<r.y1-.08;y+=.16)this.floorRect({x0:r.x0+.12,y0:y,x1:r.x1-.12,y1:y+.025},zone.accent,.24);
      }else{
        this.floorRect(r,zone.color);for(let i=0;i<44;i++){const p=px({x:r.x0+(i*.618%1)*(r.x1-r.x0),y:r.y0+(i*.371%1)*(r.y1-r.y0)});ground.fillStyle(zone.accent,.45);ground.fillEllipse(p.x,p.y,5+i%4*2,2+i%2);}
      }
      if(zone.label){
        const p=px({x:(r.x0+r.x1)/2,y:r.y1},1);
        const text=this.add.text(p.x,p.y,zone.label,{fontFamily:FONT,fontSize:'11px',color:'#6c614d',backgroundColor:'#efe6ce',padding:{x:5,y:2},resolution:2}).setOrigin(.5,0).setDepth(-4998);
        this.staticObjects.push(text);
      }
    }
    drawWorkArchitecture(architecture,ink,'walls',asHex(appearance.wall));
    drawWorkArchitecture(architecture,ink,'fittings',asHex(appearance.wall));
    // Soft daylight is static; no decorative animation keeps the renderer awake.
    this.floorRect({x0:5,y0:1.1,x1:6.65,y1:3.45},0xfff0c1,.18);
    if(layout.outdoor&&['farm','tra_da'].includes(this.owner.career)){
      // The saved sill becomes a garden trellis on outdoor plans.
      for(const x of [4.4,6.6]){const a=px({x,y:0}),b=px({x,y:0},175);ground.lineStyle(8,0xb7996e);ground.lineBetween(a.x,a.y,b.x,b.y);}
      for(const z of [105,175]){const a=px({x:4.3,y:0},z),b=px({x:6.7,y:0},z);ground.lineStyle(7,0xc6aa80);ground.lineBetween(a.x,a.y,b.x,b.y);}
      this.flower({x:4.4,y:0},0xa9bb86,145);this.flower({x:6.6,y:0},0xa9bb86,145);
    }else if(layout.outdoor){
      // Yards, island watch and the rig retain the saved sill coordinates as a
      // lookout rail, with an open sky instead of an indoor window or trellis.
      for(const x of [4.4,6.6]){const a=px({x,y:0},74),b=px({x,y:0},140);ground.lineStyle(5,0xb8ad90);ground.lineBetween(a.x,a.y,b.x,b.y);}
      const a=px({x:4.3,y:0},140),b=px({x:6.7,y:0},140);ground.lineStyle(6,0xc9c3a7);ground.lineBetween(a.x,a.y,b.x,b.y);
    }else this.window(WORK_WINDOW,WORK_WINDOW.z);

    const furnishing=(item:WorkFixture):{bounds:Phaser.Geom.Rectangle;depth:number}=>{
      const {footprint:r,height:h,color,kind}=item,elevation=workFurnitureElevation(architecture,r);
      const raised=(p:Point,z=0)=>px(p,z+elevation);
      if(['shelf','crate','counter','desk','board','door','bench'].includes(kind)){
        const image=this.prop(r,h,color,kind);image.y-=elevation;return {bounds:image.getBounds(),depth:image.depth};
      }
      const points=(box:Rect,z:number)=>[raised({x:box.x0,y:box.y0},z),raised({x:box.x1,y:box.y0},z),raised({x:box.x1,y:box.y1},z),raised({x:box.x0,y:box.y1},z)];
      const corners=points(r,0),top=points(r,h),left=Math.min(...corners.map(p=>p.x)),right=Math.max(...corners.map(p=>p.x)),above=Math.min(...top.map(p=>p.y)),bottom=Math.max(...corners.map(p=>p.y));
      const bounds=new Phaser.Geom.Rectangle(left-12,above-12,right-left+24,bottom-above+24),depth=(r.x1+r.y1)*32;
      // Occupation silhouettes are rendered once into a shared texture. Room
      // refreshes reuse the bitmap; they never add a new per-frame vector loop.
      const signature=['console','seatrow','beacon','pipework','pool','rack','washer','bin','signal','freezer','coldcabinet','photobooth'].includes(kind);
      const textureKey='work-signature-v1-'+[kind,r.x0,r.y0,r.x1,r.y1,h,color].join('-');
      const center={x:(r.x0+r.x1)/2,y:(r.y0+r.y1)/2},foot=px(center),width=(r.x1-r.x0+r.y1-r.y0)*64;
      ground.fillStyle(0x705943,.14);ground.fillEllipse(foot.x+3,foot.y+6,width+14,Math.max(19,width*.37));
      const cached=()=>{const image=this.add.image(bounds.x,bounds.y,textureKey).setOrigin(0,0).setScale(.5).setDepth(depth);this.staticObjects.push(image);return {bounds,depth};};
      if(signature&&this.textures.exists(textureKey))return cached();
      const g=this.add.graphics().setDepth(depth);this.staticObjects.push(g);
      const polygon=(p:Point[],fill:number,alpha=1)=>{g.fillStyle(fill,alpha);g.fillPoints(p,true);g.lineStyle(1.2,shade(fill,.76),.68);g.strokePoints(p,true);};
      const block=(box:Rect,height:number,fill:number,z=0)=>{const top=points(box,z+height),base=points(box,z);polygon([top[1],base[1],base[2],top[2]],shade(fill,.82));polygon([top[2],base[2],base[3],top[3]],shade(fill,.94));polygon(top,shade(fill,1.09));};
      const front=(x0:number,x1:number,z0:number,z1:number,fill:number,y=r.y1+.012)=>polygon([raised({x:x0,y},z0),raised({x:x1,y},z0),raised({x:x1,y},z1),raised({x:x0,y},z1)],fill);
      if(kind==='console'){
        block(r,h*.53,color);block(r,7,0xe9dfc8,h*.53);
        for(let x=r.x0+.12;x<r.x1-.28;x+=.7){
          const panel={x0:x,y0:r.y0+.08,x1:Math.min(x+.56,r.x1-.08),y1:r.y0+.32};block(panel,h*.32,0x7d918d,h*.57);
          const p=raised({x:(panel.x0+panel.x1)/2,y:panel.y1+.01},h*.76);g.fillStyle(0xb9d8c4);g.fillRoundedRect(p.x-11,p.y-8,22,14,3);g.lineStyle(1,0xf4eccd);g.lineBetween(p.x-7,p.y,p.x+6,p.y-3);
          const keys=raised({x:x+.24,y:r.y1-.16},h*.58+3);g.fillStyle(0xd8dece);g.fillRoundedRect(keys.x-11,keys.y-3,22,6,2);
        }
      }else if(kind==='seatrow'){
        const count=Math.max(1,Math.round((r.x1-r.x0)/.65)),span=(r.x1-r.x0)/count;
        for(let i=0;i<count;i++){
          const seat={x0:r.x0+i*span+.05,y0:r.y0+.03,x1:r.x0+(i+1)*span-.05,y1:r.y1-.04};
          block({x0:seat.x0+.1,y0:seat.y0+.1,x1:seat.x1-.1,y1:seat.y1-.1},h*.3,0x9a8c75);
          block(seat,12,color,h*.3);block({...seat,y1:seat.y0+.18},h*.55,color,h*.3);
          block({...seat,x1:seat.x0+.07},5,0xd7c6a6,h*.53);block({...seat,x0:seat.x1-.07},5,0xd7c6a6,h*.53);
        }
      }else if(kind==='beacon'){
        const inset=(v:number)=>({x0:r.x0+v,y0:r.y0+v,x1:r.x1-v,y1:r.y1-v});
        block(r,15,0xb9aa8b);block(inset(.23),h*.66,color,15);block(inset(.2),18,0xc68f78,h*.48);block(r,9,0x9da89c,h*.73);
        block(inset(.15),h*.2,0xb6d4c8,h*.77);block(r,7,0xae9578,h*.96);
        const lamp=raised(center,h*.88);g.fillStyle(0xffe5a0,.7);g.fillCircle(lamp.x,lamp.y,12);g.fillStyle(0xfff0ba);g.fillCircle(lamp.x,lamp.y,5);
        for(const x of [r.x0+.15,r.x1-.15]){const a=raised({x,y:r.y1-.15},h*.77),b=raised({x,y:r.y1-.15},h*.96);g.lineStyle(3,0xb39570);g.lineBetween(a.x,a.y,b.x,b.y);}
      }else if(kind==='pipework'){
        block(r,15,0xa6aba0);
        for(let x=r.x0+.16;x<r.x1-.2;x+=.72){
          block({x0:x,y0:r.y0+.18,x1:x+.23,y1:r.y1-.12},h*.8,color,15);
          const valve=raised({x:x+.12,y:r.y1},h*.56);g.lineStyle(4,0xb4816f);g.strokeCircle(valve.x,valve.y,10);g.lineBetween(valve.x-7,valve.y-7,valve.x+7,valve.y+7);g.lineBetween(valve.x-7,valve.y+7,valve.x+7,valve.y-7);
          const gauge=raised({x:x+.1,y:r.y1},h*.79);g.fillStyle(0xf1e9d2);g.fillCircle(gauge.x,gauge.y,7);g.lineStyle(2,0x6c807c);g.lineBetween(gauge.x,gauge.y,gauge.x+3,gauge.y-4);
        }
        block({x0:r.x0,y0:r.y0+.18,x1:r.x1,y1:r.y0+.4},12,0xb4c5ba,h*.68);
      }else if(kind==='pool'){
        block(r,10,0xe2d9bc);const water={x0:r.x0+.18,y0:r.y0+.18,x1:r.x1-.18,y1:r.y1-.18};polygon(points(water,11),color);
        for(let x=water.x0+.4;x<water.x1;x+=.75){const a=raised({x,y:water.y0},12),b=raised({x,y:water.y1},12);g.lineStyle(2,0xe9eee0,.82);g.lineBetween(a.x,a.y,b.x,b.y);}
        for(let i=0;i<8;i++){const p=raised({x:water.x0+.2+(i*.41%1)*(water.x1-water.x0-.4),y:water.y0+.15+(i*.63%1)*(water.y1-water.y0-.3)},12);g.lineStyle(2,0xe5f2df,.6);g.lineBetween(p.x-7,p.y,p.x+7,p.y);}
      }else if(kind==='rack'){
        block(r,h,color);front(r.x0+.07,r.x1-.07,8,h-8,0x627e78);
        for(let z=17;z<h-8;z+=22){front(r.x0+.11,r.x1-.11,z,z+15,0xb8c9be);const p=raised({x:r.x0+.18,y:r.y1+.025},z+8);g.fillStyle(0xeae5ac);g.fillCircle(p.x,p.y,2);g.lineStyle(2,0x72877f);for(let i=0;i<3;i++)g.lineBetween(p.x+8+i*4,p.y-4,p.x+8+i*4,p.y+3);}
      }else if(kind==='washer'){
        block(r,h,color);front(r.x0+.1,r.x1-.1,h*.75,h*.87,0xb5c4b9);
        const p=raised({x:center.x,y:r.y1+.02},h*.42),radius=Math.min(23,(r.x1-r.x0)*22);g.fillStyle(0x8faba9);g.fillCircle(p.x,p.y,radius);g.lineStyle(5,0xece8d7);g.strokeCircle(p.x,p.y,radius);g.fillStyle(0xb9d2c5);g.fillEllipse(p.x,p.y+5,radius*1.2,10);
      }else if(kind==='bin'){
        const count=Math.max(1,Math.floor((r.x1-r.x0)/.8)),span=(r.x1-r.x0)/count;
        for(let i=0;i<count;i++){const box={x0:r.x0+i*span+.025,y0:r.y0,x1:r.x0+(i+1)*span-.025,y1:r.y1};block(box,h-10,count>1?[0xa8b897,0xd4bc84,0x969e92][i%3]:color);block(box,8,0xb9c3a9,h-10);const p=raised({x:(box.x0+box.x1)/2,y:r.y1+.015},h*.53);g.fillStyle(0xe8e5cd);g.fillRoundedRect(p.x-8,p.y-6,16,12,3);}
      }else if(kind==='signal'){
        block({x0:r.x0,y0:r.y0,x1:r.x0+.48,y1:r.y1},h*.76,0xaaa791);
        front(r.x0+.09,r.x0+.4,h*.35,h,0x7e8980);
        for(const [z,color] of [[h*.54,0xb4c896],[h*.82,0xdba58a]]){const p=raised({x:r.x0+.25,y:r.y1+.02},z);g.fillStyle(color);g.fillCircle(p.x,p.y,7);}
        for(let x=r.x0+.5,i=0;x<r.x1;x+=.28,i++)block({x0:x,y0:r.y0+.3,x1:Math.min(x+.28,r.x1),y1:r.y0+.47},10,i%2?0xc58975:0xf1dfb9,h*.45);
      }else if(kind==='coldcabinet'){
        // Upright, closed cold storage is shared by household and dispensary
        // stock. No scoops, serving tubs or food-display glass from the ice cart.
        block(r,6,0x8f9d8c);block(r,h-6,color,6);
        front(r.x0+.055,r.x1-.055,10,h*.56,0xe6e8d5);
        front(r.x0+.055,r.x1-.055,h*.58,h-7,0xeff0df);
        front(r.x0+.065,r.x1-.065,h*.56,h*.58,0xa4b4a2);
        for(const [z0,z1] of [[h*.33,h*.48],[h*.65,h*.8]]){
          const a=raised({x:r.x1-.15,y:r.y1+.025},z0),b=raised({x:r.x1-.15,y:r.y1+.025},z1);
          g.lineStyle(4,0xa3b6a8);g.lineBetween(a.x,a.y,b.x,b.y);g.lineStyle(1,0xf8f2d9);g.lineBetween(a.x-1,a.y,b.x-1,b.y);
        }
        front(r.x0+.13,r.x0+(r.x1-r.x0)*.55,h*.86,h*.93,0x91a999);
        for(const x of [r.x0+.12,r.x1-.12]){const a=raised({x,y:r.y1+.015},3),b=raised({x,y:r.y1+.015},9);g.lineStyle(4,0x8d9984);g.lineBetween(a.x,a.y,b.x,b.y);}
      }else if(kind==='photobooth'){
        const span=r.x1-r.x0,backY=r.y0+.2;
        block(r,7,0xb6a188);
        block({...r,y1:backY},h-7,color,7);
        block({...r,x1:r.x0+.14},h-7,0xc5b2bc,7);
        block({...r,x0:r.x1-.14},h-7,0xc5b2bc,7);
        block({x0:r.x0+span*.2,y0:r.y0+.42,x1:r.x1-span*.2,y1:r.y1-.22},25,0xd9b9bc,7);
        front(r.x0+span*.3,r.x1-span*.3,h*.4,h*.82,0xf2e8d2,backY+.012);
        front(r.x0+span*.34,r.x1-span*.34,h*.57,h*.77,0x879994,backY+.024);
        const lens=raised({x:center.x,y:backY+.03},h*.68);
        g.fillStyle(0x586d69);g.fillCircle(lens.x,lens.y,11);g.lineStyle(3,0xc3d7cc);g.strokeCircle(lens.x,lens.y,11);g.fillStyle(0x9bbfbb);g.fillCircle(lens.x-2,lens.y-2,4);
        const railA=raised({x:r.x0,y:r.y1},h-6),railB=raised({x:r.x1,y:r.y1},h-6);g.lineStyle(5,0xd6c4a3);g.lineBetween(railA.x,railA.y,railB.x,railB.y);
        for(const [x0,x1] of [[r.x0+.03,r.x0+span*.17],[r.x1-span*.22,r.x1-.03]]){
          front(x0,x1,15,h-9,0xc49ba8,r.y1+.01);
          for(let x=x0+.04;x<x1;x+=.075){const a=raised({x,y:r.y1+.022},17),b=raised({x,y:r.y1+.022},h-11);g.lineStyle(2,0xe2bfc9);g.lineBetween(a.x,a.y,b.x,b.y);}
        }
        // A rear lintel leaves the camera visible in this isometric cutaway.
        block({...r,y1:r.y0+.27},7,0xe2c9b0,h-3);
        front(r.x1-span*.18,r.x1-.03,36,42,0x71847e,r.y1+.025);
        front(r.x1-span*.16,r.x1-.045,18,37,0xf0e9d6,r.y1+.03);
        for(const z of [22,28,34])front(r.x1-span*.14,r.x1-.055,z,z+3,0xa4bfb4,r.y1+.035);
      }else if(kind==='freezer'){
        block(r,h*.8,color);block(r,8,0xe8e4cd,h*.8);
        const inset={x0:r.x0+.1,y0:r.y0+.1,x1:r.x1-.1,y1:r.y1-.1};polygon(points(inset,h*.8+9),0xa8c9c1);
        for(let x=r.x0+.32,i=0;x<r.x1-.2;x+=.55,i++){const p=raised({x,y:center.y},h*.8+11);g.fillStyle([0xe5c89c,0xc7b99c,0xdbadad,0xbad1a6][i%4]);g.fillEllipse(p.x,p.y,25,16);g.lineStyle(2,0xf0e4cd);g.strokeEllipse(p.x,p.y,25,16);}
      }else if(kind==='planter'){
        block(r,20,0xa17c55);block({x0:r.x0+.06,y0:r.y0+.06,x1:r.x1-.06,y1:r.y1-.06},2,0x746649,20);
        for(let x=r.x0+.2;x<r.x1-.1;x+=.42)for(let y=r.y0+.15;y<r.y1-.1;y+=.36){const p=raised({x,y},23);g.fillStyle(0x75935d);g.fillEllipse(p.x-5,p.y-5,14,8);g.fillStyle(0xa4bc71);g.fillEllipse(p.x+4,p.y-7,11,13);g.fillStyle(0xc0cd8b);g.fillEllipse(p.x,p.y-10,5,10);}
      }else if(kind==='bed'||kind==='crib'||kind==='sofa'){
        block(r,22,0xb39577);block({x0:r.x0+.07,y0:r.y0+.07,x1:r.x1-.07,y1:r.y1-.07},15,kind==='sofa'?color:0xf1e8d6,22);
        block({x0:r.x0+.13,y0:r.y0+.12,x1:r.x0+(r.x1-r.x0)*.3,y1:r.y1-.12},8,0xfaf4e5,37);
        block({x0:r.x0+(r.x1-r.x0)*.36,y0:r.y0+.1,x1:r.x1-.08,y1:r.y1-.1},3,color,37);
        if(kind==='crib')for(let x=r.x0;x<r.x1;x+=.24){block({x0:x,y0:r.y1-.05,x1:x+.045,y1:r.y1},58,0xc9ae88);block({x0:x,y0:r.y0,x1:x+.045,y1:r.y0+.045},58,0xdcc5a0);}
        if(kind==='crib')block({x0:r.x0,y0:r.y1-.06,x1:r.x1,y1:r.y1+.02},5,0xe5d3af,56);
        if(kind==='sofa')block({x0:r.x0,y0:r.y0,x1:r.x1,y1:r.y0+.17},63,color);
      }else if(['bookcase','medicine'].includes(kind)){
        block(r,h,color);
        for(let z=13;z<h-15;z+=28){front(r.x0+.07,r.x1-.07,z,z+25,0x8f795e);let i=0;for(let x=r.x0+.12;x<r.x1-.1;x+=.16,i++){const tones=kind==='medicine'?[0xf3eee2,0xc6dbd0,0xf0e4c3]:[0x96a77c,0xba8167,0xd2b06e,0x809ca6,0xb598af];front(x,Math.min(x+.12,r.x1-.08),z+2,z+21-i%3*2,tones[i%tones.length]);}front(r.x0+.035,r.x1-.035,z-2,z+2,0xdac09a);}
      }else if(['chalkboard','routeboard','mirror','tools'].includes(kind)){
        block(r,22,0xbd9c76);front(r.x0,r.x1,24,h,0xb89972);
        front(r.x0+.07,r.x1-.07,30,h-6,kind==='chalkboard'?0x527663:kind==='mirror'?0xc0dbd8:kind==='tools'?0xc9b694:0xe2dec5);
        if(kind==='mirror'){front(r.x0+.13,r.x0+(r.x1-r.x0)*.46,38,h-15,0xe6efe5);for(let z=38;z<h-8;z+=18){const p=raised({x:r.x0+.015,y:r.y1+.04},z);g.fillStyle(0xffefbb);g.fillCircle(p.x,p.y,3);}}
        else for(let i=0;i<4;i++){
          const z=40+i*(h-56)/4,a=raised({x:r.x0+.16,y:r.y1+.025},z),b=raised({x:r.x1-.17-i%2*.2,y:r.y1+.025},z+(kind==='routeboard'?i%2*10:0));g.lineStyle(kind==='tools'?5:2,kind==='chalkboard'?0xdbe4bf:kind==='tools'?0x777b75:0x94ae9b,.86);g.lineBetween(a.x,a.y,b.x,b.y);
          if(kind==='routeboard'){g.fillStyle(i%2?0xb88670:0xa6af79);g.fillCircle(b.x,b.y,4);}
        }
      }else{
        block(r,h*.72,color);block(r,7,0xe8dac0,h*.72);
        if(kind==='oven'){front(r.x0+.13,r.x1-.13,17,h*.6,0x665b50);front(r.x0+.2,r.x1-.2,23,h*.49,0xbf946a);front(r.x0+.15,r.x1-.15,h*.56,h*.61,0xe1cda9);}
        if(kind==='display'){block({x0:r.x0+.08,y0:r.y0+.07,x1:r.x1-.08,y1:r.y1-.08},h*.26,0xb7ccc7,h*.76);for(let x=r.x0+.2;x<r.x1-.12;x+=.25){const p=raised({x,y:center.y},h);g.fillStyle(x%1>.5?0xe0bc87:0xc69e92);g.fillRoundedRect(p.x-5,p.y-11,10,14,3);}}
        if(kind==='stove'||kind==='sink'){for(const x of kind==='stove'?[r.x0+(r.x1-r.x0)*.3,r.x0+(r.x1-r.x0)*.72]:[center.x]){const p=raised({x,y:center.y},h*.72+10);g.fillStyle(kind==='sink'?0x86a8aa:0x626c63);g.fillEllipse(p.x,p.y,kind==='sink'?width*.46:34,kind==='sink'?22:17);g.lineStyle(3,0xd8dfce);g.strokeEllipse(p.x,p.y,kind==='sink'?width*.46:34,kind==='sink'?22:17);if(kind==='stove'){g.fillStyle(0xb8c4b7);g.fillRoundedRect(p.x-13,p.y-14,26,15,5);g.fillStyle(0xe0e3cb);g.fillEllipse(p.x,p.y-14,26,9);}}}
        if(kind==='altar'){for(const x of [r.x0+.3,r.x1-.3]){const p=raised({x,y:center.y},h);g.fillStyle(0xd5b267);g.fillRoundedRect(p.x-4,p.y-23,8,24,3);g.fillStyle(0xf4d190);g.fillEllipse(p.x,p.y-26,6,10);}this.flower(center,color,h*.8+elevation);}
      }
      if(signature){
        const canvas=document.createElement('canvas');canvas.width=Math.ceil(bounds.width*2);canvas.height=Math.ceil(bounds.height*2);
        const camera=new Phaser.Cameras.Scene2D.Camera(0,0,canvas.width,canvas.height).setScene(this).setOrigin(0,0).setScroll(bounds.x,bounds.y).setZoom(2);camera.preRender();
        (g as any).renderCanvas(this.game.renderer,g,camera,null,canvas.getContext('2d'),false);camera.destroy();
        const texture=this.textures.create(textureKey,canvas)!;texture.add('__BASE',0,0,0,canvas.width,canvas.height);texture.setFilter(Phaser.Textures.FilterMode.LINEAR);
        g.destroy();this.staticObjects=this.staticObjects.filter(object=>object!==g);return cached();
      }
      return {bounds,depth};
    };
    for(const item of layout.fixtures)furnishing(item);
    const labels:Record<string,string>={shelf:words.shelf||'Kệ hàng',warehouse:words.warehouse||'Kho',workbench:layout.identity.workbench,counter:words.counter||'Quầy bàn giao',evidence:words.evidence||'Phiếu công việc',board:words.board||'Chuyện phố',door:this.owner.c.open?words.door_open:words.door_closed,pet:words.pet||'Chơi với Mướp','ops:finance':words.finance||'Sổ thu chi','ops:property':words.property||'Mặt bằng','ops:security':words.security||'An ninh'};
    for(const station of layout.stations){
      const {id,at,approach,height,kind,color}=station,label=labels[id];
      if(id.startsWith('ops:')){this.operationsStation(id,label,at,height,approach,id==='ops:finance'?'ledger':id.slice(4));continue;}
      const elevation=station.footprint?workFurnitureElevation(architecture,station.footprint):0;
      const point=px(at),h:Hotspot={id,label,...at,approach,point,z:height+elevation,range:45};this.owner.hotspots.push(h);
      if(id==='pet'){this.cat(at);this.hits.push({hotspot:h,rect:new Phaser.Geom.Rectangle(point.x-35,point.y-48,70,58)});continue;}
      const drawn=furnishing({kind,footprint:station.footprint!,height,color});this.hits.push({hotspot:h,rect:drawn.bounds});
      const tag=this.label(label,drawn.bounds.centerX,drawn.bounds.y-14,12,160,0xa18a69);tag.setDepth(drawn.depth+.6);
      if(id==='workbench'&&['cafe','teabar','kitchen','pho','comtam','home'].includes(layout.id)){const r=station.footprint!;this.cup({x:r.x1-.35,y:r.y0+.35},height+elevation+4,primary);if(layout.id==='cafe')this.bread({x:r.x0+.4,y:r.y1-.25},height+elevation+4);}
    }
    // Saved semantic decoration spots keep their established anchors; tool badges
    // sit on the career's actual work surface even when that surface moves.
    this.savedRoomDetails({...appearance,tools:appearance.tools.filter(id=>id!=='workbench'),gearTier:0,needsRepair:false},[],primary);
    const surface=layout.stations.find(s=>s.id==='workbench')!,surfaceBox=surface.footprint!,surfaceAt={x:(surfaceBox.x0+surfaceBox.x1)/2,y:(surfaceBox.y0+surfaceBox.y1)/2},surfaceZ=surface.height+workFurnitureElevation(architecture,surfaceBox);
    if(appearance.tools.includes('workbench'))this.roomIcon('check',surfaceAt,surfaceZ+5,.45);
    if(appearance.gearTier)this.roomIcon('gear-'+appearance.gearTier,{x:surfaceAt.x+.4,y:surfaceAt.y},surfaceZ+5,.45);
    if(appearance.needsRepair)this.roomIcon('repair',{x:surfaceAt.x-.4,y:surfaceAt.y},surfaceZ+5,.45);
    this.navigation=workNavigation(layout,appearance);
    const tasks=activeTasks(this.owner.c),seen=new Set<string>(),people:{id:string;label:string;seed:number}[]=[];
    for(const task of tasks){if(!task.npc||seen.has(task.npc)||seen.size>=4)continue;seen.add(task.npc);people.push({id:'npc:'+task.npc,label:this.owner.game?.npcs?.find(n=>n.id===task.npc)?.display_name||'Khách',seed:seen.size});}
    const staff=(this.owner.c.ops?.staff||[]).filter((s:any)=>s.status==='hired');staff.slice(0,3).forEach((s:any,i:number)=>people.push({id:'staff:'+s.id,label:s.name||'Nhân viên',seed:i+4}));
    if(this.owner.c.event&&this.owner.c.event.stage!=='resolved')people.push({id:'event',label:'Chuyện mới',seed:8});
    if(this.owner.c.upgrades?.includes('assistant')&&!staff.length)people.push({id:'assistant',label:'Bạn phụ việc',seed:5});
    if(['reported','result'].includes(this.owner.c.ops?.security?.current_case?.status))people.push({id:'officer',label:'Công an khu phố',seed:7});
    const positions=workActorPositions(layout,this.navigation,people.length);people.forEach((person,i)=>{if(positions[i])this.person(person.id,person.label,positions[i],person.seed);});
    const name=String(this.owner.c.life?.shop_name||meta?.place||meta?.short||'Nơi làm việc');this.placard(name+'\n'+layout.identity.focus,{x:1.4,y:8.85},14,360,primary,54);
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
  private placard(text:string,at:Point,size:number,maxWidth:number,color:number,height=96){
    const p=px(at),elevation=Math.max(96,height),plate=this.label(facadeTextLines(text),0,-elevation,size,maxWidth,color),post=this.add.graphics();
    const half=Math.max(28,Math.min(64,plate.getBounds().width*.32));
    post.fillStyle(0x71583e,.15).fillEllipse(0,2,half*2+28,12);
    for(const x of [-half,half]){post.fillStyle(0x8b6d4c).fillRoundedRect(x-4,-elevation,8,elevation,2);post.fillStyle(0xc6aa7d).fillRect(x-1,-elevation,2,elevation-3);}
    // Board and supports share one planted origin, depth, visibility and lifetime.
    const tag=this.add.container(p.x,p.y,[post,plate]).setDepth(p.y+.4).setData('wayfindingSign',true);
    this.staticObjects=this.staticObjects.filter(object=>object!==plate);this.staticObjects.push(tag);this.placards.push({tag,size,mounted:true});return tag;
  }
  wayfindingSign(text:string,approach:Point,size=15,maxWidth=190,color=0x668574){
    const doors=[...this.buildings.map(b=>b.door),...townShopLots().map(lot=>lot.door),...townAmenities().map(p=>p.at),...townLandmarks().map(p=>p.approach)];
    const tag=this.placard(text,approach,size,maxWidth,color),r=tag.getBounds();
    // Graphics have no Phaser bounds: include the frame, both posts and feet
    // around the measured text when checking foreground sprite silhouettes.
    const shape={x0:Math.min(-68,r.left-tag.x-14),y0:Math.min(-124,r.top-tag.y-10),x1:Math.max(68,r.right-tag.x+14),y1:8};
    const resident=this.residentObjects.filter((o):o is Phaser.GameObjects.Image=>o instanceof Phaser.GameObjects.Image).map(image=>{const b=image.getBounds();return {depth:image.depth,bounds:{x0:b.left,y0:b.top,x1:b.right,y1:b.bottom}};});
    const mount=wayfindingMount(approach,this.navigation,townTrails(),[...this.signMounts.values()],doors,[...this.occluders,...resident],shape),point=px(mount);
    tag.setPosition(point.x,point.y).setDepth(point.y+.4);
    tag.setData('interactionPoint',mount);this.signMounts.set(tag,mount);this.reindexStatics();return tag;
  }
  removeWayfindingSign(tag:Phaser.GameObjects.Container){
    tag.destroy();this.signMounts.delete(tag);this.staticObjects=this.staticObjects.filter(object=>object!==tag);this.placards=this.placards.filter(p=>p.tag!==tag);this.reindexStatics();
  }
  /** Available services bind to scenery that also exists for a locked account. */
  addAmenityVisual(p:AmenityArt,hotspot:Hotspot){
    const image=this.imageById.get('amenity:'+p.id);if(!image)return null;
    if(!this.hits.some(hit=>hit.hotspot===hotspot&&hit.object===image))this.hits.push({hotspot,object:image});
    return image;
  }
  removeAmenityVisual(image:Phaser.GameObjects.Image,hotspot:Hotspot){this.hits=this.hits.filter(hit=>!(hit.hotspot===hotspot&&hit.object===image));}
  amenitySign(p:AmenityArt,image:Phaser.GameObjects.Image){
    if(!p.art||!(FACADE_SIGNS[p.art]||CIVIC_FACADES[p.art]))return null;
    const sign=this.facadeSign(p.label,image,p.art,0x668574);sign.setData('interactionPoint',p.at);return sign;
  }
  removeAmenitySign(tag:Phaser.GameObjects.Container){
    for(const entry of this.occluders)if(entry.sign===tag)entry.sign=undefined;
    this.removeWayfindingSign(tag);
  }
  private facadeSign(text:string,image:Phaser.GameObjects.Image,kind:string,color:number){
    const loadedKind=image.texture.key.startsWith('art-')?image.texture.key.slice(4):kind;
    const sign=CIVIC_FACADES[loadedKind]||FACADE_SIGNS[loadedKind]||CIVIC_FACADES[kind]||FACADE_SIGNS[kind]||FACADE_SIGNS.home,width=image.displayWidth*sign.width,height=image.displayHeight*sign.height;
    const title=this.add.text(0,0,facadeTextLines(text),{fontFamily:FONT,fontSize:'16px',fontStyle:'bold',color:'#68472e',align:'center',lineSpacing:1,resolution:2}).setOrigin(.5,.5);
    // Use the sign already painted on the building, rather than a second floating board.
    const fit=Math.min(1,width/Math.max(1,title.width),height/Math.max(1,title.height));title.setScale(fit);
    const layers:Phaser.GameObjects.GameObject[]=[];
    if(sign.panel){const panel=this.add.graphics();panel.fillStyle(0x9b744e);panel.fillRoundedRect(-width/2-5,-height/2-4,width+10,height+8,3);panel.fillStyle(0xffefcd);panel.fillRoundedRect(-width/2-2,-height/2-1,width+4,height+2,2);panel.fillStyle(0x98764e);for(const side of [-1,1])panel.fillCircle(side*(width/2-3),0,1.4);layers.push(panel);}
    layers.push(title);
    const tag=this.add.container(image.x+(sign.x-image.originX)*image.displayWidth,image.y+(sign.y-image.originY)*image.displayHeight,layers);this.staticObjects.push(tag);
    tag.setRotation(sign.angle).setDepth(image.depth+.4);tag.setData('buildingSign',true);this.placards.push({tag,size:16,mounted:true});if(this.owner.mode==='town')this.registerOccluder(image,tag);return tag;
  }
  private careerArt(career:string,kind:string,fallback:string){
    if(!this.textures.exists('art-'+kind))return fallback;
    // Each finished painting is already the whole building, with its own roof,
    // equipment and physical name board. Do not bake legacy overlays over it.
    if(kind==='career-'+career)return 'art-'+kind;
    const key=careerFacadeTextureKey(career,kind);if(!key)return fallback;
    const source=this.textures.get('art-'+kind).getSourceImage() as HTMLImageElement|HTMLCanvasElement,size=careerFacadeSize(source);
    return this.textureObject(key,size.width,size.height,ctx=>drawCareerFacade(ctx,source,career,kind));
  }
  private textureObject(key:string,width:number,height:number,draw:(ctx:CanvasRenderingContext2D)=>void){if(!this.textures.exists(key)){const c=document.createElement('canvas');c.width=width;c.height=height;const ctx=c.getContext('2d')!;ctx.imageSmoothingEnabled=true;draw(ctx);this.textures.addCanvas(key,c)!.setFilter(Phaser.Textures.FilterMode.LINEAR);}return key;}
  private characterTexture(prefix:string,look:any,gender:string,direction:Facing,uniformColor:string,walkFrame=0){
    return this.characterFrames.get(prefix,JSON.stringify([look,gender,uniformColor,this.characterRevision]),direction+':'+walkFrame,key=>{
      const stamp=getCharacterStamp({look,gender,direction,uniformColor,walkFrame,onReady:this.charactersReady});
      this.textures.addCanvas(key,stamp.canvas)!.setFilter(Phaser.Textures.FilterMode.LINEAR);
    });
  }
  syncRemotePlayers(){
    if(!this.sys.isActive())return;const peers=this.owner.mode==='town'?publicTownPlayers(this.owner.remotePlayers,this.navigation):[],present=new Set(peers.map(p=>p.pid));
    for(const [pid,actor] of this.remoteActors)if(!present.has(pid)){actor.image.destroy();actor.tag.destroy();this.characterFrames.release('iso-peer-'+pid);this.remoteActors.delete(pid);}
    for(const peer of peers){
      const look={...defaultLook(peer.gender),...peer.look},key=this.characterTexture('iso-peer-'+peer.pid,look,peer.gender,peer.direction,'#8ba77a');
      let actor=this.remoteActors.get(peer.pid);
      if(!actor){const image=this.add.image(0,0,key).setOrigin(.5,1).setScale(CHARACTER_SCALE),tag=this.add.text(0,0,peer.name,{fontFamily:FONT,fontSize:'13px',color:'#654a39',backgroundColor:'#fff3da',padding:{x:6,y:3}}).setOrigin(.5,1);actor={peer,at:{x:peer.x,y:peer.y},from:{x:peer.x,y:peer.y},path:[],started:0,image,tag,texture:key};this.remoteActors.set(peer.pid,actor);}
      else{
        if(actor.texture!==key){actor.image.setTexture(key);actor.texture=key;}
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
      const walkFrame=moving&&!this.owner.reduced?1+Math.floor(now*7)%2:0,key=this.characterTexture('iso-peer-'+actor.peer.pid,{...defaultLook(actor.peer.gender),...actor.peer.look},actor.peer.gender,actor.peer.direction,'#8ba77a',walkFrame);if(key!==actor.texture){actor.image.setTexture(key);actor.texture=key;}
      const point=px(actor.at);actor.image.setPosition(point.x,point.y).setDepth(point.y+.5);actor.tag.setPosition(point.x,point.y-112).setDepth(point.y+.7).setVisible(this.cameras.main.zoom>=.22);
    }
    return active;
  }
  artSource(kind:string){if(ASSETS[kind]&&!this.textures.exists('art-'+kind)){this.ensureAssets([kind]);kind=kind==='pho'?'cafe':'home';}return this.textures.get(this.artTexture(kind)).getSourceImage() as HTMLImageElement|HTMLCanvasElement;}
  private artTexture(kind:string,variant:string|number=0){
    this.ensureAssets([kind]);if(this.textures.exists('art-'+kind))return 'art-'+kind;
    // A shop name needs an actual wall while its authored building image loads.
    if(FACADE_SIGNS[kind]&&this.textures.exists('art-home'))return 'art-home';
    const key='illustrated-detail-'+kind+'-'+variant,size:Record<string,[number,number]>={lamp:[192,512],window:[384,360],cat:[384,300],cup:[256,300],bread:[384,260],pond:[512,320],pool:[512,320],boat:[512,360]};const [width,height]=size[kind]||[384,384];return this.textureObject(key,width,height,ctx=>drawIllustratedDetail(ctx,kind,String(variant)));
  }
  private artObject(kind:string,p:Point,z:number,width:number,variant:string|number=0){
    const key=this.artTexture(kind,variant),source=this.textures.get(key).getSourceImage() as HTMLImageElement|HTMLCanvasElement,point=px(p,z),image=this.add.image(point.x,point.y,key).setOrigin(.5,1).setDisplaySize(width,width*source.height/source.width).setDepth(px(p).y+.2);this.staticObjects.push(image);if(this.owner.mode==='town'&&['tree','gazebo'].includes(kind))this.registerOccluder(image);return image;
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
    const point=px(p),image=this.add.image(point.x,point.y,key,name).setOrigin(.5,.93).setDisplaySize(210*size,210*size*height/width).setDepth(point.y+.2);this.staticObjects.push(image);if(this.owner.mode==='town'&&!['flowers','shrubs','rocks'].includes(kind))this.registerOccluder(image);return image;
  }
  private flower(p:Point,color:number,z=0){return this.artObject('plant',p,z,59,color%3);}
  private bench(p:Point){return this.artObject('bench',p,0,125);}
  private lamp(p:Point){return this.artObject('lamp',p,0,52);}
  private window(p:Point,z:number){const image=this.artObject('window',p,z,110);image.setOrigin(.5,.5).setDepth(-100);return image;}
  private cup(p:Point,z:number,color:number){return this.artObject('cup',p,z,24,color%3);}
  private bread(p:Point,z:number){return this.artObject('bread',p,z,45);}
  private cat(p:Point){return this.artObject('cat',p,0,62);}
  private amenities(){
    for(const p of townAmenities()){
      const placement=amenityPlacement(p);if(!placement)continue;
      const {kind,at,width,originY}=placement;this.ensureAssets([kind]);
      // A shape-mismatched house is a poor loading placeholder for an open park.
      if(!this.textures.exists('art-'+kind))continue;
      const source=this.textures.get('art-'+kind).getSourceImage() as HTMLImageElement;
      const foot=px(at),image=this.add.image(foot.x,foot.y,'art-'+kind).setOrigin(.5,originY).setDisplaySize(width,width*source.height/source.width).setDepth(foot.y+.2);
      this.staticObjects.push(image);this.imageById.set('amenity:'+p.id,image);this.registerOccluder(image);
    }
  }
  private landmarks(){
    for(const landmark of townLandmarks()){
      const r=landmark.footprint,g=landmarkPlaneGeometry(r);
      if(landmark.kind==='boat'){
        // The boat artwork is a top view: project a small hull onto the water plane.
        const basin=(scale:number)=>Array.from({length:36},(_,i)=>px({x:(r.x0+r.x1)/2+Math.cos(i/18*Math.PI)*(r.x1-r.x0)/2*scale,y:(r.y0+r.y1)/2+Math.sin(i/18*Math.PI)*(r.y1-r.y0)/2*scale}));
        this.background!.fillStyle(0xa2ad84).fillPoints(basin(1),true);this.background!.fillStyle(0x7eafb3).fillPoints(basin(.9),true);
        this.floorRect({x0:r.x1-.4,y0:r.y0+.6,x1:r.x1+.2,y1:r.y1-.4},0xc3a276);
        for(let y=r.y0+.6;y<r.y1-.4;y+=.28)this.floorRect({x0:r.x1-.4,y0:y,x1:r.x1+.2,y1:y+.05},0x9b7c59);
        const hull=landmarkPlaneGeometry({x0:landmark.at.x-.45,y0:landmark.at.y-1.05,x1:landmark.at.x+.45,y1:landmark.at.y+1.05}),source=this.artSource('boat'),key='park-moored-boat-'+this.textures.exists('art-boat');
        this.textureObject(key,Math.ceil(hull.width),Math.ceil(hull.height),ctx=>{ctx.setTransform(hull.a/source.width,hull.b/source.width,hull.c/source.height,hull.d/source.height,hull.e,0);ctx.drawImage(source,0,0);});
        const boat=this.add.image(hull.x,hull.y,key).setOrigin(0,0).setDepth(hull.depth);this.staticObjects.push(boat);
        this.artObject('bench',{x:r.x1+.45,y:r.y1+.15},0,80);
      }else if(landmark.kind==='pool'){
        this.ensureAssets(['pool-map']);
        if(this.textures.exists('art-pool-map')){
          const source=this.textures.get('art-pool-map').getSourceImage() as HTMLImageElement;
          const at=landmarkSpritePlacement(r,source.width,source.height);
          const image=this.add.image(at.x,at.y,'art-pool-map').setOrigin(.5,1).setDisplaySize(at.width,at.height).setDepth(at.depth);
          this.staticObjects.push(image);
        }else{
          // A small native ground fallback while the transparent town sprite loads.
          this.floorRect(r,0xd8c6a4);
          this.floorRect({x0:r.x0+.25,y0:r.y0+.25,x1:r.x1-.25,y1:r.y1-.25},0x65bdb8);
        }
      }else{
        const source=this.artSource(landmark.kind),key='island-landmark-'+landmark.kind+'-'+this.textures.exists('art-'+landmark.kind);
        this.textureObject(key,Math.ceil(g.width),Math.ceil(g.height),ctx=>{
          ctx.setTransform(g.a/source.width,g.b/source.width,g.c/source.height,g.d/source.height,g.e,0);
          if(landmark.kind==='pond'){ctx.beginPath();ctx.roundRect(0,0,source.width,source.height,Math.min(source.width,source.height)*.23);ctx.clip();}
          ctx.drawImage(source,0,0);
        });
        const image=this.add.image(g.x,g.y,key).setOrigin(0,0).setDepth(g.depth-.5);this.staticObjects.push(image);
      }
      const point=px(landmark.at),h:Hotspot={id:landmark.id,label:landmark.label,...landmark.at,approach:landmark.approach,point,z:0,range:70};this.owner.hotspots.push(h);this.hits.push({hotspot:h,footprint:r});
      const tag=this.wayfindingSign(landmark.label,landmark.approach,14,190,0x668574);h.interactionPoint=tag.getData('interactionPoint');this.hits.push({hotspot:h,object:tag});
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
    if(key===this.actorKey)return false;if(this.actor)this.actor.setTexture(key);else this.actor=this.add.image(0,0,key).setOrigin(.5,1).setScale(CHARACTER_SCALE);this.actorKey=key;return true;
  }
  positionPlayer(moving:boolean){const pose=walkingPose(this.owner.walkDistance,moving,this.owner.reduced);if(this.actorDirection!==this.owner.direction||this.actorWalkFrame!==pose.frame)this.refreshPlayer(pose.frame);if(!this.actor)return;const f=px(this.owner.player);this.actor.setPosition(f.x,f.y).setDepth(f.y+.5).setRotation(pose.lean).setScale(CHARACTER_SCALE,CHARACTER_SCALE*pose.squash);if(this.speech){const target=this.speechTarget?this.owner.hotspots.find(h=>h.id===this.speechTarget):null,at=target?px(target,138):{x:f.x,y:f.y-138};this.speech.setPosition(at.x,at.y);} }
  hitTest(point:Point){const ground=unproject(point),hits=this.hits.filter(h=>h.rect?.contains(point.x,point.y)||h.footprint&&inside(ground,h.footprint)||h.object?.visible&&h.object.alpha>.6&&h.object.getBounds().contains(point.x,point.y)).sort((a,b)=>b.hotspot.point.y-a.hotspot.point.y);return hits[0]?.hotspot;}
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
