import { dataPath } from '../../test/data';
import {test,expect} from 'vitest';
import {readFileSync} from 'node:fs';
import {validateTwoPlayerData} from './twoPlayerValidation';
const load=()=>JSON.parse(readFileSync(dataPath('public/two-player.json'),'utf8'));
test('accepts the complete source export and rejects another disc',()=>{
 const m=load();validateTwoPlayerData(m,m.sourceFingerprint);
 expect(()=>validateTwoPlayerData(m,'different')).toThrow();
});
test('rejects missing turn media, scorecard cases and second-player bonuses before play',()=>{
 for(const corrupt of [(m:ReturnType<typeof load>)=>m.scenes.splice(0,1),(m:ReturnType<typeof load>)=>delete m.levels[7].scorecards[1]['6:48'],(m:ReturnType<typeof load>)=>m.bonuses[1].viewer.pop(),(m:ReturnType<typeof load>)=>m.levels[0].turns[0]=[]]){
  const m=load();corrupt(m);expect(()=>validateTwoPlayerData(m,m.sourceFingerprint)).toThrow();
 }
});
test('requires each scorecard carry to match its player and round score',()=>{
 for(const player of [0,1])for(const score of [0,3,5])for(const invalid of [undefined,-1,6,1.5,Number.NaN,player===0?5:0]){
  const m=load();const card=m.levels[3].scorecards[player][`${score}:${score}`];
  if(invalid===undefined)delete card.nextOrderingRepeatOffset;else card.nextOrderingRepeatOffset=invalid;
  expect(()=>validateTwoPlayerData(m,m.sourceFingerprint),`player ${player+1} score ${score} carry ${invalid}`).toThrow();
 }
});
