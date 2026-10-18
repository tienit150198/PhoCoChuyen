/** 📺 The button of a rewarded-ad place, drawn from state.ads alone (game/ads.py public(): null while ads are off),
 * for views that render at once. A tap goes to app.js "bonusVideo", which loads v4/bonus-video.js and runs the ad with
 * data-place / data-what / data-career. File name: no "ad" word (blockers hide such files, tests/test_asset_names.py). */
import {escapeHTML as esc} from '../icons.js';

export function tvButton(state,place,label,{what='',career='',cls='primary small'}={}){
  const a=state?.ads;if(!a||!(a.left>0))return '';
  const more=(what?` data-what="${esc(what)}"`:'')+(career?` data-career="${esc(career)}"`:'');
  return `<button type="button" class="btn ${cls} bv-btn" data-action="bonusVideo" data-place="${esc(place)}"${more}>📺 ${label} <small>· còn ${a.left}/${a.max}</small></button>`;
}
