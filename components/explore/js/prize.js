/* 서라벌 탐방 — 79곳 완료 상품: 학번·이름 받기 → GitHub 저장소에 기록 → "2층 교무실 선생님에게 찾아가세요".
   GitHub 열쇠(토큰)는 공개 코드에 넣지 않습니다(공개 저장소에 올리면 GitHub가 바로 폐기함).
   선생님이 사이니지 기기에서 ?setup 주소로 한 번 입력하면 그 기기 localStorage에만 저장됩니다.
   보내기에 실패해도 기록은 기기에 남고, 다음에 자동으로 다시 보냅니다. */
(function () {
  'use strict';
  var U = SRB.U;
  var CFG = 'srb.explore.github', LOG = 'srb.explore.winners';
  var P = {};

  function get(k, d) { try { var v = JSON.parse(localStorage.getItem(k) || 'null'); return v == null ? d : v; } catch (e) { return d; } }
  function put(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); return true; } catch (e) { return false; } }
  function pad(n, w) { n = String(n); while (n.length < (w || 2)) n = '0' + n; return n; }
  function stamp(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate()) + ' ' + pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
  }
  function hash(s) { var h = 5381; for (var i = 0; i < s.length; i++) h = ((h * 33) ^ s.charCodeAt(i)) >>> 0; return 'h' + h.toString(36); }
  function b64(str) { return btoa(unescape(encodeURIComponent(str))); }

  P.config = function () { return get(CFG, { repo: '', token: '', branch: '', pin: '' }); };
  P.ready = function () { var c = P.config(); return !!(c.repo && c.token); };
  P.log = function () { return get(LOG, []); };

  /* GitHub Contents API: one file per record, so nothing ever needs merging. XHR works on every browser. */
  function request(method, url, token, body) {
    return new Promise(function (ok, fail) {
      var x = new XMLHttpRequest();
      x.open(method, url);
      x.setRequestHeader('Accept', 'application/vnd.github+json');
      x.setRequestHeader('Authorization', 'Bearer ' + token);
      if (body) x.setRequestHeader('Content-Type', 'application/json');
      x.timeout = 15000;
      x.onload = function () { if (x.status >= 200 && x.status < 300) ok(x.status); else fail(new Error('GitHub ' + x.status)); };
      x.onerror = function () { fail(new Error('연결 안 됨')); };
      x.ontimeout = function () { fail(new Error('시간 초과')); };
      x.send(body ? JSON.stringify(body) : null);
    });
  }
  function send(entry) {
    var c = P.config();
    if (!c.repo || !c.token) return Promise.reject(new Error('저장소 설정 없음'));
    var r = entry.record, path = 'records/' + entry.day + '/' + entry.file;
    var body = { message: '서라벌 탐방 완료 ' + r['학번'] + ' ' + r['이름'], content: b64(JSON.stringify(r, null, 2) + '\n') };
    if (c.branch) body.branch = c.branch;
    return request('PUT', 'https://api.github.com/repos/' + c.repo + '/contents/' + path.split('/').map(encodeURIComponent).join('/'), c.token, body);
  }
  function mark(id, sent, err) {
    var log = P.log();
    for (var i = 0; i < log.length; i++) if (log[i].id === id) { log[i].sent = sent; log[i].error = err || ''; }
    put(LOG, log);
  }
  /* save locally first, then try GitHub; resolves {sent, error} (never rejects) */
  P.submit = function (num, name, places) {
    var d = new Date();
    var record = { '학번': num, '이름': name, '완료 시각': stamp(d), '장소 수': places, '게임': '서라벌 탐방' };
    var entry = {
      id: d.getTime() + '-' + num, record: record, sent: false, error: '',
      day: stamp(d).slice(0, 10), file: stamp(d).slice(11).replace(/:/g, '') + '-' + num.replace(/[^0-9A-Za-z]/g, '') + '.json'
    };
    var log = P.log(); log.push(entry); put(LOG, log);
    return send(entry).then(function () { mark(entry.id, true); return { sent: true }; },
      function (e) { mark(entry.id, false, e.message); return { sent: false, error: e.message }; });
  };
  P.flush = function () {
    if (!P.ready()) return Promise.resolve(0);
    var pending = P.log().filter(function (e) { return !e.sent; }), n = 0;
    return pending.reduce(function (pr, e) {
      return pr.then(function () { return send(e).then(function () { mark(e.id, true); n++; }, function (x) { mark(e.id, false, x.message); }); });
    }, Promise.resolve()).then(function () { return n; });
  };

  /* ---------- 학생: 학번·이름 ---------- */
  P.form = function (places, done) {
    var w = U.el('div', { 'class': 'prize-form' });
    w.appendChild(U.el('p', { 'class': 'prize-big' }, '장소 ' + places + '곳을 모두 탐방했어요! 축하해요!'));
    w.appendChild(U.el('p', null, '상품을 받을 수 있도록 학번과 이름을 적어 주세요.'));
    var num = U.el('input', { type: 'text', inputmode: 'numeric', maxlength: '8', autocomplete: 'off', placeholder: '학번 (예: 10203)', 'aria-label': '학번' });
    var name = U.el('input', { type: 'text', maxlength: '20', autocomplete: 'off', placeholder: '이름', 'aria-label': '이름' });
    var msg = U.el('p', { 'class': 'prize-msg' });
    w.appendChild(U.el('label', null, '학번')); w.appendChild(num);
    w.appendChild(U.el('label', null, '이름')); w.appendChild(name);
    w.appendChild(msg);
    var busy = false;
    U.modal('서라벌 탐방 완료!', w, [{ label: '저장하기', primary: true, keep: true, fn: function () {
      if (busy) return;
      var n = (num.value || '').replace(/\s+/g, ''), m = (name.value || '').replace(/^\s+|\s+$/g, '');
      if (!/^[0-9]{3,8}$/.test(n)) { msg.textContent = '학번을 숫자로 적어 주세요.'; num.focus(); return; }
      if (m.length < 2) { msg.textContent = '이름을 적어 주세요.'; name.focus(); return; }
      busy = true; msg.textContent = '저장하는 중이에요…';
      P.submit(n, m, places).then(function (res) { busy = false; U.closeModal(); P.finish(m, res, done); });
    } }]);
  };
  P.finish = function (name, res, done) {
    var w = U.el('div', { 'class': 'prize-form' });
    w.appendChild(U.el('p', { 'class': 'prize-big' }, name + ' 학생, 저장했어요!'));
    w.appendChild(U.el('p', { 'class': 'prize-go' }, '2층 교무실 선생님에게 찾아가세요.'));
    if (!res.sent) w.appendChild(U.el('p', { 'class': 'muted' }, '(인터넷 연결이 안 돼서 기록은 이 기기에 보관했어요. 연결되면 자동으로 보내요.)'));
    U.modal('상품 안내', w, [{ label: '확인', primary: true, fn: done }]);
  };

  /* ---------- 선생님: ?setup ---------- */
  P.setup = function () {
    var c = P.config();
    if (c.pin) {
      var w0 = U.el('div'), pin = U.el('input', { type: 'password', inputmode: 'numeric', maxlength: '12', placeholder: '선생님 PIN', 'aria-label': '선생님 PIN' });
      var m0 = U.el('p', { 'class': 'prize-msg' });
      w0.appendChild(pin); w0.appendChild(m0);
      U.modal('선생님 설정', w0, [{ label: '열기', primary: true, keep: true, fn: function () {
        if (hash(pin.value || '') === c.pin) { U.closeModal(); settings(); } else m0.textContent = 'PIN이 맞지 않아요.';
      } }, { label: '닫기' }]);
    } else settings();
  };
  function settings() {
    var c = P.config(), log = P.log();
    var w = U.el('div', { 'class': 'prize-form' });
    w.appendChild(U.el('p', null, '79곳을 모두 찾은 학생의 학번·이름을 기록할 GitHub 저장소입니다. 학생 이름이 들어가므로 반드시 비공개(Private) 저장소를 쓰세요.'));
    var repo = U.el('input', { type: 'text', autocomplete: 'off', placeholder: '저장소 (예: pse915/srbschoolex-records)', 'aria-label': '저장소' }); repo.value = c.repo || '';
    var token = U.el('input', { type: 'password', autocomplete: 'off', placeholder: c.token ? '열쇠 저장됨 — 바꿀 때만 입력' : 'GitHub 열쇠(토큰)', 'aria-label': 'GitHub 토큰' });
    var branch = U.el('input', { type: 'text', autocomplete: 'off', placeholder: '브랜치 (비우면 기본 브랜치)', 'aria-label': '브랜치' }); branch.value = c.branch || '';
    var pin = U.el('input', { type: 'password', inputmode: 'numeric', maxlength: '12', placeholder: c.pin ? 'PIN 저장됨 — 바꿀 때만 입력' : '선생님 PIN (선택, 이 화면 잠금)', 'aria-label': '선생님 PIN' });
    var msg = U.el('p', { 'class': 'prize-msg' });
    [['저장소', repo], ['열쇠', token], ['브랜치', branch], ['PIN', pin]].forEach(function (r) { w.appendChild(U.el('label', null, r[0])); w.appendChild(r[1]); });
    var pending = log.filter(function (e) { return !e.sent; }).length;
    w.appendChild(U.el('p', { 'class': 'muted' }, '이 기기의 완료 기록 ' + log.length + '건 (보내지 못한 기록 ' + pending + '건)'));
    var list = U.el('ol', { 'class': 'prize-list' });
    log.slice(-20).reverse().forEach(function (e) {
      list.appendChild(U.el('li', null, e.record['완료 시각'] + ' · ' + e.record['학번'] + ' ' + e.record['이름'] + (e.sent ? '' : ' (보관 중: ' + (e.error || '미전송') + ')')));
    });
    w.appendChild(list); w.appendChild(msg);
    function save() {
      var n = P.config();
      n.repo = (repo.value || '').replace(/^\s+|\s+$/g, '').replace(/^https?:\/\/github\.com\//, '').replace(/\/+$/, '');
      n.branch = (branch.value || '').replace(/^\s+|\s+$/g, '');
      if (token.value) n.token = token.value.replace(/\s+/g, '');
      if (pin.value) n.pin = hash(pin.value);
      put(CFG, n); token.value = ''; pin.value = '';
      return n;
    }
    U.modal('선생님 설정', w, [
      { label: '저장', primary: true, keep: true, fn: function () {
        var n = save();
        msg.textContent = /^[^\/\s]+\/[^\/\s]+$/.test(n.repo) && n.token ? '저장했어요. [연결 시험]으로 확인해 보세요.' : '저장소(이름/저장소)와 열쇠를 모두 넣어 주세요.';
      } },
      { label: '연결 시험', keep: true, fn: function () {
        var n = save(); msg.textContent = '확인하는 중…';
        if (!n.repo || !n.token) { msg.textContent = '저장소와 열쇠를 먼저 넣어 주세요.'; return; }
        request('GET', 'https://api.github.com/repos/' + n.repo, n.token).then(function () {
          msg.textContent = '연결됐어요. 이제 완료 기록이 이 저장소의 records/ 폴더에 쌓여요.';
        }, function (e) { msg.textContent = '연결 실패: ' + e.message + ' (저장소 이름, 열쇠 권한 Contents: Read and write 를 확인하세요)'; });
      } },
      { label: '보관 기록 다시 보내기', keep: true, fn: function () {
        msg.textContent = '보내는 중…';
        P.flush().then(function (k) { msg.textContent = k + '건 보냈어요.'; });
      } },
      { label: '열쇠 지우기', keep: true, fn: function () { var n = P.config(); n.token = ''; put(CFG, n); msg.textContent = '이 기기에서 열쇠를 지웠어요.'; token.placeholder = 'GitHub 열쇠(토큰)'; } },
      { label: '닫기' }
    ]);
  }

  // 보관 중인 기록은 시작할 때와 5분마다 다시 보내 본다
  setTimeout(function () { P.flush(); }, 4000);
  setInterval(function () { P.flush(); }, 300000);
  SRB.P = P;
})();
