import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
import type {GameData} from '../src/game/types';
test.use({trace:'off'});
const playbackRate=Number(process.env.GAME_SPEED??1);
const files=['game.json','game-viewer.json','game-geek.json','game-hattie.json','game-viewer-hattie.json','game-geek-hattie.json'];
const games=files.map(f=>JSON.parse(readFileSync(new URL('../public/'+f,import.meta.url),'utf8')) as GameData);
const label=(id:string)=>id==='general-knowledge'?'General Knowledge':id==='viewer'?'Viewer':'Geek';
async function choose(page:import('@playwright/test').Page,name:string){const b=page.getByRole('button',{name,exact:true});await expect(b).toBeEnabled({timeout:90000});await b.click();}
test('two-player original menus accept independent modes and restart safely',async({page})=>{
 const failures:string[]=[];page.on('pageerror',e=>failures.push(e.message));
 await page.goto('/');await choose(page,'Play game');await choose(page,'Two players');
 await expect(page.getByRole('group',{name:'Player 1 quiz mode'})).toBeVisible();
 await choose(page,'Viewer');await expect(page.getByRole('group',{name:'Player 2 quiz mode'})).toBeVisible();
 await choose(page,'Geek');await expect(page.locator('footer')).toContainText('Two players · Player 1');
 await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
 expect(failures).toEqual([]);
});

test('missing two-player data prevents a partial game and offers Retry',async({page})=>{
 await page.route('**/games/two-player-*',route=>route.abort());await page.goto('/');
 await expect(page.getByText('The game could not load.',{exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Retry',exact:true})).toBeVisible();
 await expect(page.getByRole('button',{name:'Play game',exact:true})).not.toBeVisible();
});
test(`two-player complete ${playbackRate===1?'original-paced':playbackRate+'x media'} game, both scorecards and bonuses`,async({page},info)=>{
 test.setTimeout(7200000);
 const pair=info.project.name==='webkit'?['viewer','geek']:['general-knowledge','general-knowledge'];
 const failures:string[]=[],requests:string[]=[];page.on('pageerror',e=>failures.push(e.message));page.on('request',r=>requests.push(r.url()));
 if(playbackRate!==1)await page.addInitScript(rate=>document.addEventListener('play',e=>{if(e.target instanceof HTMLVideoElement)e.target.playbackRate=rate;},true),playbackRate);
 await page.goto('/');await choose(page,'Play game');await choose(page,'Two players');for(const mode of pair)await choose(page,label(mode));
 let count=0;const bonuses:number[]=[],turns:number[]=[],deadline=Date.now()+6900000;
 while(Date.now()<deadline){
  const status=page.getByRole('status',{name:'Round status'});
  if((await status.textContent())?.includes('Game complete.'))break;
  const group=page.locator('fieldset');
  if(await group.isVisible()){
   const id=await group.getAttribute('id'),footer=await page.locator('footer > span').first().textContent();
   const player=footer?.includes('Player 1')?0:1;
   const data=games[(player===0?0:3)+(['general-knowledge','viewer','geek'].indexOf(pair[player]))];
   const q=data.levels.flatMap(l=>l.questions).find(q=>q.id===id)??data.bonuses.find(b=>b.question.id===id)?.question;
   expect(q,`${id} for player ${player+1}`).toBeTruthy();
   for(const choice of q!.kind==='sequence'?q!.correctSequence:[q!.correctChoice!]){
    const c=q!.choices.find(c=>c.id===choice)!;const b=group.getByRole('button',{name:`${choice}. ${c.label}`,exact:true});
    await expect(b).toBeEnabled({timeout:90000});await b.click();if(q!.kind==='sequence')await page.waitForTimeout(200/playbackRate);
   }
   if(id?.startsWith('perfect-bonus'))bonuses.push(player);else{turns.push(player);count++;}
   console.log(JSON.stringify({count,player,id,footer}));
   await expect(group).not.toBeVisible({timeout:5000});
   if(count===1||count===2||bonuses.length)await page.screenshot({path:info.outputPath(`turn-${count}-bonus-${bonuses.length}.png`)});
  }else{
   const b=page.getByRole('button',{name:'Continue',exact:true});if(await b.isVisible()&&await b.isEnabled())await b.click();
   await page.waitForTimeout(250);
  }
 }
 expect(count).toBe(96);expect(turns).toEqual(Array.from({length:96},(_,i)=>i%2));expect(bonuses).toEqual([0,1]);
 await expect(page.getByLabel('Player scores',{exact:true})).toHaveText('Player 1: 48 · Player 2: 48');
 await expect(page.getByRole('status',{name:'Round status'})).toContainText('Game complete.');
 expect(failures).toEqual([]);expect(requests.filter(u=>/\.(ifo|vob|bup|wasm)(\?|$)/i.test(u))).toEqual([]);
 await page.screenshot({path:info.outputPath('complete.png')});
 await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
});
