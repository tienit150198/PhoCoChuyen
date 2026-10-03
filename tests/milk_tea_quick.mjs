// The milk tea picks shown ahead of the server (public/js/careers/milk_tea.js "picks at once") against the server.
// Run by tests/test_milk_tea_quick.py, which sends the cases on stdin:
//   {ingredients, cases:[{room, task, op, payload, pending:[{op,payload}]}]}
// Prints [{quick, cup, ticket}] per case: canQuick on the task with `pending` laid on it, then the cup and the order
// ticket with this pick laid on too.
import {readFileSync} from 'node:fs';
import {quickParts} from '../public/js/careers/milk_tea.js';
const {laid,reTicket,canQuick,withLocal}=quickParts;
const spec=JSON.parse(readFileSync(0,'utf8'));
const out=spec.cases.map(k=>{
  const x={room:k.room,content:{experiences:{ingredients:spec.ingredients}},ui:{mtLocal:k.pending}};
  const t=withLocal(k.room.tasks.find(v=>v.id===k.task.id)||k.task,x);
  const quick=canQuick(x,t,k.op,k.payload);
  const cup=laid(x,t.cup,[{op:k.op,payload:k.payload}]);
  return {quick,cup,ticket:t.ticket?reTicket(x,t.ticket,cup):null};
});
process.stdout.write(JSON.stringify(out));
