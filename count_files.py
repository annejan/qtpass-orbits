#!/usr/bin/env python3
"""Lines per source file over QtPass's history.

count_files.py QTPASS_REPO [REV] [OUTDIR]   -> OUTDIR/files.json, tags.json

Sampled at every first-parent commit up to REV. A source file is a .cpp,
.h or .ui outside tests/ (the app, not its tests: those were the city).
Blobs repeat between commits, so each is counted once.

files.json: {"paths": [path, ...], "classes": {basename: ClassName},
             "samples": [{"t": unix, "rev": sha, "subject": s,
                          "files": {path_index: lines}}, ...]}
tags.json: [[tag, unix], ...] for every v* tag up to REV, oldest first.
profiles.json: {basename: [512 mean line lengths, 0..1]}, the planets' bands.
"""
import json
import os
import re
import subprocess
import sys

REPO = sys.argv[1] if len(sys.argv) > 1 else os.path.expanduser("~/Projects/QtPass")
REV = sys.argv[2] if len(sys.argv) > 2 else "refs/heads/main"
OUT = sys.argv[3] if len(sys.argv) > 3 else "data"
SOURCE = re.compile(r"\.(cpp|h|ui)$")
PROFILE = 512  # bands of line length per planet, pole to pole


def git(*a):
    return subprocess.run(["git", "-C", REPO, *a], capture_output=True, text=True,
                          errors="replace").stdout


class Lines:
    """Line counts of blobs, through one long-running cat-file."""

    def __init__(self):
        self.p = subprocess.Popen(["git", "-C", REPO, "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        self.seen = {}

    def __call__(self, blob):
        if blob not in self.seen:
            self.p.stdin.write(blob.encode() + b"\n")
            self.p.stdin.flush()
            size = int(self.p.stdout.readline().split()[2])
            data = self.p.stdout.read(size + 1)[:size]
            self.seen[blob] = data.count(b"\n") + (0 if data.endswith(b"\n") or not data else 1)
        return self.seen[blob]


def main():
    log = git("log", "--first-parent", "--reverse", "--format=%H%x09%ct%x09%s", REV)
    lines, paths, index, samples, headers, last_blob = Lines(), [], {}, [], {}, {}
    for row in log.split("\n"):
        if not row.strip():
            continue
        sha, t, subject = row.split("\t", 2)
        files = {}
        for entry in git("ls-tree", "-r", sha).split("\n"):
            if not entry:
                continue
            meta, path = entry.split("\t", 1)
            if path.startswith("tests/") or not SOURCE.search(path):
                continue
            if path not in index:
                index[path] = len(paths)
                paths.append(path)
            files[index[path]] = lines(meta.split()[2])
            last_blob[path] = meta.split()[2]
            if path.endswith(".h"):
                headers[path] = meta.split()[2]
        samples.append({"t": int(t), "rev": sha[:9], "subject": subject, "files": files})
    # the class name each header declares, as written (MainWindow, not mainwindow)
    classes = {}
    for path, blob in headers.items():
        base = os.path.splitext(os.path.basename(path))[0]
        for name in re.findall(r"^\s*(?:class|struct)\s+(?:\w+_EXPORT\s+)?(\w+)\b[^;]*$",
                               git("cat-file", "-p", blob), re.M):
            if name.lower() == base.lower():
                classes[base.lower()] = name
    # the texture of each planet: the lengths of its lines, .cpp then .h then
    # .ui, at the last commit the file existed, squeezed into PROFILE bands
    bodies = {}
    for path in sorted(last_blob, key=lambda p: (".cpp", ".h", ".ui").index(os.path.splitext(p)[1])):
        k = os.path.splitext(os.path.basename(path))[0].lower()
        text = git("cat-file", "-p", last_blob[path]).expandtabs(4)
        bodies.setdefault(k, []).extend(len(l.rstrip()) for l in text.split("\n"))
    profiles = {}
    for k, ls in bodies.items():
        out = []
        for b in range(PROFILE):
            chunk = ls[b * len(ls) // PROFILE:max((b + 1) * len(ls) // PROFILE, b * len(ls) // PROFILE + 1)]
            out.append(round(min(sum(chunk) / len(chunk) / 80.0, 1.0), 3))
        profiles[k] = out
    os.makedirs(OUT, exist_ok=True)
    json.dump(profiles, open(os.path.join(OUT, "profiles.json"), "w"))
    json.dump({"paths": paths, "samples": samples, "classes": classes}, open(os.path.join(OUT, "files.json"), "w"))
    end = samples[-1]["t"]
    tags = git("for-each-ref", "--sort=creatordate",
               "--format=%(refname:short) %(creatordate:unix)", "refs/tags").split("\n")
    json.dump([[n, int(t)] for n, t in (l.split() for l in tags if l.startswith("v"))
               if int(t) <= end + 2 * 86400],
              open(os.path.join(OUT, "tags.json"), "w"))
    last = samples[-1]["files"]
    print(len(samples), "samples,", len(paths), "paths,", len(last), "files and",
          sum(last.values()), "lines at", REV)


if __name__ == "__main__":
    main()
