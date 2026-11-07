import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync} from 'node:fs';
import {MODE_IDS,type ModeId} from '../game/modes';
import {PRESENTER_IDS,type PresenterLibrary,type PresenterId} from '../game/presenters';
import type {GameData} from '../game/types';
import {createSession,reduceSession,type SessionLibrary,type SessionEvent} from './session';
const read=(p:string)=>JSON.parse(readFileSync(dataPath(p),'utf8'));
const catalog=read('public/catalog.json');
const presenterGames=Object.fromEntries(PRESENTER_IDS.map(p=>[p,Object.fromEntries(MODE_IDS.map(mode=>[mode,read('public'+(p==='norman'?catalog.modes:catalog.hattieModes)[mode].dataPath)]))])) as PresenterLibrary['presenterGames'];
const library:SessionLibrary={games:presenterGames.norman,presenterGames,controls:Object.fromEntries(MODE_IDS.map(mode=>[mode,catalog.modes[mode].control])) as PresenterLibrary['controls'],labels:Object.fromEntries(MODE_IDS.map(mode=>[mode,catalog.modes[mode].label])) as PresenterLibrary['labels'],twoPlayer:read('public'+catalog.twoPlayer.dataPath),extras:read('../analysis/extras/gateway.json')};
type Trace={modes:ModeId[];presenter:PresenterId|null;events:SessionEvent[];setup:string[];questions:{id:string;variant:number;slot:number;level:number;player:number;choices:{id:'A'|'B'|'C'|'D';time:number}[]}[]};
const traces=read('../analysis/extras/legacy-quiz-traces.json') as Trace[];
for(const trace of traces)test(`continuous original deterministic quiz ${trace.modes.join('/')} ${trace.presenter??'two players'}`,()=>{
 let s=createSession(library);s={...s,context:{...s.context,randomized:false},quiz:{...s.quiz,phase:'menu',menuIndex:0,activeScene:library.games['general-knowledge'].entry.menus[0].scene,ready:true,sceneToken:10}};
 let expected=trace.questions[0],steps=0;
 const send=(e:SessionEvent)=>{s=reduceSession(library,s,e,()=>expected?.variant===6?.9:0);};
 const ready=()=>send({type:'SCENE_READY',token:s.quiz.sceneToken});
 for(const event of trace.events){ready();send({...event,token:s.quiz.sceneToken} as SessionEvent);}
 const setup:string[]=[];
 const tick=()=>{ready();const q=s.quiz,g=q.currentPresentation?.gate;
  if(g?.scene===q.activeScene)send({type:'CONTINUE',token:q.sceneToken,time:g.control.windows[0].startTicks/90000+.001});else send({type:'SCENE_ENDED',token:q.sceneToken});
  if(++steps>5000)throw new Error('Legacy quiz failed to finish');
 };
 for(const [index,q] of trace.questions.entries()){
  expected=q;
  while(s.quiz.phase!=='question'){
   if(index===0&&s.quiz.activeScene?.startsWith('s02m-'))setup.push(s.quiz.activeScene);tick();
  }
  expect(s.quiz.questionId).toBe(q.id);expect(s.quiz.selection.variant).toBe(q.variant);expect(s.quiz.selection.candidateMask).toBe(q.slot);expect(s.quiz.levelIndex).toBe(q.level);
  if('activePlayer' in s.quiz)expect(s.quiz.activePlayer).toBe(q.player);
  for(const c of q.choices){ready();send({type:'ANSWER',token:s.quiz.sceneToken,time:c.time,choiceId:c.id});}
 }
 expect(setup).toEqual(trace.setup);
 while(s.quiz.phase!=='complete')tick();
 expect(s.quiz.totalScore).toBe(0);if('scores' in s.quiz)expect(s.quiz.scores).toEqual([0,0]);
});
