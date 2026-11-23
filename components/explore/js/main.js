/* 서라벌 탐방 — boot. ?map (or Streamlit arg mode="map") opens only the school map. */
(function () {
  'use strict';
  var U = SRB.U;
  var IMAGES = ['terrain', 'environment', 'furniture', 'facilities', 'details', 'avatars', 'npcs', 'school', 'school-ground',
    'school-annex', 'school-gate-east', 'school-gate-north', 'school-fountain', 'map-pin', 'stamp',
    'floor-plan-1', 'floor-plan-2', 'floor-plan-3', 'floor-plan-4', 'stack-floor-1', 'stack-floor-2', 'stack-floor-3', 'stack-floor-4',
    'interior-tiles', 'interior-props'];
  var mapOnly = /[?&]map\b/.test(location.search), booted = false, data = null;

  function frameHeight() { U.bridge('streamlit:setFrameHeight', { height: Math.max(640, Math.min(980, (window.screen && screen.height ? screen.height : 900) - 140)) }); }
  function openMapOnly() {
    U.$('title').hidden = true; U.$('play').hidden = true;
    SRB.MV.show({ standalone: true, pin: SRB.G.kioskPin(), tab: 1 });
  }
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.type !== 'streamlit:render') return;
    var args = d.args || {};
    if (args.mode === 'map') { mapOnly = true; if (booted) openMapOnly(); }
    frameHeight();
  });
  U.bridge('streamlit:componentReady', { apiVersion: 1 });
  frameHeight();

  Promise.all([U.getJSON('data/places.json')].concat(IMAGES.map(U.loadImage))).then(function (r) {
    data = r[0];
    SRB.E.init(U.$('world'), U.$('mini'));
    SRB.MV.init(data);
    SRB.G.init(data);
    booted = true;
    if (mapOnly) openMapOnly();
    if (/[?&]setup\b/.test(location.search)) SRB.P.setup();      // 선생님: GitHub 기록 설정
    window.__explore = { data: data, E: SRB.E, MV: SRB.MV, G: SRB.G };
  }).catch(function (err) {
    U.$('titleNote').textContent = '불러오지 못했어요: ' + err.message;
    console.error(err);
  });
})();
