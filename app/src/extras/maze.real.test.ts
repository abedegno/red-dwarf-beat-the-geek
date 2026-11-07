import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {createExtras,reduceExtras} from './gateway';
import {startMaze} from './maze';
import type {ExtrasData,ExtraEvent} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
const traces=JSON.parse(readFileSync(dataPath('../analysis/extras/maze-traces.json'),'utf8')) as {name:string;steps:{event:ExtraEvent;expected:{page:string;focus:number;lives:number;docking:number;victory:boolean}}[]}[];
for(const trace of traces)test(`continuous source keyboard maze ${trace.name}`,()=>{
 let s=startMaze(data,{...createExtras('archive',1),gameId:'maze'});
 for(const {event,expected} of trace.steps){s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken});s=reduceExtras(data,s,{...event,token:s.sceneToken});expect(s.pageId).toBe(expected.page);expect(s.focus).toBe(expected.focus);expect(s.maze).toEqual({lives:expected.lives,docking:expected.docking});}
 expect(trace.name==='success'?s.context.randomized:s.maze?.lives).toBe(trace.name==='success'?false:0);
});
