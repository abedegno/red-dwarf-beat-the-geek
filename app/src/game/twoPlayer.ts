import type {GameData,GamePresentation,Menu,Scene} from './types';
import {MODE_IDS,type ModeId} from './modes';
import {createPresenterGame,type PresenterLibrary,type PresenterState,type PresenterEvent} from './presenters';
import {reduceGame,playGameScenes,playGamePresentation} from './progression';
import {selectQuestion} from './selection';

export interface TwoPlayerPresentation extends Omit<GamePresentation,'destination'> {destination:'next-player'|'next-level'|'complete'|'bonus'}
export interface TwoPlayerScorecard extends TwoPlayerPresentation {nextOrderingRepeatOffset:number}
export interface TwoPlayerData {
 schemaVersion:1;sourceFingerprint:string;main:Menu;menus:[Record<ModeId,Menu>,Record<ModeId,Menu>];setupOptions:string[][];scenes:Scene[];
 levels:{intros:Record<string,string[]>;closings:Record<string,string[]>;turns:[string[],string[]];scorecards:[Record<string,TwoPlayerScorecard>,Record<string,TwoPlayerScorecard>]}[];
 bonuses:[Record<ModeId,{introScenes:string[];correctChoice:string;correct:TwoPlayerPresentation;wrong:TwoPlayerPresentation}[]>,Record<ModeId,{introScenes:string[];correctChoice:string;correct:TwoPlayerPresentation;wrong:TwoPlayerPresentation}[]>];
}
export interface TwoPlayerState extends PresenterState {
 playerModes:[ModeId,ModeId];scores:[number,number];roundScores:[number,number];activePlayer:0|1;turnNumber:number;
 usedMasks:Record<ModeId,number>;stage:'choose'|'entry'|'play'|'closing'|'scorecard'|'bonus';segmentDestination:TwoPlayerPresentation['destination'];segmentRepeat:number;
}
const banks=():Record<ModeId,number>=>({'general-knowledge':0,viewer:0,geek:0});
export function createTwoPlayerGame(library:PresenterLibrary,metadata:TwoPlayerData,token:number):TwoPlayerState {
 return {...createPresenterGame(library),phase:'menu',menuIndex:1,activeScene:metadata.menus[0]['general-knowledge'].scene,sceneToken:token,
  playerModes:['general-knowledge','general-knowledge'],scores:[0,0],roundScores:[0,0],activePlayer:0,turnNumber:0,usedMasks:banks(),stage:'choose',segmentDestination:'complete',segmentRepeat:0};
}
export function activeTwoPlayerData(library:PresenterLibrary,metadata:TwoPlayerData,s:TwoPlayerState):GameData {
 const data=library.presenterGames[s.presenterId][s.modeId];
 return {...data,scenes:[...data.scenes,...metadata.scenes],bonuses:data.bonuses.map((b,i)=>{
  const extra=metadata.bonuses[s.activePlayer][s.modeId][i];
  return {...b,introScenes:extra.introScenes,correct:{...extra.correct,destination:'complete'},wrong:{...extra.wrong,destination:'complete'}};
 })};
}
function asPlayer(s:TwoPlayerState,player:0|1):TwoPlayerState {
 return {...s,activePlayer:player,modeId:s.playerModes[player],presenterId:player===0?'norman':'hattie',roundScore:s.roundScores[player],totalScore:s.scores[player]};
}
function beginTurn(library:PresenterLibrary,m:TwoPlayerData,s:TwoPlayerState,draw:()=>number):TwoPlayerState {
 const level=m.levels[s.levelIndex];
 if(s.turnNumber===12)return segment(library,m,{...s,stage:'closing'},{scenes:level.closings[String(s.nextCandidateMask)],destination:'next-player',nextCandidateMask:s.nextCandidateMask},draw);
 s=asPlayer(s,s.turnNumber%2 as 0|1);
 const data=activeTwoPlayerData(library,m,s),selected=selectQuestion(data.levels[s.levelIndex],{usedMask:s.usedMasks[s.modeId],candidateMask:s.nextCandidateMask,variant:s.selection.variant},draw,data.randomized!==false);
 const next={...s,stage:'play' as const,usedMasks:{...s.usedMasks,[s.modeId]:selected.state.usedMask},questionNumber:Math.floor(s.turnNumber/2)+1,
  selection:selected.state,questionId:selected.questionId,chosenAnswers:[],promptCompleted:0,timeoutOutcome:null,currentPresentation:null,bonusId:null};
 return playGameScenes(data,next,'question-intro',[...level.turns[s.activePlayer],...selected.introScenes],'question',draw) as TwoPlayerState;
}
function segment(library:PresenterLibrary,m:TwoPlayerData,s:TwoPlayerState,p:TwoPlayerPresentation,draw:()=>number):TwoPlayerState {
 if(!p?.scenes)throw new Error('Missing two-player presentation');
 const next={...s,segmentDestination:p.destination,segmentRepeat:p.nextOrderingRepeatOffset??s.orderingRepeatOffset};
 return playGamePresentation(activeTwoPlayerData(library,m,next),next,{...p,destination:'complete',nextCandidateMask:s.nextCandidateMask},'ending',draw) as TwoPlayerState;
}
function scorecard(library:PresenterLibrary,m:TwoPlayerData,s:TwoPlayerState,player:0|1,draw:()=>number):TwoPlayerState {
 s=asPlayer({...s,stage:'scorecard'},player);
 return segment(library,m,s,m.levels[s.levelIndex].scorecards[player][`${s.roundScore}:${s.totalScore}`],draw);
}
function advanceSegment(library:PresenterLibrary,m:TwoPlayerData,s:TwoPlayerState,draw:()=>number):TwoPlayerState {
 if(s.stage==='closing')return scorecard(library,m,s,0,draw);
 const destination=s.stage==='bonus'?(s.activePlayer===0?'next-player':'complete'):s.segmentDestination;
 if(destination==='bonus'){
  const data=activeTwoPlayerData(library,m,s),bonus=data.bonuses[s.selection.variant<3?0:1];
  const next:TwoPlayerState={...s,stage:'bonus',bonusId:bonus.id,questionId:bonus.question.id,chosenAnswers:[],currentPresentation:null};
  return playGameScenes(data,next,'bonus-intro',bonus.introScenes,'bonus-question',draw) as TwoPlayerState;
 }
 if(destination==='next-player')return scorecard(library,m,s,1,draw);
 if(destination==='complete')return {...s,phase:'complete',ready:false,currentPresentation:null};
 const next={...s,stage:'entry' as const,levelIndex:s.levelIndex+1,turnNumber:0,roundScores:[0,0] as [number,number],roundScore:0,questionNumber:0,
  usedMasks:banks(),orderingRepeatOffset:s.segmentRepeat,questionId:null,bonusId:null,currentPresentation:null,chosenAnswers:[]};
 return playGameScenes(activeTwoPlayerData(library,m,next),next,'entry',m.levels[next.levelIndex].intros[String(next.nextCandidateMask)],'next-question',draw) as TwoPlayerState;
}
export function reduceTwoPlayerGame(library:PresenterLibrary,m:TwoPlayerData,s:TwoPlayerState,event:PresenterEvent,draw:()=>number=Math.random):TwoPlayerState {
 if(event.type==='CHOOSE_MODE'){
  if(s.stage!=='choose'||s.phase!=='menu'||!s.ready||event.token!==s.sceneToken||!MODE_IDS.includes(event.modeId))return s;
  const index=s.menuIndex-1,control=m.menus[index as 0|1][event.modeId];
  const window=control.windows.find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks);
  if(!window)return s;
  const playerModes=[...s.playerModes] as [ModeId,ModeId];playerModes[index]=event.modeId;
  if(index===0)return {...s,playerModes,menuIndex:2,activeScene:m.menus[1]['general-knowledge'].scene,sceneToken:s.sceneToken+1,ready:false};
  const next=asPlayer({...s,playerModes,stage:'entry',nextCandidateMask:window.candidateMask},0);
  const setup=m.setupOptions.length===1?m.setupOptions[0]:m.setupOptions[Math.min(m.setupOptions.length-1,Math.floor(draw()*m.setupOptions.length))];
  return playGameScenes(activeTwoPlayerData(library,m,next),next,'entry',[...setup,...m.levels[0].intros[String(window.candidateMask)]],'next-question',draw) as TwoPlayerState;
 }
 if(event.type==='CHOOSE_PRESENTER'||event.type==='MENU_CHOOSE'||event.type==='START'||event.type==='RESET')return s;
 if(event.type==='SCENE_ENDED'&&event.token===s.sceneToken&&s.ready&&s.queue.length===0&&s.destination==='next-question'&&(s.phase==='feedback'||s.phase==='entry')){
  return beginTurn(library,m,{...s,turnNumber:s.turnNumber+(s.phase==='feedback'?1:0)},draw);
 }
 const next=reduceGame(activeTwoPlayerData(library,m,s),s,event,draw) as TwoPlayerState;
 if(next===s)return s;
 const scores=[...s.scores] as [number,number],roundScores=[...s.roundScores] as [number,number];
 scores[s.activePlayer]=next.totalScore;roundScores[s.activePlayer]=next.roundScore;
 const updated={...next,scores,roundScores};
 return updated.phase==='complete'&&s.phase!=='complete'?advanceSegment(library,m,updated,draw):updated;
}
