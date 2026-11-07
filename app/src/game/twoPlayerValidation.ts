import {MODE_IDS} from './modes';
import type {Menu,TimedControl} from './types';
import type {TwoPlayerData,TwoPlayerPresentation} from './twoPlayer';
export function validateTwoPlayerData(value:unknown,fingerprint:string):asserts value is TwoPlayerData {
 const m=value as TwoPlayerData;
 function need(ok:unknown):asserts ok {if(!ok)throw new Error('Incomplete two-player game');}
 need(m?.schemaVersion===1&&m.sourceFingerprint===fingerprint&&m.levels?.length===8&&m.menus?.length===2&&m.setupOptions?.length===6&&m.scenes?.length);
 const ids=new Set(m.scenes.map(s=>s.id));need(ids.size===m.scenes.length);
 for(const s of m.scenes)need(s.src.startsWith('/media/')&&s.durationSeconds>0);
 const scene=(id:string)=>need(ids.has(id));
 const sequence=(list:string[])=>{need(Array.isArray(list));list.forEach(scene);};
 const required=(list:string[])=>{need(list?.length);sequence(list);};
 function control(c:TimedControl){need(c?.rect?.width>0&&c.rect.height>0&&c.highlightSrc?.startsWith('/media/')&&c.windows?.length);for(const w of c.windows)need(w.startTicks>=0&&w.endTicks>w.startTicks);}
 function menu(c:Menu,candidate=true){control(c);scene(c.scene);for(const w of c.windows)if(candidate)need(w.candidateMask>=1&&w.candidateMask<=32768&&(w.candidateMask&(w.candidateMask-1))===0);}
 function presentation(p:TwoPlayerPresentation,destination:string){need(p?.destination===destination);required(p.scenes);if(p.gate){scene(p.gate.scene);need(p.scenes.at(-1)===p.gate.scene);control(p.gate.control);sequence(p.gate.afterScenes);}}
 menu(m.main,false);for(const set of m.menus)for(const mode of MODE_IDS)menu(set[mode]);m.setupOptions.forEach(required);
 for(const [i,l] of m.levels.entries()){
  need(l.turns?.length===2&&l.scorecards?.length===2);l.turns.forEach(required);
  for(let bit=0;bit<16;bit++){required(l.intros[String(1<<bit)]);required(l.closings[String(1<<bit)]);}
  for(const player of [0,1])for(let score=0;score<=6;score++)for(let prior=0;prior<=6*i;prior++){
   const total=prior+score,destination=i===7&&total===48?'bonus':player===0?'next-player':i===7?'complete':'next-level';
   const card=l.scorecards[player][`${score}:${total}`];presentation(card,destination);
   // The source scorecard audio register also controls ordering prompt expiry.
   need(card.nextOrderingRepeatOffset===player*3+(score<3?0:score<5?1:2));
  }
 }
 need(m.bonuses?.length===2);
 for(const player of [0,1])for(const mode of MODE_IDS){
  const b=m.bonuses[player][mode];need(b?.length===2);
  for(const bonus of b){need(['A','B','C','D'].includes(bonus.correctChoice));required(bonus.introScenes);for(const p of [bonus.correct,bonus.wrong])presentation(p,player===0?'next-player':'complete');}
 }
}
