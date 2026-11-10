"""One clock for the film: which date it is at every frame, and where every
planet is and how big.

Shared by build_scene.py (inside Blender), cards.py and audio.py. Plain
Python, no bpy.
"""
import bisect
import math
from datetime import datetime

import system as S

FPS = 24
SECONDS = 85
FRAMES = SECONDS * FPS


def ts(day):
    return datetime.fromisoformat(day).timestamp()


# The calendar: (second, date). Seven quiet years go by in a blink; the
# splits get room.
NOW = ts(datetime.fromtimestamp(S.TIMES[-1]).date().isoformat()) + 86400
KEYS = [
    (0, ts("2014-07-30")), (3, ts("2014-07-30")),      # the first commit
    (9, ts("2015-12-31")),                              # MainWindow and its dialogs
    (11, ts("2016-11-15")),
    (14, ts("2016-11-28")),                             # the first split
    (16, ts("2018-03-20")),
    (18, ts("2018-04-01")),                             # datahelpers shatters
    (19.5, ts("2018-09-20")),
    (21.5, ts("2018-10-01")),                           # QtPass pulled off
    (26, ts("2026-03-01")),                             # seven years, a blink
    (33, ts("2026-05-31")),                             # spring: growth
    (36, ts("2026-06-20")),
    (39, ts("2026-09-14")),
    (47, ts("2026-09-19")),                             # eight in two days
    (50, ts("2026-09-27")),
    (56, NOW),
    (SECONDS, NOW),
]


def _raw(sec):
    for (s0, d0), (s1, d1) in zip(KEYS, KEYS[1:]):
        if sec <= s1:
            u = min(max((sec - s0) / (s1 - s0), 0.0), 1.0)
            return d0 + (d1 - d0) * u
    return KEYS[-1][1]


def _smooth():
    half = int(0.6 * FPS)
    raw = [_raw((f - 1) / FPS) for f in range(1 - half, FRAMES + 2 + half)]
    out = [raw[half]]
    for f in range(1, FRAMES + 2):
        w = raw[f - 1:f + 2 * half]
        out.append(sum(w) / len(w))
    for f in range(2, len(out)):
        out[f] = max(out[f], out[f - 1])
    return out


DATE = _smooth()  # unix time at every frame (1-based)


def t_of(frame):
    return (frame - 1) / FPS


def date_at(frame):
    return DATE[min(max(int(frame), 1), FRAMES + 1)]


def frame_of_date(t):
    """First frame at which the calendar has reached t (the last one at most)."""
    return max(1, bisect.bisect_left(DATE, min(t, DATE[-1]), 1))


# ---------------------------------------------------------------- bodies

BIRTH = {k: frame_of_date(S.TIMES[i]) for k, i in S.BORN.items()}
DEATH = {k: frame_of_date(S.TIMES[i]) for k, i in S.DIED.items()}
DRIFT = 2.5 * FPS   # frames a split-off moon takes to reach its own orbit
FALL = 2.0 * FPS    # frames a dead class takes to fall into the sun
SPEED = 0.45        # rad/s at the innermost orbit


def _sizes():
    """Planet radius per body per frame, easing towards the lines it has."""
    out = {k: [0.0] * (FRAMES + 2) for k in S.ORDER}
    last = {k: 0.0 for k in S.ORDER}
    for f in range(1, FRAMES + 2):
        b = S.SIZES[S.sample_at(date_at(f))]
        for k in S.ORDER:
            n = b.get(k, 0)
            if not n and k in DEATH and f >= DEATH[k]:
                n = S.SIZES[S.DIED[k] - 1][k]  # keep its size while it falls
            target = S.radius(n) if n else 0.0
            last[k] += (target - last[k]) * 0.12
            out[k][f] = last[k]
    return out


SIZE = _sizes()


def lines_at(k, frame):
    return S.SIZES[S.sample_at(date_at(frame))].get(k, 0)


def _ease(u):
    u = min(max(u, 0.0), 1.0)
    return u * u * (3 - 2 * u)


def _orbit_xyz(k, r, film_s):
    a = S.PHASE[k] + film_s * SPEED * (S.ORBIT[S.ORDER[0]] / S.ORBIT[k]) ** 1.5
    tilt = S.TILT[k]
    return (r * math.cos(a), r * math.sin(a), r * math.sin(a - S.PHASE[k]) * tilt)


def place(k, frame, depth=0):
    """(x, y, z) of body k at a frame: on its orbit, still drifting off its
    donor if it was just split off, or falling into the sun if it died."""
    film_s = t_of(frame)
    r = S.ORBIT[k]
    if k in DEATH and frame >= DEATH[k]:
        r *= 1 - _ease((frame - DEATH[k]) / FALL)
    p = _orbit_xyz(k, r, film_s)
    d = S.DONOR.get(k)
    if d and depth < 3 and frame < BIRTH[k] + DRIFT:
        u = _ease((frame - BIRTH[k]) / DRIFT)
        q = place(d, frame, depth + 1)
        gap = SIZE[d][frame] + 0.35
        a = S.PHASE[k]
        moon = (q[0] + gap * math.cos(a), q[1] + gap * math.sin(a), q[2] + 0.2)
        p = tuple(moon[i] + (p[i] - moon[i]) * u for i in range(3))
    return p


def alive(k, frame):
    """0..1: how present the body is (fades in at birth, out in the sun)."""
    if frame < BIRTH[k]:
        return 0.0
    if k in DEATH and frame >= DEATH[k] + FALL:
        return 0.0
    return 1.0


def touched(k, frame):
    """0..1: a glow when the body's lines just changed (a commit landed)."""
    i = S.sample_at(date_at(frame))
    j = S.sample_at(date_at(max(frame - 6, 1)))
    if i == j:
        return 0.0
    a, b = S.SIZES[j].get(k, 0), S.SIZES[i].get(k, 0)
    return min(abs(b - a) / 40.0, 1.0) if a and b else 0.0


def releases():
    """(frame, name) for every tag, at the frame the calendar reaches it."""
    return [(frame_of_date(t), name) for name, t in S.TAGS if t <= NOW + 86400]


# ---------------------------------------------------------------- camera
# (second, camera xyz, target xyz, lens, follow): follow 0..1 pulls the
# camera along with MainWindow.
CAMERA = [
    (0.0, (0.0, -7.0, 3.2), (0.0, 0.0, 0.0), 30, 0.0),
    (3.0, (1.5, -8.0, 3.5), (0.0, 0.0, 0.0), 30, 0.0),
    (9.0, (3.0, -11.0, 5.0), (0.0, 0.0, 0.0), 28, 0.0),
    (12.5, (0.0, -9.0, 3.0), (0.0, 0.0, 0.0), 30, 1.0),     # at MainWindow, the split
    (15.0, (2.0, -16.0, 7.0), (0.0, 0.0, 0.0), 26, 0.0),
    (21.5, (4.0, -18.0, 8.0), (0.0, 0.0, 0.0), 26, 0.0),
    (26.0, (-8.0, -22.0, 9.0), (0.0, 0.0, 0.0), 24, 0.0),   # seven years
    (36.0, (-10.0, -21.0, 8.0), (0.0, 0.0, 0.0), 24, 0.0),  # growth, outward
    (40.0, (0.0, -9.0, 3.0), (0.0, 0.0, 0.0), 26, 1.0),      # down to MainWindow
    (47.0, (0.0, -9.0, 3.0), (0.0, 0.0, 0.0), 24, 1.0),      # moons tearing off
    (50.0, (2.0, -16.0, 6.0), (0.0, 0.0, 0.0), 26, 0.4),
    (60.0, (9.0, -27.0, 11.0), (0.0, 0.0, 0.0), 26, 0.0),   # the whole system
    (SECONDS, (30.0, -50.0, 8.0), (0.0, 0.0, 0.0), 28, 0.0),
]


def _hermite(ts_, vs, t):
    n = len(ts_)
    i = min(max(bisect.bisect_right(ts_, t) - 1, 0), n - 2)
    t0, t1 = ts_[i], ts_[i + 1]
    u = min(max((t - t0) / (t1 - t0), 0.0), 1.0)

    def slope(j):
        if j <= 0 or j >= n - 1:
            return 0.0
        return (vs[j + 1] - vs[j - 1]) / (ts_[j + 1] - ts_[j - 1])

    m0, m1 = slope(i) * (t1 - t0), slope(i + 1) * (t1 - t0)
    h00 = 2 * u ** 3 - 3 * u ** 2 + 1
    h10 = u ** 3 - 2 * u ** 2 + u
    h01 = -2 * u ** 3 + 3 * u ** 2
    h11 = u ** 3 - u ** 2
    return h00 * vs[i] + h10 * m0 + h01 * vs[i + 1] + h11 * m1


_CT = [k[0] for k in CAMERA]


FOLLOW = (1.2, -3.8, 1.0)  # outward, along the orbit, up: from MainWindow


def camera(frame):
    """Camera, target, lens. While following, the camera rides just outside
    MainWindow's orbit and looks in at it, the sun behind it."""
    t = t_of(frame)
    cam = [_hermite(_CT, [k[1][a] for k in CAMERA], t) for a in range(3)]
    tgt = [_hermite(_CT, [k[2][a] for k in CAMERA], t) for a in range(3)]
    lens = _hermite(_CT, [k[3] for k in CAMERA], t)
    w = min(max(_hermite(_CT, [k[4] for k in CAMERA], t), 0.0), 1.0)
    if w:
        x, y, z = place("mainwindow", frame)
        r = math.hypot(x, y)
        out, along = (x / r, y / r), (-y / r, x / r)
        fc = (x + FOLLOW[0] * out[0] + FOLLOW[1] * along[0],
              y + FOLLOW[0] * out[1] + FOLLOW[1] * along[1], z + FOLLOW[2])
        cam = [cam[a] + w * (fc[a] - cam[a]) for a in range(3)]
        tgt = [tgt[a] + w * ((x, y, z)[a] - tgt[a]) for a in range(3)]
    return tuple(cam), tuple(tgt), lens
