import type { GameData,GameState,GameEvent,GamePhase,GameDestination,GamePresentation,GameQuestion,TimeoutOutcome } from './types';
import { selectQuestion } from './selection';

// Shared native transitions; session coordinators provide their own boundaries.
export {play as playGameScenes,presentation as playGamePresentation};

export function createGame(_data:GameData):GameState {
  return {phase:'idle',activeScene:null,sceneToken:0,ready:false,queue:[],destination:'menu',menuIndex:0,levelIndex:0,
    orderingRepeatOffset:0,promptCompleted:0,questionNumber:0,roundScore:0,totalScore:0,questionId:null,selection:{usedMask:0,candidateMask:1,variant:0},
    chosenAnswers:[],nextCandidateMask:1,currentPresentation:null,timeoutOutcome:null,bonusId:null};
}
export function currentQuestion(data:GameData,state:GameState):GameQuestion|null {
  if(state.bonusId)return data.bonuses.find(b=>b.id===state.bonusId)?.question??null;
  return data.levels[state.levelIndex].questions.find(q=>q.id===state.questionId)??null;
}
function timeoutChoice(data:GameData,state:GameState,draw:()=>number):TimeoutOutcome|null {
  const q=currentQuestion(data,state);
  if(q?.expiry!=='timeout')return null;
  const options=data.levels[state.levelIndex].timeouts[`${state.selection.variant}:${state.selection.candidateMask}`];
  if(!options?.length)throw new Error('Missing authored timeout path');
  return options.length===1?options[0]:options[Math.min(options.length-1,Math.floor(draw()*options.length))];
}
function play(data:GameData,s:GameState,phase:GamePhase,scenes:string[],destination:GameDestination,draw:()=>number):GameState {
  if(!scenes.length)return arrive(data,s,destination,draw);
  return {...s,phase,activeScene:scenes[0],queue:scenes.slice(1),destination,ready:false,sceneToken:s.sceneToken+1};
}
function presentation(data:GameData,s:GameState,p:GamePresentation,phase:'ending'|'bonus-feedback',draw:()=>number):GameState {
  return play(data,{...s,currentPresentation:p,nextCandidateMask:p.nextCandidateMask},phase,p.scenes,p.destination,draw);
}
function leaveGate(data:GameData,s:GameState,draw:()=>number):GameState {
  const {gate,...p}=s.currentPresentation!;
  return play(data,{...s,currentPresentation:p,ready:false},s.phase,gate!.afterScenes,p.destination,draw);
}
function arrive(data:GameData,s:GameState,destination:GameDestination,draw:()=>number):GameState {
  if(destination==='complete')return {...s,phase:'complete',ready:false,queue:[],currentPresentation:null};
  if(destination==='menu')return play(data,s,'menu',[data.entry.menus[s.menuIndex].scene],'menu',draw);
  if(destination==='question') {
    const q=currentQuestion(data,s);if(!q)throw new Error('Missing current question');
    return play(data,{...s,timeoutOutcome:timeoutChoice(data,s,draw)},'question',[q.promptScene],'question',draw);
  }
  if(destination==='bonus') {
    const bonus=data.bonuses.find(b=>b.id===(s.selection.variant<3?'perfect-bonus-low':'perfect-bonus-high'));
    if(!bonus)throw new Error('Missing perfect-game bonus');
    return play(data,{...s,bonusId:bonus.id,questionId:bonus.question.id,chosenAnswers:[],currentPresentation:null},'bonus-intro',bonus.introScenes,'bonus-question',draw);
  }
  if(destination==='bonus-question') {
    const q=currentQuestion(data,s);if(!q)throw new Error('Missing bonus question');
    return play(data,s,'bonus',[q.promptScene],'bonus-question',draw);
  }
  if(destination==='next-level') {
    const levelIndex=s.levelIndex+1,level=data.levels[levelIndex];if(!level)throw new Error('Unexpected extra level');
    const intros=level.intros[String(s.nextCandidateMask)];if(!intros)throw new Error('Missing next-level introduction');
    const next={...s,levelIndex,orderingRepeatOffset:s.currentPresentation?.nextOrderingRepeatOffset??(s.roundScore<3?0:s.roundScore<5?1:2),promptCompleted:0,questionNumber:0,roundScore:0,questionId:null,chosenAnswers:[],
      selection:{usedMask:0,candidateMask:s.nextCandidateMask,variant:data.randomized===false?s.selection.variant:0},currentPresentation:null,timeoutOutcome:null};
    return play(data,next,'entry',intros,'next-question',draw);
  }
  const level=data.levels[s.levelIndex];
  if(s.questionNumber>=6) {
    const p=level.endings[`${s.roundScore}:${s.totalScore}:${s.nextCandidateMask}`];
    if(!p)throw new Error('Missing source cumulative-score ending');
    return presentation(data,s,p,'ending',draw);
  }
  const selected=selectQuestion(level,{...s.selection,candidateMask:s.nextCandidateMask},draw,data.randomized!==false);
  const next={...s,questionNumber:s.questionNumber+1,questionId:selected.questionId,selection:selected.state,
    promptCompleted:0,chosenAnswers:[],timeoutOutcome:null,currentPresentation:null,bonusId:null};
  return play(data,next,'question-intro',selected.introScenes,'question',draw);
}

export function reduceGame(data:GameData,s:GameState,event:GameEvent,draw:()=>number=Math.random):GameState {
  if(event.type==='RESET')return {...createGame(data),sceneToken:s.sceneToken+1};
  if(event.type==='START')return s.phase==='idle'?play(data,s,'boot',data.entry.boot,'menu',draw):s;
  if(event.token!==s.sceneToken || !s.activeScene || s.phase==='complete')return s;
  if(event.type==='SCENE_READY')return {...s,ready:true};
  if(event.type==='SCENE_WAITING')return {...s,ready:false};
  if(event.type==='CONTINUE') {
    const gate=s.currentPresentation?.gate;
    if(!s.ready || gate?.scene!==s.activeScene || !gate.control.windows.some(w=>w.startTicks<=event.time*90000 && event.time*90000<w.endTicks))return s;
    return leaveGate(data,s,draw);
  }
  if(event.type==='SCENE_ENDED') {
    if(!s.ready)return s;
    if(s.phase==='question') {
      const q=currentQuestion(data,s)!;
      if(q.expiry==='loop')return {...s,sceneToken:s.sceneToken+1,ready:false};
      const repeated=(q.promptPlays??1)>1;
      if(repeated && s.orderingRepeatOffset+1<q.promptPlays!)return {...s,orderingRepeatOffset:s.orderingRepeatOffset+1,
        promptCompleted:s.promptCompleted+1,sceneToken:s.sceneToken+1,ready:false};
      const out=s.timeoutOutcome;if(!out)throw new Error('Missing selected timeout outcome');
      return play(data,{...s,orderingRepeatOffset:repeated?0:s.orderingRepeatOffset,nextCandidateMask:out.nextCandidateMask},'feedback',out.feedback,'next-question',draw);
    }
    if(s.phase==='bonus')return presentation(data,s,data.bonuses.find(b=>b.id===s.bonusId)!.wrong,'bonus-feedback',draw);
    const gate=s.currentPresentation?.gate;
    if(gate?.scene===s.activeScene)return gate.loop?{...s,sceneToken:s.sceneToken+1,ready:false}:leaveGate(data,s,draw);
    return play(data,s,s.phase,s.queue,s.destination,draw);
  }
  if(event.type==='MENU_CHOOSE') {
    if(s.phase!=='menu' || !s.ready)return s;
    const menu=data.entry.menus[s.menuIndex],window=menu.windows.find(w=>w.startTicks<=event.time*90000 && event.time*90000<w.endTicks);
    if(!window)return s;
    if(s.menuIndex<data.entry.menus.length-1)return arrive(data,{...s,menuIndex:s.menuIndex+1},'menu',draw);
    const intros=data.levels[0].intros[String(window.candidateMask)];if(!intros)throw new Error('Missing first-level introduction');
    const options=data.entry.setupOptions;
    const setup=options?.length?options[Math.min(options.length-1,Math.floor(draw()*options.length))]:data.entry.setupScenes;
    return play(data,{...s,nextCandidateMask:window.candidateMask},'entry',[...setup,...intros],'next-question',draw);
  }
  if(event.type==='ANSWER') {
    if(!s.ready || (s.phase!=='question' && s.phase!=='bonus'))return s;
    const q=currentQuestion(data,s);if(!q || !q.choices.some(c=>c.id===event.choiceId))return s;
    const window=q.windows.find(w=>w.choiceId===event.choiceId && w.startTicks<=event.time*90000 && event.time*90000<w.endTicks);
    if(!window)return s;
    const chosen=[...s.chosenAnswers,event.choiceId];
    if(q.kind==='sequence' && chosen.length<q.correctSequence.length) {
      const next={...s,chosenAnswers:chosen,sceneToken:s.sceneToken+1,ready:false};
      return {...next,timeoutOutcome:timeoutChoice(data,next,draw)};
    }
    const correct=q.kind==='sequence'?chosen.every((id,i)=>id===q.correctSequence[i]):event.choiceId===q.correctChoice;
    if(s.phase==='bonus')return presentation(data,{...s,chosenAnswers:chosen},data.bonuses.find(b=>b.id===s.bonusId)![correct?'correct':'wrong'],'bonus-feedback',draw);
    const candidate=window.nextCandidateMask || s.selection.candidateMask;
    const scenes=data.levels[s.levelIndex].answers[`${s.selection.variant}:${s.selection.candidateMask}:${correct?'correct':'wrong'}:${candidate}:${window.feedbackVariant??event.choiceId}`];
    if(!scenes)throw new Error('Missing source answer feedback');
    return play(data,{...s,chosenAnswers:chosen,nextCandidateMask:candidate,
      roundScore:s.roundScore+(correct?1:0),totalScore:s.totalScore+(correct?1:0)},'feedback',scenes,'next-question',draw);
  }
  return s;
}
