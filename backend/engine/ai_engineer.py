"""Engenheiro de IA autônomo que avalia a corrida e emite recomendações.

Roda em background durante a corrida, lendo estado do motor/publicador e
tomando decisões estratégicas por piloto (push, conserve, pit, defend, etc.).

Arquitetura:
- Separação clara entre ANÁLISE (recomendação) e EXECUÇÃO (envio de comando)
- O piloto do usuário é ANALISADO mas NÃO recebe comandos automáticos
- Eventos de ciclo de vida explícitos para observabilidade no frontend
"""

from __future__ import annotations

import logging
import random
import threading
import time
from dataclasses import dataclass, replace
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import redis

from .coach_controller import CommandBus, normalize_command
from .events import (
    AiCommandEvent,
    AiSuggestionEvent,
    AiStartedEvent,
    AiMonitoringEvent,
    AiStoppedEvent,
    AiErrorEvent,
)

logger = logging.getLogger(__name__)


class DriverRole(Enum):
    """Papel do piloto na corrida."""
    USER = "user"           # Controlado pelo jogador
    AI_BOT = "ai_bot"       # Controlado por IA (rule-based)
    AI_ANALYZED = "ai_analyzed"  # Analisado pelo engenheiro, mas sem comando automático


@dataclass
class DriverSituation:
    """Situação tática completa de um piloto."""
    driver_id: str
    name: str
    role: DriverRole
    position: int
    lap: int
    total_laps: int
    gap_ahead_s: Optional[float]
    gap_behind_s: Optional[float]
    tyre_life_pct: float
    tyre_compound: str
    fuel_kg: float
    speed_mps: float
    last_command_seq: int = -1
    last_command_time: float = 0.0


@dataclass
class Recommendation:
    """Recomendação do engenheiro (resultado da análise)."""
    driver_id: str
    driver_name: str
    command: str
    value: float
    reason: str
    urgency: str  # "baixa" | "media" | "alta"
    should_execute: bool  # False para piloto do usuário
    confidence: float = 1.0  # 0.0 a 1.0


class AiEngineer:
    """Engenheiro de IA que gerencia a estratégia de todos os pilotos."""

    # Intervalos de decisão (tempo SIMULADO)
    DECISION_INTERVAL_S = 5.0  # avalia a cada 5s de simulação (era 8.0)
    MIN_COMMAND_INTERVAL_S = 10.0  # mínimo entre comandos no mesmo piloto (era 15.0)
    PIT_WINDOW_START_PCT = 0.20  # janela de pit abre a 20% da corrida (era 25%)
    PIT_WINDOW_END_PCT = 0.85   # janela de pit fecha a 85% da corrida (era 80%)

    # Thresholds configuráveis
    TYRE_CRITICAL_PCT = 15.0
    TYRE_LOW_PCT = 30.0
    GAP_SMALL_S = 1.5
    GAP_MEDIUM_S = 3.0
    GAP_LARGE_S = 5.0
    FUEL_CRITICAL_KG = 3.0
    FUEL_LOW_KG = 8.0

    def __init__(
        self,
        race_id: str,
        redis_client: redis.Redis,
        command_bus: CommandBus,
        publisher: Any,
        engine: Any,
        total_laps: int,
        drivers_meta: List[Dict[str, Any]],
        user_driver_id: Optional[str] = None,
    ) -> None:
        self.race_id = race_id
        self.redis = redis_client
        self.bus = command_bus
        self.publisher = publisher
        self.engine = engine
        self.total_laps = total_laps
        self.user_driver_id = user_driver_id
        self.drivers_meta = {d["driver_id"]: d for d in drivers_meta}

        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._last_decision_sim_ts = 0.0
        self._started = False
        self._monitoring_active = False

        # Estatísticas para observabilidade
        self._stats = {
            "cycles": 0,
            "recommendations_generated": 0,
            "commands_executed": 0,
            "user_driver_analyzed": 0,
            "errors": 0,
            "last_cycle_sim_ts": 0.0,
        }

    # ==================== CICLO DE VIDA ====================

    def start(self) -> None:
        """Inicia o engenheiro de IA."""
        if self._thread and self._thread.is_alive():
            logger.warning("AiEngineer já rodando para corrida %s", self.race_id)
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"AiEngineer-{self.race_id[:8]}")
        self._thread.start()

        self._started = True
        self._publish_lifecycle_event("ai_started", {
            "total_laps": self.total_laps,
            "user_driver_id": self.user_driver_id,
            "num_drivers": len(self.drivers_meta),
            "decision_interval_s": self.DECISION_INTERVAL_S,
        })
        logger.info("=== AiEngineer INICIADO para corrida %s ===", self.race_id)
        logger.info("  total_laps=%s, user_driver_id=%s, drivers=%d, decision_interval=%.1fs",
                    self.total_laps, self.user_driver_id, len(self.drivers_meta), self.DECISION_INTERVAL_S)

    def stop(self, reason: str = "race_ended") -> None:
        """Para o engenheiro de IA graciosamente."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)

        self._publish_lifecycle_event("ai_stopped", {
            "reason": reason,
            "stats": self._stats.copy(),
        })
        logger.info("=== AiEngineer PARADO para %s (reason=%s, stats=%s) ===",
                    self.race_id, reason, self._stats)

    def _publish_lifecycle_event(self, event_type: str, payload: Dict[str, Any], sim_ts: Optional[float] = None) -> None:
        """Publica evento de ciclo de vida via publisher."""
        if not self.publisher:
            return
        try:
            event_map = {
                "ai_started": AiStartedEvent,
                "ai_monitoring": AiMonitoringEvent,
                "ai_stopped": AiStoppedEvent,
                "ai_error": AiErrorEvent,
            }
            event_class = event_map.get(event_type)
            if event_class:
                self.publisher.publish(event_class(
                    sim_ts=sim_ts if sim_ts is not None else float(getattr(self.engine, "sim_ts", 0)),
                    race_id=self.race_id,
                    **payload,
                ))
        except Exception as e:
            logger.warning("Falha ao publicar evento %s: %s", event_type, e)

    # ==================== LOOP PRINCIPAL ====================

    def _run(self) -> None:
        """Loop principal do engenheiro."""
        logger.info("=== AiEngineer LOOP INICIADO para %s ===", self.race_id)

        # Primeira publicação de monitoring
        self._monitoring_active = True
        self._publish_lifecycle_event("ai_monitoring", {
            "status": "waiting_for_race_start",
        })

        while not self._stop.is_set():
            try:
                self._stats["cycles"] += 1
                cycle_start = time.time()

                # Avalia e decide
                recommendations = self._evaluate_and_recommend()

                # Executa recomendações (exceto piloto do usuário)
                for rec in recommendations:
                    if rec.should_execute:
                        self._execute_recommendation(rec)
                    else:
                        # Para piloto do usuário: apenas publica sugestão textual
                        self._publish_suggestion_only(rec)

                # Publica heartbeat de monitoring a cada 10 ciclos (~5s real)
                if self._stats["cycles"] % 10 == 0:
                    self._publish_monitoring_heartbeat()

            except Exception as e:
                self._stats["errors"] += 1
                logger.exception("Erro no ciclo do AiEngineer para corrida %s", self.race_id)
                self._publish_lifecycle_event("ai_error", {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "cycle": self._stats["cycles"],
                })

            # Sleep curto para não consumir CPU excessivamente
            # Decisões são baseadas em sim_ts, não em tempo real
            time.sleep(0.3)

        self._monitoring_active = False
        logger.info("=== AiEngineer LOOP FINALIZADO para %s (ciclos=%d) ===",
                    self.race_id, self._stats["cycles"])

    def _publish_monitoring_heartbeat(self) -> None:
        """Publica heartbeat de monitoring com estatísticas atuais."""
        snapshot = getattr(self.publisher, "snapshot", None)
        status = snapshot.get("status") if snapshot else "unknown"
        sim_ts = 0.0
        if snapshot and snapshot.get("last_tick"):
            sim_ts = float(snapshot["last_tick"].get("sim_ts", 0))

        self._publish_lifecycle_event("ai_monitoring", {
            "status": status,
            "stats": self._stats.copy(),
        }, sim_ts=sim_ts)

    # ==================== ANÁLISE (SEPARADA DA EXECUÇÃO) ====================

    def _evaluate_and_recommend(self) -> List[Recommendation]:
        """
        Avalia a corrida e gera recomendações para TODOS os pilotos.
        NÃO executa comandos - apenas retorna lista de recomendações.
        """
        # Pega snapshot mais recente do publisher
        snapshot = getattr(self.publisher, "snapshot", None)
        if not snapshot:
            logger.debug("AiEngineer %s: sem snapshot", self.race_id)
            return []

        status = snapshot.get("status")
        if status != "running":
            logger.debug("AiEngineer %s: status=%s (esperado 'running')", self.race_id, status)
            return []

        last_tick = snapshot.get("last_tick")
        if not last_tick:
            logger.debug("AiEngineer %s: sem last_tick", self.race_id)
            return []

        sim_ts = float(last_tick.get("sim_ts", 0))

        # Rate limit baseado em tempo SIMULADO
        if sim_ts - self._last_decision_sim_ts < self.DECISION_INTERVAL_S:
            return []
        self._last_decision_sim_ts = sim_ts
        self._stats["last_cycle_sim_ts"] = sim_ts

        positions = last_tick.get("positions", [])
        if not positions:
            logger.debug("AiEngineer %s: sem positions no tick", self.race_id)
            return []

        # Constrói situação de cada piloto
        situations = self._build_situations(positions, last_tick)

        # Analisa cada piloto (inclui o do usuário)
        recommendations = []
        for sit in situations:
            rec = self._analyze_driver(sit, positions)
            if rec:
                recommendations.append(rec)
                self._stats["recommendations_generated"] += 1

                # Log específico para piloto do usuário
                if sit.role == DriverRole.USER:
                    self._stats["user_driver_analyzed"] += 1
                    logger.info("AiEngineer %s: ANÁLISE do piloto do usuário %s (P%s): %s — %s [%s]",
                              self.race_id, sit.name, sit.position, rec.command, rec.reason, rec.urgency)

        if recommendations:
            logger.info("AiEngineer %s: %d recomendações geradas em sim_ts=%.1f",
                        self.race_id, len(recommendations), sim_ts)

        return recommendations

    def _analyze_driver(self, sit: DriverSituation, all_positions: List[Dict[str, Any]]) -> Optional[Recommendation]:
        """
        Analisa UM piloto e retorna recomendação.
        NÃO executa - apenas decide o que seria ideal.
        """
        now = time.time()
        progress_pct = sit.lap / max(1, self.total_laps)

        # Rate limit por piloto (tempo REAL)
        if sit.last_command_seq >= 0 and now - sit.last_command_time < self.MIN_COMMAND_INTERVAL_S:
            logger.debug("AiEngineer %s: rate limit para %s (%.1fs desde último comando)",
                         self.race_id, sit.driver_id, now - sit.last_command_time)
            return None

        # Determina papel do piloto
        is_user = (sit.driver_id == self.user_driver_id)
        role = DriverRole.USER if is_user else DriverRole.AI_BOT

        command = None
        value = 0.0
        reason = ""
        urgency = "baixa"
        confidence = 1.0

        # Log de contexto para debug
        logger.debug("AiEngineer %s: Analisando %s (role=%s) P%s lap=%d/%d tyre=%.0f%% fuel=%.1fkg "
                     "gap_ahead=%s gap_behind=%s",
                     self.race_id, sit.name, role.value, sit.position, sit.lap, self.total_laps,
                     sit.tyre_life_pct, sit.fuel_kg, sit.gap_ahead_s, sit.gap_behind_s)

        # ========== LÓGICA DE DECISÃO ==========
        # (Aplicada a TODOS os pilotos, incluindo o do usuário)

        # 1. PIT STOP NECESSÁRIO?
        in_pit_window = self.PIT_WINDOW_START_PCT <= progress_pct <= self.PIT_WINDOW_END_PCT
        tyre_critical = sit.tyre_life_pct <= self.TYRE_CRITICAL_PCT
        tyre_low = sit.tyre_life_pct <= self.TYRE_LOW_PCT
        fuel_critical = sit.fuel_kg <= self.FUEL_CRITICAL_KG
        fuel_low = sit.fuel_kg <= self.FUEL_LOW_KG

        if in_pit_window and (tyre_critical or (tyre_low and sit.lap > 3) or fuel_low):
            command = "conserve"
            value = 0.85
            reason = (f"Pneus {sit.tyre_compound} {sit.tyre_life_pct:.0f}% / "
                      f"Combustível {sit.fuel_kg:.1f}kg — janela de pit aberta ({progress_pct:.0%})")
            urgency = "alta"
            confidence = 0.95

        # 2. DEFESA / ATAQUE por posição
        elif sit.gap_ahead_s is not None and sit.gap_ahead_s <= self.GAP_SMALL_S:
            command = "overtake"
            value = 0.0
            reason = f"Gap {sit.gap_ahead_s:.1f}s para P{sit.position - 1} — tentativa de ultrapassagem"
            urgency = "alta"
            confidence = 0.85

        elif sit.gap_behind_s is not None and sit.gap_behind_s <= self.GAP_SMALL_S:
            command = "defend"
            value = 0.0
            reason = f"P{sit.position + 1} a {sit.gap_behind_s:.1f}s — defendendo posição"
            urgency = "media"
            confidence = 0.80

        elif sit.gap_ahead_s is not None and sit.gap_ahead_s <= self.GAP_MEDIUM_S:
            command = "push"
            value = 0.0
            reason = f"Fechar gap de {sit.gap_ahead_s:.1f}s para P{sit.position - 1}"
            urgency = "media"
            confidence = 0.75

        elif sit.gap_ahead_s is not None and sit.gap_ahead_s <= self.GAP_LARGE_S:
            command = "push"
            value = 0.0
            reason = f"Reduzir gap de {sit.gap_ahead_s:.1f}s para P{sit.position - 1}"
            urgency = "baixa"
            confidence = 0.65

        # 3. GESTÃO DE PNEUS / COMBUSTÍVEL (fora da janela de pit)
        elif tyre_low and not in_pit_window:
            command = "conserve"
            value = 0.90
            reason = f"Preservando pneus {sit.tyre_compound} ({sit.tyre_life_pct:.0f}%) até janela de pit"
            urgency = "baixa"
            confidence = 0.85

        elif fuel_critical:
            command = "conserve"
            value = 0.85
            reason = f"Combustível crítico ({sit.fuel_kg:.1f}kg) — economizando para terminar"
            urgency = "alta"
            confidence = 0.95

        elif fuel_low and not in_pit_window:
            command = "conserve"
            value = 0.92
            reason = f"Combustível baixo ({sit.fuel_kg:.1f}kg) — gerenciando até pit"
            urgency = "media"
            confidence = 0.80

        # 4. LIDERANÇA: gerencia vantagem
        elif sit.position == 1 and sit.gap_ahead_s is None:
            if sit.gap_behind_s is not None and sit.gap_behind_s < self.GAP_MEDIUM_S:
                command = "push"
                value = 0.0
                reason = f"Líder pressionado (gap {sit.gap_behind_s:.1f}s) — mantendo ritmo forte"
                urgency = "media"
                confidence = 0.75
            else:
                command = "pace"
                value = 0.95
                reason = f"Líder confortável (gap {sit.gap_behind_s:.1f}s) — gerenciando vantagem"
                urgency = "baixa"
                confidence = 0.70

        # 5. ÚLTIMAS VOLTAS: tudo ou nada
        elif sit.lap >= self.total_laps - 2:
            command = "push"
            value = 0.0
            reason = f"Últimas voltas ({sit.lap}/{self.total_laps}) — ataque total"
            urgency = "alta"
            confidence = 0.90

        # 6. MEIO DE CORRIDA: ritmo consistente
        elif sit.lap >= 3 and sit.lap <= self.total_laps - 3:
            if sit.position <= 3:
                command = "pace"
                value = 0.98
                reason = f"Top 3 — ritmo consistente para manter posição"
                urgency = "baixa"
                confidence = 0.65
            else:
                command = "push"
                value = 0.0
                reason = f"Meio de pelotão — buscando ganhar posições"
                urgency = "baixa"
                confidence = 0.60

        # 7. VARIAÇÃO OCASIONAL (simula engenheiro humano)
        elif random.random() < 0.03:  # 3% chance (era 5%)
            command = random.choice(["push", "conserve", "careful", "pace"])
            reason = "Ajuste de ritmo rotineiro"
            urgency = "baixa"
            confidence = 0.40

        # Se não há recomendação aplicável
        if command is None or command == "neutral":
            logger.debug("AiEngineer %s: %s sem recomendação aplicável no momento", self.race_id, sit.driver_id)
            return None

        # Normaliza comando
        norm_cmd = normalize_command(command)

        return Recommendation(
            driver_id=sit.driver_id,
            driver_name=sit.name,
            command=norm_cmd,
            value=value,
            reason=reason,
            urgency=urgency,
            should_execute=not is_user,  # NÃO executa para piloto do usuário
            confidence=confidence,
        )

    # ==================== EXECUÇÃO (SEPARADA DA ANÁLISE) ====================

    def _execute_recommendation(self, rec: Recommendation) -> None:
        """Executa uma recomendação enviando comando ao barramento."""
        try:
            self.bus.push(rec.driver_id, rec.command, rec.value, rec.reason, issued_by="ai")
            self._stats["commands_executed"] += 1

            # Publica evento AiCommandEvent
            if self.publisher:
                self.publisher.publish(AiCommandEvent(
                    sim_ts=float(getattr(self.engine, "sim_ts", 0)),
                    driver_id=rec.driver_id,
                    driver_name=rec.driver_name,
                    lap=int(getattr(self.engine, "current_lap", 1)) if hasattr(self.engine, "current_lap") else 1,
                    command=rec.command,
                    value=rec.value,
                    reason=rec.reason,
                    issued_by="ai",
                ))

            logger.info("=== AiEngineer %s COMANDO EXECUTADO para %s (P%s): %s %.2f — %s [%s] (conf=%.0f%%) ===",
                        self.race_id, rec.driver_name, "?", rec.command, rec.value, rec.reason, rec.urgency, rec.confidence * 100)

        except Exception as e:
            logger.error("Falha ao executar recomendação para %s: %s", rec.driver_id, e)
            self._publish_lifecycle_event("ai_error", {
                "error": f"Falha ao executar comando para {rec.driver_id}: {e}",
                "error_type": "execution_error",
                "driver_id": rec.driver_id,
            })

    def _publish_suggestion_only(self, rec: Recommendation) -> None:
        """Publica apenas sugestão textual (para piloto do usuário)."""
        try:
            suggestion_text = self._suggestion_text(rec.command, rec.reason, rec.urgency)

            if self.publisher:
                self.publisher.publish(AiSuggestionEvent(
                    sim_ts=float(getattr(self.engine, "sim_ts", 0)),
                    driver_id=rec.driver_id,
                    driver_name=rec.driver_name,
                    lap=int(getattr(self.engine, "current_lap", 1)) if hasattr(self.engine, "current_lap") else 1,
                    aviso=suggestion_text,
                    urgencia=rec.urgency,
                    comando={
                        "tipo": rec.command,
                        "valor": rec.value,
                        "motivo": rec.reason,
                        "confianca": round(rec.confidence, 2),
                    },
                    fallback=False,
                ))

            logger.info("=== AiEngineer %s SUGESTÃO para piloto do usuário %s: %s [%s] ===",
                        self.race_id, rec.driver_name, suggestion_text, rec.urgency)

        except Exception as e:
            logger.error("Falha ao publicar sugestão para %s: %s", rec.driver_id, e)

    # ==================== HELPERS ====================

    def _build_situations(
        self, positions: List[Dict[str, Any]], last_tick: Dict[str, Any]
    ) -> List[DriverSituation]:
        """Constrói situação tática de cada piloto a partir do tick."""
        situations = []
        lap = int(last_tick.get("lap", 1))

        for idx, pos in enumerate(positions):
            driver_id = pos.get("driver_id")
            meta = self.drivers_meta.get(driver_id, {})
            name = meta.get("name", driver_id)

            # Gaps
            gap_ahead = pos.get("gap_to_leader_s")
            if gap_ahead is not None and gap_ahead > 0 and idx > 0:
                ahead = positions[idx - 1]
                gap_ahead = ahead.get("gap_to_leader_s")
                if gap_ahead is not None and pos.get("gap_to_leader_s") is not None:
                    gap_ahead = pos["gap_to_leader_s"] - gap_ahead
            else:
                gap_ahead = None

            gap_behind = None
            if idx < len(positions) - 1:
                behind = positions[idx + 1]
                if behind.get("gap_to_leader_s") is not None and pos.get("gap_to_leader_s") is not None:
                    gap_behind = behind["gap_to_leader_s"] - pos["gap_to_leader_s"]

            # Pneu
            tyre_life = pos.get("tyre_life_pct")
            if tyre_life is None:
                tyre_life = 100.0
            tyre_compound = pos.get("tyre_compound", "UNKNOWN")

            # Combustível
            fuel = pos.get("fuel_kg")
            if fuel is None or not isinstance(fuel, (int, float)):
                fuel = 50.0

            # Comando anterior
            last_cmd = self.bus.latest(driver_id)
            last_seq = last_cmd.seq if last_cmd else -1
            last_time = last_cmd.ts if last_cmd else 0.0

            is_user = (driver_id == self.user_driver_id)
            role = DriverRole.USER if is_user else DriverRole.AI_BOT

            situations.append(DriverSituation(
                driver_id=driver_id,
                name=name,
                role=role,
                position=idx + 1,
                lap=lap,
                total_laps=self.total_laps,
                gap_ahead_s=gap_ahead,
                gap_behind_s=gap_behind,
                tyre_life_pct=float(tyre_life),
                tyre_compound=tyre_compound,
                fuel_kg=float(fuel),
                speed_mps=pos.get("velocity_mps", 0.0),
                last_command_seq=last_seq,
                last_command_time=last_time,
            ))
        return situations

    def _suggestion_text(self, command: str, reason: str, urgency: str) -> str:
        """Gera texto natural da sugestão em português."""
        templates = {
            "push": [
                "Vamos lá, aumenta o ritmo!",
                "Hora de atacar, {reason}",
                "Push agora, {reason}",
                "Pode acelerar mais, {reason}",
            ],
            "overtake": [
                "Tenta a ultrapassagem na próxima curva!",
                "O carro à frente está ao alcance — vai por fora!",
                "Momento de passar, {reason}",
                "Freia mais tarde e passa por dentro, {reason}",
            ],
            "defend": [
                "Protege a linha interna, {reason}",
                "Não deixa passar, fecha a porta!",
                "Defesa ativa: {reason}",
                "Mantém a trajetória defensiva, {reason}",
            ],
            "conserve": [
                "Cuida dos pneus, {reason}",
                "Economiza um pouco: {reason}",
                "Gerencia o equipamento: {reason}",
                "Pé leve, {reason}",
            ],
            "careful": [
                "Cuidado aí, {reason}",
                "Mais margem nas curvas: {reason}",
                "Condições traiçoeiras, {reason}",
                "Traçado limpo agora, {reason}",
            ],
            "pace": [
                "Mantém o ritmo atual, {reason}",
                "Controla a vantagem: {reason}",
                "Ritmo constante: {reason}",
                "Não force, {reason}",
            ],
        }
        opts = templates.get(command, ["{reason}"])
        return random.choice(opts).format(reason=reason)

    # ==================== API PÚBLICA PARA INSPEÇÃO ====================

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas atuais do engenheiro."""
        return self._stats.copy()

    def is_running(self) -> bool:
        """Verifica se o engenheiro está rodando."""
        return self._thread is not None and self._thread.is_alive()

    def get_user_driver_recommendation(self) -> Optional[Recommendation]:
        """Retorna a última recomendação gerada para o piloto do usuário (se houver)."""
        # Isso seria implementado se mantivéssemos histórico
        # Por enquanto retorna None - o frontend recebe via events
        return None