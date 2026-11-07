import { dataPath } from '../../test/data';
import { readFileSync } from 'node:fs';
import { expect,test } from 'vitest';
import {currentQuestion} from './progression';
import {MODE_IDS} from './modes';
import {PRESENTER_IDS,createPresenterGame,reducePresenterGame,type PresenterLibrary,type PresenterEvent} from './presenters';
import type { GameState } from './types';
const catalog=JSON.parse(readFileSync(dataPath('public/catalog.json'),'utf8'));
const games=Object.fromEntries(MODE_IDS.map(id=>[id,JSON.parse(readFileSync(dataPath(`public${catalog.hattieModes[id].dataPath}`),'utf8'))])) as PresenterLibrary['games'];
const normanGames=Object.fromEntries(MODE_IDS.map(id=>[id,JSON.parse(readFileSync(dataPath(`public${catalog.modes[id].dataPath}`),'utf8'))])) as PresenterLibrary['games'];
const library:PresenterLibrary={games:normanGames,presenterGames:{norman:normanGames,hattie:games},controls:Object.fromEntries(MODE_IDS.map(id=>[id,catalog.modes[id].control])) as PresenterLibrary['controls'],labels:Object.fromEntries(MODE_IDS.map(id=>[id,catalog.modes[id].label])) as PresenterLibrary['labels']};
for(const presenterId of PRESENTER_IDS)for(const mode of MODE_IDS){
const data=library.presenterGames[presenterId][mode];

test(`${presenterId} ${mode}: complete real-data games cover all304 questions, score paths and both perfect bonuses`,()=>{
  const visited=new Set<string>(),bonuses=new Set<string>(),scenes=new Set(data.scenes.map(s=>s.id));
  for(let seed=1;seed<=100;seed++)for(const outcome of ['correct','wrong','mixed'] as const){
    let random=seed,state=createPresenterGame(library),answers=0;
    const draw=()=>{random=(Math.imul(random,1664525)+1013904223)>>>0;return random/4294967296;};
    const send=(event:PresenterEvent)=>{state=reducePresenterGame(library,state,event,draw);};
    send({type:'START'});
    for(let step=0;step<1500 && state.phase!=='complete';step++){
      if(state.activeScene)expect(scenes.has(state.activeScene)).toBe(true);
      send({type:'SCENE_READY',token:state.sceneToken});
      const s=state as GameState;
      if(s.phase==='menu'){
        const windows=data.entry.menus[s.menuIndex].windows;
        const w=windows[Math.floor(draw()*windows.length)];
        const end=Math.min(w.endTicks/90000,data.scenes.find(scene=>scene.id===s.activeScene)!.durationSeconds-.04);
        const time=w.startTicks/90000+draw()*(end-w.startTicks/90000);
        if(s.menuIndex===1)send({type:'CHOOSE_MODE',modeId:mode,token:s.sceneToken,time});
        else if(s.menuIndex===2)send({type:'CHOOSE_PRESENTER',presenterId,token:s.sceneToken,time});
        else send({type:'MENU_CHOOSE',token:s.sceneToken,time});
      } else if(s.phase==='question' || s.phase==='bonus'){
        const q=currentQuestion(data,s)!;visited.add(q.id);
        if(presenterId==='hattie' && s.phase==='question' && s.levelIndex>0 && s.questionNumber===1)expect(s.orderingRepeatOffset).toBe(outcome==='correct'?5:outcome==='wrong'?3:4);
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
  expect([...visited].filter(id=>id.startsWith(`${mode==='general-knowledge'?'gk':mode}-l`)).length).toBe(304);
  expect(bonuses).toEqual(new Set(['perfect-bonus-low','perfect-bonus-high']));
});

}
