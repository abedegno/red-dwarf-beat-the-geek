import {expect,test} from '@playwright/test';
test('loads the complete quiz catalog before Play',async({page})=>{
  const response=page.waitForResponse(r=>r.url().endsWith('/catalog.json'),{timeout:5000});
  await page.goto('/');expect((await response).ok()).toBe(true);
  await expect(page.getByRole('button',{name:'Play game',exact:true})).toBeVisible();
});
test('an unavailable mode prevents a partial game and offers Retry',async({page})=>{
  await page.route('**/games/geek-*',route=>route.abort());
  await page.goto('/');await expect(page.getByText('The game could not load.',{exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Retry',exact:true})).toBeVisible();
  await expect(page.getByRole('button',{name:'Play game',exact:true})).not.toBeVisible();
});
