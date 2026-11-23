// 79곳 완료 → 학번·이름 → GitHub 기록 → "2층 교무실 선생님에게 찾아가세요" 확인 (GitHub는 가짜 응답으로 대신)
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/prize_check.cjs        -> docs/screenshots-explore/29~32-*.png
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const OUT='docs/screenshots-explore', URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1280,height:800}});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error'&&!/Failed to load resource/.test(m.text()))errors.push(m.text());});
 let online=true;const puts=[];
 await page.route('https://api.github.com/**',async r=>{
   if(!online)return r.abort();
   const q=r.request();
   if(q.method()==='PUT'){puts.push({url:q.url(),auth:q.headers()['authorization'],body:JSON.parse(q.postData())});return r.fulfill({status:201,contentType:'application/json',body:'{}'});}
   return r.fulfill({status:200,contentType:'application/json',body:'{"private":true}'});
 });
 // 선생님 설정(?setup): 저장소·열쇠 입력
 await page.goto(URL_+'/?setup');await page.waitForFunction(()=>window.__explore&&!document.getElementById('modal').hidden);
 await page.fill('[aria-label="저장소"]','https://github.com/pse915/srb-records/');
 await page.fill('[aria-label="GitHub 토큰"]','test-token-123');
 await page.locator('#modalActions button',{hasText:'연결 시험'}).click();
 await page.waitForFunction(()=>/연결됐어요/.test(document.querySelector('.prize-msg').textContent));
 await page.screenshot({path:`${OUT}/29-teacher-setup.png`});
 const cfg=await page.evaluate(()=>JSON.parse(localStorage.getItem('srb.explore.github')));
 assert.equal(cfg.repo,'pse915/srb-records');assert.equal(cfg.token,'test-token-123');
 assert.equal(await page.inputValue('[aria-label="GitHub 토큰"]'),'','token is never shown again');
 await page.locator('#modalActions button',{hasText:'닫기'}).click();
 // 처음 화면: 상품 안내
 await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
 assert.ok((await page.locator('#title').innerText()).includes('상품이 있습니다!'));
 await page.screenshot({path:`${OUT}/30-title-prize.png`});
 // 78곳을 모은 상태에서 마지막 장소에 들어간다
 const last=await page.evaluate(()=>{const g=__explore.data.places.filter(p=>p.game&&p.map&&p.map.indexOf('room-')===0);const s=__explore.G.save;s.cards={};
   __explore.data.places.filter(p=>p.game).forEach(p=>{if(p.id!==g[0].id)s.cards[p.id]=1;});localStorage.setItem('srb.explore.v1',JSON.stringify(s));return g[0].id;});
 await page.reload();await page.waitForFunction(()=>window.__explore);
 await page.locator('#btnStart').click();await page.waitForFunction(()=>__explore.E.map&&!__explore.E.paused);
 await page.evaluate(id=>__explore.E.loadMap(id),last);
 await page.waitForFunction(()=>/탐방 완료/.test(document.getElementById('modalTitle').textContent));
 // 빈칸 확인
 await page.locator('#modalActions button',{hasText:'저장하기'}).click();
 assert.match(await page.locator('.prize-msg').innerText(),/학번/);
 await page.fill('[aria-label="학번"]','10203');await page.fill('[aria-label="이름"]','김서라');
 await page.screenshot({path:`${OUT}/31-prize-form.png`});
 await page.locator('#modalActions button',{hasText:'저장하기'}).click();
 await page.waitForFunction(()=>/2층 교무실 선생님에게 찾아가세요/.test(document.getElementById('modalBody').textContent));
 await page.screenshot({path:`${OUT}/32-prize-go-teacher.png`});
 assert.equal(puts.length,1);
 assert.match(puts[0].url,/^https:\/\/api\.github\.com\/repos\/pse915\/srb-records\/contents\/records\/\d{4}-\d{2}-\d{2}\/\d{6}-10203\.json$/);
 assert.equal(puts[0].auth,'Bearer test-token-123');
 const rec=JSON.parse(Buffer.from(puts[0].body.content,'base64').toString('utf8'));
 assert.equal(rec['학번'],'10203');assert.equal(rec['이름'],'김서라');assert.equal(rec['장소 수'],79);
 await page.locator('#modalActions button',{hasText:'확인'}).click();
 assert.ok(await page.evaluate(()=>!document.getElementById('title').hidden&&Object.keys(__explore.G.save.cards).length===0),'next student starts from 0');
 // 인터넷이 끊겼을 때: 기기에 보관 → 연결되면 다시 보냄
 online=false;
 await page.evaluate(id=>{const s=__explore.G.save;__explore.data.places.filter(p=>p.game).forEach(p=>{if(p.id!==id)s.cards[p.id]=1;});},last);
 await page.locator('#btnStart').click();await page.waitForFunction(()=>__explore.E.map&&!__explore.E.paused);
 await page.evaluate(id=>__explore.E.loadMap(id),last);
 await page.waitForFunction(()=>/탐방 완료/.test(document.getElementById('modalTitle').textContent));
 await page.fill('[aria-label="학번"]','20511');await page.fill('[aria-label="이름"]','박벌');
 await page.locator('#modalActions button',{hasText:'저장하기'}).click();
 await page.waitForFunction(()=>/이 기기에 보관/.test(document.getElementById('modalBody').textContent));
 assert.ok(/2층 교무실 선생님에게 찾아가세요/.test(await page.locator('#modalBody').innerText()));
 assert.equal(await page.evaluate(()=>__explore.G.save&&SRB.P.log().filter(e=>!e.sent).length),1);
 online=true;
 assert.equal(await page.evaluate(()=>SRB.P.flush()),1);
 assert.equal(puts.length,2);
 assert.equal(await page.evaluate(()=>SRB.P.log().filter(e=>!e.sent).length),0);
 assert.deepEqual(errors,[]);
 await browser.close();console.log('prize check ok');
})().catch(e=>{console.error(e);process.exit(1);});
