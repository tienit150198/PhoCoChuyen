/* 🧧 A red envelope's request id, and what a send that failed means (public/js/v4/walk.js sendEnvelope).
 *
 * game/wedding_live.py envelope pays once per request id (rid): the same rid again answers "already sent". So:
 * - a send the server answered (done, or refused: nothing moved) ends its rid; the next tap is a new envelope;
 * - a send with no answer (a timeout, the network, the proxy's 502/503/504) may still have gone through: its rid
 *   is kept for the same amount and wish, so tapping "Gửi" again is that same envelope, never a second debit.
 *   Another amount or wish is another envelope (a new rid).
 * Pure: tests/envelope_send.mjs. */
import {transient} from '../api.js';

export const UNKNOWN_TEXT='Mạng chập chờn, chưa chắc phong bì đã tới. Bấm gửi lại: nếu đã tới rồi sẽ không bị trừ thêm tiền.';

export const newRid=()=>`e${Date.now().toString(36)}${Math.random().toString(36).slice(2,10)}`;

/** The rid for sending this envelope now (`key`: the wedding, the amount and the wish): the one kept in `k` from an
 * unanswered send of the same envelope, or a new one. `k` outlives the panel (closed and opened again in between). */
export const envKey=(wid,n,wish)=>`${wid}|${n}|${wish}`;
export function envRid(k,key,mint=newRid){
  if(!k.rid||k.ridKey!==key){k.rid=mint();k.ridKey=key;}
  return k.rid;
}

/** After a send: 'sent' (no error), 'refused' (the server said no: nothing moved) or 'unknown' (no answer: kept). */
export function envSettle(k,error){
  if(error&&transient(error))return 'unknown';
  k.rid=null;k.ridKey='';
  return error?'refused':'sent';
}
