import { dataPath } from '../../test/data';
import {expect,test} from 'vitest';
import {readFileSync,writeFileSync} from 'node:fs';
import type {GameData} from './types';
import type {PresenterLibrary} from './presenters';
import {MODE_IDS,type ModeId} from './modes';
import {currentQuestion} from './progression';
import {createTwoPlayerGame,reduceTwoPlayerGame,activeTwoPlayerData,type TwoPlayerData} from './twoPlayer';
const load=(name:string)=>JSON.parse(readFileSync(dataPath('public/'+name),'utf8'));
const metadata=load('two-player.json') as TwoPlayerData;
const presenterGames=Object.fromEntries(['norman','hattie'].map(p=>[p,Object.fromEntries(MODE_IDS.map(mode=>[mode,load('game'+(mode==='general-knowledge'?'':'-'+mode)+(p==='hattie'?'-hattie':'')+'.json')]))])) as PresenterLibrary['presenterGames'];
const library:PresenterLibrary={games:presenterGames.norman,presenterGames,controls:Object.fromEntries(MODE_IDS.map(m=>[m,presenterGames.norman[m].entry.menus[1]])) as PresenterLibrary['controls'],labels:{viewer:'Viewer',geek:'Geek','general-knowledge':'General Knowledge'}};
test('all nine real-data combinations preserve scores, turns, pools and both eligible bonuses',()=>{
 const coverage:Record<string,Set<string>>={},results:object[]=[];
 for(const first of MODE_IDS)for(const second of MODE_IDS)for(const strategy of ['correct','wrong','mixed','late-timeouts'])for(let seed=1;seed<=30;seed++){
  let rng=seed;const draw=()=>{rng=(Math.imul(rng,1664525)+1013904223)>>>0;return rng/4294967296;};
  let s=createTwoPlayerGame(library,metadata,1),count=0,bonus:number[]=[],guard=0;
  const send=(e:Parameters<typeof reduceTwoPlayerGame>[3])=>{s=reduceTwoPlayerGame(library,metadata,s,e,draw);};
  for(const [i,modeId] of [first,second].entries()){
   send({type:'SCENE_READY',token:s.sceneToken});send({type:'CHOOSE_MODE',token:s.sceneToken,modeId,time:metadata.menus[i as 0|1][modeId].windows[0].startTicks/90000});
  }
  while(s.phase!=='complete'&&guard++<12000){
   send({type:'SCENE_READY',token:s.sceneToken});
   const data=library.presenterGames[s.presenterId][s.modeId],q=currentQuestion(data,s);
   if((s.phase==='question'||s.phase==='bonus')&&q){
    const isBonus=s.phase==='bonus',correct=strategy==='correct'||strategy==='mixed'&&Math.floor(count/2)%2===0;
    if(!isBonus){
     expect(s.activePlayer).toBe(count%2);const key=s.presenterId+':'+s.modeId;(coverage[key]??=new Set()).add(q.id);
    }
    if(!isBonus&&strategy==='late-timeouts'&&s.levelIndex>=3){
     const old=s.turnNumber;while(s.phase==='question'){
      send({type:'SCENE_READY',token:s.sceneToken});send({type:'SCENE_ENDED',token:s.sceneToken});
     }
     expect(s.turnNumber).toBe(old);
    }else{
     const ids=q.kind==='sequence'?(correct?q.correctSequence:['A','A','A','A'] as const):[isBonus||correct?q.correctChoice!:q.choices.find(c=>c.id!==q.correctChoice)!.id];
     for(const choiceId of ids){
      send({type:'SCENE_READY',token:s.sceneToken});const windows=q.windows.filter(w=>w.choiceId===choiceId),w=windows[Math.floor(draw()*windows.length)];
      send({type:'ANSWER',token:s.sceneToken,choiceId,time:(w.startTicks+1)/90000});
     }
    }
    if(isBonus)bonus.push(s.activePlayer);else count++;
   }else{
    const gate=s.currentPresentation?.gate;
    send(gate?.scene===s.activeScene?{type:'CONTINUE',token:s.sceneToken,time:(gate.control.windows[0].startTicks+1)/90000}:{type:'SCENE_ENDED',token:s.sceneToken});
   }
  }
  expect(guard).toBeLessThan(12000);expect(count).toBe(96);
  expect(s.scores).toEqual(strategy==='correct'?[48,48]:strategy==='mixed'?[24,24]:[0,0]);expect(bonus).toEqual(strategy==='correct'?[0,1]:[]);
  results.push({players:[first,second],strategy,seed,questions:count,scores:s.scores,bonuses:bonus});
 }
 for(const player of ['norman','hattie'])for(const mode of MODE_IDS)expect(coverage[player+':'+mode]?.size,player+':'+mode).toBe(304);
 writeFileSync(dataPath('../analysis/two-player/native-real-data.json'),JSON.stringify({games:results.length,coverage:Object.fromEntries(Object.entries(coverage).map(([k,v])=>[k,v.size])),results},null,2)+'\n');
},180000);
