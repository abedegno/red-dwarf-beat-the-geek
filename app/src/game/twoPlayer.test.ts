import {expect,test} from 'vitest';
import {gameFixture} from './fixtures/game';
import {MODE_IDS} from './modes';
import type {PresenterLibrary} from './presenters';
import {createTwoPlayerGame,reduceTwoPlayerGame,activeTwoPlayerData,type TwoPlayerData,type TwoPlayerState} from './twoPlayer';
import {currentQuestion} from './progression';

function fixture(){
 const games=Object.fromEntries(MODE_IDS.map(id=>[id,gameFixture()])) as PresenterLibrary['games'];
 const library:PresenterLibrary={games,presenterGames:{norman:games,hattie:games},controls:{viewer:games.viewer.entry.menus[0],geek:games.geek.entry.menus[0],'general-knowledge':games['general-knowledge'].entry.menus[0]},labels:{viewer:'Viewer',geek:'Geek','general-knowledge':'General Knowledge'}};
 const menu=games.viewer.entry.menus[0];
 const metadata:TwoPlayerData={schemaVersion:1,sourceFingerprint:'fixture',main:menu,menus:[library.controls,library.controls],setupOptions:[['setup']],scenes:[],
  levels:games.viewer.levels.map((l,i)=>({intros:{'1':['level-intro'],'2':['level-intro']},closings:{'1':['closing'],'2':['closing']},turns:[['turn-1'],['turn-2']],
   scorecards:[0,1].map(player=>Object.fromEntries(Object.keys(l.endings).map(key=>{
    const [score,total]=key.split(':');return [`${score}:${total}`,{scenes:[`card-${player}`],destination:i===7&&+total===48?'bonus':player===0?'next-player':i===7?'complete':'next-level',nextCandidateMask:1,nextOrderingRepeatOffset:player===0?2:5}];
   }))) as TwoPlayerData['levels'][number]['scorecards']})),
  bonuses:[0,1].map(player=>Object.fromEntries(MODE_IDS.map(mode=>[mode,games[mode].bonuses.map(b=>({...b,correctChoice:b.question.correctChoice!,correct:{...b.correct,destination:player===0?'next-player':'complete'},wrong:{...b.wrong,destination:player===0?'next-player':'complete'}}))]))) as TwoPlayerData['bonuses']};
 return {library,metadata};
}
function harness(){const {library,metadata}=fixture();let s=createTwoPlayerGame(library,metadata,10);
 const send=(e:Parameters<typeof reduceTwoPlayerGame>[3])=>{s=reduceTwoPlayerGame(library,metadata,s,e,()=>0);return s;};
 const ready=()=>send({type:'SCENE_READY',token:s.sceneToken});
 const tick=()=>{ready();const g=s.currentPresentation?.gate;return g?.scene===s.activeScene?send({type:'CONTINUE',token:s.sceneToken,time:0}):send({type:'SCENE_ENDED',token:s.sceneToken});};
 const choose=(modeId:typeof MODE_IDS[number])=>{ready();send({type:'CHOOSE_MODE',token:s.sceneToken,time:0,modeId});};
 return {library,metadata,send,ready,tick,choose,get s(){return s;}};
}
test('twelve alternating questions share used slots and credit only the answering player',()=>{
 const h=harness();h.choose('viewer');h.choose('viewer');const turns:number[]=[],ids:string[]=[];
 for(let guard=0;guard<300&&h.s.stage!=='closing';guard++){
  if(h.s.phase==='question'){
   turns.push(h.s.activePlayer);ids.push(h.s.questionId!);h.ready();h.send({type:'ANSWER',token:h.s.sceneToken,time:0,choiceId:h.s.activePlayer===0?'A':'B'});
  }else h.tick();
 }
 expect(turns).toEqual([0,1,0,1,0,1,0,1,0,1,0,1]);expect(new Set(ids).size).toBe(12);
 expect(h.s.scores).toEqual([6,0]);expect(h.s.roundScores).toEqual([6,0]);
});
test('mixed modes have separate selection banks and scorecards preserve next-level repeat carry',()=>{
 const h=harness();h.choose('viewer');h.choose('geek');let guard=0;
 while(h.s.levelIndex===0&&guard++<300){
  if(h.s.phase==='question'){h.ready();h.send({type:'ANSWER',token:h.s.sceneToken,time:0,choiceId:'A'});}else h.tick();
 }
 expect(h.s.levelIndex).toBe(1);expect(h.s.scores).toEqual([6,6]);expect(h.s.roundScores).toEqual([0,0]);expect(h.s.orderingRepeatOffset).toBe(5);
 expect(h.s.usedMasks).toEqual({'general-knowledge':0,viewer:0,geek:0});
});
test('both perfect players receive bonuses in order and complete with independent totals',()=>{
 const h=harness();h.choose('viewer');h.choose('geek');const bonuses:number[]=[];
 for(let guard=0;guard<4000&&h.s.phase!=='complete';guard++){
  if(h.s.phase==='question'||h.s.phase==='bonus'){
   const q=currentQuestion(activeTwoPlayerData(h.library,h.metadata,h.s),h.s)!;
   if(h.s.phase==='bonus')bonuses.push(h.s.activePlayer);
   h.ready();h.send({type:'ANSWER',token:h.s.sceneToken,time:0,choiceId:q.correctChoice!});
  }else h.tick();
 }
 expect(h.s.phase).toBe('complete');expect(h.s.scores).toEqual([48,48]);expect(bonuses).toEqual([0,1]);
});
test('mode choices require readiness, current token and active interval',()=>{
 const h=harness(),s=h.s;
 expect(h.send({type:'CHOOSE_MODE',modeId:'geek',token:s.sceneToken,time:0})).toBe(s);
 h.ready();const ready=h.s;
 expect(h.send({type:'CHOOSE_MODE',modeId:'geek',token:s.sceneToken-1,time:0})).toBe(ready);
 expect(h.send({type:'CHOOSE_MODE',modeId:'geek',token:s.sceneToken,time:100})).toBe(ready);
});
test('player one bonus expiry still allows player two bonus and late answers cannot steal a turn',()=>{
 const h=harness();h.choose('viewer');h.choose('geek');const bonuses:number[]=[];
 for(let guard=0;guard<4000&&h.s.phase!=='complete';guard++){
  if(h.s.phase==='question'||h.s.phase==='bonus'){
   const q=currentQuestion(activeTwoPlayerData(h.library,h.metadata,h.s),h.s)!;
   if(h.s.phase==='bonus'){
    bonuses.push(h.s.activePlayer);h.ready();h.send({type:'SCENE_ENDED',token:h.s.sceneToken});
   }else{
    h.ready();const old=h.s.sceneToken;
    h.send({type:'ANSWER',token:old,time:0,choiceId:q.correctChoice!});const after=h.s;
    expect(h.send({type:'ANSWER',token:old,time:0,choiceId:q.correctChoice!})).toBe(after);
   }
  }else h.tick();
 }
 expect(h.s.phase).toBe('complete');expect(h.s.scores).toEqual([48,48]);expect(bonuses).toEqual([0,1]);
});
test('ordering repeat carry survives a player change and resets only on expiry',()=>{
 const h=harness();
 for(const mode of MODE_IDS){const l=h.library.games[mode].levels[0];for(const q of l.questions){q.expiry='timeout';q.promptPlays=4;}for(const key of Object.keys(l.timeouts))l.timeouts[key]=[{feedback:['feedback'],nextCandidateMask:2}];}
 h.s.orderingRepeatOffset=3;h.choose('viewer');h.choose('geek');
 while(h.s.phase!=='question')h.tick();h.ready();h.send({type:'ANSWER',token:h.s.sceneToken,time:0,choiceId:'A'});
 while(h.s.phase!=='question')h.tick();expect(h.s.activePlayer).toBe(1);expect(h.s.orderingRepeatOffset).toBe(3);
 h.tick();expect(h.s.phase).toBe('feedback');expect(h.s.orderingRepeatOffset).toBe(0);
 while(h.s.phase!=='question')h.tick();expect(h.s.activePlayer).toBe(0);
 for(let i=1;i<=3;i++){h.tick();expect(h.s.phase).toBe('question');expect(h.s.orderingRepeatOffset).toBe(i);}
 h.tick();expect(h.s.phase).toBe('feedback');expect(h.s.orderingRepeatOffset).toBe(0);
});
test('legacy turns carry the effective variant between players and fixed setup consumes no draw',()=>{
 const {library,metadata}=fixture();for(const game of Object.values(library.games))game.randomized=false;
 let s=createTwoPlayerGame(library,metadata,10);const draw=()=>{throw new Error('unexpected legacy random draw');};
 const send=(e:Parameters<typeof reduceTwoPlayerGame>[3])=>{s=reduceTwoPlayerGame(library,metadata,s,e,draw);};
 for(let i=0;i<2;i++){send({type:'SCENE_READY',token:s.sceneToken});send({type:'CHOOSE_MODE',token:s.sceneToken,time:0,modeId:i===0?'viewer':'geek'});}
 for(let n=0;n<20&&s.phase!=='question';n++){send({type:'SCENE_READY',token:s.sceneToken});send({type:'SCENE_ENDED',token:s.sceneToken});}
 expect(s.selection.variant).toBe(2);send({type:'SCENE_READY',token:s.sceneToken});send({type:'ANSWER',token:s.sceneToken,time:0,choiceId:'A'});
 for(let n=0;n<20&&s.phase!=='question';n++){send({type:'SCENE_READY',token:s.sceneToken});send({type:'SCENE_ENDED',token:s.sceneToken});}
 expect(s.activePlayer).toBe(1);expect(s.selection.variant).toBe(3);
});
