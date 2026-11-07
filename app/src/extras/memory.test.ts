import {expect,test} from 'vitest';
import {initializeMemory,startMemory,firstMemoryObject,nextMemoryObject,recallMemory,beginMemoryStage,memoryMenu} from './memory';
import {createExtras,reduceExtras} from './gateway';
import {gatewayFixture} from './gatewayFixture';
import type {ExtrasData,ExtrasState,ExtraAction} from './types';
function fixture():ExtrasData{
 const d=gatewayFixture();d.memory={initialLegacyCues:[16,30],initialVariantThreshold:3,legacyOffsets:{'12':12,'11':9,'10':17,'9':22,'8':6,'7':14,'6':20,'5':5,'4':10,'3':13,'2':8,'1':11},objects:Array.from({length:30},(_,i)=>({id:i+1,label:`Object ${i+1}`,page:`object-${i+1}`})),rounds:[]};
 const page=(id:string,after:ExtraAction|null,controls=false)=>d.pages.push({id,scene:'clip',focus:controls?1:0,loop:controls,after,controls:controls?[{id:1,label:'Object 1',autoActivate:false,neighbours:{up:1,down:1,left:1,right:1},variants:[{startTicks:0,endTicks:900000,rect:{x:0,y:0,width:10,height:10},highlightSrc:'/media/h.png',action:{type:'memory-choice',objectId:1}}]}]:[]});
 for(const obj of d.memory.objects)page(obj.page,{type:'memory-next'});
 for(const [stage,length] of [5,8,12].entries()){
  const recall=Array.from({length},(_,i)=>`recall-${stage}-${i}`),results=Array.from({length:length+1},(_,i)=>`result-${stage}-${i}`);
  d.memory.rounds.push({length,intro:`intro-${stage}`,recall,results,recallFocus:Array(length).fill(null),alwaysCorrectLast:stage===2});page(`intro-${stage}`,{type:'memory-first'});
  for(const id of recall)page(id,null,true);for(const [score,id] of results.entries())page(id,stage<2&&score>=[3,5][stage]?{type:'memory-stage',stage:stage+1}:{type:'page',page:'memory-menu'});
 }
 return d;
}
function shown(d:ExtrasData,s:ExtrasState){s=firstMemoryObject(d,s,()=>0);while(s.memory!.phase==='show')s=nextMemoryObject(d,s,()=>0);return s;}
test('legacy initial cue uses prior variant and retains the unused next cue for replay',()=>{
 const d=fixture();let s=initializeMemory(d,createExtras('archive',1,false),()=>0);expect(s.memory?.cue).toBe(16);s=startMemory(d,s);s=shown(d,s);expect(s.memory?.shown).toEqual([16,21,15,28,18]);expect(s.memory?.cue).toBe(29);
 s=memoryMenu(d,s);s=startMemory(d,s);s=firstMemoryObject(d,s,()=>0);expect(s.memory?.shown[0]).toBe(29);
 const other={...createExtras('archive',1,false)};other.context.variantCue=3;expect(initializeMemory(d,other,()=>0).memory?.cue).toBe(30);
});
test('source partial thresholds progress5 to8 to12 and first/ninth/tenth/twelfth context slots follow shown objects',()=>{
 const d=fixture();let s=initializeMemory(d,createExtras('archive',1,false),()=>0);s=startMemory(d,s);s=shown(d,s);
 for(let i=0;i<5;i++)s=recallMemory(d,s,i<3?s.memory!.shown[i]:s.memory!.shown[i]%30+1);
 expect(s.memory?.score).toBe(3);expect(d.pages.find(p=>p.id===s.pageId)?.after).toEqual({type:'memory-stage',stage:1});s=beginMemoryStage(d,s,1);s=shown(d,s);expect(s.memory?.shown).toHaveLength(8);
 s=beginMemoryStage(d,s,2);s=shown(d,s);const seq=s.memory!.shown;expect(seq).toHaveLength(12);expect(s.context.guardMarker).toBe(seq[0]*1000);expect(s.context.cursorCue).toBe(seq[8]*1000);expect(s.context.selectionSeed).toBe(seq[9]*1000);expect(s.context.variantCue).toBe(seq[11]*1000);
});
test('the final twelve-item comparison always awards one point and failure returns to menu',()=>{
 const d=fixture();let s=initializeMemory(d,createExtras('archive',1),()=>0);s=beginMemoryStage(d,s,2);s=shown(d,s);
 for(let i=0;i<12;i++)s=recallMemory(d,s,s.memory!.shown[i]%30+1);
 expect(s.memory?.score).toBe(1);expect(d.pages.find(p=>p.id===s.pageId)?.after).toEqual({type:'page',page:'memory-menu'});
});
test('stale or buffered recall cannot consume two choices',()=>{
 const d=fixture();let s=initializeMemory(d,{...createExtras('archive',1),gameId:'memory'},()=>0);s=startMemory(d,s);s=shown(d,s);const token=s.sceneToken,e={type:'ACTIVATE' as const,token,controlId:1,time:.2};expect(reduceExtras(d,s,e)).toBe(s);s=reduceExtras(d,s,{type:'SCENE_READY',token});s=reduceExtras(d,s,e);expect(s.memory?.recalled).toHaveLength(1);expect(reduceExtras(d,s,e)).toBe(s);
});
