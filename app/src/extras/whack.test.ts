import {expect,test} from 'vitest';
import {startWhack,advanceWhack,hitWhack,whackMenu} from './whack';
import {gatewayFixture} from './gatewayFixture';
import {createExtras,reduceExtras} from './gateway';
import type {ExtrasData} from './types';
function fixture():ExtrasData{
 const d=gatewayFixture();d.whack={positions:Array.from({length:17},(_,i)=>'position-'+(i+1)),results:Array.from({length:21},(_,i)=>'score-'+i),cursorCycle:[4,5,3,2,7,6,4,9,7,1,5,8,2,3,9,4,1]};
 for(const id of [...d.whack.positions,...d.whack.results])d.pages.push({id,scene:'clip',focus:0,loop:false,controls:[],after:{type:'whack-next'}});return d;
}
test('randomized appearance preserves cursor/position/cursor draw order',()=>{
 const d=fixture(),values=[.9,.5,.1];let s=startWhack(d,{...createExtras('archive',4),gameId:'whack'},()=>values.shift()!);
 expect(s.whack?.attempt).toBe(1);expect(s.whack?.appearance).toBe(9);expect(s.focus).toBe(1);expect(s.context.cursorCue).toBe(1024);expect(values).toHaveLength(0);
});
test('hits, misses, score floor and expiry follow twenty appearances exactly',()=>{
 const d=fixture();let s=startWhack(d,createExtras('archive',1),()=>0);
 s=hitWhack(d,s,false,2,()=>0);expect(s.whack?.score).toBe(0);s=hitWhack(d,s,true,2,()=>0);expect(s.whack?.score).toBe(1);s=advanceWhack(d,s,()=>0);expect(s.whack?.score).toBe(1);
 while(s.whack!.attempt<20)s=hitWhack(d,s,true,2,()=>0);
 expect(s.pageId).toBe('position-1');s=advanceWhack(d,s,()=>.9);expect(s.pageId).toBe('score-17');expect(s.whack?.attempt).toBe(20);expect(s.context.cursorCue).toBe(9);
});
test('legacy cursor cycle and chosen next-position seed survive replay correctly',()=>{
 const d=fixture();let s=startWhack(d,createExtras('archive',1,false),()=>{throw new Error('legacy draw');});
 expect(s.focus).toBe(0);expect(s.whack?.appearance).toBe(1);s=hitWhack(d,s,true,16,()=>0);expect(s.whack?.appearance).toBe(17);expect(s.focus).toBe(4);expect(s.context.selectionSeed).toBe(1);
 s=whackMenu(d,s);expect(s.whack?.score).toBe(0);expect(s.whack?.cursorStep).toBe(2);s=startWhack(d,s,()=>0);expect(s.focus).toBe(5);expect(s.whack?.appearance).toBe(1);
 const opened=whackMenu(d,s,true);expect(opened.whack?.cursorStep).toBe(0);
});
test('waiting and stale callbacks cannot consume an appearance twice',()=>{
 const d=fixture();let s=startWhack(d,{...createExtras('archive',1),gameId:'whack'},()=>0);const token=s.sceneToken;
 const p=d.pages.find(p=>p.id===s.pageId)!;p.after={type:'whack-next'};
 expect(reduceExtras(d,s,{type:'SCENE_ENDED',token},()=>0)).toBe(s);
 s=reduceExtras(d,s,{type:'SCENE_READY',token},()=>0);s=reduceExtras(d,s,{type:'SCENE_ENDED',token},()=>0);expect(s.whack?.attempt).toBe(2);expect(reduceExtras(d,s,{type:'SCENE_ENDED',token},()=>0)).toBe(s);
});
