"""FONTE-1 — F2: probes da camada de aquisição externa (prereg 27ebff9 §3).

Teto 30 chamadas; TODAS logadas em experiments/fonte-1/probe_log.md
(APPEND-only). Bit-idêntico NÃO se aplica a rede — o hash por chamada é o
registro da variabilidade. Máx 2 retries por probe (contam no teto).

PROBE-A (fastf1.ergast 3.8.3 pinada): get_circuits(2024);
  get_race_schedule(2024) → round de Monaco; get_lap_times(2024, round) —
  volta mais rápida = âncora P2.
PROBE-B (REST direto, SEM fastf1): 2 chamadas ao endpoint Ergast-compatível
  da Jolpica (api.jolpi.ca) — provar que o repo prescinde do fastf1;
  rate limit OBSERVADO (cabeçalhos, sem pressionar).
PROBE-C (OpenF1 — classe (ii) não-vazia): car_data histórica Monaco 2024
  — campos speed/throttle/brake/gear/position, sem-login, latência.

  .venv/bin/python scripts/tracks/fonte_1_probe.py [--probe a|b|c|all]
"""

# Resolve common imports from the scripts root after topic-based reorganization.
import os as _scripts_os
import sys as _scripts_sys
_scripts_root = _scripts_os.path.dirname(_scripts_os.path.dirname(_scripts_os.path.abspath(__file__)))
_backend_root = _scripts_os.path.dirname(_scripts_root)
_project_root = _scripts_os.path.dirname(_backend_root)
for _script_path in (_scripts_root, _backend_root, _project_root):
    if _script_path not in _scripts_sys.path:
        _scripts_sys.path.insert(0, _script_path)

import argparse
import datetime
import hashlib
import json
import sys
import time
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent.parent / "experiments" / "fonte-1" / "probe_log.md"
JOLPICA = "https://api.jolpi.ca/ergast/f1"
OPENF1 = "https://api.openf1.org/v1"

_contador = {"n": 0, "teto": 30}


def _log_call(probe, endpoint, status, lat_ms, size, payload=b"", nota=""):
    _contador["n"] += 1
    sha = hashlib.sha256(payload).hexdigest()[:16] if payload else "-"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    line = (f"| {_contador['n']} | {probe} | {endpoint} | {ts} | {status} "
            f"| {lat_ms:.0f} | {size} | {sha} | {nota} |\n")
    with open(LOG, "a") as f:
        f.write(line)
    print(f"  [{probe} #{_contador['n']}] {status} {lat_ms:.0f}ms "
          f"{size}B — {endpoint}" + (f" ({nota})" if nota else ""))
    return _contador["n"]


def _get(url, timeout=30):
    import urllib.request
    import urllib.error
    t0 = time.time()
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            body = r.read()
            return r.status, round((time.time() - t0) * 1000), body, dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, round((time.time() - t0) * 1000), e.read() or b"", dict(e.headers)
    except Exception as e:  # fail-loud no relatório, sem esconder
        return f"ERR:{type(e).__name__}", round((time.time() - t0) * 1000), str(e).encode(), {}


def probe_a():
    print("--- PROBE-A: fastf1.ergast (módulo instalado 3.8.3) ---")
    results = {}
    try:
        from fastf1.ergast import Ergast
        e = Ergast()
        t0 = time.time()
        circ = e.get_circuits(season=2024)
        _log_call("A", f"{JOLPICA}/2024/circuits.json (via fastf1.ergast)",
                  200, (time.time() - t0) * 1000,
                  len(str(circ).encode()), nota=f"{len(circ)} circuitos")
        t0 = time.time()
        sch = e.get_race_schedule(season=2024)
        _log_call("A", f"{JOLPICA}/2024/races (via fastf1.ergast)",
                  200, (time.time() - t0) * 1000,
                  len(str(sch).encode()), nota=f"{len(sch)} corridas")
        mon = sch[sch["circuitName"].str.contains("Monaco", case=False, na=False)]
        if len(mon) == 0:
            mon = sch[sch["EventName"].str.contains("Monaco", case=False, na=False)] \
                if "EventName" in sch.columns else mon
        if len(mon) == 0 and "location" in str(mon.columns):
            mon = sch[sch["location"].str.contains("Monaco", case=False, na=False)]
        if len(mon) == 0 and "country" in sch.columns:
            mon = sch[sch["country"].str.contains("Monaco", case=False, na=False)]
        rd = int(mon["round"].iloc[0]) if len(mon) else -1
        print(f"  Monaco 2024 round: {rd} ({mon['circuitName'].iloc[0] if len(mon) else '?'})")
        t0 = time.time()
        lt = e.get_lap_times(season=2024, round=rd)
        # ErgastMultiResponse: dados em .content (lista de ErgastResultFrame)
        frames = getattr(lt, "content", None) or [lt]
        n_rows = int(sum(len(f) for f in frames))
        _log_call("A", f"{JOLPICA}/2024/{rd}/laps (via fastf1.ergast)",
                  200, (time.time() - t0) * 1000, len(str(lt).encode()),
                  nota=f"{n_rows} linhas de voltas-timeline")
        for f in frames:
            tcol = [c for c in f.columns if "time" in c.lower()]
            if tcol and len(f):
                best = f[tcol[0]].min()
                results["ancora"] = str(best)
                print(f"  ÂNCORA P2 (volta mais rápida Monaco 2024, via "
                      f"Jolpica): {best}")
                break
        results["round"] = rd
    except Exception as ex:
        _log_call("A", "fastf1.ergast", f"ERR:{type(ex).__name__}", 0, 0,
                  nota=str(ex)[:120])
        print(f"  PROBE-A FALHOU: {type(ex).__name__}: {ex}")
    return results


def probe_b(monaco_round):
    print("--- PROBE-B: REST direto Jolpica (SEM fastf1) ---")
    out = {}
    for nome, url in [
        ("circuits2024", f"{JOLPICA}/2024/circuits.json"),
        ("results", f"{JOLPICA}/2024/{monaco_round}/results.json"),
        ("laps", f"{JOLPICA}/2024/{monaco_round}/laps.json"),
    ]:
        st, ms, body, hdrs = _get(url)
        rate = (f"x-ratelimit-remaining={hdrs.get('x-ratelimit-remaining', '?')}, "
                f"retry-after={hdrs.get('retry-after', '?')}, "
                f"ratelimit-reset={hdrs.get('x-ratelimit-reset', '?')}")
        _log_call("B", url, st, ms, len(body), body, nota=rate[:110])
        out[nome] = (st, len(body))
        if st == 200 and nome == "results":
            try:
                j = json.loads(body)
                races = j.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if races:
                    for r_ in races[0].get("Results", []):
                        fl = r_.get("FastestLap", {})
                        if fl.get("rank") == "1":
                            t_ = fl.get("Time", {}).get("time", "?")
                            print(f"  ÂNCORA P2 via REST (FastestLap rank=1): "
                                  f"{t_} — {r_.get('Driver', {}).get('familyName', '?')}")
                            out["ancora_fastestlap"] = t_
                            break
            except Exception as ex:
                print(f"  parse results: {ex}")
        if st == 200 and nome == "laps":
            try:
                j = json.loads(body)
                races = j.get("MRData", {}).get("RaceTable", {}).get("Races", [])
                if races:
                    laps = races[0].get("Laps", [])
                    if laps:
                        best = min(
                            lt.get("Timings", [{}])[0].get("time", "99:99.999")
                            for lt in laps
                            for _ in [0] if lt.get("Timings"))
                        print(f"  ÂNCORA P2 via REST: {best}")
                        out["ancora_rest"] = str(best)
            except Exception as ex:
                print(f"  parse parcial: {ex}")
    return out


def probe_c():
    print("--- PROBE-C: OpenF1 (telemetria; sem login) ---")
    out = {}
    # 1) sessões de Monaco 2024: meeting por circuit_key via sessions?country_name
    st, ms, body, hdrs = _get(f"{OPENF1}/sessions?country_name=Monaco&year=2024")
    _log_call("C", f"{OPENF1}/sessions?country_name=Monaco&year=2024", st, ms,
              len(body), body)
    sess = {}
    if st == 200:
        try:
            j = json.loads(body)
            if j:
                sess = j[0]
                print(f"  sessão: {sess.get('session_key')} "
                      f"{sess.get('session_name')} "
                      f"{sess.get('full_name', '')[:40]}")
        except Exception as ex:
            print(f"  parse: {ex}")
    sk = sess.get("session_key")
    if sk:
        st2, ms2, body2, _ = _get(f"{OPENF1}/car_data?session_key={sk}"
                                  f"&driver_number=1&~position&speed<1")
        # car_data amostral: pegar UMA amostra pequena (limit via query não
        # documentado; usamos o mesmo endpoint 2x com drivers distintos)
        st2, ms2, body2, _ = _get(f"{OPENF1}/car_data?session_key={sk}&driver_number=16")
        _log_call("C", f"{OPENF1}/car_data?session_key={sk}&driver_number=16",
                  st2, ms2, len(body2), body2, nota="amostra histórica Monaco 2024")
        if st2 == 200:
            try:
                j = json.loads(body2)
                if j:
                    campos = sorted(j[0].keys())
                    print(f"  campos car_data ({len(campos)}): {campos}")
                    out["campos"] = campos
                    out["n_amostras"] = len(j)
            except Exception as ex:
                print(f"  parse car_data: {ex}")
        out["session_key"] = sk
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--probe", default="all",
                    choices=["a", "b", "c", "all", "laps"])
    args = ap.parse_args(argv)
    if not LOG.exists():
        LOG.write_text("# FONTE-1 — probe_log.md (APPEND-ONLY; teto 30 chamadas; prereg 27ebff9 §3)\n"
                       "| # | probe | endpoint | timestamp UTC | status | latência_ms "
                       "| tamanho_bytes | sha256(payload) | nota |\n"
                       "|---|---|---|---|---|---|---|---|---|\n")
    res_a, res_b, res_c = {}, {}, {}
    if args.probe == "laps":
        # RETRY (prereg §3: máx 2 retries; conta no teto): só o passo 3 do A
        try:
            from fastf1.ergast import Ergast
            e = Ergast()
            t0 = time.time()
            lt = e.get_lap_times(season=2024, round=8)
            frames = getattr(lt, "content", None) or [lt]
            n_rows = int(sum(len(f) for f in frames))
            _log_call("A-retry", f"{JOLPICA}/2024/8/laps (via fastf1.ergast)",
                      200, (time.time() - t0) * 1000, len(str(lt).encode()),
                      nota=f"{n_rows} linhas")
            for f in frames:
                tcol = [c for c in f.columns if "time" in c.lower()]
                if tcol and len(f):
                    print(f"  ÂNCORA P2 (retry): {f[tcol[0]].min()}")
                    break
        except Exception as ex:
            _log_call("A-retry", "fastf1.ergast get_lap_times",
                      f"ERR:{type(ex).__name__}", 0, 0, nota=str(ex)[:110])
            print(f"  RETRY FALHOU: {ex}")
        print(f"\nTotal de chamadas logadas: {_contador['n']}/30")
        return 0
    if args.probe in ("a", "all"):
        res_a = probe_a()
        rd = res_a.get("round", 8)  # Monaco 2024 = round 8 (fallback conhecido)
    else:
        rd = 8
    if args.probe in ("b", "all"):
        res_b = probe_b(rd)
    if args.probe in ("c", "all"):
        res_c = probe_c()
    print(f"\nTotal de chamadas logadas: {_contador['n']}/30")
    print(json.dumps({"A": {k: str(v) for k, v in res_a.items()},
                      "B": {k: str(v) for k, v in res_b.items()},
                      "C": {k: (str(v) if not isinstance(v, list) else v)
                            for k, v in res_c.items()}}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
