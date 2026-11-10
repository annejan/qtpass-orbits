"""The solar system: which bodies exist, how big, where they orbit.

A body is a class: its .cpp, .h and .ui together (MainWindow is
mainwindow.cpp + mainwindow.h + mainwindow.ui), wherever in the tree.
A renamed class (Dialog -> ConfigDialog) stays the same body. A class
that appears in the same commit as another one loses lines was split off
it: it is born as that donor's moon and drifts out to its own orbit. A
class that disappears falls into the sun.

Orbits go by age: the oldest bodies circle closest to the sun, so the
2026 classes form the outer system. Plain Python, no bpy.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
D = json.load(open(os.path.join(HERE, "data", "files.json")))
PATHS, SAMPLES = D["paths"], D["samples"]
TAGS = json.load(open(os.path.join(HERE, "data", "tags.json")))
PROFILES = json.load(open(os.path.join(HERE, "data", "profiles.json")))  # the planets' bands
TIMES = [s["t"] for s in SAMPLES]
DONOR_MIN = 40   # lines a donor must lose in the same commit
RENAMES = {"dialog": "configdialog", "progressindicator": "qprogressindicator"}


def _key(path):
    k = os.path.splitext(os.path.basename(path))[0].lower()
    return RENAMES.get(k, k)


_KEY = [_key(p) for p in PATHS]
# body -> class name as written in its header, for labels (main.cpp has none)
DISPLAY = {k: D["classes"].get(k, k) for k in _KEY}


def bodies_at_sample(i):
    b = {}
    for idx, n in SAMPLES[i]["files"].items():
        k = _KEY[int(idx)]
        b[k] = b.get(k, 0) + n
    return b


SIZES = [bodies_at_sample(i) for i in range(len(SAMPLES))]


def _history():
    born, died, donor = {}, {}, {}
    prev = {}
    for i, b in enumerate(SIZES):
        for k in b:
            if k not in prev and k not in born:
                born[k] = i
                if prev:
                    loss = {j: prev[j] - b.get(j, 0) for j in prev if prev[j] - b.get(j, 0) > 0}
                    if loss:
                        j = max(loss, key=loss.get)
                        if loss[j] >= DONOR_MIN:
                            donor[k] = j
        for k in prev:
            if k not in b:
                died[k] = i
        prev = b
    return born, died, donor


BORN, DIED, DONOR = _history()
ORDER = sorted(BORN, key=lambda k: (BORN[k], -SIZES[BORN[k]][k]))
# Orbit radius by age, packed tighter where many were born together.
ORBIT = {k: 4.2 + 1.25 * math.sqrt(n) * 1.6 for n, k in enumerate(ORDER)}
PHASE = {k: (n * 2.39996) % (2 * math.pi) for n, k in enumerate(ORDER)}  # golden angle
TILT = {k: 0.07 * math.sin(n * 1.7) for n, k in enumerate(ORDER)}  # a slight inclination


def sample_at(t):
    """Index of the last sample at or before unix time t."""
    import bisect
    return max(bisect.bisect(TIMES, t) - 1, 0)


def radius(lines):
    """Planet radius from its size: volume grows with the lines."""
    return 0.06 * lines ** (1 / 3)


def angle(k, film_s):
    """Orbital angle: Kepler-ish, outer bodies slower, by film time."""
    r = ORBIT[k]
    return PHASE[k] + film_s * 0.9 * (3.0 / r) ** 1.5


def position(k, film_s):
    a = angle(k, film_s)
    return ORBIT[k] * math.cos(a), ORBIT[k] * math.sin(a)
