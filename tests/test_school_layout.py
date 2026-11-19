"""v6: data/school_layout.json is the single source of the school's rooms.
The floor maps, kiosk-plan.json and the school_art outputs must agree with it."""
import collections, hashlib, json, sys, tempfile, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'components' / 'rpg_game'
ASSETS = GAME / 'assets'
sys.path.insert(0, str(ROOT / 'tools'))
import school_art as SA  # noqa: E402


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


LAYOUT = SA.load_layout()
PLANS = SA.all_plans(LAYOUT)
KIOSK = read(ASSETS / 'kiosk-plan.json')


def layout_rooms(f):
    return {e['id']: e for e in PLANS[f]['items'] if e['kind'] in ('room', 'restroom')}


class SchoolLayoutTest(unittest.TestCase):
    def test_ids_are_unique_and_room_maps_exist(self):
        seen = set()
        for f in PLANS:
            for rid in layout_rooms(f):
                self.assertNotIn(rid, seen, rid)
                seen.add(rid)
                self.assertTrue(rid.startswith(f'room-{f}-'), rid)
                self.assertTrue((GAME / 'data' / 'maps' / f'{rid}.json').exists(), rid)

    def test_floor_maps_match_layout(self):
        for f in PLANS:
            m = read(GAME / 'data' / 'maps' / f'floor{f}.json')
            doors = {p['target']: p['label'] for p in m['portals'] if p['target'].startswith('room-')}
            rooms = layout_rooms(f)
            self.assertEqual(set(doors), set(rooms), f'floor{f}')
            for rid, e in rooms.items():
                self.assertEqual(doors[rid], SA.room_label(e))

    def test_kiosk_plan_matches_layout(self):
        for f in PLANS:
            k = {r['id']: r for r in KIOSK['floors'][str(f)]['rooms'] if r['kind'] in ('room', 'restroom')}
            self.assertEqual(set(k), set(layout_rooms(f)), f'kiosk floor {f}')
            for rid, e in layout_rooms(f).items():
                self.assertEqual(k[rid]['name'], e['name'])

    def test_catalog_names_match_labels(self):
        cat = {c['id']: c['name'] for c in read(GAME / 'data' / 'catalog.json')}
        for f in PLANS:
            for rid, e in layout_rooms(f).items():
                self.assertEqual(cat[rid], SA.room_label(e))
        self.assertNotIn('room-1-0', cat)   # retired: the 중앙현관 is the floor-1 lobby now

    def test_layout_follows_the_reference_table(self):
        names = lambda f, wing: [i.get('name') for i in next(x for x in LAYOUT['floors'] if x['floor'] == f)[wing]['inner'] if 'name' in i]
        self.assertEqual(names(1, 'west'), ['행정자료실', '학습지원실1', '보건실', '여교사휴게실', '자료실', '학생자치공간', '체육교과연구실'])
        self.assertEqual(names(2, 'main')[:4], ['1-2', '1-1', '1학년 교무실', '교무센터'])
        self.assertEqual(names(4, 'main')[-2:], ['글빛소회의실', '글빛도서관'])
        void = [e for e in PLANS[4]['items'] if e['kind'] == 'void']
        self.assertEqual(len(void), 1)
        self.assertFalse(void[0]['confirmed'])

    def test_stairs_and_elevator_share_coordinates_on_every_floor(self):
        pos = collections.defaultdict(set)
        for f, plan in PLANS.items():
            for e in plan['items']:
                if e['kind'] in ('stair', 'ev'):
                    pos[e['id']].add(tuple(e['rect']))
        self.assertIn('ev-ev', pos)
        self.assertIn('stair-centralStair', pos)
        for sid, rects in pos.items():
            self.assertEqual(len(rects), 1, sid)
        lobby = next(e for e in PLANS[1]['items'] if e['kind'] == 'lobby')
        central = next(e for e in PLANS[1]['items'] if e['id'] == 'stair-centralStair')
        self.assertAlmostEqual((lobby['rect'][0] + lobby['rect'][2]) / 2, (central['rect'][0] + central['rect'][2]) / 2)   # 중앙계단 바로 북쪽
        ev = next(e for e in PLANS[1]['items'] if e['id'] == 'ev-ev')
        self.assertLess(ev['rect'][2], central['rect'][0])    # EV 는 중앙계단보다 서쪽

    def test_kiosk_graph_reaches_every_room_from_the_signage(self):
        adj = collections.defaultdict(set)
        for fl in KIOSK['floors'].values():
            for a, b, _ in fl['edges']:
                adj[a].add(b); adj[b].add(a)
        for v in KIOSK['vertical']:
            adj[v['a']].add(v['b']); adj[v['b']].add(v['a'])
        start = KIOSK['kiosk']['node']
        seen, q = {start}, collections.deque([start])
        while q:
            for n in adj[q.popleft()]:
                if n not in seen:
                    seen.add(n); q.append(n)
        for f, fl in KIOSK['floors'].items():
            for r in fl['rooms']:
                if 'node' in r:
                    self.assertIn(r['node'], seen, r['id'])

    def test_art_is_deterministic_and_committed_outputs_are_current(self):
        files = ['school.png', 'school-ruin.png', 'school-footprint.json', 'kiosk-plan.json',
                 'floor-plan-1.png', 'floor-plan-4.png', 'school-annex.png', 'school-ground.png']
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            for out in (a, b):
                SA.main(['--out', out, '--only', 'sprite'])
                SA.main(['--out', out, '--only', 'ruin'])
                SA.main(['--out', out, '--only', 'props'])
                SA.main(['--out', out, '--only', 'plans'])
            for f in files:
                ha = hashlib.sha256((Path(a) / f).read_bytes()).hexdigest()
                hb = hashlib.sha256((Path(b) / f).read_bytes()).hexdigest()
                hc = hashlib.sha256((ASSETS / f).read_bytes()).hexdigest()
                self.assertEqual(ha, hb, f'{f} not deterministic')
                self.assertEqual(ha, hc, f'{f} differs from the committed asset; run tools/school_art.py --only all')

    def test_sprite_is_the_code_pixel_art_reference(self):
        from PIL import Image, ImageChops
        a = Image.open(ASSETS / 'school.png').convert('RGBA')
        b = Image.open(ROOT / 'docs' / 'kiosk' / 'art-v1' / 'school-sprite-1x.png').convert('RGBA')
        self.assertEqual(a.size, b.size)
        self.assertIsNone(ImageChops.difference(a, b).getbbox())


if __name__ == '__main__':
    unittest.main()
