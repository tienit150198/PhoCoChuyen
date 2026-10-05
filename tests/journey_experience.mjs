import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import test from 'node:test';

globalThis.document={createElement:()=>({getContext:()=>null}),getElementById:()=>null,querySelector:()=>({sheet:{}}),addEventListener:()=>{}};
globalThis.addEventListener=()=>{};
const {journeyHome,journeyAction}=await import('../public/js/v4/journey.js');
const career=(started=false,level=1)=>({started,level,day:1,job:{},metrics:{served:started?3:0}});
function env(goals){return {api:{state:{name:'An',current:'milk_tea',careers:{milk_tea:career(true),repair:career(),hr_admin:career()},journey:{story:true,intro:true,gender:'female',chapter:2,life_day:2,wallet:100,debt:0,titles:[],skills:[],places:{},unlocked:['milk_tea','repair','hr_admin'],suggested:'repair',maturity:{level:1,xp:0,floor:0,next:100,name:'Mới đến'},goals:goals.map(id=>({id,text:`Mục tiêu ${id}`,done:false,cur:0,goal:3}))}},content:{catalogue:[{id:'milk_tea',place:'Trà sữa',category:'food'},{id:'repair',place:'Sửa xe',category:'service'},{id:'hr_admin',place:'Văn phòng',category:'office'}],journey:{chapters:[{n:2,title:'Chương hai',tagline:'Làm quen phố',art:'🏡',intro:[{emoji:'🙂',name:'Hàng xóm',text:'Thử việc nhé'}]}],skills:[]}}},ui:{view:'home',homeMode:'list'}};}
const row=(html,id)=>html.match(new RegExp(`<li[^>]*data-goal="${id}"[\\s\\S]*?</li>`))?.[0]||'';

test('current chapter precedes character, workplaces and secondary cards in mobile reading order',()=>{
 const e=env(['places']);e.api.state.board={};const h=journeyHome(e);
 assert.ok(h.indexOf('jr-chapter')<h.indexOf('jr-me"'),'goals before character');
 assert.ok(h.indexOf('jr-chapter')<h.indexOf('jr-places"'),'goals before workplace catalogue');
 assert.ok(h.indexOf('jr-chapter')<h.indexOf('bd-entry'),'goals before neighbourhood card');
 const css=readFileSync(new URL('../public/css/journey.css',import.meta.url),'utf8');
 assert.match(css,/html\[data-layout="phone"\] \.jr-columns\{grid-template-columns:minmax\(0,1fr\)/);
 assert.match(css,/html\[data-layout="phone"\] \.jr-columns>\.jr-col\{grid-column:auto;grid-row:auto\}/);
});
test('each incomplete goal offers an honest existing destination; completed goals have no CTA',()=>{
 const e=env(['days','tasks','places','draw','level','clean','titles','mature','office_hired','office_days']);
 e.api.state.careers.hr_admin.job={required:true,status:'hired'};
 const h=journeyHome(e);
 for(const id of ['days','tasks','level','mature'])assert.match(row(h,id),/data-action="choose"/);
 assert.match(row(h,'places'),/data-action="jrPlaces"/);
 for(const id of ['draw','clean'])assert.match(row(h,id),/data-action="jrView" data-view="wallet"/);
 assert.match(row(h,'titles'),/data-action="jrView" data-view="titles"/);
 for(const id of ['office_hired','office_days'])assert.match(row(h,id),/data-action="choose" data-career="hr_admin"/);
 assert.match(row(h,'clean'),/ngày sống/);
 assert.doesNotMatch(h,/data-command=/,'navigation never completes a goal or spends funds');
 e.api.state.journey.goals[0].done=true;
 assert.doesNotMatch(row(journeyHome(e),'days'),/data-action=/);
});
test('recommendation stays with a visible reason in the chapter',()=>{
 const h=journeyHome(env(['places']));
 const chapter=h.match(/<section class="jr-card jr-chapter"[\s\S]*?<\/section>/)?.[0]||'';
 assert.match(chapter,/jr-resume/);
 assert.match(chapter,/jr-recommend-reason/);
 assert.match(chapter,/nơi mới/);
});
test('workplace goal opens existing catalogue and focuses it without a game command',async()=>{
 const e=env(['places']),calls=[];
 e.renderSheet=()=>calls.push('render');e.cmd=()=>assert.fail('navigation must not mutate game');
 const catalog={scrollIntoView:()=>calls.push('scroll'),focus:()=>calls.push('focus')};
 document.querySelector=s=>s==='.jr-places'?catalog:null;
 assert.equal(await journeyAction('jrPlaces',{},null,e),true);
 assert.equal(e.ui.homeMode,'list');assert.equal(e.ui.homeCat,'all');
 assert.deepEqual(calls,['render','scroll','focus']);
 document.querySelector=()=>null;
});
test('existing home navigation explicitly names changing workplace',()=>{
 const app=readFileSync(new URL('../public/js/app.js',import.meta.url),'utf8');
 assert.match(app,/\['home','grid','Đổi nghề'\]/);
 assert.match(app,/home:'Hành trình · mục tiêu của bạn'/);
 assert.match(app,/case'home':openSheet\('home'/,'same home destination retained');
});


test('town default includes shared actionable goals before the map',async()=>{
 const {townHTML}=await import('../public/js/v4/town-walk.js');
 const {chapterCard}=await import('../public/js/v4/journey.js');
 const h=townHTML(env(['places']),{FIRST_JOB:'milk_tea',chapterCard});
 assert.ok(h.includes('jr-chapter'),'town shows current chapter');
 assert.ok(h.indexOf('jr-chapter')<h.indexOf('data-tw-slot'),'goals before map');
 assert.match(h,/data-action="jrPlaces"/);
 assert.match(h,/jr-recommend-reason/);
});

test('unavailable recommended workplaces never get a direct choose CTA',()=>{
 const e=env(['tasks','office_days']);e.api.state.journey.unlocked=['milk_tea'];
 const h=journeyHome(e);
 assert.doesNotMatch(row(h,'office_days'),/data-career="hr_admin"/);
 assert.doesNotMatch(h.match(/jr-resume[^>]*>/)?.[0]||'',/data-career="repair"/);
});

test('office goal excludes unrelated office-category jobs; blocked places use catalogue guidance',()=>{
 const e=env(['office_hired','tasks']);
 e.api.state.careers.hr_admin.job={required:true,status:'none'};
 e.api.state.careers.accounting=career(true);e.api.state.careers.accounting.job={required:true,status:'hired'};
 e.api.content.catalogue.unshift({id:'accounting',category:'office',place:'Kế toán'});
 e.api.state.journey.unlocked=['accounting','hr_admin'];
 const h=journeyHome(e);
 assert.match(row(h,'office_hired'),/data-career="hr_admin"/);
 e.api.state.journey.places={accounting:{paused:true},hr_admin:{paused:true}};
 assert.match(row(journeyHome(e),'tasks'),/data-action="jrPlaces"/);
 assert.doesNotMatch(row(journeyHome(e),'tasks'),/data-action="choose"/);
});

test('compact first-day card prioritizes tasks with one primary work CTA and no long tagline',async()=>{
 const {chapterCard}=await import('../public/js/v4/journey.js');
 const e=env(['days','tasks']);e.api.state.current=null;e.api.state.journey.suggested='milk_tea';
 Object.values(e.api.state.careers).forEach(c=>c.started=false);
 const h=chapterCard(e,{compact:true});
 assert.match(h,/data-goal="tasks"/);
 assert.doesNotMatch(h,/data-goal="days"/);
 assert.equal((h.match(/data-action="choose"/g)||[]).length,1,'only one work CTA');
 assert.equal((h.match(/class="btn primary /g)||[]).length,1,'work CTA remains primary');
 assert.doesNotMatch(h,/Làm quen phố/,'compact omits long chapter tagline');
 assert.match(h,/jr-recommend-reason/,'matching work recommendation keeps its reason');
 assert.match(h,/Xem tất cả mục tiêu/);
 const full=chapterCard(e);
 assert.match(full,/Làm quen phố/);assert.match(full,/data-goal="days"/);assert.match(full,/data-goal="tasks"/);
 e.api.state.journey.goals[1].done=true;
 assert.match(chapterCard(e,{compact:true}),/data-goal="days"/,'closing day becomes next after tasks');
});

test('fresh profile all-goals control expands inline without re-entering introduction',async()=>{
 const {chapterCard}=await import('../public/js/v4/journey.js');
 const e=env(['days','tasks']);e.api.state.journey.intro=false;e.ui.homeMode='town';
 const h=chapterCard(e,{compact:true});
 assert.match(h,/data-action="jrGoals"[^>]*>Xem tất cả mục tiêu/);
 assert.doesNotMatch(h,/data-action="jrList"/);
 let renders=0;e.renderSheet=()=>renders++;e.cmd=()=>assert.fail('goal expansion cannot mutate player');
 const before=JSON.stringify(e.api.state);
 assert.equal(await journeyAction('jrGoals',{},null,e),true);
 assert.equal(e.ui.homeMode,'town');assert.equal(e.ui.jrView,undefined);assert.equal(renders,1);
 const expanded=chapterCard(e,{compact:true});
 assert.match(expanded,/data-goal="days"/);assert.match(expanded,/data-goal="tasks"/);
 assert.equal(JSON.stringify(e.api.state),before,'name, gender, introduction state unchanged');
 await journeyAction('jrGoals',{},null,e);
 assert.doesNotMatch(chapterCard(e,{compact:true}),/data-goal="days"/);
});
