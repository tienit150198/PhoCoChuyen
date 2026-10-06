// Run account rendering/actions in the existing Node module harness.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {runInNewContext} from 'node:vm';
const {accountPane,accountSubmit,accountAction,accountBoot}=await import('../public/js/v4/account.js');
const {GameAPI}=await import('../public/js/api.js');
globalThis.CustomEvent??=class extends Event{constructor(type,options={}){super(type);this.detail=options.detail;}};
globalThis.localStorage={getItem:()=>null};
let opened=0,cleaned='',assigned='',posts=[];
globalThis.location={href:'https://game.example/?tiktok=success&keep=1#game',assign:url=>{assigned=url;}};
globalThis.history={replaceState:(_state,_title,url)=>{cleaned=url;}};
const env={api:{account:null,auth:{tiktok:{enabled:true,mode:'sandbox'}},accountPost:async(route,body)=>{posts.push([route,body]);return {authorization_url:'https://www.tiktok.com/v2/auth/authorize/?state=abc'};}},ui:{},openSheet:()=>{opened++;},renderSheet:()=>{},toast:()=>{}};
let html=accountPane(env);
assert.match(html,/accountRegisterForm/);assert.match(html,/v4AccountTikTok/);
assert.match(html,/đang thử nghiệm cho tài khoản được mời/);
assert.match(html,/acct-username/);assert.match(html,/minlength="8"/);
env.ui.acctMode='login';html=accountPane(env);assert.match(html,/accountLoginForm/);assert.match(html,/v4AccountTikTok/);
env.api.auth.tiktok.enabled=false;assert.doesNotMatch(accountPane(env),/v4AccountTikTok/);
env.api.auth.tiktok.enabled=true;env.api.account={username:'local',display:'Local'};
html=accountPane(env);assert.match(html,/accountPasswordForm/);assert.match(html,/data-mode="link"/);
env.api.account={username:'tt_123',display:'TikTok',tiktok_linked:true,has_password:false};
html=accountPane(env);assert.doesNotMatch(html,/accountPasswordForm/);assert.doesNotMatch(html,/data-mode="link"/);
env.api.account={username:'local',display:'Local',tiktok_linked:true,has_password:true};assert.match(accountPane(env),/accountPasswordForm/);
env.api.account=null;
assert.equal(await accountAction('v4AccountTikTok',{mode:'login'},{disabled:false},env),true);
assert.deepEqual(posts.pop(),['tiktok/start',{mode:'login'}]);assert.match(assigned,/^https:\/\/www.tiktok.com\/v2\/auth\/authorize\//);
accountBoot(env);assert.equal(opened,1);assert.equal(cleaned,'/?keep=1#game');
location.href='https://game.example/?tiktok=tiktok_denied';accountBoot(env);assert.match(env.ui.acctError,/hủy/);
location.href='https://game.example/?tiktok=untrusted<script>';env.ui.acctError='';accountBoot(env);assert.equal(env.ui.acctError,'');
// A local form still performs its validation before any API call.
posts=[];
const values={username:'x',display:'Player',password:'short',confirm:'short'};
const form={id:'accountRegisterForm',querySelector:sel=>sel.includes('type=submit')?null:{value:values[sel.match(/name="([^"]+)"/)?.[1]]||''}};
assert.equal(await accountSubmit(form,env),true);assert.equal(posts.length,0);assert.match(env.ui.acctError,/3–24/);
// Bootstrap accepts safe auth metadata independently of account info.
const api=new GameAPI();api.updates.watch=()=>{};
api.json=async url=>url.includes('bootstrap')?{csrf:'c',ai:{},state:{settings:{}},revision:0,auth:{tiktok:{enabled:true,mode:'sandbox'}},content:{careers:{}},account:null}:{};
await api.init();assert.deepEqual(api.auth,{tiktok:{enabled:true,mode:'sandbox'}});
// Execute the actual app startup with DOM/network/module boundaries stubbed. This catches a later
// startup sheet or automatic card replacing the real accountBoot result (a unit call alone cannot).
const appSource=(await readFile(new URL('../public/js/app.js',import.meta.url),'utf8')).replace(/\r\n/g,'\n');
const startupBegin=appSource.indexOf('  await api.init();'),startupEnd=appSource.lastIndexOf("}catch(error){$('#loading')");
assert.ok(startupBegin>0&&startupEnd>startupBegin,'app startup block exists');
const startup=appSource.slice(startupBegin,startupEnd).replace(/\bimport\(/g,'loadModule(');
async function startGame({marker='',current=null,open=false,summary=false,social='',newbie=false}={}){
  const sheet=Object.assign(new EventTarget(),{open:false}),ui={},calls=[],idle=[];
  const query=new URLSearchParams();if(marker)query.set('tiktok',marker);if(social)query.set('social',social);
  location={href:'https://game.example/?'+query,search:'?'+query,origin:'https://game.example'};
  history={replaceState:(_state,_title,url)=>{const next=new URL(url,location.href);location.href=next.href;location.search=next.search;}};
  const state={current,settings:{},careers:{}},game={state,content:{careers:{}},gifts:[{}],init:async()=>{},more:async()=>{}};
  const environment={api:game,ui,openSheet:(view,data={})=>{Object.assign(ui,data,{view});sheet.open=true;calls.push('sheet:'+view);},toast:message=>calls.push('toast:'+message)};
  const noop=()=>{},module=names=>Object.fromEntries(names.map(name=>[name,()=>calls.push(name)]));
  const lazy=names=>({get:async()=>module(names)});
  const L={tut:lazy(['tutorialBoot']),inc:lazy(['incidentBoot']),chat:lazy(['aiNoticeBoot']),happen:lazy(['happenBoot']),
    people:lazy([]),social:lazy(['startSocialPoll','invalidate']),tips:lazy(['tipsBoot']),live:lazy(['liveBoot'])};
  const node={hidden:true};
  // The 2.5D HUD and world are stubbed (iso-boot.js has its own tests).
  const context={iso:{bootShell(){},start(){},booted:()=>false},interact:()=>{},isoTownFirst:()=>!newbie,api:game,ui,L,CAREER_MODULES:[],career:()=>current,careerAssets:async()=>{},setLanguage:async()=>{},
    shell:{boot:noop},journeyBoot:noop,boardBoot:noop,startTicker:noop,$:selector=>selector==='#sheet'?sheet:node,
    world:{resize:noop},renderMain:noop,accountBoot,env:()=>environment,ensureCareerUI:noop,performance:{mark:noop},
    console,localStorage,location,history,CustomEvent,URL,URLSearchParams,sound:{prepare:noop},needsJob:()=>false,
    room:()=>({open,shift_summary:summary}),firstDay:()=>true,registerWorker:noop,listenWorker:noop,
    openSheet:environment.openSheet,prefetch:noop,whenIdle:fn=>idle.push(fn),setTimeout:fn=>idle.push(fn),
    window:{requestIdleCallback:fn=>idle.push(fn)},document:{dispatchEvent:noop},
    loadModule:async()=>module(['telemetryBoot','whatsNewBoot','x3Boot','giftBoot','onboardBoot','tickerBoot'])};
  await runInNewContext('(async()=>{'+startup+'})()',context);
  const settle=async()=>{for(let i=0;i<30;i++){while(idle.length)idle.shift()();await Promise.resolve();}};
  await settle();
  return {sheet,ui,calls,settle};
}
const automatic=['tutorialBoot','incidentBoot','aiNoticeBoot','happenBoot','whatsNewBoot','x3Boot','giftBoot','onboardBoot'];
const startupFailures=[];
for(const [name,test] of [
  ['callback account remains visible for guest, preparation, summary and active shift',async()=>{
    for(const state of [{},{current:'tea'},{current:'tea',summary:true},{current:'tea',open:true}]){
      const g=await startGame({...state,marker:'tiktok_denied'});
      assert.equal(g.ui.view,'settings');assert.equal(g.ui.setTab,'account');assert.match(g.ui.acctError,/hủy/);
      assert.deepEqual(g.calls.filter(c=>c.startsWith('sheet:')),['sheet:settings']);
      assert.equal(new URL(location.href).searchParams.has('tiktok'),false);
    }
  }],
  ['callback notices wait for a true close and then start once',async()=>{
    const g=await startGame({marker:'linked',current:'tea',summary:true,social:'street'});
    assert.deepEqual(g.calls.filter(c=>automatic.includes(c)),[]);
    // Native close events are queued: a stale event after a sheet reopens must not release notices.
    g.sheet.dispatchEvent(new Event('close'));await g.settle();
    assert.deepEqual(g.calls.filter(c=>automatic.includes(c)),[]);
    g.sheet.open=false;g.sheet.dispatchEvent(new Event('close'));await g.settle();
    for(const name of automatic)assert.equal(g.calls.filter(c=>c===name).length,1,name+' resumes');
    g.sheet.dispatchEvent(new Event('close'));await g.settle();
    for(const name of automatic)assert.equal(g.calls.filter(c=>c===name).length,1,name+' stays one-use');
  }],
  ['ordinary startup keeps initial sheets, social link and automatic features',async()=>{
    // 🏝️ Every open lands on the 2.5D island (no workplace sheet); a brand-new player meets the intro (home) first.
    for(const [state,view] of [[{newbie:true},'home'],[{},null],[{current:'tea'},null],[{current:'tea',summary:true},null],[{current:'tea',open:true},null],[{social:'street'},'social']]){
      const g=await startGame(state);assert.equal(g.ui.view||null,view);
      for(const name of automatic)assert.equal(g.calls.filter(c=>c===name).length,1,name+' starts normally');
    }
  }]
]){try{await test();}catch(error){startupFailures.push(new Error(name,{cause:error}));}}
if(startupFailures.length)throw new AggregateError(startupFailures,'app OAuth startup regressions');
console.log(JSON.stringify({ok:true}));
