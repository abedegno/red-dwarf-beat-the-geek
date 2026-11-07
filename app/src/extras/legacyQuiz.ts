import {MODE_IDS} from '../game/modes';
import {PRESENTER_IDS,type PresenterLibrary} from '../game/presenters';
import type {SessionLibrary,SessionState} from './session';
const cache=new WeakMap<SessionLibrary,Map<number,SessionLibrary>>();
export function sessionLibrary(library:SessionLibrary,s:SessionState):SessionLibrary {
 if(s.context.randomized)return library;
 const cached=cache.get(library)?.get(s.entrySeed);if(cached)return cached;
 const metadata=library.extras?.quizEntry,setup=metadata?.setups[String(s.entrySeed)];if(!setup)throw new Error('Missing original deterministic quiz entry');
 const presenterGames=Object.fromEntries(PRESENTER_IDS.map(p=>[p,Object.fromEntries(MODE_IDS.map(mode=>{
  const d=library.presenterGames[p][mode];return [mode,{...d,randomized:false,scenes:[...d.scenes,...library.extras!.scenes],entry:{...d.entry,setupScenes:setup[p],setupOptions:undefined}}];
 }))])) as PresenterLibrary['presenterGames'];
 const effective={...library,games:presenterGames.norman,presenterGames,twoPlayer:library.twoPlayer?{...library.twoPlayer,setupOptions:[setup.two]}:undefined};
 if(!cache.has(library))cache.set(library,new Map());cache.get(library)!.set(s.entrySeed,effective);return effective;
}
