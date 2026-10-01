/** Salon bowl maths: a line-for-line port of game/careers/salon.py (_band, _blend, _mix, _level_ok, _level_text,
 * _dev_note, bowl_check). Pure, no DOM: the content tables come in as `cc` (the career content, x.cc).
 * tests/test_salon_mix_parity.py runs every combination through both, so the preview never disagrees with the bowl. */
const BANDS=['ash','cool','natural','warm','deep'];
const LIFT_DEFAULT={10:0,20:2,30:3,40:4};

export function band(tn,den){
  if(tn<=-12*den)return 'ash';
  if(tn<=-3*den)return 'cool';
  if(tn<3*den)return 'natural';
  if(tn<18*den)return 'warm';
  return 'deep';
}
export function blend(rows){
  const tot=rows.reduce((a,r)=>a+r[1],0);let out='#';
  for(let i=0;i<3;i++){const v=rows.reduce((a,[c,p])=>a+parseInt(c.slice(1+2*i,3+2*i),16)*p,0)/tot;out+=Math.floor(v+0.5).toString(16).padStart(2,'0');}
  return out;
}
const dye=(cc,id)=>(cc.dyes||[]).find(d=>d.id===id)||null;
/** Tube A (pa parts) and tube B (pb parts) on hair whose base warms the mix by `warm` bands; null if a tube is unknown. */
export function mix(cc,a,b,pa,pb,warm=0){
  const rows=[[dye(cc,a),pa]];if(b&&pb)rows.push([dye(cc,b),pb]);
  if(rows.some(r=>!r[0]))return null;
  const tone=cc.tone||{N:0,A:-1,G:1,R:2};
  const den=rows.reduce((s,r)=>s+r[1],0),lv=rows.reduce((s,[d,p])=>s+d.level*p,0);
  const tn=rows.reduce((s,[d,p])=>s+tone[d.fam]*20*p,0)+warm*20*den;
  const nat=rows.reduce((s,[d,p])=>s+(d.fam==='N'?p:0),0);
  return {den,lv,tn,nat,band:band(tn,den),color:blend(rows.map(([d,p])=>[d.color,p]))};
}
export const levelOk=(m,l)=>Math.abs(m.lv-l*m.den)*4<=m.den;
export const levelText=m=>(m.lv/m.den).toFixed(2).replace(/0+$/,'').replace(/\.$/,'').replace('.',',');

function devNote(lift,dev,need,tones){
  if(need==null||dev==null)return null;
  if(dev===need)return 'ok';
  if(dev===40)return 'dev40';
  if(dev<need){
    if(tones==null)return 'low';
    return tones>lift[dev]?'weak':'cover';
  }
  return 'strong';
}

/** Same arguments and result as salon.py bowl_check (mixSpec = {b,pa,pb} or null). */
export function bowlCheck(cc,kind,shade,mixSpec,dev,ratio,want,warm=0,photoBlind=false,lift=null){
  const L=cc.lift?Object.fromEntries(Object.entries(cc.lift).map(([k,v])=>[Number(k),v])):LIFT_DEFAULT;
  const out={issue:null,hit:null,mix:null,text:null,level_ok:null,band_ok:null,nat_ok:null,dlv:null,dband:null,
    dev_note:null,need:null,cap:L[dev]??null,tones:null,block:false};
  if(mixSpec!=null){
    const m=mix(cc,shade,mixSpec.b,mixSpec.pa,mixSpec.pb,warm);
    if(!m)return out;
    out.mix=m;out.text=levelText(m);
    if(lift&&lift.dyed!=null)out.block=(m.lv-lift.dyed*m.den)*4>m.den;
    if(!want){out.issue='nowant';out.hit=false;return out;}
    const lvOk=levelOk(m,want.level),bdOk=m.band===want.tone;
    const natOk=!want.grey||2*m.nat>=m.den;
    const hit=lvOk&&bdOk;
    const need=want.dev??null;
    const tones=lift&&lift.base!=null?want.level-lift.base:null;
    Object.assign(out,{hit,level_ok:lvOk,band_ok:bdOk,nat_ok:natOk,dlv:m.lv-want.level*m.den,
      dband:BANDS.indexOf(m.band)-BANDS.indexOf(want.tone),need,tones,dev_note:photoBlind?null:devNote(L,dev,need,tones)});
    if(dev===40)out.issue='dev40';
    else if(!hit)out.issue=photoBlind?'photo':!lvOk?'level':'tone';
    else if(!natOk)out.issue='grey';
    else if(need!=null&&dev!==need)out.issue='dev';
    else if(ratio!==want.ratio)out.issue='ratio';
    return out;
  }
  if(!want){out.issue='nowant';return out;}
  const need=want.dev??null;
  out.need=need;out.dev_note=devNote(L,dev,need,null);
  if(dev===40)out.issue='dev40';
  else if(kind!=='bleach'&&want.shade!=null&&shade!==want.shade)out.issue='shade';
  else if(need!=null&&dev!==need)out.issue='dev';
  else if(ratio!==want.ratio)out.issue='ratio';
  return out;
}

/** The client's colour target as the stylist knows it: the real photo once checked, else the reference photo. */
export function target(t){
  if(t.real)return {level:t.real.level,band:t.real.tone};
  const ph=t.needs?.photo;return ph?.level&&ph.band?{level:ph.level,band:ph.band}:null;
}
/** bowlCheck's inputs for a two-tube colour bowl from a task's public view: only what has been found out
 * (the developer once the roots are seen, grey from the roots, the brassy base from the lengths). */
export function previewInputs(t){
  const tg=target(t),rc=t.recipe?.color||null;
  const want=tg&&rc?{level:tg.level,tone:tg.band,dev:rc.dev??null,ratio:rc.ratio,grey:(t.grey||0)>=50}:null;
  return {want,warm:t.base_warm||0,photoBlind:t.needs?.case==='photo'&&!t.photo_seen,
    lift:rc&&rc.base!=null?{base:rc.base,dyed:rc.dyed??null}:null};
}
/** A single-tube bowl's want (bleach, toner) from the public view; null when the client needs no such bowl. */
export function recipeWant(t,kind){const r=t.recipe?.[kind];return r?{shade:r.shade??null,dev:r.dev,ratio:r.ratio}:null;}
