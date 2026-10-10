export const DISTRICTS={rent:{name:'Xóm trọ',wall:'#efd4a1',roof:'#aa644c',floors:1},apartment:{name:'Khu căn hộ',wall:'#e1e7d7',roof:'#5c8792',floors:3},townhouse:{name:'Phố nhà liền kề',wall:'#eeddb8',roof:'#bf7255',floors:2},villa:{name:'Vườn biệt thự',wall:'#fff0d5',roof:'#b45f46',floors:2}};
/** Public district coordinates are separate from the island's authoritative entrance. */
export function districtStep(at,input,dt){
  const n=Math.hypot(input.x,input.y),s=Math.max(0,Math.min(.05,Number(dt)||0))*3.2/Math.max(1,n);
  return {x:Math.max(-2.8,Math.min(2.8,at.x+input.x*s)),y:Math.max(-14,Math.min(14,at.y+input.y*s))};
}
export function districtHomes(group,content,state,rentals){
  const cat=(content?.journey?.homes?.homes||[]).filter(h=>h.group===group);
  const home=state?.journey?.home||{},own=home.own,rent=home.rent,shared=home.shared;
  const props=[...(own?[own]:[]),...(home.props||[])],lease=home.tenancy||rentals?.tenancy;
  // housing.public.place resolves lease/estate precedence. Older public states may
  // omit it; use the same own > shared > NPC rent order as housing.where then.
  const fallback=lease?['lease',lease]:own?['own',own]:shared?['shared',shared]:rent?['rent',rent]:['attic',null];
  const place=home.place?.where_id?home.place:{where_id:fallback[0],kind:fallback[1]?.kind};
  const current=(where,kind)=>place.where_id===where&&place.kind===kind;
  const homes=[],byKind=new Map(cat.map(h=>[h.id,{...h,kindId:h.id}]));
  if(rent){const h=byKind.get(rent.kind);if(h)homes.push({...h,id:'rent:'+h.id,status:current('rent',h.id)?'current':'rented',label:current('rent',h.id)?'Phòng bạn đang ở':'Phòng bạn thuê'});}
  for(const p of props){
    const h=byKind.get(p.kind);if(!h)continue;
    const live=p===own&&current('own',p.kind),ad=(rentals?.mine||[]).find(r=>r.property===p.id&&['listing','leased'].includes(r.status));
    const label=live?'Nhà bạn đang ở':p.let||ad?.status==='leased'?'Nhà của bạn · đang cho thuê':ad?.status==='listing'||p.rental_ad?.active?'Nhà của bạn · đang đăng cho thuê':'Nhà của bạn';
    homes.push({...h,id:'own:'+p.id,property:p.id,status:live?'current':'owned',label});
  }
  if(shared){const h=byKind.get(shared.kind);if(h)homes.push({...h,id:'shared:'+(shared.id||h.id),status:current('shared',h.id)?'current':'shared',label:'Nhà ở cùng'+(shared.name?' · '+shared.name:'')});}
  if(lease){const h=byKind.get(lease.kind);if(h)homes.push({...h,id:'lease:'+lease.id,status:current('lease',h.id)?'current':'leased',label:current('lease',h.id)?'Nhà thuê bạn đang ở':'Nhà bạn thuê'});}
  // Luxury estates have their own catalogue, but this authorized public place is
  // enough to show the real current residence without inventing a housing kind.
  if(place.where_id==='estate'&&place.group===group&&place.kind&&place.name)homes.push({...place,id:'estate:'+place.kind,status:'current',label:'Dinh thự bạn đang ở'});
  for(const p of (rentals?.market||[]).slice(0,100)){const h=byKind.get(p.kind);if(h&&p.status==='listing')homes.push({...h,id:'listing:'+p.id,status:'listing',label:`${p.owner_name} · cho thuê`,rent:p.rent});}
  for(const h of cat)homes.push({...h,kindId:h.id,id:'model:'+h.id,status:'model',label:'Nhà mẫu · xem thông tin'});
  // Only the scene limits itself to eight buildings. The UI keeps the full
  // bounded server page plus owned/current homes and the group's catalogue.
  return homes.sort((a,b)=>Number(b.status==='current')-Number(a.status==='current'));
}
export function customerPoint(slot,t){
  const phase=(t*.065+slot/6)%1,y=-13+phase*26;
  return {x:(slot%2?1:-1)*(1.5+Math.sin(phase*Math.PI*2)*.35),y};
}
