import {startLager,routeLager} from './lager';
import {initializeMemory,startMemory,memoryMenu,beginMemoryStage,firstMemoryObject,nextMemoryObject,recallMemory} from './memory';
import {initializeVending,startVending,vendingTable,nextVendingOrder,enterVendingDigit} from './vending';
import {startWhack,advanceWhack,hitWhack,whackMenu} from './whack';
import {routeMaze,startMaze} from './maze';
import type {CompatibilityContext,ExtraAction,ExtrasData,ExtraEvent,ExtraPage,ExtrasState} from './types';
export const initialContext=(randomized=true):CompatibilityContext=>({randomized,guardMarker:10000,cursorCue:0,selectionSeed:1,variantCue:0});
export function createExtras(branch:'instructions'|'archive',token:number,randomized=true):ExtrasState {
 return {lager:null,memory:null,vending:null,stopped:false,whack:null,maze:null,pageId:branch==='instructions'?'instructions-choice':'archive-intro',sceneToken:token,ready:false,focus:branch==='instructions'?1:0,code:'',subtitles:false,gameId:null,context:initialContext(randomized),exit:null};
}
export function extraPage(data:ExtrasData,state:ExtrasState):ExtraPage {
 const p=data.pages.find(p=>p.id===state.pageId);if(!p)throw new Error('Missing original extras page');return p;
}
export function activeVariant(control:ExtraPage['controls'][number],time:number){return Number.isFinite(time)?control.variants.find(v=>v.startTicks<=time*90000&&time*90000<v.endTicks):undefined;}
function navigate(data:ExtrasData,s:ExtrasState,pageId:string):ExtrasState {
 const p=data.pages.find(p=>p.id===pageId);if(!p)throw new Error('Missing original extras route');
 return {...s,pageId,sceneToken:s.sceneToken+1,ready:false,focus:p.focus};
}
function action(data:ExtrasData,s:ExtrasState,a:ExtraAction,draw:()=>number):ExtrasState {
 switch(a.type){
  case 'lager-route':return routeLager(data,s,a.page,a.focus);
  case 'focus':return {...s,focus:a.controlId};
  case 'stop':return {...s,stopped:true,ready:false};
  case 'page':if(a.page==='memory-menu'&&s.gameId==='memory'&&data.memory)return memoryMenu(data,s);return a.page==='whack-menu'&&s.gameId==='whack'&&data.whack?whackMenu(data,s):navigate(data,s,a.page);
  case 'main-menu':return {...s,sceneToken:s.sceneToken+1,ready:false,exit:s.context.guardMarker===s.context.selectionSeed?'restart':'main-menu',subtitles:false,gameId:null};
  case 'archive-quit':return s.context.guardMarker===s.context.selectionSeed?{...s,sceneToken:s.sceneToken+1,ready:false,exit:'restart'}:navigate(data,{...s,code:'',gameId:null,whack:null},'archive-intro');
  case 'instructions':
   if(s.context.guardMarker===s.context.selectionSeed)return {...s,sceneToken:s.sceneToken+1,ready:false,exit:'restart'};
   return navigate(data,{...s,subtitles:a.subtitles},'instructions-video');
  case 'digit':{
   if(!/^keypad-[0-3]$/.test(s.pageId)||s.code.length>=4)return s;
   const code=s.code+String(a.digit),next=navigate(data,{...s,code},code.length===4?'keypad-confirm':`keypad-${code.length}`);
   return {...next,focus:s.focus};
  }
  case 'dispatch-code':{
   const gameId=data.codes[s.code];if(!gameId)return navigate(data,s,'invalid-code');
   if(s.context.guardMarker===s.context.selectionSeed)return {...s,sceneToken:s.sceneToken+1,ready:false,exit:'restart'};
   if(gameId==='memory'&&data.memory)return initializeMemory(data,{...s,gameId},draw);
   if(gameId==='vending'&&data.vending)return initializeVending(data,{...s,gameId},draw);
   return gameId==='whack'&&data.whack?whackMenu(data,{...s,gameId},true):navigate(data,{...s,gameId},data.games[gameId].menuPage);
  }
  case 'maze-route':return routeMaze(data,s,a);
  case 'memory-first':return firstMemoryObject(data,s,draw);
  case 'memory-next':return nextMemoryObject(data,s,draw);
  case 'memory-stage':return beginMemoryStage(data,s,a.stage);
  case 'memory-choice':return recallMemory(data,s,a.objectId);
  case 'vending-table':return vendingTable(data,s);
  case 'vending-order':return nextVendingOrder(data,s,draw);
  case 'vending-digit':return enterVendingDigit(data,s,a.digit,a.correct,a.nextStage);
  case 'whack-next':return advanceWhack(data,s,draw);
  case 'whack-hit':return hitWhack(data,s,a.correct,a.positionSeed,draw);
  case 'whack-menu':return whackMenu(data,s);
  case 'game':return a.action==='play'?(s.gameId==='maze'?startMaze(data,s):s.gameId==='whack'?startWhack(data,s,draw):s.gameId==='vending'?startVending(data,s,draw):s.gameId==='memory'?startMemory(data,s):s.gameId==='lager'?startLager(data,s):s):s;
 }
}
export function reduceExtras(data:ExtrasData,s:ExtrasState,e:ExtraEvent,draw:()=>number=Math.random):ExtrasState {
 if(s.exit||s.stopped||e.token!==s.sceneToken)return s;
 if(e.type==='SCENE_READY')return {...s,ready:true};
 if(e.type==='SCENE_WAITING')return {...s,ready:false};
 if(!s.ready)return s;
 const p=extraPage(data,s);
 if(e.type==='SCENE_ENDED')return p.after?action(data,s,p.after,draw):s;
 const control=e.type==='MOVE'?p.controls.find(c=>c.id===s.focus)?.neighbours[e.direction]:e.controlId;
 const c=p.controls.find(c=>c.id===control);if(!c)return s;
 const v=activeVariant(c,e.time);if(!v)return s;
 const focused={...s,focus:c.id};
 return e.type==='ACTIVATE'||c.autoActivate?action(data,focused,v.action,draw):focused;
}
