/* 서라벌 탐방 — small tile engine (rendering, collision, tap-to-move, portals, minimap).
   Written for this game; it does not import the old life-design game code. */
(function () {
  'use strict';
  var U = SRB.U, T = 32;
  var E = {
    map: null, player: { x: 0, y: 0, dir: 0, anim: 0, moving: false }, avatar: 0,
    paused: true, keys: {}, pad: null, path: [], tapMark: null, zoom: 1,
    onDoor: null, onStairs: null, onTile: null, onMap: null, onNearChange: null
  };
  var cv, ctx, mini, mctx, miniBase = null, camera = { x: 0, y: 0 }, cache = {}, lastTile = '', ignoreTile = '', near = null, last = 0;

  E.init = function (canvas, miniCanvas) {
    cv = canvas; ctx = cv.getContext('2d'); mini = miniCanvas; mctx = mini.getContext('2d');
    window.addEventListener('resize', resize); resize();
    bindInput();
    requestAnimationFrame(frame);
  };
  function resize() {
    if (!cv) return;
    var w = cv.clientWidth || window.innerWidth, h = cv.clientHeight || window.innerHeight;
    E.zoom = Math.max(1, Math.floor(h / 560));
    cv.width = Math.ceil(w / E.zoom); cv.height = Math.ceil(h / E.zoom);
    ctx.imageSmoothingEnabled = false;
  }
  E.resize = resize;

  E.getMap = function (id) {
    if (cache[id]) return Promise.resolve(cache[id]);
    return U.getJSON('data/maps/' + id + '.json').then(function (m) { cache[id] = m; return m; });
  };
  function walkable(m, tx, ty) {
    return tx >= 1 && ty >= 1 && tx < m.width - 1 && ty < m.height - 1 && !m.solid[ty * m.width + tx];
  }
  E.walkable = function (tx, ty) { return E.map ? walkable(E.map, tx, ty) : false; };
  function nearestWalkable(m, tx, ty) {
    if (walkable(m, tx, ty)) return [tx, ty];
    for (var r = 1; r < 14; r++) for (var dy = -r; dy <= r; dy++) for (var dx = -r; dx <= r; dx++) {
      if (Math.abs(dx) !== r && Math.abs(dy) !== r) continue;
      if (walkable(m, tx + dx, ty + dy)) return [tx + dx, ty + dy];
    }
    return [m.spawn[0], m.spawn[1]];
  }
  E.loadMap = function (id, arrival) {
    return E.getMap(id).then(function (m) {
      E.map = m; miniBase = null; E.path = [];
      var a = nearestWalkable(m, (arrival || m.spawn)[0], (arrival || m.spawn)[1]);
      E.player.x = a[0] * T + 16; E.player.y = a[1] * T + 24;
      ignoreTile = a[0] + ',' + a[1]; lastTile = ignoreTile;
      if (E.onMap) E.onMap(m);
      return m;
    });
  };
  E.tileOf = function () { return [Math.floor(E.player.x / T), Math.floor(E.player.y / T)]; };

  /* ---------- input ---------- */
  function bindInput() {
    window.addEventListener('keydown', function (e) {
      if (E.paused || U.modalOpen()) return;
      var k = e.key;
      if (k === 'Enter' || k === ' ') { if (E.onAct) E.onAct(); e.preventDefault(); return; }
      E.keys[k.toLowerCase()] = true;
      if (/^arrow/i.test(k)) e.preventDefault();
    });
    window.addEventListener('keyup', function (e) { E.keys[e.key.toLowerCase()] = false; });
    window.addEventListener('blur', function () { E.keys = {}; E.pad = null; });
    var pad = U.$('pad'), padId = null;
    pad.addEventListener('pointerdown', function (e) {
      var b = e.target.closest ? e.target.closest('button') : e.target;
      if (!b || padId !== null) return;                  // first finger only
      padId = e.pointerId; E.pad = b.getAttribute('data-dir'); E.path = [];
      try { pad.setPointerCapture(e.pointerId); } catch (x) {}
      e.preventDefault();
    });
    function padUp(e) { if (e.pointerId === padId) { padId = null; E.pad = null; } }
    pad.addEventListener('pointerup', padUp); pad.addEventListener('pointercancel', padUp);
    pad.addEventListener('pointermove', function (e) {
      if (e.pointerId !== padId) return;
      var el = document.elementFromPoint(e.clientX, e.clientY);
      var d = el && el.getAttribute && el.getAttribute('data-dir'); if (d) E.pad = d;
    });
    var tapId = null;
    cv.addEventListener('pointerdown', function (e) { if (tapId === null) tapId = e.pointerId; });
    cv.addEventListener('pointerup', function (e) {
      if (e.pointerId !== tapId) return; tapId = null;
      if (E.paused || U.modalOpen() || !E.map) return;
      var r = cv.getBoundingClientRect();
      var wx = (e.clientX - r.left) / E.zoom + camera.x, wy = (e.clientY - r.top) / E.zoom + camera.y;
      E.walkTo(Math.floor(wx / T), Math.floor(wy / T));
    });
    cv.addEventListener('pointercancel', function () { tapId = null; });
  }

  /* ---------- tap-to-move (movement only; no guidance is drawn) ---------- */
  E.walkTo = function (tx, ty) {
    var m = E.map, goal = nearestWalkable(m, tx, ty), start = E.tileOf();
    var w = m.width, prev = new Int32Array(w * m.height).fill(-1), q = [start[1] * w + start[0]], head = 0;
    prev[q[0]] = q[0];
    var end = goal[1] * w + goal[0];
    while (head < q.length) {
      var cur = q[head++]; if (cur === end) break;
      var cx = cur % w, cy = (cur / w) | 0;
      var nb = [[1, 0], [-1, 0], [0, 1], [0, -1]];
      for (var i = 0; i < 4; i++) {
        var nx = cx + nb[i][0], ny = cy + nb[i][1], j = ny * w + nx;
        if (walkable(m, nx, ny) && prev[j] < 0) { prev[j] = cur; q.push(j); }
      }
    }
    if (prev[end] < 0) { U.toast('그곳으로는 갈 수 없어요.'); return; }
    var path = [];
    for (var n = end; n !== prev[n]; n = prev[n]) path.push([n % w, (n / w) | 0]);
    E.path = path.reverse();
    E.tapMark = { x: goal[0], y: goal[1], t: 0.45 };
  };

  /* ---------- update ---------- */
  function step(dt) {
    var m = E.map, p = E.player; if (!m) return;
    var dx = 0, dy = 0, k = E.keys;
    if (k.arrowleft || k.a || E.pad === 'left') dx -= 1;
    if (k.arrowright || k.d || E.pad === 'right') dx += 1;
    if (k.arrowup || k.w || E.pad === 'up') dy -= 1;
    if (k.arrowdown || k.s || E.pad === 'down') dy += 1;
    if (dx || dy) E.path = [];
    else if (E.path.length) {
      var t = E.path[0], tx = t[0] * T + 16, ty = t[1] * T + 24;
      var ddx = tx - p.x, ddy = ty - p.y;
      if (Math.abs(ddx) < 3 && Math.abs(ddy) < 3) { p.x = tx; p.y = ty; E.path.shift(); }
      else { dx = Math.abs(ddx) > 2 ? Math.sign(ddx) : 0; dy = Math.abs(ddy) > 2 ? Math.sign(ddy) : 0; }
    }
    p.moving = !!(dx || dy);
    if (p.moving) {
      var sp = 118 * dt;
      if (dx && dy && !E.path.length) { sp *= 0.7071; }
      var nx = p.x + dx * sp, ny = p.y + dy * sp;
      if (free(nx, p.y)) p.x = nx; else if (E.path.length) p.x = nx;
      if (free(p.x, ny)) p.y = ny; else if (E.path.length) p.y = ny;
      p.dir = dy > 0 ? 0 : dy < 0 ? 3 : dx < 0 ? 1 : 2;
      p.anim += dt * 8;
    } else p.anim = 0;
    var tile = Math.floor(p.x / T) + ',' + Math.floor(p.y / T);
    if (tile !== lastTile) {
      lastTile = tile;
      if (tile !== ignoreTile) { ignoreTile = ''; checkTile(); }
    }
    var n = nearest();
    if ((n && n.person) !== (near && near.person)) { near = n; if (E.onNearChange) E.onNearChange(n); }
    if (E.tapMark) { E.tapMark.t -= dt; if (E.tapMark.t <= 0) E.tapMark = null; }
  }
  function free(x, y) {
    var m = E.map;
    return walkable(m, Math.floor((x - 7) / T), Math.floor(y / T)) && walkable(m, Math.floor((x + 7) / T), Math.floor(y / T)) &&
      walkable(m, Math.floor(x / T), Math.floor((y - 6) / T));
  }
  function checkTile() {
    var m = E.map, t = E.tileOf();
    for (var i = 0; i < m.portals.length; i++) {
      var pt = m.portals[i];
      if (pt.type === 'door' && pt.x === t[0] && pt.y === t[1]) { E.path = []; E.keys = {}; E.pad = null; if (E.onDoor) E.onDoor(pt); return; }
      if (pt.type === 'stairs') for (var j = 0; j < pt.tiles.length; j++) if (pt.tiles[j][0] === t[0] && pt.tiles[j][1] === t[1]) {
        E.path = []; E.keys = {}; E.pad = null; if (E.onStairs) E.onStairs(pt); return;
      }
    }
    if (E.onTile) E.onTile(t[0], t[1]);
  }
  function nearest() {
    var m = E.map, p = E.player, best = null, bd = 1e9;
    (m.people || []).forEach(function (n) {
      var d = Math.hypot(n.x * T + 16 - p.x, n.y * T + 24 - p.y);
      if (d < 56 && d < bd) { bd = d; best = { person: n }; }
    });
    return best;
  }
  E.near = function () { return near; };
  E.leaveTile = function () { ignoreTile = lastTile; };

  /* ---------- draw ---------- */
  function atlas(index) {
    var I = U.images;
    if (index >= 65) return [I.details, index - 65];
    if (index >= 49) return [I.facilities, index - 49];
    if (index >= 33) return [I.furniture, index - 33];
    return [I.environment, index];
  }
  function drawObject(o) {
    var x = Math.round(o.x * T - camera.x), y = Math.round(o.y * T - camera.y);
    if (o.image) { var im = U.images[o.image]; if (im) ctx.drawImage(im, x, y, o.w, o.h); return; }
    var a = atlas(o.asset); if (!a[0]) return;
    var cw = a[0].width / 4, ch = a[0].height / 4, j = a[1];
    ctx.drawImage(a[0], (j % 4) * cw, Math.floor(j / 4) * ch, cw, ch, x, y, o.w, o.h);
  }
  function drawActor(img, sx, sy, fx, fy) {
    if (img) ctx.drawImage(img, sx, sy, 32, 48, Math.round(fx - camera.x - 16), Math.round(fy - camera.y - 44), 32, 48);
  }
  function label(text, x, y, strong) {
    ctx.font = (strong ? 'bold ' : '') + '12px "Malgun Gothic","Apple SD Gothic Neo",sans-serif';
    var w = ctx.measureText(text).width + 10, lx = Math.round(x - camera.x - w / 2), ly = Math.round(y - camera.y);
    ctx.fillStyle = strong ? '#96483aee' : '#463c52d8'; ctx.fillRect(lx, ly - 13, w, 17);
    ctx.fillStyle = '#fff'; ctx.fillText(text, lx + 5, ly);
  }
  function draw() {
    var m = E.map; if (!m) return;
    var p = E.player, W = cv.width, H = cv.height;
    camera.x = m.width * T <= W ? (m.width * T - W) / 2 : Math.max(0, Math.min(m.width * T - W, p.x - W / 2));
    camera.y = m.height * T <= H ? (m.height * T - H) / 2 : Math.max(0, Math.min(m.height * T - H, p.y - H * 0.55));
    camera.x = Math.round(camera.x); camera.y = Math.round(camera.y);
    ctx.fillStyle = '#263b3c'; ctx.fillRect(0, 0, W, H);
    var terr = U.images.terrain;
    var x0 = Math.max(0, Math.floor(camera.x / T)), y0 = Math.max(0, Math.floor(camera.y / T));
    var x1 = Math.min(m.width, Math.ceil((camera.x + W) / T) + 1), y1 = Math.min(m.height, Math.ceil((camera.y + H) / T) + 1);
    for (var ty = y0; ty < y1; ty++) for (var tx = x0; tx < x1; tx++) {
      if (tx < 0 || ty < 0) continue;
      ctx.drawImage(terr, m.tiles[ty * m.width + tx] * T, 0, T, T, tx * T - camera.x, ty * T - camera.y, T, T);
    }
    var list = [];
    m.objects.forEach(function (o) {
      if (o.x * T > camera.x + W || o.y * T > camera.y + H || o.x * T + o.w < camera.x || o.y * T + o.h < camera.y) return;
      list.push({ y: o.ground ? -1e9 : (o.sortY != null ? o.sortY * T : o.y * T + o.h - 8), o: o });
    });
    (m.people || []).forEach(function (n) {
      var v = n.variant % 35;
      list.push({ y: n.y * T + 24, fn: function () { drawActor(U.images.npcs, (v % 7) * 32, Math.floor(v / 7) * 48, n.x * T + 16, n.y * T + 24); } });
    });
    list.push({ y: p.y, fn: function () {
      ctx.fillStyle = '#24372f44'; ctx.beginPath(); ctx.ellipse(p.x - camera.x, p.y - camera.y, 11, 4, 0, 0, 7); ctx.fill();
      drawActor(U.images.avatars, (p.moving ? Math.floor(p.anim) % 4 : 0) * 32, (E.avatar * 4 + p.dir) * 48, p.x, p.y);
    } });
    list.sort(function (a, b) { return a.y - b.y; });
    list.forEach(function (it) { if (it.o) drawObject(it.o); else it.fn(); });
    if (E.tapMark) {
      ctx.strokeStyle = 'rgba(255,255,255,' + Math.min(1, E.tapMark.t * 3) + ')'; ctx.lineWidth = 2;
      ctx.strokeRect(E.tapMark.x * T + 6 - camera.x, E.tapMark.y * T + 6 - camera.y, 20, 20);
    }
    // door / stair / person name tags near the player
    m.portals.forEach(function (pt) {
      var px = (pt.type === 'door' ? pt.x : pt.tiles[0][0]) * T + 16, py = (pt.type === 'door' ? pt.y : pt.tiles[0][1]) * T + 4;
      if (Math.abs(px - p.x) > 260 || Math.abs(py - p.y) > 200) return;
      label(pt.type === 'door' ? pt.label : pt.name, px, py, pt.type !== 'door');
    });
    (m.people || []).forEach(function (n) {
      if (Math.abs(n.x * T - p.x) < 220 && Math.abs(n.y * T - p.y) < 180) label(n.name, n.x * T + 16, n.y * T - 26);
    });
    if (E.extraDraw) E.extraDraw(ctx, camera);
    drawMini();
  }
  function drawMini() {
    var m = E.map, w = mini.width, h = mini.height;
    if (!miniBase) {
      miniBase = document.createElement('canvas'); miniBase.width = w; miniBase.height = h;
      var o = miniBase.getContext('2d'), colors = m.minimapColors || {};
      o.fillStyle = '#536254'; o.fillRect(0, 0, w, h);
      var s = Math.min(w / m.width, h / m.height), ox = (w - m.width * s) / 2, oy = (h - m.height * s) / 2;
      for (var y = 0; y < m.height; y++) for (var x = 0; x < m.width; x++) {
        var j = y * m.width + x, key = (m.solid[j] ? 's' : 'w') + m.tiles[j];
        var c = colors[key] || (m.solid[j] ? null : '#e8dfc8');
        if (!c) continue;
        o.fillStyle = c; o.fillRect(ox + x * s, oy + y * s, Math.ceil(s), Math.ceil(s));
      }
      miniBase.s = s; miniBase.ox = ox; miniBase.oy = oy;
    }
    mctx.drawImage(miniBase, 0, 0);
    mctx.fillStyle = '#fff8e0'; mctx.strokeStyle = '#96483a'; mctx.lineWidth = 2;
    mctx.beginPath(); mctx.arc(miniBase.ox + E.player.x / T * miniBase.s, miniBase.oy + E.player.y / T * miniBase.s, 3.5, 0, 7);
    mctx.fill(); mctx.stroke();
  }
  function frame(t) {
    var dt = Math.min(0.05, (t - last) / 1000 || 0); last = t;
    if (!E.paused && !U.modalOpen()) step(dt);
    if (E.map && !E.hidden) draw();
    requestAnimationFrame(frame);
  }
  SRB.E = E;
})();
