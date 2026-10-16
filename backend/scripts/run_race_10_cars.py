#!/usr/bin/env python3
"""Corrida de Fórmula 1 com 10 Carros no PyBullet controlados por Modelo Neural.

Inicia uma simulação completa com 10 carros no grid de largada, interface 3D
do PyBullet com asfalto renderizado, câmera dinâmica (Overview / Follow),
rótulos de telemetria 3D sobre os carros e controle autônomo dos 10 pilotos
utilizando o modelo de rede neural multi-contexto.

A inferência neural é executada via motor NumPy com pesos compilados do modelo Keras,
eliminando conflitos de símbolos de LLVM/Mesa entre o TensorFlow e o OpenGL do PyBullet.

Uso:
    python backend/scripts/run_race_10_cars.py --laps 5 --realtime
    python backend/scripts/run_race_10_cars.py --camera follow --follow-driver VER
    python backend/scripts/run_race_10_cars.py --camera overview
"""

from __future__ import annotations

import argparse
import math
import os
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
# DEFAULT (v15 FASE 4b PROMOÇÃO APLICADA): 'race' = composite (solo v10
# congelado + residual gated). B3.1 verde: 223 contatos, 0 pós-larg, 103,4s,
# 0 hesit, 0,17% fora. race-blind preserva o v10 puro.
DEFAULT_PROFILE = "race"
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

    # Modos de observação
    EDGE_RAY_ANGLES_DEG = (-90.0, -72.0, -54.0, -36.0, -18.0, 0.0,
                             18.0, 36.0, 54.0, 72.0, 90.0)
    N_LIDAR_RAYS = len(EDGE_RAY_ANGLES_DEG)  # 11
    LIDAR_MAX_RANGE_M = 40.0
    LIDAR_WINDOW_SEGS = 30

    def __init__(self, weights_path: Path, mappings_path: Optional[Path] = None,
                 track=None, obs_mode: str = "legacy") -> None:
        print(f"[Model] Carregando pesos neurais (NumPy Engine) de: {weights_path.name}")
        self.actor = NumpyNeuralActor(weights_path)
        self.obs_mode = obs_mode

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
        self._res_gate = {}          # drv -> último gate (instrumento)
        self._res_norm = {}          # drv -> último |r| (instrumento)

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
            drv_v[i] = phys["speed_mps"]

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
                kap_ahead = float(tels[i, 11]) / 25.0  # obs10 = κ@10m × 25
                ps, pl = self._res_prev.get(drv.driver_id, (0.0, 0.0))
                res_in[i] = build_residual_input(tf_feats, v_ego, kap_ahead, ps, pl)
                gates[i] = g
            # residual forward (NumPy)
            r = self._composite_np.residual_forward_only(res_in)
            a = np.tanh(m_solo + gates[:, None] * r)
            # instrumento: registra gate e |r| por driver
            for i, drv in enumerate(drivers):
                self._res_gate[drv.driver_id] = float(gates[i])
                self._res_norm[drv.driver_id] = float(np.linalg.norm(r[i]))
                self._res_prev[drv.driver_id] = (float(np.clip(a[i, 0], -1, 1)),
                                                   float(np.clip(a[i, 1], -1, 1)))
            preds = a  # substitui o forward solo pela ação composite
        else:
            preds = self.actor.forward(tels, ctxs, t_ids, c_ids)

        actions = []
        for i in range(n_drivers):
            phys   = engine.physics.get_state(engine.handles[drivers[i].driver_id])
            speed  = phys["speed_mps"]
            th, brk, steer_rad = self._action_to_controls(preds[i], speed)
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

            # ---- 3. rejoin (fora do asfalto) ----------------------------------
            if offtrack:
                signed_lat = float(tels[i, 4]) * self._half_width  # obs v2: idx 4 = lat assinado
                correction = -float(np.sign(signed_lat)) * min(self.STEER_MAX_RAD,
                                                               0.3 + lat_dist / 40.0)
                steer_rad = correction
                if speed > self.REJOIN_TARGET_MPS * 1.2:
                    excess = (speed - self.REJOIN_TARGET_MPS) / 6.0
                    th, brk = 0.0, max(brk, float(np.clip(excess, 0.3, 1.0)))
                else:
                    th, brk = self.REJOIN_THROTTLE, 0.0

            # ---- 2. recovery (imobilização) ------------------------------------
            rec = self._recovery_state.setdefault(drivers[i].driver_id, {})
            progress_m = float(engine.cum_dist_m.get(drivers[i].driver_id, 0.0))
            th, brk, rec_active = self._recovery_step(rec, speed, th, brk,
                                                      engine.sim_ts, progress_m,
                                                      offtrack)

            # ---- 1. blocked (segurança) ---------------------------------------
            blocked = speed < 2.0 and self._contact_with_other_car(engine, drivers, i)
            if blocked:
                th = min(th, self.BLOCKED_THROTTLE)
                self._blocked_events[drivers[i].driver_id] = \
                    self._blocked_events.get(drivers[i].driver_id, 0) + 1

            # ---- rótulo de autoridade final ----------------------------------
            if blocked:
                authority = "blocked_contact"
            elif rec_active:
                authority = "recovery_rejoin" if offtrack else "recovery"
            elif offtrack:
                authority = "rejoin"
            elif gov_braked:
                authority = "governor"
            else:
                authority = "policy"

            self.last_authority[drivers[i].driver_id] = authority
            actions.append((th, brk, steer_rad))
        return actions

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
    ranked = sorted(
        drivers,
        key=lambda d: (
            engine.states[d.driver_id].lap,
            engine.cum_dist_m.get(d.driver_id, 0.0),
        ),
        reverse=True,
    )

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

def place_grid(engine, track, drivers, spacing_m=9.0, lateral_m=1.9):
    """Grid estilo F1 (5 fileiras x 2 colunas) ancorado na RETA mais longa que
    termina ANTES da linha de largada/chegada.

    Corrige o problema do grid nascer dentro da penúltima curva: antes ele era
    ancorado no waypoint da SF e caminhava para trás — e o trecho atrás da SF
    neste conjunto de waypoints é justamente o canto final (Junção-like).
    Aqui detectamos a reta contígua antes da SF e comprimimos o espaçamento se
    a reta for curta.
    """
    wps = np.array(track.waypoints, dtype=np.float64)
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

    grid_len = 4.0 * spacing_m + 6.0
    if straight < grid_len:
        spacing_m = max(6.0, (straight - 6.0) / 4.0)
        print(f"[Grid] aviso: reta antes da SF curta ({straight:.0f} m); "
              f"espacamento reduzido para {spacing_m:.1f} m")
    print(f"[Grid] reta antes da SF: {straight:.0f} m | grid ocupa {4.0*spacing_m+6.0:.0f} m")

    for i, drv in enumerate(drivers):
        row, side = i // 2, (1.0 if i % 2 == 0 else -1.0)
        s = (front - row * spacing_m) % track_len
        x, y, yaw, nx, ny = pose_at_s(s)
        px, py = x + nx * side * lateral_m, y + ny * side * lateral_m
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
    print("[Grid] 10 carros no grid estilo F1 (5 fileiras x 2 colunas, NA RETA)")

def run_race():
    parser = argparse.ArgumentParser(description="Simulação de Corrida F1 com 10 Carros no PyBullet")
    parser.add_argument("--laps", type=int, default=5, help="Número de voltas da corrida (default: 5)")
    parser.add_argument("--camera", type=str, default="follow", choices=["follow", "overview"], help="Modo inicial de câmera")
    parser.add_argument("--follow-driver", type=str, default="VER", help="Piloto a seguir na câmera inicial (ex: VER, NOR, LEC)")
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
                        help="checkpoint de DEPLOY (FASE 4): race=v10 padrão | "
                             "quali=v11b pace | traffic=v14 60d. Substitui o "
                             "default antigo por mtime (escolhia errado entre "
                             "3 candidatos)")
    parser.add_argument("--actor", type=str, default=None,
                        help="Checkpoint .keras específico (sobrepõe o --profile)")
    parser.add_argument("--gov", type=str, default="vplan", choices=["on", "off", "vplan"],
                        help="v15 FASE 1 (ADOTADO): freio de segurança da camada de "
                             "corrida — vplan = teto v_plan do professor (default do "
                             "produto; 103,4s vs 137,1s on, zero hesitações) | on = "
                             "histórico | off = sem governor")
    args = parser.parse_args()

    prof = PROFILES[args.profile]
    actor_keras = Path(args.actor) if args.actor else prof["keras"]
    # FASE 0.8 (v15): resolve pelo ALIAS do registry (MLflow) com fallback
    # para o caminho de arquivo — registry vazio/indisponível nunca quebra
    if not args.actor:
        try:
            from backend.model_train.tracking import resolve_deploy
            r = resolve_deploy(args.profile)
            if r is not None and Path(r).exists():
                actor_keras = Path(r)
                print(f"[Model] registry: alias '{args.profile}' -> {actor_keras.name}")
        except Exception:
            pass  # fallback: caminho do PROFILES
    actor_npz = actor_keras.with_name(actor_keras.stem + "_weights.npz")
    obs_mode = args.obs_mode if args.obs_mode else prof["obs_mode"]
    print(f"[Model] profile: {args.profile} — {prof['desc']}")
    if args.actor:
        print(f"[Model] --actor explícito sobrepõe o profile")
    if not actor_keras.exists():
        raise SystemExit(f"[ERRO] checkpoint do profile '{args.profile}' não existe: "
                         f"{actor_keras}")

    # 1. Carrega pista e pilotos
    # Pista REAL via FastF1 (padrão: GP de São Paulo/Interlagos), com fallback
    # automático (evento pedido -> São Paulo -> preset local).
    print("[Setup] Carregando circuito via FastF1 (fallback: Interlagos)...")
    track = resolve_track(track=args.track, year=args.year, session=args.session)
    drivers = build_grid_drivers()

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
        input_stale_after_s=300.0,  # Neural controller publica a cada tick — sem stale
    )

    weather_model = WeatherModel(initial=BASE_CONDITIONS[WeatherKind.DRY])
    engine = SimulationEngine(config=sim_config, track=track, drivers=drivers, weather_model=weather_model)
    print("[Setup] Inicializando PyBullet e spawnando os 10 carros no grid de largada...")
    engine.setup()
    place_grid(engine, track, drivers)

    client_id = engine.physics._client_id
    if not args.no_gui:
        setup_pybullet_visuals(client_id)

    # 3. Carrega o Controlador Neural (em NumPy, sem poluição de LLVM)
    npz_path = ensure_npz_weights_exist(actor_keras, actor_npz)
    print(f"[Model] Ator: {actor_keras}")
    controller = NeuralRaceController(
        weights_path=npz_path,
        mappings_path=DEFAULT_MAPPINGS_PATH,
        track=track,   # passa a pista: evita rebuild das tabelas a cada predict_batch
        obs_mode=obs_mode,   # do --profile (ou --obs-mode explícito)
    )
    # v15 FASE 1 (ADOTADO): fix da camada de corrida — o governor histórico
    # (A_LAT_MAX=14 sem downforce, SEM distância de frenagem) custava ~34s de
    # volta (137,1 -> 103,4s). O teto v_plan usa a MESMA fórmula do professor.
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

            # 1. Inferência Neural para os 10 Carros (NumPy puro, ultra rápido)
            actions = controller.predict_batch(engine, drivers, wps, track_id=0)

            # 2. Aplica os comandos em todos os carros
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
        engine.physics.close()
        print("Simulação concluída com sucesso.")


if __name__ == "__main__":
    run_race()
