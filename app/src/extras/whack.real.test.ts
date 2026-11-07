import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {createExtras,reduceExtras} from './gateway';
import {startWhack,whackMenu} from './whack';
import type {ExtrasData,ExtrasState,ExtraEvent} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
type Expected={page:string;attempt:number;score:number;positionSeed:number;cursorStep:number;cursorCue:number;selectionSeed:number;focus:number;terminal:boolean};
const traces=JSON.parse(readFileSync(dataPath('../analysis/extras/whack-traces.json'),'utf8')) as {randomized:boolean;strategy:string;initialCursor:number;initial:Expected;steps:{event:ExtraEvent;expected:Expected}[];menu:Expected;replay:Expected}[];
for(const trace of traces)test(`continuous source Whack ${trace.randomized?'randomized':'legacy'} ${trace.strategy}`,()=>{
 let s:ExtrasState={...createExtras('archive',1,trace.randomized),gameId:'whack'};s.context.cursorCue=trace.initialCursor;
 const draws=(e:Expected)=>{
  const values=trace.randomized?(e.terminal?[(e.cursorCue-.5)/9]:[0,(e.positionSeed-.5)/17,((e.cursorCue>>>10)-.5)/9]):[];
  return ()=>{const v=values.shift();if(v===undefined)throw new Error('Unexpected source Whack draw');return v;};
 };
 const compare=(e:Expected)=>{expect(s.pageId).toBe(e.page);expect(s.whack?.attempt).toBe(e.attempt);expect(s.whack?.score).toBe(e.score);expect(s.whack?.positionSeed).toBe(e.positionSeed);expect(s.whack?.cursorStep).toBe(e.cursorStep);expect(s.context.cursorCue).toBe(e.cursorCue);expect(s.context.selectionSeed).toBe(e.selectionSeed);expect(s.focus).toBe(e.focus);};
 s=startWhack(data,s,draws(trace.initial));compare(trace.initial);
 for(const {event,expected} of trace.steps){s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken});s=reduceExtras(data,s,{...event,token:s.sceneToken},draws(expected));compare(expected);}
 s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken});s=reduceExtras(data,s,{type:'SCENE_ENDED',token:s.sceneToken});expect(s.pageId).toBe('whack-menu');expect(s.whack?.score).toBe(0);expect(s.whack?.cursorStep).toBe(trace.menu.cursorStep);expect(s.context.cursorCue).toBe(trace.menu.cursorCue);
 s=startWhack(data,s,draws(trace.replay));compare(trace.replay);
});
