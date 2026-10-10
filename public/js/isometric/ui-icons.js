import {illustratedIcon} from '../illustrated-icons.js';

/** The HUD shares the same material colors and silhouettes as every game sheet. */
export function uiIcon(name,size=20){
  const dimension=Math.max(12,Math.min(64,Number(size)||20));
  return illustratedIcon(name,dimension);
}
