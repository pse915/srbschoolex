/* 서라벌 탐방 — shared helpers. Plain script (no modules / bundler) for older built-in browsers. */
var SRB = window.SRB || {};
window.SRB = SRB;
(function () {
  'use strict';
  var U = {};
  U.$ = function (id) { return document.getElementById(id); };
  U.el = function (tag, attrs, text) {
    var e = document.createElement(tag);
    if (attrs) for (var k in attrs) { if (k === 'class') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); }
    if (text != null) e.textContent = text;
    return e;
  };
  U.getJSON = function (url) {
    if (!window.fetch) return new Promise(function (ok, fail) {  // very old built-in browsers
      var x = new XMLHttpRequest();
      x.open('GET', url);
      x.onload = function () { if (x.status >= 200 && x.status < 300) { try { ok(JSON.parse(x.responseText)); } catch (e) { fail(e); } } else fail(new Error(url + ' ' + x.status)); };
      x.onerror = function () { fail(new Error(url)); };
      x.send();
    });
    return fetch(url).then(function (r) { if (!r.ok) throw new Error(url + ' ' + r.status); return r.json(); });
  };
  U.images = {};
  U.loadImage = function (name) {
    return new Promise(function (ok, fail) {
      var im = new Image();
      im.onload = function () { U.images[name] = im; ok(im); };
      im.onerror = function () { fail(new Error('image ' + name)); };
      im.src = 'assets/' + name + '.png';
    });
  };
  /* ---------- 계절 (봄·여름·가을·겨울 그림) ---------- */
  U.SEASONS = ['spring', 'summer', 'autumn', 'winter'];
  U.SEASON_KO = { auto: '자동', spring: '봄', summer: '여름', autumn: '가을', winter: '겨울' };
  U.SEASON_IMAGES = ['terrain', 'trees', 'school', 'school-ground', 'school-annex', 'school-gate-east', 'school-gate-north'];
  var SEASON_KEY = 'srb.explore.season';
  U.autoSeason = function (d) {           // 3~5월 봄, 6~8월 여름, 9~11월 가을, 12~2월 겨울
    var m = (d || new Date()).getMonth() + 1;
    return m >= 3 && m <= 5 ? 'spring' : m >= 6 && m <= 8 ? 'summer' : m >= 9 && m <= 11 ? 'autumn' : 'winter';
  };
  U.seasonChoice = function () {          // 'auto' or a season; ?season=winter wins for this visit
    var q = /[?&]season=(\w+)/.exec(location.search);
    if (q && U.SEASONS.indexOf(q[1]) >= 0) return q[1];
    try { var v = localStorage.getItem(SEASON_KEY); if (v && (v === 'auto' || U.SEASONS.indexOf(v) >= 0)) return v; } catch (e) {}
    return 'auto';
  };
  U.season = 'summer';
  U.loadSeason = function (s) {
    return Promise.all(U.SEASON_IMAGES.map(function (n) {
      return U.images[n + '-' + s] ? U.images[n + '-' + s] : U.loadImage(n + '-' + s);
    }));
  };
  // choice: 'auto' | season. Loads that season's pictures, then switches.
  U.setSeason = function (choice, remember) {
    if (remember) { try { localStorage.setItem(SEASON_KEY, choice); } catch (e) {} }
    var s = choice === 'auto' ? U.autoSeason() : choice;
    U.seasonPick = choice;
    return U.loadSeason(s).then(function () { U.season = s; if (U.onSeason) U.onSeason(s); return s; });
  };
  U.img = function (name) { return U.images[name + '-' + U.season] || U.images[name]; };

  // 받침에 따라 조사 고르기 (은/는, 이/가, 을/를, 으로/로, 이에요/예요)
  U.josa = function (word, a, b) {
    for (var i = word.length - 1; i >= 0; i--) {
      var c = word.charCodeAt(i);
      if (c >= 0xAC00 && c <= 0xD7A3) {
        var jong = (c - 0xAC00) % 28;
        if (a === '으로' && jong === 8) return b;      // ㄹ 받침은 '로'
        return jong ? a : b;
      }
    }
    return /[013678lmnr]$/i.test(word) ? a : b;
  };
  U.fmtTime = function (sec) {
    sec = Math.max(0, Math.round(sec));
    return Math.floor(sec / 60) + ':' + ('0' + (sec % 60)).slice(-2);
  };
  // 기기에만 익명 저장 (서버 저장 없음)
  var KEY = 'srb.explore.v1';
  U.load = function () {
    try { var s = JSON.parse(localStorage.getItem(KEY) || 'null'); if (s && s.v === 1) return s; } catch (e) {}
    return { v: 1, avatar: 0, cards: {}, best: null, plays: 0, timer: true };
  };
  U.save = function (s) { try { localStorage.setItem(KEY, JSON.stringify(s)); } catch (e) {} };
  U.clear = function () { try { localStorage.removeItem(KEY); } catch (e) {} };
  // Streamlit component bridge (no-op outside Streamlit)
  U.inStreamlit = window.parent !== window;
  U.bridge = function (type, extra) {
    if (!U.inStreamlit) return;
    var msg = { isStreamlitMessage: true, type: type };
    if (extra) for (var k in extra) msg[k] = extra[k];
    try { window.parent.postMessage(msg, '*'); } catch (e) {}
  };
  U.toastTimer = 0;
  U.toast = function (text) {
    var t = U.$('toast'); if (!t) return;
    t.textContent = text; t.className = 'toast show';
    clearTimeout(U.toastTimer); U.toastTimer = setTimeout(function () { t.className = 'toast'; }, 2200);
  };
  // 창 (모달)
  U.modal = function (title, body, actions) {
    U.$('modalTitle').textContent = title;
    var b = U.$('modalBody'); b.innerHTML = '';
    if (typeof body === 'string') b.appendChild(U.el('p', null, body)); else if (body) b.appendChild(body);
    var a = U.$('modalActions'); a.innerHTML = '';
    (actions && actions.length ? actions : [{ label: '닫기' }]).forEach(function (act) {
      var btn = U.el('button', { type: 'button', 'class': act.primary ? 'primary' : '' }, act.label);
      btn.onclick = function () { if (!act.keep) U.closeModal(); if (act.fn) act.fn(); };
      a.appendChild(btn);
    });
    U.$('modal').hidden = false;
    var first = a.querySelector('button'); if (first) first.focus();
  };
  U.closeModal = function () { U.$('modal').hidden = true; if (U.onModalClose) U.onModalClose(); };
  U.modalOpen = function () { return !U.$('modal').hidden; };
  SRB.U = U;
})();
