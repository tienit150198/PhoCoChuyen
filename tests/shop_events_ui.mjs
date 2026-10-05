import assert from 'node:assert/strict';
import {shopEventCard} from '../public/js/shop-events-ui.js';
assert.equal(shopEventCard(null,()=>''),'');
const events=[];
const html=shopEventCard({camera:true,pending:{id:'e1',title:'Khách <x>',text:'Chưa trả tiền',choices:[{id:'ask',label:'Nhắc khách',cost:0,effect:'Kiểm hóa đơn'},{id:'help',label:'Hỗ trợ',cost:10,effect:'Tốn công'}]},recent:[{title:'Đã xử lý',text:'Kết quả <x>'}]},(label,e,c)=>{events.push([e.id,c.id]);return `<button>${label}</button>`;});
assert.match(html,/giảm 50%/);assert.match(html,/Khách &lt;x&gt;/);assert.match(html,/10 xu/);assert.doesNotMatch(html,/<x>/);
assert.deepEqual(events,[['e1','ask'],['e1','help']]);
console.log('Shop event UI: choices, cost, camera, history and escaping passed');
