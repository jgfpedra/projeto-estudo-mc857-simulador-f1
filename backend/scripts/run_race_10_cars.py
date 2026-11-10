#!/usr/bin/env python3
"""Corrida de Fórmula 1 com 10 carros no PyBullet.

Inicia uma simulação completa com 10 carros no grid de largada, interface 3D
do PyBullet com asfalto renderizado, câmera dinâmica (Overview / Follow),
rótulos de telemetria 3D sobre os carros e controle autônomo dos 10 pilotos
por profile (regras Apex Formula por padrão ou modelos neurais).

O profile padrão funciona só com regras e não precisa de checkpoint. Os profiles
neurais usam o motor NumPy com pesos compilados para evitar conflitos entre
TensorFlow e OpenGL do PyBullet.

Uso:
    python backend/scripts/run_race_10_cars.py --laps 5 --realtime
    python backend/scripts/run_race_10_cars.py --profile race  # profile neural
    python backend/scripts/run_race_10_cars.py --camera follow --follow-driver VER
    python backend/scripts/run_race_10_cars.py --camera overview
"""

from __future__ import annotations

import argparse
import math
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import joblib

# Garante inclusão da raiz do projeto e de backend no sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BACKEND_DIR = PROJECT_ROOT / "backend"
# CORREÇÃO (investigação v2-vs-v4): era `BACKEND_DIR / "model_train" / "v2"` —
# hardcoded em v2! Isso fazia o DEFAULT da corrida carregar SEMPRE o ator v2
# (v3/v4 nunca eram candidatos) e quebrava silenciosamente os caminhos de
# supporte (mappings.pkl, scaler_*.pkl vivem na RAIZ de model_train, não em v2/).
MODEL_DIR = BACKEND_DIR / "model_train"

for p_dir in [str(PROJECT_ROOT), str(BACKEND_DIR), str(MODEL_DIR)]:
    if p_dir not in sys.path:
        sys.path.insert(0, p_dir)

# Auto-detect project virtualenv se executado com python do sistema
VENV_DIR = BACKEND_DIR / ".venv"
VENV_PYTHON = VENV_DIR / "bin" / "python"
if sys.prefix != str(VENV_DIR) and VENV_PYTHON.exists():
    try:
        import pybullet
    except ImportError:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON)] + sys.argv)

import pybullet as p

from backend.domain import (
    CarSpecs,
    Driver,
    Track,
    TyreCompound,
    WeatherModel,
    WeatherKind,
    BASE_CONDITIONS,
)
from backend.model_train.f1_env import resolve_track
from backend.engine import SimulationEngine, SimulationConfig, CarInput

# --- PROFILES de deploy (FASE 4 v14): o default antigo escolhia o ator por
# MTIME — com 3 checkpoints candidatos (v10/v11b/v14) ele carregaria
# arbitrariamente o mais recente. Substituído por --profile EXPLÍCITO.
PROFILES = {
    "apex-rules": dict(
        controller="apex-rules",
        desc="pure pursuit, frenagem por horizonte, tráfego e variação semeada",
    ),
    # v15 FASE 4b: PROMOÇÃO APLICADA — race default = composite (B3.1 verde)
    "race": dict(
        keras=MODEL_DIR / "v10_dagger" / "dagger_actor_best.keras",
        residual_npz=MODEL_DIR / "v15_residual" / "residual_best_weights.npz",
        obs_mode="traffic",
        desc="v15 composite r2 — solo v10 congelado + residual gated "
             "(PROMOVIDO: B3.1 223 cont/0 pós-larg/103,4s/0 hesit/0,17% fora)"),
    "race-blind": dict(
        keras=MODEL_DIR / "v10_dagger" / "dagger_actor_best.keras",
        obs_mode="edge",
        desc="v10 DAgger sf=0,80 — cego a tráfego (o antigo 'race')"),
    "composite": dict(
        keras=MODEL_DIR / "v10_dagger" / "dagger_actor_best.keras",
        residual_npz=MODEL_DIR / "v15_residual" / "residual_best_weights.npz",
        obs_mode="traffic",
        desc="alias para race (= composite)"),
    "quali": dict(
        keras=MODEL_DIR / "v11b_pace90" / "dagger_actor_best.keras",
        obs_mode="edge",
        desc="v11b DAgger sf=0,90 — pace máximo (quali; Suzuka 2/3)"),
    "traffic": dict(
        # FASE 5 (v15): alinhado à declaração final de produto — o iter8 em par/
        # all-neural é PROIBIDO (1691 contatos); o iter3 é o cidadão validado
        # no campo misto (1406 < controle 1820). Eval denso (fantasmas): iter8.
        keras=MODEL_DIR / "v14_traffic" / "dagger_actor_best_s1_n4.keras",
        obs_mode="traffic",
        desc="v14 iter3 — obs de tráfego 60d (campo misto condicional; ver PROJECT_STATE.md)"),
}
# O profile de regras é o padrão da simulação visual de 10 carros; os profiles
# neurais seguem disponíveis explicitamente via --profile race|quali|traffic.
DEFAULT_PROFILE = "apex-rules"
DEFAULT_MAPPINGS_PATH = MODEL_DIR / "mappings.pkl"
DEFAULT_SCALER_Y_PATH = MODEL_DIR / "scaler_y_multi.pkl"

# Definição dos 10 pilotos e cores características de suas equipes na F1
GRID_DRIVERS_CONFIG = [
    {
        "id": "VER",
        "name": "Max Verstappen",
        "team": "Red Bull Racing",
        "color": (0.08, 0.16, 0.55, 1.0),      # Azul Red Bull
        "label_color": [0.2, 0.4, 1.0],
        "compound": TyreCompound.SOFT,
    },
    {
        "id": "NOR",
        "name": "Lando Norris",
        "team": "McLaren",
        "color": (1.0, 0.50, 0.0, 1.0),        # Laranja Papaya McLaren
        "label_color": [1.0, 0.6, 0.1],
        "compound": TyreCompound.MEDIUM,
    },
    {
        "id": "LEC",
        "name": "Charles Leclerc",
        "team": "Ferrari",
        "color": (0.90, 0.05, 0.05, 1.0),      # Vermelho Ferrari
        "label_color": [1.0, 0.1, 0.1],
        "compound": TyreCompound.SOFT,
    },
    {
        "id": "HAM",
        "name": "Lewis Hamilton",
        "team": "Mercedes",
        "color": (0.0, 0.85, 0.82, 1.0),       # Ciano Petronas / Mercedes
        "label_color": [0.0, 0.9, 0.9],
        "compound": TyreCompound.MEDIUM,
    },
    {
        "id": "PIA",
        "name": "Oscar Piastri",
        "team": "McLaren",
        "color": (0.95, 0.70, 0.0, 1.0),       # Papaya Claro
        "label_color": [1.0, 0.8, 0.1],
        "compound": TyreCompound.MEDIUM,
    },
    {
        "id": "RUS",
        "name": "George Russell",
        "team": "Mercedes",
        "color": (0.75, 0.80, 0.85, 1.0),      # Prata Mercedes
        "label_color": [0.8, 0.85, 0.9],
        "compound": TyreCompound.SOFT,
    },
    {
        "id": "SAI",
        "name": "Carlos Sainz",
        "team": "Ferrari",
        "color": (0.65, 0.02, 0.02, 1.0),      # Vermelho Escuro
        "label_color": [0.8, 0.2, 0.2],
        "compound": TyreCompound.MEDIUM,
    },
    {
        "id": "PER",
        "name": "Sergio Perez",
        "team": "Red Bull Racing",
        "color": (0.05, 0.10, 0.35, 1.0),      # Azul Marinho
        "label_color": [0.1, 0.3, 0.7],
        "compound": TyreCompound.HARD,
    },
    {
        "id": "ALO",
        "name": "Fernando Alonso",
        "team": "Aston Martin",
        "color": (0.0, 0.45, 0.30, 1.0),       # Verde Aston Martin
        "label_color": [0.1, 0.8, 0.4],
        "compound": TyreCompound.HARD,
    },
    {
        "id": "GAS",
        "name": "Pierre Gasly",
        "team": "Alpine",
        "color": (0.15, 0.50, 0.90, 1.0),      # Azul Alpine
        "label_color": [0.3, 0.7, 1.0],
        "compound": TyreCompound.MEDIUM,
    },
]


def ensure_npz_weights_exist(keras_path: Path, npz_path: Path) -> Path:
    """Extrai pesos do modelo Keras para formato NPZ semântico via subprocesso isolado se necessário."""
    need_export = False
    if not npz_path.exists():
        need_export = True
    elif keras_path.exists() and keras_path.stat().st_mtime > npz_path.stat().st_mtime:
        need_export = True

    if not need_export:
        return npz_path

    print(f"[Model] Exportando pesos de {keras_path} para formato NPZ otimizado...")
    py_exec = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable
    code = f"""
import tensorflow as tf, numpy as np
model = tf.keras.models.load_model(r'{keras_path}', compile=False)
weights = {{}}
for layer in model.layers:
    w = layer.get_weights()
    if w:
        for idx, arr in enumerate(w):
            weights[f'{{layer.name}}_{{idx}}'] = arr
np.savez(r'{npz_path}', **weights)
print('Pesos extraidos com sucesso.')
"""
    subprocess.check_call([py_exec, "-c", code])
    return npz_path


class NumpyNeuralActor:
    """Implementação em NumPy puro do Actor Multi-Contexto.

    Inferencia em lote ultrarrápida e 100% livre de colisões com os drivers
    gráficos OpenGL do Mesa/radeonsi no PyBullet GUI.
    """

    def __init__(self, npz_path: Path):
        data = np.load(str(npz_path))
        
        # Resolução flexível de pesos por shape para suportar qualquer convenção de nomes de camadas do Keras
        w1, b1, w2, b2, w3, b3, w4, b4, w5, b5 = None, None, None, None, None, None, None, None, None, None
        embs_20_8 = []
        emb_cmp = None

        for k in data.keys():
            arr = data[k]
            s = arr.shape
            if len(s) == 2 and s[1] == 256: w1 = arr  # 1a densa: entrada variavel (24) -> 256
            elif s == (256,): b1 = arr
            elif s == (256, 128): w2 = arr
            elif s == (128,): b2 = arr
            elif s == (128, 64): w3 = arr
            elif s == (64,): b3 = arr
            elif s == (64, 32): w4 = arr
            elif s == (32,): b4 = arr
            elif s == (32, 3): w5 = arr      # saída v1: [throttle, brake, steer]
            elif s == (3,): b5 = arr
            elif s == (32, 2): w5 = arr      # saída v2: [steer, longitudinal]
            elif s == (2,): b5 = arr
            elif s == (20, 8): embs_20_8.append(arr)
            elif s == (5, 4): emb_cmp = arr

        missing = [n for n, w in zip(
            ["w1", "b1", "w2", "b2", "w3", "b3", "w4", "b4", "w5", "b5"],
            [w1, b1, w2, b2, w3, b3, w4, b4, w5, b5],
        ) if w is None]
        if missing:
            raise ValueError(
                f"Pesos nao encontrados no NPZ ({npz_path.name}): {missing}. "
                f"Shapes disponiveis: {[d.shape for d in data.values()]}"
            )

        self.w1 = w1
        self.b1 = b1
        self.w2 = w2
        self.b2 = b2
        self.w3 = w3
        self.b3 = b3
        self.w4 = w4
        self.b4 = b4
        self.w5 = w5
        self.b5 = b5
        self.act_dim = int(w5.shape[1])            # 3 = política v1, 2 = v2
        # dimensão de entrada da 1ª densa: tel(13 ou 23) + ctx(2) + emb(8) + emb(4)
        self.input_dim = int(w1.shape[0])

        self.emb_trk = embs_20_8[0] if len(embs_20_8) > 0 else np.zeros((20, 8), dtype=np.float32)
        self.emb_cmp = emb_cmp if emb_cmp is not None else np.zeros((5, 4), dtype=np.float32)

    def forward(
        self,
        telemetry: np.ndarray,
        ctx_numeric: np.ndarray,
        track_ids: np.ndarray,
        compound_ids: np.ndarray,
    ) -> np.ndarray:
        """Forward pass em lote: retorna as ações da política (tanh [-1, 1]).

        O modelo é geral (sem embedding de piloto); o clip para os limites
        físicos de throttle/brake é feito em predict_batch.
        """
        et = self.emb_trk[track_ids]
        ec = self.emb_cmp[compound_ids]

        concat = np.concatenate([telemetry, ctx_numeric, et, ec], axis=-1)
        if concat.shape[-1] != self.w1.shape[0]:
            raise ValueError(
                f"Observação incompatível com o NPZ: concat tem {concat.shape[-1]} dims "
                f"(telemetria {telemetry.shape[-1]} + ctx 2 + emb 12), mas a 1ª camada densa "
                f"espera {self.w1.shape[0]}. Provavelmente o NPZ foi exportado de um modelo "
                f"com outra versão de observação (v1: tel 13 -> entrada 27; v2: tel 23 -> 37). "
                f"Re-exporte com ensure_npz_weights_exist a partir do checkpoint desejado."
            )

        x = np.maximum(0.0, concat @ self.w1 + self.b1)
        x = np.maximum(0.0, x @ self.w2 + self.b2)
        x = np.maximum(0.0, x @ self.w3 + self.b3)
        x = np.maximum(0.0, x @ self.w4 + self.b4)
        out = np.tanh(x @ self.w5 + self.b5)
        return out

    def forward_linear(self, telemetry, ctx_numeric, track_ids, compound_ids):
        """Média LINEAR (PRÉ-tanh) — v15 FASE 3: o composite precisa do
        m_solo cru, NÃO do atanh(tanh(m)); atanh explode em float32 quando
        tanh(m) satura em ±0,999 (retas longas)."""
        et = self.emb_trk[track_ids]
        ec = self.emb_cmp[compound_ids]
        concat = np.concatenate([telemetry, ctx_numeric, et, ec], axis=-1)
        x = np.maximum(0.0, concat @ self.w1 + self.b1)
        x = np.maximum(0.0, x @ self.w2 + self.b2)
        x = np.maximum(0.0, x @ self.w3 + self.b3)
        x = np.maximum(0.0, x @ self.w4 + self.b4)
        return x @ self.w5 + self.b5   # LINEAR, sem tanh


class ProjectionAnchorGate:
    """Keeps the last on-track projection and freezes one rejoin target."""

    def __init__(self) -> None:
        self._anchors: Dict[str, Dict[str, Any]] = {}

    def remember_on_track(self, driver_id: str, pose_xy: Tuple[float, float],
                          s: float, ns: int,
                          projection_xy: Tuple[float, float]) -> None:
        self._anchors[driver_id] = {
            "pose_xy": (float(pose_xy[0]), float(pose_xy[1])),
            "s": float(s),
            "ns": int(ns),
            "projection_xy": (float(projection_xy[0]), float(projection_xy[1])),
            "target_xy": None,
        }

    def target_for(self, driver_id: str, build_target) -> Optional[Tuple[float, float]]:
        anchor = self._anchors.get(driver_id)
        if anchor is None:
            return None
        if anchor["target_xy"] is None:
            target_x, target_y = build_target(anchor)
            anchor["target_xy"] = (float(target_x), float(target_y))
        return anchor["target_xy"]


class NeuralRaceController:
    """Controlador neural — monta a observação IDÊNTICA ao f1_env.py v2
    (23 telemetria normalizada + 2 contexto) e ações v2 [steer, longitudinal]."""

    # Constantes de normalização — MESMOS valores do f1_env.py
    OBS_SPEED, OBS_YAW_RATE, OBS_G, OBS_SLIP_DEG = 100.0, 2.0, 5.0, 10.0
    OBS_TYRE_LIFE, OBS_FUEL_KG, OBS_CLIP = 30.0, 110.0, 5.0
    PREVIEW_DISTS = (10.0, 20.0, 35.0, 50.0, 75.0, 100.0, 150.0)
    KAPPA_OBS_SCALE = 25.0
    KAPPA_WINDOW_M = 20.0
    N_OBS_TELEMETRY = 9 + 2 * len(PREVIEW_DISTS)   # 23
    STEER_MAX_RAD, STEER_MIN_RAD, STEER_V0 = math.radians(45.0), 0.04, 25.0
    # REALISMO-1 C3-B: constantes congeladas do teto pós-reentrada.
    REJOIN_RAMP_HOLD_S = 5.0
    REJOIN_RAMP_V0_MPS = 8.0
    REJOIN_RAMP_TARGET_FRACTION = 0.8
    # REALISMO-1 C6-B: offsets frozen por slot; só obs4 policy-facing muda.
    LAT_OFFSET_SLOTS_COMPOSITE = (0.273, -1.000, -0.693, 0.590, 1.000,
                                   -0.784, 0.018, -0.902, 0.064, 1.000)
    LAT_OFFSET_SLOTS_BLIND = (0.251, -0.003, -0.549, -0.042, -0.879,
                              -0.518, 0.896, 0.142, 0.694, 0.180)
    LAT_OFFSET_LIMIT_M = 1.0

    # Modos de observação
    EDGE_RAY_ANGLES_DEG = (-90.0, -72.0, -54.0, -36.0, -18.0, 0.0,
                             18.0, 36.0, 54.0, 72.0, 90.0)
    N_LIDAR_RAYS = len(EDGE_RAY_ANGLES_DEG)  # 11
    LIDAR_MAX_RANGE_M = 40.0
    LIDAR_WINDOW_SEGS = 30

    def __init__(self, weights_path: Path, mappings_path: Optional[Path] = None,
                 track=None, obs_mode: str = "legacy",
                 steer_gov: str = "off", rejoin_gap: float = 0.0,
                 launch_cap: bool = False, launch_stagger: bool = False,
                 launch_steer_mute: bool = False,
                 rejoin_handoff: str = "off",
                 rejoin_ramp: bool = False,
                 c8_rejoin: bool = False,
                 lat_offset_slots: bool = False,
                 lat_offset_profile: str = "blind",
                 pguard: bool = False,
                 rejoin_mode: str = "bearing",
                 anti_glue: bool = False,
                 proj_gate: bool = False) -> None:
        print(f"[Model] Carregando pesos neurais (NumPy Engine) de: {weights_path.name}")
        self.actor = NumpyNeuralActor(weights_path)
        self.obs_mode = obs_mode
        # v15 R8: 'off' (default, bit-reproduzível) | 'cap' (clip por κ_preview)
        self.steer_gov = steer_gov
        self.REJOIN_GAP_ENABLED = float(rejoin_gap)  # CICLO ALAVANCA: X em m; 0=off
        # CICLO LARGADA L-1a: launch-cap (prereg a3b8ff0) — default OFF
        self.LAUNCH_CAP_ENABLED = bool(launch_cap)
        # CICLO LARGADA L-1b: launch-stagger (prereg cd3ca5e) — default OFF
        self.LAUNCH_STAGGER_ENABLED = bool(launch_stagger)
        # REALISMO-1 C1-B: default OFF = byte-idêntico; validação do SHA
        # acontece no construtor para falhar antes de qualquer tick.
        self.LAUNCH_STEER_MUTE_ENABLED = bool(launch_steer_mute)
        self._launch_steer_mute_state = {}
        self._launch_steer_mute_active = {}
        self._launch_steer_mute_end_reason = {}
        self._launch_steer_mute_s_end = None
        if self.LAUNCH_STEER_MUTE_ENABLED:
            frozen_sha = str(getattr(track, 'frozen_sha256', '?')) if track is not None else '?'
            self._launch_steer_mute_s_end = self.LAUNCH_STEER_MUTE_S_END_BY_SHA.get(
                frozen_sha)
            if self._launch_steer_mute_s_end is None:
                raise ValueError(
                    "--launch-steer-mute requer pista frozen conhecida; "
                    f"sha256 recebido={frozen_sha!r}")
        self.REJOIN_HANDOFF_MODE = str(rejoin_handoff)
        self.REJOIN_HANDOFF_ENABLED = self.REJOIN_HANDOFF_MODE == "align"
        if self.REJOIN_HANDOFF_MODE not in ("off", "align"):
            raise ValueError(f"rejoin_handoff inválido: {rejoin_handoff!r}")
        self._rejoin_handoff_state = {}
        self._rejoin_handoff_active = {}
        self._rejoin_handoff_end_reason = {}
        # REALISMO-1 C3-B: teto longitudinal pós-reentrada; default OFF.
        # Estado por carro/episódio e contadores são inertes no caminho OFF.
        self.REJOIN_RAMP_ENABLED = bool(rejoin_ramp)
        self.C8_REJOIN_ENABLED = bool(c8_rejoin)
        self.REJOIN_RAMP_HOLD_S = 5.0
        self.REJOIN_RAMP_V0_MPS = 8.0
        self.REJOIN_RAMP_TARGET_FRACTION = 0.8
        self._rejoin_ramp_state = {}
        self._rejoin_ramp_active = {}
        self._rejoin_ramp_braked = {}
        self._rejoin_ramp_end_reason = {}
        self._rejoin_ramp_activation_count = 0
        self._rejoin_ramp_brake_count = 0
        self._rejoin_ramp_activation_by_driver = {}
        self._rejoin_ramp_brake_by_driver = {}
        self.LAT_OFFSET_SLOTS_ENABLED = bool(lat_offset_slots)
        self.LAT_OFFSET_PROFILE = str(lat_offset_profile)
        self._lat_offset_slots = None
        if self.LAT_OFFSET_SLOTS_ENABLED:
            if self.LAT_OFFSET_PROFILE not in ("composite", "blind"):
                raise ValueError("--lat-offset-slots exige perfil composite ou blind")
            offsets = (self.LAT_OFFSET_SLOTS_COMPOSITE
                       if self.LAT_OFFSET_PROFILE == "composite"
                       else self.LAT_OFFSET_SLOTS_BLIND)
            if len(offsets) != 10 or any(
                    not math.isfinite(float(v))
                    or abs(float(v)) > self.LAT_OFFSET_LIMIT_M for v in offsets):
                raise ValueError("--lat-offset-slots: tabela inválida")
            self._lat_offset_slots = tuple(float(v) for v in offsets)
        self._rejoin_handoff_s_end = None
        if self.REJOIN_HANDOFF_ENABLED:
            frozen_sha = str(getattr(track, 'frozen_sha256', '?')) if track is not None else '?'
            self._rejoin_handoff_s_end = self.REJOIN_HANDOFF_S_END_BY_SHA.get(frozen_sha)
            if self._rejoin_handoff_s_end is None:
                raise ValueError(
                    "--rejoin-handoff align requer pista frozen conhecida; "
                    f"sha256 recebido={frozen_sha!r}")
        # SANIDADE-0 NIT N1 (review ANTI-D3-1): o progress-guard foi REPROVADO
        # no gate (hesit 12 vs 3; cc 752->1520; 9/10 disparos na LARGADA) e fica
        # isolado atrás de --pguard, DEFAULT OFF. Off = comportamento
        # pré-ANTI-D3-1 (bit-idêntico à F4v15) e instrumento carrega o gate
        # NOMINAL (contrato do prereg 57a9342, violado na implementação).
        self.PGUARD_ENABLED = bool(pguard)
        # SANIDADE-0 M2 (prereg 1007636 §1): rejoin PERCEPTIVE — substitui o
        # bearing quando ON (ângulo raso <=15°, cap por superfície, gap X=20
        # via o gap-check reparado). Trigger é ESTADO (off-track), NUNCA fade
        # por progresso (lição ANTI-D3-1). Default 'bearing' = bit-idêntico.
        self.REJOIN_MODE = str(rejoin_mode)
        # SANIDADE-0 M3 (prereg 1007636 §1): anti-glue — (ii) preventivo
        # escopado a composite/professor; (iii) deadlock-breaker p/ todos.
        # Default OFF = bit-idêntico (estado só é tocado sob a flag).
        self.ANTI_GLUE_ENABLED = bool(anti_glue)
        self._glue_state = {}   # drv_id -> dict(partner_id, ticks, breaking)
        self.PROJ_GATE_ENABLED = bool(proj_gate)
        self._projection_anchor_gate = (
            ProjectionAnchorGate() if self.PROJ_GATE_ENABLED else None)
        self._steergov_clips = {}   # drv -> n de ticks clipados (instrumento)
        self.last_steergov = {}     # drv -> 1/0 no tick corrente (coluna CSV)

        # VALIDAÇÃO DE SHAPE: entradas totais por modo (tel + 2 ctx + 8 emb
        # + 4 emb): legacy=37, edge=48, traffic=60 (ator v14). Erro EXPLÍCITO
        # se incompatível (não um crash numérico).
        w1_shape = None
        for attr in dir(self.actor):
            v = getattr(self.actor, attr)
            if isinstance(v, np.ndarray) and v.ndim == 2 and v.shape[1] == 256:
                w1_shape = v.shape
                break
        expected_tel = {'legacy': 23, 'edge': 34, 'traffic': 46}[obs_mode]
        expected_total = expected_tel + 2 + 8 + 4
        # v15 FASE 4: no modo composite, o actor solo (48d/edge) é carregado
        # apenas para reuso das tabelas; a AÇÃO vem do NumpyCompositeActor com
        # obs 'traffic' — o shape check é pulado (documentado, não é silencioso)
        skip_check = (obs_mode == 'traffic' and w1_shape and w1_shape[0] == 48)
        if w1_shape and w1_shape[0] != expected_total and not skip_check:
            sugestao = {60: 'traffic', 48: 'edge'}.get(w1_shape[0], 'legacy')
            raise ValueError(
                f"INCOMPATÍVEL: o ator espera {w1_shape[0]} entradas mas "
                f"obs_mode='{obs_mode}' produz {expected_total} "
                f"({expected_tel} tel + 2 ctx + 8 emb + 4 emb). "
                f"Use --obs-mode {sugestao}.")
        # obs_mode='edge': N_OBS_TELEMETRY continua 23 (base); os 11 raios
        # são adicionados via hstack ANTES da inferência (o ator espera 34+14=48)

        self.mappings = {}
        if mappings_path and mappings_path.exists():
            self.mappings = joblib.load(str(mappings_path))
        self.compound_id_map = self.mappings.get("compounds", {})

        self._A = None
        if track is not None:
            self._build_tables(np.array(track.waypoints, dtype=np.float64),
                               getattr(track, "width_m", 12.0) / 2.0)
        self._stuck_since = {}
        self._recovery_state = {}  # drv -> estado da recuperação (histerese/progresso)
        self._blocked_events = {}   # drv -> nº de ticks bloqueado por contato
        self.last_authority = {}    # drv -> autoridade FINAL sobre th/brk no tick
        self._prev_actions = {}   # driver_id -> (steer, long) p/ obs v2
        # v15 FASE 4: composite (solo congelado + residual gated)
        self._composite_np = None   # NumpyCompositeActor (set externamente)
        self._res_prev = {}          # drv -> (prev_steer, prev_long) p/ o residual
        # ANTI-D3-1: estado do progress-guard (fade gate->base) por driver
        self._pguard_state = {}
        # CICLO ALAVANCA: estado do gap-check por driver
        self._gapcheck_state = {}   # drv -> dict(tick0, hold, fb) ou None
        # REPARO (amenda ALAVANCA): telemetria por carro EM FASE com a ação —
        # o bloco usava 'drv' STALE do loop de observações (= último driver):
        # UM estado compartilhado por todos os carros + flags só do último.
        self._gap_hold = {}         # drv -> 1/0 no tick corrente (coluna CSV)
        self._gap_fb = {}           # drv -> 1/0 SOMENTE no tick do fallback
        self._was_offtrack = {}    # drv -> offtrack no tick ANTERIOR (transição off->on)
        # CICLO LARGADA L-1a: telemetria do launch-cap por carro (lição stale-drv)
        self._cap_active = {}      # drv -> 1/0 no tick corrente (coluna CSV)
        # CICLO LARGADA L-1b: stagger — slots do run (o runner seta; fail-loud
        # se a flag ligada sem ordem) e telemetria por carro
        self._launch_grid_slots = None   # drv -> posição de largada (1..10)
        self._stagger_held = {}          # drv -> 1/0 no tick corrente (coluna CSV)
        # v15 R13-FECHAMENTO: residual input 16d por tick (logging ADITIVO v3.3)
        self._res_in_last = {}       # drv -> res_in[i] (16d) do tick corrente
        self._res_gate = {}          # drv -> último gate (instrumento)
        self._res_norm = {}          # drv -> último |r| (instrumento)

    def _rejoin_target_point(self, driver_id: str, s_live: float,
                             projection_x_live: float,
                             projection_y_live: float,
                             ahead_m: float) -> Tuple[float, float]:
        """Resolve a live target or the frozen target from the last anchor."""
        if self.PROJ_GATE_ENABLED:
            def from_anchor(anchor):
                h_anchor = self._heading_at(anchor["s"])
                px, py = anchor["projection_xy"]
                return (px + ahead_m * math.cos(h_anchor),
                        py + ahead_m * math.sin(h_anchor))

            frozen = self._projection_anchor_gate.target_for(driver_id, from_anchor)
            if frozen is not None:
                return frozen

        h_track = self._heading_at(float(s_live))
        return (projection_x_live + ahead_m * math.cos(h_track),
                projection_y_live + ahead_m * math.sin(h_track))

    @staticmethod
    def steer_limit_rad(speed_mps):
        return max(NeuralRaceController.STEER_MIN_RAD,
                   NeuralRaceController.STEER_MAX_RAD /
                   (1.0 + (float(speed_mps) / NeuralRaceController.STEER_V0) ** 2))

    @staticmethod
    def _apply_launch_steer_mute(action, solo_action, active):
        """Substitui apenas o eixo steer pelo solo durante D_L."""
        out = np.asarray(action, dtype=np.float64).copy()
        if active:
            solo = np.asarray(solo_action, dtype=np.float64).ravel()
            out[0] = math.tanh(float(solo[0]))
        return out

    def _launch_steer_mute_step(self, driver_id, s_live, lat_dist, sim_ts):
        """Atualiza D_L por carro e retorna se o mute vale neste tick.

        D_L é uso único: crossed/offtrack/deadline encerra o estado e o
        motivo permanece disponível para o CSV ON. A posição é medida no
        progresso circular desde o primeiro tick observado para o carro.
        """
        if not self.LAUNCH_STEER_MUTE_ENABLED:
            return False
        st = self._launch_steer_mute_state.setdefault(
            driver_id, dict(start_s=float(s_live), ended=False, reason=None))
        if st['ended']:
            self._launch_steer_mute_active[driver_id] = 0
            return False
        if float(lat_dist) > self._half_width * self.OFFTRACK_FACTOR:
            st.update(ended=True, reason='offtrack')
            self._launch_steer_mute_active[driver_id] = 0
            self._launch_steer_mute_end_reason[driver_id] = st['reason']
            return False
        if float(sim_ts) > self.LAUNCH_STEER_MUTE_TMAX_S:
            st.update(ended=True, reason='deadline')
            self._launch_steer_mute_active[driver_id] = 0
            self._launch_steer_mute_end_reason[driver_id] = st['reason']
            return False
        delta_end = ((float(self._launch_steer_mute_s_end) - st['start_s'])
                     % self._track_len_s)
        delta_live = ((float(s_live) - st['start_s']) % self._track_len_s)
        if delta_live >= delta_end:
            st.update(ended=True, reason='crossed')
            self._launch_steer_mute_active[driver_id] = 0
            self._launch_steer_mute_end_reason[driver_id] = st['reason']
            return False
        self._launch_steer_mute_active[driver_id] = 1
        return True

    @classmethod
    def rejoin_ramp_v_cap(cls, v_plan_mps: float, elapsed_s: float) -> float:
        """C3-B: teto de velocidade congelado no prereg, em m/s."""
        target = cls.REJOIN_RAMP_TARGET_FRACTION * float(v_plan_mps)
        elapsed = float(elapsed_s)
        return min(target, cls.REJOIN_RAMP_V0_MPS
                   + max(target - cls.REJOIN_RAMP_V0_MPS, 0.0)
                   * elapsed / cls.REJOIN_RAMP_HOLD_S)

    def _rejoin_ramp_step(self, driver_id, *, was_offtrack, offtrack,
                          s_live, speed, sim_ts, th, brk):
        """Aplica o teto C3-B por carro/episódio e só altera th/brk.

        A janela inclui elapsed=0 e elapsed=5,0 s; expira no primeiro tick
        estritamente posterior a 5,0 s. Uma nova transição off->on cria novo
        episódio. O v_plan é consultado na posição corrente, como pinado na
        fórmula do C3-B.
        """
        if not self.REJOIN_RAMP_ENABLED:
            return False, False, th, brk
        st = self._rejoin_ramp_state.get(driver_id)
        if was_offtrack and not offtrack and (st is None or st.get('ended')):
            st = dict(active=True, ended=False, t0=float(sim_ts), reason=None)
            self._rejoin_ramp_state[driver_id] = st
            self._rejoin_ramp_activation_count += 1
            self._rejoin_ramp_activation_by_driver[driver_id] = (
                self._rejoin_ramp_activation_by_driver.get(driver_id, 0) + 1)
        self._rejoin_ramp_active[driver_id] = 0
        self._rejoin_ramp_braked[driver_id] = 0
        if st is None or st.get('ended') or not st.get('active'):
            return False, False, th, brk
        if offtrack:
            st.update(active=False, ended=True, reason='offtrack')
            self._rejoin_ramp_end_reason[driver_id] = st['reason']
            return False, False, th, brk
        elapsed = float(sim_ts) - float(st['t0'])
        if elapsed > self.REJOIN_RAMP_HOLD_S:
            st.update(active=False, ended=True, reason='deadline')
            self._rejoin_ramp_end_reason[driver_id] = st['reason']
            return False, False, th, brk
        v_plan = getattr(self, '_v_plan_cap', None)
        if v_plan is None:
            raise RuntimeError('--rejoin-ramp requer --gov vplan')
        v_cap = self.rejoin_ramp_v_cap(
            float(v_plan.at(float(s_live))), elapsed)
        self._rejoin_ramp_active[driver_id] = 1
        if float(speed) <= v_cap:
            return True, False, th, brk
        excess_frac = (float(speed) - v_cap) / max(v_cap, 1.0)
        ramp_brake = float(np.clip(excess_frac * 0.8, 0.15, 1.0))
        self._rejoin_ramp_brake_count += 1
        self._rejoin_ramp_brake_by_driver[driver_id] = (
            self._rejoin_ramp_brake_by_driver.get(driver_id, 0) + 1)
        self._rejoin_ramp_braked[driver_id] = 1
        # Mesma lei do governor: corta th e eleva brk sem tocar no esterço.
        return True, True, 0.0, max(float(brk), ramp_brake)

    def rejoin_ramp_summary(self):
        """Resumo aditivo para auditoria, sem alterar o CSV OFF."""
        return dict(
            enabled=bool(self.REJOIN_RAMP_ENABLED),
            activations=int(self._rejoin_ramp_activation_count),
            brake_ticks=int(self._rejoin_ramp_brake_count),
            activations_by_driver=dict(self._rejoin_ramp_activation_by_driver),
            brake_ticks_by_driver=dict(self._rejoin_ramp_brake_by_driver),
        )

    @staticmethod
    def c8_gap_blocked(s_live: float, other_s: tuple[float, ...],
                       track_len_s: float, gap_m: float) -> bool:
        """Return whether a car ahead is inside the C8 reentry gap."""
        for peer_s in other_s:
            gap = (float(peer_s) - float(s_live)) % float(track_len_s)
            if gap > float(track_len_s) / 2.0:
                gap -= float(track_len_s)
            if 0.0 < gap < float(gap_m):
                return True
        return False

    def _apply_lat_offset_slots(self, tels, drivers, drv_signed):
        """C6-B: altera somente o canal obs4, nunca os arrays físicos."""
        if not self.LAT_OFFSET_SLOTS_ENABLED:
            return tels
        if self._lat_offset_slots is None or not self._launch_grid_slots:
            raise ValueError("--lat-offset-slots: tabela de slots ausente")
        out = np.asarray(tels, dtype=np.float32).copy()
        for i, drv in enumerate(drivers):
            slot_one_based = self._launch_grid_slots.get(drv.driver_id)
            if slot_one_based is None or not 1 <= int(slot_one_based) <= 10:
                raise ValueError("--lat-offset-slots: slot fora de 1..10")
            off = self._lat_offset_slots[int(slot_one_based) - 1]
            out[i, 4] = (float(drv_signed[i]) - off) / self._half_width
        return out

    def _rejoin_handoff_step(self, driver_id, *, was_offtrack, offtrack,
                              s_live, signed_lat, speed, heading_rad,
                              live_x, live_y, projection_x, projection_y,
                              sim_ts):
        """Run one C2-B handoff step; returns (active, steer, reason).

        The helper changes steering only. It never receives or writes th/brk,
        so policy + governor longitudinal commands remain untouched.
        """
        if not self.REJOIN_HANDOFF_ENABLED:
            return False, None, None
        st = self._rejoin_handoff_state.get(driver_id)
        if was_offtrack and not offtrack and (st is None or st.get('ended')):
            st = dict(active=True, ended=False, t0=float(sim_ts), reason=None)
            self._rejoin_handoff_state[driver_id] = st
        if st is None or st.get('ended') or not st.get('active'):
            self._rejoin_handoff_active[driver_id] = 0
            return False, None, st.get('reason') if st else None
        if offtrack:
            st.update(active=False, ended=True, reason='offtrack')
            self._rejoin_handoff_active[driver_id] = 0
            self._rejoin_handoff_end_reason[driver_id] = st['reason']
            return False, None, st['reason']
        heading_err = self._wrap(
            float(heading_rad) - self._heading_at(float(s_live)))
        margin = self._half_width - abs(float(signed_lat))
        elapsed = float(sim_ts) - st['t0']
        if (abs(heading_err) <= self.REJOIN_HANDOFF_THETA_RAD
                and margin >= self.REJOIN_HANDOFF_MARGIN_M):
            st.update(active=False, ended=True, reason='aligned')
            self._rejoin_handoff_active[driver_id] = 0
            self._rejoin_handoff_end_reason[driver_id] = st['reason']
            return False, None, st['reason']
        if elapsed >= self.REJOIN_HANDOFF_TMAX_S:
            st.update(active=False, ended=True, reason='timeout')
            self._rejoin_handoff_active[driver_id] = 0
            self._rejoin_handoff_end_reason[driver_id] = st['reason']
            return False, None, st['reason']
        tx, ty = self._rejoin_target_point(
            driver_id, float(s_live), float(projection_x), float(projection_y),
            self.REJOIN_AHEAD_M)
        bearing = math.atan2(ty - float(live_y), tx - float(live_x))
        berr = self._wrap(bearing - float(heading_rad))
        steer_limit = self.steer_limit_rad(float(speed))
        steer = float(np.clip(self.REJOIN_BEARING_GAIN * berr,
                              -steer_limit, steer_limit))
        self._rejoin_handoff_active[driver_id] = 1
        return True, steer, None

    def _build_tables(self, A: np.ndarray, half_width: float) -> None:
        B = np.roll(A, -1, axis=0)
        self._A, self._AB = A, B - A
        self._seg_len = np.hypot(self._AB[:, 0], self._AB[:, 1])
        self._seg_cum = np.concatenate([[0.0], np.cumsum(self._seg_len)])[:-1]
        self._seg_heading = np.arctan2(self._AB[:, 1], self._AB[:, 0])
        self._track_len_s = float(self._seg_len.sum())
        self._half_width = half_width
        # Percepção de bordas (obs edge/traffic): pré-computa polilinhas L/R
        # ('traffic' INCLUI os 11 raios do edge — 34d base + 12d de tráfego)
        if getattr(self, "obs_mode", "legacy") in ("edge", "traffic"):
            norm_x = -np.sin(self._seg_heading)
            norm_y = np.cos(self._seg_heading)
            self._edge_L = np.column_stack([A[:, 0] + norm_x * half_width,
                                            A[:, 1] + norm_y * half_width])
            self._edge_R = np.column_stack([A[:, 0] - norm_x * half_width,
                                            A[:, 1] - norm_y * half_width])

    @staticmethod
    def _wrap(a: float) -> float:
        return (a + math.pi) % (2.0 * math.pi) - math.pi

    def _heading_at(self, s: float) -> float:
        s = s % self._track_len_s
        j = int(np.searchsorted(self._seg_cum, s, side="right") - 1)
        return float(self._seg_heading[min(max(j, 0), len(self._seg_heading) - 1)])

    def _kappa_signed(self, s: float, window_m: float = None) -> float:
        """Curvatura assinada local (+ = esquerda), idêntica ao f1_env v2.

        CORREÇÃO (wrap ±180°): acumula diferenças pequenas (~2m, sempre <90°)
        ao longo da janela — a diferença central única cruza a fronteira do
        wrap em hairpins de ~180° e INVERTE o sinal (bug medido em Monaco).
        """
        w = window_m or self.KAPPA_WINDOW_M
        n_steps = max(2, int(w / 2.0))
        step = w / n_steps
        dh_total = 0.0
        for i in range(n_steps):
            s1 = s - w / 2.0 + i * step
            s2 = s - w / 2.0 + (i + 1) * step
            dh = self._heading_at(s2) - self._heading_at(s1)
            dh = (dh + math.pi) % (2 * math.pi) - math.pi
            dh_total += dh
        return float(dh_total / w)

    def _kappa_ahead(self, s: float, horizon_m: float = 120.0) -> float:
        """Curvatura MÁXIMA local (rad/m) nos próximos `horizon_m` metros.

        Idêntico ao f1_env.py: amostra o heading a cada 10 m e toma o maior
        giro por metro — não a média, pois ela diluiria a curva fechada.
        """
        n = max(2, int(horizon_m // 10.0) + 1)
        ds = horizon_m / (n - 1)
        prev_h = self._heading_at(s)
        kappa = 0.0
        for k in range(1, n):
            h = self._heading_at(s + k * ds)
            kappa = max(kappa, abs(self._wrap(h - prev_h)) / ds)
            prev_h = h
        return kappa

    def _action_to_controls(self, action, speed_mps: float):
        """Réplica de F1MultiContextEnv.action_to_controls v2: [steer, long]."""
        a = np.asarray(action, dtype=np.float64).ravel()
        if a.size >= 3:   # modelo legado v1 [throttle, brake, steer]
            th = float(np.clip(a[0], 0.0, 1.0))
            brk = float(np.clip(a[1], 0.0, 1.0))
            steer = float(np.clip(a[2], -1.0, 1.0))
            if th >= brk:
                brk = 0.0
            else:
                th = 0.0
        else:
            steer = float(np.clip(a[0], -1.0, 1.0))
            long_cmd = float(np.clip(a[1], -1.0, 1.0))
            th, brk = max(long_cmd, 0.0), max(-long_cmd, 0.0)
        steer_rad = steer * max(self.STEER_MIN_RAD,
                                self.STEER_MAX_RAD / (1.0 + (speed_mps / self.STEER_V0) ** 2))
        return th, brk, steer_rad

    # Parâmetros do governador de curva — mesma física de f1_env.py
    A_LAT_MAX   = 14.0   # m/s²: alinhado ao teto medido do assist (era 30, impossível)
    V_GOV_MIN   = 12.0   # m/s (43 km/h): velocidade segura mínima em curvas fechadas
    V_GOV_MAX   = 90.0   # m/s (324 km/h): teto na reta
    GOV_HORIZON = 120.0  # m à frente para calcular curvatura máxima
    GOV_MARGIN  = 1.15   # 15% de margem: só freia se speed > 115% da velocidade segura

    # Parâmetros de recuperação de saída de pista (modo rejoin)
    # CORREÇÃO: era 2.0 (12 m) — o carro podia viajar 6 m pela grama sem
    # reação. Agora: 1.0 = reage quando o CENTRO atinge a borda do asfalto.
    OFFTRACK_FACTOR   = 1.0
    REJOIN_TARGET_MPS = 8.0    # velocidade alvo fora da pista (retorno seguro)
    REJOIN_THROTTLE   = 0.35  # torque moderado para crawlar de volta
    # v15 FASE R3 (fix do ABSORVEDOR): o rejoin antigo comandava um VALOR
    # fixo de esterço (saturado a |lat|>20 m) — na grama o carro crawl a
    # ~1,5 m/s e esterço constante = ORBITAS de ~3 m sem rumo à pista
    # (PER: lat 20-78 m por 500+s; NOR: 861 m de excursão). Agora o alvo
    # é uma DIREÇÃO: bearing ao ponto de re-entrada (projeção + AHEAD m
    # na linha central) — o carro anda RETO até o asfalto.
    REJOIN_AHEAD_M    = 10.0  # ponto de re-entrada: projeção + 10 m à frente
    REJOIN_BEARING_GAIN = 2.0  # steer = clip(ganho * erro de bearing)
    # CICLO ALAVANCA (prereg 1883d6d): gap-check no rejoin — UMA variável.
    # Ao chegar à borda (on-track, |lat| < 1,5×meia-largura, saindo de
    # off-track), segura em crawl 4 m/s até gap À FRENDE ≥ X ou T_max=10 s.
    # Fallback T_max solta e registra (sem deadlock). Hold em crawl NÃO é
    # parada ≥3 s (v≥1 > 0,5 — isenção documentada no prereg).
    REJOIN_GAP_ENABLED = 0.0   # X em metros; 0 = desligado (default)
    REJOIN_GAP_CRAWL_MPS = 4.0
    REJOIN_GAP_TMAX_TICKS = 100  # 10 s a 10 Hz
    # C8-B: constants frozen from C8-0 N=0; default OFF is byte-identical.
    C8_GRASS_V_CAP_MPS = 6.0
    C8_GAP_M = 20.0
    C8_GAP_WINDOW_TICKS = 100
    # CICLO LARGADA L-1a (prereg a3b8ff0): launch-cap — CONSTANTES PINADAS
    LAUNCH_CAP_K = 0.8          # teto = k × v_plan(s)
    LAUNCH_CAP_S_CUT = 2950.0   # janela: s < s_cut (cobre o cluster 2699,7-2814 + saída do S)
    LAUNCH_CAP_TMAX_S = 30.0    # janela: t < T_max (≈5× a fase crítica, med 6,2 s)
    # CICLO LARGADA L-1b (prereg cd3ca5e): launch-stagger — ÚNICA constante nova
    LAUNCH_STAGGER_DT = 1.0     # s/slot: release(slot) = (pos-1)×Δt (P1→0; P10→9 s)
    # REALISMO-1 C1-B (prereg v1.1): mute SOMENTE do esterço residual.
    # S_L_END é indexado pelo SHA da pista frozen; SHA desconhecido = erro.
    LAUNCH_STEER_MUTE_TMAX_S = 10.0
    LAUNCH_STEER_MUTE_S_END_BY_SHA = {
        '164876196eb12174': 2718.3,  # Interlagos v2
        '67ca11dc211c8c78': 3331.2,  # Monaco v2
    }
    # REALISMO-1 C2-B (prereg): handoff alinhado pós-reentrada.
    REJOIN_HANDOFF_THETA_RAD = 0.3490658503988659
    REJOIN_HANDOFF_MARGIN_M = 0.5
    REJOIN_HANDOFF_TMAX_S = 24.0
    REJOIN_HANDOFF_S_END_BY_SHA = {
        '164876196eb12174': 2718.3,
        '67ca11dc211c8c78': 3331.2,
    }
    # SANIDADE-0 M2 (prereg 1007636 §1): rejoin PERCEPTIVE — PINADAS
    REJOIN_PERCEPTIVE_ANGLE_DEG = 15.0    # ângulo raso de chegada (<=15°)
    REJOIN_PERCEPTIVE_V_GRASS = 6.0        # cap na grama (< 8,0 do bearing)
    REJOIN_PERCEPTIVE_AHEAD_MIN_M = 10.0   # nunca mais perto que o bearing
    REJOIN_PERCEPTIVE_AHEAD_MAX_M = 120.0  # teto do braço longo (15° de 32 m)
    # SANIDADE-0 M3 (prereg 1007636 §1): anti-glue — PINADAS
    ANTI_GLUE_NEAR_LAT = 2.5      # |Δlat| de "colado" (base = LAT_CORRIDOR_M)
    ANTI_GLUE_NEAR_DS = 10.0      # adjacência longitudinal do preventivo (ii)
    ANTI_GLUE_OFFSET_STEER = 0.25 # esterço PARA FORA do preventivo (ii)
    ANTI_GLUE_TH_CAP = 0.6        # teto de aceleração do par colado (ii)
    ANTI_GLUE_BREAK_S = 3.0        # breaker: par colado > 3 s contíguos (iii)
    ANTI_GLUE_BREAK_DS = 5.5       # adjacência do breaker (iii)
    ANTI_GLUE_BREAK_STEER = 0.4    # offset máximo do breaker (iii)
    ANTI_GLUE_RELEASE_LAT = 3.0   # solta quando |Δlat| > 3 m
    ANTI_GLUE_RELEASE_DS = 8.0    # ...ou Δs wrap > 8 m
    # SANIDADE-1b M3-v2 (prereg 87214c7 §2): TETOS POR-REALIZAÇÃO — o v1 é
    # MORTO (FAIL por margens no SANIDADE-0; D4: preventivo crônico é o
    # custo dominante; D5: breaker incompetente no regime crawl/borda).
    # Tick lógico 0,1 s (10 Hz) em TODOS os pins abaixo.
    ANTI_GLUE_PREV_MAX_EP_TICKS = 10    # preventivo: 1,0 s por episódio contíguo
    ANTI_GLUE_PREV_COOLDOWN_TICKS = 20  # cooldown 2,0 s após o teto do episódio
    ANTI_GLUE_PREV_MAX_EPS = 10          # máx episódios por PAR por corrida
    ANTI_GLUE_PREV_DV_MAX = 8.0          # preventivo só com |Δv| < 8 m/s
    ANTI_GLUE_BRK_MAX_EP_TICKS = 40     # breaker: 4,0 s por episódio -> DESISTE
    ANTI_GLUE_BRK_V_FULL = 25.0          # abaixo: lift+0,4 (v1); acima: suave
    ANTI_GLUE_BRK_STEER_SOFT = 0.15     # offset suave acima de BRK_V_FULL
    ANTI_GLUE_BRK_TH_SOFT = 0.5          # th<=0,5 acima de BRK_V_FULL (sem lift)
    ANTI_GLUE_BRK_MAX_EPS = 8            # máx episódios breaker por par/corrida
    # v15 R8 — STEER-GOVERNOR (OPT-IN, default off): a física lateral é sã
    # (R7b scripted: círculo estável até v_allow) mas a política comanda
    # esterço ~24× a necessidade cinemática nas saídas (weave/caça). Cap:
    # |δ| ≤ k_comp×atan(L×κ@10m) sobre o comando da POLÍTICA, antes da
    # composição — rejoin bearing (R3) sobrescreve depois e é ISENTO;
    # recovery/blocked não tocam esterço; professor não é afetado.
    STEER_GOV_K_COMP = 2.0
    STEER_GOV_WHEELBASE_M = 3.4
    BLOCKED_THROTTLE  = 0.25  # carro parado em contato com outro: empurrão leve

    # Anti-stall (ver correção no corpo de predict_batch)
    STALL_RELEASE_MPS = 5.0   # acima disso, considera-se "andando" (nada na pista exige < 5 m/s)
    STALL_TIMEOUT_S   = 1.0   # parado/lento por > 1 s -> engata recuperação

    # RECUPERAÇÃO (Fase D — substitui o anti-stall de ciclo-limite)
    RECOVERY_TARGET_MPS      = 9.0    # alvo na recuperação (abaixo de TODO v_safe da pista)
    RECOVERY_EXIT_PROGRESS_M = 25.0   # progresso físico exigido p/ devolver o controle
    RESTALL_TIMEOUT_S        = 0.15  # re-engate rápido se re-estolar < 5 s após liberar

    def _recovery_step(self, rec, speed, th, brk, sim_ts, progress_m, offtrack):
        """Recuperação de imobilização COM ESTADO e saída por progresso REAL.

        O anti-stall anterior liberava ao cruzar STALL_RELEASE_MPS — a
        política (que freia forte em curvas fora da sua distribuição de
        treino, kappa_obs ~2.6 vs ~2.25 do treino) matava a velocidade no
        tick seguinte e o carro entrava num ciclo-limite parar/andar:
        96 episódios de 0,3-1,0 s medidos numa corrida headless de 600 s,
        concentrados nas curvas fechadas — percebido na corrida visual como
        "parado até um carro de trás empurrar". Agora a recuperação é um
        MODO com histerese: engata após o stall, aplica torque progressivo
        com freio ZERO e só devolve o controle quando o carro ganhou
        RECOVERY_EXIT_PROGRESS_M de progresso físico. Re-stall logo após uma
        liberação re-engata quase imediatamente (anti-chattering).

        Retorna (th, brk, ativo).
        """
        now = float(sim_ts)
        # --- timer de imobilização: reseta SÓ com velocidade real (>= release) ---
        if speed < self.STALL_RELEASE_MPS:
            rec.setdefault('stall_since', now)
        else:
            rec['stall_since'] = now
        stalled_for = now - rec.get('stall_since', now)

        # --- engate ---
        if not rec.get('active', False):
            since_release = now - rec.get('last_release', -1e9)
            timeout = self.RESTALL_TIMEOUT_S if since_release < 5.0 else self.STALL_TIMEOUT_S
            if stalled_for > timeout and speed < 2.0:
                rec['active'] = True
                rec['progress0'] = float(progress_m)
                rec['engaged_ts'] = now

        # --- saída por progresso REAL (não por velocidade) ---
        if rec.get('active', False):
            gained = float(progress_m) - rec.get('progress0', float(progress_m))
            if gained >= self.RECOVERY_EXIT_PROGRESS_M and speed >= 3.0:
                rec['active'] = False
                rec['last_release'] = now
                return th, brk, False
            if offtrack:
                # rejoin comanda a velocidade/esterço; a recuperação só garante
                # que nenhum freio da política mate o crawle de volta
                return th, 0.0, True
            th_rec = float(np.clip((self.RECOVERY_TARGET_MPS - speed) / 6.0 + 0.25,
                                   0.25, 0.9))
            return th_rec, 0.0, True
        return th, brk, False

    def _cast_rays_batch(self, xs, ys, headings, ss):
        """Raios LiDAR para todos os carros (idêntico ao _cast_rays do f1_env).

        11 raios nos ângulos EDGE_RAY_ANGLES_DEG a partir do heading, medindo
        as polilinhas de BORDA do asfalto (L/R pré-computadas em _build_tables).
        """
        n = len(xs)
        rays_out = np.full((n, self.N_LIDAR_RAYS), 1.0, dtype=np.float32)
        max_r = self.LIDAR_MAX_RANGE_M
        n_wp = len(self._A)
        w = self.LIDAR_WINDOW_SEGS
        for i in range(n):
            x, y, hdg, s = xs[i], ys[i], headings[i], ss[i]
            j0 = int(np.searchsorted(self._seg_cum, s, side="right") - 1) % n_wp
            idx = np.arange(j0 - w, j0 + w + 1) % n_wp
            idx_n = (idx + 1) % n_wp
            LA, LB = self._edge_L[idx], self._edge_L[idx_n]
            RA, RB = self._edge_R[idx], self._edge_R[idx_n]
            A = np.vstack([LA, RA]); B = np.vstack([LB, RB])
            ax, ay = A[:, 0], A[:, 1]
            bx, by = B[:, 0], B[:, 1]
            apx, apy = ax - x, ay - y
            dBAx, dBAy = bx - ax, by - ay
            cAPBA = apx * dBAy - apy * dBAx
            for k, ang_deg in enumerate(self.EDGE_RAY_ANGLES_DEG):
                ang = hdg + math.radians(ang_deg)
                dx, dy = math.cos(ang), math.sin(ang)
                den = dx * dBAy - dy * dBAx
                t_num = cAPBA
                u_num = apx * dy - apy * dx
                with np.errstate(divide="ignore", invalid="ignore"):
                    t = t_num / den
                    u = u_num / den
                valid = (np.abs(den) > 1e-12) & (t > 0.01) & (t < max_r) & (u >= 0.0) & (u <= 1.0)
                d = np.where(valid, t, max_r)
                rays_out[i, k] = d.min() if valid.any() else max_r
        return rays_out / max_r

    def predict_batch(self, engine, drivers, waypoints, track_id: int = 0):
        n_drivers = len(drivers)
        if self._A is None:                      # fallback: usa os waypoints recebidos
            self._build_tables(np.array(waypoints, dtype=np.float64), 6.0)

        tels = np.zeros((n_drivers, self.N_OBS_TELEMETRY), dtype=np.float32)
        ctxs = np.zeros((n_drivers, 2), dtype=np.float32)
        t_ids = np.full(n_drivers, track_id, dtype=np.int32)
        c_ids = np.zeros(n_drivers, dtype=np.int32)

        # Cache de posição arco s e dist lateral para uso no pós-processamento
        drv_s   = np.zeros(n_drivers, dtype=np.float64)
        drv_lat = np.zeros(n_drivers, dtype=np.float64)
        # FASE 4 v14: lat COM SINAL e velocidade por carro — insumos do bloco
        # de tráfego (compute_traffic_features) no obs_mode='traffic'
        drv_signed = np.zeros(n_drivers, dtype=np.float64)
        drv_v      = np.zeros(n_drivers, dtype=np.float64)
        drv_proj_x = np.zeros(n_drivers, dtype=np.float64)
        drv_proj_y = np.zeros(n_drivers, dtype=np.float64)

        A, AB, L = self._A, self._AB, self._seg_len
        for i, drv in enumerate(drivers):
            handle = engine.handles[drv.driver_id]
            phys = engine.physics.get_state(handle)
            state = engine.states[drv.driver_id]
            x, y = phys["x"], phys["y"]

            # projeção idêntica ao env: erro lateral COM SINAL + arco s (metros)
            ap_x, ap_y = x - A[:, 0], y - A[:, 1]
            t = np.clip((ap_x * AB[:, 0] + ap_y * AB[:, 1]) / (L * L + 1e-9), 0.0, 1.0)
            proj_x = A[:, 0] + t * AB[:, 0]
            proj_y = A[:, 1] + t * AB[:, 1]
            d = np.hypot(proj_x - x, proj_y - y)
            idx = int(np.argmin(d))
            s = self._seg_cum[idx] + float(t[idx]) * L[idx]
            cross = AB[idx, 0] * (y - proj_y[idx]) - AB[idx, 1] * (x - proj_x[idx])
            signed = float(d[idx]) if cross >= 0.0 else -float(d[idx])

            drv_s[i]   = s
            drv_lat[i] = float(d[idx])   # distância absoluta à linha central
            drv_signed[i] = signed       # lateral COM SINAL (+ = esquerda)
            # v15 FASE R3: projeção física na linha central (alvo do rejoin)
            drv_proj_x[i] = float(proj_x[idx])
            drv_proj_y[i] = float(proj_y[idx])
            drv_v[i] = phys["speed_mps"]

            if (self.PROJ_GATE_ENABLED
                    and drv_lat[i] <= self._half_width * self.OFFTRACK_FACTOR):
                # Keep the last valid state while off-track. The global `idx`
                # above replaces it on the first on-track tick after rejoin.
                self._projection_anchor_gate.remember_on_track(
                    drv.driver_id, (x, y), s, idx,
                    (float(proj_x[idx]), float(proj_y[idx])))

            heading_err = self._wrap(phys["heading_rad"] - float(self._seg_heading[idx]))

            # preview v2: por distância d, [delta_heading/π, kappa_assinada*25]
            h0 = self._heading_at(s)
            preview = []
            for dm in self.PREVIEW_DISTS:
                preview.append(self._wrap(self._heading_at(s + dm) - h0) / math.pi)
                preview.append(self._kappa_signed(s + dm) * self.KAPPA_OBS_SCALE)

            prev_steer, prev_long = self._prev_actions.get(drv.driver_id, (0.0, 0.0))
            tels[i] = [
                phys["speed_mps"] / self.OBS_SPEED,
                phys["yaw_rate"] / self.OBS_YAW_RATE,
                phys["g_lat"] / self.OBS_G,
                phys["g_long"] / self.OBS_G,
                signed / self._half_width,
                math.sin(heading_err),
                math.cos(heading_err),
                prev_steer,
                prev_long,
                *preview,
            ]
            ctxs[i] = [state.tyre.tyre_life / self.OBS_TYRE_LIFE,
                       state.car.fuel_kg / self.OBS_FUEL_KG]

        # C6-B: policy-facing obs4 only; drv_signed/drv_lat/s/physical state
        # above remain untouched and are used by rays, traffic and controls.
        tels = self._apply_lat_offset_slots(tels, drivers, drv_signed)

        # mesmo clip do env (OBS_CLIP = 5)
        tels = np.clip(np.nan_to_num(tels, nan=0.0, posinf=5.0, neginf=-5.0), -5.0, 5.0)
        ctxs = np.clip(np.nan_to_num(ctxs), -5.0, 5.0)

        # ─── Percepção de bordas (obs edge/traffic): 11 raios ao final ───
        if self.obs_mode in ("edge", "traffic"):
            xs_all = np.zeros(n_drivers); ys_all = np.zeros(n_drivers)
            hdg_all = np.zeros(n_drivers)
            for i, drv in enumerate(drivers):
                phys_i = engine.physics.get_state(engine.handles[drv.driver_id])
                xs_all[i] = phys_i["x"]; ys_all[i] = phys_i["y"]
                hdg_all[i] = phys_i["heading_rad"]
            rays = self._cast_rays_batch(xs_all, ys_all, hdg_all, drv_s)
            tels = np.hstack([tels, rays.astype(np.float32)])

        # ─── Percepção de TRÁFEGO (obs 'traffic', FASE 4 v14): 12d finais ───
        # FÓRMULA ÚNICA do f1_env (compute_traffic_features) — nunca
        # reimplemente aqui (o kappa wrap duplicou bug 2× por esse caminho).
        if self.obs_mode == "traffic":
            from backend.model_train.f1_env import compute_traffic_features
            traf = np.zeros((n_drivers, 12), dtype=np.float32)
            for i in range(n_drivers):
                others = [(drv_s[j], drv_signed[j], drv_v[j])
                          for j in range(n_drivers) if j != i]
                traf[i] = compute_traffic_features(
                    drv_v[i], drv_s[i], self._half_width,
                    self._track_len_s, others)
            tels = np.hstack([tels, traf])

        # REALISMO-1 C1-B: a flag só existe no caminho composite.
        if (self.LAUNCH_STEER_MUTE_ENABLED
                and not (getattr(self, "_composite_np", None) is not None
                         and self.obs_mode == "traffic")):
            raise RuntimeError("--launch-steer-mute requer profile composite")
        # v15 FASE 4: COMPOSITE — quando o modo é traffic com composite ativo,
        # a ação = tanh(m_solo + g·r), NÃO o forward solo direto
        if (getattr(self, "_composite_np", None) is not None
                and self.obs_mode == "traffic"):
            from backend.model_train.residual_gated import (gate_value,
                                                             build_residual_input)
            # m_solo PRÉ-tanh (forward_linear)
            m_solo = self.actor.forward_linear(tels[:, :34], ctxs, t_ids, c_ids)
            n_drv = len(drivers)
            res_in = np.zeros((n_drv, 16), dtype=np.float32)
            gates = np.zeros(n_drv, dtype=np.float32)
            for i, drv in enumerate(drivers):
                # v_ego e d_ahead_min da MESMA fórmula do eval (obs canais)
                v_ego = float(tels[i, 0]) * 100.0
                tf_feats = tels[i, 34:46]  # 12d de tráfego
                d_min = None
                for k in range(3):
                    if tf_feats[4 * k + 3] > 0.5:
                        d = tf_feats[4 * k] * 100.0
                        if d_min is None or d < d_min:
                            d_min = d
                g = gate_value(v_ego, d_min)
                # SANIDADE-0 NIT N1 (review ANTI-D3-1): guard REPROVADO no gate
                # (hesit 12 vs 3; cc 752->1520; 9/10 disparos na LARGADA) —
                # isolado atrás de --pguard, DEFAULT OFF. Com a flag off este
                # bloco NÃO roda: g segue NOMINAL (comportamento bit-idêntico
                # à F4v15) e o instrumento volta a carregar o gate nominal.
                if self.PGUARD_ENABLED:
                    # ANTI-D3-1 (prereg 57a9342): PROGRESS-GUARD com fade
                    # gate->base. g>0,01 + Δcum<0,5m por N=5 ticks (tick
                    # lógico 0,1s = 0,5s) -> fade linear de g_eff a 0 em F=5;
                    # retoma ao reprogredir >=0,5 m.
                    pg = self._pguard_state.setdefault(
                        drv.driver_id,
                        dict(no_prog=0, fade=0.0, last_cum=None))
                    cum = float(engine.cum_dist_m.get(drv.driver_id, 0.0))
                    if pg['last_cum'] is None:
                        pg['last_cum'] = cum
                    delta = cum - pg['last_cum']
                    pg['last_cum'] = cum
                    if g > 0.01:
                        if delta < 0.5:
                            pg['no_prog'] += 1
                        else:
                            pg['no_prog'] = 0
                            pg['fade'] = 0.0
                        if pg['no_prog'] >= 5:
                            pg['fade'] = min(1.0, pg['fade'] + 1.0 / 5.0)
                        g_eff = g * (1.0 - pg['fade'])
                    else:
                        pg['no_prog'] = 0
                        pg['fade'] = 0.0
                        g_eff = g
                    g = g_eff  # instrumento: g EFETIVO pós-fade (desvio divulgado)
                kap_ahead = float(tels[i, 11]) / 25.0  # obs10 = κ@10m × 25
                ps, pl = self._res_prev.get(drv.driver_id, (0.0, 0.0))
                res_in[i] = build_residual_input(tf_feats, v_ego, kap_ahead, ps, pl)
                self._res_in_last[drv.driver_id] = res_in[i].copy()
                gates[i] = g
            # residual forward (NumPy)
            r = self._composite_np.residual_forward_only(res_in)
            a = np.tanh(m_solo + gates[:, None] * r)
            # REALISMO-1 C1-B: mute SOMENTE do steer dentro de D_L.
            # O long continua exatamente m_solo_long + g·r_long.
            if self.LAUNCH_STEER_MUTE_ENABLED:
                for i, drv in enumerate(drivers):
                    active = self._launch_steer_mute_step(
                        drv.driver_id, drv_s[i], drv_lat[i], engine.sim_ts)
                    a[i] = self._apply_launch_steer_mute(
                        a[i], m_solo[i], active)
            # instrumento: registra gate e |r| por driver
            for i, drv in enumerate(drivers):
                self._res_gate[drv.driver_id] = float(gates[i])
                self._res_norm[drv.driver_id] = float(np.linalg.norm(r[i]))
                self._res_prev[drv.driver_id] = (float(np.clip(a[i, 0], -1, 1)),
                                                   float(np.clip(a[i, 1], -1, 1)))
            preds = a  # substitui o forward solo pela ação composite
        else:
            # Solo puro: trunca a telemetria ao que o ator espera
            # (input_dim − ctx 2 − emb 12). Ex.: race sem residual NPZ roda
            # o v10 edge (48d) sobre as 34d de edge da obs traffic — o mesmo
            # slice que o composite faz no m_solo.
            tel_dim = self.actor.input_dim - 14
            preds = self.actor.forward(tels[:, :tel_dim], ctxs, t_ids, c_ids)

        actions = []
        for i in range(n_drivers):
            phys   = engine.physics.get_state(engine.handles[drivers[i].driver_id])
            speed  = phys["speed_mps"]
            th, brk, steer_rad = self._action_to_controls(preds[i], speed)
            # v15 R8 — steer-governor: cap do COMANDO da política por κ@10m
            # (tels[i,10] = κ@10m × 25). Atua ANTES da composição — o rejoin
            # bearing sobrescreve steer_rad quando off-track (ISENTO), e
            # recovery/blocked não tocam esterço.
            if self.steer_gov == "cap":
                k_prev = max(0.0, float(tels[i, 10])) / 25.0
                cap = self.STEER_GOV_K_COMP * math.atan(
                    self.STEER_GOV_WHEELBASE_M * k_prev)
                clipped = abs(steer_rad) > cap
                self.last_steergov[drivers[i].driver_id] = int(clipped)
                if clipped:
                    self._steergov_clips[drivers[i].driver_id] = \
                        self._steergov_clips.get(drivers[i].driver_id, 0) + 1
                    steer_rad = float(np.clip(steer_rad, -cap, cap))
            # registra ação anterior p/ a próxima observação (obs v2)
            a = np.asarray(preds[i], dtype=np.float64).ravel()
            if a.size >= 3:
                self._prev_actions[drivers[i].driver_id] = (float(np.clip(a[2], -1, 1)),
                                                            float(np.clip(a[0], 0, 1) - np.clip(a[1], 0, 1)))
            else:
                self._prev_actions[drivers[i].driver_id] = (float(np.clip(a[0], -1, 1)),
                                                            float(np.clip(a[1], -1, 1)))

            # ==================================================================
            # COMPOSIÇÃO DE CONTROLES — precedência explícita (investigação
            # "carros parados até serem empurrados"):
            #   5. policy    — base (th/brk/steer da rede)
            #   4. governor  — freio de curva (v = sqrt(A_lat/kappa) à frente)
            #   3. rejoin    — fora do asfalto: esterço p/ centro + teto de vel.
            #   2. recovery  — imobilizado: torque progressivo, freio ZERO,
            #                  saída SOMENTE com progresso físico real
            #   1. blocked   — segurança: contato c/ outro carro + parado ->
            #                  torque limitado (nunca arremeter)
            # A recuperação (2) é o fix do ciclo-limite: o anti-stall antigo
            # liberava ao cruzar 5 m/s, a política re-freava no tick seguinte
            # (curvas fora da distribuição de treino) e o carro alternava
            # parar/andar — 96 episódios de 0,3-1 s medidos em 600 s. Na
            # corrida visual isso era percebido como "parado até alguém
            # empurrar". last_authority registra quem definiu th/brk finais.
            # ==================================================================
            lat_dist = float(drv_lat[i])
            offtrack = lat_dist > self._half_width * self.OFFTRACK_FACTOR
            was_offtrack = self._was_offtrack.get(drivers[i].driver_id, False)
            handoff_active, handoff_steer, _handoff_reason = (
                self._rejoin_handoff_step(
                    drivers[i].driver_id,
                    was_offtrack=was_offtrack,
                    offtrack=offtrack,
                    s_live=float(drv_s[i]),
                    signed_lat=float(drv_signed[i]),
                    speed=speed,
                    heading_rad=float(phys["heading_rad"]),
                    live_x=float(phys["x"]), live_y=float(phys["y"]),
                    projection_x=float(drv_proj_x[i]),
                    projection_y=float(drv_proj_y[i]),
                    sim_ts=engine.sim_ts))
            if handoff_active:
                steer_rad = handoff_steer
            gov_braked = False

            # ---- 4. governor --------------------------------------------------
            # v15 FASE 1: modos instrumentados (race_diagnostic --gov):
            #   _gov_enabled=False           -> OFF (isola a contribuição)
            #   _v_plan_cap=VelocityProfile  -> teto = v_plan(s) (downforce +
            #     frenagem do professor; SEM constantes novas: mesmo trigger
            #     GOV_MARGIN, mesmo freio proporcional)
            # default (ambos ausentes) = comportamento histórico idêntico.
            v_safe = None
            if getattr(self, "_gov_enabled", True):
                if getattr(self, "_v_plan_cap", None) is not None:
                    v_safe = float(self._v_plan_cap.at(float(drv_s[i])))
                else:
                    kappa = self._kappa_ahead(float(drv_s[i]), self.GOV_HORIZON)
                    v_safe = min(self.V_GOV_MAX,
                                 max(self.V_GOV_MIN,
                                     math.sqrt(self.A_LAT_MAX / max(kappa, 1e-4))))
            if v_safe is not None and speed > v_safe * self.GOV_MARGIN:
                excess_frac = (speed - v_safe) / max(v_safe, 1.0)
                gov_brake   = float(np.clip(excess_frac * 0.8, 0.15, 1.0))
                th, brk, gov_braked = 0.0, max(brk, gov_brake), True

            # ---- 3a-bis. launch-cap (CICLO LARGADA L-1a; prereg a3b8ff0) ------
            # Teto de CHEGADA na largada: v_ceiling = k×v_plan(s) enquanto
            # t < T_max E s < s_cut (k=0,8; s_cut=2950; T_max=30 s — PINADOS).
            # Mesma lei de freio do governor (zero constantes novas). Composição
            # min() com o vplan: ceiling efetivo = min(v_plan×GOV_MARGIN,
            # k×v_plan) = k×v_plan. NUNCA lê clima; default OFF = bit-idêntico.
            cap_active = False
            # (reparo do smoke: `not offtrack` — v_plan é plano ON-TRACK; carro
            # fora é domínio do rejoin (teto 8 m/s), que SOBRESCREVE th/brk e
            # deixava FLAG FANTASMA launch_cap_active=1 com authority rejoin —
            # 3 violações de fase no smoke s0; mudança de comportamento ZERO)
            if (self.LAUNCH_CAP_ENABLED and self._v_plan_cap is not None
                    and not offtrack
                    and engine.sim_ts < self.LAUNCH_CAP_TMAX_S
                    and float(drv_s[i]) < self.LAUNCH_CAP_S_CUT):
                v_ceiling = self.LAUNCH_CAP_K * float(self._v_plan_cap.at(float(drv_s[i])))
                if speed > v_ceiling:
                    excess_cap = (speed - v_ceiling) / max(v_ceiling, 1.0)
                    th, brk = 0.0, max(brk, float(np.clip(excess_cap * 0.8, 0.15, 1.0)))
                    cap_active = True
            # telemetria EM FASE, keyed por carro (drivers[i] — lição stale-drv)
            self._cap_active[drivers[i].driver_id] = int(cap_active)

            # ---- 3a-bis2. anti-glue (SANIDADE-1b M3-v2; prereg 87214c7 §2) --
            # TETOS POR-REALIZAÇÃO (v1 MORTO: FAIL por margens; D4 = o
            # preventivo crônico era o custo dominante; D5 = breaker
            # incompetente no crawl/borda). Lógica compartilhada em
            # _anti_glue_step (neural E professor por herança). Default OFF
            # = bit-idêntico (estado inerte). Δlat com SINAL via drv_signed.
            drv_id = drivers[i].driver_id   # (o gap-check abaixo re-usa)
            glue_breaking = False
            if self.ANTI_GLUE_ENABLED and not offtrack:
                partner = None
                for j in range(n_drivers):
                    if j == i:
                        continue
                    dsj = (float(drv_s[j]) - float(drv_s[i])) % self._track_len_s
                    if dsj > self._track_len_s / 2.0:
                        dsj -= self._track_len_s
                    dlatj = float(drv_signed[j]) - float(drv_signed[i])
                    if (abs(dlatj) < self.ANTI_GLUE_NEAR_LAT
                            and abs(dsj) < self.ANTI_GLUE_NEAR_DS):
                        partner = (drivers[j].driver_id, dsj, dlatj,
                                   abs(float(drv_signed[j])), float(drv_v[j]))
                        break
                if partner is None:
                    th, brk, steer_rad, glue_breaking = self._anti_glue_step(
                        drv_id, None, 0.0, 0.0, speed, 0.0, 0.0, 0.0, True,
                        th, brk, steer_rad, False)
                else:
                    hw_off = self._half_width * self.OFFTRACK_FACTOR
                    th, brk, steer_rad, glue_breaking = self._anti_glue_step(
                        drv_id, partner[0], partner[1], partner[2], speed,
                        partner[4], abs(float(drv_signed[i])), partner[3],
                        partner[3] > hw_off, th, brk, steer_rad,
                        getattr(self, "_composite_np", None) is not None
                        and self.obs_mode == "traffic")

            # C2-B: handoff tem precedência sobre qualquer steering de gap/anti-glue.
            if handoff_active:
                steer_rad = handoff_steer

            # ---- 3a. rejoin-gap-check (CICLO ALAVANCA; prereg §3) -----------
            # Aplica-se quando o carro ESTÁ na borda on-track (saiu do off-track,
            # |lat| < 1,5×meia-largura) e ainda teria gap < X à frente. Crawl 4 m/s
            # mantendo o esterço de bearing ao ponto de reentrada. T_max=10s → solta.
            gap_hold = False
            fb_this_tick = False
            # REPARO keying (amenda A.1-ii): chave por carro = drivers[i]
            drv_id = drivers[i].driver_id
            c8_gap_hold = False
            if self.C8_REJOIN_ENABLED and not offtrack:
                c8_st = self._gapcheck_state.get(drv_id)
                near_edge = abs(lat_dist) < self._half_width * 1.5
                if c8_st is None and self._was_offtrack.get(drv_id, False) and near_edge:
                    c8_st = dict(tick0=int(engine.sim_ts * 10), hold=False, fb=False)
                    self._gapcheck_state[drv_id] = c8_st
                if c8_st is not None:
                    age = int(engine.sim_ts * 10) - c8_st["tick0"]
                    if age <= self.C8_GAP_WINDOW_TICKS:
                        c8_st["hold"] = self.c8_gap_blocked(
                            float(drv_s[i]),
                            tuple(float(drv_s[j]) for j in range(n_drivers) if j != i),
                            self._track_len_s,
                            self.C8_GAP_M)
                    else:
                        c8_st["hold"] = False
                        c8_st["fb"] = True
                    c8_gap_hold = bool(c8_st["hold"])
            if c8_gap_hold:
                # C8 gap-check is the strictest post-return gate.
                handoff_active, handoff_steer = False, None
            if self.REJOIN_GAP_ENABLED > 0 and not offtrack and not handoff_active and not c8_gap_hold:
                st = self._gapcheck_state.get(drv_id)
                # drv_lat é distância ABSOLUTA à linha central (loop de obs):
                # near_edge já é bilateral; abs() torna a intenção explícita.
                near_edge = abs(lat_dist) < self._half_width * 1.5
                # REPARO engate (amenda A.1-i): SÓ na transição off->on — o
                # "estado rejoin criado pelo bearing pós-excursão" do prereg
                # §3; a janela de 10 s é a histerese. _was_offtrack exige
                # excursão prévia: NUNCA engaja na largada nem em tráfego comum.
                if st is None and self._was_offtrack.get(drv_id, False) and near_edge:
                    self._gapcheck_state[drv_id] = dict(tick0=int(engine.sim_ts * 10), hold=False, fb=False)
                    st = self._gapcheck_state[drv_id]
                if st is not None:
                    age = int(engine.sim_ts * 10) - st['tick0']
                    if age > self.REJOIN_GAP_TMAX_TICKS:
                        if st['hold']:
                            st['fb'] = True   # fallback T_max: solta (uma vez)
                            st['hold'] = False
                            fb_this_tick = True   # REPARO: telemetria = transição 0->1 no tick do evento
                        # dentro da janela vencida: deixa o policy cuidar
                    else:
                        # gap à frente: menor Δs > 0 a qualquer outro carro
                        s_me = float(drv_s[i])
                        gap_f = None
                        for j in range(n_drivers):
                            if j == i:
                                continue
                            d = (float(drv_s[j]) - s_me) % self._track_len_s
                            if d <= 0 or d > self._track_len_s / 2:
                                d -= self._track_len_s if d > self._track_len_s / 2 else 0
                            if 0 < d < 2 * self.REJOIN_AHEAD_M + self.REJOIN_GAP_ENABLED * 3:
                                if gap_f is None or d < gap_f:
                                    gap_f = d
                        if gap_f is not None and gap_f < self.REJOIN_GAP_ENABLED:
                            st['hold'] = True
                            gap_hold = True
                        elif st['hold'] and not st['fb']:
                            # gap surgiu OU sem carro à frente → solta
                            st['hold'] = False
                    if st['hold']:
                        # crawl 4 m/s: mantém bearing ao ponto de reentrada
                        tx, ty = self._rejoin_target_point(
                            drv_id, float(drv_s[i]), drv_proj_x[i], drv_proj_y[i],
                            self.REJOIN_AHEAD_M)
                        bearing = math.atan2(ty - phys["y"], tx - phys["x"])
                        berr = self._wrap(bearing - float(phys["heading_rad"]))
                        steer_rad = float(np.clip(self.REJOIN_BEARING_GAIN * berr,
                                                  -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
                        if speed > self.REJOIN_GAP_CRAWL_MPS:
                            th, brk = 0.0, max(brk, 0.4)
                        else:
                            th, brk = self.REJOIN_THROTTLE, 0.0
            # expira o estado se a janela venceu sem hold
            if self.REJOIN_GAP_ENABLED > 0 and not offtrack and not gap_hold:
                st = self._gapcheck_state.get(drv_id)
                if st is not None and (int(engine.sim_ts * 10) - st['tick0']) > self.REJOIN_GAP_TMAX_TICKS:
                    self._gapcheck_state.pop(drv_id, None)
            # REPARO telemetria (amenda A.1-ii): EM FASE com a ação DESTE carro
            # NESTE tick, keyed por carro (todo tick — off-track incluído, hold=0).
            self._gap_hold[drv_id] = int(gap_hold)
            self._gap_fb[drv_id] = int(fb_this_tick)
            self._was_offtrack[drv_id] = bool(offtrack)

            # ---- 3. rejoin (fora do asfalto) ----------------------------------
            if offtrack:
                # estado do gap-check expira ao voltar para off-track (re-engata depois)
                if self.REJOIN_GAP_ENABLED > 0:
                    self._gapcheck_state.pop(drv_id, None)
                # SANIDADE-0 M2 (prereg 1007636 §1): PERCEPTIVE substitui o
                # bearing quando ON — alvo com ÂNGULO RASO (<=15°): ponto na
                # linha central a |lat|/tan(15°) m da projeção (clip 10-120);
                # cap de superfície: grama 6,0 m/s (asfalto = fim do
                # off-track libera o policy). Trigger é ESTADO (off-track),
                # NUNCA fade por progresso (lição ANTI-D3-1).
                if self.REJOIN_MODE == 'perceptive':
                    ahead_m = float(np.clip(
                        abs(lat_dist) / math.tan(
                            math.radians(self.REJOIN_PERCEPTIVE_ANGLE_DEG)),
                        self.REJOIN_PERCEPTIVE_AHEAD_MIN_M,
                        self.REJOIN_PERCEPTIVE_AHEAD_MAX_M))
                    rejoin_cap = self.REJOIN_PERCEPTIVE_V_GRASS
                else:
                    ahead_m = self.REJOIN_AHEAD_M
                    rejoin_cap = (
                        self.C8_GRASS_V_CAP_MPS
                        if self.C8_REJOIN_ENABLED else self.REJOIN_TARGET_MPS)
                # v15 FASE R3: esterço por BEARING ao ponto de re-entrada
                # (projeção + ahead_m ao longo da linha central).
                # Quadro FÍSICO (x, y, heading do mundo) — imune às
                # convenções de sinal da obs. Esterço + = virar à esquerda
                # (Y local = esquerda na física), logo steer = ganho·berr.
                tx, ty = self._rejoin_target_point(
                    drv_id, float(drv_s[i]), drv_proj_x[i], drv_proj_y[i], ahead_m)
                bearing = math.atan2(ty - phys["y"], tx - phys["x"])
                berr = self._wrap(bearing - float(phys["heading_rad"]))
                steer_rad = float(np.clip(self.REJOIN_BEARING_GAIN * berr,
                                          -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
                if speed > rejoin_cap * 1.2:
                    excess = (speed - rejoin_cap) / 6.0
                    th, brk = 0.0, max(brk, float(np.clip(excess, 0.3, 1.0)))
                else:
                    th, brk = self.REJOIN_THROTTLE, 0.0

            # ---- 2. recovery (imobilização) ------------------------------------
            rec = self._recovery_state.setdefault(drivers[i].driver_id, {})
            progress_m = float(engine.cum_dist_m.get(drivers[i].driver_id, 0.0))
            th, brk, rec_active = self._recovery_step(rec, speed, th, brk,
                                                      engine.sim_ts, progress_m,
                                                      offtrack)

            # REALISMO-1 C3-B: teto longitudinal pós-reentrada. O bloco vem
            # depois do rejoin/recovery para ser o último cap de velocidade;
            # só th/brk mudam, steer_rad permanece intocado.
            if c8_gap_hold:
                ramp_active, ramp_braked = False, False
            else:
                ramp_active, ramp_braked, th, brk = self._rejoin_ramp_step(
                    drivers[i].driver_id,
                    was_offtrack=was_offtrack,
                    offtrack=offtrack,
                    s_live=float(drv_s[i]),
                    speed=speed,
                    sim_ts=engine.sim_ts,
                    th=th,
                    brk=brk)

            # ---- 1. blocked (segurança) ----------------------------------------
            blocked = speed < 2.0 and self._contact_with_other_car(engine, drivers, i)
            if blocked:
                th = min(th, self.BLOCKED_THROTTLE)
                self._blocked_events[drivers[i].driver_id] = \
                    self._blocked_events.get(drivers[i].driver_id, 0) + 1

            # ---- 0. launch-stagger hold (CICLO LARGADA L-1b; prereg cd3ca5e) --
            # Enquanto t < release(slot) = (pos−1)×Δt (frente→trás): th=0,
            # brk=1, pose mantida (carro nasce parado; freio segura). Pós-
            # release CANÔNICO PURO: rec.clear() a cada tick held — sem isso
            # a recovery veria "encravado" por até 9 s e governaria a largada.
            # Última escrita em th/brk (acima de todas as camadas); NUNCA lê clima.
            held = False
            if self.LAUNCH_STAGGER_ENABLED:
                if not self._launch_grid_slots:
                    raise RuntimeError("--launch-stagger: ordem de largada do run "
                                       "ausente (fail-loud; nunca no-op silencioso)")
                slot = self._launch_grid_slots.get(drivers[i].driver_id)
                # release EM TICKS (prereg: "(pos-1)×Δt, em ticks: ×10") —
                # round() mata o erro de acumulação de sim_ts (+= 0.1 deixa
                # 0,99999… < 1,0 e segurava 1 amostra extra no boundary;
                # pego pelo release-exato do smoke, tick 60 vs 58 no slot 7)
                if slot is not None and int(round(engine.sim_ts * 10)) < (slot - 1) * 10:
                    th, brk = 0.0, 1.0
                    rec.clear()
                    held = True
            self._stagger_held[drivers[i].driver_id] = int(held)

            # ---- rótulo de autoridade final ----------------------------------
            # Precedência (prereg cd3ca5e): stagger (hold do grid) > segurança
            # (rejoin/recovery/blocked) > launch_cap > governor > policy.
            if held:
                authority = "stagger"
            elif glue_breaking:
                authority = "anti_glue"
            elif handoff_active:
                authority = "rejoin_handoff"
            elif gap_hold:
                authority = "rejoin_gap"
            elif blocked:
                authority = "blocked_contact"
            elif rec_active:
                authority = "recovery_rejoin" if offtrack else "recovery"
            elif ramp_braked:
                authority = "rejoin_ramp"
            elif offtrack:
                authority = "rejoin"
            elif cap_active:
                authority = "launch_cap"
            elif gov_braked:
                authority = "governor"
            else:
                authority = "policy"

            self.last_authority[drivers[i].driver_id] = authority
            actions.append((th, brk, steer_rad))
        return actions

    def _anti_glue_step(self, drv_id, p_id, ds, dlat, speed, v_partner,
                        slat_i_abs, slat_p_abs, partner_off, th, brk,
                        steer_rad, composite_scope):
        """SANIDADE-1b M3-v2 (prereg 87214c7 §2): anti-glue com TETOS POR-
        REALIZAÇÃO. Compartilhado por neural E professor (herança) — os
        chamadores resolvem o parceiro e passam os dados; devolve
        (th, brk, steer_rad, glue_breaking). Tick lógico 0,1 s.

        Prev (ii, escopo composite/professor — o chamador passa o escopo):
        |Δlat|<2,5 ∧ |Δs|<10 garantidos pelo chamador; teto 1,0 s por
        episódio contíguo -> cooldown 2,0 s; <=10 eps/par/corrida; só com
        |Δv|<8 m/s; REVERT se o próprio carro OU o parceiro está off-track.
        Breaker (iii, todos): >3 s colado (|Δs|<5,5), de trás cede (empate
        |Δs|<0,5 -> o de fora; desempate driver_id); teto 4,0 s por
        episódio -> DESISTE (uma vez por run contíguo); competência por
        velocidade: <25 m/s lift total + 0,4 rad (v1); acima th<=0,5 +
        0,15 rad aditivo (a 60+ m/s o grip satura — R7b — o yank 0,4
        lança pra fora); <=8 eps/par/corrida; REVERT alvo off-track."""
        st = self._glue_state.setdefault(
            drv_id, dict(partner=None, ticks=0, breaking=False,
                         prev_ticks=0, prev_cool=0, prev_eps={},
                         brk_ticks=0, brk_done_run=False, brk_eps={}))
        glue_breaking = False
        if partner_off:
            # REVERT (D5): nunca agir contra alvo na grama/borda — o domínio
            # do rejoin cuida do par; o breaker solta, o preventivo inerte.
            st.update(partner=None, ticks=0, prev_ticks=0, brk_done_run=False)
            st['breaking'] = False
            if st['prev_cool'] > 0:
                st['prev_cool'] -= 1
            return th, brk, steer_rad, glue_breaking
        # ---------- (iii) BREAKER ----------
        if abs(ds) < self.ANTI_GLUE_BREAK_DS:
            if st['partner'] != p_id:
                st.update(partner=p_id, ticks=0, brk_done_run=False)
            st['ticks'] += 1
            if (st['ticks'] > int(self.ANTI_GLUE_BREAK_S * 10)
                    and not st['breaking'] and not st['brk_done_run']):
                i_rear = 0.0 < ds < self._track_len_s / 2.0
                tie = abs(ds) < 0.5
                i_out = (slat_i_abs > slat_p_abs
                         or (slat_i_abs == slat_p_abs and drv_id < p_id))
                if ((i_rear or (tie and i_out))
                        and st['brk_eps'].get(p_id, 0)
                        < self.ANTI_GLUE_BRK_MAX_EPS):
                    st['breaking'] = True
                    st['brk_ticks'] = 0
                    st['brk_eps'][p_id] = st['brk_eps'].get(p_id, 0) + 1
        else:
            st.update(partner=None, ticks=0, brk_done_run=False)
        if st['breaking']:
            if (abs(dlat) > self.ANTI_GLUE_RELEASE_LAT
                    or abs(ds) > self.ANTI_GLUE_RELEASE_DS):
                st['breaking'] = False
            else:
                st['brk_ticks'] += 1
                if st['brk_ticks'] > self.ANTI_GLUE_BRK_MAX_EP_TICKS:
                    # teto 4 s: DESISTE — não persegue separação eterna no
                    # regime crawl/borda (D5); nova tentativa só noutro run
                    st['breaking'] = False
                    st['brk_done_run'] = True
                else:
                    if speed < self.ANTI_GLUE_BRK_V_FULL:
                        th, brk = 0.0, max(brk, 0.0)   # lift + 0,4 (v1)
                        steer_rad = float(np.clip(
                            -math.copysign(1.0, dlat)
                            * self.ANTI_GLUE_BREAK_STEER,
                            -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
                    else:
                        th = min(th, self.ANTI_GLUE_BRK_TH_SOFT)  # suave
                        steer_rad = float(np.clip(
                            steer_rad
                            - math.copysign(1.0, dlat)
                            * self.ANTI_GLUE_BRK_STEER_SOFT,
                            -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
                    glue_breaking = True
        elif composite_scope:
            # ---------- (ii) PREVENTIVO com tetos (D4: custo dominante) ----
            if st['prev_cool'] > 0:
                st['prev_cool'] -= 1
            dv = abs(speed - v_partner)
            away = float(np.clip(
                steer_rad - math.copysign(1.0, dlat)
                * self.ANTI_GLUE_OFFSET_STEER,
                -self.STEER_MAX_RAD, self.STEER_MAX_RAD))
            if st['prev_ticks'] > 0:
                if dv < self.ANTI_GLUE_PREV_DV_MAX:
                    st['prev_ticks'] += 1
                    if st['prev_ticks'] > self.ANTI_GLUE_PREV_MAX_EP_TICKS:
                        st['prev_ticks'] = 0
                        st['prev_cool'] = self.ANTI_GLUE_PREV_COOLDOWN_TICKS
                    else:
                        steer_rad = away
                        th = min(th, self.ANTI_GLUE_TH_CAP)
                else:
                    st['prev_ticks'] = 0    # |Δv| quebrou: fim do episódio
            elif (st['prev_cool'] == 0
                    and dv < self.ANTI_GLUE_PREV_DV_MAX
                    and st['prev_eps'].get(p_id, 0)
                    < self.ANTI_GLUE_PREV_MAX_EPS):
                st['prev_ticks'] = 1
                st['prev_eps'][p_id] = st['prev_eps'].get(p_id, 0) + 1
                steer_rad = away
                th = min(th, self.ANTI_GLUE_TH_CAP)
        return th, brk, steer_rad, glue_breaking

    def _v_gov_active(self, s, speed):
        """(diagnóstico) o governador está freando neste estado?"""
        kappa = self._kappa_ahead(float(s), self.GOV_HORIZON)
        v_safe = min(self.V_GOV_MAX, max(self.V_GOV_MIN,
                     math.sqrt(self.A_LAT_MAX / max(kappa, 1e-4))))
        return v_safe * self.GOV_MARGIN

    def _contact_with_other_car(self, engine, drivers, i) -> bool:
        """True se o chassis do carro i está em contato físico com OUTRO carro.

        CORREÇÕES da investigação de paradas:
        1. p.getContactData NÃO EXISTE neste pybullet (a chamada era
           silenciada pelo except e sempre retornava False — o cap de
           bloqueio nunca funcionou).
        2. getContactPoints retorna TUPLAS de 14 campos, não objetos:
           c[1]=bodyUniqueIdA, c[2]=bodyUniqueIdB, c[9]=força normal.
           getattr(c, 'bodyUniqueIdB') devolvia None -> nunca casava.
        """
        try:
            import pybullet as pb
            cid = engine.physics._client_id
            me = engine.handles[drivers[i].driver_id].chassis_id
            others = {engine.handles[d.driver_id].chassis_id
                      for j, d in enumerate(drivers) if j != i}
            for c in pb.getContactPoints(me, physicsClientId=cid):
                if len(c) >= 10 and (c[1] in others or c[2] in others):
                    if abs(float(c[9])) > 1.0:   # força normal significativa
                        return True
        except Exception:
            return False
        return False


def build_grid_drivers() -> List[Driver]:
    """Cria os 10 pilotos do grid de F1 com especificações e cores oficiais."""
    drivers: List[Driver] = []
    base_specs = CarSpecs(
        name="F1 Car",
        power_kw=740.0,
        mass_kg=798.0,
        fuel_capacity_kg=110.0,
        drag_coeff=0.85,
        downforce_coeff=3.2,
        frontal_area_m2=1.5,
        wheelbase_m=3.4,
    )

    for cfg in GRID_DRIVERS_CONFIG:
        drv = Driver(
            driver_id=cfg["id"],
            name=cfg["name"],
            car_specs=base_specs,
            starting_tyre_compound=cfg["compound"],
            starting_fuel_pct=1.0,
        )
        setattr(drv, "color_rgba", cfg["color"])
        setattr(drv, "label_color", cfg["label_color"])
        setattr(drv, "team_name", cfg["team"])
        drivers.append(drv)

    return drivers


def setup_pybullet_visuals(client_id: int) -> None:
    """Configura iluminação, sombras e esconde painéis laterais de debug no PyBullet."""
    if client_id is None or client_id < 0:
        return
    try:
        p.configureDebugVisualizer(p.COV_ENABLE_SHADOWS, 1, physicsClientId=client_id)
        p.configureDebugVisualizer(p.COV_ENABLE_GUI, 0, physicsClientId=client_id)
        p.configureDebugVisualizer(p.COV_ENABLE_SEGMENTATION_MARK_PREVIEW, 0, physicsClientId=client_id)
        p.configureDebugVisualizer(p.COV_ENABLE_DEPTH_BUFFER_PREVIEW, 0, physicsClientId=client_id)
        p.configureDebugVisualizer(p.COV_ENABLE_RGB_BUFFER_PREVIEW, 0, physicsClientId=client_id)
    except Exception:
        pass


def update_3d_car_labels(
    engine: SimulationEngine,
    drivers: List[Driver],
    label_ids: Dict[str, int],
    client_id: int,
    show_labels: bool = True,
) -> None:
    """Desenha e atualiza rótulos 3D com o nome do piloto e velocidade sobre cada carro."""
    if not show_labels or client_id is None or client_id < 0:
        return

    for drv in drivers:
        handle = engine.handles[drv.driver_id]
        phys = engine.physics.get_state(handle)
        speed_kmh = phys["speed_mps"] * 3.6
        pos = (phys["x"], phys["y"], 1.3)

        text = f"{drv.driver_id} | {speed_kmh:.0f} km/h"
        color = getattr(drv, "label_color", [1.0, 1.0, 1.0])

        existing_id = label_ids.get(drv.driver_id, -1)
        try:
            new_id = p.addUserDebugText(
                text=text,
                textPosition=pos,
                textColorRGB=color,
                textSize=1.1,
                replaceItemUniqueId=existing_id,
                physicsClientId=client_id,
            )
            label_ids[drv.driver_id] = new_id
        except Exception:
            pass


def print_leaderboard(engine: SimulationEngine, drivers: List[Driver], elapsed_s: float) -> None:
    """Imprime classificação em tempo real da corrida no terminal."""
    ranked = engine.ranked_drivers()

    print("\033[H\033[J", end="")  # Limpa terminal (ANSI)
    print("=" * 80)
    print(f"🏁 GP DE INTERLAGOS - F1 SIMULATOR (10 CARROS) | Tempo de Simulação: {elapsed_s:.1f}s")
    print("=" * 80)
    print(f"{'POS':<4} {'PILOTO':<20} {'EQUIPE':<18} {'VOLTA':<6} {'VELOCIDADE':<12} {'PNEU':<10} {'DISTÂNCIA':<10}")
    print("-" * 80)

    for pos, drv in enumerate(ranked, start=1):
        state = engine.states[drv.driver_id]
        phys = engine.physics.get_state(engine.handles[drv.driver_id])
        speed_kmh = phys["speed_mps"] * 3.6
        dist_km = engine.cum_dist_m.get(drv.driver_id, 0.0) / 1000.0
        team = getattr(drv, "team_name", "F1")

        print(
            f"P{pos:<3} {drv.name:<20} {team:<18} {state.lap:<6} "
            f"{speed_kmh:>5.1f} km/h   {state.tyre.tyre_life:>5.1f}%     {dist_km:>6.2f} km"
        )
    print("=" * 80)
    print("🎮 Controles PyBullet: [0-9] Seguir Carro | [O] Overview | [F] Follow | [L] Labels | [ESPAÇO] Pausa | [Q] Sair")
    print("=" * 80)

def variedade_params(seed: int, n: int, n_cars: int = 10):
    """VARIEDADE-1 (prereg b237aeb §1): PRNG PRÓPRIO derivado de (seed, N) —
    sha256("<seed>//variedade//<N>", o padrão weather_rng_from_seed) — NUNCA
    o RNG global da sim. Devolve, por carro na ordem do grid, a tupla
    (d_long m, d_lat m, fator mu) das CONDIÇÕES INICIAIS; None com N<=0
    (inércia: nenhum código do caminho canônico roda)."""
    if n <= 0:
        return None
    import hashlib
    import random as _random
    digest = hashlib.sha256(f"{seed}//variedade//{n}".encode()).hexdigest()
    rng = _random.Random(int(digest, 16))
    return [(rng.uniform(-0.5, 0.5), rng.uniform(-0.3, 0.3),
             rng.uniform(0.98, 1.02)) for _ in range(n_cars)]


def place_grid(engine, track, drivers, spacing_m=9.0, lateral_m=1.9,
               layout: str = "f1", jitter=None):
    """Grid estilo F1 (5 fileiras x 2 colunas) ancorado na RETA mais longa que
    termina ANTES da linha de largada/chegada.

    Corrige o problema do grid nascer dentro da penúltima curva: antes ele era
    ancorado no waypoint da SF e caminhava para trás — e o trecho atrás da SF
    neste conjunto de waypoints é justamente o canto final (Junção-like).
    Aqui detectamos a reta contígua antes da SF e comprimimos o espaçamento se
    a reta for curta.

    SANIDADE-0 M1 (prereg 1007636 §1): layout='staggered' = 2 colunas com
    offset lateral ±2,5 m (Δlat 5,0 m > corredor 3,5 do professor). A
    alternativa ao 1-carro-por-fileira c/ gap 12 m é JUSTIFICADA por D1:
    grid_len 9×12+6 = 114 m > reta de 45 m antes da SF (aborto por
    construção). Determinístico; a ORDEM segue semeada por --variance grid.
    """
    race_progress = getattr(engine, "race_progress_m", None)
    if race_progress is not None:
        race_progress.clear()
    last_race_s = getattr(engine, "_race_last_s", None)
    if last_race_s is not None:
        last_race_s.clear()
    wps = np.array(track.waypoints, dtype=np.float64)
    if layout == "staggered":
        lateral_m = 2.5   # SANIDADE-0 M1: Δlat 5,0 m entre colunas (pin prereg)
    elif layout != "f1":
        raise ValueError(f"layout de grid desconhecido: {layout!r}")
    AB = np.roll(wps, -1, axis=0) - wps
    seg_len = np.hypot(AB[:, 0], AB[:, 1])
    seg_cum = np.concatenate([[0.0], np.cumsum(seg_len)])[:-1]
    track_len = float(seg_len.sum())
    seg_head = np.arctan2(AB[:, 1], AB[:, 0])

    def heading_at_s(s):
        s %= track_len
        j = int(np.searchsorted(seg_cum, s, side="right") - 1) % len(wps)
        return seg_head[j]

    def pose_at_s(s):
        s %= track_len
        j = int(np.searchsorted(seg_cum, s, side="right") - 1)
        t = (s - seg_cum[j]) / (seg_len[j] + 1e-9)
        x = wps[j, 0] + t * AB[j, 0]
        y = wps[j, 1] + t * AB[j, 1]
        yaw = math.atan2(AB[j, 1], AB[j, 0])
        nx, ny = -AB[j, 1] / (seg_len[j] + 1e-9), AB[j, 0] / (seg_len[j] + 1e-9)
        return x, y, yaw, nx, ny

    sf_s = seg_cum[track.start_finish_waypoint % len(wps)]
    front = (sf_s - 6.0) % track_len          # nariz da 1ª fila, 6 m antes da SF

    # Acha a reta CONTÍGUA terminando em `front`: caminha p/ trás até o heading virar
    h0 = heading_at_s(front)
    straight = 0.0
    for L in np.arange(5.0, 300.0, 5.0):
        dh = math.atan2(math.sin(h0 - heading_at_s(front - L)),
                        math.cos(h0 - heading_at_s(front - L)))
        if abs(dh) > 0.12:                    # >~7 graus = acabou a reta
            break
        straight = float(L)

    MIN_GRID_STRAIGHT_M = 40.0  # v15 FASE R: abaixo disso = pista errada
    grid_len = 4.0 * spacing_m + 6.0
    if straight < grid_len:
        spacing_m = max(6.0, (straight - 6.0) / 4.0)
        # v15 FASE R: reta < mínimo = PISTA ERRADA, não um problema de
        # espaçamento. No Interlagos frozen existe a reta oposta (~100+ m
        # antes da SF). 0 m ou < 40 m = o runner carregou uma pista
        # procedural/preset ou o SF está no meio de uma curva — ABORTO
        # (incidente 9099235: "largada em cima da curva").
        raise RuntimeError(
            f"ABORTO: reta antes da SF = {straight:.0f} m (< {MIN_GRID_STRAIGHT_M} m). "
            f"Isto é sinal de PISTA ERRADA (fallback procedural ou SF mal "
            f"posicionado), não um problema de espaçamento. Verifique a fonte "
            f"da pista e o start_finish_waypoint.")
    print(f"[Grid] reta antes da SF: {straight:.0f} m | grid ocupa {4.0*spacing_m+6.0:.0f} m")

    for i, drv in enumerate(drivers):
        row, side = i // 2, (1.0 if i % 2 == 0 else -1.0)
        # VARIEDADE-1 (prereg b237aeb §1): jitter de grid = CONDIÇÃO INICIAL
        # (±0,5 m long / ±0,3 m lat; folga §2). None (flag OFF) = bit-idêntico.
        d_long = d_lat = 0.0
        if jitter is not None:
            d_long, d_lat = float(jitter[i][0]), float(jitter[i][1])
        s = (front - row * spacing_m + d_long) % track_len
        x, y, yaw, nx, ny = pose_at_s(s)
        px, py = (x + nx * (side * lateral_m + d_lat),
                  y + ny * (side * lateral_m + d_lat))
        engine.physics.set_position(engine.handles[drv.driver_id],
                                    pos=(px, py, 0.5), yaw_rad=yaw, reset_vel=True)
        st = engine.states[drv.driver_id]
        st.position_x, st.position_y, st.heading_rad = px, py, yaw
        engine.last_pos[drv.driver_id] = (px, py)
        engine.cum_dist_m[drv.driver_id] = 0.0
        # hint de waypoint ressincronizado (bug da parede do wrap — ver track.py)
        if hasattr(engine, "prev_waypoint_idx"):
            _, wp_now = track.nearest_segment(px, py)
            engine.prev_waypoint_idx[drv.driver_id] = wp_now
    print("[Grid] 10 carros no grid estilo F1 (5 fileiras x 2 colunas, NA RETA)"
          + (f" | layout=staggered ±{lateral_m:.1f} m (SANIDADE-0 M1)"
             if layout == "staggered" else ""))

def resolve_race_randomization(seed: Optional[int], variance: Optional[str],
                               use_rule_controller: bool) -> Tuple[int, str]:
    """Use a new seed and varied grid by default for the rule-based race."""
    if seed is None:
        seed = secrets.randbits(32) if use_rule_controller else 0
    if variance is None:
        variance = "grid" if use_rule_controller else "off"
    return seed, variance


def run_race():
    parser = argparse.ArgumentParser(description="Simulação de Corrida F1 com 10 Carros no PyBullet")
    parser.add_argument("--laps", type=int, default=5, help="Número de voltas da corrida (default: 5)")
    parser.add_argument("--camera", type=str, default="follow", choices=["follow", "overview"], help="Modo inicial de câmera")
    parser.add_argument("--follow-driver", type=str, default="VER", help="Piloto a seguir na câmera inicial (ex: VER, NOR, LEC)")
    parser.add_argument("--variance", type=str, default=None,
                        help="Variância semeada (grid,compound); padrão grid no apex-rules; off fixa o grid")
    parser.add_argument("--steer-gov", type=str, default="off", choices=["off", "cap"],
                        help="v15 R8: steer-governor opt-in — cap do esterço da "
                             "política em 2,0×atan(L·κ@10m) (rejoin/recovery isentos)")
    parser.add_argument("--launch-steer-mute", action="store_true",
                        help="REALISMO-1 C1-B: mute somente o esterço do residual "
                             "na janela D_L; default OFF = byte-idêntico")
    parser.add_argument("--lat-offset-slots", action="store_true",
                        help="REALISMO-1 C6-B: desloca somente obs4 por slot; default OFF")
    parser.add_argument("--c8-rejoin", action="store_true",
                        help="C8-B: perfil de velocidade na grama + gap-check; default OFF")
    parser.add_argument("--weather", type=str, default="seeded", choices=["seeded", "fixed"],
                        help="PÓS-CICLO-2: seeded = rng do clima derivado do --seed (igual ao "
                             "race_diagnostic); fixed = kind travado (prob transição 0)")
    parser.add_argument("--seed", type=int, default=None,
                        help="Seed da corrida; sem ela, o apex-rules sorteia e exibe uma seed")
    parser.add_argument("--track", type=str, default="interlagos", help="Evento FastF1 (ex: 'interlagos', 'Monaco', 'Silverstone')")
    parser.add_argument("--year", type=int, default=2024, help="Ano da sessão FastF1")
    parser.add_argument("--session", type=str, default="R", help="Sessão FastF1 (R, Q, ...)")
    parser.add_argument("--no-gui", action="store_true", help="Rodar em modo headless sem janela 3D")
    parser.add_argument("--realtime", action="store_true", default=True, help="Sincronizar com tempo real")
    parser.add_argument("--hz", type=float, default=10.0, help="Frequência de lógica em Hz (default: 10.0)")
    parser.add_argument("--sub-steps", type=int, default=24, help="Sub-passos de física por tick (default: 24)")
    parser.add_argument("--obs-mode", type=str, default=None,
                        choices=["legacy", "edge", "traffic"],
                        help="esquema de observação do ator: legacy=23d | edge=34d | "
                             "traffic=46d (v14). Default: o do --profile")
    parser.add_argument("--profile", type=str, default=DEFAULT_PROFILE,
                        choices=list(PROFILES),
                        help="controlador da corrida: apex-rules (padrão), "
                             "race, quali ou traffic (neurais)")
    parser.add_argument("--actor", type=str, default=None,
                        help="Checkpoint .keras específico (sobrepõe o --profile)")
    parser.add_argument("--gov", type=str, default=None, choices=["on", "off", "vplan"],
                        help="v15 FASE 1 (ADOTADO): freio de segurança da camada de "
                             "corrida neural — vplan = teto v_plan | on = histórico | "
                             "off = sem governor (default vplan nos profiles neurais)")
    parser.add_argument("--grid", type=str, default="f1", choices=["f1", "staggered"],
                        help="SANIDADE-0 M1 (prereg 1007636): staggered = 2 colunas "
                             "±2,5 m (Δlat 5,0 m); default f1 = bit-idêntico. "
                             "Opt-in research, NÃO-GAITADO: o gate SANIDADE-0 "
                             "correu o bundle completo; FAIL (c60 942/1352 > 812); "
                             "configuração solo não medida até SANIDADE-1b")
    parser.add_argument("--rejoin", type=str, default="bearing",
                        choices=["bearing", "perceptive"],
                        help="SANIDADE-0 M2: perceptive = ângulo raso <=15° + "
                             "grama 6 m/s + gap X=20 (auto); default bearing. "
                             "Opt-in research, não-gaitado: solo MEDIDO no "
                             "SANIDADE-1b (comp s0: fora 28,0%% <= teto 29,9; cc "
                             "516 = -31%%; hesit 6) — adoção = dono")
    parser.add_argument("--rejoin-handoff", type=str, default=None,
                        choices=["off", "align"],
                        help="REALISMO-1 C2-B: handoff alinhado após off->on "
                             "(theta=20deg, margem=0,5m, teto=24s); "
                             "default align em race/composite e off nos demais perfis")
    ramp_group = parser.add_mutually_exclusive_group()
    ramp_group.add_argument("--rejoin-ramp", dest="rejoin_ramp",
                        action="store_true",
                        help="REALISMO-1 C3-B: teto longitudinal pós-reentrada "
                             "por 5,0 s; requer --gov vplan; "
                             "default ON em race/composite")
    ramp_group.add_argument("--no-rejoin-ramp", dest="rejoin_ramp",
                        action="store_false",
                        help="desliga explicitamente a rampa homologada de rejoin")
    parser.add_argument("--anti-glue", action="store_true",
                        help="SANIDADE-0 M3: fricção 0,01 + preventivo comp/prof "
                             "+ deadlock-breaker 3 s; default OFF. Opt-in "
                             "research, NÃO-GAITADO: o gate SANIDADE-0 correu o "
                             "bundle completo; FAIL por margens (17,8 > 16,5s; "
                             "1 deadlock s72); configuração solo não medida até "
                             "SANIDADE-1b")
    parser.add_argument("--modo", type=str, default="corrida",
                        choices=["corrida", "espectador"],
                        help="SANIDADE BUNDLE: espectador liga SÓ o mecanismo "
                             "verde (M2 rejoin perceptive; árvore 7afe4a8). "
                             "Atribuição solo MEDIDA no SANIDADE-1b (comp s0: "
                             "fora 28,0%% <= 29,9; cc 516; hesit 6; colado 16,4s "
                             "dead 0) — opt-in research, não-gaitado; adoção = "
                             "dono; defaults canônicos intactos")
    parser.add_argument("--variedade", type=int, default=0,
                        help="VARIEDADE-1 (prereg b237aeb): N>=1 deriva PRNG "
                             "proprio sha256(seed//variedade//N) e perturba "
                             "SO condições iniciais (jitter grid ±0,5m/±0,3m; "
                             "mu_nominal ×U[0,98,1,02] no spawn). Default 0 = "
                             "OFF = bit-idêntico ao canônico. MESMA (seed,N) "
                             "-> bit-idêntica; N diferente -> corrida "
                             "diferente. N<0 = erro")
    ramp_group.set_defaults(rejoin_ramp=None)
    args = parser.parse_args()
    prof = PROFILES[args.profile]
    use_rule_controller = prof.get("controller") == "apex-rules"
    args.seed, args.variance = resolve_race_randomization(
        args.seed, args.variance, use_rule_controller,
    )
    if use_rule_controller:
        if args.actor:
            parser.error("--actor não se aplica ao profile apex-rules")
        if args.obs_mode:
            parser.error("--obs-mode só se aplica aos profiles neurais")
        if args.gov:
            parser.error("--gov só se aplica aos profiles neurais")
        if args.steer_gov != "off" or args.c8_rejoin or args.modo != "corrida":
            parser.error("--steer-gov, --c8-rejoin e --modo são opções dos profiles neurais")
        if args.rejoin == "perceptive":
            parser.error("--rejoin só se aplica aos profiles neurais")
    else:
        args.gov = args.gov or "vplan"
    if args.rejoin_handoff is None:
        args.rejoin_handoff = "align" if args.profile in ("race", "composite") else "off"
    if args.rejoin_ramp is None:
        args.rejoin_ramp = args.profile in ("race", "composite")

    if args.lat_offset_slots and args.profile not in ("race", "composite", "race-blind"):
        parser.error("--lat-offset-slots requer profile race/composite/race-blind")
    if args.launch_steer_mute and not prof.get("residual_npz"):
        parser.error("--launch-steer-mute requer profile composite/race")
    if args.rejoin_handoff == "align" and not prof.get("residual_npz"):
        parser.error("--rejoin-handoff align requer profile composite/race")
    if args.rejoin_ramp and args.gov != "vplan":
        parser.error("--rejoin-ramp requer --gov vplan")
    actor_keras = None
    if not use_rule_controller:
        actor_keras = Path(args.actor) if args.actor else prof["keras"]
    # FASE 0.8 (v15): resolve pelo ALIAS do registry (MLflow) com fallback
    # para o caminho de arquivo — registry vazio/indisponível nunca quebra
    if not use_rule_controller and not args.actor:
        try:
            from backend.model_train.tracking import resolve_deploy
            r = resolve_deploy(args.profile)
            if r is not None and Path(r).exists():
                actor_keras = Path(r)
                print(f"[Model] registry: alias '{args.profile}' -> {actor_keras.name}")
        except Exception:
            pass  # fallback: caminho do PROFILES
    actor_npz = (actor_keras.with_name(actor_keras.stem + "_weights.npz")
                 if actor_keras is not None else None)
    obs_mode = args.obs_mode if args.obs_mode else prof.get("obs_mode")
    print(f"[Model] profile: {args.profile} — {prof['desc']}")
    if args.actor:
        print(f"[Model] --actor explícito sobrepõe o profile")
    if actor_keras is not None and not actor_keras.exists():
        raise SystemExit(f"[ERRO] checkpoint do profile '{args.profile}' não existe: "
                         f"{actor_keras}")

    # 1. Carrega pista e pilotos
    # Pista REAL via FastF1 (padrão: GP de São Paulo/Interlagos), com fallback
    # automático (evento pedido -> São Paulo -> preset local).
    print("[Setup] Carregando circuito via FastF1 (fallback: Interlagos)...")
    # v15 FASE R: pista SEMPRE da fonte frozen (fail-fast)
    from backend.model_train.f1_env import load_track_frozen
    track = load_track_frozen(args.track, strict=True)
    print(f"[Setup] pista FROZEN: {track.name} | {len(track.waypoints)} wp | "
          f"SF wp {track.start_finish_waypoint}")
    drivers = build_grid_drivers()
    # v15 R7a: variância semeada opt-in (cenário, nunca física) — mesmo
    # mecanismo/streams do race_diagnostic (domínio racevar).
    if getattr(args, 'variance', 'off') not in ('off', 'none', '0', ''):
        from backend.domain.racevar import (parse_variance,
                                             variance_rng_from_seed,
                                             assign_compounds, shuffled_order)
        vd = parse_variance(args.variance)
        if 'compound' in vd:
            pool = [d.starting_tyre_compound for d in drivers]
            cmap = assign_compounds(variance_rng_from_seed(args.seed, 'compound'),
                                    [d.driver_id for d in drivers], pool)
            for d in drivers:
                d.starting_tyre_compound = cmap[d.driver_id]
            print(f"[Setup] VARIÂNCIA compound: "
                  f"{ {k: v.value for k, v in cmap.items()} }")
        if 'grid' in vd:
            order = shuffled_order(variance_rng_from_seed(args.seed, 'grid'),
                                   len(drivers))
            drivers = [drivers[k] for k in order]
            print(f"[Setup] VARIÂNCIA grid: {[d.driver_id for d in drivers]}")

    # 2. Configura a Engine de Simulação
    sim_config = SimulationConfig(
        race_id="f1_10_cars_race",
        num_laps=args.laps,
        logic_step_hz=args.hz,
        physics_sub_steps=args.sub_steps,
        gui=not args.no_gui,
        camera_mode=args.camera,
        draw_track=True,
        realtime=args.realtime,
        random_seed=args.seed,
        track_progress_laps=True,
        input_stale_after_s=300.0,  # Neural controller publica a cada tick — sem stale
    )

    # PÓS-CICLO-2 PASSO 0: clima SEMEADO por seed no GUI (wiring igual ao
    # race_diagnostic — mesma derivação sha256 '<seed>//weather'; --weather
    # seeded|fixed). Antes: WeatherModel SEM rng (clima-loteria entre processos).
    from backend.domain.weather import weather_rng_from_seed, WeatherTransitionConfig
    from backend.domain import WeatherModel as _WM
    if args.weather == 'fixed':
        weather_rng = weather_rng_from_seed(0)
        weather_cfg = WeatherTransitionConfig.default(transition_prob_per_lap=0.0)
    else:
        weather_rng = weather_rng_from_seed(args.seed)
        weather_cfg = None
    weather_model = _WM(initial=BASE_CONDITIONS[WeatherKind.DRY],
                         config=weather_cfg, rng=weather_rng)
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers, weather_model=weather_model)
    # PÓS-CICLO-2 PASSO 0: bloco de IDENTIDADE (mesmo formato do race_diagnostic)
    import hashlib as _hl
    _actor_keras_name = (
        "não se aplica (controle por regras)" if use_rule_controller
        else getattr(actor_keras, 'name', str(actor_keras).split('/')[-1])
    )
    print(f"[gui-identity] pista FROZEN: {track.name} | {len(track.waypoints)} wp | "
          f"SF wp {track.start_finish_waypoint} | sha256 {getattr(track, 'frozen_sha256', '?')} | "
          f"clima={args.weather} (seed {args.seed}) | gov={args.gov or 'profile'} | profile={args.profile} | "
          f"ator={_actor_keras_name} | "
          f"grid={[d.driver_id for d in drivers]}")
    print("[Setup] Inicializando PyBullet e spawnando os 10 carros no grid de largada...")
    # SANIDADE-0 (prereg 1007636 §1): bundle ESPECTADOR — ÁRVORE aplicada ao
    # veredito do gate s70-73: M1 (PRIM-1 FAIL: c60 942/1352 > 812) e M3
    # (PRIM-3 FAIL: 1 deadlock >10s na s72; comp s73 17,8 > 16,5s) são
    # research-negativos e SAEM; o bundle embarca SÓ mecanismo verde (M2
    # rejoin perceptive — PRIM-2 4/4). Flags individuais permanecem p/
    # research; defaults canônicos intactos.
    if args.modo == "espectador":
        grid_layout, rejoin_mode_v, anti_glue_v = "f1", "perceptive", False
        rejoin_gap_v = 20.0   # M2: X=20 m (cotovelo do dossiê R13) auto
    else:
        grid_layout = getattr(args, "grid", "f1")
        rejoin_mode_v = getattr(args, "rejoin", "bearing")
        anti_glue_v = bool(getattr(args, "anti_glue", False))
        rejoin_gap_v = 20.0 if rejoin_mode_v == "perceptive" else 0.0
    if args.variedade < 0:
        parser.error("--variedade deve ser >= 0 (0 = OFF bit-idêntico)")
    # VARIEDADE-1 (prereg b237aeb §1): ICs por carro do PRNG próprio
    # (seed, N); N=0 -> None -> NENHUM código roda (inércia bit-idêntica).
    var_params = variedade_params(args.seed, args.variedade, len(drivers))
    var_jitter = [(a, b) for a, b, _ in var_params] if var_params else None
    engine.setup()
    place_grid(engine, track, drivers, layout=grid_layout, jitter=var_jitter)
    if var_params:
        for drv, (_, _, mu_f) in zip(drivers, var_params):
            engine.physics.scale_mu_nominal(drv.driver_id, mu_f)
        print(f"[Setup] VARIEDADE-1: N={args.variedade} "
              f"(PRNG proprio sha256(seed//variedade//N)) | "
              f"jitter ±0,5m/±0,3m | mu_nominal ×U[0,98,1,02] — "
              f"mesma (seed,N) = bit-idêntica; N diferente = corrida "
              f"diferente; --variedade 0 = canônico")
    if anti_glue_v:
        # M3(i): fricção chassis-chassis 0,05 -> 0,01 (rodas intactas)
        engine.physics.set_chassis_lateral_friction(0.01)
        print("[Setup] anti-glue ON: fricção chassis-chassis 0,01 "
              "(SANIDADE-0 M3)")
    print(f"[Setup] SANIDADE-0: grid={grid_layout} | rejoin={rejoin_mode_v} "
          f"| anti_glue={anti_glue_v} | rejoin_gap={rejoin_gap_v} "
          f"| launch_steer_mute={args.launch_steer_mute} "
          f"| rejoin_handoff={args.rejoin_handoff}")

    client_id = engine.physics._client_id
    if not args.no_gui:
        setup_pybullet_visuals(client_id)

    # 3. Seleciona o controlador do profile. O profile de regras não carrega
    # checkpoints nem passa pela inferência neural em lote.
    if use_rule_controller:
        from backend.engine import RuleBasedRaceController
        controller = RuleBasedRaceController(track, seed=args.seed)
        for drv in drivers:
            engine.set_controller(drv.driver_id, controller)
        print(f"[Controller] Apex Formula por regras | aleatoriedade semeada: {args.seed}")
    else:
        npz_path = ensure_npz_weights_exist(actor_keras, actor_npz)
        print(f"[Model] Ator: {actor_keras}")
        controller = NeuralRaceController(
            steer_gov=getattr(args, "steer_gov", "off"),
            launch_steer_mute=getattr(args, "launch_steer_mute", False),
            lat_offset_slots=getattr(args, "lat_offset_slots", False),
            lat_offset_profile=("composite" if prof.get("residual_npz") else "blind"),
            rejoin_handoff=getattr(args, "rejoin_handoff", "off"),
            rejoin_ramp=getattr(args, "rejoin_ramp", False),
            c8_rejoin=getattr(args, "c8_rejoin", False),
            rejoin_gap=rejoin_gap_v,
            rejoin_mode=rejoin_mode_v,
            anti_glue=anti_glue_v,
            weights_path=npz_path,
            mappings_path=DEFAULT_MAPPINGS_PATH,
            track=track,
            obs_mode=obs_mode,
        )
        if prof.get("residual_npz"):
            from backend.model_train.residual_gated import NumpyCompositeActor
            controller._composite_np = NumpyCompositeActor(str(npz_path),
                                                           str(prof["residual_npz"]))
            print(f"[Model] composite: residual={prof['residual_npz'].name} "
                  f"(solo congelado + residual gated)")
        controller._launch_grid_slots = {
            d.driver_id: i + 1 for i, d in enumerate(drivers)}
        if args.gov == "off":
            controller._gov_enabled = False
        elif args.gov == "vplan":
            from backend.model_train.velocity_profile import VelocityProfile
            controller._v_plan_cap = VelocityProfile(
                np.array(track.waypoints, dtype=np.float64), grip_mult=0.788,
                sf=0.80, ds_target=4.0, smooth_window_m=20.0)
        print(f"[Model] governor: {args.gov}")

    # 4. Configuração de Câmera e Visualização
    camera_mode = args.camera
    follow_idx = 0
    for idx, d in enumerate(drivers):
        if d.driver_id == args.follow_driver.upper():
            follow_idx = idx
            break

    if camera_mode == "follow" and not args.no_gui:
        engine.physics.set_follow_target(engine.handles[drivers[follow_idx].driver_id])

    label_ids: Dict[str, int] = {}
    show_labels = True
    paused = False

    wps = np.array(track.waypoints)
    dt = 1.0 / sim_config.logic_step_hz
    last_ui_print = 0.0

    print("\n🏁 TUDO PRONTO! CORRIDA DE 10 CARROS INICIADA! 🏁\n")
    engine.race_started = True
    authority_ticks = {}  # PC2: acumulado por tick

    try:
        while not engine.race_finished:
            t0 = time.time()

            # Processa eventos de teclado na interface do PyBullet
            if not args.no_gui and client_id is not None:
                keys = p.getKeyboardEvents(physicsClientId=client_id)
                for k, v in keys.items():
                    if v & p.KEY_WAS_TRIGGERED:
                        # Teclas '0' a '9': seleciona carro para seguir
                        if ord("0") <= k <= ord("9"):
                            car_num = 9 if k == ord("0") else (k - ord("1"))
                            if car_num < len(drivers):
                                follow_idx = car_num
                                camera_mode = "follow"
                                engine.physics.set_follow_target(engine.handles[drivers[follow_idx].driver_id])
                                print(f"[Câmera] Seguindo {drivers[follow_idx].name} ({drivers[follow_idx].driver_id})")

                        # Alterna para Overview
                        elif k in (ord("o"), ord("O")):
                            camera_mode = "overview"
                            engine.physics.set_follow_target(None)
                            xs = [w[0] for w in track.waypoints]
                            ys = [w[1] for w in track.waypoints]
                            cx, cy = (min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0
                            rad = max(max(xs) - min(xs), max(ys) - min(ys)) / 2.0
                            engine.physics.setup_overview_camera((cx, cy), rad)
                            print("[Câmera] Modo Overview Ativado")

                        # Alterna para Follow
                        elif k in (ord("f"), ord("F")):
                            camera_mode = "follow"
                            engine.physics.set_follow_target(engine.handles[drivers[follow_idx].driver_id])
                            print(f"[Câmera] Modo Follow Ativado: {drivers[follow_idx].name}")

                        # Alterna Rótulos 3D
                        elif k in (ord("l"), ord("L")):
                            show_labels = not show_labels
                            print(f"[Visual] Rótulos 3D: {'Ligados' if show_labels else 'Desligados'}")

                        # Pausa
                        elif k == ord(" "):
                            paused = not paused
                            print(f"[Simulação] {'Pausada' if paused else 'Retomada'}")

                        # Sair
                        elif k in (ord("q"), ord("Q"), 27):  # 27 = ESC
                            print("[Simulação] Encerrando corrida...")
                            engine.race_finished = True
                            break

            if paused:
                time.sleep(0.05)
                continue

            if not use_rule_controller:
                # Inferência neural em lote e publicação dos comandos.
                actions = controller.predict_batch(engine, drivers, wps, track_id=0)
                for i, drv in enumerate(drivers):
                    th, brk, steer = actions[i]
                    engine.set_driver_input(
                        drv.driver_id,
                        throttle=th,
                        brake=brk,
                        steering_yaw_rad=steer,
                    )

            # 3. Avança um tick físico
            engine._step_tick(dt, sim_config.physics_sub_steps)
            # PC2: authority acumulado POR TICK (comparável ao headless; o
            # Counter por carro media só o último estado — métricas diferentes)
            for _a in controller.last_authority.values():
                authority_ticks[_a] = authority_ticks.get(_a, 0) + 1

            # 4. Atualiza câmera e HUD 3D
            if not args.no_gui:
                if camera_mode == "follow":
                    engine.physics.update_camera()
                update_3d_car_labels(engine, drivers, label_ids, client_id, show_labels=show_labels)

            # 5. Placar no Terminal a cada 0.5s
            if engine.sim_ts - last_ui_print >= 0.5:
                print_leaderboard(engine, drivers, engine.sim_ts)
                last_ui_print = engine.sim_ts

            # 6. Sincronização em tempo real
            if args.realtime:
                elapsed = time.time() - t0
                if elapsed < dt:
                    time.sleep(dt - elapsed)

    except KeyboardInterrupt:
        print("\n[Simulação] Corrida interrompida pelo usuário.")
    finally:
        print("\n🏆 RESULTADO FINAL DA CORRIDA 🏆")
        print_leaderboard(engine, drivers, engine.sim_ts)
        # PÓS-CICLO-2 PASSO 0: resumo de authority% (instrumento aditivo)
        try:
            total = max(sum(authority_ticks.values()), 1)
            print("[authority% por tick] " + " | ".join(
                f"{k}: {100*v/total:.1f}%" for k, v in
                sorted(authority_ticks.items(), key=lambda kv: -kv[1])))
            if controller.REJOIN_RAMP_ENABLED:
                print(f"[rejoin-ramp] {controller.rejoin_ramp_summary()}")
        except Exception as e:
            print(f"[authority% por tick] indisponível: {e}")
        engine.physics.close()
        print("Simulação concluída com sucesso.")


if __name__ == "__main__":
    run_race()
