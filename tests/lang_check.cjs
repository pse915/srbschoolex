// 지도 화면 한국어/English 전환 확인
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/lang_check.cjs        -> docs/screenshots-explore/33~35-*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const OUT='docs/screenshots-explore', URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
 await page.evaluate(()=>localStorage.clear());await page.reload();await page.waitForFunction(()=>window.__explore);
 await page.locator('#btnTitleMap').click();await page.waitForFunction(()=>__explore.MV.open);
 // the button sits right next to 닫기
 const lb=await page.locator('#mapLang').boundingBox(), cb=await page.locator('#mapClose').boundingBox();
 assert.ok(Math.abs(lb.y-cb.y)<6&&cb.x>lb.x&&cb.x-(lb.x+lb.width)<30,'language button next to close');
 assert.equal(await page.locator('#mapTitle').innerText(),'서라벌여중 길 안내');
 await page.locator('#mapLang').click();await page.waitForTimeout(200);
 assert.equal(await page.locator('#mapTitle').innerText(),"Seorabeol Girls' Middle School · Directions");
 assert.equal(await page.locator('#mapClose').innerText(),'Close');
 assert.equal(await page.locator('#mapTabs button[data-tab="1"]').innerText(),'1F');
 assert.equal(await page.locator('#mapTabs button[data-tab="0"]').innerText(),'Grounds');
 assert.match(await page.locator('#routeLabel').innerText(),/Show the way/);
 await page.screenshot({path:`${OUT}/33-map-english.png`});
 // search in English, route in English
 await page.fill('#mapSearch','library');
 await page.locator('#mapResults button').first().click();
 assert.match(await page.locator('#mapInfo h3').innerText(),/Geulbit Library/);
 const steps=await page.locator('#routeSteps li').allInnerTexts();
 assert.ok(steps.length>=2,'route steps');
 assert.ok(steps.every(s=>!/[가-힣]/.test(s)),'route steps are English: '+steps.join(' | '));
 await page.screenshot({path:`${OUT}/34-map-english-route.png`});
 // no Hangul left in the side panel or tabs
 const side=await page.locator('.map-head, .map-side').allInnerTexts();
 assert.ok(!/[가-힣]/.test(side.join(' ').replace('한국어','')),'side panel is English');
 // remembered, and back to Korean
 await page.locator('#mapClose').click();await page.locator('#btnTitleMap').click();
 assert.equal(await page.locator('#mapClose').innerText(),'Close','language remembered');
 await page.locator('#mapLang').click();await page.waitForTimeout(200);
 assert.equal(await page.locator('#mapClose').innerText(),'닫기');
 assert.match(await page.locator('#mapInfo h3').innerText(),/글빛도서관/);
 assert.ok((await page.locator('#routeSteps li').allInnerTexts()).some(s=>/[가-힣]/.test(s)));
 await page.screenshot({path:`${OUT}/35-map-korean-again.png`});
 // 2 minutes idle -> title, and the next visitor gets Korean
 await page.locator('#mapLang').click();
 await page.evaluate(()=>{__explore.G.idle.last=Date.now()-121000;});
 await page.waitForFunction(()=>__explore.MV.lang==='ko'&&!__explore.MV.open,null,{timeout:5000});
 assert.deepEqual(errors,[]);
 await browser.close();console.log('lang check ok');
})().catch(e=>{console.error(e);process.exit(1);});
