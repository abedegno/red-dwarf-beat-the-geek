import {expect,test} from '@playwright/test';
for(const name of ['Norman Lovett’s Holly','Hattie Hayridge’s Holly'])test(`${name} occupies its original artwork region`,async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
 for(const label of ['One player','Viewer']){const b=page.getByRole('button',{name:label,exact:true});await expect(b).toBeEnabled({timeout:90000});await b.tap();}
 const b=page.getByRole('button',{name,exact:true});await expect(b).toBeEnabled({timeout:5000});
 const stage=(await page.getByLabel('Game screen',{exact:true}).boundingBox())!;
 const x=stage.x+stage.width*(name.startsWith('Hattie')?500:220)/720,y=stage.y+stage.height*280/576;
 expect(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.getAttribute('aria-label'),{x,y})).toBe(name);
 await b.focus();await b.press('ArrowRight');await page.keyboard.press('ArrowLeft');await expect(b).toBeFocused();
 await page.screenshot({path:test.info().outputPath('holly-menu.png')});
 await page.touchscreen.tap(x,y);await expect(page.locator('footer')).toContainText(name.startsWith('Hattie')?'Hattie Holly':'Norman Holly');
});
