import {expect,test} from 'vitest';
import {routeMaze,startMaze} from './maze';
import {gatewayFixture} from './gatewayFixture';
import {createExtras} from './gateway';
import type {ExtrasData} from './types';
function fixture():ExtrasData{
 const d=gatewayFixture();d.maze={entry:{page:'first',focus:8},nodes:{first:{lives:3,docking:1,victory:false},death:{lives:2,docking:1,victory:false},second:{lives:2,docking:2,victory:false},third:{lives:2,docking:3,victory:false},victory:{lives:2,docking:3,victory:true},loss:{lives:0,docking:3,victory:false}}};
 for(const id of Object.keys(d.maze.nodes))d.pages.push({id,scene:'clip',loop:true,focus:1,controls:[],after:null});return d;
}
test('maze begins with three lives and moving on one page keeps its media instance',()=>{
 const d=fixture(),s=startMaze(d,{...createExtras('archive',7),gameId:'maze'});expect(s.maze).toEqual({lives:3,docking:1});expect(s.focus).toBe(8);
 const moved=routeMaze(d,{...s,ready:true},{page:'first',focus:15});expect(moved.sceneToken).toBe(s.sceneToken);expect(moved.focus).toBe(15);expect(moved.ready).toBe(true);
});
test('collision, retry and three docking sections follow their original normalized routes',()=>{
 const d=fixture();let s=startMaze(d,{...createExtras('archive',7),gameId:'maze'});
 for(const [page,lives,docking] of [['death',2,1],['second',2,2],['third',2,3],['loss',0,3]] as const){const old=s.sceneToken;s=routeMaze(d,s,{page,focus:1});expect(s.maze).toEqual({lives,docking});expect(s.sceneToken).toBe(old+1);expect(s.ready).toBe(false);}
 s=routeMaze(d,s,{page:'maze-menu',focus:1});expect(s.maze).toBe(null);s=startMaze(d,s);expect(s.maze?.lives).toBe(3);
});
test('victory changes shared selection mode and menu return retains it',()=>{
 const d=fixture();let s=startMaze(d,createExtras('archive',7));s=routeMaze(d,s,{page:'victory',focus:1});expect(s.context.randomized).toBe(false);
 s=routeMaze(d,s,{page:'maze-menu',focus:1});expect(s.context.randomized).toBe(false);expect(createExtras('archive',s.sceneToken).context.randomized).toBe(true);
});
