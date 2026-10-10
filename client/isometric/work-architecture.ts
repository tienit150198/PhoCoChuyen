import {project,WORK_WINDOW} from './model';
import type {Point,Rect} from './model';
import type {WorkLayout} from './work-layout';

export type WallFinish='lime'|'brick'|'ceramic'|'timber'|'glazing'|'acoustic'|'metal'|'bamboo'|'stone';
export type WallOpening='sash'|'arch'|'clerestory'|'porthole'|'ribbon'|'shutter'|'lattice'|'open';
export type WallCrest='flat'|'gable'|'step'|'bow';
export type ArchitecturalFitting='plinth'|'glass-screen'|'timber-screen'|'privacy-curtain'|'extractor'|'service-hatch'|'pigeonholes'|'canopy'|'handrail'|'pipe-chase'|'trellis'|'cabin-ribs'|'pegwall'|'hanging-rail'|'lightbox'|'wash-splash'|'acoustic-baffle'|'arched-niche'|'sorting-cubbies'|'display-steps';
export interface WorkWall {from:Point;to:Point;height:number;finish:WallFinish;opening?:WallOpening;crest:WallCrest}
export interface WorkArchitecturalElement {kind:ArchitecturalFitting;footprint:Rect;height:number}
export interface WorkArchitecture {career:string;outline:Point[];walls:WorkWall[];elements:WorkArchitecturalElement[];window:typeof WORK_WINDOW;floor:number}
export interface ArchitectureInk {polygon(points:Point[],color:number,alpha?:number):void;line(from:Point,to:Point,color:number,width:number,alpha?:number):void}
type XY=readonly [number,number];
type Fit=readonly [anchor:string,kind:ArchitecturalFitting,height:number];
interface Plan {edge:readonly XY[];height:number;finish:WallFinish;opening:WallOpening;crest:WallCrest;fits:readonly Fit[];floor:number}
const plan=(edge:readonly XY[],height:number,finish:WallFinish,opening:WallOpening,crest:WallCrest,fits:readonly Fit[],floor=0xd8c09b):Plan=>({edge,height,finish,opening,crest,fits,floor});

/** These are authored cutaway profiles, not an indexed/random room generator.
 * Each profile runs from the front-left cut to the back-right cut. Alcoves extend
 * outward so the old 10×9 walkable room, saved sill and all approaches survive.
 * The middle back-wall panel at x 4.1–6.9 carries the saved, breakable window.
 * Fittings resolve against actual furniture; they cannot create hidden blockers.
 */
const PLANS:Record<string,Plan>={
  // Tea: a glazed brewing bay and a low open pickup wing. Bakery: a deep brick
  // oven apse. Restaurant: two tiled service returns under a stepped hot-line wall.
  milk_tea:plan([[0,9],[0,5],[-.65,5],[-.65,1],[0,0],[1.5,-.8],[3.4,-.8],[4.1,0],[6.9,0],[8,-.45],[10,-.45],[10,0]],180,'glazing','ribbon','flat',[['workbench','pipe-chase',102],['fixture0','display-steps',32],['shelf','lightbox',118]],0xe3d5b4),
  cafe_bakery:plan([[0,9],[0,6.4],[-.35,6.4],[-.35,0],[1,-.5],[1.4,-1.25],[3.5,-1.25],[4.1,0],[6.9,0],[8.5,0],[8.5,-.6],[10,-.6],[10,0]],208,'brick','arch','gable',[['workbench','arched-niche',166],['workbench','extractor',194],['shelf','display-steps',38]],0xcbb089),
  restaurant:plan([[0,9],[0,4.3],[-.8,4.3],[-.8,2],[0,2],[0,-.55],[3.3,-.55],[4.1,0],[6.9,0],[7.2,-1],[10,-1],[10,0]],192,'ceramic','clerestory','step',[['workbench','extractor',172],['shelf','hanging-rail',148],['fixture0','wash-splash',94]],0xd6c8a7),
  grocery:plan([[0,9],[0,6.5],[-1,6.5],[-1,1.3],[0,1.3],[0,-.35],[2.8,-.35],[2.8,-.8],[3.5,-.8],[4.1,0],[6.9,0],[9.1,0],[10,-.6],[10,0]],168,'timber','shutter','step',[['fixture0','sorting-cubbies',144],['fixture1','canopy',137],['shelf','display-steps',42]],0xd8bd95),
  florist:plan([[0,9],[0,5.4],[-.8,4.5],[-.8,1],[.4,-.9],[2,-1.5],[3.5,-.9],[4.1,0],[6.9,0],[8,-.85],[9.4,-.85],[10,0]],186,'glazing','lattice','gable',[['fixture0','trellis',156],['fixture1','trellis',132],['workbench','hanging-rail',118]],0xd7cda8),
  mother_baby:plan([[0,9],[0,7],[-.55,7],[-.55,3],[0,3],[0,0],[1.3,-.9],[3.2,-.9],[4.1,0],[6.9,0],[7.3,-.5],[9.3,-.5],[10,0]],184,'lime','arch','bow',[['fixture2','canopy',142],['shelf','arched-niche',156],['workbench','display-steps',25]],0xe3d0ac),
  pharmacy:plan([[0,9],[0,6],[-.35,6],[-.35,0],[1.7,0],[1.7,-1],[3.7,-1],[4.1,0],[6.9,0],[7.3,-.65],[10,-.65],[10,0]],202,'ceramic','sash','step',[['shelf','sorting-cubbies',161],['workbench','glass-screen',96],['counter','service-hatch',132]],0xd8d8bc),
  salon:plan([[0,9],[0,6.7],[-.9,6.7],[-.9,3.3],[-.3,2.7],[-.3,0],[1.4,-.6],[3.4,-.6],[4.1,0],[6.9,0],[9,-1],[10,0]],198,'lime','arch','bow',[['workbench','arched-niche',154],['fixture0','arched-niche',148],['fixture1','wash-splash',91]],0xddc9b0),
  pet_care:plan([[0,9],[0,5.5],[-.5,5.5],[-.5,2],[0,2],[0,-.9],[2.8,-.9],[4.1,0],[6.9,0],[7.8,-.6],[9,-.6],[10,0]],160,'ceramic','porthole','flat',[['workbench','wash-splash',111],['fixture1','timber-screen',73],['fixture2','arched-niche',119]],0xd4d2b3),
  repair:plan([[0,9],[0,7.2],[-.75,7.2],[-.75,1.5],[0,1.5],[0,-.65],[3.5,-.65],[4.1,0],[6.9,0],[7.3,-1.1],[10,-1.1],[10,0]],220,'brick','clerestory','step',[['fixture0','pegwall',184],['workbench','lightbox',118],['fixture1','pipe-chase',138]],0xc3b69b),
  nail:plan([[0,9],[0,6.2],[-.4,6.2],[-.4,1.6],[.2,-.2],[1.8,-.8],[3.3,-.8],[4.1,0],[6.9,0],[8.3,-.3],[9.1,-.3],[10,0]],166,'lime','ribbon','flat',[['workbench','glass-screen',74],['fixture0','display-steps',112],['fixture1','lightbox',96]],0xe2cdbd),
  teacher:plan([[0,9],[0,4.6],[-.45,4.6],[-.45,0],[.8,-.7],[3.3,-.7],[4.1,0],[6.9,0],[7.5,-1.15],[9.5,-1.15],[10,0]],204,'timber','sash','gable',[['workbench','plinth',14],['shelf','pigeonholes',111],['fixture0','timber-screen',65]],0xd4bd92),
  // Eight office departments have different spatial organizations: archive apse,
  // double team bays, private payroll screens, tiered reporting gallery, call pods,
  // interview room, vestibule/waiting suite, and ventilated equipment enclosure.
  accounting:plan([[0,9],[0,6.2],[-.75,6.2],[-.75,3.6],[0,3.6],[0,0],[.8,-.65],[3.25,-.65],[4.1,0],[6.9,0],[7.8,-.25],[10,-.25],[10,0]],192,'timber','sash','gable',[['fixture0','arched-niche',153],['workbench','pigeonholes',99],['fixture1','glass-screen',77]],0xcfbb98),
  corp_accounting:plan([[0,9],[0,7],[-.45,7],[-.45,4.5],[-1.05,4.5],[-1.05,1],[0,0],[1.3,-.45],[3.3,-.45],[4.1,0],[6.9,0],[7.3,-.9],[10,-.9],[10,0]],184,'glazing','ribbon','flat',[['workbench','pigeonholes',110],['fixture0','glass-screen',98],['fixture1','glass-screen',98]],0xd5cbbb),
  tax_payroll:plan([[0,9],[0,6.6],[-.65,6.6],[-.65,2.5],[0,2.5],[0,-.3],[2,-.3],[2,-1],[3.65,-1],[4.1,0],[6.9,0],[8,-.65],[9.4,-.65],[10,0]],178,'acoustic','clerestory','step',[['workbench','timber-screen',97],['fixture0','sorting-cubbies',151],['fixture1','acoustic-baffle',127]],0xd0c4aa),
  group_accounting:plan([[0,9],[0,5.8],[-.35,5.8],[-.35,2.5],[-.9,2.5],[-.9,0],[.7,-1],[3.45,-1],[4.1,0],[6.9,0],[7.5,-.5],[8.4,-.5],[8.4,-1.15],[10,-1.15],[10,0]],222,'timber','clerestory','step',[['fixture0','plinth',14],['fixture1','plinth',14],['fixture2','plinth',14],['fixture3','plinth',14],['workbench','lightbox',114]],0xd7c8ac),
  customer_care:plan([[0,9],[0,6.5],[-.8,6.5],[-.8,4.5],[-.25,4.5],[-.25,1.5],[-.8,1.5],[-.8,-.35],[3.25,-.35],[4.1,0],[6.9,0],[7.2,-.75],[8.3,-.75],[8.3,-.3],[10,-.3],[10,0]],176,'acoustic','porthole','bow',[['workbench','acoustic-baffle',136],['fixture0','acoustic-baffle',126],['fixture1','timber-screen',88]],0xd3cdb3),
  hr_admin:plan([[0,9],[0,7],[-.9,7],[-.9,3],[0,3],[0,0],[1,-.3],[1,-1.2],[3.5,-1.2],[4.1,0],[6.9,0],[8.9,0],[8.9,-.8],[10,-.8],[10,0]],188,'lime','shutter','flat',[['fixture0','glass-screen',112],['fixture1','timber-screen',85],['fixture2','timber-screen',85],['workbench','pigeonholes',97]],0xd6c5a6),
  secretary:plan([[0,9],[-.55,8.4],[-.55,5.2],[0,4.6],[0,0],[.7,-.7],[2.8,-.7],[4.1,0],[6.9,0],[7.7,-1.05],[9.3,-1.05],[10,0]],210,'lime','arch','gable',[['workbench','service-hatch',115],['fixture1','canopy',133],['fixture2','pigeonholes',109]],0xddc6a7),
  it_helpdesk:plan([[0,9],[0,6.8],[-.4,6.8],[-.4,3.4],[-1,3.4],[-1,-.7],[2.6,-.7],[2.6,-.25],[4.1,0],[6.9,0],[7.2,-1.2],[10,-1.2],[10,0]],212,'metal','ribbon','step',[['shelf','cabin-ribs',171],['fixture0','pipe-chase',173],['workbench','pegwall',115],['fixture1','lightbox',121]],0xc6c4af),
  farm:plan([[0,9],[0,6],[-1.1,6],[-1.1,1],[0,-.8],[2.6,-.8],[4.1,0],[6.9,0],[8.2,-1.35],[10,-1.35],[10,0]],100,'bamboo','open','gable',[['fixture0','trellis',151],['workbench','trellis',121],['shelf','canopy',140]],0xbfc396),
  delivery:plan([[0,9],[0,7.6],[-1,7.6],[-1,2],[0,2],[0,-.5],[1.5,-.5],[1.5,-1.2],[3.3,-1.2],[4.1,0],[6.9,0],[7.8,-.85],[10,-.85],[10,0]],222,'brick','shutter','step',[['fixture0','sorting-cubbies',117],['fixture1','sorting-cubbies',147],['fixture2','sorting-cubbies',117],['workbench','lightbox',116]],0xc8b79c),
  tour_guide:plan([[0,9],[0,5.1],[-.8,4.3],[-.8,1.4],[.4,-.8],[2.8,-1.3],[4.1,0],[6.9,0],[7.8,-.4],[9,-.4],[10,0]],150,'stone','open','gable',[['workbench','canopy',163],['fixture0','handrail',67],['shelf','lightbox',133]],0xcac2a1),
  homestay:plan([[0,9],[0,6.8],[-.85,6.8],[-.85,2.6],[0,2.6],[0,-.65],[1.2,-1.25],[3.1,-1.25],[4.1,0],[6.9,0],[7.8,-.6],[9.2,-.6],[10,0]],208,'timber','shutter','gable',[['fixture0','canopy',163],['fixture1','timber-screen',98],['workbench','pigeonholes',112]],0xd7ba92),
  homemaker:plan([[0,9],[-.45,8.55],[-.45,5.6],[0,5.15],[0,0],[1.1,-1.1],[3.3,-1.1],[4.1,0],[6.9,0],[7.5,-.5],[9.5,-.5],[10,0]],186,'lime','sash','gable',[['workbench','wash-splash',96],['fixture0','timber-screen',103],['fixture1','hanging-rail',117]],0xe1cbaa),
  naucom:plan([[0,9],[0,6.3],[-.55,6.3],[-.55,0],[.9,-.35],[.9,-.9],[3,-.9],[4.1,0],[6.9,0],[7.8,-.8],[10,-.8],[10,0]],174,'ceramic','lattice','flat',[['workbench','extractor',145],['fixture0','wash-splash',101],['fixture1','canopy',105]],0xdcc6a4),
  tra_da:plan([[0,9],[0,6],[-.7,5.3],[-.7,1.8],[0,.7],[0,-.3],[3.2,-.3],[4.1,0],[6.9,0],[7.6,-.6],[8.5,-.6],[10,0]],81,'bamboo','open','flat',[['workbench','canopy',156],['fixture0','trellis',111],['shelf','hanging-rail',128]],0xc6bc97),
  clothing:plan([[0,9],[0,6.9],[-.75,6.9],[-.75,1.5],[0,1.5],[0,-.3],[1.5,-1.05],[3.3,-1.05],[4.1,0],[6.9,0],[7.4,-.7],[9.4,-.7],[10,0]],197,'lime','arch','bow',[['fixture0','hanging-rail',163],['fixture1','privacy-curtain',155],['workbench','display-steps',27]],0xddc6b0),
  pet_shop:plan([[0,9],[0,6.1],[-1,6.1],[-1,3.2],[0,3.2],[0,-.65],[2.3,-.65],[3.3,-.25],[4.1,0],[6.9,0],[7.9,-1],[9.1,-1],[10,0]],170,'timber','porthole','step',[['fixture2','arched-niche',111],['shelf','sorting-cubbies',149],['fixture0','hanging-rail',122]],0xd2c5a0),
  fruit:plan([[0,9],[0,5.7],[-.7,5.7],[-.7,1.3],[.5,-.5],[1.8,-1.1],[3.1,-1.1],[4.1,0],[6.9,0],[8.4,-.8],[10,0]],96,'timber','open','gable',[['fixture0','canopy',137],['fixture1','canopy',137],['workbench','display-steps',34]],0xcfc49a),
  garbage:plan([[0,9],[0,7.4],[-.9,7.4],[-.9,0],[1.5,-.7],[3.4,-.7],[4.1,0],[6.9,0],[7.1,-1.3],[10,-1.3],[10,0]],110,'brick','open','step',[['fixture0','wash-splash',119],['fixture1','wash-splash',119],['fixture2','wash-splash',119],['workbench','handrail',91]],0xbfc2a6),
  drain:plan([[0,9],[0,6.6],[-.55,6.6],[-.55,3.1],[-1.1,3.1],[-1.1,-.45],[3.2,-.45],[4.1,0],[6.9,0],[7.4,-.95],[8.7,-.95],[10,0]],132,'stone','shutter','flat',[['fixture0','pipe-chase',121],['workbench','pegwall',136],['fixture1','wash-splash',104]],0xc7c1a6),
  ice_cream:plan([[0,9],[0,6.3],[-.65,6.3],[-.65,2.7],[0,2.7],[0,-.45],[1.3,-.95],[3,-.95],[4.1,0],[6.9,0],[7.8,-.25],[9.6,-.25],[10,0]],142,'ceramic','porthole','bow',[['workbench','canopy',151],['fixture0','display-steps',97],['shelf','lightbox',125]],0xe1d2b7),
  com:plan([[0,9],[0,5.9],[-.35,5.9],[-.35,2],[-.85,2],[-.85,-.7],[2.9,-.7],[4.1,0],[6.9,0],[7.8,-1.1],[10,-1.1],[10,0]],180,'brick','shutter','flat',[['workbench','extractor',157],['counter','service-hatch',117],['fixture2','display-steps',98]],0xd0b590),
  pagoda:plan([[0,9],[0,6.5],[-.9,6.5],[-.9,0],[.8,-1.25],[3.3,-1.25],[4.1,0],[6.9,0],[7.7,-1.25],[9.2,-1.25],[10,0]],234,'timber','lattice','gable',[['workbench','plinth',17],['workbench','canopy',203],['fixture0','timber-screen',62],['fixture1','timber-screen',62]],0xcab088),
  pho:plan([[0,9],[0,5.3],[-.65,5.3],[-.65,0],[1,-.4],[1,-1.05],[3.45,-1.05],[4.1,0],[6.9,0],[7.5,-.3],[10,-.3],[10,0]],190,'ceramic','lattice','step',[['workbench','pipe-chase',137],['fixture2','extractor',151],['shelf','hanging-rail',158]],0xd6c8a9),
  photobooth:plan([[0,9],[0,7.3],[-.6,7.3],[-.6,3.3],[0,3.3],[0,-.9],[.8,-.9],[.8,-1.45],[3.3,-1.45],[4.1,0],[6.9,0],[7.7,-.7],[10,-.7],[10,0]],202,'acoustic','porthole','flat',[['workbench','privacy-curtain',166],['workbench','lightbox',185],['fixture0','lightbox',121]],0xd8c5bd),
  giupviec:plan([[0,9],[0,7.1],[-.5,7.1],[-.5,2.4],[0,2.4],[0,-.8],[2,-.8],[2,-.3],[4.1,0],[6.9,0],[7.6,-1],[9.3,-1],[10,0]],168,'ceramic','shutter','flat',[['fixture0','hanging-rail',132],['fixture1','sorting-cubbies',151],['shelf','wash-splash',110]],0xd8d0b0),
  babysitter:plan([[0,9],[0,7.5],[-.8,7.5],[-.8,3.8],[0,3.8],[0,-.25],[.8,-.8],[3,-.8],[4.1,0],[6.9,0],[7.6,-.65],[8.9,-.65],[10,0]],164,'lime','arch','bow',[['fixture0','canopy',135],['fixture1','timber-screen',81],['shelf','arched-niche',105]],0xe4d1b0),
  library:plan([[0,9],[0,6.7],[-.4,6.7],[-.4,4],[-1,4],[-1,.8],[.3,-.8],[1.4,-1.35],[3.4,-1.35],[4.1,0],[6.9,0],[7.6,-1.1],[9.3,-1.1],[10,0]],232,'timber','arch','gable',[['fixture0','arched-niche',176],['fixture2','arched-niche',163],['fixture1','lightbox',102],['workbench','pigeonholes',116]],0xc9b18d),
  pilot:plan([[0,9],[0,6.2],[-.35,5.5],[-.35,2.4],[0,1.5],[0,-.25],[.7,-1.2],[2.8,-1.65],[3.6,-.9],[4.1,0],[6.9,0],[7.6,-.7],[9.1,-.35],[10,0]],186,'metal','ribbon','bow',[['workbench','cabin-ribs',158],['workbench','lightbox',118],['fixture0','handrail',79],['fixture1','handrail',79]],0xc6c5b3),
  flight_attendant:plan([[0,9],[-.3,8.5],[-.7,6.8],[-.7,1.8],[-.3,.3],[.3,-.5],[3.3,-.5],[4.1,0],[6.9,0],[7.4,-.4],[9.3,-.4],[10,0]],180,'metal','porthole','bow',[['fixture0','cabin-ribs',163],['fixture1','cabin-ribs',163],['fixture2','cabin-ribs',163],['fixture3','cabin-ribs',163],['workbench','sorting-cubbies',119]],0xd6ceba),
  oil:plan([[0,9],[0,7.3],[-1.2,7.3],[-1.2,1.4],[0,1.4],[0,-1],[3.1,-1],[4.1,0],[6.9,0],[7.1,-1.45],[10,-1.45],[10,0]],132,'metal','open','step',[['fixture0','pipe-chase',197],['fixture1','handrail',93],['workbench','canopy',153]],0xb8b5a0),
  railway:plan([[0,9],[0,6.1],[-1,6.1],[-1,3.5],[0,3.5],[0,-.4],[1.2,-1.15],[3.2,-1.15],[4.1,0],[6.9,0],[8.2,-.7],[9.5,-.7],[10,0]],164,'brick','sash','gable',[['workbench','canopy',139],['fixture0','handrail',62],['shelf','pegwall',147]],0xc9bfa2),
  nurse:plan([[0,9],[0,6.4],[-.3,6.4],[-.3,2],[-.75,2],[-.75,-.6],[1.2,-.6],[1.2,-1.1],[3.5,-1.1],[4.1,0],[6.9,0],[7.4,-.85],[10,-.85],[10,0]],198,'ceramic','clerestory','flat',[['fixture0','privacy-curtain',146],['fixture1','privacy-curtain',146],['fixture2','wash-splash',106],['workbench','glass-screen',92]],0xd9dbc2),
  lighthouse:plan([[0,9],[0,5.5],[-.6,4.9],[-1.2,2.9],[-1.2,.6],[-.3,-.7],[1.2,-1.4],[2.9,-1.4],[3.6,-.6],[4.1,0],[6.9,0],[7.5,-.6],[9.1,-.6],[10,0]],142,'stone','porthole','bow',[['fixture0','handrail',112],['fixture0','plinth',18],['fixture1','pipe-chase',164],['workbench','canopy',146]],0xc3b99c),
  rescue:plan([[0,9],[0,6.9],[-.7,6.9],[-.7,3.8],[-1.2,3.8],[-1.2,-.6],[3.1,-.6],[4.1,0],[6.9,0],[7.5,-1.2],[9.5,-1.2],[10,0]],216,'acoustic','clerestory','step',[['fixture0','lightbox',169],['workbench','acoustic-baffle',127],['fixture2','lightbox',121]],0xc9c7af),
  lifeguard:plan([[0,9],[0,6.8],[-.8,6],[-.8,1.6],[.5,-1],[3,-1],[4.1,0],[6.9,0],[7.4,-.55],[9,-.55],[10,0]],91,'ceramic','open','flat',[['fixture0','handrail',37],['fixture1','canopy',161],['workbench','lightbox',107]],0xd2d3b4),
  police:plan([[0,9],[0,7.2],[-.7,7.2],[-.7,2.7],[0,2.7],[0,-.75],[1.7,-.75],[1.7,-1.2],[3.4,-1.2],[4.1,0],[6.9,0],[7.8,-.9],[9.6,-.9],[10,0]],200,'lime','sash','step',[['workbench','service-hatch',128],['fixture0','timber-screen',89],['shelf','sorting-cubbies',155]],0xd0c1a4),
  zpop:plan([[0,9],[0,7.4],[-.8,7.4],[-.8,2.2],[-.3,1.7],[-.3,-.5],[1.1,-1.1],[3.4,-1.1],[4.1,0],[6.9,0],[7.5,-.35],[8.6,-.35],[8.6,-1],[10,-1],[10,0]],206,'acoustic','ribbon','step',[['fixture0','lightbox',151],['fixture1','plinth',14],['shelf','display-steps',143],['workbench','glass-screen',83]],0xd6c2b2),
};
export const WORK_ARCHITECTURE_CAREERS:readonly string[]=Object.freeze(Object.keys(PLANS));

export function workArchitecture(layout:WorkLayout,career:string):WorkArchitecture{
  const p=PLANS[career]||PLANS.grocery,edge=p.edge.map(([x,y])=>({x,y}));
  const walls:WorkWall[]=edge.slice(1).map((to,i)=>{
    const from=edge[i],length=Math.hypot(to.x-from.x,to.y-from.y),sill=from.x===4.1&&to.x===6.9&&from.y===0&&to.y===0;
    // The forward side is a low cutaway, long rear walls carry the occupation's
    // windows. The preserved central opening is painted by the existing renderer.
    const front=Math.min(from.y,to.y)>4.4;
    return {from,to,height:front?Math.min(94,p.height):sill&&!layout.outdoor?Math.max(184,p.height):p.height,finish:p.finish,opening:front||sill?undefined:length>1.6?p.opening:undefined,crest:front||sill||length<1.6?'flat':p.crest};
  });
  const elements=p.fits.map(([anchor,kind,height])=>{
    const item=anchor.startsWith('fixture')?layout.fixtures[Number(anchor.slice(7))]:layout.stations.find(s=>s.id===anchor);
    if(!item?.footprint)throw new Error(`Architecture ${career}: missing furniture anchor ${anchor}`);
    return {kind,footprint:{...item.footprint},height};
  });
  return {career,outline:[...edge,{x:10,y:9}],walls,elements,window:{...WORK_WINDOW},floor:p.floor};
}

/** A dais supports only its own furniture. It never raises an interaction
 * approach or changes any saved ground coordinate. */
export function workFurnitureElevation(a:WorkArchitecture,footprint:Rect):number{
  return a.elements.reduce((height,e)=>e.kind==='plinth'&&e.footprint.x0===footprint.x0&&e.footprint.y0===footprint.y0&&e.footprint.x1===footprint.x1&&e.footprint.y1===footprint.y1?Math.max(height,e.height):height,0);
}

const shade=(c:number,f:number)=>Math.round(Math.min(255,(c>>16)*f))*65536+Math.round(Math.min(255,(c>>8&255)*f))*256+Math.round(Math.min(255,(c&255)*f));
const px=(p:Point,z=0)=>{const q=project(p);return {x:q.x,y:q.y-z};};
const lerp=(a:Point,b:Point,t:number):Point=>({x:a.x+(b.x-a.x)*t,y:a.y+(b.y-a.y)*t});
const finishes:Record<WallFinish,number>={lime:0xe7d4b6,brick:0xc39478,ceramic:0xdbe0c8,timber:0xc5a37b,glazing:0xc6dacf,acoustic:0xc4bdb0,metal:0xb9c4b7,bamboo:0xc4b383,stone:0xc2b99c};

/** Pure drawing commands let both the Phaser scene and geometry/contact-sheet
 * tests consume the exact same art. Calls occur only on scene rebuild; Graphics
 * are baked by the existing viewport ground cache, behind actors and hit targets.
 */
export function drawWorkArchitecture(a:WorkArchitecture,ink:ArchitectureInk,pass:'base'|'walls'|'fittings',wallTint=0xe7d4b6):void{
  const line=(p:Point,q:Point,c:number,w=2,alpha=1)=>ink.line(p,q,c,w,alpha);
  const poly=(points:Point[],c:number,alpha=1)=>ink.polygon(points,c,alpha);
  const surface=(box:Rect,z=0)=>[px({x:box.x0,y:box.y0},z),px({x:box.x1,y:box.y0},z),px({x:box.x1,y:box.y1},z),px({x:box.x0,y:box.y1},z)];
  const block=(box:Rect,z:number,h:number,c:number)=>{const b=surface(box,z),t=surface(box,z+h);poly([t[1],b[1],b[2],t[2]],shade(c,.78));poly([t[2],b[2],b[3],t[3]],shade(c,.92));poly(t,shade(c,1.05));};
  if(pass==='base'){
    const outline=a.outline.map(p=>px(p));poly(outline.map(p=>({x:p.x+5,y:p.y+22})),0x766343,.13);
    for(let i=0;i<a.outline.length;i++){const p=a.outline[i],q=a.outline[(i+1)%a.outline.length];poly([px(p),px(q),px(q,-18),px(p,-18)],shade(a.floor,q.y>p.y?.79:.9));}
    poly(outline,a.floor);return;
  }
  const face=(from:Point,to:Point,height:number,color:number,crest:WallCrest='flat')=>{
    const top=[px(to,height)];
    if(crest==='gable')top.push(px(lerp(from,to,.5),height+29));
    if(crest==='step')top.push(px(lerp(from,to,.8),height),px(lerp(from,to,.8),height+19),px(lerp(from,to,.2),height+19),px(lerp(from,to,.2),height));
    if(crest==='bow')for(let t=.9;t>.05;t-=.1)top.push(px(lerp(from,to,t),height+Math.sin(t*Math.PI)*22));
    top.push(px(from,height));poly([px(from),px(to),...top],color);
    for(let i=1;i<top.length;i++){line(top[i-1],top[i],0x987b58,7);line({x:top[i-1].x,y:top[i-1].y-2},{x:top[i].x,y:top[i].y-2},0xe7d1a6,2);}
    line(px(from,4),px(to,4),0xb19570,7);line(px(from),px(from,height),0xac906a,3);
  };
  const panel=(from:Point,to:Point,t0:number,t1:number,z0:number,z1:number,c:number,alpha=1)=>poly([px(lerp(from,to,t0),z0),px(lerp(from,to,t1),z0),px(lerp(from,to,t1),z1),px(lerp(from,to,t0),z1)],c,alpha);
  if(pass==='walls'){
    for(const wall of [...a.walls].sort((a,b)=>(a.from.x+a.from.y+a.to.x+a.to.y)-(b.from.x+b.from.y+b.to.x+b.to.y))){
      const {from,to,height:h,finish,opening,crest}=wall,c=finish==='lime'?wallTint:finishes[finish],length=Math.hypot(to.x-from.x,to.y-from.y);
      face(from,to,h,shade(c,to.x===from.x?.94:1.02),crest);
      if(['brick','ceramic','stone'].includes(finish)){
        const course=finish==='brick'?17:finish==='stone'?31:25,span=finish==='brick'?.42:finish==='stone'?.8:.5;
        for(let z=course,row=0;z<h-8;z+=course,row++){
          line(px(from,z),px(to,z),shade(c,.84),1.3,.8);
          for(let d=(row%2)*span/2;d<length;d+=span){const p=lerp(from,to,d/length);line(px(p,z-course),px(p,z),shade(c,.83),1,.8);}
        }
      }else if(['timber','bamboo','metal','acoustic'].includes(finish)){
        const step=finish==='bamboo'?.16:finish==='metal'?.65:finish==='acoustic'?.45:.62;
        for(let d=step;d<length;d+=step){const p=lerp(from,to,d/length);line(px(p,8),px(p,h-8),shade(c,.83),finish==='bamboo'?4:finish==='acoustic'?5:2,.66);}
        if(finish==='timber')for(const z of [h*.32,h*.67])line(px(from,z),px(to,z),0xaa8960,6);
        if(finish==='metal')for(let d=.2;d<length;d+=.8)for(const z of [17,h-17]){const p=px(lerp(from,to,d/length),z);line({x:p.x-1.6,y:p.y},{x:p.x+1.6,y:p.y},0x7b9185,3);}
      }else if(finish==='glazing'){
        panel(from,to,.03,.97,17,h-12,0xbad3c7,.82);
        for(let d=.7;d<length;d+=.7){const p=lerp(from,to,d/length);line(px(p,9),px(p,h-8),0xa6a884,5);}
        for(const z of [h*.4,h*.73])line(px(from,z),px(to,z),0xc3bc96,4);
        panel(from,to,.09,.22,26,h-26,0xf0f0d6,.5);
      }else{
        panel(from,to,0,1,8,48,0xd1b68e);for(let d=.85;d<length;d+=.85){const p=lerp(from,to,d/length);line(px(p,12),px(p,44),0xe3cba7,2);}
      }
      if(!opening)continue;
      const low=opening==='clerestory'?h*.7:opening==='open'?36:Math.max(58,h*.4),high=h-21;
      if(opening==='open'){
        panel(from,to,.08,.92,low,high,0xe6e7ce);line(px(lerp(from,to,.08),low),px(lerp(from,to,.92),low),0xc4ad80,6);
        for(const t of [.08,.5,.92])line(px(lerp(from,to,t),low),px(lerp(from,to,t),h-9),0xae956c,5);
      }else if(opening==='porthole'){
        const count=Math.max(1,Math.floor(length/1.2));
        for(let n=0;n<count;n++){
          const t=(n+.5)/count,center=lerp(from,to,t),half=Math.min(.24,.35/length),z=(low+high)/2,rz=Math.min(28,(high-low)/2),points:Point[]=[];
          for(let i=0;i<24;i++){const angle=i*Math.PI/12;points.push(px(lerp(from,to,t+Math.cos(angle)*half),z+Math.sin(angle)*rz));}
          poly(points,0xa5c5be);for(let i=0;i<points.length;i++)line(points[i],points[(i+1)%points.length],0xf0e4c7,5);line(px(center,z-rz*.65),px(center,z+rz*.65),0xd8e3cb,1,.8);
        }
      }else{
        const frame=0xa78961;
        if(opening==='arch'){
          const arch=(left:number,right:number,bottom:number,shoulder:number,rise:number)=>{
            const points=[px(lerp(from,to,left),bottom),px(lerp(from,to,right),bottom)];
            for(let i=0;i<=20;i++){const t=i/20;points.push(px(lerp(from,to,right-t*(right-left)),shoulder+Math.sin(t*Math.PI)*rise));}return points;
          };
          poly(arch(.09,.91,low-5,high-20,25),frame);const points=arch(.12,.88,low,high-23,23);poly(points,0xc5dcce);
          for(let i=2;i<points.length-1;i++)line(points[i],points[i+1],0xe6cf9d,3);
        }else{panel(from,to,.09,.91,low-5,high+5,frame);panel(from,to,.12,.88,low,high,0xb4d0c5);}
        const divisions=opening==='ribbon'?Math.max(3,Math.ceil(length/.6)):opening==='lattice'?Math.max(4,Math.ceil(length/.4)):2;
        for(let n=1;n<divisions;n++){const p=lerp(from,to,.12+.76*n/divisions),top=opening==='arch'?high-23+Math.sin(n/divisions*Math.PI)*23:high;line(px(p,low),px(p,top),0xddcaa2,opening==='lattice'?2:4);}
        if(opening==='sash'||opening==='lattice')for(let z=low+(opening==='lattice'?19:(high-low)/2);z<high;z+=opening==='lattice'?19:high-low)line(px(lerp(from,to,.12),z),px(lerp(from,to,.88),z),0xddcaa2,3);
        if(opening==='shutter')for(const [l,r] of [[.02,.17],[.83,.98]]){panel(from,to,l,r,low-6,high+6,0xb4a078);for(let z=low;z<high;z+=9)line(px(lerp(from,to,l),z),px(lerp(from,to,r),z),0xd6c19a,2);}
        panel(from,to,.18,.26,low+5,opening==='arch'?high-23:high-5,0xf3edce,.43);
      }
    }
    return;
  }
  for(const element of a.elements){
    const {footprint:r,height:h,kind}=element,from={x:r.x0,y:r.y0+.015},to={x:r.x1,y:r.y0+.015},width=r.x1-r.x0;
    const side={x:r.x1-.015,y:r.y1},p=(t:number,z:number)=>px(lerp(from,to,t),z);
    if(kind==='plinth'||kind==='display-steps'){
      const steps=kind==='plinth'?1:3;for(let i=0;i<steps;i++){const box={...r,y1:r.y1-(r.y1-r.y0)*i*.25};block(box,i*h/steps,h/steps,kind==='plinth'?0xbfa780:0xd8be94);}continue;
    }
    if(kind==='handrail'){
      for(let t=0;t<=1;t+=.2)line(p(t,12),p(t,h),0x9a9c82,4);line(p(0,h),p(1,h),0xd7c5a0,7);line(p(0,h*.5),p(1,h*.5),0xb8b299,3);continue;
    }
    if(kind==='canopy'||kind==='cabin-ribs'){
      const inset={...r,y1:r.y0+(r.y1-r.y0)*.38};
      for(const at of [from,to])line(px(at,0),px(at,h),0xac926b,5);
      if(kind==='canopy'){
        poly(surface(inset,h),0xddc398);const count=Math.max(3,Math.round(width/.28));
        for(let i=0;i<count;i+=2)poly(surface({...inset,x0:r.x0+width*i/count,x1:r.x0+width*(i+1)/count},h+.7),0xcba98a);
        const a=px({x:inset.x0,y:inset.y1},h),b=px({x:inset.x1,y:inset.y1},h);poly([a,b,{x:b.x,y:b.y+10},{x:a.x,y:a.y+10}],0xccad80);
      }else{
        const back=px(lerp(from,to,.5),h+23);line(p(0,h-16),back,0xd3d4bd,9);line(back,p(1,h-16),0xd3d4bd,9);line(p(0,h-16),back,0xf0e8cd,2);line(back,p(1,h-16),0xf0e8cd,2);
        line(p(1,h-16),px(side,h-16),0xbcc5af,9);
      }continue;
    }
    if(kind==='extractor'){
      const narrow={x0:r.x0+width*.25,y0:r.y0,x1:r.x1-width*.25,y1:r.y0+(r.y1-r.y0)*.35};block(narrow,h-20,43,0xb9b7a2);
      const top=surface(narrow,h),base=surface({...r,y1:r.y0+(r.y1-r.y0)*.68},h-26);poly([base[0],base[1],top[1],top[0]],0xd3c9af);poly([base[1],base[2],top[2],top[1]],0xb2ae99);poly([base[2],base[3],top[3],top[2]],0xc4bca6);line(base[2],base[3],0x928d76,5);continue;
    }
    if(kind==='pipe-chase'){
      for(let t=.16;t<1;t+=.3){line(p(t,12),p(t,h),0x96aaa0,10);line(p(t,12),p(t,h),0xd0d7bd,3);const v=p(t,h*.63);line({x:v.x-8,y:v.y},{x:v.x+8,y:v.y},0xb18e6b,4);line({x:v.x,y:v.y-7},{x:v.x,y:v.y+7},0xb18e6b,3);}line(p(.08,h),p(.92,h),0x9fac98,10);continue;
    }
    if(kind==='hanging-rail'||kind==='trellis'){
      for(const t of [0,1])line(p(t,10),p(t,h),0xb4966b,5);line(p(0,h),p(1,h),0xc2a87b,6);
      if(kind==='trellis')for(let t=.1;t<1;t+=.16){line(p(t,26),p(t,h),0xb3a477,2);line(p(0,h*t),p(1,h*t),0xb3a477,2);const leaf=p(t,h*(.35+t*.5));poly([{x:leaf.x,y:leaf.y-9},{x:leaf.x+11,y:leaf.y-6},{x:leaf.x+5,y:leaf.y+3},{x:leaf.x-5,y:leaf.y+5}],0x8da878);}
      else for(let t=.15,i=0;t<1;t+=.19,i++){const hook=p(t,h-6),low=p(t,h-34);line(hook,low,0x958368,2);poly([{x:low.x-10,y:low.y-2},{x:low.x+10,y:low.y-2},{x:low.x+13,y:low.y+24},{x:low.x-13,y:low.y+24}],[0xc1c8a9,0xd5b49c,0x9cb7ae][i%3]);}continue;
    }
    if(kind==='privacy-curtain'){
      line(p(0,h),p(1,h),0xbbad8c,5);line(p(1,h),px(side,h),0xbbad8c,5);
      for(const [a,b] of [[0,.3],[.75,1]]){panel(from,to,a,b,28,h-6,0xc2cdb3);for(let t=a;t<b;t+=.045)line(p(t,30),p(t,h-6),0xe1dfc3,2);}continue;
    }
    if(kind==='glass-screen'){
      panel(from,to,0,1,52,h,0xc1d9c9,.67);line(p(0,52),p(1,52),0xcab189,5);for(const t of [0,1])line(p(t,38),p(t,h),0xb79d76,4);line(p(0,h),p(1,h),0xe9d7b2,3);panel(from,to,.15,.23,58,h-7,0xf3ecd0,.72);continue;
    }
    if(kind==='arched-niche'){
      face(from,to,h,0xc9ad87,'bow');panel(from,to,.09,.91,26,h-23,0x9b9273);
      const head=[p(.09,h-35),p(.91,h-35)];for(let i=0;i<=16;i++){const t=i/16;head.push(p(.91-t*.82,h-35+Math.sin(t*Math.PI)*27));}poly(head,0x9b9273);for(let i=1;i<head.length-1;i++)line(head[i],head[i+1],0xe0c79e,6);continue;
    }
    if(kind==='lightbox'){
      for(const t of [.08,.92])line(p(t,48),p(t,h),0xa19577,3);panel(from,to,.04,.96,h-27,h,0x9b9a7c);panel(from,to,.08,.92,h-23,h-4,0xf1e4b1);for(let t=.25;t<.9;t+=.25)line(p(t,h-21),p(t,h-6),0xd2c595,2);continue;
    }
    const fill=kind==='acoustic-baffle'?0xb2bda7:kind==='wash-splash'?0xcbd9c3:kind==='pegwall'?0xb79d75:0xc6ac85;
    face(from,to,h,fill);
    if(kind==='service-hatch'){
      panel(from,to,.15,.85,69,h-17,0xb8d3c3);line(p(.09,66),p(.91,66),0xe3caa0,11);line(p(.5,70),p(.5,h-15),0xac946e,4);
    }else if(kind==='pigeonholes'||kind==='sorting-cubbies'){
      panel(from,to,.04,.96,48,h-5,0x947d5e);for(let z=52;z<h;z+=kind==='pigeonholes'?17:27)line(p(.04,z),p(.96,z),0xe0c9a1,4);
      const columns=kind==='pigeonholes'?Math.max(3,Math.round(width/.36)):Math.max(2,Math.round(width/.6));for(let n=1;n<columns;n++)line(p(n/columns,49),p(n/columns,h-5),0xd1b68d,4);
      for(let t=.14;t<.95;t+=1/columns)for(let z=59;z<h-8;z+=kind==='pigeonholes'?17:27)panel(from,to,t,Math.min(.93,t+.1),z,z+6,0xece0be);
    }else if(kind==='pegwall'){
      for(let t=.1;t<1;t+=.14)for(let z=37;z<h-7;z+=17){const q=p(t,z);line({x:q.x-1,y:q.y},{x:q.x+1,y:q.y},0x8a7c5c,2);}
      for(let t=.18;t<.95;t+=.25){line(p(t,h-21),p(t,h-55),0x7c8c7d,5);line(p(t-.065,h-24),p(t+.065,h-24),0x819280,5);}
    }else if(kind==='wash-splash'){
      for(let z=25;z<h;z+=21)line(p(0,z),p(1,z),0xe9e5cb,2);for(let t=.15;t<1;t+=.2)line(p(t,12),p(t,h),0xe9e5cb,2);
    }else{
      for(let t=.05;t<1;t+=kind==='acoustic-baffle'?.11:.16)line(p(t,14),p(t,h-6),kind==='acoustic-baffle'?0xd3d5b9:0xe5cfa8,kind==='acoustic-baffle'?6:3);
      if(kind==='timber-screen')line(p(0,h*.45),p(1,h*.45),0xac916c,5);
    }
  }
}
