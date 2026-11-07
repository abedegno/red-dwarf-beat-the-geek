import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {validateCompleteExtrasData} from './validation';
import type {ExtrasData} from './types';
const data=JSON.parse(readFileSync(dataPath('../analysis/extras/gateway.json'),'utf8')) as ExtrasData;
test('a published extras catalog requires all five engines and deterministic quiz metadata',()=>{
 validateCompleteExtrasData(data,data.sourceFingerprint);
 for(const key of ['maze','whack','vending','memory','lager','quizEntry'] as const){const d=structuredClone(data);delete d[key];expect(()=>validateCompleteExtrasData(d,d.sourceFingerprint)).toThrow();}
});
test('rejects missing required continuations and actions owned by another engine',()=>{
 const mutations:((d:ExtrasData)=>void)[]=[];
 for(const id of ['archive-intro','keypad-confirm','invalid-code','instructions-video','vending-success-0','vending-wrong-0','vending-complete','memory-result-0-47'])mutations.push(d=>{d.pages.find(p=>p.id===id)!.after=null;});
 mutations.push(
  d=>{d.pages.find(p=>p.id==='archive-intro')!.after={type:'memory-next'};},
  d=>{d.pages.find(p=>p.id==='memory-result-0-47')!.after={type:'vending-order'};},
  d=>{d.pages.find(p=>p.id==='memory-result-0-47')!.after={type:'page',page:'memory-menu'};},
  d=>{d.pages.find(p=>p.id==='vending-success-0')!.after={type:'page',page:'vending-menu'};},
  d=>{d.pages.find(p=>p.id==='whack-menu')!.controls[0].variants[0].action={type:'memory-next'};},
  d=>{d.pages.find(p=>p.id==='vending-help')!.controls[0].variants[0].action={type:'page',page:'memory-menu'};},
 );
 for(const mutate of mutations){const d=structuredClone(data);mutate(d);expect(()=>validateCompleteExtrasData(d,d.sourceFingerprint)).toThrow();}
});
