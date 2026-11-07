import { expect, test, type APIRequestContext } from '@playwright/test';
import type { GameData } from '../src/game/types';

test.use({ trace: 'off' });

async function catalog(request: APIRequestContext) {
  const response = await request.get('/catalog.json');
  expect(response.ok()).toBe(true);
  return response.json();
}

async function choose(page: import('@playwright/test').Page, name: string) {
  const button = page.getByRole('button', { name, exact: true });
  await expect(button).toBeEnabled({ timeout: 90000 });
  await button.click();
}

test('complete hosted catalog, missing-file404 and video delivery', async ({ page, request }) => {
  const data = await catalog(request);
  expect(Object.keys(data.modes)).toHaveLength(3);
  expect(Object.keys(data.hattieModes)).toHaveLength(3);
  expect(data.twoPlayer.dataPath).toBeTruthy();
  expect(data.extras.dataPath).toBeTruthy();
  const game = await (await request.get(data.modes['general-knowledge'].dataPath)).json();
  const response = await request.get(game.scenes[0].src, { headers: { Range: 'bytes=0-1023' } });
  expect(response.headers()['content-type']).toContain('video/mp4');
  if (response.status() === 200 && process.env.BTG_ALLOW_FULL_MEDIA_RESPONSE === '1') {
    // Pages currently ignores Range. Require the complete, unchanged MP4;
    // this explicit host exception must never accept a truncated response.
    const complete = await request.get(game.scenes[0].src);
    expect(complete.status()).toBe(200);
    const body = await response.body();
    expect(body.equals(await complete.body())).toBe(true);
    expect(body.length).toBeGreaterThan(1024);
    expect(Number(response.headers()['content-length'])).toBe(body.length);
    expect(body.subarray(4, 8).toString()).toBe('ftyp');
  } else {
    expect(response.status()).toBe(206);
    expect(response.headers()['content-range']).toMatch(/^bytes 0-1023\//);
    expect((await response.body()).length).toBe(1024);
  }
  expect((await request.get('/media/nonexistent-deployment-check.mp4')).status()).toBe(404);
  await page.goto('/');
  await expect(page.getByRole('button', { name: 'Play game', exact: true })).toBeVisible();
});

for (const kind of ['mode', 'twoPlayer', 'extras'] as const) {
  test(`unavailable hosted ${kind} data prevents partial playback`, async ({ page, request }) => {
    const data = await catalog(request);
    const path = kind === 'mode' ? data.modes.geek.dataPath : data[kind].dataPath;
    await page.route('**' + path, route => route.abort());
    await page.goto('/');
    await expect(page.getByText('The game could not load.', { exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Retry', exact: true })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Play game', exact: true })).toHaveCount(0);
  });
}

for (const presenter of ['norman', 'hattie'] as const) {
  test(`hosted ${presenter} quiz plays and accepts its first source answer`, async ({ page, request }) => {
    const failures: string[] = [];
    page.on('pageerror', error => failures.push(error.message));
    const data = await catalog(request);
    const entry = (presenter === 'norman' ? data.modes : data.hattieModes)['general-knowledge'];
    const game = await (await request.get(entry.dataPath)).json() as GameData;
    await page.goto('/');
    for (const name of ['Play game', 'One player', 'General Knowledge', presenter === 'norman' ? 'Norman Lovett’s Holly' : 'Hattie Hayridge’s Holly']) await choose(page, name);
    const field = page.locator('fieldset');
    await expect(field).toBeVisible({ timeout: 90000 });
    const id = await field.getAttribute('id');
    const question = game.levels.flatMap(level => level.questions).find(item => item.id === id);
    if (!question) throw new Error('Hosted question is absent from its dataset: ' + id);
    for (const id of question.kind === 'sequence' ? question.correctSequence : [question.correctChoice!]) {
      const choice = question.choices.find(item => item.id === id);
      if (!choice) throw new Error('Hosted answer is absent: ' + id);
      const button = field.getByRole('button', { name: `${id}. ${choice.label}`, exact: true });
      await expect(button).toBeEnabled();
      await button.click();
      if (question.kind === 'sequence') await page.waitForTimeout(200);
    }
    await expect(field).not.toBeVisible();
    await expect(page.getByRole('status', { name: 'Round status' })).toContainText('Total 1 of 48');
    expect(failures).toEqual([]);
  });
}

test('hosted two-player menus retain independent modes and restart', async ({ page }) => {
  await page.goto('/');
  for (const name of ['Play game', 'Two players', 'Viewer', 'Geek']) await choose(page, name);
  await expect(page.locator('footer')).toContainText('Two players · Player 1');
  await choose(page, 'Restart');
  await expect(page.getByRole('button', { name: 'Play game', exact: true })).toBeVisible();
});
