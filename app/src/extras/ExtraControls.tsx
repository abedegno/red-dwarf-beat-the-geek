import {useEffect,useRef} from 'react';
import type {ExtraEvent,ExtraPage,ExtrasState,Direction} from './types';
import {activeVariant} from './gateway';
export function ExtraControls({page,state,time,mediaTime,send}:{page:ExtraPage;state:ExtrasState;time:number;mediaTime:()=>number;send:(e:ExtraEvent)=>void}){
 const root=useRef<HTMLFieldSetElement>(null);
 const selected=page.controls.find(c=>c.id===state.focus),highlight=selected&&activeVariant(selected,time),focusActive=!!highlight;
 useEffect(()=>{if(state.ready&&state.focus)root.current?.querySelector<HTMLButtonElement>(`[data-control="${state.focus}"]`)?.focus({preventScroll:true});},[state.ready,state.sceneToken,state.focus,focusActive]);
 return <fieldset id={page.id} ref={root} className="choices" aria-label="Original game controls" onKeyDown={e=>{
  const direction=({ArrowUp:'up',ArrowDown:'down',ArrowLeft:'left',ArrowRight:'right'} as Record<string,Direction>)[e.key];
  if(direction){e.preventDefault();send({type:'MOVE',direction,token:state.sceneToken,time:mediaTime()});}
 }}>
  <legend className="sr-only">Original game controls</legend>
  {state.ready&&highlight&&<img className="highlight" src={highlight.highlightSrc} alt=""/>}
  {page.controls.map(c=>{const v=activeVariant(c,time);return v&&<button key={c.id} data-control={c.id} className="hit-area" aria-label={c.label}
   style={{left:`${v.rect.x/720*100}%`,top:`${v.rect.y/576*100}%`,width:`${v.rect.width/720*100}%`,height:`${v.rect.height/576*100}%`}}
   disabled={!state.ready} onPointerEnter={()=>send({type:'FOCUS',controlId:c.id,token:state.sceneToken,time:mediaTime()})}
   onFocus={()=>send({type:'FOCUS',controlId:c.id,token:state.sceneToken,time:mediaTime()})}
   onClick={()=>send({type:'ACTIVATE',controlId:c.id,token:state.sceneToken,time:mediaTime()})}><span className="sr-only">{c.label}</span></button>;})}
 </fieldset>;
}
