import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {validateExtrasData} from './validation';
import {createExtras,reduceExtras} from './gateway';
import type {ExtrasData} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
test('original exported gateway is internally consistent with complete presentation assets',()=>{
 validateExtrasData(data,'0876ff298e2cd9ba1e752370ac5e87901b79364126a5126fa0dcf7136fd02c77');
 expect(data.subtitles).toHaveLength(30);expect(data.subtitles[0].startTicks).toBe(180000);
 for(const s of data.scenes)expect(readFileSync(dataPath('public')+s.src).length).toBeGreaterThan(100);
 for(const p of data.pages)for(const c of p.controls)for(const v of c.variants)expect(readFileSync(dataPath('public')+v.highlightSrc).subarray(1,4).toString()).toBe('PNG');
});
test('source keypad button numbers and all five routes work with the native coordinator',()=>{
 for(const [code,game] of Object.entries(data.codes)){
  let s=createExtras('archive',1);
  const end=()=>{s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken});s=reduceExtras(data,s,{type:'SCENE_ENDED',token:s.sceneToken});};end();
  for(const digit of code){s=reduceExtras(data,s,{type:'SCENE_READY',token:s.sceneToken});s=reduceExtras(data,s,{type:'ACTIVATE',token:s.sceneToken,controlId:Number(digit)||10,time:1});}
  expect(s.pageId).toBe('keypad-confirm');end();expect(s.gameId).toBe(game);
 }
});
test('rejects broken maze routes and deterministic-entry metadata before playback',()=>{
 for(const mutate of [
  (d:ExtrasData)=>{Object.values(d.maze!.nodes)[0].lives=9;},
  (d:ExtrasData)=>{d.maze!.entry.page='absent';},
  (d:ExtrasData)=>{d.quizEntry!.holly.norman[0].variantCue=9;},
  (d:ExtrasData)=>{d.quizEntry!.setups['1'].norman=['absent'];},
  (d:ExtrasData)=>{d.quizEntry!.mainOne[0].selectionSeed=0;},
  (d:ExtrasData)=>{delete d.quizEntry;},
  (d:ExtrasData)=>{d.whack!.positions.pop();},
  (d:ExtrasData)=>{d.whack!.results[0]='absent';},
  (d:ExtrasData)=>{d.whack!.cursorCycle[0]=0;},
  (d:ExtrasData)=>{delete d.whack;},
  (d:ExtrasData)=>{d.vending!.rounds[0].products.pop();},
  (d:ExtrasData)=>{d.vending!.rounds[1].cueProducts['5']='absent';},
  (d:ExtrasData)=>{delete d.vending;},
  (d:ExtrasData)=>{d.memory!.objects[0].label='';},
  (d:ExtrasData)=>{d.memory!.rounds[2].alwaysCorrectLast=false;},
  (d:ExtrasData)=>{delete d.memory;},
  (d:ExtrasData)=>{d.lager!.stages.pop();},
  (d:ExtrasData)=>{delete d.lager;},
 ]){const d=structuredClone(data);mutate(d);expect(()=>validateExtrasData(d,d.sourceFingerprint)).toThrow();}
});
