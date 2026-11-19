"""Map connectivity check (split out of finish_art.py so it has no side effects).
  python tools/check_maps.py            -> prints a summary, writes docs/evidence/v6-connectivity.json, exit 1 on errors

Checks
 - every map: portals / NPCs / interactions are next to a tile reachable from the spawn
 - every portal: target exists, arrival is inside the target and not solid
 - school: from the 중앙현관 (floor1 lobby) every room, stair, elevator and restroom of floors 1~4 is reachable on foot + portals
 - data points (discoveries.js, activities.json, landmarks) are walkable
"""
import collections, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'components' / 'rpg_game'
DATA = GAME / 'data'
sys.path.insert(0, str(ROOT / 'tools'))
import school_art as SA  # noqa: E402

N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def load_maps():
    return {p.stem: json.loads(p.read_text(encoding='utf-8')) for p in (DATA / 'maps').glob('*.json')}


def flood(m, start):
    w, h = m['width'], m['height']
    sx, sy = int(start[0]), int(start[1])
    seen = {(sx, sy)}; q = collections.deque(seen)
    while q:
        x, y = q.popleft()
        for dx, dy in N4:
            xx, yy = x + dx, y + dy
            # game.js pass(): the 1-tile border is never walkable
            if 1 <= xx < w - 1 and 1 <= yy < h - 1 and (xx, yy) not in seen and not m['solid'][yy * w + xx]:
                seen.add((xx, yy)); q.append((xx, yy))
    return seen


def near(seen, x, y):
    return any((int(x) + dx, int(y) + dy) in seen for dx, dy in ((0, 0),) + N4)


def walkable(m, x, y):
    x, y = int(x), int(y)
    return 0 <= x < m['width'] and 0 <= y < m['height'] and not m['solid'][y * m['width'] + x]


def check(maps):
    errors = []
    reach = {}
    for name, m in maps.items():
        seen = flood(m, m['spawn'])
        reach[name] = seen
        for p in m['portals'] + m['interactions'] + m['npcs']:
            if not near(seen, p['x'], p['y']):
                errors.append([name, p.get('label', p.get('name')), 'unreachable from spawn'])
        for p in m['portals']:
            dest = maps.get(p['target']); pos = p.get('arrival')
            if not dest:
                errors.append([name, p['target'], 'missing target']); continue
            if not pos or not (0 <= pos[0] < dest['width'] and 0 <= pos[1] < dest['height']):
                errors.append([name, p['target'], 'invalid arrival']); continue
            if dest['solid'][pos[1] * dest['width'] + pos[0]]:
                errors.append([name, p['target'], f'solid arrival {pos}'])
    # map graph from the school entrance: walk + portals (arrivals are new flood starts)
    start = ('floor1', tuple(maps['floor1']['spawn']))
    visited_maps, q, done = set(), collections.deque([start]), set()
    while q:
        mid, pos = q.popleft()
        if (mid, pos) in done:
            continue
        done.add((mid, pos)); visited_maps.add(mid)
        m = maps[mid]; seen = flood(m, pos)
        for p in m['portals']:
            if near(seen, p['x'], p['y']) and p['target'] in maps and p.get('arrival'):
                q.append((p['target'], tuple(p['arrival'])))
    layout = SA.load_layout()
    need = []
    for f, plan in SA.all_plans(layout).items():
        for e in plan['items']:
            if e['kind'] in ('room', 'restroom'):
                need.append(e['id'])
        need.append(f'floor{f}')
    for rid in need:
        if rid not in visited_maps:
            errors.append(['school', rid, 'not reachable from 중앙현관'])
    # every stair / elevator portal on every floor is reachable from that floor's spawn
    stair_count = 0
    for f in range(1, 5):
        m = maps[f'floor{f}']
        for p in m['portals']:
            if p['target'].startswith('floor'):
                stair_count += 1
                if not near(reach[f'floor{f}'], p['x'], p['y']):
                    errors.append([f'floor{f}', p['label'], 'stair/EV portal unreachable'])
    # data points
    disc = (GAME / 'discoveries.js').read_text(encoding='utf-8')
    for mid, x, y in re.findall(r"map:'([\w-]+)'[^}]*?point:\[(\d+),(\d+)\]", disc):
        if mid in maps and not near(reach[mid], int(x), int(y)):
            errors.append([mid, f'discovery point {x},{y}', 'not walkable'])
    acts = json.loads((DATA / 'activities.json').read_text(encoding='utf-8'))
    for a in acts.get('activities', []):
        if a.get('point') and a.get('map') in maps and not near(reach[a['map']], *a['point']):
            errors.append([a['map'], f"activity {a.get('id')}", 'not walkable'])
    lm = maps['school'].get('landmarks', {})
    for k in ('students', 'repair', 'care', 'garden', 'access'):
        if k in lm and not walkable(maps['school'], *lm[k]):
            errors.append(['school', f'landmark {k} {lm[k]}', 'on a solid tile'])
    summary = {'maps': len(maps), 'reachableFromLobby': len(visited_maps), 'schoolRoomsChecked': len(need),
               'stairEvPortals': stair_count,
               'checks': 'spawn reachability; portal/NPC/interaction adjacency; portal target+arrival; '
                         'lobby -> all rooms/stairs/EV/restrooms; discovery/activity/landmark points',
               'errors': errors}
    return summary


if __name__ == '__main__':
    s = check(load_maps())
    out = ROOT / 'docs' / 'evidence' / 'v6-connectivity.json'
    out.write_text(json.dumps(s, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in s.items() if k != 'errors'}, ensure_ascii=False))
    for e in s['errors']:
        print('ERROR', e)
    sys.exit(1 if s['errors'] else 0)
