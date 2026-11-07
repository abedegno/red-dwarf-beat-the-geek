import {expect,test} from 'vitest';
import {gameFixture} from './fixtures/game';
import {createPresenterGame,reducePresenterGame,type PresenterLibrary,type PresenterId} from './presenters';
import {MODE_IDS} from './modes';
function library():PresenterLibrary{
  const sets=Object.fromEntries(['norman','hattie'].map(p=>[p,Object.fromEntries(MODE_IDS.map(mode=>{
    const g=gameFixture(),menu=g.entry.menus[0];g.entry.menus=['main','player-type','holly'].map(id=>({...menu,id}));
    g.entry.menus[2].windows=[{startTicks:0,endTicks:90000,candidateMask:1}];
    if(p==='hattie')g.entry.setupOptions=[['setup-a'],['setup-b'],['setup-c']];
    for(const l of g.levels)for(const q of l.questions)q.correctChoice=p==='hattie'?'B':'A';
    return [mode,g];
  }))])) as PresenterLibrary['presenterGames'];
  return {games:sets.norman,controls:Object.fromEntries(MODE_IDS.map(id=>[id,sets.norman[id].entry.menus[1]])) as PresenterLibrary['controls'],
    labels:{viewer:'Viewer',geek:'Geek','general-knowledge':'General Knowledge'},presenterGames:sets};
}
for(const modeId of MODE_IDS)for(const presenterId of ['norman','hattie'] as PresenterId[])test(`${modeId} selects ${presenterId} with its own setup and answers`,()=>{
 const lib=library();let s=createPresenterGame(lib);
 const send=(e:Parameters<typeof reducePresenterGame>[2])=>{s=reducePresenterGame(lib,s,e,()=>.5);};
 send({type:'START'});send({type:'SCENE_READY',token:s.sceneToken});send({type:'MENU_CHOOSE',token:s.sceneToken,time:0});
 send({type:'SCENE_READY',token:s.sceneToken});send({type:'CHOOSE_MODE',modeId,token:s.sceneToken,time:0});send({type:'SCENE_READY',token:s.sceneToken});
 const token=s.sceneToken;send({type:'CHOOSE_PRESENTER',presenterId,token,time:0});expect(s.presenterId).toBe(presenterId);expect(s.modeId).toBe(modeId);
 if(presenterId==='hattie')expect(s.activeScene).toBe('setup-b');
 const chosen=s;send({type:'CHOOSE_PRESENTER',presenterId:presenterId==='hattie'?'norman':'hattie',token,time:0});expect(s).toBe(chosen);
 while(s.phase!=='question'){send({type:'SCENE_READY',token:s.sceneToken});send({type:'SCENE_ENDED',token:s.sceneToken});}
 send({type:'SCENE_READY',token:s.sceneToken});send({type:'ANSWER',token:s.sceneToken,choiceId:presenterId==='hattie'?'B':'A',time:0});expect(s.totalScore).toBe(1);
 const old=s.sceneToken;send({type:'RESET'});expect(s.presenterId).toBe('norman');expect(s.modeId).toBe('general-knowledge');expect(s.totalScore).toBe(0);expect(s.selection.usedMask).toBe(0);expect(s.sceneToken).toBeGreaterThan(old);
});
test('unready, early, stale and expired presenter choices are ignored',()=>{
 const lib=library();let s=createPresenterGame(lib);const event={type:'CHOOSE_PRESENTER' as const,presenterId:'hattie' as const,time:0,token:0};
 expect(reducePresenterGame(lib,s,event)).toBe(s);
 s={...s,phase:'menu',menuIndex:2,activeScene:'menu',sceneToken:5};
 expect(reducePresenterGame(lib,s,{...event,token:5})).toBe(s);
 s={...s,ready:true};expect(reducePresenterGame(lib,s,event)).toBe(s);expect(reducePresenterGame(lib,s,{...event,token:5,time:1})).toBe(s);
});
