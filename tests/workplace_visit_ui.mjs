import assert from 'node:assert/strict';
import {mergePeople,movePerson,applyVisitEvent,visitCustomer,sellerVisitStrip,preserveVisitDraft,visitorSelectionValid,visitControlId,customerTaskBanner,createVisitSettlementSync,visitSubtitle} from '../public/js/v4/workplace-visit-ui.js';
const a={place:'career:p1:milk_tea',people:[],messages:[]};
assert.equal(applyVisitEvent(a,{t:'visit_people',place:'career:other',people:[{pid:'bad'}]}),false);
assert.equal(a.people.length,0);
applyVisitEvent(a,{t:'visit_people',place:a.place,people:[{pid:'p1',name:'<A>',x:.5,y:.4}]});
applyVisitEvent(a,{t:'visit_mv',place:a.place,pid:'p1',p:[[.5,.4],[.7,.8]],ms:300});
assert.equal(a.people[0].x,.7);assert.equal(a.people[0].y,.8);
assert.equal(movePerson(a.people,'missing',[[0,0],[1,1]]).length,1);
assert.equal(mergePeople([{pid:'x',x:1,y:1},{pid:'x',x:0,y:0}]).length,1);
const draft={note:'giữ giúp mình',stars:4,tags:['friendly'],comment:'Rất vui'};
assert.deepEqual(preserveVisitDraft(draft,{status:'working'}),draft);
const task={npc:'npc1',customer:{name:'Minh',fc:'face',pid:'p1'}};
assert.equal(visitCustomer(task,{display_name:'NPC'}).display_name,'Minh');
assert.equal(visitCustomer({}, {display_name:'NPC'}).display_name,'NPC');
assert.doesNotMatch(sellerVisitStrip({tasks:[]}),/Phục vụ/);
assert.equal(visitorSelectionValid({status:'queued',dish:'tea'},['tea']),true);
assert.equal(visitorSelectionValid({status:'queued',dish:'tea'},['tea','tea']),false);
assert.equal(visitorSelectionValid({status:'completed',dish:'tea'},['tea']),false);
assert.equal(visitCustomer({npc:'n',player_order:{buyer:{name:'Khách thật',fc:'abc'}}},{display_name:'Mẫu',role:'Khách'}).display_name,'Khách thật');
console.log('Visit UI: foreign-room isolation, avatar positions, independent drafts and customer identity passed.');

assert.equal(visitControlId("offer", "data-id=tea"),visitControlId("offer", "data-id=tea"),"Polling reuses stable control ids to preserve focus");
assert.notEqual(visitControlId("offer", "data-id=tea"),visitControlId("offer", "data-id=cake"));
assert.match(customerTaskBanner({npc:"x",player_order:{buyer:{name:"<Khách>"},note:"<note>"}}),/&lt;Khách&gt;/);
assert.doesNotMatch(customerTaskBanner({}),/Đang phục vụ/);

// Settlement happens on the server when either participant polls. Refresh only changed order data.
let syncCalls=0,release;
const sync=createVisitSettlementSync(async()=>{syncCalls++;await new Promise(resolve=>{release=resolve});});
await sync({incoming:[],outgoing:[]});assert.equal(syncCalls,0);
const pending={incoming:[{id:'one',status:'accepted',price:75}],outgoing:[]};
const first=sync(pending);assert.equal(syncCalls,1);const duplicate=sync(pending);assert.equal(syncCalls,1,'No overlapping own-state refresh');release();await Promise.all([first,duplicate]);
await sync(pending);assert.equal(syncCalls,1,'Unchanged polls do not refresh');
const paid=sync({incoming:[{id:'one',status:'completed',price:75}],outgoing:[]});assert.equal(syncCalls,2,'Settlement refreshes the seller balance');release();await paid;
const refunded=sync({incoming:[{id:'one',status:'completed',price:75}],outgoing:[{id:'two',status:'cancelled',price:10}]});assert.equal(syncCalls,3,'Refund changes refresh the buyer balance');release();await refunded;
let attempts=0;const retry=createVisitSettlementSync(async()=>{if(++attempts===1)throw new Error('offline')});
await assert.rejects(retry(pending));await retry(pending);assert.equal(attempts,2,'Failed refresh is retried on the next same-state poll');
assert.match(visitSubtitle({mine:true}),/Chỗ làm của bạn/);assert.match(visitSubtitle({mine:false}),/Bạn đang làm khách/);
