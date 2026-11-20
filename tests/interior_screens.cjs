// 복도·중앙현관·방송실 꾸밈 확인용 스크린샷 (tools/interior_art.py)
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/interior_screens.cjs        -> docs/screenshots-explore/20~23-*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const OUT='docs/screenshots-explore', URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
 await page.evaluate(()=>localStorage.clear());await page.reload();await page.waitForFunction(()=>window.__explore);
 await page.locator('#btnStart').click();
 await page.waitForFunction(()=>__explore.E.map&&!__explore.E.paused);
 const at=async(map,x,y,name)=>{
   await page.evaluate(([m,x,y])=>__explore.E.loadMap(m,[x,y]),[map,x,y]);
   await page.waitForTimeout(500);
   for(let i=0;i<4&&await page.locator('#modal').isVisible();i++)await page.locator('#modalActions button').first().click();
   await page.waitForTimeout(200);await page.screenshot({path:`${OUT}/${name}.png`});
 };
 await at('floor1',60,19,'20-lobby');
 assert.ok(await page.evaluate(()=>__explore.E.walkable(60,20)&&__explore.E.walkable(60,21)),'lobby path stays open');
 await at('floor1',36,12,'21-corridor-main');
 await at('floor1',12,40,'22-corridor-west');
 await at('room-1-9',16,14,'23-broadcast-room');
 await at('floor2',40,12,'24-corridor-2f');
 assert.deepEqual(errors,[]);
 await browser.close();console.log('interior screens ok');
})().catch(e=>{console.error(e);process.exit(1);});
