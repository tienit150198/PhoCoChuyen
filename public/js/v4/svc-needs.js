/** 🧰 / 🔬 What a buyer must have before ordering a Phố dịch vụ service whose server `check` looks at the buyer's own
 * things (game/restore_service.py: an open ticket for that service, written in 🧰 Phục chế đồ; game/research_lab.py:
 * 🌟 Vườn mới for a seed batch, a food shop for a recipe, one live batch at a time, a few days between two orders).
 * Read from the buyer's own GETs and save, so the directory card, the provider page and the 🎪 fair show the reason
 * and a button before "Đặt" instead of a refusal after "Giữ xu & đặt". The server still decides at order time.
 * needsFor(api, items) → {"career.service": {why, hard, go:{action, data, label}}}; hard: Đặt stays off. */
const FOOD=['milk_tea','cafe_bakery','restaurant','pho','com','ice_cream','tra_da'];   // research_lab.FOOD
const RESTORE={action:'restoreDesk',label:'🧰 Mở Phục chế đồ'};
const GARDEN={action:'svcGarden',label:'🌱 Mở Vườn mới'};
const key=(c,s)=>`${c}.${s}`;
let cache={at:0,restore:null};

/** 🧰 the buyer's tickets (GET /api/restore/mine, kept 20 s: the directory, a card and the fair ask together). */
async function restoreMine(api){
  if(cache.restore&&Date.now()-cache.at<20000)return cache.restore;
  const v=await api.json('/api/restore/mine').catch(()=>null);
  cache={at:Date.now(),restore:v};return v;
}
/** Forget the cached tickets (a ticket was written or dropped). */
export function needsReset(){cache={at:0,restore:null};}

function restoreNeed(v,service){
  if(!v)return null;
  if(v.off)return {why:'Xưởng phục chế đang tạm nghỉ, quay lại sau nhé.',hard:true};
  if((v.tickets||[]).some(t=>t.service===service&&t.status==='open'))return null;
  const s=(v.services||[]).find(x=>x.id===service);
  const why=s&&!s.items?.length?`Bạn chưa có món nào cần “${s.name}”. Mở 🧰 Phục chế đồ để xem món nào mang tới thợ được.`
    :'Mở 🧰 Phục chế đồ, chọn món cần mang tới thợ trước đã.';
  return {why,hard:true,go:{...RESTORE,data:{service}}};
}

function researchNeed(state,service){
  const careers=state?.careers||{},lab=state?.journey?.lab||null,now=Date.now()/1000;
  if(service==='giong'){
    const farm=careers.farm;
    if(!farm?.started)return {why:'Giống cải tiến dùng cho 🌟 Vườn mới ở Trang trại. Mở Vườn mới trước đã.',hard:true,go:{...GARDEN,data:{}}};
    const plus=state?.current==='farm'?farm.data?.plus:undefined;   // only the current career's save is sent in full
    if(plus&&!plus.open)return {why:'Giống cải tiến dùng cho 🌟 Vườn mới ở Trang trại. Mở Vườn mới trước đã.',hard:true,go:{...GARDEN,data:{}}};
    if(lab?.seed&&lab.seed.left>0&&lab.seed.until>now)return {why:'Vườn mới đang dùng một lô giống của Viện. Dùng hết rồi đặt tiếp nhé.',hard:true};
    if(plus===undefined)return {why:'Giống cải tiến dùng cho 🌟 Vườn mới ở Trang trại: mở Vườn mới trước khi đặt nhé.',hard:false,go:{...GARDEN,data:{}}};
  }
  if(service==='mon'){
    if(!FOOD.some(c=>careers[c]?.started))return {why:'Công thức món dùng cho quán ăn của bạn (trà sữa, bánh, mì cay, phở, cơm, kem, trà đá). Mở quán trước đã.',hard:true};
    if(lab?.recipe&&lab.recipe.left>0&&lab.recipe.until>now)return {why:'Quán đang dùng một công thức của Viện. Dùng hết rồi đặt tiếp nhé.',hard:true};
  }
  return null;   // the days between two orders and a full gadget shelf are the server's to say (not in the public save)
}

/** The needs of the restore / research services among `items` ({career, service}); {} for every other service. */
export async function needsFor(api,items){
  const out={},list=(items||[]).filter(i=>i&&!i.mine&&(i.career==='restore'||i.career==='research'));
  if(!list.length)return out;
  const v=list.some(i=>i.career==='restore')?await restoreMine(api):null;
  for(const i of list){
    const n=i.career==='restore'?restoreNeed(v,i.service):researchNeed(api.state,i.service);
    if(n)out[key(i.career,i.service)]=n;
  }
  return out;
}
export const needKey=key;

/** The need's button: 🧰 Phục chế đồ (its own dialog), or the farm's 🌟 Trại pane (Vườn mới opens there). */
export async function goNeed(env,go){
  if(!go||!env?.act)return;
  if(go.action==='svcGarden'){
    if(env.api?.state?.current!=='farm')await env.act('choose',{career:'farm'});
    if(env.api?.state?.current!=='farm')return;   // not switched (a shift kept going): the farm stays one tap away
    await env.act('car:tab',{tab:'plus'});await env.act('job',{});
    return;
  }
  needsReset();
  await env.act(go.action,{...(go.data||{})});
}
