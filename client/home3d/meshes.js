import * as T from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';
import {dimensions,surfaceHeight} from './model.js';
import {addInteriorArchitecture,interiorProfile} from './architecture.js';

// The palette follows deco-art.js: milk cream, terracotta, warm wood, mint and peach.
const P={wood:'#c99260',dark:'#79563f',cream:'#fff3df',pink:'#efa8ba',mint:'#9acbb3',blue:'#9bc7df',leaf:'#6da775',gold:'#edc773',ink:'#51494b'};
export function resources(){
  const geometries={box:new RoundedBoxGeometry(1,1,1,2,.07),ball:new T.SphereGeometry(.5,12,8),cylinder:new T.CylinderGeometry(.5,.5,1,12),cone:new T.ConeGeometry(.5,1,12),ring:new T.TorusGeometry(.36,.1,8,20)};
  const materials=new Map();
  return {geometries,material(color,glow=false,wall=''){const key=color+glow+wall;if(!materials.has(key))materials.set(key,new T.MeshStandardMaterial({color,roughness:.87,metalness:0,...(glow?{emissive:color,emissiveIntensity:.35}:{})}));return materials.get(key);},
    prune(root){const used=new Set();root.traverse(o=>{if(o.material)used.add(o.material);});for(const [key,m]of materials)if(!used.has(m)){m.dispose();materials.delete(key);}},
    dispose(){for(const g of Object.values(geometries))g.dispose();for(const m of materials.values())m.dispose();materials.clear();}};
}
function sculpt(group,R,wall=''){
  function shape(kind,x,y,z,w,h,d,c,glow=false){const m=new T.Mesh(R.geometries[kind],R.material(c,glow,wall));m.position.set(x,y,z);m.scale.set(w,h,d);m.castShadow=true;m.receiveShadow=true;if(wall)m.userData.wall=wall;group.add(m);return m;}
  return {box:(...a)=>shape('box',...a),ball:(...a)=>shape('ball',...a),cyl:(...a)=>shape('cylinder',...a),cone:(...a)=>shape('cone',...a),ring:(...a)=>shape('ring',...a)};
}
const sets={
  sofa:'sofa sofa_don ghe_da_bo ghe_rap_doi',bed:'giuong giuong_don giuong_king nem sap_go',
  shelf:'ke_sach ke_go ke_tivi ke_giay ke_bep ke_treo ke_go_treo ke_tron ke_khan ke_tam ke_my_pham ke_chen tu_giay',
  wardrobe:'tu_quan_ao tu_ngan_keo tu_dau_giuong tu_thuoc chan_bat',
  fridge:'tu_lanh tu_lanh_magnet',washer:'may_giat',screen:'tv may_choi_game ban_gaming',
  fan:'quat quat_mini quat_tran',guitar:'dan dan_bau',piano:'piano',speaker:'loa loa_cot radio hop_nhac',
  plush:'gau_bong gau_bong_lon tho_bong goi_om goi_tua',rug:'tham tham_hoa tham_tam tham_tron tham_dai',
  curtain:'rem rem_voan rem_giuong man_tuyn ao_choang',mirror:'guong guong_tam guong_dung ban_trang_diem',
  clock:'dong_ho dong_ho_qua_lac dong_ho_cuc_cu dong_ho_bao_thuc',
  tub:'bon_tam bon_rua',shower:'buong_tam',basket:'gio_do_tam gio_giat gio_trai_cay mam_ngu_qua ro_rau',
  vessel:'am_chen noi_com am_sieu_toc may_ca_phe may_xay hu_dua binh_gom chum_nuoc binh_tuoi coc_ban_chai thung_ruou',
  oven:'lo_nuong lo_vi_song lo_nuong_banh bep_ga lo_suoi_ngoai',umbrella:'du_che ban_ngoai',
  swing:'xich_du ghe_trung',hammock:'vong',float:'phao phao_hong_hac',water:'be_ca ho_ca_koi',
  birdcage:'long_chim',bike:'xe_dap xe_may_co xe_do_choi',tent:'leu_choi nha_cho',
  globe:'qua_dia_cau cau_tuyet',gym:'may_chay_bo gia_ta',telescope:'kinh_thien_van',rack:'moc_ao treo_noi',
};
const byId=new Map(Object.entries(sets).flatMap(([family,ids])=>ids.split(' ').map(id=>[id,family])));
export function familyOf(it){
  if(byId.has(it.id))return byId.get(it.id);
  if(it.id==='cay_dua'||it.id==='cay_mai'||it.id==='canh_dao'||it.cat==='plant')return 'plant';
  if(it.cat==='light'||it.id==='den_vuon'||it.id==='long_den_sao'||it.id==='den_keo_quan')return 'lamp';
  if(it.spot==='rug')return 'rug';
  if(it.tags?.includes('seat'))return 'chair';
  if(it.tags?.includes('table')||it.tags?.includes('desk')||it.cat==='table')return 'table';
  if(it.spot==='wall')return 'art';
  return {bath:'bathkit',bep:'kitchenkit',le:'festival',bed:'cushion',pool:'garden',fun:'toy'}[it.cat]||'art';
}
/** Every catalogue category has a volumetric silhouette; models use shared primitive buffers. */
export function furniture(it,tint,R){
  const g=new T.Group(),s=sculpt(g,R); // keep all geometry local to its saved footprint
  const B=s.box,C=s.cyl,S=s.ball,K=s.cone,Q=s.ring,w=(it.w||1)*.9,d=(it.h||1)*.87;
  const family=familyOf(it),color=tint||({table:P.pink,bed:P.wood,plant:'#df9a72',light:P.gold,bath:P.blue,pool:P.mint,bep:P.cream,wall:P.wood,fun:P.mint,le:'#da7377'}[it.cat]||P.wood);
  g.userData.family=family;g.name=it.name||it.id;
  const legs=(h=.6)=>{for(const x of [-w*.38,w*.38])for(const z of [-d*.35,d*.35])B(x,h/2,z,.09,h,.09,P.dark);};
  const tabletop=(h=surfaceHeight(it))=>{legs(h);B(0,h,0,w,.12,d,color);return h;};
  const plant=(x=0,z=0,scale=1)=>{C(x,.2*scale,z,.48*scale,.4*scale,.48*scale,color);C(x,.41*scale,z,.45*scale,.06*scale,.45*scale,P.dark);C(x,.65*scale,z,.04,.56*scale,.04,P.dark);for(let i=0;i<5;i++){const a=i*2.4;const leaf=S(x+Math.cos(a)*.17*scale,(.66+i*.08)*scale,z+Math.sin(a)*.13*scale,.3*scale,.12*scale,.48*scale,i%2?P.leaf:P.mint);leaf.rotation.z=Math.cos(a)*.6;}if(/hoa|mai|dao|sen|cuc/.test(it.id))for(let i=0;i<4;i++)S(x+Math.cos(i*2)*.22*scale,1.05*scale,z+Math.sin(i*2)*.17*scale,.18,.18,.18,P.pink);};
  switch(family){
    case 'sofa':legs(.19);B(0,.4,0,w,.4,d,color);B(0,.88,-d*.4,w,.65,.2,color);for(const x of [-w*.43,w*.43])B(x,.65,0,.2,.55,d,color);for(let i=0;i<Math.ceil(w);i++)B(-w*.32+i*w/Math.ceil(w),.66,.04,w/Math.ceil(w)*.72,.15,d*.7,P.cream);S(w*.28,.83,-.12,.32,.32,.15,P.gold);break;
    case 'bed':{const h=surfaceHeight(it);legs(h*.55);B(0,h*.7,0,w,.2,d,P.dark);B(0,h,0,w,.23,d,P.cream);B(0,h+.14,d*.22,w*.98,.1,d*.54,color);B(0,h+.32,-d*.47,w,.8,.13,P.wood);for(const x of [-w*.24,w*.24])B(x,h+.19,-d*.28,w*.37,.16,d*.23,P.cream);break;}
    case 'table':{const h=tabletop();if(it.id==='ban_co_tuong'){B(0,h+.08,0,w*.65,.03,d*.7,P.cream);for(let i=0;i<5;i++)C(-w*.25+i*.2,h+.12,-d*.15,.08,.05,.08,P.ink);}if(it.id==='may_may'){B(0,h+.25,0,.5,.4,.3,P.ink);B(.2,h+.15,.1,.1,.2,.1,P.gold);}break;}
    case 'chair':{const stool=it.id==='ghe_dau',lounge=/tam_nang|bap_benh|luoi/.test(it.id);legs(.42);B(0,.48,0,w,.17,d,color);if(!stool)B(0,lounge?.66:.9,-d*.38,w*.95,lounge?.45:.9,.16,color);if(!stool)for(const x of [-w*.43,w*.43])B(x,.68,0,.1,.1,d*.9,P.wood);break;}
    case 'shelf':{const h=it.spot==='wall'?.75:1.5;B(-w*.46,h/2,0,.09,h,d,P.dark);B(w*.46,h/2,0,.09,h,d,P.dark);B(0,h/2,-d*.43,w,h,.07,P.wood);for(let j=0;j<3;j++){B(0,j*h/2+.04,0,w,.08,d,color);for(let i=0;i<3;i++)B(-w*.28+i*w*.27,j*h/2+.19,0,w*.17,.28,d*.6,[P.mint,P.pink,P.gold][i]);}break;}
    case 'wardrobe':{const h=it.id==='tu_dau_giuong'?surfaceHeight(it):1.75;B(0,h/2,0,w,h,d,color);for(const x of [-w*.24,w*.24]){B(x,h/2,d*.5,w*.45,h*.9,.06,P.cream);C(x*.45,h*.55,d*.56,.06,.13,.06,P.gold);}break;}
    case 'fridge':B(0,.93,0,w,1.86,d,color);for(const [h,y] of [[.56,1.55],[1.13,.68]]){B(0,y,d*.5,w*.92,h,.05,P.cream);B(w*.3,y,d*.56,.07,.3,.07,P.dark);}if(it.id.endsWith('magnet'))for(let i=0;i<3;i++)B(-.18+i*.16,1.4,d*.55,.1,.1,.03,[P.pink,P.gold,P.blue][i]);break;
    case 'washer':B(0,.57,0,w,1.12,d,color);B(0,1.02,d*.5,w*.9,.12,.04,P.cream);Q(0,.51,d*.51,.9,.9,.8,P.cream);C(0,.51,d*.5,.52,.06,.52,P.blue).rotation.x=Math.PI/2;break;
    case 'screen':{const h=it.id==='ban_gaming'?tabletop():.18;B(0,h,0,w*.65,.12,d*.55,P.dark);B(0,h+.2,-.12,.15,.4,.12,P.dark);B(0,h+.7,-.12,w,1,.14,P.ink);B(0,h+.7,-.035,w*.9,.85,.035,P.blue,true);B(-w*.18,h+.5,-.01,w*.4,.22,.025,P.mint);break;}
    case 'fan':C(0,.06,0,w*.6,.1,d*.6,color);C(0,.47,0,.08,.9,.08,P.cream);Q(0,.95,0,.9,.9,.75,color);for(let i=0;i<3;i++){const blade=S(Math.sin(i*2.1)*.18,.95+Math.cos(i*2.1)*.18,0,.16,.4,.06,P.blue);blade.rotation.z=-i*2.1;}break;
    case 'guitar':S(0,.42,0,w*.7,.8,d*.4,color);S(0,.67,0,w*.5,.5,d*.35,P.wood);B(0,1.15,0,.13,.9,.1,P.dark);C(0,.6,d*.21,.19,.025,.19,P.dark).rotation.x=Math.PI/2;break;
    case 'piano':legs(.6);B(0,1,0,w,1.2,d*.8,color);B(0,.68,d*.45,w,.15,d*.5,P.cream);for(let i=0;i<12;i++)B(-w*.46+i*w/12,.78,d*.4,.065,.07,.2,P.ink);break;
    case 'speaker':B(0,.62,0,w*.8,1.24,d*.8,color);for(const y of [.35,.87]){C(0,y,d*.42,.35,.07,.35,P.ink).rotation.x=Math.PI/2;C(0,y,d*.46,.12,.03,.12,P.gold).rotation.x=Math.PI/2;}break;
    case 'plush':S(0,.32,0,w*.74,.65,d*.72,color);S(0,.7,0,w*.58,.5,d*.57,color);for(const x of [-w*.23,w*.23])S(x,.95,0,.22,it.id==='tho_bong'?.6:.23,.19,color);for(const x of [-.12,.12])S(x,.76,d*.28,.055,.055,.04,P.ink);S(0,.64,d*.29,.09,.06,.05,P.pink);break;
    case 'rug':B(0,.023,0,w,.035,d,color);B(0,.048,0,w*.84,.016,d*.76,P.cream);for(let i=0;i<5;i++)B(-w*.33+i*w*.16,.061,0,.025,.012,d*.72,color);break;
    case 'curtain':B(0,0,0,w,.08,.09,P.dark);for(let i=0;i<7;i++)B(-w*.43+i*w*.143,-it.h*.38,Math.sin(i)*.04,w*.15,it.h*.76,.1,i%2?color:P.cream);break;
    case 'mirror':B(0,.5,0,w*.82,1.15,.12,P.gold);B(0,.5,.07,w*.7,1.02,.025,P.blue);B(-w*.12,.64,.09,w*.04,.65,.02,P.cream).rotation.z=-.25;if(it.spot==='floor')legs(.2);break;
    case 'clock':C(0,.2,0,w*.8,.13,w*.8,color).rotation.x=Math.PI/2;C(0,.2,.08,w*.66,.035,w*.66,P.cream).rotation.x=Math.PI/2;B(0,.3,.12,.04,.25,.03,P.ink);B(.09,.2,.12,.2,.04,.03,P.ink);break;
    case 'plant':if(w>1.3){B(0,.2,0,w,.38,d,color);plant(-w*.27,0,.7);plant(w*.27,0,.8);}else plant(0,0,it.spot==='top'?.55:1);break;
    case 'lamp':{const wall=it.spot==='wall',h=it.id==='den_cay'?1.4:.65;C(0,.04,0,.38,.08,.38,P.dark);C(0,h/2,0,.065,h,.065,P.wood);K(0,h,0,.72,.45,.72,color,true);S(0,h-.14,0,.24,.2,.24,P.cream,true);if(wall){B(0,h/2,-.18,.08,.07,.4,P.dark);}break;}
    case 'tub':B(0,.33,0,w,.62,d,color);B(0,.66,0,w*.92,.08,d*.92,P.cream);B(0,.7,0,w*.72,.035,d*.7,P.blue);C(-w*.33,.86,-d*.3,.05,.42,.05,P.gold);B(-w*.27,1.04,-d*.3,.17,.05,.06,P.gold);break;
    case 'shower':B(0,.06,0,w,.1,d,P.cream);for(const x of [-w*.46,w*.46])B(x,1.1,0,.06,2.2,d,P.blue);B(0,2.17,0,w,.06,d,P.gold);C(0,1.1,-d*.43,.05,2.2,.05,P.dark);S(0,2.05,-d*.2,.35,.08,.32,P.gold);break;
    case 'basket':C(0,.27,0,w*.7,.5,d*.8,color);Q(0,.63,0,w*.78,.75,.6,P.dark);for(let i=0;i<3;i++)S(-w*.2+i*w*.2,.5,0,.22,.22,.3,[P.gold,P.mint,P.pink][i]);break;
    case 'vessel':C(0,.25,0,w*.6,.48,d*.6,color);C(0,.5,0,w*.68,.07,d*.68,P.cream);S(0,.56,0,.13,.11,.13,P.dark);Q(w*.3,.27,0,.5,.5,.4,P.dark);break;
    case 'oven':legs(.23);B(0,.58,0,w,.7,d,color);B(0,.53,d*.52,w*.77,.44,.04,P.ink);B(0,.76,d*.55,w*.65,.04,.03,P.gold);for(const x of [-w*.25,w*.25])C(x,.96,0,.3,.03,.3,P.dark);break;
    case 'umbrella':if(it.id==='ban_ngoai')tabletop();C(0,1.2,0,.055,2.4,.055,P.wood);K(0,2.33,0,w*1.3,.5,w*1.3,color);K(0,2.36,0,w*.9,.48,w*.9,P.cream);break;
    case 'swing':for(const x of [-w*.44,w*.44])B(x,1,0,.1,2,.1,P.dark);B(0,2,0,w,.1,.1,P.wood);for(const x of [-w*.25,w*.25])C(x,1.23,0,.03,1.4,.03,P.dark);B(0,.6,0,w*.7,.2,d*.8,color);B(0,.9,-d*.3,w*.7,.65,.1,color);break;
    case 'hammock':for(const x of [-w*.45,w*.45])B(x,.7,0,.1,1.4,.12,P.wood);S(0,.5,0,w,.15,d*.8,color);B(0,.1,0,w,.1,.15,P.dark);break;
    case 'float':Q(0,.23,0,w,w,d,color).rotation.x=Math.PI/2;if(it.id==='phao_hong_hac'){C(w*.32,.55,0,.12,.75,.12,P.pink);S(w*.32,.94,0,.3,.3,.3,P.pink);}else S(w*.3,.22,0,.12,.08,.12,P.cream);break;
    case 'water':B(0,.25,0,w,.45,d,P.dark);B(0,.51,0,w*.9,.07,d*.9,P.blue);for(let i=0;i<3;i++)S(-w*.25+i*w*.25,.56,Math.sin(i)*d*.2,.21,.07,.11,P.gold);if(it.id==='be_ca'){for(const x of [-w*.45,w*.45])B(x,.88,0,.05,.7,d,P.blue);B(0,1.24,0,w,.06,d,P.dark);}break;
    case 'birdcage':C(0,.08,0,w*.7,.12,d*.7,P.gold);for(let i=0;i<8;i++){const a=i*Math.PI/4;C(Math.cos(a)*w*.3,.5,Math.sin(a)*d*.3,.025,.85,.025,P.gold);}K(0,1,0,w*.8,.35,d*.8,P.gold);S(0,.45,0,.3,.26,.2,P.mint);break;
    case 'bike':for(const x of [-w*.34,w*.34]){Q(x,.35,0,.8,.8,.7,P.ink);C(x,.35,0,.08,.08,.08,P.gold);}B(0,.6,0,w*.65,.09,.09,color).rotation.z=.2;B(.1,.9,0,.5,.12,.2,P.dark);B(w*.33,.8,0,.05,.6,.05,P.dark);break;
    case 'tent':B(0,.25,0,w,.5,d,color);const roof=K(0,.85,0,w*1.3,.95,d*1.3,P.wood);roof.rotation.y=Math.PI/4;B(0,.3,d*.51,w*.37,.58,.02,P.dark);break;
    case 'globe':C(0,.07,0,.45,.1,.45,P.wood);C(0,.32,0,.06,.5,.06,P.gold);S(0,.68,0,.65,.65,.65,P.blue);S(.12,.71,.25,.3,.25,.06,P.leaf);break;
    case 'gym':B(0,.15,0,w,.22,d,P.ink);B(0,.28,0,w*.8,.05,d*.72,P.dark);for(const x of [-w*.4,w*.4])B(x,.7,-d*.35,.08,1.4,.08,color);B(0,1.4,-d*.35,w,.09,.1,color);break;
    case 'telescope':for(let i=0;i<3;i++){const a=i*2.1;B(Math.cos(a)*.2,.45,Math.sin(a)*.2,.06,.9,.06,P.dark).rotation.z=Math.cos(a)*.4;}C(0,1,0,.25,.9,.25,color).rotation.z=1;C(.35,1.23,0,.3,.08,.3,P.ink).rotation.z=1;break;
    case 'rack':C(0,.9,0,.06,1.8,.06,P.wood);B(0,1.6,0,w,.08,.08,P.dark);for(let i=0;i<3;i++)B(-w*.3+i*w*.3,1.2,0,w*.2,.6,.12,[P.pink,P.mint,P.blue][i]);C(0,.05,0,.6,.1,.6,P.dark);break;
    case 'art':B(0,0,0,w,it.h*.83,.12,color);B(0,0,.07,w*.87,it.h*.7,.02,P.cream);S(-w*.22,it.h*.16,.1,.22,.22,.04,P.gold);K(w*.12,-it.h*.12,.1,w*.62,it.h*.43,.03,P.mint);break;
    case 'bathkit':C(0,.18,0,.38,.36,.38,color);B(.12,.46,0,.09,.35,.09,P.cream);S(-.15,.28,.12,.22,.16,.2,P.gold);break;
    case 'kitchenkit':B(0,.05,0,w*.8,.1,d*.75,P.wood);B(-.12,.14,0,w*.38,.09,.18,P.cream);C(.2,.23,0,.22,.38,.22,color);break;
    case 'festival':C(0,.07,0,w,.1,d,P.gold);for(let i=0;i<5;i++)S(Math.cos(i*1.4)*w*.25,.2,Math.sin(i*1.4)*d*.22,.25,.25,.25,[P.gold,P.pink,P.leaf][i%3]);break;
    case 'cushion':S(0,.15,0,w,.3,d,color);B(0,.25,0,w*.7,.08,d*.7,P.cream);break;
    case 'garden':C(0,.25,0,w*.7,.5,d*.7,color);B(.25,.35,0,.5,.1,.1,P.dark);break;
    case 'toy':B(0,.18,0,w*.55,.36,d*.55,color);B(-.15,.43,0,w*.3,.18,d*.3,P.gold);S(.16,.29,d*.3,.12,.12,.1,P.cream);break;
  }
  return g;
}

const walls={kem:'#f8edd9',bac_ha:'#c6e2d1',hong_dao:'#f1c8bb',soc:'#e2d6d8',cham_bi:'#e6dbe8',hoa_nhi:'#e6dfcc',may_sao:'#ccdce8',gach_the:'#eee8dc',op_go:'#d9ba95'};
const floors={go_sang:'#d4ae83',gach_trang:'#eee9de',chieu:'#c7b580',caro:'#d5d1c4',tham_len:'#d89baf',gach_bong:'#b7cbbb',xuong_ca:'#bd9670',ga_ke:'#e2b9c2',ga_may:'#bdd7e3',ga_dau:'#e9b9b8',ga_meo:'#e7d2b6'};
export function roomStructure(room,parts={},R,scope=''){
  const g=new T.Group(),solid=sculpt(g,R),{box:B,cyl:C,ball:S}=solid,{width:w,depth:d,height:h}=dimensions(room),skin={...room.skin0,...room.skin};
  const profile=interiorProfile(room,scope),bayWindow=profile.windowDepth&&(room.fix||[]).find(f=>f.t==='window'&&f.layer==='wall');
  const backGroup=new T.Group(),sideGroup=new T.Group();g.add(backGroup,sideGroup);
  const backArt=sculpt(backGroup,R,'back'),sideArt=sculpt(sideGroup,R,'side'),W=backArt.box,L=sideArt.box;
  const outside=room.out,wall=walls[skin.w]||(/bath/.test(room.type)?'#d8e7df':parts?.wall?.lv?'#faefdb':P.cream),floor=floors[skin.f]||(room.type==='yard'?'#9cbd89':outside?'#d3c5ad':parts?.floor?.lv===1?'#e0ddd1':parts?.floor?.lv===2?'#b68b60':'#d1ac87');
  B(0,-.16,0,w+.3,.3,d+.3,P.dark);const ground=B(0,-.01,0,w,.05,d,floor);ground.name='floor';ground.userData.zone='floor';
  // Individual plank/tile seams give depth and scale without a room-sized billboard.
  for(let z=0;z<d*2;z++)B(0,.019,-d/2+z*.5,w,.012,.012,'#b7a18a');
  for(let x=0;x<w;x++)B(-w/2+x,.019,0,.014,.012,d,'#b7a18a');
  if(!outside){
    const wallPart=(x,y,width,height)=>{if(width<=0||height<=0)return;const m=W(x,y,-d/2-.075,width,height,.16,wall);m.userData.zone='wall';if(!g.getObjectByName('back-wall'))m.name='back-wall';};
    if(bayWindow){
      // Cut only the existing reserved window rectangle. Saved wall/floor cells
      // remain exactly where the server placed them and paint still hits wall.
      const f=bayWindow,cx=-w/2+f.x+f.w/2,cy=h-(f.y+f.h/2)*1.1,ow=f.w*.87,oh=f.h*.85,l=cx-ow/2,r=cx+ow/2,b=cy-oh/2,t=cy+oh/2;
      wallPart((-w/2-.125+l)/2,h/2,l+w/2+.125,h);wallPart((r+w/2+.125)/2,h/2,w/2+.125-r,h);
      wallPart(cx,b/2,ow,b);wallPart(cx,(t+h)/2,ow,h-t);
    }else wallPart(0,h/2,w+.25,h);
    const sideHeight=profile.sideHeight??h,side=L(-w/2-.075,sideHeight/2,0,.16,sideHeight,d,wall);side.name='side-wall';
    if(sideHeight<h){for(const zz of [-d/2,d/2])L(-w/2-.075,h/2,zz,.16,h,.14,P.cream);L(-w/2-.075,sideHeight,0,.24,.09,d,P.wood);}
    W(0,.13,-d/2+.035,w,.24,.08,P.wood);L(-w/2+.035,.13,0,.08,.24,d,P.wood);
    W(0,h,-d/2,w+.3,.13,.24,P.dark);L(-w/2,h,0,.23,.13,d,P.dark);
    if(room.type==='bunk'){B(0,.13,0,w,.2,d,P.cream);for(const x of [-w/2,w/2])for(const z of [-d/2,d/2])B(x,h/2,z,.12,h,.12,P.wood);}
    if((room.fix||[]).some(f=>f.t==='slope'))B(-w*.29,h-.22,-d*.22,w*.5,.15,d*.65,P.wood).rotation.z=-.24;
    if(parts?.wall?.c<65){for(let i=0;i<3;i++)W(-w*.22+i*.16,.8+i*.13,-d/2+.018,.025,.3,.025,'#ab9079').rotation.z=i%2?.5:-.5;}
    if(parts?.wall?.lv===2||skin.w==='op_go'){const trim=W(0,.53,-d/2+.03,w,1,.065,'#cfab83');trim.name='wall-upgrade';for(let x=0;x<w;x+=.45)W(-w/2+x,.53,-d/2+.075,.028,1,.03,'#b58d66');}
    if(parts?.floor?.c<60){const crack=B(w*.21,.038,d*.15,.026,.012,.9,'#8f775f');crack.rotation.y=.6;crack.name='floor-damage';B(w*.21-.16,.038,d*.15+.25,.45,.012,.026,'#8f775f');}
    if(parts?.roof?.c<60){const damp=backArt.ball(w*.25,h-.16,-d/2+.026,1,.25,.025,'#cabda4');damp.name='roof-damage';}
    if(parts?.power?.lv===2)W(0,h-.12,-d/2+.11,w*.9,.06,.08,P.gold,true);
    if(['soc','cham_bi','hoa_nhi','may_sao','gach_the'].includes(skin.w))for(let x=0;x<w;x+=.65){
      if(skin.w==='soc')W(-w/2+x,h/2,-d/2+.015,.12,h,.012,'#fff3e6');
      else for(let y=.55;y<h;y+=.6)backArt.ball(-w/2+x,y,-d/2+.022,skin.w==='gach_the'?.55:.07,skin.w==='gach_the'?.015:.07,.012,skin.w==='may_sao'?P.gold:P.cream);
    }
  }else{
    const fence=new T.Group();fence.name='garden-fence';g.add(fence);const F=sculpt(fence,R).box;
    for(let x=0;x<=w;x+=.5)F(-w/2+x,.38,-d/2,.09,.78,.09,P.cream);
    for(const y of [.24,.59])F(0,y,-d/2,w,.07,.08,P.wood);
    for(let z=0;z<=d;z+=.5)F(-w/2,.38,-d/2+z,.09,.78,.09,P.cream);
    F(-w/2,.56,0,.09,.08,d,P.wood);
  }
  for(const f of room.fix||[]){
    const painter=f.layer==='wall'?backArt:solid;
    const marked=Object.fromEntries(Object.entries(painter).map(([key,fn])=>[key,(...args)=>{const m=fn(...args);m.userData.fixture=f.t;return m;}]));
    const {box:B,cyl:C,ball:S,cone:K,ring:Q}=marked;
    const x=-w/2+f.x+f.w/2,z=-d/2+f.y+f.h/2,fy=h-(f.y+f.h/2)*1.1;
    if(f===bayWindow){
      const width=f.w*.87,height=f.h*.85,deep=profile.windowDepth,outer=-d/2-deep;
      B(x,fy,outer,width,height,.07,P.blue);
      for(const xx of [x-width/2,x+width/2]){B(xx,fy,-d/2-deep/2,.085,height+.15,deep+.18,P.cream);B(xx,fy,outer+.06,.09,height+.15,.12,P.wood);}
      for(const yy of [fy-height/2,fy+height/2])B(x,yy,-d/2-deep/2,width+.2,.08,deep+.3,P.wood);
      B(x,fy,outer+.09,.045,height,.055,P.cream);B(x,fy,outer+.09,width,.045,.055,P.cream);
    }else if(f.t==='window'&&f.layer==='wall'){
      B(x,fy,-d/2+.03,f.w*.87,f.h*.85,.1,P.wood);B(x,fy,-d/2+.1,f.w*.73,f.h*.7,.06,P.blue);
      B(x,fy,-d/2+.16,.05,f.h*.73,.05,P.cream);B(x,fy,-d/2+.16,f.w*.76,.05,.05,P.cream);B(x,fy-f.h*.4,-d/2+.23,f.w,.09,.35,P.wood);
    }else if(f.t==='door'&&f.layer==='wall'){B(x,1.05,-d/2+.025,f.w*.83,2.1,.12,P.wood);B(x,.96,-d/2+.1,f.w*.65,1.6,.04,'#b88256');S(x+.25,.95,-d/2+.15,.07,.07,.07,P.gold);}
    else if(f.t==='pool'){B(x,.025,z,f.w,.07,f.h,P.cream);B(x,.07,z,f.w-.2,.045,f.h-.2,P.blue);for(let i=0;i<4;i++)B(x-f.w*.3+i*f.w*.2,.1,z,.4,.012,.045,'#cee9e7');}
    else if(f.t==='toilet'){C(x,.26,z,.5,.5,.65,P.cream);S(x,.56,z+.06,.6,.15,.7,P.cream);B(x,.65,z-.25,.5,.65,.19,P.cream);}
    else if(f.t==='shower'){C(x,1.1,-d/2+.12,.04,1.9,.04,P.gold);S(x,2,-d/2+.28,.35,.08,.3,P.gold);B(x,.025,-d/2+.5,.9,.04,.9,P.cream);}
    else if(f.t==='ladder'){for(const xx of [-.27,.27])B(x+xx,.8,z,.08,1.6,.08,P.wood);for(let i=0;i<5;i++)B(x,.15+i*.29,z,.62,.08,.08,P.dark);}
    else if(f.t==='pillow')B(x,.23,z,f.w*.9,.26,f.h*.75,P.cream);
    else if(f.t==='bookwall'){
      B(x,fy,-d/2+.15,f.w*.93,f.h*1.02,.22,P.dark);
      for(let row=0;row<4;row++){const yy=fy-f.h*.43+row*f.h*.27;B(x,yy,-d/2+.32,f.w,.065,.32,P.wood);for(let col=0;col<Math.floor(f.w*5);col++){const xx=x-f.w*.43+col*.2;B(xx,yy+.17,-d/2+.34,.13,.25+(col%3)*.04,.19,[P.mint,P.pink,P.gold,P.blue][(col+row)%4]);}}
      for(const xx of [x-f.w*.48,x+f.w*.48])B(xx,fy,-d/2+.3,.09,f.h*1.12,.37,P.wood);
    }else if(f.t==='screen'){
      B(x,fy,-d/2+.12,f.w,f.h,.2,P.ink);B(x,fy,-d/2+.24,f.w*.91,f.h*.85,.025,'#b6cacc');B(x,fy+f.h*.43,-d/2+.28,f.w*.8,.035,.025,P.cream);
      for(const side of [-1,1]){B(x+side*f.w*.48,fy,-d/2+.28,.12,f.h,.14,'#9a5c60');for(let i=0;i<2;i++)C(x+side*f.w*.56,fy-.23+i*.47,-d/2+.24,.19,.08,.19,P.ink).rotation.x=Math.PI/2;}
    }else if(f.t==='racks'){
      B(x,fy,-d/2+.16,f.w,f.h,.27,P.dark);for(let row=0;row<4;row++)for(let col=0;col<Math.floor(f.w*2);col++){
        const xx=x-f.w*.42+col*.48,yy=fy-f.h*.36+row*f.h*.24;
        for(const direction of [-1,1])B(xx,yy,-d/2+.34,.045,.48,.25,P.wood).rotation.z=direction*Math.PI/4;
        C(xx,yy,-d/2+.36,.15,.3,.15,col%2?'#61877a':'#895a57').rotation.x=Math.PI/2;C(xx,yy,-d/2+.54,.055,.1,.055,P.gold).rotation.x=Math.PI/2;
      }
    }else if(f.t==='mirror'){
      B(x,fy,-d/2+.15,f.w,f.h,.14,P.gold);B(x,fy,-d/2+.24,f.w*.95,f.h*.93,.035,'#c3d5d4');for(let i=0;i<3;i++)B(x-f.w*.35+i*f.w*.32,fy,-d/2+.27,.025,f.h*.9,.025,P.cream);
    }else if(f.t==='rails'){
      for(const xx of [x-f.w*.46,x+f.w*.46])B(xx,fy,-d/2+.3,.09,f.h,.4,P.wood);B(x,fy+f.h*.46,-d/2+.3,f.w,.1,.48,P.wood);B(x,fy+f.h*.2,-d/2+.32,f.w,.055,.055,P.gold);
      for(let i=0;i<5;i++){const xx=x-f.w*.35+i*f.w*.17;Q(xx,fy+f.h*.14,-d/2+.34,.13,.17,.09,P.gold);for(const s of [-1,1])B(xx+s*.1,fy-.03,-d/2+.34,.24,.035,.04,P.wood).rotation.z=s*.45;}
    }else if(f.t==='gate'){
      for(const xx of [x-f.w/2,x+f.w/2])B(xx,1.07,-d/2+.15,.16,2.15,.18,P.dark);for(let i=0;i<12;i++)B(x,.12+i*.165,-d/2+.19,f.w,.14,.07,i%2?'#a6b4af':'#bac4b7');B(x,2.16,-d/2+.23,f.w+.24,.25,.4,P.dark);
    }else if(f.t==='car'){
      const fw=f.w*.86,fd=f.h*.72;B(x,.48,z,fw,.47,fd,'#c88470');S(x,.76,z,fw*.57,.66,fd*.84,P.cream);B(x,.82,z+fd*.43,fw*.46,.32,.035,P.blue);B(x,.32,z+fd*.5,fw*.93,.09,.08,P.gold);
      for(const xx of [x-fw*.35,x+fw*.35])for(const zz of [z-fd*.47,z+fd*.47]){C(xx,.25,zz,.36,.16,.36,P.ink).rotation.x=Math.PI/2;C(xx,.25,zz+(zz>z?.09:-.09),.18,.025,.18,P.gold).rotation.x=Math.PI/2;}
      for(const xx of [x-fw*.36,x+fw*.36])S(xx,.5,z+fd*.51,.18,.11,.035,P.cream);
    }else if(f.t==='gazebo'){
      for(const xx of [x-f.w*.44,x+f.w*.44])for(const zz of [z-f.h*.43,z+f.h*.43])C(xx,1.03,zz,.12,2.06,.12,P.wood);
      B(x,2.06,z,f.w,.15,f.h,P.dark);K(x,2.56,z,f.w*1.25,1,f.h*1.25,P.wood).rotation.y=Math.PI/4;B(x,.07,z,f.w,.14,f.h,P.cream);
    }
    else if(f.surface){const y=f.layer==='wall'?fy:f.surface/32;const top=B(x,y,f.layer==='wall'?-d/2+.3:z,f.w,.14,f.layer==='wall'?.5:f.h,parts?.kitchen?.lv===2?'#dadbd3':P.wood);top.userData.host='#'+f.t;if(f.layer!=='wall')B(x,y/2,z,f.w*.92,y,f.h*.9,parts?.kitchen?.lv===2?P.mint:P.cream);}
  }
  addInteriorArchitecture(room,scope,{solid,back:backArt,side:sideArt},dimensions(room));g.userData.architecture=profile.id;
  return g;
}
