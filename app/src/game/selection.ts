import type { RoundData, SelectionResult, SelectionState } from './types';

export function selectQuestion(data: Pick<RoundData,'selection'>, state: SelectionState, draw: () => number, randomized=true): SelectionResult {
  let candidate = state.candidateMask;
  if(candidate < 1 || candidate > 32768 || (candidate & (candidate-1)) !== 0) throw new Error('Invalid selection candidate');
  let variant = randomized?Math.min(3, Math.floor(draw()*3)+1):state.variant;
  for(let attempt=0;attempt<16;attempt++) {
    variant++;
    if(variant<=1 || variant>4)variant=2;
    if(!(state.usedMask & candidate)) {
      const options=data.selection[`${variant}:${candidate}`];
      if(!options?.length)throw new Error('Missing normalized selection route');
      const option=options.length===1?options[0]:options[Math.min(options.length-1,Math.floor(draw()*options.length))];
      return {questionId:option.questionId,introScenes:option.introScenes,
        state:{usedMask:state.usedMask|candidate,candidateMask:candidate,variant:option.variant}};
    }
    // These are two sequential source conditions, not conventional bit rotation.
    if(candidate>=32768)candidate=1;
    if(candidate<32768)candidate*=2;
  }
  throw new Error('No unused selection slot is reachable');
}
