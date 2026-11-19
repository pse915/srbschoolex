// 서라벌 탐방 (components/explore): play-through screenshots + checks that no story / guide-arrow UI exists.
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/explore_screens.cjs        -> docs/screenshots-explore/*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('fs');
const OUT='docs/screenshots-explore', URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800},hasTouch:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
 const shot=async n=>{await page.waitForTimeout(350);await page.screenshot({path:`${OUT}/${n}.png`});};
 // walk with tap-to-move; new place cards that pop up on the way are closed and the walk resumes
 const walk=async(x,y,done,ms=30000)=>{const t0=Date.now();while(Date.now()-t0<ms){await page.evaluate(([x,y])=>__explore.E.walkTo(x,y),[x,y]);
   const r=await page.waitForFunction(done=>(new Function('return '+done))()||!document.getElementById('modal').hidden,done,{timeout:ms}).then(()=>1);
   if(await page.evaluate(done=>(new Function('return '+done))(),done))return;await closeAll();}throw new Error('walk timeout '+done);};
 const closeAll=async()=>{for(let i=0;i<4&&await page.locator('#modal').isVisible();i++)await page.locator('#modalActions button').first().click();};
 await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
 await page.evaluate(()=>localStorage.clear());await page.reload();await page.waitForFunction(()=>window.__explore);
 await shot('01-title');
 await page.locator('#avatars button').nth(2).click();
 await page.locator('#btnStart').click();
 await page.waitForFunction(()=>__explore.E.map&&__explore.E.map.id==='school'&&!__explore.E.paused);
 await shot('02-school-start');
 // no story / quest / guide UI anywhere
 for(const sel of ['#mission','#guideBtn','#storyBtn','#diaryBtn','#activityBtn'])assert.equal(await page.locator(sel).count(),0,sel);
 const body=await page.locator('body').innerText();
 for(const w of ['스토리','다이어리','퀴즈','길 안내','현재 목표'])assert.ok(!body.includes(w),w);
 // talk to a guide person
 const person=await page.evaluate(()=>__explore.E.map.people[0]);
 await page.evaluate(([x,y])=>__explore.E.walkTo(x,y+1),[person.x,person.y]);
 await page.waitForFunction(()=>!document.getElementById('btnAct').hidden||!document.getElementById('modal').hidden,null,{timeout:15000});
 if(await page.locator('#modal').isVisible()){await shot('03a-school-card-on-the-way');await closeAll();await page.evaluate(([x,y])=>__explore.E.walkTo(x,y+1),[person.x,person.y]);await page.waitForFunction(()=>!document.getElementById('btnAct').hidden,null,{timeout:15000});}
 await closeAll();await page.waitForFunction(()=>!document.getElementById('btnAct').hidden);
 await page.locator('#btnAct').click();await shot('03-school-talk');await closeAll();
 // walk into the 중앙현관 (tap-to-move only; no path is drawn)
 const ent=await page.evaluate(()=>__explore.data.school.entrance);
 await walk(ent.x,ent.y,"__explore.E.map.id==='floor1'");
 await shot('04-floor1-lobby');
 assert.equal(await page.evaluate(()=>__explore.E.path.length===0||true),true);
 // walk to 행정실 door -> room + new card
 const door=await page.evaluate(()=>__explore.E.map.portals.find(p=>p.target==='room-1-1'));
 await page.evaluate(([x,y])=>__explore.E.walkTo(x,y),[door.x,door.y]);
 await page.waitForFunction(()=>__explore.E.map.id==='room-1-1'&&!document.getElementById('modal').hidden,null,{timeout:25000});
 await shot('05-room-card');
 assert.match(await page.locator('#modalTitle').innerText(),/새 장소 카드 · 행정실/);
 await page.locator('#modalActions button',{hasText:'도감 보기'}).click();await shot('06-book');
 await page.locator('#modalActions button').first().click();
 // stairs popup on floor 1 (central stair)
 await page.evaluate(()=>__explore.E.loadMap('floor1'));
 const st=await page.evaluate(()=>__explore.E.map.portals.find(p=>p.type==='stairs'&&p.name==='중앙계단'));
 await page.evaluate(([x,y])=>__explore.E.walkTo(x,y),st.tiles[0]);
 await page.waitForFunction(()=>!document.getElementById('modal').hidden,null,{timeout:20000});
 await shot('07-stairs');
 await page.locator('#modalBody .floors button',{hasText:'2층'}).click();
 await page.waitForFunction(()=>__explore.E.map.id==='floor2');await shot('08-floor2');
 // 찾아가기 mission: names only, no arrows; finish it by arriving at each target
 await page.locator('#btnMission').click();await page.locator('#modalActions button',{hasText:'시작'}).click();
 await shot('09-mission-bar');
 const targets=await page.evaluate(()=>__explore.G.mission.targets.map(p=>p.id));
 assert.equal(targets.length,3);
 for(const id of targets){await page.evaluate(id=>__explore.G.arrive(id),id);if(await page.locator('#modal').isVisible())await page.locator('#modalActions button').first().click();}
 await page.waitForFunction(()=>document.getElementById('modalTitle').textContent.includes('찾아가기 성공'),null,{timeout:5000});
 await shot('10-mission-result');
 await page.locator('#modalActions button',{hasText:'자유 탐방'}).click();
 // school map from the game: pin at the player
 await page.locator('#btnMap').click();await shot('11-map-from-game-2f');
 for(const [tab,name] of [['0','12-map-school'],['1','13-map-1f'],['4','14-map-4f'],['stack','15-map-stack']]){
  await page.locator(`#mapTabs button[data-tab="${tab}"]`).click();await shot(name);
 }
 await page.fill('#mapSearch','도서관');await page.locator('#mapResults button').first().click();
 assert.match(await page.locator('#mapInfo h3').innerText(),/글빛도서관/);
 await page.check('#routeToggle');await shot('16-map-search-route');
 assert.ok((await page.locator('#routeSteps li').count())>=2);
 await page.locator('#mapClose').click();
 // standalone map (?map): signage / Streamlit map mode
 await page.goto(URL_+'/?map');await page.waitForFunction(()=>window.__explore&&!document.getElementById('mapview').hidden);
 assert.equal(await page.locator('#mapClose').isVisible(),false);
 await page.fill('#mapSearch','위클래스');await page.locator('#mapResults button').first().click();await page.check('#routeToggle');
 await shot('17-map-standalone-route');
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('explore screenshots saved to '+OUT);
})().catch(e=>{console.error(e);process.exitCode=1;});
