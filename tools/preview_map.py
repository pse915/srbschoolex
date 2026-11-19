"""Render a game map JSON to a PNG (tiles + objects, same draw order as game.js) for review.
  python tools/preview_map.py school out.png [--scale 0.25] [--box x y w h] [--solid]
"""
import argparse, json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1] / 'components' / 'rpg_game'
A = ROOT / 'assets'


def atlas_cell(index, atl):
    if index >= 65: im, j = atl['details'], index - 65
    elif index >= 49: im, j = atl['facilities'], index - 49
    elif index >= 33: im, j = atl['furniture'], index - 33
    elif index >= 16: im, j = atl['buildings'], index - 16
    else: im, j = atl['environment'], index
    cw, ch = im.width // 4, im.height // 4
    return im.crop(((j % 4) * cw, (j // 4) * ch, (j % 4 + 1) * cw, (j // 4 + 1) * ch))


def render(map_id, box=None, show_solid=False):
    m = json.loads((ROOT / 'data' / 'maps' / f'{map_id}.json').read_text(encoding='utf-8'))
    terrain = Image.open(A / 'terrain.png').convert('RGBA')
    atl = {n: Image.open(A / f'{n}.png').convert('RGBA') for n in ('environment', 'buildings', 'furniture', 'facilities', 'details')}
    x0, y0, w, h = box or (0, 0, m['width'], m['height'])
    cv = Image.new('RGBA', (w * 32, h * 32), (38, 59, 60, 255))
    for ty in range(y0, min(m['height'], y0 + h)):
        for tx in range(x0, min(m['width'], x0 + w)):
            t = m['tiles'][ty * m['width'] + tx]
            cv.alpha_composite(terrain.crop((t * 32, 0, t * 32 + 32, 32)), ((tx - x0) * 32, (ty - y0) * 32))
    objs = []
    for o in m['objects']:
        sort = -1e9 if o.get('ground') else (o['sortY'] * 32 if o.get('sortY') is not None else o['y'] * 32 + o['h'] - 8)
        objs.append((sort, o))
    for _, o in sorted(objs, key=lambda t: t[0]):
        im = Image.open(A / f"{o['image']}.png").convert('RGBA') if o.get('image') else atlas_cell(o['asset'], atl)
        im = im.resize((int(o['w']), int(o['h'])), Image.NEAREST)
        cv.alpha_composite(im, (int(round((o['x'] - x0) * 32)), int(round((o['y'] - y0) * 32)))) if (o['x'] - x0) * 32 > -im.width else None
    d = ImageDraw.Draw(cv)
    if show_solid:
        for ty in range(y0, min(m['height'], y0 + h)):
            for tx in range(x0, min(m['width'], x0 + w)):
                if m['solid'][ty * m['width'] + tx]:
                    d.rectangle(((tx - x0) * 32 + 12, (ty - y0) * 32 + 12, (tx - x0) * 32 + 19, (ty - y0) * 32 + 19), fill=(220, 40, 40, 200))
    for p in m['portals']:
        d.rectangle(((p['x'] - x0) * 32 + 4, (p['y'] - y0) * 32 + 4, (p['x'] - x0) * 32 + 27, (p['y'] - y0) * 32 + 27), outline=(255, 230, 80, 255), width=3)
    for n in m.get('npcs', []) + m.get('interactions', []):
        d.ellipse(((n['x'] - x0) * 32 + 8, (n['y'] - y0) * 32 + 8, (n['x'] - x0) * 32 + 23, (n['y'] - y0) * 32 + 23), outline=(80, 200, 255, 255), width=3)
    sx, sy = m['spawn']
    d.ellipse(((sx - x0) * 32 + 6, (sy - y0) * 32 + 6, (sx - x0) * 32 + 25, (sy - y0) * 32 + 25), fill=(255, 255, 255, 255))
    return cv


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('map'); ap.add_argument('out')
    ap.add_argument('--scale', type=float, default=0.25)
    ap.add_argument('--box', type=int, nargs=4)
    ap.add_argument('--solid', action='store_true')
    a = ap.parse_args()
    im = render(a.map, a.box, a.solid)
    if a.scale != 1:
        im = im.resize((max(1, int(im.width * a.scale)), max(1, int(im.height * a.scale))), Image.NEAREST)
    im.save(a.out)
    print(a.out, im.size)
