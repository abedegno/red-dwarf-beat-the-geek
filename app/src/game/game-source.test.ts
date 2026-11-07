import { dataPath } from '../../test/data';
import { readFileSync } from 'node:fs';
import { expect,test } from 'vitest';
import { createGame,reduceGame,currentQuestion } from './progression';
import type { GameData,GameState,GameEvent,ChoiceId } from './types';
const data=JSON.parse(readFileSync(dataPath('public/game.json'),'utf8')) as GameData;

test('complete real-data games cover all304 questions, score paths and both perfect bonuses',()=>{
  const visited=new Set<string>(),bonuses=new Set<string>(),scenes=new Set(data.scenes.map(s=>s.id));
  for(let seed=1;seed<=100;seed++)for(const outcome of ['correct','wrong','mixed'] as const){
    let random=seed,state=createGame(data),answers=0;
    const draw=()=>{random=(Math.imul(random,1664525)+1013904223)>>>0;return random/4294967296;};
    const send=(event:GameEvent)=>{state=reduceGame(data,state,event,draw);};
    send({type:'START'});
    for(let step=0;step<1500 && state.phase!=='complete';step++){
      if(state.activeScene)expect(scenes.has(state.activeScene)).toBe(true);
      send({type:'SCENE_READY',token:state.sceneToken});
      const s=state as GameState;
      if(s.phase==='menu'){
        const windows=data.entry.menus[s.menuIndex].windows;
        const w=windows[Math.floor(draw()*windows.length)];
        const end=Math.min(w.endTicks/90000,data.scenes.find(scene=>scene.id===s.activeScene)!.durationSeconds-.04);
        send({type:'MENU_CHOOSE',token:s.sceneToken,time:w.startTicks/90000+draw()*(end-w.startTicks/90000)});
      } else if(s.phase==='question' || s.phase==='bonus'){
        const q=currentQuestion(data,s)!;visited.add(q.id);
        if(s.phase==='bonus')bonuses.add(s.bonusId!);
        const correct=outcome==='correct' || outcome==='mixed' && answers%2===0;
        const choiceId=q.kind==='sequence'?(correct?q.correctSequence[s.chosenAnswers.length]:'A'):
          (correct?q.correctChoice!:q.choices.find(c=>c.id!==q.correctChoice)!.id);
        const windows=q.windows.filter(w=>w.choiceId===choiceId && w.startTicks/90000<q.durationSeconds-.04);
        const w=windows[Math.floor(draw()*windows.length)];
        const end=Math.min(w.endTicks/90000,q.durationSeconds-.04);
        send({type:'ANSWER',token:s.sceneToken,time:w.startTicks/90000+draw()*(end-w.startTicks/90000),choiceId});
        if(state.phase!=='question' && s.phase==='question')answers++;
      } else if(s.currentPresentation?.gate?.scene===s.activeScene){
        const w=s.currentPresentation.gate.control.windows[0];
        send({type:'CONTINUE',token:s.sceneToken,time:w.startTicks/90000+.001});
      } else send({type:'SCENE_ENDED',token:s.sceneToken});
    }
    expect(state.phase).toBe('complete');expect(answers).toBe(48);
    expect(state.totalScore).toBe(outcome==='correct'?48:outcome==='wrong'?0:24);
  }
  expect([...visited].filter(id=>id.startsWith('gk-l')).length).toBe(304);
  expect(bonuses).toEqual(new Set(['perfect-bonus-low','perfect-bonus-high']));
});

test('generated source data retains304 verified prompts, authored expiry and original score-audio groups',()=>{
  expect(data.levels.map(l=>l.questions.length)).toEqual(Array(8).fill(38));
  expect(data.levels[0].questions.find(q=>q.id==='gk-l1-006')!.windows.filter(w=>w.choiceId==='A').map(w=>w.startTicks)).toEqual([0,270000,540000,810000]);
  expect(data.levels[1].questions.find(q=>q.id==='gk-l2-112')!.expiry).toBe('loop');
  expect(data.levels[3].questions.find(q=>q.id==='gk-l4-118')!.expiry).toBe('timeout');
  for(const level of data.levels)for(let score=0;score<=6;score++){
    const path=level.endings[`${score}:${score}:1`];
    const card=path.scenes.map(id=>data.scenes.find(s=>s.id===id)!).find(s=>/^s\d+t-/.test(s.id))!;
    expect(card.audioVariant).toBe(score<=2?0:score<=4?1:2);
  }
});
