"""Controlador clássico de referência (Pure Pursuit + planejador de velocidade).

Serve como BASELINE: separa problemas de física/percepção dos problemas de
aprendizado. Se este controlador não completa uma volta, o problema está na
pista ou na física — não no RL.

Também pode gerar demonstrações p/ Behavior Cloning.

Uso típico num teste ou script:
    env = F1MultiContextEnv(track='interlagos')
    ctrl = ReferenceController(env)
    obs, _ = env.reset()
    for _ in range(3000):
        action = ctrl.action()          # [steer, long] em [-1,1]²
        obs, r, term, trunc, info = env.step(action)
        if term or trunc:
            break
    assert info['completed_lap']
"""

from __future__ import annotations

import math
import numpy as np


def signed_dist_s(s_o: float, s_ego: float, track_len_s: float) -> float:
    """Distância AO LONGO DA PISTA com sinal (PASSO 1 v14, métrica de tráfego).

    DECISÃO DE MÉTRICA (documentada — test 3c do PASSO 1):
      A distância de tráfego correta é a distância ao longo da pista
      (arc-length) COM SINAL: positiva = o outro carro está À FRENTE,
      negativa = atrás. A distância EUCLIDIANA bruta marcaria um carro do
      outro lado de um hairpin a 10 m como "mais próximo" do que um carro
      30 m à frente na mesma reta — não é essa a relação que importa para
      car-following. O RANKING dos N carros mais próximos usa |dist_s|
      (o sinal entra no flag ahead(1|0), não no ranking); o professor de
      tráfego usa apenas carros com 0 < dist_s < D_AHEAD (só se segue quem
      está à frente).

    Wrap: o resultado vive em [-L/2, +L/2) — um carro 5 m ATRÁS do ego dá
    dist_s = -5 (e NÃO +L-5, como daria (s_o - s_ego) % L cru).
    """
    L = float(track_len_s)
    return ((s_o - s_ego + 0.5 * L) % L) - 0.5 * L


class ReferenceController:
    """Pure Pursuit geométrico + velocidade-alvo pela curvatura à frente.

    Parâmetros físicos alinhados aos do ambiente (ver f1_env.py):
    - esterço limitado por velocidade (mesma lei de steer_limit_rad);
    - velocidade alvo v = sqrt(A_LAT_MAX / |kappa|), com antecipação por
      distância de frenagem: procura a pior curva a uma distância alcançável
      dado o freio disponível.
    """

    # --- Parâmetros de TRÁFEGO (Fase 1 v14) ---------------------------
    D_AHEAD_M = 60.0        # distância de detecção do carro à frente
    D_FOLLOW_M = 25.0       # abaixo desta dist: siga atrás (proibido arriscar)
    V_MARGIN = 2.0          # margem de velocidade sobre o carro à frente
    LAT_OFFSET_MAX = 2.5    # deslocamento lateral máximo (m)
    OFFSET_SMOOTH = 0.15    # filtro 1ª ordem: novo = α·alvo + (1-α)·anterior
    # PASSO 0.2 (FASE 3 v14): o offset só dispara quando o carro à frente
    # está no MEU corredor lateral (|lat_outro − lat_ego| < LAT_CORRIDOR_M).
    # Motivo (evidência do gate): na largada, o líder mais próximo fica na
    # COLUNA OPOSTA do grid (Δlat = 3,8 m) e a regra antiga (só |lat_ahead|)
    # mandava o follower CRUZAR a pista — 258 contatos concentrados em t=
    # 1,2-47,8 s, todos entre pares de fileira. 3,5 m < 3,8 m faz pares de
    # colunas opostas NUNCA dispararem; líder na mesma coluna (Δ=0) dispara.
    # Lição Monaco aplicada: o professor que rotula a FASE 3 precisa estar
    # limpo na largada — rótulo ruim vira comportamento do aluno.
    LAT_CORRIDOR_M = 3.5    # largura do corredor lateral "ele me bloqueia"
    # FASE 6: líder PARADO (v < V_MIN_FOLLOW) NÃO gera v_cap de car-following.
    # Sem isso o professor rasteja a (0+V_MARGIN) m/s atrás de um carro
    # parado para sempre — o encravamento medido. Sem cap, o próprio v_plan
    # carrega o professor e o offset do corredor desvia do carro parado.
    # Pré-gate obrigatório: professor deve CONTORNAR fantasma parado sem contato.
    V_MIN_FOLLOW = 1.0      # m/s — abaixo disso o líder é obstáculo, não líder
    G_SAFE_M = 6.0        # v15 FASE 3: abaixo deste gap, o alvo fica ATRÁS
                          # do líder (reabre; o 'close' antigo nunca reabria)
    # --- FASE 2 (v15): ultrapassagem — constantes (uma máquina, estado por driver) ---
    LAT_SAME_LINE_M = 2.6   # 2.3: só é "líder" quem está NA MINHA linha — carro
                            # lateral (passador) NÃO gera v_cap/offset (anti-recíproco).
                            # CALIBRAÇÃO (medida nos testes): precisa ficar ACIMA do
                            # span do offset de follow (|Δlat| máx 2,5 — senão o
                            # follower com offset aberto perde o líder e oscila o
                            # cap) e ABAIXO da margem do PASS (2,75 — senão o
                            # ultrapassado vê o passador como líder). Janela 2,5-2,75.
    PASS_G_PREPARE_M = 45.0 # PREPARE: gap de entrada
    PASS_G_COMMIT_M = 30.0  # PREPARE→PASS: compromisso
    PASS_MARGIN_M = 2.75    # offset lateral alvo durante o PASS (≥2,5 m do alvo)
    PASS_AHEAD_DONE_M = 8.0 # PASS→RETURN: concluído ≥8 m à frente do alvo
    PASS_COOLDOWN_TICKS = 100  # sem nova tentativa após aborto/retorno
    PASS_KAPPA_MAX = 0.02  # só PREPARE/PASS em R>50 m (κ local baixo)
    KAPPA_OFFSET_FACTOR = 1.2  # κ da LINHA DE OFFSET ~ κ_central×1,2 (R 100→~83 m)
    # PASS-1: decisão experimental de passagem. Com a flag ON, o caminho
    # legado continua até o primeiro engajamento; OFF preserva a política.
    PASS_DECISION_GAP_MIN_M = 15.0
    PASS_DECISION_DV_MIN_MPS = 1.0
    PASS_DECISION_SAMPLES = 15       # amostras a 5 Hz = 3 s sustentados
    PASS_DECISION_ABORT_GAP_M = 8.0
    PASS_DECISION_ABORT_S = 8.0
    PASS_DECISION_PROGRESS_M = 0.5
    PASS_DECISION_NEARBY_M = 25.0
    PASS_DECISION_REJOIN_LOCK_S = 10.0
    # FASE 2b — Experimento 1: isolar a máquina. Com _overtake_machine_only,
    # o offset do corredor no FOLLOW é SUPRIMIDO (cap v_ahead+2 MANTIDO) e o
    # único caminho de ultrapassagem passa a ser a máquina _pass_layer.
    # Hipótese mensurável: PASS% > 0, passes 2-6, contatos pós-largada ~0.

    def __init__(self, env, wheelbase_m=3.4, a_lat_max=12.0, a_brake_max=12.0,
                 lookahead_gain=0.6, lookahead_min_m=5.0, lookahead_max_m=45.0,
                 speed_margin=0.93, velocity_profile=None, sf=0.80,
                 smooth_window_m=20.0, driver_id=None, pass_decision=False,
                 leader_yield=False, prof_control=False,
                 prof_control_kappa=None, prof_grip=False,
                 prof_grip_windows=None, prof_pace=False,
                 prof_pace_windows=None, prof_pace_kappa_inst=None,
                 prof_pace_eta="eta1"):
        # a_lat/a_brake CONSERVADORES: a física analítica (Pacejka + limites de
        # esterço por velocidade) entrega menos que os 25/30 teóricos na prática.
        self.env = env
        # FASE 2 v14: fantasmas do env compartilham o MESMO objeto env, cada
        # um com seu driver_id (default: o do próprio env — solo/DAgger atual)
        self.driver_id = driver_id if driver_id is not None else env.driver_id
        self.wheelbase = wheelbase_m
        self.a_lat_max = a_lat_max
        self.a_brake = a_brake_max
        self.k_ld = lookahead_gain
        self.ld_min = lookahead_min_m
        self.ld_max = lookahead_max_m
        self.margin = speed_margin
        # --- Professor v2 (Fase 1): perfil de velocidade FÍSICO -------------
        # Substitui o planejador interno (a_lat constante + V_TGT_MIN/MAX
        # hardcoded) por v_plan(s) pré-computado com downforce e forward-
        # backward pass. Elimina V_TGT_MIN=15 (que era 58% acima da física
        # em Monaco) e acelera curvas rápidas (a_lat cresce com downforce).
        if velocity_profile is not None:
            self.v_profile = velocity_profile
        else:
            from backend.model_train.velocity_profile import VelocityProfile
            self.v_profile = VelocityProfile(
                np.array(env.track.waypoints, dtype=np.float64),
                grip_mult=0.788, sf=sf,
                ds_target=4.0, smooth_window_m=smooth_window_m)
        self.use_v_plan = True
        # --- Estado de tráfego (Fase 1 v14) -------------------------------
        self._lat_offset = 0.0   # deslocamento lateral suavizado
        self.last_follow_mode = 'none'  # 'none' | 'cap' | 'close' (métrica do gate)
        self._last_pursuit = (0.0, 0.0)  # ponto de perseguição do último action()
        # FASE 2 (v15): máquina de ultrapassagem — estado POR DRIVER
        self._pass_state = 'FOLLOW'    # FOLLOW|PREPARE|PASS|RETURN|COOLDOWN
        self.last_pass_state = 'FOLLOW'  # log por tick (CSV do gate)
        self._pass_target = None       # (lat_ref_alvo, lado, ticks_fechando)
        self._pass_cooldown = 0
        self._pass_closing = 0
        self.PASS_DECISION_ENABLED = bool(pass_decision)
        self.LEADER_YIELD_ENABLED = bool(leader_yield)
        # PROF-CONTROL-1 (prereg 7fe656ac, Freeze 53ea581): prof_control=True
        # ativa feedforward cinemático arctan(L*kappa) + lookahead modulado
        # por curvatura (g = 1/(1 + c_ld*|kappa|)), c_ld derivado do
        # LAGO_ANATOMY.json pela regra §3. Default OFF = bit-idêntico ao
        # professor histórico (o caminho OFF não executa nada deste módulo).
        self.PROF_CONTROL_ENABLED = bool(prof_control)
        if self.PROF_CONTROL_ENABLED:
            from backend.model_train import prof_control as _prof_mod
            if prof_control_kappa is not None:
                # caminho do runner: κ perfil construído UMA vez pelo
                # ProfessorRaceController a partir de track.waypoints e
                # emprestado às instâncias (o adapter _RaceEnvView não
                # expõe .track)
                self._prof_kappa_s, self._prof_kappa_v = prof_control_kappa
            else:
                # uso direto com o env real (testes/DAgger standalone)
                from backend.model_train.prof_curva import _instantaneous_kappa_profile
                kappa_s_arr, kappa_signed_arr = _instantaneous_kappa_profile(
                    np.array(env.track.waypoints, dtype=np.float64), ds_target=4.0)
                self._prof_kappa_s = kappa_s_arr
                self._prof_kappa_v = kappa_signed_arr
            self._prof_c_ld = float(_prof_mod.derive_c_ld()["c_ld"])
            self._prof_delta_ff = _prof_mod.delta_ff
            self._prof_gain = _prof_mod.lookahead_gain_factor
        else:
            self._prof_kappa_s = None
            self._prof_c_ld = 0.0
            self._prof_delta_ff = None
            self._prof_gain = None
        # PROF-GRIP-1 (prereg 6568b9a8, Freeze 715c677): prof_grip=True ativa
        # o teto de pacing grip-sensível nas janelas canônicas de C01/C06/
        # C07/C08 — v_alvo = v_plan·min(1,sqrt(grip_atual/0,85))·sqrt(1/1,10),
        # grip_atual = tyre.grip_multiplier (fonte idêntica à coluna
        # telemetrada). Default OFF = bit-idêntico (caminho OFF não executa
        # nada deste módulo). Pacing-only: esterço intocado.
        self.PROF_GRIP_ENABLED = bool(prof_grip)
        if self.PROF_GRIP_ENABLED:
            from backend.model_train import prof_grip as _prof_grip_mod
            if prof_grip_windows is not None:
                self._prof_grip_windows = prof_grip_windows
            else:
                self._prof_grip_windows = _prof_grip_mod.corner_windows(
                    np.array(env.track.waypoints, dtype=np.float64))
            self._prof_grip_mod = _prof_grip_mod
        else:
            self._prof_grip_windows = None
            self._prof_grip_mod = None
        # PROF-PACE-1 (prereg 6568b9a8-família, Freeze 947c091): prof_pace=True
        # ativa o pacing preventivo grip_mode=FIXED (grip_ref=0,7895474400345001)
        # nas janelas canônicas de C01/C06/C07/C08 — v_alvo = v_target_cap
        # (0,93 + cap η EMBUTIDOS no perfil via prof_pace.py; SEM margin
        # adicional). Fora de Interlagos: no-op explícito. Default OFF =
        # bit-idêntico ao professor histórico (caminho OFF não executa nada).
        self.PROF_PACE_ENABLED = bool(prof_pace)
        self._prof_pace = None
        self._prof_pace_noop = False
        if self.PROF_PACE_ENABLED:
            from backend.model_train import prof_pace as _pp
            if prof_pace_windows is None:
                self._prof_pace_noop = True   # fora de Interlagos: no-op explícito
            elif prof_pace_kappa_inst is None:
                raise ValueError("prof_pace com janelas exige prof_pace_kappa_inst")
            else:
                self._prof_pace = _pp.build_capped(
                    self.v_profile.v_plan, self.v_profile.s_arr,
                    self.v_profile.kappa_arr, prof_pace_windows,
                    prof_pace_kappa_inst, prof_pace_eta)
        self._leader_yield_state = {
            'active': False, 'follower_id': None, 'started_s': None,
            'start_lat': None, 'target_lat': None,
        }
        self._leader_yield_stats = {
            'engaged': 0, 'consumed': 0, 'aborted': 0, 'attempts': [],
        }
        # Estado separado: com a flag OFF, a máquina legada acima é usada sem
        # ler nem alterar este estado.
        self._pass_decision_state = {
            'active': False, 'candidate_id': None, 'candidate_samples': 0,
            'target_id': None, 'started_s': None, 'start_lat': None,
            'side': 0.0, 'target_lat': None, 'lateral_progress_m': 0.0,
        }
        self._pass_decision_stats = {
            'opportunities': 0, 'engaged': 0, 'aborted_gap': 0,
            'aborted_timeout': 0, 'aborted_contact': 0,
            'aborted_rejoin': 0, 'aborted_target': 0, 'consumed': 0,
            'attempts': [],
        }

    # ------------------------------------------------------------------
    def _v_target(self, s, v_now):
        """Velocidade alvo em s.

        Professor v2: usa o v_plan pré-computado (física real com downforce,
        forward-backward pass). O v_plan JÁ incorpora a distância de frenagem
        na passada backward — não precisa de horizonte adicional aqui.
        """
        if getattr(self, 'use_v_plan', False):
            return self.v_profile.at(s)
        # Fallback: planejador antigo (a_lat constante) — mantido p/ compat.
        v_min_curve = 15.0
        brake_dist = max(0.0, (v_now ** 2 - v_min_curve ** 2)) / (2.0 * self.a_brake)
        horizon = max(80.0, v_now * 0.8 + brake_dist + 40.0)
        n = max(2, int(horizon // 4.0) + 1)
        ds = horizon / (n - 1)
        v_tgt = self.env_track_vmax()
        for i in range(1, n):
            kappa = abs(self.env_kappa(s + i * ds))
            if kappa > 1e-5:
                v_curve = math.sqrt(self.a_lat_max / kappa)
                v_allow = math.sqrt(v_curve ** 2 + 2.0 * self.a_brake * i * ds)
                v_tgt = min(v_tgt, v_allow)
        return min(self.env_track_vmax(), v_tgt)

    # ------------------------------------------------------------------
    def env_kappa(self, s):
        return self.env._kappa_signed(s)

    def _prof_kappa_local(self, s):
        """κ local instantânea ASSINADA em s (PROF-CONTROL-1 §2 do prereg).

        Perfil canônico de janela mínima (prof_curva) sobre os waypoints da
        pista frozen; nunca o perfil suavizado de 30 m. Só existe com a
        flag ON."""
        s_arr = self._prof_kappa_s
        total = float(s_arr[-1] + (s_arr[1] - s_arr[0]))
        return float(np.interp(s % total, s_arr, self._prof_kappa_v))

    def env_track_vmax(self):
        return 85.0  # mesmo V_TGT_MAX do env

    # ------------------------------------------------------------------
    def _traffic_adjust(self, s_ego, v_ego, lat_ego, traffic):
        """Car-following + offset lateral com base no carro à frente.

        Métrica: dist_s ASSINADA ao longo da pista (ver signed_dist_s) — só
        carros com 0 < dist_s < D_AHEAD são candidatos a "carro à frente".
        Registra self.last_follow_mode p/ a métrica do gate (% follow):
          'close' = colado (dist_s < D_FOLLOW), v_alvo = v_ahead
          'cap'   = fechando, v_alvo = v_ahead + V_MARGIN
          'none'  = sem tráfego relevante no alcance
        OFFSET (PASSO 0.2): só desloca o ponto de perseguição quando o líder
        está no MEU corredor lateral (|lat_ahead − lat_ego| < LAT_CORRIDOR_M)
        E perto da linha (|lat_ahead| < 0,6·hw — líder na borda deixa o
        centro livre). Fora do corredor: offset 0 (já estou lateralmente
        livre; cruzar a pista só gera contato — evidência da largada do gate).
        """
        self.last_follow_mode = 'none'
        if not traffic:
            return None, 0.0
        L = self.env._track_len_s
        best_gap, best_car = 1e9, None
        for (s_o, lat_o, v_o) in traffic:
            dist_s = signed_dist_s(s_o, s_ego, L)   # + = à frente (com wrap)
            # 2.3 (v15): SEGURANÇA — só é líder quem está NA MINHA linha
            # (|Δlat| < LAT_SAME_LINE_M). Carro LATERAL (passador ao meu lado)
            # não gera cap nem offset: sem isso o ultrapassado "desvia para
            # o mesmo lado" do passador (offset recíproco → colisão).
            if abs(lat_o - lat_ego) >= self.LAT_SAME_LINE_M:
                continue
            if 0.0 < dist_s < best_gap and dist_s < self.D_AHEAD_M:
                best_gap, best_car = dist_s, (s_o, lat_o, v_o)
        if best_car is None:
            return None, 0.0
        s_ahead, lat_ahead, v_ahead = best_car
        v_cap = None
        # FASE 6: líder PARADO é obstáculo a CONTORNAR, não líder a seguir
        if v_ego > v_ahead and v_ahead > self.V_MIN_FOLLOW:
            v_cap = v_ahead + self.V_MARGIN
            self.last_follow_mode = 'cap'
            if best_gap < self.D_FOLLOW_M:
                # v15 FASE 3 (0.2): ABAIXO do gap seguro, alvo ATRÁS do líder
                # (o gap REABRE; antes ficava v=v_ahead para sempre — contato
                # sustentado a 3,7 m medido em Monza)
                if best_gap < self.G_SAFE_M:
                    v_cap = max(v_ahead - 0.5, self.V_MIN_FOLLOW)
                    self.last_follow_mode = 'reopen'
                else:
                    v_cap = v_ahead  # colado: siga atrás
                    self.last_follow_mode = 'close'
        hw = float(getattr(self.env, '_half_width', 6.0))
        if (abs(lat_ahead - lat_ego) < self.LAT_CORRIDOR_M
                and abs(lat_ahead) < hw * 0.6):
            # líder no MEU corredor: desloca o ponto de perseguição p/ o
            # LADO OPOSTO ao dele (esquerda dele -> persegue à direita)
            offset_target = -math.copysign(self.LAT_OFFSET_MAX,
                                           lat_ahead if abs(lat_ahead) > 0.5 else 1.0)
        else:
            offset_target = 0.0
        return v_cap, offset_target

    # ------------------------------------------------------------------
    # FASE 2 (v15): máquina de ultrapassagem — FOLLOW→PREPARE→PASS→RETURN
    # → cooldown. Estado por driver (cada carro tem seu controller). O cap
    # longitudinal (v_ahead+2) é o que impede fechar o gap: no PASS ele é
    # LEVANTADO (alvo = v_plan PRÓPRIO) e religado só no RETURN concluído.
    # O mecanismo lateral é o MESMO _lat_offset (filtro 1ª ordem) — não há
    # segundo mecanismo. ABORTOS → FOLLOW com cooldown.
    # ------------------------------------------------------------------
    def _pass_layer(self, s_ego, v_ego, lat_ego, traffic, v_plan_here):
        """Retorna (levantar_cap: bool, offset_target: float|None, estado)."""
        L = self.env._track_len_s
        # alvo = líder válido mais próximo (mesma linha — 2.3)
        tgt = None
        for (s_o, lat_o, v_o) in traffic:
            d = signed_dist_s(s_o, s_ego, L)
            if (0.0 < d < self.PASS_G_PREPARE_M
                    and abs(lat_o - lat_ego) < self.LAT_SAME_LINE_M):
                if tgt is None or d < tgt[0]:
                    tgt = (d, lat_o, v_o)
        if self._pass_cooldown > 0:
            self._pass_cooldown -= 1
            self._pass_state = 'COOLDOWN'
            return False, None, self._pass_state

        kappa_local = abs(self.env_kappa(s_ego + 20.0))
        # --- RETURN: volta suave à linha (cap religado, offset -> 0) -------
        if self._pass_state == 'RETURN':
            if abs(lat_ego) < 0.6:
                self._pass_state = 'COOLDOWN'
                self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                self._pass_target = None
                return False, None, self._pass_state
            return False, 0.0, self._pass_state
        # --- PASS: cap LEVANTADO; offset = lado do alvo + margem ---------
        if self._pass_state == 'PASS' and self._pass_target is not None:
            lat_ref, lado, _ = self._pass_target
            d_t, lat_o, v_o = (tgt if tgt else (None, lat_ref, 0.0))
            # abortos: alvo saiu da linha dele > 1,0 m | gap fechando
            if d_t is not None and abs(lat_o - lat_ref) > 1.0:
                self._pass_state = 'COOLDOWN'
                self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                return False, 0.0, 'ABORT->COOLDOWN'
            if d_t is None:
                # alvo não é mais líder válido à frente <G_p: ou passamos ou sumiu
                ds = [signed_dist_s(s_o2, s_ego, L) for (s_o2, la2, va2) in traffic
                      if abs(la2 - lat_ref) < 2.0 and la2 is not None
                      and abs(signed_dist_s(s_o2, s_ego, L)) < 60.0]
                # FASE 2c: mesma correção de sinal do 2º sítio — o alvo
                # deixou de ser líder VÁLIDO (abrimos lateral, |Δlat|>2,6);
                # concluído só quando NENHUM carro da linha dele está a menos
                # de 8 m de nós (era `ahead > 8`, que disparava RETURN com o
                # alvo ainda A0 LADO — a manobra abortava no nascedouro).
                if ds and min(abs(d) for d in ds) > self.PASS_AHEAD_DONE_M:
                    self._pass_state = 'RETURN'   # concluído: alvo ≥8 m atrás
                    return False, 0.0, self._pass_state
            elif d_t < -self.PASS_AHEAD_DONE_M:
                # FASE 2c: BUG INVERTIDO corrigido com evidência da medição.
                # Era `d_t > PASS_AHEAD_DONE_M` (alvo 8 m À FRENTE = estado
                # do commit!) → RETURN disparava no tick seguinte ao commit e
                # a manobra nunca acontecia (PASS durava 1-2 ticks; Δlat+3s
                # medido ~0-0,6 m). Conclusão correta: alvo ≥8 m ATRÁS.
                self._pass_state = 'RETURN'
                return False, 0.0, self._pass_state
            # Exp3: janela de reta também no PASS (curva chegando = aborta)
            need_now = abs(d_t if d_t is not None else 8.0) + 8.0 + 40.0
            window_now = all(self.v_profile.at(s_ego + dd) >= 0.9 * max(v_ego, 10.0)
                             for dd in np.arange(0.0, need_now, 20.0))
            if not window_now:
                self._pass_state = 'COOLDOWN'
                self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                return False, 0.0, 'ABORT->COOLDOWN'
            # κ da LINHA DE OFFSET (física): se a curva aperta e v excede o
            # allow da linha deslocada, aborta por segurança
            from backend.model_train.velocity_profile import PhysicsParams
            k_off = kappa_local * self.KAPPA_OFFSET_FACTOR
            v_allow_off = PhysicsParams.v_curve(k_off, 0.788) * 0.80
            if v_ego > v_allow_off and k_off > 1e-3:
                self._pass_state = 'COOLDOWN'
                self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                return False, 0.0, 'ABORT->COOLDOWN'
            return True, lat_ref + lado * self.PASS_MARGIN_M, self._pass_state
        # --- PREPARE: confirma e commit ------------------------------------
        if self._pass_state == 'PREPARE' and tgt is not None and self._pass_target:
            d_t, lat_o, v_o = tgt
            lat_ref, lado, _ = self._pass_target
            # aborto: terceiro carro no lado alvo (±25 m, mesma faixa lateral)
            for (s_o3, lat3, v3) in traffic:
                d3 = signed_dist_s(s_o3, s_ego, L)
                if (abs(d3) < 25.0
                        and abs((lat3) - (lat_ref + lado * self.PASS_MARGIN_M)) < 3.0
                        and abs(d3 - d_t) > 5.0):
                    self._pass_state = 'COOLDOWN'
                    self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                    return False, None, 'ABORT->COOLDOWN'
            # Exp2 (v15 FASE 2b): COMMIT POR GAP. O predicado antigo exigia
            # v_ego−v_o > 0,5, mas o cap v_ahead+2 (ainda ativo no PREPARE)
            # equaliza a velocidade ANTES do commit — a máquina nunca tinha
            # tempo-espaço lateral (passes viravam empurrões, lateral med.
            # 0,00 m). Agora: d < G_COMMIT ⇒ PASS (levanta o cap), e a
            # MARGEM LATERAL É APLICADA DESDE O PREPARE (não só no PASS) —
            # quando o commit chega, o deslocamento já está materializado.
            # Exp3: a janela de reta tem que existir em CADA tick do PREPARE —
            # a curva chegando encurta o trecho; aborta por GEOMETRIA
            need = d_t + 8.0 + 3.0 * max(v_ego, 10.0) + 40.0
            window = all(self.v_profile.at(s_ego + dd) >= 0.9 * max(v_ego, 10.0)
                         for dd in np.arange(0.0, need, 20.0))
            if not window or v_o >= v_plan_here * 0.97:
                # curva ou o alvo deixou de ser lento — sem sala p/ completar
                self._pass_state = 'COOLDOWN'
                self._pass_cooldown = self.PASS_COOLDOWN_TICKS
                return False, 0.0, 'ABORT->COOLDOWN'
            if d_t < self.PASS_G_COMMIT_M:
                self._pass_state = 'PASS'   # compromisso: cap levantado
                return True, lat_ref + lado * self.PASS_MARGIN_M, self._pass_state
            # PREPARE mantém o deslocamento lateral vivo (margem desde o início)
            return False, lat_ref + lado * self.PASS_MARGIN_M, self._pass_state
        # --- FOLLOW → PREPARE (Exp3 v15 FASE 2d) ----------------------------
        # UMA hipótese: passagem limpa exige janela de reta com margem
        # pré-aberta. Três sub-condições formam UM predicado de quando-passar:
        # (1) JANELA DE RETA (derivada do v_plan, sem coordenadas por pista):
        #     v_plan alto e constante por todo o trecho de conclusão =
        #     gap + 8 (conclusão) + 3s·v (materialização) + 40 (margem).
        # (2) DIFERENCIAL PLANEJADO (não Δv medido — o cap equaliza):
        #     v_plan_ego > v_o × 1,03. Falsificação: homogêneo = 0 passes.
        # (3) PRÉ-ABERTURA no FOLLOW-lento (substitui a abertura no commit).
        self._pass_state = 'FOLLOW'
        preopen_offset = None
        if tgt is not None:
            d_t, lat_o, v_o = tgt
            # (2) diferencial PLANEJADO (v_plan vs v_o; o cap v_ahead+2 já
            # equalizou o Δv medido — não usar)
            planned_diff = v_plan_here > v_o * 1.03
            # (1) janela de reta: v_plan ≥ 0,9·v_ego por todo o trecho
            need = d_t + 8.0 + 3.0 * max(v_ego, 10.0) + 40.0
            window = all(self.v_profile.at(s_ego + dd) >= 0.9 * max(v_ego, 10.0)
                         for dd in np.arange(0.0, need, 20.0))
            slow_leader = v_o < v_plan_here * 0.95
            if planned_diff and window and slow_leader:
                lado = -1.0 if lat_o > 0.5 else 1.0
                blocked = any(
                    abs(signed_dist_s(s_o4, s_ego, L)) < 25.0
                    and abs(lat4 - (lat_o + lado * self.PASS_MARGIN_M)) < 3.0
                    for (s_o4, lat4, v4) in traffic)
                if not blocked:
                    # (3) PRÉ-ABERTURA: a margem constrói DURANTE o follow
                    preopen_offset = lat_o + lado * self.PASS_MARGIN_M
                    self._pass_state = 'PREPARE'
                    self._pass_target = (lat_o, lado, 0)
        if self._pass_state == 'FOLLOW':
            return False, None, self._pass_state
        return False, preopen_offset, self._pass_state
        return False, None, self._pass_state

    def _pass_decision_choose_side(self, s_ego, lat_ego, cars, half_width,
                                   track_len_s):
        """Escolhe o offset com maior folga lateral disponível.

        A folga considera os demais carros a até ±25 m de arco. Empates usam
        a distância à borda e, por último, o lado esquerdo (+lat) para manter
        o resultado determinístico.
        """
        half_width = float(half_width)
        if half_width <= 0.5:
            return 0.0, float(lat_ego)
        rows = []
        for side in (-1.0, 1.0):
            target_lat = float(np.clip(
                lat_ego + side * self.LAT_OFFSET_MAX,
                -half_width + 0.5, half_width - 0.5))
            clearances = []
            for car in cars:
                d = signed_dist_s(float(car['s']), float(s_ego), track_len_s)
                if abs(d) <= self.PASS_DECISION_NEARBY_M:
                    clearances.append(abs(target_lat - float(car['lat'])))
            lateral_clearance = min(clearances) if clearances else float('inf')
            edge_clearance = min(half_width - target_lat, half_width + target_lat)
            rows.append((lateral_clearance, edge_clearance, side, target_lat))
        # lado esquerdo é o desempate determinístico final.
        _, _, side, target_lat = max(rows, key=lambda row: (row[0], row[1], row[2]))
        return side, target_lat

    def _pass_decision_close_attempt(self, outcome, now_s):
        state = self._pass_decision_state
        if state['active']:
            self._pass_decision_stats['attempts'].append(dict(
                target_id=state['target_id'], start_s=state['started_s'],
                end_s=float(now_s), outcome=str(outcome)))

    def _leader_yield_step(self, context, s_ego, lat_ego):
        state = self._leader_yield_state
        now_s = float(context.get('t_s', 0.0))
        allowed = bool(context.get('leader_yield_allowed', False))
        contacts = set(context.get('leader_yield_contact_pairs', ()))
        follower_id = state['follower_id']
        if state['active']:
            pair = tuple(sorted((str(self.driver_id), str(follower_id))))
            follower_cum = float(context.get('leader_yield_follower_cum', 0.0))
            ego_cum = float(context.get('leader_yield_ego_cum', 0.0))
            outcome = None
            if not allowed or pair in contacts:
                outcome = 'abort'
            elif follower_cum - ego_cum >= 10.0:
                outcome = 'consumed'
            elif now_s - float(state['started_s']) > 8.0:
                outcome = 'abort_timeout'
            if outcome is not None:
                self._leader_yield_stats['attempts'].append(dict(
                    follower_id=follower_id, start_s=state['started_s'],
                    end_s=now_s, outcome=outcome))
                if outcome == 'consumed':
                    self._leader_yield_stats['consumed'] += 1
                else:
                    self._leader_yield_stats['aborted'] += 1
                state.update(active=False, follower_id=None, started_s=None,
                             start_lat=None, target_lat=None)
                return 0.0
            return float(state['target_lat'])

        target_id = context.get('leader_yield_engage_follower')
        if target_id is None or not allowed:
            return None
        cars = context.get('leader_yield_cars', ())
        target = next((car for car in cars
                       if str(car['driver_id']) == str(target_id)), None)
        if target is None:
            return None
        follower_lat = float(target['lat'])
        side, _ = self._pass_decision_choose_side(
            s_ego, lat_ego, cars,
            float(context.get('half_width', getattr(self.env, '_half_width', 6.0))),
            float(context.get('track_len_s', self.env._track_len_s)))
        target_lat = follower_lat + math.copysign(3.5, side or 1.0)
        half_width = float(context.get(
            'half_width', getattr(self.env, '_half_width', 6.0)))
        target_lat = float(np.clip(target_lat, -half_width + 0.5,
                                   half_width - 0.5))
        state.update(active=True, follower_id=str(target_id),
                     started_s=now_s, start_lat=float(lat_ego),
                     target_lat=target_lat)
        self._leader_yield_stats['engaged'] += 1
        return target_lat - float(lat_ego)

    def leader_yield_summary(self):
        return dict(self._leader_yield_stats,
                    active=(dict(self._leader_yield_state)
                            if self._leader_yield_state['active'] else None))

    def _pass_decision_candidate(self, s_ego, v_ego, lat_ego, cars,
                                 track_len_s=None):
        """Pure candidate lookup shared by the live layer and its history gate."""
        length = float(track_len_s or self.env._track_len_s)
        ahead = []
        for car in cars:
            gap = signed_dist_s(float(car['s']), float(s_ego), length)
            if (0.0 < gap < self.D_AHEAD_M
                    and abs(float(car['lat']) - float(lat_ego))
                    < self.LAT_SAME_LINE_M):
                ahead.append((gap, car))
        nearest = min(ahead, key=lambda item: item[0]) if ahead else None
        if nearest is None:
            return None
        gap, car = nearest
        if (gap >= self.PASS_DECISION_GAP_MIN_M
                and abs(float(v_ego) - float(car['speed']))
                >= self.PASS_DECISION_DV_MIN_MPS):
            return car
        return None

    def pass_decision_sustained_target(self, samples, allowed=False):
        """Purely recognize the frozen 15-sample opportunity window.

        The caller supplies existing diagnostic snapshots plus the current
        snapshot. This method reads them only and never mutates controller state.
        """
        if not allowed or len(samples) != self.PASS_DECISION_SAMPLES:
            return None
        target_id = None
        for sample in samples:
            if float(sample['t_s']) < 60.0:
                return None
            candidate = self._pass_decision_candidate(
                sample['s_ego'], sample['v_ego'], sample['lat_ego'],
                sample['cars'], sample.get('track_len_s'))
            if candidate is None:
                return None
            current_id = str(candidate['driver_id'])
            if target_id is None:
                target_id = current_id
            elif current_id != target_id:
                return None
        return target_id

    def _pass_decision_layer(self, s_ego, v_ego, lat_ego, v_plan_here,
                             context=None):
        """Decisão PASS-1: oportunidade sustentada, lado livre e abortos.

        `context` é fornecido pelo runner professor e contém snapshots dos
        demais carros, tempo, permissão (largada/rejoin), amostra 5 Hz,
        progresso acumulado e pares com contato solver no tick anterior.
        Retorna (levantar_cap, offset_target, estado). O writer não é alterado.
        """
        del v_plan_here  # a tentativa libera o cap e usa o plano próprio
        context = context or {}
        state = self._pass_decision_state
        now_s = float(context.get('t_s', 0.0))
        sample_5hz = bool(context.get('sample_5hz', False))
        allowed = bool(context.get('allowed', False)) and now_s >= 60.0
        cars = list(context.get('cars', ()))
        track_len_s = float(context.get('track_len_s', self.env._track_len_s))
        half_width = float(context.get(
            'half_width', getattr(self.env, '_half_width', 6.0)))
        contact_pairs = set(context.get('contact_pairs', ()))

        candidate = self._pass_decision_candidate(
            s_ego, v_ego, lat_ego, cars, track_len_s)

        if state['active']:
            target = next((car for car in cars
                           if car['driver_id'] == state['target_id']), None)
            pair = tuple(sorted((str(self.driver_id), str(state['target_id']))))
            if not allowed:
                self._pass_decision_close_attempt('abort_rejoin', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['aborted_rejoin'] += 1
                return False, None, 'DECISION_ABORT_REJOIN'
            if pair in contact_pairs:
                self._pass_decision_close_attempt('abort_contact', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['aborted_contact'] += 1
                return False, None, 'DECISION_ABORT_CONTACT'
            if target is None:
                # A lista contém sempre os demais carros; desaparecer implica
                # dados inconsistentes e o gate falha fechado para follow.
                self._pass_decision_close_attempt('abort_target', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['aborted_target'] += 1
                return False, None, 'DECISION_ABORT_TARGET'
            own_cum = float(context.get('ego_cum_dist', 0.0))
            target_cum = float(target.get('cum_dist', 0.0))
            if own_cum - target_cum >= 10.0:
                self._pass_decision_close_attempt('consumed', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['consumed'] += 1
                return False, None, 'DECISION_CONSUMED'
            gap = signed_dist_s(float(target['s']), float(s_ego), track_len_s)
            state['lateral_progress_m'] = max(
                float(state['lateral_progress_m']),
                float(state['side']) * (float(lat_ego) - float(state['start_lat'])))
            if (now_s - float(state['started_s']) > self.PASS_DECISION_ABORT_S):
                self._pass_decision_close_attempt('abort_timeout', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['aborted_timeout'] += 1
                return False, None, 'DECISION_ABORT_TIMEOUT'
            if (gap < self.PASS_DECISION_ABORT_GAP_M
                    and float(state['lateral_progress_m'])
                    < self.PASS_DECISION_PROGRESS_M):
                self._pass_decision_close_attempt('abort_gap', now_s)
                state['active'] = False
                state['candidate_id'] = None
                state['candidate_samples'] = 0
                state['target_id'] = None
                self._pass_decision_stats['aborted_gap'] += 1
                return False, None, 'DECISION_ABORT_GAP'
            return True, float(state['target_lat']), 'DECISION_ACTIVE'

        if sample_5hz:
            if not allowed or candidate is None:
                state['candidate_id'] = None
                state['candidate_samples'] = 0
            elif candidate['driver_id'] == state['candidate_id']:
                state['candidate_samples'] += 1
            else:
                state['candidate_id'] = candidate['driver_id']
                state['candidate_samples'] = 1

        if (allowed and candidate is not None
                and int(state['candidate_samples']) >= self.PASS_DECISION_SAMPLES):
            side, target_lat = self._pass_decision_choose_side(
                s_ego, lat_ego, cars, half_width, track_len_s)
            state.update(active=True, target_id=candidate['driver_id'],
                         started_s=now_s, start_lat=float(lat_ego), side=side,
                         target_lat=target_lat, lateral_progress_m=0.0,
                         candidate_id=None, candidate_samples=0)
            self._pass_decision_stats['opportunities'] += 1
            self._pass_decision_stats['engaged'] += 1
            return True, target_lat, 'DECISION_ACTIVE'

        return False, None, 'FOLLOW'

    def pass_decision_summary(self):
        """Retorna contadores da decisão opt-in, sem tocar o CSV."""
        out = dict(self._pass_decision_stats)
        state = self._pass_decision_state
        out['active_attempt'] = (dict(
            target_id=state['target_id'], start_s=state['started_s'])
            if state['active'] else None)
        return out

    def action(self, traffic=None, pass_decision_context=None):
        env = self.env
        phys = env.engine.physics.get_state(env.engine.handles[self.driver_id])
        x, y, v = phys['x'], phys['y'], phys['speed_mps']
        heading = phys['heading_rad']
        _, s, _, lat_signed = env._project_on_path(x, y)

        # --- Camada de TRÁFEGO (Fase 1 v14) — ANTES do pure pursuit ------
        # Roda primeiro para que o offset lateral suavizado (_lat_offset)
        # desloque o PONTO DE PERSEGUIÇÃO deste tick. Na FASE 1 original o
        # offset era computado DEPOIS do pure pursuit e nunca aplicado —
        # estado morto (bug corrigido no PASSO 1 do gate v14).
        v_cap = None
        offset_target = 0.0
        if traffic is not None:
            v_cap, offset_target = self._traffic_adjust(s, v, lat_signed, traffic)
            if getattr(self, '_overtake_machine_only', False):
                # FASE 2b (Exp 1): offset do follow SUPRIMIDO — só a máquina
                # desloca lateralmente (o cap de car-following permanece)
                offset_target = 0.0
            # Antes do primeiro engajamento, a flag ON chama a máquina legada
            # exatamente como OFF. O runner só entrega decision_engage_target
            # quando a janela sustentada foi reconhecida por leitura pura da
            # história 5 Hz já existente. Depois do primeiro engage, a troca
            # de máquina é permanente, inclusive após abort/retorno.
            if not self.PASS_DECISION_ENABLED:
                lift_cap, pass_offset, p_state = self._pass_layer(
                    s, v, lat_signed, traffic, self.v_profile.at(s))
            else:
                decision_context = pass_decision_context or {}
                decision_state = self._pass_decision_state
                decision_started = bool(
                    decision_state['active']
                    or decision_state['started_s'] is not None)
                decision_target = decision_context.get('decision_engage_target')
                if decision_started or decision_target is not None:
                    if decision_target is not None and not decision_started:
                        # PASS-PARITY-3 v3: the runner's pure window is the
                        # authoritative same-tick engagement contract.
                        side, target_lat = self._pass_decision_choose_side(
                            s, lat_signed, decision_context.get('cars', ()),
                            float(decision_context.get(
                                'half_width',
                                getattr(env, '_half_width', 6.0))),
                            float(decision_context.get(
                                'track_len_s', env._track_len_s)))
                        now_s = float(decision_context.get('t_s', 0.0))
                        decision_state.update(
                            active=True, target_id=str(decision_target),
                            started_s=now_s, start_lat=float(lat_signed),
                            side=side, target_lat=target_lat,
                            lateral_progress_m=0.0, candidate_id=None,
                            candidate_samples=0)
                        self._pass_decision_stats['opportunities'] += 1
                        self._pass_decision_stats['engaged'] += 1
                        lift_cap, pass_offset, p_state = (
                            True, target_lat, 'DECISION_ACTIVE')
                    else:
                        lift_cap, pass_offset, p_state = (
                            self._pass_decision_layer(
                                s, v, lat_signed, self.v_profile.at(s),
                                context=pass_decision_context))
                    if (decision_target is not None
                            and not decision_state['active']):
                        live_candidate = self._pass_decision_candidate(
                            s, v, lat_signed,
                            decision_context.get('cars', ()),
                            decision_context.get('track_len_s'))
                        diagnostic = dict(
                            context=decision_context,
                            state=dict(decision_state),
                            candidate=live_candidate,
                            allowed=bool(decision_context.get('allowed', False)),
                            sample_5hz=bool(
                                decision_context.get('sample_5hz', False)),
                            now_s=float(decision_context.get('t_s', 0.0)))
                        raise RuntimeError(
                            'predicado puro de passagem não confirmou o engage '
                            f'no mesmo tick; payload={diagnostic!r}')
                else:
                    lift_cap, pass_offset, p_state = self._pass_layer(
                        s, v, lat_signed, traffic, self.v_profile.at(s))
            self.last_pass_state = p_state
            if pass_offset is not None:
                offset_target = pass_offset
            if lift_cap:
                v_cap = None          # PASS: alvo = v_plan PRÓPRIO
        else:
            self.last_pass_state = 'FOLLOW'
        if self.LEADER_YIELD_ENABLED and pass_decision_context:
            yield_offset = self._leader_yield_step(
                pass_decision_context, s, lat_signed)
            if yield_offset is not None:
                offset_target = yield_offset
        if traffic is not None:
            self._lat_offset = (self.OFFSET_SMOOTH * offset_target +
                                (1.0 - self.OFFSET_SMOOTH) * self._lat_offset)

        # --- Pure Pursuit ---
        # v2: lookahead adaptado à curva AHEAD — sem isso, ld=45m num hairpin
        # mira do lado oposto da curva e o carro subesterça mortalmente.
        v_for_ld = v
        if getattr(self, 'use_v_plan', False):
            # usa a velocidade do PLANO no ponto de lookahead (não a atual):
            # approaching um hairpin, v_plan lá já é baixo → ld encolhe ANTES
            ld_probe = float(np.clip(self.k_ld * v, self.ld_min, self.ld_max))
            v_for_ld = min(v, self.v_profile.at(s + ld_probe))
        ld = float(np.clip(self.k_ld * v_for_ld, self.ld_min, self.ld_max))
        kappa_here = 0.0
        if self.PROF_CONTROL_ENABLED:
            # PROF-CONTROL-1: ld_eff = clip(k_ld·v, min, max)·g(κ), com
            # g(κ) = 1/(1 + c_ld·|κ_local|) — mantém o ponto de perseguição
            # dentro do arco no ápice/saída (C01) e aperta nas quinas (C08).
            kappa_here = self._prof_kappa_local(s)
            ld = ld * self._prof_gain(kappa_here, self._prof_c_ld)
        tx, ty, th = env._point_at(s + ld)
        if self._lat_offset != 0.0:
            # desloca o ponto de perseguição lateralmente: +offset = à
            # ESQUERDA da linha (mesma convenção de lat/_point_at do env)
            nx, ny = -math.sin(th), math.cos(th)
            tx += nx * self._lat_offset
            ty += ny * self._lat_offset
        self._last_pursuit = (tx, ty)
        dx, dy = tx - x, ty - y
        alpha = math.atan2(dy, dx) - heading
        alpha = (alpha + math.pi) % (2 * math.pi) - math.pi
        steer_rad = math.atan2(2.0 * self.wheelbase * math.sin(alpha), ld)
        if self.PROF_CONTROL_ENABLED:
            # PROF-CONTROL-1: feedforward cinemático δ_ff = arctan(L·κ_local)
            # soma-se ao pure pursuit residual (correção lateral). Em reta
            # (κ=0) vale 0.0: preservação exata do comportamento em reta.
            steer_rad += self._prof_delta_ff(kappa_here, self.wheelbase)

        # --- Velocidade ---
        v_tgt = self._v_target(s, v) * self.margin
        # O perfil usa uma janela suavizada de 20 m; ela pode esconder picos
        # de curvatura em hairpins muito apertados. Faça uma passada de frenagem
        # sobre a curvatura local à frente para começar a reduzir antes do ápice.
        local_kappa_fn = getattr(env, '_kappa_signed', None)
        if (callable(local_kappa_fn)
                and hasattr(env, '_wps_arr')
                and hasattr(env, '_track_len_s')):
            local_brake_mps2 = min(self.a_brake, 4.0)
            for distance_m in range(0, 97, 8):
                kappa_local = abs(float(local_kappa_fn(
                    s + distance_m, window_m=4.0)))
                if kappa_local <= 1e-3:
                    continue
                v_corner = math.sqrt(self.a_lat_max / kappa_local) * self.margin * 0.65
                v_reachable = math.sqrt(
                    v_corner * v_corner + 2.0 * local_brake_mps2 * distance_m,
                )
                v_tgt = min(v_tgt, v_reachable)
        if v_cap is not None:
            v_tgt = min(v_tgt, v_cap)
        if self.PROF_PACE_ENABLED and self._prof_pace is not None:
            # PROF-PACE-1: alvo = perfil capado (0,93 + teto η EMBUTIDOS nas
            # passadas de prof_curva) — SEM margin adicional. Pacing-only:
            # esterço intocado. Fora de Interlagos: no-op (perfil ausente).
            v_tgt = self._prof_pace["v_at"](s)
        if self.PROF_GRIP_ENABLED:
            # PROF-GRIP-1: teto grip-sensível nas janelas das 4 crônicas —
            # grip_atual pela MESMA expressão da coluna telemetrada
            # (tyre.grip_multiplier × clima), alvo = v_plan(s)·fator (§2 do
            # prereg), teto nunca ELEVA o alvo histórico. Pacing-only:
            # esterço intocado.
            wstate = self.env.engine.weather_model.current
            tyre = self.env.engine.states[self.driver_id].tyre
            grip_now = float(tyre.grip_multiplier(wstate.kind,
                                                  wstate.track_temp))
            v_tgt = self._prof_grip_mod.cap_v_target(
                self.v_profile.at(s), v_tgt, s, grip_now,
                self._prof_grip_windows)
        long_cmd = float(np.clip((v_tgt - v) / 8.0, -1.0, 1.0))

        # Normaliza esterço p/ o espaço [-1, 1] da ação (limite depende de v)
        steer_cmd = float(np.clip(steer_rad / env.steer_limit_rad(v), -1.0, 1.0))
        return np.array([steer_cmd, long_cmd], dtype=np.float32)


def run_reference_episode(env, controller=None, max_steps=3000, verbose=False):
    """Roda um episódio com o controlador clássico. Retorna (done_info, retorno)."""
    ctrl = controller or ReferenceController(env)
    obs, _ = env.reset()
    ret, info = 0.0, {}
    for step in range(max_steps):
        a = ctrl.action()
        obs, r, term, trunc, info = env.step(a)
        ret += r
        if verbose and step % 100 == 0:
            print(f"  step={step} s_prog={info.get('progress_m', 0):.0f}m "
                  f"v={info.get('speed', 0):.1f}m/s")
        if term or trunc:
            break
    info = dict(info or {})
    info["return"] = ret
    info["steps"] = step + 1
    return info
