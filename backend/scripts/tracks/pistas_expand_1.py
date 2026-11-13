#!/usr/bin/env python
"""PISTAS_EXPAND_1 (prereg 8afec70 + PATCH_PISTAS_EXPAND_1_A 51da2d8) —
biblioteca de mirrors reais expandida via OpenF1 /location, método v4 do
FONTE-2 em REUSO EXATO (import de track_geometry_free; sem reinvenção).

Ciclo de AQUISIÇÃO: ZERO sims; rede SÓ em discover/acquire, com TETO de
25 chamadas logadas APPEND em experiments/pistas-expand-1/probe_log.csv
(contador desde a 1ª). Cache local antes de re-baixar (nunca 2× o mesmo
GET). Gates fail-loud: FAILED = resultado honesto no manifest, sem
mirror congelado. Pool de treino --tracks INTOCIDO (congelar ≠ adotar).

Classificação RATIFICADA pelo PATCH_A (fixada em código; disco divergente
do inventário = ABORT fail-loud, sem reclassificação silenciosa):
  (b) Suzuka/Hungaroring/Zandvoort — v1 EXISTE → contorno OpenF1 +
      comparativo v1×candidato, SEM congelar (status COMPARADO)
  (c) Montreal/Bahrain/Mexico — v2 CONGELA nesta rodada (status OK)
  (c) Silverstone — v2 candidato FORA do path frozen (AGUARDA_DONO)
  (c) LasVegas/Miami — esticamento: congela se o teto deixar; sem teto,
      NAO_EXECUTADO (resultado honesto)

Subcomandos SERIAIS:
  t0        — inventário OFFLINE (§1; primeiro commit de dados)
  discover  — 2 chamadas logadas (/sessions 2023+2024 session_name=Race)
              + mapa pista→session p/ PIN explícito em SESSION_PINS
  acquire   — pipeline §2 por pista: ladder P1..P3 do f1db (OFFLINE) →
              /location com cache → saltos>300 m avança classificado →
              v4 → gates → congela/candidato → PNG via draw_track --csv
              (rota EXISTENTE; draw_track é zona proibida, SÓ chamado)
  golden    — §4: case-exata carrega + track_identity(fonte=openf1) +
              canônicos/v1s intocados + manifest×arquivos (sha recalculado)
"""
from __future__ import annotations

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
import csv
import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND.parent
for _p in (str(PROJECT_ROOT), str(BACKEND)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from scripts.tracks import track_geometry_free as TGF  # método v4 EXATO do FONTE-2 (reuso)
from backend.domain.track_resolution import (FROZEN_TRACKS_DIR,
                                              load_track_frozen,
                                              track_identity)

EXP = BACKEND / "experiments" / "pistas-expand-1"
CACHE_DIR = BACKEND / "cache" / "openf1_pistas_expand_1"
PROBE_LOG = EXP / "probe_log.csv"
MANIFEST = EXP / "manifest_pistas_expand_1.csv"
TETO_CHAMADAS = 25
SALTO_M = 300.0   # §2.2: salto >300 m no stream → avança classificado
UNIT_SCALE = 0.1  # FONTE-2: /location x/y em DECÍMETROS

# canônicos intocados (§4 golden)
SHAS_CANONICOS = {"interlagos": "164876196eb12174",
                  "Monaco": "67ca11dc211c8c78",
                  "Spa": "4b05f2c3bbc625fc"}
# v1s que devem permanecer EXATAMENTE como estão (§6: proibido substituir)
SHAS_V1 = {"Monza": "6ed5fac92bc2fb17", "Suzuka": "4323ecb67e12d18e",
           "Hungaroring": "24c7cd7f33653781", "Zandvoort": "0fb026c95f674eab",
           "interlagos": "e1857ffda5fe617f"}
# chaves que NÃO podem ganhar {key}_v2.json no path frozen nesta rodada
# ((b) + Silverstone AGUARDA_DONO + Monza fora dos alvos)
SEM_V2_FROZEN = {"Suzuka", "Hungaroring", "Zandvoort", "Monza", "Silverstone"}

# §1 tabela alvo — chave case-exata do arquivo {key}_v2.json (H-1: loader
# usa a key VERBATIM — track_resolution.py:212-216, prioridade {key}_v2),
# circuito f1db (race.circuit_id), oficial km (âncora §1; f1db CONFIRMA no t0)
TARGETS = [
    {"key": "Hungaroring", "f1db": "hungaroring", "oficial_km": 4.381, "primaria": True},
    {"key": "Silverstone", "f1db": "silverstone", "oficial_km": 5.891, "primaria": True},
    {"key": "Montreal", "f1db": "montreal", "oficial_km": 4.361, "primaria": True},
    {"key": "Bahrain", "f1db": "bahrain", "oficial_km": 5.412, "primaria": True},
    {"key": "Mexico", "f1db": "mexico-city", "oficial_km": 4.304, "primaria": True},
    {"key": "Zandvoort", "f1db": "zandvoort", "oficial_km": 4.259, "primaria": True},
    {"key": "Suzuka", "f1db": "suzuka", "oficial_km": 5.807, "primaria": True},
    {"key": "LasVegas", "f1db": "las-vegas", "oficial_km": 6.201, "primaria": False},
    {"key": "Miami", "f1db": "miami", "oficial_km": 5.412, "primaria": False},
]

# PATCH_A FIXAÇÃO 1 — inventário ratificado (fail-loud se o disco divergir)
CLASSE_RATIFICADA = {"Hungaroring": "b", "Zandvoort": "b", "Suzuka": "b",
                     "Silverstone": "c", "Montreal": "c", "Bahrain": "c",
                     "Mexico": "c", "LasVegas": "c", "Miami": "c"}
CONGELAR = {"Montreal", "Bahrain", "Mexico"}   # (c) congela nesta rodada
CONGELAR_STRETCH = {"LasVegas", "Miami"}        # (c) stretch (se teto deixar)

# PINS de sessão OpenF1 — PREENCHER APÓS `discover` (COMMIT DEDICADO dos
# pins ANTES das primeiras /location); acquire FAIL-LOUD sem pin. location
# = verificação contra o cache de descoberta (EUA: Miami × Austin ×
# Las Vegas discriminados por location — §2.1).
SESSION_PINS = {
    # descoberta 2024 (probe_log 2/25; discovery_sessions_2024.json em cache)
    "Hungaroring": {"session_key": 9566, "ano": 2024, "location": "Budapest", "country_name": "Hungary"},
    "Silverstone": {"session_key": 9558, "ano": 2024, "location": "Silverstone", "country_name": "United Kingdom"},
    "Montreal": {"session_key": 9531, "ano": 2024, "location": "Montréal", "country_name": "Canada"},
    "Bahrain": {"session_key": 9472, "ano": 2024, "location": "Sakhir", "country_name": "Bahrain"},
    "Mexico": {"session_key": 9625, "ano": 2024, "location": "Mexico City", "country_name": "Mexico"},
    "Zandvoort": {"session_key": 9582, "ano": 2024, "location": "Zandvoort", "country_name": "Netherlands"},
    "Suzuka": {"session_key": 9496, "ano": 2024, "location": "Suzuka", "country_name": "Japan"},
    "LasVegas": {"session_key": 9644, "ano": 2024, "location": "Las Vegas", "country_name": "United States"},
    "Miami": {"session_key": 9507, "ano": 2024, "location": "Miami", "country_name": "United States"},
}

# location strings aceitas por pista (lowercase, substring)
_LOC_EXPECT = {
    "Hungaroring": ("hungaroring", "mogyorod", "mogyoród", "budapest"),
    "Silverstone": ("silverstone",),
    "Montreal": ("montreal", "montréal", "gilles villeneuve"),
    "Bahrain": ("sakhir", "bahrain"),
    "Mexico": ("mexico",),
    "Zandvoort": ("zandvoort",),
    "Suzuka": ("suzuka",),
    "LasVegas": ("las vegas",),
    "Miami": ("miami",),
}


def _loc_match(key: str, loc: str) -> bool:
    l = str(loc).strip().lower()
    return any(p in l for p in _LOC_EXPECT.get(key, (key.lower(),)))


# ───────────────────────────────────────────────── probe_log + teto (§6)
def _log_call(probe, url, status, lat_ms, size, body, nota=""):
    """TODA chamada de rede é logada APPEND (contador = linhas do log)."""
    EXP.mkdir(parents=True, exist_ok=True)
    novo = not PROBE_LOG.exists()
    with open(PROBE_LOG, "a") as f:
        if novo:
            f.write("ts,probe,url,status_http,latency_ms,bytes,nota\n")
        f.write(f"{datetime.now().isoformat()},{probe},{url},{status},"
                f"{lat_ms},{size},{nota}\n")


def _n_calls() -> int:
    if not PROBE_LOG.exists():
        return 0
    return max(0, len(PROBE_LOG.read_text().strip().splitlines()) - 1)


def _check_teto(ctx: str):
    n = _n_calls()
    if n >= TETO_CHAMADAS:
        raise SystemExit(f"[PISTAS_EXPAND_1][ABORT] TETO {TETO_CHAMADAS} "
                         f"chamadas ATINGIDO ({n}) ctx={ctx}")
    print(f"[teto] {n}/{TETO_CHAMADAS} chamadas logadas — próxima permitida")


# ───────────────────────────────────────────────────────── f1db (offline)
def _f1db():
    con = sqlite3.connect(str(BACKEND / "f1db.db"))
    con.row_factory = sqlite3.Row
    return con


def _races(circuit_id: str, years=(2023, 2024)):
    con = _f1db()
    rows = con.execute(
        "select r.id, r.year, r.round, r.date, gp.name gp, c.name circuit, "
        "r.course_length, r.laps from race r "
        "join grand_prix gp on gp.id=r.grand_prix_id "
        "join circuit c on c.id=r.circuit_id "
        "where c.id=? and r.year in (?,?) order by r.year",
        (circuit_id, *years)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def _ladder(race_id: int, n: int = 10):
    """Classificação final RACE_RESULT (regra determinística §2.2: P1
    primeiro; driver_number direto do f1db — zero rede)."""
    con = _f1db()
    rows = con.execute(
        "select rd.position_number pos, rd.driver_number num, "
        "d.abbreviation abbr, d.full_name nome from race_data rd "
        "join driver d on d.id=rd.driver_id where rd.race_id=? "
        "and rd.type='RACE_RESULT' and rd.position_number is not null "
        "order by rd.position_number limit ?", (race_id, n)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def _classify(key: str) -> str:
    """(a) v2 existente | (b) v1 existente | (c) sem mirror — pelo DISCO."""
    if (FROZEN_TRACKS_DIR / f"{key}_v2.json").exists():
        return "a"
    if (FROZEN_TRACKS_DIR / f"{key}_v1.json").exists():
        return "b"
    return "c"


# ───────────────────────────────────────────────── saltos / gates (§2)
def _saltos(samples):
    pts = sorted(samples, key=lambda s: s.get("date", ""))
    xy = np.array([[float(s["x"]), float(s["y"])] for s in pts]) * UNIT_SCALE
    if len(xy) < 2:
        return 0, 0.0
    d = np.hypot(*np.diff(xy, axis=0).T)
    return int((d > SALTO_M).sum()), float(d.max())


def _gates(line, L_oficial_m: float):
    """§2.5 fail-loud, SEM forçar: bbox plausível (unidade ÷10 já aplicada),
    Δ<1% vs oficial, fechamento, espaçamento ~10 m, n_wp plausível."""
    wps = np.asarray(line, dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    dd = np.hypot(*np.diff(closed, axis=0).T)
    L = float(dd.sum())
    bbox = wps.max(0) - wps.min(0)
    fails = []
    if not (100.0 <= float(bbox.max()) <= 6000.0):
        fails.append(f"bbox_max {bbox.max():.1f} m fora de [100,6000]")
    if float(bbox.min()) < 50.0:
        fails.append(f"bbox_min {bbox.min():.1f} m < 50")
    dpct = 100.0 * (L - L_oficial_m) / L_oficial_m
    if abs(dpct) >= 1.0:
        fails.append(f"delta {dpct:+.2f}% fora de ±1%")
    gap = float(np.hypot(*(wps[0] - wps[-1])))
    if gap > 20.0:
        fails.append(f"fechamento {gap:.1f} m > 20")
    if not (8.5 <= float(dd.mean()) <= 11.5):
        fails.append(f"spacing_med {dd.mean():.2f} m fora de [8.5,11.5]")
    if float(dd.max()) > 25.0:
        fails.append(f"spacing_max {dd.max():.1f} m > 25")
    if not (L / 12.0 <= len(wps) <= L / 8.0):
        fails.append(f"n_wp {len(wps)} fora de [{L/12:.0f},{L/8:.0f}]")
    return fails, L, dpct


# ───────────────────────────────────────── manifest (§3) + JSONs (FIX 4)
MANIFEST_COLS = ["pista", "chave_case_exata", "session_key", "ano", "driver",
                 "n_amostras", "wp", "L_m", "L_oficial_m", "delta_pct",
                 "sha256", "status", "notas"]


def _manifest_rows():
    if not MANIFEST.exists():
        return []
    with open(MANIFEST) as f:
        return list(csv.DictReader(f))


def _manifest_append(row):
    novo = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=MANIFEST_COLS)
        if novo:
            w.writeheader()
        w.writerow({k: row.get(k, "") for k in MANIFEST_COLS})


def _embedded_sha(data: dict) -> str:
    """sha256 EXATAMENTE como o loader verifica (track_resolution.py:227)."""
    raw = json.dumps({k: v for k, v in data.items() if k != "sha256"},
                     sort_keys=True).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


def _write_json(path: Path, key: str, line, cand, pin, race, L, dpct, n_am):
    """Formato v2 (FIXAÇÃO 4): official_length_m do f1db, sf_idx=0 +
    sf_note (a /location não marca SF — padrão Monaco_v2/Spa_v2), sha256
    recalculado sobre o conteúdo novo."""
    data = {
        "name": f"{key} (mirror OpenF1 {pin['ano']})",
        "waypoints": [[float(x), float(y)] for x, y in line],
        "width_m": 12.0,
        "sf_idx": 0,
        "n_wp": int(len(line)),
        "fonte": "openf1",
        "fonte_metodo": ("v4 FONTE-2: remove-parado → célula-60m-mais-"
                         "visitada → janelas-entre-visitas=volta → mediana "
                         "→ re-amostra 10 m (reuso EXATO track_geometry_free)"),
        "session_key": int(pin["session_key"]),
        "ano": int(pin["ano"]),
        "driver_number": int(cand["num"]),
        "driver": str(cand["nome"]),
        "n_amostras": int(n_am),
        "L_m": round(float(L), 1),
        "official_length_m": round(float(race["course_length"]) * 1000.0, 1),
        "delta_pct": round(float(dpct), 2),
        "sf_note": ("sf_idx=0: /location não marca SF nem direção (padrão "
                    "Monaco_v2/Spa_v2); âncoras de corrida = decisão de dono"),
    }
    data["sha256"] = _embedded_sha(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))
    return data["sha256"]


def _v1_stats(key: str):
    f = FROZEN_TRACKS_DIR / f"{key}_v1.json"
    data = json.loads(f.read_text())
    wps = np.asarray(data["waypoints"], dtype=np.float64)
    closed = np.vstack([wps, wps[:1]])
    return {"wp": int(len(wps)),
            "L_m": float(np.hypot(*np.diff(closed, axis=0).T).sum()),
            "sha": data["sha256"]}


def _png(line, stem: str):
    """PNG de conferência via draw_track --csv (rota EXISTENTE — zona
    proibida SÓ chamada, intocada; PLOT de geometria, não simulação)."""
    import pandas as pd
    EXP.joinpath("png").mkdir(parents=True, exist_ok=True)
    csvp = EXP / "png" / f"{stem}.csv"
    pngp = EXP / "png" / f"{stem}.png"
    pd.DataFrame({"X": np.asarray(line)[:, 0],
                  "Y": np.asarray(line)[:, 1]}).to_csv(csvp, index=False)
    r = subprocess.run([sys.executable,
                        str(BACKEND / "scripts" / "draw_track.py"),
                        "--csv", str(csvp), "--save", str(pngp)],
                       cwd=str(BACKEND), capture_output=True, text=True,
                       timeout=120)
    if r.returncode != 0:
        print(r.stdout)
        print(r.stderr)
        raise SystemExit(f"[ABORT] draw_track --csv falhou para {stem} "
                         f"(zona proibida intocada — disclose no PARE)")
    print(f"    PNG: {pngp.name}")


# ────────────────────────────────────────────────────── t0 (§1, offline)
def cmd_t0(args):
    EXP.mkdir(parents=True, exist_ok=True)
    inv = {"gerado_em": datetime.now().isoformat(),
           "tracks_frozen": [], "canonicos": {}, "f1db": {},
           "classificacao": [], "oficiais": [], "ratificacao": []}
    md = ["# T0 PISTAS_EXPAND_1 — inventário (§1; primeiro commit de dados)",
          "", f"Gerado em {inv['gerado_em']} — OFFLINE, zero rede.", "",
          "## tracks_frozen existentes (§1.1)", "",
          "| arquivo | chave case-exata | sha embutido | sha recalculado | "
          "wp | L (m) | sf_idx | loader resolve |",
          "|---|---|---|---|---|---|---|---|"]
    for f in sorted(FROZEN_TRACKS_DIR.glob("*.json")):
        stem = f.stem
        key = stem[:-3] if (stem.endswith("_v1") or stem.endswith("_v2")) else stem
        data = json.loads(f.read_text())
        wps = np.asarray(data.get("waypoints", []), dtype=np.float64)
        closed = np.vstack([wps, wps[:1]]) if len(wps) else wps
        L = float(np.hypot(*np.diff(closed, axis=0).T).sum()) if len(wps) else 0.0
        res = (f"{key}_v2.json" if (FROZEN_TRACKS_DIR / f"{key}_v2.json").exists()
               else f"{key}_v1.json")
        sha_rec = _embedded_sha(data)
        row = {"arquivo": f.name, "chave": key,
               "sha_embutido": data.get("sha256"), "sha_recalculado": sha_rec,
               "wp": int(len(wps)), "L_m": round(L, 1),
               "sf_idx": data.get("sf_idx"), "loader_resolve": res,
               "integro": data.get("sha256") == sha_rec}
        inv["tracks_frozen"].append(row)
        md.append(f"| {f.name} | `{key}` | {row['sha_embutido']} | {sha_rec} "
                  f"| {row['wp']} | {row['L_m']} | {row['sf_idx']} | {res} |")
        print(f"  {f.name:28s} chave={key!r} sha={row['sha_embutido']} "
              f"integro={row['integro']} wp={row['wp']} L={row['L_m']}")

    md += ["", "## canônicos (§4: bit-idênticos, NÃO tocados)", ""]
    for k, sha in SHAS_CANONICOS.items():
        t = load_track_frozen(k, strict=True)
        got = getattr(t, "frozen_sha256", "?")
        ok = got == sha
        inv["canonicos"][k] = {"esperado": sha, "obtido": got, "ok": ok}
        md.append(f"- `{k}`: sha {got} {'✓ INTACTO' if ok else '✗ DIVERGE'}")
        print(f"  canônico {k}: {got} {'OK' if ok else 'DIVERGE!'}")

    md += ["", "## f1db — corridas-alvo + ladder RACE_RESULT (§2.2: P1)", ""]
    for t in TARGETS:
        inv["f1db"][t["key"]] = {"ancora_km": t["oficial_km"], "races": []}
        for r in _races(t["f1db"]):
            ladder = _ladder(r["id"], n=10 if r["year"] == 2024 else 3)
            inv["f1db"][t["key"]]["races"].append({**r, "ladder": ladder})
            top = " ".join(f"P{c['pos']}#{c['num']}{c['abbr']}" for c in ladder[:3])
            md.append(f"- **{t['key']}** {r['year']} r{r['round']:02d} "
                      f"race_id={r['id']} ({r['circuit']}, {r['laps']} voltas): "
                      f"L oficial = {r['course_length']} km | {top}")
            print(f"  {t['key']:12s} {r['year']} r{r['round']:02d} "
                  f"race_id={r['id']} L={r['course_length']}km | {top}")

    md += ["", "## oficiais §1 × f1db (âncora CONFIRMADA? §7)", "",
           "| pista | âncora §1 (km) | f1db 2024 (km) | status |",
           "|---|---|---|---|"]
    for t in TARGETS:
        r24 = [r for r in inv["f1db"][t["key"]]["races"] if r["year"] == 2024]
        f_km = r24[0]["course_length"] if r24 else None
        st = ("CONFIRMA" if f_km is not None
              and abs(f_km - t["oficial_km"]) < 1e-9 else "DIVERGE → re-pin")
        inv["oficiais"].append({"pista": t["key"], "ancora_km": t["oficial_km"],
                                "f1db_2024_km": f_km, "status": st})
        md.append(f"| {t['key']} | {t['oficial_km']} | {f_km} | {st} |")
        print(f"  oficial {t['key']}: âncora {t['oficial_km']} × f1db {f_km} → {st}")

    md += ["", "## classificação REAL §1.2 + congelamento (PATCH_A FIX 1)", "",
           "| pista | esperada (prereg) | REAL (disco) | congelamento |", "|---|---|---|---|"]
    esperada = {"Hungaroring": "(c)", "Silverstone": "(c)", "Montreal": "(c)",
                "Bahrain": "(c)", "Mexico": "(c)", "Zandvoort": "(c)",
                "Suzuka": "(b)", "LasVegas": "(c)", "Miami": "(c)"}
    for t in TARGETS:
        k = t["key"]
        real = _classify(k)
        if real != CLASSE_RATIFICADA[k]:
            raise SystemExit(f"[ABORT] inventário DIVERGE da ratificação: "
                             f"{k} disco=({real}) ratificado=({CLASSE_RATIFICADA[k]}) "
                             f"— fail-loud PATCH_A (sem reclassificação silenciosa)")
        cong = ("CONGELA (OK)" if k in CONGELAR else
                "CONGELA se teto deixar (stretch)" if k in CONGELAR_STRETCH else
                "COMPARADO sem congelar (b)" if real == "b" else
                "AGUARDA_DONO (candidato fora do frozen)")
        inv["classificacao"].append({"pista": k, "esperada": esperada[k],
                                     "real": f"({real})", "congelamento": cong,
                                     "t0_reclassifica": esperada[k] != f"({real})"})
        md.append(f"| {k} | {esperada[k]} | ({real}) | {cong} |")
        print(f"  classe {k}: esperada {esperada[k]} REAL ({real}) → {cong}")
    md += ["", "Ratificação PATCH_A: TODAS as 9 conferem com o disco "
               "(fail-loud se divergisse).", ""]

    (EXP / "t0_inventario.json").write_text(json.dumps(inv, indent=1))
    (EXP / "t0_inventario.md").write_text("\n".join(md))
    print(f"\n[t0] → {EXP/'t0_inventario.json'} + t0_inventario.md")


# ─────────────────────────────────────────────── discover (§2.1; 2 GETs)
def cmd_discover(args):
    EXP.mkdir(parents=True, exist_ok=True)
    for year in (2024, 2023):
        cache = EXP / f"discovery_sessions_{year}.json"
        if cache.exists():
            print(f"[discover] {year}: cache local {cache.name} (não re-baixa)")
            continue
        url = f"{TGF.OPENF1}/sessions?year={year}&session_name=Race"
        _check_teto(f"discover year={year}")
        st, ms, size, body = TGF._get(url, timeout=60.0)
        _log_call("D", url, st, ms, size, body, nota=f"year={year} session_name=Race")
        if st != 200:
            raise SystemExit(f"[ABORT] /sessions year={year} → HTTP {st}")
        cache.write_text(json.dumps(json.loads(body), indent=1))
        print(f"[discover] {year}: {len(json.loads(body))} corridas → {cache.name}")
    print("\n== mapa p/ SESSION_PINS (preencher + commit DEDICADO antes das /location) ==")
    for t in TARGETS:
        for year in (2024, 2023):
            cache = EXP / f"discovery_sessions_{year}.json"
            if not cache.exists():
                continue
            for s in json.loads(cache.read_text()):
                if _loc_match(t["key"], str(s.get("location", ""))):
                    print(f"  {t['key']:12s} {year} session_key={s['session_key']} "
                          f"location={s.get('location')!r} "
                          f"country={s.get('country_name')!r} "
                          f"date={s.get('date_start')}")


# ───────────────────────────────────────────────── acquire (§2, serial)
def _get_samples_cached(session_key: int, driver_number: int, ctx: str):
    cf = CACHE_DIR / f"location_{session_key}_{driver_number}.json"
    if cf.exists():
        return json.loads(cf.read_text())
    _check_teto(f"{ctx} location s{session_key} d{driver_number}")
    samples, _ = TGF.openf1_location(session_key, driver_number, log=_log_call)
    if samples:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cf.write_text(json.dumps(samples))
    return samples or None


def _row(key, pin, race, L_oficial_m, status, driver="", n_am=0, wp="",
         L_m="", delta="", sha="", notas=""):
    return {"pista": key, "chave_case_exata": key,
            "session_key": pin["session_key"], "ano": pin["ano"],
            "driver": driver, "n_amostras": n_am, "wp": wp, "L_m": L_m,
            "L_oficial_m": L_oficial_m, "delta_pct": delta, "sha256": sha,
            "status": status, "notas": notas}


def _acquire_one(t):
    key = t["key"]
    classe = _classify(key)
    if classe != CLASSE_RATIFICADA[key]:
        raise SystemExit(f"[ABORT] inventário divergente: {key} disco=({classe}) "
                         f"ratificado=({CLASSE_RATIFICADA[key]}) — fail-loud")
    pin = SESSION_PINS.get(key)
    if pin is None:
        raise SystemExit(f"[ABORT] {key} SEM SESSION_PIN — rode discover, "
                         f"preencha SESSION_PINS e COMMIT os pins (antes das /location)")
    dcache = EXP / f"discovery_sessions_{pin['ano']}.json"
    if not dcache.exists():
        raise SystemExit(f"[ABORT] cache de descoberta ausente: {dcache}")
    sess = {int(s["session_key"]): s for s in json.loads(dcache.read_text())}
    s = sess.get(int(pin["session_key"]))
    if s is None or not _loc_match(key, str(s.get("location", ""))):
        raise SystemExit(f"[ABORT] pin {key} session={pin['session_key']} não "
                         f"casa com a descoberta (location="
                         f"{s.get('location') if s else 'AUSENTE'!r})")
    races = [r for r in _races(t["f1db"]) if r["year"] == int(pin["ano"])]
    if not races:
        raise SystemExit(f"[ABORT] f1db sem corrida {t['f1db']} {pin['ano']}")
    race = races[0]
    L_oficial_m = round(float(race["course_length"]) * 1000.0, 1)
    if abs(float(race["course_length"]) - t["oficial_km"]) > 1e-9:
        print(f"[AVISO LOUD] {key}: f1db {race['course_length']} km != âncora §1 "
              f"{t['oficial_km']} — GATE USA f1db (re-pin no ANEXO)")
    ladder = _ladder(race["id"])
    if not ladder:
        raise SystemExit(f"[ABORT] ladder RACE_RESULT vazio (race {race['id']})")
    print(f"\n[acquire] {key} classe=({classe}) session={pin['session_key']} "
          f"ano={pin['ano']} race_id={race['id']} L_oficial={L_oficial_m} m")

    # §2.2: P1 primeiro; salto>300 m avança classificado (até 3 candidatos;
    # TODOS com saltos → MENOR contagem, empate = ordem de classificação;
    # fallback documentado — os gates decidem. Registro no manifest.)
    tried, escolhido = [], None
    for cand in ladder[:3]:
        samples = _get_samples_cached(int(pin["session_key"]), int(cand["num"]), key)
        if not samples:
            tried.append((cand, -1, None))
            print(f"    P{cand['pos']} #{cand['num']} {cand['abbr']}: stream VAZIO")
            continue
        ns, mx = _saltos(samples)
        tried.append((cand, ns, samples))
        print(f"    P{cand['pos']} #{cand['num']} {cand['abbr']}: "
              f"{len(samples)} amostras, saltos>300m={ns} (max {mx:.0f} m)")
        if ns == 0:
            escolhido = (cand, samples)
            break
    if escolhido is None:
        com = [x for x in tried if x[2] is not None]
        if not com:
            _manifest_append(_row(key, pin, race, L_oficial_m, status="FAILED",
                notas="streams VAZIOS nos 3 primeiros classificados: "
                      + " ".join(f"P{c['pos']}#{c['num']}" for c, _, _ in tried)))
            print("  FAILED: streams vazios (honesto, sem mirror)")
            return
        best = min(com, key=lambda x: (x[1], x[0]["pos"]))
        escolhido = (best[0], best[2])
        print(f"    [fallback documentado] todos com saltos → "
              f"P{best[0]['pos']} (menor contagem {best[1]})")
    cand, samples = escolhido
    notas_cand = " | ".join(f"P{c['pos']}#{c['num']}{c['abbr']} saltos={n}"
                            for c, n, _ in tried)
    driver = f"P{cand['pos']} #{cand['num']} {cand['abbr']}"

    line = TGF.filter_race_line(samples)  # v4 EXATO (defaults FONTE-2)
    if line is None:
        _manifest_append(_row(key, pin, race, L_oficial_m, status="FAILED",
            driver=driver, n_am=len(samples),
            notas=f"v4 devolveu None (janelas<2/amostras<100) [{notas_cand}]"))
        print("  FAILED: v4 None (honesto, sem mirror)")
        return
    fails, L, dpct = _gates(line, L_oficial_m)
    if fails:
        _manifest_append(_row(key, pin, race, L_oficial_m, status="FAILED",
            driver=driver, n_am=len(samples), wp=len(line), L_m=round(L, 1),
            delta=round(dpct, 2),
            notas="GATES FAIL: " + "; ".join(fails) + f" [{notas_cand}]"))
        print(f"  FAILED (gates): {'; '.join(fails)} — sem mirror (honesto)")
        return

    # gates OK → destino por classe × congelamento (PATCH_A FIXAÇÃO 1)
    if classe == "b":
        path = EXP / "candidatos" / f"{key}_candidato_openf1.json"
        sha = _write_json(path, key, line, cand, pin, race, L, dpct, len(samples))
        _png(line, f"{key}_candidato")
        v1 = _v1_stats(key)
        notas = (f"(b) v1 wp={v1['wp']} L={v1['L_m']:.1f} m sha={v1['sha']}; "
                 f"candidato {path.name} FORA do tracks_frozen (v1 intacto; "
                 f"loader prioriza _v2; substituição = dono) [{notas_cand}]")
        _manifest_append(_row(key, pin, race, L_oficial_m, status="COMPARADO",
            driver=driver, n_am=len(samples), wp=len(line), L_m=round(L, 1),
            delta=round(dpct, 2), sha=sha, notas=notas))
        print(f"  COMPARADO: {path.name} sha={sha} (v1 intacto)")
    elif key in (CONGELAR | CONGELAR_STRETCH):
        path = FROZEN_TRACKS_DIR / f"{key}_v2.json"
        sha = _write_json(path, key, line, cand, pin, race, L, dpct, len(samples))
        trk = load_track_frozen(key, strict=True)  # prova de carga case-exata
        ident = track_identity(trk, requested=key, fonte="openf1")
        if ident["n_wp"] != len(line):
            raise SystemExit(f"[ABORT] {key}: wp divergem pós-carga "
                             f"({ident['n_wp']} != {len(line)})")
        _png(line, f"{key}_v2")
        _manifest_append(_row(key, pin, race, L_oficial_m, status="OK",
            driver=driver, n_am=len(samples), wp=len(line), L_m=round(L, 1),
            delta=round(dpct, 2), sha=sha, notas=notas_cand))
        print(f"  OK CONGELADO: {path.name} sha={sha} | {ident}")
    else:
        path = EXP / "candidatos" / f"{key}_v2_candidato.json"
        sha = _write_json(path, key, line, cand, pin, race, L, dpct, len(samples))
        _png(line, f"{key}_v2_candidato")
        notas = (f"(c) aprovado nos gates mas FORA da lista de congelamento "
                 f"da rodada (PATCH_A FIX 1: Montreal/Bahrain/Mexico) — v2 "
                 f"PRONTO em {path.name}, FORA do path frozen; freeze = dono "
                 f"na revisão do PARE. Comparativo vs oficial: {dpct:+.2f}% "
                 f"[{notas_cand}]")
        _manifest_append(_row(key, pin, race, L_oficial_m, status="AGUARDA_DONO",
            driver=driver, n_am=len(samples), wp=len(line), L_m=round(L, 1),
            delta=round(dpct, 2), sha=sha, notas=notas))
        print(f"  AGUARDA_DONO: {path.name} sha={sha} (fora do frozen)")


def cmd_acquire(args):
    rows = _manifest_rows()
    done = {r["pista"] for r in rows}
    if args.stretch:
        prim = [t["key"] for t in TARGETS if t["primaria"]]
        faltam = [k for k in prim if k not in done]
        if faltam:
            raise SystemExit(f"[ABORT] stretch exige primária COMPLETA; faltam: {faltam}")
        alvos = [t for t in TARGETS if not t["primaria"]]
        if _n_calls() + 2 > TETO_CHAMADAS:
            for t in alvos:
                if t["key"] not in done:
                    _manifest_append(_row(t["key"],
                        {"session_key": "", "ano": ""}, {"course_length": t["oficial_km"]},
                        round(t["oficial_km"] * 1000.0, 1), status="NAO_EXECUTADO",
                        notas=f"esticamento SEM teto restante "
                              f"({_n_calls()}/{TETO_CHAMADAS} chamadas logadas)"))
            print(f"[acquire] teto insuficiente p/ esticamento → "
                  f"NAO_EXECUTADO (resultado honesto)")
            return
    else:
        alvos = [t for t in TARGETS if t["primaria"]]
    for t in alvos:
        if t["key"] in done:
            print(f"[acquire] {t['key']}: já no manifest — PULA")
            continue
        _acquire_one(t)


# ───────────────────────────────────────────── golden (§4) + anti-troca
def cmd_golden(args):
    ok = True

    print("== §4 canônicos bit-idênticos, NÃO tocados ==")
    for k, sha in SHAS_CANONICOS.items():
        got = getattr(load_track_frozen(k, strict=True), "frozen_sha256", "?")
        st = "PASS" if got == sha else "FAIL"
        ok &= (got == sha)
        print(f"  {st} {k}: {got} (esperado {sha})")

    print("== §6 v1s intactos + SEM _v2 não-autorizado no frozen ==")
    for k, sha in SHAS_V1.items():
        f = FROZEN_TRACKS_DIR / f"{k}_v1.json"
        data = json.loads(f.read_text())
        intacto = f.exists() and _embedded_sha(data) == sha and data["sha256"] == sha
        st = "PASS" if intacto else "FAIL"
        ok &= intacto
        print(f"  {st} {k}_v1 intacto (sha {sha})")
    for k in SEM_V2_FROZEN:
        existe = (FROZEN_TRACKS_DIR / f"{k}_v2.json").exists()
        st = "PASS" if not existe else "FAIL"
        ok &= (not existe)
        print(f"  {st} {k}: SEM {k}_v2.json no path frozen "
              f"(anti-substituição PATCH_A)")

    rows = _manifest_rows()
    print(f"\n== §4 mirrors novos (status OK) × manifest ==")
    for r in [x for x in rows if x["status"] == "OK"]:
        key = r["chave_case_exata"]
        try:
            trk = load_track_frozen(key, strict=True)
        except Exception as e:
            print(f"  FAIL {key}: load_track_frozen → {e}")
            ok = False
            continue
        ident = track_identity(trk, requested=key, fonte="openf1")
        bom = (ident["n_wp"] == int(r["wp"])
               and abs(ident["length_m"] - float(r["L_m"])) <= 0.1
               and ident["fonte"] == "openf1"
               and abs(ident["length_m"] - float(r["L_oficial_m"])) \
                   / float(r["L_oficial_m"]) < 0.01)
        st = "PASS" if bom else "FAIL"
        ok &= bom
        print(f"  {st} {key}: {ident}")

    print("\n== §3 manifest × arquivos (sha256 recalculado) ==")
    for r in rows:
        stt = r["status"]
        if stt == "OK":
            f = FROZEN_TRACKS_DIR / f"{r['chave_case_exata']}_v2.json"
        elif stt == "COMPARADO":
            f = EXP / "candidatos" / f"{r['chave_case_exata']}_candidato_openf1.json"
        elif stt == "AGUARDA_DONO":
            f = EXP / "candidatos" / f"{r['chave_case_exata']}_v2_candidato.json"
        else:  # FAILED / NAO_EXECUTADO: sem artefato
            if (FROZEN_TRACKS_DIR / f"{r['chave_case_exata']}_v2.json").exists():
                print(f"  FAIL {r['pista']}: status {stt} mas {r['chave_case_exata']}_v2.json EXISTE")
                ok = False
            continue
        if not f.exists():
            print(f"  FAIL arquivo ausente: {f}")
            ok = False
            continue
        data = json.loads(f.read_text())
        sha = _embedded_sha(data)
        bom = sha == r["sha256"] and sha == data["sha256"]
        st = "PASS" if bom else "FAIL"
        ok &= bom
        print(f"  {st} {f.name}: sha {sha} == manifest {r['sha256']}")

    print("\n== orçamento (§6) ==")
    print(f"  chamadas logadas: {_n_calls()}/{TETO_CHAMADAS} "
          f"{'PASS (dentro do teto)' if _n_calls() <= TETO_CHAMADAS else 'FAIL'}")
    ok &= (_n_calls() <= TETO_CHAMADAS)

    print("\nGOLDEN:", "PASS" if ok else "FAIL")
    if not ok:
        raise SystemExit(1)


def main():
    ap = argparse.ArgumentParser(
        description="PISTAS_EXPAND_1 — aquisição OpenF1 → mirrors v2 (0 sims)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("t0", help="inventário OFFLINE (§1)")
    sub.add_parser("discover", help="2 chamadas /sessions logadas + mapa de pins")
    pa = sub.add_parser("acquire", help="pipeline §2 por pista (serial)")
    pa.add_argument("--stretch", action="store_true",
                    help="esticamento LasVegas/Miami (exige primária completa + teto)")
    sub.add_parser("golden", help="verificação §4 + anti-substituição")
    args = ap.parse_args()
    {"t0": cmd_t0, "discover": cmd_discover,
     "acquire": cmd_acquire, "golden": cmd_golden}[args.cmd](args)


if __name__ == "__main__":
    main()
