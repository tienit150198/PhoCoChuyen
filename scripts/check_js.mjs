// Syntax-check every browser module (node --check), no dependencies.
import {readdirSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {execFileSync} from 'node:child_process';
const files=[];
// _v contains immutable server-generated copies, not additional browser source.
const walk=dir=>{for(const name of readdirSync(dir)){const p=join(dir,name);if(statSync(p).isDirectory()){if(name!=='_v')walk(p);}else if(p.endsWith('.js')||p.endsWith('.mjs'))files.push(p);}};
walk('public');
let failed=0;
for(const f of files){try{execFileSync(process.execPath,['--check',f],{stdio:'pipe'});}catch(e){failed++;console.error(`✗ ${f}\n${e.stderr}`);}}
console.log(`${files.length-failed}/${files.length} JS files OK`);
// …and each one must also parse and run on old iPhones (Safari 15.0 / iOS 15, 16.0–16.3): scripts/check_old_safari.mjs.
try{execFileSync(process.execPath,[fileURLToPath(new URL('./check_old_safari.mjs',import.meta.url))],{stdio:'inherit'});}catch{failed++;}
process.exit(failed?1:0);
