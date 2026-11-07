import { expect, test, type Page } from '@playwright/test';
import { readFileSync } from 'node:fs';
import type { RoundData } from '../src/game/types';
const data=JSON.parse(readFileSync(new URL('../public/round.json',import.meta.url),'utf8')) as RoundData;

async function enterRound(page:Page){
  await page.goto('/');
  await page.getByRole('button',{name:'Play game',exact:true}).click();
  for(const label of ['One player','General Knowledge','Norman Lovett’s Holly']){
    const button=page.getByRole('button',{name:label,exact:true});
    await expect(button).toBeEnabled({timeout:90000});
    await button.click();
  }
  await expect(page.getByRole('group',{name:/./}).first()).toBeVisible({timeout:90000});
}

async function round(page:Page,outcome:boolean|'mixed'){
  let score=0;
  for(let number=1;number<=6;number++){
    const group=page.locator('fieldset');
    await expect(group).toBeVisible({timeout:90000});
    const id=await group.getAttribute('id');
    const q=data.questions.find(q=>q.id===id)!;
    expect(q).toBeTruthy();
    const correct=outcome==='mixed'?number%2===1:outcome;
    const choices=q.kind==='sequence'?(correct?q.correctSequence:['A','A','A','A'] as const)
      :[correct?q.correctChoice!:q.choices.find(c=>c.id!==q.correctChoice)!.id];
    for(const choiceId of choices){
      const c=q.choices.find(c=>c.id===choiceId)!;
      const button=page.getByRole('button',{name:`${choiceId}. ${c.label}`,exact:true});
      await expect(button).toBeEnabled({timeout:90000});
      if(correct)await button.tap();
      else {await button.focus();await button.press('Enter');}
      if(q.kind==='sequence' && choiceId!==choices.at(-1))await page.waitForTimeout(100);
    }
    score+=correct?1:0;
    await expect(page.getByRole('status',{name:'Round status'})).toContainText(`Score ${score} of 6`);
    await expect(group).not.toBeVisible({timeout:5000});
  }
  const continueButton=page.getByRole('button',{name:'Continue',exact:true});
  if(score===6){await expect(continueButton).toBeEnabled({timeout:90000});await continueButton.click();}
  await expect(page.getByRole('status',{name:'Round status'})).toContainText('Level 2 of 8',{timeout:90000});
}

test('source entry and six-question correct round work with touch and aligned 4:3 controls',async({page})=>{
  const requests:string[]=[];page.on('request',r=>requests.push(r.url()));
  await enterRound(page);
  await page.setViewportSize({width:390,height:844});
  const stage=await page.getByLabel('Game screen',{exact:true}).boundingBox();
  expect(stage!.width/stage!.height).toBeCloseTo(4/3,2);
  const id=await page.locator('fieldset').getAttribute('id');const q=data.questions.find(q=>q.id===id)!;
  const rect=q.choices[0].rect;
  const hit=await page.getByRole('button',{name:`A. ${q.choices[0].label}`,exact:true}).boundingBox();
  expect(Math.abs(hit!.x-(stage!.x+stage!.width*rect.x/720))).toBeLessThan(1.5);
  expect(Math.abs(hit!.y-(stage!.y+stage!.height*rect.y/576))).toBeLessThan(1.5);
  await page.screenshot({path:'test-results/question-mobile.png'});
  await round(page,true);
  expect(requests.filter(url=>/\.(vob|ifo|bup|wasm)(\?|$)/i.test(url))).toEqual([]);
});

test('unanswered question loops and wrong keyboard answers leave score zero',async({page})=>{
  await enterRound(page);
  const original=await page.locator('fieldset').getAttribute('id');
  await page.waitForTimeout(13000);
  await expect(page.locator('fieldset')).toHaveAttribute('id',original!);
  await expect(page.getByRole('status',{name:'Round status'})).toContainText('Score 0 of 6');
  const buttons=page.locator('fieldset button');await buttons.first().focus();
  await page.keyboard.press('ArrowDown');await expect(buttons.nth(1)).toBeFocused();
  await round(page,false);
});

test('failed media can be retried without changing the active scene or score',async({page})=>{
  let failed=false;
  await page.route('**/media/*.mp4',route=>{
    if(!failed){failed=true;return route.abort('failed');}
    return route.continue();
  });
  await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
  await expect(page.getByRole('button',{name:'Retry',exact:true})).toBeVisible();
  const source=await page.locator('video').getAttribute('src');
  await page.getByRole('button',{name:'Retry',exact:true}).click();
  await expect.poll(()=>page.locator('video').evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(0);
  await expect(page.locator('video')).toHaveAttribute('src',source!);
  await expect(page.getByRole('status',{name:'Round status'})).toContainText('Score 0 of 6');
});

test('fullscreen preserves the source image coordinate surface',async({page})=>{
  await page.goto('/');
  await page.getByRole('button',{name:'Full screen',exact:true}).click();
  await expect.poll(()=>page.evaluate(()=>!!document.fullscreenElement)).toBe(true);
  const surface=await page.locator('.stage-content').boundingBox();
  expect(surface).toBeTruthy();
  expect(surface!.width/surface!.height).toBeCloseTo(4/3,2);
  await page.evaluate(()=>document.exitFullscreen());
});


test('mixed answers complete a real round with score three',async({page})=>{
  await enterRound(page);
  await round(page,'mixed');
});

test('autoplay refusal retains the scene and offers a working Play action',async({page})=>{
  await page.addInitScript(()=>{
    const play=HTMLMediaElement.prototype.play;let refused=false;
    HTMLMediaElement.prototype.play=function(){
      if(!refused){refused=true;this.autoplay=false;this.pause();return Promise.reject(new DOMException('Gesture required','NotAllowedError'));}
      return play.call(this);
    };
  });
  await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();
  await expect(page.getByRole('button',{name:'Play',exact:true})).toBeVisible();
  const source=await page.locator('video').getAttribute('src');
  await page.getByRole('button',{name:'Play',exact:true}).click();
  await expect.poll(()=>page.locator('video').evaluate((v:HTMLVideoElement)=>v.currentTime)).toBeGreaterThan(0);
  await expect(page.locator('video')).toHaveAttribute('src',source!);
  await expect(page.getByRole('status',{name:'Round status'})).toContainText('Score 0 of 6');
});
