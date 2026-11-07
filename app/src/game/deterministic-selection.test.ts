import {expect,test} from 'vitest';
import {selectQuestion} from './selection';
import {createGame,reduceGame} from './progression';
import {gameFixture} from './fixtures/game';

test('legacy selection increments the previous effective variant without an initial random draw',()=>{
 const d=gameFixture(),draw=()=>{throw new Error('unexpected random draw');};
 for(const [variant,next] of [[0,2],[1,2],[2,3],[3,4],[4,2],[5,2],[6,2]]){
  const r=selectQuestion(d.levels[0],{usedMask:0,candidateMask:1,variant},draw,false);expect(r.state.variant).toBe(next);
 }
});
test('legacy selection retains the source unconditional fallback draw',()=>{
 const data={selection:{'4:1':[{questionId:'a',introScenes:[],variant:5},{questionId:'b',introScenes:[],variant:6}]}};
 let draws=0;expect(selectQuestion(data,{usedMask:0,candidateMask:1,variant:3},()=>{draws++;return .9;},false).questionId).toBe('b');expect(draws).toBe(1);
});
test('default randomized selection is unchanged and legacy mode carries variant across levels',()=>{
 const d=gameFixture();expect(selectQuestion(d.levels[0],{usedMask:0,candidateMask:1,variant:4},()=>0).state.variant).toBe(2);
 d.randomized=false;let s={...createGame(d),phase:'ending' as const,activeScene:'outro',ready:true,destination:'next-level' as const,selection:{usedMask:1,candidateMask:1,variant:2}};
 const next=reduceGame(d,s,{type:'SCENE_ENDED',token:s.sceneToken},()=>{throw new Error('legacy initial draw');});
 expect(next.levelIndex).toBe(1);expect(next.selection.variant).toBe(3);
});
