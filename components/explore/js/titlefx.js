/* 서라벌 탐방 — 처음 화면의 계절: 아래쪽 교정 풍경(잔디·나무), 계절 한 줄, 화면 위로 날리는 꽃잎·햇살·낙엽·눈.
   The animation runs only while the title screen is showing. */
(function () {
  'use strict';
  var U = SRB.U, TF = {};
  var LINE = {
    spring: '벚꽃이 활짝 핀 봄 교정을 걸어 봐요',
    summer: '초록이 짙은 여름 교정을 걸어 봐요',
    autumn: '단풍이 곱게 물든 가을 교정을 걸어 봐요',
    winter: '하얀 눈이 내린 겨울 교정을 걸어 봐요'
  };
  var FALL = {
    spring: { n: 46, c: ['#f7c4d4', '#fbd9e4', '#f3a9c0', '#ee93b0'], vy: [40, 75], sway: 40, size: [5, 8] },
    summer: { n: 26, c: ['rgba(255,236,150,0.95)', 'rgba(255,255,255,0.95)', 'rgba(190,235,170,0.9)'], vy: [-12, 12], sway: 14, size: [3, 6], glint: true },
    autumn: { n: 38, c: ['#c8502c', '#e08a2c', '#e6b83a', '#9b3f24'], vy: [50, 90], sway: 50, size: [6, 9] },
    winter: { n: 90, c: ['#ffffff', '#e4eefa', '#cfe0f2'], vy: [35, 80], sway: 22, size: [3, 7] }
  };
  var fx, fctx, scene, sctx, flakes = [], flakeSeason = '', last = 0, running = false;

  TF.init = function () {
    fx = U.$('titleFx'); scene = U.$('titleScene');
    if (!fx || !scene) return;
    fctx = fx.getContext('2d'); sctx = scene.getContext('2d');
    window.addEventListener('resize', function () { size(); TF.redraw(); });
    size(); TF.redraw(); TF.start();
  };
  function size() {
    var t = U.$('title');
    fx.width = t.clientWidth || window.innerWidth; fx.height = t.clientHeight || window.innerHeight;
    var p = scene.parentNode;
    scene.width = Math.max(1, Math.ceil((p.clientWidth || 600) / 2)); scene.height = 60;    // drawn at 2x pixels
    flakes = [];
  }

  // 아래쪽 풍경: 계절 잔디 + 나무 줄 (game pictures of this season)
  TF.redraw = function () {
    if (!sctx) return;
    var s = U.season, W = scene.width, H = scene.height, terr = U.img('terrain'), trees = U.images['trees-' + s];
    var line = U.$('seasonLine');
    if (line) { line.textContent = LINE[s] || ''; line.className = 'season-line sl-' + s; }
    sctx.imageSmoothingEnabled = false; sctx.clearRect(0, 0, W, H);
    var gy = H - 18;                                   // ground top
    if (terr) for (var x = 0; x < W; x += 32) sctx.drawImage(terr, 0, 0, 32, 32, x, gy, 32, 32);
    sctx.fillStyle = 'rgba(0,0,0,0.08)'; sctx.fillRect(0, gy, W, 1);
    if (trees) {
      var tw = trees.width / 2, th = trees.height, size = 54, step = 64;
      var n = Math.ceil(W / step) + 1, off = (W - (n - 1) * step) / 2 - size / 2;
      for (var i = 0; i < n; i++) {
        var kind = i % 3 === 1 ? 1 : 0, sz = size - (i % 2) * 8;
        sctx.drawImage(trees, kind * tw, 0, tw, th, Math.round(off + i * step + (size - sz) / 2), H - sz - 4, sz, sz);
      }
    }
    flakes = [];
  };

  function seed(f, W, H, top) {
    var sp = FALL[U.season];
    f.x = Math.random() * W; f.y = top ? -10 : Math.random() * H;
    f.vy = sp.vy[0] + Math.random() * (sp.vy[1] - sp.vy[0]); f.ph = Math.random() * 6.3;
    f.s = sp.size[0] + Math.random() * (sp.size[1] - sp.size[0]);
    f.c = sp.c[Math.floor(Math.random() * sp.c.length)]; f.life = 1.5 + Math.random() * 3;
    return f;
  }
  function frame(t) {
    if (!running) return;
    var title = U.$('title');
    if (title.hidden) { running = false; return; }
    var dt = Math.min(0.05, (t - last) / 1000 || 0); last = t;
    var sp = FALL[U.season], W = fx.width, H = fx.height, now = t / 1000;
    fctx.clearRect(0, 0, W, H);
    if (sp) {
      var n = Math.min(120, Math.round(sp.n * W * H / 1000000));
      if (flakeSeason !== U.season) { flakes = []; flakeSeason = U.season; }
      while (flakes.length < n) flakes.push(seed({}, W, H, false));
      flakes.length = n;
      for (var i = 0; i < flakes.length; i++) {
        var f = flakes[i];
        fctx.fillStyle = f.c;
        if (sp.glint) {                                  // summer: twinkling sunlight
          f.life -= dt; f.y += f.vy * dt;
          if (f.life <= 0) seed(f, W, H, false);
          fctx.globalAlpha = Math.max(0, Math.sin(f.life * 1.7));
          fctx.fillRect(Math.round(f.x - f.s / 2), Math.round(f.y - 1), Math.round(f.s), 2);
          fctx.fillRect(Math.round(f.x - 1), Math.round(f.y - f.s / 2), 2, Math.round(f.s));
          continue;
        }
        f.y += f.vy * dt; f.x += Math.sin(now * 1.2 + f.ph) * sp.sway * dt;
        if (f.y > H + 10 || f.x < -12 || f.x > W + 12) seed(f, W, H, true);
        if (U.season === 'winter') {
          fctx.globalAlpha = 0.9;
          fctx.beginPath(); fctx.arc(f.x, f.y, f.s / 2, 0, 6.3); fctx.fill();
          fctx.strokeStyle = 'rgba(110,145,190,0.45)'; fctx.lineWidth = 1; fctx.stroke();   // visible on the white half too
        } else {                                         // petal / leaf turning as it falls
          fctx.globalAlpha = 0.92;
          var flip = Math.abs(Math.sin(now * 2 + f.ph));
          if (fctx.ellipse) { fctx.beginPath(); fctx.ellipse(f.x, f.y, Math.max(1, f.s * 0.7 * flip), f.s * 0.45, now + f.ph, 0, 6.3); fctx.fill(); }
          else fctx.fillRect(Math.round(f.x), Math.round(f.y), Math.max(1, Math.round(f.s * 1.4 * flip)), Math.round(f.s * 0.9));
        }
      }
      fctx.globalAlpha = 1;
    }
    requestAnimationFrame(frame);
  }
  TF.start = function () {
    if (running || !fx) return;
    running = true; last = 0; size(); TF.redraw(); requestAnimationFrame(frame);
  };
  TF.running = function () { return running; };
  SRB.TF = TF;
})();
