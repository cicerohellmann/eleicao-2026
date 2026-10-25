"""Recompute each state's label point ("c" in brmap.json) from the drawn paths.

Uses the pole of inaccessibility of the state's largest polygon: the interior
point farthest from any edge, so the label sits in the middle of the
clickable shape even for concave states. Run after geo2svg.py.
"""
import json, math, re
from pathlib import Path

root = Path(__file__).resolve().parent.parent
path = root / "brmap.json"
m = json.loads(path.read_text())

def rings(d):
    for sub in re.findall(r"M([^Z]+)Z", d):
        yield [tuple(map(float, p.split(","))) for p in sub.split("L")]

def area(r):
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]))) / 2

def inside(x, y, r):
    hit = False
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        if (y1 > y) != (y2 > y) and x < x1 + (y - y1) * (x2 - x1) / (y2 - y1):
            hit = not hit
    return hit

def edge_dist(x, y, r):
    best = math.inf
    for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
        dx, dy = x2 - x1, y2 - y1
        t = max(0, min(1, ((x - x1) * dx + (y - y1) * dy) / (dx * dx + dy * dy or 1e-9)))
        best = min(best, math.hypot(x - x1 - t * dx, y - y1 - t * dy))
    return best

def pole(r):
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    step = max(x1 - x0, y1 - y0) / 24
    best, bx, by = -1, (x0 + x1) / 2, (y0 + y1) / 2
    cx, cy, span = bx, by, max(x1 - x0, y1 - y0) / 2
    while step > 0.05:  # coarse grid, then refine around the best point
        for i in range(-24, 25):
            for j in range(-24, 25):
                x, y = cx + i * step, cy + j * step
                if x0 <= x <= x1 and y0 <= y <= y1 and inside(x, y, r):
                    dd = edge_dist(x, y, r)
                    if dd > best: best, bx, by = dd, x, y
        cx, cy, step = bx, by, step / 6
    return bx, by

for code, s in m["s"].items():
    r = max(rings(s["d"]), key=area)
    x, y = pole(r)
    s["c"] = [round(x, 1), round(y, 1)]
    print(code, s["c"])

path.write_text(json.dumps(m, separators=(",", ":")))
