import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.use({trace:'off'});
const data=JSON.parse(readFileSync(new URL('../../analysis/extras/gateway.json',import.meta.url),'utf8'));
for(const strategy of ['targets'] as const)test(`complete original Whack game ${strategy}`,async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
 await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const digit of '1921'){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}
 const play=page.getByRole('button',{name:'Play',exact:true});await expect(play).toBeEnabled({timeout:10000});await play.click();
 let score=0;
 for(let attempt=0;attempt<20;attempt++){
  await expect(page.getByRole('button',{name:'Hole 1',exact:true})).toBeEnabled({timeout:10000});
  const video=await page.locator('video').elementHandle();const src=await video!.getAttribute('src');
  const frame=data.pages.find((p:{id:string;scene:string})=>data.whack.positions.includes(p.id)&&data.scenes.find((s:{id:string})=>s.id===p.scene).src===src);
  expect(frame).toBeTruthy();const target=frame.controls.find((c:{variants:{action:{correct:boolean}}[]})=>c.variants[0].action.correct);
  if(target){await page.getByRole('button',{name:target.label,exact:true}).click();score++;}
  await expect.poll(()=>video!.evaluate(v=>v.isConnected),{timeout:10000}).toBe(false);
 }
 const result=data.pages.find((p:{id:string})=>p.id===data.whack.results[score]);const src=data.scenes.find((s:{id:string})=>s.id===result.scene).src;
 await expect(page.locator('video')).toHaveAttribute('src',src);await expect(page.getByRole('button',{name:'Hole 1',exact:true})).toHaveCount(0);
 await expect.poll(()=>page.locator('video').evaluate(v=>(v as HTMLVideoElement).currentTime)).toBeGreaterThan(1.5);
 await page.screenshot({path:test.info().outputPath('whack-result.png')});
 await expect(play).toBeEnabled({timeout:12000});await page.getByRole('button',{name:'Quit',exact:true}).click();
 await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
});
