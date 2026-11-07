import type {ExtrasData,ExtrasState} from './types';
export function routeLager(data:ExtrasData,s:ExtrasState,page:string,focus:number):ExtrasState {
 if(!data.lager||!data.pages.some(p=>p.id===page))throw new Error('Missing original Lager presentation');
 const node=data.lager.nodes[page];if(!node&&page!==data.games.lager.menuPage)throw new Error('Unknown original Lager stage');
 return {...s,pageId:page,focus,ready:false,sceneToken:s.sceneToken+1,lager:node??null};
}
export function startLager(data:ExtrasData,s:ExtrasState):ExtrasState {
 if(!data.lager)throw new Error('Missing original Lager data');return routeLager(data,s,data.lager.entry,0);
}
