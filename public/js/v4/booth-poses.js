/** booth-poses.js — the poses of the fair's photobooth (public/js/v4/fair-booth.js; owner 03/10: "hội chợ có cái
 * photobooth đó làm đẹp hơn nha, nhiều dáng với đẹp hơn nha").
 * The character is the game's own (./look.js: legs, hair, top, accessory, the same face), drawn here with its arms,
 * hands, head and face posed: an arm is shoulder → elbow → hand, a hand is a fist, an open palm, a V, a thumb, a
 * pointing finger, a finger heart, a cat paw…; the head tilts at the neck; the body leans and jumps; the eyes wink,
 * smile, laugh; the mouth grins, pouts, says :3. Drawn in code (canvas 2D), no images.
 *
 *   POSES            [{id, emoji, name, group}]   group false: one person; true: made together (2+ in the booth)
 *   POSE             {id: row}                    DEFAULT 'dung' (an id this build does not know is drawn as it)
 *   FACES            [{id, emoji, name}]          the expressions ("Biểu cảm"), first 'auto' (= the pose's own face)
 *   FACE, knownFace  {id: row}, id → bool         a face this build does not know is drawn as 'auto'
 *   paintPeople(c, people, w, h) → [{x, s}]      people [{lk, g, pose, prop, face}] side by side in a w × h photo
 *                                                (origin its corner), whole (no head, hat, raised item cut off), not
 *                                                overlapping; returns each one's centre x and the scale
 *                                                ({scale}: no bigger than this; {measure: true}: only the scale;
 *                                                {sign}: the words of the sign in hand: bang_chu, and gio_bien's)
 *   poseThumb(lk, g, id, size, face) → dataURL   a tile of the picker: this look in the pose (a group pose: with a friend)
 *   faceThumb(lk, g, face, size) → dataURL       a tile of the face picker: this look's head and shoulders in the face
 *
 * A face changes the eyes, brows, mouth and cheeks (and adds its tears, zzz, 💢…); the pose keeps its arms, body and
 * hand items. Some poses hold their own item (a teddy, balloons, a sign, an ice cream, a cup): a booth hand prop then
 * takes the other hand, or none when both hands are busy.
 *
 * A group pose is the same id on neighbours in the booth: each one takes their part (the left of a big heart, the one
 * with the phone in a squished selfie…); a group pose with nobody next to them in it is drawn as its own solo pose.
 * Ids are short lowercase words (live/booth.py clean_id); the 1.5.1 client draws an id it does not know as 'dung'. */
import {CANVAS,FRONT,figureOf,defaultLook,paintLegs,paintDress,paintHairBack,paintTop,paintHairFront,paintAcc} from './look.js';
import {t as tr} from './i18n.js';

const {R,E,L,P,heart}=CANVAS;
const TAU=Math.PI*2;
const INK='#705140',LIP='#b17c69',MOUTH='#a8434b',TONGUE='#ef8a98';

/* ---------------------------------------------------------------- the catalogue */
// [id, emoji, name, group]; the first seven are the 1.5.1 poses (same ids: older clients in the room still know them)
const ROWS=[
  ['dung','🧍','Đứng thẳng',0],['v','✌️','Chữ V',0],['vay','👋','Vẫy tay',0],['tim','🫶','Bắn tim',0],
  ['tim_nho','🤏','Tim nhỏ',0],['tim_dau','💗','Tim trên đầu',0],['ma','🥰','Chống má',0],['nhay_mat','😉','Nháy mắt',0],
  ['hoan_ho','🙌','Hoan hô',0],['nhay','🤸','Nhảy lên',0],['nghieng','😊','Nghiêng đầu',0],['like','👍','Like',0],
  ['ngau','😎','Ngầu',0],['ngai','🙈','Ngại ngùng',0],['suy_nghi','🤔','Suy nghĩ',0],['cuoi','😆','Cười lớn',0],
  ['ngac','😮','Ngạc nhiên',0],['meo','🐱','Tay mèo',0],['gong','💪','Gồng cơ',0],['hon_gio','😘','Hôn gió',0],
  ['chong_nanh','🦸','Chống nạnh',0],
  // 1.5.2: more solo poses (some hold their own item)
  ['om_gau','🧸','Ôm gấu',0],['cam_bong','🎈','Chùm bóng bay',0],['selfie','📱','Tự sướng',0],['xoay_vay','💃','Xoay vòng',0],
  ['chay','🏃','Chạy bộ',0],['ngoi_xom','🧎','Ngồi xổm',0],['bong_hoa','🌼','Mặt bông hoa',0],['gio_bien','🪧','Giơ biển',0],
  ['an_kem','🍦','Ăn kem',0],['tra_sua','🧋','Trà sữa',0],['chao','🫡','Chào kiểu lính',0],['bay','✈️','Máy bay',0],
  ['u_oa','🫣','Ú òa',0],['om_tim','💝','Ôm tim',0],['vo_tay','👏','Vỗ tay',0],
  ['tim_to','💞','Tim to',1],['khoac_vai','🤝','Khoác vai',1],['dap_tay','✋','Đập tay',1],['chi_nhau','👉','Chỉ nhau',1],
  ['tua_lung','😎','Tựa lưng',1],['tua_vai','🥹','Tựa vai',1],['cung_nhay','🦘','Cùng nhảy',1],['chum_dau','🤳','Chụm đầu',1],
  ['nam_tay','🙌','Nắm tay',1],
  ['om_nhau','🤗','Ôm nhau',1],['tau_hoa','🚂','Tàu hỏa',1],['xoa_dau','🫳','Xoa đầu',1],['cung_ly','🥂','Cụng ly',1],
];
export const POSES=ROWS.map(([id,emoji,name,g])=>({id,emoji,name,group:!!g}));
export const POSE=Object.fromEntries(POSES.map(p=>[p.id,p]));
export const DEFAULT='dung';
export const known=id=>typeof id==='string'&&Object.hasOwn(POSE,id);

/* ---------------------------------------------------------------- the faces ("Biểu cảm"), with any pose
 * {eyes, mouth, brows, blush, blushC (the cheeks' colour), puff (puffed cheeks), fx (head effects)} */
const FACE_ROWS=[
  ['auto','✨','Theo dáng'],['cuoi_hip','😊','Cười híp mắt'],['cuoi_tit','😆','Cười tít'],['lap_lanh','🤩','Mắt lấp lánh'],
  ['mat_tim','😍','Mắt tim'],['phong_ma','🐡','Phồng má'],['le_luoi','😜','Lè lưỡi'],['khoc_nhe','😭','Khóc nhè'],
  ['ngu_gat','😴','Ngủ gật'],['gian_doi','😤','Giận dỗi'],['do_mat','😳','Đỏ mặt'],['hoang_hot','😱','Hoảng hốt'],
  ['ngo_ngac','❓','Ngơ ngác'],['hon','😚','Chu môi'],['mat_meo','😺','Mặt mèo'],
];
export const FACES=FACE_ROWS.map(([id,emoji,name])=>({id,emoji,name}));
export const FACE=Object.fromEntries(FACES.map(f=>[f.id,f]));
export const knownFace=id=>typeof id==='string'&&Object.hasOwn(FACE,id);
const FACE_SPEC={
  cuoi_hip:{eyes:'happy',mouth:'bigsmile',blush:.7},
  cuoi_tit:{eyes:'laugh',mouth:'laugh',blush:.5,fx:['joytears']},
  lap_lanh:{eyes:'star',mouth:'grin',blush:.4,fx:['fsparkle']},
  mat_tim:{eyes:'heart',mouth:'grin',blush:.8,fx:['fhearts']},
  phong_ma:{eyes:'sulk',mouth:'pucker',blush:.9,puff:1},
  le_luoi:{eyes:'wink',mouth:'tongue_out',blush:.4},
  khoc_nhe:{eyes:'cry',mouth:'wail',brows:'worry',blush:.6,fx:['tears']},
  ngu_gat:{eyes:'sleep',mouth:'smallo',fx:['bubble','zzz']},
  gian_doi:{eyes:'angry',mouth:'frown',brows:'angry',blush:.8,blushC:'#f08484',fx:['anger']},
  do_mat:{eyes:'big',mouth:'wavy',brows:'worry',blush:1.6,blushC:'#ff8593',fx:['blushlines']},
  hoang_hot:{eyes:'round',mouth:'scream',brows:'worry',fx:['sweat']},
  ngo_ngac:{eyes:'dot',mouth:'smallo',brows:'up',fx:['qmark']},
  hon:{eyes:'closed',mouth:'pucker3',blush:1,fx:['fheart1']},
  mat_meo:{eyes:'happy',mouth:'cat',blush:.6,fx:['whiskers']},
};
// the pose's own face effects that go when a face is chosen (the face brings its own)
const POSE_FACE_FX={shine:1,blushlines:1,whiskers:1,ha:1,shock:1,twinkle:1};
function withFace(sp,face){
  const f=FACE_SPEC[face];if(!f)return sp;
  return {...sp,eyes:f.eyes,mouth:f.mouth,brows:f.brows||null,blush:f.blush||0,blushC:f.blushC||null,puff:!!f.puff,shades:false,
    fx:[...sp.fx.filter(x=>!POSE_FACE_FX[Array.isArray(x)?x[0]:x]),...(f.fx||[])]};
}

/* ---------------------------------------------------------------- pose specs
 * {arms: {l, r}, tilt, lean, lift, step, eyes, mouth, blush, brows, shades, fx}
 *   arm  null (resting at the side) | 'hide' (behind a friend) | {e: elbow, h: hand, hand: 'fist'|'open'|'v'|'thumb'|
 *        'point'|'fheart'|'paw'|'flat'|'phone', dir (the fingers' angle, default along the forearm), layer: 'mid'
 *        (over the body, behind the head) | 'front' | 'over' (over the friend next to them), muscle, keep (it holds the
 *        pose's own item: a booth prop never takes this hand)}
 *   items [{k: 'teddy'|'balloons'|'sign'|'cone'|'cup'|'pillow', x, y, layer, side, rot}]  held by the arm on `side`
 *   legs 'run'|'squat' (drawn here, else look.js paintLegs), sit (squat: the body is that much lower), twirl (a flared hem)
 *   points in the character's own units: feet at 0, up negative, shoulders at (±20, -44), the face around (0, -77). */
const A=(e,h,hand='fist',o={})=>({e,h,hand,...o});
const BASE={arms:{l:null,r:null},tilt:0,lean:0,lift:0,step:0,eyes:'open',mouth:'smile',blush:0,brows:null,shades:false,fx:[]};
const CROSSED={l:A([-29,-31],[13,-38]),r:A([29,-31],[-13,-41])};
const CLASPED={l:A([-27,-30],[-6,-28]),r:A([27,-30],[6,-28])};
const HIPS={l:A([-40,-36],[-23,-24]),r:A([40,-36],[23,-24])};
const SOLO={
  dung:()=>({}),
  v:()=>({arms:{r:A([36,-60],[34,-92],'v',{dir:-1.75})},tilt:.06,eyes:'wink',mouth:'grin'}),
  vay:()=>({arms:{r:A([38,-64],[44,-94],'open',{dir:-1.4})},tilt:-.06,mouth:'grin',fx:['wave']}),
  tim:()=>({arms:{l:A([-31,-30],[-10,-38]),r:A([31,-30],[10,-38])},eyes:'happy',fx:['handheart','hearts']}),
  tim_nho:()=>({arms:{r:A([36,-50],[40,-76],'fheart',{dir:-1.75})},eyes:'wink',tilt:.07,blush:.4}),
  tim_dau:()=>({arms:{l:A([-46,-100],[-6,-128],'fist',{layer:'mid'}),r:A([46,-100],[6,-128],'fist',{layer:'mid'})},eyes:'happy',mouth:'grin'}),
  ma:()=>({both:1,arms:{l:A([-33,-40],[-21,-57]),r:A([33,-40],[21,-57])},eyes:'happy',mouth:'cat',blush:1,tilt:.08}),
  nhay_mat:()=>({arms:{r:A([37,-56],[43,-82],'v',{dir:-.45})},eyes:'wink',mouth:'tongue',tilt:.1,fx:['twinkle']}),
  hoan_ho:()=>({arms:{l:A([-38,-66],[-44,-100],'open',{layer:'mid',dir:-1.85}),r:A([38,-66],[44,-100],'open',{layer:'mid',dir:-1.29})},eyes:'happy',mouth:'laugh',fx:['sparkle']}),
  nhay:()=>({lift:18,step:5,arms:{l:A([-40,-58],[-54,-84],'open'),r:A([40,-58],[54,-84],'open')},eyes:'big',mouth:'grin',tilt:-.05,fx:['jump']}),
  nghieng:()=>({tilt:-.18,arms:CLASPED,eyes:'happy',blush:.5}),
  like:()=>({arms:{l:A([-38,-38],[-44,-56],'thumb'),r:A([38,-38],[44,-56],'thumb')},eyes:'happy',mouth:'grin'}),
  ngau:()=>({arms:CROSSED,shades:true,mouth:'smirk',brows:'cool',tilt:-.08,fx:['shine']}),
  ngai:()=>({arms:{l:A([-25,-31],[-6,-40],'point',{dir:-.25}),r:A([25,-31],[6,-40],'point',{dir:Math.PI+.25})},eyes:'down',mouth:'wavy',blush:1.3,tilt:-.14,lean:.03,fx:['blushlines']}),
  suy_nghi:()=>({arms:{r:A([29,-30],[12,-53]),l:A([-26,-32],[22,-33])},eyes:'up',mouth:'flat',tilt:.1,fx:['think']}),
  cuoi:()=>({arms:{l:A([-30,-28],[-8,-26]),r:A([38,-52],[44,-76],'open',{dir:-1.25})},eyes:'laugh',mouth:'laugh',tilt:-.1,fx:['ha']}),
  ngac:()=>({both:1,arms:{l:A([-36,-48],[-28,-70],'flat',{dir:-1.45}),r:A([36,-48],[28,-70],'flat',{dir:-1.69})},eyes:'big',mouth:'o',brows:'up',fx:['shock']}),
  meo:()=>({both:1,arms:{l:A([-37,-54],[-33,-84],'paw'),r:A([37,-54],[33,-84],'paw')},eyes:'happy',mouth:'cat',tilt:.06,fx:['whiskers']}),
  gong:()=>({both:1,arms:{l:A([-47,-48],[-45,-74],'fist',{muscle:1}),r:A([47,-48],[45,-74],'fist',{muscle:1})},mouth:'grin',brows:'cool',fx:['sparkle']}),
  hon_gio:()=>({arms:{r:A([29,-46],[14,-62],'flat',{dir:-1.2})},eyes:'closed',mouth:'kiss',tilt:.08,fx:['kiss']}),
  chong_nanh:()=>({arms:HIPS,mouth:'grin',tilt:.06,eyes:'wink'}),
  om_gau:()=>({arms:{l:A([-32,-26],[-13,-19],'fist',{keep:1}),r:A([32,-28],[13,-23],'fist',{keep:1})},items:[{k:'teddy',x:0,y:-24}],
    eyes:'happy',mouth:'cat',blush:.9,tilt:.09,fx:['hearts']}),
  cam_bong:()=>({arms:{r:A([40,-50],[38,-74],'fist',{keep:1})},items:[{k:'balloons',x:38,y:-74,layer:'mid',side:1}],eyes:'big',mouth:'grin',tilt:-.06}),
  selfie:()=>({arms:{l:A([-42,-70],[-47,-102],'phone',{layer:'mid',dir:-1.62}),r:A([36,-46],[33,-72],'v',{dir:-1.68})},tilt:-.1,eyes:'wink',mouth:'grin'}),
  xoay_vay:()=>({twirl:1,step:3,arms:{l:A([-40,-58],[-56,-74],'open',{dir:-2.4}),r:A([40,-54],[57,-66],'open',{dir:-.78})},tilt:.1,eyes:'happy',mouth:'laugh',fx:['swirl']}),
  chay:()=>({legs:'run',lean:-.05,arms:{l:A([-38,-34],[-27,-56]),r:A([38,-40],[46,-22])},tilt:-.05,eyes:'big',mouth:'grin',fx:['speed']}),
  ngoi_xom:()=>({sit:14,legs:'squat',arms:{l:A([-38,-30],[-27,-37]),r:A([37,-46],[36,-74],'v',{dir:-1.6})},tilt:.1,eyes:'happy',mouth:'grin',blush:.5}),
  bong_hoa:()=>({both:1,arms:{l:A([-34,-32],[-15,-51],'open',{dir:-2.25}),r:A([34,-32],[15,-51],'open',{dir:-.89})},tilt:.07,eyes:'happy',mouth:'grin',blush:.8,fx:['sparkle']}),
  gio_bien:()=>({arms:{l:A([-44,-94],[-32,-124],'fist',{layer:'mid',keep:1}),r:A([44,-94],[32,-124],'fist',{layer:'mid',keep:1})},items:[{k:'sign',x:0,y:-138}],
    eyes:'happy',mouth:'laugh'}),
  an_kem:()=>({arms:{r:A([46,-30],[39,-45],'fist',{keep:1})},items:[{k:'cone',x:39,y:-54,side:1}],tilt:.1,eyes:'happy',mouth:'tongue',blush:.5}),
  tra_sua:()=>({arms:{r:A([40,-30],[20,-25],'fist',{keep:1}),l:A([-37,-58],[-41,-86],'v',{dir:-1.45})},items:[{k:'cup',x:10,y:-30,rot:.1,side:1}],tilt:-.06,eyes:'wink',mouth:'cat'}),
  chao:()=>({arms:{r:A([46,-72],[27,-94],'flat',{dir:Math.PI+.22}),l:HIPS.l},tilt:-.05,eyes:'wink',mouth:'grin'}),
  bay:()=>({lean:.08,step:3,arms:{l:A([-42,-50],[-58,-55],'flat',{dir:Math.PI+.1}),r:A([42,-46],[58,-42],'flat',{dir:.06})},tilt:.06,eyes:'happy',mouth:'grin',fx:['speedL']}),
  u_oa:()=>({both:1,arms:{l:A([-36,-48],[-12,-79],'open',{dir:-1.8}),r:A([36,-48],[12,-79],'open',{dir:-1.34})},tilt:.08,mouth:'grin',blush:.8}),
  om_tim:()=>({arms:{l:A([-32,-27],[-13,-22],'fist',{keep:1}),r:A([32,-29],[13,-27],'fist',{keep:1})},items:[{k:'pillow',x:0,y:-19}],
    eyes:'happy',mouth:'cat',blush:1,tilt:-.08,fx:['hearts']}),
  vo_tay:()=>({both:1,arms:{l:A([-34,-30],[-5,-42],'flat',{dir:-1.36}),r:A([34,-30],[5,-42],'flat',{dir:-1.78})},eyes:'happy',mouth:'laugh',tilt:.05,fx:['claps']}),
};
/* Group poses. type 'pair': neighbours two by two (the left 'a', the right 'b'); 'chain': each one with whoever is next
 * to them. gap: the distance between the two (units), so arms meet; alone: the solo pose of someone left without. */
const inward=r=>r.n<2?0:Math.sign((r.n-1)/2-r.i);   // +1: right of them is the middle of the group
const GROUP={
  tim_to:{type:'pair',gap:100,alone:'tim_dau',f:r=>r.pair==='a'
    ?{arms:{r:A([44,-104],[50,-124],'fist',{layer:'mid'}),l:A([-38,-36],[-22,-25])},tilt:.1,lean:.02,eyes:'happy',fx:[['bigheart',50,-92]]}
    :{arms:{l:A([-44,-104],[-50,-124],'fist',{layer:'mid'}),r:A([38,-36],[22,-25])},tilt:-.1,lean:-.02,eyes:'happy'}},
  tua_lung:{type:'pair',gap:80,alone:'ngau',f:r=>r.pair==='a'
    ?{arms:CROSSED,lean:.05,tilt:-.12,shades:true,mouth:'smirk',brows:'cool'}
    :{arms:CROSSED,lean:-.05,tilt:.12,eyes:'wink',mouth:'smirk',brows:'cool'}},
  chi_nhau:{type:'pair',gap:104,alone:'like',f:r=>r.pair==='a'
    ?{arms:{r:A([36,-52],[52,-60],'point',{dir:-.12}),l:HIPS.l},eyes:'big',mouth:'grin',lean:-.03,fx:[['zap',62,-64]]}
    :{arms:{l:A([-36,-52],[-52,-60],'point',{dir:Math.PI+.12}),r:HIPS.r},eyes:'laugh',mouth:'laugh',lean:.03}},
  khoac_vai:{type:'chain',gap:76,alone:'v',f:r=>({arms:{
      r:r.R?A([41,-49],[58,-42],'fist',{layer:'over'}):A([37,-40],[43,-58],'thumb'),
      l:r.L?'hide':A([-35,-60],[-38,-90],'v',{dir:-1.4})},
    tilt:inward(r)*.06,mouth:'grin',eyes:r.i%2?'happy':'open'})},
  dap_tay:{type:'chain',gap:104,alone:'vay',f:r=>({arms:{
      r:r.R?A([38,-80],[52,-110],'open',{dir:-1.15,layer:'mid'}):null,
      l:r.L?A([-38,-80],[-52,-110],'open',{dir:-1.99,layer:'mid'}):null},
    eyes:'big',mouth:'grin',lean:r.R&&!r.L?.04:r.L&&!r.R?-.04:0,fx:r.R?[['clap',52,-110]]:[]})},
  tua_vai:{type:'chain',gap:86,alone:'nghieng',f:r=>({lean:inward(r)*.05,tilt:inward(r)*.15||.08,arms:CLASPED,eyes:'happy',blush:.6})},
  cung_nhay:{type:'chain',gap:0,alone:'nhay',f:r=>({lift:r.i%2?26:14,step:5,arms:{l:A([-32,-64],[-38,-98],'open',{layer:'mid',dir:-1.8}),r:A([32,-64],[38,-98],'open',{layer:'mid',dir:-1.34})},
    eyes:r.i%2?'happy':'big',mouth:'laugh',tilt:r.i%2?.06:-.06,fx:['jump']})},
  chum_dau:{type:'chain',gap:80,alone:'chum_dau',f:r=>({tilt:inward(r)*.12,lean:inward(r)*.03,arms:{
      l:r.i===0?A([-42,-72],[-50,-106],'phone',{layer:'mid',dir:-1.7}):null,
      r:r.i===r.n-1?A([35,-58],[39,-88],'v',{dir:-1.75}):null},
    eyes:r.i%2?'wink':'happy',mouth:r.i%2?'tongue':'grin'})},
  nam_tay:{type:'chain',gap:92,alone:'hoan_ho',f:r=>({arms:{
      r:A([36,-72],[46,-102],r.R?'fist':'open',{layer:'mid',dir:-1.3}),l:A([-36,-72],[-46,-102],r.L?'fist':'open',{layer:'mid',dir:-1.84})},
    eyes:'happy',mouth:'laugh',fx:r.R?[['join',46,-104]]:[]})},
  // 1.5.2
  om_nhau:{type:'chain',gap:74,alone:'om_gau',f:r=>({arms:{
      r:r.R?'hide':A([36,-58],[40,-88],'v',{dir:-1.6}),
      l:r.L?A([-41,-49],[-58,-42],'fist',{layer:'over'}):A([-36,-58],[-40,-88],'v',{dir:-1.54})},
    tilt:inward(r)*.14,lean:inward(r)*.03,eyes:'happy',mouth:'grin',blush:.9,fx:r.R?[['miniheart',37,-122]]:[]})},
  tau_hoa:{type:'chain',gap:80,alone:'chay',f:r=>({lean:-.03,step:r.i%2?4:-4,arms:{
      l:r.L?A([-40,-50],[-57,-47],'flat',{layer:'over',dir:Math.PI}):A([-40,-66],[-36,-96],'fist'),
      r:r.R?null:A([40,-56],[48,-82],'open',{dir:-1.3})},
    eyes:r.L?'happy':'big',mouth:r.L?'grin':'o',fx:r.L?(r.R?[]:['speed']):[['puff',-34,-128]]})},
  xoa_dau:{type:'pair',gap:74,alone:'ngoi_xom',f:r=>r.pair==='a'
    ?{sit:14,legs:'squat',arms:{l:A([-37,-46],[-38,-74],'v',{dir:-1.6}),r:A([38,-30],[27,-37])},eyes:'happy',mouth:'cat',blush:1,tilt:.1}
    :{lean:-.04,arms:{l:A([-44,-80],[-62,-100],'flat',{layer:'over',dir:Math.PI+.12}),r:A([38,-38],[44,-56],'thumb')},eyes:'wink',mouth:'grin',tilt:-.08}},
  cung_ly:{type:'chain',gap:84,alone:'tra_sua',f:r=>{
    const arms={},items=[];
    if(r.R){arms.r=A([43,-66],[33,-90],'fist',{keep:1});items.push({k:'cup',x:34.5,y:-103,rot:.28,side:1});}
    if(r.L){arms.l=A([-43,-66],[-33,-90],'fist',{keep:1});items.push({k:'cup',x:-34.5,y:-103,rot:-.28,side:-1});}
    return {arms,items,eyes:'happy',mouth:'laugh',fx:r.R?[['clink',42,-126]]:[]};}},
};
function solo(id){const f=SOLO[id]||SOLO[DEFAULT];const s=f();return {...BASE,...s,arms:{...BASE.arms,...(s.arms||{})},fx:s.fx||[]};}
function group(id,role){const g=GROUP[id],s=g.f(role);return {...BASE,...s,arms:{...BASE.arms,...(s.arms||{})},fx:s.fx||[]};}

/** Who is with whom: runs of neighbours in the same group pose; pairs two by two in a run. */
function roles(ids){
  const out=ids.map(id=>({id,i:0,n:1,L:false,R:false,pair:null,alone:true}));
  for(let i=0;i<ids.length;){
    let j=i;
    if(GROUP[ids[i]])while(j+1<ids.length&&ids[j+1]===ids[i])j++;
    const n=j-i+1,g=GROUP[ids[i]];
    for(let k=i;k<=j;k++){
      const r=out[k];r.i=k-i;r.n=n;
      if(!g||n<2)continue;
      if(g.type==='pair'){const a=r.i%2===0;if(a&&r.i+1<n){r.pair='a';r.R=true;r.alone=false;}else if(!a){r.pair='b';r.L=true;r.alone=false;}}
      else{r.L=k>i;r.R=k<j;r.alone=false;}
    }
    i=j+1;
  }
  return out;
}
function specOf(r){
  const g=GROUP[r.id];
  if(!g)return solo(known(r.id)?r.id:DEFAULT);
  if(r.alone)return g.alone===r.id?group(r.id,{...r,i:0,n:1,L:false,R:false}):solo(g.alone);
  return group(r.id,r);
}

/* ---------------------------------------------------------------- props (the booth's hats, glasses and hand items) */
const HAT={mu_tiec:1,non_la:1,mu_tn:1,tai_tho:1,vuong_mien:1},EYES={kinh_tim:1,kinh_ram:1},HAND={bang_chu:1,hoa:1,bong_bay:1,long_den:1};
const PROP_TOP={mu_tiec:152,non_la:144,mu_tn:134,tai_tho:154,vuong_mien:138};
function starShape(c,x,y,Ro,ri,fill){c.beginPath();for(let i=0;i<10;i++){const a=-Math.PI/2+i*Math.PI/5,d=i%2?ri:Ro;c.lineTo(x+Math.cos(a)*d,y+Math.sin(a)*d);}c.closePath();c.fillStyle=fill;c.fill();}
function headProp(c,id){
  switch(id){
    case'mu_tiec':c.save();c.translate(10,-112);c.rotate(.28);P(c,[[-14,0],[14,0],[0,-38]],'#5bb6d9');for(let i=1;i<4;i++){const y=-38*i/4,w=14*(1-i/4);L(c,-w,y,w,y,'#f2c84b',3);}E(c,0,-39,5,5,'#e2574c');c.restore();break;
    case'non_la':P(c,[[-46,-104],[46,-104],[0,-142]],'#efd79a');L(c,-46,-104,46,-104,'#c9a75a',2.5);L(c,-30,-115,30,-115,'#d8bc72',1.2);L(c,-16,-126,16,-126,'#d8bc72',1.2);break;
    case'mu_tn':P(c,[[-38,-118],[0,-132],[38,-118],[0,-104]],'#1f2a44');R(c,-20,-118,40,14,'#1f2a44',4);E(c,0,-118,3,2.4,'#f2c84b');L(c,0,-118,24,-113,'#f2c84b',1.6);L(c,24,-113,25,-98,'#f2c84b',3);break;
    case'tai_tho':c.strokeStyle='#ffffff';c.lineWidth=4;c.beginPath();c.arc(0,-84,34,Math.PI*1.1,Math.PI*1.9);c.stroke();
      for(const s of [-1,1]){c.save();c.translate(s*15,-130);c.rotate(s*.2);E(c,0,0,8,22,'#ffffff');E(c,0,2,4,15,'#ffb3cf');c.restore();}break;
    case'vuong_mien':P(c,[[-20,-110],[-21,-132],[-10,-120],[0,-136],[10,-120],[21,-132],[20,-110]],'#f2c84b');E(c,0,-117,3.2,3.2,'#e2574c');E(c,-12,-115,2.4,2.4,'#5bb6d9');E(c,12,-115,2.4,2.4,'#5bb6d9');break;
    case'kinh_tim':heart(c,-11,-75,.36,'#e8335a');heart(c,11,-75,.36,'#e8335a');L(c,-4,-80,4,-80,'#e8335a',2);break;
    case'kinh_ram':shades(c);break;
  }
}
function handProp(c,id,[hx,hy],side,skin,sign){
  switch(id){
    case'bang_chu':{R(c,-30,-44,60,26,'#fffaf0',5,'#c79879',2);c.font='900 11px "Trebuchet MS",sans-serif';c.fillStyle='#d0567f';c.textAlign='center';c.textBaseline='middle';c.fillText(sign,0,-30.5,54);
      E(c,-29,-32,6,6,skin);E(c,29,-32,6,6,skin);break;}
    case'hoa':for(let i=0;i<5;i++)CANVAS.bloom(c,hx-7+(i%3)*7,hy-12+Math.floor(i/3)*7,6,['#ff8fab','#f2c84b','#ffffff','#d9506c','#ffb3cf'][i]);P(c,[[hx-8,hy-2],[hx+6,hy-2],[hx-1,hy+14]],'#9cc58a');E(c,hx,hy,6,6,skin);break;
    case'bong_bay':{const bx=hx+side*10,by=hy-58;c.strokeStyle='#9c7b6a';c.lineWidth=1.2;c.beginPath();c.moveTo(hx,hy);c.quadraticCurveTo(hx+side*14,hy-24,bx,by+20);c.stroke();
      E(c,bx,by,15,18,'#e2574c');P(c,[[bx-3,by+18],[bx+3,by+18],[bx,by+14]],'#e2574c');E(c,bx-5,by-6,3.4,6,'#ffffff66');E(c,hx,hy,6,6,skin);break;}
    case'long_den':{L(c,hx,hy,hx+side*8,hy-30,'#8b5e3c',2.4);const lx=hx+side*14,ly=hy-26;starShape(c,lx,ly+14,15,6.8,'#c0392b');starShape(c,lx,ly+14,11.5,5.2,'#f2c84b');E(c,lx,ly+14,2.6,2.6,'#fff3c4');E(c,hx,hy,6,6,skin);break;}
  }
}
/** A hand item needs a free hand: the right one if it rests, else the left, else the right lets go of its pose; the
 * sign takes both hands. */
function withProp(sp,prop){
  if(!HAND[prop])return {sp,hold:null};
  // a hand holding the pose's own item keeps it: the prop takes the other hand, or none (the pose's item wins)
  const kept=a=>!!(a&&a!=='hide'&&a.keep),kl=kept(sp.arms.l),kr=kept(sp.arms.r);
  if(kl||kr){
    if(prop==='bang_chu'||kl&&kr)return {sp,hold:null};
    const side=kr?-1:1,arms=side>0?{l:sp.arms.l,r:null}:{l:null,r:sp.arms.r};
    return {sp:{...sp,arms},hold:{at:[side*25,-36],side}};
  }
  if(prop==='bang_chu')return {sp:{...sp,arms:{l:null,r:null}},hold:{at:[0,-36],side:1}};
  if(sp.arms.r==null)return {sp,hold:{at:[25,-36],side:1}};
  if(sp.arms.l==null)return {sp,hold:{at:[-25,-36],side:-1}};
  // both hands busy: the lower hand lets go (the raised one makes the pose: a half heart, a V); the other keeps its
  // gesture only when it is one of its own (on its side); arms that make one gesture together both let go
  const {l,r}=sp.arms,y=a=>a==='hide'?-1e3:a.h[1];
  const side=sp.both||r==='hide'||l==='hide'||y(r)>=y(l)?1:-1,other=side>0?l:r;
  const keep=!sp.both&&(other==='hide'||-side*other.h[0]>14);
  const arms=side>0?{l:keep?l:null,r:null}:{l:null,r:keep?r:null};
  return {sp:{...sp,arms},hold:{at:[side*25,-36],side}};
}

/* ---------------------------------------------------------------- the face */
function shades(c){R(c,-21,-85,19,13,'#1d1d24',6);R(c,2,-85,19,13,'#1d1d24',6);L(c,-2,-80,2,-80,'#1d1d24',2);L(c,-17,-82,-12,-82,'#ffffff70',1.5);L(c,6,-82,11,-82,'#ffffff50',1.5);}
function stroke(c,col,w,fn){c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.lineJoin='round';c.beginPath();fn();c.stroke();}
function eyes(c,kind,F){
  const open=(ex,dx=0,dy=0,k=1)=>{E(c,ex+dx,-78+dy,5*k,7*k,INK);E(c,ex+dx-1.3*k,-80.4+dy,1.8*k,2.3*k,'#fffdf3');E(c,ex+dx+1,-75+dy,1,1,'#d7b895');};
  const happy=ex=>stroke(c,INK,2.6,()=>c.arc(ex,-75,5.2,Math.PI*1.1,Math.PI*1.9));
  const closed=ex=>stroke(c,INK,2.4,()=>c.arc(ex,-80,5,Math.PI*.12,Math.PI*.88));
  const skin=F?.skin?.face||'#f8dcc2';
  for(const ex of [-11,11]){
    const right=ex>0,inner=right?-1:1;
    switch(kind){
      case'star':starShape(c,ex,-78,9,4.3,INK);starShape(c,ex,-78,7,3.3,'#ffcf3d');E(c,ex-1.6,-80.2,1.4,1.4,'#fffdf3');break;
      case'heart':heart(c,ex,-75.2,.5,'#b8264c');heart(c,ex,-75.4,.42,'#ff4f7b');E(c,ex-3.2,-80,1.6,1.2,'#ffffffcc');break;
      case'round':E(c,ex,-78,6.6,7.8,INK);E(c,ex,-78,5.2,6.4,'#ffffff');E(c,ex+inner*.6,-77.6,1.9,2.1,INK);break;
      case'dot':E(c,ex,-77.5,2.7,3.2,INK);E(c,ex-.8,-78.6,.8,.8,'#fffdf3');break;
      case'sleep':stroke(c,INK,2.4,()=>{c.moveTo(ex-5.5,-78);c.quadraticCurveTo(ex,-74,ex+5.5,-78);});
        stroke(c,INK,1.4,()=>{c.moveTo(ex-4.5*inner-.5*inner,-77);c.lineTo(ex-7*inner,-75.5);});break;
      case'cry':stroke(c,INK,2.6,()=>{c.moveTo(ex-6,-80);c.quadraticCurveTo(ex,-77.5,ex+6,-80);});break;
      case'angry':open(ex,inner*.5,1);P(c,[[ex-8,-85.6],[ex+8,-85.6],[ex+8,inner>0?-77:-84],[ex-8,inner>0?-84:-77]],skin);
        L(c,ex-6.5,inner>0?-83.4:-78.6,ex+6.5,inner>0?-78.6:-83.4,INK,2);break;
      case'sulk':open(ex,-2,1);P(c,[[ex-8,-85.6],[ex+8,-85.6],[ex+8,-79.5],[ex-8,-79.5]],skin);L(c,ex-6,-79.5,ex+6,-79.5,INK,2);break;
      case'wink':right?happy(ex):open(ex);break;
      case'happy':happy(ex);break;
      case'closed':closed(ex);break;
      case'laugh':stroke(c,INK,2.6,()=>{const s=right?-1:1;c.moveTo(ex-4*s,-83);c.lineTo(ex+4*s,-78);c.lineTo(ex-4*s,-73);});break;
      case'big':open(ex,0,0,1.18);E(c,ex+1.8,-75.5,1.2,1.2,'#fffdf3');break;
      case'down':E(c,ex,-75.5,4.6,5.2,INK);E(c,ex-1.2,-76.6,1.4,1.5,'#fffdf3');stroke(c,INK,2,()=>{c.moveTo(ex-5.5,-79.5);c.quadraticCurveTo(ex,-81.5,ex+5.5,-79.5);});break;
      case'up':open(ex,1.4,-1.6,.94);break;
      default:open(ex);
    }
  }
}
function brows(c,kind,F){
  const col=F.hair;
  if(kind==='up'){for(const s of [-1,1])stroke(c,col,2.2,()=>c.arc(s*11,-88,6,Math.PI*1.2,Math.PI*1.8));return;}
  if(kind==='cool'){L(c,-17,-91,-6,-88,col,2.4);L(c,6,-88,17,-91,col,2.4);return;}
  if(kind==='angry'){L(c,-17,-93,-5,-87,col,2.8);L(c,5,-87,17,-93,col,2.8);return;}
  if(kind==='worry'){L(c,-17,-88,-6,-92,col,2.4);L(c,6,-92,17,-88,col,2.4);return;}
  if(F.g==='male'){L(c,-16,-89,-6,-90,col,2.4);L(c,6,-90,16,-89,col,2.4);}
}
function mouth(c,kind){
  switch(kind){
    case'grin':c.beginPath();c.moveTo(-6.5,-67);c.quadraticCurveTo(0,-56.5,6.5,-67);c.closePath();c.fillStyle=MOUTH;c.fill();R(c,-4.6,-67.2,9.2,2.4,'#ffffff',1.2);E(c,0,-61.6,2.8,1.7,TONGUE);break;
    case'laugh':c.beginPath();c.moveTo(-8,-68);c.quadraticCurveTo(0,-52.5,8,-68);c.closePath();c.fillStyle=MOUTH;c.fill();R(c,-5.6,-68.2,11.2,2.6,'#ffffff',1.3);E(c,0,-59.6,3.6,2.3,TONGUE);break;
    case'o':E(c,0,-63.5,3.3,4.3,MOUTH);E(c,0,-61.6,1.9,1.5,TONGUE);break;
    case'cat':stroke(c,LIP,1.7,()=>{c.arc(-2.5,-66,2.5,0,Math.PI);c.moveTo(5,-66);c.arc(2.5,-66,2.5,0,Math.PI);});break;
    case'tongue':E(c,1.6,-62.8,2.3,2.9,TONGUE);CANVAS.stroke(c,'M4 -66A4 4 0 0 1 -4 -66',LIP,1.6);break;
    case'smirk':stroke(c,LIP,1.8,()=>{c.moveTo(-4,-65.5);c.quadraticCurveTo(1,-63.2,5.5,-67.6);});break;
    case'kiss':E(c,0,-64.5,2.4,2.6,'#d8707c');E(c,-.6,-65.2,.8,.9,'#f3b0b8');break;
    case'flat':L(c,-3.5,-64.6,3.5,-65.4,LIP,1.8);break;
    case'wavy':stroke(c,LIP,1.6,()=>{c.moveTo(-5,-64.5);c.quadraticCurveTo(-3.3,-66.5,-1.7,-64.5);c.quadraticCurveTo(0,-62.5,1.7,-64.5);c.quadraticCurveTo(3.3,-66.5,5,-64.5);});break;
    case'bigsmile':c.beginPath();c.moveTo(-9,-67.5);c.quadraticCurveTo(0,-52,9,-67.5);c.closePath();c.fillStyle=MOUTH;c.fill();E(c,0,-59.4,4.2,2.6,TONGUE);break;
    case'tongue_out':c.beginPath();c.moveTo(-6.5,-67);c.quadraticCurveTo(0,-59.5,6.5,-67);c.closePath();c.fillStyle=MOUTH;c.fill();
      E(c,1.8,-60,3.8,5,TONGUE);L(c,1.8,-62.6,1.8,-58,'#d8677c',1.1);break;
    case'wail':c.beginPath();c.moveTo(-7.5,-58.5);c.quadraticCurveTo(0,-73,7.5,-58.5);c.quadraticCurveTo(0,-61.5,-7.5,-58.5);c.fillStyle=MOUTH;c.fill();E(c,0,-60.2,3,1.4,TONGUE);break;
    case'frown':stroke(c,LIP,2,()=>{c.moveTo(-5,-61.5);c.quadraticCurveTo(0,-67,5,-61.5);});break;
    case'pucker':E(c,0,-63.2,3,2.4,'#d8707c');L(c,-1.6,-63.2,1.6,-63.2,'#b55764',1);break;
    case'pucker3':stroke(c,'#c65a6a',1.9,()=>{c.moveTo(-1.5,-68);c.quadraticCurveTo(3.5,-67,1,-64.2);c.quadraticCurveTo(3.5,-61.5,-1.5,-60.5);});E(c,5.5,-64.2,1.2,1.2,'#ffb3c3');break;
    case'scream':E(c,0,-61,5,7.2,MOUTH);E(c,0,-57,3.2,2.2,TONGUE);break;
    case'smallo':E(c,0,-63,2.4,2.8,MOUTH);break;
    default:CANVAS.stroke(c,'M4 -66A4 4 0 0 1 -4 -66',LIP,1.6);
  }
}
function sparkle(c,x,y,s,fill){c.beginPath();c.moveTo(x,y-s);c.quadraticCurveTo(x,y,x+s,y);c.quadraticCurveTo(x,y,x,y+s);c.quadraticCurveTo(x,y,x-s,y);c.quadraticCurveTo(x,y,x,y-s);c.fillStyle=fill;c.fill();}

/* ---------------------------------------------------------------- arms and hands */
function hand(c,F,a,side=1){
  const [x,y]=a.h,sk=F.skin.hand,ol=F.skin.neck;
  const dir=a.dir??Math.atan2(a.h[1]-a.e[1],a.h[0]-a.e[0]);
  const finger=(ang,len,w=3.6,from=0)=>{const x1=x+Math.cos(ang)*from,y1=y+Math.sin(ang)*from,x2=x+Math.cos(ang)*len,y2=y+Math.sin(ang)*len;L(c,x1,y1,x2,y2,ol,w+1.6);L(c,x1,y1,x2,y2,sk,w);};
  const palm=(rx=7,ry=7.5)=>{E(c,x,y,rx+.9,ry+.9,ol);E(c,x,y,rx,ry,sk);};
  switch(a.hand){
    case'open':for(const k of [-.5,-.17,.17,.5])finger(dir+k,10.5,3.3);finger(dir+(dir<-Math.PI/2?-1.25:1.25),8,3.4);palm(7.6,7.6);break;
    case'v':finger(dir-.24,14,3.6);finger(dir+.24,14,3.6);palm();break;
    case'thumb':{c.save();c.translate(x,y);c.rotate(side*.18);const tx=-side*3.2;
      L(c,tx,-4,tx-side*.6,-12.5,ol,7.4);L(c,tx,-4,tx-side*.6,-12.5,sk,5.8);E(c,tx-side*.6,-13.6,1.7,1.3,'#ffffff66');
      R(c,-8.9,-5.9,17.8,13.8,ol,5.6);R(c,-8,-5,16,12,sk,5);for(const fy of [-1.2,2.4])L(c,side*-1.5,fy,side*7,fy,ol,1.1);c.restore();break;}
    case'point':finger(dir,14,3.6);palm();break;
    case'fheart':finger(dir-.2,10,3.4);finger(dir+.3,9,3.6);palm();heart(c,x+Math.cos(dir)*17,y+Math.sin(dir)*17-1,.34,'#ff4f7b');break;
    case'paw':palm(8,7.4);for(const [dx,dy] of [[-4.6,-5.4],[0,-7.4],[4.6,-5.4]]){E(c,x+dx,y+dy,3.1,3.1,ol);E(c,x+dx,y+dy,2.4,2.4,sk);}E(c,x,y+1,3.2,2.3,'#f4a6b8');break;
    case'flat':c.save();c.translate(x,y);c.rotate(dir);E(c,2,0,11,7.6,ol);E(c,2,0,10.1,6.7,sk);L(c,6,-2.2,11,-2.2,ol,.9);L(c,6,1.6,11,1.6,ol,.9);c.restore();break;
    case'phone':c.save();c.translate(x,y);c.rotate(dir+Math.PI/2);R(c,-8,-20,16,26,'#3a3550',4);R(c,-6,-18,12,21,'#f2eefb',3);E(c,-3,-15,1.6,1.6,'#3a3550');c.restore();palm();break;
    default:palm();
  }
}
const shade=(hex,k=.8)=>{const m=/^#([0-9a-f]{6})/i.exec(String(hex||''));if(!m)return '#00000033';const n=parseInt(m[1],16);
  return '#'+[16,8,0].map(b=>Math.round(((n>>b)&255)*k).toString(16).padStart(2,'0')).join('');};
function drawArm(c,F,side,a){
  const col=F.topC||F.classic,sx=side*20,sy=-44,line=w=>{c.lineWidth=w;c.lineCap='round';c.lineJoin='round';c.beginPath();c.moveTo(sx,sy);c.lineTo(a.e[0],a.e[1]);c.lineTo(a.h[0],a.h[1]);c.stroke();};
  c.strokeStyle=shade(col,.82);line(12.6);
  if(a.muscle){const mx=(sx+a.e[0])/2,my=(sy+a.e[1])/2;E(c,mx,my-4.5,9.3,7.3,shade(col,.82));E(c,mx,my-4.5,8.5,6.5,col);}
  c.strokeStyle=col;line(10.6);E(c,sx,sy,5.3,5.3,col);
  hand(c,F,a,side);
}
const armsOf=(sp,layer)=>[[-1,sp.arms.l],[1,sp.arms.r]].filter(([,a])=>a&&a!=='hide'&&(a.layer||'front')===layer);

/* ---------------------------------------------------------------- effects around a person */
const FX_LAYER={bigheart:'mid',whiskers:'head',blushlines:'head',shine:'head',clap:'over',join:'over',zap:'over',
  tears:'head',joytears:'head',bubble:'head',fsparkle:'top',fhearts:'top',fheart1:'top',zzz:'top',anger:'top',sweat:'top',qmark:'top',
  miniheart:'over',clink:'over',puff:'mid'};
function drop(c,x,y,k,fill){c.beginPath();c.moveTo(x,y-8*k);c.bezierCurveTo(x+6*k,y-1*k,x+5*k,y+5*k,x,y+5*k);c.bezierCurveTo(x-5*k,y+5*k,x-6*k,y-1*k,x,y-8*k);
  c.fillStyle=fill;c.fill();c.strokeStyle='#ffffff';c.lineWidth=1.4;c.stroke();E(c,x-1.6*k,y,1.1*k,1.8*k,'#ffffffcc');}
function word(c,s,x,y,size,fill){c.font=`900 ${size}px "Trebuchet MS",sans-serif`;c.textAlign='center';c.textBaseline='middle';c.lineJoin='round';
  c.strokeStyle='#ffffff';c.lineWidth=3;c.strokeText(s,x,y);c.fillStyle=fill;c.fillText(s,x,y);}
/** The new effects (faces and the 1.5.2 poses). */
function effect2(c,k,x,y){
  switch(k){
    case'tears':for(const s of [-1,1]){const tx=s*11;R(c,tx-3.2,-76,6.4,22,'#8fd3ffdd',3.2);L(c,tx-1,-73,tx-1,-58,'#ffffffaa',1.2);E(c,tx+s*2,-53,4.6,2.6,'#8fd3ffcc');}break;
    case'joytears':for(const s of [-1,1])drop(c,s*20,-77,.62,'#8fd3ff');break;
    case'bubble':E(c,9,-66,5.4,5.4,'#cfeaffcc');stroke(c,'#8fc4e8',1,()=>c.arc(9,-66,5.4,0,TAU));E(c,7.2,-67.8,1.5,1.2,'#ffffff');break;
    case'fsparkle':for(const [sx,sy,s] of [[-38,-102,5.5],[39,-98,6.5],[31,-124,4]]){sparkle(c,sx,sy,s+1.4,'#ffffff');sparkle(c,sx,sy,s,'#ffcf3d');}break;
    case'fhearts':for(const [hx,hy,s] of [[-36,-104,.26],[38,-108,.32],[27,-126,.2]]){heart(c,hx,hy,s+.06,'#ffffff');heart(c,hx,hy,s,'#ff4f7b');}break;
    case'fheart1':heart(c,31,-60,.32,'#ffffff');heart(c,31,-60,.26,'#ff4f7b');break;
    case'zzz':word(c,'z',31,-104,10,'#6f86c4');word(c,'Z',40,-115,13,'#6f86c4');word(c,'Z',50,-129,16,'#6f86c4');break;
    case'anger':for(const [sx,sy] of [[-1,-1],[1,-1],[-1,1],[1,1]])for(const [col,w] of [['#ffffff',4.6],['#e8433a',2.4]])
      stroke(c,col,w,()=>{c.moveTo(26+sx*2,-106+sy*7);c.quadraticCurveTo(26+sx*2,-106+sy*2,26+sx*7,-106+sy*2);});break;
    case'sweat':drop(c,-30,-94,1.25,'#8fd3ff');break;
    case'qmark':word(c,'?',37,-114,22,'#8a6a58');break;
    case'swirl':stroke(c,'#8a6a58aa',1.8,()=>c.ellipse(0,-10,42,9,0,Math.PI*.12,Math.PI*.88));stroke(c,'#8a6a58aa',1.8,()=>c.ellipse(0,-14,46,11,0,Math.PI*1.08,Math.PI*1.32));
      stroke(c,'#8a6a58aa',1.8,()=>c.ellipse(0,-14,46,11,0,Math.PI*1.68,Math.PI*1.92));sparkle(c,-40,-30,4.4,'#ffcf3d');sparkle(c,42,-26,3.6,'#ffcf3d');break;
    case'speed':for(const [sy,x0,x1] of [[-6,28,46],[-15,31,51],[-36,54,64]])L(c,x0,sy,x1,sy,'#8a6a5877',2.4);break;
    case'speedL':for(const [sy,x0,x1] of [[-6,-28,-46],[-15,-31,-51],[-26,-34,-50]])L(c,x0,sy,x1,sy,'#8a6a5877',2.4);break;
    case'claps':for(const s of [-1,1]){L(c,s*12,-54,s*19,-61,'#ffb020',2.4);L(c,s*15,-46,s*24,-48,'#ffb020',2.4);}
      sparkle(c,-30,-62,4,'#ffcf3d');sparkle(c,31,-66,3.4,'#ffcf3d');break;
    case'miniheart':heart(c,x,y,.4,'#ffffff');heart(c,x,y,.32,'#ff5c8a');break;
    case'puff':for(const [px,py,r] of [[x,y,8],[x-11,y+5,6],[x+8,y-9,6.5],[x-6,y-13,4.5]]){E(c,px,py,r+1.4,r+1.2,'#d9cfc6');}
      for(const [px,py,r] of [[x,y,8],[x-11,y+5,6],[x+8,y-9,6.5],[x-6,y-13,4.5]])E(c,px,py,r,r-.2,'#ffffff');break;
    case'clink':sparkle(c,x,y,8,'#ffffff');sparkle(c,x,y,6,'#ffcf3d');for(const a of [-2.2,-1.57,-.94])L(c,x+Math.cos(a)*10,y+Math.sin(a)*10,x+Math.cos(a)*15,y+Math.sin(a)*15,'#ffb020',2);break;
  }
}
function effect(c,k,x,y){
  switch(k){
    case'sparkle':for(const [sx,sy,s] of [[-42,-112,6],[44,-104,5],[-48,-80,4],[40,-128,3.5]]){sparkle(c,sx,sy,s+1.4,'#ffffff');sparkle(c,sx,sy,s,'#ffcf3d');}break;
    case'hearts':for(const [hx,hy,s] of [[-36,-106,.26],[40,-112,.32],[28,-130,.2]])heart(c,hx,hy,s,'#ff5c8a');break;
    case'handheart':heart(c,0,-35,.5,'#ff4f7b');E(c,-3,-42,2,1.4,'#ffffff88');break;
    case'wave':for(const r of [14,21])stroke(c,'#8a6a58aa',1.8,()=>c.arc(44,-94,r,-1.15,-.25));break;
    case'twinkle':sparkle(c,30,-96,6,'#ffffff');sparkle(c,30,-96,4.4,'#ffcf3d');break;
    case'think':for(const [tx,ty,r] of [[34,-102,2.4],[41,-112,3.6],[52,-128,7.5]]){E(c,tx,ty,r+1.2,r+1.2,'#8a6a5899');E(c,tx,ty,r,r,'#ffffff');}
      for(const dx of [-3,0,3])E(c,52+dx,-128,.9,.9,'#8a6a58');break;
    case'shock':L(c,-22,-124,-29,-134,'#5b4436',2.2);L(c,0,-128,0,-141,'#5b4436',2.2);L(c,22,-124,29,-134,'#5b4436',2.2);break;
    case'kiss':for(const [hx,hy,s] of [[30,-74,.22],[42,-86,.3],[56,-100,.24]])heart(c,hx,hy,s,'#ff4f7b');break;
    case'jump':for(const [jx,jy] of [[-14,6],[0,9],[14,6]])L(c,jx,jy,jx,jy+7,'#8a6a5877',2);break;
    case'ha':for(const [hx,hy,a0] of [[38,-100,-1.2],[-40,-98,-2.3]])stroke(c,'#8a6a58aa',1.8,()=>c.arc(hx,hy,8,a0-.6,a0+.6));sparkle(c,44,-118,4,'#ffcf3d');break;
    case'whiskers':for(const s of [-1,1]){L(c,s*17,-69,s*31,-71,INK,1.3);L(c,s*17,-65,s*31,-63,INK,1.3);}break;
    case'blushlines':for(const s of [-1,1])for(const k of [-4,0,4])L(c,s*20+k+1.2,-70,s*20+k-1.2,-65,'#e07a7a',1.3);break;
    case'shine':sparkle(c,-16,-84,4,'#ffffff');break;
    case'bigheart':heart(c,x,y,1.32,'#ffffffcc');heart(c,x,y,1.16,'#ff6f9f');E(c,x-8,y-14,3.4,2.4,'#ffffff99');break;
    case'clap':for(let i=0;i<8;i++){const a=i*TAU/8;L(c,x+Math.cos(a)*11,y+Math.sin(a)*11,x+Math.cos(a)*17,y+Math.sin(a)*17,'#ffb020',2.4);}sparkle(c,x,y-2,6,'#fff6cf');break;
    case'join':sparkle(c,x,y-12,6,'#ffffff');sparkle(c,x,y-12,4.4,'#ffcf3d');break;
    case'zap':for(const a of [-.5,0,.5])L(c,x+Math.cos(a)*4,y+Math.sin(a)*4,x+Math.cos(a)*10,y+Math.sin(a)*10,'#ff7a59',2);break;
    default:effect2(c,k,x,y);
  }
}
function effects(c,sp,layer){for(const f of sp.fx){const [k,x=0,y=0]=Array.isArray(f)?f:[f];if((FX_LAYER[k]||'front')===layer)effect(c,k,x,y);}}

/* ---------------------------------------------------------------- the poses' own items, legs and hems */
// [left, right, top] of each item around its point (top: how far up it reaches)
const ITEM_BOX={teddy:[-18,18,24],balloons:[-24,34,70],sign:[-40,40,15],cone:[-10,10,25],cup:[-10,12,33],pillow:[-23,23,27]};
function teddy(c,x,y){
  const fur='#c98f62',lt='#f3d2a8',dk='#5a3a2a';
  E(c,x,y+7,12.5,11.5,fur);E(c,x,y+9,7,6.5,lt);
  for(const s of [-1,1]){E(c,x+s*9.5,y-18,5,5,fur);E(c,x+s*9.5,y-18,2.6,2.6,lt);E(c,x+s*8,y+17,4.6,3.4,fur);}
  E(c,x,y-9,12.5,11,fur);E(c,x,y-5,5.2,3.9,lt);E(c,x,y-6.6,1.9,1.4,dk);
  E(c,x-5,y-11,1.6,1.9,dk);E(c,x+5,y-11,1.6,1.9,dk);E(c,x-8.5,y-6,2,1.2,'#f29a9a99');E(c,x+8.5,y-6,2,1.2,'#f29a9a99');
  P(c,[[x,y+2],[x-6.5,y-1.5],[x-6.5,y+5.5]],'#ff6f9f');P(c,[[x,y+2],[x+6.5,y-1.5],[x+6.5,y+5.5]],'#ff6f9f');E(c,x,y+2,2,2,'#e2507a');
}
function balloons(c,x,y){
  for(const [bx,by,col] of [[-12,-46,'#ff7aa2'],[22,-38,'#6ec6f0'],[7,-56,'#ffd166']]){
    stroke(c,'#9c7b6a',1.1,()=>{c.moveTo(x,y);c.quadraticCurveTo(x+bx*.2,y+by*.5,x+bx,y+by+13);});
    E(c,x+bx,y+by,10.5,12.5,col);P(c,[[x+bx-2.6,y+by+14],[x+bx+2.6,y+by+14],[x+bx,y+by+11]],col);E(c,x+bx-3.6,y+by-4.5,2.6,4.4,'#ffffff88');
  }
}
function signItem(c,x,y,text){
  R(c,x-38,y-13,76,26,'#fffaf0',7,'#c79879',2.2);
  heart(c,x-28,y+1.6,.28,'#ff6f9f');heart(c,x+28,y+1.6,.28,'#ff6f9f');
  c.font='900 12px "Trebuchet MS",sans-serif';c.fillStyle='#d0567f';c.textAlign='center';c.textBaseline='middle';c.fillText(text,x,y+.5,44);
}
function cone(c,x,y){
  P(c,[[x-7.5,y-7],[x+7.5,y-7],[x,y+10]],'#e3a75e');
  stroke(c,'#c4843f',1,()=>{c.moveTo(x-5,y-6);c.lineTo(x+2,y+5);c.moveTo(x+5,y-6);c.lineTo(x-2,y+5);c.moveTo(x-1,y-6.5);c.lineTo(x+4,y);c.moveTo(x+1,y-6.5);c.lineTo(x-4,y);});
  E(c,x,y-13,9,8,'#ffc0d2');E(c,x-5,y-7.5,2.6,3,'#ffc0d2');E(c,x+1.5,y-7,2.4,3.4,'#ffc0d2');E(c,x+5.6,y-8,2.2,2.6,'#ffc0d2');
  E(c,x-3,y-16.5,2.6,1.7,'#ffffffaa');E(c,x+1.5,y-21.5,2.8,2.8,'#e2574c');E(c,x+.6,y-22.5,.9,.9,'#ffffffaa');
  for(const [sx,sy,col] of [[-4,-12,'#6ec6f0'],[3,-15,'#ffd166'],[5,-11,'#9cc58a']])L(c,x+sx,y+sy,x+sx+1.6,y+sy-.8,col,1.4);
}
function cup(c,x,y,rot=0){
  c.save();c.translate(x,y);c.rotate(rot);
  L(c,2,-15,4.5,-26,'#ff7aa2',3.2);
  P(c,[[-8.5,-14],[8.5,-14],[6.8,11],[-6.8,11]],'#e9e4f2');P(c,[[-7.5,-9],[7.5,-9],[6.2,10],[-6.2,10]],'#e5bf95');
  for(const [px,py] of [[-3.6,7],[0,7.6],[3.6,7],[-1.8,4],[1.8,4]])E(c,px,py,1.7,1.7,'#4a3028');
  E(c,0,-15,9.2,3.2,'#ffffff');E(c,0,-15.4,6.4,4.6,'#ffffffcc');L(c,-5.6,-7,-4.6,7,'#ffffff88',1.4);
  c.restore();
}
function pillow(c,x,y){heart(c,x,y,1.46,'#ffffff');heart(c,x,y,1.32,'#ff7aa2');heart(c,x,y-3,.62,'#ffa6c2');E(c,x-10,y-17,3.4,2.4,'#ffffffaa');}
function drawItem(c,it,sign){
  switch(it.k){
    case'teddy':teddy(c,it.x,it.y);break;
    case'balloons':balloons(c,it.x,it.y);break;
    case'sign':signItem(c,it.x,it.y,sign);break;
    case'cone':cone(c,it.x,it.y);break;
    case'cup':cup(c,it.x,it.y,it.rot||0);break;
    case'pillow':pillow(c,it.x,it.y);break;
  }
}
// an item held by one hand goes with that hand (a booth prop may have taken it)
const itemsOf=(sp,layer)=>(sp.items||[]).filter(it=>(it.layer||'front')===layer&&(!it.side||(it.side>0?sp.arms.r:sp.arms.l)&&(it.side>0?sp.arms.r:sp.arms.l)!=='hide'));
function limb(c,pts,col,w=15){c.strokeStyle=col;c.lineWidth=w;c.lineCap='round';c.lineJoin='round';c.beginPath();pts.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y));c.stroke();}
function shoe(c,F,x,y,rot=0){const s=F.shoes;c.save();c.translate(x,y);c.rotate(rot);if(s.tall)R(c,-8.5,-11,17,15,s.c,5);R(c,-9.5,s.flat?-3:-5,19,s.flat?7:10,s.c,5,s.line||null,1.2);c.restore();}
/** Running: the right foot down, the left knee up (the foot off the ground). */
function runLegs(c,F){
  const b=F.bottom,sk=F.skin.hand,bare=b.short||b.skirt,col=bare?sk:b.c;
  limb(c,[[11.5,-16],[12.5,-8]],col);shoe(c,F,12.5,-2);
  limb(c,[[-11.5,-16],[-14,-12],[-17,-12]],col);shoe(c,F,-19,-9,-.32);
  if(b.short){limb(c,[[11.5,-17],[11.8,-13]],b.c,17);limb(c,[[-11.5,-17],[-13,-14]],b.c,17);}
  if(b.dress)paintDress(c,F);
  else if(b.skirt==='flare')P(c,[[-21,-24],[21,-24],[28,-9],[-28,-9]],b.c);
  else if(b.skirt==='long'){P(c,[[-21,-24],[21,-24],[25,-7],[-25,-7]],b.c);for(const [x,y] of [[-14,-14],[0,-10],[13,-16],[-6,-19],[8,-9]])E(c,x,y,1.8,1.8,'#fff8ee');}
  if(F.top.long)P(c,[[-17,-22],[17,-22],[13,-5],[-13,-5]],F.topC);
}
/** Squatting, drawn over the (lowered) body: the knees up and out, the feet under them. Behind: a skirt, áo dài flaps. */
function squatBack(c,F){
  const b=F.bottom;
  if(b.skirt)P(c,[[-22,-16],[22,-16],[32,-1],[-32,-1]],b.c);
  if(F.top.long)P(c,[[-17,-16],[17,-16],[14,-1],[-14,-1]],F.topC);
}
function squatLegs(c,F){
  const b=F.bottom,sk=F.skin.hand,bare=b.short||b.skirt;
  for(const s of [-1,1]){
    shoe(c,F,s*18,-3,s*.12);
    limb(c,[[s*19,-7],[s*25,-21]],bare?sk:b.c);
    limb(c,[[s*8,-9],[s*25,-21]],b.skirt?sk:b.c,16);
    if(b.short)limb(c,[[s*8,-9],[s*16,-15]],b.c,18);
    E(c,s*25.5,-22,8.4,7.6,b.skirt||b.short?sk:b.c);
  }
}
/** Twirling: the skirt (or áo dài) flares out, with a wavy hem. */
function twirl(c,F){
  const b=F.bottom,col=b.skirt?b.c:F.top.long?F.topC:null;if(!col)return;
  c.beginPath();c.moveTo(-20,-27);c.lineTo(20,-27);c.quadraticCurveTo(33,-17,42,-7);
  const xs=[42,25,8,-9,-25,-42];for(let i=0;i<5;i++)c.quadraticCurveTo((xs[i]+xs[i+1])/2,i%2?-11:-2,xs[i+1],-7);
  c.quadraticCurveTo(-33,-17,-20,-27);c.closePath();c.fillStyle=col;c.fill();
  for(const [x0,x1] of [[-8,-17],[8,17],[0,0]])L(c,x0,-24,x1,-9,shade(col,.86),1.4);
}

/* ---------------------------------------------------------------- one person */
function headT(c,sp,fn){c.save();if(sp.tilt){c.translate(0,-50);c.rotate(sp.tilt);c.translate(0,50);}fn();c.restore();}
function body(c,F,sp,prop,hold,sign){
  const sk=F.skin,K=CANVAS,sit=sp.sit||0,ink=it=>{try{drawItem(c,it,prop==='bang_chu'?sign:tr('XINH QUÁ'));}catch(e){console.warn('chụp ảnh: đồ',e);}};
  E(c,0,0,sp.lift?19:26,sp.lift?6:8,'#81644823');
  c.save();if(sp.lean)c.rotate(sp.lean);if(sp.lift)c.translate(0,-sp.lift);
  if(sp.legs==='run')runLegs(c,F);else if(sp.legs==='squat')squatBack(c,F);else paintLegs(c,F,sp.step,K);
  if(sp.twirl)twirl(c,F);
  if(sit)c.translate(0,sit);
  headT(c,sp,()=>paintHairBack(c,F,K));
  R(c,-23,-52,46,36,F.topC||F.classic,15);
  if(sp.arms.l==null)E(c,-25,-36,8,14,sk.hand);
  if(sp.arms.r==null)E(c,25,-36,8,14,sk.hand);
  paintTop(c,F,K);
  if(F.L.acc==='tui_cheo')paintAcc(c,F,K);
  if(sp.legs==='squat'){c.save();c.translate(0,-sit);squatLegs(c,F);c.restore();}
  for(const it of itemsOf(sp,'mid'))ink(it);
  for(const [s,a] of armsOf(sp,'mid'))drawArm(c,F,s,a);
  effects(c,sp,'mid');
  headT(c,sp,()=>{
    E(c,0,-84,33,35,F.hair);E(c,-29,-71,5,8,sk.ear);E(c,29,-71,5,8,sk.ear);E(c,0,-77,29,28,sk.face);
    K.path(c,F.short?FRONT.short:FRONT.soft,F.hair);
    const male=F.g==='male',b=sp.blush,bc=sp.blushC||(b?'#f29a9a':male?'#efb3a466':'#efa7a0');
    if(sp.puff){for(const s of [-1,1]){E(c,s*23.5,-64,11.4,10.6,sk.neck);E(c,s*23.2,-64,10.4,9.6,sk.face);}E(c,0,-64,20,15.5,sk.face);}
    E(c,-20,-67,7+b*2.4,4+b*1.2,bc);E(c,20,-67,7+b*2.4,4+b*1.2,bc);
    eyes(c,sp.eyes,F);brows(c,sp.brows,F);mouth(c,sp.mouth);
    effects(c,sp,'head');
    paintHairFront(c,F,K);if(F.L.acc!=='tui_cheo')paintAcc(c,F,K);
    if(sp.shades&&F.L.acc!=='kinh_ram'&&!EYES[prop])shades(c);
    if(HAT[prop]||EYES[prop])headProp(c,prop);
    effects(c,sp,'top');
  });
  for(const it of itemsOf(sp,'front'))ink(it);
  for(const [s,a] of armsOf(sp,'front'))drawArm(c,F,s,a);
  if(hold)handProp(c,prop,hold.at,hold.side,sk.hand,sign);
  effects(c,sp,'front');
  c.restore();
}
function over(c,F,sp){
  c.save();if(sp.lean)c.rotate(sp.lean);if(sp.lift)c.translate(0,-sp.lift);if(sp.sit)c.translate(0,sp.sit);
  for(const [s,a] of armsOf(sp,'over'))drawArm(c,F,s,a);
  effects(c,sp,'over');
  c.restore();
}

/* ---------------------------------------------------------------- how much room a person takes */
const FX_EXT={sparkle:[-50,50,-134],hearts:[-40,44,-136],kiss:[-34,60,-104],think:[-34,62,-138],wave:[-34,66,-116],shock:[-32,32,-142],ha:[-50,50,-124],twinkle:[-34,38,-104],
  fsparkle:[-46,48,-130],fhearts:[-42,44,-132],zzz:[-34,60,-139],qmark:[-34,48,-128],anger:[-34,36,-115],sweat:[-42,36,-106],fheart1:[-34,38,-80],
  swirl:[-48,48,-40],speed:[-36,66,-40],speedL:[-53,36,-30],claps:[-36,36,-72]};
const FX_POS={miniheart:9,puff:20,clink:16};   // the new effects at a point: how far around it they reach
function extent(sp,prop,hold){
  let l=-36,r=36,top=124;
  for(const [,a] of [[0,sp.arms.l],[0,sp.arms.r]]){
    if(!a||a==='hide'||a.layer==='over')continue;
    for(const [x,y] of [a.e,a.h]){l=Math.min(l,x-9);r=Math.max(r,x+9);top=Math.max(top,-y+12);}
    if(a.hand==='v'||a.hand==='point'||a.hand==='open'||a.hand==='phone'||a.hand==='fheart'){const d=a.dir??-Math.PI/2;top=Math.max(top,-a.h[1]-Math.sin(d)*18+4);l=Math.min(l,a.h[0]+Math.cos(d)*20-4);r=Math.max(r,a.h[0]+Math.cos(d)*20+4);}
  }
  for(const f of sp.fx){const k=Array.isArray(f)?f[0]:f,x=FX_EXT[k];if(x){l=Math.min(l,x[0]);r=Math.max(r,x[1]);top=Math.max(top,-x[2]);}
    const pr=FX_POS[k];if(pr&&Array.isArray(f)){l=Math.min(l,f[1]-pr);r=Math.max(r,f[1]+pr);top=Math.max(top,-f[2]+pr);}}
  for(const it of itemsOf(sp,'mid').concat(itemsOf(sp,'front'))){const b=ITEM_BOX[it.k];if(b){l=Math.min(l,it.x+b[0]-2);r=Math.max(r,it.x+b[1]+2);top=Math.max(top,-it.y+b[2]+2);}}
  if(sp.legs==='run')l=Math.min(l,-38);
  if(PROP_TOP[prop]){top=Math.max(top,PROP_TOP[prop]);if(prop==='non_la'){l=Math.min(l,-48);r=Math.max(r,48);}}
  if(hold){const [hx]=hold.at;if(prop==='bong_bay'){top=Math.max(top,118);r=Math.max(r,hx+30);l=Math.min(l,hx-30);}else if(prop==='long_den'){r=Math.max(r,hx+32);l=Math.min(l,hx-32);}else{l=Math.min(l,-36);r=Math.max(r,36);}}
  const tilt=Math.abs(sp.tilt)*50+Math.abs(sp.lean)*top*.8;
  return {l:l-tilt,r:r+tilt,top:top+sp.lift-(sp.sit||0)};
}

/* ---------------------------------------------------------------- the people of one photo */
const UNIT_H=150;   // the height the scale is made for (a character is ~124 units, with a hat ~150)
/** People side by side in a w × h photo. Returns [{x, s}] (centre x of each, the scale). */
export function paintPeople(c,people,w,h,{sign='VUI QUÁ!',scale=0,measure=false}={}){
  const ppl=(Array.isArray(people)?people:[]).slice(0,6).map(p=>p&&typeof p==='object'?p:{});
  if(!ppl.length)return measure?Infinity:[];
  const rs=roles(ppl.map(p=>known(p.pose)?p.pose:DEFAULT));
  const items=ppl.map((p,i)=>{
    const F=figureOf(p.lk&&typeof p.lk==='object'?p.lk:defaultLook(p.g),p.g);
    const prop=typeof p.prop==='string'?p.prop:'none';
    const held=withProp(specOf(rs[i]),prop),hold=held.hold,sp=withFace(held.sp,knownFace(p.face)?p.face:'auto');
    return {F,sp,prop,hold,ext:extent(sp,prop,hold),role:rs[i]};
  });
  // the distance from each one to the next: a group pose's own (so hands meet), else side by side with a little room
  const PAD=4,links=[],head=it=>it.prop==='non_la'?47:it.prop==='mu_tn'?39:34;
  for(let i=0;i<items.length-1;i++){
    const a=rs[i],b=rs[i+1],g=GROUP[a.id];
    const linked=g&&a.id===b.id&&g.gap&&(g.type==='pair'?a.pair==='a'&&b.pair==='b':a.R&&b.L);
    links.push(linked?{d:Math.max(g.gap,head(items[i])+head(items[i+1])+(g.gap>=90?0:6)),fixed:true}:{d:items[i].ext.r-items[i+1].ext.l+PAD,fixed:false});
  }
  const span=-items[0].ext.l+links.reduce((t,k)=>t+k.d,0)+items[items.length-1].ext.r;
  const top=Math.max(...items.map(it=>it.ext.top));
  const foot=h*.955;
  let s=Math.min(h*.82/UNIT_H,(foot-h*.02)/top,w*.97/span);
  if(measure)return s;
  if(scale>0)s=Math.min(s,scale);   // the same size in every photo of a strip
  // room to spare: spread the ones who are not holding each other, a little
  const free=w/s-span,loose=links.filter(k=>!k.fixed).length;
  if(free>0&&loose){const add=Math.min(free/(loose+2),46);for(const k of links)if(!k.fixed)k.d+=add;}
  const total=-items[0].ext.l+links.reduce((t,k)=>t+k.d,0)+items[items.length-1].ext.r;
  let x=(w/s-total)/2-items[0].ext.l;
  const xs=[x];for(const k of links){x+=k.d;xs.push(x);}
  const at=(i,fn)=>{c.save();c.translate(xs[i]*s,foot);c.scale(s,s);try{fn();}catch(e){console.warn('chụp ảnh: dáng',e);}c.restore();};
  items.forEach((it,i)=>at(i,()=>body(c,it.F,it.sp,it.prop,it.hold,sign)));
  items.forEach((it,i)=>at(i,()=>over(c,it.F,it.sp)));
  return xs.map(v=>({x:v*s,s}));
}

/* ---------------------------------------------------------------- the picker's tiles */
const FRIEND={female:{hair:'toc_ngan',shade:'mau_den',skin:'da_trung',top:'ao_thun_xanh',bottom:'quan_jean',shoes:'giay_trang',acc:'pk_khong'},
  male:{hair:'toc_duoi_ngua',shade:'mau_mat_ong',skin:'da_sang',top:'ao_chi_may',bottom:'vay_xoe',shoes:'giay_do',acc:'pk_khong'}};
const tiles=new Map();
/** A square tile (size px, already ×2 for sharp screens) of this look in pose id; a group pose shows a friend too. */
export function poseThumb(lk,g,id,size=128,face='auto'){
  const key=JSON.stringify([lk,g,id,size,face]);
  if(tiles.has(key))return tiles.get(key);
  let url='';
  try{
    const cv=document.createElement('canvas');cv.width=cv.height=size;
    const c=cv.getContext('2d'),me={lk,g,pose:id,prop:'none',face};
    const ppl=POSE[id]?.group?[me,{lk:{...defaultLook(g==='male'?'female':'male'),...FRIEND[g==='male'?'male':'female'],uniform:true},g:g==='male'?'female':'male',pose:id,prop:'none'}]:[me];
    c.translate(0,size*.03);paintPeople(c,ppl,size,size);
    url=cv.toDataURL('image/png');
  }catch{url='';}
  if(tiles.size>200)tiles.clear();
  tiles.set(key,url);
  return url;
}
/** A square tile (size px) of the face picker: this look's head and shoulders with face id (standing, the pose's arms
 * left out). '' when it cannot be drawn. */
export function faceThumb(lk,g,face,size=128){
  const key=JSON.stringify(['face',lk,g,face,size]);
  if(tiles.has(key))return tiles.get(key);
  let url='';
  try{
    const cv=document.createElement('canvas');cv.width=cv.height=size;
    const c=cv.getContext('2d'),s=size/114;
    const F=figureOf(lk&&typeof lk==='object'?lk:defaultLook(g),g);
    c.translate(size/2,144*s);c.scale(s,s);
    body(c,F,withFace(solo(DEFAULT),knownFace(face)?face:'auto'),'none',null,'');
    url=cv.toDataURL('image/png');
  }catch{url='';}
  if(tiles.size>200)tiles.clear();
  tiles.set(key,url);
  return url;
}
