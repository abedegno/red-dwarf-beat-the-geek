import type {KeyboardEvent} from 'react';
import {MODE_IDS,type GameLibrary,type ModeId} from '../game/modes';
import type {TimedControl} from '../game/types';
import {SingleControl} from './ChoiceOverlay';
export function ControlMenu({label,items,ready,time}:{label:string;items:{id:string;control:TimedControl;onActivate:()=>void}[];ready:boolean;time:number}){
  function navigate(event:KeyboardEvent<HTMLFieldSetElement>){
    const direction=['ArrowDown','ArrowRight'].includes(event.key)?1:['ArrowUp','ArrowLeft'].includes(event.key)?-1:0;
    if(!direction)return;
    const buttons=[...event.currentTarget.querySelectorAll<HTMLButtonElement>('button:not(:disabled)')];
    const index=buttons.indexOf(event.target as HTMLButtonElement);
    if(index<0)return;
    event.preventDefault();buttons[(index+direction+buttons.length)%buttons.length].focus();
  }
  return <fieldset className="choices mode-menu" aria-label={label} onKeyDown={navigate}>
    <legend className="sr-only">{label}</legend>
    {items.map(item=><SingleControl key={item.id} control={item.control}
      disabled={!ready || !item.control.windows.some(w=>w.startTicks<=time*90000 && time*90000<w.endTicks)} onActivate={item.onActivate}/>)}
  </fieldset>;
}
export function ModeMenu({library,ready,time,onChoose}:{library:GameLibrary;ready:boolean;time:number;onChoose:(mode:ModeId)=>void}){
  return <ControlMenu label="Quiz mode" ready={ready} time={time}
    items={MODE_IDS.map(id=>({id,control:library.controls[id],onActivate:()=>onChoose(id)}))}/>;
}
