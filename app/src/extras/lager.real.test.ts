import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {createExtras,reduceExtras} from './gateway';
import type {ExtrasData,ExtraEvent} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
const traces=JSON.parse(readFileSync(dataPath('../analysis/extras/lager-traces.json'),'utf8')) as {randomized:boolean;strategy:string|number;initial:{page:string;focus:number};steps:{event:ExtraEvent;expected:{page:string;focus:number;context:unknown}}[]}[];
for(const t of traces)test(`continuous source Lager ${t.randomized?'randomized':'legacy'} ${t.strategy}`,()=>{
 let s={...createExtras('archive',1,t.randomized),gameId:'lager' as const,pageId:t.initial.page,focus:t.initial.focus,context:{randomized:t.randomized,guardMarker:12000,cursorCue:7000,selectionSeed:4,variantCue:3000}};
 for(const step of t.steps){s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken}) as typeof s;s=reduceExtras(data,s,{...step.event,token:s.sceneToken}) as typeof s;expect(s.pageId).toBe(step.expected.page);expect(s.focus).toBe(step.expected.focus);expect(s.context).toEqual(step.expected.context);}
 s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken}) as typeof s;s=reduceExtras(data,s,{type:'ACTIVATE',token:s.sceneToken,controlId:3,time:1}) as typeof s;expect(s.pageId).toBe('archive-intro');
});
