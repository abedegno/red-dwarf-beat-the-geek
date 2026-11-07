import {expect,test} from '@playwright/test';
import {readFileSync,writeFileSync} from 'node:fs';
test.use({trace:'off'});
const data=JSON.parse(readFileSync(new URL('../../analysis/extras/gateway.json',import.meta.url),'utf8'));
const game=JSON.parse(readFileSync(new URL('../public/game.json',import.meta.url),'utf8'));
test.beforeEach(async({page})=>{if(process.env.MEMORY_DEBUG||process.env.MEMORY_TRACE)await page.addInitScript((debug:boolean)=>{
 if(debug)Math.random=()=>.4;const ids=new WeakMap<HTMLVideoElement,number>();let nextId=1;const events:unknown[]=[];(window as unknown as {memoryMediaEvents:unknown[]}).memoryMediaEvents=events;
 const record=(type:string,v:HTMLVideoElement)=>{if(!ids.has(v))ids.set(v,nextId++);events.push({id:ids.get(v),type,at:performance.now(),visibility:document.visibilityState,src:v.getAttribute('src'),time:v.currentTime,paused:v.paused,ended:v.ended,readyState:v.readyState});if(events.length>1000)events.shift();};
 for(const type of ['playing','waiting','ended','pause','stalled','error','loadedmetadata','canplay','emptied'])document.addEventListener(type,e=>{if(e.target instanceof HTMLVideoElement){record(type,e.target);if(debug&&type==='playing'&&/s00m-|s11t-/.test(e.target.src))e.target.playbackRate=16;}},true);
 const original=HTMLMediaElement.prototype.addEventListener;
 HTMLMediaElement.prototype.addEventListener=function(type,...args){if(this instanceof HTMLVideoElement&&['playing','waiting','error'].includes(type))record('listen-'+type,this);return original.call(this,type,...args);};
},!!process.env.MEMORY_DEBUG);});
test.afterEach(async({page},info)=>{if(process.env.MEMORY_DEBUG||process.env.MEMORY_TRACE){const media=await page.evaluate(()=>({events:(window as unknown as {memoryMediaEvents:unknown[]}).memoryMediaEvents,video:[...document.querySelectorAll('video')].map(v=>({src:v.src,time:v.currentTime,duration:v.duration,paused:v.paused,ended:v.ended,readyState:v.readyState,networkState:v.networkState,error:v.error?.message}))}));writeFileSync(info.outputPath('media-events.json'),JSON.stringify(media,null,2));await info.attach('media-events',{path:info.outputPath('media-events.json'),contentType:'application/json'});}});
test('original Memory Morph5/8/12 objects, recall and source Quit guard',async({page})=>{
 await page.goto('/');await page.getByRole('button',{name:'Play game',exact:true}).click();await expect(page.getByRole('button',{name:'Games Archive',exact:true})).toBeEnabled({timeout:90000});await page.getByRole('button',{name:'Games Archive',exact:true}).click();
 for(const digit of '9639'){const b=page.getByRole('button',{name:digit,exact:true});await expect(b).toBeEnabled({timeout:10000});await b.click();}
 const play=page.getByRole('button',{name:'Play',exact:true});await expect(play).toBeEnabled({timeout:10000});await play.click();
 const status=page.getByRole('status',{name:'Memory Morph',exact:true});let last:number[]=[];
 for(const [stage,length] of [5,8,12].entries()){
  const shown:number[]=[];
  for(let n=0;n<length;n++){
   await expect.poll(async()=>{const label=await status.textContent().catch(()=>null);return data.memory.objects.some((o:{label:string})=>o.label===label);},{timeout:15000}).toBe(true);
   const label=await status.textContent(),object=data.memory.objects.find((o:{label:string})=>o.label===label);shown.push(object.id);
   const video=await page.locator('video').elementHandle();await expect.poll(()=>video!.evaluate(v=>v.isConnected),{timeout:10000}).toBe(false);
  }
  for(const [index,id] of shown.entries()){
   await expect(status).toHaveText(`Recall object ${index+1} of ${length}.`);const label=data.memory.objects.find((o:{id:number})=>o.id===id).label;
   const b=page.getByRole('button',{name:label,exact:true});await expect(b).toBeEnabled();await b.click();
  }
  const result=data.pages.find((p:{id:string})=>p.id===data.memory.rounds[stage].results[length]);await expect(page.locator('video')).toHaveAttribute('src',data.scenes.find((s:{id:string})=>s.id===result.scene).src);
  if(stage===2){last=shown;await expect.poll(()=>page.locator('video').evaluate(v=>(v as HTMLVideoElement).currentTime)).toBeGreaterThan(1.5);await page.screenshot({path:test.info().outputPath('memory-complete.png')});}
 }
 await expect(play).toBeEnabled({timeout:10000});await page.getByRole('button',{name:'Quit',exact:true}).click();
 if(last[0]===last[9])await expect(page.locator('video')).toHaveAttribute('src',game.scenes.find((s:{id:string})=>s.id===game.entry.boot[0]).src);
 else await expect(page.getByRole('button',{name:'Menu',exact:true})).toBeEnabled({timeout:10000});
});
