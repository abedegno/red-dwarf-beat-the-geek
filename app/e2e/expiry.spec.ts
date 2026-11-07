import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
import type {GameData} from '../src/game/types';
const data=JSON.parse(readFileSync(new URL('../public/game.json',import.meta.url),'utf8')) as GameData;
test('late-level unanswered prompt expires with no point and restart clears progress',async({page})=>{
  test.setTimeout(1500000);
  await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
  for(const name of ['One player','General Knowledge','Norman Lovett’s Holly']){
    const b=page.getByRole('button',{name,exact:true});await expect(b).toBeEnabled({timeout:90000});await b.click();
  }
  let answered=0;
  while(answered<18){
    const group=page.locator('fieldset');
    if(await group.isVisible()){
      // Read the real source question rather than injecting engine state.
      const id=await group.getAttribute('id');const question=data.levels.flatMap(l=>l.questions).find(q=>q.id===id)!;
      for(const choice of question.kind==='sequence'?question.correctSequence:[question.correctChoice!]){
        const c=question.choices.find(c=>c.id===choice)!;
        const b=group.getByRole('button',{name:`${choice}. ${c.label}`,exact:true});
        await expect(b).toBeEnabled({timeout:90000});await b.click();await page.waitForTimeout(200);
      }
      answered++;await expect(group).not.toBeVisible({timeout:5000});
    }else{
      const next=page.getByRole('button',{name:'Continue',exact:true});
      if(await next.isVisible() && await next.isEnabled())await next.click();
      await page.waitForTimeout(250);
    }
  }
  const group=page.locator('fieldset');const deadline=Date.now()+150000;
  while(!await group.isVisible() && Date.now()<deadline){
    const next=page.getByRole('button',{name:'Continue',exact:true});
    if(await next.isVisible() && await next.isEnabled())await next.click();
    await page.waitForTimeout(250);
  }
  await expect(group).toBeVisible();
  const id=await group.getAttribute('id');expect(id).toMatch(/^gk-l4-/);
  const q=data.levels[3].questions.find(q=>q.id===id)!;expect(q.expiry).toBe('timeout');
  await page.evaluate(id=>{
    (window as unknown as {promptEnds:number}).promptEnds=0;
    document.addEventListener('ended',event=>{
      if(event.target instanceof HTMLVideoElement && document.querySelector('fieldset')?.id===id)
        (window as unknown as {promptEnds:number}).promptEnds++;
    },true);
  },id);
  await expect(group).not.toHaveAttribute('id',id!,{timeout:100000});
  const expectedPlays=(q.promptPlays??1)>1?q.promptPlays!-2:1;
  expect(await page.evaluate(()=>(window as unknown as {promptEnds:number}).promptEnds)).toBe(expectedPlays);
  const status=page.getByRole('status',{name:'Round status'});
  await expect(status).toContainText('Total 18 of 48');
  await expect(status).toContainText('Question 2 of 6',{timeout:90000});
  await expect(status).toContainText('Score 0 of 6');
  await page.getByRole('button',{name:'Restart',exact:true}).click();
  await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
  await expect(status).toContainText('Total 0 of 48');
});
