/** ☑️ Không hỏi lại (owner 23/10 "bấm là cường hóa luôn, đỡ phải bấm 2 lần"): this device's choice to act at once,
 * with no confirm dialog, in ⚒️ Cường hóa (and 🛍️ Cửa hàng's buy buttons, which read the same key). localStorage
 * 'mnl.noAsk' = '1' skips; anything else (or no storage: a private window, blocked site data) asks, the default.
 * The server is unchanged: the client sends confirm: true as it does after the dialog. */
export const NO_ASK_KEY='mnl.noAsk';

export function noAsk(){
  try{return globalThis.localStorage?.getItem(NO_ASK_KEY)==='1';}catch{return false;}
}

export function setNoAsk(on){
  try{if(on)globalThis.localStorage?.setItem(NO_ASK_KEY,'1');else globalThis.localStorage?.removeItem(NO_ASK_KEY);}catch{/* no storage: it keeps asking */}
}
