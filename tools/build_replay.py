"""Condense the night's recordings into replay.json for the page's "Reviver a apuração" player.

Inputs (archive/ is local only, made by record_history.py):
  history.json        national % from 20:08 BRT (votes and flags only from ~21:16)
  archive/br/         full national file at each TSE update from 21:16
  archive/full/<t>/   every state, abroad and governor-runoff file, every ~2.5 min from 21:14
Each frame keeps only the TSE fields the page reads, in TSE's own shape, so the
page's renderers draw a replay frame exactly like a live one.

Run:  python3 tools/build_replay.py
"""
import datetime, json, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCHIVE = ROOT / "archive"
STATES = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to".split()
RUNOFF = "ac am df es rn to".split()
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
        "e": pick(d.get("e", {}), ["esnt", "pc", "a", "pa"]),
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

out = {"nat": [{"t": t, **nat[t]} for t in sorted(nat)], "states": states}
path = ROOT / "replay.json"
path.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
print(f"{len(out['nat'])} national frames, {len(states)} state frames, {path.stat().st_size // 1024} KB")
