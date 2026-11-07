import {activeGame,createPresenterGame,reducePresenterGame,type PresenterLibrary,type PresenterState,type PresenterEvent} from '../game/presenters';
import {createTwoPlayerGame,reduceTwoPlayerGame,type TwoPlayerData,type TwoPlayerState} from '../game/twoPlayer';
import type {ExtrasData,ExtrasState,ExtraEvent,CompatibilityContext} from './types';
import {sessionLibrary} from './legacyQuiz';
import {createExtras,reduceExtras,initialContext} from './gateway';
export type SessionLibrary=PresenterLibrary & {twoPlayer?:TwoPlayerData;extras?:ExtrasData};
export type SessionState={entrySeed:number;quiz:PresenterState|TwoPlayerState;extra:ExtrasState|null;context:CompatibilityContext};
export type SessionEvent=PresenterEvent|{type:'CHOOSE_PLAYERS';token:number;time:number}|{type:'OPEN_EXTRA';branch:'instructions'|'archive';token:number;time:number}|{type:'EXTRA';event:ExtraEvent};

function isTwo(state:PresenterState|TwoPlayerState):state is TwoPlayerState{return 'playerModes' in state;}
export const createSession=(library:SessionLibrary):SessionState=>({entrySeed:1,quiz:createPresenterGame(library),extra:null,context:initialContext()});
export function reduceSession(library:SessionLibrary,session:SessionState,event:SessionEvent,draw:()=>number=Math.random):SessionState {
    let previous=session.quiz;
    if(event.type==='RESET')return {entrySeed:1,quiz:{...createPresenterGame(library),sceneToken:Math.max(previous.sceneToken,session.extra?.sceneToken??0)+1},extra:null,context:initialContext()};
    if(event.type==='EXTRA'){
      if(!session.extra||!library.extras)return session;
      const next=reduceExtras(library.extras,session.extra,event.event,draw);
      if(next===session.extra)return session;
      if(!next.exit)return {...session,extra:next};
      const fresh={...createPresenterGame(library),sceneToken:next.sceneToken+1};
      const quiz=next.exit==='restart'?reducePresenterGame(library,fresh,{type:'START'}):{...fresh,phase:'menu' as const,menuIndex:0,activeScene:activeGame(library,fresh).entry.menus[0].scene};
      return {entrySeed:1,quiz,extra:null,context:next.exit==='restart'?initialContext():next.context};
    }
    if(session.extra)return session;
    if(event.type==='OPEN_EXTRA'){
      const m=library.extras?.main[event.branch];
      if(!m||isTwo(previous)||previous.phase!=='menu'||previous.menuIndex!==0||!previous.ready||event.token!==previous.sceneToken)return session;
      const window=m.windows.find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks);if(!window)return session;
      const context={...session.context,selectionSeed:window.selectionSeed};
      return {...session,context,extra:{...createExtras(event.branch,previous.sceneToken+1,context.randomized),context}};
    }
    if(event.type==='CHOOSE_PLAYERS'){
      const m=library.twoPlayer;
      if(!m||isTwo(previous)||previous.phase!=='menu'||previous.menuIndex!==0||!previous.ready||event.token!==previous.sceneToken||!m.main.windows.some(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks))return session;
      const window=m.main.windows.find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks)!;
      const entrySeed=window.candidateMask;
      const quiz=createTwoPlayerGame(library,m,previous.sceneToken+1);
      return {...session,entrySeed,context:{...session.context,guardMarker:10000,cursorCue:0,variantCue:(entrySeed-1)%4+1,selectionSeed:entrySeed},quiz:session.context.randomized?quiz:{...quiz,selection:{...quiz.selection,variant:(entrySeed-1)%4+1}}};
    }
    if(event.type==='MENU_CHOOSE'&&!isTwo(previous)&&previous.phase==='menu'&&previous.menuIndex===0){
      const quiz=reducePresenterGame(library,previous,event,draw);if(quiz===previous)return session;
      const original=activeGame(library,previous).entry.menus[0].windows.find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks)!;
      const entrySeed=session.context.randomized?original.candidateMask:library.extras!.quizEntry!.mainOne.find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks)!.selectionSeed;
      const variant=(entrySeed-1)%4+1;
      return {...session,entrySeed,context:{...session.context,guardMarker:10000,cursorCue:0,selectionSeed:entrySeed,variantCue:variant},quiz:session.context.randomized?quiz:{...quiz,selection:{...quiz.selection,variant}}};
    }
    const effective=session.context.randomized?library:sessionLibrary(library,session);
    if(!session.context.randomized&&previous.phase==='menu'&&previous.ready&&'token' in event&&event.token===previous.sceneToken){
      const entries=library.extras!.quizEntry!;
      if(event.type==='CHOOSE_PRESENTER'&&!isTwo(previous)&&previous.menuIndex===2){
        const c=effective.presenterGames[event.presenterId][previous.modeId].entry.menus[2];
        const w=entries.holly[event.presenterId].find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks);
        if(w&&c.windows.some(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks))previous={...previous,selection:{...previous.selection,variant:(previous.selection.variant+w.variantCue-1)%4+1}};
      }
      if(event.type==='CHOOSE_MODE'&&isTwo(previous)&&previous.stage==='choose'&&previous.menuIndex===2){
        const c=effective.twoPlayer!.menus[1][event.modeId],w=entries.secondMode[event.modeId].find(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks);
        if(w&&c.windows.some(w=>w.startTicks<=event.time*90000&&event.time*90000<w.endTicks))previous={...previous,selection:{...previous.selection,variant:w.variantCue}};
      }
    }
    return {...session,quiz:isTwo(previous)?reduceTwoPlayerGame(effective,effective.twoPlayer!,previous,event,draw):reducePresenterGame(effective,previous,event,draw)};
  }
