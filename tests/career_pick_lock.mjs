// 🔒 test_career_locks.py ClientAgrees: the picker's chapter line (v4/career-pick.js chapterLock) for {J, n: {cid: chapter}}
// on stdin, as JSON {cid: {k, t, how}}: the server's game/career_locks.py says the same words.
import {readFileSync} from 'node:fs';
globalThis.document={head:{append(){}},createElement:()=>({getContext:()=>null,dataset:{}}),getElementById:()=>null,querySelector:()=>null,addEventListener:()=>{}};
globalThis.addEventListener=()=>{};
const {chapterLock}=await import('../public/js/v4/career-pick.js');
const {J,n}=JSON.parse(readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(Object.fromEntries(Object.entries(n).map(([cid,ch])=>[cid,chapterLock(J,ch,cid)]))));
