/** 🙂 Ảnh đại diện, the code: the small public string a player's chat face travels as (live/faces.py checks it, the
 * part ids are game/avatar.py's; tests/test_avatar.py compares the three lists). Small and always loaded with the live
 * socket (./live.js sends it); the art is ./face.js, the builder ./avatar.js.
 *   faceCode(state)  the code of this save: s.avatar (kind face / emoji) or, never built, the face that follows the
 *                    character (hair, colour and skin of the wardrobe look); with "Mặc đồ trong tủ" (shirt 'tu') the
 *                    wardrobe's top and accessory in their colours (look.tint) go in too
 *   parseFace(code)  {kind:'emoji', emoji} | {kind:'face', auto, f:{part: id}, g, top, topTint, acc, accTint} | null
 *                    (an id this build does not know takes the default, as on the server) */
import {lookOf} from './look.js';

export const PARTS={
  skin:['s1','s2','s3','s4','s5','s6','s7','s8'],
  shape:['tron','oval','vuong','tim'],
  age:['be','teen','lon','gia'],
  hair:['ngan','dinh','hoi','lech','dung','xoan','afro','bob','dai','bui','duoi','bim','mai','song','tet','chom','bui_doi','bui_thap'],
  hc:['den','nau','mat_ong','vang','do','hong','xanh','tim','bach_kim','xam','trang'],
  expr:['cuoi','toe','nhay','diu','ngac','then','ngau'],
  glasses:['0','tron','vuong','ram','meo'],
  head:['0','hijab','khan','luoi_trai','len','non_la','tai_beo','bang_do','hoa','khan_dong'],
  hwc:['den','nau','vang','bac','hong','do','dao','mint','navy','lavender','trang'],
  beard:['0','lun','ria','de','quai'],
  extra:['0','bong_tai','not_ruoi','bang_ca','tai_nghe'],
  bg:['kem','hong','dao','vang','mint','xanh','lavender','xam','navy','la'],
  shirt:['tu','den','nau','vang','bac','hong','do','dao','mint','navy','lavender','trang'],
};
export const EMOJIS=['🌸','☕','🍜','🎉','💪','🌈','🍀','⭐','🧁','🎁','🧑‍🍳','👩‍🏫','🧑‍💼','🧑‍🌾','🐱','🐶',
  '🐰','🦊','🐼','🐸','🐧','🐯','🐨','🦁','🌻','🌙','🍉','🍓','🧋','🎨','🎸','⚽','📚','🌊','🍵','🎮'];
// Same as game/avatar.py DEFAULT_FACE (tests/test_avatar.py compares them).
export const DEFAULT_FACE={"skin":"s2","shape":"tron","age":"lon","hair":"ngan","hc":"nau","expr":"cuoi","glasses":"0","head":"0","hwc":"do","beard":"0","freckles":false,"extra":"0","bg":"kem","shirt":"tu"};
/** The order of the parts in the code (after the tag), then g, top, top colour, acc, acc colour. */
export const ORDER=['skin','shape','age','hair','hc','expr','glasses','head','hwc','beard','freckles','extra','bg','shirt'];

// The face that follows the character: wardrobe ids → face parts (game/wardrobe.py ITEMS).
const FROM_SKIN={da_sang:'s2',da_hong:'s1',da_trung:'s4',da_ngam:'s6'};
const FROM_HAIR={toc_ngan:'ngan',toc_bui:'bui',toc_dai:'dai',toc_bob:'bob',toc_duoi_ngua:'duoi',toc_xoan:'xoan',toc_bui_cao:'chom',toc_bui_doi:'bui_doi',toc_bui_thap:'bui_thap',
  toc_song_dai:'song',toc_bob_mai:'mai',toc_duoi_cao:'duoi',toc_bui_tron:'bui_doi',toc_wolf:'dung',toc_undercut:'lech',toc_mai_bay:'bob',toc_tet:'tet'};
const FROM_SHADE={mau_nau:'nau',mau_den:'den',mau_mat_ong:'mat_ong',mau_hong:'hong',mau_xanh_khoi:'xanh',mau_bach_kim:'bach_kim'};
const G={male:'m',female:'f'};

/** The face drawn for a save that never opened the builder: the character's hair, hair colour and skin. */
export function autoFace(state){
  const L=lookOf(state);
  return {...DEFAULT_FACE,skin:FROM_SKIN[L.skin]||'s2',hair:FROM_HAIR[L.hair]||'ngan',hc:FROM_SHADE[L.shade]||'nau',
    shape:state?.journey?.gender==='female'?'oval':'tron'};
}
/** The face of the save (s.avatar), else autoFace; `own` true when the player built it. */
export function faceOf(state){
  const a=state?.avatar;
  if(a&&a.face&&typeof a.face==='object')return {own:true,f:clean({...DEFAULT_FACE,...a.face})};
  return {own:false,f:autoFace(state)};
}
const clean=f=>{const o={...DEFAULT_FACE};for(const k of ORDER){if(k==='freckles')o.freckles=f.freckles===true;else if(PARTS[k].includes(f[k]))o[k]=f[k];}return o;};

/** The code of face `f` worn by the character of `state` (its gender and, with shirt 'tu', its wardrobe clothes). */
export function encode(tag,f,state){
  const L=lookOf(state),tu=f.shirt==='tu',top=tu?L.top:'ao_quen',acc=tu?L.acc:'pk_khong';
  const tt=tu&&L.tint?.[top]||'0',at=tu&&L.tint?.[acc]||'0';
  return [tag,...ORDER.map(k=>k==='freckles'?(f.freckles?'1':'0'):f[k]),G[state?.journey?.gender]||'n',top,tt,acc,at].join('.');
}
export function faceCode(state){
  const a=state?.avatar;
  if(a?.kind==='emoji'&&EMOJIS.includes(a.emoji))return 'e1.'+a.emoji;
  const {own,f}=faceOf(state);
  return encode(own?'f1':'a1',f,state);
}

export function parseFace(code){
  if(typeof code!=='string'||!code||code.length>240)return null;
  const p=code.split('.');
  if(p[0]==='e1')return p.length===2&&EMOJIS.includes(p[1])?{kind:'emoji',emoji:p[1]}:null;
  if(p[0]!=='f1'&&p[0]!=='a1')return null;
  const f={...DEFAULT_FACE};
  ORDER.forEach((k,i)=>{const v=p[i+1];if(k==='freckles')f.freckles=v==='1';else if(PARTS[k].includes(v))f[k]=v;});
  const n=ORDER.length,id=v=>/^[a-z_0-9]{1,24}$/.test(v||'')?v:null;   // the art falls back for an id it does not draw
  return {kind:'face',auto:p[0]==='a1',f,g:{m:'male',f:'female'}[p[n+1]]||null,top:id(p[n+2])||'ao_quen',topTint:id(p[n+3])||'0',
    acc:id(p[n+4])||'pk_khong',accTint:id(p[n+5])||'0'};
}
