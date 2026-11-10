#!/usr/bin/env python3
"""The soundtrack, generated from the same clock as the picture.

audio.py [OUT.wav]   (default audio.wav; 48 kHz stereo, SECONDS long)

A deep space drone that changes chord with each chapter, a faint tick for
every commit as it lands (so the quiet years go quiet and 2026 turns to
rain), a bell when a class is born (low for the inner planets, high for
the outer ones), a tearing swell when one splits off another, a falling
tone when one falls into the sun, a soft boom for every release's
shockwave, and a riser into the eight splits of 16 and 17 September.
"""
import random
import sys
import wave

import numpy as np
from scipy import signal

import system as S
import timeline as TL

SR = 48000
N = TL.SECONDS * SR
T = np.arange(N) / SR
rng = np.random.default_rng(2014)
rnd = random.Random(31254)
# the last of the eight splits of 16 and 17 September
CLIMAX = max(TL.t_of(TL.BIRTH[k]) for k, d in S.DONOR.items()
             if S.TIMES[S.BORN[k]] < TL.ts("2026-09-18"))


def lowpass(x, hz, order=2):
    b, a = signal.butter(order, hz / (SR / 2))
    return signal.lfilter(b, a, x)


def bandpass(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band")
    return signal.lfilter(b, a, x)


def hz(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def keyed(keys):
    """Smoothstep between (second, value) keys, at every sample."""
    grid = np.arange(0, TL.SECONDS + 1, 0.05)
    vals = []
    for t in grid:
        v = keys[-1][1]
        for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
            if t <= t1:
                u = min(max((t - t0) / (t1 - t0), 0.0), 1.0)
                v = v0 + (v1 - v0) * u * u * (3 - 2 * u)
                break
        vals.append(v)
    return np.interp(T, grid, vals)


def add(i, g, pan=0.5, amp=1.0):
    """Mix mono g into out at sample i, panned 0 (left) .. 1 (right)."""
    if i >= N:
        return
    j = min(i + len(g), N)
    out[i:j, 0] += g[:j - i] * amp * (1 - pan)
    out[i:j, 1] += g[:j - i] * amp * pan


def pan_of(k):
    return 0.5 + 0.35 * np.sin(S.PHASE[k])


out = np.zeros((N, 2))

# ---------------------------------------------------------------- drone
CHORDS = [  # (from second, MIDI notes)
    (0, [38, 45, 50, 53]),         # Dm: the system forms
    (10.5, [34, 41, 46, 50]),      # Bb: the first split
    (15.5, [36, 43, 48, 52]),      # C: 2018
    (22.5, [38, 45, 52]),          # sparse: the quiet years
    (26.5, [34, 41, 46, 50, 53]),  # Bb: spring 2026
    (36.0, [36, 43, 48, 52, 55]),  # C: September builds
    (CLIMAX, [38, 45, 50, 54, 57]),  # D major: the splits
    (58.0, [38, 45, 52, 54, 57]),  # Dsus2/6: today
]
drone = np.zeros(N)
fade = int(2.0 * SR)
for n, (t0, notes) in enumerate(CHORDS):
    t1 = CHORDS[n + 1][0] if n + 1 < len(CHORDS) else TL.SECONDS
    a, b = int(t0 * SR), min(int(t1 * SR) + fade, N)
    tt = T[a:b]
    g = np.ones(b - a)
    g[:fade] = np.linspace(0, 1, fade) ** 1.5
    if b < N:
        g[-fade:] *= np.linspace(1, 0, fade) ** 1.5
    for note in notes:
        for h, amp in ((1, 1.0), (2, 0.25), (3, 0.08)):
            for det in (-0.4, 0.4):
                drone[a:b] += np.sin(2 * np.pi * (hz(note) * h + det) * tt
                                     + rng.uniform(0, 6.28)) * amp * g
drone = lowpass(drone, 1200) / 30
level = keyed([(0, 0), (3, 0.45), (22.5, 0.4), (26.5, 0.5), (CLIMAX - 0.3, 0.7),
               (CLIMAX + 0.2, 1.0), (60, 0.75), (TL.SECONDS - 4, 0.6), (TL.SECONDS, 0)])
out[:, 0] += drone * level
out[:, 1] += np.roll(drone, 300) * level
# the hiss of space, a little louder as the system fills
space = lowpass(rng.standard_normal(N), 700, 2)
out[:, 0] += space * 0.012
out[:, 1] += np.roll(space, 997) * 0.012

# ---------------------------------------------------------------- commits
# A tick for every commit on main as the calendar passes it.
landed = []
prev = S.sample_at(TL.date_at(1))
for f in range(2, TL.FRAMES + 1):
    cur = S.sample_at(TL.date_at(f))
    landed += [f] * (cur - prev)
    prev = cur
per_sec = np.zeros(TL.SECONDS + 1)
for f in landed:
    per_sec[min(int(TL.t_of(f)), TL.SECONDS)] += 1
L = int(0.08 * SR)
tg = np.arange(L) / SR
PENTA = [74, 76, 78, 81, 83, 86, 88, 90]  # D major pentatonic, high
for f in landed:
    t = TL.t_of(f) + rnd.uniform(0, 1 / TL.FPS)
    fr = hz(rnd.choice(PENTA)) * 2
    g = np.sin(2 * np.pi * fr * tg) * np.exp(-tg * 70) * (1 - np.exp(-tg * 3000))
    amp = 0.05 / np.sqrt(max(per_sec[min(int(t), TL.SECONDS)], 1))
    add(int(t * SR), g, rnd.uniform(0.15, 0.85), amp)


# ---------------------------------------------------------------- births
def bell(t, f0, amp, pan=0.5, decay=3.0):
    i = int(t * SR)
    L = min(int(decay * 2.5 * SR), N - i)
    if L <= 0:
        return
    tt = np.arange(L) / SR
    g = sum(a * np.sin(2 * np.pi * f0 * p * tt) * np.exp(-tt * (1 + p) / decay)
            for p, a in ((1, 1), (2.76, 0.4), (5.4, 0.18), (8.9, 0.07)))
    add(i, g, pan, amp)


R = max(S.ORBIT.values())
for k in S.ORDER:
    t = TL.t_of(TL.BIRTH[k])
    # inner orbits low, outer ones high, on the D major pentatonic
    steps = [50, 52, 54, 57, 59, 62, 64, 66, 69, 71, 74, 76, 78, 81]
    note = steps[int((S.ORBIT[k] - 4.2) / (R - 4.2) * (len(steps) - 1))]
    big = min(S.SIZES[-1].get(k, 300) / 1500, 1.0)
    if k in S.DONOR:
        # torn off its donor: a swell of filtered noise, then the bell
        Ls = int(1.2 * SR)
        ts_ = np.arange(Ls) / SR
        sw = bandpass(rng.standard_normal(Ls), 300, 2500) * np.sin(np.pi * ts_ / 1.2) ** 2
        sweep = np.sin(2 * np.pi * np.cumsum(90 + 140 * ts_ / 1.2) / SR) * np.sin(np.pi * ts_ / 1.2) ** 2
        add(int(max(t - 0.6, 0) * SR), sw * 0.05 + sweep * 0.08, pan_of(k))
    bell(t, hz(note), 0.05 + 0.07 * big, pan_of(k), decay=2.0 + 2.5 * big)

# ---------------------------------------------------------------- deaths
for k, f in TL.DEATH.items():
    t = TL.t_of(f)
    Lf = int(TL.FALL / TL.FPS * SR)
    tf = np.arange(Lf) / SR
    fr = 330 * np.exp(-tf * 1.2)
    g = np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.exp(-tf * 1.0) * (1 - np.exp(-tf * 40))
    add(int(t * SR), g, pan_of(k), 0.06)

# ---------------------------------------------------------------- releases
for f0, name in TL.releases():
    t = TL.t_of(f0)
    big = "rc" not in name and "beta" not in name
    Lb = int(2.5 * SR)
    tb = np.arange(Lb) / SR
    fb = 42 * np.exp(-tb * 0.7) + 30
    boom = np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tb * 1.8) * (1 - np.exp(-tb * 200))
    shimmer = bandpass(rng.standard_normal(Lb), 3000, 9000) * np.exp(-tb * 2.5) * 0.15
    add(int(t * SR), boom * (0.25 if big else 0.14) + shimmer * (0.6 if big else 0.3),
        rnd.uniform(0.4, 0.6))

# ---------------------------------------------------------------- September
rise = keyed([(0, 0), (39.5, 0), (CLIMAX - 0.05, 1), (CLIMAX + 0.3, 0), (TL.SECONDS, 0)])
noise = bandpass(rng.standard_normal(N), 400, 6000)
for ch in range(2):
    out[:, ch] += np.roll(noise, ch * 37) * rise ** 2 * 0.045
i = int(CLIMAX * SR)
Lb = int(3.0 * SR)
tb = np.arange(Lb) / SR
fb = 48 * np.exp(-tb * 0.8) + 30
boom = np.sin(2 * np.pi * np.cumsum(fb) / SR) * np.exp(-tb * 1.4) * (1 - np.exp(-tb * 300))
add(i, boom, 0.5, 0.9)
bell(CLIMAX, hz(74), 0.14, 0.45, decay=5)
bell(CLIMAX + 0.02, hz(78), 0.09, 0.55, decay=5)
bell(CLIMAX + 0.04, hz(81), 0.07, 0.5, decay=5)

# ---------------------------------------------------------------- room
ir_len = int(2.8 * SR)
ti = np.arange(ir_len) / SR
wet = np.zeros_like(out)
for ch in range(2):
    ir = lowpass(rng.standard_normal(ir_len) * np.exp(-ti * 2.2), 4500)
    ir /= np.sqrt(np.sum(ir ** 2))
    wet[:, ch] = signal.fftconvolve(out[:, ch], ir)[:N]
mix = out * 0.75 + wet * 0.4
mix *= (np.minimum(T / 0.5, 1) * np.clip((TL.SECONDS - T) / 3.0, 0, 1))[:, None]
mix = np.tanh(mix / np.max(np.abs(mix)) * 1.4) / np.tanh(1.4) * 0.9

path = sys.argv[1] if len(sys.argv) > 1 else "audio.wav"
with wave.open(path, "wb") as w:
    w.setnchannels(2)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes((mix * 32767).astype("<i2").tobytes())
print("wrote", path, f"{TL.SECONDS} s,", len(landed), "commits,", len(S.ORDER), "births,",
      len(TL.DEATH), "deaths,", len(TL.releases()), "releases, climax at", round(CLIMAX, 2), "s")
