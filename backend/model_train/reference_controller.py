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
    # FASE 2b — Experimento 1: isolar a máquina. Com _overtake_machine_only,
    # o offset do corredor no FOLLOW é SUPRIMIDO (cap v_ahead+2 MANTIDO) e o
    # único caminho de ultrapassagem passa a ser a máquina _pass_layer.
    # Hipótese mensurável: PASS% > 0, passes 2-6, contatos pós-largada ~0.

    def __init__(self, env, wheelbase_m=3.4, a_lat_max=12.0, a_brake_max=12.0,
                 lookahead_gain=0.6, lookahead_min_m=5.0, lookahead_max_m=45.0,
                 speed_margin=0.93, velocity_profile=None, sf=0.80,
                 smooth_window_m=20.0, driver_id=None):
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

    def action(self, traffic=None):
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
            # FASE 2 (v15): camada de ULTRAPASSAGEM (pode levantar o cap e
            # sobrescrever o offset — mesmo mecanismo lateral _lat_offset)
            lift_cap, pass_offset, p_state = self._pass_layer(
                s, v, lat_signed, traffic, self.v_profile.at(s))
            self.last_pass_state = p_state
            if pass_offset is not None:
                offset_target = pass_offset
            if lift_cap:
                v_cap = None          # PASS: alvo = v_plan PRÓPRIO
        else:
            self.last_pass_state = 'FOLLOW'
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

        # --- Velocidade ---
        v_tgt = self._v_target(s, v) * self.margin
        if v_cap is not None:
            v_tgt = min(v_tgt, v_cap)
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
