import type {ExtrasData,ExtrasState,VendingState} from './types';
const initial=(productCue:number):VendingState=>({round:0,order:0,productId:null,entered:[],correctDigits:0,successes:0,usedProducts:[],productCue});
function display(data:ExtrasData,s:ExtrasState,pageId:string,focus=0):ExtrasState {
 if(!data.pages.some(p=>p.id===pageId))throw new Error('Missing original Vending presentation');return {...s,pageId,focus,ready:false,sceneToken:s.sceneToken+1};
}
export function initializeVending(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 const d=data.vending;if(!d)throw new Error('Missing original Vending data');
 const cue=s.context.randomized?Math.min(d.initialRandomRange,Math.floor(draw()*d.initialRandomRange)+1):d.initialCues[String(s.context.selectionSeed)]??d.initialCueDefault;
 return display(data,{...s,vending:initial(cue)},data.games.vending.menuPage,1);
}
export function startVending(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 if(!s.vending)s=initializeVending(data,s,draw);
 return display(data,{...s,vending:initial(s.vending!.productCue),context:{...s.context,guardMarker:0,variantCue:0}},data.vending!.rounds[0].intro[0]);
}
export function vendingTable(data:ExtrasData,s:ExtrasState):ExtrasState {
 if(!s.vending||!data.vending)throw new Error('Missing original Vending round');return display(data,s,data.vending.rounds[s.vending.round].intro[1]);
}
export function nextVendingOrder(data:ExtrasData,s:ExtrasState,draw:()=>number=Math.random):ExtrasState {
 const d=data.vending;if(!d||!s.vending)throw new Error('Missing original Vending order');
 const v={...s.vending},context={...s.context};
 if(v.order===2){
  if(v.round===2)return display(data,s,v.successes===6?d.completePage:data.games.vending.menuPage,v.successes===6?0:1);
  context.selectionSeed=Math.min(65535,context.selectionSeed*2);if(context.selectionSeed>=32768)context.selectionSeed=4;
  v.productCue=d.roundCueOverrides[v.round as 0|1][String(context.selectionSeed)]??v.productCue;v.round++;v.order=0;v.productId=null;v.entered=[];v.correctDigits=0;v.usedProducts=[];
  context.guardMarker=0;context.variantCue=0;return display(data,{...s,vending:v,context},d.rounds[v.round].intro[0]);
 }
 const r=d.rounds[v.round];v.order++;v.entered=[];v.correctDigits=0;context.guardMarker=v.order;context.variantCue=0;
 v.productCue=context.randomized?Math.min(r.randomRange,Math.floor(draw()*r.randomRange)+1):Math.min(65535,v.productCue+2);
 let id=r.cueProducts[String(v.productCue)]??r.defaultProduct;
 for(let tries=0;v.usedProducts.includes(id);tries++){
  if(tries>=r.products.length)throw new Error('No unused original Vending product');const index=r.products.findIndex(p=>p.id===id);id=r.products[(index+1)%r.products.length].id;
 }
 const product=r.products.find(p=>p.id===id);if(!product)throw new Error('Missing original Vending product');v.productId=id;v.usedProducts=[...v.usedProducts,id];
 return display(data,{...s,vending:v,context},product.pages[0],1);
}
export function enterVendingDigit(data:ExtrasData,s:ExtrasState,digit:number,correct:boolean,nextStage?:number|null):ExtrasState {
 if(!data.vending||!s.vending)throw new Error('Missing original Vending entry');
 const v={...s.vending,entered:[...s.vending.entered,digit],correctDigits:Math.min(65535,s.vending.correctDigits+Number(correct))},r=data.vending.rounds[v.round],product=r.products.find(p=>p.id===v.productId);
 if(!product)throw new Error('Missing original Vending code');
 const context={...s.context,variantCue:v.correctDigits};
 const next=nextStage===undefined?(v.entered.length<product.pages.length?v.entered.length:null):nextStage;
 if(next!==null){v.entered=next===0?[]:v.entered.slice(0,next);return display(data,{...s,vending:v,context},product.pages[next],s.focus);}
 const success=v.correctDigits===product.pages.length;if(success)v.successes++;
 return display(data,{...s,vending:v,context},success?r.successPage:r.wrongPage);
}
