"""紀念頁資料：歷季排名/隊名、兩兩交手、單週紀錄、連勝連敗。不含 email 或習慣分析。"""
import json, re, sys, unicodedata
from collections import defaultdict
from pathlib import Path
A = Path(sys.argv[1])
LEAGUES = {2023: 14141, 2024: 33511, 2025: 31094}
N = lambda s: "".join(c for c in s if not c.isspace() and unicodedata.category(c) != "Co")
CLEAN = lambda s: "".join(c for c in s if unicodedata.category(c) != "Co").strip()
CATS = ["FGM", "FG%", "FT%", "3PTM", "PTS", "OREB", "REB", "AST", "ST", "BLK", "TO", "A/T"]
IDX = [0, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]
seasons, names = {}, defaultdict(dict)
wkdays = {}
cat_rows = []
for y, lid in LEAGUES.items():
    D = A/str(y)
    rows = [l.split("\t") for l in (D/"teams.txt").read_text().splitlines()[1:] if "\t" in l]
    mgr = {N(r[0]): r[1] for r in rows}
    st = (D/"standings.txt").read_text()
    top = [N(x) for x in st.split("Finished\n")[1].splitlines()[0].split("\t")[:3]]
    table = []
    for rank, name, w, l, t in re.findall(r"^\*?(\d+)\t (.*?)\t(\d+)-(\d+)-(\d+)\t", st, re.M):
        m = mgr[N(name)]; names[m][y] = CLEAN(name)
        table.append({"rank": int(rank), "team": CLEAN(name), "mgr": m, "cat": [int(w), int(l), int(t)]})
    seasons[y] = {"table": table, "podium": [mgr[n] for n in top]}
    for f in sorted((D/"matchup").glob("*.txt")):
        w = int(f.stem[1:3]); t = f.read_text()
        wkdays[(y, w)] = len(re.findall(r"^(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun) \d+/\d+", t.split("Totals")[1].split("Points")[0], re.M))
        seg = t.split("\nA/T\n", 1)[1].split("*Non-scoring")[0]
        toks = [l.strip() for l in seg.splitlines() if l.strip()]
        i = 0
        for _ in range(2):
            name = ""
            if N(toks[i]) in mgr: name = N(toks[i]); i += 1
            v = toks[i:i+14]; i += 15
            fga, (ftm, fta) = float(v[1].replace(",", "")), (float(x) for x in v[3].split("/"))
            cat_rows.append({"y": y, "w": w, "mgr": mgr[name], "team": names[mgr[name]][y], "FGA": fga, "FTM": ftm, "FTA": fta,
                             **{c: float(v[k].rstrip("*").replace(",", "")) if v[k] != "-" else None for c, k in zip(CATS, IDX)}})
games = json.load(open(A/"games.json"))
for g in games: g["days"] = wkdays[(g["y"], g["w"])]
# 連勝連敗（依季、依週次，含季後賽）
streaks = []
for y in LEAGUES:
    for m in {g["a"] for g in games if g["y"] == y} | {g["b"] for g in games if g["y"] == y}:
        seq = sorted(((g["w"], (g["sa"] - g["sb"]) * (1 if g["a"] == m else -1)) for g in games if g["y"] == y and m in (g["a"], g["b"])))
        for sign in (1, -1):
            run, start = 0, None
            for w, d in seq + [(99, 0)]:
                if d * sign > 0:
                    run += 1; start = start or w
                else:
                    if run >= 5: streaks.append({"y": y, "mgr": m, "team": names[m][y], "kind": "W" if sign > 0 else "L", "len": run, "from": start, "to": start + run - 1})
                    run, start = 0, None
streaks.sort(key=lambda s: (-s["len"], s["y"], s["from"], s["mgr"]))
# 單週類別紀錄：只算 7 天的正常週，長週另外標
recs = []
for c in CATS:
    rows = [r for r in cat_rows if r[c] is not None and wkdays[(r["y"], r["w"])] <= 7]
    best = (min if c == "TO" else max)(rows, key=lambda r: r[c])
    recs.append({"cat": c, "val": best[c], "y": best["y"], "w": best["w"], "mgr": best["mgr"], "team": best["team"]})
# 每季類別王：例行賽 7 天週；計數類取每週平均，命中率與助失比用整季加總再算
po = {(g["y"], g["w"]) for g in games if g["po"]}
reg = [r for r in cat_rows if (r["y"], r["w"]) not in po and wkdays[(r["y"], r["w"])] <= 7 and None not in (r[c] for c in CATS)]
catkings = {}
for y in LEAGUES:
    by = defaultdict(list)
    for r in reg:
        if r["y"] == y: by[r["mgr"]].append(r)
    def season_val(rs, c):
        s = lambda k: sum(r[k] for r in rs)
        if c == "FG%": return s("FGM") / s("FGA")
        if c == "FT%": return s("FTM") / s("FTA")
        if c == "A/T": return s("AST") / s("TO")
        return s(c) / len(rs)
    rows = []
    for c in CATS:
        vals = sorted(((season_val(rs, c), m) for m, rs in by.items()), reverse=c != "TO")
        rows.append({"cat": c, "top": [{"mgr": m, "val": round(v, 4)} for v, m in vals[:3]], "last": {"mgr": vals[-1][1], "val": round(vals[-1][0], 4)}})
    catkings[y] = rows
# 運氣：例行賽每週假設跟其他 13 隊都打一次（全打），比實際對戰勝場多或少
def beats(a, b):
    w = l = 0
    for c in CATS:
        if a[c] == b[c]: continue
        if (a[c] < b[c]) == (c == "TO"): w += 1
        else: l += 1
    return (w > l) - (w < l)
luck = {}
for y in LEAGUES:
    wk = defaultdict(dict)
    for r in cat_rows:
        if r["y"] == y and (y, r["w"]) not in po: wk[r["w"]][r["mgr"]] = r
    res = {}
    for w, teams in wk.items():
        for m, a in teams.items():
            d = res.setdefault(m, {"mgr": m, "w": 0, "l": 0, "t": 0, "aw": 0, "al": 0, "at": 0})
            for o, b in teams.items():
                if o != m: d[("aw", "at", "al")[1 - beats(a, b)]] += 1
    for g in games:
        if g["y"] != y or g["po"]: continue
        for m, s in ((g["a"], g["sa"] - g["sb"]), (g["b"], g["sb"] - g["sa"])):
            res[m]["w" if s > 0 else "l" if s < 0 else "t"] += 1
    for d in res.values():
        n = d["w"] + d["l"] + d["t"]
        d["exp"] = round(n * (d["aw"] + d["at"] / 2) / (d["aw"] + d["al"] + d["at"]), 1)
        d["diff"] = round(d["w"] + d["t"] / 2 - d["exp"], 1)
    luck[y] = sorted(res.values(), key=lambda d: -d["diff"])
blow = sorted(games, key=lambda g: -abs(g["sa"] - g["sb"]))[:8]
h2h = json.load(open(A/"h2h.json"))
out = {"seasons": seasons, "names": names, "h2h": {a: {b: {k: r[k] for k in ("w", "l", "t", "cw", "cl", "games")} for b, r in v.items()} for a, v in h2h.items()},
       "streaks": streaks[:12], "catrecs": recs, "catkings": catkings, "luck": luck, "blowouts": blow, "longweeks": sorted({f"{y}W{w}:{d}" for (y, w), d in wkdays.items() if d > 7})}
json.dump(out, open(sys.argv[2] if len(sys.argv) > 2 else A/"page_data.json", "w"), ensure_ascii=False)
print(json.dumps({k: out[k] for k in ("streaks", "catrecs", "longweeks")}, ensure_ascii=False, indent=0)[:3500])
print([ (g["y"],g["w"],g["a"],g["b"],g["sa"],g["sb"]) for g in blow])
