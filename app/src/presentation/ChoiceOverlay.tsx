import { useState, type CSSProperties, type KeyboardEvent } from 'react';
import type { Choice, ChoiceId, Control, Rect } from '../game/types';

function position(rect:Rect):CSSProperties {
  return {left:`${rect.x/720*100}%`,top:`${rect.y/576*100}%`,width:`${rect.width/720*100}%`,height:`${rect.height/576*100}%`};
}
export function ChoiceOverlay({id,text,choices,disabled,onChoose}:{id:string;text:string;choices:Choice[];
  disabled:boolean;onChoose:(id:ChoiceId)=>void}){
  const [highlight,setHighlight]=useState<ChoiceId|null>(null);
  const selected=choices.find(c=>c.id===highlight);
  function navigate(event:KeyboardEvent<HTMLButtonElement>,index:number){
    const direction=['ArrowDown','ArrowRight'].includes(event.key)?1:['ArrowUp','ArrowLeft'].includes(event.key)?-1:0;
    if(direction){event.preventDefault();const buttons=event.currentTarget.closest('fieldset')!.querySelectorAll('button');
      (buttons[(index+direction+buttons.length)%buttons.length] as HTMLButtonElement).focus();}
  }
  return <fieldset id={id} aria-label={text} className="choices">
    <legend className="sr-only">{text}</legend>
    {selected && !disabled && <img className="highlight" src={selected.highlightSrc} alt=""/>}
    {choices.map((choice,index)=><button key={choice.id} className="hit-area" style={position(choice.rect)}
      aria-label={`${choice.id}. ${choice.label}`} disabled={disabled}
      onPointerEnter={()=>setHighlight(choice.id)} onPointerLeave={()=>setHighlight(null)}
      onFocus={()=>setHighlight(choice.id)} onBlur={()=>setHighlight(null)}
      onKeyDown={event=>navigate(event,index)} onClick={()=>onChoose(choice.id)}>
      <span className="sr-only">{choice.id}. {choice.label}</span>
    </button>)}
  </fieldset>;
}
export function SingleControl({control,disabled,onActivate}:{control:Control;disabled:boolean;onActivate:()=>void}){
  const [highlight,setHighlight]=useState(false);
  return <>
    {highlight && !disabled && <img className="highlight" src={control.highlightSrc} alt=""/>}
    <button className="hit-area" style={position(control.rect)} disabled={disabled} aria-label={control.label}
      onPointerEnter={()=>setHighlight(true)} onPointerLeave={()=>setHighlight(false)}
      onFocus={()=>setHighlight(true)} onBlur={()=>setHighlight(false)} onClick={onActivate}>
      <span className="sr-only">{control.label}</span>
    </button>
  </>;
}
