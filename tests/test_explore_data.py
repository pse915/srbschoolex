"""New exploration game (components/explore): data comes only from the school sources, with no life-design story."""
import collections, hashlib, json, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / 'components' / 'explore'
sys.path.insert(0, str(ROOT / 'tools'))
import build_explore_data as B  # noqa: E402
import school_art as SA  # noqa: E402


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


def snapshot():
    files = sorted((EX / 'data').rglob('*.json')) + [EX / 'assets' / 'assets.json']
    return {str(p.relative_to(EX)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}


class ExploreDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = snapshot()
        B.build()
        cls.after = snapshot()
        cls.data = read(EX / 'data' / 'places.json')
        cls.maps = {p.stem: read(p) for p in (EX / 'data' / 'maps').glob('*.json')}

    def test_build_is_deterministic_and_committed_output_is_current(self):
        B.build()
        self.assertEqual(snapshot(), self.after)
        self.assertEqual(self.before, self.after, 'components/explore is stale; run python tools/build_explore_data.py')

    def test_places_match_school_layout(self):
        layout_rooms = {e['id'] for f, p in SA.all_plans(SA.load_layout()).items() for e in p['items']
                        if e['kind'] in ('room', 'restroom') and e.get('game', True) and e.get('confirmed', True)}
        game_rooms = {p['id'] for p in self.data['places'] if p['game'] and p['floor'] >= 1}
        self.assertEqual(game_rooms, layout_rooms)
        door_targets = {pt['target'] for m in self.maps.values() if m['id'].startswith('floor') for pt in m['portals']
                        if pt['type'] == 'door' and pt['target'].startswith('room-')}
        all_rooms = {p['id'] for p in self.data['places'] if p['kind'] in ('room', 'restroom')}
        self.assertEqual(door_targets, all_rooms)
        outdoor = {p['name'] for p in self.data['places'] if p['floor'] == 0}
        self.assertEqual(outdoor, {'운동장', '조회대', '목련관', '급수대', '정문', '후문'})

    def test_no_life_design_story_in_the_new_game(self):
        banned_keys = set(B.STORY_KEYS) | {'quest', 'story', 'diary', 'clue'}
        old_lines = set()
        for p in (ROOT / 'components' / 'rpg_game' / 'data' / 'maps').glob('*.json'):
            m = read(p)
            for x in m.get('npcs', []) + m.get('interactions', []):
                if x.get('text'): old_lines.add(x['text'])
        blob = (EX / 'data' / 'places.json').read_text(encoding='utf-8')
        for mid, m in self.maps.items():
            self.assertFalse(banned_keys & set(m), mid)
            self.assertNotIn('town', json.dumps(m['portals']), mid)
            blob += json.dumps(m, ensure_ascii=False)
        for line in old_lines:
            self.assertNotIn(line, blob)
        for word in ('미래 다이어리', '미래마을', '생애', '퀴즈', '노후'):
            self.assertNotIn(word, blob, word)
        js = ''.join(p.read_text(encoding='utf-8') for p in (EX / 'js').glob('*.js'))
        for word in ('story_v4', 'quests.json', 'quiz_v5', 'futureLayers', 'drawGuidance', 'routeTarget'):
            self.assertNotIn(word, js, word)

    def test_every_game_place_is_reachable_from_the_entrance(self):
        def flood(m, start):
            w, h = m['width'], m['height']
            seen = {tuple(start)}; q = collections.deque(seen)
            while q:
                x, y = q.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    a, b = x + dx, y + dy
                    if 1 <= a < w - 1 and 1 <= b < h - 1 and (a, b) not in seen and not m['solid'][b * w + a]:
                        seen.add((a, b)); q.append((a, b))
            return seen
        near = lambda seen, x, y: any((x + dx, y + dy) in seen for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)))
        e = self.data['school']['entrance']
        todo, done, maps_seen, outdoor_ok = collections.deque([('school', (e['x'], e['y'] + 2))]), set(), set(), set()
        while todo:
            mid, pos = todo.popleft()
            if (mid, pos) in done:
                continue
            done.add((mid, pos)); maps_seen.add(mid)
            m = self.maps[mid]; seen = flood(m, pos)
            for pt in m['portals']:
                if pt['type'] == 'door' and near(seen, pt['x'], pt['y']):
                    todo.append((pt['target'], tuple(pt['arrival'])))
                if pt['type'] == 'stairs' and any(near(seen, *t) for t in pt['tiles']):
                    for target, arr in pt['targets'].items():
                        todo.append((target, tuple(arr)))
            if mid == 'school':
                for p in self.data['places']:
                    if p['floor'] == 0 and p.get('tile') and near(seen, *p['tile']):
                        outdoor_ok.add(p['id'])
        for p in self.data['places']:
            if not p['game']:
                continue
            if p['floor'] == 0:
                self.assertIn(p['id'], outdoor_ok, p['name'])
            else:
                self.assertIn(p['id'], maps_seen, p['name'])

    def test_asset_copies_match_the_originals(self):
        sums = read(EX / 'assets' / 'assets.json')['sha256']
        self.assertEqual(sorted(sums), sorted(B.ASSETS))
        for name, digest in sums.items():
            src = ROOT / 'components' / 'rpg_game' / 'assets' / name
            self.assertEqual(hashlib.sha256((EX / 'assets' / name).read_bytes()).hexdigest(), digest, name)
            self.assertEqual(hashlib.sha256(src.read_bytes()).hexdigest(), digest, name)

    def test_unconfirmed_area_is_marked_not_invented(self):
        un = {p['id'] for p in self.data['places'] if not p['confirmed']}
        self.assertEqual(un, {'void-4-west'})
        self.assertFalse(next(p for p in self.data['places'] if p['id'] == 'void-4-west')['game'])


if __name__ == '__main__':
    unittest.main()
