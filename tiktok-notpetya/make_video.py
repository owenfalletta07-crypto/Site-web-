#!/usr/bin/env python3
"""TikTok motion design : NotPetya (2017).

Tout est dessiné en code (PIL) et la musique est synthétisée (numpy).
Usage :
    python3 make_video.py check   # images de contrôle + vérif débordements
    python3 make_video.py render  # rendu MP4 final
"""
import math, os, random, re, subprocess, sys, wave
from multiprocessing import Pool

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")
FONT_ANTON = os.path.join(HERE, "assets", "Anton-Regular.ttf")
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, H, FPS, S = 1080, 1920, 30, 2          # S = suréchantillonnage (anti-crénelage)
SAFE = dict(x0=40, x1=W - 150, y0=150, y1=H - 450)   # zone sûre TikTok
INK = "#1B1B2F"
YELLOW = "#FFE600"
TRANS = 0.22                               # durée du volet de transition (s)

# ---------------------------------------------------------------- script ----
# '*' = mot-clé en jaune, '_' = espace insécable (mots groupés)
SCENES = [
    dict(dur=3.0, txt="*10_MILLIARDS de dégâts… à cause d'une *mise_à_jour."),
    dict(dur=2.5, txt="27 juin 2017, en *Ukraine."),
    dict(dur=2.7, txt="Un logiciel de *compta très utilisé se met à jour."),
    dict(dur=2.8, txt="Mais des hackers y ont caché un virus : *NotPetya."),
    dict(dur=2.8, txt="Il réclame une rançon… mais il *détruit tout."),
    dict(dur=2.7, txt="Le jour même, il frappe dans le *monde entier."),
    dict(dur=2.9, txt="Le géant Maersk : *76 terminaux portuaires à l'arrêt."),
    dict(dur=2.8, txt="*45_000 PC et *4_000 serveurs à réinstaller."),
    dict(dur=2.7, txt="Seul survivant : un serveur en *Afrique."),
    dict(dur=2.7, txt="Sauvé par… une *coupure de courant_!"),
    dict(dur=2.8, txt="Sa copie part en *avion pour tout reconstruire."),
    dict(dur=2.9, txt="Facture pour Maersk : jusqu'à *300_millions de dollars."),
    dict(dur=2.9, txt="En 2018, Washington et Londres accusent l'armée *russe."),
    dict(dur=2.5, txt="Moscou, elle, *dément."),
    dict(dur=3.0, txt="Et *toi, tu cliques encore sur «_mettre à jour_»_?"),
]
STARTS = []
_acc = 0.0
for _s in SCENES:
    STARTS.append(_acc)
    _acc += _s["dur"]
TOTAL = _acc
NFRAMES = int(round(TOTAL * FPS))

# --------------------------------------------------------------- helpers ----
def clamp(v, a=0.0, b=1.0):
    return max(a, min(b, v))

def prog(t, a, b):
    return clamp((t - a) / (b - a))

def eo(t):                      # ease-out cubic
    t = clamp(t)
    return 1 - (1 - t) ** 3

def eio(t):
    t = clamp(t)
    return 4 * t ** 3 if t < .5 else 1 - (-2 * t + 2) ** 3 / 2

def eob(t):                     # ease-out back (rebond)
    t = clamp(t)
    c1 = 1.70158; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def lerp(a, b, t):
    return a + (b - a) * t

def rot(pts, cx, cy, ang):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in pts]

def mix(c1, c2, t):
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(int(lerp(a[i], b[i], clamp(t))) for i in range(3))

def fmt_int(n):
    return f"{int(n):,}".replace(",", " ")

_FONTS = {}
def font(name, size):
    key = (name, int(size))
    if key not in _FONTS:
        _FONTS[key] = ImageFont.truetype(FONT_ANTON if name == "anton" else FONT_BOLD, max(4, int(size)))
    return _FONTS[key]


class Canvas:
    def __init__(self, bg):
        self.im = Image.new("RGB", (W * S, H * S), bg)
        self.d = ImageDraw.Draw(self.im)
        self.boxes = []          # (kind, label, (x0,y0,x1,y1)) pour le contrôle

    def reg(self, kind, label, box):
        self.boxes.append((kind, label, tuple(box)))

    # formes ------------------------------------------------------------
    def rect(self, x0, y0, x1, y1, fill=None, outline=INK, w=5, r=0):
        x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1)
        if x1 - x0 < 1 or y1 - y0 < 1:
            return
        r = min(r, (x1 - x0) / 2, (y1 - y0) / 2)
        self.d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=r * S, fill=fill,
                                 outline=outline if w else None, width=int(w * S))

    def circle(self, x, y, r, fill=None, outline=INK, w=5):
        if r <= 0:
            return
        self.d.ellipse([(x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S], fill=fill,
                       outline=outline if w else None, width=int(w * S))

    def ellipse(self, x0, y0, x1, y1, fill=None, outline=INK, w=5):
        self.d.ellipse([min(x0, x1) * S, min(y0, y1) * S, max(x0, x1) * S, max(y0, y1) * S],
                       fill=fill, outline=outline if w else None, width=int(w * S))

    def poly(self, pts, fill=None, outline=INK, w=5):
        p = [(x * S, y * S) for x, y in pts]
        self.d.polygon(p, fill=fill)
        if w and outline:
            self.d.line(p + [p[0]], fill=outline, width=int(w * S), joint="curve")

    def line(self, pts, fill=INK, w=8, cap=True):
        p = [(x * S, y * S) for x, y in pts]
        self.d.line(p, fill=fill, width=int(w * S), joint="curve")
        if cap:
            for x, y in (pts[0], pts[-1]):
                self.d.ellipse([(x - w / 2) * S, (y - w / 2) * S, (x + w / 2) * S, (y + w / 2) * S], fill=fill)

    def arc(self, x0, y0, x1, y1, a0, a1, fill=INK, w=6):
        self.d.arc([x0 * S, y0 * S, x1 * S, y1 * S], a0, a1, fill=fill, width=int(w * S))

    def chord(self, x0, y0, x1, y1, a0, a1, fill, outline=None, w=0):
        self.d.chord([x0 * S, y0 * S, x1 * S, y1 * S], a0, a1, fill=fill,
                     outline=outline, width=int(w * S))

    def text(self, x, y, s, size, fill="white", fname="anton", anchor="mm", stroke=0,
             stroke_fill=INK, maxw=None, kind="text", reg=True):
        size = int(size)
        f = font(fname, size)
        if maxw:
            while size > 10:
                f = font(fname, size)
                bb = self.d.textbbox((0, 0), s, font=f, stroke_width=int(stroke))
                if bb[2] - bb[0] <= maxw:
                    break
                size -= 2
            f = font(fname, size)
        f2 = font(fname, size * S)
        self.d.text((x * S, y * S), s, font=f2, fill=fill, anchor=anchor,
                    stroke_width=int(stroke * S), stroke_fill=stroke_fill)
        if reg:
            bb = self.d.textbbox((x * S, y * S), s, font=f2, anchor=anchor, stroke_width=int(stroke * S))
            self.reg(kind, s, [v / S for v in bb])
        return size

    def final(self):
        return self.im.reduce(S)


# ------------------------------------------------------------ personnages ----
ARM = {
    "down": (-18, 80), "up": (-40, -95), "out": (-85, -15), "head": (-8, -128),
    "hip": (-40, 45), "point": (-115, -45), "front": (40, 40), "wave_up": (-55, -90),
}


def face(c, hx, hy, r, expr, t=0.0, look=(0, 0), skin="#FFD6A5"):
    ex = r * 0.34
    ey = hy - r * 0.05
    lx, ly = look
    blink = (t % 2.7) < 0.09 and expr in ("happy", "worried", "smug")
    if expr in ("happy", "worried", "angry", "sad", "smug"):
        for sd in (-1, 1):
            x = hx + sd * ex
            if blink:
                c.line([(x - r * .16, ey), (x + r * .16, ey)], w=r * .07)
                continue
            c.circle(x, ey, r * .2, fill="white", w=r * .05)
            c.circle(x + lx * r * .07, ey + ly * r * .07, r * .1, fill=INK, w=0)
            c.circle(x + lx * r * .07 + r * .03, ey + ly * r * .07 - r * .04, r * .03, fill="white", w=0)
            if expr == "smug":
                c.chord(x - r * .22, ey - r * .22, x + r * .22, ey + r * .22, 180, 360, fill=skin)
                c.line([(x - r * .22, ey), (x + r * .22, ey)], w=r * .06)
    if expr == "happy":
        c.chord(hx - r * .38, hy + r * .0, hx + r * .38, hy + r * .58, 10, 170, fill="#7A1F2B", outline=INK, w=r * .05)
        c.circle(hx - r * .6, hy + r * .25, r * .12, fill="#FF8FA3", w=0)
        c.circle(hx + r * .6, hy + r * .25, r * .12, fill="#FF8FA3", w=0)
    elif expr == "smug":
        c.arc(hx - r * .2, hy + r * .1, hx + r * .45, hy + r * .45, 20, 150, w=r * .07)
    elif expr == "worried":
        for sd in (-1, 1):
            c.line([(hx + sd * ex - r * .18, ey - r * .32 + (r * .06 if sd < 0 else -r * .06) * -1),
                    (hx + sd * ex + r * .18, ey - r * .32 - (r * .06 if sd < 0 else -r * .06) * -1)], w=r * .07)
        pts = [(hx - r * .3 + i * r * .1, hy + r * .38 + (r * .05 if i % 2 else -r * .05)) for i in range(7)]
        c.line(pts, w=r * .07)
    elif expr == "angry":
        for sd in (-1, 1):
            c.line([(hx + sd * (ex + r * .2), ey - r * .38), (hx + sd * (ex - r * .2), ey - r * .2)], w=r * .1)
        c.arc(hx - r * .3, hy + r * .35, hx + r * .3, hy + r * .75, 200, 340, w=r * .08)
    elif expr == "sad":
        for sd in (-1, 1):
            c.line([(hx + sd * (ex - r * .2), ey - r * .38), (hx + sd * (ex + r * .2), ey - r * .22)], w=r * .08)
        c.arc(hx - r * .28, hy + r * .38, hx + r * .28, hy + r * .78, 200, 340, w=r * .08)
        ty = ey + r * .25 + ((t * 1.6) % 1) * r * .7
        tear(c, hx - ex, ty, r * .09)
    elif expr in ("shock", "panic"):
        for sd in (-1, 1):
            x = hx + sd * ex
            c.circle(x, ey, r * .27, fill="white", w=r * .05)
            c.circle(x + lx * r * .05, ey + ly * r * .05, r * .08, fill=INK, w=0)
            c.arc(x - r * .22, ey - r * .62, x + r * .22, ey - r * .3, 200, 340, w=r * .08)
        c.ellipse(hx - r * .16, hy + r * .3, hx + r * .16, hy + r * .72, fill="#7A1F2B", w=r * .05)
        if expr == "panic":
            for sd in (-1, 1):
                k = (t * 2 + (0.5 if sd > 0 else 0)) % 1
                tear(c, hx + sd * r * 1.08, hy - r * .4 + k * r * .5, r * .12)
    elif expr == "evil":
        for sd in (-1, 1):
            x = hx + sd * ex
            c.chord(x - r * .22, ey - r * .18, x + r * .22, ey + r * .22, 0, 180, fill="#FFE600", outline=INK, w=r * .04)
            c.line([(x - sd * r * .26, ey - r * .3), (x + sd * r * .24, ey - r * .1)], w=r * .09)
        c.chord(hx - r * .45, hy + r * .05, hx + r * .45, hy + r * .6, 0, 180, fill="white", outline=INK, w=r * .05)
        for i in range(1, 5):
            xx = hx - r * .45 + i * r * .18
            c.line([(xx, hy + r * .33), (xx, hy + r * .55)], w=r * .03, cap=False)
    elif expr == "dizzy":
        for sd in (-1, 1):
            x = hx + sd * ex
            for k in range(3):
                rr = r * (.08 + k * .07)
                a0 = (t * 600 + k * 60) % 360
                c.arc(x - rr, ey - rr, x + rr, ey + rr, a0, a0 + 250, w=r * .05)
        pts = [(hx - r * .3 + i * r * .1, hy + r * .42 + (r * .06 if i % 2 else -r * .06)) for i in range(7)]
        c.line(pts, w=r * .07)
    elif expr == "sleep":
        for sd in (-1, 1):
            x = hx + sd * ex
            c.arc(x - r * .18, ey - r * .15, x + r * .18, ey + r * .15, 20, 160, w=r * .07)
        c.circle(hx, hy + r * .45, r * .08, fill="#7A1F2B", w=r * .04)


def tear(c, x, y, r):
    c.poly([(x, y - r * 2.2), (x + r, y), (x - r, y)], fill="#4CC9F0", w=0)
    c.circle(x, y, r, fill="#4CC9F0", w=0)


def person(c, x, y, s=1.0, shirt="#E63946", pants="#1D3557", skin="#FFD6A5", hair="#3D2C2E",
           expr="happy", la="down", ra="down", walk=0.0, glasses=False, tie=None, hat=None,
           headdx=0.0, headdy=0.0, t=0.0, look=(0, 0), label="perso"):
    hip = y - 80 * s
    sh_y = y - 175 * s
    # jambes
    sw = math.sin(walk) * 22 * s
    for sd, k in ((-1, 1), (1, -1)):
        fx = x + sd * 24 * s + sw * k
        c.line([(x + sd * 18 * s, hip), (fx, y - 6 * s)], fill=INK, w=11 * s)
        c.ellipse(fx - 18 * s + (6 * s * sd), y - 12 * s, fx + 18 * s + (6 * s * sd), y + 6 * s, fill=INK, w=0)
    # corps
    c.rect(x - 46 * s, y - 195 * s, x + 46 * s, hip + 4 * s, fill=shirt, w=5 * s, r=30 * s)
    c.rect(x - 46 * s, hip - 22 * s, x + 46 * s, hip + 6 * s, fill=pants, w=5 * s, r=8 * s)
    if tie:
        c.poly([(x, y - 190 * s), (x + 12 * s, y - 150 * s), (x, y - 110 * s), (x - 12 * s, y - 150 * s)], fill=tie, w=3 * s)
    # bras
    hands = []
    for sd, spec in ((-1, la), (1, ra)):
        if isinstance(spec, str):          # préréglages : symétriques
            dx, dy = ARM[spec]
            if sd > 0:
                dx = -dx
        else:                              # tuple : décalage absolu
            dx, dy = spec
        shx = x + sd * 40 * s
        hxp, hyp = shx + dx * s, sh_y + dy * s
        c.line([(shx, sh_y), (hxp, hyp)], fill=INK, w=10 * s)
        hands.append((hxp, hyp))
    for hxp, hyp in hands:
        c.circle(hxp, hyp, 13 * s, fill=skin, w=4 * s)
    # tête
    r = 75 * s
    hx, hy = x + headdx * s, y - 265 * s + headdy * s
    if hair:
        c.circle(hx, hy - 8 * s, r + 4 * s, fill=hair, w=5 * s)
    c.circle(hx, hy, r, fill=skin, w=5 * s)
    if hair:
        c.chord(hx - r, hy - r - 6 * s, hx + r, hy + r * .4, 190, 350, fill=hair)
    face(c, hx, hy, r, expr, t, look, skin)
    if glasses:
        for sd in (-1, 1):
            c.circle(hx + sd * r * .34, hy - r * .05, r * .26, fill=None, w=4 * s)
        c.line([(hx - r * .1, hy - r * .08), (hx + r * .1, hy - r * .08)], w=4 * s)
    if hat == "helmet":
        c.chord(hx - r * 1.05, hy - r * 1.15, hx + r * 1.05, hy + r * .5, 180, 360, fill="#FFB703", outline=INK, w=5 * s)
        c.rect(hx - r * 1.2, hy - r * .4, hx + r * 1.2, hy - r * .28, fill="#FFB703", w=4 * s, r=5)
    xs = [hx - r, hx + r] + [p[0] - 13 * s for p in hands] + [p[0] + 13 * s for p in hands]
    ys = [hy - r - 10 * s, y + 6 * s] + [p[1] - 13 * s for p in hands]
    c.reg("obj", label, (min(xs), min(ys), max(xs), max(ys)))


def server_buddy(c, x, y, s=1.0, expr="happy", t=0.0, color="#ADB5BD", label="serveur"):
    """Petit serveur mignon (personnage original). (x,y) = bas-centre."""
    w2, h = 70 * s, 190 * s
    c.rect(x - w2, y - h, x + w2, y, fill=color, w=5 * s, r=16 * s)
    for i in range(3):
        yy = y - h + 22 * s + i * 26 * s
        c.rect(x - w2 + 16 * s, yy, x + w2 - 16 * s, yy + 14 * s, fill="#6C757D", w=3 * s, r=4 * s)
        on = expr != "sleep" and int(t * 6 + i) % 2 == 0
        c.circle(x + w2 - 26 * s, yy + 7 * s, 4 * s, fill="#2EE59D" if on else "#495057", w=0)
    face(c, x, y - 55 * s, 48 * s, expr, t, skin=color)
    c.reg("obj", label, (x - w2, y - h, x + w2, y))


def bubble(c, x0, y0, x1, y1, tail, txt, size=60, fill="white", tc=INK, label=None):
    c.rect(x0, y0, x1, y1, fill=fill, w=6, r=34)
    tx, ty = tail
    mx = clamp(tx, x0 + 60, x1 - 60)
    by = y1 if ty > y1 else y0
    c.poly([(mx - 30, by), (mx + 30, by), (tx, ty)], fill=fill, w=0)
    c.line([(mx - 30, by + (3 if by == y1 else -3)), (tx, ty), (mx + 30, by + (3 if by == y1 else -3))], w=6)
    c.text((x0 + x1) / 2, (y0 + y1) / 2, txt, size, fill=tc, maxw=(x1 - x0) - 50)


def floor(c, y, col):
    c.rect(-10, y, W + 10, H + 10, fill=col, w=0)
    c.line([(-10, y), (W + 10, y)], w=6, cap=False)


def star(c, x, y, r1, r2, n, fill, ang=0.0, w=4):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = ang + i * math.pi / n - math.pi / 2
        pts.append((x + r * math.cos(a), y + r * math.sin(a)))
    c.poly(pts, fill=fill, w=w)


def bill(c, x, y, ang, s=1.0):
    w2, h2 = 70 * s, 34 * s
    pts = rot([(x - w2, y - h2), (x + w2, y - h2), (x + w2, y + h2), (x - w2, y + h2)], x, y, ang)
    c.poly(pts, fill="#8BD17C", w=4 * s)
    c.circle(x, y, 18 * s, fill="#5CA94F", w=3 * s)
    c.text(x, y, "$", 26 * s, fill=INK, fname="bold", reg=False)


def smoke(c, x, y, k):
    for i, (dx, dy) in enumerate(((0, 0), (-22, -14), (20, -18), (0, -34))):
        c.circle(x + dx * (1 + k), y + dy * (1 + k) - k * 60, (16 + i * 3) * (1 - k * .5) * (0.6 + k), fill="#CED4DA", w=3)


def virus(c, x, y, r, t, label=True, expr="angry"):
    n = 10
    for i in range(n):
        a = i * 2 * math.pi / n + t * 1.5
        c.line([(x + math.cos(a) * r * .8, y + math.sin(a) * r * .8),
                (x + math.cos(a) * r * 1.3, y + math.sin(a) * r * 1.3)], fill="#2D6A4F", w=r * .16)
        c.circle(x + math.cos(a) * r * 1.35, y + math.sin(a) * r * 1.35, r * .14, fill="#95D5B2", w=3)
    c.circle(x, y, r, fill="#52B788", w=5)
    face(c, x, y, r, expr, t, skin="#52B788")
    c.reg("obj", "virus", (x - r * 1.5, y - r * 1.5, x + r * 1.5, y + r * 1.5))


# ----------------------------------------------------------------- scènes ----
def sc01(c, t, d):   # coffre de banque, compteur
    c.rect(-10, -10, W + 10, H + 10, fill="#2A9D8F", w=0)
    for i in range(0, W, 120):
        c.rect(i, 0, i + 60, 1000, fill="#33AE9F", w=0)
    floor(c, 1000, "#21867A")
    # porte de coffre
    vx, vy = 300, 640
    c.circle(vx, vy, 230, fill="#ADB5BD", w=7)
    c.circle(vx, vy, 180, fill="#CED4DA", w=5)
    a = t * 2.2
    for k in range(3):
        aa = a + k * math.pi / 3
        c.line([(vx - math.cos(aa) * 120, vy - math.sin(aa) * 120), (vx + math.cos(aa) * 120, vy + math.sin(aa) * 120)], w=16)
    c.circle(vx, vy, 34, fill="#6C757D", w=5)
    for k in range(8):
        aa = k * math.pi / 4
        c.circle(vx + math.cos(aa) * 205, vy + math.sin(aa) * 205, 9, fill="#6C757D", w=3)
    c.reg("obj", "coffre", (vx - 230, vy - 230, vx + 230, vy + 230))
    # billets qui tombent puis partent en fumée
    rnd = random.Random(1)
    for i in range(9):
        x0 = rnd.uniform(120, 880); t0 = rnd.uniform(0, 1.4); sp = rnd.uniform(380, 520)
        tt = t - t0
        if tt < 0:
            continue
        y = 160 + tt * sp
        if y < 900:
            bill(c, x0 + math.sin(tt * 4 + i) * 40, y, math.sin(tt * 3 + i) * .6, .9)
        else:
            k = clamp((y - 900) / 300)
            if k < 1:
                smoke(c, x0, 900, k)
    # compteur
    v = 10_000_000_000 * eo(prog(t, 0.05, 1.5))
    pop = 1 + 0.12 * (1 - eo(prog(t, 1.5, 1.8))) if t > 1.5 else 1
    c.rect(90, 190, 900, 380, fill="#1B4332", w=7, r=30)
    c.text(495, 290, fmt_int(v) + " $", 110 * pop, fill=YELLOW, stroke=4, maxw=760, kind="text")
    person(c, 760, 990, 0.95, shirt="#FFB703", tie="#E63946", hair="#6B4226",
           expr="panic" if t > 0.5 else "shock", la="head", ra="head", t=t, label="banquier")


def sc02(c, t, d):   # calendrier
    c.rect(-10, -10, W + 10, H + 10, fill="#F4A261", w=0)
    # soleil
    a = t * .8
    for k in range(10):
        aa = a + k * math.pi / 5
        c.line([(960 + math.cos(aa) * 95, 190 + math.sin(aa) * 95), (960 + math.cos(aa) * 140, 190 + math.sin(aa) * 140)], fill="#FFD166", w=14)
    c.circle(960, 190, 75, fill="#FFD166", w=6)
    floor(c, 1000, "#E76F51")
    # calendrier
    k = eob(prog(t, 0, .45))
    cx, cy = 450, 600
    cw, ch = 280 * k, 300 * k
    if k > .05:
        c.rect(cx - cw, cy - ch, cx + cw, cy + ch, fill="white", w=7, r=24)
        c.rect(cx - cw, cy - ch, cx + cw, cy - ch + 140 * k, fill="#E63946", w=7, r=24)
        for sd in (-1, 1):
            c.rect(cx + sd * 140 * k - 14, cy - ch - 40 * k, cx + sd * 140 * k + 14, cy - ch + 40 * k, fill="#6C757D", w=5, r=10)
        if k > .9:
            c.text(cx, cy - ch + 75, "JUIN 2017", 80, fill="white", stroke=0, kind="text")
            day = 20 + int(clamp(prog(t, .35, 1.25)) * 7)
            day = min(27, day)
            pop = 1 + .25 * (1 - eo(prog(t, 1.25, 1.5))) if day == 27 else 1
            col = "#E63946" if day == 27 else INK
            c.text(cx, cy + 75, str(day), 300 * pop, fill=col, kind="text")
            # page qui s'envole
            ft = (prog(t, .35, 1.25) * 7) % 1 if t < 1.25 else 1
            if t < 1.3 and ft < 1:
                px, py = cx + ft * 300, cy + 75 + ft * 250
                pts = rot([(px - 160, py - 120), (px + 160, py - 120), (px + 160, py + 120), (px - 160, py + 120)], px, py, ft * 1.2)
                c.poly(pts, fill="#F8F9FA", w=5)
                c.text(px, py, str(max(20, day - 1)), 260 * (1 - ft * .4), fill=INK, reg=False)
            if t > 1.4:
                rr = 190 + 10 * math.sin(t * 8)
                c.arc(cx - rr, cy + 75 - rr * .8, cx + rr, cy + 75 + rr * .8, 0, 360 * eo(prog(t, 1.4, 1.9)), fill="#E63946", w=12)
    # drapeau ukrainien qui ondule
    fx, fy = 760, 560
    c.line([(fx, fy - 40), (fx, 1000)], fill="#6C757D", w=12)
    up, dn = [], []
    for i in range(11):
        xx = fx + i * 12
        off = math.sin(t * 6 - i * .6) * 10 * (i / 10)
        up.append((xx, fy - 30 + off)); dn.append((xx, fy + 90 + off))
    mid = [(p[0], (p[1] + q[1]) / 2) for p, q in zip(up, dn)]
    c.poly(up + mid[::-1], fill="#0057B7", w=4)
    c.poly(mid + dn[::-1], fill="#FFD700", w=4)
    c.reg("obj", "drapeau", (fx - 6, fy - 50, fx + 132, fy + 110))


def sc03(c, t, d):   # bureau, mise à jour
    c.rect(-10, -10, W + 10, H + 10, fill="#5DADE2", w=0)
    # fenêtre
    c.rect(80, 200, 360, 440, fill="#CAF0F8", w=7, r=10)
    cx0 = 80 + ((t * 60) % 340)
    for dx in (0, -340):
        x = cx0 + dx
        if 90 < x < 330:
            c.circle(x, 300, 30, fill="white", w=0); c.circle(x + 30, 290, 38, fill="white", w=0)
    c.line([(220, 200), (220, 440)], w=7); c.line([(80, 320), (360, 320)], w=7)
    # horloge
    c.circle(780, 290, 90, fill="white", w=7)
    a = t * 6
    c.line([(780, 290), (780 + math.sin(a) * 65, 290 - math.cos(a) * 65)], w=7)
    c.line([(780, 290), (780 + math.sin(a / 12 + 1) * 45, 290 - math.cos(a / 12 + 1) * 45)], w=10)
    floor(c, 1000, "#3A86C8")
    # bureau
    c.rect(380, 820, 900, 860, fill="#A0522D", w=6, r=6)
    c.rect(410, 860, 440, 1000, fill="#8B4513", w=5); c.rect(840, 860, 870, 1000, fill="#8B4513", w=5)
    # écran
    c.rect(600, 760, 680, 822, fill="#6C757D", w=5)
    c.rect(440, 500, 860, 770, fill="#343A40", w=7, r=18)
    c.rect(462, 520, 838, 750, fill="#0B132B", w=0, r=8)
    p = eio(prog(t, .35, 2.3))
    c.text(650, 575, "MISE À JOUR", 54, fill="white", kind="text")
    c.rect(490, 640, 810, 690, fill="#1B263B", outline="white", w=4, r=12)
    if p > .02:
        c.rect(496, 646, 496 + 308 * p, 684, fill="#2EE59D", w=0, r=8)
    c.text(650, 722, f"{int(p * 100)} %", 40, fill="#2EE59D", kind="text")
    c.reg("obj", "ecran", (440, 500, 860, 822))
    # tasse
    c.rect(780, 770, 830, 820, fill="white", w=5, r=8)
    for i in range(2):
        pts = [(795 + i * 18 + math.sin(t * 5 + j + i) * 6, 760 - j * 14) for j in range(5)]
        c.line(pts, fill="white", w=5)
    person(c, 260, 990, 1.0, shirt="#7209B7", hair="#2B2D42", glasses=True,
           expr="happy", la="down", ra=(160, -30), t=t, look=(1, 0), label="comptable")
    # notif
    k = eob(prog(t, .1, .45))
    if k > .05:
        c.rect(470 + 180 * (1 - k), 380, 470 + 360 * k + 180 * (1 - k) * 0 + 0, 470, fill="#FFE600", w=5, r=20) if False else None
        x0, x1 = 650 - 190 * k, 650 + 190 * k
        c.rect(x0, 400, x1, 470, fill=YELLOW, w=5, r=22)
        if k > .8:
            c.text(650, 435, "NOUVELLE VERSION !", 36, fill=INK, kind="text")


def sc04(c, t, d):   # hacker cache le virus
    c.rect(-10, -10, W + 10, H + 10, fill="#3C096C", w=0)
    rnd = random.Random(4)
    for i in range(16):
        x = 30 + i * 66
        sp = rnd.uniform(150, 320); off = rnd.uniform(0, 900)
        for j in range(7):
            y = 170 + ((off + t * sp + j * 46) % 820)
            c.text(x, y, rnd.choice("01"), 34, fill=mix("#3C096C", "#7B2CBF", 1 - j / 8), fname="bold", reg=False)
    floor(c, 1000, "#240046")
    # silhouette à capuche
    hx, hy = 250, 640
    c.chord(hx - 170, hy - 40, hx + 170, hy + 560, 180, 360, fill="#10002B", outline=INK, w=6)
    c.circle(hx, hy, 115, fill="#10002B", w=6)
    c.circle(hx, hy + 12, 82, fill="#000000", w=0)
    face(c, hx, hy + 12, 82, "evil", t, skin="#000000")
    c.reg("obj", "hacker", (hx - 170, hy - 115, hx + 170, 1000))
    # ordi portable
    c.poly([(150, 920), (370, 920), (400, 960), (120, 960)], fill="#ADB5BD", w=5)
    c.poly([(170, 920), (350, 920), (380, 790), (200, 790)], fill="#495057", w=5)
    c.poly([(185, 905), (340, 905), (362, 805), (212, 805)], fill="#80FFDB" if int(t * 8) % 2 else "#64DFDF", w=0)
    # carton "mise à jour"
    bx, by = 720, 900
    c.rect(bx - 150, by - 220, bx + 150, by, fill="#DDA15E", w=6, r=8)
    lid = 1 - eo(prog(t, 1.55, 1.9))
    for sd in (-1, 1):
        ang = sd * (2.0 * lid + .05)
        pts = rot([(bx, by - 220), (bx + sd * 150, by - 220), (bx + sd * 150, by - 250), (bx, by - 250)], bx + sd * 150 * 0 + (sd * 150 if False else 0) + sd * 150, by - 220, 0)
        hinge = (bx + sd * 150, by - 220)
        flap = [(hinge[0], hinge[1]), (hinge[0] - sd * 150, hinge[1]), (hinge[0] - sd * 150, hinge[1] - 22), (hinge[0], hinge[1] - 22)]
        c.poly(rot(flap, hinge[0], hinge[1], ang), fill="#BC6C25", w=5)
    # virus : sort du PC, saute dans le carton
    p1 = eob(prog(t, .1, .6))
    p2 = eio(prog(t, .7, 1.5))
    sx, sy = 280, 820 - 120 * p1
    ex, ey = bx, by - 160
    x = lerp(sx, ex, p2); y = lerp(sy, ey, p2) - math.sin(p2 * math.pi) * 330
    if t < 1.6:
        virus(c, x, y, 55 * max(.05, p1), t)
    else:
        sticker = eob(prog(t, 1.85, 2.2))
        if sticker > .05:
            c.rect(bx - 135 * sticker, by - 140, bx + 135 * sticker, by - 70, fill="white", w=5, r=12)
            if sticker > .8:
                c.text(bx, by - 105, "MISE À JOUR", 40, fill=INK, kind="text")
        c.text(bx, by - 30, "☠", 1, reg=False) if False else None
    c.reg("obj", "carton", (bx - 150, by - 250, bx + 150, by))
    if t > .25:
        lk = eob(prog(t, .25, .55))
        c.rect(495 - 200 * lk, 210, 495 + 200 * lk, 320, fill="#52B788", w=6, r=26)
        if lk > .8:
            c.text(495, 265, "NotPetya", 76, fill="white", stroke=4, kind="text")


def sc05(c, t, d):   # fausse rançon
    flash = int(t * 6) % 2 == 0 and t < 1.6
    c.rect(-10, -10, W + 10, H + 10, fill="#E63946" if not flash else "#C1121F", w=0)
    floor(c, 1000, "#9D0208")
    shake = math.sin(t * 60) * 8 if 1.6 < t < 2.0 else 0
    mx0, my0, mx1, my1 = 120 + shake, 200, 870 + shake, 650
    c.rect(450 + shake, 650, 540 + shake, 720, fill="#6C757D", w=5)
    c.rect(360 + shake, 715, 630 + shake, 740, fill="#6C757D", w=5, r=8)
    c.rect(mx0, my0, mx1, my1, fill="#343A40", w=7, r=20)
    scr = "#000000" if flash else "#370617"
    c.rect(mx0 + 22, my0 + 22, mx1 - 22, my1 - 22, fill=scr, w=0, r=10)
    c.reg("obj", "ecran", (mx0, my0, mx1, my1))
    # crâne cartoon
    sk = 1 + .06 * math.sin(t * 10)
    sx, sy = 300 + shake, 420
    c.circle(sx, sy - 10, 80 * sk, fill="white", w=5)
    c.rect(sx - 45, sy + 40, sx + 45, sy + 95, fill="white", w=5, r=10)
    for sd in (-1, 1):
        c.circle(sx + sd * 30, sy - 15, 22, fill=INK, w=0)
    c.poly([(sx, sy + 10), (sx - 10, sy + 30), (sx + 10, sy + 30)], fill=INK, w=0)
    for i in (-1, 0, 1):
        c.line([(sx + i * 20, sy + 60), (sx + i * 20, sy + 95)], w=4, cap=False)
    c.text(620 + shake, 340, "PAYEZ", 80, fill="#FF4D6D", kind="text")
    c.text(620 + shake, 440, "EN BITCOIN", 64, fill="white", kind="text")
    c.text(620 + shake, 525, "…pour rien.", 44, fill="#ADB5BD", kind="text") if t > 1.0 else None
    if t > 1.6:   # écran fissuré
        k = eo(prog(t, 1.6, 1.9))
        cx, cy = 455 + shake, 300
        rnd = random.Random(5)
        for i in range(9):
            a = i * 2 * math.pi / 9 + rnd.uniform(-.2, .2)
            L = rnd.uniform(160, 260) * k
            pts = [(cx, cy)]
            for j in range(1, 4):
                rr = L * j / 3
                pts.append((cx + math.cos(a) * rr + rnd.uniform(-15, 15), cy + math.sin(a) * rr + rnd.uniform(-15, 15)))
            pts = [(clamp(px, mx0 + 25, mx1 - 25), clamp(py, my0 + 25, my1 - 25)) for px, py in pts]
            c.line(pts, fill="white", w=5)
        star(c, cx, cy, 34 * k, 14 * k, 8, "#FFE600", w=3)
    person(c, 230, 1000, 0.82, shirt="#3A86FF", hair="#000000", expr="panic", la="head", ra="head", t=t, label="victime1")
    person(c, 740, 1000, 0.82, shirt="#FB8500", hair="#8D5524", skin="#C68642", expr="sad" if t < 1.6 else "shock",
           la="down", ra="front", t=t, label="victime2")


CONT = {
    "na": [(90, 330), (230, 300), (360, 320), (420, 390), (360, 450), (310, 520), (250, 560), (210, 520), (150, 470), (100, 410)],
    "sa": [(280, 590), (360, 600), (420, 660), (390, 760), (340, 840), (310, 800), (300, 700)],
    "eu": [(480, 360), (560, 340), (640, 360), (620, 430), (560, 450), (500, 440)],
    "af": [(480, 480), (590, 470), (640, 540), (610, 650), (560, 740), (520, 700), (500, 600), (460, 540)],
    "as": [(650, 330), (800, 300), (950, 330), (990, 400), (920, 480), (840, 520), (760, 560), (700, 500), (650, 440)],
    "au": [(830, 680), (920, 670), (960, 720), (920, 780), (850, 770)],
}

def sc06(c, t, d):   # carte du monde
    c.rect(-10, -10, W + 10, H + 10, fill="#023E8A", w=0)
    for i in range(6):
        y = 220 + i * 140
        pts = [(x, y + math.sin(x / 60 + t * 2 + i) * 6) for x in range(0, W + 40, 40)]
        c.line(pts, fill="#0353A4", w=4)
    floor(c, 1010, "#012A5E")
    for k, pts in CONT.items():
        c.poly(pts, fill="#52B788", w=6)
    origin = (585, 400)
    cities = [((520, 380), .2), ((540, 425), .35), ((300, 420), .7), ((190, 450), 1.0), ((720, 470), .55),
              ((860, 420), .85), ((890, 725), 1.2), ((360, 680), 1.1), ((560, 560), .6), ((620, 365), .3)]
    for (x, y), t0 in cities:
        k = prog(t, t0, t0 + .45)
        if k <= 0:
            continue
        mx, my = (origin[0] + x) / 2, min(origin[1], y) - 90
        n = 14
        pts = []
        for i in range(int(n * eo(k)) + 1):
            u = i / n
            pts.append(((1 - u) ** 2 * origin[0] + 2 * (1 - u) * u * mx + u * u * x,
                        (1 - u) ** 2 * origin[1] + 2 * (1 - u) * u * my + u * u * y))
        if len(pts) > 1:
            c.line(pts, fill="#FF4D6D", w=6)
        if k >= 1:
            rr = 14 + ((t - t0) * 50) % 40
            c.circle(x, y, rr, fill=None, outline="#FF4D6D", w=4)
            c.circle(x, y, 14, fill="#FF0A54", w=4)
    virus(c, origin[0], origin[1], 32 + 4 * math.sin(t * 8), t)
    # badge
    k = eob(prog(t, .1, .45))
    if k > .05:
        c.rect(495 - 230 * k, 180, 495 + 230 * k, 270, fill="#FF0A54", w=6, r=24)
        if k > .8:
            c.text(495, 225, "27 JUIN 2017", 56, fill="white", kind="text")


def container(c, x, y, w, h, col):
    c.rect(x, y, x + w, y + h, fill=col, w=5, r=4)
    for i in range(1, 6):
        xx = x + i * w / 6
        c.line([(xx, y + 8), (xx, y + h - 8)], fill=mix(col, "#000000", .3), w=4, cap=False)


def sc07(c, t, d):   # port à l'arrêt
    c.rect(-10, -10, W + 10, H + 10, fill="#FFB703", w=0)
    c.circle(860, 420, 120, fill="#FB8500", w=0)
    c.rect(-10, 900, W + 10, H + 10, fill="#219EBC", w=0)
    for i in range(5):
        y = 950 + i * 70
        pts = [(x, y + math.sin(x / 50 + t * 3 + i) * 7) for x in range(0, W + 40, 40)]
        c.line(pts, fill="#8ECAE6", w=4)
    c.rect(-10, 820, W + 10, 900, fill="#6C757D", w=6)
    # grue
    c.rect(100, 470, 140, 820, fill="#E63946", w=5)
    for i in range(7):
        y = 480 + i * 48
        c.line([(102, y), (138, y + 48)], fill="#9D0208", w=4, cap=False)
    c.rect(60, 460, 560, 495, fill="#E63946", w=5)
    # conteneur suspendu (se fige)
    sw = math.sin(t * 5) * (1 - eo(prog(t, .8, 1.6))) * .25
    px, py = 440, 495
    L = 120
    hx, hy = px + math.sin(sw) * L, py + math.cos(sw) * L
    c.line([(px, py), (hx, hy)], w=5)
    container(c, hx - 90, hy, 180, 70, "#2A9D8F")
    c.reg("obj", "conteneur", (hx - 90, hy, hx + 90, hy + 70))
    cols = ["#E63946", "#457B9D", "#F4A261", "#2A9D8F", "#8338EC", "#FB8500"]
    for r_ in range(3):
        for k in range(2):
            container(c, 590 + k * 160, 820 - (r_ + 1) * 62, 150, 58, cols[(r_ * 2 + k) % 6])
    c.reg("obj", "pile", (590, 634, 900, 820))
    # camions bloqués
    for i in range(3):
        x = 160 + i * 150 + math.sin(t * 20 + i) * 2
        c.rect(x, 760, x + 100, 815, fill="#ADB5BD", w=4, r=4)
        c.rect(x + 100, 775, x + 135, 815, fill="#3A86FF", w=4, r=6)
        c.circle(x + 25, 818, 12, fill=INK, w=0); c.circle(x + 115, 818, 12, fill=INK, w=0)
    # compteur 76
    k = eo(prog(t, .05, 1.2))
    pop = 1 + .2 * (1 - eo(prog(t, 1.2, 1.45))) if t > 1.2 else 1
    c.text(495, 280, str(int(round(76 * k))), 210 * pop, fill="white", stroke=8, kind="text")
    # panneau STOP
    sk = eob(prog(t, 1.3, 1.7))
    if sk > .05:
        sy = lerp(-100, 640, clamp(sk))
        c.line([(330, sy), (330, 760)], fill="#495057", w=10) if sk > .9 else None
        pts = [(330 + 62 * sk * math.cos(i * math.pi / 4 + math.pi / 8), sy + 62 * sk * math.sin(i * math.pi / 4 + math.pi / 8)) for i in range(8)]
        c.poly(pts, fill="#D00000", outline="white", w=6)
        if sk > .6:
            c.text(330, sy, "STOP", 38 * sk, fill="white", kind="text")


def rack(c, x, y, w, h, t, red, ang=0.0, label="rack"):
    pivot = (x + w, y + h)
    body = rot([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], *pivot, ang)
    c.poly(body, fill="#343A40", outline="#ADB5BD", w=5)
    for i in range(9):
        yy = y + 22 + i * (h - 40) / 9
        sl = rot([(x + 14, yy), (x + w - 14, yy), (x + w - 14, yy + 34), (x + 14, yy + 34)], *pivot, ang)
        c.poly(sl, fill="#212529", outline="#6C757D", w=3)
        for j in range(3):
            on = (int(t * 7 + i * 3 + j * 5) % 3) != 0
            col = ("#FF0A54" if on else "#590D22") if red else ("#2EE59D" if on else "#1B4332")
            p = rot([(x + w - 30 - j * 18, yy + 17)], *pivot, ang)[0]
            c.circle(p[0], p[1], 5, fill=col, w=0)
    xs = [p[0] for p in body]; ys = [p[1] for p in body]
    c.reg("obj", label, (min(xs), min(ys), max(xs), max(ys)))


def sc08(c, t, d):   # salle des serveurs
    c.rect(-10, -10, W + 10, H + 10, fill="#0B132B", w=0)
    floor(c, 960, "#1C2541")
    for i in range(0, W, 90):
        c.line([(i, 960), (i - 60, 1100)], fill="#3A506B", w=3, cap=False)
    xs = [70, 245, 420, 595]
    wave = prog(t, .25, 1.0) * 4.5
    for i in range(3, -1, -1):          # dominos : chaque baie s'appuie sur la suivante
        x = xs[i]
        red = wave > i + .5
        ft = prog(t, 1.35 + i * .1, 1.65 + i * .1)
        ang = eob(ft) * (0.33 if i < 3 else 0.29)
        rack(c, x, 420, 140, 540, t, red, ang, label=f"rack{i}")
    if t > 1.35:
        for i in range(4):
            k = prog(t, 1.75 + i * .12, 2.3 + i * .12)
            if 0 < k < 1:
                smoke(c, xs[i] + 70, 950, k)
    k1 = eo(prog(t, .05, 1.3))
    c.text(495, 235, fmt_int(45000 * k1) + " PC", 110, fill="white", stroke=6, maxw=820, kind="text")
    c.text(495, 345, fmt_int(4000 * k1) + " SERVEURS", 70, fill="#FF4D6D", stroke=5, maxw=820, kind="text")


AFRICA = [(-17, 21), (-16, 12), (-8, 5), (5, 5), (9, 4), (10, -2), (13, -12), (12, -17), (15, -28), (20, -35),
          (27, -34), (33, -27), (35, -20), (40, -15), (40, -10), (42, -2), (51, 11), (43, 12), (38, 18), (33, 30),
          (25, 32), (20, 31), (10, 37), (0, 36), (-6, 35), (-10, 30), (-13, 27)]

def africa_pts(cx=430, cy=610, sx=8.6, sy=8.2):
    return [(cx + (lo - 12) * sx, cy - (la - 3) * sy) for lo, la in AFRICA]


def sc09(c, t, d):   # survivant en Afrique
    c.rect(-10, -10, W + 10, H + 10, fill="#E9C46A", w=0)
    a = t * .5
    for k in range(12):
        aa = a + k * math.pi / 6
        c.poly([(780, 760), (780 + math.cos(aa) * 700, 760 + math.sin(aa) * 700),
                (780 + math.cos(aa + .18) * 700, 760 + math.sin(aa + .18) * 700)], fill="#F1D17A", w=0)
    floor(c, 1000, "#D4A373")
    pts = africa_pts()
    c.poly(pts, fill="#E76F51", w=7)
    c.reg("obj", "afrique", (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
    # épingle Afrique de l'Ouest
    px, py = 430 + (1 - 12) * 8.6, 610 - (7 - 3) * 8.2
    k = eob(prog(t, .3, .7))
    if k > .05:
        for i in range(2):
            rr = 20 + ((t * 60 + i * 30) % 60)
            c.circle(px, py, rr, fill=None, outline="white", w=4)
        yy = py - 90 * k
        c.poly([(px - 34, yy), (px + 34, yy), (px, py)], fill="#D00000", w=5)
        c.circle(px, yy, 38, fill="#D00000", w=5)
        c.circle(px, yy, 14, fill="white", w=0)
    # serveur survivant
    sk = eob(prog(t, .7, 1.1))
    if sk > .05:
        sy = 960
        star(c, 790, sy - 100, 150 * sk, 105 * sk, 12, "#FFE600", ang=t, w=5)
        server_buddy(c, 790, sy, 1.0 * sk, "happy", t, label="serveur")
    lk = eob(prog(t, 1.2, 1.5))
    if lk > .05:
        c.rect(495 - 250 * lk, 190, 495 + 250 * lk, 290, fill="#264653", w=6, r=26)
        if lk > .8:
            c.text(495, 240, "1 SEUL SURVIVANT", 58, fill="white", kind="text")


def sc10(c, t, d):   # coupure de courant
    dark = prog(t, .9, 1.0)
    flick = .6 < t < .9 and int(t * 20) % 2 == 0
    bg = "#1D1A31" if (dark >= 1 or flick) else "#FFD166"
    c.rect(-10, -10, W + 10, H + 10, fill=bg, w=0)
    floor(c, 1000, "#120F22" if bg == "#1D1A31" else "#E9B949")
    on = bg != "#1D1A31"
    # lampe
    c.line([(495, 150), (495, 300)], w=6, cap=False)
    c.chord(395, 260, 595, 420, 180, 360, fill="#6C757D", outline=INK, w=6)
    c.circle(495, 350, 32, fill="#FFF3B0" if on else "#495057", w=5)
    if on:
        for k in range(6):
            aa = math.pi * (.15 + k * .14)
            c.line([(495 + math.cos(aa) * 60, 350 + math.sin(aa) * 60), (495 + math.cos(aa) * 95, 350 + math.sin(aa) * 95)], fill="#FFF3B0", w=8)
    # prise + étincelle
    c.rect(820, 760, 890, 850, fill="white", w=5, r=10)
    c.circle(843, 795, 6, fill=INK, w=0); c.circle(867, 795, 6, fill=INK, w=0)
    c.line([(690, 940), (760, 940), (800, 805), (830, 805)], fill=INK, w=8)
    if .85 < t < 1.25:
        star(c, 855, 805, 70, 25, 7, "#FFE600", ang=t * 5, w=4)
    # serveur
    server_buddy(c, 620, 990, 1.0, "happy" if on else "sleep", t, color="#ADB5BD" if on else "#6C757D", label="serveur")
    if not on:
        for i in range(3):
            k = ((t - 1.0) * .9 + i * .33) % 1
            c.text(700 + k * 80 + i * 10, 760 - k * 220, "Z", 40 + i * 14, fill="white", stroke=3, kind="text")
    # perso avec bougie
    if not on:
        for rr, col in ((150, "#2E2A4A"), (105, "#3D3760"), (65, "#4F4778")):
            c.circle(330, 700, rr, fill=col, w=0)
    person(c, 260, 990, 0.95, shirt="#06D6A0", hair="#F8F9FA", expr="happy" if not on else "worried",
           la="down", ra=(70, -20) if not on else "down", t=t, label="technicien")
    if not on:
        c.rect(318, 715, 342, 790, fill="#FFF8E7", w=4, r=4)
        fl = 1 + .15 * math.sin(t * 30)
        c.poly([(330, 680 - 18 * fl), (342, 708), (318, 708)], fill="#FFB703", w=3)


def plane(c, x, y, ang, s=1.0):
    def P(pts):
        return rot([(x + px * s, y + py * s) for px, py in pts], x, y, ang)
    c.poly(P([(-60, -20), (10, -95), (45, -95), (15, -20)]), fill="#ADB5BD", w=5)      # aile arrière
    c.poly(P([(-190, -10), (-210, -85), (-170, -85), (-130, -20)]), fill="#E63946", w=5)  # dérive
    body = [(-200, -20), (140, -40), (200, -10), (205, 15), (140, 35), (-200, 25)]
    c.poly(P(body), fill="white", w=6)
    c.poly(P([(-30, 15), (40, 15), (-10, 95), (-50, 95)]), fill="#ADB5BD", w=5)          # aile
    for i in range(4):
        cx, cy = P([(-130 + i * 55, -5)])[0]
        c.circle(cx, cy, 13 * s, fill="#4CC9F0", w=4)
    cx, cy = P([(130, -12)])[0]
    c.circle(cx, cy, 30 * s, fill="#FFD6A5", w=4)
    face(c, cx, cy, 30 * s, "happy", 0)
    xs = [p[0] for p in P(body)]; ys = [p[1] for p in P([(0, -95), (0, 95)] + body)]
    c.reg("obj", "avion", (min(xs) - 10, min(ys), max(xs) + 10, max(ys)))


def sc11(c, t, d):   # avion vers l'Europe
    c.rect(-10, -10, W + 10, H + 10, fill="#90E0EF", w=0)
    for i, (y, sp, r) in enumerate(((260, 90, 45), (430, 60, 35), (700, 120, 50), (880, 70, 40))):
        x = (W + 200) - ((t * sp + i * 300) % (W + 400))
        c.circle(x, y, r, fill="white", w=0); c.circle(x + r, y - r * .4, r * 1.2, fill="white", w=0); c.circle(x + r * 2.2, y, r, fill="white", w=0)
    floor(c, 1000, "#48CAE4")
    a, b = (190, 900), (770, 900)
    def arcpt(u):
        return lerp(a[0], b[0], u), lerp(a[1], b[1], u) - math.sin(u * math.pi) * 460
    for i in range(0, 40):
        u0 = i / 40
        if i % 2 == 0:
            c.line([arcpt(u0), arcpt(u0 + 1 / 40)], fill="white", w=6)
    for (x, y), lab, col in ((a, "AFRIQUE", "#E76F51"), (b, "EUROPE", "#3A86FF")):
        c.circle(x, y, 20, fill=col, w=5)
        c.rect(x - 110, y + 32, x + 110, y + 92, fill=col, w=5, r=20)
        c.text(x, y + 62, lab, 44, fill="white", kind="text")
    u = eio(prog(t, .1, 2.3))
    x, y = arcpt(u)
    x2, y2 = arcpt(min(1, u + .01))
    ang = math.atan2(y2 - y, x2 - x) if u < .99 else 0
    plane(c, x, y - 40 + math.sin(t * 6) * 6, ang * .8, 0.7)
    if t > 2.3:
        k = eob(prog(t, 2.3, 2.6))
        c.circle(b[0], b[1] - 100, 50 * k, fill="#2EE59D", w=5)
        c.line([(b[0] - 22 * k, b[1] - 100), (b[0] - 5 * k, b[1] - 80 * 1 - 3), (b[0] + 25 * k, b[1] - 125)], fill="white", w=10)
    k = eob(prog(t, .1, .4))
    if k > .05:
        c.rect(495 - 210 * k, 180, 495 + 210 * k, 270, fill="#023E8A", w=6, r=24)
        if k > .8:
            c.text(495, 225, "LA SAUVEGARDE", 50, fill="white", kind="text")


def sc12(c, t, d):   # facture
    c.rect(-10, -10, W + 10, H + 10, fill="#B5179E", w=0)
    rnd = random.Random(12)
    floor(c, 1000, "#7209B7")
    for i in range(10):
        x = rnd.uniform(60, 1000); t0 = rnd.uniform(0, 2); sp = rnd.uniform(400, 600)
        y = 150 + (t - t0) * sp
        if t > t0 and y < 990:
            c.ellipse(x - 26 * abs(math.cos(t * 6 + i)) - 3, y - 26, x + 26 * abs(math.cos(t * 6 + i)) + 3, y + 26, fill="#FFD60A", w=4)
    # ticket qui se déroule
    x0, x1 = 110, 610
    k = eo(prog(t, .05, 1.1))
    y1 = lerp(200, 900, k)
    c.rect(x0 - 20, 175, x1 + 20, 215, fill="#6C757D", w=5, r=10)
    zig = [(x0, 200), (x1, 200), (x1, y1)]
    n = 10
    for i in range(n):
        zig.append((x1 - (i + .5) * (x1 - x0) / n, y1 + (18 if i % 2 == 0 else 0)))
        zig.append((x1 - (i + 1) * (x1 - x0) / n, y1))
    c.poly(zig, fill="white", w=5)
    c.reg("obj", "ticket", (x0, 175, x1, y1 + 18))
    if y1 > 330:
        c.text((x0 + x1) / 2, 270, "FACTURE", 64, fill=INK, kind="text")
    for i in range(4):
        yy = 340 + i * 60
        if y1 > yy + 30:
            c.rect(x0 + 40, yy, x0 + 40 + (i * 53 % 120) + 180, yy + 22, fill="#DEE2E6", w=0, r=8)
            c.rect(x1 - 130, yy, x1 - 40, yy + 22, fill="#DEE2E6", w=0, r=8)
    if y1 > 640:
        c.line([(x0 + 30, 600), (x1 - 30, 600)], fill="#ADB5BD", w=4, cap=False)
        c.text((x0 + x1) / 2, 650, "JUSQU'À", 44, fill="#7209B7", kind="text")
        v = 300_000_000 * eo(prog(t, .9, 1.9))
        pop = 1 + .15 * (1 - eo(prog(t, 1.9, 2.15))) if t > 1.9 else 1
        c.text((x0 + x1) / 2, 745, fmt_int(v) + " $", 72 * pop, fill="#D00000", maxw=440, kind="text")
    sink = 40 * eo(prog(t, 2.0, 2.6))
    person(c, 790, 990 + sink * 0, 0.95, shirt="#264653", tie="#E63946", hair="#ADB5BD",
           expr="dizzy" if t > 2.0 else "shock", la="out" if t < 2.0 else "up", ra="out" if t < 2.0 else "up",
           headdy=sink, t=t, label="patron")


def flag_us(c, x, y, w, h):
    for i in range(7):
        c.rect(x, y + i * h / 7, x + w, y + (i + 1) * h / 7, fill="#B22234" if i % 2 == 0 else "white", w=0)
    c.rect(x, y, x + w * .45, y + h * 4 / 7, fill="#3C3B6E", w=0)
    c.rect(x, y, x + w, y + h, fill=None, w=4)


def flag_uk(c, x, y, w, h):
    c.rect(x, y, x + w, y + h, fill="#012169", w=0)
    c.line([(x, y), (x + w, y + h)], fill="white", w=h * .2, cap=False)
    c.line([(x + w, y), (x, y + h)], fill="white", w=h * .2, cap=False)
    c.line([(x, y), (x + w, y + h)], fill="#C8102E", w=h * .07, cap=False)
    c.line([(x + w, y), (x, y + h)], fill="#C8102E", w=h * .07, cap=False)
    c.rect(x + w / 2 - h * .17, y, x + w / 2 + h * .17, y + h, fill="white", w=0)
    c.rect(x, y + h / 2 - h * .17, x + w, y + h / 2 + h * .17, fill="white", w=0)
    c.rect(x + w / 2 - h * .1, y, x + w / 2 + h * .1, y + h, fill="#C8102E", w=0)
    c.rect(x, y + h / 2 - h * .1, x + w, y + h / 2 + h * .1, fill="#C8102E", w=0)
    c.rect(x, y, x + w, y + h, fill=None, w=4)


def sc13(c, t, d):   # accusation
    c.rect(-10, -10, W + 10, H + 10, fill="#264653", w=0)
    c.rect(-10, 560, W + 10, 1000, fill="#1D3540", w=0)
    floor(c, 1000, "#132A33")
    rnd = random.Random(int(t * 5))
    for i in range(3):         # flashs photo
        x, y = rnd.uniform(60, 1020), rnd.uniform(520, 640)
        star(c, x, y, 34, 10, 4, "white", w=0)
    for x, fl, shirt, skin, hair, la, ra in ((270, flag_us, "#1D3557", "#FFD6A5", "#6B4226", "down", "point"),
                                             (700, flag_uk, "#3D405B", "#8D5524", "#000000", "point", "down")):
        person(c, x, 960, 0.9, shirt=shirt, tie="#E63946", skin=skin, hair=hair, expr="angry",
               la=la if x > 500 else "down", ra="point" if x < 500 else "down", t=t, label="porte-parole")
        c.poly([(x - 120, 780), (x + 120, 780), (x + 95, 1000), (x - 95, 1000)], fill="#8D6E63", w=6)
        c.rect(x - 140, 765, x + 140, 795, fill="#6D4C41", w=5, r=6)
        fl(c, x - 55, 830, 110, 66)
        c.reg("obj", "pupitre", (x - 140, 765, x + 140, 1000))
    k = eob(prog(t, .9, 1.25))
    if k > .05:
        x0, x1 = 495 - 330 * k, 495 + 330 * k
        c.rect(x0, 290, x1, 430, fill="white", w=6, r=34)
        c.poly([(470, 428), (530, 428), (500, 480)], fill="white", w=0)
        c.line([(470, 431), (500, 480), (530, 431)], w=6)
        if k > .85:
            c.text(495, 360, "C'EST L'ARMÉE RUSSE !", 62, fill="#D00000", maxw=600, kind="text")
    dk = eob(prog(t, .1, .4))
    if dk > .05:
        c.rect(495 - 130 * dk, 175, 495 + 130 * dk, 250, fill=YELLOW, w=5, r=20)
        if dk > .8:
            c.text(495, 212, "FÉV. 2018", 48, fill=INK, kind="text")


def onion(c, x, base, w, h, col):
    c.rect(x - w * .4, base - h * .55, x + w * .4, base, fill=mix(col, "#FFFFFF", .5), w=5)
    pts = []
    for i in range(21):
        u = i / 20
        yy = base - h * .55 - u * h * .45
        ww = w * .55 * math.sin(math.pi * min(1, u * 1.25)) ** .8 * (1 - u * .6)
        pts.append((x - ww, yy))
    pts2 = [(2 * x - px, py) for px, py in pts[::-1]]
    c.poly(pts + pts2, fill=col, w=5)
    c.line([(x, base - h), (x, base - h - 30)], w=5)


def sc14(c, t, d):   # Moscou dément
    c.rect(-10, -10, W + 10, H + 10, fill="#6D597A", w=0)
    onion(c, 120, 1000, 150, 380, "#E63946")
    onion(c, 900, 1000, 130, 320, "#2A9D8F")
    onion(c, 1010, 1000, 110, 250, "#FFB703")
    floor(c, 1000, "#4A3B55")
    shake = math.sin(t * 14) * 18 if t > .3 else 0
    person(c, 495, 990, 1.05, shirt="#495057", tie="#14213D", hair="#ADB5BD", expr="smug",
           la="out", ra="out", headdx=shake, t=t, label="officiel")
    k = eob(prog(t, .35, .7))
    if k > .05:
        x0, x1 = 495 - 300 * k, 495 + 300 * k
        c.rect(x0, 230, x1, 380, fill="white", w=6, r=34)
        c.poly([(470, 378), (530, 378), (510, 450)], fill="white", w=0)
        c.line([(470, 381), (510, 450), (530, 381)], w=6)
        if k > .85:
            c.text(495, 305, "CE N'ÉTAIT PAS NOUS.", 58, fill=INK, maxw=540, kind="text")
    for i, (x, y) in enumerate(((210, 560), (790, 520), (250, 760), (770, 740))):
        kk = eob(prog(t, .6 + i * .15, .9 + i * .15))
        if kk > .05:
            c.text(x, y + math.sin(t * 4 + i) * 12, "?", 110 * kk, fill=YELLOW, stroke=5, kind="text")


def sc15(c, t, d):   # chute
    c.rect(-10, -10, W + 10, H + 10, fill="#FFD60A", w=0)
    for i in range(-4, 12):
        x = i * 120 + (t * 40) % 120
        c.poly([(x, 0), (x + 60, 0), (x - 340, 1000), (x - 400, 1000)], fill="#FFE347", w=0)
    floor(c, 1000, "#F2B705")
    k = eob(prog(t, 0, .4))
    x0, x1, y0, y1 = 495 - 380 * k, 495 + 380 * k, 230, 640
    if k > .05:
        c.rect(x0, y0, x1, y1, fill="white", w=7, r=22)
        c.rect(x0, y0, x1, y0 + 80, fill="#3A86FF", w=7, r=22)
        c.rect(x0 + 4, y0 + 50, x1 - 4, y0 + 78, fill="#3A86FF", w=0)
        if k > .85:
            c.text(495, y0 + 42, "MISE À JOUR DISPONIBLE", 44, fill="white", maxw=640, kind="text")
            c.text(495, 410, "Installer maintenant ?", 52, fill=INK, kind="text")
            hv = (t * 1.4) % 2 < 1
            for bx, lab, col in ((320, "OUI", "#2EE59D"), (670, "NON", "#FF4D6D")):
                big = 1.08 if (hv and lab == "OUI") or (not hv and lab == "NON") else 1
                c.rect(bx - 120 * big, 500 - 45 * big, bx + 120 * big, 500 + 45 * big, fill=col, w=6, r=24)
                c.text(bx, 500, lab, 54 * big, fill=INK, kind="text")
            cx = lerp(330, 680, eio((math.sin(t * 2.2 * math.pi / 1.4 * .5 * 2) + 1) / 2))
            cy = 545
            c.poly([(cx, cy), (cx, cy + 70), (cx + 18, cy + 54), (cx + 32, cy + 84), (cx + 44, cy + 78), (cx + 30, cy + 48), (cx + 52, cy + 48)], fill="white", w=5)
    person(c, 230, 990, 0.9, shirt="#7209B7", hair="#2B2D42", glasses=True, expr="worried",
           la="down", ra=(30, -150), t=t, look=(1, -1), label="comptable")
    ak = eob(prog(t, .8, 1.2))
    if ak > .05:
        bounce = math.sin(t * 9) * 14
        c.rect(560, 720, 880, 800, fill=INK, w=0, r=24)
        c.text(720, 760, "DIS-LE EN COMMENTAIRE", 34 * ak, fill="white", maxw=300, kind="text")
        ax, ay = 720, 830 + bounce
        c.poly([(ax - 26, ay), (ax + 26, ay), (ax + 26, ay + 60), (ax + 55, ay + 60), (ax, ay + 120), (ax - 55, ay + 60), (ax - 26, ay + 60)], fill="white", w=6)


SCENE_FN = [sc01, sc02, sc03, sc04, sc05, sc06, sc07, sc08, sc09, sc10, sc11, sc12, sc13, sc14, sc15]
for _i, _s in enumerate(SCENES):
    _s["fn"] = SCENE_FN[_i]

# ------------------------------------------------------------ sous-titres ----
def tokens(txt):
    out = []
    for raw in txt.split(" "):
        kw = raw.startswith("*")
        w = raw.lstrip("*").replace("_", " ")
        out.append((w.upper(), kw))
    return out


def word_times(i):
    sc = SCENES[i]
    toks = tokens(sc["txt"])
    n = len(toks)
    start = TRANS * .6
    span = min(sc["dur"] * .68, n * .27)
    return toks, [start + k * span / n for k in range(n)]


SUB_FS, SUB_MAXW, SUB_CX, SUB_CY = 96, 800, (SAFE["x0"] + SAFE["x1"]) / 2 + 10, 1250


def sub_layout(toks):
    fs = SUB_FS
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    while True:
        f = font("anton", fs)
        sp = fs * .28
        lines, cur, cw = [], [], 0
        for k, (w, kw) in enumerate(toks):
            ww = probe.textlength(w, font=f)
            if cur and cw + sp + ww > SUB_MAXW:
                lines.append((cur, cw)); cur, cw = [], 0
            cw = cw + (sp if cur else 0) + ww
            cur.append((k, ww))
        lines.append((cur, cw))
        if len(lines) <= 3 or fs < 60:
            break
        fs -= 6
    lh = fs * 1.5
    slots = {}
    y0 = SUB_CY - lh * (len(lines) - 1) / 2
    for li, (items, lw) in enumerate(lines):
        x = SUB_CX - lw / 2
        for k, ww in items:
            slots[k] = (x + ww / 2, y0 + li * lh)
            x += ww + fs * .28
    return fs, slots


def subtitles(c, i, t):
    toks, times = word_times(i)
    fs, slots = sub_layout(toks)
    for k, ((w, kw), t0) in enumerate(zip(toks, times)):
        if t < t0:
            continue
        pop = 1 + .22 * (1 - eo((t - t0) / .13))
        x, y = slots[k]
        c.text(x, y + 8, w, fs * pop, fill="#000000", stroke=10, stroke_fill="#000000", reg=False)
        c.text(x, y, w, fs * pop, fill=YELLOW if kw else "white", stroke=9, stroke_fill="#000000",
               kind="sub" if pop < 1.01 else "subpop")


# ------------------------------------------------------------- rendu -------
def scene_at(T):
    for i in range(len(SCENES) - 1, -1, -1):
        if T >= STARTS[i] - 1e-9:
            return i, T - STARTS[i]
    return 0, T


def draw_scene(i, t):
    sc = SCENES[i]
    c = Canvas("#000000")
    sc["fn"](c, t, sc["dur"])
    subtitles(c, i, t)
    return c


def render_frame(fi):
    T = fi / FPS
    i, t = scene_at(T)
    c = draw_scene(i, t)
    img = c.final()
    if i > 0 and t < TRANS:      # volet circulaire
        prev = draw_scene(i - 1, SCENES[i - 1]["dur"] - 1 / FPS).final()
        k = eio(t / TRANS)
        mask = Image.new("L", (W, H), 0)
        r = k * math.hypot(W, H) * .6
        ImageDraw.Draw(mask).ellipse([W / 2 - r, H * .38 - r, W / 2 + r, H * .38 + r], fill=255)
        img = Image.composite(img, prev, mask)
    return img.tobytes()


# --------------------------------------------------------------- audio -----
SR = 44100

def synth_audio(path):
    n = int((TOTAL + .5) * SR)
    out = np.zeros(n)
    tt = np.arange(n) / SR
    bpm = 118
    beat = 60 / bpm
    rng = np.random.default_rng(7)

    def add(sig, at, gain=1.0):
        s = int(at * SR)
        if s >= n:
            return
        e = min(n, s + len(sig))
        out[s:e] += sig[: e - s] * gain

    def env(L, a=.005, dcy=.2):
        x = np.arange(int(L * SR)) / SR
        return np.minimum(1, x / a) * np.exp(-x / dcy)

    L = .35; x = np.arange(int(L * SR)) / SR
    kick = np.sin(2 * np.pi * np.cumsum(50 + 110 * np.exp(-x * 30)) / SR) * env(L, .002, .12)
    L = .25; x = np.arange(int(L * SR)) / SR
    snare = (rng.normal(0, 1, len(x)) * .6 + np.sin(2 * np.pi * 190 * x) * .5) * env(L, .002, .07)
    L = .06
    hat = np.diff(rng.normal(0, 1, int(L * SR) + 1)) * env(L, .001, .015)
    roots = [55.0, 43.65, 65.41, 49.0]                    # La, Fa, Do, Sol
    chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [261.6, 329.6, 392], [196, 246.9, 293.7]]
    nbeats = int(TOTAL / beat) + 2
    for b in range(nbeats):
        at = b * beat
        if at > TOTAL - .6:
            break
        bar = (b // 4) % 4
        add(kick, at, .9)
        if b % 4 == 2 and b % 8 != 6:
            add(kick, at + beat / 2, .55)
        if b % 2 == 1:
            add(snare, at, .45)
        for h in range(2):
            add(hat, at + h * beat / 2, .22 if h else .12)
        for h in range(2):        # basse en croches
            L = beat / 2 * .9; x = np.arange(int(L * SR)) / SR
            f0 = roots[bar] * (2 if h else 1)
            bs = np.sign(np.sin(2 * np.pi * f0 * x)) * .5 + np.sin(2 * np.pi * f0 * x)
            add(bs * env(L, .004, .12), at + h * beat / 2, .16)
        for h in range(2):        # arpège pluck
            L = .3; x = np.arange(int(L * SR)) / SR
            f0 = chords[bar][(b * 2 + h) % 3] * 2
            pl = (2 * np.abs(2 * ((x * f0) % 1) - 1) - 1) * env(L, .002, .09)
            add(pl, at + h * beat / 2, .07)
    # effets : whoosh + pop à chaque changement de scène
    for i, st in enumerate(STARTS):
        if i == 0:
            continue
        L = .32; x = np.arange(int(L * SR)) / SR
        noise = rng.normal(0, 1, len(x))
        k = np.exp(-((x - .26) ** 2) / .006)
        sweep = np.convolve(noise, np.ones(6) / 6, "same") * k
        add(sweep, st - .26, .35)
        L = .12; x = np.arange(int(L * SR)) / SR
        pop = np.sin(2 * np.pi * np.cumsum(900 * np.exp(-x * 25) + 250) / SR) * env(L, .001, .04)
        add(pop, st, .4)
    # effets spéciaux
    def ding(at):
        L = .9; x = np.arange(int(L * SR)) / SR
        add((np.sin(2 * np.pi * 1318 * x) + .5 * np.sin(2 * np.pi * 1976 * x)) * env(L, .002, .3), at, .25)
    ding(1.55)                                     # compteur 10 milliards
    ding(STARTS[6] + 1.2)                          # 76
    def boom(at, g=.8):
        L = .9; x = np.arange(int(L * SR)) / SR
        add(np.sin(2 * np.pi * np.cumsum(30 + 80 * np.exp(-x * 8)) / SR) * env(L, .003, .35), at, g)
        add(np.convolve(rng.normal(0, 1, len(x)), np.ones(30) / 30, "same") * env(L, .002, .2), at, g * .8)
    boom(STARTS[4] + 1.6)                          # écran fissuré
    for k in range(4):
        boom(STARTS[7] + 1.55 + k * .12, .35)      # racks qui tombent
    L = .6; x = np.arange(int(L * SR)) / SR          # coupure de courant
    add(np.sin(2 * np.pi * np.cumsum(400 * np.exp(-x * 5) + 40) / SR) * np.exp(-x * 3), STARTS[9] + .9, .35)
    for k in range(int(SCENES[4]["dur"] * 3)):     # alarme rançon
        L = .12; x = np.arange(int(L * SR)) / SR
        add(np.sign(np.sin(2 * np.pi * 880 * x)) * env(L, .002, .05), STARTS[4] + k / 3, .06)
    # mixage
    fade = np.clip((TOTAL + .4 - tt) / .8, 0, 1)
    out *= fade
    out = np.tanh(out * 1.2)
    out /= np.max(np.abs(out)) + 1e-9
    out *= .78
    data = (out * 32767).astype(np.int16)
    st = np.stack([data, data], 1)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
        wf.writeframes(st.tobytes())


# ------------------------------------------------------------- contrôle ----
def overlap(a, b, pad=0):
    return not (a[2] <= b[0] + pad or b[2] <= a[0] + pad or a[3] <= b[1] + pad or b[3] <= a[1] + pad)


def check():
    os.makedirs(os.path.join(OUT, "check"), exist_ok=True)
    problems = []
    thumbs = []
    for i, sc in enumerate(SCENES):
        for frac in np.linspace(.12, 1, 9):
            t = sc["dur"] * frac - (1 / FPS if frac == 1 else 0)
            c = draw_scene(i, t)
            subs = [b for b in c.boxes if b[0] == "sub"]
            items = [b for b in c.boxes if b[0] in ("text", "obj")]
            for kind, lab, bx in c.boxes:
                if kind in ("sub", "text") or (kind == "obj"):
                    if bx[0] < SAFE["x0"] - 1 or bx[2] > SAFE["x1"] + 1 or bx[1] < SAFE["y0"] - 1 or bx[3] > SAFE["y1"] + 1:
                        problems.append(f"scène {i+1} t={t:.2f} : '{lab}' ({kind}) hors zone sûre {tuple(round(v) for v in bx)}")
            for _, lab, bx in subs:
                for k2, lab2, bx2 in items:
                    if overlap(bx, bx2):
                        problems.append(f"scène {i+1} t={t:.2f} : sous-titre '{lab}' chevauche '{lab2}'")
            texts = [b for b in c.boxes if b[0] == "text"]
            for a in range(len(texts)):
                for b in range(a + 1, len(texts)):
                    if overlap(texts[a][2], texts[b][2]):
                        problems.append(f"scène {i+1} t={t:.2f} : textes '{texts[a][1]}' / '{texts[b][1]}' se chevauchent")
            for _, lab, bx in subs:
                for _, lab2, bx2 in subs:
                    if lab is not lab2 and bx < bx2 and overlap(bx, bx2, pad=10):   # tolérance = épaisseur du contour
                        problems.append(f"scène {i+1} t={t:.2f} : mots '{lab}' / '{lab2}' se chevauchent")
        # image de contrôle (fin de scène) avec zones TikTok
        c = draw_scene(i, sc["dur"] * .97)
        img = c.final()
        img.save(os.path.join(OUT, "check", f"scene_{i+1:02d}.png"))
        ov = img.copy().convert("RGBA")
        lay = Image.new("RGBA", ov.size, (0, 0, 0, 0))
        dr = ImageDraw.Draw(lay)
        dr.rectangle([0, H - 450, W, H], fill=(255, 0, 0, 70))
        dr.rectangle([W - 150, 0, W, H], fill=(255, 0, 0, 70))
        ov = Image.alpha_composite(ov, lay).convert("RGB")
        thumbs.append(ov.resize((270, 480)))
    sheet = Image.new("RGB", (270 * 5 + 40, 480 * 3 + 30), "white")
    for k, th in enumerate(thumbs):
        sheet.paste(th, (10 + (k % 5) * 274, 10 + (k // 5) * 490))
    sheet.save(os.path.join(OUT, "check", "planche_contact.png"))
    uniq = list(dict.fromkeys(problems))
    print(f"{len(uniq)} problème(s)")
    import collections
    agg = collections.Counter(re.sub(r" t=[0-9.]+", "", p) for p in uniq)
    for p in list(agg)[:80]:
        print(" -", p)
    return uniq


def render():
    os.makedirs(OUT, exist_ok=True)
    wav = os.path.join(OUT, "beat.wav")
    synth_audio(wav)
    mp4 = os.path.join(OUT, "notpetya_tiktok.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
           "-pix_fmt", "yuv420p", "-profile:v", "high", "-c:a", "aac", "-b:a", "192k", "-shortest",
           "-movflags", "+faststart", mp4]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for k, buf in enumerate(pool.imap(render_frame, range(NFRAMES), chunksize=4)):
            ff.stdin.write(buf)
            if k % 150 == 0:
                print(f"frame {k}/{NFRAMES}", flush=True)
    ff.stdin.close()
    ff.wait()
    print("OK", mp4, f"{TOTAL:.1f}s")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    if mode == "check":
        check()
    elif mode == "render":
        render()
    elif mode == "frame":
        T = float(sys.argv[2]); i, t = scene_at(T)
        draw_scene(i, t).final().save(os.path.join(OUT, "frame.png"))
