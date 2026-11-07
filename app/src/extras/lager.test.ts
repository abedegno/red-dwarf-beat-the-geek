import {expect,test} from 'vitest';
import {startLager,routeLager} from './lager';
import {createExtras,reduceExtras} from './gateway';
import {gatewayFixture} from './gatewayFixture';
import type {ExtrasData} from './types';
function fixture():ExtrasData {
 const d=gatewayFixture();d.lager={entry:'lager-intro',stages:['lager-aim-1'],nodes:{'lager-intro':{stage:0,phase:'intro'},'lager-aim-1':{stage:1,phase:'aim'},'lager-hit-1':{stage:1,phase:'hit'},'lager-fail':{stage:0,phase:'fail'}}};
 for(const id of Object.keys(d.lager.nodes))d.pages.push({id,scene:'clip',loop:false,focus:id==='lager-aim-1'?1:0,controls:[],after:{type:'lager-route',page:id==='lager-intro'?'lager-aim-1':'lager-menu',focus:id==='lager-intro'?1:1}});
 const p=d.pages.find(p=>p.id==='lager-aim-1')!;p.after={type:'lager-route',page:'lager-fail',focus:0};p.controls=[{id:1,label:'Fire',neighbours:{up:1,down:1,left:1,right:1},autoActivate:false,variants:[{startTicks:90000,endTicks:180000,rect:{x:10,y:10,width:20,height:20},highlightSrc:'/media/h.png',action:{type:'lager-route',page:'lager-hit-1',focus:0}},{startTicks:270000,endTicks:360000,rect:{x:40,y:30,width:20,height:20},highlightSrc:'/media/h.png',action:{type:'lager-route',page:'lager-fail',focus:0}}]}];return d;
}
test('only active authored shot windows accept fire, including decoy and exact end boundary',()=>{
 const d=fixture();let s=startLager(d,{...createExtras('archive',1),gameId:'lager'});expect(s.pageId).toBe('lager-intro');s=routeLager(d,s,'lager-aim-1',1);s=reduceExtras(d,s,{type:'SCENE_READY',token:s.sceneToken});
 for(const time of [0,.999,2,2.999,4,NaN])expect(reduceExtras(d,s,{type:'ACTIVATE',token:s.sceneToken,controlId:1,time})).toBe(s);
 expect(reduceExtras(d,s,{type:'ACTIVATE',token:s.sceneToken,controlId:1,time:1}).pageId).toBe('lager-hit-1');expect(reduceExtras(d,s,{type:'ACTIVATE',token:s.sceneToken,controlId:1,time:3}).pageId).toBe('lager-fail');
 expect(reduceExtras(d,s,{type:'SCENE_ENDED',token:s.sceneToken}).pageId).toBe('lager-fail');
});
test('shot transitions reject duplicate/stale and buffered events and retain five-field shared context',()=>{
 const d=fixture();let s=routeLager(d,{...createExtras('archive',1,false),gameId:'lager'},'lager-aim-1',1);const e={type:'ACTIVATE' as const,token:s.sceneToken,controlId:1,time:1};expect(reduceExtras(d,s,e)).toBe(s);s=reduceExtras(d,s,{type:'SCENE_READY',token:s.sceneToken});const next=reduceExtras(d,s,e);expect(next.context).toEqual(s.context);expect(next.lager).toEqual({stage:1,phase:'hit'});expect(reduceExtras(d,next,e)).toBe(next);
 const menu=routeLager(d,next,'lager-menu',1);expect(menu.lager).toBe(null);
});
