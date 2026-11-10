#!/usr/bin/env python3
"""A flat storyboard before any 3D: the sizes over time, and the system
seen from above at the moments the film would slow down for.

preview.py [OUT.png]   (default preview.png)
"""
import datetime as dt
import math
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle

import system as S

BG, INK, DIM = "#05060d", "#e8eef8", "#59607a"
ERA = [(2014, "#ffcf6b"), (2016, "#ff9a5c"), (2018, "#e86a8f"), (2019, "#9b7cff"), (2026, "#5fd4ff")]


def era_colour(k):
    y = dt.datetime.fromtimestamp(S.TIMES[S.BORN[k]]).year
    c = ERA[0][1]
    for y0, col in ERA:
        if y >= y0:
            c = col
    return c


def ts(s):
    return dt.datetime.fromisoformat(s).timestamp()


MOMENTS = [
    ("2015-12-31T23:59", "end of 2015", "MainWindow and its dialogs"),
    ("2016-11-23T23:59", "23 November 2016", "Pass, ImitatePass and RealPass torn off MainWindow"),
    ("2018-09-25T23:59", "25 September 2018", "QtPass torn off: \"It compiles, ship it . .\""),
    ("2025-12-31T23:59", "end of 2025", "seven quiet years: 28 classes, 10,680 lines"),
    ("2026-09-17T23:59", "17 September 2026", "eight classes pulled off in two days"),
    (None, "today", "61 classes, 31,254 lines"),
]


def draw_system(ax, t, title, sub, film_s):
    i = S.sample_at(t) if t else len(S.SAMPLES) - 1
    b = S.SIZES[i]
    ax.set_facecolor(BG)
    ax.add_patch(Circle((0, 0), 1.1, color="#fff3c4", zorder=3))
    ax.add_patch(Circle((0, 0), 1.9, color="#ffcf6b", alpha=0.18, zorder=2))
    for k, n in b.items():
        r = S.ORBIT[k]
        ax.add_patch(Circle((0, 0), r, fill=False, lw=0.4, color=DIM, alpha=0.5, zorder=1))
        x, y = S.position(k, film_s)
        fresh = S.DONOR.get(k) and S.TIMES[i] - S.TIMES[S.BORN[k]] < 3 * 86400
        if fresh:  # still a moon: drawn beside its donor, with the pull
            dx, dy = S.position(S.DONOR[k], film_s)
            ang = S.PHASE[k]
            mx, my = dx + 1.2 * math.cos(ang), dy + 1.2 * math.sin(ang)
            ax.annotate("", (x, y), (mx, my), arrowprops=dict(arrowstyle="->", color=INK, lw=0.6, alpha=0.6))
            x, y = mx, my
        rad = S.radius(n) * 1.6
        ax.add_patch(Circle((x, y), rad, color=era_colour(k), zorder=5,
                            ec="white" if k == "mainwindow" else "none", lw=1.2))
        if n > 600 or k == "mainwindow" or fresh:
            ax.text(x, y - rad - 0.35, S.DISPLAY[k], color=INK, fontsize=5.5, ha="center", va="top", zorder=6)
    lim = 20.0
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(f"{title}\n{sub}", color=INK, fontsize=8, loc="left")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "preview.png"
    fig = plt.figure(figsize=(15, 13), facecolor=BG)
    gs = fig.add_gridspec(3, 3, height_ratios=[1, 1.15, 1.15], hspace=0.25, wspace=0.05)

    ax = fig.add_subplot(gs[0, :])
    ax.set_facecolor(BG)
    days = [dt.datetime.fromtimestamp(t) for t in S.TIMES]
    total = [sum(b.values()) for b in S.SIZES]
    mw = [b.get("mainwindow", 0) for b in S.SIZES]
    count = [len(b) for b in S.SIZES]
    ax.fill_between(days, total, color="#5fd4ff", alpha=0.25, step="post")
    ax.plot(days, total, color="#5fd4ff", lw=1, drawstyle="steps-post", label="all classes (lines)")
    ax.plot(days, mw, color="white", lw=1.2, drawstyle="steps-post", label="MainWindow (lines)")
    ax2 = ax.twinx()
    ax2.plot(days, count, color="#ffcf6b", lw=0.8, drawstyle="steps-post", label="classes")
    ax2.set_ylim(0, 70)
    for k, d in S.DONOR.items():
        if d == "mainwindow":
            x = days[S.BORN[k]]
            ax.axvline(x, color="white", lw=0.4, alpha=0.4)
    for k, i in S.DIED.items():
        ax.plot(days[i], 0, marker="v", color="#e86a8f", ms=4)
    for a, (axis, lab) in enumerate(((ax, "lines"), (ax2, "classes"))):
        axis.tick_params(colors=DIM, labelsize=7)
        axis.set_ylabel(lab, color=DIM, fontsize=7)
        for sp in axis.spines.values():
            sp.set_color(DIM)
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=7, facecolor=BG, labelcolor=INK, edgecolor=DIM)
    ax.set_title("QtPass as a solar system: every class a planet, sized by its lines; "
                 "white lines = classes split off MainWindow, red = classes that died",
                 color=INK, fontsize=9, loc="left")

    for n, (t, title, sub) in enumerate(MOMENTS):
        a = fig.add_subplot(gs[1 + n // 3, n % 3])
        draw_system(a, ts(t) if t else None, title, sub, film_s=n * 9.0)
    fig.text(0.13, 0.035, "born:", color=DIM, fontsize=7)
    for n, (y, c) in enumerate(ERA):
        fig.text(0.16 + n * 0.06, 0.035, ("%d+" % y) if n == len(ERA) - 1 else f"{y}", color=c, fontsize=7)
    fig.savefig(out, dpi=110, facecolor=BG)
    print("wrote", out)


if __name__ == "__main__":
    main()
