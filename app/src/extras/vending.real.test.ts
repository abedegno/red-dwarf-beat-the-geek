import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {createExtras,reduceExtras} from './gateway';
import {initializeVending} from './vending';
import type {ExtrasData,ExtraEvent} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
type Expected={page:string;round:number;productId:string|null;order:number;successes:number;correctDigits:number;productCue:number;guardMarker:number;variantCue:number;selectionSeed:number;cursorCue:number;usedProducts:string[];focus:number};
type Step={event:ExtraEvent;expected:Expected;draws:number[]};
const traces=JSON.parse(readFileSync(dataPath('../analysis/extras/vending-traces.json'),'utf8')) as {randomized:boolean;seed:number;strategy:string;initial:Expected;initialDraws:number[];steps:Step[];replay:Step[];quirk:boolean}[];
for(const trace of traces)test(`continuous source Vending ${trace.randomized?'randomized':'legacy'} seed${trace.seed} ${trace.strategy}`,()=>{
 let s={...createExtras('archive',1,trace.randomized),gameId:'vending' as const};s.context={...s.context,selectionSeed:trace.seed,cursorCue:65535,variantCue:3};
 const draw=(values:number[])=>{const remaining=[...values];return ()=>{if(!remaining.length)throw new Error('Unexpected Vending random draw');return remaining.shift()!;};};
 s=initializeVending(data,s,draw(trace.initialDraws)) as typeof s;
 const compare=(e:Expected)=>{expect(s.pageId).toBe(e.page);expect(s.focus).toBe(e.focus);expect(s.vending?.round).toBe(e.round);expect(s.vending?.productId).toBe(e.productId);expect(s.vending?.order).toBe(e.order);expect(s.vending?.successes).toBe(e.successes);expect(s.vending?.correctDigits).toBe(e.correctDigits);expect(s.vending?.productCue).toBe(e.productCue);expect([...s.vending!.usedProducts].sort()).toEqual([...e.usedProducts].sort());for(const key of ['guardMarker','variantCue','selectionSeed','cursorCue'] as const)expect(s.context[key]).toBe(e[key]);};
 compare(trace.initial);
 for(const {event,expected,draws} of [...trace.steps,...trace.replay]){
  s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken}) as typeof s;s=reduceExtras(data,s,{...event,token:s.sceneToken},draw(draws)) as typeof s;compare(expected);
 }
});
test('source traces exercise both retained-match recovery and selection-only digit buttons',()=>{
 expect(traces.some(t=>t.strategy==='recover'&&t.quirk)).toBe(true);expect(traces.some(t=>t.strategy==='focus'&&t.quirk)).toBe(true);
});
