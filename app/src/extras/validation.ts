import {EXTRA_GAMES,type ExtrasData,type ExtraAction} from './types';
// Validate before allowing a new catalog to reach any interactive state.
export function validateExtrasData(input:unknown,fingerprint:string):asserts input is ExtrasData {
 const d=input as ExtrasData;
 const bad=()=>{throw new Error('Invalid original extras data');};
 if(!d||d.schemaVersion!==1||d.sourceFingerprint!==fingerprint||!Array.isArray(d.pages)||!Array.isArray(d.scenes)||!d.scenes.length||!Array.isArray(d.subtitles)||!d.codes||!d.games)bad();
 const scenes=new Map(d.scenes.map(s=>[s.id,s]));if(scenes.size!==d.scenes.length)bad();
 const media=(s:string)=>typeof s==='string'&&/^\/media\/[a-zA-Z0-9_.-]+$/.test(s);
 const interval=(v:{startTicks:number;endTicks:number})=>Number.isFinite(v.startTicks)&&Number.isFinite(v.endTicks)&&v.startTicks>=0&&v.endTicks>v.startTicks;
 const rect=(r:{x:number;y:number;width:number;height:number})=>r&&[r.x,r.y,r.width,r.height].every(Number.isFinite)&&r.x>=0&&r.y>=0&&r.width>0&&r.height>0&&r.x+r.width<=720&&r.y+r.height<=576;
 for(const s of d.scenes)if(!s.id||!media(s.src)||!Number.isFinite(s.durationSeconds)||s.durationSeconds<=0)bad();
 const pages=new Set(d.pages.map(p=>p.id));if(pages.size!==d.pages.length)bad();
 for(const id of ['instructions-choice','instructions-video','archive-intro','keypad-0','keypad-1','keypad-2','keypad-3','keypad-confirm','invalid-code'])if(!pages.has(id))bad();
 function action(a:ExtraAction){
  if(!a)bad();
  switch(a.type){case 'lager-route':if(!d.lager||!pages.has(a.page)||!Number.isInteger(a.focus)||a.focus<0||a.focus>36)bad();break;case 'memory-first':case 'memory-next':if(!d.memory)bad();break;case 'memory-choice':if(!d.memory||!Number.isInteger(a.objectId)||a.objectId<1||a.objectId>30)bad();break;case 'memory-stage':if(!d.memory||!Number.isInteger(a.stage)||a.stage<0||a.stage>2)bad();break;case 'vending-table':case 'vending-order':if(!d.vending)bad();break;case 'vending-digit':if(!d.vending||!Number.isInteger(a.digit)||a.digit<0||a.digit>9||typeof a.correct!=='boolean'||a.nextStage!==null&&(!Number.isInteger(a.nextStage)||a.nextStage<0||a.nextStage>3))bad();break;case 'whack-next':case 'whack-menu':if(!d.whack)bad();break;case 'whack-hit':if(!d.whack||typeof a.correct!=='boolean'||!Number.isInteger(a.positionSeed)||a.positionSeed<0||a.positionSeed>17)bad();break;case 'maze-route':if(!d.maze||!pages.has(a.page)||!Number.isInteger(a.focus)||a.focus<0)bad();break;case 'page':if(!pages.has(a.page))bad();break;case 'digit':if(!Number.isInteger(a.digit)||a.digit<0||a.digit>9)bad();break;case 'instructions':if(typeof a.subtitles!=='boolean')bad();break;case 'focus':if(!Number.isInteger(a.controlId)||a.controlId<1||a.controlId>36)bad();break;case 'stop':case 'main-menu':case 'archive-quit':case 'dispatch-code':break;case 'game':if(!a.action)bad();break;default:bad();}
 }
 for(const p of d.pages){
  if(!scenes.has(p.scene)||typeof p.loop!=='boolean'||!Array.isArray(p.controls))bad();
  const ids=new Set(p.controls.map(c=>c.id));if(ids.size!==p.controls.length||p.focus!==0&&!ids.has(p.focus))bad();
  if(p.after)action(p.after);
  for(const c of p.controls){
   if(!Number.isInteger(c.id)||c.id<1||!c.label||typeof c.autoActivate!=='boolean'||!Array.isArray(c.variants)||!c.variants.length||!c.neighbours)bad();
   for(const direction of ['up','down','left','right'] as const)if(!ids.has(c.neighbours[direction]))bad();
   let end=-1;for(const v of c.variants){if(!interval(v)||v.startTicks<end||!rect(v.rect)||!media(v.highlightSrc))bad();action(v.action);if(v.action.type==='focus'&&!ids.has(v.action.controlId))bad();end=v.endTicks;}
  }
 }
 for(const s of d.subtitles)if(!scenes.has(s.scene)||!media(s.src)||!interval(s))bad();
 for(const name of ['instructions','archive'] as const){const c=d.main?.[name];if(!c||!c.label||!rect(c.rect)||!media(c.highlightSrc)||!c.windows?.length)bad();for(const w of c.windows)if(!interval(w)||!Number.isInteger(w.selectionSeed)||w.selectionSeed<1||w.selectionSeed>65535)bad();}
 const codes=Object.entries(d.codes);if(codes.length!==5||new Set(codes.map(([,id])=>id)).size!==5)bad();
 for(const [code,id] of codes)if(!/^\d{4}$/.test(code)||!EXTRA_GAMES.includes(id))bad();
 for(const id of EXTRA_GAMES){const g=d.games[id];if(!g||!pages.has(g.menuPage)||!pages.has(g.instructionPage))bad();}
 if(d.maze&&!d.quizEntry)bad();
 if(d.maze){
  const route=(r:{page:string;focus:number})=>{const p=d.pages.find(p=>p.id===r?.page);if(!p||!Number.isInteger(r.focus)||(r.focus!==0&&!p.controls.some(c=>c.id===r.focus)))bad();};
  route(d.maze.entry);if(!d.maze.nodes||!Object.keys(d.maze.nodes).length)bad();
  for(const [id,node] of Object.entries(d.maze.nodes))if(!pages.has(id)||!Number.isInteger(node.lives)||node.lives<0||node.lives>3||![1,2,3].includes(node.docking)||typeof node.victory!=='boolean')bad();
  for(const p of d.pages)for(const a of [p.after,...p.controls.flatMap(c=>c.variants.map(v=>v.action))])if(a?.type==='maze-route'){route(a);if(a.page!=='maze-menu'&&!d.maze.nodes[a.page])bad();}
 }
 if(d.quizEntry){
  const main=d.quizEntry.mainOne;if(!Array.isArray(main)||main.length!==d.main.instructions.windows.length)bad();
  for(const [i,w] of main.entries()){const expected=d.main.instructions.windows[i];if(!interval(w)||w.startTicks!==expected.startTicks||w.endTicks!==expected.endTicks||!Number.isInteger(w.selectionSeed)||w.selectionSeed<1||w.selectionSeed>16)bad();}
  for(const table of [d.quizEntry.holly,d.quizEntry.secondMode]){
   if(!table)bad();for(const windows of Object.values(table)){if(!Array.isArray(windows)||!windows.length)bad();let end=-1;for(const w of windows){if(!interval(w)||w.startTicks<end||!Number.isInteger(w.variantCue)||w.variantCue<1||w.variantCue>4)bad();end=w.endTicks;}}
  }
  for(const id of ['norman','hattie'] as const)if(!d.quizEntry.holly[id])bad();
  for(const id of ['viewer','geek','general-knowledge'] as const)if(!d.quizEntry.secondMode[id])bad();
  for(let seed=1;seed<=16;seed++)for(const p of ['norman','hattie','two'] as const){const setup=d.quizEntry.setups?.[String(seed)]?.[p];if(!setup?.length||setup.some(id=>!scenes.has(id)))bad();}
 }

 if(d.whack){
  const w=d.whack;
  if(!Array.isArray(w.positions)||w.positions.length!==17||new Set(w.positions).size!==17||!Array.isArray(w.results)||w.results.length!==21||new Set(w.results).size!==21||!Array.isArray(w.cursorCycle)||w.cursorCycle.length!==17||w.cursorCycle.some(c=>!Number.isInteger(c)||c<1||c>9))bad();
  for(const id of w.positions){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||p.controls.length!==9||p.after?.type!=='whack-next'||Math.abs(scenes.get(p.scene)!.durationSeconds-2)>.01)bad();for(const c of p!.controls)if(c.id>9||c.autoActivate||c.variants.some(v=>v.action.type!=='whack-hit'))bad();if(p!.controls.filter(c=>c.variants[0].action.type==='whack-hit'&&c.variants[0].action.correct).length>1)bad();}
  for(const id of w.results){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||p.controls.length||p.after?.type!=='whack-menu'||Math.abs(scenes.get(p.scene)!.durationSeconds-7)>.01)bad();}
 }

 if(d.vending){
  const v=d.vending;if(!Array.isArray(v.rounds)||v.rounds.length!==3||!Array.isArray(v.roundCueOverrides)||v.roundCueOverrides.length!==2||v.initialRandomRange!==3||!Number.isInteger(v.initialCueDefault)||v.initialCueDefault<1||v.initialCueDefault>3)bad();
  const cues=(table:Record<string,number>,max:number)=>{if(!table)bad();for(const [key,cue] of Object.entries(table))if(!/^\d+$/.test(key)||Number(key)>65535||!Number.isInteger(cue)||cue<1||cue>max)bad();};
  cues(v.initialCues,3);cues(v.roundCueOverrides[0],5);cues(v.roundCueOverrides[1],7);
  for(const [n,r] of v.rounds.entries()){
   if(!Array.isArray(r.products)||r.products.length!==n+3||!Array.isArray(r.intro)||r.intro.length!==2||r.randomRange!==(n?5:3))bad();
   const productIds=new Set(r.products.map(p=>p.id));if(productIds.size!==r.products.length||!productIds.has(r.defaultProduct)||!r.cueProducts)bad();
   for(const id of Object.values(r.cueProducts))if(!productIds.has(id))bad();
   for(let cue=1;cue<=r.randomRange;cue++)if(!r.cueProducts[String(cue)])bad();
   for(const [i,id] of r.intro.entries()){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||p.controls.length||p.after?.type!==(i?'vending-order':'vending-table')||Math.abs(scenes.get(p.scene)!.durationSeconds-(i?[3,12,17][n]:4))>.01)bad();}
   for(const product of r.products){
    if(!Array.isArray(product.pages)||product.pages.length!==n+2)bad();
    for(const id of product.pages){const p=d.pages.find(p=>p.id===id);if(!p||!p.loop||p.after||p.controls.length!==10)bad();
     for(const c of p!.controls){if(c.id>10)bad();for(const {action:a} of c.variants)if(a.type!=='focus'&&a.type!=='vending-digit'||a.type==='vending-digit'&&a.nextStage!==null&&a.nextStage>=product.pages.length)bad();}
    }
   }
   for(const id of [r.successPage,r.wrongPage]){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||p.controls.length||Math.abs(scenes.get(p.scene)!.durationSeconds-4)>.01)bad();}
  }
  const ending=d.pages.find(p=>p.id===v.completePage);if(!ending||ending.loop||ending.controls.length||Math.abs(scenes.get(ending.scene)!.durationSeconds-10)>.01)bad();
 }

 if(d.lager){
  const l=d.lager;if(!pages.has(l.entry)||!Array.isArray(l.stages)||l.stages.length!==10||new Set(l.stages).size!==10||!l.nodes)bad();
  for(const [id,n] of Object.entries(l.nodes)){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||!Number.isInteger(n.stage)||n.stage<0||n.stage>10||!['intro','aim','hit','transition','interlude','fail'].includes(n.phase)||p.after?.type!=='lager-route')bad();}
  for(const id of l.stages){const p=d.pages.find(p=>p.id===id);if(!p||l.nodes[id]?.phase!=='aim'||p.controls.length!==1||p.controls[0].variants.some(v=>v.action.type!=='lager-route'))bad();}
  for(const p of d.pages)for(const a of [p.after,...p.controls.flatMap(c=>c.variants.map(v=>v.action))])if(a?.type==='lager-route'){const target=d.pages.find(p=>p.id===a.page);if(!target||!l.nodes[a.page]&&a.page!==d.games.lager.menuPage||a.focus!==0&&!target.controls.some(c=>c.id===a.focus))bad();}
 }
 if(d.memory){
  const m=d.memory;if(!Array.isArray(m.objects)||m.objects.length!==30||new Set(m.objects.map(o=>o.id)).size!==30||!Array.isArray(m.rounds)||m.rounds.length!==3||!Array.isArray(m.initialLegacyCues)||m.initialLegacyCues.length!==2||m.initialLegacyCues.some(c=>!Number.isInteger(c)||c<1||c>30)||m.initialVariantThreshold!==3||!m.legacyOffsets)bad();
  for(let n=1;n<=13;n++){const offset=m.legacyOffsets[String(n)];if(!Number.isInteger(offset)||offset<0||offset>30)bad();}
  for(const o of m.objects){const p=d.pages.find(p=>p.id===o.page);if(!Number.isInteger(o.id)||o.id<1||o.id>30||!o.label||!p||p.loop||p.controls.length||p.after?.type!=='memory-next'||Math.abs(scenes.get(p.scene)!.durationSeconds-2)>.01)bad();}
  for(const [stage,r] of m.rounds.entries()){
   if(r.length!==[5,8,12][stage]||r.alwaysCorrectLast!==(stage===2)||!Array.isArray(r.recall)||r.recall.length!==r.length||!Array.isArray(r.results)||r.results.length!==r.length+1||!Array.isArray(r.recallFocus)||r.recallFocus.length!==r.length||r.recallFocus.some(f=>f!==null&&(!Number.isInteger(f)||f<1||f>30)))bad();
   const intro=d.pages.find(p=>p.id===r.intro);if(!intro||intro.loop||intro.controls.length||intro.after?.type!=='memory-first'||Math.abs(scenes.get(intro.scene)!.durationSeconds-5)>.01)bad();
   for(const id of r.recall){const p=d.pages.find(p=>p.id===id);if(!p||!p.loop||p.after||p.controls.length!==30)bad();for(const c of p!.controls)if(c.id>30||c.variants.some(v=>v.action.type!=='memory-choice'))bad();}
   for(const id of r.results){const p=d.pages.find(p=>p.id===id);if(!p||p.loop||p.controls.length||Math.abs(scenes.get(p.scene)!.durationSeconds-5)>.01)bad();}
  }
 }

}

export function validateCompleteExtrasData(input:unknown,fingerprint:string):asserts input is ExtrasData {
 validateExtrasData(input,fingerprint);
 if(!input.maze||!input.whack||!input.vending||!input.memory||!input.lager||!input.quizEntry)throw new Error('Incomplete original extras data');
 validateExtraOwnership(input);
}

function validateExtraOwnership(d:ExtrasData){
 const bad=():never=>{throw new Error('Invalid original extras continuation');};
 const owners=new Map<string,string>(),pages=new Map(d.pages.map(p=>[p.id,p]));
 const claim=(id:string,owner:string)=>{if(!pages.has(id)||owners.has(id)&&owners.get(id)!==owner)bad();owners.set(id,owner);};
 for(const id of ['instructions-choice','instructions-video','archive-intro','keypad-0','keypad-1','keypad-2','keypad-3','keypad-confirm','invalid-code'])claim(id,'gateway');
 const menus=new Set<string>();
 for(const id of EXTRA_GAMES){const g=d.games[id];claim(g.menuPage,id);claim(g.instructionPage,id);menus.add(g.menuPage);}
 for(const id of Object.keys(d.maze!.nodes))claim(id,'maze');
 for(const id of [...d.whack!.positions,...d.whack!.results])claim(id,'whack');
 for(const r of d.vending!.rounds)for(const id of [...r.intro,r.successPage,r.wrongPage,...r.products.flatMap(p=>p.pages)])claim(id,'vending');
 claim(d.vending!.completePage,'vending');
 for(const o of d.memory!.objects)claim(o.page,'memory');
 for(const r of d.memory!.rounds)for(const id of [r.intro,...r.recall,...r.results])claim(id,'memory');
 for(const id of Object.keys(d.lager!.nodes))claim(id,'lager');
 const continuation=(id:string,expected:ExtraAction)=>{
  const actual=pages.get(id)?.after;
  if(!actual||actual.type!==expected.type)return bad();
  if(expected.type==='page'&&(actual.type!=='page'||actual.page!==expected.page))bad();
  if(expected.type==='memory-stage'&&(actual.type!=='memory-stage'||actual.stage!==expected.stage))bad();
 };
 continuation('instructions-video',{type:'main-menu'});continuation('archive-intro',{type:'page',page:'keypad-0'});continuation('keypad-confirm',{type:'dispatch-code'});continuation('invalid-code',{type:'main-menu'});
 for(const r of d.vending!.rounds){continuation(r.successPage,{type:'vending-order'});continuation(r.wrongPage,{type:'page',page:d.games.vending.menuPage});}
 continuation(d.vending!.completePage,{type:'page',page:d.games.vending.menuPage});
 for(const [stage,r] of d.memory!.rounds.entries())for(const [score,id] of r.results.entries())continuation(id,stage<2&&score>=[3,5][stage]?{type:'memory-stage',stage:stage+1}:{type:'page',page:d.games.memory.menuPage});
 for(const p of d.pages){
  const owner=owners.get(p.id);if(!owner||(p.loop?p.after!==null:!p.after))bad();
  for(const a of [p.after,...p.controls.flatMap(c=>c.variants.map(v=>v.action))]){
   if(!a)continue;
   const engine=EXTRA_GAMES.find(id=>a.type.startsWith(id+'-'));if(engine&&owner!==engine)bad();
   if(a.type==='page'&&owners.get(a.page)!==owner)bad();
   if(a.type==='game'&&(!menus.has(p.id)||a.action!=='play'))bad();
   if(a.type==='archive-quit'&&!menus.has(p.id))bad();
   if(a.type==='instructions'&&p.id!=='instructions-choice')bad();
   if(a.type==='digit'&&!/^keypad-[0-3]$/.test(p.id))bad();
   if(a.type==='dispatch-code'&&p.id!=='keypad-confirm')bad();
   if(a.type==='main-menu'&&owner!=='gateway')bad();
   if(a.type==='stop'&&!((owner==='whack'||owner==='memory')&&p.id===d.games[owner].instructionPage))bad();
  }
 }
 for(const id of EXTRA_GAMES){
  const g=d.games[id],menu=pages.get(g.menuPage)!;
  if(!menu.loop)bad();
  const control=(id:number,type:string,page?:string)=>{const c=menu.controls.find(c=>c.id===id);if(!c||c.variants.some(v=>v.action.type!==type||page!==undefined&&(v.action.type!=='page'||v.action.page!==page)))bad();};
  control(1,'game');control(id==='maze'?2:3,'archive-quit');
  if(g.instructionPage!==g.menuPage)control(2,'page',g.instructionPage);
 }
}
