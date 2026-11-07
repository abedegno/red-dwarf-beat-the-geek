import {expect,test} from 'vitest';
import {createSession,reduceSession,type SessionLibrary} from './session';
import {gatewayFixture} from './gatewayFixture';
import {gameFixture} from '../game/fixtures/game';
import {MODE_IDS} from '../game/modes';
import type {PresenterLibrary} from '../game/presenters';
function library():SessionLibrary {
 const game=gameFixture();game.entry.menus=['main','mode','holly'].map(id=>({...game.entry.menus[0],id}));
 const games=Object.fromEntries(MODE_IDS.map(id=>[id,game])) as PresenterLibrary['games'];
 const extras=gatewayFixture();for(const c of Object.values(extras.main))c.windows=[{startTicks:0,endTicks:90000,selectionSeed:9}];
 return {games,presenterGames:{norman:games,hattie:games},labels:{viewer:'Viewer',geek:'Geek','general-knowledge':'General Knowledge'},controls:Object.fromEntries(MODE_IDS.map(id=>[id,game.entry.menus[1]])) as PresenterLibrary['controls'],extras};
}
test('scopes quiz and extras callbacks across entry, return and Restart',()=>{
 const lib=library();let s=createSession(lib);s=reduceSession(lib,s,{type:'START'});s=reduceSession(lib,s,{type:'SCENE_READY',token:s.quiz.sceneToken});
 const token=s.quiz.sceneToken;s=reduceSession(lib,s,{type:'OPEN_EXTRA',branch:'instructions',token,time:0});expect(s.extra?.context.selectionSeed).toBe(9);
 const active=s;expect(reduceSession(lib,s,{type:'MENU_CHOOSE',token,time:0})).toBe(active);
 s=reduceSession(lib,s,{type:'EXTRA',event:{type:'SCENE_READY',token:s.extra!.sceneToken}});
 s=reduceSession(lib,s,{type:'EXTRA',event:{type:'ACTIVATE',token:s.extra!.sceneToken,controlId:3,time:.2}});
 expect(s.extra).toBe(null);expect(s.quiz.phase).toBe('menu');expect(s.quiz.sceneToken).toBeGreaterThan(token+1);
 const returned=s;expect(reduceSession(lib,s,{type:'EXTRA',event:{type:'SCENE_ENDED',token:token+1}})).toBe(returned);
 expect(reduceSession(lib,s,{type:'MENU_CHOOSE',token,time:0}).quiz).toBe(s.quiz);
 s={...s,context:{...s.context,randomized:false}};s=reduceSession(lib,s,{type:'RESET'});expect(s.quiz.phase).toBe('idle');expect(s.context.randomized).toBe(true);
});
test('entry requires the original main-menu time window and readiness',()=>{
 const lib=library(),s=createSession(lib),e={type:'OPEN_EXTRA' as const,branch:'archive' as const,token:0,time:0};
 expect(reduceSession(lib,s,e)).toBe(s);
 const menu={...s,quiz:{...s.quiz,phase:'menu' as const,ready:true,menuIndex:0}};
 for(const event of [{...e,time:1},{...e,token:999},{...e,time:NaN}])expect(reduceSession(lib,menu,event)).toBe(menu);
});
