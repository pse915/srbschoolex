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
