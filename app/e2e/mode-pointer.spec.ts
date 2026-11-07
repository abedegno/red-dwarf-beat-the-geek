import {expect,test} from '@playwright/test';
test.describe.configure({mode:'parallel'});
// Centers are independently measured from original DVD artwork in720×576 space.
for(const [mode,y] of [['Viewer',220],['Geek',280]] as const)test(`${mode} selects from its visible source label`,async({page})=>{
  await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
  const one=page.getByRole('button',{name:'One player',exact:true});await expect(one).toBeEnabled({timeout:90000});await one.tap();
  await expect(page.getByRole('button',{name:mode,exact:true})).toBeEnabled({timeout:90000});
  if(mode==='Viewer'){
    const viewer=page.getByRole('button',{name:'Viewer',exact:true});await viewer.focus();await viewer.press('ArrowDown');
    await expect(page.getByRole('button',{name:'Geek',exact:true})).toBeFocused();await page.keyboard.press('ArrowUp');await expect(viewer).toBeFocused();
  }
  await page.getByRole('button',{name:mode,exact:true}).focus();
  await page.screenshot({path:test.info().outputPath('mode-menu.png')});
  const stage=(await page.getByLabel('Game screen',{exact:true}).boundingBox())!;
  const x=stage.x+stage.width*360/720,screenY=stage.y+stage.height*y/576;
  expect(await page.evaluate(({x,y})=>document.elementFromPoint(x,y)?.getAttribute('aria-label'),{x,y:screenY})).toBe(mode);
  await page.touchscreen.tap(x,screenY);
  await expect(page.locator('footer')).toContainText(`One player · ${mode} ·`);
  await expect(page.getByRole('button',{name:'Norman Lovett’s Holly',exact:true})).toBeVisible({timeout:90000});
});
