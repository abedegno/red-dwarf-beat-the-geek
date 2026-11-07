import { dataPath } from '../../test/data';
import { readFileSync } from 'node:fs';
import { expect,test } from 'vitest';
import {currentQuestion} from './progression';
import {MODE_IDS,createModeGame,reduceModeGame,type GameLibrary,type ModeEvent} from './modes';
import type { GameState } from './types';
const catalog=JSON.parse(readFileSync(dataPath('public/catalog.json'),'utf8'));
const games=Object.fromEntries(MODE_IDS.map(id=>[id,JSON.parse(readFileSync(dataPath(`public${catalog.modes[id].dataPath}`),'utf8'))])) as GameLibrary['games'];
const library:GameLibrary={games,controls:Object.fromEntries(MODE_IDS.map(id=>[id,catalog.modes[id].control])) as GameLibrary['controls'],labels:Object.fromEntries(MODE_IDS.map(id=>[id,catalog.modes[id].label])) as GameLibrary['labels']};
for(const mode of MODE_IDS){
const data=games[mode];

test(`${mode}: complete real-data games cover all304 questions, score paths and both perfect bonuses`,()=>{
  const visited=new Set<string>(),bonuses=new Set<string>(),scenes=new Set(data.scenes.map(s=>s.id));
  for(let seed=1;seed<=100;seed++)for(const outcome of ['correct','wrong','mixed'] as const){
    let random=seed,state=createModeGame(library),answers=0;
    const draw=()=>{random=(Math.imul(random,1664525)+1013904223)>>>0;return random/4294967296;};
    const send=(event:ModeEvent)=>{state=reduceModeGame(library,state,event,draw);};
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
        else send({type:'MENU_CHOOSE',token:s.sceneToken,time});
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
  expect([...visited].filter(id=>id.startsWith(`${mode==='general-knowledge'?'gk':mode}-l`)).length).toBe(304);
  expect(bonuses).toEqual(new Set(['perfect-bonus-low','perfect-bonus-high']));
});

}
