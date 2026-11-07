import {describe,it,expect} from 'vitest';
import {createExtras,reduceExtras} from './gateway';
import {validateExtrasData} from './validation';
import type {ExtrasData,ExtrasState,ExtraEvent} from './types';

import {gatewayFixture as fixture} from './gatewayFixture';
function ready(s:ExtrasState,d=fixture()){return reduceExtras(d,s,{type:'SCENE_READY',token:s.sceneToken});}
function act(s:ExtrasState,id:number,time=.2,d=fixture()){return reduceExtras(d,ready(s,d),{type:'ACTIVATE',token:s.sceneToken,controlId:id,time});}
function end(s:ExtrasState,d=fixture()){return reduceExtras(d,ready(s,d),{type:'SCENE_ENDED',token:s.sceneToken});}

describe('original Instructions and Archive gateway',()=>{
 it('offers both subtitle choices and returns after instruction playback',()=>{
  for(const id of [1,2]){let s=act(createExtras('instructions',4),id);expect(s.pageId).toBe('instructions-video');expect(s.subtitles).toBe(id===2);s=end(s);expect(s.exit).toBe('main-menu');expect(s.subtitles).toBe(false);}
 });
 it('has four untimed masked input stages then the authored confirmation delay',()=>{
  let s=end(createExtras('archive',1));
  for(const digit of [7,5,2,3]){expect(s.pageId).toBe('keypad-'+s.code.length);expect(end(s).pageId).toBe(s.pageId);s=act(s,digit+1);}
  expect(s.pageId).toBe('keypad-confirm');expect(s.gameId).toBe(null);s=end(s);expect(s.gameId).toBe('maze');expect(s.pageId).toBe('maze-menu');
 });
 it('dispatches every known code without unlock flags and rejects unknown codes',()=>{
  const d=fixture();for(const [code,id] of Object.entries(d.codes)){let s=end(createExtras('archive',1));for(const digit of code)s=act(s,Number(digit)+1);s=end(s);expect(s.gameId).toBe(id);}
  let s=end(createExtras('archive',1));for(let i=0;i<4;i++)s=act(s,1);s=end(s);expect(s.pageId).toBe('invalid-code');expect(end(s).exit).toBe('main-menu');
 });
 it('distinguishes keypad Menu from mini-game Quit',()=>{
  expect(act(end(createExtras('archive',1)),11).exit).toBe('main-menu');
  let s=createExtras('archive',1);s={...s,pageId:'whack-menu',gameId:'whack'};s=act(s,1);expect(s.pageId).toBe('archive-intro');expect(end(s).code).toBe('');
 });
 it('rejects stale, duplicate, buffered and out-of-interval activations',()=>{
  const s=createExtras('instructions',2),d=fixture();const event={type:'ACTIVATE',token:2,controlId:1,time:.2} as ExtraEvent;
  expect(reduceExtras(d,s,event)).toBe(s);const r=ready(s);for(const e of [{...event,token:1},{...event,time:0},{...event,time:10},{...event,time:NaN}])expect(reduceExtras(d,r,e)).toBe(r);
  const next=reduceExtras(d,r,event);expect(reduceExtras(d,next,event)).toBe(next);expect(reduceExtras(d,r,{type:'SCENE_WAITING',token:2}).ready).toBe(false);
 });
 it('preserves compatibility context and resets on the original entry guard',()=>{
  let s=createExtras('instructions',1,false);s={...s,context:{...s.context,guardMarker:5,selectionSeed:5}};expect(act(s,1).exit).toBe('restart');
  s=createExtras('archive',1,false);s=end(s);for(const digit of '7523')s=act(s,Number(digit)+1);s=end(s);expect(s.context.randomized).toBe(false);
 });
 it('uses the source neighbour graph and activates automatic destinations without restarting ordinary focus moves',()=>{
  const d=fixture(),p=d.pages.find(p=>p.id==='instructions-choice')!;
  p.controls[0].neighbours.right=2;
  let s=ready(createExtras('instructions',8),d);
  const moved=reduceExtras(d,s,{type:'MOVE',token:8,direction:'right',time:.2});expect(moved.focus).toBe(2);expect(moved.sceneToken).toBe(8);
  p.controls[1].autoActivate=true;p.controls[1].variants[0].action={type:'page',page:'whack-help'};
  s=reduceExtras(d,s,{type:'MOVE',token:8,direction:'right',time:.2});expect(s.pageId).toBe('whack-help');expect(s.ready).toBe(false);
 });
 it('resolves adjacent action intervals at their exact boundary',()=>{
  const d=fixture(),c=d.pages[0].controls[0],v=c.variants[0];
  c.variants=[{...v,startTicks:0,endTicks:9000,action:{type:'page',page:'whack-help'}},{...v,startTicks:9000,endTicks:18000,action:{type:'main-menu'}}];
  const s=ready(createExtras('instructions',3),d);
  expect(reduceExtras(d,s,{type:'ACTIVATE',token:3,controlId:1,time:.099}).pageId).toBe('whack-help');
  expect(reduceExtras(d,s,{type:'ACTIVATE',token:3,controlId:1,time:.1}).exit).toBe('main-menu');
 });
 it('applies the source restart guard on Main Menu and mini-game Quit returns',()=>{
  const d=fixture();let s=createExtras('instructions',7);s={...s,context:{...s.context,guardMarker:3,selectionSeed:3}};expect(act(s,3,.2,d).exit).toBe('restart');
  s={...s,pageId:'whack-menu',gameId:'whack'};expect(act(s,1,.2,d).exit).toBe('restart');
 });
 it('honours an authored playback stop and ignores further scene or menu input',()=>{
  const d=fixture();d.pages.find(p=>p.id==='whack-help')!.after={type:'stop'};
  let s={...createExtras('archive',1),pageId:'whack-help'};s=end(s,d);expect(s.stopped).toBe(true);expect(s.ready).toBe(false);
  expect(reduceExtras(d,s,{type:'SCENE_READY',token:s.sceneToken})).toBe(s);
 });
 it('preserves the media instance for an authored selection-only button',()=>{
  const d=fixture();d.pages[0].controls[1].variants[0].action={type:'focus',controlId:1};
  const s=ready(createExtras('instructions',9)),next=act(s,2,.2,d);expect(next.focus).toBe(1);expect(next.sceneToken).toBe(9);expect(next.ready).toBe(true);
 });
 it('validates complete gateway data and rejects missing or inconsistent records',()=>{
  const d=fixture();expect(()=>validateExtrasData(d,'source')).not.toThrow();
  for(const changed of [{...d,sourceFingerprint:'other'},{...d,pages:d.pages.filter(p=>p.id!=='keypad-2')},{...d,codes:{...d.codes,'7523':'absent'}},{...d,scenes:[]},{...d,subtitles:[{...d.subtitles[0],endTicks:0}]}])expect(()=>validateExtrasData(changed,'source')).toThrow();
 });
});
