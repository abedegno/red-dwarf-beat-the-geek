import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.use({trace:'off'});
const data=JSON.parse(readFileSync(new URL('../../analysis/extras/gateway.json',import.meta.url),'utf8'));
test('original six-order Vending game and authored instruction stop',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
 await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 const code=async(value:string)=>{for(const digit of value){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}};
 await code('3598');const play=page.getByRole('button',{name:'Play',exact:true});await expect(play).toBeEnabled({timeout:10000});await play.click();
 for(let order=0;order<6;order++){
  const round=Math.floor(order/2),field=page.locator('fieldset[id^="vending-product-"]');
  await expect(field.locator('button:enabled').first()).toBeVisible({timeout:30000});
  for(let digit=0;digit<round+2;digit++){
   await expect(field.locator('button:enabled').first()).toBeVisible();
   const id=await field.getAttribute('id'),record=data.pages.find((p:{id:string})=>p.id===id);
   const control=record.controls.find((c:{variants:{action:{correct?:boolean}}[]})=>c.variants[0].action.correct);
   const next=control.variants[0].action.nextStage;await field.getByRole('button',{name:control.label,exact:true}).click();
   if(next!==null)await expect(field).not.toHaveAttribute('id',id!);else await expect(field).toHaveCount(0);
  }
  const success=data.pages.find((p:{id:string})=>p.id===data.vending.rounds[round].successPage);
  await expect(page.locator('video')).toHaveAttribute('src',data.scenes.find((s:{id:string})=>s.id===success.scene).src);
 }
 const ending=data.pages.find((p:{id:string})=>p.id===data.vending.completePage);
 await expect(page.locator('video')).toHaveAttribute('src',data.scenes.find((s:{id:string})=>s.id===ending.scene).src,{timeout:10000});
 await expect.poll(()=>page.locator('video').evaluate(v=>(v as HTMLVideoElement).currentTime)).toBeGreaterThan(1.5);
 await page.screenshot({path:test.info().outputPath('vending-complete.png')});
 await expect(play).toBeEnabled({timeout:15000});await page.getByRole('button',{name:'Quit',exact:true}).click();
 await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
 await code('1921');await expect(page.getByRole('button',{name:'Instructions',exact:true})).toBeEnabled({timeout:10000});await page.getByRole('button',{name:'Instructions',exact:true}).click();
 await expect(page.getByRole('button',{name:'Back',exact:true})).toBeEnabled();
 // Accelerate only the separate30s instruction-stop check; game footage used1x throughout.
 await page.locator('video').evaluate(v=>{(v as HTMLVideoElement).playbackRate=16;});
 await expect(page.getByRole('button',{name:'Back',exact:true})).toHaveCount(0,{timeout:10000});await expect(page.locator('video')).toHaveJSProperty('ended',true);
 await page.getByRole('button',{name:'Restart',exact:true}).click();await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
});
