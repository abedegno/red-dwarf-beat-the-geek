import type { QueueDestination, RoundData, RoundEvent, RoundState, Phase } from './types';
import { selectQuestion } from './selection';

export function createRound(_data: RoundData): RoundState {
  return {phase:'idle',activeScene:null,sceneToken:0,ready:false,queue:[],destination:'menu',
    menuIndex:0,questionNumber:0,score:0,questionId:null,
    selection:{usedMask:0,candidateMask:1,variant:0},chosenAnswers:[],nextCandidateMask:1,endingKey:null};
}

function play(data:RoundData,state:RoundState,phase:Phase,scenes:string[],destination:QueueDestination,draw:()=>number):RoundState {
  if(!scenes.length)return arrive(data,state,destination,draw);
  return {...state,phase,activeScene:scenes[0],queue:scenes.slice(1),destination,
    ready:false,sceneToken:state.sceneToken+1};
}

function arrive(data:RoundData,state:RoundState,destination:QueueDestination,draw:()=>number):RoundState {
  if(destination==='complete')return {...state,phase:'complete',ready:false,queue:[]};
  if(destination==='menu')return play(data,state,'menu',[data.entry.menus[state.menuIndex].scene],'menu',draw);
  if(destination==='question') {
    const question=data.questions.find(q=>q.id===state.questionId);
    if(!question)throw new Error('Missing current question');
    return play(data,state,'question',[question.promptScene],'question',draw);
  }
  if(state.questionNumber>=6) {
    const key=`${state.score}:${state.nextCandidateMask}`;
    const ending=data.feedback.endings[key];
    if(!ending)throw new Error('Missing round completion presentation');
    return play(data,{...state,endingKey:key},'ending',ending.scenes,'complete',draw);
  }
  const selection=selectQuestion(data,{...state.selection,candidateMask:state.nextCandidateMask},draw);
  const next={...state,questionNumber:state.questionNumber+1,questionId:selection.questionId,
    selection:selection.state,chosenAnswers:[]};
  return play(data,next,'question-intro',selection.introScenes,'question',draw);
}

export function reduceRound(data:RoundData,state:RoundState,event:RoundEvent,draw:()=>number=Math.random):RoundState {
  if(event.type==='RESET')return {...createRound(data),sceneToken:state.sceneToken+1};
  if(event.type==='START')return state.phase==='idle'?play(data,state,'boot',data.entry.boot,'menu',draw):state;
  if(event.token!==state.sceneToken || !state.activeScene)return state;
  if(event.type==='SCENE_READY')return {...state,ready:true};
  if(event.type==='SCENE_WAITING')return {...state,ready:false};
  if(event.type==='SCENE_ENDED') {
    if(state.phase==='question' || state.phase==='menu')return {...state,sceneToken:state.sceneToken+1,ready:false};
    const ending=state.endingKey?data.feedback.endings[state.endingKey]:null;
    if(state.phase==='ending' && ending?.loopScene===state.activeScene)return {...state,sceneToken:state.sceneToken+1,ready:false};
    return play(data,state,state.phase,state.queue,state.destination,draw);
  }
  if(event.type==='CONTINUE') {
    const ending=state.endingKey?data.feedback.endings[state.endingKey]:null;
    return state.ready && state.phase==='ending' && ending?.loopScene===state.activeScene
      ?{...state,phase:'complete',ready:false}:state;
  }
  if(event.type==='MENU_CHOOSE') {
    if(state.phase!=='menu' || !state.ready)return state;
    const menu=data.entry.menus[state.menuIndex];
    const window=menu.windows.filter(w=>w.startTicks<=event.time*90000 && event.time*90000<w.endTicks).at(-1);
    if(!window)return state;
    if(state.menuIndex<data.entry.menus.length-1)return arrive(data,{...state,menuIndex:state.menuIndex+1},'menu',draw);
    const candidate=window.candidateMask;
    const intro=data.entry.roundIntros[String(candidate)];
    if(!intro)throw new Error('Missing level introduction');
    return play(data,{...state,nextCandidateMask:candidate},'entry',[...data.entry.setupScenes,...intro],'next-question',draw);
  }
  if(event.type==='ANSWER') {
    if(state.phase!=='question' || !state.ready)return state;
    const question=data.questions.find(q=>q.id===state.questionId);
    if(!question || !question.choices.some(c=>c.id===event.choiceId))return state;
    const window=question.windows.filter(w=>w.choiceId===event.choiceId && w.startTicks<=event.time*90000 && event.time*90000<w.endTicks).at(-1);
    if(!window)return state;
    const chosen=[...state.chosenAnswers,event.choiceId];
    if(question.kind==='sequence' && chosen.length<question.correctSequence.length) {
      return {...state,chosenAnswers:chosen,sceneToken:state.sceneToken+1,ready:false};
    }
    const correct=question.kind==='sequence'
      ?chosen.every((answer,index)=>answer===question.correctSequence[index])
      :event.choiceId===question.correctChoice;
    const candidate=window.nextCandidateMask || state.selection.candidateMask;
    const key=`${state.selection.variant}:${state.selection.candidateMask}:${correct?'correct':'wrong'}:${candidate}`;
    const scenes=data.feedback.answers[key];
    if(!scenes)throw new Error('Missing normalized feedback path');
    return play(data,{...state,chosenAnswers:chosen,nextCandidateMask:candidate,score:state.score+(correct?1:0)},
      'feedback',scenes,'next-question',draw);
  }
  return state;
}
