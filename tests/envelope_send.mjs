// Unit test of public/js/v4/envelope-send.js (the 🧧 envelope's request id across a lost answer).
// Run by tests/test_envelope_client.py (node tests/envelope_send.mjs); exits non-zero on failure.
import assert from 'node:assert/strict';
import {envRid,envSettle,envKey,newRid,UNKNOWN_TEXT} from '../public/js/v4/envelope-send.js';

let n=0;const mint=()=>`rid-${++n}`;
const err=status=>Object.assign(new Error('x'),status?{status}:{});

// A send the server answered ends its rid: the next tap is a new envelope.
let e={amount:200,wish:0};
assert.equal(envRid(e,envKey(7,200,0),mint),'rid-1');
assert.equal(envSettle(e,null),'sent');
assert.equal(envRid(e,envKey(7,200,0),mint),'rid-2','after a success, a new envelope');
assert.equal(envSettle(e,err(409)),'refused','the server said no (party over, not a guest…): nothing moved');
assert.equal(envRid(e,envKey(7,200,0),mint),'rid-3');
assert.equal(envSettle(e,err(400)),'refused');
assert.equal(envSettle({rid:'x',ridKey:'1|0'},err(429)),'refused','rate limited: refused, nothing moved');

// No answer (timeout / offline: no status; the proxy's 502, 503, 504): the same envelope keeps its rid.
for(const x of [err(0),err(502),err(503),err(504),new TypeError('Failed to fetch'),new DOMException('Timeout','AbortError')]){
  e={};const first=envRid(e,envKey(7,200,1),mint);
  assert.equal(envSettle(e,x),'unknown',String(x?.status??x?.name));
  assert.equal(envRid(e,envKey(7,200,1),mint),first,'the retap of the same envelope is the same rid (the server pays it once)');
  assert.notEqual(envRid(e,envKey(7,100,1),mint),first,'another amount is another envelope');
  const other=envRid(e,envKey(7,100,1),mint);
  assert.notEqual(envRid(e,envKey(7,100,2),mint),other,'another wish is another envelope');
}
// Another wedding is another envelope too.
e={};const here=envRid(e,envKey(7,50,0),mint);envSettle(e,err(504));
assert.notEqual(envRid(e,envKey(8,50,0),mint),here);

// Once an unknown send is answered (the retap went through, or "already sent"), the rid ends.
e={};envRid(e,envKey(7,50,0),mint);envSettle(e,err(504));envSettle(e,null);
assert.equal(e.rid,null);

// The real rid fits the server's pattern ([A-Za-z0-9-]{8,64}, cut to 24) and differs each time.
const r=newRid();
assert.match(r,/^[A-Za-z0-9-]{8,24}$/);
assert.notEqual(newRid(),newRid());
assert.match(UNKNOWN_TEXT,/không bị trừ thêm/);
console.log('envelope_send ok');
