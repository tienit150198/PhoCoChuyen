import assert from 'node:assert/strict';
import {barkCompetition} from '../public/js/v4/dog-bark-board.js';

assert.match(barkCompetition(null),/Chưa tải được bảng top/);
const base={week:'2026-10-05',ends:1791738000,minimum:30,prizes:[{rank:1,coins:2000000,title:'Vua sủa'}],rows:[],previous:null};
assert.match(barkCompetition(base),/Chưa có người đủ 30 trận/);
const data={...base,rows:[{rank:1,name:'<img onerror=x>',wins:27,played:30,rate:90,reward:2000000,title:'<b>Vua sủa</b>'}],
  me:{played:12,wins:9,rate:75,remaining:18,eligible:false,visible:true},
  previous:{week:'2026-09-28',rows:[{rank:1,name:'Lan',wins:29,played:30,rate:96.666,reward:2000000,title:'Vua sủa'}]}};
const html=barkCompetition(data);
assert.match(html,/2\.000\.000/);assert.match(html,/27\/30/);assert.match(html,/90%/);
assert.match(html,/18 trận nữa/);assert.match(html,/Kết quả tuần trước/);assert.match(html,/96,67%/);
assert.match(html,/75% thắng · 9\/12 trận/);
assert.match(html,/&lt;img/);assert.doesNotMatch(html,/<img|<b>Vua/);
assert.match(html,/Hòa tính vào tổng trận/);assert.match(html,/không tính/);
assert.match(barkCompetition({...base,me:{eligible:true,visible:false,rank:null,played:30,wins:27,rate:90,remaining:0}}),/đang ẩn tên/);
assert.match(barkCompetition({...base,me:{eligible:true,visible:true,rank:2,played:30,wins:27,rate:90,remaining:0}}),/Hạng 2/);
assert.match(barkCompetition({...base,me:{eligible:true,visible:true,rank:null,played:40,wins:20,rate:50,remaining:0}}),/Đã đủ điều kiện/);
console.log('Bark weekly board: prizes, qualification, ranking, privacy, previous winners and escaping passed.');
