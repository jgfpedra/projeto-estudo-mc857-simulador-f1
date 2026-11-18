"""Diagnóstico da corrida de 10 carros — Fase C/G da investigação v2 vs v4.

Replica EXATAMENTE o loop da corrida visual (run_race_10_cars.py):
  mesmos drivers, mesmo grid, mesmo NeuralRaceController (governador de
  velocidade + anti-stall + recuperação de pista), mesma física e grip real.
Rodando headless e registrando, a cada tick, por carro:
  velocidade, s na pista, lat, th/brk/steer aplicados, ação bruta da política,
  intervenções do governador/anti-stall/recovery.

Modo --controller professor (PASSO 1 v14, gate all-professor):
  10 ReferenceControllers simultâneos (professor de tráfego da FASE 1),
  cada um consumindo posição/velocidade dos outros 9 como tráfego.
  Composição de autoridade SEM governor (ver ProfessorRaceController).

Uso:
  .venv/bin/python model_train/race_diagnostic.py \
      --actor model_train/v4/multi_context_rl_actor_best.keras --ticks 600
  .venv/bin/python model_train/race_diagnostic.py \
      --controller professor --ticks 6000 --laps 99 --track interlagos
"""
from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Optional

MODEL_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODEL_DIR.parent.parent
BACKEND = MODEL_DIR.parent
for p in (str(PROJECT_ROOT), str(BACKEND), str(BACKEND / 'scripts')):
    if p not in sys.path:
        sys.path.insert(0, p)

import numpy as np
import pandas as pd

# camada da corrida (mesma instância de código do run_race_10_cars.py) —
# ProfessorRaceController herda dele as camadas rejoin/recovery/blocked
from scripts.simulation import run_race_10_cars as R
from backend.model_train.reference_controller import signed_dist_s


def parse_mixed(spec: str, n_total: int = 10):
    """A2 (FASE 5): parse de --mixed "traffic:2,edge:8".
    FASE 4 v15 (wiring): + grupo 'composite' ("composite:N,edge:M") — o
    grupo composite usa o composite COMPLETO por carro (solo v10 + residual
    r2 + gate g), não um ator .keras único.

    PASS-1: + grupo 'professor', formado por ReferenceControllers; pode ser
    combinado com edge para medir o opt-in em apenas parte do campo.

    Retorna grupos entre {'composite', 'traffic', 'edge', 'professor'}.
    Valida: soma == n_total, chaves conhecidas, contagens positivas.
    """
    if not spec:
        return None
    groups = {}
    for part in spec.split(','):
        part = part.strip()
        if ':' not in part:
            raise ValueError(f"--mixed: trecho '{part}' sem ':' (formato grupo:N)")
        k, v = part.split(':')
        k, v = k.strip(), int(v)
        if k not in ('traffic', 'edge', 'composite', 'professor'):
            raise ValueError(
                f"--mixed: grupo '{k}' desconhecido "
                "(use composite/traffic/edge/professor)")
        if v <= 0:
            raise ValueError(f"--mixed: contagem de '{k}' deve ser > 0")
        groups[k] = v
    if sum(groups.values()) != n_total:
        raise ValueError(f"--mixed: soma {sum(groups.values())} != {n_total} carros")
    return groups


_XY_DIAG_COLUMNS = ("body_x", "body_y", "ns_raw")
_REJOIN_TEL_COLUMNS = (
    "off_window_id", "off_age_ticks", "anchor_x", "anchor_y", "anchor_s",
    "target_x", "target_y", "reentry_heading_err_deg", "target_kappa",
)


def _pass_decision_prior_snapshots(rows, drivers, project_row,
                                  track_len_s, count=14):
    """Rebuild the last complete 5 Hz windows from existing CSV rows.

    The function is read-only: ``rows`` is the same list used by the race
    writer. It returns one ordered list per driver, or ``None`` if the tail is
    incomplete or does not contain consecutive sampled ticks.
    """
    if rows is None:
        return None
    driver_ids = [str(drv.driver_id) for drv in drivers]
    by_tick = {}
    for row in reversed(rows):
        tick = int(row['tick'])
        bucket = by_tick.setdefault(tick, {})
        drv_id = str(row['drv'])
        if drv_id in driver_ids and drv_id not in bucket:
            bucket[drv_id] = row
        if len(bucket) == len(driver_ids):
            complete = [key for key, value in by_tick.items()
                        if len(value) == len(driver_ids)]
            if len(complete) >= count:
                break
    complete_ticks = sorted(
        key for key, value in by_tick.items()
        if len(value) == len(driver_ids))
    if len(complete_ticks) < count:
        return None
    complete_ticks = complete_ticks[-count:]
    if any(b - a != 2 for a, b in zip(complete_ticks, complete_ticks[1:])):
        return None

    out = {driver_id: [] for driver_id in driver_ids}
    for tick in complete_ticks:
        bucket = by_tick[tick]
        projected = {driver_id: project_row(bucket[driver_id])
                     for driver_id in driver_ids}
        cars_by_id = {
            driver_id: dict(
                driver_id=driver_id, s=float(projected[driver_id][0]),
                lat=float(projected[driver_id][1]),
                speed=float(bucket[driver_id]['speed']))
            for driver_id in driver_ids
        }
        for driver_id in driver_ids:
            ego = bucket[driver_id]
            ego_s, ego_lat = projected[driver_id]
            out[driver_id].append(dict(
                t_s=float(ego['t_s']), s_ego=float(ego_s),
                lat_ego=float(ego_lat), v_ego=float(ego['speed']),
                cars=[car for other_id, car in cars_by_id.items()
                      if other_id != driver_id],
                track_len_s=float(track_len_s)))
    return out


def _pass_decision_snapshot(driver_id, t_s, s_ego, lat_ego, v_ego,
                            drivers, snap_s, snap_lat, snap_v, track_len_s):
    """Build the current read-only snapshot in the same shape as CSV history."""
    cars = []
    for j, other in enumerate(drivers):
        if str(other.driver_id) == str(driver_id):
            continue
        cars.append(dict(
            driver_id=str(other.driver_id), s=float(snap_s[j]),
            lat=float(snap_lat[j]), speed=float(snap_v[j])))
    return dict(t_s=float(t_s), s_ego=float(s_ego), lat_ego=float(lat_ego),
                v_ego=float(v_ego), cars=cars,
                track_len_s=float(track_len_s))


class RejoinWindowTelemetry:
    """Read-only logical-tick snapshots for the opt-in v3.5 CSV writer."""

    def __init__(self):
        self._cars = {}

    def observe(self, driver_id, tick, offtrack, x, y, s):
        st = self._cars.setdefault(driver_id, dict(
            next_id=0, active_id=0, entry_tick=None, was_off=False,
            anchor=None, pending_reentry_id=None, pending_reentries=0,
            last_sample_id=0))
        tick = int(tick)
        if offtrack:
            if not st['was_off']:
                st['next_id'] += 1
                st['active_id'] = st['next_id']
                st['entry_tick'] = tick
            window_id = st['active_id']
            age = tick - st['entry_tick']
        else:
            if st['was_off']:
                st['pending_reentry_id'] = st['active_id']
                st['pending_reentries'] += 1
            st['active_id'] = 0
            st['entry_tick'] = None
            st['anchor'] = (float(x), float(y), float(s))
            window_id, age = 0, 0
        st['was_off'] = bool(offtrack)
        if st['anchor'] is None:
            raise ValueError(f"v3.5 sem âncora on-track inicial para {driver_id}")
        ax, ay, anchor_s = st['anchor']
        return dict(off_window_id=window_id, off_age_ticks=age,
                    anchor_x=ax, anchor_y=ay, anchor_s=anchor_s)

    def sample_reentry(self, driver_id, snapshot):
        """Mark only a return visible between adjacent emitted 5 Hz rows."""
        st = self._cars[driver_id]
        current_id = int(snapshot['off_window_id'])
        marker = False
        if current_id == 0 and st['pending_reentries']:
            if st['pending_reentries'] > 1:
                raise ValueError(
                    f"v3.5 múltiplas reentradas entre amostras para {driver_id}")
            marker = (st['pending_reentry_id'] == st['last_sample_id']
                      and st['last_sample_id'] != 0)
            st['pending_reentry_id'] = None
            st['pending_reentries'] = 0
        st['last_sample_id'] = current_id
        return marker


def _rejoin_tel_heading_error(prev_xy, curr_xy, s, heading_at_s):
    """CSV-course minus frozen track tangent, in degrees; zero if unidentifiable."""
    dx = float(curr_xy[0]) - float(prev_xy[0])
    dy = float(curr_xy[1]) - float(prev_xy[1])
    if math.hypot(dx, dy) <= 1e-9:
        return 0.0
    course = math.atan2(dy, dx)
    tangent = float(heading_at_s(float(s)))
    error = (course - tangent + math.pi) % (2.0 * math.pi) - math.pi
    return math.degrees(error)


def _install_rejoin_tel_target_capture(ctrl):
    """Wrap the live target resolver pass-through and retain its exact result."""
    captured = {}
    original = ctrl._rejoin_target_point

    def capture(driver_id, s_live, projection_x_live, projection_y_live, ahead_m):
        target = original(driver_id, s_live, projection_x_live,
                          projection_y_live, ahead_m)
        target_s = float(s_live) + float(ahead_m)
        captured[driver_id] = dict(
            target_x=float(target[0]), target_y=float(target[1]),
            target_kappa=float(ctrl._kappa_signed(target_s)))
        return target

    ctrl._rejoin_target_point = capture
    return captured


def _add_writer_v35_argument(parser):
    parser.add_argument('--writer-v35', action='store_true', default=False,
                        help='telemetria aditiva de rejoin v3.5; opt-in, default OFF')
    return parser


def _add_corpus_dump_argument(parser):
    parser.add_argument(
        '--corpus-dump', type=str, default=None,
        help='Composite v15 JSONL.GZ corpus dump; opt-in and read-only',
    )
    return parser


def _track_geometry_id(track):
    key = str(getattr(track, 'name', '')).strip().lower()
    if 'monaco' in key:
        return 'monaco_v2'
    if 'são paulo' in key or 'sao paulo' in key or 'interlagos' in key:
        return 'interlagos_v2'
    if key not in {'interlagos_v2', 'monaco_v2'}:
        raise ValueError(f'--corpus-dump requer geometria frozen conhecida: {key!r}')
    return key


_CORPUS_GEOMETRY_SHA256 = {
    'interlagos_v2': 'c4617650983df9b1141296dac953b0e4be03f0c06c1de006340233c39e308613',
    'monaco_v2': 'af3125959ade1f82062d9c9fe0dfa8020d31e431d919408ae4d293f0fac20bf2',
}


def _capture_composite_dump_rows(dumper, ctrl, engine, drivers, tick,
                                 compound_mapping):
    """Capture the exact edge+traffic observation primitives without mutation."""
    from backend.model_train.f1_env import compute_traffic_features

    n = len(drivers)
    drv_s = np.zeros(n, dtype=np.float64)
    drv_lat = np.zeros(n, dtype=np.float64)
    drv_v = np.zeros(n, dtype=np.float64)
    xs = np.zeros(n, dtype=np.float64)
    ys = np.zeros(n, dtype=np.float64)
    headings = np.zeros(n, dtype=np.float64)
    physical = []
    for i, drv in enumerate(drivers):
        phys = engine.physics.get_state(engine.handles[drv.driver_id])
        physical.append(phys)
        xs[i], ys[i] = phys['x'], phys['y']
        headings[i] = phys['heading_rad']
        A, AB, L = ctrl._A, ctrl._AB, ctrl._seg_len
        ap_x, ap_y = phys['x'] - A[:, 0], phys['y'] - A[:, 1]
        t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / (L * L + 1e-9), 0.0, 1.0)
        px, py = A[:, 0] + t * AB[:, 0], A[:, 1] + t * AB[:, 1]
        d = np.hypot(px - phys['x'], py - phys['y'])
        idx = int(np.argmin(d))
        cross = AB[idx, 0] * (phys['y'] - py[idx]) - AB[idx, 1] * (phys['x'] - px[idx])
        drv_s[i] = ctrl._seg_cum[idx] + float(t[idx]) * L[idx]
        drv_lat[i] = float(d[idx]) if cross >= 0.0 else -float(d[idx])
        drv_v[i] = phys['speed_mps']

    rays = ctrl._cast_rays_batch(xs, ys, headings, drv_s).astype(np.float32)
    for i, drv in enumerate(drivers):
        phys = physical[i]
        s = float(drv_s[i])
        obs23 = _obs23(ctrl, engine, drv, phys, s, drv_lat[i], drivers)
        telemetry = np.concatenate([obs23, rays[i]]).astype(np.float32)
        traffic = compute_traffic_features(
            drv_v[i], drv_s[i], ctrl._half_width, ctrl._track_len_s,
            [(drv_s[j], drv_lat[j], drv_v[j]) for j in range(n) if j != i],
        )
        state = engine.states[drv.driver_id]
        ctx = np.array([
            state.tyre.tyre_life / ctrl.OBS_TYRE_LIFE,
            state.car.fuel_kg / ctrl.OBS_FUEL_KG,
        ], dtype=np.float32)
        curvature = float(obs23[11]) / ctrl.KAPPA_OBS_SCALE
        from scripts.training.composite_corpus_dump import resolve_compound_id
        compound_id = resolve_compound_id(
            getattr(getattr(state.tyre, 'model', None), 'compound', None),
            compound_mapping,
        )
        dumper.write_row(
            drv=drv.driver_id,
            tick=tick,
            t_s=float(engine.sim_ts),
            track_id=0,
            compound_id=compound_id,
            telemetry_edge_34=telemetry,
            ctx=ctx,
            traffic_features_12=traffic,
            speed_mps=float(drv_v[i]),
            curvature_ahead=curvature,
        )


def _write_race_diag_csv(df, out_path, header_metadata, include_xy=None,
                         writer_v35=False):
    """Escreve CSV v3.4; RACE_DIAG_NO_XY=1 restaura o CSV v3.3 byte a byte.

    ``header_metadata`` contém o sufixo estável iniciado em `` | track_...``.
    ``include_xy`` é fixado no início da corrida para não haver divergência
    entre a coleta e a versão do cabeçalho.
    """
    if include_xy is None:
        include_xy = os.environ.get("RACE_DIAG_NO_XY") != "1"
    if writer_v35 and not include_xy:
        raise ValueError("CSV v3.5 exige XY habilitado")
    out = df
    missing_tel = ([col for col in _REJOIN_TEL_COLUMNS if col not in out.columns]
                   if writer_v35 else [])
    if missing_tel:
        raise ValueError(f"CSV v3.5 sem colunas de telemetria obrigatórias: {missing_tel}")
    if include_xy:
        missing = [col for col in _XY_DIAG_COLUMNS if col not in out.columns]
        if missing:
            raise ValueError(f"CSV v3.4 sem colunas XY obrigatórias: {missing}")
        legacy = [col for col in out.columns
                  if col not in _XY_DIAG_COLUMNS and col not in _REJOIN_TEL_COLUMNS]
        out = out[legacy + list(_XY_DIAG_COLUMNS)
                  + (list(_REJOIN_TEL_COLUMNS) if writer_v35 else [])]
        version = "race_diag_v3_5_rejoin_tel" if writer_v35 else "race_diag_v3_4_xyraw"
    else:
        out = out.drop(columns=list(_XY_DIAG_COLUMNS), errors="ignore")
        version = "race_diag_v3_3_res16d"
    with open(out_path, "w") as f:
        f.write(f"# {version}{header_metadata}\n")
        out.to_csv(f, index=False)


def assign_groups(driver_ids, mixed):
    """driver_id -> 'composite' | 'traffic' | 'edge'. Os primeiros N
    driver_ids (ordem do grid original) por grupo na ordem fixa abaixo; a
    posição FÍSICA no grid é embaralhada à parte; o grupo é por driver_id."""
    out = {}
    i = 0
    for g, n in (('professor', mixed.get('professor', 0)),
                 ('composite', mixed.get('composite', 0)),
                 ('traffic', mixed.get('traffic', 0)),
                 ('edge', mixed.get('edge', 0))):
        for _ in range(n):
            out[driver_ids[i]] = g
            i += 1
    return out


def mixed_summary(df, groups):
    """Métricas por GRUPO e por par de grupos de uma corrida mista (A2 FASE 5).

    Convenções: contatos por grupo = amostras 5 Hz com car_car>0 do carro
    (cada contato físico conta para AMBOS os lados); pares de grupos via
    reconstrução de proximidade (|Δs|<8m no mesmo tick); hesitação = episódio
    v<2 m/s de ≥0,4 s após o carro já ter passado de 10 m/s (pós-largada);
    voltas por cruzamento de wrap; rolante = entre wraps consecutivos.
    """
    res = dict(total_contacts=int((df.car_car > 0).sum()),
               post_launch=int(((df.car_car > 0) & (df.t_s > 60)).sum()))
    pair_hits = {}
    for _t, g in df[df.car_car > 0].groupby('tick'):
        ss = g[['drv', 's']].values
        for i in range(len(ss)):
            for j in range(i + 1, len(ss)):
                if abs(ss[i][1] - ss[j][1]) < 8.0:
                    k = '-'.join(sorted([groups[ss[i][0]], groups[ss[j][0]]]))
                    pair_hits[k] = pair_hits.get(k, 0) + 1
    res['pair_contacts'] = pair_hits
    for gname in ('professor', 'traffic', 'edge', 'composite'):
        if gname not in groups.values():
            continue
        gdf = df[df.drv.map(groups) == gname]
        laps, roll, hes = 0, [], 0
        for _drv, g2 in gdf.sort_values('tick').groupby('drv'):
            s = g2.s.values
            tick = g2.tick.values
            cross = [k for k in range(1, len(s)) if s[k] < s[k - 1] - 2000]
            laps += len(cross)
            # tempo ENTRE wraps em VALORES DE TICK (× 0.1 s/tick lógico) —
            # nunca em índices de amostra (amostras são 5 Hz = 0.2 s)
            roll += [(tick[b] - tick[a]) * 0.1 for a, b in zip(cross[:-1], cross[1:])]
            v = g2.speed.values
            above = np.where(v > 10)[0]
            if len(above) == 0:
                continue
            slow, run = v[above[0]:] < 2.0, 0
            for x in slow:
                if x:
                    run += 1
                else:
                    if run >= 2:
                        hes += 1
                    run = 0
            if run >= 2:
                hes += 1
        res[gname] = dict(
            cars=int(gdf.drv.nunique()),
            contacts=int((gdf.car_car > 0).sum()),
            post_launch=int(((gdf.car_car > 0) & (gdf.t_s > 60)).sum()),
            laps=laps,
            rolling_med=float(np.median(roll)) if roll else None,
            hesitations=hes,
            offtrack_pct=100.0 * float(gdf.offtrack.mean()))
    return res


class _RaceEnvView:
    """Adaptador engine→ReferenceController (modo professor).

    Expõe EXATAMENTE a interface que o professor consome do
    F1MultiContextEnv (engine/driver_id/projeção/ponto/steer_limit),
    emprestando os métodos REAIS do env — fonte única de verdade, sem
    duplicação de algoritmo de projeção. As tabelas de segmentos são
    COMPARTILHADAS (por referência) com as do controller da corrida.
    """

    def __init__(self, engine, tables, driver_id):
        from backend.model_train.f1_env import F1MultiContextEnv
        _RaceEnvView._project_on_path = F1MultiContextEnv._project_on_path
        _RaceEnvView._point_at = F1MultiContextEnv._point_at
        _RaceEnvView._kappa_signed = F1MultiContextEnv._kappa_signed
        _RaceEnvView._heading_at = F1MultiContextEnv._heading_at
        _RaceEnvView.steer_limit_rad = staticmethod(F1MultiContextEnv.steer_limit_rad)
        (self._wps_arr, self._seg_AB, self._seg_len, self._seg_cum,
         self._seg_heading, self._track_len_s, self._half_width) = tables
        self.engine = engine
        self.driver_id = driver_id


class ProfessorRaceController(R.NeuralRaceController):
    """10 professores de tráfego simultâneos (gate all-professor v14).

    Cada carro é dirigido por um ReferenceController (FASE 1: car-following
    + offset lateral) que recebe os outros 9 como tráfego — a mesma camada
    que os fantasmas do env usarão na FASE 2.

    COMPOSIÇÃO DE AUTORIDADE (decisão explícita do PASSO 1 v14):
        professor → rejoin → recovery → blocked         (SEM governor)
      - professor: pure pursuit + v_plan físico (a frenagem já está
        planejada no perfil; o sf=0,80 já embute a margem de segurança);
      - rejoin: fora do asfalto → esterço p/ o centro + teto de 8 m/s;
      - recovery: imobilizado → torque progressivo, freio ZERO, saída
        SOMENTE por progresso físico real (máquina herdada do neural);
      - blocked: parado em contato com outro carro → torque limitado.
      SEM GOVERNOR: o governor assiste a política NEURAL (que não planeja
      frenagem); o professor JÁ freia pelo v_plan — aplicar os dois seria
      frenagem dupla e destruiria o pace calibrado (16/16 nas 8 pistas).
      O governor permanece APENAS no modo neural (superclasse intacta).

    Herda da superclasse as camadas de autoridade e a instrumentação do
    CSV (constantes OBS_*, _wrap/_heading_at/_kappa_signed) — só o __init__
    (sem ator neural) e o predict_batch são substituídos.
    """

    # PROF-REPAIR-1 (prereg fc0a939 §2): CONSTANTES PINADAS do reparo —
    # pacing pós-reentrada. UM fator; flag opt-in default-OFF.
    PROF_REPAIR_ENABLED_DEFAULT = False
    PROF_REPAIR_HOLD_S = 5.0     # janela de settling (tick 0,1 s)
    PROF_REPAIR_V0_MPS = 8.0     # = REJOIN_TARGET_MPS (velocidade de reentrada)

    def __init__(self, track, sf=0.80, sf_range=None, machine_only=False,
                 rejoin_mode: str = "bearing", anti_glue: bool = False,
                 prof_repair: bool = False, pass_decision: bool = False,
                 leader_yield: bool = False,
                 prof_curva: bool = False,
                 prof_control: bool = False,
                 prof_grip: bool = False,
                 prof_pace: bool = False,
                 prof_pace_eta: str = 'eta1',
                 physics_frontier_file: Optional[str] = None):
        """sf_range=(lo, hi): FASE 2 — sf POR PILOTO determinístico (crc32 do
        driver_id), U[lo,hi]; profile PRÓPRIO por piloto. None = homogêneo
        (controle, comportamento histórico).

        SANIDADE-0 (prereg 1007636 §1): rejoin_mode/anti_glue espelham o modo
        neural — M2 perceptive (ângulo raso + grama 6 m/s) e M3 (preventivo
        do professor + breaker). Defaults = bit-idêntico ao histórico.

        PROF-REPAIR-1 (prereg fc0a939): prof_repair=True ativa o pacing
        pós-reentrada (janela 5,0 s com rampa v: 8 m/s -> v_plan). Default
        OFF = bit-idêntico ao professor histórico.

        PROF-CURVA-1: prof_curva=True ativa o teto local de velocidade proporcional
        ao raio físico viável lido de physics_frontier_current.json. Default OFF
        = bit-idêntico ao professor histórico.

        PROF-CONTROL-1: prof_control=True ativa o feedforward cinemático
        arctan(L*kappa_local) + lookahead modulado por curvatura (c_ld derivado
        do LAGO_ANATOMY.json pela regra §3 do prereg). Default OFF
        = bit-idêntico ao professor histórico.

        PROF-GRIP-1: prof_grip=True ativa o teto de pacing grip-sensível nas
        janelas canônicas de C01/C06/C07/C08 (v_alvo = v_plan·fator(grip),
        grip_atual = tyre.grip_multiplier por tick). Default OFF
        = bit-idêntico ao professor histórico."""
        from backend.model_train.velocity_profile import VelocityProfile
        import zlib
        self._sf_range = sf_range
        self.REJOIN_MODE = str(rejoin_mode)
        self.ANTI_GLUE_ENABLED = bool(anti_glue)
        self.PROF_REPAIR_ENABLED = bool(prof_repair)
        self.PROF_CONTROL_ENABLED = bool(prof_control)
        self._prof_control_kappa = None
        if self.PROF_CONTROL_ENABLED:
            # PROF-CONTROL-1: κ local instantânea assinada derivada UMA vez
            # dos waypoints da pista frozen e emprestada a cada
            # ReferenceController (o adapter _RaceEnvView não expõe .track).
            from backend.model_train.prof_curva import _instantaneous_kappa_profile
            from backend.model_train import prof_control as _prof_mod
            self._prof_control_kappa = _instantaneous_kappa_profile(
                np.array(track.waypoints, dtype=np.float64), ds_target=4.0)
            _prof_mod.derive_c_ld()  # log da derivação (uma vez no processo)
        self.PROF_GRIP_ENABLED = bool(prof_grip)
        self._prof_grip_windows = None
        if self.PROF_GRIP_ENABLED:
            # PROF-GRIP-1: janelas canônicas das 4 crônicas derivadas UMA vez
            # dos waypoints da pista frozen e emprestadas a cada
            # ReferenceController (o adapter _RaceEnvView não expõe .track).
            from backend.model_train import prof_grip as _pg
            self._prof_grip_windows = _pg.corner_windows(
                np.array(track.waypoints, dtype=np.float64))
        self.PROF_PACE_ENABLED = bool(prof_pace)
        self._prof_pace_windows = None
        self._prof_pace_kappa_inst = None
        self._prof_pace_eta = str(prof_pace_eta)
        if self.PROF_PACE_ENABLED:
            # PROF-PACE-1: janelas canônicas + κ_inst derivadas UMA vez dos
            # waypoints da pista frozen; NO-OP EXPLÍCITO fora de Interlagos
            # (o perfil capado só existe para a pista pinada).
            from backend.model_train import prof_pace as _pp
            if _pp.is_interlagos(str(getattr(track, 'frozen_sha256', ''))):
                self._prof_pace_windows = _pp.chronic_windows(
                    np.array(track.waypoints, dtype=np.float64))
                self._prof_pace_kappa_inst = _pp.kappa_inst_interpolator(
                    np.array(track.waypoints, dtype=np.float64))
            else:
                print('[prof-pace] NO-OP: pista não é Interlagos '
                      f'({str(getattr(track, "frozen_sha256", "?"))[:16]}) — '
                      'comportamento histórico preservado')
        self.PASS_DECISION_ENABLED = bool(pass_decision)
        self.LEADER_YIELD_ENABLED = bool(leader_yield)
        self.PROF_CURVA_ENABLED = bool(prof_curva)
        self.PHYSICS_FRONTIER_FILE = physics_frontier_file
        self._yield_windows = {}
        self._yield_stats = {}
        self._pass_rejoin_lock_until = {}
        self._pass_contact_cursor = 0
        self._repair_state = {}   # PROF-REPAIR-1: janela por driver
        self._glue_state = {}
        # estado exigido pelas camadas herdadas / pelo loop de diagnóstico
        self.obs_mode = 'legacy'
        self.mappings = {}
        self.compound_id_map = {}
        self._stuck_since = {}
        self._recovery_state = {}
        self._blocked_events = {}
        self.last_authority = {}
        self._prev_actions = {}
        self._build_tables(np.array(track.waypoints, dtype=np.float64),
                           float(getattr(track, 'width_m', 12.0)) / 2.0)
        # FASE 2: heterogêneo = 1 profile POR PILOTO com sf próprio
        # (determinístico: crc32(driver_id)); homogêneo = profile único
        if sf_range is not None:
            lo, hi = sf_range
            self._sf_by_driver = {}
            self._vp = None
        else:
            self._sf_by_driver = None
            if self.PROF_CURVA_ENABLED:
                from backend.model_train.prof_curva import build_capped_velocity_profile
                frontier_f = self.PHYSICS_FRONTIER_FILE or 'experiments/prof-curva-1/physics_frontier_current.json'
                self._vp = build_capped_velocity_profile(
                    np.array(track.waypoints, dtype=np.float64),
                    frontier_path=frontier_f,
                    grip_mult=0.788, sf=sf,
                    ds_target=4.0, smooth_window_m=20.0,
                )
            else:
                self._vp = VelocityProfile(np.array(track.waypoints, dtype=np.float64),
                                            grip_mult=0.788, sf=sf,
                                            ds_target=4.0, smooth_window_m=20.0)
        self._sf_base = sf
        self._machine_only = machine_only   # FASE 2b Exp1 (usado em _ensure_professors)
        self._tables = (self._A, self._AB, self._seg_len, self._seg_cum,
                        self._seg_heading, self._track_len_s, self._half_width)
        self.professors = []
        self._engine_ref = None

    def _ensure_professors(self, engine, drivers):
        if self._engine_ref is engine and len(self.professors) == len(drivers):
            return
        from backend.model_train.reference_controller import ReferenceController
        from backend.model_train.velocity_profile import VelocityProfile
        self.professors = []
        for drv in drivers:
            if self._sf_range is not None:
                lo, hi = self._sf_range
                # determinístico por piloto (reproducível) — FASE 2.1
                import zlib
                frac = (zlib.crc32(drv.driver_id.encode()) % 1000) / 1000.0
                sf_i = lo + (hi - lo) * frac
                self._sf_by_driver[drv.driver_id] = round(sf_i, 3)
                if self.PROF_CURVA_ENABLED:
                    from backend.model_train.prof_curva import build_capped_velocity_profile
                    frontier_f = self.PHYSICS_FRONTIER_FILE or 'experiments/prof-curva-1/physics_frontier_current.json'
                    vp_i = build_capped_velocity_profile(
                        np.array(self._A, dtype=np.float64),
                        frontier_path=frontier_f,
                        grip_mult=0.788, sf=sf_i,
                        ds_target=4.0, smooth_window_m=20.0,
                    )
                else:
                    vp_i = VelocityProfile(np.array(self._A, dtype=np.float64),
                                            grip_mult=0.788, sf=sf_i,
                                            ds_target=4.0, smooth_window_m=20.0)
            else:
                vp_i = self._vp
            prof_i = ReferenceController(_RaceEnvView(engine, self._tables, drv.driver_id),
                                         velocity_profile=vp_i,
                                         pass_decision=self.PASS_DECISION_ENABLED,
                                         leader_yield=self.LEADER_YIELD_ENABLED,
                                         prof_control=self.PROF_CONTROL_ENABLED,
                                         prof_control_kappa=self._prof_control_kappa,
                                         prof_grip=self.PROF_GRIP_ENABLED,
                                         prof_grip_windows=self._prof_grip_windows,
                                         prof_pace=self.PROF_PACE_ENABLED,
                                         prof_pace_windows=self._prof_pace_windows,
                                         prof_pace_kappa_inst=self._prof_pace_kappa_inst,
                                         prof_pace_eta=self._prof_pace_eta)
            prof_i._overtake_machine_only = self._machine_only  # FASE 2b Exp1
            self.professors.append(prof_i)
        self._engine_ref = engine

    def _project_signed(self, x, y):
        """(s, lat com sinal) usando as tabelas da corrida (+ = esquerda)."""
        A, AB, L = self._A, self._AB, self._seg_len
        ap_x, ap_y = x - A[:, 0], y - A[:, 1]
        t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / (L * L + 1e-9), 0.0, 1.0)
        proj_x = A[:, 0] + t * AB[:, 0]
        proj_y = A[:, 1] + t * AB[:, 1]
        d = np.hypot(proj_x - x, proj_y - y)
        idx = int(np.argmin(d))
        s = self._seg_cum[idx] + float(t[idx]) * L[idx]
        cross = AB[idx, 0] * (y - proj_y[idx]) - AB[idx, 1] * (x - proj_x[idx])
        signed = float(d[idx]) if cross >= 0.0 else -float(d[idx])
        return s, signed

    def _project_signed_from_raw_row(self, row):
        """Rebuild signed `(s, lat)` from CSV raw XY and frozen nearest segment."""
        idx = int(row['ns_raw'])
        if idx < 0 or idx >= len(self._A):
            raise ValueError(f"ns_raw fora da geometria frozen: {idx}")
        x, y = float(row['body_x']), float(row['body_y'])
        ax, ay = self._A[idx]
        abx, aby = self._AB[idx]
        length = float(self._seg_len[idx])
        t = float(np.clip(((x - ax) * abx + (y - ay) * aby)
                          / (length * length + 1e-9), 0.0, 1.0))
        px, py = ax + t * abx, ay + t * aby
        distance = math.hypot(float(px) - x, float(py) - y)
        cross = abx * (y - py) - aby * (x - px)
        signed = distance if cross >= 0.0 else -distance
        s = self._seg_cum[idx] + t * length
        if (abs(float(s) - float(row['s'])) > 1e-6
                or abs(abs(signed) - float(row['lat'])) > 1e-6):
            raise ValueError(
                "ns_raw/body XY não reproduzem a projeção do CSV para "
                f"{row['drv']} no tick {row['tick']}")
        return float(s), float(signed)

    def predict_batch(self, engine, drivers, waypoints, track_id=0,
                      sim_time_s=None, sample_5hz=False,
                      active_driver_ids=None, pass_decision_history=None):
        from backend.model_train.f1_env import F1MultiContextEnv
        self._ensure_professors(engine, drivers)
        n = len(drivers)
        sim_time_s = float(engine.sim_ts if sim_time_s is None else sim_time_s)
        active_pass_ids = (None if active_driver_ids is None
                           else set(active_driver_ids))
        pass_contact_pairs = set()
        if self.PASS_DECISION_ENABLED or self.LEADER_YIELD_ENABLED:
            collector = engine.physics.contact_collector
            if collector is None:
                raise RuntimeError(
                    "--pass-decision exige o contact_collector solver ativo")
            recent_events = collector[self._pass_contact_cursor:]
            self._pass_contact_cursor = len(collector)
            for event in recent_events:
                a, b = event.get('drv_a'), event.get('drv_b')
                if a is not None and b is not None:
                    pass_contact_pairs.add(tuple(sorted((str(a), str(b)))))
        # 1) snapshot de TODOS: (s, lat com sinal, v) — métrica signed_dist_s
        snap_s = np.zeros(n); snap_lat = np.zeros(n); snap_v = np.zeros(n)
        for i, drv in enumerate(drivers):
            phys = engine.physics.get_state(engine.handles[drv.driver_id])
            s_i, lat_i = self._project_signed(phys['x'], phys['y'])
            snap_s[i], snap_lat[i], snap_v[i] = s_i, lat_i, phys['speed_mps']

        pass_prior = None
        if (self.PASS_DECISION_ENABLED and sample_5hz
                and sim_time_s >= 60.0):
            pass_prior = _pass_decision_prior_snapshots(
                pass_decision_history, drivers, self._project_signed_from_raw_row,
                self._track_len_s)
            if pass_prior is None:
                raise RuntimeError(
                    "--pass-decision sem 14 snapshots 5 Hz completos "
                    "antes do primeiro tick elegível")

        actions = []
        for i, drv in enumerate(drivers):
            # 2) professor: os outros 9 como tráfego
            traffic = [(snap_s[j], snap_lat[j], snap_v[j])
                       for j in range(n) if j != i]
            prof_i = self.professors[i]
            if self.PASS_DECISION_ENABLED or self.LEADER_YIELD_ENABLED:
                pass_enabled_for_driver = (active_pass_ids is None
                                           or drv.driver_id in active_pass_ids)
                prof_i.PASS_DECISION_ENABLED = pass_enabled_for_driver
                if pass_enabled_for_driver or self.LEADER_YIELD_ENABLED:
                    off_now = (abs(float(snap_lat[i]))
                               > self._half_width * self.OFFTRACK_FACTOR)
                    if off_now:
                        self._pass_rejoin_lock_until[drv.driver_id] = (
                            sim_time_s + prof_i.PASS_DECISION_REJOIN_LOCK_S)
                    locked_until = self._pass_rejoin_lock_until.get(
                        drv.driver_id, 0.0)
                    cars = [{
                        'driver_id': other.driver_id,
                        's': float(snap_s[j]), 'lat': float(snap_lat[j]),
                        'speed': float(snap_v[j]),
                        'cum_dist': float(engine.cum_dist_m.get(
                            other.driver_id, 0.0)),
                    } for j, other in enumerate(drivers) if j != i]
                    context = dict(
                        t_s=sim_time_s,
                        sample_5hz=bool(sample_5hz),
                        allowed=(not off_now and sim_time_s >= locked_until),
                        cars=cars,
                        ego_cum_dist=float(engine.cum_dist_m.get(
                            drv.driver_id, 0.0)),
                        track_len_s=float(self._track_len_s),
                        half_width=float(self._half_width),
                        contact_pairs=pass_contact_pairs,
                    )
                    if self.LEADER_YIELD_ENABLED:
                        yield_candidate = None
                        for j, other in enumerate(drivers):
                            if j == i:
                                continue
                            gap = signed_dist_s(
                                float(snap_s[j]), float(snap_s[i]),
                                self._track_len_s)
                            if not (-20.0 <= gap <= -5.0):
                                continue
                            if abs(float(snap_lat[j]) - float(snap_lat[i])) >= 2.6:
                                continue
                            if abs(float(snap_lat[j])) > (
                                    self._half_width * self.OFFTRACK_FACTOR):
                                continue
                            leader = float(snap_v[i])
                            follower = float(snap_v[j])
                            if leader <= 1.0 or follower < leader:
                                continue
                            # The follower is in FOLLOW/cap when this leader
                            # is its nearest same-line car ahead; equal speed
                            # is expected under the shared v_plan cap.
                            follower_ahead = []
                            for k, _other in enumerate(drivers):
                                if k == j:
                                    continue
                                d_other = signed_dist_s(
                                    float(snap_s[k]), float(snap_s[j]),
                                    self._track_len_s)
                                if (0.0 < d_other < 60.0
                                        and abs(float(snap_lat[k])
                                                - float(snap_lat[j])) < 2.6):
                                    follower_ahead.append(d_other)
                            if not follower_ahead or gap != -min(follower_ahead):
                                continue
                            yield_candidate = other.driver_id
                            break
                        window = self._yield_windows.setdefault(
                            drv.driver_id, [])
                        if sample_5hz and sim_time_s >= 60.0:
                            window.append(yield_candidate)
                            del window[:-15]
                        elif sim_time_s < 60.0:
                            window.clear()
                        target = (yield_candidate if len(window) == 15
                                  and window[-1] is not None
                                  and all(x == window[-1] for x in window)
                                  else None)
                        if target is not None and sim_time_s >= 60.0:
                            context.update(
                                leader_yield_engage_follower=target,
                                leader_yield_cars=cars,
                                leader_yield_allowed=bool(
                                    context['allowed']
                                    and sim_time_s >= 60.0),
                                leader_yield_contact_pairs=pass_contact_pairs,
                                leader_yield_ego_cum=context['ego_cum_dist'],
                                leader_yield_follower_cum=next(
                                    car['cum_dist'] for car in cars
                                    if car['driver_id'] == target))
                        elif prof_i._leader_yield_state['active']:
                            active_target = prof_i._leader_yield_state[
                                'follower_id']
                            active_car = next(
                                (car for car in cars
                                 if car['driver_id'] == active_target), None)
                            context.update(
                                leader_yield_allowed=bool(
                                    context['allowed']
                                    and sim_time_s >= 60.0),
                                leader_yield_contact_pairs=pass_contact_pairs,
                                leader_yield_ego_cum=context['ego_cum_dist'],
                                leader_yield_follower_cum=float(
                                    active_car['cum_dist'])
                                if active_car else 0.0)
                    # Inicia a nova máquina apenas após uma janela sustentada
                    # reconhecida por leitura pura dos snapshots 5 Hz que o
                    # runner já guarda para o CSV. Não cria buffer novo nem
                    # grava estado no controller antes do engajamento.
                    if (self.PASS_DECISION_ENABLED
                            and sample_5hz and sim_time_s >= 60.0
                            and context['allowed']):
                        current = _pass_decision_snapshot(
                            drv.driver_id, sim_time_s, snap_s[i], snap_lat[i],
                            snap_v[i], drivers, snap_s, snap_lat, snap_v,
                            self._track_len_s)
                        target_id = prof_i.pass_decision_sustained_target(
                            pass_prior[drv.driver_id] + [current], allowed=True)
                        if target_id is not None:
                            context['decision_engage_target'] = target_id
                    a = prof_i.action(traffic,
                                      pass_decision_context=context)
                else:
                    a = prof_i.action(traffic)
            else:
                a = prof_i.action(traffic)
            speed = float(snap_v[i])
            th, brk, steer_rad = F1MultiContextEnv.action_to_controls(a, speed)

            # ---- SANIDADE-1b M3-v2 (prereg 87214c7 §2): anti-glue no
            # professor — TETOS POR-REALIZAÇÃO via _anti_glue_step COMPARTI-
            # LHADO (herdado da superclasse; v1 MORTO). Este controller É o
            # professor: preventivo escopado (composite_scope=True) +
            # breaker para todos. Default OFF = bit-idêntico. Δlat com SINAL
            # via snap_lat (+ = esquerda).
            glue_breaking = False
            if self.ANTI_GLUE_ENABLED and not (
                    abs(float(snap_lat[i])) > self._half_width * self.OFFTRACK_FACTOR):
                partner = None
                for j in range(n):
                    if j == i:
                        continue
                    dsj = (float(snap_s[j]) - float(snap_s[i])) % self._track_len_s
                    if dsj > self._track_len_s / 2.0:
                        dsj -= self._track_len_s
                    dlatj = float(snap_lat[j]) - float(snap_lat[i])
                    if (abs(dlatj) < self.ANTI_GLUE_NEAR_LAT
                            and abs(dsj) < self.ANTI_GLUE_NEAR_DS):
                        partner = (drivers[j].driver_id, dsj, dlatj,
                                   abs(float(snap_lat[j])), float(snap_v[j]))
                        break
                hw_off = self._half_width * self.OFFTRACK_FACTOR
                if partner is None:
                    th, brk, steer_rad, glue_breaking = self._anti_glue_step(
                        drv.driver_id, None, 0.0, 0.0, speed, 0.0, 0.0, 0.0,
                        True, th, brk, steer_rad, False)
                else:
                    th, brk, steer_rad, glue_breaking = self._anti_glue_step(
                        drv.driver_id, partner[0], partner[1], partner[2],
                        speed, partner[4], abs(float(snap_lat[i])), partner[3],
                        partner[3] > hw_off, th, brk, steer_rad, True)

            # ---- 3. rejoin (fora do asfalto) — MESMA regra do modo neural
            lat_dist = abs(float(snap_lat[i]))
            offtrack = lat_dist > self._half_width * self.OFFTRACK_FACTOR
            if offtrack:
                if self.REJOIN_MODE == 'perceptive':
                    # SANIDADE-0 M2: alvo com ângulo raso (<=15°) por bearing
                    # ao ponto na linha central a |lat|/tan(15°) m (clip
                    # 10-120); cap de superfície grama 6,0 m/s.
                    ahead_m = float(np.clip(
                        lat_dist / math.tan(
                            math.radians(self.REJOIN_PERCEPTIVE_ANGLE_DEG)),
                        self.REJOIN_PERCEPTIVE_AHEAD_MIN_M,
                        self.REJOIN_PERCEPTIVE_AHEAD_MAX_M))
                    phys_i = engine.physics.get_state(
                        engine.handles[drv.driver_id])
                    h_track = self._heading_at(float(snap_s[i]))
                    # ponto na linha central: caminha ahead_m a partir da
                    # projeção do carro (pos − d·n, com n = normal esquerda)
                    px_i = phys_i['x'] + float(snap_lat[i]) * math.sin(h_track)
                    py_i = phys_i['y'] - float(snap_lat[i]) * math.cos(h_track)
                    tx = px_i + ahead_m * math.cos(h_track)
                    ty = py_i + ahead_m * math.sin(h_track)
                    bearing = math.atan2(ty - phys_i['y'], tx - phys_i['x'])
                    berr = self._wrap(bearing - float(phys_i['heading_rad']))
                    steer_rad = float(np.clip(
                        self.REJOIN_BEARING_GAIN * berr,
                        -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
                    rejoin_cap = self.REJOIN_PERCEPTIVE_V_GRASS
                else:
                    correction = -float(np.sign(snap_lat[i])) * min(
                        self.STEER_MAX_RAD, 0.3 + lat_dist / 40.0)
                    steer_rad = correction
                    rejoin_cap = self.REJOIN_TARGET_MPS
                if speed > rejoin_cap * 1.2:
                    excess = (speed - rejoin_cap) / 6.0
                    th, brk = 0.0, max(brk, float(np.clip(excess, 0.3, 1.0)))
                else:
                    th, brk = self.REJOIN_THROTTLE, 0.0

            # ---- PROF-REPAIR-1 (prereg fc0a939 §2): PACING pós-reentrada --
            # UM fator: janela de settling após a transição off->on. O
            # mecanismo da cascata (94,6% baseline) é o PULSO DE PACE —
            # o v_plan frozen exige ritmo pleno já no tick seguinte ao
            # reentry (8 m/s na borda). Rampa: alvo = min(v_plan*margin,
            # V0 + (v_plan*margin − V0)*elapsed/HOLD); long_cmd com a
            # MESMA fórmula do professor (reference_controller.py:452).
            # Esterço do professor INTOCADO. Default OFF = bit-idêntico
            # (estado lazy: só tocado sob a flag).
            if self.PROF_REPAIR_ENABLED:
                rp = self._repair_state.setdefault(
                    drv.driver_id, dict(active=False, t0=0.0, was_off=False))
                if offtrack:
                    rp['active'] = False
                elif rp['was_off']:
                    rp.update(active=True, t0=float(engine.sim_ts))
                if rp['active']:
                    elapsed = float(engine.sim_ts) - rp['t0']
                    hold = self.PROF_REPAIR_HOLD_S
                    if elapsed >= hold:
                        rp['active'] = False
                    else:
                        prof_i = self.professors[i]
                        v_plan = (float(prof_i.v_profile.at(float(snap_s[i])))
                                  * float(getattr(prof_i, 'margin', 1.0)))
                        v0 = self.PROF_REPAIR_V0_MPS
                        alvo = min(v_plan,
                                   v0 + (max(v_plan - v0, 0.0))
                                   * (elapsed / hold))
                        long_cmd = float(np.clip((alvo - speed) / 8.0,
                                                 -1.0, 1.0))
                        th = max(long_cmd, 0.0)
                        brk = max(-long_cmd, 0.0)
                        self.last_authority[drv.driver_id] = 'prof_repair'
                rp['was_off'] = bool(offtrack)

            # ---- 2. recovery (imobilização) — máquina herdada do modo neural
            rec = self._recovery_state.setdefault(drv.driver_id, {})
            progress_m = float(engine.cum_dist_m.get(drv.driver_id, 0.0))
            th, brk, rec_active = self._recovery_step(
                rec, speed, th, brk, engine.sim_ts, progress_m, offtrack)

            # ---- 1. blocked (segurança)
            blocked = speed < 2.0 and self._contact_with_other_car(engine, drivers, i)
            if blocked:
                th = min(th, self.BLOCKED_THROTTLE)
                self._blocked_events[drv.driver_id] = \
                    self._blocked_events.get(drv.driver_id, 0) + 1

            if blocked:
                authority = 'blocked_contact'
            elif glue_breaking:
                authority = 'anti_glue'
            elif rec_active:
                authority = 'recovery_rejoin' if offtrack else 'recovery'
            elif offtrack:
                authority = 'rejoin'
            elif self.last_authority.get(drv.driver_id) == 'prof_repair' \
                    and self.PROF_REPAIR_ENABLED:
                authority = 'prof_repair'
            else:
                authority = 'professor'
            self.last_authority[drv.driver_id] = authority
            actions.append((th, brk, steer_rad))
        return actions

    def pass_decision_summary(self, active_driver_ids=None):
        """Contadores por piloto para o log; não acrescenta colunas ao CSV."""
        selected = (None if active_driver_ids is None
                    else set(active_driver_ids))
        out = {}
        for prof in self.professors:
            if selected is not None and prof.driver_id not in selected:
                continue
            if prof.PASS_DECISION_ENABLED:
                out[prof.driver_id] = prof.pass_decision_summary()
        return out


def main():
    os.environ.setdefault('TF_CPP_MIN_LOG_LEVEL', '3')
    ap = argparse.ArgumentParser()
    ap.add_argument('--actor', required=False, default=None,
                    help='checkpoint .keras (obrigatório só com --controller neural; '
                         'com --profile composite, é o SOLO)')
    ap.add_argument('--profile', type=str, default=None,
                    choices=['race', 'quali', 'traffic', 'composite'],
                    help='v15 FASE 4: composite = solo v10 + residual gated')
    ap.add_argument('--controller', type=str, default='neural',
                    choices=['neural', 'professor'],
                    help='neural = ator da política | professor = 10 ReferenceControllers')
    ap.add_argument('--obs-mode', type=str, default='legacy',
                    choices=['legacy', 'edge', 'traffic'],
                    help='esquema de observação: legacy=23d | edge=34d | traffic=46d (v14)')
    ap.add_argument('--pass-machine-only', action='store_true',
                    help='FASE 2b Exp1: suprime o offset do corredor no follow '
                         '— só a máquina de ultrapassagem desloca lateralmente')
    ap.add_argument('--pass-decision', action='store_true', default=False,
                    help='PASS-1: troca para a decisão opt-in após o primeiro '
                         'engajamento; default OFF')
    ap.add_argument('--leader-yield', action='store_true', default=False,
                    help='YIELD-1: líder cede lateralmente após 15 amostras '
                         '5 Hz de seguidor same-line; default OFF')
    ap.add_argument('--sf-range', type=str, default=None,
                    help='FASE 2: "lo:hi" p/ sf POR PILOTO no all-professor '
                         '(ex: "0.85:0.95", determinístico por driver_id); '
                         'default = homogêneo 0.80 (controle)')
    ap.add_argument('--rejoin-gap', type=float, default=0.0,
                    help='CICLO ALAVANCA: gap à frente X em m no rejoin (0=off)')
    ap.add_argument('--rejoin-handoff', type=str, default=None,
                    choices=['off', 'align'],
                    help='REALISMO-1 C2-B: handoff alinhado após off->on '
                         '(theta=20deg, margem=0,5m, teto=24s); '
                         'default align em composite e off nos demais perfis')
    ramp_group = ap.add_mutually_exclusive_group()
    ramp_group.add_argument('--rejoin-ramp', dest='rejoin_ramp',
                    action='store_true',
                    help='REALISMO-1 C3-B: teto longitudinal pós-reentrada '
                         'por 5,0 s; requer --gov vplan; default ON em composite')
    ramp_group.add_argument('--no-rejoin-ramp', dest='rejoin_ramp',
                    action='store_false',
                    help='desliga explicitamente a rampa homologada de rejoin')
    ap.add_argument('--launch-cap', action='store_true',
                    help='CICLO LARGADA L-1a: teto k×v_plan na janela de largada '
                         '(k=0,8; s<2950; t<30s — PINADOS no prereg a3b8ff0; default off)')
    ap.add_argument('--launch-steer-mute', action='store_true',
                    help='REALISMO-1 C1-B: mute somente o esterço do residual '
                         'na janela D_L; default OFF = byte-idêntico')
    ap.add_argument('--lat-offset-slots', action='store_true',
                    help='REALISMO-1 C6-B: desloca somente obs4 por slot; default OFF')
    ap.add_argument('--c8-rejoin', action='store_true',
                    help='C8-B: perfil de velocidade na grama + gap-check; default OFF')
    ap.add_argument('--launch-stagger', action='store_true',
                    help='CICLO LARGADA L-1b: release escalonado por slot de grid '
                         '(Δt=1,0 s/slot frente->trás; prereg cd3ca5e; default off)')
    ap.add_argument('--pguard', action='store_true',
                    help='SANIDADE-0 NIT N1 (review ANTI-D3-1): progress-guard '
                         'fade gate->base REPROVADO no gate — default OFF; ON '
                         'reativa exatamente o mecanismo da ANTI-D3-1 '
                         '(N=5 ticks de 0,1s; F=5; Δcum<0,5m)')
    ap.add_argument('--grid', type=str, default='f1', choices=['f1', 'staggered'],
                    help='SANIDADE-0 M1 (prereg 1007636): staggered = 2 colunas '
                         '±2,5 m (Δlat 5,0 m > corredor 3,5); default f1 = '
                         'bit-idêntico. Opt-in research, NÃO-GAITADO: o gate '
                         'SANIDADE-0 correu o bundle completo; FAIL (c60 '
                         '942/1352 > 812); configuração solo não medida até '
                         'SANIDADE-1b')
    ap.add_argument('--rejoin', type=str, default='bearing',
                    choices=['bearing', 'perceptive'],
                    help='SANIDADE-0 M2: perceptive = ângulo raso <=15° + grama '
                         '6 m/s + gap X=20 m (auto via --rejoin-gap 0); '
                         'default bearing = bit-idêntico. Opt-in research, '
                         'não-gaitado: o gate SANIDADE-0 correu o bundle '
                         'completo; configuração solo não medida até SANIDADE-1b')
    ap.add_argument('--proj-gate', action='store_true', default=False,
                    help='PROJ-GATE-1 V-A: congela o alvo de rejoin do runner '
                         'na última projeção on-track; default OFF')
    _add_writer_v35_argument(ap)
    _add_corpus_dump_argument(ap)
    ap.add_argument('--anti-glue', action='store_true',
                    help='SANIDADE-0 M3: fricção chassis 0,01 + preventivo '
                         'composite/professor + breaker 3 s (todos); default '
                         'OFF = bit-idêntico. Opt-in research: v1 MORTO; '
                         'v2 ARQUIVADA no SANIDADE-1b (tetos mataram a '
                         'separação: comp colado 51,6/50,6s vs teto 16,5) — '
                         'flag p/ research apenas')
    ap.add_argument('--prof-repair', action='store_true',
                    help='PROF-REPAIR-1 (prereg fc0a939): pacing '
                         'pós-reentrada do professor — janela 5,0 s de '
                         'settling após off->on com rampa de alvo de '
                         'velocidade 8 m/s -> v_plan (ataca a cascata '
                         'de 94,6%%: o v_plan frozen exige ritmo pleno '
                         'já no tick seguinte ao reentry). Default OFF '
                         '= professor histórico bit-idêntico')
    ap.add_argument('--prof-curva', action='store_true', default=False,
                    help='PROF-CURVA-1 (Task 3, após Freeze d2a2215): teto local de velocidade '
                         'no professor solo derivado de physics_frontier_current.json '
                         'para eliminar saídas crônicas por pacing em quinas. '
                         'Default OFF = bit-idêntico ao professor histórico.')
    ap.add_argument('--physics-frontier-file', type=str,
                    default='experiments/prof-curva-1/physics_frontier_current.json',
                    help='PROF-CURVA-1: caminho para a fronteira física JSON.')
    ap.add_argument('--prof-control', action='store_true', default=False,
                    help='PROF-CONTROL-1 (Task 2, Freeze 53ea581): feedforward '
                         'cinemático arctan(L*kappa_local) + lookahead modulado '
                         'por curvatura (g=1/(1+c_ld*|kappa|)), com c_ld derivado '
                         'do LAGO_ANATOMY.json pela regra §3 do prereg. '
                         'Default OFF = bit-idêntico ao professor histórico.')
    ap.add_argument('--prof-grip', action='store_true', default=False,
                    help='PROF-GRIP-1 (Task 2, Freeze 715c677): teto de pacing '
                         'grip-sensível nas janelas canônicas de C01/C06/C07/C08 '
                         '(v_alvo = v_plan·min(1,sqrt(grip_atual/0,85))·'
                         'sqrt(1/1,10), grip_atual = tyre.grip_multiplier por '
                         'tick). Default OFF = bit-idêntico ao professor '
                         'histórico.')
    ap.add_argument('--prof-pace', action='store_true', default=False,
                    help='PROF-PACE-1 (Task 2, Freeze 947c091): pacing '
                         'preventivo grip_mode=FIXED (grip_ref='
                         '0,7895474400345001 constante) nas janelas canônicas '
                         'de C01/C06/C07/C08 de Interlagos (v_alvo = '
                         'v_target_cap: 0,93 + cap η EMBUTIDOS no perfil via '
                         'passadas de prof_curva). No-op explícito fora de '
                         'Interlagos. Default OFF = bit-idêntico.')
    ap.add_argument('--prof-pace-eta', type=str, default='eta1',
                    choices=['eta1', 'eta2'],
                    help='ESTADA de η pré-declarada (sem valores livres): '
                         'eta1=0,48848 | eta2=0,40000. Selecionado somente '
                         'por estágio (PREREG_PROF_PACE_1 §2).')
    ap.add_argument('--variedade', type=int, default=0,
                    help='VARIEDADE-1 (prereg b237aeb): N>=1 deriva PRNG '
                         'proprio sha256(seed//variedade//N) e perturba SO '
                         'condições iniciais (jitter grid ±0,5m/±0,3m; '
                         'mu_nominal ×U[0,98,1,02] no spawn). Default 0 = '
                         'OFF = bit-idêntico ao canônico. MESMA (seed,N) -> '
                         'bit-idêntica; N diferente -> corrida diferente. '
                         'N<0 = erro')
    ap.add_argument('--residual-override', type=str, default=None,
                    help='R12-CANÁRIAS/PILOTO (preregistrado): caminho do npz '
                         'residual do CANDIDATO — única diferença vs braço A')
    ap.add_argument('--n-cars', type=int, default=10,
                    help='R12-CANÁRIAS (preregistrado): nº de carros do campo '
                         '(1 = canária solo funcional do stack no runner frozen)')
    ap.add_argument('--steer-gov', type=str, default='off', choices=['off', 'cap'],
                    help='v15 R8: steer-governor opt-in — cap 2,0×atan(L·κ@10m) '
                         'no esterço da política (rejoin/recovery isentos; '
                         'professor não afetado)')
    ap.add_argument('--variance', type=str, default='off',
                    help='v15 R7a: variância de corrida SEMEADA opt-in (csv: '
                         '"grid,compound"). grid = ordem de largada por stream '
                         'dedicada; compound = atribuição de compostos por stream '
                         '(distribuição preservada). Default off = bit-reproduzível '
                         'como antes. Domínios de CENÁRIO, nunca física.')
    ap.add_argument('--weather', type=str, default='seeded', choices=['seeded', 'fixed'],
                    help='v15 R6: seeded = RNG do clima derivado do --seed (transições '
                         'determinísticas por seed); fixed = kind travado no nominal '
                         '(prob de transição 0 — braço de controle)')
    ap.add_argument('--gov', type=str, default='vplan', choices=['on', 'off', 'vplan'],
                    help='v15 FASE 1 (ADOTADO): vplan é o DEFAULT do produto (103,4s vs 137,1s '
                         'off (isola a contribuição) | vplan (teto = v_plan do '
                         'professor, mesma fórmula do velocity_profile)')
    ap.add_argument('--ticks', type=int, default=600)
    ap.add_argument('--laps', type=int, default=2)
    ap.add_argument('--track', type=str, default='interlagos',
                    help='pista para a corrida (nome FastF1)')
    ap.add_argument('--out', default='race_diag.csv')
    ap.add_argument('--seed', type=int, default=0,
                    help='semente (sim determinística; documenta reprodutibilidade)')
    # --- A2 (FASE 5 v14): campo MISTO N×v14(traffic) + M×v10(edge) ---------
    ap.add_argument('--mixed', type=str, default=None,
                    help='"traffic:2,edge:8" — N carros v14 + M carros v10, '
                         'controllers independentes, grid embaralhado entre grupos')
    ap.add_argument('--traffic-actor', type=str, default=None,
                    help='checkpoint do grupo traffic no --mixed '
                         '(default: profile traffic = v14 best_s2_n8)')
    # --- B3.3 (FASE 5): controle all-v10 embaralhado + carro travado ------
    ap.add_argument('--shuffle-grid', action='store_true',
                    help='embaralha o grid (mesma permutação do --mixed, por '
                         '--seed) sem grupos — controle p/ isolar efeito do grid')
    ap.add_argument('--hold-at', type=float, default=None,
                    help='B3.3d: congela o PRIMEIRO carro do grupo edge (ou o '
                         'último do grid, sem --mixed) na posição s=X da linha '
                         'central a cada tick (set_position + reset_vel) — '
                         'testa contornar carro PARADO')
    ramp_group.set_defaults(rejoin_ramp=None)
    args = ap.parse_args()
    if args.rejoin_handoff is None:
        args.rejoin_handoff = 'align' if args.profile == 'composite' else 'off'
    if args.rejoin_ramp is None:
        args.rejoin_ramp = args.profile == 'composite'
    if args.writer_v35:
        if args.controller != 'neural' or args.profile != 'composite' or args.mixed:
            ap.error('--writer-v35 requer controller neural único com --profile composite')
        if args.proj_gate:
            ap.error('--writer-v35 requer --proj-gate OFF')
        if args.rejoin_gap != 0.0:
            ap.error('--writer-v35 requer --rejoin-gap 0 no replay canônico')
        if os.environ.get('RACE_DIAG_NO_XY') == '1':
            ap.error('--writer-v35 requer XY habilitado')
    if args.corpus_dump:
        if args.controller != 'neural' or args.profile != 'composite' or args.mixed:
            ap.error('--corpus-dump requer controller neural único com --profile composite')
        if args.proj_gate or args.pass_decision or args.leader_yield:
            ap.error('--corpus-dump requer flags de decisão/rejoin opt-in OFF')
        if os.environ.get('RACE_DIAG_NO_XY') == '1':
            ap.error('--corpus-dump requer XY habilitado')
    if args.proj_gate and args.controller != 'neural':
        ap.error('--proj-gate V-A requer --controller neural')
    # REALISMO-1 C1-B: D_L junto ao launch-steer-mute é a única janela definida.
    if args.launch_steer_mute and (args.pguard or args.launch_cap
                                   or args.launch_stagger):
        ap.error("--launch-steer-mute é mutuamente exclusivo com "
                 "--pguard, --launch-cap e --launch-stagger")
    # prereg cd3ca5e: combinação não definida — exclusão mútua explícita
    if args.launch_cap and args.launch_stagger:
        ap.error("--launch-cap e --launch-stagger são mutuamente exclusivos "
                 "(combinação não definida no prereg L-1b)")
    # validação antecipada do --mixed (ap.error antes de qualquer setup caro)
    if args.mixed:
        try:
            parse_mixed(args.mixed, n_total=10)
        except ValueError as e:
            ap.error(str(e))
    if args.launch_steer_mute:
        if args.mixed:
            if 'composite' not in parse_mixed(args.mixed, n_total=10):
                ap.error('--launch-steer-mute requer grupo composite no --mixed')
        elif args.profile != 'composite':
            ap.error('--launch-steer-mute requer --profile composite')
    if args.rejoin_handoff == 'align':
        if args.mixed:
            if 'composite' not in parse_mixed(args.mixed, n_total=10):
                ap.error('--rejoin-handoff align requer grupo composite no --mixed')
        elif args.profile != 'composite':
            ap.error('--rejoin-handoff align requer --profile composite')
    if args.rejoin_ramp:
        if args.gov != 'vplan':
            ap.error('--rejoin-ramp requer --gov vplan')
        if args.controller != 'neural' or args.mixed:
            ap.error('--rejoin-ramp requer caminho neural único; mixed/professor não suportado')
    if args.lat_offset_slots and args.controller == 'professor':
        ap.error('--lat-offset-slots requer controller neural')
    if args.prof_curva:
        professor_path = args.controller == 'professor' and not args.mixed
        if args.mixed:
            professor_path = 'professor' in parse_mixed(
                args.mixed, n_total=10)
        if not professor_path:
            ap.error('--prof-curva requer --controller professor ou grupo '
                     'professor explícito em --mixed; neural nunca engaja')
    if args.prof_control:
        professor_path = args.controller == 'professor' and not args.mixed
        if args.mixed:
            professor_path = 'professor' in parse_mixed(
                args.mixed, n_total=10)
        if not professor_path:
            ap.error('--prof-control requer --controller professor ou grupo '
                     'professor explícito em --mixed; neural nunca engaja')
    if args.prof_grip:
        from backend.model_train import prof_grip as _pg
        has_mixed = bool(args.mixed)
        professor_in_mixed = ('professor' in parse_mixed(
            args.mixed, n_total=10)) if has_mixed else False
        if not _pg.guard_professor_path(args.controller, has_mixed,
                                        professor_in_mixed):
            ap.error('--prof-grip requer --controller professor ou grupo '
                     'professor explícito em --mixed; neural nunca engaja')
    if args.prof_pace:
        from backend.model_train import prof_pace as _pp
        has_mixed = bool(args.mixed)
        professor_in_mixed = ('professor' in parse_mixed(
            args.mixed, n_total=10)) if has_mixed else False
        if args.prof_grip or args.prof_control:
            ap.error('--prof-pace é exclusivo: não combine com --prof-grip '
                     'ou --prof-control (mecanismos de pacing isolados)')
        if args.controller != 'professor' and not (
                args.mixed and professor_in_mixed):
            ap.error('--prof-pace requer --controller professor ou grupo '
                     'professor explícito em --mixed; neural nunca engaja')
    if args.pass_decision:
        professor_path = args.controller == 'professor' and not args.mixed
        if args.mixed:
            try:
                professor_path = 'professor' in parse_mixed(
                    args.mixed, n_total=10)
            except ValueError as e:
                ap.error(str(e))
        if not professor_path:
            ap.error('--pass-decision requer --controller professor ou grupo '
                     'professor explícito em --mixed; neural/v10 nunca engaja')
    if (args.controller == 'neural' and not args.actor
            and not args.mixed and not args.profile):
        ap.error('--actor é obrigatório com --controller neural '
                 '(ou use --profile composite/race/quali/traffic)')
    np.random.seed(args.seed)

    # camada da corrida: mesmo R importado no nível do módulo (professor
    # herda dele; neural usa a mesma instância de código da corrida visual)
    # v15 FASE R: pista SEMPRE da fonte frozen (fail-fast). FastF1 é
    # opcional; fallback para preset procedural é PROIBIDO no runner.
    from backend.model_train.f1_env import load_track_frozen
    track = load_track_frozen(args.track, strict=True)
    # v15 R6: RNG do clima SEMEADO por seed (ou travado c/ --weather fixed).
    from backend.domain.weather import weather_rng_from_seed, WeatherTransitionConfig
    # v15 R7a: variância semeada (opt-in) — valida a flag ANTES de qualquer setup
    from backend.domain.racevar import (parse_variance, variance_rng_from_seed,
                                         assign_compounds, shuffled_order)
    variance_domains = parse_variance(args.variance)
    from backend.domain import WeatherModel as _WM
    if args.weather == 'fixed':
        weather_rng = weather_rng_from_seed(0)   # stream morta: prob 0 nunca transita
        weather_cfg = WeatherTransitionConfig.default(transition_prob_per_lap=0.0)
    else:
        weather_rng = weather_rng_from_seed(args.seed)
        weather_cfg = None
    drivers = R.build_grid_drivers()
    # R12-CANÁRIAS (preregistrado): campo reduzido p/ canária solo funcional
    if args.n_cars < len(drivers):
        drivers = drivers[:args.n_cars]
        print(f"[diag] CANÁRIA: campo de {args.n_cars} carro(s)")
    # v15 R7a: sorteio de CENÁRIO por stream dedicada (nunca física; nunca
    # np.random global). Composto primeiro (pool da ordem de build), grid depois.
    var_grid_order = None
    var_compound_map = None
    if variance_domains:
        if 'compound' in variance_domains:
            pool = [d.starting_tyre_compound for d in drivers]
            var_compound_map = assign_compounds(
                variance_rng_from_seed(args.seed, 'compound'),
                [d.driver_id for d in drivers], pool)
            for d in drivers:
                d.starting_tyre_compound = var_compound_map[d.driver_id]
        if 'grid' in variance_domains:
            var_grid_order = shuffled_order(
                variance_rng_from_seed(args.seed, 'grid'), len(drivers))
            drivers = [drivers[k] for k in var_grid_order]
        print(f"[diag] VARIÂNCIA ON ({','.join(sorted(variance_domains))}): "
              f"grid={[d.driver_id for d in drivers]} | "
              f"compostos={ {k: v.value for k, v in (var_compound_map or {}).items()} }")
    print(f"[diag] pista FROZEN: {track.name} | {len(track.waypoints)} wp | "
          f"SF wp {track.start_finish_waypoint} | "
          f"sha256 {getattr(track, 'frozen_sha256', '?')} | "
          f"clima={args.weather} (rng semeado por seed) | "
          f"variance={args.variance} | rejoin_gap={args.rejoin_gap} | rejoin_handoff={args.rejoin_handoff} | launch_cap={args.launch_cap} | launch_stagger={args.launch_stagger} | launch_steer_mute={args.launch_steer_mute} | pguard={args.pguard}"
          f" | grid={args.grid} | rejoin={args.rejoin} | anti_glue={args.anti_glue} | variedade={args.variedade} | prof_repair={args.prof_repair} | pass_decision={args.pass_decision} | prof_curva={getattr(args, 'prof_curva', False)} | prof_control={getattr(args, 'prof_control', False)} | prof_grip={getattr(args, 'prof_grip', False)} | prof_pace={getattr(args, 'prof_pace', False)}|{getattr(args, 'prof_pace_eta', 'eta1')}"
          + (f" | grid_order={[d.driver_id for d in drivers]}" if var_grid_order else "")
          + (f" | compounds={ {k: v.value for k, v in var_compound_map.items()} }"
             if var_compound_map else ""))
    mixed_groups = None
    mixed = None
    if args.mixed:
        mixed = parse_mixed(args.mixed, n_total=10)
        mixed_groups = assign_groups([d.driver_id for d in drivers], mixed)
        # grid EMBARALHADO entre grupos (posição física independente do grupo;
        # embaralhamento determinístico por --seed)
        perm = np.random.default_rng(args.seed).permutation(len(drivers))
        drivers = [drivers[k] for k in perm]
        print(f"[diag] MIXED {args.mixed} | grupos: {mixed_groups} | "
              f"grid embaralhado (seed {args.seed})")
    elif args.shuffle_grid:
        # B3.3c (controle): MESMA permutação do --mixed, sem grupos — separa o
        # efeito do GRID EMBARALHADO do efeito dos v14 no campo
        perm = np.random.default_rng(args.seed).permutation(len(drivers))
        drivers = [drivers[k] for k in perm]
        print(f"[diag] CONTROLE: grid embaralhado (seed {args.seed}), sem grupos")
    from backend.engine import SimulationConfig, SimulationEngine
    from backend.domain import WeatherModel, WeatherKind, BASE_CONDITIONS

    sim_config = SimulationConfig(
        race_id='diag', num_laps=args.laps, logic_step_hz=10.0,
        physics_sub_steps=24, gui=False, camera_mode='overview',
        draw_track=False, realtime=False, input_stale_after_s=300.0,
    )
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers,
                              weather_model=_WM(initial=BASE_CONDITIONS[WeatherKind.DRY],
                                                config=weather_cfg, rng=weather_rng))
    engine.setup()
    # v15 FASE R5a: instrumento de contato AUTORITATIVO (opt-in) — colhe
    # getContactPoints por SUB-STEP no solver. A física não lê nada daqui;
    # a guarda bit-idêntica (re-run s0 vs R4) valida a não-contaminação.
    import os as _os
    if _os.environ.get('RACE_DIAG_NO_CONTACT_LOG') == '1':
        engine.physics.contact_collector = None   # guarda: run "puro" (sem log)
    else:
        engine.physics.contact_collector = []
    if args.pass_decision and engine.physics.contact_collector is None:
        ap.error('--pass-decision requer a coleta solver para abortar contato do par')
    if args.variedade < 0:
        ap.error('--variedade deve ser >= 0 (0 = OFF bit-idêntico)')
    # VARIEDADE-1 (prereg b237aeb §1): ICs por carro do PRNG próprio
    # (seed, N); N=0 -> None -> NENHUM código roda (inércia bit-idêntica).
    var_params = R.variedade_params(args.seed, args.variedade, len(drivers))
    var_jitter = [(a, b) for a, b, _ in var_params] if var_params else None
    R.place_grid(engine, track, drivers, layout=args.grid, jitter=var_jitter)
    if var_params:
        for drv, (_, _, mu_f) in zip(drivers, var_params):
            engine.physics.scale_mu_nominal(drv.driver_id, mu_f)
        print(f"[diag] VARIEDADE-1: N={args.variedade} (PRNG proprio "
              f"sha256(seed//variedade//N)) | jitter ±0,5m/±0,3m | "
              f"mu_nominal ×U[0,98,1,02] — mesma (seed,N) = bit-idêntica; "
              f"N diferente = corrida diferente; 0 = canônico")
    # SANIDADE-0 M3(i) (prereg 1007636 §1): fricção chassis-chassis 0,05->0,01
    # sob a flag (rodas intactas — solo vem dos pneus por construção).
    if args.anti_glue:
        engine.physics.set_chassis_lateral_friction(0.01)
        print("[diag] anti-glue ON: fricção chassis-chassis 0,01")
    engine.race_started = True

    # exportador + controller EXATOS da corrida
    ctrl_traffic = ctrl_edge = ctrl_comp = ctrl_prof = None
    ctrl = None
    # SANIDADE-0 M2 (prereg 1007636 §1): perceptive auto-liga o gap-check
    # REPARADO (ead15a7) com X=20 m (cotovelo do dossiê R13) se o usuário
    # não pinou outro X.
    gap_x = 20.0 if (args.rejoin == 'perceptive' and args.rejoin_gap == 0.0) \
        else float(args.rejoin_gap)
    if args.controller == 'professor':
        sf_range = None
        if args.sf_range:
            lo, hi = args.sf_range.split(':')
            sf_range = (float(lo), float(hi))
        ctrl = ProfessorRaceController(track, sf=0.80, sf_range=sf_range,
                                      machine_only=args.pass_machine_only,
                                      rejoin_mode=args.rejoin,
                                      anti_glue=args.anti_glue,
                                      prof_repair=getattr(args, 'prof_repair', False),
                                      pass_decision=args.pass_decision,
                                      leader_yield=args.leader_yield,
                                      prof_curva=getattr(args, 'prof_curva', False),
                                      prof_control=getattr(args, 'prof_control', False),
                                      prof_grip=getattr(args, 'prof_grip', False),
                                      prof_pace=getattr(args, 'prof_pace', False),
                                      prof_pace_eta=getattr(args, 'prof_pace_eta', 'eta1'),
                                      physics_frontier_file=getattr(args, 'physics_frontier_file', None))
        print(f"[diag] controller: PROFESSOR x{len(drivers)} (gate all-professor) "
              f"| sf_range={sf_range or 'homog 0.80'} | machine_only={args.pass_machine_only} "
              f"| track={track.name} | seed={args.seed}")
    elif args.mixed:
        # Só instancia modelos que pertencem ao campo. Cada controlador
        # neural ainda computa ações para todos os carros, pois suas
        # observações incluem o campo completo; o runner seleciona o grupo.
        mixed_models = []
        if 'traffic' in mixed:
            tk = (Path(args.traffic_actor) if args.traffic_actor
                  else R.PROFILES['traffic']['keras'])
            tn = R.ensure_npz_weights_exist(
                tk, tk.with_name(tk.stem + '_weights.npz'))
            ctrl_traffic = R.NeuralRaceController(
                weights_path=tn, obs_mode='traffic',
                mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                lat_offset_slots=args.lat_offset_slots,
                lat_offset_profile='blind',
                rejoin_mode=args.rejoin, anti_glue=args.anti_glue,
                rejoin_gap=gap_x, c8_rejoin=args.c8_rejoin,
                proj_gate=args.proj_gate)
            ctrl = ctrl_traffic
            mixed_models.append(f"traffic={tk.name}")
        if 'edge' in mixed:
            ek = Path(args.actor) if args.actor else R.PROFILES['race']['keras']
            en = R.ensure_npz_weights_exist(
                ek, ek.with_name(ek.stem + '_weights.npz'))
            ctrl_edge = R.NeuralRaceController(
                weights_path=en, obs_mode='edge',
                mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                lat_offset_slots=args.lat_offset_slots,
                lat_offset_profile='blind',
                rejoin_mode=args.rejoin, anti_glue=args.anti_glue,
                rejoin_gap=gap_x, c8_rejoin=args.c8_rejoin,
                proj_gate=args.proj_gate)
            if ctrl is None:
                ctrl = ctrl_edge
            mixed_models.append(f"edge={ek.name}")
        # FASE 4 v15 (wiring): grupo COMPOSITE — o composite COMPLETO por
        # carro (limitação 2 da sessão FASE 4 resolvida): solo v10 em obs
        # 'traffic' + residual r2 via NumpyCompositeActor — o MESMO caminho
        # do --profile composite, aplicado a um subconjunto do grid.
        if 'composite' in mixed:
            ck = R.PROFILES['race']['keras']
            cn = R.ensure_npz_weights_exist(ck, ck.with_name(ck.stem + '_weights.npz'))
            ctrl_comp = R.NeuralRaceController(weights_path=cn, obs_mode='traffic',
                                               mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                                               rejoin_handoff=args.rejoin_handoff,
                                               rejoin_ramp=args.rejoin_ramp,
                                               c8_rejoin=args.c8_rejoin,
                                               lat_offset_slots=args.lat_offset_slots,
                                               lat_offset_profile='composite',
                                               launch_steer_mute=args.launch_steer_mute,
                                               pguard=args.pguard,
                                               rejoin_mode=args.rejoin,
                                               anti_glue=args.anti_glue,
                                               rejoin_gap=gap_x,
                                               proj_gate=args.proj_gate)
            from backend.model_train.residual_gated import NumpyCompositeActor
            comp_npz = Path(args.residual_override) if args.residual_override \
                else R.PROFILES['race']['residual_npz']
            ctrl_comp._composite_np = NumpyCompositeActor(str(cn), str(comp_npz))
            if ctrl is None:
                ctrl = ctrl_comp
            mixed_models.append(f"composite={ck.name}")
            print(f"[diag] MIXED composite: solo={ck.name} + residual={comp_npz.name} "
                  f"(input {ctrl_comp.actor.input_dim}) x{mixed.get('composite', 0)}")
        if 'professor' in mixed:
            ctrl_prof = ProfessorRaceController(
                track, sf=0.80, sf_range=None,
                machine_only=args.pass_machine_only,
                rejoin_mode=args.rejoin, anti_glue=args.anti_glue,
                prof_repair=getattr(args, 'prof_repair', False),
                pass_decision=args.pass_decision,
                leader_yield=args.leader_yield,
                prof_curva=getattr(args, 'prof_curva', False),
                prof_control=getattr(args, 'prof_control', False),
                prof_grip=getattr(args, 'prof_grip', False),
                prof_pace=getattr(args, 'prof_pace', False),
                prof_pace_eta=getattr(args, 'prof_pace_eta', 'eta1'),
                physics_frontier_file=getattr(args, 'physics_frontier_file', None))
            print(f"[diag] MIXED professor x{mixed.get('professor', 0)} "
                  f"| pass_decision={args.pass_decision}")
            if ctrl is None:
                ctrl = ctrl_prof
        print(f"[diag] MIXED: {', '.join(mixed_models) or 'professor only'}")
        if args.lat_offset_slots:
            for neural_ctrl in (ctrl_traffic, ctrl_edge, ctrl_comp):
                if neural_ctrl is not None:
                    neural_ctrl._launch_grid_slots = {
                        d.driver_id: i + 1 for i, d in enumerate(drivers)}
    else:
        if args.profile == 'composite':
            # v15 FASE 4: solo v10 (edge via NPZ) + residual NPZ; obs='traffic'
            from backend.model_train.residual_gated import NumpyCompositeActor
            actor_keras = R.PROFILES['race']['keras']
            npz_path = R.ensure_npz_weights_exist(actor_keras,
                    actor_keras.with_name(actor_keras.stem + '_weights.npz'))
            ctrl = R.NeuralRaceController(weights_path=npz_path, obs_mode='traffic',
                                          mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                                          rejoin_handoff=args.rejoin_handoff,
                                          rejoin_ramp=args.rejoin_ramp,
                                          c8_rejoin=args.c8_rejoin,
                                          lat_offset_slots=args.lat_offset_slots,
                                          lat_offset_profile='composite',
                                          launch_steer_mute=args.launch_steer_mute,
                                          steer_gov=args.steer_gov,
                                          rejoin_gap=gap_x,
                                          launch_cap=args.launch_cap,
                                          launch_stagger=args.launch_stagger,
                                          pguard=args.pguard,
                                          rejoin_mode=args.rejoin,
                                          anti_glue=args.anti_glue,
                                          proj_gate=args.proj_gate)
            comp_npz = R.PROFILES['composite']['residual_npz']
            # v3.3: sha do residual LOGADO SEMPRE (não só com override)
            import hashlib as _hl2
            print(f"[diag] residual baseline sha256="
                  f"{_hl2.sha256(comp_npz.read_bytes()).hexdigest()[:16]}")
            if args.residual_override:
                comp_npz = Path(args.residual_override)
                # A.2(a): sha256 do artefato EFETIVAMENTE carregado (mata fallback
                # silencioso — lição FASE 1: mudança visível no instrumento)
                import hashlib as _hl
                _sha = _hl.sha256(comp_npz.read_bytes()).hexdigest()[:16]
                print(f"[diag] RESIDUAL OVERRIDE (candidato): {comp_npz.name} "
                      f"sha256={_sha}")
                print(f"[diag] RESIDUAL BASELINE (r2): "
                      f"{R.PROFILES['composite']['residual_npz'].name} sha256="
                      f"{_hl.sha256(R.PROFILES['composite']['residual_npz'].read_bytes()).hexdigest()[:16]}")
            ctrl._composite_np = NumpyCompositeActor(str(npz_path), str(comp_npz))
        else:
            actor_keras = Path(args.actor)
            npz_path = R.ensure_npz_weights_exist(actor_keras,
                    actor_keras.with_name(actor_keras.stem + '_weights.npz'))
            ctrl = R.NeuralRaceController(weights_path=npz_path, obs_mode=args.obs_mode,
                                          mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                                          steer_gov=args.steer_gov,
                                          rejoin_ramp=args.rejoin_ramp,
                                          c8_rejoin=args.c8_rejoin,
                                          lat_offset_slots=args.lat_offset_slots,
                                          lat_offset_profile='blind',
                                          rejoin_gap=gap_x,
                                          launch_cap=args.launch_cap,
                                          launch_stagger=args.launch_stagger,
                                          pguard=args.pguard,
                                          rejoin_mode=args.rejoin,
                                          anti_glue=args.anti_glue,
                                          proj_gate=args.proj_gate)
        if args.gov == 'off':
            ctrl._gov_enabled = False
        elif args.gov == 'vplan':
            from backend.model_train.velocity_profile import VelocityProfile
            ctrl._v_plan_cap = VelocityProfile(
                np.array(track.waypoints, dtype=np.float64), grip_mult=0.788,
                sf=0.80, ds_target=4.0, smooth_window_m=20.0)
        comp_note = (f" | composite={Path(comp_npz).name}" if args.profile == 'composite' else "")
        print(f"[diag] ator: {actor_keras.name} | input_dim={ctrl.actor.input_dim} "
              f"| gov={args.gov} | profile={args.profile or 'manual'}{comp_note}")
        # CICLO LARGADA L-1b (prereg cd3ca5e): slots de largada do RUN — a
        # lista `drivers` JÁ é a ordem de largada efetiva (reordenada pelo
        # --variance grid na linha ~446; place_grid a consome). Fonte única.
        ctrl._launch_grid_slots = {d.driver_id: i + 1 for i, d in enumerate(drivers)}

    # REJOIN-TEL-1: telemetria opt-in e pass-through. Captura o retorno literal
    # do resolvedor usado pelo controller; o snapshot de âncora/janela faz
    # somente leituras de estado antes da ação e não alimenta o controle.
    rejoin_tel_targets = None
    rejoin_tel_tracker = None
    if args.writer_v35:
        rejoin_tel_targets = _install_rejoin_tel_target_capture(ctrl)
        rejoin_tel_tracker = RejoinWindowTelemetry()

    corpus_dump = None
    corpus_compound_mapping = None
    if args.corpus_dump:
        from scripts.training.composite_corpus_dump import (
            CompositeCorpusDump, load_compound_mapping,
        )
        corpus_compound_mapping = load_compound_mapping(R.DEFAULT_MAPPINGS_PATH)
        geometry_id = _track_geometry_id(track)
        geometry_sha256 = _CORPUS_GEOMETRY_SHA256[geometry_id]
        corpus_dump = CompositeCorpusDump(
            args.corpus_dump,
            run=Path(args.corpus_dump).stem,
            geometry_id=geometry_id,
            geometry_sha256=geometry_sha256,
        )
        print(f"[corpus-dump] schema=composite-corpus-dump-v2 "
              f"path={args.corpus_dump} geometry={track.name} "
              f"sha256={track.frozen_sha256}")

    wps = np.array(track.waypoints)
    # B3.3d: --hold-at congela o PRIMEIRO carro do grupo edge (sem --mixed,
    # o último do grid) na linha central em s — testa contornar carro PARADO
    hold_drv = None
    if args.hold_at is not None:
        if mixed_groups is not None:
            hold_drv = next(d.driver_id for d in drivers
                             if mixed_groups[d.driver_id] == 'edge')
        else:
            hold_drv = drivers[-1].driver_id
        print(f"[diag] HOLD-AT: carro {hold_drv} congelado em s={args.hold_at:.0f}m")
    dt = 0.1
    import pybullet as pb
    cid = engine.physics._client_id
    diag_no_xy = os.environ.get('RACE_DIAG_NO_XY') == '1'
    rows = []
    stoplog = []      # episodios de parada >= 3 s: como terminaram
    slow_since = {}   # drv -> tick em que ficou lento
    # gate v14: ultrapassagens líquidas por par com histerese (±10 m de
    # progresso acumulado) — contato momentâneo não conta como troca
    pair_settled = {}
    overtakes = 0
    overtakes_post_launch = 0
    OVERTAKE_HYST_M = 10.0
    _prev_w_kind = engine.weather_model.current.kind
    for t in range(args.ticks):
        rejoin_tel_snapshots = {}
        if args.writer_v35:
            rejoin_tel_targets.clear()
            for drv in drivers:
                phys_tel = engine.physics.get_state(engine.handles[drv.driver_id])
                _, s_tel, _, lat_tel = _proj(ctrl, phys_tel['x'], phys_tel['y'])
                off_tel = lat_tel > ctrl._half_width * ctrl.OFFTRACK_FACTOR
                rejoin_tel_snapshots[drv.driver_id] = rejoin_tel_tracker.observe(
                    drv.driver_id, t, off_tel, phys_tel['x'], phys_tel['y'], s_tel)
        if corpus_dump is not None:
            _capture_composite_dump_rows(
                corpus_dump, ctrl, engine, drivers, t, corpus_compound_mapping)
        if mixed_groups is not None:
            # Cada controller presente vê o campo inteiro; só a ação do
            # grupo atribuído é usada. Modelos de grupos ausentes não são
            # carregados nem executados.
            acts_by_group = {}
            if ctrl_traffic is not None:
                acts_by_group['traffic'] = ctrl_traffic.predict_batch(
                    engine, drivers, wps, track_id=0)
            if ctrl_edge is not None:
                acts_by_group['edge'] = ctrl_edge.predict_batch(
                    engine, drivers, wps, track_id=0)
            if ctrl_comp is not None:
                acts_by_group['composite'] = ctrl_comp.predict_batch(
                    engine, drivers, wps, track_id=0)
            if ctrl_prof is not None:
                professor_ids = {drv.driver_id for drv in drivers
                                 if mixed_groups[drv.driver_id] == 'professor'}
                if args.pass_decision:
                    acts_by_group['professor'] = ctrl_prof.predict_batch(
                        engine, drivers, wps, track_id=0,
                        sim_time_s=float(engine.sim_ts), sample_5hz=(t % 2 == 0),
                        active_driver_ids=professor_ids,
                        pass_decision_history=rows)
                else:
                    acts_by_group['professor'] = ctrl_prof.predict_batch(
                        engine, drivers, wps, track_id=0,
                        sim_time_s=float(engine.sim_ts), sample_5hz=(t % 2 == 0),
                        active_driver_ids=professor_ids)
            actions = [acts_by_group[mixed_groups[drv.driver_id]][i]
                       for i, drv in enumerate(drivers)]
        else:
            if args.controller == 'professor':
                if args.pass_decision:
                    actions = ctrl.predict_batch(
                        engine, drivers, wps, track_id=0,
                        sim_time_s=float(engine.sim_ts), sample_5hz=(t % 2 == 0),
                        pass_decision_history=rows)
                else:
                    actions = ctrl.predict_batch(
                        engine, drivers, wps, track_id=0,
                        sim_time_s=float(engine.sim_ts), sample_5hz=(t % 2 == 0))
            else:
                actions = ctrl.predict_batch(engine, drivers, wps, track_id=0)
        if corpus_dump is not None:
            for drv in drivers:
                corpus_dump.observe_action(
                    drv.driver_id,
                    ctrl._prev_actions.get(drv.driver_id, (0.0, 0.0)),
                )
        for i, drv in enumerate(drivers):
            th, brk, steer = actions[i]
            engine.set_driver_input(drv.driver_id, throttle=th, brake=brk, steering_yaw_rad=steer)
        engine._step_tick(dt, sim_config.physics_sub_steps)
        if hold_drv is not None:
            # congela o carro held: teleporte de volta à pose + velocidade zero
            # a cada tick (set_position/reset_vel — mesmo mecanismo do grid)
            hx, hy, hyaw = _pose_at_s(ctrl, args.hold_at)
            engine.physics.set_position(engine.handles[hold_drv], (hx, hy, 0.5),
                                        yaw_rad=hyaw, reset_vel=True)

        if t % 2 == 0:  # 5 Hz de amostragem basta
            cums = [float(engine.cum_dist_m.get(d.driver_id, 0.0)) for d in drivers]
            # ultrapassagem: par (i<j) cuja ordem de progresso INVERTEU com
            # margem >= histerese (troca LÍQUIDA, não jitter de contato)
            for i in range(len(drivers)):
                for j in range(i + 1, len(drivers)):
                    diff = cums[i] - cums[j]
                    if abs(diff) < OVERTAKE_HYST_M:
                        continue
                    sign = 1 if diff > 0 else -1
                    prev = pair_settled.get((i, j), sign)
                    if prev != sign:
                        overtakes += 1
                        if (t * dt) > 60.0:
                            overtakes_post_launch += 1
                    pair_settled[(i, j)] = sign
            for i, drv in enumerate(drivers):
                h = engine.handles[drv.driver_id]
                phys = engine.physics.get_state(h)
                _, s, _, lat_s = ctrl._project(phys['x'], phys['y']) if hasattr(ctrl, '_project') \
                    else _proj(ctrl, phys['x'], phys['y'])
                th, brk, steer = actions[i]
                # contatos fisicos — getContactPoints retorna TUPLAS de 14
                # campos: c[1]=bodyA, c[2]=bodyB, c[9]=força normal. CORREÇÕES:
                # p.getContactData NÃO EXISTE (except silenciava -> "0 contatos"
                # era instrumento quebrado) e getattr em tupla devolvia None.
                n_contacts, car_car, impulse = 0, 0, 0.0
                other_ids = {engine.handles[d.driver_id].chassis_id
                             for j, d in enumerate(drivers) if d.driver_id != drv.driver_id}
                try:
                    for c in pb.getContactPoints(h.chassis_id, physicsClientId=cid):
                        n_contacts += 1
                        impulse += abs(float(c[9]))
                        if c[1] in other_ids or c[2] in other_ids:
                            car_car += 1
                except Exception as e:
                    if t == 0:
                        print(f"[diag] AVISO: getContactPoints falhou: {e}")
                impulse_delta_v = impulse / 798.0
                ctrl_i = ctrl
                if mixed_groups is not None:
                    g = mixed_groups[drv.driver_id]
                    ctrl_i = ({'professor': ctrl_prof,
                               'composite': ctrl_comp,
                               'traffic': ctrl_traffic,
                               'edge': ctrl_edge}[g])
                row = dict(
                    tick=t, t_s=round(t * dt, 1), drv=drv.driver_id,
                    speed=phys['speed_mps'], s=s, lat=lat_s,
                    th=th, brk=brk, steer_rad=steer,
                    g_long=phys['g_long'],
                    stuck_t=ctrl_i._stuck_since.get(drv.driver_id, -1),
                    contacts=n_contacts, car_car=car_car, impulse=impulse, impulse_dv=impulse_delta_v,
                    offtrack=int(abs(lat_s) > ctrl_i._half_width),
                    authority=ctrl_i.last_authority.get(drv.driver_id, "?"),
                )
                if args.writer_v35:
                    tel = rejoin_tel_snapshots[drv.driver_id]
                    target = rejoin_tel_targets.get(drv.driver_id)
                    row.update(tel)
                    row.update(target or dict(target_x=0.0, target_y=0.0,
                                              target_kappa=0.0))
                    row['_rejoin_reentry_sample'] = int(
                        rejoin_tel_tracker.sample_reentry(drv.driver_id, tel))
                    if bool(tel['off_window_id']) != bool(target):
                        raise ValueError(
                            f"v3.5 alvo não corresponde ao estado off-track de "
                            f"{drv.driver_id} no tick {t}")
                if getattr(ctrl, '_composite_np', None) is not None:
                    row['g_gate'] = ctrl._res_gate.get(drv.driver_id, 0.0)
                    row['r_norm'] = ctrl._res_norm.get(drv.driver_id, 0.0)
                    row['composite_active'] = int(row['g_gate'] > 0)
                if getattr(ctrl, 'steer_gov', 'off') == 'cap':
                    row['steer_gov_active'] = int(
                        ctrl.last_steergov.get(drv.driver_id, 0))
                if getattr(ctrl, 'REJOIN_GAP_ENABLED', 0) > 0:
                    row['rejoin_gap_hold'] = int(ctrl._gap_hold.get(drv.driver_id, 0))
                    row['rejoin_gap_fb'] = int(ctrl._gap_fb.get(drv.driver_id, 0))
                if getattr(ctrl, 'LAUNCH_CAP_ENABLED', False):
                    row['launch_cap_active'] = int(ctrl._cap_active.get(drv.driver_id, 0))
                if getattr(ctrl, 'LAUNCH_STAGGER_ENABLED', False):
                    row['stagger_held'] = int(ctrl._stagger_held.get(drv.driver_id, 0))
                if getattr(ctrl, 'LAUNCH_STEER_MUTE_ENABLED', False):
                    row['launch_steer_mute'] = int(
                        ctrl._launch_steer_mute_active.get(drv.driver_id, 0))
                    row['launch_steer_mute_end_reason'] = (
                        ctrl._launch_steer_mute_end_reason.get(drv.driver_id, ""))
                if getattr(ctrl, 'REJOIN_HANDOFF_ENABLED', False):
                    row['rejoin_handoff_active'] = int(
                        ctrl._rejoin_handoff_active.get(drv.driver_id, 0))
                    row['rejoin_handoff_end_reason'] = (
                        ctrl._rejoin_handoff_end_reason.get(drv.driver_id, ""))
                if getattr(ctrl_i, 'REJOIN_RAMP_ENABLED', False):
                    row['rejoin_ramp_active'] = int(
                        ctrl_i._rejoin_ramp_active.get(drv.driver_id, 0))
                    row['rejoin_ramp_braked'] = int(
                        ctrl_i._rejoin_ramp_braked.get(drv.driver_id, 0))
                    row['rejoin_ramp_end_reason'] = (
                        ctrl_i._rejoin_ramp_end_reason.get(drv.driver_id, ""))
                # v15 R13-FECHAMENTO (CSV v3.3 ADITIVO): residual input 16d
                # por tick — rota 2 do backlog (weave/slide com tráfego VIVO)
                _rin = (None if os.environ.get('RACE_DIAG_NO_RES16') == '1'
                        else getattr(ctrl, '_res_in_last', {}).get(drv.driver_id))
                if _rin is not None:
                    for _j in range(16):
                        row[f'res_{_j}'] = float(_rin[_j])
                # v15 R6 (CSV v3.1): clima por tick + degradação de pneu por carro
                wstate = engine.weather_model.current
                row['w_kind'] = wstate.kind.value
                row['w_grip'] = round(float(wstate.grip_factor), 3)
                row['w_trans'] = 1 if wstate.kind != _prev_w_kind else 0
                _prev_w_kind = wstate.kind
                tyre = engine.states[drv.driver_id].tyre
                row['tyre_life'] = round(float(tyre.tyre_life), 2)
                row['tyre_grip'] = round(float(tyre.grip_multiplier(
                    wstate.kind, wstate.track_temp)), 3)
                if mixed_groups is not None:
                    row['grupo'] = mixed_groups[drv.driver_id]
                row['cum_dist'] = float(engine.cum_dist_m.get(drv.driver_id, 0.0))
                if args.controller == 'professor':
                    row['t_mode'] = ctrl.professors[i].last_follow_mode
                    row['p_state'] = ctrl.professors[i].last_pass_state
                # rastreio de episodios de parada (v < 0.5 por >= 3 s)
                if phys['speed_mps'] < 0.5:
                    slow_since.setdefault(drv.driver_id, t)
                else:
                    t0s = slow_since.pop(drv.driver_id, None)
                    if t0s is not None and (t - t0s) >= 30:
                        stoplog.append(dict(drv=drv.driver_id, t_start=t0s * dt,
                                            dur_s=(t - t0s) * dt,
                                            freed_by='contato' if impulse > 0 else ' proprio',
                                            s=s))
                # observacao v2 completa (para Fase D: comparar politicas no MESMO estado)
                obs23 = _obs23(ctrl, engine, drv, phys, s, lat_s, drivers)
                for j in range(23):
                    row[f'obs{j}'] = obs23[j]
                if not diag_no_xy:
                    # Instrumentação read-only: phys vem de get_state(), e a
                    # busca é o argmin global bruto da geometria frozen.
                    row['body_x'] = float(phys['x'])
                    row['body_y'] = float(phys['y'])
                    row['ns_raw'] = int(track.nearest_segment(
                        phys['x'], phys['y'])[1])
                rows.append(row)
        if engine.race_finished:
            break

    df = pd.DataFrame(rows)

    if args.writer_v35:
        df['reentry_heading_err_deg'] = 0.0
        unidentifiable = 0
        for _drv, indices in df.groupby('drv', sort=False).groups.items():
            ordered = sorted(indices, key=lambda idx: int(df.at[idx, 'tick']))
            previous = None
            for idx in ordered:
                if bool(df.at[idx, '_rejoin_reentry_sample']):
                    if previous is None:
                        raise ValueError(
                            f"v3.5 reentrada sem amostra XY anterior para {_drv}")
                    prev_xy = (df.at[previous, 'body_x'], df.at[previous, 'body_y'])
                    curr_xy = (df.at[idx, 'body_x'], df.at[idx, 'body_y'])
                    if math.hypot(float(curr_xy[0]) - float(prev_xy[0]),
                                  float(curr_xy[1]) - float(prev_xy[1])) <= 1e-9:
                        unidentifiable += 1
                    else:
                        df.at[idx, 'reentry_heading_err_deg'] = \
                            _rejoin_tel_heading_error(
                                prev_xy, curr_xy, df.at[idx, 's'], ctrl._heading_at)
                previous = idx
        df.drop(columns=['_rejoin_reentry_sample'], inplace=True)
        print(f"[rejoin-tel] reentradas observáveis com curso XY não identificável: "
              f"{unidentifiable}")

    # -------- v15 FASE R5a: eventos de impulso do solver -> CSV + colunas --
    # Evento = ponto de contato chassis×chassis com força normal >0 em um
    # sub-step. Colunas por carro-tick: imp_events (n de eventos), imp_dv
    # (soma |Δv| normal aplicada ao carro), imp_dv_max. A flag cc 5Hz é
    # PRESERVADA (car_car) — a cobertura flag⊆eventos é checada na análise.
    sub_steps = sim_config.physics_sub_steps
    contact_events = engine.physics.contact_collector or []
    if contact_events:
        ev = pd.DataFrame(contact_events)
        ev['tick'] = ev['sub'] // sub_steps
        per_a = ev.groupby(['tick', 'drv_a']).agg(
            n=('j_n', 'size'), dv=('dv_a', 'sum'), dvmax=('dv_a', 'max')).reset_index()
        per_b = ev.groupby(['tick', 'drv_b']).agg(
            n=('j_n', 'size'), dv=('dv_b', 'sum'), dvmax=('dv_b', 'max')).reset_index()
        per_a.columns = ['tick', 'drv', 'imp_events', 'imp_dv', 'imp_dv_max']
        per_b.columns = ['tick', 'drv', 'imp_events', 'imp_dv', 'imp_dv_max']
        per = pd.concat([per_a, per_b]).groupby(['tick', 'drv']).agg(
            imp_events=('imp_events', 'sum'), imp_dv=('imp_dv', 'sum'),
            imp_dv_max=('imp_dv_max', 'max')).reset_index()
        df = df.merge(per, on=['tick', 'drv'], how='left')
        for col in ('imp_events', 'imp_dv', 'imp_dv_max'):
            df[col] = df[col].fillna(0)
    else:
        df['imp_events'] = 0
        df['imp_dv'] = 0.0
        df['imp_dv_max'] = 0.0
    header_metadata = (f" | track_frozen_sha256="
                       f"{getattr(track, 'frozen_sha256', '?')} | sub_steps={sub_steps} | "
                       f"weather_mode={args.weather} | weather_seed={args.seed} | "
                       f"weather_transitions={getattr(engine.weather_model, 'history', [])} | "
                       f"variance={args.variance}"
                       + (f" | grid_order={[d.driver_id for d in drivers]}"
                          if var_grid_order else "")
                       + (f" | compounds={ {k: v.value for k, v in (var_compound_map or {}).items()} }"
                          if var_compound_map else ""))
    _write_race_diag_csv(df, args.out, header_metadata,
                         include_xy=not diag_no_xy, writer_v35=args.writer_v35)
    if corpus_dump is not None:
        dump_sha = corpus_dump.close()
        print(f"[corpus-dump] {corpus_dump.rows} linhas -> "
              f"{args.corpus_dump} sha256={dump_sha}")
    if contact_events:
        ev_path = args.out.replace('.csv', '_events.csv')
        with open(ev_path, 'w') as f:
            f.write(f"# race_diag_v3_contact_solver_v1 events=raw contact points | "
                    f"sub->tick: sub//{sub_steps}\n")
            ev.drop(columns=['tick']).to_csv(f, index=False)
        print(f"[diag] {len(ev)} eventos de contato do solver -> {ev_path}")
    print(f"[diag] {len(df)} linhas -> {args.out} (instrumento race_diag_v3_contact_solver_v1)")
    if getattr(ctrl, 'REJOIN_RAMP_ENABLED', False):
        print(f"[rejoin-ramp] {ctrl.rejoin_ramp_summary()}")

    print("\n===== ESTADO FINAL POR CARRO =====")
    last = df[df.tick == df.tick.max()]
    print(last[['drv', 'speed', 's', 'lat', 'th', 'brk', 'steer_rad']].round(2).to_string(index=False))

    # v15 R5a: clima da corrida (o RNG do WeatherModel NÃO é semeado por
    # processo — transições reais divergem a realização; registrar p/ auditoria)
    wh = getattr(engine.weather_model, 'history', [])
    print(f"\n===== CLIMA (transições reais: {len(wh)}) =====")
    for h in wh:
        print(f"  volta {h[0]}: {h[1].name} -> {h[2].name}")
    if not wh:
        print("  nenhuma transição de kind (grip constante)")

    print("\n===== IMOBILIZACAO (v < 2 m/s) =====")
    for drv, g in df.groupby('drv'):
        slow = g[g.speed < 2.0]
        if len(slow):
            first = slow.tick.min()
            brk_at = g[g.tick >= first].brk.mean()
            print(f"{drv}: {len(slow)} amostras v<2 | primeiro tick lento={first} "
                  f"(s={g[g.tick==first].s.iloc[0]:.0f}m) | brake medio apos={brk_at:.2f}")
        else:
            print(f"{drv}: nunca ficou abaixo de 2 m/s | v_min={g.speed.min():.1f}")

    print("\n===== EPISODIOS DE PARADA >= 3 s (como terminaram) =====")
    if stoplog:
        for st in stoplog:
            print(f"  {st['drv']}: parou em t={st['t_start']:.0f}s por {st['dur_s']:.0f}s "
                  f"(s={st['s']:.0f}m) -> liberado por: {st['freed_by']}")
        n_contato = sum(1 for s_ in stoplog if s_['freed_by'] == 'contato')
        print(f"  TOTAL: {len(stoplog)} paradas | liberadas por contato: {n_contato} | "
              f"por movimento proprio: {len(stoplog) - n_contato}")
    else:
        print("  nenhuma parada >= 3 s")

    print("\n===== SAIDA DE PISTA / CORTES =====")
    off = df[df.offtrack == 1]
    print(f"amostras com centro fora do asfalto: {len(off)} de {len(df)} "
          f"({100 * len(off) / max(len(df), 1):.1f}%)")
    if len(off):
        for drv, g in off.groupby('drv'):
            print(f"  {drv}: {len(g)} amostras fora | lat max={g.lat.abs().max():.1f} m | "
                  f"trechos: {sorted(set((g.s // 200) * 200))}")
    cc = df[df.car_car > 0]
    print(f"\ncontatos c/ SOLO (todo tick, esperado): {df.contacts.sum()} | "
          f"contatos CARRO-CARRO: {len(cc)} amostras, impulso medio "
          f"{cc.impulse.mean() if len(cc) else 0:.0f} N | dv medio "
          f"{cc.impulse_dv.mean() if len(cc) else 0:.2f} m/s")

    # ------------- R3: decomposição FORA-PILOTAGEM vs FORA-PRESO -----------
    # Gate multi-realização (pré-registrado 2026-10-17T12:54:27Z):
    #   preso = |lat|>20 m OU progresso <5 m em janela de 30 s (fora da pista)
    # Janelas de 30 s sobre (lat, cum_dist) por carro; só conta janelas com
    # ticks off-track. Pós-processamento do CSV — NÃO muda comportamento.
    if 'steer_gov_active' in df.columns:
        on_track = df[df.offtrack == 0]
        pct = 100 * on_track.steer_gov_active.mean() if len(on_track) else 0.0
        print(f"\n===== R8 STEER-GOV: ativo em {pct:.2f}% dos ticks ON-TRACK | "
              f"total de clips: {int(df.steer_gov_active.sum())} =====")
        if pct > 0.5:
            print("  [DISCIPLINA] >0,5% — PARE: re-derivar constantes (prereg R8)")
    print("\n===== R3: FORA-PILOTAGEM vs FORA-PRESO (janelas 30 s) =====")
    tot_pilot = tot_preso = 0
    preso_cars = []
    t_end = float(df.t_s.max())
    for drv, g in df.groupby('drv'):
        g = g.sort_values('t_s')
        t = g.t_s.values; lat = g.lat.abs().values
        cum = g.cum_dist.values; offm = g.offtrack.values
        n_pilot = n_preso = 0
        for w0 in np.arange(0.0, t_end, 30.0):
            m = (t >= w0) & (t < w0 + 30.0)
            if not m.any() or not offm[m].any():
                continue
            if (lat[m].max() > 20.0) or ((cum[m].max() - cum[m].min()) < 5.0):
                n_preso += int(offm[m].sum())
            else:
                n_pilot += int(offm[m].sum())
        tot_pilot += n_pilot; tot_preso += n_preso
        if n_preso:
            preso_cars.append(drv)
        print(f"  {drv}: pilotagem={n_pilot:4d} ticks | preso={n_preso:4d} ticks"
              f"{'  <== CARRO-PRESO' if n_preso else ''}")
    n_off = int(df.offtrack.sum())
    print(f"  TOTAL fora: {n_off} ticks ({100*n_off/max(len(df),1):.1f}%) | "
          f"FORA-PILOTAGEM: {tot_pilot} ({100*tot_pilot/max(n_off,1):.1f}% do fora) | "
          f"FORA-PRESO: {tot_preso} ({100*tot_preso/max(n_off,1):.1f}% do fora)")
    print(f"  CARROS-PRESO na sessão: {len(preso_cars)} "
          f"({', '.join(preso_cars) if preso_cars else 'nenhum'} — gate exige 0)")

    # hesitações R3: episódios v<0,5 m/s de 0,3-3 s APÓS a largada (t>20 s)
    hesit = 0
    for drv, g in df.groupby('drv'):
        v = g.sort_values('t_s').speed.values
        tt = g.sort_values('t_s').t_s.values
        m = tt > 20.0
        v, tt = v[m], tt[m]
        i = 0
        while i < len(v):
            if v[i] < 0.5:
                j = i
                while j < len(v) and v[j] < 0.5:
                    j += 1
                dur = (tt[min(j, len(tt)-1)] - tt[i]) if j > i else 0.0
                if 0.3 <= dur < 3.0:
                    hesit += 1
                i = j
            else:
                i += 1
    print(f"  HESITAÇÕES (v<0,5 m/s por 0,3-3 s, pós-largada): {hesit} (gate: <=3)")

    # ---------------- RESUMO DO GATE (modo professor) ----------------
    if args.controller == 'professor':
        print("\n===== GATE ALL-PROFESSOR (v14) =====")
        n_cars = len(drivers)
        laps_done = {d.driver_id: int(engine.states[d.driver_id].lap)
                     for d in drivers}
        completed = sum(1 for v in laps_done.values() if v >= 1)
        print(f"carros com >=1 volta: {completed}/{n_cars} "
              f"(meta >=9/10 {'OK' if completed >= 9 else 'FALHOU'})")
        all_laps, later_laps = [], []
        for d in drivers:
            ts = list(engine.states[d.driver_id].lap_times)
            all_laps.extend(ts)
            later_laps.extend(ts[1:])     # volta 1 = largada parada
            print(f"  {d.driver_id}: {laps_done[d.driver_id]} voltas | "
                  f"tempos={[round(x,1) for x in ts]}")
        print(f"contatos carro-carro (amostras 5 Hz): {len(cc)} (meta < 400 "
              f"{'OK' if len(cc) < 400 else 'FALHOU'}) | baseline aluno-cego: 1333")
        print(f"paradas >= 3 s: {len(stoplog)} (meta 0 "
              f"{'OK' if not stoplog else 'FALHOU'})")
        print(f"ultrapassagens liquidas (trocas com histerese 10 m): {overtakes} "
              f"| pós-largada={overtakes_post_launch} "
              f"{'-> FILA (sem ultrapassagem; teto v14 = evita colisoes)' if overtakes == 0 else ''}")
        if 't_mode' in df.columns:
            print("% de tempo em modo follow por carro (cap+close / total):")
            for drv, g in df.groupby('drv'):
                fol = 100.0 * g.t_mode.isin(['cap', 'close']).mean()
                close = 100.0 * (g.t_mode == 'close').mean()
                print(f"  {drv}: follow {fol:.1f}% (colado {close:.1f}%)")
        if all_laps:
            print(f"tempo mediano de volta COM trafego: "
                  f"{np.median(all_laps):.1f}s (todas; n={len(all_laps)}) | "
                  f"{np.median(later_laps) if later_laps else float('nan'):.1f}s "
                  f"(excl. volta 1, largada rolando) | solo professor: ~107s, aluno: ~112s")

    # FASE 0.8 (v15): MLflow best-effort — métricas da corrida no MLflow
    try:
        from backend.model_train import tracking
        ccn = int((df.car_car > 0).sum())
        with tracking.start_run('race-layer',
                                 params={'track': args.track, 'ticks': args.ticks,
                                         'controller': args.controller,
                                         'mixed': args.mixed or 'none',
                                         'actor': args.actor or 'professor'},
                                 tags={'status': 'research'}):
            tracking.log_race(dict(
                contatos_carro=ccn,
                contatos_pos_largada=int(((df.car_car > 0) & (df.t_s > 60)).sum()),
                fora_asfalto_pct=100.0 * float(df.offtrack.mean()),
                paradas_3s=len(stoplog),
                ultrapassagens=overtakes))
    except Exception:
        pass

    # ---------------- RESUMO CAMPO MISTO (A2 FASE 5) ----------------
    if mixed_groups is not None:
        ms = mixed_summary(df, mixed_groups)
        print("\n===== CAMPO MISTO (A2 FASE 5) =====")
        print(f"contatos TOTAIS: {ms['total_contacts']} | pós-largada (t>60s): "
              f"{ms['post_launch']} | pares: {ms['pair_contacts']}")
        for gname in ('professor', 'traffic', 'edge', 'composite'):
            if gname not in mixed_groups.values():
                continue
            g = ms[gname]
            print(f"  [{gname} x{g['cars']}] contatos {g['contacts']} "
                  f"(pós-largada {g['post_launch']}) | voltas {g['laps']} | "
                  f"rolante med {g['rolling_med'] and round(g['rolling_med'], 1)}s | "
                  f"hesitações {g['hesitations']} | fora {g['offtrack_pct']:.2f}%")
        print("  baseline all-v10: 1333 contatos, 137s rolantes, 1 hesitação, 0,8% fora")
    if args.pass_decision:
        pass_controller = ctrl if args.controller == 'professor' else ctrl_prof
        active_ids = (None if mixed_groups is None else
                      {drv.driver_id for drv in drivers
                       if mixed_groups[drv.driver_id] == 'professor'})
        for driver_id, stats in pass_controller.pass_decision_summary(
                active_ids).items():
            print(f"[pass-decision] {driver_id}: {stats}")
    if args.leader_yield:
        yield_controller = ctrl if args.controller == 'professor' else ctrl_prof
        active_ids = (None if mixed_groups is None else
                      {drv.driver_id for drv in drivers
                       if mixed_groups[drv.driver_id] == 'professor'})
        for driver_id, prof in zip(
                [drv.driver_id for drv in drivers],
                yield_controller.professors):
            if active_ids is not None and driver_id not in active_ids:
                continue
            print(f"[leader-yield] {driver_id}: "
                  f"{prof.leader_yield_summary()}")
    engine.physics.close()


def _obs23(ctrl, engine, drv, phys, s, lat_s, drivers):
    """Replica a observacao 23-dim que o NeuralRaceController monta para a política."""
    import math as m
    A, AB, L = ctrl._A, ctrl._AB, ctrl._seg_len
    x, y = phys['x'], phys['y']
    ap_x, ap_y = x - A[:, 0], y - A[:, 1]
    t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / (L * L + 1e-9), 0.0, 1.0)
    proj_x, proj_y = A[:, 0] + t * AB[:, 0], A[:, 1] + t * AB[:, 1]
    d = np.hypot(proj_x - x, proj_y - y)
    idx = int(np.argmin(d))
    cross = AB[idx, 0] * (y - proj_y[idx]) - AB[idx, 1] * (x - proj_x[idx])
    signed = float(d[idx]) if cross >= 0.0 else -float(d[idx])
    heading_err = ctrl._wrap(phys['heading_rad'] - float(ctrl._seg_heading[idx]))
    h0 = ctrl._heading_at(s)
    prev_steer, prev_long = ctrl._prev_actions.get(drv.driver_id, (0.0, 0.0))
    tel = [
        phys['speed_mps'] / ctrl.OBS_SPEED,
        phys['yaw_rate'] / ctrl.OBS_YAW_RATE,
        phys['g_lat'] / ctrl.OBS_G,
        phys['g_long'] / ctrl.OBS_G,
        signed / ctrl._half_width,
        m.sin(heading_err), m.cos(heading_err),
        prev_steer, prev_long,
    ]
    for dm in ctrl.PREVIEW_DISTS:
        tel.append(ctrl._wrap(ctrl._heading_at(s + dm) - h0) / m.pi)
        tel.append(ctrl._kappa_signed(s + dm) * ctrl.KAPPA_OBS_SCALE)
    return np.clip(np.nan_to_num(np.array(tel, dtype=np.float32)), -5.0, 5.0)


def _pose_at_s(ctrl, s):
    """(x, y, yaw) na LINHA CENTRAL em s — usado pelo --hold-at (B3.3d)."""
    A, AB, L = ctrl._A, ctrl._AB, ctrl._seg_len
    s = float(s) % ctrl._track_len_s
    j = int(np.clip(np.searchsorted(ctrl._seg_cum, s, side='right') - 1,
                    0, len(A) - 1))
    t = (s - ctrl._seg_cum[j]) / max(L[j], 1e-9)
    x = A[j, 0] + t * AB[j, 0]
    y = A[j, 1] + t * AB[j, 1]
    yaw = float(np.arctan2(AB[j, 1], AB[j, 0]))
    return float(x), float(y), yaw


def _proj(ctrl, x, y):
    A, AB, L = ctrl._A, ctrl._AB, ctrl._seg_len
    ap_x, ap_y = x - A[:, 0], y - A[:, 1]
    t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / (L * L + 1e-9), 0.0, 1.0)
    px, py = A[:, 0] + t * AB[:, 0], A[:, 1] + t * AB[:, 1]
    d = np.hypot(px - x, py - y)
    idx = int(np.argmin(d))
    s = ctrl._seg_cum[idx] + float(t[idx]) * L[idx]
    return None, s, None, float(d[idx])


if __name__ == '__main__':
    main()
