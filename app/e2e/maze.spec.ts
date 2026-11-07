import {expect,test} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.use({trace:'off'});
const data=JSON.parse(readFileSync(new URL('../../analysis/extras/gateway.json',import.meta.url),'utf8'));
const traces=JSON.parse(readFileSync(new URL('../../analysis/extras/maze-traces.json',import.meta.url),'utf8')) as {name:string;steps:{event:{type:string;direction?:string};expected:{page:string;focus:number}}[]}[];
for(const trace of traces)test(`Black Holes original keyboard ${trace.name}`,async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
 await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const digit of '7523'){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}
 const play=page.getByRole('button',{name:'Play',exact:true});await expect(play).toBeEnabled({timeout:10000});await play.click();
 for(const {event,expected} of trace.steps){
  if(event.type==='SCENE_ENDED'){
   const src=page.locator('video');const target=data.scenes.find((s:{id:string})=>s.id===data.pages.find((p:{id:string})=>p.id===expected.page).scene).src;
   await expect(src).toHaveAttribute('src',target,{timeout:15000});
  }else{
   await expect(page.locator('.choices button:enabled').first()).toBeVisible({timeout:10000});
   await expect(page.locator('.choices button:focus')).toHaveCount(1);
   if(event.type==='MOVE')await page.keyboard.press('Arrow'+event.direction![0].toUpperCase()+event.direction!.slice(1));
   else await page.keyboard.press('Enter');
  }
 }
 const last=trace.steps.at(-1)!.expected;
 const target=data.scenes.find((s:{id:string})=>s.id===data.pages.find((p:{id:string})=>p.id===last.page).scene).src;
 await expect(page.locator('video')).toHaveAttribute('src',target);await expect(page.getByRole('button',{name:'Continue',exact:true})).toBeEnabled();
 await page.screenshot({path:test.info().outputPath(`maze-${trace.name}.png`)});
 await page.getByRole('button',{name:'Continue',exact:true}).click();await expect(play).toBeEnabled();
 await page.getByRole('button',{name:'Quit',exact:true}).click();await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
});
