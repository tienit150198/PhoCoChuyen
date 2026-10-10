import {findRoute,isWalkable,makeNavigation,project,workWindowAnchors} from './model';
import type {Navigation,Point,Rect,RoomAppearance} from './model';
import {applyCareerPlan} from './work-careers';
import type {CareerRoomIdentity} from './work-careers';
import {workArchitecture} from './work-architecture';
import type {WorkArchitecture} from './work-architecture';

export type WorkFurniture='shelf'|'crate'|'counter'|'desk'|'board'|'door'|'bench'|'oven'|'stove'|'medicine'|'bed'|'mirror'|'tools'|'sofa'|'crib'|'chalkboard'|'bookcase'|'planter'|'routeboard'|'altar'|'display'|'sink'|'console'|'seatrow'|'beacon'|'pipework'|'pool'|'rack'|'washer'|'bin'|'signal'|'freezer'|'coldcabinet'|'photobooth';
export interface WorkFixture {kind:WorkFurniture;footprint:Rect;height:number;color:number}
export interface WorkStation {id:string;kind:WorkFurniture;footprint?:Rect;at:Point;approach:Point;height:number;color:number}
export interface WorkFloor {footprint:Rect;pattern:'plank'|'tile'|'checker'|'carpet'|'earth'|'mat'|'stone';color:number;accent:number;label?:string}
export interface WorkLayout {id:string;identity:CareerRoomIdentity;spawn:Point;bounds:Rect;outdoor:boolean;stations:WorkStation[];fixtures:WorkFixture[];floors:WorkFloor[];architecture?:WorkArchitecture}
const r=(x0:number,y0:number,x1:number,y1:number):Rect=>({x0,y0,x1,y1});
const fixture=(kind:WorkFurniture,footprint:Rect,height=58,color=0xbc9972):WorkFixture=>({kind,footprint,height,color});
const station=(id:string,kind:WorkFurniture,footprint:Rect,approach:Point,height=62,color=0xbc9972):WorkStation=>({id,kind,footprint,at:{x:(footprint.x0+footprint.x1)/2,y:footprint.y1},approach,height,color});
const floor=(footprint:Rect,pattern:WorkFloor['pattern'],color:number,accent:number):WorkFloor=>({footprint,pattern,color,accent});

/** Distinct plans follow the original scene identities (oven café, central service
 * stations, classroom rows, reading tables, nursery mat and outdoor farm beds).
 * The lower edge deliberately reserves every legacy decoration/property anchor.
 */
export function workLayout(family:string,career=''):WorkLayout{
  let id='retail';
  if(['cafe','teabar','sidewalk','pho','comtam','kitchen'].includes(family))id=family;
  else if(['office','classroom','library','nursery','farm','pagoda','lodging'].includes(family))id=family;
  else if(['drugstore','ward'].includes(family))id='clinic';
  else if(family==='service')id='service';
  else if(['home','flat'].includes(family))id='home';
  else if(['street','airfield','rig','lighthouse','dispatch','station','pool','lane'].includes(family))id='transport';
  else if(['booth','albumshop'].includes(family))id='studio';
  const warm=0xbc9972,mint=0x93b9a6,cream=0xe9d6af,blue=0x8baab7;
  const result:WorkLayout={id,identity:{focus:'Chuẩn bị và bàn giao công việc',workbench:'Bàn làm việc',zones:['Chuẩn bị','Bàn giao']},spawn:{x:6.4,y:6.4},bounds:r(.25,.25,9.75,8.75),outdoor:['farm','sidewalk'].includes(id),stations:[],fixtures:[],floors:[floor(r(0,0,10,9),'plank',0xe5cba4,0xd8b98d)]};
  const s=(key:string,kind:WorkFurniture,box:Rect,x:number,y:number,h=62,color=warm)=>result.stations.push(station(key,kind,box,{x,y},h,color));
  const f=(kind:WorkFurniture,box:Rect,h=58,color=warm)=>result.fixtures.push(fixture(kind,box,h,color));
  const zone=(box:Rect,pattern:WorkFloor['pattern'],color:number,accent:number)=>result.floors.push(floor(box,pattern,color,accent));

  if(['cafe','teabar','sidewalk'].includes(id)){
    // A back bar and a separate pastry/tea island leave a diagonal guest aisle.
    s('shelf','display',r(.5,2,1.55,3.9),2,3,85);
    s('workbench',id==='cafe'?'oven':'counter',r(3.1,.65,5.2,1.9),4.2,2.5,80,id==='teabar'?mint:0xb97b60);
    s('counter','counter',r(5.6,3.45,7.9,4.35),6.7,4.9,63,mint);
    s('evidence','board',r(7.1,.55,8.35,1.25),7.6,1.8,89);
    f('desk',r(3.3,3.7,4.25,4.4),40);f('bench',r(.55,7.7,1.35,8.35),33);
    zone(r(.3,.3,8.65,2.25),'checker',0xf3e4ca,0xc3d1b8);
    zone(r(3,3.35,4.5,4.65),'carpet',id==='teabar'?0xdcc5d6:0xd4ae99,0xf2d8b7);
    if(id==='teabar'){f('display',r(5.65,.55,6.3,1.45),106,0xd7b8c0);result.stations.find(p=>p.id==='counter')!.footprint=r(6.2,3.45,8.1,4.35);}
    if(id==='sidewalk'){result.floors[0]=floor(r(0,0,10,9),'stone',0xc5bc9e,0xddd5bb);f('planter',r(8,3,8.5,3.6),34,mint);}
  }else if(['kitchen','pho','comtam'].includes(id)){
    // An L-shaped cooking line faces a low dining table and a front pickup bar.
    s('shelf','shelf',r(.5,1.7,1.5,3.95),1.95,2.7,122);
    s('workbench','stove',r(3.3,.7,6.2,1.8),4.7,2.4,66,0xc6cfbd);
    s('counter','counter',r(6.4,3.5,8.3,4.35),7.2,4.95,63,0xb58568);
    s('evidence','board',r(7.05,.7,8.1,1.5),7.6,2.05,72);
    f('sink',r(6.35,.7,6.85,2.05),63,blue);f('desk',r(3.5,3.6,4.6,4.45),38,cream);
    zone(r(.2,.2,8.65,2.3),'tile',0xe9e9ce,0xc0cdc1);zone(r(3.2,3.3,4.9,4.7),'checker',0xddc2a2,0xf0dbc0);
    if(id==='pho'){result.stations.find(p=>p.id==='workbench')!.footprint=r(4,.7,6.2,1.8);f('stove',r(2.6,1.8,3.2,2.65),72,0xa5bbb4);}
    if(id==='comtam'){result.stations.find(p=>p.id==='counter')!.footprint=r(5.4,3.5,8.3,4.35);f('display',r(2.6,1.8,3.2,2.65),73,cream);}
  }else if(id==='clinic'){
    s('shelf','medicine',r(2.8,.55,5.2,1.35),4,1.9,128,0xbcdad0);
    s('workbench',family==='ward'?'bed':'counter',r(3.5,3.4,5.45,4.3),4.4,4.85,57,0xc3dfd7);
    s('counter','desk',r(6.8,3.6,8.2,4.45),7.45,5,56,0xc3dfd7);
    s('evidence','board',r(6.6,.55,8.25,1.25),7.2,1.8,79,0x8dbbad);
    f(family==='ward'?'bed':'medicine',r(.55,2.1,1.5,3.9),family==='ward'?43:105,0xeceded);f('sink',r(5.75,.55,6.25,1.35),62,0xd5e8e1);
    result.floors[0]=floor(r(0,0,10,9),'tile',0xe4e8dd,0xc6d6cc);zone(r(2.85,2.8,5.85,4.6),'tile',0xcce1d7,0xf4eee1);
  }else if(id==='service'){
    const kind:WorkFurniture=career==='repair'?'tools':career==='pet_care'?'sink':career==='nail'?'desk':'mirror';
    s('shelf','shelf',r(.5,1.75,1.45,3.8),1.95,2.7,105);
    s('workbench',kind,r(3.4,2,4.85,3.1),4.2,3.65,kind==='mirror'?115:62,0xd5b3a1);
    s('counter','desk',r(6.9,3.4,8.25,4.25),7.4,4.85,58,0xc5a283);
    s('evidence','board',r(7,.5,8.35,1.3),7.6,1.9,86);
    f(kind,r(5.45,.6,6.45,1.65),kind==='mirror'?109:58,0xd2b5a7);f('bench',r(2.7,.6,4.4,1.15),34,0xb4c4b0);
    zone(r(3.15,1.7,5.15,3.4),'stone',0xc8c6b7,0xeee1cf);zone(r(6.55,3.05,8.5,4.6),'carpet',0xd4bcb0,0xeed9bf);
  }else if(id==='office'){
    const tax=career==='tax_payroll',corporate=['corp_accounting','group_accounting','hr_admin','secretary','it_helpdesk'].includes(career);
    s('shelf','bookcase',r(.55,1.65,1.5,4.15),2,2.7,123);
    s('workbench','desk',tax?r(3,2.8,5.6,3.65):r(3.15,1.25,5.3,2.45),4.1,tax?4.2:3,63,corporate?mint:warm);
    s('counter','desk',r(6.85,3.35,8.35,4.25),7.5,4.8,60,blue);
    s('evidence','board',r(6.85,.5,8.3,1.2),7.5,1.8,83);
    f(corporate?'desk':'sofa',r(5.65,.65,6.35,1.95),corporate?58:40,blue);f('bench',r(.6,7.65,1.5,8.3),35);
    zone(r(2.9,.95,5.6,tax?4:2.75),tax?'tile':'carpet',0xb1b8ae,0xd8d4c1);zone(r(6.6,3.1,8.6,4.5),'plank',0xd9c4a3,0xcab18c);
  }else if(['home','lodging'].includes(id)){
    s('shelf','shelf',r(.55,2.05,1.5,3.95),1.95,3,119);
    s('workbench',id==='home'?'stove':'desk',r(3,.6,5.75,1.7),4.5,2.25,63,0xc7b192);
    s('counter','counter',r(7.15,3.55,8.3,4.45),7.7,5,61,0xc1a080);
    s('evidence','board',r(6.95,.5,8.2,1.35),7.4,1.9,86);
    f('sofa',r(3.5,3.5,5.4,4.35),43,0xa6b9a1);f(id==='lodging'?'bed':'sink',r(5.9,.65,6.55,2.2),43,0xe3d8c3);
    zone(r(3.05,3.1,5.8,4.7),'carpet',0xd2b9ad,0xefddc2);zone(r(2.7,.3,6.8,2.5),'tile',0xe7dfc4,0xc9ccb4);
  }else if(id==='nursery'){
    s('shelf','display',r(.6,2,1.5,3.8),2,2.8,63,0xd8c0a0);
    s('workbench','desk',r(3.3,3.4,4.65,4.2),4,4.75,34,0xe5c784);
    s('counter','counter',r(7.05,3.7,8.35,4.4),7.7,5,50,0xb3cabc);
    s('evidence','board',r(7,.55,8.2,1.3),7.5,1.9,86);
    f('crib',r(3,.65,5.1,1.9),57,0xe5d3af);f('sofa',r(5.85,.7,6.4,1.85),40,0xd4bcc8);
    zone(r(2.8,2.75,5.65,4.6),'mat',0xf0d3b3,0xbad6cb);zone(r(.35,1.65,1.8,4.1),'mat',0xd8cee1,0xf0dbb1);
  }else if(id==='classroom'){
    s('shelf','bookcase',r(.55,1.9,1.5,4.1),1.95,3,77);
    s('workbench','chalkboard',r(3.2,.45,6.5,.95),4.6,1.55,124,0x658c76);
    s('counter','desk',r(7,3.5,8.3,4.35),7.6,4.9,60);
    s('evidence','board',r(7.05,.5,8.3,1.3),7.6,1.9,97);
    for(const x of [3.25,5.1])for(const y of [2.15,3.85])f('desk',r(x,y,x+1.1,y+.65),37,cream);
    zone(r(2.95,1.9,6.45,4.8),'plank',0xdfc394,0xcba97c);zone(r(.3,1.65,1.75,4.35),'carpet',0xb2c5ac,0xe8dabb);
  }else if(id==='library'){
    s('shelf','bookcase',r(.6,1.85,1.5,4.15),1.95,2.95,135);
    s('workbench','desk',r(3.05,3.5,5.1,4.35),4,4.95,61,0xb4c5ae);
    s('counter','desk',r(6.75,3.5,8.3,4.35),7.5,4.95,61,0xb4c5ae);
    s('evidence','board',r(7.2,.5,8.35,1.25),7.7,1.85,90);
    f('bookcase',r(3,.5,5.6,1.3),132);f('desk',r(5.65,1.65,6.5,2.4),47);f('bookcase',r(6,.5,6.6,1.1),118);
    zone(r(2.8,3.2,8.55,4.65),'carpet',0xbfc2a6,0xe9d5ad);zone(r(5.4,1.4,6.75,2.65),'plank',0xd5b790,0xe8d2ad);
  }else if(id==='farm'){
    s('shelf','display',r(.6,2,1.55,3.9),2,3,84);
    s('workbench','planter',r(3.1,2.15,5.6,3.15),4.2,3.75,24,0x8fa877);
    s('counter','counter',r(7,3.55,8.3,4.4),7.6,4.95,61);
    s('evidence','board',r(7.05,.5,8.35,1.3),7.65,1.9,92);
    f('planter',r(3.1,.55,5.6,1.4),23,0x8fa877);f('crate',r(6,.65,6.55,1.6),50);
    result.floors[0]=floor(r(0,0,10,9),'earth',0xb9c995,0xaabc85);zone(r(1.8,4.6,9,7.45),'earth',0xdfcba3,0xd1b992);zone(r(2.8,.3,5.85,3.4),'earth',0x9d8060,0xb59a6c);
  }else if(id==='pagoda'){
    s('shelf','bookcase',r(.55,1.9,1.45,4.15),1.95,3,113);
    s('workbench','altar',r(3.2,.65,6,1.8),4.6,2.45,81,0xbd835b);
    s('counter','desk',r(7,3.55,8.3,4.45),7.6,5,57);
    s('evidence','board',r(7,.5,8.3,1.35),7.6,1.95,90);
    f('bench',r(3.2,3.8,4.65,4.35),24,0xba9a78);f('bench',r(5.35,3.8,6.45,4.35),24,0xba9a78);
    zone(r(2.8,.3,6.4,2.05),'stone',0xc4b99e,0xe2d4b3);zone(r(2.9,3.4,6.65,4.7),'mat',0xd2b797,0xe9d3ae);
  }else if(id==='transport'){
    s('shelf','routeboard',r(.55,2.1,1.4,4.1),1.95,3,114,blue);
    s('workbench','desk',r(3.2,1.8,5.5,2.85),4.25,3.45,66,blue);
    s('counter','counter',r(6.95,3.55,8.3,4.35),7.6,4.95,60,0xc9b294);
    s('evidence','routeboard',r(6.9,.55,8.3,1.25),7.6,1.85,108,blue);
    f('crate',r(2.7,.5,4.7,1.15),66);f('bench',r(5.7,.6,6.35,1.75),38);
    result.floors[0]=floor(r(0,0,10,9),'stone',0xd6d4c4,0xc1c9bf);zone(r(2.95,1.55,5.75,3.1),'carpet',0xa4b7bd,0xdbe1cf);zone(r(6.7,3.3,8.55,4.6),'tile',0xd9c9a9,0xeddfc3);
    if(['street','lane'].includes(family)){result.stations.find(p=>p.id==='workbench')!.kind='crate';f('crate',r(5.75,3.7,6.25,4.3),44);}
    if(['lighthouse','pool'].includes(family))f('planter',r(5.75,3.7,6.25,4.3),32,mint);
  }else if(id==='studio'){
    s('shelf','display',r(.55,1.8,1.5,4.05),1.95,3,113,0xbea5b4);
    s('workbench','display',r(3.35,1.1,5.25,2.25),4.3,2.85,111,0xb4c3ce);
    s('counter','desk',r(6.9,3.5,8.3,4.3),7.6,4.9,59,0xd0b1b9);
    s('evidence','board',r(7,.55,8.2,1.25),7.5,1.85,93,0xc1b1c4);
    f('sofa',r(3.3,3.8,5.25,4.4),40,0xd6b5c2);f('display',r(5.9,.6,6.4,1.8),90);
    zone(r(3,.8,5.6,2.6),'checker',0xe6dbe5,0xc6c4d6);zone(r(3,3.5,5.5,4.65),'carpet',0xcbb8cc,0xefe0d3);
  }else{
    const shelf:WorkFurniture=family==='flowershop'?'planter':family==='boutique'?'display':'shelf';
    s('shelf',shelf,r(.55,1.8,1.55,4.2),2,3,118);
    s('workbench','counter',r(3.05,3.45,5.5,4.3),4.3,4.9,62,0xb5c6ad);
    s('counter','desk',r(6.95,3.45,8.3,4.3),7.6,4.9,62,0xcbb090);
    s('evidence','board',r(7,.55,8.3,1.25),7.6,1.85,87);
    f(shelf,r(2.9,.55,5.5,1.35),family==='flowershop'?33:100);f('display',r(5.95,.6,6.5,1.7),82);
    zone(r(2.8,3.2,5.75,4.55),'checker',0xf0dfbd,0xc4d0ad);zone(r(2.65,.3,6.7,1.6),'plank',0xdcc299,0xc4a179);
    if(family==='babyshop')f('crib',r(3.4,1.9,4.85,2.65),49,0xd6bc9d);
    if(family==='petshop')f('display',r(3.45,1.95,4.8,2.65),60,0xaac7c7);
  }
  // The occupational plan replaces only the work area. Shared stations and the
  // saved decoration edge below retain their stable IDs and anchors.
  applyCareerPlan(result,career);
  // Shared structural utilities stay outside changing work areas and legacy décor.
  const storage:WorkFurniture=id==='clinic'?'medicine':['office','library','classroom','pagoda'].includes(id)?'bookcase':id==='service'?'tools':['nursery','studio','home','lodging'].includes(id)?'display':'crate';
  s('warehouse',storage,r(.5,6.2,1.5,7.25),1.95,6.75,storage==='crate'?62:84,id==='clinic'?0xbcdad0:warm);
  s('board','board',r(.55,.45,1.35,1.05),1.85,1.15,105);
  s('door','door',r(9.1,5.6,9.65,6.5),8.65,6.15,110);
  result.stations.push(
    {id:'pet',kind:'bench',at:{x:2.2,y:7.75},approach:{x:2.5,y:7.3},height:30,color:warm},
    {id:'ops:finance',kind:'board',at:{x:9.35,y:1.5},approach:{x:9,y:2.3},height:85,color:warm},
    {id:'ops:property',kind:'board',at:{x:0,y:5.5},approach:{x:2.05,y:5.95},height:105,color:warm},
    {id:'ops:security',kind:'board',at:{x:1,y:.25},approach:{x:2,y:.6},height:135,color:warm},
  );
  for(const station of result.stations)if(station.footprint)station.at={x:(station.footprint.x0+station.footprint.x1)/2,y:station.footprint.y1};
  result.architecture=workArchitecture(result,career);
  return result;
}

/** These fixed rectangles match savedRoomDetails, preserving existing spot saves. */
export function workNavigation(layout:WorkLayout,appearance:RoomAppearance):Navigation{
  const obstacles=[...layout.stations.flatMap(s=>s.footprint?[s.footprint]:[]),...layout.fixtures.map(f=>f.footprint),...appearance.decor.flatMap(d=>d.footprint?[d.footprint]:[])];
  if(appearance.tier!=='cozy')obstacles.push(r(3.05,7.85,4.55,8.4));
  if(appearance.tier==='garden')for(const x of [5.95,6.65])obstacles.push(r(x-.23,8.02,x+.23,8.48));
  if(appearance.tools.includes('shelf'))obstacles.push(r(.65,4.75,1.7,5.65));
  return makeNavigation({bounds:layout.bounds,roads:[layout.bounds],obstacles,step:.25});
}
export const workActorFootprint=(p:Point):Rect=>r(p.x-.27,p.y-.2,p.x+.27,p.y+.2);

/** SceneFx targets are semantic names, not furniture IDs. Actors and debris belong
 * on a station's free approach; ball impacts remain on the actual window glass.
 * Read the rendered hotspots so later room/actor placement cannot leave stale FX.
 */
export function workEventAnchors(stations:readonly {id:string;approach:Point}[]):Record<string,[number,number]>{
  const at=(id:string)=>stations.find(s=>s.id===id)?.approach||{x:6.4,y:6.4};
  const pixels=(p:Point):[number,number]=>{const q=project(p);return [q.x,q.y];};
  const door=at('door'),window=workWindowAnchors();
  return {
    shelf:pixels(at('shelf')),till:pixels(at('counter')),table:pixels(at('workbench')),door:pixels(door),
    out:pixels({x:door.x+2.35,y:door.y+1.85}),street:pixels({x:door.x+1.35,y:door.y+1.85}),car:pixels({x:door.x+1.35,y:door.y+.85}),
    window:[window.window.x,window.window.y],glass:[window.glass.x,window.glass.y],
  };
}

/** NPCs are temporary solid furniture too. Reserve every interaction approach,
 * including those of earlier visitors, before accepting the next standing spot.
 */
export function workActorPositions(layout:WorkLayout,navigation:Navigation,count:number):Point[]{
  const nav={...navigation,obstacles:[...navigation.obstacles]},points:Point[]=[],approaches=layout.stations.map(s=>s.approach);
  const candidates:Point[]=[{x:8.6,y:7.35},{x:7.8,y:6.65},{x:3.65,y:6.5},{x:5.9,y:5.6},{x:8.25,y:5.5}];
  for(const y of [5.8,4.95,3.15,2.25,6.85,7.4,1.7])for(const x of [3.55,4.8,6.15,7.5,8.75])candidates.push({x,y});
  for(const at of candidates){
    if(points.length>=count)break;
    const approach={x:at.x-.6,y:at.y+.35};
    if(!isWalkable(nav,at)||!isWalkable(nav,approach)||Math.hypot(at.x-layout.spawn.x,at.y-layout.spawn.y)<.8)continue;
    const next={...nav,obstacles:[...nav.obstacles,workActorFootprint(at)]};
    if([...approaches,approach].some(p=>!isWalkable(next,p)||!findRoute(next,layout.spawn,p).length))continue;
    nav.obstacles=next.obstacles;points.push(at);approaches.push(approach);
  }
  return points;
}
