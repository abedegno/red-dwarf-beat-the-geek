import { describe, expect, test } from 'vitest';
import { createRound, reduceRound } from './round';
import { selectQuestion } from './selection';
import type { RoundData, RoundState, Question } from './types';

function fixture(): RoundData {
  const rect={x:73,y:274,width:441,height:34};
  const questions: Question[] = Array.from({length:16},(_,i)=>({
    id:`q${i}`,kind:'single',text:'A question',correctChoice:'A',correctSequence:[],
    choices:('ABCD'.split('') as ('A'|'B'|'C'|'D')[]).map(id=>({id,label:id,rect,highlightSrc:''})),
    promptScene:`q${i}`,revealScene:null,durationSeconds:12.04,revealSeconds:3,
    windows:['A','B','C','D'].flatMap(choiceId=>[
      {startTicks:0,endTicks:54000,choiceId:choiceId as 'A',nextCandidateMask:1},
      {startTicks:54000,endTicks:1083600,choiceId:choiceId as 'A',nextCandidateMask:4}]),
  }));
  const selection: RoundData['selection']={},answers:Record<string,string[]>={},endings:RoundData['feedback']['endings']={};
  for(let v=2;v<=6;v++)for(let bit=0;bit<16;bit++){
    const mask=1<<bit;
    if(v<=4)selection[`${v}:${mask}`]=[{questionId:`q${bit}`,introScenes:[],variant:v}];
    for(const outcome of ['correct','wrong'])for(let next=0;next<16;next++)answers[`${v}:${mask}:${outcome}:${1<<next}`]=['feedback'];
  }
  for(let score=0;score<=6;score++)for(let bit=0;bit<16;bit++)endings[`${score}:${1<<bit}`]={scenes:['end'],loopScene:null};
  return {schemaVersion:1,sourceFingerprint:'fixture',questions,selection,
    scenes:[...questions.map(q=>q.promptScene),'menu','feedback','end'].map(id=>({id,src:'',durationSeconds:1,kind:'clip',audioVariant:null})),
    feedback:{answers,endings},entry:{boot:[],setupScenes:[],roundIntros:{'1':[]},
      menus:[{id:'holly',scene:'menu',label:'Holly',rect,highlightSrc:'',windows:[{startTicks:0,endTicks:999999,candidateMask:1}]}]}};
}
const draw=()=>0;
function event(data:RoundData,s:RoundState,type:'SCENE_READY'|'SCENE_ENDED'){
  return reduceRound(data,s,{type,token:s.sceneToken},draw);
}
function begin(data:RoundData){
  let s=reduceRound(data,createRound(data),{type:'START'},draw);
  s=event(data,s,'SCENE_READY');
  s=reduceRound(data,s,{type:'MENU_CHOOSE',token:s.sceneToken,time:0},draw);
  return event(data,s,'SCENE_READY');
}
function finishMedia(data:RoundData,s:RoundState){
  for(let i=0;i<20 && s.phase!=='question' && s.phase!=='complete';i++){
    s=event(data,s,'SCENE_READY');s=event(data,s,'SCENE_ENDED');
  }
  return s.phase==='question'?event(data,s,'SCENE_READY'):s;
}

describe('native round rules',()=>{
  for(const [name,choices,want] of [['correct','AAAAAA',6],['wrong','BBBBBB',0],['mixed','ABABAB',3]] as const){
    test(`six ${name} answers complete the round with score ${want}`,()=>{
      const data=fixture();let s=begin(data);
      for(const choiceId of choices){
        expect(s.phase).toBe('question');
        s=reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId:choiceId as 'A'|'B'},draw);
        s=finishMedia(data,s);
      }
      expect(s.phase).toBe('complete');expect(s.score).toBe(want);
    });
  }
  test('double clicks and old media completion cannot score or skip a new scene',()=>{
    const data=fixture();const start=begin(data);const token=start.sceneToken;
    const answered=reduceRound(data,start,{type:'ANSWER',token,time:0,choiceId:'A'},draw);
    const double=reduceRound(data,answered,{type:'ANSWER',token,time:0,choiceId:'A'},draw);
    expect(double).toEqual(answered);
    expect(reduceRound(data,double,{type:'SCENE_ENDED',token},draw)).toEqual(answered);
    expect(answered.score).toBe(1);
  });
  test('unanswered presentation loops without changing question or score',()=>{
    const data=fixture();let s=begin(data);const id=s.questionId;
    for(let i=0;i<3;i++){s=event(data,s,'SCENE_ENDED');s=event(data,s,'SCENE_READY');}
    expect(s.questionId).toBe(id);expect(s.questionNumber).toBe(1);expect(s.score).toBe(0);
  });
  test('buffering gates answers until the current scene is playing again',()=>{
    const data=fixture();let s=begin(data);
    s=reduceRound(data,s,{type:'SCENE_WAITING',token:s.sceneToken},draw);
    expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId:'A'},draw)).toEqual(s);
    s=event(data,s,'SCENE_READY');
    expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId:'A'},draw).score).toBe(1);
  });
  test('media time selects the original candidate window',()=>{
    const data=fixture(),s=begin(data);
    expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:1,choiceId:'A'},draw).nextCandidateMask).toBe(4);
  });
  test('ordering question waits for all four selections',()=>{
    const data=fixture();data.questions[0].kind='sequence';data.questions[0].correctChoice=null;
    data.questions[0].correctSequence=['B','D','A','C'];let s=begin(data);
    for(const [i,choiceId] of (['B','D','A','C'] as const).entries()){
      s=reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:0,choiceId},draw);
      expect(s.score).toBe(i===3?1:0);
      if(i<3){expect(s.phase).toBe('question');s=event(data,s,'SCENE_READY');}
    }
    expect(s.phase).toBe('feedback');
  });
  test('reset does not reuse an old playback token',()=>{
    const data=fixture(),s=begin(data);
    const reset=reduceRound(data,s,{type:'RESET'},draw);
    const started=reduceRound(data,reset,{type:'START'},draw);
    expect(started.sceneToken).toBeGreaterThan(s.sceneToken);
  });
});

describe('source selection semantics',()=>{
  test('duplicate high-bit candidate wraps to 2 and advances variant as the DVD does',()=>{
    const result=selectQuestion(fixture(),{usedMask:32768,candidateMask:32768,variant:0},draw);
    expect(result.state.candidateMask).toBe(2);expect(result.state.variant).toBe(3);
    expect(result.state.usedMask).toBe(32770);
  });
  test('slot 8 / variant 3 selects the recorded source question 34',()=>{
    const data=fixture();data.selection['3:8']=[{questionId:'gk-l1-034',introScenes:[],variant:3}];
    const result=selectQuestion(data,{usedMask:0,candidateMask:8,variant:0},()=>.4);
    expect(result.questionId).toBe('gk-l1-034');
  });
});


test('expired answer and menu selection intervals reject activation',()=>{
  const data=fixture(),s=begin(data);
  expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:12.04,choiceId:'A'},draw)).toEqual(s);
  let menu=reduceRound(data,createRound(data),{type:'START'},draw);
  menu=event(data,menu,'SCENE_READY');
  expect(reduceRound(data,menu,{type:'MENU_CHOOSE',token:menu.sceneToken,time:12},draw)).toEqual(menu);
});

test('authored three-second boundary changes candidate at presentation time',()=>{
  const data=fixture(),s=begin(data);
  for(const q of data.questions)for(const w of q.windows){
    if(w.startTicks===0)w.endTicks=270000;else w.startTicks=270000;
  }
  expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:2.99,choiceId:'A'},draw).nextCandidateMask).toBe(1);
  expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:3,choiceId:'A'},draw).nextCandidateMask).toBe(4);
  expect(reduceRound(data,s,{type:'ANSWER',token:s.sceneToken,time:3.01,choiceId:'A'},draw).nextCandidateMask).toBe(4);
});
