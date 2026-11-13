#!/usr/bin/env python3
"""FONTE-2 PROBE-A (prereg 9ba3f8c §4): OpenF1 location → Monza 2024.
Teto 10 chamadas (aqui: 2). Log APPEND em experiments/fonte-2/probe_log.md."""
import datetime
import hashlib
import sys
from pathlib import Path

_here = Path(__file__).resolve()
sys.path.insert(0, str(_here.parents[2] / "scripts"))   # backend/scripts
sys.path.insert(0, str(_here.parents[2]))               # backend/

import track_geometry_free as TGF

LOG = Path(__file__).resolve().parent / "probe_log.md"
_n = {"i": 0}


def log_call(probe, endpoint, status, lat_ms, size, payload=b"", nota=""):
    _n["i"] += 1
    sha = hashlib.sha256(payload).hexdigest()[:16] if payload else "-"
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with open(LOG, "a") as f:
        f.write(f"| {_n['i']} | {probe} | {endpoint} | {ts} | {status} "
                f"| {lat_ms} | {size} | {sha} | {nota} |\n")
    print(f"  [{probe} #{_n['i']}] {status} {lat_ms}ms {size}B — {endpoint}"
          + (f" ({nota})" if nota else ""))


if __name__ == "__main__":
    if not LOG.exists():
        LOG.write_text("# FONTE-2 — probe_log.md (APPEND-ONLY; teto 10; prereg 9ba3f8c §4)\n"
                       "| # | probe | endpoint | timestamp UTC | status | latência_ms "
                       "| tamanho_bytes | sha256(payload) | nota |\n"
                       "|---|---|---|---|---|---|---|---|---|\n")
    print("=== PROBE-A: OpenF1 location → Monza 2024 (driver 44; retry 2/2, "
          "método DENSIDADE, cache local) ===")
    trk = TGF.openf1_track("Italy", 2024, driver_number=44, log=log_call,
                           session_key=9590,
                           cache_path=Path(__file__).resolve().parent
                           / "location_9590_d44.json")
    if trk:
        print(f"  PISTA: {trk['name']} | session_key={trk['session_key']} | "
              f"n_wp={trk['n_wp']} | L~{trk['length_m']:.0f} m "
              f"(Monza oficial ~5793 m)")
    else:
        print("  PROBE-A FALHOU (payload vazio/indisponível) — árvore §3")
    print(f"Total de chamadas: {_n['i']}/10")
