import assert from 'node:assert/strict';
import pilot from '../public/js/careers/pilot.js';

const x = {
  room: {day: 4, open: true, day_completed: 1, data: {
    mod: {}, schedule: {total: 5, completed: 1, remaining: 4}
  }, tasks: [{id: 'pilot-0004-00', day: 4, status: 'waiting', known: false,
    expected_bonus: 19, leg: {dep: '06:00', code: 'CC101', to: 'Đảo', gate: 'A1'}}]},
  esc: v => String(v ?? ''), icon: () => '', cmd: () => '', button: () => '',
  npc: () => ({}), portrait: () => ''
};
const board = pilot.board(x);
assert.match(board, /Lịch hôm nay: 5 chặng/);
assert.match(board, /1 đã bay · 4 còn lại/);
assert.match(board, /Thưởng dự kiến 19 xu/);
assert.doesNotMatch(board, /undefined|NaN/);
const hud = pilot.hudCard(x.room, x.room.tasks[0], x, {});
assert.match(hud, /Lịch hôm nay: 5 chặng/);
assert.match(hud, /4 còn lại/);
assert.match(hud, /Thưởng dự kiến 19 xu/);
const closedHud = pilot.hudCard({...x.room, open: false}, null, x, {});
assert.doesNotMatch(closedHud, /Lịch hôm nay|Thưởng dự kiến/);
console.log('Pilot roster progress and flight bonus rendered.');
