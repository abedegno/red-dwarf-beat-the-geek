import type {ExtrasData,ExtrasState} from './types';
function display(data:ExtrasData,s:ExtrasState,pageId:string,focus=0):ExtrasState {
 if(!data.pages.some(p=>p.id===pageId))throw new Error('Missing original Memory presentation');return {...s,pageId,focus,ready:false,sceneToken:s.sceneToken+1};
}
export function initializeMemory(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 const d=data.memory;if(!d)throw new Error('Missing original Memory data');
 const cue=s.context.randomized?Math.min(d.objects.length,Math.floor(draw()*d.objects.length)+1):d.initialLegacyCues[s.context.variantCue<d.initialVariantThreshold?0:1];
 return display(data,{...s,memory:{stage:0,phase:'menu',cue,shown:[],recalled:[],score:0,cursor:1}},data.games.memory.menuPage,1);
}
export function memoryMenu(data:ExtrasData,s:ExtrasState):ExtrasState {
 return display(data,{...s,memory:s.memory?{...s.memory,phase:'menu',cursor:1}:null},data.games.memory.menuPage,1);
}
export function beginMemoryStage(data:ExtrasData,s:ExtrasState,stage:number):ExtrasState {
 if(!data.memory||!s.memory||!data.memory.rounds[stage])throw new Error('Missing original Memory round');
 return display(data,{...s,memory:{...s.memory,stage,phase:'intro',shown:[],recalled:[],score:0},context:{...s.context,guardMarker:0,cursorCue:0,selectionSeed:0,variantCue:0}},data.memory.rounds[stage].intro);
}
export function startMemory(data:ExtrasData,s:ExtrasState):ExtrasState {
 if(!s.memory)throw new Error('Missing original Memory entry');return beginMemoryStage(data,{...s,memory:{...s.memory,cursor:1}},0);
}
function selectCue(data:ExtrasData,s:ExtrasState,remaining:number,draw:()=>number):ExtrasState {
 const d=data.memory!,m=s.memory!;let cue=m.cue;
 if(s.context.randomized)cue=Math.min(d.objects.length,Math.floor(draw()*d.objects.length)+1);
 else {cue+=d.legacyOffsets[String(remaining)]??0;for(let n=0;n<3&&cue>d.objects.length;n++)cue=Math.floor(cue/2);}
 return {...s,memory:{...m,cue}};
}
function showObject(data:ExtrasData,s:ExtrasState):ExtrasState {
 const m=s.memory!,object=data.memory!.objects.find(o=>o.id===m.cue);if(!object)throw new Error('Missing original Memory object');
 const shown=[...m.shown,object.id],context={...s.context},value=object.id*1000;
 if(shown.length===1)context.guardMarker=value;if(shown.length===9)context.cursorCue=value;if(shown.length===10)context.selectionSeed=value;if(shown.length===12)context.variantCue=value;
 return display(data,{...s,memory:{...m,phase:'show',shown,cursor:1},context},object.page);
}
export function firstMemoryObject(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 if(!s.memory||!data.memory)throw new Error('Missing original Memory presentation');
 if(s.memory.stage>0)s=selectCue(data,s,data.memory.rounds[s.memory.stage].length+1,draw);return showObject(data,s);
}
export function nextMemoryObject(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 if(!data.memory||!s.memory)throw new Error('Missing original Memory sequence');const r=data.memory.rounds[s.memory.stage];
 s=selectCue(data,s,r.length-s.memory.shown.length+1,draw);
 if(s.memory!.shown.length<r.length)return showObject(data,s);
 const focus=r.recallFocus[0]??s.memory!.cursor;
 return display(data,{...s,memory:{...s.memory!,phase:'recall',score:0}},r.recall[0],focus);
}
export function recallMemory(data:ExtrasData,s:ExtrasState,objectId:number):ExtrasState {
 if(!data.memory||!s.memory)throw new Error('Missing original Memory recall');const m=s.memory,r=data.memory.rounds[m.stage],index=m.recalled.length;
 const correct=objectId===m.shown[index]||r.alwaysCorrectLast&&index===r.length-1;
 const next={...m,cursor:objectId,recalled:[...m.recalled,objectId],score:m.score+Number(correct)};
 if(next.recalled.length<r.length)return display(data,{...s,memory:next},r.recall[next.recalled.length],r.recallFocus[next.recalled.length]??objectId);
 return display(data,{...s,memory:{...next,phase:'result'}},r.results[next.score]);
}
