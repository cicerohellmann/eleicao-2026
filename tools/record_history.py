"""Record every national TSE update into history.json and push it, so the page's
"minuto a minuto" chart shows the whole night to every visitor. Each push also
refreshes data/, a mirror of every TSE file the page reads, which the page falls
back to if TSE stops serving them.

Run:  python3 tools/record_history.py      (stops by itself when the count is final)
"""
import datetime, json, pathlib, subprocess, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "history.json"
BASE = "https://resultados.tse.jus.br/oficial"
URL = BASE + "/ele2026/6258/dados/br/br-c0001-e006258-u.json"
STATES = "ac al am ap ba ce df es go ma mg ms mt pa pb pe pi pr rj rn ro rr rs sc se sp to".split()
RUNOFF = "ac am df es rn to".split()
MIRROR = (["comum/config/ele-c.json"]
          + [f"ele2026/6258/dados/{uf}/{uf}-c0001-e006258-u.json" for uf in ["br", "zz", *STATES]]
          + [f"ele2026/6259/dados/{uf}/{uf}-c0003-e006259-u.json" for uf in STATES]
          + [f"ele2026/6260/dados/{uf}/{uf}-c0003-e006260-u.json" for uf in RUNOFF])
POLL_S, PUSH_EVERY_S = 60, 150


def num(s):
    return float(str(s).replace(",", ".")) if s not in (None, "") else 0.0


def point(d):
    dd, mm, yy = d["dt"].split("/")
    t = datetime.datetime.fromisoformat(f"{yy}-{mm}-{dd}T{d['ht']}-03:00")
    c = {}
    for a in d["carg"][0]["agr"]:
        for p in a["par"]:
            for cand in p["cand"]:
                c[cand["n"]] = round(num(cand.get("pvapn") or cand.get("pvap")), 4)
    return {"t": int(t.timestamp() * 1000), "p": round(num(d["s"].get("pstn") or d["s"]["pst"]), 4), "c": c}


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def mirror():
    for path in MIRROR:
        try:
            body = urllib.request.urlopen(f"{BASE}/{path}", timeout=20).read()
            json.loads(body)  # only keep files that parse
            f = ROOT / "data" / path
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(body)
        except Exception as e:
            print(time.strftime("%H:%M:%S"), "mirror error:", path, e)


def push(hist, note):
    OUT.write_text(json.dumps({"source": URL, "points": hist}, separators=(",", ":")))
    mirror()
    git("add", "history.json", "data")
    if git("diff", "--cached", "--quiet").returncode == 0:
        return
    git("commit", "-m", f"Record count {note}")
    git("pull", "--rebase", "-q")
    r = git("push", "-q")
    print(time.strftime("%H:%M:%S"), "pushed", note, "" if r.returncode == 0 else r.stderr.strip())


def main():
    hist = json.loads(OUT.read_text())["points"] if OUT.exists() else []
    seen = {h["t"] for h in hist}
    last_push, dirty = 0.0, False
    while True:
        try:
            d = json.load(urllib.request.urlopen(URL, timeout=20))
            pt = point(d)
            if pt["t"] not in seen:
                hist.append(pt); seen.add(pt["t"]); hist.sort(key=lambda h: h["t"]); dirty = True
            final = d.get("tf") == "s"
            if dirty and (final or time.time() - last_push >= PUSH_EVERY_S):
                push(hist, f"{d['ht']} BRT, {d['s']['pst']}% apurado"); last_push, dirty = time.time(), False
            if final:
                print("count is final, stopping"); return
        except Exception as e:  # keep recording through network hiccups
            print(time.strftime("%H:%M:%S"), "error:", e)
        time.sleep(POLL_S)


if __name__ == "__main__":
    main()
