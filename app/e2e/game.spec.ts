import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
import type {GameData} from '../src/game/types';
const data=JSON.parse(readFileSync(new URL('../public/game.json',import.meta.url),'utf8')) as GameData;
test('complete original-paced eight-level game and perfect bonus',async({page})=>{
  test.setTimeout(3600000);
  const failures:string[]=[],requests:string[]=[];
  page.on('pageerror',e=>failures.push(e.message));page.on('request',r=>requests.push(r.url()));
  await page.goto('/');await expect(page.locator('footer')).toContainText('Level 1 of 8');
  await page.getByRole('button',{name:'Play game',exact:true}).click();
  for(const name of ['One player','General Knowledge','Norman Lovett’s Holly']){
    const b=page.getByRole('button',{name,exact:true});await expect(b).toBeEnabled({timeout:90000});await b.click();
  }
  let answered=0,bonus=false;
  const deadline=Date.now()+3400000;
  while(Date.now()<deadline){
    const status=page.getByRole('status',{name:'Round status'});
    if((await status.textContent())?.includes('Game complete.'))break;
    const group=page.locator('fieldset');
    if(await group.isVisible()){
      const id=await group.getAttribute('id');
      const q=data.levels.flatMap(l=>l.questions).find(q=>q.id===id)??data.bonuses.find(b=>b.question.id===id)?.question;
      expect(q).toBeTruthy();
      const ids=q!.kind==='sequence'?q!.correctSequence:[q!.correctChoice!];
      for(const choice of ids){
        const c=q!.choices.find(c=>c.id===choice)!;
        const b=group.getByRole('button',{name:`${choice}. ${c.label}`,exact:true});
        await expect(b).toBeEnabled({timeout:90000});await b.tap();
        if(ids.length>1)await page.waitForTimeout(200);
      }
      if(id?.startsWith('perfect-bonus'))bonus=true;else answered++;
      console.log('Answered',answered,id);
      await expect(group).not.toBeVisible({timeout:5000});
      await expect(status).toContainText(`Total ${answered} of 48`);
    }else{
      const proceed=page.getByRole('button',{name:'Continue',exact:true});
      if(await proceed.isVisible() && await proceed.isEnabled())await proceed.tap();
      await page.waitForTimeout(250);
    }
  }
  expect(answered).toBe(48);expect(bonus).toBe(true);
  await expect(page.getByRole('status',{name:'Round status'})).toContainText('Game complete.');
  expect(failures).toEqual([]);expect(requests.filter(u=>/\.(ifo|vob|bup|wasm)(\?|$)/i.test(u))).toEqual([]);
  await page.screenshot({path:test.info().outputPath('complete.png')});
  await page.getByRole('button',{name:'Restart',exact:true}).click();
  await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
});
