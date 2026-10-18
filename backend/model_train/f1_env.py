import math
import os
import sys
from collections import deque
from pathlib import Path
import numpy as np
import gymnasium as gym
from gymnasium import spaces
import pandas as pd

# Garante que a raiz do projeto esteja no sys.path mesmo em subprocessos ou importado diretamente
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MODEL_DIR = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
if str(MODEL_DIR) not in sys.path:
    sys.path.insert(0, str(MODEL_DIR))

from backend.engine import SimulationEngine, SimulationConfig
from backend.engine import CarInput
from backend.domain import (
    CarSpecs,
    Driver,
    Track,
    TyreCompound,
    WeatherModel,
    WeatherKind,
    BASE_CONDITIONS,
    build_interlagos_track,
)

try:
    from backend.config import load_track
except ImportError:
    load_track = None

from backend.domain.track_loader import FastF1TrackLoader

DEFAULT_REFERENCE_CSV = MODEL_DIR / 'reference_path.csv'

# --- Pistas reais via FastF1 (sem waypoints hardcoded) ---------------------
# Padrão: GP de São Paulo (Interlagos) baixado do FastF1, cacheado em disco.
# Se o evento pedido não existir, cai para o GP de São Paulo; se ainda assim
# falhar (ex.: sem internet e sem cache), último recurso é o preset local.
FASTF1_DEFAULT_YEAR = 2024
FASTF1_DEFAULT_EVENT = "São Paulo"
FASTF1_CACHE_DIR = MODEL_DIR / "cache_fastf1"

# aliases amigáveis -> nome do evento no FastF1
_FASTF1_EVENT_ALIASES = {
    "interlagos": FASTF1_DEFAULT_EVENT,
    "sao paulo": FASTF1_DEFAULT_EVENT,
    "são paulo": FASTF1_DEFAULT_EVENT,
    "sao-paulo": FASTF1_DEFAULT_EVENT,
    "são-paulo": FASTF1_DEFAULT_EVENT,
    "brazil": FASTF1_DEFAULT_EVENT,
    "default": FASTF1_DEFAULT_EVENT,
    "none": FASTF1_DEFAULT_EVENT,
}


def _fastf1_event_name(track_str):
    if track_str is None or not str(track_str).strip():
        return FASTF1_DEFAULT_EVENT
    s = str(track_str).strip()
    return _FASTF1_EVENT_ALIASES.get(s.lower(), s)


def resolve_track(track=None, reference_csv=None, year=FASTF1_DEFAULT_YEAR,
                  session="R", cache_dir=None, width_m=12.0):
    """Resolve a pista de treino com esta ordem de prioridade:

    1. ``track`` já sendo um objeto :class:`Track` -> usa direto;
    2. CSV de referência (``reference_csv`` ou caminho .csv) -> pista do arquivo;
    3. FastF1 com o evento pedido (dados reais);
    4. Fallback: FastF1 GP de São Paulo (Interlagos);
    5. Último recurso (offline/sem cache): preset local de Interlagos.
    """
    if isinstance(track, Track):
        return track

    csv_path = None
    if reference_csv is not None:
        csv_path = Path(reference_csv)
    elif track is not None:
        candidate = Path(str(track))
        if str(track).lower().endswith(".csv") or candidate.exists():
            csv_path = candidate
    if csv_path is not None:
        if not csv_path.is_absolute() and not csv_path.exists():
            if (MODEL_DIR / csv_path).exists():
                csv_path = MODEL_DIR / csv_path
            elif (PROJECT_ROOT / csv_path).exists():
                csv_path = PROJECT_ROOT / csv_path
        ref = pd.read_csv(str(csv_path))
        return Track.from_waypoints(
            name=csv_path.stem,
            waypoints=ref[['X', 'Y']].values.astype(float),
            width_m=width_m,
        )

    cache = Path(cache_dir) if cache_dir is not None else FASTF1_CACHE_DIR
    loader = FastF1TrackLoader(cache_dir=cache)
    event = _fastf1_event_name(track)
    attempts = [event] + ([] if event == FASTF1_DEFAULT_EVENT else [FASTF1_DEFAULT_EVENT])
    for ev in attempts:
        try:
            t = loader.load(year=year, event=ev, session=session,
                            load_session=True,       # circuit_info exige voltas carregadas
                            grid_from_telemetry=False)  # sem telemetria: só o desenho da pista
            print(f"[F1MultiContextEnv] Pista carregada do FastF1: {t.name} "
                  f"({year}, {ev}), {len(t.waypoints)} waypoints")
            return t
        except Exception as e:
            print(f"[F1MultiContextEnv] FastF1 falhou p/ '{ev}' ({year}): {e}")

    print("[F1MultiContextEnv] Sem FastF1; usando preset local de Interlagos (último recurso).")
    return build_interlagos_track()

# ----------------------------------------------------------------------------
# Constantes do ambiente (todas ajustáveis)
# ----------------------------------------------------------------------------
# Normalização da observação: a rede recebe tudo em ordem de grandeza ~[-1, 1].
# (Antes, fuel_kg≈110 e speed≈80 entravam crus e davam ao ator um viés enorme
# e constante, independente do estado, já na inicialização.)
OBS_SPEED = 100.0      # m/s
OBS_YAW_RATE = 2.0     # rad/s
OBS_G = 5.0            # g
OBS_SLIP_DEG = 10.0    # graus
OBS_TYRE_LIFE = 30.0
OBS_FUEL_KG = 110.0
OBS_CLIP = 5.0

# --- Observação local com preview geométrico (Alternativa B, estilo F1TENTH) ---
# Em vez de 3 previews de heading, a política recebe, por ponto à frente, a
# MUDANÇA DE HEADING e a CURVATURA ASSINADA — o necessário para decidir
# "preciso frear" antes de entrar na curva. `s_frac` foi REMOVIDO (memorização
# posicional); os embedding ids ficam constantes no treino single-track.
PREVIEW_DISTS = (10.0, 20.0, 35.0, 50.0, 75.0, 100.0, 150.0)  # m à frente
KAPPA_OBS_SCALE = 25.0     # kappa (rad/m) * 25: hairpin ~0.1 -> ~2.5 na obs
KAPPA_WINDOW_M = 20.0      # janela de suavização p/ curvatura local (cobre os
                           # segmentos de ~24 m da linha FastF1 sem ruído de quina)
N_OBS_BASE = 9             # speed, yaw_rate, g_lat, g_long, lat_err, sin/cos herr,
                           # prev_steer, prev_long
N_OBS_TELEMETRY = N_OBS_BASE + 2 * len(PREVIEW_DISTS)   # = 23

# --- Percepção de BORDAS (Fase C v8, inspirada no LiDAR do F1TENTH) --------
# Raios virtuais a partir do carro até os limites do ASFALTO (não a grama,
# não a linha central). Dá à política a distância REAL ao "muro" na direção
# de movimento — informação que lat_err e previews de curvatura não dão:
# num hairpin, a borda interna vem em direção ao carro mesmo com lat_err=0.
# Modos de observação:
#   'legacy' = 23 dims (atual, compatível com todos os checkpoints v2–v7)
#   'edge'   = 23 + N_LIDAR_RAYS (34 com 11 raios) — F1TENTH-like
EDGE_RAY_ANGLES_DEG = (-90.0, -72.0, -54.0, -36.0, -18.0, 0.0,
                         18.0, 36.0, 54.0, 72.0, 90.0)  # ±90° a partir do heading
N_LIDAR_RAYS = len(EDGE_RAY_ANGLES_DEG)          # 11
LIDAR_MAX_RANGE_M = 40.0                          # alcance do raio (m)
LIDAR_WINDOW_SEGS = 30                            # segmentos de borda por lado
                                                  # (30×~4m=120m > 2×max_range)

# --- Percepção de TRÁFEGO (FASE 2 v14) -----------------------------------
# obs_mode='traffic' = edge (34d) + 12d de tráfego. Layout dos 12d: os
# 3 carros mais próximos ranqueados por |dist_s| (distância AO LONGO DA
# PISTA com sinal — ver signed_dist_s em reference_controller.py), 4
# features por carro, nesta ordem:
#   [ |dist_s|/100,  (v_outro - v_ego)/OBS_SPEED,  lat_outro/half_width,  ahead(1|0) ]
# Convenções: dist_s>0 = carro À FRENTA (o sinal vive no flag `ahead`, o
# canal de distância é sempre positivo); Δv>0 = o outro é mais rápido;
# lat>0 = outro carro à esquerda da linha central. Menos de 3 visíveis ->
# slots restantes em ZERO. A obs do aluno NUNCA contém o próprio carro.
# Ator v14: 46 tel + 2 ctx + 8 emb_track + 4 emb_compound = 60 entradas.
N_TRAFFIC_CARS_OBS = 3      # carros representados na obs
N_TRAFFIC_FEAT = 4          # features por carro
N_OBS_TRAFFIC = N_TRAFFIC_CARS_OBS * N_TRAFFIC_FEAT   # 12
OBS_MODES = {
    'legacy': N_OBS_TELEMETRY,
    'edge':   N_OBS_TELEMETRY + N_LIDAR_RAYS,             # 34
    'traffic': N_OBS_TELEMETRY + N_LIDAR_RAYS + N_OBS_TRAFFIC,  # 46
}


def compute_traffic_features(v_ego, s_ego, half_width, track_len_s, others):
    """FÓRMULA ÚNICA do bloco 12d de tráfego (FASE 2 v14).

    Consumida pelo env (F1MultiContextEnv._traffic_features) E pelo race
    runner neural (NeuralRaceController) — REUTILIZE, não reimplemente
    (histórico: a duplicação do cálculo de kappa gerou o bug do wrap ±180°
    DUAS vezes).

    Args:
      v_ego, s_ego: velocidade (m/s) e arco (m) do carro OBSERVADOR;
      half_width, track_len_s: geometria da pista;
      others: [(s, lat_com_sinal, v)] dos OUTROS carros (nunca o ego).

    Layout (N_TRAFFIC_CARS_OBS carros mais próximos por |dist_s|, 4 feats
    cada): [|dist_s|/100, (v_outro-v_ego)/OBS_SPEED, lat/half_width,
    ahead(1|0)]; zeros se menos de 3 visíveis.
    """
    from backend.model_train.reference_controller import signed_dist_s
    cands = []
    for (s_o, lat_o, v_o) in others:
        dist_s = signed_dist_s(s_o, s_ego, track_len_s)
        cands.append((abs(dist_s), dist_s, lat_o, v_o))
    cands.sort(key=lambda c: c[0])          # ranking por |dist_s|
    feats = np.zeros(N_OBS_TRAFFIC, dtype=np.float32)
    for k in range(min(N_TRAFFIC_CARS_OBS, len(cands))):
        _, dist_s, lat_o, v_o = cands[k]
        feats[N_TRAFFIC_FEAT * k + 0] = abs(dist_s) / 100.0
        feats[N_TRAFFIC_FEAT * k + 1] = (v_o - v_ego) / OBS_SPEED
        feats[N_TRAFFIC_FEAT * k + 2] = lat_o / half_width
        feats[N_TRAFFIC_FEAT * k + 3] = 1.0 if dist_s > 0.0 else 0.0
    return feats

# Esterço: ±1 da ação -> ângulo de roda. O limite ENCOLHE com a velocidade
# (a 60 m/s, 25° de roda é rodopio instantâneo; ruído de exploração vira suicídio).
STEER_MAX_RAD = math.radians(45.0)  # era ~25.7° (pi/7): insuficiente p/ horquillas
                                    # fechadas (Ferradura/Bico de Pato). Com wheelbase
                                    # 3.4 m, 25.7° dá raio mín. ~7.1 m; 45° dá ~3.4 m.
                                    # O encolhimento com a velocidade continua protegendo
                                    # em alta (a 50 m/s já cai para ~7°, mesma faixa de antes).
STEER_MIN_RAD = 0.04            # piso em alta velocidade
STEER_V0 = 25.0                 # m/s: velocidade onde o limite cai pela metade

# Recompensa (escala ~0.1/m -> uma volta de 4.3 km ≈ +430)
R_PROGRESS = 0.1        # por metro de progresso ao longo da linha central
P_OFFTRACK = 0.5        # por metro fora da pista, por step
P_CENTER = 0.02         # * (lat/half_width)^2 por step
P_HEADING = 0.05        # * |heading_err| (rad) por step
P_CRASH = 10.0          # terminal: saiu da pista
P_STUCK = 30.0          # terminal: sem progresso — dobrado para punir travamento mais que crash
R_LAP = 100.0           # bônus por completar a volta — dobrado para o agente aprender a terminar

# --- CHECKPOINT GATES ("dividir e conquistar", estilo jogo de corrida) ---
# Gates ao longo da pista: passar por um gate dá bônus (pequenas conquistas em
# vez de só o R_LAP distante). Se sair da pista, o carro é REPOSICIONADO no
# último gate completado (com penalidade) em vez de terminar o episódio — assim
# o agente prica muito mais as regiões difíceis (ex.: a penúltima curva) e o
# sinal de recompensa deixa de ser tão esparso.
GATE_SPACING_M = 60.0      # distância alvo entre gates (Interlagos ~4,3 km -> ~72 gates)
GATE_CURVATURE_BIAS = 2.0  # gates extras nas curvas: espaçamento/este FATOR onde kappa for alta
R_GATE = 3.0               # bônus por gate cruzado (~72 gates * 3 ≈ +216, comparável ao R_LAP)
P_RESPAWN = 5.0            # penalidade fixa por ser reposicionado (metade do crash)
MAX_RESPAWNS = 5           # respawns por episódio; esgotou -> termina como crash
RESPAWN_SPEED_MPS = 5.0    # volta à pista já rolando devagar (evita flag de "stuck")
STUCK_WINDOW = 40       # steps (4 s a 10 Hz) — detecta travamento mais rápido (era 60/6s)
STUCK_MIN_PROGRESS_M = 5.0  # exige 5 m em 4 s (antes: 3 m em 6 s)

# --- P_SLOW: pressão p/ andar na velocidade que a curva permite ---
# Evidência (treino 500 iters): melhor volta RODA A ~10 km/h e morre a ~350-470 m
# do fim (penúltima curva). Com só R_PROGRESS, andar devagar é quase de graça e
# parar custa -5 < crash -10 -> "travar na curva fechada" vira política ótima.
# v_tgt = sqrt(A_LAT_MAX / kappa_ahead), clipada; penaliza speed < SLOW_FRAC*v_tgt.
A_LAT_MAX = 14.0        # m/s²: LEGADO — mantido p/ compatibilidade com o
                         # v_tgt do P_SLOW e do currículo (NÃO é mais usado no
                         # _v_allow_at, que agora usa o modelo físico com downforce).
# --- Modelo físico p/ v_allow da RECOMPENSA (Fase 0 Meta C) ----------------
# a_lat_avail(v) = sf_reward · mu · grip · (g + 0.5·rho·CL·A·v²/m)
# Medido no skidpad: 16 m/s² (v=20), 22.3 (v=40), 32.7 (v=60) — o A_LAT_MAX=14
# fixo ignorava o downforce e PROIBIA o ritmo que a Meta C exige.
MU_NOMINAL = 1.8         # slick F1 seco
RHO_AIR = 1.225          # kg/m³
CL_A = 3.2 * 1.5         # CL · área frontal (m²)
CAR_MASS = 798.0         # kg (specs + piloto + combustível base)
C_DOWN = 0.5 * RHO_AIR * CL_A   # coef de downforce = 2.94 N/(m/s)²
GRIP_REAL = 0.788        # grip realista (temp de pneu) quando override=None
SF_REWARD_DEFAULT = 0.80 # fator de segurança da recompensa (0.80 ≈ comportamento legado)
                        # o assist de guinada limita a_lat a mu_eff*g ≈ 14-17.7.
A_BRAKE_REF = 10.0      # m/s²: planeja frenagem a ~83% do limite físico (~12).
                        # EVIDÊNCIA: 17/17 falhas determinísticas (v5c/v6) eram
                        # sub-frenagem na entrada do wrap (chegava a 95-128 km/h
                        # onde a curva exige ~70); o professor passa freando a
                        # ~7.3 m/s² médios. Planejar SEM margem (12 = limite)
                        # deixa a política sem crédito por frear um pouco antes.
V_TGT_MIN = 15.0        # m/s: piso da velocidade alvo (curva muito fechada)
V_TGT_MAX = 85.0        # m/s: teto (reta longa)
SLOW_FRAC = 0.6         # penaliza abaixo de 60% da velocidade alvo
P_SLOW = 0.15           # por step, proporcional ao déficit relativo
KAPPA_AHEAD_M = 150.0   # horizonte de busca da curvatura (m)

# --- Velocidade segura por DISTÂNCIA DE FRENAGEM (fase: planejamento) -------
# Diagnóstico v2: a política NÃO freava para o hairpin — o preview mostrava
# kappa=0.037 a 150 m, lat explodia a 53 m/s. Comprimento de treino com a
# recompensa antiga: o P_FAST antigo usava só a curvatura NA POSIÇÃO ATUAL via
# kappa_ahead(s), e o prêmio de progresso por velocidade alta pagava o crash.
# Agora a velocidade permitida é a mesma do controlador de referência:
#   v_allow = min_d sqrt( v_curve(d)^2 + 2 * A_BRAKE_REF * d )
# e o PRÊMIO DE PROGRESSO é modulado por min(1, v_allow/v): andar mais rápido
# do que dá para frenar deixa de pagar. Isso remove o incentivo raiz
# (não é mais uma penalização arbitrária — é um gate no próprio progresso).
FAST_FRAC = 1.05         # tolera 5% acima de v_allow sem custo
P_FAST = 0.5             # por step, proporcional ao excesso relativo


class F1MultiContextEnv(gym.Env):
    def __init__(
        self,
        track=None,
        reference_csv=None,
        driver_id='HAM',
        track_id=0,
        compound_id=0,
        logic_step_hz=10.0,
        physics_sub_steps=24,
        max_steps=3000,   # era 1500: no crawl ~2.9 m/s a volta (4309 m) não cabia
                          # em 1500 steps (iter 108: len=1500, prog=3838 m) -> R_LAP
                          # nunca era visto; 3000 steps = 300 s garantem completar
        random_start_prob=0.0,
        f1_year=FASTF1_DEFAULT_YEAR,
        f1_session="R",
        fastf1_cache_dir=None,
        obs_mode='legacy',    # 'legacy'=23 dims | 'edge'=23+11 raios LiDAR (v8)
        sf_reward=SF_REWARD_DEFAULT,  # fator de segurança do v_allow da recompensa
        allow_respawn=True,   # treino: respawn no último gate; avaliação: False
        grip_random=None,     # (lo, hi): domain randomization de aderência por
                              # episódio — sorteia grip_override em [lo, hi] no
                              # reset. None = usa grip_override fixo.
        start_zones=None,     # Currículo v5 (Fase D): lista de (s_lo, s_hi) em
                              # metros ANTES de curvas críticas. Uma fração dos
                              # starts aleatórios nasce nessas janelas com
                              # velocidade de APROXIMAÇÃO (0.5–1.3 × v_segura),
                              # ensinando a política a frear ATÉ a velocidade
                              # da curva — não até zero (v4 freava a ~0 nos
                              # hairpins por nunca ter visto aproximações).
        zone_frac=0.5,        # fração dos starts aleatórios que usam as zonas
        grip_override=1.0,    # treino: grip cheio (ignora temperatura/pneu gasto);
                            # a penalidade de temperatura (pista 42°C vs pneu ótimo
                            # 95°C) derrubava mu_eff p/ ~1.42 e tornava o hairpin
                            # marginal até p/ o controlador clássico — o agente
                            # aprende pilotagem, não química de pneu. None = realista.
        n_traffic=0,         # FASE 2 v14: nº de fantasmas (0-9) dirigidos pelo
                            # professor de TRÁFEGO (FASE 1), grip nominal 1.0,
                            # espaçados no grid à FRENTE do aluno no reset.
                            # NÃO geram eventos de volta (engine._no_lap_drivers)
                            # e NÃO contam no lap% do aluno.
        grid_position=10,   # FASE 6: posição do aluno no grid (P1..P10).
                            # None = default 10 (solo).
                            # int = fixo; (lo,hi) = sorteado por reset (ex:
                            # (5,7) — fantasmas à frente E ATRÁS: a obs já
                            # codifica atrás com ahead=0, mas nenhum treino
                            # anterior os expôs).
        ghost_hold_ticks=None,  # FASE 6: (lo, hi) — 1 fantasma sortudo PARa
                            # por esse intervalo de ticks em momento aleatório
                            # do episódio (congelado na pose via set_position
                            # + reset_vel). Rótulos de CONTORNO de carro
                            # parado — a causa-raiz medida do encravamento.
        ghost_hold_n=1,     # nº de fantasmas que param por episódio (1-2)
        ghost_sf_range=None,  # v15 FASE 3: (lo, hi) — sf POR FANTASMA
                              # (determinístico por driver_id; profile
                              # próprio) — heterogeneidade de pace real
    ):
        self.allow_respawn = allow_respawn
        if obs_mode not in OBS_MODES:
            raise ValueError(f"obs_mode inválido: {obs_mode!r}; use {list(OBS_MODES)}")
        self.obs_mode = obs_mode
        self.n_traffic = int(n_traffic)
        if not 0 <= self.n_traffic <= 9:
            raise ValueError(f"n_traffic inválido: {n_traffic} — use 0 a 9 "
                             f"(corrida de 10 carros: aluno + até 9 fantasmas)")
        # FASE 6: validação dos novos parâmetros
        if isinstance(grid_position, (tuple, list)):
            if not (1 <= grid_position[0] <= grid_position[1] <= 10):
                raise ValueError(f"grid_position range inválido: {grid_position}")
        elif grid_position is not None and not (isinstance(grid_position, int) and 1 <= grid_position <= 10):
            raise ValueError(f"grid_position inválido: {grid_position} (P1-P10 ou None)")
        self.grid_position = grid_position
        self.ghost_hold_ticks = (tuple(ghost_hold_ticks)
                                 if ghost_hold_ticks is not None else None)
        if self.ghost_hold_ticks is not None and n_traffic <= 0:
            self.ghost_hold_ticks = None  # solo: sem fantasmas, hold irrelevante
        if self.ghost_hold_ticks is not None and self.ghost_hold_ticks[1] < self.ghost_hold_ticks[0]:
            raise ValueError("ghost_hold_ticks: (lo, hi) com hi >= lo")
        self.ghost_hold_n = max(1, int(ghost_hold_n))
        self.ghost_sf_range = (tuple(ghost_sf_range)
                                if ghost_sf_range is not None else None)
        if self.ghost_sf_range is not None:
            if not (0.5 <= self.ghost_sf_range[0] <= self.ghost_sf_range[1] <= 1.0):
                raise ValueError(f"ghost_sf_range inválido: {ghost_sf_range}")
            if n_traffic <= 0:
                self.ghost_sf_range = None  # solo: sem fantasmas, sf_range irrelevante
        self.sf_reward = float(sf_reward)
        self._n_obs = OBS_MODES[obs_mode]
        self._grip_override_cfg = grip_override
        self.grip_override = grip_override
        self.grip_random = tuple(grip_random) if grip_random is not None else None
        self.zone_frac = float(zone_frac)
        self._start_zones_cfg = start_zones  # resolvido após as tabelas (abaixo)
        super().__init__()

        # Resolução da pista: dados REAIS via FastF1 (padrão: GP de São Paulo),
        # com fallback para Interlagos e, sem internet/cache, o preset local.
        self.track = resolve_track(
            track=track,
            reference_csv=reference_csv,
            year=f1_year,
            session=f1_session,
            cache_dir=fastf1_cache_dir,
        )

        car_specs = CarSpecs(name="F1 Car", power_kw=735.0, mass_kg=798.0, fuel_capacity_kg=110.0)
        self.driver = Driver(driver_id=driver_id, name=driver_id, car_specs=car_specs, starting_tyre_compound=TyreCompound.MEDIUM)
        # FASE 2 v14: fantasmas são carros físicos completos (colidem, têm
        # inércia) dirigidos pelo professor de tráfego a cada step.
        self._ghost_ids = [f'GHOST{i}' for i in range(self.n_traffic)]
        ghost_drivers = [Driver(driver_id=gid, name=gid, car_specs=car_specs,
                                starting_tyre_compound=TyreCompound.MEDIUM)
                         for gid in self._ghost_ids]
        config = SimulationConfig(
            gui=False,
            logic_step_hz=logic_step_hz,
            physics_sub_steps=physics_sub_steps,
            num_laps=1,
            input_stale_after_s=60.0,  # Sem stale no treinamento
        )
        weather_model = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY])

        self.engine = SimulationEngine(config=config, track=self.track,
                                       drivers=[self.driver] + ghost_drivers,
                                       weather_model=weather_model)
        self.engine.setup()
        # Fantasmas NÃO completam voltas (FASE 2): sem eventos de volta, sem
        # degradação de pneu/combustível (grip nominal) e sem avançar o clima.
        self.engine._no_lap_drivers = set(self._ghost_ids)

        self.driver_id = driver_id
        self.logic_dt = 1.0 / config.logic_step_hz
        self.sub_steps = config.physics_sub_steps

        # IDs de Contexto (fixos para esta instância de ambiente)
        self.track_id_int = track_id
        self.compound_id_int = compound_id

        # Espaço de Ação v2: [steer, longitudinal] ambos em [-1, 1]
        # steer: -1 = roda toda à direita, +1 = à esquerda (após limite por velocidade)
        # longitudinal: >0 = throttle, <0 = brake, ~0 = neutro. Elimina a
        # redundância throttle/brake e as regiões de gradiente zero da exclusão mútua.
        self.action_space = spaces.Box(low=-1.0, high=1.0, shape=(2,), dtype=np.float32)

        # Observação v2 (ver PREVIEW_DISTS acima):
        # base (9): [speed, yaw_rate, g_lat, g_long, lat_err_signed,
        #            sin(heading_err), cos(heading_err), prev_steer, prev_long]
        # preview (2*7=14): por distância d: [delta_heading/pi, kappa_assinada*25]
        self.observation_space = spaces.Dict({
            "telemetry": spaces.Box(low=-OBS_CLIP, high=OBS_CLIP, shape=(self._n_obs,), dtype=np.float32),
            "ctx_numeric": spaces.Box(low=-OBS_CLIP, high=OBS_CLIP, shape=(2,), dtype=np.float32),  # [TyreLife, Fuel]
            "track_id": spaces.Box(low=0, high=20, shape=(1,), dtype=np.int32),
            "compound_id": spaces.Box(low=0, high=5, shape=(1,), dtype=np.int32),
        })

        # Ações anteriores (entram na observação p/ suavizar comandos)
        self._prev_steer = 0.0
        self._prev_long = 0.0

        # Polilinha fechada da pista para projeção: erro lateral real (distância ao
        # segmento, não só ao waypoint) e progresso denso em metros (arc length)
        self._wps_arr = np.array(self.track.waypoints, dtype=np.float64)
        self._seg_B = np.roll(self._wps_arr, -1, axis=0)
        self._seg_AB = self._seg_B - self._wps_arr
        self._seg_len = np.hypot(self._seg_AB[:, 0], self._seg_AB[:, 1])
        self._seg_cum = np.concatenate([[0.0], np.cumsum(self._seg_len)])[:-1]
        self._seg_heading = np.arctan2(self._seg_AB[:, 1], self._seg_AB[:, 0])
        self._track_len_s = float(self._seg_len.sum())
        self._half_width = self.track.width_m / 2.0

        # --- Start/finish AUTOMÁTICO na melhor reta ---------------------------
        # FastF1 às vezes mapeia o start/finish para perto de uma curva (ex.: em
        # Interlagos cai na Descida do Lago). Detectamos a maior reta (menor
        # curvatura à frente) e colocamos a largada no meio dela, garantindo
        # bastante espaço antes da próxima curva.
        # v15 R2 S4: usa a função PURA (fonte única com o runner)
        best_start = find_best_start_waypoint(self.track.waypoints)
        if best_start is not None and best_start != self.track.start_finish_waypoint:
            print(f"[F1MultiContextEnv] Start/finish ajustado do wp "
                  f"{self.track.start_finish_waypoint} -> {best_start} (melhor reta)")
            self.track.start_finish_waypoint = best_start

        # Currículo de largadas: pré-computa a curvatura à frente de cada waypoint
        # e vira peso de amostragem (curva fechada tem ~10x mais chance de start).
        # É o que ensina o agente a NASCER dentro da penúltima curva e sair dela.
        self._start_kappa = np.array(
            [self._kappa_ahead(s, KAPPA_AHEAD_M) for s in self._seg_cum],
            dtype=np.float64,
        )
        knorm = self._start_kappa / max(float(self._start_kappa.max()), 1e-9)
        w = 1.0 + 9.0 * knorm ** 2            # 1x uniforme + 9x viés por curvatura²
        self._start_p = (w / w.sum()).astype(np.float64)

        # --- Percepção de bordas: pré-computa as polilinhas L/R (Fase C v8) ---
        # Borda esquerda = centro + normal*half_width; direita = centro - normal.
        # Usadas pelos raios dos obs_mode 'edge' e 'traffic' (traffic inclui
        # os 11 raios) — sem efeito na física.
        if self.obs_mode in ('edge', 'traffic'):
            norm_x = -np.sin(self._seg_heading)      # normal à esquerda do heading
            norm_y = np.cos(self._seg_heading)
            self._edge_L = np.column_stack([self._wps_arr[:, 0] + norm_x * self._half_width,
                                            self._wps_arr[:, 1] + norm_y * self._half_width])
            self._edge_R = np.column_stack([self._wps_arr[:, 0] - norm_x * self._half_width,
                                            self._wps_arr[:, 1] - norm_y * self._half_width])

        # --- Zonas de aproximação: explícitas ou AUTOMÁTICAS (Fase 4) -------
        # 'auto' detecta as 3 curvas mais fechadas DESTA pista (por geometria —
        # funciona para qualquer circuito, sem coordenadas hardcoded) e cria
        # janelas de 100-300 m antes de cada ápice.
        if self._start_zones_cfg == 'auto':
            zones = []
            n_wp = len(self._wps_arr)
            ks = sorted(((abs(self._kappa_signed(self._seg_cum[i])), float(self._seg_cum[i]))
                         for i in range(0, n_wp, max(1, n_wp // 300))), reverse=True)
            picked = []
            for _k, s_pk in ks:
                if all(min(abs(s_pk - q), self._track_len_s - abs(s_pk - q)) > 400.0
                       for q in picked):
                    picked.append(s_pk)
                if len(picked) >= 3:
                    break
            for s_pk in picked:
                zones.append(((s_pk - 300.0) % self._track_len_s,
                             (s_pk - 100.0) % self._track_len_s))
            self.start_zones = zones
            print(f"[F1MultiContextEnv] zonas auto ({self.track.name}): "
                  f"{[(round(a), round(b)) for a, b in zones]}")
        else:
            self.start_zones = ([(float(a), float(b)) for a, b in self._start_zones_cfg]
                                if self._start_zones_cfg else None)

        # --- Gates de checkpoint ao longo da pista ---
        # Espaçamento adaptativo: mais denso onde a curvatura à frente é alta
        # (curvas fechadas ganham mais "sub-objetivos").
        gates = []
        s = 0.0
        while s < self._track_len_s:
            gates.append(s)
            k = min(float(self._kappa_ahead(s, GATE_SPACING_M)) / max(float(self._start_kappa.max()), 1e-9), 1.0)
            s += GATE_SPACING_M / (1.0 + GATE_CURVATURE_BIAS * k)
        self._gates = np.array(gates, dtype=np.float64)     # posições s dos gates
        self._n_gates = len(self._gates)
        self._next_gate = 0          # índice do próximo gate a cruzar
        self._respawns_left = MAX_RESPAWNS

        self.max_steps = max_steps
        self.random_start_prob = float(random_start_prob)
        self._warned_vel = False
        self._last_wp_idx = self.track.start_finish_waypoint
        self._last_s = 0.0
        self._total_wp_progress = 0.0  # progresso acumulado em metros neste episódio
        self._prog_hist = deque(maxlen=STUCK_WINDOW)
        self.steps = 0

        # --- Fantasmas (FASE 2 v14): professor de TRÁFEGO por carro -------
        # A MESMA camada validada no gate all-professor (FASE 1): cada
        # fantasma vê os outros carros (aluno inclusive) como tráfego.
        # v_plan ÚNICO compartilhado (a passada forward-backward é cara).
        self._ghost_ctrls = {}
        if self._ghost_ids:
            from backend.model_train.reference_controller import ReferenceController
            from backend.model_train.velocity_profile import VelocityProfile
            import zlib
            vp_shared = None
            if self.ghost_sf_range is None:
                vp_shared = VelocityProfile(self._wps_arr, grip_mult=0.788, sf=0.80,
                                             ds_target=4.0, smooth_window_m=20.0)
            for gid in self._ghost_ids:
                if self.ghost_sf_range is not None:
                    lo, hi = self.ghost_sf_range
                    frac = (zlib.crc32(gid.encode()) % 1000) / 1000.0
                    sf_i = lo + (hi - lo) * frac
                    vp_i = VelocityProfile(self._wps_arr, grip_mult=0.788, sf=sf_i,
                                            ds_target=4.0, smooth_window_m=20.0)
                else:
                    vp_i = vp_shared
                self._ghost_ctrls[gid] = ReferenceController(
                    self, velocity_profile=vp_i, driver_id=gid)

    # ------------------------------------------------------------------
    # Mapeamento ação -> comandos. USE ESTE MÉTODO no script de corrida/simulação
    # para o carro se comportar exatamente como no treino.
    # ------------------------------------------------------------------
    @staticmethod
    def steer_limit_rad(speed_mps):
        return max(STEER_MIN_RAD, STEER_MAX_RAD / (1.0 + (speed_mps / STEER_V0) ** 2))

    @classmethod
    def action_to_controls(cls, action, speed_mps):
        """Converte a ação da política em comandos físicos — ÚNICO ponto de conversão.

        v2 (2 dims): [steer, longitudinal] em [-1,1]²
            longitudinal > 0 -> throttle = long;  < 0 -> brake = -long
        Legado (3 dims): [throttle, brake, steer] com exclusão mútua (aceito
        apenas p/ compatibilidade com scripts antigos/modelos v1).

        Retorna (throttle, brake, steer_rad).
        """
        a = np.asarray(action, dtype=np.float64).ravel()
        if a.size >= 3:  # legado
            throttle = float(np.clip(a[0], 0.0, 1.0))
            brake = float(np.clip(a[1], 0.0, 1.0))
            steer = float(np.clip(a[2], -1.0, 1.0))
            if throttle >= brake:
                brake = 0.0
            else:
                throttle = 0.0
        else:
            steer = float(np.clip(a[0], -1.0, 1.0))
            long_cmd = float(np.clip(a[1], -1.0, 1.0))
            throttle = max(long_cmd, 0.0)
            brake = max(-long_cmd, 0.0)
        return throttle, brake, steer * cls.steer_limit_rad(speed_mps)

    # ------------------------------------------------------------------
    def _find_best_start_waypoint(self, min_straight_m=150.0):
        """Acha o waypoint no MEIO da melhor reta para largar.

        Estratégia: encontra todas as retas (zonas de baixa curvatura) e,
        entre as 3 mais longas, escolhe aquela cuja **próxima curva é menos
        fechada** — o carro precisa de espaço para acelerar antes da primeira
        curva de verdade.
        """
        n = len(self._seg_cum)
        kappas = np.array(
            [self._kappa_ahead(self._seg_cum[i], KAPPA_AHEAD_M) for i in range(n)],
            dtype=np.float64,
        )
        kmax = float(kappas.max())
        if kmax <= 0.0:
            return None
        is_straight = kappas < 0.30 * kmax

        segments = []  # (length_m, mid_idx, kappa_ahead_next_300m)
        i = 0
        while i < n:
            if not is_straight[i]:
                i += 1
                continue
            j = i
            while j < n and is_straight[j]:
                j += 1
            length = float(self._seg_cum[min(j, n - 1)] - self._seg_cum[i])
            mid = (i + j - 1) // 2
            # curvatura nos 300 m APÓS o fim da reta (a curva que vem)
            s_end = float(self._seg_cum[min(j, n - 1)])
            k_next = self._kappa_ahead(s_end + 50.0, 250.0)
            segments.append((length, mid, k_next))
            i = j

        if not segments:
            return None

        # pega as 3 mais longas e escolhe a de menor curvatura seguinte
        segments.sort(key=lambda t: -t[0])
        candidates = [s for s in segments if s[0] >= min_straight_m][:3]
        if not candidates:
            return None
        best = min(candidates, key=lambda t: t[2])
        return int(best[1])

    def _project_on_path(self, x, y):
        """Projeta (x, y) na polilinha fechada da pista.

        Retorna (lateral_err, s, seg_idx, signed_err): distância perpendicular ao
        segmento mais próximo, posição em metros ao longo da pista, índice do
        segmento e o erro lateral COM SINAL (+ = carro à esquerda da linha).
        """
        A, AB, L = self._wps_arr, self._seg_AB, self._seg_len
        ap_x = x - A[:, 0]
        ap_y = y - A[:, 1]
        denom = (L * L) + 1e-9
        t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / denom, 0.0, 1.0)
        proj_x = A[:, 0] + t * AB[:, 0]
        proj_y = A[:, 1] + t * AB[:, 1]
        d = np.hypot(proj_x - x, proj_y - y)
        i = int(np.argmin(d))
        s = self._seg_cum[i] + float(t[i]) * L[i]
        # produto vetorial (direção do segmento x vetor projeção->carro): >0 = esquerda
        cross = AB[i, 0] * (y - proj_y[i]) - AB[i, 1] * (x - proj_x[i])
        signed = float(d[i]) if cross >= 0.0 else -float(d[i])
        return float(d[i]), s, i, signed

    def _heading_at(self, s):
        s = s % self._track_len_s
        j = int(np.searchsorted(self._seg_cum, s, side='right') - 1)
        return float(self._seg_heading[min(max(j, 0), len(self._seg_heading) - 1)])

    @staticmethod
    def _wrap(a):
        return (a + math.pi) % (2 * math.pi) - math.pi

    def _point_at(self, s):
        """Posição (x, y) e heading interpolados numa posição s (m) da pista."""
        s = s % self._track_len_s
        j = int(np.searchsorted(self._seg_cum, s, side='right') - 1)
        j = min(max(j, 0), len(self._seg_len) - 1)
        t = (s - self._seg_cum[j]) / max(self._seg_len[j], 1e-9)
        x = self._wps_arr[j, 0] + t * self._seg_AB[j, 0]
        y = self._wps_arr[j, 1] + t * self._seg_AB[j, 1]
        return float(x), float(y), float(self._seg_heading[j])

    def _v_allow_at(self, s, v_now):
        """Velocidade máxima permitida em s (MODELO FÍSICO com downforce).

        FASE 0 Meta C: substitui o A_LAT_MAX=14 fixo por
            a_lat_avail(v) = sf_reward · mu · grip · (g + c_down·v²/m)
        resolvendo v² = mu_s·g / (kappa − mu_s·c_down/m) — a mesma fórmula
        fechada do velocity_profile.py (professor). O downforce dá a_lat
        real de 16–33 m/s² dependendo da velocidade; o fixo 14 PROIBIA o
        ritmo que a Meta C exige (gate min(1, v_allow/v) zerava o prêmio
        de progresso acima do teto conservador).

        sf_reward=0.80 ≈ comportamento legado; 1.00 = física pura.
        Usa o grip DO EPISÓDIO (domain randomization preserva a margem).
        """
        # grip do episódio (override ou realista)
        grip = self.grip_override if self.grip_override is not None else GRIP_REAL
        mu_s = MU_NOMINAL * grip * self.sf_reward
        c_m = C_DOWN / CAR_MASS  # ~0.003684 1/m

        brake_dist = max(0.0, (v_now ** 2 - V_TGT_MIN ** 2)) / (2.0 * A_BRAKE_REF)
        horizon = max(KAPPA_AHEAD_M, v_now * 0.7 + brake_dist + 30.0)
        n = max(2, int(horizon // 10.0) + 1)
        ds = horizon / (n - 1)
        v_allow = V_TGT_MAX
        for i in range(0, n):
            d = i * ds
            kappa = abs(self._kappa_signed(s + d))
            if kappa > 1e-4:
                denom = kappa - mu_s * c_m
                if denom > 1e-6:
                    v_curve = math.sqrt(mu_s * 9.81 / denom)
                else:
                    v_curve = V_TGT_MAX  # downforce segura a curva em qualquer v
                v_allow = min(v_allow, math.sqrt(v_curve ** 2 + 2.0 * A_BRAKE_REF * d))
        return min(V_TGT_MAX, max(V_TGT_MIN, v_allow))

    def _kappa_ahead(self, s, horizon_m=KAPPA_AHEAD_M):
        """Curvatura MÁXIMA local (rad/m) nos próximos `horizon_m` metros.

        Amostra o heading a cada 10 m e toma o maior giro por metro de intervalo
        (não a média do trecho: média diluiria a curva fechada na reta seguinte).
        Usada para v_tgt = sqrt(A_LAT_MAX / kappa) no P_SLOW e no currículo.
        """
        n = max(2, int(horizon_m // 10.0) + 1)
        ds = horizon_m / (n - 1)
        prev_h = self._heading_at(s)
        kappa = 0.0
        for i in range(1, n):
            h = self._heading_at(s + i * ds)
            kappa = max(kappa, abs(self._wrap(h - prev_h)) / ds)
            prev_h = h
        return kappa

    def _kappa_signed(self, s, window_m=KAPPA_WINDOW_M):
        """Curvatura ASSINADA local (rad/m): + = a pista vira à esquerda.

        CORREÇÃO (wrap de ±180°): a diferença central h(s+w)−h(s−w) numa
        janela de 20 m num hairpin de ~180° cruza EXATAMENTE a fronteira do
        wrap — o sinal INVERTE entre pontos adjacentes (medido em Monaco
        s=1015: +0,157; s=1016: −0,156!). O aluno via curva à DIREITA num
        hairpin à ESQUERDA. Fix: acumula diferenças PEQUENAS (~2 m cada,
        sempre <90°) ao longo da janela — a soma preserva o sinal correto
        porque cada passo é muito menor que π.
        """
        n_steps = max(2, int(window_m / 2.0))   # passos de ~2 m
        step = window_m / n_steps
        dh_total = 0.0
        for i in range(n_steps):
            s1 = s - window_m / 2.0 + i * step
            s2 = s - window_m / 2.0 + (i + 1) * step
            dh = self._heading_at(s2) - self._heading_at(s1)
            dh = (dh + math.pi) % (2 * math.pi) - math.pi  # wrap pequeno (<90°)
            dh_total += dh
        return float(dh_total / window_m)

    def _cast_rays(self, x, y, heading):
        """Raios virtuais do carro até as bordas do ASFALTO (Fase C v8).

        Lança N_LIDAR_RAYS raios nos ângulos EDGE_RAY_ANGLES_DEG a partir do
        heading do carro e devolve a distância normalizada [0..1] até a borda
        mais próxima em cada direção (LIDAR_MAX_RANGE_M se não intersecta).

        Os raios medem as POLILINHAS DE BORDA (L/R), não a linha central —
        é percepção de "quanto asfalto me resta nesta direção". Num hairpin,
        o raio frontal encurta ANTES do lat_err crescer: sinal direto de
        "a pista está fechando na minha frente".

        Cada raio é testado contra uma JANELA de segmentos próxima do carro
        (±LIDAR_WINDOW_SEGS), selecionada pela posição s — sem varrer a
        pista toda. Nenhum trecho do lado oposto do circuito interfere
        (a janela é local em s, e raios têm alcance de 40 m).
        """
        if self.obs_mode not in ('edge', 'traffic'):
            return np.array([], dtype=np.float32)
        max_r = LIDAR_MAX_RANGE_M
        n_wp = len(self._wps_arr)
        # janela de segmentos em torno da posição REAL do carro (projeção —
        # robusta mesmo após teleporte, quando _last_s está stale)
        _, s_now, _, _ = self._project_on_path(x, y)
        j0 = int(np.searchsorted(self._seg_cum, s_now, side='right') - 1) % n_wp
        w = LIDAR_WINDOW_SEGS
        idx = np.arange(j0 - w, j0 + w + 1) % n_wp
        idx_n = (idx + 1) % n_wp

        # segmentos das duas bordas: A->B
        LA, LB = self._edge_L[idx], self._edge_L[idx_n]
        RA, RB = self._edge_R[idx], self._edge_R[idx_n]
        # concatena L+R para um único teste vetorial
        A = np.vstack([LA, RA])
        B = np.vstack([LB, RB])

        # pré-computa termos INvariantes entre raios (dependem só de A,B,P)
        ax, ay = A[:, 0], A[:, 1]
        bx, by = B[:, 0], B[:, 1]
        apx = ax - x                          # A - P
        apy = ay - y
        dBAx = bx - ax                        # B - A (direção do segmento)
        dBAy = by - ay
        # termos cruzados pré-computados (verificados com caso simples):
        #   den = cross(D, B-A) = dx*dBAy - dy*dBAx
        #   t   = cross(A-P, B-A) / den = (apx*dBAy - apy*dBAx) / den
        #   u   = cross(A-P, D) / den     = (apx*dy - apy*dx) / den
        #   (fórmula padrão; caso teste: P=(0,0), D=(1,0), A=(5,-1), B=(5,1)
        #    → t=5, u=0.5 ✓)
        cAPBA = apx * dBAy - apy * dBAx       # cross(A-P, B-A) — invariante
        dists = np.empty(N_LIDAR_RAYS, dtype=np.float32)
        for k, ang_deg in enumerate(EDGE_RAY_ANGLES_DEG):
            ang = heading + math.radians(ang_deg)
            dx, dy = math.cos(ang), math.sin(ang)
            den = dx * dBAy - dy * dBAx       # cross(D, B-A)
            t_num = cAPBA                      # cross(A-P, B-A)
            u_num = apx * dy - apy * dx       # cross(A-P, D)
            with np.errstate(divide='ignore', invalid='ignore'):
                t = t_num / den
                u = u_num / den
            valid = (np.abs(den) > 1e-12) & (t > 0.01) & (t < max_r) & (u >= 0.0) & (u <= 1.0)
            d = np.where(valid, t, max_r)
            dists[k] = d.min() if valid.any() else max_r
        return dists / max_r      # normalizado [0..1]

    # ------------------------------------------------------------------
    # TRÁFEGO (FASE 2 v14): snapshot compartilhado, obs e fantasmas
    # ------------------------------------------------------------------
    def _all_cars_snapshot(self):
        """[(driver_id, s, lat_com_sinal, v_mps)] de TODOS os carros físicos
        (aluno + fantasmas), projetados na linha central. Fonte única p/:
        obs 'traffic', decisões dos fantasmas e rótulos do professor (FASE 3).
        """
        out = []
        for drv_id in [self.driver_id] + self._ghost_ids:
            phys = self.engine.physics.get_state(self.engine.handles[drv_id])
            _, s, _, lat_signed = self._project_on_path(phys['x'], phys['y'])
            out.append((drv_id, s, lat_signed, phys['speed_mps']))
        return out

    def traffic_for(self, driver_id):
        """[(s, lat_com_sinal, v)] dos OUTROS carros — o formato exato que
        ReferenceController.action(traffic=...) consome. Usado pelos fantasmas
        (FASE 2) e à disposição do professor do DAgger (FASE 3): o rótulo de
        tráfego sai da MESMA percepção que a política verá na obs.
        """
        return [(s, lat, v) for (d, s, lat, v) in self._all_cars_snapshot()
                if d != driver_id]

    def _traffic_features(self, v_ego, s_ego):
        """12d de tráfego para a obs do aluno — delega à FÓRMULA ÚNICA
        (compute_traffic_features), compartilhada com o race runner neural."""
        others = [(s, lat, v) for (d, s, lat, v) in self._all_cars_snapshot()
                  if d != self.driver_id]
        return compute_traffic_features(v_ego, s_ego, self._half_width,
                                        self._track_len_s, others)

    def _place_traffic_grid(self, s_ego, start_speed):
        """Fantasmas no grid estilo F1 (fileiras de 9 m, colunas alternadas
        ±1,9 m — mesma geometria do place_grid da corrida). FASE 6: o aluno
        ocupa a posição self.grid_position (P1-P10; (lo,hi) sorteia por
        reset — carros ATRÁS entram na distribuição: obs ahead=0) e os
        fantasmas tomam as posições restantes. Velocidade inicial = a do
        aluno. Estado de tráfego dos professores + holds reiniciados.
        """
        spacing, lateral = 9.0, 1.9
        # posição do aluno neste episódio
        if isinstance(self.grid_position, (tuple, list)):
            p_ego = int(self.np_random.integers(self.grid_position[0],
                                                self.grid_position[1] + 1))
        else:
            p_ego = int(self.grid_position)
        # FASE 6: slots ordenados por proximidade (|fileiras|) — o default
        # P10 preenche +9,+18,...,+81 na MESMA ordem da FASE 2; grids médios
        # preenchem simetricamente (±9, ±18, ...): carros atrás desde o 1º.
        posicoes = sorted([p for p in range(1, 11) if p != p_ego],
                          key=lambda p: abs(p_ego - p))
        for k, gid in enumerate(self._ghost_ids):
            p = posicoes[k]                             # posição no grid (P1..P10)
            # FASE 6: slot p fica (p_ego − p) fileiras À FRENTE do aluno
            # (negativo = ATRÁS). p_ego=10 (default) reproduz o mesmo conjunto
            # {9..81 m à frente} — só qual fantasma ocupa qual slot muda.
            s_g = (s_ego + (p_ego - p) * spacing) % self._track_len_s
            side = 1.0 if p % 2 == 1 else -1.0          # P ímpar à esquerda
            gx, gy, gth = self._point_at(s_g)
            nx, ny = -math.sin(gth), math.cos(gth)
            px, py = gx + nx * side * lateral, gy + ny * side * lateral
            self.engine.physics.set_position(self.engine.handles[gid],
                                             (px, py, 0.5), yaw_rad=gth)
            if start_speed > 0.0:
                self._set_forward_speed(gth, start_speed, driver_id=gid)
            st = self.engine.states[gid]
            st.lap = 0
            st.total_time_s = 0
            self.engine.cum_dist_m[gid] = 0.0
            self.engine.lap_start_ts[gid] = 0.0
            self.engine.last_pos[gid] = (px, py)
            if hasattr(self.engine, 'prev_waypoint_idx'):
                _, wp_now = self.track.nearest_segment(px, py)
                self.engine.prev_waypoint_idx[gid] = wp_now
            self._ghost_ctrls[gid]._lat_offset = 0.0     # episódio novo
        # --- FASE 6: sorteio dos HOLDS (fantasmas que param no episódio) ---
        self._ghost_holds = {}
        if self.ghost_hold_ticks is not None and self._ghost_ids:
            lo, hi = self.ghost_hold_ticks
            k = min(self.ghost_hold_n, self.n_traffic)
            for gid in self.np_random.choice(self._ghost_ids, size=k, replace=False):
                start = int(self.np_random.integers(100, 700))
                dur = int(self.np_random.integers(lo, hi + 1))
                self._ghost_holds[gid] = dict(start=start, dur=dur, pose=None)

    def _step_ghosts(self):
        """Uma decisão por fantasma, ANTES do tick, com o professor de
        TRÁFEGO (FASE 1 — o do gate all-professor, não o cego): cada
        fantasma vê aluno + outros fantasmas. GRIP NOMINAL (1.0): fantasmas
        definem o tráfego de referência — sem química de pneu (eles não
        degradam: não completam voltas).
        FASE 6: fantasmas em HOLD congelen na pose (set_position + reset_vel
        a cada tick) em vez de dirigir — carro PARADO na linha p/ os rótulos
        de contorno.
        """
        snap = self._all_cars_snapshot()
        for gid, ctrl in self._ghost_ctrls.items():
            hold = getattr(self, '_ghost_holds', {}).get(gid)
            if hold is not None and hold['start'] <= self.steps < hold['start'] + hold['dur']:
                if hold['pose'] is None:   # congela na pose atual do hold
                    h = self.engine.handles[gid]
                    phys = self.engine.physics.get_state(h)
                    hold['pose'] = ((phys['x'], phys['y'], 0.5), phys['heading_rad'])
                (pos, yaw) = hold['pose']
                self.engine.physics.set_position(self.engine.handles[gid], pos,
                                                 yaw_rad=yaw, reset_vel=True)
                continue
            traffic = [(s, lat, v) for (d, s, lat, v) in snap if d != gid]
            a = ctrl.action(traffic)
            v_g = self.engine.physics.get_state(self.engine.handles[gid])['speed_mps']
            th, brk, steer = self.action_to_controls(a, v_g)
            self.engine.set_driver_input(gid, throttle=th, brake=brk,
                                         steering_yaw_rad=steer,
                                         grip_override=1.0)

    def _get_obs(self):
        handle = self.engine.handles[self.driver_id]
        phys = self.engine.physics.get_state(handle)
        state = self.engine.states[self.driver_id]

        x, y = phys['x'], phys['y']
        lateral_abs, s, idx, lateral_signed = self._project_on_path(x, y)

        tangent = float(self._seg_heading[idx])
        heading_err = self._wrap(phys['heading_rad'] - tangent)

        # Preview geométrico: por distância d, mudança de heading (+ = esquerda)
        # e curvatura assinada. É isso que dá à política a informação "vem curva
        # fechada, preciso frear" ANTES de chegar nela.
        h0 = self._heading_at(s)
        preview = []
        for d in PREVIEW_DISTS:
            preview.append(self._wrap(self._heading_at(s + d) - h0) / math.pi)
            preview.append(self._kappa_signed(s + d) * KAPPA_OBS_SCALE)

        telemetry = np.array([
            phys['speed_mps'] / OBS_SPEED,
            phys['yaw_rate'] / OBS_YAW_RATE,
            phys['g_lat'] / OBS_G,
            phys['g_long'] / OBS_G,
            lateral_signed / self._half_width,
            math.sin(heading_err),
            math.cos(heading_err),
            self._prev_steer,
            self._prev_long,
            *preview,
        ], dtype=np.float32)

        # Contexto numérico dinâmico (Combustível e Vida do Pneu)
        ctx_numeric = np.array([state.tyre.tyre_life / OBS_TYRE_LIFE,
                                state.car.fuel_kg / OBS_FUEL_KG], dtype=np.float32)

        # --- Percepção de bordas (Fase C v8): raios LiDAR ao final ---
        # 'traffic' INCLUI os 11 raios do edge (34d) + 12d de tráfego (46d)
        if self.obs_mode in ('edge', 'traffic'):
            rays = self._cast_rays(phys['x'], phys['y'], phys['heading_rad'])
            telemetry = np.concatenate([telemetry, rays])
        if self.obs_mode == 'traffic':
            telemetry = np.concatenate(
                [telemetry, self._traffic_features(phys['speed_mps'], s)])

        # VALIDAÇÃO DE SHAPE (padrão do projeto — erro explícito, não crash
        # numérico emaciado): o layout da obs é contrato com o ator.
        if telemetry.shape[0] != self._n_obs:
            raise ValueError(
                f"obs_mode='{self.obs_mode}': telemetria com {telemetry.shape[0]} "
                f"dimensões, mas o contrato deste modo é {self._n_obs} "
                f"(base {N_OBS_TELEMETRY} + raios {N_LIDAR_RAYS if self.obs_mode in ('edge', 'traffic') else 0} "
                f"+ tráfego {N_OBS_TRAFFIC if self.obs_mode == 'traffic' else 0}). "
                f"Layout: ver comentário N_TRAFFIC_FEAT em f1_env.py.")

        telemetry = np.clip(np.nan_to_num(telemetry, nan=0.0, posinf=OBS_CLIP, neginf=-OBS_CLIP), -OBS_CLIP, OBS_CLIP)
        ctx_numeric = np.clip(np.nan_to_num(ctx_numeric), -OBS_CLIP, OBS_CLIP)
        return {
            "telemetry": telemetry,
            "ctx_numeric": ctx_numeric,
            "track_id": np.array([self.track_id_int], dtype=np.int32),
            "compound_id": np.array([self.compound_id_int], dtype=np.int32),
        }

    def _set_forward_speed(self, yaw, speed, driver_id=None):
        """Dá velocidade inicial ao chassi (usado nos starts aleatórios e no
        grid dos fantasmas — FASE 2)."""
        try:
            import pybullet as p
            ph = self.engine.physics
            p.resetBaseVelocity(
                self.engine.handles[driver_id or self.driver_id].chassis_id,
                linearVelocity=[speed * math.cos(yaw), speed * math.sin(yaw), 0.0],
                angularVelocity=[0.0, 0.0, 0.0],
                physicsClientId=ph._client_id,
            )
        except Exception as e:  # cai para largada parada
            if not self._warned_vel:
                print(f"[F1MultiContextEnv] não consegui setar velocidade inicial ({e}); largada parada.")
                self._warned_vel = True

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        # Domain randomization de aderência (currículo): sorteia grip por episódio
        if self.grip_random is not None:
            lo, hi = self.grip_random
            self.grip_override = float(self.np_random.uniform(lo, hi))
        self.engine.sim_ts = 0.0
        self.engine.current_lap = 0
        self.engine.race_started = True
        self.engine.race_finished = False

        state = self.engine.states[self.driver_id]
        state.lap = 0
        state.total_time_s = 0
        self.engine.cum_dist_m[self.driver_id] = 0.0
        self.engine.lap_start_ts[self.driver_id] = 0.0

        start_speed = 0.0
        if self.random_start_prob > 0.0 and self.np_random.random() < self.random_start_prob:
            use_zone = (self.start_zones is not None
                        and self.np_random.random() < self.zone_frac)
            if use_zone:
                # ---- Currículo de APROXIMAÇÃO (Fase D v5) ------------------
                # Nasce 100-300 m ANTES de uma curva crítica, com velocidade
                # abaixo/próxima/acima da segura — a política aprende a FREAR
                # ATÉ a velocidade da curva (v4 freava até ~0: nunca viu
                # aproximações, só kinks onde parar era racional).
                s_lo, s_hi = self.start_zones[int(self.np_random.integers(0, len(self.start_zones)))]
                s0 = float(self.np_random.uniform(s_lo, s_hi)) % self._track_len_s
                # velocidade segura da curva à frente (distância de frenagem)
                v_allow = self._v_allow_at(s0, V_TGT_MAX)
                # entrada: 0.5–1.15 × v_allow (devagar/adequado/levemente acima —
                # acima DIANTE da distância de frenagem disponível seria crash
                # garantido: 1.15² ≈ 1.32× a distância de frenagem, ensinável)
                start_speed = float(np.clip(self.np_random.uniform(0.5, 1.15) * v_allow,
                                            0.0, V_TGT_MAX))
                j = int(np.searchsorted(self._seg_cum, s0, side='right') - 1)
                j = min(max(j, 0), len(self._wps_arr) - 1)
                yaw = float(self._seg_heading[j])
                lat_j = float(self.np_random.uniform(-0.3, 0.3)) * self._half_width
                hdg_j = float(self.np_random.uniform(-0.08, 0.08))
                nx, ny = -math.sin(yaw), math.cos(yaw)
                px = float(self._wps_arr[j, 0]) + nx * lat_j
                py = float(self._wps_arr[j, 1]) + ny * lat_j
                yaw = float(self._wrap(yaw + hdg_j))
            else:
                # Currículo original: 50% uniformes + 50% viés de curvatura
                if self.np_random.random() < 0.5:
                    k = int(self.np_random.integers(0, len(self._wps_arr)))
                else:
                    k = int(self.np_random.choice(len(self._wps_arr), p=self._start_p))
                yaw = float(self._seg_heading[k])
                # jitter lateral (±35% da meia-largura) p/ não decorar só a linha central
                lat_j = float(self.np_random.uniform(-0.35, 0.35)) * self._half_width
                nx, ny = -math.sin(yaw), math.cos(yaw)          # normal à esquerda do heading
                px = float(self._wps_arr[k, 0]) + nx * lat_j
                py = float(self._wps_arr[k, 1]) + ny * lat_j
                kappa_now = max(float(self._start_kappa[k]), 1e-4)
                v_entry = min(math.sqrt(A_LAT_MAX / kappa_now), V_TGT_MAX)   # vel. da curva dali
                start_speed = float(self.np_random.uniform(0.0, 1.05) * v_entry)
        else:
            # Posição de largada: usa o start_finish WAYPOINT (meio da melhor reta),
            # NÃO o grid do FastF1 (que pode estar colado na primeira curva).
            sf_idx = self.track.start_finish_waypoint
            px, py = float(self._wps_arr[sf_idx, 0]), float(self._wps_arr[sf_idx, 1])
            yaw = float(self._seg_heading[sf_idx])
            # Se a próxima curva está muito perto (<100m), dá uma velocidade
            # inicial compatível com ela — evita que o agente tenha que decidir
            # "acelerar + frear" em menos de 2 segundos.
            _, s_sf, _, _ = self._project_on_path(px, py)
            kappa_next = self._kappa_ahead(s_sf, 100.0)
            if kappa_next > 0.015:  # curva mais fechada que raio ~65m à frente
                start_speed = min(V_TGT_MIN * 0.8, math.sqrt(A_LAT_MAX / max(kappa_next, 1e-4)))
        self.engine.physics.set_position(self.engine.handles[self.driver_id], (px, py, 0.5), yaw_rad=yaw)
        if start_speed > 0.0:
            self._set_forward_speed(yaw, start_speed)
        # evita que o "salto" de teleporte seja contado como distância percorrida
        if hasattr(self.engine, "last_pos"):
            self.engine.last_pos[self.driver_id] = (px, py)
        # CORREÇÃO (bug da parede do wrap): ressincroniza o hint de waypoint
        # da engine após o teleporte — o grip usa a distância à linha central
        # via janela em torno desse hint; stale => fator de grama no asfalto.
        if hasattr(self.engine, "prev_waypoint_idx"):
            _, wp_now = self.track.nearest_segment(px, py)
            self.engine.prev_waypoint_idx[self.driver_id] = wp_now

        # FASE 2 v14: fantasmas no grid à frente do aluno (novo episódio —
        # reposicionados a CADA reset, ancorados à largada atual do aluno)
        if self._ghost_ids:
            _, s_start, _, _ = self._project_on_path(px, py)
            self._place_traffic_grid(s_start, start_speed)

        self.steps = 0
        _, self._last_s, self._last_wp_idx, _ = self._project_on_path(px, py)
        self._total_wp_progress = 0.0
        self._prog_hist.clear()
        self._prev_steer = 0.0
        self._prev_long = 0.0
        # Gates: o próximo gate é o primeiro À FRENTE do ponto de largada;
        # respawns restaurados por episódio.
        self._next_gate = int(np.searchsorted(self._gates, self._last_s, side='right') % self._n_gates)
        self._respawns_left = MAX_RESPAWNS
        return self._get_obs(), {}

    # ------------------------------------------------------------------
    def _respawn_at_last_gate(self):
        """Reposiciona o carro no último gate já cruzado (estilo jogo de corrida).

        Volta rolando devagar para não disparar a regra de "stuck" logo em
        seguida, e alinha os contadores de progresso para o teleporte não ser
        contado como distância percorrida.
        """
        last = (self._next_gate - 1) % self._n_gates
        s = float(self._gates[last])
        x, y, yaw = self._point_at(s)
        self.engine.physics.set_position(self.engine.handles[self.driver_id], (x, y, 0.5), yaw_rad=yaw)
        self._set_forward_speed(yaw, RESPAWN_SPEED_MPS)
        if hasattr(self.engine, "last_pos"):
            self.engine.last_pos[self.driver_id] = (x, y)
        self._last_s = s
        self._prog_hist.clear()

    def step(self, action):
        handle = self.engine.handles[self.driver_id]
        speed_before = self.engine.physics.get_state(handle)['speed_mps']
        throttle, brake, steer_rad = self.action_to_controls(action, speed_before)
        a = np.asarray(action, dtype=np.float64).ravel()
        if a.size >= 3:   # legado v1
            self._prev_long = float(np.clip(a[0], 0, 1) - np.clip(a[1], 0, 1))
            self._prev_steer = float(np.clip(a[2], -1, 1))
        else:
            self._prev_steer = float(np.clip(a[0], -1, 1))
            self._prev_long = float(np.clip(a[1], -1, 1))
        # FASE 2 v14: fantasmas decidem ANTES do tick (mesmo tick físico
        # avança aluno + fantasmas; a obs retornada é do estado PÓS-tick)
        if self._ghost_ctrls:
            self._step_ghosts()
        self.engine.set_driver_input(
            self.driver_id,
            throttle=throttle,
            brake=brake,
            steering_yaw_rad=steer_rad,
            grip_override=self.grip_override,
        )
        self.engine._step_tick(self.logic_dt, self.sub_steps)
        self.steps += 1

        obs = self._get_obs()
        phys = self.engine.physics.get_state(handle)

        speed = phys['speed_mps']
        x, y = phys['x'], phys['y']
        lateral_err, cur_s, cur_wp, _ = self._project_on_path(x, y)
        tangent = float(self._seg_heading[cur_wp])
        heading_err = self._wrap(phys['heading_rad'] - tangent)

        # --- Progresso DENSO em metros ao longo da linha de referência ---
        old_s = self._last_s
        progress = cur_s - old_s
        if progress < -self._track_len_s / 2.0:      # wrapping da pista fechada
            progress += self._track_len_s
        elif progress > self._track_len_s / 2.0:
            progress -= self._track_len_s
        if abs(progress) > 50.0:                     # teleporte / erro numérico
            progress = 0.0
        self._last_s = cur_s
        self._last_wp_idx = cur_wp
        if progress > 0:
            self._total_wp_progress += progress
        self._prog_hist.append(progress)

        # --- Recompensa (componentes registrados separadamente) ---
        parts = {"progress": R_PROGRESS * progress,
                 "gate": 0.0, "offtrack": -P_OFFTRACK * max(0.0, lateral_err - self._half_width),
                 "center": -P_CENTER * (lateral_err / self._half_width) ** 2,
                 "heading": -P_HEADING * abs(heading_err),
                 "slow": 0.0, "fast": 0.0, "respawn": 0.0, "terminal": 0.0}

        # --- Bônus por cruzar gates de checkpoint (pequenas conquistas) ---
        gates_passed = 0
        if progress > 0:
            moved = progress
            while gates_passed < self._n_gates:
                dg = (self._gates[self._next_gate] - old_s) % self._track_len_s
                if dg <= moved and dg < self._track_len_s / 2.0:
                    gates_passed += 1
                    self._next_gate = (self._next_gate + 1) % self._n_gates
                else:
                    break
        parts["gate"] = R_GATE * gates_passed

        # --- Velocidade segura pela DISTÂNCIA DE FRENAGEM (ver _v_allow_at) ---
        # v_allow: a maior velocidade atual tal que ainda dá p/ frear até a
        # velocidade de cada curva no horizonte. Se a política excede, o prêmio
        # de progresso é modulado por min(1, v_allow/v) — "ir mais rápido do que
        # dá para frear" deixa de pagar, removendo o incentivo raiz do crash.
        v_allow = self._v_allow_at(cur_s, speed)
        parts["progress"] *= min(1.0, v_allow / max(speed, 1e-3))
        if speed < SLOW_FRAC * min(v_allow, V_TGT_MAX):
            v_tgt_s = min(v_allow, V_TGT_MAX)
            parts["slow"] = -P_SLOW * (SLOW_FRAC * v_tgt_s - speed) / v_tgt_s
        elif speed > FAST_FRAC * v_allow:
            parts["fast"] = -P_FAST * (speed - FAST_FRAC * v_allow) / v_allow

        terminated = False
        truncated = False
        completed_lap = False

        if not np.isfinite(speed) or not np.isfinite(x) or not np.isfinite(y):
            parts["terminal"] = -P_CRASH
            terminated = True                                                    # física explodiu
        elif lateral_err > self._half_width * 1.3:                             # saiu da pista
            if self.allow_respawn and self._respawns_left > 0:
                self._respawns_left -= 1
                parts["respawn"] = -P_RESPAWN
                self._respawn_at_last_gate()
            else:
                parts["terminal"] = -P_CRASH
                terminated = True
        elif (len(self._prog_hist) == STUCK_WINDOW
              and sum(self._prog_hist) < STUCK_MIN_PROGRESS_M):                # parado / girando / de ré
            parts["terminal"] = -P_STUCK
            terminated = True

        # Volta válida: o contador da engine E o progresso acumulado confirmam
        # uma volta completa (respawn não pode gerar volta fictícia).
        if self.engine.states[self.driver_id].lap >= 1 \
                and self._total_wp_progress >= 0.98 * self._track_len_s:
            terminated = True
            completed_lap = True
            parts["terminal"] = R_LAP
        if not terminated and self.steps >= self.max_steps:
            truncated = True

        reward = sum(parts.values())
        info = {"lat": float(lateral_err), "speed": float(speed),
                "progress_m": float(self._total_wp_progress),
                "gate": int(self._next_gate), "n_gates": self._n_gates,
                "respawns_left": int(self._respawns_left),
                "grip": float(self.grip_override) if self.grip_override is not None else -1.0,
                "completed_lap": completed_lap,
                "reward_parts": parts}
        return obs, float(reward), terminated, truncated, info

    def close(self):
        if hasattr(self, 'engine') and self.engine is not None and hasattr(self.engine, 'physics'):
            self.engine.physics.close()

# --- v15 FASE R: fonte de pista FROZEN (fail-fast, sem fallback) -----------
# Regra do incidente 9099235: FastF1 é OPCIONAL (só nomes/cores); a geometria
# vem SEMPRE da pista congelada quando disponível. Fallback silencioso para
# preset procedural ("último recurso") é PROIBIDO no runner — pista errada
# = carros burros + largada em cima da curva. Se a frozen não existe ou o
# hash diverge: ERRO DURO + aborto.

FROZEN_TRACKS_DIR = MODEL_DIR / 'tracks_frozen'


def load_track_frozen(name: str, strict: bool = True):
    """Carrega a pista congelada v1 pelo nome. VERIFICA sha256.

    Args:
      name: alias amigável (interlagos, Monza, ...) — resolve o arquivo
            <name>_v1.json em tracks_frozen/.
      strict: se True (runner) — hash errado ou arquivo ausente = ERRO.
              se False — retorna None silenciosamente (para uso opcional).

    NUNCA faz fallback: se não tem frozen, o chamador decide (o runner
    deve abortar; scripts de investigação podem usar resolve_track).
    """
    import hashlib
    import json as _json
    alias = name.strip().lower()
    _alias_map = {
        'interlagos': 'interlagos', 'são paulo': 'interlagos',
        'sao paulo': 'interlagos', 'sao-paulo': 'interlagos',
        'brazil': 'interlagos', 'default': 'interlagos', 'none': 'interlagos',
    }
    key = _alias_map.get(alias, name.strip())
    # v15 R2 S4: v2 (SF corrigido) tem prioridade sobre v1 (SF original)
    path = FROZEN_TRACKS_DIR / f'{key}_v2.json'
    if not path.exists():
        path = FROZEN_TRACKS_DIR / f'{key}_v1.json'
    if not path.exists():
        if strict:
            raise FileNotFoundError(
                f"PISTA FROZEN AUSENTE: {path}. O runner REJEITA corridas em "
                f"pistas não congeladas (incidente 9099235: fallback silencioso "
                f"para preset procedural produziu carros burros). Congele a "
                f"pista primeiro ou use --track com uma frozen existente.")
        return None
    data = _json.loads(path.read_text())
    # verifica sha256 do conteúdo ORIGINAL (sem o campo sha256 em si)
    data_check = {k: v for k, v in data.items() if k != 'sha256'}
    raw = _json.dumps(data_check, sort_keys=True).encode()
    actual = hashlib.sha256(raw).hexdigest()[:16]
    if actual != data['sha256']:
        if strict:
            raise ValueError(
                f"PISTA FROZEN CORROMPIDA: {path.name} sha256 esperado "
                f"{data['sha256']} mas calculado {actual}. ABORTO — pista "
                f"adulterada.")
        return None
    wps = [(float(x), float(y)) for x, y in data['waypoints']]
    from backend.domain import Track
    t = Track.from_waypoints(
        name=data['name'],
        waypoints=wps,
        width_m=float(data.get('width_m', 12.0)),
    )
    # v15 R2 S6: o sf_idx do ARQUIVO FROZEN é AUTORITATIVO. A função pura
    # find_best_start_waypoint foi a FERRAMENTA que gerou o valor de v2
    # (registrado em sf_method no json); no load, o json é a fonte única.
    # O override em runtime (herança do FASE R) fez B3.1-v2 ignorar o
    # sf_idx do arquivo e rodar SEMPRE com a função pura — medido:
    # SF 929 (sweeper) = largada VERMELHA (1352 contatos, 68% fora);
    # toda a base verde (B3.1 223, v14, B3.3c) foi medida com SF 729.
    t.start_finish_waypoint = int(data['sf_idx'])
    # v15 R5a: sha256 do arquivo frozen visível ao runner (FONTE em todo log)
    t.frozen_sha256 = str(data['sha256'])
    return t


# ============================================================================
# v15 FASE R2 S1: função PURA de ajuste de SF (fonte única para env+runner)
# ============================================================================

def find_best_start_waypoint(waypoints, min_straight_m=150.0):
    """Acha o waypoint no MEIO da melhor reta para a largada/chegada.

    EXTRAÇÃO DO ENV (FASE R2 S1): o mesmo algoritmo de
    F1MultiContextEnv._find_best_start_waypoint, mas como FUNÇÃO PURA que
    recebe apenas os waypoints — sem estado de env, sem tabelas internas.
    É a FONTE ÚNICA: o env chama esta função no construtor, e o
    load_track_frozen também chama (nunca mais divergem).

    Estratégia: encontra todas as retas (zonas de baixa curvatura à frente
    no horizonte KAPPA_AHEAD_M=150) e, entre as 3 mais longas, escolhe a
    cuja próxima curva é menos fechada.

    Args:
      waypoints: lista [(x, y)] ou array (N, 2) — polilinha FECHADA.
      min_straight_m: comprimento mínimo da reta candidata (150 m).

    Returns:
      int: índice do waypoint no MEIO da melhor reta.
    """
    import math as _math
    wps = np.asarray(waypoints, dtype=np.float64)
    n = len(wps)
    if n < 3:
        return 0

    d = np.roll(wps, -1, axis=0) - wps
    seg = np.hypot(d[:, 0], d[:, 1])
    cum = np.concatenate([[0.0], np.cumsum(seg)])[:-1]
    total = float(seg.sum())
    heading = np.arctan2(d[:, 1], d[:, 0])

    KAPPA_AHEAD_M = 150.0

    def _heading_at(s_val):
        s_val = s_val % total
        j = int(np.searchsorted(cum, s_val, side='right') - 1)
        return float(heading[min(max(j, 0), n - 1)])

    def _kappa_ahead(s_val, horizon_m):
        ns = max(2, int(horizon_m // 10.0) + 1)
        ds = horizon_m / (ns - 1)
        prev_h = _heading_at(s_val)
        k = 0.0
        for kk in range(1, ns):
            h = _heading_at(s_val + kk * ds)
            k = max(k, abs((h - prev_h + _math.pi) % (2 * _math.pi) - _math.pi) / ds)
            prev_h = h
        return k

    kappas = np.array([_kappa_ahead(float(cum[i]), KAPPA_AHEAD_M)
                       for i in range(n)], dtype=np.float64)
    kmax = float(kappas.max())
    if kmax <= 0.0:
        return 0
    is_straight = kappas < 0.30 * kmax

    segments = []
    i = 0
    while i < n:
        if not is_straight[i]:
            i += 1
            continue
        j = i
        while j < n and is_straight[j]:
            j += 1
        length = float(cum[min(j, n - 1)] - cum[i])
        mid = (i + j - 1) // 2
        s_end = float(cum[min(j, n - 1)])
        k_next = _kappa_ahead(s_end + 50.0, 250.0)
        segments.append((length, mid, k_next))
        i = j

    if not segments:
        return 0
    segments.sort(key=lambda t: -t[0])
    candidates = [s for s in segments if s[0] >= min_straight_m][:3]
    if not candidates:
        return 0
    best = min(candidates, key=lambda t: t[2])
    return int(best[1])
