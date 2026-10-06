/** Release 1.8.0 keeps the Phaser 2.5D client in the repo but does not wire it into the game (docs/PHASER_25D.md).
 * Import this module FIRST in a 2.5D test that needs that wiring (the app.js hooks, game/content.py `playable`,
 * the v4/look.js portrait markers, icons.js's illustrated icons, the isometric delivery view): while the client is
 * not wired, the test prints why it is skipped and exits 0. Once app.js imports the Phaser world again, it runs. */
import {readFileSync} from 'node:fs';
import {basename} from 'node:path';

export const wired=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8').includes('./isometric/phaser-world.js');
if(!wired){
  console.log(`${basename(process.argv[1]||'2.5D test')}: skipped: the Phaser 2.5D client is not wired into public/js/app.js in 1.8.0 (see docs/PHASER_25D.md)`);
  process.exit(0);
}
