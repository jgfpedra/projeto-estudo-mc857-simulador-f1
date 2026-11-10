#!/usr/bin/env python3
"""REALISMO-1 — instrumento report-only do PLANO_REALISMO_BOTS_1 (v1.1).

Lê SOMENTE artefatos de corrida já gravados (log do runner, CSV principal
5 Hz e CSV de eventos do solver) e a geometria frozen. Não importa o
simulador, controllers, modelos nem o pipeline de treino.

Reuso sem cópia (dependências carregadas pelo caminho, com SHA-256 pinado;
SHA divergente = InstrumentError = PARE):
  base_metrics.analyze_race   -> métricas canônicas (contatos 5 Hz, t<=60 s,
                                 laps_total, fora%, hesitações)
  saidas_verdict              -> load_track_geometry, build_corner_definitions,
                                 match_corner, extract_excursions,
                                 anatomy_cascade
  sanidade1b_verdict.stats    -> D3 colado/deadlock. O original fixa
                                 L_TRACK = 4160,4 (Interlagos); aqui o atributo
                                 do módulo recebe o comprimento da pista
                                 durante a chamada e é restaurado depois
                                 (Interlagos: valor idêntico; Monaco: corrige
                                 o wrap em s=0). O arquivo não é editado.
Réplica autorizada pelo plano (a lógica está embutida no main() do runner e
não é importável): FORA-PRESO = race_diagnostic.py:1774-1799.

Tempo em TICKS inteiros (tick lógico 0,1 s; o CSV grava ticks pares = 5 Hz):
t <= 10 s <=> tick <= 100; t <= 60 s <=> tick <= 600; 5 s = 50 ticks. As
fronteiras são exatas, sem ponto flutuante.

CLI:
  realismo_metrics.py --run-id R --log L --main-csv M --events-csv E \\
      --track interlagos|Monaco [--out X.json] [--arm composite|blind] \\
      [--expect-variedade N] [--expect-main-lines 30002]
      -> exit 0 = integridade OK; 3 = integridade FALHOU (JSON gravado)
  realismo_metrics.py noise --track T --off N=run.json [N=run.json ...] [--out X]
  realismo_metrics.py gates --cycle C1 --track T --off N=run.json ... \\
      --on N=run.json ... [--out X]      -> exit 0 = todos PASS; 1 = algum FAIL
O JSON é criado em modo exclusivo (nunca sobrescreve) e carrega
metrics_sha256 = sha256 do JSON canônico (convenção do base_metrics).
"""
from __future__ import annotations

import argparse
import contextlib
import functools
import hashlib
import importlib.util
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List, Mapping, Optional, Tuple

import numpy as np
import pandas as pd

VERSION = "realismo-metrics-v1.0"
SCRIPT_DIR = Path(__file__).resolve().parent

# --- dependências pinadas (o plano proíbe editá-las) ------------------------
BASE_METRICS_SHA256 = "9107c2d0f6bb3b1c7b317020b09b90a7c615390cdfb4e565acb29c27c362d728"
SAIDAS_VERDICT_SHA256 = "e1ac9f699e6d1339e67b7d53683f6becd5e3041da52102516cc4529c21496d6c"
SANIDADE1B_VERDICT_SHA256 = "c23f3c6692dfdb5add216e5d021cf1db6ba49b4113f1052d2aef2b54a74d8b16"

PRODUCTION_RESIDUAL_SHA16 = "6210fff65b19ad0e"   # STAGE 6 (produção)
EXPECTED_MAIN_LINES = 30002                       # metadado + header + 30.000

# --- tempo e convenções -----------------------------------------------------
ROW_S = 0.2                  # linha 5 Hz
TICKS_PER_ROW = 2            # o CSV grava ticks lógicos pares
Z_RETA_T_MAX_TICKS = 100     # t <= 10 s (inclusivo)
T60_TICKS = 600              # t <= 60 s (inclusivo)
NEW_EXIT_MAX_TICKS = 50      # nova saída <= 5 s após o fim da anterior
CASCADE_MAX_TICKS = 100      # anatomy_cascade: <= 10 s
WANDERER_MIN_ROWS = 300      # anatomy_cascade: duração > 60 s

# --- geometria do grid (place_grid, run_race_10_cars.py) e zonas (D3) -------
GRID_FRONT_BEFORE_SF_M = 6.0   # nariz da 1ª fila 6 m antes da SF
GRID_ROW_SPACING_M = 9.0       # spacing_m default
GRID_ROWS = 5                  # 5 fileiras x 2 colunas
Z_RETA_BACK_MARGIN_M = 5.0     # fundo do grid − 5 m (cobre o jitter ±0,5 m)
CORNER_MARGIN_M = 30.0         # margin_m do match_corner
ZONE_TOL_M = 0.1               # conferência com os valores do D3 (0,1 m)

TRACK_PINS = {
    "interlagos": dict(
        file_sha256="c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613",
        sha16="164876196eb12174"),
    "monaco": dict(
        file_sha256="af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2",
        sha16="67ca11dc211c8c78"),
}
EXPECTED_ZONES = {
    "interlagos": dict(z_reta=(2608.2, 2718.3), t1_id="C10", z_t1=(2718.3, 2882.3),
                       junction=("C08", 2276.2, 2344.2)),
    "monaco": dict(z_reta=(3288.3, 3331.2), t1_id="C01", z_t1=(3331.2, None),
                   junction=None),
}

RESIDUAL_RE = re.compile(r"\[diag\] residual baseline sha256=([0-9a-f]{16})")
FROZEN_RE = re.compile(r"^\[diag\] pista FROZEN: .*$", re.M)
VARIEDADE_FIELD_RE = re.compile(r"\bvariedade=(\d+)\b")
VARIEDADE_LINE_RE = re.compile(r"^\[diag\] VARIEDADE-1: N=(\d+)\b", re.M)
FORA_PRESO_LOG_RE = re.compile(r"FORA-PRESO:\s*(\d+)")
CSV_TRACK_RE = re.compile(r"track_frozen_sha256=([0-9a-f?]+)")


class InstrumentError(RuntimeError):
    """Entrada, pin ou contrato do instrumento violado (PARE)."""


# ---------------------------------------------------------------------------
# dependências
# ---------------------------------------------------------------------------
def sha256_file(path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_verified_module(name: str, path, expected_sha256: str):
    """Confere o SHA-256 ANTES de importar e carrega o módulo pelo caminho."""
    path = Path(path)
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise InstrumentError(
            f"{path}: SHA-256 {actual} != pin {expected_sha256} "
            "(dependência alterada; PARE)")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise InstrumentError(f"{path}: não importável")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise
    return module


@functools.lru_cache(maxsize=None)
def dependencies() -> SimpleNamespace:
    return SimpleNamespace(
        BM=load_verified_module("_realismo_dep_base_metrics",
                                SCRIPT_DIR / "base_metrics.py", BASE_METRICS_SHA256),
        SV=load_verified_module("_realismo_dep_saidas_verdict",
                                SCRIPT_DIR / "saidas_verdict.py", SAIDAS_VERDICT_SHA256),
        S1B=load_verified_module("_realismo_dep_sanidade1b_verdict",
                                 SCRIPT_DIR / "sanidade1b_verdict.py",
                                 SANIDADE1B_VERDICT_SHA256),
    )


def canonical_json(value) -> str:
    return dependencies().BM._canonical_json(value)


def payload_sha256(payload: Mapping) -> str:
    body = {k: v for k, v in payload.items() if k != "metrics_sha256"}
    return hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()


def verify_metrics_sha(payload: Mapping) -> bool:
    return payload.get("metrics_sha256") == payload_sha256(payload)


def _seal(payload: Dict) -> Dict:
    payload = dict(payload)
    payload.pop("metrics_sha256", None)
    payload["metrics_sha256"] = payload_sha256(payload)
    return payload


def dump_text(payload: Mapping) -> str:
    return json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False,
                      allow_nan=False) + "\n"


def write_exclusive(path, payload: Mapping) -> None:
    with Path(path).open("x", encoding="utf-8") as stream:
        stream.write(dump_text(payload))


# ---------------------------------------------------------------------------
# geometria e zonas
# ---------------------------------------------------------------------------
def normalize_track(name) -> str:
    key = str(name).strip().lower()
    if key not in TRACK_PINS:
        raise InstrumentError(f"pista não suportada: {name!r} "
                              f"(opções: {sorted(TRACK_PINS)})")
    return key


def in_interval_mod(s: float, a: float, b: float, length: float) -> bool:
    """s em [a, b) no círculo de comprimento `length` (aceita a > b = wrap)."""
    return ((s - a) % length) < ((b - a) % length)


def corner_zone(corner: Mapping, length: float) -> Tuple[float, float]:
    """Zona de um complexo com a semântica de saidas_verdict.match_corner:
    s0 < 0 (curva com wrap) = sem margem no s0; senão s0 − 30 m (piso 0,
    pois s_mod >= 0); fim = s1 + 30 m."""
    s0, s1 = float(corner["s0"]), float(corner["s1"])
    start = s0 % length if s0 < 0 else max(s0 - CORNER_MARGIN_M, 0.0)
    return start, s1 + CORNER_MARGIN_M


@dataclass(frozen=True)
class TrackGeometry:
    key: str
    file: str
    sha16: str
    file_sha256: str
    length_m: float
    geom: tuple
    corners: tuple
    sf_s: float
    grid_front: float
    grid_back: float
    z_reta: Tuple[float, float]
    t1_corner_id: str
    z_t1: Tuple[float, float]
    junction_corner_id: Optional[str]
    junction_zone: Optional[Tuple[float, float]]

    def zones_record(self) -> Dict:
        def r(x):
            return None if x is None else round(float(x), 4)
        return dict(
            length_m=r(self.length_m), sf_s=r(self.sf_s),
            grid_front=r(self.grid_front), grid_back=r(self.grid_back),
            z_reta=[r(self.z_reta[0]), r(self.z_reta[1])],
            t1_corner_id=self.t1_corner_id,
            z_t1=[r(self.z_t1[0]), r(self.z_t1[1])],
            junction_corner_id=self.junction_corner_id,
            junction_zone=(None if self.junction_zone is None
                           else [r(self.junction_zone[0]), r(self.junction_zone[1])]),
            corners=[dict(id=c["id"], name=c["name"], s0=r(c["s0"]), s1=r(c["s1"]),
                          kmax=round(float(c["kmax"]), 6)) for c in self.corners],
        )


def _close(value: float, expected: float) -> bool:
    return abs(float(value) - float(expected)) <= ZONE_TOL_M


@functools.lru_cache(maxsize=None)
def track_geometry(track) -> TrackGeometry:
    key = normalize_track(track)
    SV = dependencies().SV
    cfg = SV.TRACKS[key]
    pins = TRACK_PINS[key]
    path = Path(cfg["file"])
    file_sha = sha256_file(path)
    if file_sha != pins["file_sha256"]:
        raise InstrumentError(f"{path}: SHA-256 {file_sha} != pin {pins['file_sha256']}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if str(data.get("sha256")) != pins["sha16"] or cfg["sha256"] != pins["sha16"]:
        raise InstrumentError(f"{path}: sha embutido não confere com o pin {pins['sha16']}")
    geom = SV.load_track_geometry(path)
    wps, _diff, _seg, seg_cum, length, _head = geom
    length = float(length)
    corners = tuple(SV.build_corner_definitions(wps, generic_names=cfg["generic_names"]))
    sf_s = float(seg_cum[int(data["sf_idx"]) % len(wps)])
    front = (sf_s - GRID_FRONT_BEFORE_SF_M) % length
    back = (front - (GRID_ROWS - 1) * GRID_ROW_SPACING_M) % length
    best = None
    for corner in corners:   # T1 = primeira zona de curva à frente do nariz do grid
        start, end = corner_zone(corner, length)
        forward = (start - front) % length
        if best is None or forward < best[0]:
            best = (forward, corner, start, end)
    _fwd, t1, t1_start, t1_end = best
    z_reta = ((back - Z_RETA_BACK_MARGIN_M) % length, t1_start)
    if not in_interval_mod(front, z_reta[0], z_reta[1], length):
        raise InstrumentError(f"{key}: nariz do grid fora da Z_RETA calculada")
    span = (z_reta[1] - z_reta[0]) % length
    for k in range(int(span)):          # Z_RETA inteira é 'Reta' no match_corner
        s = (z_reta[0] + k) % length
        if SV.match_corner(s, list(corners), length)[0] != "Reta":
            raise InstrumentError(f"{key}: Z_RETA cruza uma zona de curva em s={s:.1f}")
    exp = EXPECTED_ZONES[key]
    junction_id = junction_zone = None
    problems = []
    if not (_close(z_reta[0], exp["z_reta"][0]) and _close(z_reta[1], exp["z_reta"][1])):
        problems.append(f"Z_RETA {z_reta} != {exp['z_reta']}")
    if t1["id"] != exp["t1_id"] or not _close(t1_start, exp["z_t1"][0]):
        problems.append(f"T1 {t1['id']}@{t1_start:.3f} != {exp['t1_id']}@{exp['z_t1'][0]}")
    if exp["z_t1"][1] is not None and not _close(t1_end, exp["z_t1"][1]):
        problems.append(f"fim da Z_T1 {t1_end:.3f} != {exp['z_t1'][1]}")
    if exp["junction"] is not None:
        jid, js0, js1 = exp["junction"]
        jc = next((c for c in corners if c["id"] == jid), None)
        if (jc is None or "Junção" not in jc["name"]
                or not (_close(jc["s0"], js0) and _close(jc["s1"], js1))):
            problems.append(f"{jid} Junção não confere com [{js0}, {js1}]")
        else:
            junction_id, junction_zone = jid, corner_zone(jc, length)
    if problems:
        raise InstrumentError(f"{key}: zonas divergem do D3 do plano (PARE): "
                              + "; ".join(problems))
    return TrackGeometry(
        key=key, file=str(path), sha16=pins["sha16"], file_sha256=file_sha,
        length_m=length, geom=geom, corners=corners, sf_s=sf_s, grid_front=front,
        grid_back=back, z_reta=z_reta, t1_corner_id=t1["id"], z_t1=(t1_start, t1_end),
        junction_corner_id=junction_id, junction_zone=junction_zone)


# ---------------------------------------------------------------------------
# métricas novas
# ---------------------------------------------------------------------------
def fora_preso_split(df: pd.DataFrame) -> Tuple[int, int]:
    """Réplica de race_diagnostic.py:1774-1799 (FORA-PILOTAGEM vs FORA-PRESO).
    Por carro, janelas fixas de 30 s a partir de t=0 até t_max da sessão; uma
    janela com alguma linha fora vira PRESO se max|lat| > 20 m ou progresso de
    cum_dist < 5 m; senão PILOTAGEM. Devolve (preso, pilotagem) em linhas."""
    tot_pilot = tot_preso = 0
    t_end = float(df.t_s.max())
    for _drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        t = g.t_s.values
        lat = g.lat.abs().values
        cum = g.cum_dist.values
        offm = g.offtrack.values
        for w0 in np.arange(0.0, t_end, 30.0):
            m = (t >= w0) & (t < w0 + 30.0)
            if not m.any() or not offm[m].any():
                continue
            if (lat[m].max() > 20.0) or ((cum[m].max() - cum[m].min()) < 5.0):
                tot_preso += int(offm[m].sum())
            else:
                tot_pilot += int(offm[m].sum())
    return tot_preso, tot_pilot


@contextlib.contextmanager
def _sanidade_track_length(length_m: float):
    s1b = dependencies().S1B
    saved = s1b.L_TRACK
    s1b.L_TRACK = float(length_m)
    try:
        yield s1b
    finally:
        s1b.L_TRACK = saved


def glue_deadlock(main_csv, length_m: float) -> Tuple[int, int]:
    """D3 do SANIDADE (sanidade1b_verdict.stats) com o comprimento da pista
    certo. Devolve (linhas coladas, deadlocks) — colado em linhas de 0,2 s."""
    with _sanidade_track_length(length_m) as s1b:
        st = s1b.stats(str(main_csv))
    return int(round(float(st["glue"]) / ROW_S)), int(st["dead"])


def _excursions(df: pd.DataFrame, geo: TrackGeometry) -> pd.DataFrame:
    SV = dependencies().SV
    ev, _rec = SV.extract_excursions(df, list(geo.corners), geo.geom)
    cols = ["drv", "tick", "t_s", "dur_s", "s", "corner_id"]
    if len(ev) == 0:
        ev = pd.DataFrame({c: pd.Series(dtype=object) for c in cols})
    ev = ev[cols].copy()
    ev["tick"] = [int(x) for x in ev["tick"]]
    ev["rows"] = [int(round(float(d) / ROW_S)) for d in ev["dur_s"]]
    ev["end_tick"] = [t + TICKS_PER_ROW * n for t, n in zip(ev["tick"], ev["rows"])]
    last_tick = {d: int(t) for d, t in df.groupby("drv")["tick"].max().items()}
    ev["censored"] = [int(e) > last_tick[d] for d, e in zip(ev["drv"], ev["end_tick"])]
    return ev.sort_values(["drv", "tick"], kind="stable").reset_index(drop=True)


def _event_record(row) -> Dict:
    return dict(drv=str(row.drv), tick=int(row.tick), t_s=round(float(row.t_s), 1),
                s=round(float(row.s), 3), rows=int(row.rows),
                corner_id=str(row.corner_id))


def _sequence_metrics(ev: pd.DataFrame) -> Dict[str, int]:
    """Nova saída <= 5 s e cascata (convenção anatomy_cascade) em ticks."""
    new_exit = cascade = wanderer = 0
    for _drv, g in ev.groupby("drv", sort=True):
        prev_end = None
        for row in g.itertuples(index=False):
            if prev_end is not None and row.tick - prev_end <= NEW_EXIT_MAX_TICKS:
                new_exit += 1
            if row.rows > WANDERER_MIN_ROWS:
                wanderer += 1
            elif prev_end is not None and row.tick - prev_end <= CASCADE_MAX_TICKS:
                cascade += 1
            prev_end = row.end_tick
    return dict(new_exit=new_exit, cascade=cascade, wanderer=wanderer)


def _frac(num: int, den: int) -> Optional[float]:
    return None if den == 0 else float(num) / float(den)


def _new_metrics(df: pd.DataFrame, ev: pd.DataFrame, geo: TrackGeometry,
                 main_csv) -> Tuple[Dict, Dict]:
    SV = dependencies().SV
    n_exc = int(len(ev))
    offtrack_rows = int(df["offtrack"].sum())
    in_reta = [int(t) <= Z_RETA_T_MAX_TICKS
               and in_interval_mod(float(s), geo.z_reta[0], geo.z_reta[1], geo.length_m)
               for t, s in zip(ev["tick"], ev["s"])]
    in_t1 = [int(t) <= T60_TICKS and c == geo.t1_corner_id
             for t, c in zip(ev["tick"], ev["corner_id"])]
    in_junction = [geo.junction_corner_id is not None and c == geo.junction_corner_id
                   for c in ev["corner_id"]]
    classes = (SV.anatomy_cascade(ev[["drv", "t_s", "dur_s"]].assign(
        rows=ev["rows"])) if n_exc else pd.DataFrame(columns=["classe", "rows"]))
    cascade_mask = classes["classe"] == "REJOIN-CASCATA" if n_exc else []
    seq = _sequence_metrics(ev)
    censored = int(sum(bool(x) for x in ev["censored"]))
    reentries = n_exc - censored
    preso, pilot = fora_preso_split(df)
    glued_rows, deadlocks = glue_deadlock(main_csv, round(geo.length_m, 1))
    corner_counts = {str(k): int(v) for k, v in
                     sorted(ev["corner_id"].value_counts().items())}
    cascade_events = int(sum(bool(x) for x in cascade_mask)) if n_exc else 0
    cascade_rows = int(classes.loc[cascade_mask, "rows"].sum()) if n_exc else 0
    metrics = dict(
        offtrack_rows=offtrack_rows,
        fora_preso_rows=int(preso), fora_pilotagem_rows=int(pilot),
        excursions_total=n_exc,
        excursions_t_le_60s=int(sum(int(t) <= T60_TICKS for t in ev["tick"])),
        z_reta_exits=int(sum(in_reta)),
        z_t1_exits_t_le_60s=int(sum(in_t1)),
        junction_exits=(int(sum(in_junction)) if geo.junction_corner_id else None),
        corner_exits=corner_counts,
        cascade_events=cascade_events,
        cascade_events_int=int(seq["cascade"]),
        wanderer_events=(int((classes["classe"] == "WANDERER").sum()) if n_exc else 0),
        cascade_offtime_rows=cascade_rows,
        cascade_event_frac=_frac(cascade_events, n_exc),
        cascade_offtime_frac=_frac(cascade_rows, offtrack_rows),
        censored_excursions=censored,
        reentries=reentries,
        new_exit_le_5s=int(seq["new_exit"]),
        new_exit_le_5s_per_reentry=_frac(seq["new_exit"], reentries),
        new_exit_le_5s_per_excursion=_frac(seq["new_exit"], n_exc),
        glued_rows=glued_rows,
        glued_s=round(glued_rows * ROW_S, 1),
        deadlocks=deadlocks,
    )
    events = dict(
        z_reta=[_event_record(r) for r, keep in zip(ev.itertuples(index=False), in_reta) if keep],
        z_t1_t_le_60s=[_event_record(r) for r, keep in zip(ev.itertuples(index=False), in_t1) if keep],
        junction=([_event_record(r) for r, keep in zip(ev.itertuples(index=False), in_junction) if keep]
                  if geo.junction_corner_id else None),
    )
    for key in ("z_reta", "z_t1_t_le_60s"):
        events[key].sort(key=lambda e: (e["tick"], e["drv"]))
    if events["junction"] is not None:
        events["junction"].sort(key=lambda e: (e["tick"], e["drv"]))
    return metrics, events


# ---------------------------------------------------------------------------
# integridade por corrida (D2)
# ---------------------------------------------------------------------------
def _physical_lines(path: Path) -> int:
    with path.open("rb") as stream:
        return sum(1 for _ in stream)


def check_integrity(geo: TrackGeometry, log: Path, main_csv: Path, events_csv: Path, *,
                    arm: str = "composite", expect_variedade: Optional[int] = None,
                    expected_main_lines: int = EXPECTED_MAIN_LINES) -> Dict:
    if arm not in ("composite", "blind"):
        raise InstrumentError(f"--arm inválido: {arm!r}")
    text = Path(log).read_text(encoding="utf-8")
    checks: Dict[str, Dict] = {}

    def put(name, ok, detail):
        checks[name] = {"pass": bool(ok), "detail": detail}

    n_lines = _physical_lines(Path(main_csv))
    put("main_physical_lines", n_lines == expected_main_lines,
        {"found": n_lines, "expected": expected_main_lines})
    put("events_present", Path(events_csv).is_file(), str(Path(events_csv).name))
    residual = RESIDUAL_RE.findall(text)
    if arm == "composite":
        put("residual_baseline", residual == [PRODUCTION_RESIDUAL_SHA16],
            {"found": residual, "expected": [PRODUCTION_RESIDUAL_SHA16]})
    else:
        put("residual_baseline", residual == [], {"found": residual, "expected": []})
    put("no_residual_override", "RESIDUAL OVERRIDE" not in text,
        {"override_lines": text.count("RESIDUAL OVERRIDE")})
    with Path(main_csv).open("r", encoding="utf-8") as stream:
        first = stream.readline()
    csv_sha = CSV_TRACK_RE.findall(first) if first.startswith("#") else []
    put("csv_track_sha", csv_sha == [geo.sha16], {"found": csv_sha, "expected": geo.sha16})
    frozen = FROZEN_RE.findall(text)
    put("log_track_sha", len(frozen) == 1 and f"sha256 {geo.sha16}" in frozen[0],
        {"frozen_lines": len(frozen), "expected": geo.sha16})
    fields = VARIEDADE_FIELD_RE.findall(frozen[0]) if len(frozen) == 1 else []
    variedade = int(fields[0]) if len(fields) == 1 else None
    put("variedade_frozen", variedade is not None, {"found": fields})
    var_lines = [int(x) for x in VARIEDADE_LINE_RE.findall(text)]
    if variedade is None:
        put("variedade_line", False, {"found": var_lines})
    elif variedade == 0:
        put("variedade_line", var_lines == [], {"found": var_lines, "expected": []})
    else:
        put("variedade_line", var_lines == [variedade],
            {"found": var_lines, "expected": [variedade]})
    if expect_variedade is not None:
        put("expected_variedade", variedade == int(expect_variedade),
            {"found": variedade, "expected": int(expect_variedade)})
    return {"ok": all(c["pass"] for c in checks.values()), "variedade": variedade,
            "arm": arm, "checks": checks}


# ---------------------------------------------------------------------------
# análise de uma corrida
# ---------------------------------------------------------------------------
def analyze_run(*, run_id, log, main_csv, events_csv, track, arm: str = "composite",
                expect_variedade: Optional[int] = None,
                expected_main_lines: int = EXPECTED_MAIN_LINES) -> Dict:
    deps = dependencies()
    geo = track_geometry(track)
    log, main_csv, events_csv = Path(log), Path(main_csv), Path(events_csv)
    integrity = check_integrity(geo, log, main_csv, events_csv, arm=arm,
                                expect_variedade=expect_variedade,
                                expected_main_lines=expected_main_lines)
    canonical = deps.BM.analyze_race(log, main_csv, events_csv, run_id=str(run_id))
    df = pd.read_csv(main_csv, comment="#")
    ev = _excursions(df, geo)
    new, events = _new_metrics(df, ev, geo, main_csv)
    metrics = dict(
        sample_rows=int(len(df)),
        contacts_5hz_total=int(canonical["contacts_5hz_total"]),
        contacts_5hz_t_le_60s=int(canonical["contacts_5hz_t_le_60s"]),
        laps_total=int(canonical["laps_total"]),
        offtrack_pct=float(canonical["offtrack_pct"]),
        hesitations=int(canonical["hesitations"]),
        **new,
    )
    log_text = log.read_text(encoding="utf-8")
    preso_log = FORA_PRESO_LOG_RE.findall(log_text)
    preso_log_v = int(preso_log[0]) if len(preso_log) == 1 else None
    summary = canonical["runner_summary"]
    cross_checks = dict(
        fora_preso_vs_log=dict(computed=metrics["fora_preso_rows"], log=preso_log_v,
                               match=(None if preso_log_v is None
                                      else preso_log_v == metrics["fora_preso_rows"])),
        offtrack_vs_log=dict(computed=metrics["offtrack_rows"],
                             log=int(summary["offtrack_ticks"]),
                             match=int(summary["offtrack_ticks"]) == metrics["offtrack_rows"]),
        sample_rows_vs_canonical=dict(computed=metrics["sample_rows"],
                                      canonical=int(canonical["sample_rows"]),
                                      match=int(canonical["sample_rows"]) == metrics["sample_rows"]),
    )
    payload = dict(
        schema_version=VERSION,
        run_id=str(run_id),
        track=geo.key,
        arm=arm,
        instrument=dict(
            realismo_metrics_sha256=sha256_file(Path(__file__)),
            base_metrics_sha256=BASE_METRICS_SHA256,
            saidas_verdict_sha256=SAIDAS_VERDICT_SHA256,
            sanidade1b_verdict_sha256=SANIDADE1B_VERDICT_SHA256,
            track_file_sha256=geo.file_sha256,
            track_sha16=geo.sha16,
        ),
        source_sha256=dict(canonical["source_sha256"]),
        integrity=integrity,
        cross_checks=cross_checks,
        metrics=metrics,
        events=events,
        zones=geo.zones_record(),
        canonical=canonical,
    )
    return _seal(payload)


# ---------------------------------------------------------------------------
# gates (D3) — aritmética inteira
# ---------------------------------------------------------------------------
def band_110(off_sum: int) -> int:
    """ceil(1,10 × ΣOFF) em inteiros."""
    return (11 * int(off_sum) + 9) // 10


def floor_95(off_sum: int) -> int:
    """floor(0,95 × ΣOFF) em inteiros."""
    return (95 * int(off_sum)) // 100


@dataclass(frozen=True)
class Gate:
    id: str
    name: str
    cycles: Tuple[str, ...]
    metric: str
    agg: str          # "sum" | "rate" | "per_realization"
    kind: str         # "anti-regression" | "primary"
    direction: str    # "upper" (ON <= limite) | "lower" (ON >= limite)
    status: str
    tracks: Optional[Tuple[str, ...]] = None


_BEHAVIOR = ("C1", "C2", "C3", "C5", "C6")
GATES: Tuple[Gate, ...] = (
    Gate("B1", "B-1 contatos totais", _BEHAVIOR, "contacts_5hz_total", "sum",
         "anti-regression", "upper", "ratificado"),
    Gate("S1", "S-1 contatos t<=60 s", ("C1",), "contacts_5hz_t_le_60s", "sum",
         "anti-regression", "upper", "ratificado"),
    Gate("R1", "R-1 ritmo (laps_total)", _BEHAVIOR, "laps_total", "sum",
         "anti-regression", "lower",
         "gate ratificado; agregação a ratificar no freeze do C1"),
    Gate("R2", "R-2 fora (+1,0 pp)", ("C1", "C5", "C6"), "offtrack_rows", "rate",
         "anti-regression", "upper",
         "gate ratificado; agregação a ratificar no freeze do C1"),
    Gate("C1P1", "C1-P1 reta de largada", ("C1",), "z_reta_exits", "per_realization",
         "primary", "upper", "ratificado (estrutural)"),
    Gate("C1P2", "C1-P2 saídas t<=60 s", ("C1",), "excursions_t_le_60s", "sum",
         "primary", "upper", "agregação a ratificar"),
    Gate("R2T1", "R-2-T1 entrada da T1", ("C1",), "z_t1_exits_t_le_60s",
         "per_realization", "anti-regression", "upper",
         "gate ratificado (ajuste 2); classificação estrutural a confirmar no freeze do C1"),
    Gate("C23P", "C2/C3 primário (fora)", ("C2", "C3"), "offtrack_rows", "rate",
         "primary", "upper", "agregação a ratificar"),
    Gate("C5P", "C5 primário (saídas na C08 Junção)", ("C5",), "junction_exits", "sum",
         "primary", "upper", "agregação a ratificar", tracks=("interlagos",)),
    Gate("C6G", "C6 primário (colado)", ("C6",), "glued_rows", "sum",
         "primary", "upper", "agregação a ratificar"),
    Gate("C6D", "C6 primário (deadlocks por realização)", ("C6",), "deadlocks",
         "per_realization", "primary", "upper", "agregação a ratificar"),
)


def gates_for(cycle: str, track) -> List[Gate]:
    cycle = str(cycle).strip().upper()
    key = normalize_track(track)
    if cycle not in _BEHAVIOR:
        raise InstrumentError(f"ciclo sem gates de comportamento: {cycle!r}")
    if cycle == "C5" and key != "interlagos":
        raise InstrumentError("C5 só tem braço ON em Interlagos (v3)")
    return [g for g in GATES if cycle in g.cycles and (g.tracks is None or key in g.tracks)]


def gate_bound(gate: Gate, off_value: int, lines: Optional[int] = None) -> int:
    if gate.id == "B1":
        return band_110(off_value)
    if gate.id == "S1":
        return int(off_value)
    if gate.id == "R1":
        return floor_95(off_value)
    if gate.id == "R2":
        if lines is None:
            raise InstrumentError("R-2 exige o total de linhas")
        return (100 * int(off_value) + int(lines)) // 100
    if gate.id in ("C1P2", "C23P", "C5P", "C6G"):
        return int(off_value) - 1          # melhora estrita: ON < OFF
    if gate.id == "C1P1":
        return 0                           # zero saídas, independente do OFF
    if gate.id in ("R2T1", "C6D"):
        return int(off_value)              # sem piora por realização
    raise InstrumentError(f"gate sem regra: {gate.id}")


def _passes(gate: Gate, value: int, bound: int) -> bool:
    return value <= bound if gate.direction == "upper" else value >= bound


def _metric(metrics: Mapping, name: str) -> int:
    value = metrics.get(name)
    if value is None or isinstance(value, bool) or not isinstance(value, int):
        raise InstrumentError(f"métrica {name!r} ausente ou não inteira: {value!r}")
    return value


DISCLOSURE_METRICS = (
    "contacts_5hz_total", "contacts_5hz_t_le_60s", "laps_total", "offtrack_rows",
    "sample_rows", "fora_preso_rows", "excursions_total", "excursions_t_le_60s",
    "z_reta_exits", "z_t1_exits_t_le_60s", "junction_exits", "glued_rows", "deadlocks",
)
ALERT_METRICS = ("contacts_5hz_total", "excursions_total", "glued_rows")


def _same_realizations(off_by_n: Mapping, on_by_n: Mapping) -> List[int]:
    off_ns, on_ns = sorted(off_by_n), sorted(on_by_n)
    if not off_ns or off_ns != on_ns:
        raise InstrumentError(f"realizações diferentes: OFF {off_ns} × ON {on_ns}")
    return off_ns


def disclosure(off_by_n: Mapping[int, Mapping], on_by_n: Mapping[int, Mapping]) -> Dict:
    """Tabela por realização ON × OFF (obrigatória em todo closing) + alerta
    não-gate quando ON >= 3 × OFF (e ON > 0) em contatos, saídas ou colado."""
    rows, alerts = [], []
    for n in _same_realizations(off_by_n, on_by_n):
        row = {"realization": n}
        for metric in DISCLOSURE_METRICS:
            row[metric] = {"off": off_by_n[n].get(metric), "on": on_by_n[n].get(metric)}
        rows.append(row)
        for metric in ALERT_METRICS:
            off_v, on_v = off_by_n[n].get(metric), on_by_n[n].get(metric)
            if off_v is None or on_v is None:
                continue
            if on_v > 0 and on_v >= 3 * off_v:
                alerts.append(dict(realization=n, metric=metric, off=off_v, on=on_v,
                                   rule="ON >= 3 x OFF"))
    return {"rows": rows, "alerts": alerts}


def evaluate_gates(cycle: str, track, off_by_n: Mapping[int, Mapping],
                   on_by_n: Mapping[int, Mapping]) -> Dict:
    key = normalize_track(track)
    gates = gates_for(cycle, key)
    ns = _same_realizations(off_by_n, on_by_n)
    results = []
    for g in gates:
        off_v = {n: _metric(off_by_n[n], g.metric) for n in ns}
        on_v = {n: _metric(on_by_n[n], g.metric) for n in ns}
        base = dict(id=g.id, name=g.name, kind=g.kind, agg=g.agg, metric=g.metric,
                    direction=g.direction, status=g.status)
        per = [dict(realization=n, off=off_v[n], on=on_v[n]) for n in ns]
        if g.agg in ("sum", "rate"):
            off_sum, on_sum = sum(off_v.values()), sum(on_v.values())
            lines = None
            if g.agg == "rate":
                lines_off = sum(_metric(off_by_n[n], "sample_rows") for n in ns)
                lines_on = sum(_metric(on_by_n[n], "sample_rows") for n in ns)
                if lines_off != lines_on:
                    raise InstrumentError(f"{g.id}: linhas diferentes "
                                          f"(OFF {lines_off} × ON {lines_on})")
                lines = lines_off
            bound = gate_bound(g, off_sum, lines)
            results.append(dict(base, off_sum=off_sum, on_sum=on_sum, lines=lines,
                                threshold=bound, per_realization=per,
                                **{"pass": _passes(g, on_sum, bound)}))
        else:
            failing = []
            for item in per:
                bound = gate_bound(g, item["off"])
                item["threshold"] = bound
                item["pass"] = _passes(g, item["on"], bound)
                if not item["pass"]:
                    failing.append(item["realization"])
            results.append(dict(base, per_realization=per, failing_realizations=failing,
                                **{"pass": not failing}))
    return dict(cycle=str(cycle).strip().upper(), track=key, realizations=ns,
                gates=results, all_pass=all(r["pass"] for r in results),
                disclosure=disclosure(off_by_n, on_by_n))


# ---------------------------------------------------------------------------
# relatório de ruído (D4/C0) — nula caótica
# ---------------------------------------------------------------------------
def _phi(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _p_fail_normal(direction: str, bound: int, mean: float, sd: float) -> float:
    """P(FAIL) com ΣON ~ N(mean, sd²) e correção de continuidade de 0,5."""
    if sd == 0.0:
        ok = mean <= bound if direction == "upper" else mean >= bound
        return 0.0 if ok else 1.0
    if direction == "upper":
        return 1.0 - _phi((bound + 0.5 - mean) / sd)
    return _phi((bound - 0.5 - mean) / sd)


def noise_report(track, off_by_n: Mapping[int, Mapping],
                 inputs: Optional[Mapping[int, str]] = None) -> Dict:
    """μ̂/σ̂ por métrica de gate sobre as realizações OFF e P(FAIL) de cada gate
    sob a nula caótica: por realização = fração dos pares ordenados
    OFF(N')×OFF(N), N' != N, que reprovariam; por soma/taxa = ΣON ~
    N(k·μ̂, k·σ̂²) contra o ΣOFF observado (checagem de sanidade pelos pares)."""
    key = normalize_track(track)
    ns = sorted(off_by_n)
    if len(ns) < 2:
        raise InstrumentError("relatório de ruído exige >= 2 realizações")
    k = len(ns)
    gates = [g for g in GATES if g.tracks is None or key in g.tracks]
    stats = {}
    for name in sorted({g.metric for g in gates}):
        vals = [_metric(off_by_n[n], name) for n in ns]
        mean = sum(vals) / k
        sd = math.sqrt(sum((v - mean) ** 2 for v in vals) / (k - 1))
        stats[name] = dict(values={str(n): v for n, v in zip(ns, vals)},
                           mean=mean, sd=sd, n=k)
    lines = {n: _metric(off_by_n[n], "sample_rows") for n in ns}
    reports = {}
    for g in gates:
        vals = {n: _metric(off_by_n[n], g.metric) for n in ns}
        pairs = [(a, b) for a in ns for b in ns if a != b]
        fails = sum(not _passes(g, vals[a], gate_bound(g, vals[b], lines[b]))
                    for a, b in pairs)
        p_pair = fails / len(pairs)
        rep = dict(id=g.id, name=g.name, kind=g.kind, agg=g.agg, metric=g.metric,
                   direction=g.direction, status=g.status, n_pairs=len(pairs),
                   pair_fail_frac=p_pair, pair_pass_frac=1.0 - p_pair)
        if g.agg in ("sum", "rate"):
            off_sum = sum(vals.values())
            bound = gate_bound(g, off_sum, sum(lines.values()))
            mean = k * stats[g.metric]["mean"]
            sd = math.sqrt(k) * stats[g.metric]["sd"]
            p_fail = _p_fail_normal(g.direction, bound, mean, sd)
            rep.update(off_sum=off_sum, threshold=bound, sum_mean=mean, sum_sd=sd,
                       p_fail_normal=p_fail, p_pass_normal=1.0 - p_fail)
        else:
            rep.update(p_fail_all_indep=1.0 - (1.0 - p_pair) ** k,
                       note="aproximação: realizações independentes")
        reports[g.id] = rep
    payload = dict(
        schema_version=VERSION, kind="noise", track=key, realizations=ns,
        method=("nula caótica: pares ordenados OFF(N')xOFF(N), N' != N; somas: "
                "N(k·mean, k·sd²), sd amostral (ddof=1), correção de continuidade 0,5"),
        metrics=stats, gates=reports,
        inputs=({str(n): inputs[n] for n in sorted(inputs)} if inputs else None),
    )
    return _seal(payload)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _parse_runs(items: List[str]) -> Dict[int, Path]:
    out: Dict[int, Path] = {}
    for item in items:
        n_str, sep, path = item.partition("=")
        if not sep or not n_str.strip().isdigit() or not path:
            raise InstrumentError(f"esperado N=caminho.json, recebido {item!r}")
        n = int(n_str)
        if n in out:
            raise InstrumentError(f"realização repetida: {n}")
        out[n] = Path(path)
    return out


def _load_run_json(path: Path, n: int, track_key: str) -> Dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("schema_version") != VERSION:
        raise InstrumentError(f"{path}: schema {payload.get('schema_version')!r} != {VERSION}")
    if not verify_metrics_sha(payload):
        raise InstrumentError(f"{path}: metrics_sha256 não confere")
    if payload.get("track") != track_key:
        raise InstrumentError(f"{path}: pista {payload.get('track')!r} != {track_key!r}")
    if not payload["integrity"]["ok"]:
        raise InstrumentError(f"{path}: integridade da corrida FALHOU")
    if payload["integrity"]["variedade"] != n:
        raise InstrumentError(f"{path}: N declarado {n} != variedade do log "
                              f"{payload['integrity']['variedade']}")
    return payload


def _emit(payload: Mapping, out: Optional[str]) -> None:
    if out:
        write_exclusive(Path(out), payload)
        print(f"[realismo] gravado {out} metrics_sha256={payload['metrics_sha256']}",
              file=sys.stderr)
    else:
        sys.stdout.write(dump_text(payload))


def _check_out(out: Optional[str]) -> None:
    if out and Path(out).exists():
        raise FileExistsError(out)


def _main_run(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="realismo_metrics.py",
                                 description="REALISMO-1: métricas de UMA corrida")
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--log", required=True, type=Path)
    ap.add_argument("--main-csv", required=True, type=Path)
    ap.add_argument("--events-csv", required=True, type=Path)
    ap.add_argument("--track", required=True)
    ap.add_argument("--out", default=None, help="JSON novo (nunca sobrescreve)")
    ap.add_argument("--arm", default="composite", choices=["composite", "blind"])
    ap.add_argument("--expect-variedade", type=int, default=None)
    ap.add_argument("--expect-main-lines", type=int, default=EXPECTED_MAIN_LINES)
    args = ap.parse_args(argv)
    _check_out(args.out)
    payload = analyze_run(run_id=args.run_id, log=args.log, main_csv=args.main_csv,
                          events_csv=args.events_csv, track=args.track, arm=args.arm,
                          expect_variedade=args.expect_variedade,
                          expected_main_lines=args.expect_main_lines)
    _emit(payload, args.out)
    return 0 if payload["integrity"]["ok"] else 3


def _main_noise(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="realismo_metrics.py noise")
    ap.add_argument("--track", required=True)
    ap.add_argument("--off", required=True, nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    _check_out(args.out)
    key = normalize_track(args.track)
    runs = {n: _load_run_json(p, n, key) for n, p in _parse_runs(args.off).items()}
    payload = noise_report(key, {n: r["metrics"] for n, r in runs.items()},
                           inputs={n: r["metrics_sha256"] for n, r in runs.items()})
    _emit(payload, args.out)
    return 0


def _main_gates(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="realismo_metrics.py gates")
    ap.add_argument("--cycle", required=True)
    ap.add_argument("--track", required=True)
    ap.add_argument("--off", required=True, nargs="+")
    ap.add_argument("--on", required=True, nargs="+")
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    _check_out(args.out)
    key = normalize_track(args.track)
    off = {n: _load_run_json(p, n, key) for n, p in _parse_runs(args.off).items()}
    on = {n: _load_run_json(p, n, key) for n, p in _parse_runs(args.on).items()}
    arms = {r["arm"] for r in off.values()} | {r["arm"] for r in on.values()}
    if len(arms) != 1:
        raise InstrumentError(f"braços misturados: {sorted(arms)}")
    result = evaluate_gates(args.cycle, key, {n: r["metrics"] for n, r in off.items()},
                            {n: r["metrics"] for n, r in on.items()})
    payload = dict(schema_version=VERSION, kind="gates", **result,
                   inputs=dict(off={str(n): off[n]["metrics_sha256"] for n in sorted(off)},
                               on={str(n): on[n]["metrics_sha256"] for n in sorted(on)}))
    payload = _seal(payload)
    _emit(payload, args.out)
    return 0 if payload["all_pass"] else 1


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0] == "noise":
        return _main_noise(argv[1:])
    if argv and argv[0] == "gates":
        return _main_gates(argv[1:])
    return _main_run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
