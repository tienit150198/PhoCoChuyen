// F#282/#283: one unkind move used to leave a tantrum or a scrape short of 100% with every caring move used and
// nothing left to press; every caring move tried now settles the child and "BÉ ỔN RỒI" opens.
import assert from 'node:assert/strict';
import babysitter from '../public/js/careers/babysitter.js';
import {escapeHTML as esc} from '../public/js/icons.js';
const moves={tantrum:{breath:['😮‍💨','Hít một hơi',true],sit:['🧎','Ngồi xuống',true],name:['💬','Gọi tên cảm xúc',true],choice:['🎨','Cho bé chọn',true],
  shout:['📢','Quát to',false],give:['🍬','Đưa kẹo',false],threat:['👻','Dọa',false]}};
const x={esc,ui:{},room:{day:4,metrics:{served:1},data:{intro:true,fam:{kid:'Bông',temper:'stubborn'},today:{},plan:[]}},
 cc:{moves,moment_title:{tantrum:'ăn vạ đòi kẹo'}},npc:()=>({display_name:'Bố'}),portrait:()=>'',
 cmd:(label,cmd,payload,cls='',disabled=false)=>`<button data-command="${cmd}"${disabled?' disabled':''}>${label}</button>`};
const order=['breath','give','sit','name','choice','shout','threat'];
const task=(used,calm)=>({id:'babysitter-4-5',kind:'moment',npc:'dad',needs:{mk:'tantrum',moves:order},st:{calm,used,bad:[],order_err:0}});
let html=babysitter.job(task(['breath','give','sit'],40),x);
assert.ok([...html.matchAll(/<button[^>]+data-command="bm_care"[^>]*>/g)].some(b=>!b[0].includes('disabled')),'caring moves left to press');
html=babysitter.job(task(['breath','give','sit','name','choice'],95),x);
const care=[...html.matchAll(/<button[^>]+data-command="bm_care"[^>]*>/g)].map(b=>b[0]);
assert.ok(care.length&&care.every(b=>b.includes('disabled')),'every caring move tried: the child is settled, nothing more to press');
assert.match(html,/class="ok"><span>✓<\/span>Dỗ bé tới khi bé ổn/,'the checklist row is ticked at 95% once every caring move is used');
console.log('Babysitter moment: a settled child can always be handed on passed.');
