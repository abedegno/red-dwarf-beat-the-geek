import {expect,test,type Page} from '@playwright/test';
import {readFileSync} from 'node:fs';
test.use({trace:'off'});
const catalog=JSON.parse(readFileSync(new URL('../public/catalog.json',import.meta.url),'utf8'));
const extras=JSON.parse(readFileSync(new URL('../public'+catalog.extras.dataPath,import.meta.url),'utf8'));
function scene(id:string){const p=extras.pages.find((p:{id:string})=>p.id===id);return extras.scenes.find((s:{id:string})=>s.id===p.scene).src;}
async function main(page:Page){await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});}
async function code(page:Page,value:string){for(const digit of value){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}}
test('both complete instruction choices play at original speed and return to main',async({page})=>{
 const errors:string[]=[];page.on('pageerror',e=>errors.push(e.message));await main(page);
 for(const subtitles of [true,false]){
  await page.getByRole('button',{name:'How to Play',exact:true}).click();await page.getByRole('button',{name:subtitles?'Play With Subtitles':'Play',exact:true}).click();
  await expect(page.locator('video')).toHaveAttribute('src',scene('instructions-video'));
  if(subtitles){await expect(page.locator('img.highlight')).toHaveCount(1,{timeout:7000});await page.screenshot({path:test.info().outputPath('original-caption.png')});}
  else {await page.waitForTimeout(2500);await expect(page.locator('img.highlight')).toHaveCount(0);}
  await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:120000});
 }
 expect(errors).toEqual([]);
});
test('all five known codes work without earning them, Quit replays archive, partial and invalid return correctly',async({page})=>{
 await main(page);await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const [value,id] of Object.entries(extras.codes)){
  await code(page,value);await expect(page.locator('#'+extras.games[id as string].menuPage)).toBeAttached({timeout:10000});
  await page.getByRole('button',{name:'Quit',exact:true}).click();await expect(page.locator('video')).toHaveAttribute('src',scene('archive-intro'));await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
 }
 await code(page,'75');await page.getByRole('button',{name:'Menu',exact:true}).click();await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Games Archive',exact:true}).click();await code(page,'0000');await expect(page.locator('video')).toHaveAttribute('src',scene('invalid-code'),{timeout:10000});await expect(page.getByRole('button',{name:'How to Play',exact:true})).toBeEnabled({timeout:10000});
});
for(const engine of ['maze','whack','vending','memory','lager'])test(`reject missing ${engine} before enabling playback`,async({page})=>{
 await page.route('**'+catalog.extras.dataPath,route=>{const bad=structuredClone(extras);delete bad[engine];return route.fulfill({json:bad});});await page.goto('/');await expect(page.getByText('The game could not load.')).toBeVisible();await expect(page.getByRole('button',{name:'Play game',exact:true})).toHaveCount(0);
});
for(const [id,kind] of [['archive-intro','missing'],['keypad-confirm','missing'],['vending-success-0','missing'],['memory-result-0-47','missing'],['archive-intro','foreign-engine']])test(`reject malformed continuation ${id} ${kind} before playback`,async({page})=>{
 await page.route('**'+catalog.extras.dataPath,route=>{const bad=structuredClone(extras);bad.pages.find((p:{id:string})=>p.id===id).after=kind==='missing'?null:{type:'memory-next'};return route.fulfill({json:bad});});await page.goto('/');await expect(page.getByText('The game could not load.')).toBeVisible();await expect(page.getByRole('button',{name:'Play game',exact:true})).toHaveCount(0);
});
