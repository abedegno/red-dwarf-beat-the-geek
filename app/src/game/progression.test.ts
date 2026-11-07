import { expect,test } from 'vitest';
import { createGame,reduceGame } from './progression';
import { gameFixture } from './fixtures/game';
import type { GameData,GameState,GameEvent,ChoiceId } from './types';
const draw=()=>0;
function media(data:GameData,s:GameState,type:'SCENE_READY'|'SCENE_ENDED'|'SCENE_WAITING'){
  return reduceGame(data,s,{type,token:s.sceneToken},draw);
}
function advance(data:GameData,s:GameState):GameState {
  for(let i=0;i<100 && !['question','bonus','complete'].includes(s.phase);i++){
    s=media(data,s,'SCENE_READY');
    const gate=s.currentPresentation?.gate;
    s=gate?.scene===s.activeScene?reduceGame(data,s,{type:'CONTINUE',token:s.sceneToken,time:0},draw):media(data,s,'SCENE_ENDED');
  }
  return s.phase==='complete'?s:media(data,s,'SCENE_READY');
}
function begin(data:GameData){
  let s=reduceGame(data,createGame(data),{type:'START'},draw);
  s=media(data,s,'SCENE_READY');
  return advance(data,reduceGame(data,s,{type:'MENU_CHOOSE',token:s.sceneToken,time:0},draw));
}
function answer(data:GameData,s:GameState,correct:boolean){
  const q=s.phase==='bonus'?data.bonuses.find(b=>b.id===s.bonusId)!.question:data.levels[s.levelIndex].questions.find(q=>q.id===s.questionId)!;
  const ids=q.kind==='sequence'?(correct?q.correctSequence:['A','A','A','A'] as ChoiceId[]):[correct?q.correctChoice!:q.choices.find(c=>c.id!==q.correctChoice)!.id];
  for(const choiceId of ids){
    s=reduceGame(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId},draw);
    if(s.phase==='question')s=media(data,s,'SCENE_READY');
  }
  return s;
}
function play(data:GameData,correct:(n:number)=>boolean,finishBonus=true){
  let s=begin(data);
  for(let n=0;n<48;n++){
    expect(s.phase).toBe('question');expect(s.levelIndex).toBe(Math.floor(n/6));
    expect(s.questionNumber).toBe(n%6+1);
    s=answer(data,s,correct(n));
    expect(s.totalScore).toBe(Array.from({length:n+1},(_,i)=>correct(i)?1:0).reduce((a,b)=>a+b,0));
    s=advance(data,s);
  }
  if(s.phase==='bonus' && finishBonus)s=advance(data,answer(data,s,true));
  return s;
}
for(const [label,pattern,want] of [['correct',()=>true,48],['wrong',()=>false,0],['mixed',(n:number)=>n%2===0,24]] as const){
  test(`eight ${label} rounds complete with cumulative score${want}`,()=>{
    const data=gameFixture(),s=play(data,pattern);
    expect(s.phase).toBe('complete');expect(s.totalScore).toBe(want);expect(s.levelIndex).toBe(7);
  });
}
test('new level resets the round mask/score once after the complete outro',()=>{
  const data=gameFixture();let s=begin(data);
  for(let i=0;i<6;i++){s=answer(data,s,true);if(i<5)s=advance(data,s);}
  s=media(data,s,'SCENE_READY');s=media(data,s,'SCENE_ENDED'); // feedback → score
  s=media(data,s,'SCENE_READY');s=media(data,s,'SCENE_ENDED'); // score → gate
  expect(s.activeScene).toBe('gate');expect(s.roundScore).toBe(6);expect(s.totalScore).toBe(6);
  s=media(data,s,'SCENE_READY');const token=s.sceneToken;
  s=reduceGame(data,s,{type:'CONTINUE',token,time:0},draw);
  expect(s.activeScene).toBe('outro');expect(s.levelIndex).toBe(0);
  expect(reduceGame(data,s,{type:'CONTINUE',token,time:0},draw)).toEqual(s);
  s=advance(data,s);expect(s.levelIndex).toBe(1);expect(s.roundScore).toBe(0);expect(s.totalScore).toBe(6);
  expect(s.selection.usedMask).toBe(1);
});
test('duplicate answers and stale ended events cannot score or advance again',()=>{
  const data=gameFixture(),before=begin(data),token=before.sceneToken;
  const after=answer(data,before,true);
  expect(reduceGame(data,after,{type:'ANSWER',token,time:0,choiceId:'A'},draw)).toEqual(after);
  expect(reduceGame(data,after,{type:'SCENE_ENDED',token},draw)).toEqual(after);
  expect(after.totalScore).toBe(1);
});
test('early unanswered loops but a ready late-level question expires once',()=>{
  const data=gameFixture();let s=begin(data);const id=s.questionId;
  s=media(data,s,'SCENE_ENDED');expect(s.questionId).toBe(id);expect(s.totalScore).toBe(0);
  s=media(data,s,'SCENE_READY');
  for(let i=0;i<18;i++)s=advance(data,answer(data,s,true));
  expect(s.levelIndex).toBe(3);expect(s.questionNumber).toBe(1);
  s=media(data,s,'SCENE_WAITING');expect(media(data,s,'SCENE_ENDED')).toEqual(s);
  s=media(data,s,'SCENE_READY');const token=s.sceneToken;
  s=media(data,s,'SCENE_ENDED');expect(s.phase).toBe('feedback');expect(s.totalScore).toBe(18);expect(s.nextCandidateMask).toBe(2);
  expect(reduceGame(data,s,{type:'SCENE_ENDED',token},draw)).toEqual(s);
  s=advance(data,s);expect(s.questionNumber).toBe(2);expect(s.selection.candidateMask).toBe(2);
});
test('ordering selections score only after four and late input is ignored',()=>{
  const data=gameFixture();const q=data.levels[0].questions[0];q.kind='sequence';q.correctChoice=null;q.correctSequence=['B','D','A','C'];
  let s=begin(data);
  expect(reduceGame(data,s,{type:'ANSWER',token:s.sceneToken,time:12.04,choiceId:'B'},draw)).toEqual(s);
  for(const [i,choiceId] of q.correctSequence.entries()){
    s=reduceGame(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId},draw);
    expect(s.totalScore).toBe(i===3?1:0);if(i<3)s=media(data,s,'SCENE_READY');
  }
});
test('perfect bonus wrong/timeout and optional timed Continue preserve total48',()=>{
  const data=gameFixture(),bonus=play(data,()=>true,false);
  expect(bonus.phase).toBe('bonus');expect(bonus.totalScore).toBe(48);
  const wrong=advance(data,answer(data,bonus,false));expect(wrong.phase).toBe('complete');expect(wrong.totalScore).toBe(48);
  const timeout=advance(data,media(data,bonus,'SCENE_ENDED'));expect(timeout.phase).toBe('complete');expect(timeout.totalScore).toBe(48);
  let right=answer(data,bonus,true);right=media(data,right,'SCENE_READY');right=media(data,right,'SCENE_ENDED');
  expect(right.activeScene).toBe('bonus-gate');right=media(data,right,'SCENE_READY');
  expect(reduceGame(data,right,{type:'CONTINUE',token:right.sceneToken,time:30},draw)).toEqual(right);
  right=advance(data,media(data,right,'SCENE_ENDED'));expect(right.phase).toBe('complete');expect(right.totalScore).toBe(48);
});
test('restart invalidates all previous playback tokens',()=>{
  const data=gameFixture(),s=begin(data),token=s.sceneToken;
  const reset=reduceGame(data,s,{type:'RESET'},draw),started=reduceGame(data,reset,{type:'START'},draw);
  expect(started.sceneToken).toBeGreaterThan(token);
  expect(started.totalScore).toBe(0);
  expect(reduceGame(data,started,{type:'SCENE_ENDED',token},draw)).toEqual(started);
});

test('authored repeated prompt expires after four completed plays, including partial ordering input',()=>{
  const data=gameFixture();let s=begin(data);
  const q=data.levels[0].questions[0];q.expiry='timeout';q.promptPlays=4;
  q.kind='sequence';q.correctChoice=null;q.correctSequence=['B','D','A','C'];
  data.levels[0].timeouts['2:1']=[{feedback:['feedback'],nextCandidateMask:2}];
  // Re-enter to select the authored expiry path.
  s=begin(data);
  for(let i=0;i<3;i++){
    s=media(data,s,'SCENE_ENDED');expect(s.phase).toBe('question');s=media(data,s,'SCENE_READY');
  }
  s=reduceGame(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId:'B'},draw);
  s=media(data,s,'SCENE_READY');s=media(data,s,'SCENE_ENDED');
  expect(s.phase).toBe('feedback');expect(s.totalScore).toBe(0);
});

test('ordering repeat allowance carries across answers and score-audio level boundary',()=>{
  const data=gameFixture();let s=begin(data);
  for(let i=0;i<18;i++)s=advance(data,answer(data,s,true));
  expect(s.levelIndex).toBe(3);expect(s.orderingRepeatOffset).toBe(2);
  const q=data.levels[3].questions[0];q.promptPlays=4;q.kind='sequence';q.correctChoice=null;q.correctSequence=['B','D','A','C'];
  s=media(data,s,'SCENE_ENDED');expect(s.phase).toBe('question');expect(s.orderingRepeatOffset).toBe(3);
  s=media(data,s,'SCENE_READY');s=advance(data,answer(data,s,true));
  expect(s.orderingRepeatOffset).toBe(3);
  const next=data.levels[3].questions.find(q=>q.id===s.questionId)!;next.promptPlays=4;
  s=media(data,s,'SCENE_ENDED');expect(s.phase).toBe('feedback');expect(s.orderingRepeatOffset).toBe(0);
});

test('presenter-specific source scorecard carry can expire ordering on its first play',()=>{
 const data=gameFixture();
 for(const level of data.levels)for(const ending of Object.values(level.endings))if(ending.destination==='next-level')ending.nextOrderingRepeatOffset=5;
 let s=begin(data);for(let i=0;i<18;i++)s=advance(data,answer(data,s,true));
 expect(s.levelIndex).toBe(3);expect(s.orderingRepeatOffset).toBe(5);
 const q=data.levels[3].questions.find(q=>q.id===s.questionId)!;q.promptPlays=4;
 s=media(data,s,'SCENE_ENDED');expect(s.phase).toBe('feedback');expect(s.orderingRepeatOffset).toBe(0);
});

test('source repeat carry survives Continue and the following transition clips',()=>{
 const data=gameFixture();for(const p of Object.values(data.levels[0].endings))p.nextOrderingRepeatOffset=5;
 let s=begin(data);for(let i=0;i<6;i++)s=advance(data,answer(data,s,true));
 expect(s.levelIndex).toBe(1);expect(s.orderingRepeatOffset).toBe(5);
});
