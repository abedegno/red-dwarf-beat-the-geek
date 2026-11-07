import { useEffect, useState, type RefObject } from 'react';

export function usePlayback(video:RefObject<HTMLVideoElement|null>,src:string,token:number,
  ready:()=>void,waiting:()=>void,time:(value:number)=>void){
  const [problem,setProblem]=useState<'gesture'|'error'|null>(null);
  useEffect(()=>{
    const element=video.current;if(!element)return;
    let live=true,frame:number|undefined;
    const playing=()=>{if(live){setProblem(null);ready();}};
    const wait=()=>{if(live)waiting();};
    const error=()=>{if(live){waiting();setProblem('error');}};
    const tick=()=>{if(live){time(element.currentTime);if(element.requestVideoFrameCallback)frame=element.requestVideoFrameCallback(tick);}};
    element.addEventListener('playing',playing);element.addEventListener('waiting',wait);element.addEventListener('error',error);
    const interval=setInterval(()=>{if(live)time(element.currentTime);},100);
    if(element.requestVideoFrameCallback)frame=element.requestVideoFrameCallback(tick);
    void element.play().catch(reason=>{
      if(live && reason?.name!=='AbortError'){waiting();setProblem(reason?.name==='NotAllowedError'?'gesture':'error');}
    });
    return ()=>{live=false;clearInterval(interval);if(frame!==undefined)element.cancelVideoFrameCallback?.(frame);
      element.removeEventListener('playing',playing);element.removeEventListener('waiting',wait);element.removeEventListener('error',error);};
    // A token owns one playback instance. Old promises/listeners are cancelled;
    // readiness updates must not restart the same source.
  },[src,token]);
  async function retry(){
    const element=video.current;if(!element)return;
    if(problem==='error')element.load();
    try{await element.play();setProblem(null);}catch(reason){
      setProblem(reason instanceof DOMException && reason.name==='NotAllowedError'?'gesture':'error');
    }
  }
  return {problem,retry};
}
