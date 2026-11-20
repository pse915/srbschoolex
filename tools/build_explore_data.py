"""Build data for the new exploration game (components/explore) from the school sources.
  python tools/build_explore_data.py

Inputs (never edited here):
  data/school_layout.json, components/rpg_game/assets/{kiosk-plan.json, school-footprint.json, explore-art.json},
  components/rpg_game/data/maps/{school,floor1~4,room-*}.json  (terrain, collision, furniture, portals only)
Outputs (generated; do not edit by hand):
  components/explore/data/places.json      places, floors, corridor graph, school-map placement
  components/explore/data/maps/*.json      maps WITHOUT the life-design story (no npcs/interactions/futureLayers)
  components/explore/assets/*.png          copies of the source PNGs (+ assets.json with sha256)
  components/explore/assets/interior-*.png corridor / entrance / broadcasting-room art (tools/interior_art.py)
Deterministic: the same inputs always give byte-identical outputs.
"""
import hashlib, json, math, shutil, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'components' / 'rpg_game'
OUT = ROOT / 'components' / 'explore'
sys.path.insert(0, str(ROOT / 'tools'))
import school_art as SA  # noqa: E402
import interior_art as IA  # noqa: E402

ASSETS = ['school.png', 'school-ground.png', 'school-annex.png', 'school-gate-east.png', 'school-gate-north.png',
          'school-fountain.png', 'school-hero.png', 'terrain.png', 'environment.png', 'furniture.png', 'facilities.png',
          'details.png', 'avatars.png', 'npcs.png', 'map-pin.png', 'stamp.png'] + \
         [f'floor-plan-{f}.png' for f in range(1, 5)] + [f'stack-floor-{f}.png' for f in range(1, 5)]
CATEGORIES = {
    'classroom': {'label': '교실', 'color': '#eed6b2'},
    'office': {'label': '교무·행정', 'color': '#c0d2e6'},
    'special': {'label': '특별실', 'color': '#cce0ba'},
    'care': {'label': '학생 지원', 'color': '#f0cec8'},
    'service': {'label': '지원 공간', 'color': '#cecac4'},
    'restroom': {'label': '화장실', 'color': '#b0c4cc'},
    'lobby': {'label': '현관', 'color': '#dad8d2'},
    'stair': {'label': '계단', 'color': '#d6cec2'},
    'ev': {'label': '엘리베이터', 'color': '#464a50'},
    'outdoor': {'label': '교정', 'color': '#e2d6b8'},
}
WING = {'main': '본관', 'west': '서쪽 동', 'corner': '꺾임부', 'site': '교정'}
SIDE = {'inner': '운동장 쪽', 'outer': '바깥쪽'}
STORY_KEYS = ('npcs', 'interactions', 'futureLayers', 'landmarks', 'endingView', 'floorplanSource', 'layout')


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p, v):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(v, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')


def josa(word, a, b):
    """은/는, 이/가 ... by the final consonant of the last Hangul syllable."""
    ch = next((c for c in reversed(word) if '가' <= c <= '힣'), None)
    if ch is None:
        last = word[-1:] if word else ''
        return a if last in '013678LMNRlmnr' else b
    return a if (ord(ch) - 0xAC00) % 28 else b


def intro(p):
    if p.get('description'):
        return p['description']
    n, cat = p['label'], p['category']
    where = '교정' if p['floor'] == 0 else f"{p['floor']}층 {WING.get(p['wing'], '')} {SIDE.get(p['side'], '')}".strip()
    base = {
        'classroom': f'{n} 교실이에요. 학생들이 하루 대부분을 보내는 곳이에요.',
        'office': f'{n}{josa(n, "은", "는")} 선생님과 교직원이 일하는 곳이에요. 들어갈 때는 노크하고 인사해요.',
        'special': f'{n}{josa(n, "은", "는")} 특별한 수업이나 활동을 하는 곳이에요.',
        'care': f'{n}{josa(n, "은", "는")} 학생을 돕는 공간이에요. 도움이 필요할 때 찾아가요.',
        'service': f'{n}{josa(n, "은", "는")} 학교 생활을 뒷받침하는 지원 공간이에요.',
        'restroom': f'{n}{josa(n, "이에요", "예요")}. 깨끗하게 써요.',
        'outdoor': f'{n}{josa(n, "은", "는")} 교정에 있는 장소예요.',
    }.get(cat, f'{n}이에요.')
    return f'{base} ({where})'


def centroid(poly):
    return [round(sum(p[0] for p in poly) / len(poly), 3), round(sum(p[1] for p in poly) / len(poly), 3)]


# ---------- interior look (from the school photos; tools/interior_art.py) ----------
N4 = ((0, -1), (0, 1), (-1, 0), (1, 0))
STAIR, EV, VOID, DOOR, WALLT, CORR, LOBBY, OUTSIDE = 53, 60, 61, 52, 62, 50, 51, 7


def _tid(k):
    return IA.TILE_BASE + IA.TILE[k]


def _prop(name, x, y, **kw):
    sx, sy, w, h = IA.prop_rects()[name]
    o = {'image': 'interior-props', 'src': [sx, sy, w, h], 'x': round(x, 4), 'y': round(y, 4), 'w': w, 'h': h}
    o.update(kw)
    return o


def decorate_floor(m):
    """Terrazzo corridor, white walls with a wooden rail, lime pillars/door frames, teal room signs."""
    W, H = m['width'], m['height']
    orig, tiles, solid = list(m['tiles']), m['tiles'], m['solid']

    def at(x, y):
        return orig[y * W + x] if 0 <= x < W and 0 <= y < H else OUTSIDE

    def walk(x, y):
        return 0 <= x < W and 0 <= y < H and not solid[y * W + x]

    doors, objs = {}, []
    for pt in m['portals']:
        if pt['type'] != 'door' or pt['target'] == 'school':
            continue
        for dx, dy in N4:
            x, y = pt['x'] + dx, pt['y'] + dy
            if at(x, y) == DOOR:
                doors[(x, y)] = (dx, dy, '화장실' in pt['label'])
                pt['signed'] = True
                objs.append({'sign': pt['label'], 'x': x + 0.5, 'y': y - 0.3 if dy else y - 0.45})
                break
    face_above = set()
    for y in range(H):
        for x in range(W):
            i = y * W + x
            t = orig[i]
            if not solid[i]:
                if t == CORR:
                    tact = any(at(x + a, y + b) in (STAIR, EV) for a, b in N4)
                    tiles[i] = _tid('tactile') if tact else IA.TILE_BASE + (x * 7 + y * 13) % 4
                elif t == LOBBY:
                    tiles[i] = _tid('lobby')
                continue
            if t in (OUTSIDE, STAIR, VOID):
                continue
            nb = [(a, b) for a, b in N4 if walk(x + a, y + b)]
            if t == EV:
                tiles[i] = _tid('evDoor' if any(b for a, b in nb) else 'top')
                continue
            lobby_side = any(at(x + a, y + b) == LOBBY for a, b in nb)
            if (x, y) in doors:
                dx, dy, rest = doors[(x, y)]
                if dy:
                    tiles[i] = _tid('frost' if rest else 'door')
                else:
                    tiles[i] = _tid(('sideFrost' if rest else 'sideDoor') + ('L' if dx == -1 else 'R'))
            elif any(b for a, b in nb):
                single = t == WALLT and (at(x - 1, y) != WALLT or at(x + 1, y) != WALLT)
                tiles[i] = _tid('pillar' if single else 'wall')
                if (0, 1) in nb:
                    face_above.add((x, y))
            elif nb:
                right = nb[0][0] == 1
                tiles[i] = _tid(('panel' if lobby_side else 'side') + ('L' if right else 'R'))
            else:
                tiles[i] = _tid('top')
    # green notice boards on long plain stretches of the wall above the corridor
    plain = _tid('wall')
    for y in range(H):
        x = 0
        while x < W:
            if (x, y) in face_above and tiles[y * W + x] == plain:
                x0 = x
                while x < W and (x, y) in face_above and tiles[y * W + x] == plain:
                    x += 1
                if x - x0 >= 6:
                    c = x0 + (x - x0) // 2 - 1
                    tiles[y * W + c], tiles[y * W + c + 1] = _tid('boardL'), _tid('boardR')
            x += 1
    m['objects'] = objs          # the old arched brick doorways are replaced by the door tiles


def decorate_lobby(m):
    """중앙현관: polished floor, wooden walls, glass double doors with a clock, signage kiosk, plant, banner."""
    W = m['width']
    pts = [(i % W, i // W) for i, t in enumerate(m['tiles']) if t == _tid('lobby')]
    x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
    y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    door = next(p for p in m['portals'] if p['type'] == 'door' and p['target'] == 'school')
    keep = {(door['x'], door['y']), tuple(m['spawn']), (door['x'], door['y'] - 1)}
    objs = [_prop('glassFront', x0 - 1, y1 + 1, sortY=y1 + 3)]

    def stand(name, tx, ty):
        if (tx, ty) in keep:
            return
        w, h = IA.prop_rects()[name][2:]
        objs.append(_prop(name, tx + (32 - w) / 64, ty + 1 - h / 32 - 0.05, sortY=ty + 0.9))
        m['solid'][ty * W + tx] = 1

    stand('kiosk', x1, y0 + 2)
    stand('plant', x0, y1 - 1)
    stand('xbanner', x1, y1 - 2)
    objs.append(_prop('calligraphy', x1 + 1 + 9 / 32, y0 + 1, ground=True))
    m['objects'] = m['objects'] + objs


def decorate_studio(m):
    """방송실: dark floor, booth window with ON AIR, booth door, console desk, rack, wall panels, chairs."""
    W = m['width']
    orig, tiles, solid = list(m['tiles']), m['tiles'], m['solid']
    floor = [i for i, t in enumerate(orig) if t in (20, 21, 22, 23)]
    rx0, rx1 = min(i % W for i in floor), max(i % W for i in floor)
    ry0 = min(i // W for i in floor)
    for i, t in enumerate(orig):
        x, y = i % W, i // W
        if t in (20, 21, 22, 23):
            tiles[i] = _tid('studioFloor')
            solid[i] = 0
        elif t == 32:
            tiles[i] = _tid('studioWallU' if orig[i - W] == OUTSIDE else 'studioWallD')
        elif t == 33:
            tiles[i] = _tid('studioSideL' if x < rx0 else 'studioSideR')
        elif t == 40:
            tiles[i] = IA.TILE_BASE + (x * 7 + y * 13) % 4
    wy = ry0 - 2                                  # top wall row
    bx = rx0 + 0.5
    objs = [_prop('boothWindow', bx, wy + 0.4, ground=True),
            _prop('onAir', bx + (124 - 38) / 64, wy + 0.06, ground=True),
            _prop('boothDoor', bx + 4.6, wy + 2 - 54 / 32, ground=True),
            _prop('wallPanels', rx1 - 3.2, wy + 0.45, ground=True),
            _prop('console', rx0 + 0.6, ry0 + 1, sortY=ry0 + 3),
            _prop('rack', rx0 + 7.05, ry0 + 1, sortY=ry0 + 3),
            _prop('chair', rx0 + 2.2, ry0 + 2.6, sortY=ry0 + 3.6),
            _prop('chair', rx0 + 4.6, ry0 + 2.6, sortY=ry0 + 3.6)]
    for y in (ry0 + 1, ry0 + 2):
        for x in range(rx0, rx0 + 8):
            solid[y * W + x] = 1
    m['objects'] = objs


def decorate(out_maps):
    IA.build(OUT / 'assets')
    for mid, m in out_maps.items():
        if mid.startswith('floor'):
            decorate_floor(m)
    decorate_lobby(out_maps['floor1'])
    decorate_studio(out_maps['room-1-9'])


def build():
    layout = SA.load_layout()
    plan = read(SRC / 'assets' / 'kiosk-plan.json')
    fp = read(SRC / 'assets' / 'school-footprint.json')
    art = read(SRC / 'assets' / 'explore-art.json')
    plans = SA.all_plans(layout)
    maps_src = {p.stem: read(p) for p in (SRC / 'data' / 'maps').glob('*.json')
                if p.stem in ('school', 'floor1', 'floor2', 'floor3', 'floor4') or p.stem.startswith('room-')}
    # ---------- places ----------
    places = []
    for f, fl in plan['floors'].items():
        f = int(f)
        floor_map = maps_src[f'floor{f}']
        door_tiles = {p['target']: [p['x'], p['y']] for p in floor_map['portals'] if p['target'].startswith('room-')}
        for r in fl['rooms']:
            if r['kind'] in ('gap',):
                continue
            place = {
                'id': r['id'], 'name': r['name'], 'label': r['label'], 'aliases': r.get('aliases', []),
                'name_en': r.get('name_en', ''), 'category': r['category'] if r['kind'] not in ('stair', 'ev') else r['kind'],
                'kind': r['kind'], 'floor': f, 'wing': r['wing'], 'side': r['side'], 'polygon': r['polygon'],
                'center': centroid(r['polygon']), 'door': r.get('door'), 'node': r.get('node'),
                'visible': r['visible'], 'game': r['game'] and r['kind'] in ('room', 'restroom') and r['confirmed'],
                'confirmed': r['confirmed'], 'description': r.get('description', ''),
            }
            if r['id'] in door_tiles:
                place['map'] = r['id']; place['tile'] = door_tiles[r['id']]
            elif r['kind'] in ('stair', 'ev', 'lobby'):
                place['map'] = f'floor{f}'
                place['tile'] = [plan['gameTiles']['marginTiles'] + int(math.floor(v)) for v in (r.get('door') or place['center'])]
            places.append(place)
    # neighbours: previous / next room in the same wing+side order
    for f in plans:
        rows = {}
        for p in places:
            if p['floor'] == f and p['kind'] in ('room', 'restroom', 'lobby', 'stair', 'ev') and p['wing'] in ('main', 'west'):
                rows.setdefault((p['wing'], p['side']), []).append(p)
        for (wing, side), lst in rows.items():
            axis = 0 if wing == 'main' else 1
            lst.sort(key=lambda p: p['center'][axis])
            for i, p in enumerate(lst):
                p['neighbors'] = [q['id'] for q in (lst[i - 1] if i else None, lst[i + 1] if i + 1 < len(lst) else None) if q]
    # nearest stair / EV along the corridor graph (same floor)
    for f, fl in plan['floors'].items():
        adj = {}
        for a, b, w in fl['edges']:
            adj.setdefault(a, []).append((b, w)); adj.setdefault(b, []).append((a, w))
        stairs = [r for r in fl['rooms'] if r['kind'] in ('stair', 'ev') and r.get('node')]
        for p in places:
            if p['floor'] != int(f) or not p.get('node') or p['kind'] in ('stair', 'ev'):
                continue
            dist = {p['node']: 0.0}; todo = [(0.0, p['node'])]
            while todo:
                todo.sort(); dcur, n = todo.pop(0)
                if dcur > dist.get(n, 1e9):
                    continue
                for m, w in adj.get(n, []):
                    if dcur + w < dist.get(m, 1e9):
                        dist[m] = dcur + w; todo.append((dcur + w, m))
            best = sorted((dist.get(s['node'], 1e9), s['id']) for s in stairs)
            p['nearest'] = [{'id': sid, 'm': round(dm, 1)} for dm, sid in best[:2] if dm < 1e9]
    for p in places:
        p['intro'] = intro(p)
    # outdoor places (교정)
    school = maps_src['school']
    spots = {i['label']: [i['x'], i['y']] for i in school['interactions']}
    gate = next(p for p in school['portals'] if p['target'] == 'town')
    spots['정문'] = [gate['x'], gate['y']]
    for o in layout.get('outdoor', []):
        tile = spots.get(o['name'])
        area = fp['site'].get(o['site'])
        poly = None
        if isinstance(area, list) and len(area) == 2 and isinstance(area[0], list):
            (x0, y0), (x1, y1) = area; poly = [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]
        p = {'id': o['id'], 'name': o['name'], 'label': o['name'], 'aliases': o.get('aliases', []), 'name_en': o.get('name_en', ''),
             'category': 'outdoor', 'kind': 'outdoor', 'floor': 0, 'wing': 'site', 'side': '', 'polygon': poly,
             'center': centroid(poly) if poly else None, 'visible': o.get('visible', True),
             'game': bool(tile) and o.get('game', True), 'confirmed': o.get('confirmed', True),
             'description': o.get('description', ''), 'map': 'school', 'tile': tile}
        p['intro'] = intro(p)
        places.append(p)
    # ---------- maps without the story ----------
    names = {p['id']: p for p in places}
    out_maps = {}
    for mid, m in sorted(maps_src.items()):
        n = {k: v for k, v in m.items() if k not in STORY_KEYS}
        n['objects'] = [o for o in m['objects'] if not (mid == 'school' and o.get('asset') == 15)]   # the diary book
        n['portals'] = []
        stairs = {}
        for pt in m['portals']:
            if pt['target'] == 'town':
                continue
            if mid.startswith('floor') and pt['target'].startswith('floor'):
                key = pt['label'].split(' · ')[0]
                s = stairs.setdefault(key, {'type': 'stairs', 'name': key, 'tiles': [], 'targets': {}})
                s['tiles'].append([pt['x'], pt['y']]); s['targets'][pt['target']] = pt['arrival']
                continue
            q = {'type': 'door', 'x': pt['x'], 'y': pt['y'], 'target': pt['target'], 'arrival': pt['arrival'], 'label': pt['label']}
            if pt['target'] in names:
                q['place'] = pt['target']
            n['portals'].append(q)
        for s in stairs.values():
            s['ev'] = s['name'] == '엘리베이터'
            s['targets'] = dict(sorted(s['targets'].items()))
            n['portals'].append(s)
        if mid.startswith('room-') and mid in names:
            n['place'] = mid
        n['people'] = []
        out_maps[mid] = n
    # guide people: a few per floor + grounds, each tells about the places nearby (generated text)
    M = plan['gameTiles']['marginTiles']
    for f in plans:
        m = out_maps[f'floor{f}']
        fl_places = [p for p in places if p['floor'] == f and p['kind'] in ('room', 'restroom') and p.get('tile')]
        for k, (x, y) in enumerate([(M + 9, M + 9), (M + 30, M + 8), (M + 80, M + 8), (M + 8, M + 36), (M + 8, M + 62)]):
            if y >= m['height'] - 1 or m['solid'][y * m['width'] + x]:
                continue
            near = sorted(fl_places, key=lambda p: math.hypot(p['tile'][0] - x, p['tile'][1] - y))[:2]
            if not near:
                continue
            a, b = near[0]['label'], near[1]['label'] if len(near) > 1 else None
            last = b or a
            text = f'여기서 가장 가까운 곳은 {a}' + (f', 그다음은 {b}' if b else '') + josa(last, '이야', '야') + '. 지도에서 직접 찾아봐!'
            m['people'].append({'x': x, 'y': y, 'variant': (f * 5 + k * 3) % 35, 'name': ['안내 학생', '선생님', '친구'][k % 3], 'text': text})
    sm = out_maps['school']
    for k, (lbl, txt) in enumerate([('운동장', '운동장은 두 동이 감싸고 있어. 서쪽 동은 꺾임 계단에서 남쪽으로 뻗어 있지.'),
                                    ('목련관', '목련관은 운동장 남동쪽 별동이야. 1층은 식생활관, 2층은 강당이야.'),
                                    ('조회대', '중앙현관으로 들어가면 바로 앞이 중앙계단이야. 층마다 장소가 달라!')]):
        if lbl in spots:
            x, y = spots[lbl]
            for dx, dy in ((-2, 0), (2, 0), (0, 2), (0, -2), (-3, 1)):
                xx, yy = x + dx, y + dy
                if not sm['solid'][yy * sm['width'] + xx]:
                    sm['people'].append({'x': xx, 'y': yy, 'variant': 10 + k * 7, 'name': ['체육부 학생', '급식 도우미', '안내 선생님'][k], 'text': txt}); break
    decorate(out_maps)
    # ---------- school (교정) placement for the full map ----------
    imgs = fp['images']
    so = imgs['school']['origin']
    obj = {o.get('image'): o for o in maps_src['school']['objects'] if o.get('image')}
    data = {
        'version': 1, 'generator': 'tools/build_explore_data.py',
        'source': 'data/school_layout.json + kiosk-plan.json + school-footprint.json',
        'categories': CATEGORIES,
        'floors': [{'floor': f, 'name': f'{f}층', 'map': f'floor{f}', 'plan': f'floor-plan-{f}.png', 'stack': f'stack-floor-{f}.png'} for f in plans],
        'places': places,
        'graph': {'floors': {f: {'nodes': fl['nodes'], 'edges': fl['edges']} for f, fl in plan['floors'].items()},
                  'vertical': plan['vertical'], 'kiosk': plan['kiosk']},
        'plan': {'pxPerM': plan['image']['pxPerM'], 'marginM': plan['image']['marginM'], 'marginTiles': M},
        'school': {
            'projection': fp['projection'], 'displayScale': fp['displayScale'],
            'images': [{'image': name, 'x': o['x'], 'y': o['y'], 'w': o['w'], 'h': o['h'],
                        'ground': bool(o.get('ground')), 'sort': o.get('sortY', o['y'] + o['h'] / 32)}
                       for name, o in sorted(obj.items(), key=lambda kv: (not kv[1].get('ground'), kv[1].get('sortY', kv[1]['y'] + kv[1]['h'] / 32)))],
            'origin': {'x': obj['school']['x'] + so[0] * fp['displayScale'] / 32, 'y': obj['school']['y'] + so[1] * fp['displayScale'] / 32},
            'entrance': [p for p in maps_src['school']['portals'] if p['target'] == 'floor1'][0],
        },
        'stack': art['stack'],
        'unconfirmed': [{'id': p['id'], 'floor': p['floor'], 'name': p['name']} for p in places if not p['confirmed']],
    }
    data['school']['entrance'] = {'x': data['school']['entrance']['x'], 'y': data['school']['entrance']['y']}
    pr, sc, so_t = fp['projection'], fp['displayScale'], data['school']['origin']

    def w2t(x, y, z=0):
        return [round(so_t['x'] + pr['s'] * (x - pr['kx'] * y) * sc / 32, 2), round(so_t['y'] + pr['s'] * (pr['ky'] * y - z) * sc / 32, 2)]
    g = fp['geometry']
    def hull(pts):
        pts = sorted(set(map(tuple, pts)))
        cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
        lo, up = [], []
        for p_ in pts:
            while len(lo) >= 2 and cross(lo[-2], lo[-1], p_) <= 0: lo.pop()
            lo.append(p_)
        for p_ in reversed(pts):
            while len(up) >= 2 and cross(up[-2], up[-1], p_) <= 0: up.pop()
            up.append(p_)
        return [list(p_) for p_ in lo[:-1] + up[:-1]]

    def box_outline(x0, x1, y0, y1, h):   # screen outline (tile coords) of a building box, walls + roof
        return hull([w2t(x, y, z) for x in (x0, x1) for y in (y0, y1) for z in (0, h)])
    # tap areas on the 교정 map: the wing opens its floor-1 plan (본관 / 서쪽 동 / 목련관 is a place)
    data['school']['areas'] = [
        {'name': '본관', 'floor': 1, 'wing': 'main', 'outline': box_outline(g['D'], g['L1'], 0, g['D'], g['H4'])},
        {'name': '서쪽 동', 'floor': 1, 'wing': 'west', 'outline': box_outline(0, g['D'], 0, g['D'] + g['L2'], g['H4'])},
    ]
    data['school']['labels'] = [
        {'text': '본관', 'tile': w2t(g['D'] + 44, g['D'] * 0.5, g['H4'] + 1)},
        {'text': '서쪽 동', 'tile': w2t(g['D'] * 0.5, g['D'] + 22, g['H4'] + 1)},
        {'text': '중앙현관', 'tile': w2t(g['XE'], g['D'] + 4, 4.6)},
    ]
    # ---------- write ----------
    write(OUT / 'data' / 'places.json', data)
    mdir = OUT / 'data' / 'maps'
    if mdir.exists():
        for p in mdir.glob('*.json'):
            if p.stem not in out_maps:
                p.unlink()
    for mid, m in out_maps.items():
        write(mdir / f'{mid}.json', m)
    adir = OUT / 'assets'; adir.mkdir(parents=True, exist_ok=True)
    sums = {}
    for name in ASSETS:
        src = SRC / 'assets' / name
        dst = adir / name
        if not dst.exists() or dst.read_bytes() != src.read_bytes():
            shutil.copyfile(src, dst)
        sums[name] = hashlib.sha256(src.read_bytes()).hexdigest()
    write(adir / 'assets.json', {'source': 'components/rpg_game/assets (copied by tools/build_explore_data.py)', 'sha256': sums})
    return data, out_maps


if __name__ == '__main__':
    d, m = build()
    game = [p for p in d['places'] if p['game']]
    print(f"places {len(d['places'])} (game {len(game)}), maps {len(m)}, assets {len(ASSETS)}")
