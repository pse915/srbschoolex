/* 서라벌 탐방 — 학교 전체 지도 (교정 · 1~4층 · 입체), 검색, 장소 정보, 지금 여기 핀, 현관에서 가는 길(선택). */
(function () {
  'use strict';
  var U = SRB.U;
  var MV = { open: false, tab: 1, selected: null, pin: null, standalone: false, route: null };
  var D, cv, ctx, stage, view = null, blink = 0, raf = 0;
  var DIRS = ['north', 'east', 'south', 'west'], DIRK = { north: '북쪽', east: '동쪽', south: '남쪽', west: '서쪽' };

  MV.init = function (data) {
    D = data; cv = U.$('mapCanvas'); ctx = cv.getContext('2d'); stage = U.$('mapStage');
    var tabs = U.$('mapTabs');
    [['교정', 0]].concat(D.floors.map(function (f) { return [f.name, f.floor]; })).concat([['입체', 'stack']]).forEach(function (t) {
      var b = U.el('button', { type: 'button', role: 'tab', 'data-tab': String(t[1]) }, t[0]);
      b.onclick = function () { MV.setTab(t[1]); };
      tabs.appendChild(b);
    });
    U.$('mapClose').onclick = function () { MV.close(); };
    U.$('mapSearch').addEventListener('input', search);
    U.$('routeToggle').onchange = function () { refreshRoute(); };
    U.$('evToggle').onchange = function () { refreshRoute(); };
    cv.addEventListener('pointerup', onTap);
    window.addEventListener('resize', function () { if (MV.open) render(); });
    var lg = U.$('mapLegend');
    ['classroom', 'office', 'special', 'care', 'service', 'restroom', 'stair', 'ev'].forEach(function (k) {
      var c = D.categories[k]; var s = U.el('span', { 'class': 'chip' }, c.label);
      s.style.background = c.color; if (k === 'ev') s.style.color = '#fff'; lg.appendChild(s);
    });
    var un = U.el('span', { 'class': 'chip' }, '확인 필요'); un.style.background = 'repeating-linear-gradient(45deg,#9a9ea0 0 4px,#80848a 4px 8px)'; un.style.color = '#fff'; lg.appendChild(un);
  };

  MV.show = function (opts) {
    opts = opts || {};
    MV.open = true; MV.standalone = !!opts.standalone; MV.pin = opts.pin || null; MV.wing = null;
    U.$('mapview').hidden = false; U.$('mapClose').hidden = MV.standalone;
    U.$('routeToggle').checked = !!opts.route; U.$('routeSteps').innerHTML = '';
    U.$('mapTitle').textContent = opts.title || '학교 전체 지도';
    if (opts.route) U.$('mapInfo').innerHTML = '<p class="muted">가고 싶은 곳을 검색하거나 지도에서 누르면, 현관에서 가는 길을 알려 드려요.</p>';
    var tab = opts.tab != null ? opts.tab : (MV.pin ? MV.pin.floor : 1);
    MV.setTab(tab);
    if (opts.focus) MV.select(byId(opts.focus));
    cancelAnimationFrame(raf); loop();
  };
  MV.close = function () {
    MV.open = false; U.$('mapview').hidden = true; cancelAnimationFrame(raf);
    if (MV.onClose) MV.onClose();
  };
  MV.setTab = function (t) {
    MV.tab = t;
    var bs = U.$('mapTabs').querySelectorAll('button');
    for (var i = 0; i < bs.length; i++) bs[i].setAttribute('aria-selected', bs[i].getAttribute('data-tab') === String(t) ? 'true' : 'false');
    render();
  };
  function byId(id) { for (var i = 0; i < D.places.length; i++) if (D.places[i].id === id) return D.places[i]; return null; }
  MV.byId = byId;
  function loop() { blink += 1; if ((MV.selected || MV.wing) && blink % 20 === 0) render(); raf = requestAnimationFrame(loop); }

  /* ---------- layout & drawing ---------- */
  function fitScale(w, h) {
    var aw = stage.clientWidth - 16, ah = stage.clientHeight - 16;
    var k = Math.floor(Math.min(aw / w, ah / h));
    return k >= 1 ? k : Math.min(aw / w, ah / h);     // integer when it fits, otherwise shrink to fit
  }
  function setCanvas(w, h) {
    cv.width = Math.round(w); cv.height = Math.round(h);
    cv.style.width = cv.width + 'px'; cv.style.height = cv.height + 'px';
    ctx.imageSmoothingEnabled = false;
  }
  function font(px, bold) { ctx.font = (bold ? 'bold ' : '') + px + 'px "Malgun Gothic","Apple SD Gothic Neo",sans-serif'; }
  function tag(text, x, y, strong) {
    font(13, true); var w = ctx.measureText(text).width + 12;
    ctx.fillStyle = strong ? '#96483aee' : '#463c52e0'; ctx.fillRect(Math.round(x - w / 2), Math.round(y - 15), w, 20);
    ctx.fillStyle = '#fff'; ctx.fillText(text, Math.round(x - w / 2 + 6), Math.round(y));
  }
  function pinAt(x, y, k) {
    var im = U.images['map-pin']; if (!im) return;
    var s = Math.max(2, Math.round(k));
    ctx.drawImage(im, Math.round(x - 6 * s), Math.round(y - 18 * s), 12 * s, 18 * s);
    tag('지금 여기', x, y - 18 * s - 12, true);
  }
  function render() {
    if (!D) return;
    U.$('mapNumbers').innerHTML = '';
    if (MV.tab === 0) renderSchool(); else if (MV.tab === 'stack') renderStack(); else renderFloor(MV.tab);
  }

  // 교정: the same code-pixel-art images as the game, placed with school-footprint coordinates
  function renderSchool() {
    var S = D.school, sc = S.displayScale, imgs = S.images.filter(function (i) { return i.image.indexOf('gate') < 0; });
    var X0 = 1e9, Y0 = 1e9, X1 = -1e9, Y1 = -1e9;
    imgs.forEach(function (i) { X0 = Math.min(X0, i.x * 32); Y0 = Math.min(Y0, i.y * 32); X1 = Math.max(X1, i.x * 32 + i.w); Y1 = Math.max(Y1, i.y * 32 + i.h); });
    X0 -= 40; Y0 -= 30; X1 += 40; Y1 += 30;
    var bw = (X1 - X0) / sc, bh = (Y1 - Y0) / sc, k = fitScale(bw, bh);
    setCanvas(bw * k, bh * k);
    var px = function (tx) { return (tx * 32 - X0) / sc * k; }, py = function (ty) { return (ty * 32 - Y0) / sc * k; };
    view = { kind: 'school', px: px, py: py, k: k };
    ctx.fillStyle = '#8dab78'; ctx.fillRect(0, 0, cv.width, cv.height);
    S.images.forEach(function (i) {
      var im = U.images[i.image]; if (!im) return;
      ctx.drawImage(im, Math.round(px(i.x)), Math.round(py(i.y)), Math.round(i.w / sc * k), Math.round(i.h / sc * k));
    });
    (S.labels || []).forEach(function (l) { tag(l.text, px(l.tile[0]), py(l.tile[1]), false); });
    D.places.forEach(function (p) {
      if (p.floor !== 0 || !p.tile || !p.visible) return;
      var x = px(p.tile[0] + 0.5), y = py(p.tile[1]);
      var out = x < 10 || y < 10 || x > cv.width - 10 || y > cv.height - 10;
      if (out) {                                   // gates outside the frame: edge markers
        var ex = Math.max(60, Math.min(cv.width - 60, x)), ey = Math.max(24, Math.min(cv.height - 10, y));
        tag(p.label + (x > cv.width ? ' →' : y < 0 ? ' ↑' : ''), ex, ey, MV.selected === p);
      } else tag(p.label, x, y - 4, MV.selected === p && blink % 40 < 20);
    });
    if (MV.pin && MV.pin.floor === 0 && MV.pin.tile) pinAt(px(MV.pin.tile[0] + 0.5), py(MV.pin.tile[1] + 0.8), k);
    if (MV.pin && MV.pin.floor >= 1) tag('지금 ' + MV.pin.floor + '층에 있어요', cv.width / 2, 24, true);
  }

  // N층: floor-plan PNG (no text inside) + names drawn on top
  function renderFloor(f) {
    var im = U.images['floor-plan-' + f], P = D.plan, M = P.marginM, ppm = P.pxPerM;
    var k = fitScale(im.width, im.height);
    setCanvas(im.width * k, im.height * k);
    var X = function (m) { return (m + M) * ppm * k; };
    view = { kind: 'floor', floor: f, X: X, k: k };
    ctx.fillStyle = '#f4ecdc'; ctx.fillRect(0, 0, cv.width, cv.height);
    ctx.drawImage(im, 0, 0, cv.width, cv.height);
    var nums = [], n = 0;
    D.places.forEach(function (p) {
      if (p.floor !== f || !p.polygon) return;
      var x0 = X(p.polygon[0][0]), y0 = X(p.polygon[0][1]), x1 = X(p.polygon[2][0]), y1 = X(p.polygon[2][1]);
      if (!p.confirmed) {                          // unconfirmed area: grey hatch + 확인 필요
        ctx.save(); ctx.beginPath(); ctx.rect(x0, y0, x1 - x0, y1 - y0); ctx.clip();
        ctx.strokeStyle = '#6c7076'; ctx.lineWidth = 1;
        for (var t = -(y1 - y0); t < x1 - x0; t += 8) { ctx.beginPath(); ctx.moveTo(x0 + t, y1); ctx.lineTo(x0 + t + (y1 - y0), y0); ctx.stroke(); }
        ctx.restore();
        tag('확인 필요', (x0 + x1) / 2, (y0 + y1) / 2 + 6, false); return;
      }
      if (MV.selected === p) {
        ctx.fillStyle = blink % 40 < 20 ? '#96483a66' : '#96483a22'; ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
        ctx.strokeStyle = '#7c3a30'; ctx.lineWidth = 3; ctx.strokeRect(x0 + 1.5, y0 + 1.5, x1 - x0 - 3, y1 - y0 - 3);
      }
      if (!p.visible) return;
      var text = p.kind === 'ev' ? 'EV' : p.kind === 'stair' ? '계단' : p.label;
      var w = x1 - x0 - 4, h = y1 - y0 - 4, cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
      ctx.fillStyle = p.kind === 'ev' ? '#fff' : '#3b3244';
      var done = false, sizes = [13, 11, 10];
      for (var s = 0; s < sizes.length && !done; s++) {
        font(sizes[s], p.kind !== 'stair');
        if (ctx.measureText(text).width <= w && sizes[s] + 2 <= h) { ctx.fillText(text, Math.round(cx - ctx.measureText(text).width / 2), Math.round(cy + sizes[s] / 2 - 1)); done = true; }
        else if (text.length > 3 && sizes[s] * 2 + 4 <= h) {     // two lines
          var cut = Math.ceil(text.length / 2), a = text.slice(0, cut), b = text.slice(cut);
          if (Math.max(ctx.measureText(a).width, ctx.measureText(b).width) <= w) {
            ctx.fillText(a, Math.round(cx - ctx.measureText(a).width / 2), Math.round(cy - 1));
            ctx.fillText(b, Math.round(cx - ctx.measureText(b).width / 2), Math.round(cy + sizes[s]));
            done = true;
          }
        }
      }
      if (!done) {                                  // too narrow: number badge + list
        n += 1; nums.push([n, p]);
        ctx.fillStyle = '#96483a'; ctx.beginPath(); ctx.arc(cx, cy, 8, 0, 7); ctx.fill();
        font(11, true); ctx.fillStyle = '#fff'; var tw = ctx.measureText(String(n)).width; ctx.fillText(String(n), Math.round(cx - tw / 2), Math.round(cy + 4));
      }
    });
    if (nums.length) {
      var box = U.$('mapNumbers'); box.appendChild(U.el('b', null, '번호로 표시한 좁은 칸'));
      nums.forEach(function (it) { var d = U.el('div', null, it[0] + '. ' + it[1].label); d.onclick = function () { MV.select(it[1]); }; box.appendChild(d); });
    }
    if (MV.wing && !MV.selected && MV.wing.floor === f) {
      var bx0 = 1e9, by0 = 1e9, bx1 = -1e9, by1 = -1e9;
      D.places.forEach(function (p) {
        if (p.floor !== f || p.wing !== MV.wing.wing || !p.polygon) return;
        bx0 = Math.min(bx0, p.polygon[0][0]); by0 = Math.min(by0, p.polygon[0][1]); bx1 = Math.max(bx1, p.polygon[2][0]); by1 = Math.max(by1, p.polygon[2][1]);
      });
      if (bx1 > bx0) { ctx.strokeStyle = blink % 40 < 20 ? '#96483a' : '#c08070'; ctx.lineWidth = 4; ctx.strokeRect(X(bx0) - 3, X(by0) - 3, X(bx1) - X(bx0) + 6, X(by1) - X(by0) + 6); }
    }
    drawRoute(f, X);
    if (MV.pin && MV.pin.floor === f && MV.pin.m) pinAt(X(MV.pin.m[0]), X(MV.pin.m[1]), k);
  }

  // 입체: the four stacked floor layers; the chosen floor is solid, the others are see-through
  function renderStack() {
    var st = D.stack, w = st.size[0], h = st.size[1], k = fitScale(w, h);
    setCanvas(w * k, h * k);
    var focus = (MV.selected && MV.selected.floor >= 1) ? MV.selected.floor : (MV.lastFloor || (MV.pin && MV.pin.floor) || 1);
    view = { kind: 'stack', k: k };
    ctx.fillStyle = '#f4ecdc'; ctx.fillRect(0, 0, cv.width, cv.height);
    var P = function (x, y, f) { return [(st.origin[0] + st.s * (x - 0.5 * y)) * k, (st.origin[1] + st.s * (0.55 * y - (f - 1) * st.gap)) * k]; };
    D.floors.forEach(function (fl) {
      var im = U.images['stack-floor-' + fl.floor]; if (!im) return;
      ctx.globalAlpha = fl.floor === focus ? 1 : 0.28;
      ctx.drawImage(im, 0, 0, w * k, h * k);
      ctx.globalAlpha = 1;
    });
    D.floors.forEach(function (fl) { var a = P(0, 0, fl.floor); tag(fl.name, a[0] - 34, a[1] + 8, fl.floor === focus); });
    if (MV.selected && MV.selected.floor >= 1 && MV.selected.center) {
      var c = P(MV.selected.center[0], MV.selected.center[1], MV.selected.floor);
      ctx.fillStyle = '#96483a'; ctx.beginPath(); ctx.arc(c[0], c[1], 6, 0, 7); ctx.fill();
      tag(MV.selected.label, c[0], c[1] - 12, true);
    }
    if (MV.pin && MV.pin.floor >= 1 && MV.pin.m) { var q = P(MV.pin.m[0], MV.pin.m[1], MV.pin.floor); pinAt(q[0], q[1], k / 2); }
  }

  /* ---------- tap / select / search ---------- */
  function onTap(e) {
    if (!view) return;
    var r = cv.getBoundingClientRect(), x = (e.clientX - r.left) * cv.width / r.width, y = (e.clientY - r.top) * cv.height / r.height;
    var hit = null;
    if (view.kind === 'floor') {
      D.places.forEach(function (p) {
        if (p.floor !== view.floor || !p.polygon || !p.visible) return;
        if (x >= view.X(p.polygon[0][0]) && x <= view.X(p.polygon[2][0]) && y >= view.X(p.polygon[0][1]) && y <= view.X(p.polygon[2][1])) hit = p;
      });
    } else if (view.kind === 'school') {
      var bd = 40;
      D.places.forEach(function (p) {
        if (p.floor !== 0 || !p.tile) return;
        var d = Math.hypot(view.px(p.tile[0] + 0.5) - x, view.py(p.tile[1]) - y);
        if (d < bd) { bd = d; hit = p; }
      });
      if (!hit) {                                     // tapped a wing of the building -> its floor-1 plan
        var areas = D.school.areas || [];
        for (var i = 0; i < areas.length; i++) {
          var poly = areas[i].outline.map(function (t) { return [view.px(t[0]), view.py(t[1])]; });
          if (inside(poly, x, y)) { MV.showWing(areas[i]); return; }
        }
      }
    }
    if (hit) MV.select(hit);
  }
  function inside(poly, x, y) {
    var c = false;
    for (var i = 0, j = poly.length - 1; i < poly.length; j = i++) {
      var a = poly[i], b = poly[j];
      if ((a[1] > y) !== (b[1] > y) && x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
    }
    return c;
  }
  MV.showWing = function (area) {
    MV.selected = null; MV.wing = area; MV.lastFloor = area.floor;
    U.$('routeSteps').innerHTML = ''; MV.route = null;
    MV.setTab(area.floor);
    var box = U.$('mapInfo'); box.innerHTML = '';
    box.appendChild(U.el('h3', null, area.name + ' ' + area.floor + '층'));
    var n = D.places.filter(function (p) { return p.floor === area.floor && p.wing === area.wing && (p.kind === 'room' || p.kind === 'restroom') && p.visible; }).length;
    box.appendChild(U.el('p', null, area.name + ' ' + area.floor + '층에는 실이 ' + n + '곳 있어요. 지도에서 실을 누르면 정보가 나와요. 다른 층은 위 탭에서 고르세요.'));
  };
  MV.select = function (p) {
    if (!p) return;
    MV.selected = p; MV.wing = null;
    if (p.floor >= 1) MV.lastFloor = p.floor;
    if (MV.tab !== 'stack' && MV.tab !== p.floor) MV.tab = p.floor;
    MV.setTab(MV.tab);
    info(p); refreshRoute();
  };
  function norm(s) { return String(s || '').toLowerCase().replace(/\s+/g, ''); }
  function search() {
    var q = norm(U.$('mapSearch').value), box = U.$('mapResults'); box.innerHTML = '';
    if (!q) return;
    D.places.filter(function (p) {
      return p.visible && p.kind !== 'gap' && [p.name, p.label].concat(p.aliases || []).some(function (s) { return norm(s).indexOf(q) >= 0; });
    }).slice(0, 8).forEach(function (p) {
      var b = U.el('button', { type: 'button' }, p.label + ' · ' + (p.floor ? p.floor + '층' : '교정'));
      b.onclick = function () { MV.select(p); };
      box.appendChild(b);
    });
    if (!box.children.length) box.appendChild(U.el('p', { 'class': 'muted' }, '찾는 장소가 없어요.'));
  }
  var WING = { main: '본관', west: '서쪽 동', corner: '꺾임부', site: '교정' }, SIDE = { inner: '운동장 쪽', outer: '바깥쪽' };
  function info(p) {
    var box = U.$('mapInfo'); box.innerHTML = '';
    box.appendChild(U.el('h3', null, p.label));
    var c = D.categories[p.category] || D.categories.service, chip = U.el('span', { 'class': 'chip' }, c.label);
    chip.style.background = c.color; if (p.category === 'ev') chip.style.color = '#fff';
    box.appendChild(chip);
    box.appendChild(U.el('span', null, p.floor ? p.floor + '층 · ' + (WING[p.wing] || '') + (SIDE[p.side] ? ' · ' + SIDE[p.side] : '') : '교정'));
    box.appendChild(U.el('p', null, p.intro));
    if (p.neighbors && p.neighbors.length) box.appendChild(U.el('p', { 'class': 'muted' }, '양옆: ' + p.neighbors.map(function (id) { var q = byId(id); return q ? q.label : id; }).join(', ')));
    if (p.nearest && p.nearest.length) box.appendChild(U.el('p', { 'class': 'muted' }, '가까운 계단·EV: ' + p.nearest.map(function (n) { var q = byId(n.id); return (q ? q.name : n.id) + ' (' + Math.round(n.m) + 'm)'; }).join(', ')));
    if (!p.confirmed) box.appendChild(U.el('p', null, '이 구역은 실제 배치를 확인하는 중이에요.'));
  }

  /* ---------- 현관에서 가는 길 (map screen only) ---------- */
  function graph(evOnly) {
    var adj = {}, nodes = {};
    function add(a, b, w) { (adj[a] = adj[a] || []).push([b, w]); (adj[b] = adj[b] || []).push([a, w]); }
    for (var f in D.graph.floors) {
      D.graph.floors[f].nodes.forEach(function (n) { nodes[n.id] = n; n.floor = +f; });
      D.graph.floors[f].edges.forEach(function (e) { add(e[0], e[1], e[2]); });
    }
    D.graph.vertical.forEach(function (v) { add(v.a, v.b, v.kind === 'ev' ? 12 : (evOnly ? 1e4 : v.cost)); });
    return { adj: adj, nodes: nodes };
  }
  function shortest(G, from, to) {
    var dist = {}, prev = {}, todo = [[0, from]]; dist[from] = 0;
    while (todo.length) {
      todo.sort(function (a, b) { return a[0] - b[0]; });
      var cur = todo.shift(); if (cur[1] === to) break; if (cur[0] > dist[cur[1]]) continue;
      (G.adj[cur[1]] || []).forEach(function (e) {
        var d = cur[0] + e[1];
        if (dist[e[0]] === undefined || d < dist[e[0]]) { dist[e[0]] = d; prev[e[0]] = cur[1]; todo.push([d, e[0]]); }
      });
    }
    if (dist[to] === undefined) return null;
    var path = [to]; while (path[0] !== from) path.unshift(prev[path[0]]);
    return path;
  }
  function dirOf(a, b) {
    var dx = b.x - a.x, dy = b.y - a.y;
    if (Math.abs(dx) < 0.01 && Math.abs(dy) < 0.01) return null;
    return Math.abs(dx) >= Math.abs(dy) ? (dx > 0 ? 'east' : 'west') : (dy > 0 ? 'south' : 'north');
  }
  function rel(facing, dir) {
    var d = (DIRS.indexOf(dir) - DIRS.indexOf(facing) + 4) % 4;
    return ['앞', '오른쪽', '뒤', '왼쪽'][d];
  }
  MV.routeTo = function (p, evOnly) {
    if (!p) return null;
    if (p.floor === 0) return { steps: ['이 화면 뒤의 중앙현관 문으로 나가 교정으로 가요.', p.label + josaWa(p.label) + ' 교정에 있어요. 교정 탭에서 위치를 확인하세요.'], nodes: [] };
    if (!p.node) return null;
    var G = graph(evOnly), kiosk = D.graph.kiosk, path = shortest(G, kiosk.node, p.node);
    if (!path) return null;
    var N = path.map(function (id) { return G.nodes[id]; }), steps = [], facing = kiosk.facing || 'north';
    var i = 0;
    // floor changes (stairs / EV)
    var segments = [], cur = [N[0]];
    for (i = 1; i < N.length; i++) { if (N[i].floor !== N[i - 1].floor) { segments.push(cur); cur = [N[i]]; } else cur.push(N[i]); }
    segments.push(cur);
    function legsOf(seg) {
      var legs = [];
      for (var j = 1; j < seg.length; j++) {
        var d = dirOf(seg[j - 1], seg[j]); if (!d) continue;
        if (seg[j].kind !== 'corridor' && seg[j].kind !== 'corner' && seg[j].kind !== 'end') continue;   // stepping into a door
        if (legs.length && legs[legs.length - 1].dir === d) legs[legs.length - 1].to = seg[j]; else legs.push({ dir: d, from: seg[j - 1], to: seg[j] });
      }
      return legs.filter(function (l) { return Math.hypot(l.to.x - l.from.x, l.to.y - l.from.y) > 1.6; });
    }
    var lastSeg = segments.length - 1;
    for (var si = 0; si <= lastSeg; si++) {
      var seg = segments[si], legs = legsOf(seg);
      if (si < lastSeg) {
        var sj = si + 1;
        while (sj < lastSeg && segments[sj].length === 1) sj++;          // floors we only pass through
        var stairNode = seg[seg.length - 1], sp = byId(stairNode.id.split(':').slice(1).join(':'));
        var toFloor = segments[sj][0].floor, verb = toFloor > seg[0].floor ? '올라가요' : '내려가요';
        var sname = sp ? sp.name : '계단';
        if (si === 0 && sp && sp.id === 'stair-centralStair' && !legs.length) {
          steps.push('이 화면 바로 뒤 중앙계단으로 ' + toFloor + '층까지 ' + verb + '.' + (U.$('evToggle').checked ? '' : ' (엘리베이터는 왼쪽 복도 쪽에 있어요)'));
        } else {
          legs.forEach(function (l) { steps.push(legText(l, facing)); facing = l.dir; });
          steps.push(sp && sp.kind === 'ev' ? '엘리베이터를 타고 ' + toFloor + '층으로 가요.' : sname + U.josa(sname, '으로', '로') + ' ' + toFloor + '층까지 ' + verb + '.');
        }
        var arrive = segments[sj];
        facing = (arrive.length > 1 && dirOf(arrive[0], arrive[1])) || 'south';
        si = sj - 1;
      } else {
        legs.forEach(function (l) { steps.push(legText(l, facing)); facing = l.dir; });
        var door = seg[seg.length - 1], cn = seg[seg.length - 2];
        var side = cn ? rel(facing, dirOf(cn, door) || facing) : '앞';
        var ord = ordinal(seg, facing, side);
        steps.push(p.label + U.josa(p.label, '은', '는') + ' 복도 ' + side + (ord ? ' ' + ord + ' 문' : '') + '이에요.');
      }
    }
    return { steps: steps, nodes: N };
  };
  function josaWa(w) { return U.josa(w, '은', '는'); }
  function legText(l, facing) {
    var r = rel(facing, l.dir), where = l.dir === 'south' || l.dir === 'north' ? '서쪽 동 복도' : '본관 복도';
    if (r === '앞') return where + '를 따라 ' + DIRK[l.dir] + '으로 쭉 가요.';
    if (l.from.kind === 'corner') return '꺾임부에서 ' + r + '(' + DIRK[l.dir] + ')으로 돌아 ' + where + '로 가요.';
    return r + '(' + DIRK[l.dir] + ')으로 ' + where + '를 따라가요.';
  }
  function ordinal(seg, facing, side) {
    // count doors on the same side along the last straight leg, up to the target
    var target = seg[seg.length - 1], count = 0, f = target.floor;
    var leg = [], dir = null;
    for (var j = seg.length - 2; j > 0; j--) { var d = dirOf(seg[j - 1], seg[j]); if (!d) continue; if (dir && d !== dir) break; dir = d; leg.unshift(seg[j]); }
    if (!dir) return '';
    var startNode = seg[Math.max(0, seg.length - 2 - leg.length)];
    var doors = D.places.filter(function (p) { return p.floor === f && p.node && (p.kind === 'room' || p.kind === 'restroom') && p.visible; });
    var tp = byId(target.id.split(':').slice(1).join(':'));
    doors.forEach(function (p) {
      var c = D.graph.floors[f].nodes.filter(function (n) { return n.id === f + ':c:' + p.id; })[0];
      var dn = D.graph.floors[f].nodes.filter(function (n) { return n.id === p.node; })[0];
      if (!c || !dn || !tp) return;
      var along = dir === 'east' ? c.x - startNode.x : dir === 'west' ? startNode.x - c.x : dir === 'south' ? c.y - startNode.y : startNode.y - c.y;
      var tAlong = dir === 'east' ? target.x - startNode.x : dir === 'west' ? startNode.x - target.x : dir === 'south' ? target.y - startNode.y : startNode.y - target.y;
      var perpOk = (dir === 'east' || dir === 'west') ? Math.abs(c.y - startNode.y) < 0.5 : Math.abs(c.x - startNode.x) < 0.5;
      if (perpOk && along > 0.5 && along <= tAlong + 0.01 && rel(facing, dirOf(c, dn) || facing) === side) count += 1;
    });
    return count >= 1 && count <= 9 ? ['첫', '두', '세', '네', '다섯', '여섯', '일곱', '여덟', '아홉'][count - 1] + ' 번째' : '';
  }
  function refreshRoute() {
    var box = U.$('routeSteps'); box.innerHTML = ''; MV.route = null;
    if (U.$('routeToggle').checked && MV.selected) {
      MV.route = MV.routeTo(MV.selected, U.$('evToggle').checked);
      if (MV.route) MV.route.steps.forEach(function (s) { box.appendChild(U.el('li', null, s)); });
      else box.appendChild(U.el('li', null, '가는 길을 계산하지 못했어요.'));
    }
    render();
  }
  function drawRoute(f, X) {
    if (!MV.route || !MV.route.nodes.length) return;
    var pts = MV.route.nodes.filter(function (n) { return n.floor === f; });
    if (pts.length < 2) return;
    ctx.save(); ctx.strokeStyle = '#96483a'; ctx.lineWidth = 4; ctx.setLineDash([8, 6]);
    ctx.beginPath(); pts.forEach(function (n, i) { if (i) ctx.lineTo(X(n.x), X(n.y)); else ctx.moveTo(X(n.x), X(n.y)); }); ctx.stroke();
    ctx.restore();
  }
  SRB.MV = MV;
})();
