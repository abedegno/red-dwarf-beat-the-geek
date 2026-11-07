import { useCallback, useEffect, useRef, useState } from 'react';
import type { GameData } from './game/types';
import {MODE_IDS} from './game/modes';
import {PRESENTER_IDS,activeGame,type PresenterLibrary,type PresenterCatalog,type PresenterState} from './game/presenters';
import {ControlMenu,ModeMenu} from './presentation/ModeMenu';
import {activeTwoPlayerData,type TwoPlayerData,type TwoPlayerState} from './game/twoPlayer';
import {validateTwoPlayerData} from './game/twoPlayerValidation';
import { currentQuestion } from './game/progression';
import { Stage } from './presentation/Stage';
import { MediaScene } from './presentation/MediaScene';
import { ChoiceOverlay, SingleControl } from './presentation/ChoiceOverlay';

import type {ExtraEvent} from './extras/types';
import {validateCompleteExtrasData} from './extras/validation';
import {ExtrasView} from './extras/ExtrasView';
import {sessionLibrary} from './extras/legacyQuiz';
import {createSession,reduceSession,type SessionLibrary,type SessionState,type SessionEvent} from './extras/session';
function isTwo(state:PresenterState|TwoPlayerState):state is TwoPlayerState{return 'playerModes' in state;}
function Game({library}:{library:SessionLibrary}){
  const [session,setSession]=useState<SessionState>(()=>createSession(library));
  const state=session.quiz,extra=session.extra;
  const two=isTwo(state)?state:null;
  const effective=session.context.randomized?library:sessionLibrary(library,session);
  const data=two?activeTwoPlayerData(effective,effective.twoPlayer!,two):activeGame(effective,state);
  const [time,setTime]=useState(0);
  const stageRef=useRef<HTMLElement|null>(null),videoRef=useRef<HTMLVideoElement|null>(null);
  const send=useCallback((event:SessionEvent)=>setSession(previous=>reduceSession(library,previous,event)),[library]);
  const sendExtra=useCallback((event:ExtraEvent)=>send({type:'EXTRA',event}),[send]);
  useEffect(()=>{setTime(0);},[state.sceneToken]);
  useEffect(()=>{if(state.phase==='complete')videoRef.current?.pause();},[state.phase]);
  const scene=data.scenes.find(s=>s.id===state.activeScene);
  const question=currentQuestion(data,state);
  const menu=state.phase==='menu'?(two?library.twoPlayer!.menus[(state.menuIndex-1) as 0|1]['general-knowledge']:data.entry.menus[state.menuIndex]):null;
  const gate=state.currentPresentation?.gate;
  const activeGate=gate?.scene===state.activeScene?gate:null;
  const mediaTime=()=>videoRef.current?.currentTime ?? time;
  return <main>
    <Stage stageRef={stageRef}>
      {extra&&library.extras?<ExtrasView data={library.extras} state={extra} send={sendExtra}/>:<>
      {scene && <MediaScene key={state.sceneToken} scene={scene} token={state.sceneToken}
        loop={(state.phase==='question' && question?.expiry==='loop') || state.phase==='menu' || !!activeGate?.loop}
        videoRef={videoRef} send={send} onTime={setTime}/>}
      {state.phase==='idle' && <>
        <img className="poster" src="/media/menu-poster.png" alt="Red Dwarf Beat the Geek"/>
        <button className="start-play" aria-label="Play game" onClick={()=>send({type:'START'})}>▶ <span>Play</span></button>
      </>}
      {menu && two && <ControlMenu label={`Player ${state.menuIndex} quiz mode`} ready={state.ready} time={time}
        items={MODE_IDS.map(modeId=>({id:modeId,control:library.twoPlayer!.menus[(state.menuIndex-1) as 0|1][modeId],onActivate:()=>send({type:'CHOOSE_MODE',modeId,token:state.sceneToken,time:mediaTime()})}))}/>}
      {menu && !two && state.menuIndex===1 && <ModeMenu library={library} ready={state.ready} time={time}
        onChoose={modeId=>send({type:'CHOOSE_MODE',modeId,token:state.sceneToken,time:mediaTime()})}/>}
      {menu && !two && state.menuIndex===2 && <ControlMenu label="Holly" ready={state.ready} time={time}
        items={PRESENTER_IDS.map(presenterId=>({id:presenterId,control:library.presenterGames[presenterId][state.modeId].entry.menus[2],
          onActivate:()=>send({type:'CHOOSE_PRESENTER',presenterId,token:state.sceneToken,time:mediaTime()})}))}/>}
      {menu && !two && state.menuIndex===0 && library.twoPlayer && <ControlMenu label="Players" ready={state.ready} time={time}
        items={[{id:'one',control:menu,onActivate:()=>send({type:'MENU_CHOOSE',token:state.sceneToken,time:mediaTime()})},{id:'two',control:library.twoPlayer.main,onActivate:()=>send({type:'CHOOSE_PLAYERS',token:state.sceneToken,time:mediaTime()})},...(library.extras?(['instructions','archive'] as const).map(branch=>({id:branch,control:library.extras!.main[branch],onActivate:()=>send({type:'OPEN_EXTRA',branch,token:state.sceneToken,time:mediaTime()})})):[])]}/>}
      {menu && !two && state.menuIndex===0 && !library.twoPlayer && <SingleControl key={menu.id} control={menu}
        disabled={!state.ready || time*90000<(menu.windows[0]?.startTicks??0)}
        onActivate={()=>send({type:'MENU_CHOOSE',token:state.sceneToken,time:mediaTime()})}/>}
      {(state.phase==='question' || state.phase==='bonus') && question && <ChoiceOverlay key={question.id} id={question.id}
        text={question.text} choices={question.choices} disabled={!state.ready}
        onChoose={choiceId=>send({type:'ANSWER',token:state.sceneToken,choiceId,time:mediaTime()})}/>}
      {activeGate && <SingleControl control={activeGate.control}
        disabled={!state.ready || !activeGate.control.windows.some(w=>w.startTicks<=time*90000 && time*90000<w.endTicks)}
        onActivate={()=>send({type:'CONTINUE',token:state.sceneToken,time:mediaTime()})}/>}
      </>}
    </Stage>
    <footer>
      <span>{extra?(extra.pageId.startsWith('instructions')?'How to Play':'Games Archive'):<>{two?`Two players · Player ${two.activePlayer+1}`:'One player'} · {library.labels[state.modeId]} · {state.presenterId==='hattie'?'Hattie Holly':'Norman Holly'} · Level {state.levelIndex+1} of 8</>}</span>
      <nav aria-label="Playback controls">
        <button onClick={()=>send({type:'RESET'})}>Restart</button>
        <button onClick={()=>void stageRef.current?.requestFullscreen?.()}>Full screen</button>
      </nav>
      {!extra&&two && <span aria-label="Player scores">Player 1: {two.scores[0]} · Player 2: {two.scores[1]}</span>}
      {!extra&&<p role="status" aria-label="Round status" aria-live="polite" className="sr-only">
        {two?`Player ${two.activePlayer+1}. `:''}{state.phase==='complete'?'Game complete.':`Question ${state.questionNumber} of 6.`} Score {state.roundScore} of 6. Total {state.totalScore} of 48. Level {state.levelIndex+1} of 8.
        {question?.kind==='sequence' && state.phase==='question'?` ${state.chosenAnswers.length} of 4 selections made.`:''}
      </p>}
    </footer>
  </main>;
}

export default function App(){
  const [data,setData]=useState<SessionLibrary|null>(null),[error,setError]=useState(false);
  useEffect(()=>{
    let active=true;
    const get=async(path:string)=>{const response=await fetch(path);if(!response.ok)throw new Error('Game unavailable');return response.json();};
    get('/catalog.json').then(async(value:PresenterCatalog & {twoPlayer?:{dataPath:string};extras?:{dataPath:string}})=>{
      if(value.schemaVersion!==2 || !value.sourceFingerprint)throw new Error('Invalid catalog');
      const entries=await Promise.all(PRESENTER_IDS.flatMap(presenterId=>MODE_IDS.map(async id=>{
        const entry=(presenterId==='norman'?value.modes:value.hattieModes)?.[id];
        if(!entry?.dataPath.startsWith('/games/') || !entry.control?.windows?.length || !entry.label)throw new Error('Invalid mode');
        const game=await get(entry.dataPath) as GameData;
        if(game.schemaVersion!==2 || !game.scenes?.length || game.levels?.length!==8 || game.bonuses?.length!==2 || game.sourceFingerprint!==value.sourceFingerprint)throw new Error('Invalid game');
        return {presenterId,id,game};
      })));
      const presenterGames=Object.fromEntries(PRESENTER_IDS.map(p=>[p,Object.fromEntries(entries.filter(e=>e.presenterId===p).map(e=>[e.id,e.game]))])) as PresenterLibrary['presenterGames'];
      const library:SessionLibrary={games:presenterGames.norman,presenterGames,
        controls:Object.fromEntries(MODE_IDS.map(id=>[id,value.modes[id].control])) as PresenterLibrary['controls'],
        labels:Object.fromEntries(MODE_IDS.map(id=>[id,value.modes[id].label])) as PresenterLibrary['labels']};
      if(value.twoPlayer){
        if(!value.twoPlayer.dataPath?.startsWith('/games/'))throw new Error('Invalid two-player catalog');
        const m=await get(value.twoPlayer.dataPath) as TwoPlayerData;
        validateTwoPlayerData(m,value.sourceFingerprint);
        for(const player of [0,1] as const)for(const mode of MODE_IDS){
          const extras=m.bonuses?.[player]?.[mode],base=presenterGames[player===0?'norman':'hattie'][mode].bonuses;
          if(extras?.length!==2||extras.some((b,i)=>b.correctChoice!==base[i].question.correctChoice))throw new Error('Invalid two-player bonuses');
        }
        library.twoPlayer=m;
      }
      if(value.extras){
        if(!value.extras.dataPath?.startsWith('/games/'))throw new Error('Invalid extras catalog');
        const extras=await get(value.extras.dataPath);validateCompleteExtrasData(extras,value.sourceFingerprint);library.extras=extras;
      }
      if(active)setData(library);
    }).catch(()=>{if(active)setError(true);});
    return ()=>{active=false;};
  },[]);
  if(error)return <main className="message"><p>The game could not load.</p><button onClick={()=>location.reload()}>Retry</button></main>;
  return data?<Game library={data}/>:<main className="message" role="status">Loading game…</main>;
}
