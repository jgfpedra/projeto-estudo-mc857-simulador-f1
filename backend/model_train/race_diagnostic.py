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
import run_race_10_cars as R


def parse_mixed(spec: str, n_total: int = 10):
    """A2 (FASE 5): parse de --mixed "traffic:2,edge:8".

    Retorna {'traffic': N, 'edge': M}. Valida: soma == n_total, chaves
    conhecidas, contagens positivas.
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
        if k not in ('traffic', 'edge'):
            raise ValueError(f"--mixed: grupo '{k}' desconhecido (use traffic/edge)")
        if v <= 0:
            raise ValueError(f"--mixed: contagem de '{k}' deve ser > 0")
        groups[k] = v
    if sum(groups.values()) != n_total:
        raise ValueError(f"--mixed: soma {sum(groups.values())} != {n_total} carros")
    return groups


def assign_groups(driver_ids, mixed):
    """driver_id -> 'traffic' | 'edge' (A2 FASE 5). Os primeiros N driver_ids
    (ordem do grid original) são 'traffic', o resto 'edge'. A posição FÍSICA
    no grid é embaralhada à parte; o grupo é por driver_id."""
    out = {}
    i = 0
    for g, n in (('traffic', mixed.get('traffic', 0)), ('edge', mixed.get('edge', 0))):
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
    for gname in ('traffic', 'edge'):
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

    def __init__(self, track, sf=0.80, sf_range=None, machine_only=False):
        """sf_range=(lo, hi): FASE 2 — sf POR PILOTO determinístico (crc32 do
        driver_id), U[lo,hi]; profile PRÓPRIO por piloto. None = homogêneo
        (controle, comportamento histórico)."""
        from backend.model_train.velocity_profile import VelocityProfile
        import zlib
        self._sf_range = sf_range
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
                vp_i = VelocityProfile(np.array(self._A, dtype=np.float64),
                                        grip_mult=0.788, sf=sf_i,
                                        ds_target=4.0, smooth_window_m=20.0)
            else:
                vp_i = self._vp
            prof_i = ReferenceController(_RaceEnvView(engine, self._tables, drv.driver_id),
                                         velocity_profile=vp_i)
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

    def predict_batch(self, engine, drivers, waypoints, track_id=0):
        from backend.model_train.f1_env import F1MultiContextEnv
        self._ensure_professors(engine, drivers)
        n = len(drivers)
        # 1) snapshot de TODOS: (s, lat com sinal, v) — métrica signed_dist_s
        snap_s = np.zeros(n); snap_lat = np.zeros(n); snap_v = np.zeros(n)
        for i, drv in enumerate(drivers):
            phys = engine.physics.get_state(engine.handles[drv.driver_id])
            s_i, lat_i = self._project_signed(phys['x'], phys['y'])
            snap_s[i], snap_lat[i], snap_v[i] = s_i, lat_i, phys['speed_mps']

        actions = []
        for i, drv in enumerate(drivers):
            # 2) professor: os outros 9 como tráfego
            traffic = [(snap_s[j], snap_lat[j], snap_v[j])
                       for j in range(n) if j != i]
            a = self.professors[i].action(traffic)
            speed = float(snap_v[i])
            th, brk, steer_rad = F1MultiContextEnv.action_to_controls(a, speed)

            # ---- 3. rejoin (fora do asfalto) — MESMA regra do modo neural
            lat_dist = abs(float(snap_lat[i]))
            offtrack = lat_dist > self._half_width * self.OFFTRACK_FACTOR
            if offtrack:
                correction = -float(np.sign(snap_lat[i])) * min(
                    self.STEER_MAX_RAD, 0.3 + lat_dist / 40.0)
                steer_rad = correction
                if speed > self.REJOIN_TARGET_MPS * 1.2:
                    excess = (speed - self.REJOIN_TARGET_MPS) / 6.0
                    th, brk = 0.0, max(brk, float(np.clip(excess, 0.3, 1.0)))
                else:
                    th, brk = self.REJOIN_THROTTLE, 0.0

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
            elif rec_active:
                authority = 'recovery_rejoin' if offtrack else 'recovery'
            elif offtrack:
                authority = 'rejoin'
            else:
                authority = 'professor'
            self.last_authority[drv.driver_id] = authority
            actions.append((th, brk, steer_rad))
        return actions


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
    ap.add_argument('--sf-range', type=str, default=None,
                    help='FASE 2: "lo:hi" p/ sf POR PILOTO no all-professor '
                         '(ex: "0.85:0.95", determinístico por driver_id); '
                         'default = homogêneo 0.80 (controle)')
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
    args = ap.parse_args()
    # validação antecipada do --mixed (ap.error antes de qualquer setup caro)
    if args.mixed:
        try:
            parse_mixed(args.mixed, n_total=10)
        except ValueError as e:
            ap.error(str(e))
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
          f"variance={args.variance}"
          + (f" | grid_order={[d.driver_id for d in drivers]}" if var_grid_order else "")
          + (f" | compounds={ {k: v.value for k, v in var_compound_map.items()} }"
             if var_compound_map else ""))
    mixed_groups = None
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
    R.place_grid(engine, track, drivers)
    engine.race_started = True

    # exportador + controller EXATOS da corrida
    ctrl_traffic = ctrl_edge = None
    if args.controller == 'professor':
        sf_range = None
        if args.sf_range:
            lo, hi = args.sf_range.split(':')
            sf_range = (float(lo), float(hi))
        ctrl = ProfessorRaceController(track, sf=0.80, sf_range=sf_range,
                                      machine_only=args.pass_machine_only)
        print(f"[diag] controller: PROFESSOR x{len(drivers)} (gate all-professor) "
              f"| sf_range={sf_range or 'homog 0.80'} | machine_only={args.pass_machine_only} "
              f"| track={track.name} | seed={args.seed}")
    elif args.mixed:
        # dois controllers INDEPENDENTES, cada um computando obs/ações para
        # TODOS os 10 (o dono decide; os outros descartam) — o v14 precisa
        # ver os 9 vizinhos nas features de tráfego mesmo que sejam v10
        tk = Path(args.traffic_actor) if args.traffic_actor else R.PROFILES['traffic']['keras']
        ek = Path(args.actor) if args.actor else R.PROFILES['race']['keras']
        tn = R.ensure_npz_weights_exist(tk, tk.with_name(tk.stem + '_weights.npz'))
        en = R.ensure_npz_weights_exist(ek, ek.with_name(ek.stem + '_weights.npz'))
        ctrl_traffic = R.NeuralRaceController(weights_path=tn, obs_mode='traffic',
                                               mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track)
        ctrl_edge = R.NeuralRaceController(weights_path=en, obs_mode='edge',
                                           mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track)
        ctrl = ctrl_traffic
        print(f"[diag] MIXED: traffic={tk.name} (input {ctrl_traffic.actor.input_dim}) "
              f"+ edge={ek.name} (input {ctrl_edge.actor.input_dim})")
    else:
        if args.profile == 'composite':
            # v15 FASE 4: solo v10 (edge via NPZ) + residual NPZ; obs='traffic'
            from backend.model_train.residual_gated import NumpyCompositeActor
            actor_keras = R.PROFILES['race']['keras']
            npz_path = R.ensure_npz_weights_exist(actor_keras,
                    actor_keras.with_name(actor_keras.stem + '_weights.npz'))
            ctrl = R.NeuralRaceController(weights_path=npz_path, obs_mode='traffic',
                                          mappings_path=R.DEFAULT_MAPPINGS_PATH, track=track,
                                          steer_gov=args.steer_gov)
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
                                          steer_gov=args.steer_gov)
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
    rows = []
    stoplog = []      # episodios de parada >= 3 s: como terminaram
    slow_since = {}   # drv -> tick em que ficou lento
    # gate v14: ultrapassagens líquidas por par com histerese (±10 m de
    # progresso acumulado) — contato momentâneo não conta como troca
    pair_settled = {}
    overtakes = 0
    OVERTAKE_HYST_M = 10.0
    _prev_w_kind = engine.weather_model.current.kind
    for t in range(args.ticks):
        if mixed_groups is not None:
            # cada controller computa para TODOS (o v14 precisa ver os 9
            # vizinhos nas features de tráfego); o dono decide
            acts_t = ctrl_traffic.predict_batch(engine, drivers, wps, track_id=0)
            acts_e = ctrl_edge.predict_batch(engine, drivers, wps, track_id=0)
            actions = [acts_t[i] if mixed_groups[drv.driver_id] == 'traffic'
                       else acts_e[i] for i, drv in enumerate(drivers)]
        else:
            actions = ctrl.predict_batch(engine, drivers, wps, track_id=0)
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
                    ctrl_i = ctrl_traffic if mixed_groups[drv.driver_id] == 'traffic' \
                        else ctrl_edge
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
                if getattr(ctrl, '_composite_np', None) is not None:
                    row['g_gate'] = ctrl._res_gate.get(drv.driver_id, 0.0)
                    row['r_norm'] = ctrl._res_norm.get(drv.driver_id, 0.0)
                    row['composite_active'] = int(row['g_gate'] > 0)
                if getattr(ctrl, 'steer_gov', 'off') == 'cap':
                    row['steer_gov_active'] = int(
                        ctrl.last_steergov.get(drv.driver_id, 0))
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
                rows.append(row)
        if engine.race_finished:
            break

    df = pd.DataFrame(rows)

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
    with open(args.out, 'w') as f:
        f.write(f"# race_diag_v3_3_res16d | track_frozen_sha256="
                f"{getattr(track, 'frozen_sha256', '?')} | sub_steps={sub_steps} | "
                f"weather_mode={args.weather} | weather_seed={args.seed} | "
                f"weather_transitions={getattr(engine.weather_model, 'history', [])} | "
                f"variance={args.variance}"
                + (f" | grid_order={[d.driver_id for d in drivers]}" if var_grid_order else "")
                + (f" | compounds={ {k: v.value for k, v in (var_compound_map or {}).items()} }"
                   if var_compound_map else "") + "\n")
        df.to_csv(f, index=False)
    if contact_events:
        ev_path = args.out.replace('.csv', '_events.csv')
        with open(ev_path, 'w') as f:
            f.write(f"# race_diag_v3_contact_solver_v1 events=raw contact points | "
                    f"sub->tick: sub//{sub_steps}\n")
            ev.drop(columns=['tick']).to_csv(f, index=False)
        print(f"[diag] {len(ev)} eventos de contato do solver -> {ev_path}")
    print(f"[diag] {len(df)} linhas -> {args.out} (instrumento race_diag_v3_contact_solver_v1)")

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
        for gname in ('traffic', 'edge'):
            g = ms[gname]
            print(f"  [{gname} x{g['cars']}] contatos {g['contacts']} "
                  f"(pós-largada {g['post_launch']}) | voltas {g['laps']} | "
                  f"rolante med {g['rolling_med'] and round(g['rolling_med'], 1)}s | "
                  f"hesitações {g['hesitations']} | fora {g['offtrack_pct']:.2f}%")
        print("  baseline all-v10: 1333 contatos, 137s rolantes, 1 hesitação, 0,8% fora")
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
