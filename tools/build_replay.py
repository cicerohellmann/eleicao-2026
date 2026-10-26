"""Condense the night's recordings into replay.json for the page's "Reviver a apuração" player.

Inputs (archive/ is local only, made by record_history.py and tools/scrape_bu.py):
  history.json        national % from 20:08 BRT (votes and flags only from ~21:16)
  archive/br/         full national file at each TSE update from 21:16
  archive/full/<t>/   every state, abroad and governor-runoff file, every ~2.5 min from 21:14
  archive/bu/<uf>.jsonl  every section's receipt time and votes, from TSE's ballot-box files
                      (arquivo-urna); before the recordings start, frames are rebuilt from these
                      minute by minute and marked "recon"
Each frame keeps only the TSE fields the page reads, in TSE's own shape, so the
page's renderers draw a replay frame exactly like a live one.

Run:  python3 tools/build_replay.py
"""
import collections, datetime, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archive"
STATES = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to".split()
RUNOFF = "ac am df es rn to".split()
STATE_STEP = 2 * 60000  # rebuilt state frames every 2 min keep replay.json to a few MB; national ones every minute
BRT = datetime.timezone(datetime.timedelta(hours=-3))


def ms(dt):
    return int(dt.timestamp() * 1000)


def tse_time(d):
    dd, mm, yy = d["dt"].split("/")
    return ms(datetime.datetime.fromisoformat(f"{yy}-{mm}-{dd}T{d['ht']}-03:00"))


def pick(d, keys):
    return {k: d[k] for k in keys if k in d}


def trim(d):
    """The fields cands(), counted(), renderHero() and renderCalc() read."""
    return {
        **pick(d, ["dt", "ht", "md", "tf"]),
        "s": pick(d.get("s", {}), ["pst", "pstn", "st", "ts"]),
        "e": pick(d.get("e", {}), ["te", "esnt", "pc", "a", "pa"]),
        "v": pick(d.get("v", {}), ["vv", "vb", "pvb", "tvn", "ptvn", "tv"]),
        "carg": [{"agr": [{"par": [{"sg": p["sg"], "cand": [pick(c, ["n", "nmu", "vap", "pvap", "pvapn", "e", "st"]) for c in p["cand"]]}
                                   for p in a["par"]]} for a in d["carg"][0]["agr"]]}],
    }


def partial(h, names):
    """A national frame from history.json alone: % and sections counted, no votes."""
    t = datetime.datetime.fromtimestamp(h["t"] / 1000, BRT)
    br = lambda x, d: f"{x:.{d}f}".replace(".", ",")
    par = [{"sg": names[n][1], "cand": [{"n": n, "nmu": names[n][0], "pvap": br(v, 2), "pvapn": br(v, 4)}]} for n, v in h["c"].items()]
    return {"dt": t.strftime("%d/%m/%Y"), "ht": t.strftime("%H:%M:%S"), "partial": 1, "s": {"pst": br(h["p"], 2), "pstn": br(h["p"], 4)},
            "carg": [{"agr": [{"par": par}]}]}


nat = {}
for f in sorted((ARCHIVE / "br").glob("*.json")):
    d = json.loads(f.read_text())
    nat[tse_time(d)] = trim(d)
last = nat[max(nat)]
names = {c["n"]: (c["nmu"], p["sg"]) for a in last["carg"][0]["agr"] for p in a["par"] for c in p["cand"]}
first = min(nat)
for h in json.loads((ROOT / "history.json").read_text())["points"]:
    if h["t"] < first: nat[h["t"]] = partial(h, names)

def br(x, d):
    return f"{x:.{d}f}".replace(".", ",")


def pc(a, b):
    return 100 * a / b if b else 0


def recon(t, tot, final):
    """A TSE-shaped frame from the sections received by time t (tot: summed section rows),
    with names, section and electorate totals from the area's final file."""
    tm = datetime.datetime.fromtimestamp(t / 1000, BRT)
    cand = [c for a in final["carg"][0]["agr"] for p in a["par"] for c in p["cand"]]
    sg = {c["n"]: p["sg"] for a in final["carg"][0]["agr"] for p in a["par"] for c in p["cand"]}
    vv = sum(tot.get(c["n"], 0) for c in cand)
    ts, te, st, apt, comp = int(final["s"]["ts"]), int(final["e"]["te"]), tot["st"], tot["apt"], tot["comp"]
    return {"dt": tm.strftime("%d/%m/%Y"), "ht": tm.strftime("%H:%M:%S"), "recon": 1,
            "s": {"pst": br(pc(st, ts), 2), "pstn": br(pc(st, ts), 4), "st": str(st), "ts": str(ts)},
            "e": {"esnt": str(te - apt), "pc": br(pc(comp, apt), 2), "a": str(apt - comp), "pa": br(pc(apt - comp, apt), 2)},
            "v": {"vv": str(vv), "vb": str(tot["br"]), "pvb": br(pc(tot["br"], comp), 2), "tvn": str(tot["nu"]), "ptvn": br(pc(tot["nu"], comp), 2), "tv": str(comp)},
            "carg": [{"agr": [{"par": [{"sg": sg[c["n"]], "cand": [{"n": c["n"], "nmu": c["nmu"], "vap": str(tot.get(c["n"], 0)),
                                                                   "pvap": br(pc(tot.get(c["n"], 0), vv), 2), "pvapn": br(pc(tot.get(c["n"], 0), vv), 4), "e": "n", "st": ""}]}]}
                                for c in cand]}]}


def read(path):
    return trim(json.loads(path.read_text())) if path.exists() else None


# a file missing from a set (TSE fetch failed that round) keeps its previous value
states, uf, gov2 = [], {}, {}
for folder in sorted((ARCHIVE / "full").iterdir()):
    base = folder / "ele2026"
    uf = {**uf, **{u: d for u in ["zz", *STATES] if (d := read(base / f"6258/dados/{u}/{u}-c0001-e006258-u.json"))}}
    gov2 = {**gov2, **{u: d for u in RUNOFF if (d := read(base / f"6260/dados/{u}/{u}-c0003-e006260-u.json"))}}
    t = ms(datetime.datetime.strptime(folder.name, "%Y%m%d-%H%M%S").replace(tzinfo=BRT))
    states.append({"t": t, "uf": uf, "gov2": gov2})

# ---- before the recordings: rebuild from each section's receipt time and ballot-box votes ----
BU = ARCHIVE / "bu"
if BU.exists():
    rows = {}  # uf -> [(t, row, governor row or None)]
    for f in sorted(BU.glob("*.jsonl")):
        rows[f.stem] = sorted(((ms(datetime.datetime.strptime(f"{r['dr']} {r['hr']}", "%d/%m/%Y %H:%M:%S").replace(tzinfo=BRT)), r, r.get("g"))
                              for r in map(json.loads, f.open()) if "hr" in r), key=lambda x: x[0])
    finals = states[-1]
    start, rec_nat, rec_uf = min(r[0][0] for r in rows.values() if r), first, states[0]["t"]
    t, k = start // 60000 * 60000 + 60000, {u: 0 for u in rows}
    sums = {u: collections.Counter() for u in rows}
    gsums = {u: collections.Counter() for u in rows}
    keys = ("apt", "comp", "br", "nu", "13", "22")
    early, seen = [], -1
    while t < rec_nat:
        for u, rs in rows.items():
            while k[u] < len(rs) and rs[k[u]][0] <= t:
                _, r, g = rs[k[u]]; k[u] += 1
                sums[u].update({"st": 1, **{x: r.get(x, 0) for x in keys}})
                if g: gsums[u].update({"st": 1, **{x: v for x, v in g.items()}})
        # minutes with no new section are skipped: from 17:07 to 19:00 none arrived
        if sum(k.values()) == seen:
            t += 60000
            continue
        seen = sum(k.values())
        tot = sum(sums.values(), collections.Counter())
        nat[t] = recon(t, tot, last)
        if t < rec_uf and (not early or t - early[-1]["t"] >= STATE_STEP):
            early.append({"t": t, "uf": {u: recon(t, sums[u], finals["uf"][u]) for u in rows if u in finals["uf"]},
                          "gov2": {u: recon(t, gsums[u], finals["gov2"][u]) for u in rows if u in finals["gov2"] and gsums[u]["st"]}})
        t += 60000
    for h in [x for x in nat if nat[x].get("partial")]: del nat[h]  # the rebuilt frames have votes; the % points don't
    states = early + states
    print(f"rebuilt {len(early)} state and {sum(1 for f in nat.values() if f.get('recon'))} national frames from {len(rows)} areas")

out = {"nat": [{"t": t, **nat[t]} for t in sorted(nat)], "states": states}
path = ROOT / "replay.json"
path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"{len(out['nat'])} national frames, {len(states)} state frames, {path.stat().st_size // 1024} KB")
