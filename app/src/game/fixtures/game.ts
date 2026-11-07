import type { GameData,GamePresentation,LevelData,GameQuestion,ChoiceId } from '../types';
export function gameFixture():GameData {
  const rect={x:73,y:274,width:441,height:34};
  const choices=Array.from('ABCD',id=>({id:id as ChoiceId,label:id,rect,highlightSrc:''}));
  const question=(id:string,expiry:'loop'|'timeout'):GameQuestion=>({id,text:id,kind:'single',expiry,
    correctChoice:'A',correctSequence:[],choices,promptScene:id,revealScene:null,durationSeconds:12.04,revealSeconds:3,
    windows:choices.map(c=>({choiceId:c.id,startTicks:0,endTicks:1083600,nextCandidateMask:1}))});
  const control={label:'Continue',rect,highlightSrc:'',windows:[{startTicks:0,endTicks:2700000}]};
  const levels:LevelData[]=[];
  for(let number=1;number<=8;number++){
    const questions=Array.from({length:16},(_,i)=>question(`q${number}-${i}`,number<4?'loop':'timeout'));
    const selection:LevelData['selection']={},answers:LevelData['answers']={},timeouts:LevelData['timeouts']={},endings:LevelData['endings']={};
    for(let variant=2;variant<=6;variant++)for(let i=0;i<16;i++){
      const mask=1<<i;
      if(variant<=4)selection[`${variant}:${mask}`]=[{questionId:questions[i].id,introScenes:[],variant}];
      timeouts[`${variant}:${mask}`]=number<4?[]:[{feedback:['feedback'],nextCandidateMask:2}];
      for(const outcome of ['correct','wrong'])for(let b=0;b<16;b++)for(const choice of 'ABCD')answers[`${variant}:${mask}:${outcome}:${1<<b}:${choice}`]=['feedback'];
      for(let prior=0;prior<=6*(number-1);prior++)for(let score=0;score<=6;score++){
        const p:GamePresentation={scenes:['outro'],destination:number<8?'next-level':prior+score===48?'bonus':'complete',nextCandidateMask:mask};
        if(number===1 && score===6){p.scenes=['score','gate'];p.gate={scene:'gate',control,loop:true,afterScenes:['outro']};}
        endings[`${score}:${prior+score}:${mask}`]=p;
      }
    }
    levels.push({number,questions,selection,answers,timeouts,endings,intros:{'1':[],'2':[]}});
  }
  const bonuses=['low','high'].map(name=>{
    const q=question(`bonus-${name}`,'timeout');q.correctChoice=name==='low'?'A':'C';
    return {id:`perfect-bonus-${name}`,introScenes:['bonus-intro'],question:q,
      correct:{scenes:['bonus-correct','bonus-gate'],gate:{scene:'bonus-gate',control,loop:false,afterScenes:['final-outro']},destination:'complete' as const,nextCandidateMask:0},
      wrong:{scenes:['bonus-wrong','final-outro'],destination:'complete' as const,nextCandidateMask:0}};
  });
  const ids=[...levels.flatMap(l=>l.questions.map(q=>q.promptScene)),...bonuses.map(b=>b.question.promptScene),
    'menu','feedback','score','gate','outro','bonus-intro','bonus-correct','bonus-gate','bonus-wrong','final-outro'];
  return {schemaVersion:2,sourceFingerprint:'fixture',scenes:ids.map(id=>({id,src:'',durationSeconds:1,kind:'clip',audioVariant:null})),
    entry:{boot:[],setupScenes:[],menus:[{id:'holly',scene:'menu',label:'Holly',rect,highlightSrc:'',windows:[{startTicks:0,endTicks:999999,candidateMask:1}]}]},levels,bonuses};
}
