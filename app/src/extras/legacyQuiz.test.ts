import {expect,test} from 'vitest';
import {sessionLibrary} from './legacyQuiz';
import {createSession,reduceSession,type SessionLibrary} from './session';
import {gameFixture} from '../game/fixtures/game';
import {gatewayFixture} from './gatewayFixture';
import type {PresenterLibrary} from '../game/presenters';
import {MODE_IDS} from '../game/modes';
function fixture():SessionLibrary{
 const g=gameFixture(),menu=g.entry.menus[0];g.entry.menus=['main','mode','holly'].map(id=>({...menu,id,windows:[{startTicks:0,endTicks:900000,candidateMask:14}]}));
 g.entry.menus[2].windows[0].candidateMask=1;g.entry.setupOptions=[['random-a'],['random-b']];
 const games=Object.fromEntries(MODE_IDS.map(id=>[id,g])) as PresenterLibrary['games'];
 const cue=[{startTicks:0,endTicks:900000,variantCue:3}];const extras=gatewayFixture();extras.quizEntry={mainOne:[{startTicks:0,endTicks:900000,selectionSeed:14}],holly:{norman:cue,hattie:cue},secondMode:{viewer:cue,geek:cue,'general-knowledge':cue},setups:{'14':{norman:['norman-fixed'],hattie:['hattie-fixed'],two:['two-fixed']}}};
 return {games,presenterGames:{norman:games,hattie:games},labels:{viewer:'Viewer',geek:'Geek','general-knowledge':'General Knowledge'},controls:Object.fromEntries(MODE_IDS.map(id=>[id,g.entry.menus[1]])) as PresenterLibrary['controls'],extras};
}
test('legacy runtime overlay uses fixed setup clips while accepted payload objects remain intact',()=>{
 const library=fixture(),before=JSON.stringify(library);let s=createSession(library);s={...s,entrySeed:14,context:{...s.context,randomized:false}};
 const effective=sessionLibrary(library,s);expect(effective.presenterGames.norman.viewer.randomized).toBe(false);expect(effective.presenterGames.hattie.geek.entry.setupScenes).toEqual(['hattie-fixed']);expect(effective.presenterGames.hattie.geek.entry.setupOptions).toBeUndefined();expect(JSON.stringify(library)).toBe(before);
 expect(sessionLibrary(library,createSession(library))).toBe(library);
});
test('one-player entry seeds the legacy variant from Main and Holly source cues',()=>{
 const library=fixture();let s=createSession(library);s={...s,context:{...s.context,randomized:false},quiz:{...s.quiz,phase:'menu',menuIndex:0,ready:true,activeScene:'menu'}};
 s=reduceSession(library,s,{type:'MENU_CHOOSE',token:s.quiz.sceneToken,time:1});expect(s.entrySeed).toBe(14);expect(s.quiz.selection.variant).toBe(2);
 s=reduceSession(library,s,{type:'SCENE_READY',token:s.quiz.sceneToken});s=reduceSession(library,s,{type:'CHOOSE_MODE',token:s.quiz.sceneToken,time:1,modeId:'viewer'});
 s=reduceSession(library,s,{type:'SCENE_READY',token:s.quiz.sceneToken});s=reduceSession(library,s,{type:'CHOOSE_PRESENTER',token:s.quiz.sceneToken,time:1,presenterId:'hattie'});
 expect(s.quiz.selection.variant).toBe(1);expect(s.quiz.activeScene).toBe('hattie-fixed');
});
