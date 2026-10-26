"""Per-section receipt time (aux hr, Brasília) + presidential votes (decoded BU) for TSE pleito 3221.
Writes bu/<uf>.jsonl, resumable. Usage: python3 -I scrape_bu.py <scratch> <workers> <req/s> uf..."""
import http.client, json, os, sys, time, urllib.request, concurrent.futures as cf, threading
SP, W, RATE, UFS = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), sys.argv[4:]
HOST, TL, NEXT = "resultados.tse.jus.br", threading.local(), [0.0]


class HTTPError(Exception):
    def __init__(self, code): self.code = code


def fetch(url):
    """GET over this thread's kept-alive connection, at most RATE requests a second overall."""
    with LOCK:
        now = time.time(); NEXT[0] = max(NEXT[0] + 1 / RATE, now); wait = NEXT[0] - now
    time.sleep(wait)
    if not getattr(TL, "c", None): TL.c = http.client.HTTPSConnection(HOST, timeout=40)
    try:
        TL.c.request("GET", url.split(HOST, 1)[1]); r = TL.c.getresponse(); b = r.read()
    except Exception:
        TL.c.close(); TL.c = None; raise
    if r.status != 200: raise HTTPError(r.status)
    return b
RUNOFF = "ac am df es rn to".split()
B = "https://resultados.tse.jus.br/oficial/ele2026/arquivo-urna/3221/dados"

def tlv(b, i):
    t = b[i]; i += 1; tag = t & 0x1f
    if tag == 0x1f:
        tag = 0
        while True:
            x = b[i]; i += 1; tag = tag * 128 + (x & 0x7f)
            if not x & 0x80: break
    l = b[i]; i += 1
    if l & 0x80:
        n = l & 0x7f; l = int.from_bytes(b[i:i + n], "big"); i += n
    return (t >> 6, tag, bool(t & 0x20)), b[i:i + l], i + l

def tree(b):
    out, i = [], 0
    while i < len(b):
        k, v, i = tlv(b, i)
        if k[2]: out.append((k, tree(v)))
        elif k == (0, 4, False) and v[:1] == b"\x30":  # the envelope's OCTET STRING holds the BU; a hash may also start with 0x30
            try: out.append((k, tree(v)))
            except IndexError: out.append((k, v))
        else: out.append((k, v))
    return out

def num(v): return int.from_bytes(v, "big", signed=True)

def find_ele(n, ele):
    """The resultadoVotacaoPorEleicao SEQUENCE whose first INTEGER is ele."""
    if isinstance(n, list):
        if n and n[0][0] == (0, 2, False) and num(n[0][1]) == ele and len(n) >= 5: return n
        for k, v in n:
            r = find_ele(v, ele)
            if r: return r

def votes(t, ele):
    r = find_ele(t, ele)
    if not r: return None
    apt = num(r[1][1])
    res = r[4][1][0][1]                       # resultadosVotacao[0]
    comp = num(res[1][1])
    out = {"apt": apt, "comp": comp}
    for k, v in res[2][1][0][1][2][1]:        # totaisVotosCargo[0].votosVotaveis
        d = {kk[:2]: vv for kk, vv in v}         # context tags [2:1] tipo, [2:2] qtd, [2:3] (partido, codigo)
        tipo, q = num(d[2, 1]), num(d[2, 2])
        key = str(num(d[2, 3][1][1])) if tipo == 1 else {2: "br", 3: "nu"}.get(tipo, f"t{tipo}")
        out[key] = out.get(key, 0) + q
    return out

LOCK, BACK = threading.Lock(), [30]
PAUSE = [0.0]  # on a 429 every worker waits; the pause doubles while TSE keeps refusing


def get(url, tries=6):
    a = 0
    while a < tries:
        while time.time() < PAUSE[0]: time.sleep(1)
        try:
            r = fetch(url); BACK[0] = 30; return r
        except HTTPError as e:
            if e.code == 404: return None
            if e.code == 429:
                with LOCK:
                    if time.time() >= PAUSE[0]:
                        BACK[0] = min(BACK[0] * 2, 900); PAUSE[0] = time.time() + BACK[0]
                        print(f"429, pausing {BACK[0]}s", flush=True)
                continue
            a += 1; time.sleep(2 * a)
        except Exception: a += 1; time.sleep(2 * a)
    raise RuntimeError(url)

def one(u, m, z, s):
    base = f"{B}/{u}/{m}/{z}/{s}"
    a = get(f"{base}/p003221-{u}-m{m}-z{z}-s{s}-aux.json")
    if a is None: return {"k": f"{m}-{z}-{s}", "miss": "aux"}
    a = json.loads(a)
    h = [x for x in a.get("hashes", []) if any(f["tp"] == "bu" for f in x.get("arq", []))]
    if not h: return {"k": f"{m}-{z}-{s}", "miss": "hash", "st": a.get("st")}
    h = h[-1]; nm = next(f["nm"] for f in h["arq"] if f["tp"] == "bu")
    bu = get(f"{base}/{h['hash']}/{nm}")
    if bu is None: return {"k": f"{m}-{z}-{s}", "miss": "bu"}
    t = tree(bu); g = votes(t, 6260) if u in RUNOFF else None
    return {"k": f"{m}-{z}-{s}", "dr": h["dr"], "hr": h["hr"], "st": h["st"], "n": len(a["hashes"]), **votes(t, 6258), **({"g": g} if g else {})}

os.makedirs(f"{SP}/bu", exist_ok=True)
for u in UFS:
    csf = f"{SP}/cs/{u}.json"
    if not os.path.exists(csf):  # the section list: config/<uf>/<uf>-p003221-cs.json
        os.makedirs(f"{SP}/cs", exist_ok=True)
        open(csf, "wb").write(get(f"https://{HOST}/oficial/ele2026/arquivo-urna/3221/config/{u}/{u}-p003221-cs.json"))
    cs = json.load(open(csf))
    jobs = [(u, m["cd"], z["cd"], s["ns"]) for a in cs["abr"] for m in a["mu"] for z in m["zon"] for s in z["sec"] if "da" in s]
    path = f"{SP}/bu/{u}.jsonl"
    done = {json.loads(l)["k"] for l in open(path)} if os.path.exists(path) else set()
    jobs = [j for j in jobs if f"{j[1]}-{j[2]}-{j[3]}" not in done]
    lock, f, t0, n = threading.Lock(), open(path, "a"), time.time(), 0
    with cf.ThreadPoolExecutor(W) as ex:
        futs = [ex.submit(one, *j) for j in jobs]
        for fu in cf.as_completed(futs):
            try: r = fu.result()
            except Exception as e:
                j = jobs[futs.index(fu)]; print("ERR", j, repr(e), flush=True)
                r = {"k": f"{j[1]}-{j[2]}-{j[3]}", "miss": "err", "e": repr(e)[:80]}
            f.write(json.dumps(r) + "\n"); n += 1
            if n % 5000 == 0: f.flush(); print(u, n, len(jobs), f"{time.time() - t0:.0f}s", flush=True)
    f.close(); print(u, "done", n, f"{time.time() - t0:.0f}s", flush=True)
