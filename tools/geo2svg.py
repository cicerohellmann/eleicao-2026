import json, math, sys
src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src))
W = 600
# equirectangular with cos(lat) correction around -15°
k = math.cos(math.radians(15))
minx, maxx, miny, maxy = -74.1, -28.6, -33.8, 5.4
sx = W / ((maxx - minx) * k)
H = round((maxy - miny) * sx)
def P(lon, lat): return ((lon - minx) * k * sx, (maxy - lat) * sx)
def simplify(ring, tol):
    if len(ring) < 4: return ring
    x0, y0 = ring[0]
    m = max(range(len(ring)), key=lambda i: (ring[i][0]-x0)**2 + (ring[i][1]-y0)**2)
    return line(ring[:m+1], tol)[:-1] + line(ring[m:], tol)
def line(pts, tol):
    if len(pts) < 3: return pts
    def rdp(a, b):
        (x1, y1), (x2, y2) = pts[a], pts[b]
        dx, dy = x2 - x1, y2 - y1; L = math.hypot(dx, dy) or 1e-9
        best, idx = 0, -1
        for i in range(a + 1, b):
            x, y = pts[i]; dist = abs(dy * x - dx * y + x2 * y1 - y2 * x1) / L
            if dist > best: best, idx = dist, i
        if best > tol: return rdp(a, idx)[:-1] + rdp(idx, b)
        return [pts[a], pts[b]]
    return rdp(0, len(pts) - 1)
res = {}
for f in d['features']:
    g = f['geometry']; polys = g['coordinates'] if g['type'] == 'MultiPolygon' else [g['coordinates']]
    parts = []; cx = cy = n = 0
    for poly in polys:
        ring = [P(*c) for c in poly[0]]
        for x, y in ring: cx += x; cy += y; n += 1
        s = simplify(ring, 0.6)
        if len(s) < 4: s = simplify(ring, 0.05)
        if len(s) < 4: continue
        parts.append('M' + 'L'.join(f'{x:.1f},{y:.1f}' for x, y in s) + 'Z')
    res[f['properties']['sigla'].lower()] = {'d': ''.join(parts), 'c': [round(cx / n, 1), round(cy / n, 1)]}
json.dump({'w': W, 'h': H, 's': res}, open(out, 'w'), separators=(',', ':'))
print(W, H, sum(len(v['d']) for v in res.values()))
