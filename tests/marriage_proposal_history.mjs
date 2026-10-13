import assert from 'node:assert/strict';
import {proposalStatus} from '../public/js/v4/marriage.js';
assert.equal(proposalStatus({status:'accepted',relationship_ended:true}),'đã nhận lời trước đây · mối quan hệ đã kết thúc');
assert.equal(proposalStatus({status:'accepted',relationship_ended:false}),'đã nhận lời');
assert.equal(proposalStatus({status:'accepted'}),'đã nhận lời');
assert.equal(proposalStatus({status:'pending'}),'đang chờ trả lời');
assert.equal(proposalStatus({status:'declined'}),'chưa nhận lời');
console.log('Marriage proposal history distinguishes ended relationships.');
