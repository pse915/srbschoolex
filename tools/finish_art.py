"""Record school evidence + map connectivity; optionally re-normalize the environment atlas.
  python tools/finish_art.py            -> data/school_evidence.json, docs/evidence/graphics-connectivity.json, manifest (sizes/hashes)
  python tools/finish_art.py --atlas    -> also rebuilds environment.png from environment-source.png (v3 step)
The connectivity check itself lives in tools/check_maps.py (v6: 중앙현관 -> every room/stair/EV/restroom).
"""
from pathlib import Path
from PIL import Image
import json, hashlib, sys
root = Path(__file__).resolve().parents[1]; a = root / 'components/rpg_game/assets'; data = root / 'components/rpg_game/data'
sys.path.insert(0, str(root / 'tools'))
import check_maps, school_art as SA  # noqa: E402

if '--atlas' in sys.argv:
    from clean_atlas import clean
    im = Image.open(a / 'environment-source.png').convert('RGBA'); im.resize((1024, 1024), Image.Resampling.NEAREST).save(a / 'environment.png')
    clean(a / 'environment.png')
maps = check_maps.load_maps()
result = check_maps.check(maps)
layout = SA.load_layout(); plans = SA.all_plans(layout)
unconfirmed = [dict(floor=f, id=e['id'], name=e.get('name')) for f, p in plans.items() for e in p['items'] if e.get('confirmed') is False]
school = {
    'version': 2, 'schoolName': '서라벌여중',
    'evidenceScope': '교실배치도(docs/kiosk/floorplan.jpg), 운동장 사진(docs/kiosk/photo-playground.jpg), 교사가 확인한 실 이름(docs/kiosk/00_서라벌여중_배치_기준표.md)',
    'confirmedFromUserBrief': [
        {'feature': '학습지원실2와 행정자료실 사이 꺾임 계단에서 서쪽 동이 남쪽으로 90° 꺾이는 ┌자 구조(1~4층)', 'status': '교실배치도 + 운동장 사진으로 확인'},
        {'feature': '층별 실 이름과 순서(안쪽/바깥쪽)', 'status': '교사 확인 · data/school_layout.json'},
        {'feature': '중앙현관은 본관 남쪽(운동장 쪽) 면, 바로 북쪽에 중앙계단, EV는 중앙계단 서쪽', 'status': '기준표 1장'},
        {'feature': '시계탑·유리 커튼월 없음, 짙은 회색 캐노피 + 흰 기둥 현관, 화강석 조회대, 서쪽 동 끝 아치 지붕', 'status': '운동장 사진'},
    ],
    'inferred': [
        {'feature': '건물 치수(깊이 18m, 본관 104m, 서쪽 동 56m, 층고 3.6m), 실 폭, 계단·EV 정확한 위치', 'status': '사진·배치도 기반 추정 (tools/school_art.py 상수)'},
        {'feature': '배치도에 "…"로 표시된 바깥쪽 지원공간', 'status': '이름 없이 빈 칸으로 둠 (지어내지 않음)'},
        {'feature': '실 내부 가구 배치', 'status': '게임용 구성'},
    ],
    'unconfirmed': unconfirmed,
    'floorMaps': [{'id': f'floor{f}', 'roomCount': sum(e['kind'] in ('room', 'restroom') for e in p['items']), 'shape': '┌자 복도 (본관 동서 + 꺾임 계단 + 서쪽 동 남북)',
                   'status': 'data/school_layout.json 기준'} for f, p in plans.items()],
    'schoolRoomCount': sum(k.startswith('room-') for k in maps),
    'indoorRoomCount': sum(m['kind'] == 'room' for m in maps.values()),
    'realPlanValidation': '교실배치도 기준 배치. 치수는 추정치이며 실측 도면이 아님',
}
(data / 'school_evidence.json').write_text(json.dumps(school, ensure_ascii=False, indent=2), encoding='utf-8')
(root / 'docs/evidence/graphics-connectivity.json').write_text(json.dumps({**result, 'roomCount': school['schoolRoomCount']}, ensure_ascii=False, indent=2), encoding='utf-8')
manifest = json.loads((a / 'manifest.json').read_text(encoding='utf-8')); manifest['version'] = 3; manifest['schoolEvidence'] = 'data/school_evidence.json'
manifest['avatarSheet'] = json.loads((a / 'avatars.json').read_text())
manifest['assets'] = [dict(file=p.name, width=Image.open(p).width, height=Image.open(p).height, mode=Image.open(p).mode, sha256=hashlib.sha256(p.read_bytes()).hexdigest(), source=p.stem.endswith('-source')) for p in sorted(a.glob('*.png'))]
(a / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'maps': len(maps), 'rooms': school['schoolRoomCount'], 'errors': result['errors']}, ensure_ascii=True))
sys.exit(1 if result['errors'] else 0)
