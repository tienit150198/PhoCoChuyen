import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';

const source=readFileSync(new URL('../public/js/isometric-shell.js',import.meta.url),'utf8')
  .replace(/^import .*\r?\n/gm,'').replace(/^export /gm,'')
  .replace("import('./v4/live.js')",'Promise.resolve(liveModule)');
const calls=[],root={dataset:{},classList:{contains:()=>false}},hud={};
const environment={api:{},ui:{}};
const liveModule={live:{on:event=>calls.push(['subscribe',event])},liveBoot:env=>calls.push(['boot',env])};
const context=vm.createContext({liveModule,document:{documentElement:root,body:{classList:{add(){}}},getElementById:()=>hud},window:{addEventListener(){}},MutationObserver:class {observe(){}},Promise});
vm.runInContext(source+'\nglobalThis.boot=bootIsometricShell;',context);
context.boot(()=>environment);
await Promise.resolve();
assert.equal(calls[0]?.[0],'boot','the visible conversation entry initializes live before waiting for idle app boot');
assert.equal(calls[0][1],environment,'the real live service receives the same authenticated app environment');
assert.ok(calls.some(([type,event])=>type==='subscribe'&&event==='read'),'read receipts refresh the HUD badge');
assert.ok(calls.some(([type,event])=>type==='subscribe'&&event==='connection'),'silent handshake timeouts and retry starts refresh the HUD status');
context.boot(()=>environment);
await Promise.resolve();
assert.equal(calls.filter(([type])=>type==='boot').length,1,'recovery renders do not add another set of live subscriptions');
console.log('isometric-chat-boot: ok');
