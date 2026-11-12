# QtPass orbits

Watch the film: https://youtu.be/g7piAI_qoxE (4K)

All three films in one world: https://youtu.be/R2otmal-P-A (4K, 3:12, code in [qtpass-world](https://github.com/annejan/qtpass-world))

The source code of [QtPass](https://qtpass.org) as a solar system. Every
class is a planet, its size the lines of its `.cpp`, `.h` and `.ui`
together, circling the sun in order of age: the 2014 classes close in, the
2026 ones in a wide outer ring. A class split off another is born as that
planet's moon and drifts out to its own orbit; a class that is deleted falls
into the sun. Releases are shockwaves from the sun, and each planet is banded
by its own source: one band per stretch of lines, bright where they are long,
dark where they are short or blank.

The story is in the data. MainWindow and its dialogs formed in 2014. In
November 2016 Pass, ImitatePass and RealPass were split off MainWindow; in
2018 `datahelpers` broke into three and QtPass was split off ("It compiles,
ship it . ."). Then seven quiet years: 28 classes, 10,680 lines. In 2026 the
system nearly tripled, and on 16 and 17 September eight classes were pulled off in
two days. Today: 61 classes, 31,254 lines. MainWindow never got small; the
system grew up around it. Time in the film follows those beats, not the
calendar.

A sibling of [qtpass-strata](https://github.com/annejan/qtpass-strata) (the
history as a canyon wall) and [qtpass-city](https://github.com/annejan/qtpass-city)
(the tests as a city at night).

## Files

- `count_files.py`: lines per source file at every commit on main, the class
  names from the headers, and each class's line lengths for its bands, into
  `data/`
- `system.py`: which classes exist when, how big, which one each was split
  off, and their orbits
- `timeline.py`: the one clock (which date it is at every frame, where every
  planet is, camera path, title times) shared by the scene, the cards and the
  sound
- `build_scene.py`: builds the system in Blender and renders it, setting
  every planet, orbit, label and shockwave for each frame
- `camcheck.py`: lists frames where a planet comes too close to the camera
- `cards.py`: Lato title cards with the QtPass logo, as transparent PNGs
- `audio.py`: the soundtrack (a drone per chapter, a tick per commit, a bell
  per new class, a tearing swell per split, a falling tone per deleted class,
  a boom per release), generated with numpy and scipy
- `finish.sh`: bloom, vignette, grain, fades, titles and sound into an MP4
- `preview.py`: a flat matplotlib storyboard of the system, before any 3D

## Pipeline

```sh
python3 count_files.py ~/Projects/QtPass c8e8d2fdf     # -> data/
python3 preview.py                                     # -> preview.png
python3 camcheck.py                                    # camera clear of the planets?
blender -b --factory-startup -P build_scene.py -- --stills 121,1105,1489 --pct 25
./render_chunks.sh 1 2040 25 8 frames                  # low-res, resumes after a crash
python3 audio.py audio.wav
./finish.sh renders/frames qtpass-orbits.mp4
```

The titles are laid over the rendered frames by `finish.sh`, so another
language costs one more encode, not a render: add `cards/<lang>.json` with
the words for each card and run with `CARDS_LANG=<lang>`.

2040 frames at 24 fps (85 s), 3840x1608 (2.39:1) at 100 %. A class is a file
name without its extension, wherever it lives in the tree, outside `tests/`;
a renamed class (Dialog to ConfigDialog) stays the same planet.

Needs Blender 5.1, Python 3 with numpy, scipy, Pillow and matplotlib, and ffmpeg.
The Lato fonts come with it, in `assets/fonts/`.

## License

[REUSE](https://reuse.software) compliant; `REUSE.toml` says which file is
under which terms, the texts are in `LICENSES/`:

- the code and everything else of this film: MIT (see also `LICENSE`), so
  take it and make your own
- the Lato fonts in `assets/fonts/`: SIL Open Font License 1.1, by Łukasz
  Dziedzic
- the QtPass logo: CC0, after
  [Heart-padlock by AnonMoos](https://commons.wikimedia.org/wiki/File:Heart-padlock.svg),
  as in QtPass
- the data counted from QtPass's git history (`data/`): GPL-3.0-or-later,
  as QtPass itself
