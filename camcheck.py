#!/usr/bin/env python3
"""Frames where a planet comes too close to the camera (fills the frame or
the camera passes through it). Plain Python, run before rendering."""
import math

import system as S
import timeline as TL

RATIO = 3.5  # distance / planet radius below which a planet crowds the lens


def main():
    worst = {}
    for f in range(1, TL.FRAMES + 1):
        cam, _, _ = TL.camera(f)
        for k in S.ORDER:
            r = TL.SIZE[k][f]
            if not TL.alive(k, f) or r < 0.01:
                continue
            ratio = math.dist(cam, TL.place(k, f)) / r
            if ratio < RATIO and (k not in worst or ratio < worst[k][1]):
                worst[k] = (f, ratio)
    runs = {}
    for f in range(1, TL.FRAMES + 1):
        cam, _, _ = TL.camera(f)
        hit = [k for k in S.ORDER if TL.alive(k, f) and TL.SIZE[k][f] > 0.01
               and math.dist(cam, TL.place(k, f)) / TL.SIZE[k][f] < RATIO]
        for k in hit:
            runs.setdefault(k, []).append(f)
    for k, fs in runs.items():
        print(f"{S.DISPLAY[k]:24s} frames {fs[0]}-{fs[-1]} ({TL.t_of(fs[0]):.1f}-{TL.t_of(fs[-1]):.1f} s)"
              f", closest {worst[k][1]:.2f} radii at {TL.t_of(worst[k][0]):.1f} s")
    if not runs:
        print("clear")


if __name__ == "__main__":
    main()
