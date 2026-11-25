"""Perfil de velocidade físico (v_plan) — Fase 1, professor v2.

Computa v_plan(s) para CIRCUITO inteiro via passada forward-backward:
  1. v_curve(s): velocidade de curva com DOWNFORCE (resolve v² da equação
     v²·κ = mu_eff·(g + c/m·v²), que dá v² = mu_eff·g / (κ - mu_eff·c/m))
  2. Passada BACKWARD (frenagem): v(s) = min(v_curve(s), sqrt(v(s+ds)² + 2·a_brk·ds))
  3. Passada FORWARD (tração):  v(s) = min(v(s), sqrt(v(s-ds)² + 2·a_acc·ds))

Tudo derivado da FÍSICA REAL do simulador (mu_eff, downforce, drag, potência),
com um fator de segurança `sf` parametrizável. Substitui A_LAT_MAX constante,
V_TGT_MIN/MAX hardcoded e A_BRAKE_REF constante.

A curvatura é SUAVIZADA (média móvel + clamp) para eliminar a oscilação
±60 km/h vista em s≈1936 (janela de 20 m sobre segmentos de ~4 m).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple

import numpy as np


# Parâmetros físicos do simulador (LIDOS de physics.py, não duplicados)
class PhysicsParams:
    mass = 798.0
    g = 9.81
    rho = 1.225
    cl = 3.2          # downforce_coeff
    cd = 0.85         # drag_coeff
    area = 1.5        # frontal_area_m2
    mu = 1.8          # mu_nominal
    power_kw = 735.0
    brake_decel_max = 50.0  # m/s² (demanda; limitado por mu*Fz)

    @classmethod
    def c_downforce(cls):    # coeficiente de downforce: 0.5*rho*CL*A
        return 0.5 * cls.rho * cls.cl * cls.area

    @classmethod
    def c_drag(cls):         # coeficiente de drag: 0.5*rho*CD*A
        return 0.5 * cls.rho * cls.cd * cls.area

    @classmethod
    def a_lat(cls, v, grip_mult=1.0):
        """a_lat máxima com downforce: mu_eff * (mg + c_df*v²) / m."""
        mu_eff = cls.mu * grip_mult
        fz = cls.mass * cls.g + cls.c_downforce() * v * v
        return mu_eff * fz / cls.mass

    @classmethod
    def a_brake(cls, v, grip_mult=1.0):
        """Decel máxima: limitada por mu*Fz/m + drag (ajuda a frear)."""
        mu_eff = cls.mu * grip_mult
        fz = cls.mass * cls.g + cls.c_downforce() * v * v
        a_mu = mu_eff * fz / cls.mass
        a_drag = cls.c_drag() * v * v / cls.mass
        return a_mu + a_drag

    @classmethod
    def a_accel(cls, v, grip_mult=1.0):
        """Aceleração disponível: min(tração mu*Fz_rear, potência/v) - drag."""
        mu_eff = cls.mu * grip_mult
        fz_rear = 0.55 * (cls.mass * cls.g + cls.c_downforce() * v * v)
        f_traction = mu_eff * fz_rear
        f_power = cls.power_kw * 1000.0 / max(v, 5.0)
        f_drive = min(f_traction, f_power)
        f_drag = cls.c_drag() * v * v + cls.mass * cls.g * 0.015  # + rolling
        return max(0.0, (f_drive - f_drag) / cls.mass)

    @classmethod
    def v_curve(cls, kappa, grip_mult=1.0):
        """Velocidade de curva com downforce: resolve v²·κ = a_lat(v).

        v² = mu_eff·g / (κ - mu_eff·c/m)  [se κ > mu_eff·c/m; senão sem limite]
        """
        mu_eff = cls.mu * grip_mult
        c_m = cls.c_downforce() / cls.mass   # ~0.003684 1/m
        denom = kappa - mu_eff * c_m
        if denom <= 1e-6:
            return 200.0  # sem limite físico (curva rápida demais para o downforce importar)
        return math.sqrt(mu_eff * cls.g / denom)


def compute_kappa_profile(wps: np.ndarray, ds_target: float = 4.0,
                          smooth_window_m: float = 30.0) -> Tuple[np.ndarray, np.ndarray]:
    """Curvatura assinada suavizada ao longo da pista.

    Reamostra a polilinha em `ds_target` e computa kappa via diferença de
    heading central (janela de smooth_window_m — ELIMINA a oscilação de
    ±60 km/h vista com janela de 20 m).

    Retorna (s_arr, kappa_arr) — arrays de mesmo comprimento (fechado).
    """
    # comprimento de arco
    closed = np.vstack([wps, wps[:1]])
    seg_len = np.hypot(np.diff(closed[:, 0], axis=0), np.diff(closed[:, 1], axis=0))
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    total = cum[-1]

    # reamostra por arco
    n = max(20, int(total / ds_target))
    s_arr = np.linspace(0.0, total, n, endpoint=False)
    # interpolação linear ao longo dos segmentos
    idx = np.searchsorted(cum, s_arr, side='right') - 1
    idx = np.clip(idx, 0, len(seg_len) - 1)
    t = (s_arr - cum[idx]) / np.maximum(seg_len[idx], 1e-9)
    x = wps[idx, 0] * (1 - t) + wps[(idx + 1) % len(wps), 0] * t
    y = wps[idx, 1] * (1 - t) + wps[(idx + 1) % len(wps), 1] * t

    # heading em cada ponto (central difference)
    dx = np.roll(x, -1) - np.roll(x, 1)
    dy = np.roll(y, -1) - np.roll(y, 1)
    heading = np.arctan2(dy, dx)

    # kappa = Δheading / Δs (com wrapping)
    # heading[i] é a direção média do arco [i-1, i+1] (= heading no ponto i);
    # dh = heading[i+1]-heading[i] cobre EXATAMENTE 1 intervalo = ds_target.
    dh = np.roll(heading, -1) - heading
    dh = (dh + math.pi) % (2 * math.pi) - math.pi
    kappa_raw = dh / ds_target

    # suavização HÍBRIDA: média móvel + PRESERVAÇÃO DE SINAL.
    # A média sozinha pode INVERTER O SINAL de um hairpin entre curvas
    # de direção oposta (procedural 101: k_avg=−0,013 [DIREITA] onde
    # k_raw=+0,042 [ESQUERDA] — o professor esterçava para o lado errado).
    # O pico sozinho captura RUÍDO da spline em pistas reais (Interlagos
    # 139s vs 109s — 27% mais lento). O HÍBRIDO usa a média quando os
    # sinais CONCORDAM (caso normal, 99% das pistas reais) e o pico
    # quando DISCORDAM (hairpin procedural: reversão de direção).
    half_w = max(1, int(smooth_window_m / ds_target / 2))
    n_k = len(kappa_raw)
    # média móvel circular (comportamento original)
    kernel = np.ones(2 * half_w + 1) / (2 * half_w + 1)
    pad = np.concatenate([kappa_raw[-half_w:], kappa_raw, kappa_raw[:half_w]])
    k_avg = np.convolve(pad, kernel, mode='valid')
    # pico (maior |kappa| na janela)
    k_peak = np.empty(n_k)
    for i in range(n_k):
        ixs = [(i + k) % n_k for k in range(-half_w, half_w + 1)]
        window = kappa_raw[ixs]
        k_peak[i] = window[int(np.argmax(np.abs(window)))]
    # híbrido: usa o PICO quando (a) sinais discordam (reversão de direção
    # no hairpin procedural) OU (b) o pico é >2× a média E é significativo
    # (k>0.015 = R<67m — hairpin que a média dilui). Senão usa a média
    # (comportamento original das pistas reais: ratio tipicamente 1-1.5).
    sign_mismatch = np.sign(k_avg) != np.sign(k_peak)
    # ratio > 3: só features EXTREMAS (procedural hairpin ratio=3-7);
    # pistas reais têm ratio 1-1.5 mesmo nos ápices (Monaco 1.3-1.5)
    peak_dominant = (np.abs(k_peak) > 3.0 * np.abs(k_avg) + 0.01) & (np.abs(k_peak) > 0.02)
    use_peak = sign_mismatch | peak_dominant
    kappa = np.where(use_peak, k_peak, k_avg)

    # clamp (remove picos numéricos de splines)
    kmax_physical = 0.25  # R=4m é o mínimo físico plausível
    kappa = np.clip(kappa, -kmax_physical, kmax_physical)

    return s_arr, kappa


def compute_v_plan(s_arr: np.ndarray, kappa_arr: np.ndarray,
                   grip_mult: float = 1.0, sf: float = 0.85,
                   ds: Optional[float] = None) -> np.ndarray:
    """Forward-backward velocity profile com física real.

    Args:
        s_arr: posições de arco (m)
        kappa_arr: curvatura assinada suavizada
        grip_mult: multiplicador de aderência (0.75–1.0)
        sf: fator de segurança (fração do limite físico usado)
        ds: espaçamento entre pontos (default: derivado de s_arr)

    Returns:
        v_plan: velocidade alvo em cada ponto (m/s)
    """
    n = len(s_arr)
    if ds is None:
        ds = float(s_arr[1] - s_arr[0]) if n > 1 else 4.0
    v_plan = np.full(n, 200.0)

    # --- 1. limite de curva (sf adaptativo + cap para HAIRPINS extremos) ---
    # DUAS camadas de proteção para curvas extremas:
    # (a) sf adaptativo: decai em kappa > KAPPA_SF_FLOOR (pure pursuit tem
    #     atraso de reação que a física não modela).
    # (b) CAP DIRETO em hairpins kappa > KAPPA_EXTREME: o problema não é a
    #     física (a_lat 5,6 m/s² << limite 14), é o VETOR VELOCIDADE entrar
    #     desalinhado — a rotação do 4b assist (0,157 rad/tick a 6 m/s) não
    #     corrige a tempo e o carro DESLIZA lateralmente (medido em Monaco:
    #     lat +0,63 → −7,04 em 6 m de pista = quase sideways). A 4,5 m/s a
    #     rotação relativa é 2× mais rápida e o drift cai pela metade.
    KAPPA_SF_FLOOR = 0.10   # R=10m: abaixo disso sf cheio; acima, decai
    KAPPA_EXTREME = 0.12    # R<8,3m: cap DIRETO de velocidade
    V_HAIRPIN_CAP = 4.5     # m/s — máximo em hairpins extremos
    for i in range(n):
        k = abs(kappa_arr[i])
        if k > 1e-6:
            sf_i = sf * min(1.0, KAPPA_SF_FLOOR / max(k, KAPPA_SF_FLOOR))
            mu_s = PhysicsParams.mu * grip_mult * sf_i
            c_m = PhysicsParams.c_downforce() / PhysicsParams.mass
            denom = k - mu_s * c_m
            if denom > 1e-6:
                v_plan[i] = math.sqrt(mu_s * PhysicsParams.g / denom)
            # (cap direto removido: o problema não é a velocidade NO ápice,
            #  é o VETOR VELOCIDADE desalinhado na APROXIMAÇÃO — ver (2b) abaixo)
            # senão: sem limite (o downforce segura a curva em qualquer velocidade)

    # --- 2. passada BACKWARD (frenagem, com CÍRCULO DE ATRITO) ---
    # CÍRCULO DE ATRITO (bug de Monaco): durante a frenagem pré-curva, a
    # curvatura de ENTRADA já consome parte do orçamento de atrito. Sem
    # isso, o v_plan permite 15,8 m/s a 8 m do hairpin "freando a 11 m/s²",
    # mas a kappa ali já exige 14 m/s² LATERAL (total 18 >> 14 físico).
    # O carro entra largo e não recupera (medido: lat −2,6→−6,4 m).
    # Solução ITERATIVA (2-3 passos convergem): computa v_brake com freio
    # cheio, mede a_lat que ELE exige, reduz o freio disponível, refaz.
    for i in range(n - 2, -1, -1):
        v_next = v_plan[(i + 1) % n]
        k_here = abs(kappa_arr[i])
        # a_max avaliado em v_next (velocidade CONHECIDA do ponto seguinte,
        # já processado) — NÃO em v_plan[i] que ainda é o limite de curva
        # (possivelmente 200) e inflaria o downforce irrealisticamente.
        v_mid = v_next
        a_drag = PhysicsParams.c_drag() * v_mid * v_mid / PhysicsParams.mass
        v_brake = v_next
        for _ in range(4):  # itera: v_brake sobe, a_lat sobe, freio cai
            a_max_here = PhysicsParams.a_lat(0.5 * (v_next + v_brake), grip_mult) * sf
            a_lat_here = v_brake * v_brake * k_here if k_here > 1e-6 else 0.0
            a_brk_avail = math.sqrt(max(a_max_here * a_max_here - a_lat_here * a_lat_here, 0.0))
            a_brk = a_brk_avail + a_drag
            v_brake = math.sqrt(v_next * v_next + 2.0 * max(a_brk, 0.3) * ds)
        v_plan[i] = min(v_plan[i], v_brake)

    # --- 2b. ZONA DE APROXIMAÇÃO a hairpins extremos -------------------
    # O carro precisa entrar ALINHADO (vetor velocidade ~ tangente da pista).
    # A rotação por tick (omega = v·tan(steer)/L) é finita: a 6 m/s com 42°
    # de esterço, 90° de rotação leva ~1,3 s = ~8 m de pista. Se o carro
    # chega ao ápice a 6 m/s vindo de 15 m/s, o vetor ainda aponta 30-50°
    # para fora e o carro DESLIZA lateralmente (medido: lat +0,63→−7,04).
    # Solução: ESTENDER a velocidade do hairpin para trás por ~10m — o carro
    # já está lento e alinhado ANTES da curva começar.
    HAIRPIN_APPROACH_M = 10.0   # metros de zona lenta antes do hairpin
    n_appr = int(HAIRPIN_APPROACH_M / ds)
    for i in range(n):
        if abs(kappa_arr[i]) > KAPPA_EXTREME:
            # propaga v_plan[i] para trás (até n_appr pontos antes)
            v_here = v_plan[i]
            for j in range(1, min(n_appr + 1, i + 1)):
                idx = i - j
                if idx < 0: idx += n
                # velocidade permitida a j·ds antes: freando suavemente
                v_allow = math.sqrt(v_here * v_here + 2.0 * 3.0 * j * ds)  # 3 m/s²
                v_plan[idx] = min(v_plan[idx], v_allow)

    # fecho o loop: último ponto também é limitado pelo primeiro
    v_last = v_plan[0]
    for i in range(n - 1, max(n - 1 - int(200 / ds), -1), -1):
        v_next = v_plan[(i + 1) % n]
        a_brk = PhysicsParams.a_brake(v_next, grip_mult) * sf
        v_brake = math.sqrt(v_next * v_next + 2.0 * a_brk * ds)
        if v_brake < v_plan[i]:
            v_plan[i] = v_brake

    # --- 3. passada FORWARD (tração) ---
    # v(s) = min(v(s), sqrt(v(s-ds)² + 2·a_acc·ds))
    for i in range(1, n):
        v_prev = v_plan[i - 1]
        a_acc = PhysicsParams.a_accel(v_prev, grip_mult) * sf
        v_accel = math.sqrt(v_prev * v_prev + 2.0 * a_acc * ds)
        if v_accel < v_plan[i]:
            v_plan[i] = v_accel

    return np.clip(v_plan, 0.0, 200.0)


class VelocityProfile:
    """Wrapper com lookup O(1) por s (interpolação linear)."""

    def __init__(self, wps: np.ndarray, grip_mult: float = 1.0, sf: float = 0.85,
                 ds_target: float = 4.0, smooth_window_m: float = 30.0):
        self.s_arr, self.kappa_arr = compute_kappa_profile(wps, ds_target, smooth_window_m)
        self.v_plan = compute_v_plan(self.s_arr, self.kappa_arr, grip_mult, sf,
                                     ds=float(self.s_arr[1] - self.s_arr[0]))
        self.total_s = float(self.s_arr[-1] + (self.s_arr[1] - self.s_arr[0]))

    def at(self, s: float) -> float:
        """Velocidade alvo em s (m). Interpolação linear, O(1)."""
        s = s % self.total_s
        ds = self.s_arr[1] - self.s_arr[0]
        i = int(s / ds)
        if i >= len(self.v_plan) - 1:
            return float(self.v_plan[-1])
        t = (s - self.s_arr[i]) / ds
        return float(self.v_plan[i] * (1 - t) + self.v_plan[i + 1] * t)

    def kappa_at(self, s: float) -> float:
        """Curvatura suavizada em s (para debug/plot)."""
        s = s % self.total_s
        ds = self.s_arr[1] - self.s_arr[0]
        i = int(s / ds)
        return float(self.kappa_arr[min(i, len(self.kappa_arr) - 1)])

    @property
    def v_min(self) -> float:
        return float(self.v_plan.min())

    @property
    def v_max(self) -> float:
        return float(self.v_plan.max())
