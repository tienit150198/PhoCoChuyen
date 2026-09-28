// Syntax-check every browser module (node --check), no dependencies.
import {readdirSync,statSync} from 'node:fs';
import {join} from 'node:path';
import {execFileSync} from 'node:child_process';
const files=[];
const walk=dir=>{for(const name of readdirSync(dir)){const p=join(dir,name);if(statSync(p).isDirectory())walk(p);else if(p.endsWith('.js')||p.endsWith('.mjs'))files.push(p);}};
walk('public');
let failed=0;
for(const f of files){try{execFileSync(process.execPath,['--check',f],{stdio:'pipe'});}catch(e){failed++;console.error(`✗ ${f}\n${e.stderr}`);}}
console.log(`${files.length-failed}/${files.length} JS files OK`);
process.exit(failed?1:0);
