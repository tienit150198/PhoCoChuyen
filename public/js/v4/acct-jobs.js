/** 💼 Việc làm kế toán on the journey's workplace cards (game/accounting_jobs.py; the school, its job referral and
 * the entry check: v4/accounting-school.js). state.accounting_school.jobs = {places: {career: [ok, multiplier,
 * check]}, holiday?} lists only the places with a rule today. A server without it (older build): nothing changes. */
const COURSE={corp_accounting:'Kế toán cơ bản',group_accounting:'Kế toán doanh nghiệp Việt Nam – TT99'};

/** null, or {ok, x, holiday, why}: ok false = the place still needs its exam (why: the one line to show). */
export function acctPlace(api,cid){
  const J=api.state?.accounting_school?.jobs,row=J?.places?.[cid];
  if(!Array.isArray(row))return null;
  const ok=!!row[0],x=Number(row[1])||1;
  return {ok,x,holiday:J.holiday||null,why:ok?'':`Thi đạt chứng nhận “${COURSE[cid]||'kế toán'}” ở Học kế toán rồi mới nhận việc ở đây.`};
}

/** The tag of a certified place: its rate today. */
export const acctTag=a=>a?.x>1?(a.holiday?`🎉 Lễ: lương kế toán x${a.x}`:`💼 Lương kế toán x${a.x}`):'';
