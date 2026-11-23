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
  /* Press input that works on every browser: Pointer Events when the browser has them, otherwise touch
     events (older built-in browsers such as the signage display) plus mouse. Handlers get {x, y, id, target}. */
  U.press = function (el, h) {
    function fire(fn, x, y, id, target) { if (fn) fn({ x: x, y: y, id: id, target: target }); }
    if (window.PointerEvent) {
      el.addEventListener('pointerdown', function (e) {
        try { el.setPointerCapture(e.pointerId); } catch (x) {}
        fire(h.down, e.clientX, e.clientY, e.pointerId, e.target); e.preventDefault();
      });
      el.addEventListener('pointermove', function (e) { fire(h.move, e.clientX, e.clientY, e.pointerId, e.target); });
      el.addEventListener('pointerup', function (e) { fire(h.up, e.clientX, e.clientY, e.pointerId, e.target); });
      el.addEventListener('pointercancel', function (e) { fire(h.cancel || h.up, e.clientX, e.clientY, e.pointerId, e.target); });
      return;
    }
    var lastTouch = 0, mouseDown = false;
    function each(e, fn) {
      lastTouch = Date.now();
      for (var i = 0; i < e.changedTouches.length; i++) {
        var t = e.changedTouches[i];
        fire(fn, t.clientX, t.clientY, t.identifier, document.elementFromPoint(t.clientX, t.clientY) || e.target);
      }
    }
    el.addEventListener('touchstart', function (e) { each(e, h.down); e.preventDefault(); }, false);
    el.addEventListener('touchmove', function (e) { each(e, h.move); e.preventDefault(); }, false);
    el.addEventListener('touchend', function (e) { each(e, h.up); e.preventDefault(); }, false);
    el.addEventListener('touchcancel', function (e) { each(e, h.cancel || h.up); }, false);
    el.addEventListener('mousedown', function (e) {
      if (Date.now() - lastTouch < 800) return;           // the browser's copy of a touch
      mouseDown = true; fire(h.down, e.clientX, e.clientY, 'mouse', e.target); e.preventDefault();
    });
    window.addEventListener('mousemove', function (e) { if (mouseDown) fire(h.move, e.clientX, e.clientY, 'mouse', e.target); });
    window.addEventListener('mouseup', function (e) { if (!mouseDown) return; mouseDown = false; fire(h.up, e.clientX, e.clientY, 'mouse', e.target); });
  };
  // a plain tap on a non-button element (title halves): click everywhere, plus touchend where click may not come
  U.tap = function (el, fn) {
    var t0 = 0;
    function inButton(n) { for (; n && n !== el; n = n.parentNode) if (n.tagName === 'BUTTON') return true; return false; }
    el.addEventListener('touchend', function (e) {
      if (e.changedTouches.length !== 1 || inButton(e.target)) return;   // e.g. a character button inside the half
      t0 = Date.now(); e.preventDefault(); fn(e);
    }, false);
    el.addEventListener('click', function (e) { if (Date.now() - t0 > 800) fn(e); });
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
