import {expect,test,type Page} from '@playwright/test';
test.use({trace:'off'});
async function start(page:Page){
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
 await expect(page.getByRole('button',{name:'How to Play',exact:true})).toBeEnabled({timeout:90000});
}
test('original instructions offer timed captions and return to the four-area menu',async({page})=>{
 await start(page);await page.getByRole('button',{name:'How to Play',exact:true}).click();
 await expect(page.getByRole('button',{name:'Play With Subtitles',exact:true})).toBeEnabled();
 await page.getByRole('button',{name:'Play With Subtitles',exact:true}).click();
 const video=page.locator('video');await expect(video).toHaveJSProperty('readyState',4);
 await expect(page.locator('img.highlight')).toHaveCount(1,{timeout:7000});
 await page.screenshot({path:test.info().outputPath('instruction-caption.png')});
 await video.evaluate(v=>{(v as HTMLVideoElement).playbackRate=16;});
 await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:20000});
 await page.getByRole('button',{name:'How to Play',exact:true}).click();await page.getByRole('button',{name:'Play',exact:true}).click();
 await page.waitForTimeout(2500);await expect(page.locator('img.highlight')).toHaveCount(0);
});
test('keypad uses masked stages, accepts a known code, and Quit returns through the introduction',async({page})=>{
 await start(page);await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const digit of '1921'){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}
 await expect(page.getByRole('button',{name:'Quit',exact:true})).toBeEnabled({timeout:10000});
 await page.screenshot({path:test.info().outputPath('whack-menu.png')});await page.getByRole('button',{name:'Quit',exact:true}).click();
 await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});await page.getByRole('button',{name:'Menu',exact:true}).click();
 await expect(page.getByRole('button',{name:'How to Play',exact:true})).toBeEnabled();
});
