"""Interior pixel art for the exploration game (components/explore), drawn in code from the school photos:
  - corridor: speckled terrazzo floor, white walls with a brown wooden hand rail, lime-green pillars and door frames,
    wooden doors, frosted-glass restroom doors, green notice boards, yellow tactile pads at stairs/EV
  - central entrance (중앙현관): large polished floor tiles, wooden wall panels, glass double doors with a clock,
    signage kiosk, plant, standing banner, calligraphy frame
  - broadcasting room (방송실): dark floor, booth window with an ON AIR light, booth door, console desk with monitors,
    equipment rack, wall panels, olive chairs
Room name signs (teal plates with white text) are drawn by the game engine as text, not here.

  python tools/interior_art.py            (also run by tools/build_explore_data.py)
Writes components/explore/assets/interior-tiles.png (32x32 tiles, used as tile index 100+i) and
interior-props.png (sprite sheet; source rectangles are in PROPS). Deterministic: no fonts, fixed seeds.
"""
import random
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'components' / 'explore' / 'assets'
T = 32
TILE_BASE = 100

# palette (sampled by eye from the photos)
WALL, WALL_L, WALL_S = (238, 237, 231), (246, 245, 240), (214, 211, 202)
RAIL_H, RAIL, RAIL_D = (182, 126, 80), (142, 92, 55), (94, 60, 34)
LIME_H, LIME, LIME_D = (222, 236, 106), (197, 217, 58), (146, 165, 42)
DOOR_H, DOOR, DOOR_D = (170, 116, 76), (140, 92, 58), (100, 64, 40)
TERR = (214, 208, 194)
SPECK = [(92, 88, 82), (60, 58, 56), (150, 120, 96), (246, 244, 238), (128, 132, 128), (170, 150, 120)]
CEIL, CEIL_L = (189, 182, 170), (171, 164, 152)
STEEL, STEEL_D, FROST = (168, 174, 178), (110, 116, 120), (214, 221, 224)
WOOD_PANEL = [(138, 92, 56), (166, 117, 72), (120, 80, 48)]
BOARD, BOARD_F = (47, 107, 79), (190, 195, 199)
TACT = (214, 168, 42)
STUDIO_F, STUDIO_F2 = (62, 57, 53), (52, 48, 45)
SWALL = (232, 230, 223)
INK = (34, 34, 38)


def speckle(d, box, n, rnd, colors=SPECK, size=(1, 1)):
    x0, y0, x1, y1 = box
    for _ in range(n):
        x, y = rnd.randrange(x0, x1), rnd.randrange(y0, y1)
        c = colors[rnd.randrange(len(colors))]
        d.rectangle((x, y, x + rnd.choice(size) - 1, y), fill=c)


def wall_face(d, rnd, x0=0, x1=T - 1):
    d.rectangle((x0, 0, x1, 1), fill=(176, 170, 160))              # ceiling shadow
    d.rectangle((x0, 2, x1, 17), fill=WALL)
    speckle(d, (x0, 2, x1 + 1, 17), 6, rnd, [WALL_S, WALL_L])
    d.rectangle((x0, 18, x1, 18), fill=RAIL_H)                     # wooden hand rail
    d.rectangle((x0, 19, x1, 20), fill=RAIL)
    d.rectangle((x0, 21, x1, 21), fill=RAIL_D)
    d.rectangle((x0, 22, x1, 29), fill=(233, 232, 226))            # lower wall panels
    for y in (25, 28):
        d.line((x0, y, x1, y), fill=WALL_S)
    d.rectangle((x0, 30, x1, 30), fill=(207, 202, 192))
    d.rectangle((x0, 31, x1, 31), fill=(150, 145, 136))


def terrazzo(d, rnd, base=TERR, n=48, seam=True):
    d.rectangle((0, 0, T - 1, T - 1), fill=base)
    speckle(d, (0, 0, T, T), n, rnd, size=(1, 1, 2))
    if seam:
        d.line((0, 0, T - 1, 0), fill=(196, 190, 176)); d.line((0, 0, 0, T - 1), fill=(196, 190, 176))


def lime_post(d, x0, x1, y0=2, y1=31):
    d.rectangle((x0, y0, x1, y1), fill=LIME)
    d.line((x0, y0, x0, y1), fill=LIME_H)
    d.line((x1, y0, x1, y1), fill=LIME_D)


def tiles():
    out = []

    def tile(seed):
        im = Image.new('RGB', (T, T), WALL); return im, ImageDraw.Draw(im), random.Random(seed)

    for v in range(4):                                              # 0-3 terrazzo
        im, d, r = tile(10 + v); terrazzo(d, r); out.append(im)
    im, d, r = tile(20)                                             # 4 lobby floor: big polished tiles
    terrazzo(d, r, base=(226, 220, 207), n=45)
    d.line((0, 0, T - 1, 0), fill=(200, 193, 180)); d.line((0, 0, 0, T - 1), fill=(200, 193, 180))
    for k in range(6):
        d.point((20 + k, 6 + k), fill=(240, 237, 230))
    out.append(im)
    im, d, r = tile(21); wall_face(d, r); out.append(im)            # 5 wall face
    im, d, r = tile(22); wall_face(d, r); lime_post(d, 9, 22)       # 6 lime pillar
    d.rectangle((9, 18, 22, 21), fill=RAIL); d.line((9, 18, 22, 18), fill=RAIL_H); out.append(im)
    im, d, r = tile(23); wall_face(d, r)                            # 7 wooden door in a lime frame
    lime_post(d, 1, 4); lime_post(d, 27, 30); d.rectangle((1, 2, 30, 4), fill=LIME); d.line((1, 2, 30, 2), fill=LIME_H)
    d.rectangle((5, 5, 26, 31), fill=DOOR); d.line((5, 5, 5, 31), fill=DOOR_H); d.line((26, 5, 26, 31), fill=DOOR_D)
    d.rectangle((10, 8, 21, 14), fill=(168, 196, 204)); d.line((10, 8, 21, 8), fill=(214, 232, 236))
    d.rectangle((22, 18, 24, 19), fill=STEEL); out.append(im)
    im, d, r = tile(24); wall_face(d, r)                            # 8 frosted-glass restroom door
    d.rectangle((3, 2, 28, 31), fill=STEEL_D); d.rectangle((5, 4, 26, 31), fill=FROST)
    for y in range(4, 31, 3):
        d.line((5, y, 26, y), fill=(226, 232, 234))
    d.rectangle((21, 12, 22, 24), fill=STEEL); out.append(im)
    im, d, r = tile(25)                                             # 9 room top (seen from above)
    d.rectangle((0, 0, T - 1, T - 1), fill=CEIL); speckle(d, (0, 0, T, T), 25, r, [CEIL_L, (198, 192, 181)])
    d.line((0, 15, T - 1, 15), fill=CEIL_L); d.line((15, 0, 15, T - 1), fill=CEIL_L); out.append(im)
    for flip in (False, True):                                      # 10/11 side walls (corridor east / west of the tile)
        im, d, r = tile(26 + flip)
        d.rectangle((0, 0, T - 1, T - 1), fill=CEIL); speckle(d, (0, 0, 22, T), 14, r, [CEIL_L])
        d.rectangle((22, 0, 28, T - 1), fill=WALL); d.rectangle((29, 0, 30, T - 1), fill=RAIL); d.line((31, 0, 31, T - 1), fill=RAIL_D)
        d.line((22, 0, 22, T - 1), fill=WALL_S)
        out.append(im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im)
    im, d, r = tile(28); terrazzo(d, r)                             # 12 tactile pad
    d.rectangle((8, 8, 23, 23), fill=TACT)
    for y in range(10, 23, 4):
        for x in range(10, 23, 4):
            d.rectangle((x, y, x + 1, y + 1), fill=(236, 198, 84))
    out.append(im)
    for half in (0, 1):                                             # 13/14 green notice board (two tiles)
        im, d, r = tile(29 + half); wall_face(d, r)
        xa, xb = (4, 31) if half == 0 else (0, 27)
        d.rectangle((xa, 4, xb, 17), fill=BOARD_F); d.rectangle((xa + (2 if half == 0 else 0), 6, xb - (0 if half == 0 else 2), 15), fill=BOARD)
        if half == 0:
            d.rectangle((9, 8, 15, 12), fill=(240, 236, 220)); d.rectangle((19, 9, 23, 13), fill=(236, 206, 120))
        else:
            d.rectangle((6, 7, 12, 12), fill=(228, 236, 244)); d.point((9, 7), fill=(200, 60, 50))
        out.append(im)
    for flip in (False, True):                                      # 15/16 wooden wall panels (lobby sides)
        im, d, r = tile(31 + flip)
        for i, x in enumerate(range(0, T, 4)):
            d.rectangle((x, 0, x + 3, T - 1), fill=WOOD_PANEL[i % 2]); d.line((x + 3, 0, x + 3, T - 1), fill=WOOD_PANEL[2])
        d.rectangle((26, 0, 31, T - 1), fill=(190, 140, 92)); d.line((31, 0, 31, T - 1), fill=RAIL_D)
        out.append(im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im)
    im, d, r = tile(33)                                             # 17 studio floor
    d.rectangle((0, 0, T - 1, T - 1), fill=STUDIO_F); speckle(d, (0, 0, T, T), 30, r, [STUDIO_F2, (72, 66, 61)])
    d.line((0, 15, T - 1, 15), fill=STUDIO_F2); d.line((0, 31, T - 1, 31), fill=STUDIO_F2); out.append(im)
    im, d, r = tile(34)                                             # 18 studio wall, upper
    d.rectangle((0, 0, T - 1, 3), fill=(205, 202, 194)); d.rectangle((0, 4, T - 1, T - 1), fill=SWALL)
    speckle(d, (0, 4, T, T), 6, r, [(222, 220, 212)]); out.append(im)
    im, d, r = tile(35)                                             # 19 studio wall, lower (dark wood skirting)
    d.rectangle((0, 0, T - 1, T - 1), fill=SWALL); speckle(d, (0, 0, T, 26), 6, r, [(222, 220, 212)])
    d.rectangle((0, 26, T - 1, 30), fill=(92, 64, 44)); d.line((0, 26, T - 1, 26), fill=(130, 92, 62)); d.line((0, 31, T - 1, 31), fill=(40, 34, 30))
    out.append(im)
    for flip in (False, True):                                      # 20/21 studio side walls
        im, d, r = tile(36 + flip)
        d.rectangle((0, 0, T - 1, T - 1), fill=(40, 36, 34)); d.rectangle((20, 0, 29, T - 1), fill=SWALL)
        d.rectangle((30, 0, 31, T - 1), fill=(92, 64, 44))
        out.append(im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im)
    for frost in (False, True):                                     # 22-25 doors in side walls (west wing)
        for flip in (False, True):
            im, d, r = tile(40 + frost * 2 + flip)
            d.rectangle((0, 0, T - 1, T - 1), fill=CEIL); speckle(d, (0, 0, 20, T), 10, r, [CEIL_L])
            d.rectangle((20, 0, 31, T - 1), fill=WALL)
            if frost:
                d.rectangle((22, 2, 31, 29), fill=STEEL_D); d.rectangle((24, 4, 31, 27), fill=FROST)
            else:
                d.rectangle((21, 1, 31, 30), fill=LIME); d.line((21, 1, 21, 30), fill=LIME_D)
                d.rectangle((24, 4, 31, 27), fill=DOOR); d.line((24, 4, 24, 27), fill=DOOR_D)
            out.append(im.transpose(Image.FLIP_LEFT_RIGHT) if flip else im)
    im, d, r = tile(50); wall_face(d, r)                            # 26 elevator: steel doors in a steel frame
    d.rectangle((0, 2, 31, 31), fill=STEEL_D); d.rectangle((2, 4, 29, 31), fill=STEEL)
    d.line((15, 4, 15, 31), fill=STEEL_D); d.line((16, 4, 16, 31), fill=(196, 202, 206))
    for x in (6, 24):
        d.line((x, 6, x, 29), fill=(186, 192, 196))
    out.append(im)
    im, d, r = tile(51)                                             # 27 elevator shaft top
    d.rectangle((0, 0, T - 1, T - 1), fill=(120, 124, 128)); d.rectangle((2, 2, 29, 29), fill=(138, 142, 146))
    d.line((2, 2, 29, 29), fill=(120, 124, 128)); d.line((29, 2, 2, 29), fill=(120, 124, 128))
    out.append(im)
    im, d, r = tile(52)                                             # 28 window wall (corridor east of it): outside view + glass
    d.rectangle((0, 0, 19, T - 1), fill=(150, 186, 120)); speckle(d, (0, 0, 20, T), 30, r, [(120, 160, 96), (176, 206, 140), (104, 140, 84)])
    d.ellipse((2, 4, 13, 15), fill=(96, 146, 80)); d.ellipse((5, 18, 17, 29), fill=(110, 158, 88))         # trees outside
    d.rectangle((20, 0, 31, T - 1), fill=(236, 236, 230))                                                   # frame
    for y0 in (2, 18):
        d.rectangle((22, y0, 29, y0 + 12), fill=(176, 208, 222)); d.line((23, y0 + 1, 23, y0 + 11), fill=(222, 238, 244))
    d.line((31, 0, 31, T - 1), fill=(150, 145, 136))
    out.append(im)
    sheet = Image.new('RGB', (T * len(out), T))
    for i, im in enumerate(out):
        sheet.paste(im, (i * T, 0))
    return sheet


TILE = {'terrazzo': 0, 'lobby': 4, 'wall': 5, 'pillar': 6, 'door': 7, 'frost': 8, 'top': 9, 'sideL': 10, 'sideR': 11,
        'tactile': 12, 'boardL': 13, 'boardR': 14, 'panelL': 15, 'panelR': 16, 'studioFloor': 17, 'studioWallU': 18,
        'studioWallD': 19, 'studioSideL': 20, 'studioSideR': 21, 'sideDoorL': 22, 'sideDoorR': 23,
        'sideFrostL': 24, 'sideFrostR': 25, 'evDoor': 26, 'evTop': 27, 'windowL': 28}

GLYPH = {'O': ['0110', '1001', '1001', '1001', '0110'], 'N': ['1001', '1101', '1011', '1001', '1001'],
         'A': ['0110', '1001', '1111', '1001', '1001'], 'I': ['111', '010', '010', '010', '111'],
         'R': ['1110', '1001', '1110', '1010', '1001'], ' ': ['00', '00', '00', '00', '00']}


def pixel_text(d, x, y, text, color):
    for ch in text:
        g = GLYPH[ch]
        for j, row in enumerate(g):
            for i, b in enumerate(row):
                if b == '1':
                    d.point((x + i, y + j), fill=color)
        x += len(g[0]) + 1


def props():
    """Return (sheet, rects). Each prop is drawn on its own transparent canvas, then packed in a row."""
    items = []

    def canvas(name, w, h):
        im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); items.append((name, im)); return ImageDraw.Draw(im)

    # --- central entrance: glass front, 6 tiles wide ---
    d = canvas('glassFront', 192, 48)
    d.rectangle((0, 0, 191, 5), fill=(166, 117, 72)); d.line((0, 5, 191, 5), fill=RAIL_D)
    for gx0 in (4, 104):                                            # two groups of 4 glass leaves
        for k in range(4):
            x0 = gx0 + k * 21
            d.rectangle((x0, 6, x0 + 20, 47), fill=STEEL)
            d.rectangle((x0 + 2, 8, x0 + 18, 47), fill=(232, 222, 196))             # sunlit playground
            d.rectangle((x0 + 2, 8, x0 + 18, 13), fill=(236, 230, 214))             # canopy
            d.rectangle((x0 + 2, 14, x0 + 18, 19), fill=(176, 96, 74))              # brick buildings over there
            d.rectangle((x0 + 2, 20, x0 + 18, 22), fill=(120, 150, 110))            # trees
            d.line((x0 + 2, 23, x0 + 18, 23), fill=(200, 120, 110))                 # poster fence
            d.line((x0 + 3, 9, x0 + 9, 40), fill=(246, 242, 232))                   # glare
            d.ellipse((x0 + (14 if k % 2 == 0 else 3), 28, x0 + (17 if k % 2 == 0 else 6), 31), fill=(150, 156, 160))
        d.ellipse((gx0 + 30, 15, gx0 + 40, 23), fill=(232, 196, 60))                # ginkgo
    d.rectangle((92, 6, 103, 47), fill=(178, 128, 82)); d.line((92, 6, 92, 47), fill=RAIL_D)  # wooden mullion
    d.ellipse((93, 10, 102, 19), fill=(64, 52, 40)); d.ellipse((94, 11, 101, 18), fill=(250, 248, 242))
    d.line((97, 14, 97, 12), fill=INK); d.line((97, 14, 99, 15), fill=INK)
    d.rectangle((94, 24, 101, 36), fill=(70, 70, 72))                                # wall-mounted board
    d = canvas('kiosk', 30, 46)                                     # the signage kiosk on its white stand
    d.rectangle((1, 0, 28, 19), fill=(205, 206, 204)); d.rectangle((3, 2, 26, 17), fill=(40, 44, 48))
    d.rectangle((5, 4, 24, 15), fill=(243, 236, 222)); d.rectangle((7, 6, 22, 7), fill=(132, 60, 50)); d.rectangle((7, 6, 8, 14), fill=(132, 60, 50))
    d.rectangle((10, 9, 13, 11), fill=(192, 210, 230)); d.rectangle((15, 9, 18, 11), fill=(204, 224, 186))
    d.rectangle((12, 20, 17, 40), fill=(236, 236, 232)); d.line((17, 20, 17, 40), fill=(200, 200, 196))
    d.rectangle((3, 40, 26, 45), fill=(240, 240, 236)); d.line((3, 45, 26, 45), fill=(170, 170, 166))
    d = canvas('plant', 22, 42)
    d.rectangle((6, 30, 15, 41), fill=(40, 40, 42)); d.line((6, 30, 15, 30), fill=(80, 80, 82))
    r = random.Random(7)
    for _ in range(40):
        x, y = r.randrange(1, 21), r.randrange(0, 30)
        d.ellipse((x - 2, y - 1, x + 2, y + 1), fill=r.choice([(70, 130, 60), (96, 160, 70), (50, 104, 52)]))
    d.line((11, 12, 11, 30), fill=(90, 70, 50))
    d = canvas('xbanner', 20, 44)
    d.line((2, 43, 10, 30), fill=STEEL_D); d.line((18, 43, 10, 30), fill=STEEL_D)
    d.rectangle((2, 0, 17, 38), fill=(250, 246, 226)); d.rectangle((2, 0, 17, 6), fill=(236, 214, 120))
    d.rectangle((5, 9, 14, 10), fill=(220, 120, 150)); d.ellipse((6, 13, 13, 22), fill=(240, 200, 170))
    for y in range(25, 36, 3):
        d.line((5, y, 14, y), fill=(160, 150, 140))
    d = canvas('calligraphy', 14, 44)                               # 힘써 배우고 바르게 행하자 (strokes only, no font)
    d.rectangle((0, 0, 13, 43), fill=(150, 104, 64)); d.rectangle((2, 2, 11, 41), fill=(246, 244, 236))
    r = random.Random(11)
    for col in (4, 8):
        for y in range(4, 39, 5):
            d.line((col + r.randrange(-1, 1), y, col + r.randrange(0, 2), y + 3), fill=INK)
            d.point((col + 1, y + 1), fill=INK)

    # --- broadcasting room ---
    d = canvas('boothWindow', 124, 44)
    d.rounded_rectangle((0, 0, 123, 43), radius=8, fill=(150, 104, 64))
    d.rounded_rectangle((4, 4, 119, 43), radius=7, fill=(30, 28, 30))
    d.rectangle((72, 8, 112, 30), fill=(70, 66, 64)); d.rectangle((74, 10, 92, 20), fill=(196, 200, 196)); d.rectangle((95, 10, 110, 20), fill=(186, 192, 190))
    d.rectangle((74, 22, 110, 28), fill=(54, 50, 48)); d.rectangle((96, 21, 100, 23), fill=(200, 210, 80))
    d.line((14, 6, 30, 38), fill=(66, 62, 64)); d.line((18, 6, 34, 38), fill=(52, 48, 50))
    d.rectangle((40, 30, 44, 38), fill=(20, 20, 22)); d.rectangle((58, 30, 62, 38), fill=(20, 20, 22))
    d = canvas('onAir', 38, 11)
    d.rectangle((0, 0, 37, 10), fill=(40, 40, 42)); d.rectangle((1, 1, 30, 9), fill=(214, 46, 44))
    pixel_text(d, 3, 3, 'ON AIR', (255, 255, 255))
    d.rectangle((31, 1, 36, 9), fill=(236, 240, 248))
    d = canvas('boothDoor', 34, 54)
    d.rectangle((0, 0, 33, 53), fill=(150, 104, 64)); d.rectangle((3, 3, 30, 53), fill=(30, 28, 30))
    d.rectangle((22, 6, 29, 53), fill=(150, 150, 146)); d.line((22, 6, 22, 53), fill=(100, 100, 98))
    d.rectangle((24, 26, 25, 34), fill=(60, 60, 62))
    d.rectangle((6, 18, 10, 30), fill=(200, 200, 196)); d.point((8, 22), fill=(200, 40, 40)); d.point((8, 25), fill=(40, 60, 160))   # flag in the booth
    d = canvas('wallPanels', 66, 40)
    for x0 in (0, 34):
        d.rectangle((x0, 0, x0 + 31, 39), fill=(176, 176, 172)); d.rectangle((x0 + 2, 2, x0 + 29, 37), fill=(56, 56, 58))
        d.rectangle((x0 + 6, 16, x0 + 7, 24), fill=(150, 150, 150))
    d.rectangle((6, 6, 20, 9), fill=(230, 230, 226)); d.rectangle((14, 18, 24, 22), fill=(236, 236, 232))
    for y in (6, 9, 12):
        d.line((42, y, 46, y), fill=(120, 120, 120)); d.line((52, y, 56, y), fill=(120, 120, 120))
    d = canvas('console', 196, 64)                                  # desk seen from the room (3/4 view)
    d.rectangle((0, 22, 195, 45), fill=(94, 96, 100)); d.line((0, 22, 195, 22), fill=(128, 130, 134))
    d.rectangle((0, 46, 195, 63), fill=(44, 46, 48)); d.line((0, 46, 195, 46), fill=(30, 30, 32))
    for x0 in (6, 70, 116):                                         # monitors
        d.rectangle((x0, 0, x0 + 54, 22), fill=(18, 18, 20)); d.rectangle((x0 + 2, 2, x0 + 52, 19), fill=(28, 30, 34))
        d.line((x0 + 4, 4, x0 + 20, 4), fill=(44, 48, 56)); d.rectangle((x0 + 25, 22, x0 + 29, 26), fill=(30, 30, 32))
    d.rectangle((100, 28, 150, 37), fill=(30, 30, 32))                # video switcher
    for i in range(12):
        d.rectangle((103 + i * 4, 30, 104 + i * 4, 31), fill=[(230, 230, 230), (220, 60, 60), (240, 200, 60)][i % 3])
        d.rectangle((103 + i * 4, 34, 104 + i * 4, 35), fill=(200, 200, 200))
    d.rectangle((152, 29, 156, 37), fill=(200, 200, 200))
    d.rectangle((30, 30, 60, 35), fill=(26, 26, 28))                  # keyboard
    d.polygon([(14, 26), (30, 25), (32, 31), (16, 33)], fill=(236, 236, 232))       # papers
    d.rectangle((70, 27, 76, 31), fill=(140, 200, 230)); d.rectangle((90, 33, 95, 37), fill=(140, 200, 230)); d.rectangle((160, 26, 166, 30), fill=(140, 200, 230))
    d.polygon([(66, 38), (84, 36), (88, 58), (70, 60)], fill=(236, 170, 120))       # orange sheet over the edge
    d.line((98, 18, 104, 30), fill=(30, 30, 32)); d.ellipse((96, 15, 100, 19), fill=(50, 50, 52))   # mic arm
    d = canvas('rack', 30, 64)
    d.rectangle((0, 0, 29, 63), fill=(28, 28, 30)); d.line((0, 0, 29, 0), fill=(60, 60, 62))
    for y in range(6, 40, 6):
        d.line((3, y, 26, y), fill=(50, 50, 52))
        for x in (5, 8, 11):
            d.point((x, y - 2), fill=(120, 230, 90))
    d.rectangle((6, 42, 18, 52), fill=(232, 222, 150))
    d = canvas('chair', 24, 30)
    d.rounded_rectangle((2, 0, 21, 16), radius=5, fill=(150, 160, 50)); d.rounded_rectangle((0, 14, 23, 23), radius=4, fill=(170, 180, 60))
    d.line((4, 3, 4, 13), fill=(176, 186, 74)); d.rectangle((10, 24, 13, 27), fill=(40, 40, 42)); d.line((4, 29, 19, 29), fill=(40, 40, 42))

    w = sum(im.width for _, im in items) + 2 * len(items); h = max(im.height for _, im in items)
    sheet = Image.new('RGBA', (w, h), (0, 0, 0, 0)); rects = {}; x = 0
    for name, im in items:
        sheet.paste(im, (x, 0)); rects[name] = [x, 0, im.width, im.height]; x += im.width + 2
    return sheet, rects


def build(out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    tiles().save(out / 'interior-tiles.png', optimize=False)
    sheet, rects = props()
    sheet.save(out / 'interior-props.png', optimize=False)
    return rects


PROPS = None


def prop_rects():
    global PROPS
    if PROPS is None:
        PROPS = props()[1]
    return PROPS


if __name__ == '__main__':
    r = build()
    print('interior-tiles.png', len(TILE), 'named tiles;', 'interior-props.png', ', '.join(r))
