import {expect,test} from 'vitest';
import {gameFixture} from './fixtures/game';
import {createModeGame,reduceModeGame,type GameLibrary,type ModeId,type ModeState} from './modes';
function library():GameLibrary{
  const games=Object.fromEntries(['general-knowledge','viewer','geek'].map((id,index)=>{
    const game=gameFixture(),menu=game.entry.menus[0];
    game.entry.menus=['main','player-type','holly'].map(id=>({...menu,id}));
    for(const level of game.levels)for(const q of level.questions){q.text=id;q.correctChoice=(['A','B','C'] as const)[index];}
    return [id,game];
  })) as GameLibrary['games'];
  const controls=Object.fromEntries(Object.keys(games).map(id=>[id,{...games[id as ModeId].entry.menus[1],windows:[{startTicks:0,endTicks:90000}]}])) as GameLibrary['controls'];
  return {games,controls,labels:{'general-knowledge':'General Knowledge',viewer:'Viewer',geek:'Geek'}};
}
const draw=()=>0;
function ready(lib:GameLibrary,s:ModeState){return reduceModeGame(lib,s,{type:'SCENE_READY',token:s.sceneToken},draw);}
function enter(lib:GameLibrary){
  let s=reduceModeGame(lib,createModeGame(lib),{type:'START'},draw);s=ready(lib,s);
  return ready(lib,reduceModeGame(lib,s,{type:'MENU_CHOOSE',token:s.sceneToken,time:0},draw));
}
for(const modeId of ['general-knowledge','viewer','geek'] as const)test(`source menu chooses ${modeId} and uses its question correctness`,()=>{
  const lib=library();let s=enter(lib);
  s=reduceModeGame(lib,s,{type:'CHOOSE_MODE',modeId,token:s.sceneToken,time:0},draw);
  expect(s.modeId).toBe(modeId);expect(s.menuIndex).toBe(2);
  s=ready(lib,s);s=reduceModeGame(lib,s,{type:'MENU_CHOOSE',token:s.sceneToken,time:0},draw);
  s=ready(lib,s);expect(s.phase).toBe('question');
  const q=lib.games[modeId].levels[0].questions[0];expect(q.text).toBe(modeId);
  s=reduceModeGame(lib,s,{type:'ANSWER',choiceId:q.correctChoice!,token:s.sceneToken,time:0},draw);
  expect(s.totalScore).toBe(1);
});
test('stale, duplicate, expired and out-of-menu choices cannot change selected game',()=>{
  const lib=library(),idle=createModeGame(lib),s=enter(lib),token=s.sceneToken;
  expect(reduceModeGame(lib,idle,{type:'CHOOSE_MODE',modeId:'viewer',token:0,time:0},draw)).toBe(idle);
  expect(reduceModeGame(lib,s,{type:'CHOOSE_MODE',modeId:'viewer',token:token-1,time:0},draw)).toBe(s);
  expect(reduceModeGame(lib,s,{type:'CHOOSE_MODE',modeId:'viewer',token,time:1},draw)).toBe(s);
  const chosen=reduceModeGame(lib,s,{type:'CHOOSE_MODE',modeId:'viewer',token,time:0},draw);
  expect(reduceModeGame(lib,chosen,{type:'CHOOSE_MODE',modeId:'geek',token,time:0},draw)).toBe(chosen);
});
test('reset clears mode, score and mask and invalidates old media events',()=>{
  const lib=library();let s=enter(lib);
  s=reduceModeGame(lib,s,{type:'CHOOSE_MODE',modeId:'geek',token:s.sceneToken,time:0},draw);
  const token=s.sceneToken;s={...s,totalScore:24,roundScore:3,selection:{usedMask:32767,candidateMask:32768,variant:4}};
  const reset=reduceModeGame(lib,s,{type:'RESET'},draw);
  expect(reset.modeId).toBe('general-knowledge');expect(reset.totalScore).toBe(0);expect(reset.selection.usedMask).toBe(0);
  expect(reset.sceneToken).toBeGreaterThan(token);
  expect(reduceModeGame(lib,reset,{type:'SCENE_ENDED',token},draw)).toBe(reset);
});
