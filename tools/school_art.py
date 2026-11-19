"""Procedural pixel-art renderer for 서라벌여중 (┌-shaped building).
World coords (meters): x = east, y = south, z = up.
Main wing: x in [0, L1], y in [0, D]. West wing: x in [0, D], y in [D, D+L2] (comes south, toward the field).

This script is the single source of the school's look (see docs/kiosk/00_서라벌여중_배치_기준표.md 4장).
  python tools/school_art.py --out components/rpg_game/assets [--only sprite|ruin|hero|props|plans|all]
Outputs are deterministic (fixed seeds, no timestamps): the same input always gives identical files.
"""
import argparse, hashlib, json, math, random, sys
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
LAYOUT_PATH = ROOT / 'data' / 'school_layout.json'

# ---------------- geometry ----------------
D = 18.0            # wing depth
L1 = 104.0          # main wing length (corner -> east end)
L2 = 56.0           # west wing length beyond corner
FH = 3.6            # floor height
H4 = 4 * FH + 0.7   # 4-storey wall height incl. parapet
H3 = 3 * FH + 0.5   # arch section wall height
VAULT = 4.2         # barrel vault rise
STAIR_Y0, STAIR_Y1 = D + 25.0, D + 30.0   # mid stair recess in west wing
ARCH_Y0 = STAIR_Y1                          # arch section start
XE = D + 38.0       # central entrance x (on main wing south face)
MSTAIR = (52.0, 57.0)   # main-wing mid stair (계단·출입구), meters east of the corner (x - D)
ESTAIR_W = 5.5          # main-wing east-end stair width
# floor bands (plans / floor maps): outer support rooms | corridor | inner rooms (rest of D, toward the field)
OUTER_W, CORR_W = 7.0, 3.0
EV_X = (D + 8.0, D + 12.0)          # elevator, west of the central stair near the corner
CORNER_STAIR = (OUTER_W + CORR_W, D, OUTER_W + CORR_W, D)   # x0, x1, y0, y1 (inner corner, under the stair tower)

# ---------------- site (outside the building, meters, same axes) ----------------
FIELD = (D + 3.0, L1 - 2.0, D + 3.0, D + L2 + 30.0)          # sand playground x0, x1, y0, y1
TRACK_C = ((FIELD[0] + FIELD[1]) / 2, (FIELD[2] + FIELD[3]) / 2)
TRACK_HALF, TRACK_R = 18.5, 18.0                             # straight half-length, bend radius
FOUNTAIN = (D + 6.0, D + 10.0, D + 5.0, D + 6.2, 1.0)        # 급수대 x0, x1, y0, y1, height (NW of the field)
ANNEX = (L1 + 28.0, L1 + 58.0, D + L2 - 4.0, D + L2 + 18.0)  # 목련관 (south-east detached hall)
ANNEX_H = 2 * FH + 0.7
GATE_E = (L1 + 70.0, D + 4.0, D + 12.0)                      # 정문: x, y0, y1 (opening along y)
GATE_N = (XE + 10.0, XE + 18.0, -100.0)                      # 후문: x0, x1, y

# ---------------- palette ----------------
BRICK = (150, 72, 58)
BRICK_L = (166, 84, 66)
BRICK_D = (124, 58, 48)
MORTAR = (136, 66, 54)
FRAME = (240, 240, 234)
GLASS = (176, 196, 204)
GLASS_D = (128, 150, 162)
GLASS_HI = (214, 228, 232)
COPING = (214, 206, 194)
PLINTH = (150, 146, 140)
CANOPY = (70, 74, 80)
CANOPY_L = (98, 102, 108)
GRANITE = (176, 176, 172)
GRANITE_D = (142, 142, 140)
STEEL = (210, 214, 218)
ROOF = (150, 154, 156)
ROOF_D = (128, 132, 134)
VAULT_C = (86, 140, 196)
VAULT_L = (130, 176, 222)
VAULT_D = (60, 104, 156)
PINE = [(44, 84, 52), (58, 104, 62), (76, 124, 72), (34, 66, 44)]
HEDGE = [(62, 112, 64), (80, 132, 74), (48, 92, 54)]
TRUNK = (98, 70, 52)
# ruin
CRACK = (58, 36, 32)
SHARD = (30, 32, 36)
STAIN = (112, 114, 108)
# ground
SAND = (206, 196, 176)
SAND_L = (222, 212, 192)
SAND_D = (190, 180, 160)
LINE = (246, 244, 238)
PAVE = (184, 180, 172)
PAVE_D = (160, 156, 150)
# floor plans (top view)
PLAN_FLOOR = (238, 232, 218)
PLAN_CLASS = (238, 214, 178)
PLAN_OFFICE = (192, 210, 230)
PLAN_SPECIAL = (204, 224, 186)
PLAN_CARE = (240, 206, 200)
PLAN_SERVICE = (206, 202, 196)
PLAN_LOBBY = (218, 216, 210)


def shade(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c)


# ---------------- facade textures ----------------
def facade(length, height, ppm, floors, bay=4.5, offset=0.0, zones=(), plinth=True, k=1.0, seed=0):
    """Return RGBA texture for a wall. zones: list of (x0, x1, kind) in meters along the wall.
    kinds: 'recess' (stair core, darker, small windows), 'entrance' (glass doors at 1F), 'blank'."""
    rnd = random.Random(seed)
    W, Hp = max(1, round(length * ppm)), max(1, round(height * ppm))
    im = Image.new('RGBA', (W, Hp), BRICK + (255,))
    px = im.load()
    for yy in range(Hp):
        for xx in range(W):
            r = rnd.random()
            if r < 0.10: px[xx, yy] = BRICK_L + (255,)
            elif r < 0.20: px[xx, yy] = MORTAR + (255,)
    d = ImageDraw.Draw(im)
    P = lambda m: int(round(m * ppm))
    zt = lambda z: Hp - P(z)  # z(m) -> y pixel

    def zone_at(xm):
        for a, b, kind in zones:
            if a <= xm < b: return kind
        return None

    # pilasters + windows per bay
    n = int((length - offset) // bay) + 1
    for i in range(-1, n + 1):
        x0 = offset + i * bay
        if x0 > length or x0 + bay < 0: continue
        pil0, pil1 = x0, x0 + 0.8
        kind = zone_at(min(max(x0 + bay / 2, 0), length - 0.01))
        if kind == 'recess':
            continue
        d.rectangle((P(pil0), 0, P(pil1) - 1, Hp), fill=BRICK_L)
        d.line((P(pil1), 0, P(pil1), Hp), fill=BRICK_D)
        wx0, wx1 = x0 + 1.2, x0 + bay - 0.4
        if kind == 'blank':
            continue
        for f in range(floors):
            zb = f * FH + 0.95
            zt_ = zb + 1.95
            if f == 0 and kind == 'entrance':
                d.rectangle((P(wx0), zt(2.9), P(wx1), zt(0.15)), fill=GLASS_D, outline=FRAME)
                for m in (0.33, 0.66):
                    xm = P(wx0 + (wx1 - wx0) * m)
                    d.line((xm, zt(2.9), xm, zt(0.15)), fill=FRAME)
                continue
            a, b = P(wx0), P(wx1)
            top, bot = zt(zt_), zt(zb)
            d.rectangle((a, top, b, bot), fill=GLASS, outline=FRAME)
            if bot - top > 3:
                d.line((a + 1, top + 1, b - 1, top + 1), fill=GLASS_D)
                if rnd.random() < 0.35:   # blinds / curtains
                    d.rectangle((a + 1, top + 1, b - 1, top + max(1, (bot - top) // 3)), fill=(226, 222, 206))
                hx = a + 1 + int(rnd.random() * max(1, (b - a) // 3))
                d.line((hx, top + 2, hx + 1, bot - 2), fill=GLASS_HI)
            for m in (1 / 3, 2 / 3):
                xm = P(wx0 + (wx1 - wx0) * m)
                d.line((xm, top, xm, bot), fill=FRAME)
            mid = (top + bot) // 2
            if bot - top > 6:
                d.line((a, mid, b, mid), fill=FRAME)
            d.line((a - 1, bot + 1, b + 1, bot + 1), fill=FRAME)  # sill
    # stair recess zones: darker brick, narrow windows
    for a, b, kind in zones:
        if kind != 'recess': continue
        d.rectangle((P(a), 0, P(b), Hp), fill=BRICK_D)
        cx = (a + b) / 2
        for f in range(floors):
            z0 = f * FH + 1.6
            d.rectangle((P(cx - 0.7), zt(z0 + 1.4), P(cx + 0.7), zt(z0)), fill=GLASS_D, outline=FRAME)
        d.rectangle((P(cx - 1.2), zt(2.4), P(cx + 1.2), zt(0)), fill=(60, 70, 74), outline=FRAME)
    # parapet coping & plinth
    d.rectangle((0, 0, W, max(1, P(0.18))), fill=COPING)
    d.line((0, max(1, P(0.18)) + 1, W, max(1, P(0.18)) + 1), fill=BRICK_D)
    if plinth:
        d.rectangle((0, zt(0.45), W, Hp), fill=PLINTH)
    if k != 1.0:
        arr = np.asarray(im).astype(np.float32)
        arr[..., :3] *= k
        im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    return im


def solid(w, h, col, noise=0.08, seed=1, col2=None):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (max(1, w), max(1, h)), col + (255,))
    px = im.load()
    c2 = col2 or shade(col, 0.9)
    for y in range(im.height):
        for x in range(im.width):
            if rnd.random() < noise: px[x, y] = c2 + (255,)
    return im


# ---------------- warping ----------------
def persp_coeffs(dst, src):
    """dst: 4 output pts, src: 4 texture pts. Returns PIL PERSPECTIVE coefficients (output->input)."""
    A, B = [], []
    for (x, y), (u, v) in zip(dst, src):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    return np.linalg.solve(np.array(A, float), np.array(B, float)).tolist()


def warp(canvas, tex, quad):
    """quad: screen pts for tex corners TL, TR, BR, BL."""
    w, h = tex.size
    try:
        c = persp_coeffs(quad, [(0, 0), (w, 0), (w, h), (0, h)])
    except np.linalg.LinAlgError:
        return
    layer = tex.transform(canvas.size, Image.PERSPECTIVE, c, Image.NEAREST)
    # mask to the quad (avoid wrap-around artifacts)
    m = Image.new('L', canvas.size, 0)
    ImageDraw.Draw(m).polygon([tuple(p) for p in quad], fill=255)
    a = np.minimum(np.asarray(layer)[..., 3], np.asarray(m))
    arr = np.asarray(layer).copy(); arr[..., 3] = a
    canvas.alpha_composite(Image.fromarray(arr))


# ---------------- trees ----------------
def pine(scale, seed):
    rnd = random.Random(seed)
    w, h = int(22 * scale), int(30 * scale)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rectangle((w // 2 - max(1, int(scale)), int(h * 0.62), w // 2 + max(1, int(scale)), h), fill=TRUNK)
    # layered flat crowns like a Korean pine
    for i, (yy, rw) in enumerate([(0.55, 0.50), (0.40, 0.42), (0.27, 0.34), (0.15, 0.22)]):
        cy = int(h * yy); rx = int(w * rw); ry = max(2, int(h * 0.08))
        cx = w // 2 + rnd.randint(-int(2 * scale), int(2 * scale))
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=PINE[0])
        d.ellipse((cx - rx + 1, cy - ry, cx + rx - 2, cy + ry - 2), fill=PINE[1])
        for _ in range(int(6 * scale)):
            px_ = cx + rnd.randint(-rx + 2, rx - 2); py_ = cy + rnd.randint(-ry, 0)
            d.point((px_, py_), fill=PINE[2])
    return im


def shrub(w, h, seed):
    rnd = random.Random(seed)
    im = Image.new('RGBA', (max(2, w), max(2, h)), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, h // 4, w - 1, h - 1), radius=max(1, h // 3), fill=HEDGE[2])
    d.rounded_rectangle((0, 0, w - 1, h - 2), radius=max(1, h // 3), fill=HEDGE[0])
    for _ in range(w * h // 6):
        d.point((rnd.randint(1, w - 2), rnd.randint(1, max(1, h - 3))), fill=HEDGE[1])
    return im


# ================= A-2: 3/4 oblique game sprite =================
KX, KY = 0.50, 0.55


def planting_items():
    """Hedges and pines in front of the facades (world m), sorted back to front."""
    items = []
    for x in np.arange(D + 1.5, L1 - 1, 3.2):
        if XE - 7.5 < x < XE + 19: continue
        items.append(('hedge', x, D + 1.2))
    for y in np.arange(D + 2.5, D + L2 - 1, 3.2):
        items.append(('hedge', D + 1.2, y))
    for x, y in [(XE - 12, D + 2.6), (XE - 8.5, D + 2.2), (XE + 22, D + 2.4),
                 (D + 2.6, D + 8), (D + 2.6, D + L2 - 4)]:
        items.append(('pine', x, y))
    items.sort(key=lambda t: t[2])
    return items


@lru_cache(maxsize=4)
def _sprite_canvas(s=6, ppm=6):
    """Uncropped game sprite canvas + projection. Cached; callers must copy before drawing on it."""
    W, Hh = int((L1 + 0.5 * (D + L2) + 40) * s), int((0.55 * (D + L2) + H4 + 12) * s)
    ox, oy = int(0.50 * (D + L2) * s) + 20, int((H4 + 8) * s)
    cv = Image.new('RGBA', (W, Hh), (0, 0, 0, 0))
    dr = ImageDraw.Draw(cv)
    P = lambda x, y, z: (ox + s * (x - KX * y), oy + s * (KY * y - z))

    def south(x0, x1, y, z0, z1, tex):
        warp(cv, tex, [P(x0, y, z1), P(x1, y, z1), P(x1, y, z0), P(x0, y, z0)])

    def east(x, y0, y1, z0, z1, tex):
        warp(cv, tex, [P(x, y1, z1), P(x, y0, z1), P(x, y0, z0), P(x, y1, z0)])

    def top(x0, x1, y0, y1, z, col, rim=COPING, grid=3.0):
        poly = [P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)]
        dr.polygon(poly, fill=col)
        g = grid
        xx = x0 + g
        while xx < x1 - 0.5:
            dr.line([P(xx, y0, z), P(xx, y1, z)], fill=shade(col, 0.93)); xx += g
        yy = y0 + g
        while yy < y1 - 0.5:
            dr.line([P(x0, yy, z), P(x1, yy, z)], fill=shade(col, 0.93)); yy += g
        if rim:
            dr.line(poly + [poly[0]], fill=rim, width=max(1, s // 3))

    def box(x0, x1, y0, y1, z0, z1, col, kE=0.82, kS=0.95, kT=1.08):
        ws, hs = int((x1 - x0) * ppm) + 1, int((z1 - z0) * ppm) + 1
        we = int((y1 - y0) * ppm) + 1
        east(x1, y0, y1, z0, z1, solid(we, hs, shade(col, kE), seed=3))
        south(x0, x1, y1, z0, z1, solid(ws, hs, shade(col, kS), seed=4))
        top(x0, x1, y0, y1, z1, shade(col, kT), rim=None, grid=99)

    # --- main wing ---
    mlen = L1 - D
    off = ((XE - D) - 2.25) % 4.5
    tex = facade(mlen, H4, ppm, 4, offset=off, seed=11,
                 zones=[(XE - D - 2.3, XE - D + 2.3, 'entrance'), (MSTAIR[0], MSTAIR[1], 'recess'),
                        (mlen - ESTAIR_W, mlen, 'recess')])
    south(D, L1, D, 0, H4, tex)
    east(L1, 0, D, 0, H4, facade(D, H4, ppm, 4, offset=1.0, seed=12, k=0.84))
    top(0, L1, 0, D, H4, ROOF)
    # roof AC units & railing posts
    for i, ax in enumerate(range(26, int(L1) - 6, 13)):
        box(ax, ax + 2.4, 3 + (i % 2) * 7, 5 + (i % 2) * 7, H4, H4 + 1.2, (196, 198, 196))
    # --- west wing, 4-storey part ---
    tlen = ARCH_Y0 - D
    east(D, D, ARCH_Y0, 0, H4, facade(tlen, H4, ppm, 4, offset=0.6, seed=13, k=0.86,
                                      zones=[(0, ARCH_Y0 - STAIR_Y0, 'recess'), (tlen - 4.5, tlen, 'recess')]))
    top(0, D, D - 0.01, ARCH_Y0, H4, ROOF)
    # cover the seam between the two roofs
    dr.line([P(0.3, D, H4), P(D - 0.3, D, H4)], fill=ROOF, width=max(1, s // 2))
    south(0, D, ARCH_Y0, H3, H4, facade(D, H4, ppm, 4, offset=1.0, seed=14, plinth=False).crop(
        (0, 0, int(D * ppm), int((H4 - H3) * ppm))))
    # corner stair tower (slightly taller)
    box(10.5, 17.8, 11.5, 19.2, H4, H4 + 3.4, BRICK, kT=1.0)
    top(10.5, 17.8, 11.5, 19.2, H4 + 3.4, (118, 150, 120), rim=COPING, grid=99)
    # --- arch section (3 floors + blue barrel vault) ---
    alen = D + L2 - ARCH_Y0
    east(D, ARCH_Y0, D + L2, 0, H3, facade(alen, H3, ppm, 3, offset=1.4, seed=15, k=0.86))
    steps = 36
    for i in range(steps):
        xa, xb = D * i / steps, D * (i + 1) / steps
        za = H3 + VAULT * math.sqrt(max(0, 1 - ((xa - D / 2) / (D / 2)) ** 2))
        zb = H3 + VAULT * math.sqrt(max(0, 1 - ((xb - D / 2) / (D / 2)) ** 2))
        slope = (zb - za)
        col = VAULT_L if slope > 0.15 else (VAULT_C if slope > -0.15 else VAULT_D)
        poly = [P(xa, ARCH_Y0, za), P(xb, ARCH_Y0, zb), P(xb, D + L2, zb), P(xa, D + L2, za)]
        dr.polygon(poly, fill=col)
    for yy in np.arange(ARCH_Y0 + 1.5, D + L2, 1.5):   # standing seams
        pts = [P(D * i / 24, yy, H3 + VAULT * math.sqrt(max(0, 1 - ((D * i / 24 - D / 2) / (D / 2)) ** 2))) for i in range(25)]
        dr.line(pts, fill=shade(VAULT_C, 0.85))
    gable = facade(D, H3 + VAULT, ppm, 3, offset=1.0, seed=16)
    gpx = gable.load(); gw, gh = gable.size
    for gx in range(gw):
        xm = gx / ppm
        zc = H3 + VAULT * math.sqrt(max(0, 1 - ((xm - D / 2) / (D / 2)) ** 2))
        cut = gh - int(zc * ppm)
        for gy in range(0, max(0, cut)): gpx[gx, gy] = (0, 0, 0, 0)
        for gy in range(max(0, cut), min(gh, cut + 2)): gpx[gx, gy] = VAULT_D + (255,)
    south(0, D, D + L2, 0, H3 + VAULT, gable)
    # --- entrance: dark canopy, white columns, steps ---
    for cx in (XE - 4.6, XE + 4.0):
        box(cx, cx + 0.6, D + 3.6, D + 4.2, 0, 3.3, (236, 236, 230))
    box(XE - 4.2, XE + 4.2, D + 4.2, D + 6.0, 0, 0.45, GRANITE)
    box(XE - 6.5, XE + 6.5, D, D + 4.6, 3.3, 4.3, CANOPY, kT=1.25)
    # --- assembly platform (조회대) ---
    px0, px1, py1 = XE + 7.0, XE + 18.0, D + 8.0
    box(px0, px1, D, py1, 0, 1.3, GRANITE, kE=0.85, kS=0.92, kT=1.05)
    for k, (a, b) in enumerate([(py1, py1 + 0.8), (py1 + 0.8, py1 + 1.6), (py1 + 1.6, py1 + 2.4)]):
        box(px0 + 1.0, px0 + 5.0, a, b, 0, 1.3 - 0.43 * (k + 1) + 0.43, GRANITE)
    rail = [(px0 + 5.2, py1), (px1, py1), (px1, D + 0.4)]
    for (ax, ay), (bx, by) in zip(rail, rail[1:]):
        dr.line([P(ax, ay, 2.3), P(bx, by, 2.3)], fill=STEEL, width=max(1, s // 3))
        n = int(math.hypot(bx - ax, by - ay) / 1.6)
        for i in range(n + 1):
            t = i / max(1, n); x_, y_ = ax + (bx - ax) * t, ay + (by - ay) * t
            dr.line([P(x_, y_, 1.3), P(x_, y_, 2.3)], fill=STEEL)
    # --- planting ---
    for kind, x, y in planting_items():
        sx, sy = P(x, y, 0)
        if kind == 'hedge':
            im = shrub(int(3.4 * s), int(1.6 * s), int(x * 7 + y))
        else:
            im = pine(s / 3.2, int(x + y))
        cv.alpha_composite(im, (int(sx - im.width / 2), int(sy - im.height)))
    return cv, (ox, oy)


# ================= A-1: hero illustration (photo angle, perspective) =================
def render_hero(Wc=480, Hc=270, up=4, ppm=8):
    C = np.array([XE + 34.0, D + 40.0, 1.6])
    tgt = np.array([D + 2.0, D + 14.0])
    f = tgt - C[:2]; f = f / np.linalg.norm(f)
    r = np.array([-f[1], f[0]])
    F = (Wc / 2) / math.tan(math.radians(35))
    cx, cy = Wc / 2, Hc * 0.64
    cv = Image.new('RGBA', (Wc, Hc), (0, 0, 0, 255))
    dr = ImageDraw.Draw(cv)

    def depth(p): return float((np.array(p[:2]) - C[:2]) @ f)

    def P(x, y, z):
        d = np.array([x, y]) - C[:2]
        dep = d @ f
        return (cx + F * (d @ r) / dep, cy - F * (z - C[2]) / dep)

    # sky
    sky = np.zeros((Hc, Wc, 3), np.uint8)
    for yy in range(Hc):
        t = yy / (Hc * 0.6)
        c = np.array([118, 166, 214]) * (1 - min(t, 1)) + np.array([212, 228, 240]) * min(t, 1)
        sky[yy] = c
    cv.paste(Image.fromarray(sky).convert('RGBA'))
    rnd = random.Random(7)
    for (ccx, ccy, sc) in [(70, 40, 1.2), (190, 26, 0.9), (300, 52, 1.4), (420, 30, 1.0), (130, 88, 0.8), (380, 96, 0.7)]:
        for k in range(int(9 * sc)):
            ex, ey = ccx + rnd.randint(-int(34 * sc), int(34 * sc)), ccy + rnd.randint(-int(8 * sc), int(6 * sc))
            rx, ry = rnd.randint(8, 18) * sc, rnd.randint(5, 9) * sc
            dr.ellipse((ex - rx, ey - ry + 2, ex + rx, ey + ry + 2), fill=(196, 206, 218))
        for k in range(int(9 * sc)):
            ex, ey = ccx + rnd.randint(-int(32 * sc), int(32 * sc)), ccy + rnd.randint(-int(9 * sc), int(4 * sc))
            rx, ry = rnd.randint(7, 16) * sc, rnd.randint(4, 8) * sc
            dr.ellipse((ex - rx, ey - ry, ex + rx, ey + ry), fill=(246, 248, 250))
    # ground (sand field)
    hy = int(cy)
    g = np.zeros((Hc - hy, Wc, 3), np.uint8)
    for yy in range(Hc - hy):
        t = yy / (Hc - hy)
        g[yy] = np.array([206, 196, 176]) * (1 - t) + np.array([224, 214, 194]) * t
    gim = Image.fromarray(g).convert('RGBA'); gp = gim.load()
    for _ in range(int(Wc * (Hc - hy) * 0.08)):
        x_, y_ = rnd.randrange(Wc), rnd.randrange(Hc - hy)
        c = gp[x_, y_]; k = rnd.choice([0.94, 1.04])
        gp[x_, y_] = tuple(min(255, int(v * k)) for v in c[:3]) + (255,)
    cv.alpha_composite(gim, (0, hy))

    def face_south(x0, x1, y, z0, z1, tex):
        warp(cv, tex, [P(x0, y, z1), P(x1, y, z1), P(x1, y, z0), P(x0, y, z0)])

    def face_east(x, y0, y1, z0, z1, tex):   # left of texture = south (y1)
        warp(cv, tex, [P(x, y1, z1), P(x, y0, z1), P(x, y0, z0), P(x, y1, z0)])

    def poly(pts, col): dr.polygon([P(*p) for p in pts], fill=col)

    # plinth strip of paving in front of the building
    # --- west wing (far) ---
    tlen = ARCH_Y0 - D
    face_east(D, D, ARCH_Y0, 0, H4, facade(tlen, H4, ppm, 4, offset=0.6, seed=13, k=0.93,
                                           zones=[(0, ARCH_Y0 - STAIR_Y0, 'recess'), (tlen - 4.5, tlen, 'recess')]))
    alen = D + L2 - ARCH_Y0
    face_east(D, ARCH_Y0, D + L2, 0, H3, facade(alen, H3, ppm, 3, offset=1.4, seed=15, k=0.93))
    # barrel vault (east-facing half visible)
    n = 14
    for i in range(n):
        xa, xb = D - D / 2 * i / n, D - D / 2 * (i + 1) / n
        za = H3 + VAULT * math.sqrt(max(0, 1 - ((xa - D / 2) / (D / 2)) ** 2))
        zb = H3 + VAULT * math.sqrt(max(0, 1 - ((xb - D / 2) / (D / 2)) ** 2))
        col = VAULT_L if i > n * 0.55 else VAULT_C
        poly([(xa, ARCH_Y0, za), (xb, ARCH_Y0, zb), (xb, D + L2 + 0.4, zb), (xa, D + L2 + 0.4, za)], col)
    dr.line([P(D, ARCH_Y0, H3), P(D, D + L2, H3)], fill=COPING)
    for yy in np.arange(ARCH_Y0 + 1.2, D + L2, 1.2):
        dr.line([P(D, yy, H3), P(D / 2, yy, H3 + VAULT)], fill=VAULT_D)
    # small entrance canopy on west wing 1F (stair recess)
    poly([(D, STAIR_Y0, 3.0), (D + 2.2, STAIR_Y0, 3.0), (D + 2.2, STAIR_Y1, 3.0), (D, STAIR_Y1, 3.0)], (60, 64, 70))
    # corner stair tower
    face_east(17.8, 11.5, 19.2, H4 - 0.5, H4 + 3.4, solid(int(7.7 * ppm), int(3.9 * ppm), shade(BRICK, 0.9), seed=5))
    face_south(10.5, 17.8, 19.2, H4 - 0.5, H4 + 3.4, solid(int(7.3 * ppm), int(3.9 * ppm), BRICK, seed=6))
    dr.line([P(10.5, 19.2, H4 + 3.4), P(17.8, 19.2, H4 + 3.4), P(17.8, 11.5, H4 + 3.4)], fill=COPING)
    # --- main wing south face (near, clipped before the camera plane) ---
    xclip = D
    while depth((xclip + 0.5, D)) > 2.5 and xclip < L1: xclip += 0.5
    mlen = xclip - D
    off = ((XE - D) - 2.25) % 4.5
    face_south(D, xclip, D, 0, H4, facade(mlen, H4, ppm, 4, offset=off, seed=11,
               zones=[(XE - D - 2.3, XE - D + 2.3, 'entrance')]))
    # --- planting along facades (sorted far -> near) ---
    items = []
    for y in np.arange(D + 4, D + L2 - 1, 2.6): items.append(('hedge', D + 1.4, y))
    for x in np.arange(D + 2, xclip - 1, 2.6):
        if XE - 7.5 < x < XE + 18.5: continue
        items.append(('hedge', x, D + 1.4))
    for x, y, hgt in [(D + 2.5, D + 9, 7.0), (D + 2.8, D + 19, 6.0), (XE - 15, D + 2.4, 6.5), (XE - 10.5, D + 2.6, 7.5),
                      (XE - 8.0, D + 1.8, 5.0), (D + 3, D + L2 - 8, 5.5)]:
        items.append(('pine', x, y, hgt))
    items.sort(key=lambda t: -depth((t[1], t[2])))
    for it in items:
        kind, x, y = it[:3]
        dep = depth((x, y))
        if dep < 2: continue
        sx, sy = P(x, y, 0)
        if kind == 'hedge':
            hp = max(2, int(F * 1.1 / dep)); wp = max(3, int(F * 2.6 / dep))
            im = shrub(wp, hp, int(x * 3 + y))
        else:
            hp = max(4, int(F * it[3] / dep))
            base = pine(2.0, int(x + y))
            im = base.resize((max(3, int(base.width * hp / base.height)), hp), Image.NEAREST)
        cv.alpha_composite(im, (int(sx - im.width / 2), int(sy - im.height)))
    # --- central entrance: steps, columns, dark canopy ---
    poly([(XE - 4.2, D + 6.0, 0.45), (XE + 4.2, D + 6.0, 0.45), (XE + 4.2, D + 6.0, 0), (XE - 4.2, D + 6.0, 0)], GRANITE_D)
    poly([(XE - 4.2, D + 4.2, 0.45), (XE + 4.2, D + 4.2, 0.45), (XE + 4.2, D + 6.0, 0.45), (XE - 4.2, D + 6.0, 0.45)], GRANITE)
    for cxm in (XE - 4.6, XE + 4.0):
        poly([(cxm, D + 4.2, 3.3), (cxm + 0.6, D + 4.2, 3.3), (cxm + 0.6, D + 4.2, 0.4), (cxm, D + 4.2, 0.4)], (240, 240, 234))
        poly([(cxm + 0.6, D + 3.6, 3.3), (cxm + 0.6, D + 4.2, 3.3), (cxm + 0.6, D + 4.2, 0.4), (cxm + 0.6, D + 3.6, 0.4)], (200, 200, 196))
    poly([(XE - 6.5, D, 3.3), (XE + 6.5, D, 3.3), (XE + 6.5, D + 4.6, 3.3), (XE - 6.5, D + 4.6, 3.3)], CANOPY)   # underside
    poly([(XE + 6.5, D, 4.3), (XE + 6.5, D + 4.6, 4.3), (XE + 6.5, D + 4.6, 3.3), (XE + 6.5, D, 3.3)], shade(CANOPY_L, 0.85))
    poly([(XE - 6.5, D + 4.6, 4.3), (XE + 6.5, D + 4.6, 4.3), (XE + 6.5, D + 4.6, 3.3), (XE - 6.5, D + 4.6, 3.3)], CANOPY_L)
    # blank banner panel on canopy front (no text)
    # --- assembly platform (조회대) ---
    px0, px1, py1 = XE + 7.0, XE + 18.0, D + 8.0
    poly([(px0, D, 1.3), (px1, D, 1.3), (px1, py1, 1.3), (px0, py1, 1.3)], GRANITE)
    poly([(px1, D, 1.3), (px1, py1, 1.3), (px1, py1, 0), (px1, D, 0)], GRANITE_D)
    poly([(px0, py1, 1.3), (px1, py1, 1.3), (px1, py1, 0), (px0, py1, 0)], shade(GRANITE, 0.94))
    for k in range(3):   # steps descending south
        y0, y1, zt_ = py1 + 0.8 * k, py1 + 0.8 * (k + 1), 1.3 - 0.43 * (k + 1)
        poly([(px0 + 1, y0, zt_), (px0 + 5, y0, zt_), (px0 + 5, y1, zt_), (px0 + 1, y1, zt_)], GRANITE)
        poly([(px0 + 1, y1, zt_), (px0 + 5, y1, zt_), (px0 + 5, y1, 0), (px0 + 1, y1, 0)], shade(GRANITE, 0.88))
        poly([(px0 + 5, y0, zt_), (px0 + 5, y1, zt_), (px0 + 5, y1, 0), (px0 + 5, y0, 0)], GRANITE_D)
    rail = [(px0 + 5.2, py1), (px1, py1), (px1, D + 0.4)]
    for (ax, ay), (bx, by) in zip(rail, rail[1:]):
        for zr in (2.3, 1.8):
            dr.line([P(ax, ay, zr), P(bx, by, zr)], fill=STEEL)
        m = int(math.hypot(bx - ax, by - ay) / 1.4)
        for i in range(m + 1):
            t = i / max(1, m); x_, y_ = ax + (bx - ax) * t, ay + (by - ay) * t
            dr.line([P(x_, y_, 1.3), P(x_, y_, 2.3)], fill=(176, 180, 186))
    return cv.resize((Wc * up, Hc * up), Image.NEAREST)


# =====================================================================================
#  v6 additions: game sprite / ruin, props, ground, tiles, floor plans, kiosk plan, CLI
# =====================================================================================
def _proj(s, ox, oy):
    return lambda x, y, z: (ox + s * (x - KX * y), oy + s * (KY * y - z))


class Painter:
    """Same face/roof/box drawing as the game sprite, for any canvas + projection."""

    def __init__(self, cv, P, s=6, ppm=6):
        self.cv, self.P, self.s, self.ppm = cv, P, s, ppm
        self.dr = ImageDraw.Draw(cv)

    def south(self, x0, x1, y, z0, z1, tex):
        P = self.P
        warp(self.cv, tex, [P(x0, y, z1), P(x1, y, z1), P(x1, y, z0), P(x0, y, z0)])

    def east(self, x, y0, y1, z0, z1, tex):
        P = self.P
        warp(self.cv, tex, [P(x, y1, z1), P(x, y0, z1), P(x, y0, z0), P(x, y1, z0)])

    def top(self, x0, x1, y0, y1, z, col, rim=COPING, grid=3.0):
        P, dr = self.P, self.dr
        poly = [P(x0, y0, z), P(x1, y0, z), P(x1, y1, z), P(x0, y1, z)]
        dr.polygon(poly, fill=col)
        xx = x0 + grid
        while xx < x1 - 0.5:
            dr.line([P(xx, y0, z), P(xx, y1, z)], fill=shade(col, 0.93)); xx += grid
        yy = y0 + grid
        while yy < y1 - 0.5:
            dr.line([P(x0, yy, z), P(x1, yy, z)], fill=shade(col, 0.93)); yy += grid
        if rim:
            dr.line(poly + [poly[0]], fill=rim, width=max(1, self.s // 3))

    def box(self, x0, x1, y0, y1, z0, z1, col, kE=0.82, kS=0.95, kT=1.08):
        ppm = self.ppm
        ws, hs = int((x1 - x0) * ppm) + 1, int((z1 - z0) * ppm) + 1
        we = int((y1 - y0) * ppm) + 1
        self.east(x1, y0, y1, z0, z1, solid(we, hs, shade(col, kE), seed=3))
        self.south(x0, x1, y1, z0, z1, solid(ws, hs, shade(col, kS), seed=4))
        self.top(x0, x1, y0, y1, z1, shade(col, kT), rim=None, grid=99)


def _prop_canvas(ext, s=6):
    """ext = (x0, x1, y0, y1, zmax) in world m. Returns canvas, projection, origin px of world (0,0,0)."""
    x0, x1, y0, y1, zmax = ext
    ox = int(round(s * (-x0 + KX * y1))) + 12
    oy = int(round(s * (-KY * y0 + zmax))) + 12
    W = int(s * (x1 - x0 + KX * (y1 - y0))) + 24
    H = int(s * (KY * (y1 - y0) + zmax)) + 24
    return Image.new('RGBA', (W, H), (0, 0, 0, 0)), _proj(s, ox, oy), (ox, oy)


def _crop(cv, origin, pad=2):
    b = cv.getbbox()
    box = (b[0] - pad, b[1] - pad, b[2] + pad, b[3] + pad)
    return cv.crop(box), (origin[0] - box[0], origin[1] - box[1])


def _hash2(xx, yy, seed, a=73856093, b=19349663):
    return ((xx.astype(np.int64) * a) ^ (yy.astype(np.int64) * b) ^ seed) & 0x7fffffff


# ---------------- ruin (50 years later) ----------------
SPRITE_FACES = [((D, D), (L1, D), 0.3, H4 - 0.3),             # main wing south face
                ((L1, 0), (L1, D), 0.3, H4 - 0.3),            # main wing east end
                ((D, ARCH_Y0), (D, D), 0.3, H4 - 0.3),        # west wing east face (4 storeys)
                ((D, D + L2), (D, ARCH_Y0), 0.3, H3 - 0.3),   # arch section east face
                ((0, D + L2), (D, D + L2), 0.3, H3 - 0.3)]    # arch gable
SPRITE_ROOFS = [(0, L1, 0, D, H4), (0, D, D, ARCH_Y0, H4)]


def apply_ruin(cv, P, faces, roofs, seed=404):
    """Cracks, vines, broken windows and roof stains, drawn only on matching building pixels."""
    rnd = random.Random(seed)
    arr = np.array(cv).astype(np.int64)
    H, W = arr.shape[:2]
    r, g, b, a = arr[..., 0].copy(), arr[..., 1].copy(), arr[..., 2].copy(), arr[..., 3].copy()
    yy, xx = np.mgrid[0:H, 0:W]
    # broken windows: whole glass cells go dark, with black shards
    glass = (a == 255) & (b - r >= 16) & (r >= 95) & (b >= g)
    broken = (_hash2(xx // 6, yy // 6, seed) >> 3) % 100 < 48
    shard = (_hash2(xx, yy, seed * 7, 2654435761, 40503) >> 5) % 8 < 3
    m = glass & broken
    arr[m & ~shard, :3] = GLASS_D
    arr[m & shard, :3] = SHARD
    # roof stains and moss
    roofm = (a == 255) & (np.abs(r - g) <= 8) & (np.abs(g - b) <= 8) & (r >= 110) & (r <= 175)
    ov = Image.new('L', (W, H), 0); d = ImageDraw.Draw(ov)
    for x0, x1, y0, y1, z in roofs:
        for _ in range(int((x1 - x0) * (y1 - y0) / 70) + 2):
            px, py = P(rnd.uniform(x0, x1), rnd.uniform(y0, y1), z)
            rx = rnd.randint(3, 9); ry = max(2, rx // 2)
            d.ellipse((px - rx, py - ry, px + rx, py + ry), fill=255 if rnd.random() < 0.7 else 128)
    o = np.array(ov)
    dots = (_hash2(xx, yy, seed + 1) % 3) != 0
    arr[roofm & (o == 255) & dots, :3] = STAIN
    arr[roofm & (o == 128) & dots, :3] = HEDGE[2]
    # cracks: dark zigzags on brick
    brick = (a == 255) & (r - g >= 35)
    ov = Image.new('L', (W, H), 0); d = ImageDraw.Draw(ov)
    for (ax, ay), (bx, by), z0, z1 in faces:
        length = math.hypot(bx - ax, by - ay)
        for _ in range(max(3, int(length / 4))):
            u = rnd.random(); v = rnd.uniform(0.3, 0.98)
            px, py = P(ax + (bx - ax) * u, ay + (by - ay) * u, z0 + (z1 - z0) * v)
            pts = [(px, py)]
            for _k in range(rnd.randint(4, 9)):
                px += rnd.choice((-1, 1)) * rnd.randint(1, 3); py += rnd.randint(2, 4)
                pts.append((px, py))
            d.line(pts, fill=255)
            d.line([(x + 1, y) for x, y in pts[:len(pts) // 2]], fill=255)      # wider near the top
    o = np.array(ov)
    arr[brick & (o > 0), :3] = CRACK
    # vines climbing from the ground
    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    greens = PINE[:3] + HEDGE
    for (ax, ay), (bx, by), z0, z1 in faces:
        length = math.hypot(bx - ax, by - ay)
        for _ in range(max(2, int(length / 6))):
            u = rnd.random(); topv = rnd.uniform(0.3, 0.9); v = 0.0
            while v < topv:
                px, py = P(ax + (bx - ax) * u, ay + (by - ay) * u, (z1 + 0.3) * v)
                spread = 2 + int(3 * (1 - v / topv))
                for _k in range(rnd.randint(3, 7)):
                    d.point((px + rnd.randint(-spread, spread), py + rnd.randint(-2, 2)), fill=rnd.choice(greens) + (255,))
                v += 0.02; u = min(1, max(0, u + rnd.uniform(-0.005, 0.005)))
    o = np.array(ov)
    mv = (a == 255) & (o[..., 3] > 0)
    arr[mv, :3] = o[mv, :3]
    # weathering: everything fades a little toward grey
    solidpx = arr[..., 3] > 0
    grey = arr[..., :3].mean(axis=2, keepdims=True)
    arr[..., :3] = np.where(solidpx[..., None], (arr[..., :3] * 0.8 + grey * 0.2) * 0.94, arr[..., :3])
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def _canopy_sag(img, P):
    """The entrance canopy's east end has dropped and torn."""
    d = ImageDraw.Draw(img)
    yf = D + 4.6
    d.polygon([P(XE + 0.5, D, 4.3), P(XE + 6.5, D, 3.5), P(XE + 6.5, yf, 3.5), P(XE + 0.5, yf, 4.3)], fill=shade(CANOPY, 1.15))
    d.polygon([P(XE + 0.5, yf, 4.3), P(XE + 6.5, yf, 3.5), P(XE + 6.5, yf, 2.6), P(XE + 0.5, yf, 3.3)], fill=shade(CANOPY_L, 0.8))
    for i, xm in enumerate((XE + 1.6, XE + 3.1, XE + 4.9)):
        zt = 3.3 - (xm - XE - 0.5) * 0.12
        d.line([P(xm, yf, zt), P(xm, yf, zt - 0.5 - 0.3 * (i % 2))], fill=CANOPY)


# ---------------- game sprite ----------------
def _sprite_box(s=6, ppm=6):
    cv, origin = _sprite_canvas(s, ppm)
    b = cv.getbbox()
    return (b[0] - 4, b[1] - 4, b[2] + 4, b[3] + 4), origin


def render_sprite(s=6, ppm=6, ruin=False):
    cv, origin = _sprite_canvas(s, ppm)
    box, _ = _sprite_box(s, ppm)
    img = cv.copy()
    if ruin:
        P = _proj(s, *origin)
        img = apply_ruin(img, P, SPRITE_FACES, SPRITE_ROOFS, seed=404)
        _canopy_sag(img, P)
    return img.crop(box)


def sprite_meta(s=6, ppm=6):
    box, origin = _sprite_box(s, ppm)
    return {'size': [box[2] - box[0], box[3] - box[1]], 'origin': [origin[0] - box[0], origin[1] - box[1]]}


# ---------------- props: 목련관, gates, 급수대, ground ----------------
def render_annex(s=6, ppm=6, ruin=False):
    x0, x1, y0, y1 = ANNEX; h = ANNEX_H
    cv, P, origin = _prop_canvas((x0 - 2, x1 + 2, y0 - 2, y1 + 4, h + 2), s)
    pt = Painter(cv, P, s, ppm)
    pt.east(x1, y0, y1, 0, h, facade(y1 - y0, h, ppm, 2, offset=1.0, seed=21, k=0.84))
    pt.south(x0, x1, y1, 0, h, facade(x1 - x0, h, ppm, 2, offset=0.8, seed=22, zones=[(2.0, 6.5, 'entrance')]))
    pt.top(x0, x1, y0, y1, h, ROOF)
    pt.box(x1 - 7, x1 - 4.6, y0 + 3, y0 + 5, h, h + 1.1, (196, 198, 196))      # roof AC unit
    pt.box(x0 + 1.5, x0 + 7.5, y1, y1 + 2.2, 2.9, 3.4, CANOPY, kT=1.25)        # entrance canopy
    for x in np.arange(x0 + 9.0, x1 - 1, 3.2):
        sx, sy = P(x, y1 + 1.0, 0)
        im = shrub(int(3.4 * s), int(1.6 * s), int(x * 7 + y1))
        cv.alpha_composite(im, (int(sx - im.width / 2), int(sy - im.height)))
    if ruin:
        cv = apply_ruin(cv, P, [((x0, y1), (x1, y1), 0.3, h - 0.3), ((x1, y0), (x1, y1), 0.3, h - 0.3)],
                        [(x0, x1, y0, y1, h)], seed=505)
    return _crop(cv, origin)


def _fence(pt, along, fixed, a, b):
    """Low brick wall with a steel railing, running along 'x' or 'y'."""
    if along == 'y':
        pt.box(fixed - 0.3, fixed + 0.3, a, b, 0, 0.9, BRICK)
    else:
        pt.box(a, b, fixed - 0.3, fixed + 0.3, 0, 0.9, BRICK)
    P, dr = pt.P, pt.dr
    n = int(abs(b - a) / 1.5)
    pts = [(fixed, a + (b - a) * i / max(1, n)) if along == 'y' else (a + (b - a) * i / max(1, n), fixed) for i in range(n + 1)]
    for x, y in pts:
        dr.line([P(x, y, 0.9), P(x, y, 1.9)], fill=STEEL)
    (xa, ya), (xb, yb) = pts[0], pts[-1]
    dr.line([P(xa, ya, 1.9), P(xb, yb, 1.9)], fill=STEEL)


def render_gate(which, s=6, ppm=6):
    if which == 'east':
        gx, g0, g1 = GATE_E
        cv, P, origin = _prop_canvas((gx - 3, gx + 3, g0 - 11, g1 + 11, 4), s)
        pt = Painter(cv, P, s, ppm)
        _fence(pt, 'y', gx, g0 - 10, g0 - 1.2)
        pt.box(gx - 0.6, gx + 0.6, g0 - 1.2, g0, 0, 2.4, GRANITE)
        pt.box(gx - 0.75, gx + 0.75, g0 - 1.35, g0 + 0.15, 2.4, 2.6, COPING)
        for y in np.arange(g1 + 1.4, g1 + 4.6, 0.4):                     # folded sliding gate
            pt.dr.line([P(gx + 0.9, y, 0.1), P(gx + 0.9, y, 1.6)], fill=STEEL)
        pt.dr.line([P(gx + 0.9, g1 + 1.4, 1.6), P(gx + 0.9, g1 + 4.6, 1.6)], fill=STEEL)
        pt.box(gx - 0.6, gx + 0.6, g1, g1 + 1.2, 0, 2.4, GRANITE)
        pt.box(gx - 0.75, gx + 0.75, g1 - 0.15, g1 + 1.35, 2.4, 2.6, COPING)
        _fence(pt, 'y', gx, g1 + 1.2, g1 + 10)
    else:
        a0, a1, gy = GATE_N
        cv, P, origin = _prop_canvas((a0 - 11, a1 + 11, gy - 3, gy + 3, 4), s)
        pt = Painter(cv, P, s, ppm)
        _fence(pt, 'x', gy, a0 - 10, a0 - 1.2)
        pt.box(a0 - 1.2, a0, gy - 0.6, gy + 0.6, 0, 2.4, GRANITE)
        pt.box(a0 - 1.35, a0 + 0.15, gy - 0.75, gy + 0.75, 2.4, 2.6, COPING)
        pt.box(a1, a1 + 1.2, gy - 0.6, gy + 0.6, 0, 2.4, GRANITE)
        pt.box(a1 - 0.15, a1 + 1.35, gy - 0.75, gy + 0.75, 2.4, 2.6, COPING)
        _fence(pt, 'x', gy, a1 + 1.2, a1 + 10)
    return _crop(cv, origin)


def render_fountain(s=6, ppm=6):
    x0, x1, y0, y1, h = FOUNTAIN
    cv, P, origin = _prop_canvas((x0 - 1, x1 + 1, y0 - 1, y1 + 1, 2.5), s)
    pt = Painter(cv, P, s, ppm)
    pt.box(x0, x1, y0, y0 + 0.35, 0, 1.7, GRANITE)                 # back panel with taps
    pt.box(x0, x1, y0 + 0.35, y1, 0, h, GRANITE, kE=0.85, kS=0.92, kT=1.05)
    pt.top(x0 + 0.15, x1 - 0.15, y0 + 0.45, y1 - 0.15, h, STEEL, rim=None, grid=99)   # steel basin
    for x in np.arange(x0 + 0.5, x1 - 0.2, 0.8):
        pt.dr.line([P(x, y0 + 0.35, 1.45), P(x, y0 + 0.6, 1.35)], fill=STEEL)
    return _crop(cv, origin)


def _stadium(r, n=48):
    cx, cy = TRACK_C; h = TRACK_HALF
    pts = []
    for i in range(n + 1):                                   # east bend (top -> bottom)
        t = -math.pi / 2 + math.pi * i / n
        pts.append((cx + h + r * math.cos(t), cy + r * math.sin(t)))
    for i in range(n + 1):                                   # west bend (bottom -> top)
        t = math.pi / 2 + math.pi * i / n
        pts.append((cx - h + r * math.cos(t), cy + r * math.sin(t)))
    return pts


def render_ground(s=6):
    """Sand playground with track lines and paving along the faces. Drawn under everything (ground layer)."""
    cv, P, origin = _prop_canvas((D - 1, L1 + 2, D - 1, FIELD[3] + 1, 0.5), s)
    d = ImageDraw.Draw(cv)

    def quad(x0, x1, y0, y1, col):
        d.polygon([P(x0, y0, 0), P(x1, y0, 0), P(x1, y1, 0), P(x0, y1, 0)], fill=col)

    quad(*FIELD, SAND)
    arr = np.array(cv).astype(np.int64)
    H, W = arr.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W]
    sand = (arr[..., 3] == 255) & (arr[..., 0] == SAND[0]) & (arr[..., 1] == SAND[1]) & (arr[..., 2] == SAND[2])
    hsh = _hash2(xx, yy, 77) % 100
    arr[sand & (hsh < 8), :3] = SAND_L
    arr[sand & (hsh >= 8) & (hsh < 16), :3] = SAND_D
    cv = Image.fromarray(arr.astype(np.uint8)); d = ImageDraw.Draw(cv)
    for x0, x1, y0, y1 in [(D, L1, D, D + 3), (D, D + 3, D, D + L2 + 2), (XE - 8, XE + 20, D, D + 10)]:
        quad(x0, x1, y0, y1, PAVE)
        for x in np.arange(x0 + 1, x1, 1.0):
            d.line([P(x, y0, 0), P(x, y1, 0)], fill=PAVE_D)
        for y in np.arange(y0 + 1, y1, 1.0):
            d.line([P(x0, y, 0), P(x1, y, 0)], fill=PAVE_D)
    for r in (TRACK_R, TRACK_R - 2.5):
        pts = [P(x, y, 0) for x, y in _stadium(r)]
        d.line(pts + [pts[0]], fill=LINE)
    cx, cy = TRACK_C
    d.line([P(cx, cy + TRACK_R - 2.5, 0), P(cx, cy + TRACK_R, 0)], fill=LINE)
    return _crop(cv, origin)


PROPS = {
    'school-annex': lambda: render_annex(),
    'school-annex-ruin': lambda: render_annex(ruin=True),
    'school-gate-east': lambda: render_gate('east'),
    'school-gate-north': lambda: render_gate('north'),
    'school-fountain': lambda: render_fountain(),
    'school-ground': lambda: render_ground(),
}


# ---------------- 32px terrain tiles in the same palette ----------------
TILE_NAMES = ['sand', 'paving', 'corridor', 'lobby', 'door', 'stair', 'room_classroom', 'room_office', 'room_special',
              'room_care', 'room_service', 'restroom', 'ev', 'void', 'wall']
TILE_BASE = 48                                       # appended after the existing 48 terrain tiles
TILE = {n: TILE_BASE + i for i, n in enumerate(TILE_NAMES)}
CAT_COLOR = {'classroom': PLAN_CLASS, 'office': PLAN_OFFICE, 'care': PLAN_CARE, 'special': PLAN_SPECIAL,
             'service': PLAN_SERVICE, 'restroom': GLASS, 'lobby': PLAN_LOBBY}


def ground_tiles():
    out = []
    for i, name in enumerate(TILE_NAMES):
        seed = 600 + i
        if name == 'sand':
            t = solid(32, 32, SAND, 0.16, seed, SAND_D)
        elif name == 'paving':
            t = solid(32, 32, PAVE, 0.06, seed); dd = ImageDraw.Draw(t)
            for y in (0, 8, 16, 24):
                dd.line((0, y, 31, y), fill=PAVE_D)
                for x in range(0 if y % 16 else 8, 32, 16): dd.line((x, y, x, y + 7), fill=PAVE_D)
        elif name == 'corridor':
            t = solid(32, 32, PLAN_FLOOR, 0.05, seed); dd = ImageDraw.Draw(t)
            dd.line((0, 31, 31, 31), fill=shade(PLAN_FLOOR, 0.93)); dd.line((31, 0, 31, 31), fill=shade(PLAN_FLOOR, 0.93))
        elif name == 'lobby':
            t = solid(32, 32, PLAN_LOBBY, 0.06, seed); dd = ImageDraw.Draw(t)
            dd.rectangle((0, 0, 31, 31), outline=GRANITE); dd.line((0, 15, 31, 15), fill=GRANITE); dd.line((15, 0, 15, 31), fill=GRANITE)
        elif name == 'door':
            t = solid(32, 32, PLAN_FLOOR, 0.05, seed); dd = ImageDraw.Draw(t)
            dd.rectangle((5, 3, 26, 30), fill=TRUNK, outline=FRAME); dd.line((15, 4, 15, 29), fill=shade(TRUNK, 0.8))
            dd.rectangle((11, 16, 12, 17), fill=STEEL); dd.rectangle((18, 16, 19, 17), fill=STEEL)
        elif name == 'stair':
            t = solid(32, 32, COPING, 0.04, seed); dd = ImageDraw.Draw(t)
            for y in range(2, 32, 5):
                dd.line((0, y, 31, y), fill=PLINTH); dd.line((0, y + 1, 31, y + 1), fill=shade(COPING, 1.05))
        elif name.startswith('room_'):
            t = solid(32, 32, CAT_COLOR[name[5:]], 0.05, seed)
        elif name == 'restroom':
            t = solid(32, 32, GLASS, 0.04, seed); dd = ImageDraw.Draw(t)
            for v in (0, 8, 16, 24): dd.line((v, 0, v, 31), fill=GLASS_HI); dd.line((0, v, 31, v), fill=GLASS_HI)
        elif name == 'ev':
            t = solid(32, 32, CANOPY, 0.04, seed); dd = ImageDraw.Draw(t)
            dd.rectangle((6, 4, 25, 27), fill=STEEL, outline=CANOPY_L); dd.line((15, 4, 15, 27), fill=CANOPY_L)
        elif name == 'void':
            t = solid(32, 32, ROOF, 0.04, seed); dd = ImageDraw.Draw(t)
            for k in range(-32, 32, 8): dd.line((k, 31, k + 31, 0), fill=ROOF_D)
        else:  # wall
            t = solid(32, 32, BRICK, 0.2, seed, BRICK_D)
        out.append(t)
    return out


# ---------------- room layout (data/school_layout.json) ----------------
ANCHOR_POS = {   # wing, side, start, end (meters along the wing axis)
    'centralStair': ('main', 'outer', XE - 2.5, XE + 2.5),
    'ev': ('main', 'outer', EV_X[0], EV_X[1]),
    'staffWC': ('main', 'outer', XE + 2.5, XE + 7.5),
    'eastEnd': ('main', 'outer', L1 - 8.0, L1),
    'westWC': ('west', 'outer', D, D + 8.0),
    'lobby': ('main', 'inner', XE - 2.5, XE + 2.5),
    'mainMidStair': ('main', 'inner', D + MSTAIR[0], D + MSTAIR[1]),
    'mainEndStair': ('main', 'inner', L1 - ESTAIR_W, L1),
    'westMidStair': ('west', 'inner', STAIR_Y0, STAIR_Y1),
}
WING_RANGE = {'main': (D, L1), 'west': (D, D + L2)}
CORR_MID = OUTER_W + CORR_W / 2


def load_layout(path=None):
    return json.loads(Path(path or LAYOUT_PATH).read_text(encoding='utf-8'))


def _band_rect(wing, side, a, b):
    lo, hi = (0.0, OUTER_W) if side == 'outer' else (OUTER_W + CORR_W, D)
    return [a, lo, b, hi] if wing == 'main' else [lo, a, hi, b]


def _door(wing, side, c):
    edge = OUTER_W if side == 'outer' else OUTER_W + CORR_W
    return ([c, edge], [c, CORR_MID]) if wing == 'main' else ([edge, c], [CORR_MID, c])


def _distribute(seq, wing, side, lo, hi, where):
    out, run = [], []
    cursor = [lo]

    def flush(end):
        total = sum(it.get('gap', it.get('span', 1.0)) for it in run)
        if run and end - cursor[0] < total * 0.5 - 1e-6:
            raise ValueError(f'{where}: {end - cursor[0]:.1f} m is too short for {[i.get("name", "gap") for i in run]}')
        pos = cursor[0]
        for it in run:
            ln = (end - cursor[0]) * it.get('gap', it.get('span', 1.0)) / total
            out.append((it, pos, pos + ln)); pos += ln
        run.clear()

    for it in seq:
        anc = it.get('anchor')
        if anc:
            w, sd, a, b = ANCHOR_POS[anc]
            if (w, sd) != (wing, side):
                raise ValueError(f'{where}: anchor {anc} belongs to {w}/{sd}')
            if a < cursor[0] - 1e-6:
                raise ValueError(f'{where}: anchor {anc} is out of order')
            flush(a); out.append((it, a, b)); cursor[0] = b
        else:
            run.append(it)
    flush(hi)
    return out


def plan_floor(layout, f):
    """Place every room of floor f in world meters. Anchored stairs/EV/lobby keep the same coordinates on every floor."""
    fl = next(x for x in layout['floors'] if x['floor'] == f)
    meta = layout['anchors']
    items = []
    west_end = D + L2

    def add(it, wing, side, a, b):
        anc = it.get('anchor')
        rect = _band_rect(wing, side, a, b)
        c = (a + b) / 2
        if 'gap' in it:
            items.append({'id': f'gap-{f}-{wing}-{side}-{len(items)}', 'kind': 'gap', 'wing': wing, 'side': side, 'rect': rect})
            return
        if anc and 'id' not in it:
            m = meta[anc]
            name = m['name'] + ('·출입구' if f == 1 and anc in ('mainMidStair', 'westMidStair') else '')
            e = {'id': f'{m["kind"]}-{anc}', 'name': name, 'kind': m['kind'], 'anchor': anc, 'category': 'service'}
        else:
            e = dict(it)
            e.setdefault('kind', 'restroom' if it.get('category') == 'restroom' else 'room')
        e.update(wing=wing, side=side, rect=rect)
        if e['kind'] == 'void':
            e['rect'] = [0.0, a, D, D + L2]
        else:
            e['door'], e['node'] = _door(wing, side, c)
        items.append(e)

    for side in ('inner', 'outer'):
        lo, hi = WING_RANGE['west']
        if side == 'outer':
            hi = west_end
        for it, a, b in _distribute(fl['west'][side], 'west', side, lo, hi, f'{f}F west {side}'):
            if it.get('kind') == 'void':
                west_end = a
            add(it, 'west', side, a, b)
    for side in ('inner', 'outer'):
        lo, hi = WING_RANGE['main']
        for it, a, b in _distribute(fl['main'][side], 'main', side, lo, hi, f'{f}F main {side}'):
            add(it, 'main', side, a, b)
    x0, x1, y0, y1 = CORNER_STAIR
    items.append({'id': 'stair-cornerStair', 'name': meta['cornerStair']['name'], 'kind': 'stair', 'anchor': 'cornerStair',
                  'category': 'service', 'wing': 'corner', 'side': 'inner', 'rect': [x0, y0, x1, y1],
                  'door': [(x0 + x1) / 2, y0], 'node': [(x0 + x1) / 2, CORR_MID]})
    items.append({'id': f'gap-{f}-corner-n', 'kind': 'gap', 'wing': 'corner', 'side': 'outer', 'rect': [0.0, 0.0, D, OUTER_W]})
    items.append({'id': f'gap-{f}-corner-w', 'kind': 'gap', 'wing': 'corner', 'side': 'outer', 'rect': [0.0, OUTER_W, OUTER_W, D]})
    corridors = [[OUTER_W, OUTER_W, L1, OUTER_W + CORR_W], [OUTER_W, OUTER_W, OUTER_W + CORR_W, west_end]]
    return {'floor': f, 'items': items, 'corridors': corridors, 'westEnd': west_end}


def all_plans(layout):
    return {fl['floor']: plan_floor(layout, fl['floor']) for fl in layout['floors']}


def room_label(e):
    n = e.get('name', '')
    if e.get('category') == 'classroom' and '-' in n:
        g, c = n.split('-', 1)
        return f'{g}학년 {c}반'
    return n


# ---------------- floor plans (top view, no text) ----------------
PLAN_PPM, PLAN_MARGIN = 4, 4.0


def render_floor_plan(plan, ppm=PLAN_PPM):
    M = PLAN_MARGIN
    W, H = int((L1 + 2 * M) * ppm), int((D + L2 + 2 * M) * ppm)
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    X = lambda v: int(round((v + M) * ppm))

    def rect(r, fill, outline=None):
        d.rectangle((X(r[0]), X(r[1]), X(r[2]) - 1, X(r[3]) - 1), fill=fill, outline=outline)

    # outer wall slab (┌)
    for r in ([0, 0, L1, D], [0, D, D, D + L2]):
        d.rectangle((X(r[0]) - 2, X(r[1]) - 2, X(r[2]) + 1, X(r[3]) + 1), fill=BRICK_D)
    for r in plan['corridors']:
        rect(r, PLAN_FLOOR)
    for e in plan['items']:
        r, k = e['rect'], e['kind']
        if k == 'gap':
            rect(r, shade(PLAN_SERVICE, 0.9), BRICK_D)
        elif k == 'void':      # no floor here (arch roof below): hatched roof, clipped to the rect
            tw, th = X(r[2]) - X(r[0]), X(r[3]) - X(r[1])
            hatch = Image.new('RGBA', (tw, th), ROOF + (255,)); hd = ImageDraw.Draw(hatch)
            for t in range(-th, tw, 2 * ppm):
                hd.line((t, th - 1, t + th, 0), fill=ROOF_D)
            im.paste(hatch, (X(r[0]), X(r[1])))
            rect(r, None, BRICK_D)
        elif k == 'stair':
            rect(r, COPING, BRICK_D)
            horiz = e['wing'] == 'west'
            for t in np.arange((r[1] if horiz else r[0]) + 0.8, r[3] if horiz else r[2], 0.8):
                if horiz: d.line((X(r[0]) + 1, X(t), X(r[2]) - 2, X(t)), fill=PLINTH)
                else: d.line((X(t), X(r[1]) + 1, X(t), X(r[3]) - 2), fill=PLINTH)
        elif k == 'ev':
            rect(r, CANOPY, BRICK_D)
            d.rectangle((X(r[0]) + 3, X(r[1]) + 3, X(r[2]) - 4, X(r[3]) - 4), fill=STEEL)
            cx = (X(r[0]) + X(r[2])) // 2
            d.line((cx, X(r[1]) + 3, cx, X(r[3]) - 4), fill=CANOPY_L)
        elif k == 'lobby':
            rect(r, PLAN_LOBBY)
            for t in np.arange(r[0] + 1, r[2], 1.0): d.line((X(t), X(r[1]), X(t), X(r[3]) - 1), fill=shade(PLAN_LOBBY, 0.94))
            for t in np.arange(r[1] + 1, r[3], 1.0): d.line((X(r[0]), X(t), X(r[2]) - 1, X(t)), fill=shade(PLAN_LOBBY, 0.94))
            d.line((X(r[0]), X(r[3]) - 1, X(r[2]) - 1, X(r[3]) - 1), fill=GLASS_D)          # glass entrance doors
        else:
            rect(r, CAT_COLOR.get(e.get('category'), PLAN_SERVICE), BRICK_D)
        if e.get('door') and k != 'lobby':   # door gap toward the corridor + white door leaf
            dx, dy = e['door']; hw = 0.6
            sgn = 1 if e['side'] == 'inner' else -1
            if e['wing'] in ('main', 'corner'):
                y = X(dy) - (1 if sgn > 0 else 0)
                d.line((X(dx - hw), y, X(dx + hw), y), fill=PLAN_FLOOR)
                d.line((X(dx - hw), y + sgn, X(dx - hw), y + sgn * 3), fill=FRAME)
            else:
                x = X(dx) - (1 if sgn > 0 else 0)
                d.line((x, X(dy - hw), x, X(dy + hw)), fill=PLAN_FLOOR)
                d.line((x + sgn, X(dy - hw), x + sgn * 3, X(dy - hw)), fill=FRAME)
    return im


# ---------------- kiosk-plan.json (rooms, doors, corridor graph) ----------------
def _r(v):
    return round(float(v), 3)


def kiosk_plan(layout, plans, footprint=None):
    floors, vertical, stair_floors = {}, [], {}
    for f, plan in plans.items():
        nodes, edges, rooms = {}, [], []

        def node(nid, x, y, kind):
            nodes[nid] = {'id': nid, 'x': _r(x), 'y': _r(y), 'kind': kind}

        main_line = [(CORR_MID, f'{f}:corner')]; west_line = [(CORR_MID, f'{f}:corner')]
        node(f'{f}:corner', CORR_MID, CORR_MID, 'corner')
        node(f'{f}:main-end', L1 - 0.5, CORR_MID, 'end'); main_line.append((L1 - 0.5, f'{f}:main-end'))
        node(f'{f}:west-end', CORR_MID, plan['westEnd'] - 0.5, 'end'); west_line.append((plan['westEnd'] - 0.5, f'{f}:west-end'))
        for e in plan['items']:
            if e['kind'] == 'gap':
                continue
            rc = e['rect']
            entry = {'id': e['id'], 'floor': f, 'name': e.get('name', ''), 'label': room_label(e), 'kind': e['kind'],
                     'category': e.get('category'), 'wing': e['wing'], 'side': e['side'],
                     'polygon': [[_r(rc[0]), _r(rc[1])], [_r(rc[2]), _r(rc[1])], [_r(rc[2]), _r(rc[3])], [_r(rc[0]), _r(rc[3])]]}
            for k in ('aliases', 'name_en', 'description', 'anchor'):
                if k in e: entry[k] = e[k]
            for k, dv in (('visible', True), ('game', True), ('confirmed', True)):
                entry[k] = e.get(k, dv)
            if e.get('door'):
                cn, dn = f'{f}:c:{e["id"]}', f'{f}:{e["id"]}'
                node(cn, *e['node'], 'corridor'); node(dn, *e['door'], e['kind'])
                edges.append([cn, dn, _r(math.dist(e['node'], e['door']))])
                on_main = e['wing'] in ('main', 'corner')
                (main_line if on_main else west_line).append((e['node'][0] if on_main else e['node'][1], cn))
                entry['door'] = [_r(v) for v in e['door']]; entry['node'] = dn
                if e['kind'] in ('stair', 'ev'):
                    stair_floors.setdefault(e['id'], []).append(f)
            rooms.append(entry)
        for line in (main_line, west_line):
            line.sort()
            for (pa, a), (pb, b) in zip(line, line[1:]):
                edges.append([a, b, _r(abs(pb - pa))])
        floors[str(f)] = {'rooms': rooms, 'nodes': list(nodes.values()), 'edges': edges,
                          'image': f'floor-plan-{f}.png', 'image3x': f'floor-plan-{f}@3x.png'}
    for sid, fs in sorted(stair_floors.items()):
        fs = sorted(fs)
        for a, b in zip(fs, fs[1:]):
            if b == a + 1:
                vertical.append({'a': f'{a}:{sid}', 'b': f'{b}:{sid}', 'kind': 'ev' if sid.startswith('ev-') else 'stair',
                                 'cost': 12.0 if sid.startswith('ev-') else 8.0})
    out = {
        'version': 1, 'generator': 'tools/school_art.py (from data/school_layout.json)',
        'units': 'm', 'axes': 'x=동, y=남 (본관 북서쪽 모서리가 원점)',
        'image': {'pxPerM': PLAN_PPM, 'marginM': PLAN_MARGIN, 'scale3x': 3,
                  'toPixel': 'px = (m + marginM) * pxPerM (@3x 는 다시 3배)'},
        'gameTiles': {'tilePerM': 1, 'marginTiles': 4, 'toTile': 'tile = marginTiles + floor(m)'},
        'kiosk': {'floor': 1, 'x': _r(XE), 'y': _r(OUTER_W + CORR_W + 1.0), 'facing': 'north', 'node': '1:lobby-1',
                  'note': '사이니지는 1층 중앙현관에서 중앙계단 쪽. 보는 사람은 북쪽(중앙계단)을 바라봄'},
        'floors': floors, 'vertical': vertical,
    }
    if footprint:
        out['outdoor'] = [dict(p, area=footprint['site'].get(p['site'])) for p in layout.get('outdoor', [])]
    return out


# ---------------- school-footprint.json ----------------
def footprint(metas):
    px0, px1, py1 = XE + 7.0, XE + 18.0, D + 8.0
    return {
        'version': 1, 'generator': 'tools/school_art.py',
        'axes': 'x=동, y=남, z=위 (m). 본관 x∈[0,L1], y∈[0,D] / 서쪽 동 x∈[0,D], y∈[D,D+L2]',
        'projection': {'s': 6, 'kx': KX, 'ky': KY,
                       'formula': 'X = origin.x + s*(x - kx*y), Y = origin.y + s*(ky*y - z)  (각 이미지의 origin, 1배 픽셀)'},
        'displayScale': 2,
        'geometry': {k: _r(v) for k, v in dict(D=D, L1=L1, L2=L2, FH=FH, H4=H4, H3=H3, VAULT=VAULT, XE=XE,
                                                 STAIR_Y0=STAIR_Y0, STAIR_Y1=STAIR_Y1, ARCH_Y0=ARCH_Y0,
                                                 OUTER_W=OUTER_W, CORR_W=CORR_W).items()},
        'images': metas,
        'building': {
            'outline': [[0, 0], [L1, 0], [L1, D], [D, D], [D, D + L2], [0, D + L2]],
            'main': [[0, 0], [L1, 0], [L1, D], [0, D]],
            'west': [[0, D], [D, D], [D, D + L2], [0, D + L2]],
            'archRoof': [[0, ARCH_Y0], [D, ARCH_Y0], [D, D + L2], [0, D + L2]],
            'stairTower': [[10.5, 11.5], [17.8, 19.2]],
            'westStairRecess': [_r(STAIR_Y0), _r(STAIR_Y1)],
        },
        'entrance': {'door': [_r(XE), _r(D)], 'canopy': [[_r(XE - 6.5), _r(D)], [_r(XE + 6.5), _r(D + 4.6)]],
                     'steps': [[_r(XE - 4.2), _r(D + 4.2)], [_r(XE + 4.2), _r(D + 6.0)]],
                     'columns': [[_r(XE - 4.6), _r(D + 3.6), _r(XE - 4.0), _r(D + 4.2)],
                                 [_r(XE + 4.0), _r(D + 3.6), _r(XE + 4.6), _r(D + 4.2)]]},
        'platform': {'top': [[_r(px0), _r(D)], [_r(px1), _r(py1)]], 'steps': [[_r(px0 + 1), _r(py1)], [_r(px0 + 5), _r(py1 + 2.4)]],
                     'height': 1.3},
        'planting': [{'kind': k, 'x': _r(x), 'y': _r(y)} for k, x, y in planting_items()],
        'site': {
            'field': [[_r(FIELD[0]), _r(FIELD[2])], [_r(FIELD[1]), _r(FIELD[3])]],
            'track': {'center': [_r(TRACK_C[0]), _r(TRACK_C[1])], 'halfStraight': TRACK_HALF, 'radius': TRACK_R},
            'platform': [[_r(px0), _r(D)], [_r(px1), _r(py1 + 2.4)]],
            'fountain': [[_r(FOUNTAIN[0]), _r(FOUNTAIN[2])], [_r(FOUNTAIN[1]), _r(FOUNTAIN[3])]],
            'annex': [[_r(ANNEX[0]), _r(ANNEX[2])], [_r(ANNEX[1]), _r(ANNEX[3])]],
            'annexDoor': [_r(ANNEX[0] + 4.25), _r(ANNEX[3])],
            'gateEast': [[_r(GATE_E[0]), _r(GATE_E[1])], [_r(GATE_E[0]), _r(GATE_E[2])]],
            'gateNorth': [[_r(GATE_N[0]), _r(GATE_N[2])], [_r(GATE_N[1]), _r(GATE_N[2])]],
            'entrance': [_r(XE), _r(D + 6.5)],
        },
    }


# ---------------- CLI ----------------
def _save(img, path, written):
    img.save(path, format='PNG')
    written.append(path)


def _save_json(obj, path, written):
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    written.append(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description='서라벌여중 코드 픽셀아트 (학교 외관·폐허·대기화면·층 평면도)')
    ap.add_argument('--out', default=str(ROOT / 'components' / 'rpg_game' / 'assets'))
    ap.add_argument('--only', default='all', choices=['sprite', 'ruin', 'hero', 'props', 'plans', 'all'])
    ap.add_argument('--layout', default=str(LAYOUT_PATH))
    args = ap.parse_args(argv)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    want = lambda k: args.only in (k, 'all')
    written = []
    metas = {'school': dict(file='school.png', **sprite_meta()), 'school-ruin': dict(file='school-ruin.png', **sprite_meta())}
    if want('sprite'):
        _save(render_sprite(), out / 'school.png', written)
    if want('ruin'):
        _save(render_sprite(ruin=True), out / 'school-ruin.png', written)
    if want('hero'):
        _save(render_hero().convert('RGB'), out / 'school-hero.png', written)
    fp = None
    if args.only != 'hero':
        for name, fn in PROPS.items():
            img, origin = fn()
            metas[name] = {'file': f'{name}.png', 'size': list(img.size), 'origin': list(origin)}
            if want('props'):
                _save(img, out / f'{name}.png', written)
        fp = footprint(metas)
        if args.only != 'plans':
            _save_json(fp, out / 'school-footprint.json', written)
    if want('plans'):
        layout = load_layout(args.layout)
        plans = all_plans(layout)
        for f, plan in plans.items():
            im = render_floor_plan(plan)
            _save(im, out / f'floor-plan-{f}.png', written)
            _save(im.resize((im.width * 3, im.height * 3), Image.NEAREST), out / f'floor-plan-{f}@3x.png', written)
        _save_json(kiosk_plan(layout, plans, fp), out / 'kiosk-plan.json', written)
    for p in written:
        print(f'{hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]}  {Path(p).name}')


if __name__ == '__main__':
    main()
