import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.use({trace:'off'});
const data=JSON.parse(readFileSync(new URL('../../analysis/extras/gateway.json',import.meta.url),'utf8'));
for(const strategy of ['success','decoy','expiry'] as const)test(`original Lager ${strategy} with timed keyboard pointer and touch shots`,async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const digit of '7148'){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}
 const play=page.getByRole('button',{name:'Play',exact:true});await expect(play).toBeEnabled({timeout:10000});await play.click();
 const stages=strategy==='success'?10:strategy==='decoy'?3:1;
 for(let stage=1;stage<=stages;stage++){
  const p=data.pages.find((p:{id:string})=>p.id===`lager-aim-${stage}`),src=data.scenes.find((s:{id:string})=>s.id===p.scene).src;
  await expect(page.locator('video')).toHaveAttribute('src',src,{timeout:20000});const video=await page.locator('video').elementHandle();
  await expect(page.getByRole('button',{name:'Fire',exact:true})).toHaveCount(0);
  if(strategy==='expiry')await expect.poll(()=>video!.evaluate(v=>v.isConnected),{timeout:35000}).toBe(false);
  else {
   const variant=p.controls[0].variants.find((v:{action:{page:string}})=>strategy==='decoy'&&stage===3?v.action.page==='lager-fail':v.action.page===`lager-hit-${stage}`);
   await page.waitForFunction(start=>(document.querySelector('video')?.currentTime??0)>=start,variant.startTicks/90000,{polling:15,timeout:35000});
   const fire=page.getByRole('button',{name:'Fire',exact:true});await expect(fire).toBeEnabled();
   if(stage%3===1){await expect(fire).toBeFocused();await page.keyboard.press('Enter');}
   else if(stage%3===2)await fire.tap();else await fire.click();
   await expect.poll(()=>video!.evaluate(v=>v.isConnected),{timeout:3000}).toBe(false);
  }
 }
 if(strategy!=='success'){const p=data.pages.find((p:{id:string})=>p.id==='lager-fail');await expect(page.locator('video')).toHaveAttribute('src',data.scenes.find((s:{id:string})=>s.id===p.scene).src);}
 else {const ending=data.pages.find((p:{id:string})=>p.id==='lager-transition-10');await expect(page.locator('video')).toHaveAttribute('src',data.scenes.find((s:{id:string})=>s.id===ending.scene).src,{timeout:10000});await expect.poll(()=>page.locator('video').evaluate(v=>(v as HTMLVideoElement).currentTime)).toBeGreaterThan(1.5);await page.screenshot({path:test.info().outputPath('lager-complete.png')});}
 await expect(play).toBeEnabled({timeout:20000});await page.getByRole('button',{name:'Quit',exact:true}).click();await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
});
