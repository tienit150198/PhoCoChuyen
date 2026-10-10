import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const path=new URL('../public/js/v4/walk.js',import.meta.url),source=ts.createSourceFile('walk.js',readFileSync(path,'utf8'),ts.ScriptTarget.Latest,true,ts.ScriptKind.JS);
// Run the production header, action dispatcher, entry transport and passenger
// controls. Only their DOM, live socket and unrelated avatar helpers are stubs.
const code=source.statements.filter(node=>ts.isFunctionDeclaration(node)&&['head','count','act','enter','paintCo'].includes(node.name?.text)).map(node=>node.getText(source)).join('\n');
function harness({privateRoom=true,lastPublic='congvien',spouse=true}={}){
  const sent=[],nodes=new Map();
  const node=selector=>{
    if(!nodes.has(selector))nodes.set(selector,{dataset:{},innerHTML:'',hidden:false,classList:{toggle(){}}});
    return nodes.get(selector);
  };
  const me={pid:'me'},driver={pid:'spouse',name:'Người ấy',r:{v:'bike'}};
  const S={env:{api:{state:{journey:{gender:'female'}},content:{}}},dlg:{querySelector:node,querySelectorAll:()=>[]},
    room:{private:privateRoom,room:privateRoom?'private:coffee':'public:park',place:privateRoom?'cafe':'congvien',me:'me',icon:'☕',name:'Góc cà phê'},
    people:new Map([['me',me],['spouse',driver]]),wedding:null,cv:null,picker:false,places:[],lastPublic,taken:null};
  const context=vm.createContext({S,live:{flags:{coride:true},send:message=>sent.push(JSON.parse(JSON.stringify(message)))},
    spouseOf:()=>spouse?{pid:'spouse'}:null,paintRide(){},paintOverlays(){},esc:String,icon:()=>'',
    lookOf:()=>({}),rankRef:()=>null,BB:{wire:()=>null},wire:()=>null,choice:()=>null,TWO:{two:true}});
  vm.runInContext(code+';globalThis.ui={head,act,paintCo};',context);
  return {S,sent,node,me,driver,...context.ui};
}
const actionOf=html=>html.match(/<button\b[^>]*data-wk="([^"]+)"/)?.[1];

test('the private-place header returns to the last public place through the actual entry transport',()=>{
  for(const spouse of [true,false]){
    const x=harness({spouse});x.head();
    const action=actionOf(x.node('.wk-head').innerHTML);assert.ok(action,'private header has a return control');
    x.act(action,{});
    assert.equal(x.sent.length,1,'return must enter the public place even without a spouse');
    assert.equal(x.sent[0].t,'walk_in');assert.equal(x.sent[0].place,'congvien');
    assert.equal(x.S.want,'congvien');
  }
});

test('the visible public passenger button retains the back wire protocol',()=>{
  const x=harness({privateRoom:false});x.paintCo(true,x.me,null);
  const action=actionOf(x.node('.rd-co').innerHTML);assert.ok(action,'an eligible spouse has a passenger button');
  x.act(action,{});
  assert.deepEqual(x.sent,[{t:'back',to:'spouse'}]);
  assert.equal(x.S.want,undefined,'sitting behind a spouse does not change places');
});

test('a private room cannot offer or dispatch the passenger route',()=>{
  const x=harness();x.paintCo(false,x.me,null);
  assert.equal(actionOf(x.node('.rd-co').innerHTML),undefined);
  x.act('back',{});assert.deepEqual(x.sent,[]);
});

test('a private return without a remembered public place does not invent an entry',()=>{
  const x=harness({lastPublic:null});x.head();x.act(actionOf(x.node('.wk-head').innerHTML),{});
  assert.deepEqual(x.sent,[]);assert.equal(x.S.want,undefined);
});

test('public headers keep their place picker and dismount still clears the passenger target',()=>{
  const x=harness({privateRoom:false});x.head();
  assert.equal(actionOf(x.node('.wk-head').innerHTML),'places');
  x.act('off',{});assert.deepEqual(x.sent,[{t:'back',to:null}]);
});
