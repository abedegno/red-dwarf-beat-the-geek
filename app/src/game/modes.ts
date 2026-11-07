import type {GameData,GameEvent,GameState,TimedControl} from './types';
import {createGame,reduceGame} from './progression';
export const MODE_IDS=['viewer','geek','general-knowledge'] as const;
export type ModeId=typeof MODE_IDS[number];
export interface ModeCatalog {
  schemaVersion:1;sourceFingerprint:string;
  modes:Record<ModeId,{label:string;dataPath:string;control:TimedControl}>;
}
export interface GameLibrary {
  games:Record<ModeId,GameData>;controls:Record<ModeId,TimedControl>;labels:Record<ModeId,string>;
}
export interface ModeState extends GameState {modeId:ModeId}
export type ModeEvent=GameEvent|{type:'CHOOSE_MODE';modeId:ModeId;token:number;time:number};
const DEFAULT_MODE:ModeId='general-knowledge';
export function createModeGame(library:GameLibrary):ModeState{
  return {...createGame(library.games[DEFAULT_MODE]),modeId:DEFAULT_MODE};
}
export function reduceModeGame(library:GameLibrary,state:ModeState,event:ModeEvent,draw:()=>number=Math.random):ModeState{
  if(event.type==='CHOOSE_MODE'){
    if(state.phase!=='menu' || state.menuIndex!==1 || !state.ready || event.token!==state.sceneToken || !state.activeScene)return state;
    const game=library.games[event.modeId],control=library.controls[event.modeId];
    if(!game || !control?.windows.some(w=>w.startTicks<=event.time*90000 && event.time*90000<w.endTicks))return state;
    const next=reduceGame(game,state,{type:'MENU_CHOOSE',token:event.token,time:event.time},draw);
    return next===state?state:{...next,modeId:event.modeId};
  }
  const next=reduceGame(library.games[state.modeId],state,event,draw);
  return next===state?state:{...next,modeId:event.type==='RESET'?DEFAULT_MODE:state.modeId};
}
