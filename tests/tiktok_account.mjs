// Run account rendering/actions in the existing Node module harness.
import assert from 'node:assert/strict';
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
console.log(JSON.stringify({ok:true}));
