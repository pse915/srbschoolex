// v6 ┌-shaped school: screenshots of the grounds, floors 1~4, the ruined school and the ending comparison.
//   python -m http.server 8765 --directory components/rpg_game   (separate terminal)
//   node tests/v6_screens.cjs           -> docs/screenshots-v6/*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const fs=require('fs');
const OUT='docs/screenshots-v6';
(async()=>{
 fs.mkdirSync(OUT,{recursive:true});
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800},hasTouch:true});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=(process.env.GAME_URL||'http://127.0.0.1:8765');
 await page.goto(url+'/?test&qa-v53');await page.waitForFunction(()=>window.__game);
 await page.locator('#startBtn').click();
 await page.waitForFunction(()=>__game.map&&__game.map.id==='school'&&!__game.mapLoading);
 const shot=async(name)=>{await page.waitForTimeout(450);await page.screenshot({path:`${OUT}/${name}.png`});};
 const mini=async(name)=>{await page.locator('#minimap').screenshot({path:`${OUT}/${name}-minimap.png`});};
 // 1) grounds: spawn in front of the 중앙현관, the field, the hall
 const sp=await page.evaluate(()=>__game.map.spawn);assert.deepEqual(sp,[64,52]);
 const entrance=await page.evaluate(()=>__game.map.portals.find(p=>p.label==='중앙현관'));
 assert.deepEqual([entrance.x,entrance.y],[64,50]);
 await shot('10-school-entrance');await mini('10-school');
 const lm=await page.evaluate(()=>__game.map.landmarks);
 for(const [name,label] of [['11-school-platform','조회대'],['12-school-field','운동장'],['13-school-annex','목련관']]){
  const p=await page.evaluate(l=>__game.map.interactions.find(i=>i.label===l),label);assert.ok(p,label);
  await page.evaluate(([x,y])=>__game.setPosition(x,y),[p.x,p.y+1]);await shot(name);
 }
 // 2) floors: ┌ corridor, spawn in the 1F lobby / next to the central stair
 for(const f of [1,2,3,4]){
  await page.evaluate(f=>__game.loadMap('floor'+f,null),f);
  await page.waitForFunction(f=>__game.map.id==='floor'+f&&!__game.mapLoading,f);
  const s=await page.evaluate(()=>__game.map.spawn);await page.evaluate(([x,y])=>__game.setPosition(x,y),s);
  await shot(`2${f}-floor${f}`);await mini(`2${f}-floor${f}`);
 }
 // corner of 2F (the 90° turn at the corner stair)
 await page.evaluate(()=>__game.loadMap('floor2',[12,14]));await page.waitForFunction(()=>__game.map.id==='floor2'&&!__game.mapLoading);
 await page.evaluate(()=>__game.setPosition(12,16));await shot('25-floor2-corner');
 // 3) 50 years later (stage 4): the ruined sprite on the grounds
 await page.getByRole('button',{name:'검증 0/12',exact:true}).click();
 await page.getByRole('button',{name:'검증 학교',exact:true}).click();
 await page.waitForFunction(()=>__game.map.id==='school'&&!__game.mapLoading);
 await page.evaluate(()=>__game.setPosition(64,53));await shot('30-school-ruin-stage4');
 // 4) ending comparison (15세 / 65세), school canvases saved as PNG too
 await page.getByRole('button',{name:'검증 엔딩',exact:true}).click();
 await page.waitForFunction(()=>document.querySelectorAll('.ending-snapshot').length===4);
 await page.waitForTimeout(400);
 await page.locator('#modal').screenshot({path:`${OUT}/40-ending-modal.png`});
 const urls=await page.evaluate(()=>[...document.querySelectorAll('.ending-snapshot')].map(c=>c.toDataURL('image/png')));
 urls.forEach((u,i)=>fs.writeFileSync(`${OUT}/4${i+1}-ending-${['town-15','town-65','school-15','school-65'][i]}.png`,Buffer.from(u.split(',')[1],'base64')));
 assert.deepEqual(errors,[]);
 await browser.close();
 console.log('v6 screenshots saved to '+OUT);
})().catch(e=>{console.error(e);process.exitCode=1;});
