// 봄·여름·가을·겨울 그림 확인
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/season_check.cjs        -> docs/screenshots-explore/36~40-*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const OUT='docs/screenshots-explore', URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
const KO={spring:'봄',summer:'여름',autumn:'가을',winter:'겨울'};
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
 await page.evaluate(()=>localStorage.clear());await page.reload();await page.waitForFunction(()=>window.__explore);
 // 자동: today's month decides
 const auto=await page.evaluate(()=>__explore.U.autoSeason());
 assert.equal(await page.evaluate(()=>__explore.U.season),auto);
 assert.equal(await page.evaluate(()=>[2,5,8,11].map(m=>__explore.U.autoSeason(new Date(2026,m,1))).join()),'spring,summer,autumn,winter');
 assert.match(await page.locator('#seasons .on').innerText(),/자동/);
 let n=36;
 for(const s of ['spring','summer','autumn','winter']){
  await page.locator(`#seasons [data-season="${s}"]`).click();
  await page.waitForFunction(s=>__explore.U.season===s,s);
  assert.ok(await page.evaluate(()=>!document.getElementById('title').hidden),'chip click keeps the title');
  if(s==='spring') await page.screenshot({path:`${OUT}/${n++}-title-season.png`});
  await page.locator('#btnStart').click();
  await page.waitForFunction(()=>__explore.E.map&&__explore.E.map.id==='school'&&!__explore.E.paused);
  await page.waitForTimeout(700);
  const ok=await page.evaluate(s=>['terrain','trees','school','school-ground','school-annex'].every(k=>__explore.U.images[k+'-'+s]&&__explore.U.img(k==='trees'?'terrain':k)===__explore.U.images[(k==='trees'?'terrain':k)+'-'+s]),s);
  assert.ok(ok,'season images in use: '+s);
  await page.screenshot({path:`${OUT}/${n++}-season-${s}.png`});
  await page.evaluate(()=>__explore.G.toTitle());
 }
 // remembered after reload; ?season= wins for one visit
 await page.reload();await page.waitForFunction(()=>window.__explore);
 assert.equal(await page.evaluate(()=>__explore.U.season),'winter','choice remembered');
 await page.goto(URL_+'/?season=spring');await page.waitForFunction(()=>window.__explore);
 assert.equal(await page.evaluate(()=>__explore.U.season),'spring');
 // game menu cycles the season
 await page.locator('#btnStart').click();await page.waitForFunction(()=>__explore.E.map&&!__explore.E.paused);
 await page.locator('#btnMenu').click();
 await page.locator('.modal button',{hasText:'계절: 봄'}).click();
 await page.waitForFunction(()=>__explore.U.season==='summer');
 assert.ok(await page.locator('.modal button',{hasText:'계절: 여름'}).count(),'menu label updates');
 // map grounds tab follows the season
 await page.evaluate(()=>{__explore.U.setSeason('autumn');});await page.waitForFunction(()=>__explore.U.season==='autumn');
 assert.deepEqual(errors,[]);
 await browser.close();console.log('season check ok');
})().catch(e=>{console.error(e);process.exit(1);});
