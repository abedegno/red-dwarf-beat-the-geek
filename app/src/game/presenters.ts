import type {GameData} from './types';
import {createModeGame,reduceModeGame,type GameLibrary,type ModeState,type ModeEvent,type ModeId,type ModeCatalog} from './modes';
export const PRESENTER_IDS=['norman','hattie'] as const;
export type PresenterId=typeof PRESENTER_IDS[number];
export interface PresenterCatalog extends Omit<ModeCatalog,'schemaVersion'> {schemaVersion:2;hattieModes:ModeCatalog['modes']}
export interface PresenterLibrary extends GameLibrary {presenterGames:Record<PresenterId,Record<ModeId,GameData>>}
export interface PresenterState extends ModeState {presenterId:PresenterId}
export type PresenterEvent=ModeEvent|{type:'CHOOSE_PRESENTER';presenterId:PresenterId;token:number;time:number};
export function activeGame(library:PresenterLibrary,state:PresenterState){return library.presenterGames[state.presenterId][state.modeId];}
export function createPresenterGame(library:PresenterLibrary):PresenterState{return {...createModeGame(library),presenterId:'norman'};}
export function reducePresenterGame(library:PresenterLibrary,s:PresenterState,event:PresenterEvent,draw:()=>number=Math.random):PresenterState{
  if(event.type==='CHOOSE_PRESENTER'){
    if(s.phase!=='menu' || s.menuIndex!==2 || !s.ready || s.sceneToken!==event.token || !s.activeScene)return s;
    const games=library.presenterGames[event.presenterId],control=games?.[s.modeId]?.entry.menus[2];
    if(!control?.windows.some(w=>w.startTicks<=event.time*90000 && event.time*90000<w.endTicks))return s;
    const next=reduceModeGame({...library,games},s,{type:'MENU_CHOOSE',token:event.token,time:event.time},draw);
    return next===s?s:{...next,presenterId:event.presenterId};
  }
  const next=reduceModeGame({...library,games:library.presenterGames[s.presenterId]},s,event,draw);
  return next===s?s:{...next,presenterId:event.type==='RESET'?'norman':s.presenterId};
}
