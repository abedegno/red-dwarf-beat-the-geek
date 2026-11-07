import {useEffect,useRef,useState} from 'react';
import type {ExtrasData,ExtrasState,ExtraEvent} from './types';
import {extraPage} from './gateway';
import {ExtraControls} from './ExtraControls';
import {MediaScene} from '../presentation/MediaScene';
export function ExtrasView({data,state,send}:{data:ExtrasData;state:ExtrasState;send:(event:ExtraEvent)=>void}){
 const videoRef=useRef<HTMLVideoElement|null>(null),[time,setTime]=useState(0);
 useEffect(()=>setTime(0),[state.sceneToken]);
 const page=extraPage(data,state),scene=data.scenes.find(s=>s.id===page.scene);
 if(!scene)throw new Error('Missing original extras footage');
 return <>
  <MediaScene key={state.sceneToken} scene={scene} token={state.sceneToken} loop={page.loop} videoRef={videoRef} send={send} onTime={setTime}/>
  {state.subtitles&&data.subtitles.filter(s=>s.scene===scene.id&&s.startTicks<=time*90000&&time*90000<s.endTicks).map(s=><img key={`${s.src}-${s.startTicks}`} src={s.src} className="highlight" alt=""/>)}
  {state.memory&&data.memory&&['show','recall'].includes(state.memory.phase)&&<p className="sr-only" role="status" aria-label="Memory Morph" aria-live="polite">{state.memory.phase==='show'?data.memory.objects.find(o=>o.id===state.memory!.shown.at(-1))?.label:`Recall object ${state.memory.recalled.length+1} of ${data.memory.rounds[state.memory.stage].length}.`}</p>}
  {!state.stopped&&page.controls.length>0&&<ExtraControls page={page} state={state} time={time} mediaTime={()=>videoRef.current?.currentTime??time} send={send}/>}
 </>;
}
