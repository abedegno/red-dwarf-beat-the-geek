import {expect,test} from 'vitest';
import {initializeVending,startVending,vendingTable,nextVendingOrder,enterVendingDigit} from './vending';
import {gatewayFixture} from './gatewayFixture';
import {createExtras,reduceExtras} from './gateway';
import type {ExtrasData,ExtrasState,ExtraAction} from './types';
function fixture():ExtrasData{
 const d=gatewayFixture();d.vending={initialCues:{'2':2,'4':3},initialCueDefault:1,initialRandomRange:3,roundCueOverrides:[{'2':2,'4':3},{'4':3,'8':4}],completePage:'vending-complete',rounds:[]};
 const page=(id:string,after:ExtraAction|null,controls=false,nextStage:number|null=null)=>{d.pages.push({id,scene:'clip',focus:controls?1:0,loop:controls,after,controls:controls?Array.from({length:10},(_,i)=>({id:i+1,label:String((i+1)%10),autoActivate:false,neighbours:{up:i+1,down:i+1,left:i+1,right:i+1},variants:[{startTicks:0,endTicks:900000,rect:{x:0,y:0,width:10,height:10},highlightSrc:'/media/h.png',action:{type:'vending-digit',digit:(i+1)%10,correct:i===0,nextStage}}]})):[]});};
 for(let n=0;n<3;n++){
  const products=Array.from({length:n+3},(_,i)=>({id:`p${n}-${i}`,pages:Array.from({length:n+2},(_,j)=>`p${n}-${i}-digit-${j}`)}));
  const cueProducts=Object.fromEntries(products.map((p,i)=>[String(i+1),p.id]));if(n===1)cueProducts['5']=products[0].id;if(n===2){cueProducts['6']=products[2].id;cueProducts['7']=products[3].id;}
  d.vending.rounds.push({products,cueProducts,defaultProduct:products[0].id,randomRange:n?5:3,intro:[`intro-${n}`,`table-${n}`],successPage:`success-${n}`,wrongPage:`wrong-${n}`});
  page(`intro-${n}`,{type:'vending-table'});page(`table-${n}`,{type:'vending-order'});page(`success-${n}`,{type:'vending-order'});page(`wrong-${n}`,{type:'page',page:'vending-menu'});
  for(const p of products)for(const [stage,id] of p.pages.entries())page(id,null,true,stage+1<p.pages.length?stage+1:null);
 }
 page('vending-complete',{type:'page',page:'vending-menu'});return d;
}
function begin(d=fixture(),randomized=false){let s=initializeVending(d,{...createExtras('archive',1,randomized),gameId:'vending'},()=>0);s=startVending(d,s,()=>0);s=vendingTable(d,s);return nextVendingOrder(d,s,()=>0);}
function correctOrder(d:ExtrasData,s:ExtrasState){const product=d.vending!.rounds[s.vending!.round].products.find(p=>p.id===s.vending!.productId)!;while(s.vending!.entered.length<product.pages.length)s=enterVendingDigit(d,s,1,true);return s;}
test('wrong digits advance entry and only the complete code selects failure',()=>{
 const d=fixture();let s=begin(d);expect(s.vending?.order).toBe(1);s=enterVendingDigit(d,s,9,false);expect(s.vending?.entered).toEqual([9]);expect(s.pageId).toContain('digit-1');expect(s.context.variantCue).toBe(0);
 s=enterVendingDigit(d,s,1,true);expect(s.pageId).toBe('wrong-0');expect(s.vending?.successes).toBe(0);expect(s.context.variantCue).toBe(1);
});
test('two distinct orders per round and all six successes reach the original ending',()=>{
 const d=fixture();let s=begin(d,true);
 for(let round=0;round<3;round++){
  const first=s.vending!.productId;s=correctOrder(d,s);s=nextVendingOrder(d,s,()=>0);expect(s.vending!.productId).not.toBe(first);expect(s.vending!.order).toBe(2);
  s=correctOrder(d,s);s=nextVendingOrder(d,s,()=>0);
  if(round<2){expect(s.pageId).toBe(`intro-${round+1}`);s=vendingTable(d,s);s=nextVendingOrder(d,s,()=>0);}
 }
 expect(s.pageId).toBe('vending-complete');expect(s.vending?.successes).toBe(6);expect(s.context.guardMarker).toBe(2);expect(s.context.variantCue).toBe(4);
});
test('legacy entry, cue retention on replay and between-round seed reset match source rules',()=>{
 const d=fixture();let s=begin(d);expect(s.vending!.productCue).toBe(3);s=enterVendingDigit(d,s,9,false);s=enterVendingDigit(d,s,9,false);s=startVending(d,s,()=>0);s=vendingTable(d,s);s=nextVendingOrder(d,s,()=>0);expect(s.vending!.productCue).toBe(5);
 s=begin(d);s={...s,context:{...s.context,selectionSeed:16384}};s=correctOrder(d,s);s=nextVendingOrder(d,s,()=>0);s=correctOrder(d,s);s=nextVendingOrder(d,s,()=>0);expect(s.context.selectionSeed).toBe(4);expect(s.vending?.productCue).toBe(3);
});
test('buffering and duplicate digit events cannot enter two digits',()=>{
 const d=fixture();let s=begin(d),token=s.sceneToken;const e={type:'ACTIVATE' as const,token,controlId:2,time:.2};expect(reduceExtras(d,s,e)).toBe(s);s=reduceExtras(d,s,{type:'SCENE_READY',token});s=reduceExtras(d,s,e);expect(s.vending?.entered).toEqual([2]);expect(reduceExtras(d,s,e)).toBe(s);
});
test('authored digit restart retains matches and still judges the exact source count',()=>{
 const d=fixture();let s=begin(d);s=enterVendingDigit(d,s,1,true,1);s=enterVendingDigit(d,s,9,false,0);expect(s.vending?.entered).toEqual([]);expect(s.context.variantCue).toBe(1);
 s=enterVendingDigit(d,s,1,true,1);s=enterVendingDigit(d,s,1,true,null);expect(s.pageId).toBe('wrong-0');expect(s.context.variantCue).toBe(3);
});
