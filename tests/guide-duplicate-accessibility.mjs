import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import ts from 'typescript';

const source=readFileSync(new URL('../public/js/v4/guide.js',import.meta.url),'utf8');
const ast=ts.createSourceFile('guide.js',source,ts.ScriptTarget.Latest,true);
const code=ast.statements.filter(n=>ts.isFunctionDeclaration(n)&&['sameGo','applyGuide'].includes(n.name?.text))
  .map(n=>n.getText(ast).replace(/^export /,'')).join('\n');

function node(dataset={}){
  const attrs=new Map(),classes=new Set();
  return {dataset,attrs,classes,closest:()=>null,
    setAttribute:(k,v)=>attrs.set(k,String(v)),getAttribute:k=>attrs.get(k)??null,removeAttribute:k=>attrs.delete(k),
    set tabIndex(v){attrs.set('tabindex',String(v));},
    classList:{toggle:(c,on)=>on?classes.add(c):classes.delete(c),contains:c=>classes.has(c)},
  };
}

function fixture(){
  const action={action:'car:go',op:'tea_cup',payload:'{"task":"milk_tea-0001-00","size":"M"}',quick:'',ownBusy:''};
  const hint=node(),button=node({...action}),actual=node({...action});
  let inBody=true,note='',twins=[actual],ctas=[actual];
  hint.querySelector=s=>s==='.gd-hint'?button:s==='.gd-note'&&note?{textContent:note}:null;
  const body={textContent:'Lấy ly M',querySelectorAll:s=>s==='button:not([disabled]),[role="button"]'?twins:s==='.gd-cta:not([disabled])'?ctas:[]};
  const head={querySelector:()=>null,append:()=>{inBody=false;}};
  const dialog={querySelectorAll:s=>s==='.sheet-body .gd-next'&&inBody?[hint]:[],
    querySelector:s=>s==='.sheet-head .grow'?head:s==='.sheet-body'?body:s==='.gd-next'?hint:null};
  const context=vm.createContext({pointers:()=>{},clean:()=>false,placeToasts:()=>{}});
  vm.runInContext(code+';globalThis.apply=applyGuide;',context);
  return {hint,button,actual,action,apply:()=>context.apply(dialog),
    redraw({unique=false,help=''}={}){inBody=true;twins=unique?[]:[actual];ctas=unique?[]:[actual];note=help;}};
}

test('a clipped duplicate is absent from the accessibility tree while the real step retains its action',()=>{
  const f=fixture();f.apply();
  assert.equal(f.hint.classes.has('gd-dup'),true);
  assert.equal(f.hint.getAttribute('aria-hidden'),'true','the clipped header must not expose a dead actionable button');
  assert.equal(f.button.getAttribute('tabindex'),'-1');
  assert.equal(f.actual.getAttribute('aria-hidden'),null);
  assert.equal(f.actual.getAttribute('tabindex'),null);
  assert.deepEqual(f.actual.dataset,f.action,'the visible tile/bottom action keeps its command and payload');
});

test('a distinct instruction remains visible and available to assistive technology',()=>{
  const f=fixture();f.redraw({help:'Khách dị ứng sữa'});f.apply();
  assert.equal(f.hint.classes.has('gd-dup'),false);
  assert.equal(f.hint.getAttribute('aria-hidden'),null);
  assert.equal(f.button.getAttribute('tabindex'),null);
});

test('a reused hint becomes accessible again when it is the only way to do the next step',()=>{
  const f=fixture();f.apply();
  assert.equal(f.hint.getAttribute('aria-hidden'),'true');
  f.redraw({unique:true});f.apply();
  assert.equal(f.hint.classes.has('gd-dup'),false);
  assert.equal(f.hint.getAttribute('aria-hidden'),null);
  assert.equal(f.button.getAttribute('tabindex'),null);
  assert.deepEqual(f.button.dataset,f.action);
});
