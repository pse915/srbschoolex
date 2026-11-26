"""서라벌 탐방 — 봄·여름·가을·겨울 그림 만들기.

The copied outdoor art (terrain, trees, school buildings, playground) is recoloured per season:
  spring  연둣빛 잔디·꽃잎, 벚꽃 만개
  summer  짙은 초록, 벚나무도 초록 잎
  autumn  누런 잔디·낙엽, 단풍 든 나무
  winter  눈 덮인 잔디·운동장·지붕, 눈 쌓인 나무
Writes components/explore/assets/<name>-<season>.png (terrain, trees, school, school-annex, school-ground,
school-gate-east, school-gate-north). Called from tools/build_explore_data.py; also runnable alone.
"""
from pathlib import Path

import numpy as np
from PIL import Image

SEASONS = ('spring', 'summer', 'autumn', 'winter')
SEASON_KO = {'spring': '봄', 'summer': '여름', 'autumn': '가을', 'winter': '겨울'}
GRASS, SAND, STONE = 0, 48, 49          # outdoor terrain tiles that change
T = 32
BUILDINGS = ('school', 'school-annex', 'school-gate-east', 'school-gate-north')


# ---------- colour helpers (vectorised HSV on float arrays) ----------
def to_hsv(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    mx, mn = rgb.max(-1), rgb.min(-1)
    d = mx - mn
    h = np.zeros_like(mx)
    m = d > 1e-6
    rc = np.where(m, (mx - r) / np.where(m, d, 1), 0)
    gc = np.where(m, (mx - g) / np.where(m, d, 1), 0)
    bc = np.where(m, (mx - b) / np.where(m, d, 1), 0)
    h = np.where(r == mx, bc - gc, np.where(g == mx, 2 + rc - bc, 4 + gc - rc))
    h = np.where(m, (h / 6) % 1, 0)
    s = np.where(mx > 1e-6, d / np.where(mx > 1e-6, mx, 1), 0)
    return h, s, mx


def from_hsv(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    out = np.zeros(h.shape + (3,))
    for k, (a, b, c) in enumerate([(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]):
        sel = i == k
        out[sel, 0], out[sel, 1], out[sel, 2] = a[sel], b[sel], c[sel]
    return out


def load(path):
    a = np.asarray(Image.open(path).convert('RGBA')).astype(float) / 255
    return a


def save(a, path):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(path, optimize=True)


def hexrgb(h):
    return np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])


def masks(a):
    """green foliage / pink blossom / bluish-gray roof masks of an RGBA array"""
    h, s, v = to_hsv(a[..., :3])
    op = a[..., 3] > 0.05
    green = op & (h > 0.13) & (h < 0.48) & (s > 0.16) & (v > 0.12)
    pink = op & ((h > 0.83) | (h < 0.03)) & (s > 0.12) & (v > 0.55)
    gray = op & (s < 0.13) & (v > 0.42) & (v < 0.86)
    blue = op & (h > 0.52) & (h < 0.7) & (s > 0.25) & (v > 0.35)
    return h, s, v, green, pink, gray, blue


def noise(shape, seed):
    return np.random.default_rng(seed).random(shape)


def foliage(a, sel, v, season, n, blossom=False):
    """recolour selected leaf pixels, keeping their light/shade"""
    if not sel.any():
        return
    vv = v[sel]
    if season == 'spring':
        if blossom:
            return                                               # cherry stays pink
        rgb = from_hsv(np.full(vv.shape, 0.24), np.full(vv.shape, 0.55), np.clip(vv * 1.12 + 0.06, 0, 1))
    elif season == 'summer':
        rgb = from_hsv(np.full(vv.shape, 0.33), np.full(vv.shape, 0.68), np.clip(vv * 0.86, 0, 1))
    elif season == 'autumn':
        hue = np.where(n[sel] < 0.42, 0.02, np.where(n[sel] < 0.78, 0.07, 0.12))   # red / orange / yellow
        if blossom:
            hue = np.where(n[sel] < 0.6, 0.015, 0.05)
        rgb = from_hsv(hue, np.full(vv.shape, 0.78), np.clip(vv * 1.05 + 0.04, 0, 1))
    else:                                                       # winter: snow on the branches
        snow = np.clip(0.78 + vv * 0.26, 0, 1)
        rgb = np.stack([snow * 0.94, snow * 0.97, snow], -1)
        dark = vv < 0.33                                         # deep shade -> bare branch showing through
        rgb[dark] = np.array([0.42, 0.36, 0.33]) * (0.7 + vv[dark, None])
    a[sel, :3] = rgb


# ---------- terrain ----------
def dots(tile, rng, colors, count, size=(1, 2)):
    for _ in range(count):
        x, y = rng.integers(1, T - 2, 2)
        c = colors[rng.integers(len(colors))]
        w = rng.integers(size[0], size[1] + 1)
        tile[y:y + w, x:x + w, :3] = c
        if w == 1 and rng.random() < 0.6:                       # a petal / leaf of two pixels
            tile[y, min(T - 1, x + 1), :3] = c


def season_terrain(src, season):
    a = src.copy()
    rng = np.random.default_rng(7 + SEASONS.index(season))
    g = a[:, GRASS * T:(GRASS + 1) * T]
    sd = a[:, SAND * T:(SAND + 1) * T]
    st = a[:, STONE * T:(STONE + 1) * T]
    h, s, v = to_hsv(g[..., :3])
    if season == 'spring':
        g[..., :3] = from_hsv(np.full(h.shape, 0.25), s * 0.95, np.clip(v * 1.1, 0, 1))
        dots(g, rng, [hexrgb('#f6c6d6'), hexrgb('#fff6a8'), hexrgb('#ffffff')], 9)
        dots(sd, rng, [hexrgb('#f3b8cb'), hexrgb('#fbd5e1')], 5)
    elif season == 'summer':
        g[..., :3] = from_hsv(np.full(h.shape, 0.31), np.clip(s * 1.25, 0, 1), v * 0.88)
        dots(g, rng, [hexrgb('#4f7f3c'), hexrgb('#3f6d32')], 8)
    elif season == 'autumn':
        g[..., :3] = from_hsv(np.full(h.shape, 0.15), s * 1.05, np.clip(v * 1.04, 0, 1))
        leaves = [hexrgb('#c8502c'), hexrgb('#e08a2c'), hexrgb('#e6b83a'), hexrgb('#9b3f24')]
        dots(g, rng, leaves, 7)
        dots(sd, rng, leaves, 5)
        dots(st, rng, leaves, 3)
    else:
        n = noise(h.shape, 11)
        snow = 0.93 + (v - v.mean()) * 0.35 + n * 0.03
        g[..., :3] = np.stack([snow * 0.93, snow * 0.96, snow], -1)
        tuft = n > 0.988                                         # a few blades poking through
        g[tuft, :3] = hexrgb('#8fa486')
        for t, k in ((sd, 0.72), (st, 0.55)):
            nn = noise(t.shape[:2], 13 + int(k * 10))
            amt = (k + (nn - 0.5) * 0.16)[..., None]
            t[..., :3] = t[..., :3] * (1 - amt) + np.array([0.95, 0.97, 1.0]) * amt
    return a


# ---------- trees (environment cells 0 and 1) ----------
def season_trees(env, season):
    cw, ch = env.shape[1] // 4, env.shape[0] // 4
    out = np.zeros((ch, cw * 2, 4))
    for i in range(2):
        cell = env[0:ch, i * cw:(i + 1) * cw].copy()
        h, s, v, green, pink, gray, blue = masks(cell)
        if i == 1:                                               # pale petal highlights belong to the blossom too
            pink = pink | ((cell[..., 3] > 0.05) & (s < 0.32) & (v > 0.78))
        n = noise(h.shape, 21 + i)
        foliage(cell, green, v, season, n)
        if pink.any():                                           # blossom shade from its own light range
            lum = cell[..., :3].mean(-1)
            lo, hi = np.percentile(lum[pink], 3), np.percentile(lum[pink], 97)
            sv = np.clip(0.3 + (lum - lo) / max(hi - lo, 1e-3) * 0.62, 0, 1)
            if season == 'summer':                               # cherry: green leaves after the blossoms
                foliage(cell, pink, sv, season, n)
            elif season != 'spring':
                foliage(cell, pink, sv, season, n, blossom=True)
        out[:, i * cw:(i + 1) * cw] = cell
    return out


# ---------- buildings and playground ----------
def season_building(a, season, seed):
    a = a.copy()
    h, s, v, green, pink, gray, blue = masks(a)
    n = noise(h.shape, seed)
    foliage(a, green, v, season, n)
    if season == 'winter':
        # snow on the flat roofs, steps and the annex dome (only on top-facing light pixels)
        roof = gray & (v > 0.5)
        a[roof, :3] = a[roof, :3] * 0.25 + np.array([0.96, 0.97, 1.0]) * 0.75
        dome = blue & (v > 0.55)
        a[dome, :3] = a[dome, :3] * 0.45 + np.array([0.95, 0.97, 1.0]) * 0.55
    return a


def season_ground(a, season):
    a = a.copy()
    h, s, v, green, pink, gray, blue = masks(a)
    op = a[..., 3] > 0.05
    rng = np.random.default_rng(31 + SEASONS.index(season))
    n = noise(h.shape, 41)
    if season == 'winter':
        sand = op & ~(v > 0.93)                                  # keep the white track lines visible
        amt = np.where(n > 0.25, 0.82, 0.55)
        a[sand, :3] = a[sand, :3] * (1 - amt[sand, None]) + np.array([0.95, 0.97, 1.0]) * amt[sand, None]
        a[op & (v > 0.93), :3] = np.array([0.72, 0.8, 0.9])     # track lines -> faint blue under snow
    elif season in ('spring', 'autumn'):
        cols = [hexrgb('#f3b8cb'), hexrgb('#fbd5e1')] if season == 'spring' else \
               [hexrgb('#c8502c'), hexrgb('#e08a2c'), hexrgb('#e6b83a')]
        ys, xs = np.nonzero(op)
        pick = rng.choice(len(xs), size=len(xs) // (260 if season == 'spring' else 200), replace=False)
        for j in pick:
            y, x = ys[j], xs[j]
            c = cols[rng.integers(len(cols))]
            a[y, x, :3] = c
            if x + 1 < a.shape[1] and op[y, x + 1]:
                a[y, x + 1, :3] = c
    elif season == 'summer':
        a[op, :3] = np.clip(a[op, :3] * np.array([1.02, 1.0, 0.95]), 0, 1)   # warmer sunlit sand
    return a


def build(assets):
    assets = Path(assets)
    terr = load(assets / 'terrain.png')
    env = load(assets / 'environment.png')
    blds = {b: load(assets / f'{b}.png') for b in BUILDINGS}
    ground = load(assets / 'school-ground.png')
    written = []
    for season in SEASONS:
        save(season_terrain(terr, season), assets / f'terrain-{season}.png')
        save(season_trees(env, season), assets / f'trees-{season}.png')
        for k, (b, a) in enumerate(blds.items()):
            save(season_building(a, season, 51 + k), assets / f'{b}-{season}.png')
        save(season_ground(ground, season), assets / f'school-ground-{season}.png')
        written += [f'{n}-{season}.png' for n in ('terrain', 'trees', 'school-ground') + BUILDINGS]
    return written


if __name__ == '__main__':
    import sys
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'components' / 'explore' / 'assets'
    print(len(build(out)), 'season images ->', out)
