import { dataPath } from '../../test/data';
import { readFileSync } from 'node:fs';
import { expect, test } from 'vitest';
import { createRound, reduceRound } from './round';
import type { RoundData, RoundState } from './types';

const data=JSON.parse(readFileSync(dataPath('public/round.json'),'utf8')) as RoundData;

function sourceRound(seed:number,correct:boolean) {
  let n=seed;
  const draw=()=>{n=(Math.imul(n,1664525)+1013904223)>>>0;return n/4294967296;};
  let state=createRound(data);
  const send=(event:Parameters<typeof reduceRound>[2])=>{state=reduceRound(data,state,event,draw);};
  send({type:'START'});
  const visited=new Set<string>();
  for(let i=0;i<500 && state.phase!=='complete';i++) {
    if(state.activeScene)expect(data.scenes.some(s=>s.id===state.activeScene)).toBe(true);
    send({type:'SCENE_READY',token:state.sceneToken});
    const current=state as RoundState;
    if(current.phase==='menu')send({type:'MENU_CHOOSE',token:current.sceneToken,time:3+draw()*20});
    else if(current.phase==='question') {
      const q=data.questions.find(q=>q.id===current.questionId)!;
      visited.add(q.id);
      const choiceId=q.kind==='sequence'
        ?(correct?q.correctSequence[current.chosenAnswers.length]:'A')
        :(correct?q.correctChoice!:q.choices.find(c=>c.id!==q.correctChoice)!.id);
      send({type:'ANSWER',token:current.sceneToken,time:draw()*q.durationSeconds,choiceId});
    } else if(current.phase==='ending' && data.feedback.endings[current.endingKey!].loopScene===current.activeScene)
      send({type:'CONTINUE',token:current.sceneToken});
    else send({type:'SCENE_ENDED',token:current.sceneToken});
  }
  expect(state.phase).toBe('complete');
  expect(state.questionNumber).toBe(6);
  expect(state.score).toBe(correct?6:0);
  return visited;
}

test('normalized source paths support complete correct and wrong native rounds across selection variants',()=>{
  const visited=new Set<string>();
  for(let seed=1;seed<=80;seed++)for(const correct of [true,false])
    for(const id of sourceRound(seed,correct))visited.add(id);
  expect(visited.has('gk-l1-043')).toBe(true);
  expect(visited.size).toBe(38);
});

test('source ending voice variants follow the observed score thresholds',()=>{
  for(let score=0;score<=6;score++){
    const ending=data.feedback.endings[`${score}:1`];
    const spokenScore=ending.scenes.map(id=>data.scenes.find(s=>s.id===id)!).find(s=>s.id.startsWith('s03t-'))!;
    expect(spokenScore.audioVariant).toBe(score<=2?0:score<=4?1:2);
  }
});
