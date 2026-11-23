// 터치 입력 확인: Pointer Events가 없는 오래된 내장 브라우저(사이니지)를 흉내 내고 실제 터치 이벤트로 조작한다.
//   python -m http.server 8766 --directory components/explore     (separate terminal)
//   node tests/touch_check.cjs
const {chromium}=require('playwright');
const assert=require('node:assert/strict');
const URL_=(process.env.EXPLORE_URL||'http://127.0.0.1:8766');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 for(const noPointer of [true,false]){
  const ctx=await browser.newContext({viewport:{width:1280,height:800},hasTouch:true,isMobile:false});
  // a browser without Pointer Events: no PointerEvent constructor and pointer* listeners never fire
  if(noPointer)await ctx.addInitScript(()=>{try{delete window.PointerEvent;}catch(e){}window.PointerEvent=undefined;
    const add=EventTarget.prototype.addEventListener;EventTarget.prototype.addEventListener=function(t,f,o){if(/^pointer/.test(t))return;return add.call(this,t,f,o);};
    for(const k of ['onpointerdown','onpointerup','onpointermove'])try{Object.defineProperty(HTMLElement.prototype,k,{set(){},get(){return null;}});}catch(e){}});
  const page=await ctx.newPage();
  const errors=[];page.on('pageerror',e=>errors.push(e.message));page.on('console',m=>{if(m.type()==='error')errors.push(m.text());});
  const cdp=await ctx.newCDPSession(page);
  const touch=async(type,x,y)=>cdp.send('Input.dispatchTouchEvent',{type,touchPoints:type==='touchEnd'?[]:[{x,y}]});
  const tap=async(x,y)=>{await touch('touchStart',x,y);await page.waitForTimeout(60);await touch('touchEnd',x,y);await page.waitForTimeout(250);};
  const hold=async(x,y,ms)=>{await touch('touchStart',x,y);await page.waitForTimeout(ms);await touch('touchEnd',x,y);await page.waitForTimeout(150);};
  const tag=noPointer?'[터치만]':'[포인터]';
  await page.goto(URL_+'/');await page.waitForFunction(()=>window.__explore);
  await page.evaluate(()=>localStorage.clear());await page.reload();await page.waitForFunction(()=>window.__explore);
  assert.equal(await page.evaluate(()=>!!window.PointerEvent),!noPointer);
  // 캐릭터 버튼을 터치하면 고르기만 하고 게임은 시작하지 않는다
  const av=await page.locator('#avatars button').nth(3).boundingBox();
  await tap(av.x+av.width/2,av.y+av.height/2);
  assert.equal(await page.evaluate(()=>document.getElementById('play').hidden),true,tag+' avatar tap must not start');
  assert.equal(await page.evaluate(()=>__explore.G.save.avatar),3,tag+' avatar chosen');
  // 오른쪽 절반: 길 안내 지도
  await tap(960,150);
  assert.ok(await page.evaluate(()=>__explore.MV.open),tag+' right half opens guide map');
  // 지도 캔버스 터치 → 장소 선택
  const box=await page.locator('#mapCanvas').boundingBox();
  let picked=false;
  for(let k=0;k<30&&!picked;k++){await tap(box.x+box.width*(0.15+0.7*((k*7)%30)/30),box.y+box.height*(0.2+0.6*((k*11)%30)/30));picked=await page.evaluate(()=>!!__explore.MV.selected);}
  assert.ok(picked,tag+' map tap selects a place');
  await page.locator('#mapClose').click();await page.waitForTimeout(200);
  // 왼쪽 절반: 게임 시작
  await tap(320,120);
  await page.waitForFunction(()=>!document.getElementById('play').hidden&&__explore.E.map&&!__explore.E.paused,null,{timeout:5000});
  // 방향 패드를 누르고 있으면 움직인다
  const x0=await page.evaluate(()=>__explore.E.player.x);
  const right=await page.locator('#pad [data-dir=right]').boundingBox();
  await hold(right.x+right.width/2,right.y+right.height/2,700);
  const x1=await page.evaluate(()=>__explore.E.player.x);
  assert.ok(x1>x0+20,tag+' pad moves right '+x0+' -> '+x1);
  // 화면을 터치하면 그곳으로 걸어간다
  await page.waitForTimeout(300);
  const y0=await page.evaluate(()=>__explore.E.player.y);
  await tap(640,330);
  const moved=await page.evaluate(()=>__explore.E.path.length>0||Math.abs(__explore.E.player.y-0)>0);
  await page.waitForTimeout(800);
  const y1=await page.evaluate(()=>__explore.E.player.y);
  assert.ok(moved&&y1!==y0,tag+' tap-to-move '+y0+' -> '+y1);
  assert.deepEqual(errors,[],tag+' no errors');
  console.log(tag,'ok');
  await ctx.close();
 }
 await browser.close();console.log('touch check ok');
})().catch(e=>{console.error(e);process.exit(1);});
