import type {ExtrasData,ExtrasState,WhackState} from './types';
const initial=(cursorStep=0):WhackState=>({attempt:0,score:0,appearance:0,positionSeed:0,cursorStep});
function display(data:ExtrasData,s:ExtrasState,pageId:string,focus=0):ExtrasState{
 if(!data.pages.some(p=>p.id===pageId))throw new Error('Missing original Whack presentation');
 return {...s,pageId,focus,sceneToken:s.sceneToken+1,ready:false};
}
export function whackMenu(data:ExtrasData,s:ExtrasState,fresh=false):ExtrasState {
 return display(data,{...s,whack:initial(fresh?0:s.whack?.cursorStep??0),context:{...s.context,variantCue:0}},data.games.whack.menuPage,1);
}
export function advanceWhack(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 const d=data.whack;if(!d||!s.whack)throw new Error('Missing original Whack state');
 const w={...s.whack},context={...s.context};const roll=(n:number)=>Math.min(n,Math.floor(draw()*n)+1);
 // The selector updates the cursor even on the final trip to the result screen.
 if(context.randomized)context.cursorCue=roll(9);
 else {
  if(w.cursorStep!==0)context.cursorCue=d.cursorCycle[w.cursorStep-1];
  context.selectionSeed=w.cursorStep;w.cursorStep=w.cursorStep===17?1:w.cursorStep+1;
 }
 if(w.attempt===20)return display(data,{...s,whack:w,context},d.results[w.score]);
 w.attempt++;w.positionSeed++;if(w.positionSeed===18)w.positionSeed=1;
 if(context.randomized)w.positionSeed=roll(17);
 w.appearance=w.positionSeed;
 if(w.cursorStep===0)context.cursorCue=roll(9);
 context.cursorCue=Math.min(65535,context.cursorCue*1024);
 const selected=context.cursorCue>>>10,focus=selected>=1&&selected<=9?selected:0;
 return display(data,{...s,whack:w,context},d.positions[w.appearance-1],focus);
}
export function startWhack(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 return advanceWhack(data,{...s,whack:initial(s.whack?.cursorStep??0),context:{...s.context,variantCue:0}},draw);
}
export function hitWhack(data:ExtrasData,s:ExtrasState,correct:boolean,positionSeed:number,draw:()=>number=Math.random):ExtrasState {
 if(!s.whack)throw new Error('Missing original Whack attempt');
 return advanceWhack(data,{...s,whack:{...s.whack,score:correct?s.whack.score+1:Math.max(0,s.whack.score-1),positionSeed}},draw);
}
