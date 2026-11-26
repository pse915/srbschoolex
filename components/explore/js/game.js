/* 서라벌 탐방 — game rules: 장소 카드·도감, 찾아가기 미션, 안내 사람, 지도 연결.
   No story, quests, quizzes, diary or guide arrows: players find places themselves with the map. */
(function () {
  'use strict';
  var U = SRB.U, E = SRB.E, MV = SRB.MV;
  var G = { data: null, save: null, mission: null };
  var places = {}, gamePlaces = [], timerId = 0;
  var TITLES = ['서라벌 탐험가'];

  G.init = function (data) {
    G.data = data; G.save = U.load();
    data.places.forEach(function (p) { places[p.id] = p; if (p.game) gamePlaces.push(p); });
    buildAvatars(); buildSeasons();
    U.onSeason = function () { E.seasonChanged(); MV.redraw(); markSeason(); SRB.TF.redraw(); };
    SRB.TF.init();
    U.$('btnStart').onclick = G.start;
    U.$('btnTitleMap').onclick = function () { openMap(true); };
    U.$('titlePlay').onclick = function (e) {   // the rest of the left half also starts (buttons inside handle themselves)
      for (var n = e.target; n && n !== U.$('titlePlay'); n = n.parentNode) if (n.tagName === 'BUTTON') return;
      G.start();
    };
    U.$('btnMap').onclick = function () { openMap(false); };
    U.$('btnBook').onclick = book;
    U.$('btnMission').onclick = missionMenu;
    U.$('btnMenu').onclick = menu;
    U.$('btnAct').onclick = act;
    E.onAct = act;
    E.onMap = onMap; E.onDoor = onDoor; E.onStairs = onStairs; E.onTile = onTile; E.onNearChange = onNear;
    window.addEventListener('keydown', function (e) {
      if ((e.key === 'm' || e.key === 'M') && !U.$('play').hidden && !U.modalOpen()) { if (MV.open) MV.close(); else openMap(false); }
      if (e.key === 'Escape') { if (U.modalOpen()) U.closeModal(); else if (MV.open && !MV.standalone) MV.close(); }
    });
    MV.onClose = function () { if (!U.$('play').hidden) E.paused = false; };
    updateCount(); titleNote();
    // 2분 동안 아무 조작이 없으면 처음 화면(탐방하기 / 길 안내)으로 돌아간다. 단독 지도 화면은 교정 탭으로.
    ['pointerdown', 'keydown', 'wheel', 'touchstart'].forEach(function (ev) { document.addEventListener(ev, function () { G.idle.last = Date.now(); }, true); });
    setInterval(checkIdle, 1000);
  };
  G.idle = { last: Date.now(), ms: 120000 };
  function checkIdle() {
    if (Date.now() - G.idle.last < G.idle.ms) return;
    G.idle.last = Date.now();
    if (MV.lang !== 'ko') MV.setLang('ko');            // next visitor starts in Korean
    if (MV.open && MV.standalone) { if (MV.tab !== 0) MV.setTab(0); return; }
    if (U.modalOpen()) U.closeModal();
    if (MV.open) MV.close();
    if (!U.$('play').hidden) { E.keys = {}; E.pad = null; E.path = []; G.toTitle(); }
  }

  /* ---------- title ---------- */
  function buildAvatars() {
    var box = U.$('avatars'); box.innerHTML = '';
    for (var i = 0; i < 6; i++) (function (i) {
      var b = U.el('button', { type: 'button', role: 'radio', 'aria-label': '캐릭터 ' + (i + 1) });
      var c = U.el('canvas'); c.width = 32; c.height = 48;
      var cx = c.getContext('2d'); cx.imageSmoothingEnabled = false;
      cx.drawImage(U.images.avatars, 0, i * 4 * 48, 32, 48, 0, 0, 32, 48);
      b.appendChild(c);
      b.onclick = function (e) { if (e) e.stopPropagation(); G.save.avatar = i; U.save(G.save); markAvatar(); };   // choose only; the half starts the game
      box.appendChild(b);
    })(i);
    markAvatar();
  }
  function markAvatar() {
    var bs = U.$('avatars').children;
    for (var i = 0; i < bs.length; i++) { bs[i].setAttribute('aria-checked', i === G.save.avatar ? 'true' : 'false'); bs[i].className = i === G.save.avatar ? 'on' : ''; }
  }
  // 계절: 자동(오늘 날짜) / 봄 / 여름 / 가을 / 겨울 — this device remembers the choice
  function buildSeasons() {
    var box = U.$('seasons'); box.innerHTML = '';
    ['auto'].concat(U.SEASONS).forEach(function (k) {
      var b = U.el('button', { type: 'button', role: 'radio', 'data-season': k, 'class': 'ss-' + k },
        k === 'auto' ? '자동(' + U.SEASON_KO[U.autoSeason()] + ')' : U.SEASON_KO[k]);
      b.onclick = function (e) { if (e) e.stopPropagation(); pickSeason(k); };
      box.appendChild(b);
    });
    markSeason();
  }
  function pickSeason(k) {
    U.setSeason(k, true).then(null, function () { U.toast('계절 그림을 불러오지 못했어요.'); });
    U.seasonPick = k; markSeason();
  }
  function markSeason() {
    var bs = U.$('seasons').children, pick = U.seasonPick || 'auto';
    for (var i = 0; i < bs.length; i++) {
      var on = bs[i].getAttribute('data-season') === pick;
      bs[i].setAttribute('aria-checked', on ? 'true' : 'false');
      bs[i].className = 'ss-' + bs[i].getAttribute('data-season') + (on ? ' on' : '');
    }
    U.$('titlePlay').className = 'half half-play season-' + U.season;
  }
  G.pickSeason = pickSeason;
  function titleNote() {
    var n = Object.keys(G.save.cards).length;
    if (complete()) { U.$('titleNote').textContent = '장소를 모두 찾았어요! 눌러서 학번과 이름을 적어 주세요.'; return; }
    U.$('titleNote').textContent = n ? '지금까지 모은 장소 카드 ' + n + ' / ' + gamePlaces.length + '장' : '장소 ' + gamePlaces.length + '곳이 기다리고 있어요.';
  }
  G.start = function () {
    U.$('title').hidden = true; U.$('play').hidden = false; E.resize();
    E.avatar = G.save.avatar; G.save.plays += 1; U.save(G.save);
    var s = G.data.school.entrance;
    E.loadMap('school', [s.x, s.y + 2]).then(function () {
      E.paused = false;
      if (complete()) prize(); else U.toast('중앙현관 앞이에요. 학교 곳곳을 찾아가 보세요!');
    });
  };
  G.toTitle = function () {
    stopMission(); E.paused = true; U.$('play').hidden = true; U.$('title').hidden = false; titleNote(); markAvatar(); SRB.TF.start();
  };

  /* ---------- map events ---------- */
  function onMap(m) {
    U.$('where').textContent = m.name;
    if (m.place) arrive(m.place);
  }
  function onDoor(pt) {
    E.paused = true;
    E.loadMap(pt.target, pt.arrival).then(function () { E.paused = false; });
  }
  function onStairs(pt) {
    var cur = E.map.floor, wrap = U.el('div');
    wrap.appendChild(U.el('p', null, pt.ev ? '몇 층으로 갈까요?' : pt.name + '이에요. 몇 층으로 갈까요?'));
    var grid = U.el('div', { 'class': 'floors' });
    [1, 2, 3, 4].forEach(function (f) {
      var key = 'floor' + f, b = U.el('button', { type: 'button' }, f + '층' + (f === cur ? ' (지금)' : ''));
      if (!pt.targets[key]) b.disabled = true;
      b.onclick = function () { U.closeModal(); E.paused = true; E.loadMap(key, pt.targets[key]).then(function () { E.paused = false; }); };
      grid.appendChild(b);
    });
    wrap.appendChild(grid);
    U.modal(pt.ev ? '엘리베이터' : pt.name, wrap, [{ label: '그대로 있기', fn: function () { E.leaveTile(); } }]);
  }
  function onTile(tx, ty) {
    if (E.map.id !== 'school') return;
    gamePlaces.forEach(function (p) {
      if (p.floor === 0 && p.tile && Math.abs(p.tile[0] - tx) <= 1 && Math.abs(p.tile[1] - ty) <= 1) arrive(p.id);
    });
  }
  function onNear(n) {
    var b = U.$('btnAct'); b.hidden = !(n && n.person); if (n && n.person) b.textContent = '말 걸기';
  }
  function act() {
    var n = E.near(); if (!n || !n.person) return;
    U.modal(n.person.name, n.person.text);
  }

  /* ---------- 장소 카드 ---------- */
  function arrive(id) {
    var p = places[id]; if (!p) return;
    var fresh = p.game && !G.save.cards[id];
    if (fresh) { G.save.cards[id] = Date.now(); U.save(G.save); updateCount(); }
    var hit = missionHit(id);
    if (fresh && complete()) { prize(); return; }         // 마지막 장소: 학번·이름 받기
    if (fresh) showCard(p, hit);
    else if (hit) U.toast('찾았다! ' + p.label);
    else if (!E.map.place || E.map.place === id) U.toast(p.label);
  }
  function catChip(p) {
    var c = G.data.categories[p.category] || G.data.categories.service, s = U.el('span', { 'class': 'chip' }, c.label);
    s.style.background = c.color; if (p.category === 'ev') s.style.color = '#fff'; return s;
  }
  function where(p) {
    var W = { main: '본관', west: '서쪽 동', corner: '꺾임부', site: '교정' }, S = { inner: '운동장 쪽', outer: '바깥쪽' };
    return p.floor ? p.floor + '층 · ' + (W[p.wing] || '') + (S[p.side] ? ' · ' + S[p.side] : '') : '교정';
  }
  function showCard(p, missionFound) {
    var wrap = U.el('div', { 'class': 'card' });
    var st = U.el('canvas', { 'class': 'stamp' }); st.width = 32; st.height = 32;
    var c = st.getContext('2d'); c.imageSmoothingEnabled = false; c.drawImage(U.images.stamp, 0, 0);
    wrap.appendChild(st);
    var t = U.el('div'); t.appendChild(catChip(p)); t.appendChild(U.el('span', null, where(p)));
    t.appendChild(U.el('p', null, p.intro));
    t.appendChild(U.el('p', { 'class': 'muted' }, '장소 카드 ' + Object.keys(G.save.cards).length + ' / ' + gamePlaces.length + (missionFound ? ' · 찾아가기 성공!' : '')));
    wrap.appendChild(t);
    U.modal('새 장소 카드 · ' + p.label, wrap, [{ label: '계속 탐방', primary: true }, { label: '도감 보기', fn: book }]);
  }
  function complete() { return gamePlaces.length > 0 && Object.keys(G.save.cards).length >= gamePlaces.length; }
  // 모두 찾으면: 학번·이름 → GitHub 기록 → "2층 교무실 선생님에게 찾아가세요" → 카드를 비우고 처음 화면(다음 학생 차례)
  function prize() {
    stopMission();
    SRB.P.form(gamePlaces.length, function () { G.save.cards = {}; U.save(G.save); updateCount(); G.toTitle(); });
  }
  G.complete = complete;
  function updateCount() { U.$('bookCount').textContent = Object.keys(G.save.cards).length + '/' + gamePlaces.length; }
  function book() {
    var wrap = U.el('div');
    var groups = [[0, '교정']].concat(G.data.floors.map(function (f) { return [f.floor, f.name]; }));
    groups.forEach(function (g) {
      var list = gamePlaces.filter(function (p) { return p.floor === g[0]; }), got = list.filter(function (p) { return G.save.cards[p.id]; }).length;
      var sec = U.el('div', { 'class': 'book-floor' });
      sec.appendChild(U.el('h3', null, g[1] + ' · ' + got + ' / ' + list.length));
      var grid = U.el('div', { 'class': 'book-grid' });
      list.forEach(function (p) {
        var have = !!G.save.cards[p.id], s = U.el('span', { 'class': have ? '' : 'locked' }, have ? p.label : '???');
        if (have) s.style.background = (G.data.categories[p.category] || {}).color || '#eee';
        s.title = have ? p.intro : (G.data.categories[p.category] || {}).label || '';
        grid.appendChild(s);
      });
      sec.appendChild(grid); wrap.appendChild(sec);
    });
    U.modal('장소 도감', wrap);
  }

  /* ---------- 찾아가기 미션 ---------- */
  function missionMenu() {
    if (G.mission) {
      U.modal('찾아가기 진행 중', missionText(), [{ label: '계속하기', primary: true }, { label: '그만두기', fn: function () { stopMission(); U.toast('찾아가기를 그만뒀어요.'); } }]);
      return;
    }
    var p = U.el('div');
    p.appendChild(U.el('p', null, '장소 이름만 알려 줄게요. 지도를 보고 직접 찾아가세요. 화살표는 나오지 않아요!'));
    p.appendChild(U.el('p', { 'class': 'muted' }, G.save.timer ? '제한 시간 3분 · 메뉴에서 끌 수 있어요.' : '제한 시간 없음'));
    if (G.save.best) p.appendChild(U.el('p', { 'class': 'muted' }, '최고 기록: ' + U.fmtTime(G.save.best) + ' (이 기기)'));
    U.modal('찾아가기 (3곳)', p, [{ label: '시작', primary: true, fn: startMission }, { label: '닫기' }]);
  }
  function pick() {
    var floors = [0, 1, 2, 3, 4].sort(function () { return Math.random() - 0.5; }).slice(0, 3);
    return floors.map(function (f) {
      var pool = gamePlaces.filter(function (p) { return p.floor === f; });
      var fresh = pool.filter(function (p) { return !G.save.cards[p.id]; });
      var src = fresh.length ? fresh : pool;
      return src[Math.floor(Math.random() * src.length)];
    }).filter(Boolean);
  }
  function startMission() {
    G.mission = { targets: pick(), found: {}, start: Date.now(), limit: G.save.timer ? 180 : 0 };
    renderMission();
    clearInterval(timerId); timerId = setInterval(tick, 500);
  }
  function stopMission() { G.mission = null; clearInterval(timerId); U.$('missionBar').hidden = true; }
  function elapsed() { return (Date.now() - G.mission.start) / 1000; }
  function tick() {
    if (!G.mission) return;
    if (G.mission.limit && elapsed() >= G.mission.limit) { endMission(false); return; }
    renderMission();
  }
  function missionText() {
    var d = U.el('div');
    G.mission.targets.forEach(function (p) {
      d.appendChild(U.el('p', { 'class': G.mission.found[p.id] ? 'done' : '' }, (G.mission.found[p.id] ? '✔ ' : '□ ') + (p.floor ? p.floor + '층' : '교정') + ' · ' + p.label));
    });
    return d;
  }
  function renderMission() {
    var m = G.mission, bar = U.$('missionBar'); if (!m) return;
    bar.hidden = false; bar.innerHTML = '';
    var n = Object.keys(m.found).length;
    bar.appendChild(U.el('b', null, '찾아가기 ' + n + '/' + m.targets.length));
    bar.appendChild(document.createTextNode(m.limit ? ' · 남은 시간 ' + U.fmtTime(m.limit - elapsed()) : ' · ' + U.fmtTime(elapsed())));
    m.targets.forEach(function (p) {
      bar.appendChild(U.el('div', { 'class': m.found[p.id] ? 'done' : '' }, (p.floor ? p.floor + '층' : '교정') + ' · ' + p.label));
    });
  }
  function missionHit(id) {
    var m = G.mission; if (!m || m.found[id]) return false;
    if (!m.targets.some(function (p) { return p.id === id; })) return false;
    m.found[id] = true; renderMission();
    if (Object.keys(m.found).length === m.targets.length) setTimeout(function () { endMission(true); }, 900);
    return true;
  }
  function titleFor(m, sec, ok) {
    if (!ok) return '다음엔 꼭!';
    if (sec < 100) return '번개 탐험가';
    if (m.targets.some(function (p) { return p.floor === 4; })) return '4층 마스터';
    if (m.targets.some(function (p) { return p.wing === 'west'; })) return '서쪽 동 탐험가';
    if (m.targets.some(function (p) { return p.floor === 0; })) return '교정 산책가';
    return TITLES[0];
  }
  function endMission(ok) {
    var m = G.mission; if (!m) return;
    var sec = Math.min(elapsed(), m.limit || 1e9), found = Object.keys(m.found).length;
    clearInterval(timerId);
    if (ok && (!G.save.best || sec < G.save.best)) G.save.best = Math.round(sec);
    U.save(G.save);
    var w = U.el('div', { 'class': 'card' });
    var st = U.el('canvas', { 'class': 'stamp' }); st.width = 32; st.height = 32;
    var c = st.getContext('2d'); c.imageSmoothingEnabled = false; c.drawImage(U.images.stamp, 0, 0); if (!ok) st.style.opacity = 0.35;
    w.appendChild(st);
    var t = U.el('div');
    t.appendChild(U.el('div', { 'class': 'result-title' }, titleFor(m, sec, ok)));
    t.appendChild(U.el('p', null, '찾은 장소 ' + found + ' / ' + m.targets.length + ' · 걸린 시간 ' + U.fmtTime(sec)));
    t.appendChild(missionText());
    if (G.save.best) t.appendChild(U.el('p', { 'class': 'muted' }, '이 기기 최고 기록 ' + U.fmtTime(G.save.best)));
    w.appendChild(t);
    G.mission = null; U.$('missionBar').hidden = true;
    U.modal(ok ? '찾아가기 성공!' : '시간이 다 됐어요', w, [{ label: '한 번 더', primary: true, fn: startMission }, { label: '자유 탐방' }]);
  }

  /* ---------- menu ---------- */
  function menu() {
    var w = U.el('div');
    w.appendChild(U.el('p', null, '장소 카드 ' + Object.keys(G.save.cards).length + ' / ' + gamePlaces.length + ' · 이 기기에만 저장돼요(서버 저장 없음).'));
    U.modal('메뉴', w, [
      { label: '찾아가기 제한 시간: ' + (G.save.timer ? '켜짐' : '꺼짐'), keep: true, fn: function () { G.save.timer = !G.save.timer; U.save(G.save); menu(); } },
      { label: '계절: ' + U.SEASON_KO[U.season] + (U.seasonPick === 'auto' ? '(자동)' : '') + ' → ' + U.SEASON_KO[U.SEASONS[(U.SEASONS.indexOf(U.season) + 1) % 4]], keep: true, fn: function () {
        U.setSeason(U.SEASONS[(U.SEASONS.indexOf(U.season) + 1) % 4], true).then(menu);
      } },
      { label: '중앙현관으로 돌아가기', fn: function () { var s = G.data.school.entrance; E.loadMap('school', [s.x, s.y + 2]); } },
      { label: '기록 지우기', fn: function () { U.modal('기록 지우기', '이 기기의 장소 카드와 최고 기록을 모두 지울까요?', [{ label: '지우기', fn: function () { U.clear(); G.save = U.load(); updateCount(); U.toast('기록을 지웠어요.'); } }, { label: '취소' }]); } },
      { label: '처음 화면', fn: G.toTitle },
      { label: '닫기' }
    ]);
  }

  /* ---------- 지도 ---------- */
  function pinFromPlayer() {
    var m = E.map; if (!m) return null;
    var t = E.tileOf(), M = G.data.plan.marginTiles;
    if (m.id === 'school') return { floor: 0, tile: t };
    if (/^floor\d$/.test(m.id)) return { floor: m.floor, m: [t[0] - M + 0.5, t[1] - M + 0.5] };
    var p = places[m.place];
    return p && p.center ? { floor: p.floor, m: p.center } : null;
  }
  function openMap(fromTitle) {
    if (fromTitle) { MV.show({ standalone: false, pin: kioskPin(), tab: 1, route: true, title: '서라벌여중 길 안내' }); return; }
    E.paused = true;
    var pin = pinFromPlayer();
    MV.show({ pin: pin, tab: pin ? pin.floor : 1 });
  }
  function kioskPin() { var k = G.data.graph.kiosk; return { floor: k.floor, m: [k.x, k.y] }; }
  G.kioskPin = kioskPin;
  G.arrive = arrive;
  SRB.G = G;
})();
