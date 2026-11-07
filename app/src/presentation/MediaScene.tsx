import type { RefObject } from 'react';
import type { Scene } from '../game/types';
import { usePlayback } from './usePlayback';
export function MediaScene({scene,token,loop,videoRef,send,onTime}:{scene:Scene;token:number;loop:boolean;
  videoRef:RefObject<HTMLVideoElement|null>;send:(event:{type:'SCENE_READY'|'SCENE_WAITING'|'SCENE_ENDED';token:number})=>void;onTime:(time:number)=>void}){
  const {problem,retry}=usePlayback(videoRef,scene.src,token,
    ()=>send({type:'SCENE_READY',token}),()=>send({type:'SCENE_WAITING',token}),onTime);
  return <>
    <video ref={videoRef} src={scene.src} autoPlay playsInline preload="auto" loop={loop}
      onEnded={()=>send({type:'SCENE_ENDED',token})} aria-label="Original game footage"/>
    {problem && <div className="playback-prompt">
      <p>{problem==='gesture'?'Press Play to continue.':'This scene could not play. Please retry.'}</p>
      <button onClick={()=>void retry()}>{problem==='gesture'?'Play':'Retry'}</button>
    </div>}
  </>;
}
