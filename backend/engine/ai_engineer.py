"""Engenheiro de IA autônomo que avalia a corrida e emite recomendações.

Roda em background durante a corrida, lendo estado do motor/publicador e
tomando decisões estratégicas por piloto (push, conserve, pit, defend, etc.).

Arquitetura:
- Separação clara entre ANÁLISE (recomendação) e EXECUÇÃO (envio de comando)
- O piloto do usuário é ANALISADO mas NÃO recebe comandos automáticos
- Eventos de ciclo de vida explícitos para observabilidade no frontend
- Subscreve eventos em tempo real (clima, safety car, off-track, colisões, etc.)
- Deduplicação de mensagens para evitar repetições
"""

from __future__ import annotations

import json
import logging
import random
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set

import redis

from .coach_controller import CommandBus, normalize_command
from .events import (
    AiCommandEvent,
    AiSuggestionEvent,
    AiStartedEvent,
    AiMonitoringEvent,
    AiStoppedEvent,
    AiErrorEvent,
    WeatherChangedEvent,
    TyreWornEvent,
    PitStopEvent,
    OffTrackEvent,
    OnTrackEvent,
    CollisionEvent,
)

logger = logging.getLogger(__name__)


# ==================== EVENTOS DE RÁDIO (tipos adicionais) ====================

@dataclass
class RaceRadioEvent:
    """Evento de rádio da equipe (injetado via random_events ou simulação real)."""
    type: str = "race_radio"
    race_id: str = ""
    state: str = ""  # ataque, defesa, economia, cautela, info
    message: str = ""
    lap: int = 0
    sim_ts: float = 0.0


@dataclass
class RaceControlEvent:
    """Evento de controle de corrida (Safety Car, VSC, Bandeira Verde)."""
    type: str = "race_control"
    race_id: str = ""
    status: str = ""  # SAFETY_CAR, VSC, GREEN
    message: str = ""
    lap: int = 0
    sim_ts: float = 0.0


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
    # Estado de eventos recentes
    last_off_track: Optional[Dict[str, Any]] = None
    last_collision: Optional[Dict[str, Any]] = None
    last_tyre_worn: Optional[Dict[str, Any]] = None
    last_pit_stop: Optional[Dict[str, Any]] = None
    safety_car_active: bool = False
    weather_kind: str = "DRY"
    grip_factor: float = 1.0


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
    message_type: str = "tactical"  # tactical, event_reactive, routine


class AiEngineer:
    """Engenheiro de IA que gerencia a estratégia de todos os pilotos."""

    # Intervalos de decisão (tempo SIMULADO)
    DECISION_INTERVAL_S = 8.0  # avalia a cada 8s de simulação (era 5.0) - menos frequente
    MIN_COMMAND_INTERVAL_S = 20.0  # mínimo entre comandos no mesmo piloto (era 10.0) - cooldown maior
    PIT_WINDOW_START_PCT = 0.20
    PIT_WINDOW_END_PCT = 0.85

    # Thresholds configuráveis - MAIS CONSERVADORES para reduzir defend/attack
    TYRE_CRITICAL_PCT = 15.0
    TYRE_LOW_PCT = 30.0
    GAP_SMALL_S = 0.8      # era 1.5 - só defende/ataca se MUITO próximo
    GAP_MEDIUM_S = 2.0     # era 3.0
    GAP_LARGE_S = 4.0      # era 5.0
    FUEL_CRITICAL_KG = 3.0
    FUEL_LOW_KG = 8.0

    # Cooldowns por tipo de mensagem (segundos de simulação)
    MESSAGE_COOLDOWNS = {
        "defend": 30.0,
        "overtake": 30.0,
        "push": 25.0,
        "conserve": 40.0,
        "careful": 20.0,
        "pace": 30.0,
        "neutral": 60.0,
        "event_reactive": 15.0,  # reações a eventos podem ser mais frequentes
    }

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
        self._event_thread: Optional[threading.Thread] = None
        self._last_decision_sim_ts = 0.0
        self._started = False
        self._monitoring_active = False

        # Estado de eventos por piloto
        self._driver_events: Dict[str, DriverSituation] = {}
        # Última mensagem enviada por piloto (para deduplicação)
        self._last_message: Dict[str, Dict[str, Any]] = {}  # driver_id -> {command, reason, sim_ts, message_text}
        # Cooldowns por piloto e tipo de comando
        self._command_cooldowns: Dict[str, Dict[str, float]] = {}  # driver_id -> {command: last_sim_ts}
        # PubSub para eventos
        self._pubsub = None
        self._events_channel = f"race:{race_id}:events"

        # Estatísticas para observabilidade
        self._stats = {
            "cycles": 0,
            "recommendations_generated": 0,
            "commands_executed": 0,
            "user_driver_analyzed": 0,
            "event_reactions": 0,
            "deduplicated_messages": 0,
            "errors": 0,
            "last_cycle_sim_ts": 0.0,
        }

    # ==================== CICLO DE VIDA ====================

    def start(self) -> None:
        """Inicia o engenheiro de IA."""
        if not self.user_driver_id:
            return
        if self._thread and self._thread.is_alive():
            logger.warning("AiEngineer já rodando para corrida %s", self.race_id)
            return

        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"AiEngineer-{self.race_id[:8]}")
        self._thread.start()

        # Inicia thread de escuta de eventos
        self._event_thread = threading.Thread(target=self._listen_events, daemon=True, name=f"AiEngineer-Events-{self.race_id[:8]}")
        self._event_thread.start()

        self._started = True
        self._publish_lifecycle_event("ai_started", {
            "total_laps": self.total_laps,
            "user_driver_id": self.user_driver_id,
            "num_drivers": 1,
            "decision_interval_s": self.DECISION_INTERVAL_S,
        })
        logger.info("=== AiEngineer INICIADO para corrida %s ===", self.race_id)
        logger.info("  total_laps=%s, user_driver_id=%s, decision_interval=%.1fs",
                    self.total_laps, self.user_driver_id, self.DECISION_INTERVAL_S)

    def stop(self, reason: str = "race_ended") -> None:
        """Para o engenheiro de IA graciosamente."""
        if not self._started:
            return
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        if self._event_thread:
            self._event_thread.join(timeout=2.0)
        if self._pubsub:
            try:
                self._pubsub.close()
            except Exception:
                pass

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

    # ==================== ESCUTA DE EVENTOS (Nova thread) ====================

    def _listen_events(self) -> None:
        """Escuta eventos no canal Redis e atualiza estado dos pilotos."""
        logger.info("AiEngineer %s: iniciando escuta de eventos em %s", self.race_id, self._events_channel)
        try:
            self._pubsub = self.redis.pubsub()
            self._pubsub.subscribe(self._events_channel)
            for message in self._pubsub.listen():
                if self._stop.is_set():
                    break
                if message["type"] != "message":
                    continue
                try:
                    data = json.loads(message["data"])
                    self._process_event(data)
                except json.JSONDecodeError:
                    logger.debug("AiEngineer %s: evento JSON inválido", self.race_id)
                except Exception as e:
                    logger.exception("AiEngineer %s: erro processando evento: %s", self.race_id, e)
        except Exception as e:
            logger.exception("AiEngineer %s: erro na thread de eventos: %s", self.race_id, e)
        finally:
            logger.info("AiEngineer %s: thread de eventos finalizada", self.race_id)

    def _process_event(self, data: Dict[str, Any]) -> None:
        """Processa um evento e atualiza estado do piloto relevante."""
        event_type = data.get("type", "")
        driver_id = data.get("driver_id")
        sim_ts = data.get("sim_ts", 0.0)

        # Eventos globais (afetam todos)
        if event_type in ("weather_changed", "race_control"):
            for sit in self._driver_events.values():
                if event_type == "weather_changed":
                    sit.weather_kind = data.get("current", {}).get("kind", "DRY")
                    sit.grip_factor = data.get("current", {}).get("grip_factor", 1.0)
                elif event_type == "race_control":
                    sit.safety_car_active = data.get("status") in ("SAFETY_CAR", "VSC")
            self._stats["event_reactions"] += 1
            logger.debug("AiEngineer %s: evento global %s processado", self.race_id, event_type)
            return

        # Eventos específicos de piloto
        if not driver_id or driver_id not in self._driver_events:
            # Pode ser evento para piloto que ainda não temos no estado - ignora ou cria placeholder
            return

        sit = self._driver_events[driver_id]
        if event_type == "off_track":
            sit.last_off_track = data
        elif event_type == "on_track":
            sit.last_off_track = None  # voltou à pista
        elif event_type == "collision":
            sit.last_collision = data
        elif event_type == "tyre_worn":
            sit.last_tyre_worn = data
        elif event_type == "pit_stop":
            sit.last_pit_stop = data
        elif event_type == "race_radio":
            # Rádio da equipe - pode gerar sugestão imediata
            self._handle_radio_event(sit, data)
        self._stats["event_reactions"] += 1

    def _handle_radio_event(self, sit: DriverSituation, data: Dict[str, Any]) -> None:
        """Processa evento de rádio da equipe e pode gerar sugestão imediata."""
        state = data.get("state", "")
        message = data.get("message", "")
        if not message:
            return
        # Gera recomendação reativa baseada no rádio
        # Não executa comando, apenas publica sugestão textual
        rec = Recommendation(
            driver_id=sit.driver_id,
            driver_name=sit.name,
            command="neutral",  # comando neutro, só a mensagem importa
            value=0.0,
            reason=message,
            urgency="media" if state in ("ataque", "defesa", "cautela") else "baixa",
            should_execute=False,
            confidence=0.7,
            message_type="event_reactive",
        )
        self._publish_suggestion_only(rec)

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

                # Executa recomendações
                for rec in recommendations:
                    if rec.should_execute:
                        # Bots: executa comando + publica sugestão (rule-based)
                        self._execute_recommendation(rec)
                    else:
                        # User driver: publica sugestão SE Ollama estiver desabilitado
                        # (se Ollama estiver ON, redis_listener publica com LLM)
                        try:
                            use_ollama = self.redis.get("settings:use_ollama") == "true"
                        except Exception:
                            use_ollama = False
                        if not use_ollama:
                            self._publish_suggestion_only(rec)
                        # Se use_ollama=True, não publica aqui (Ollama cuida)

                # Publica heartbeat de monitoring a cada 10 ciclos (~8s real)
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
        Avalia a corrida e gera recomendações para o piloto do usuário.
        NÃO executa comandos - apenas retorna lista de recomendações.
        """
        if not self.user_driver_id:
            return []

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
        situations = self._build_situations(positions, last_tick, sim_ts)

        # Analisa cada piloto (inclui o do usuário)
        recommendations = []
        for sit in situations:
            rec = self._analyze_driver(sit, positions, sim_ts)
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

    def _analyze_driver(self, sit: DriverSituation, all_positions: List[Dict[str, Any]], sim_ts: float) -> Optional[Recommendation]:
        """
        Analisa UM piloto e retorna recomendação.
        NÃO executa - apenas decide o que seria ideal.
        """
        now = time.time()
        progress_pct = sit.lap / max(1, self.total_laps)

        # Rate limit por piloto (tempo REAL)
        if sit.last_command_seq >= 0 and now - sit.last_command_time < self.MIN_COMMAND_INTERVAL_S:
            logger.debug("AiEngineer %s: rate limit REAL para %s (%.1fs desde último comando)",
                         self.race_id, sit.driver_id, now - sit.last_command_time)
            return None

        # Determina papel do piloto
        is_user = (sit.driver_id == self.user_driver_id)
        role = DriverRole.USER if is_user else DriverRole.AI_BOT

        # Verifica cooldown por tipo de comando (tempo SIMULADO)
        if not self._is_command_allowed(sit.driver_id, "any", sim_ts):
            return None

        command = None
        value = 0.0
        reason = ""
        urgency = "baixa"
        confidence = 1.0
        message_type = "tactical"

        # Log de contexto para debug
        logger.debug("AiEngineer %s: Analisando %s (role=%s) P%s lap=%d/%d tyre=%.0f%% fuel=%.1fkg "
                     "gap_ahead=%s gap_behind=%s weather=%s grip=%.2f sc=%s",
                     self.race_id, sit.name, role.value, sit.position, sit.lap, self.total_laps,
                     sit.tyre_life_pct, sit.fuel_kg, sit.gap_ahead_s, sit.gap_behind_s,
                     sit.weather_kind, sit.grip_factor, sit.safety_car_active)

        # ========== PRIORIDADE 1: EVENTOS REATIVOS (têm precedência) ==========
        rec = self._check_event_reactions(sit, sim_ts)
        if rec:
            return rec

        # ========== PRIORIDADE 2: SAFETY CAR / VSC ==========
        if sit.safety_car_active:
            command = "careful"
            value = 0.0
            reason = "Safety Car/VSC ativo — mantém delta, aquece pneus e freios"
            urgency = "media"
            confidence = 0.95
            message_type = "event_reactive"

        # ========== PRIORIDADE 3: PIT STOP NECESSÁRIO? ==========
        elif self._should_pit(sit, progress_pct):
            command = "conserve"
            value = 0.85
            reason = (f"Pneus {sit.tyre_compound} {sit.tyre_life_pct:.0f}% / "
                      f"Combustível {sit.fuel_kg:.1f}kg — janela de pit aberta ({progress_pct:.0%})")
            urgency = "alta"
            confidence = 0.95

        # ========== PRIORIDADE 4: DEFESA / ATAQUE por posição (THRESHOLDS MAIS ALTOS) ==========
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

        # ========== PRIORIDADE 5: GESTÃO DE PNEUS / COMBUSTÍVEL (fora da janela de pit) ==========
        elif sit.tyre_life_pct <= self.TYRE_CRITICAL_PCT:
            command = "conserve"
            value = 0.80
            reason = f"Pneus {sit.tyre_compound} críticos ({sit.tyre_life_pct:.0f}%) — preservação máxima"
            urgency = "alta"
            confidence = 0.95

        elif sit.tyre_life_pct <= self.TYRE_LOW_PCT and not self._in_pit_window(progress_pct):
            command = "conserve"
            value = 0.90
            reason = f"Preservando pneus {sit.tyre_compound} ({sit.tyre_life_pct:.0f}%) até janela de pit"
            urgency = "baixa"
            confidence = 0.85

        elif sit.fuel_kg <= self.FUEL_CRITICAL_KG:
            command = "conserve"
            value = 0.80
            reason = f"Combustível crítico ({sit.fuel_kg:.1f}kg) — economizando para terminar"
            urgency = "alta"
            confidence = 0.95

        elif sit.fuel_kg <= self.FUEL_LOW_KG and not self._in_pit_window(progress_pct):
            command = "conserve"
            value = 0.92
            reason = f"Combustível baixo ({sit.fuel_kg:.1f}kg) — gerenciando até pit"
            urgency = "media"
            confidence = 0.80

        # ========== PRIORIDADE 6: CLIMA / ADERÊNCIA ==========
        elif sit.grip_factor < 0.85 or sit.weather_kind in ("WET", "DAMP", "HEAVY_RAIN"):
            command = "careful"
            value = 0.0
            reason = f"Pista {sit.weather_kind.lower()} (aderência {sit.grip_factor:.0%}) — mais margem nas frenagens"
            urgency = "media"
            confidence = 0.90
            message_type = "event_reactive"

        # ========== PRIORIDADE 7: LIDERANÇA: gerencia vantagem ==========
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
                reason = f"Líder confortável (gap {sit.gap_behind_s:.1f}s se houver) — gerenciando vantagem"
                urgency = "baixa"
                confidence = 0.70

        # ========== PRIORIDADE 8: ÚLTIMAS VOLTAS: tudo ou nada ==========
        elif sit.lap >= self.total_laps - 2:
            command = "push"
            value = 0.0
            reason = f"Últimas voltas ({sit.lap}/{self.total_laps}) — ataque total"
            urgency = "alta"
            confidence = 0.90

        # ========== PRIORIDADE 9: MEIO DE CORRIDA: ritmo consistente ==========
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

        # ========== PRIORIDADE 10: VARIAÇÃO OCASIONAL (simula engenheiro humano) ==========
        elif random.random() < 0.02:  # 2% chance (era 3-5%)
            command = random.choice(["push", "conserve", "careful", "pace"])
            reason = "Ajuste de ritmo rotineiro"
            urgency = "baixa"
            confidence = 0.40

        # Se não há recomendação aplicável
        if command is None or command == "neutral":
            logger.debug("AiEngineer %s: %s sem recomendação aplicável no momento", self.race_id, sit.driver_id)
            return None

        # Verifica cooldown específico do comando
        if not self._is_command_allowed(sit.driver_id, command, sim_ts):
            logger.debug("AiEngineer %s: cooldown ativo para %s comando %s", self.race_id, sit.driver_id, command)
            return None

        # Normaliza comando
        norm_cmd = normalize_command(command)

        # Verifica deduplicação de mensagem
        if self._is_duplicate_message(sit.driver_id, norm_cmd, reason, sim_ts):
            self._stats["deduplicated_messages"] += 1
            logger.debug("AiEngineer %s: mensagem duplicada evitada para %s (%s)", self.race_id, sit.driver_id, norm_cmd)
            return None

        return Recommendation(
            driver_id=sit.driver_id,
            driver_name=sit.name,
            command=norm_cmd,
            value=value,
            reason=reason,
            urgency=urgency,
            should_execute=not is_user,  # NÃO executa para piloto do usuário
            confidence=confidence,
            message_type=message_type,
        )

    def _check_event_reactions(self, sit: DriverSituation, sim_ts: float) -> Optional[Recommendation]:
        """Verifica eventos recentes e gera recomendações reativas."""
        # Off-track recente
        if sit.last_off_track:
            severity = sit.last_off_track.get("severity", "leve")
            side = sit.last_off_track.get("side", "")
            time_since = sim_ts - sit.last_off_track.get("sim_ts", 0)
            if time_since < 30:  # só reage se foi recente (30s sim)
                command = "careful"
                value = 0.0
                reason = f"Saída de pista {side} ({severity}) — cuidado na retomada, evite erros"
                urgency = "media" if severity == "grave" else "baixa"
                confidence = 0.85
                return Recommendation(
                    driver_id=sit.driver_id,
                    driver_name=sit.name,
                    command=command,
                    value=value,
                    reason=reason,
                    urgency=urgency,
                    should_execute=False,
                    confidence=confidence,
                    message_type="event_reactive",
                )

        # Colisão recente
        if sit.last_collision:
            time_since = sim_ts - sit.last_collision.get("sim_ts", 0)
            if time_since < 20:
                command = "careful"
                value = 0.0
                reason = "Contato detectado — verifica danos, mantém traçado limpo"
                urgency = "media"
                confidence = 0.80
                return Recommendation(
                    driver_id=sit.driver_id,
                    driver_name=sit.name,
                    command=command,
                    value=value,
                    reason=reason,
                    urgency=urgency,
                    should_execute=False,
                    confidence=confidence,
                    message_type="event_reactive",
                )

        # Pneu crítico reportado
        if sit.last_tyre_worn:
            time_since = sim_ts - sit.last_tyre_worn.get("sim_ts", 0)
            if time_since < 60:
                compound = sit.last_tyre_worn.get("compound", "")
                life = sit.last_tyre_worn.get("tyre_life_pct", 0)
                command = "conserve"
                value = 0.85
                reason = f"Pneu {compound} com {life}% — equipe confirma degradação, cuida deles"
                urgency = "alta"
                confidence = 0.90
                return Recommendation(
                    driver_id=sit.driver_id,
                    driver_name=sit.name,
                    command=command,
                    value=value,
                    reason=reason,
                    urgency=urgency,
                    should_execute=False,
                    confidence=confidence,
                    message_type="event_reactive",
                )

        # Pit stop recente (próprio ou rival)
        if sit.last_pit_stop:
            time_since = sim_ts - sit.last_pit_stop.get("sim_ts", 0)
            if time_since < 40:
                driver = sit.last_pit_stop.get("driver_id", "")
                compound = sit.last_pit_stop.get("new_compound", "")
                if driver == sit.driver_id:
                    command = "push"
                    value = 0.0
                    reason = f"Pit stop concluído ({compound}) — pneus frios, aqueça com voltas de push"
                    urgency = "media"
                    confidence = 0.80
                else:
                    command = "pace"
                    value = 0.98
                    reason = f"Rival {driver} fez pit ({compound}) — mantém ritmo, monitora undercut/overcut"
                    urgency = "baixa"
                    confidence = 0.70
                return Recommendation(
                    driver_id=sit.driver_id,
                    driver_name=sit.name,
                    command=command,
                    value=value,
                    reason=reason,
                    urgency=urgency,
                    should_execute=False,
                    confidence=confidence,
                    message_type="event_reactive",
                )

        return None

    def _should_pit(self, sit: DriverSituation, progress_pct: float) -> bool:
        """Verifica se deve recomendar pit stop."""
        in_pit_window = self.PIT_WINDOW_START_PCT <= progress_pct <= self.PIT_WINDOW_END_PCT
        tyre_critical = sit.tyre_life_pct <= self.TYRE_CRITICAL_PCT
        tyre_low = sit.tyre_life_pct <= self.TYRE_LOW_PCT
        fuel_low = sit.fuel_kg <= self.FUEL_LOW_KG
        return in_pit_window and (tyre_critical or (tyre_low and sit.lap > 3) or fuel_low)

    def _in_pit_window(self, progress_pct: float) -> bool:
        return self.PIT_WINDOW_START_PCT <= progress_pct <= self.PIT_WINDOW_END_PCT

    def _is_command_allowed(self, driver_id: str, command: str, sim_ts: float) -> bool:
        """Verifica se o comando passou do cooldown."""
        if driver_id not in self._command_cooldowns:
            self._command_cooldowns[driver_id] = {}
        cooldowns = self._command_cooldowns[driver_id]
        
        # Verifica cooldown do comando específico
        if command != "any":
            last_ts = cooldowns.get(command, 0)
            cooldown = self.MESSAGE_COOLDOWNS.get(command, 20.0)
            if sim_ts - last_ts < cooldown:
                return False
        
        # Verifica cooldown geral (qualquer comando)
        last_any = max(cooldowns.values()) if cooldowns else 0
        if sim_ts - last_any < 10.0:  # mínimo 10s entre quaisquer comandos
            return False
        
        return True

    def _mark_command_sent(self, driver_id: str, command: str, sim_ts: float) -> None:
        """Marca que um comando foi enviado para cooldown."""
        if driver_id not in self._command_cooldowns:
            self._command_cooldowns[driver_id] = {}
        self._command_cooldowns[driver_id][command] = sim_ts

    def _is_duplicate_message(self, driver_id: str, command: str, reason: str, sim_ts: float) -> bool:
        """Verifica se a mensagem é duplicada (mesmo comando + razão similar)."""
        last = self._last_message.get(driver_id)
        if not last:
            return False
        
        # Mesmo comando E razão muito similar (mesmo texto ou prefixo similar)
        if last["command"] == command:
            # Verifica se a razão é essencialmente a mesma
            last_reason = last.get("reason", "")
            if self._reasons_similar(last_reason, reason):
                # Também verifica tempo mínimo (não repetir em menos de 15s sim)
                if sim_ts - last.get("sim_ts", 0) < 15.0:
                    return True
        
        return False

    def _reasons_similar(self, reason1: str, reason2: str) -> bool:
        """Verifica se duas razões são semanticamente similares."""
        if not reason1 or not reason2:
            return False
        # Comparação simples: se compartilham palavras-chave principais
        # Usa prefix matching para capturar variações (ultrapassagem, ultrapassar, etc.)
        words1 = reason1.lower().split()
        words2 = reason2.lower().split()
        
        # Palavras-chave raiz que indicam mesmo contexto
        key_roots = ["gap", "defend", "protege", "ultrapass", "attack", "push", "ritmo", "pace", 
                     "pneu", "tyre", "combust", "fuel", "pit", "safety", "chuva", "wet", "ader",
                     "preserv", "econom", "gerenc", "lider", "pressur", "ultimas", "ataque",
                     "posiç", "posicao", "tras", "frente", "delta", "virtual", "carro", "rival",
                     "critic", "baixo", "terminar", "mantem", "administr"]
        
        def has_root(words, root):
            return any(w.startswith(root) for w in words)
        
        common_roots = sum(1 for root in key_roots if has_root(words1, root) and has_root(words2, root))
        return common_roots >= 2  # pelo menos 2 raízes-chave em comum

    def _record_message(self, driver_id: str, command: str, reason: str, sim_ts: float, message_text: str) -> None:
        """Registra mensagem enviada para deduplicação futura."""
        self._last_message[driver_id] = {
            "command": command,
            "reason": reason,
            "sim_ts": sim_ts,
            "message_text": message_text,
        }
        self._mark_command_sent(driver_id, command, sim_ts)

    # ==================== EXECUÇÃO (SEPARADA DA ANÁLISE) ====================

    def _execute_recommendation(self, rec: Recommendation) -> None:
        """Executa uma recomendação enviando comando ao barramento."""
        try:
            # Verifica coerência e dispara rádio do piloto se necessário (para TODOS os pilotos)
            suggestion_text = self._suggestion_text(rec.command, rec.reason, rec.urgency, rec.message_type)
            coherence_check = self._check_message_coherence(rec, suggestion_text)
            if coherence_check["has_issue"]:
                logger.warning("AiEngineer %s: INCOERÊNCIA detectada para %s — %s (conf=%.0f%%)",
                              self.race_id, rec.driver_name, coherence_check["issue"], rec.confidence * 100)
                rec.confidence = max(0.1, rec.confidence * 0.5)
                if coherence_check["issue"] == "repetitive_context":
                    suggestion_text = self._generate_corrected_message(rec)
                    logger.info("AiEngineer %s: Auto-correção aplicada — nova msg: %s", 
                               self.race_id, suggestion_text)
                # Dispara rádio do piloto para QUALQUER piloto com incoerência
                self._publish_driver_radio_response(rec, suggestion_text, coherence_check)

            self.bus.push(rec.driver_id, rec.command, rec.value, rec.reason, issued_by="ai")
            self._stats["commands_executed"] += 1
            self._record_message(rec.driver_id, rec.command, rec.reason, 
                                float(getattr(self.engine, "sim_ts", 0)), suggestion_text)

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

            logger.info("=== AiEngineer %s COMANDO EXECUTADO para %s: %s %.2f — %s [%s] (conf=%.0f%%) ===",
                        self.race_id, rec.driver_name, rec.command, rec.value, rec.reason, rec.urgency, rec.confidence * 100)

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
            suggestion_text = self._suggestion_text(rec.command, rec.reason, rec.urgency, rec.message_type)

            # ===== AUTO-DETECÇÃO DE MENSAGENS SEM NEXO =====
            coherence_check = self._check_message_coherence(rec, suggestion_text)
            if coherence_check["has_issue"]:
                # Loga o problema detectado
                logger.warning("AiEngineer %s: INCOERÊNCIA detectada para %s — %s (conf=%.0f%%)",
                              self.race_id, rec.driver_name, coherence_check["issue"], rec.confidence * 100)
                # Reduz confiança se a mensagem não faz sentido no contexto
                rec.confidence = max(0.1, rec.confidence * 0.5)
                # Adiciona flag no comando para o frontend saber
                if rec.command and isinstance(rec.command, str):
                    pass  # O evento será publicado com confiança reduzida
                
                # Auto-correção: se a mensagem é repetitiva demais, tenta variar
                if coherence_check["issue"] == "repetitive_context":
                    suggestion_text = self._generate_corrected_message(rec)
                    logger.info("AiEngineer %s: Auto-correção aplicada — nova msg: %s", 
                               self.race_id, suggestion_text)

            if self.publisher:
                self.publisher.publish(AiSuggestionEvent(
                    sim_ts=float(getattr(self.engine, "sim_ts", 0)),
                    race_id=self.race_id,
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

            # ===== RESPOSTA DO PILOTO (fallback) quando IA fala bobagem =====
            # Dispara se: confiança caiu muito OU incoerência detectada
            should_driver_respond = (
                rec.confidence < 0.5  # confiança baixa (< 50%)
                or coherence_check["has_issue"]  # incoerência detectada
            )
            if should_driver_respond:
                self._publish_driver_radio_response(rec, suggestion_text, coherence_check)

            # Registra para deduplicação
            self._record_message(rec.driver_id, rec.command, rec.reason,
                                float(getattr(self.engine, "sim_ts", 0)), suggestion_text)

            logger.info("=== AiEngineer %s SUGESTÃO para piloto do usuário %s: %s [%s] (conf=%.0f%%) ===",
                        self.race_id, rec.driver_name, suggestion_text, rec.urgency, rec.confidence * 100)

        except Exception as e:
            logger.error("Falha ao publicar sugestão para %s: %s", rec.driver_id, e)

    def _publish_driver_radio_response(self, rec: Recommendation, ai_message: str, coherence_check: Dict[str, Any]) -> None:
        """Publica resposta do piloto (fallback determinístico) quando IA fala bobagem."""
        if not self.publisher:
            return
        
        # Rate limit: não responde toda vez, só às vezes
        driver_key = f"driver_radio_last_{rec.driver_id}"
        last_response_ts = getattr(self, driver_key, 0)
        sim_ts = float(getattr(self.engine, "sim_ts", 0))
        if sim_ts - last_response_ts < 20.0:  # mínimo 20s sim entre respostas
            return
        
        # Escolhe resposta baseada no trigger
        trigger = coherence_check.get("issue", "low_confidence")
        response = self._get_driver_radio_response(rec, trigger, ai_message)
        
        if response:
            setattr(self, driver_key, sim_ts)
            
            self.publisher.publish(DriverRadioEvent(
                sim_ts=sim_ts,
                driver_id=rec.driver_id,
                driver_name=rec.driver_name,
                lap=int(getattr(self.engine, "current_lap", 1)) if hasattr(self.engine, "current_lap") else 1,
                message=response,
                trigger=trigger,
                confidence=rec.confidence,
            ))
            
            logger.info("=== AiEngineer %s PILOTO RESPONDE %s: %s [trigger=%s] ===",
                        self.race_id, rec.driver_name, response, trigger)

    def _get_driver_radio_response(self, rec: Recommendation, trigger: str, ai_message: str) -> Optional[str]:
        """Gera resposta do piloto baseada no trigger (fallback determinístico)."""
        import random
        
        name = rec.driver_name
        command = rec.command
        
        # Respostas por trigger
        responses = {
            "repetitive_context": [
                f"Já entendi, {name} aqui. Para de repetir a mesma merda.",
                "Cara, você já falou isso três vezes. Muda o disco.",
                "Entendi na primeira, engenheiro. Não precisa repetir.",
                "Já disse: tô ligado. Para de encher o saco.",
            ],
            "defend_without_threat": [
                f"Defender de quem? Não tem ninguém atrás, {name}.",
                "Engenheiro, o espelho tá limpo. Relaxa.",
                "Ninguém colado em mim. Essa info tá velha.",
            ],
            "overtake_too_far": [
                f"Ultrapassar quem? O cara tá a 5 segundos, {name}.",
                "Tá longe demais pra tentar passar agora. Espera.",
                "Gap grande demais. Vou só queimar pneu à toa.",
            ],
            "push_on_critical_resources": [
                "Push com pneu no talo e combustível acabando? Tu tá de brincadeira.",
                "Cara, não dá pra atacar assim. O carro não aguenta.",
                "Pneu acabando, combustível no reserva. Push é suicídio.",
            ],
            "conserve_unnecessary": [
                f"Economizar o quê? Pneu bom, tanque cheio. {name} quer é andar.",
                "Não precisa economizar nada agora. Deixa eu pilotar.",
                "Equipamento 100%. Por que eu ia ir devagar?",
            ],
            "stale_message_context_changed": [
                "Essa info tá velha, a corrida mudou completamente.",
                "Engenheiro, atualiza o radar. Isso aí não serve mais.",
                "Contexto mudou, a mensagem não cola mais.",
            ],
            "generic_low_confidence": [
                "Mensagem genérica, confiança baixa... Tô por minha conta.",
                "Não entendi a direção. Vou no feeling mesmo.",
                "Fala sério, isso não me ajuda em nada.",
            ],
            "low_confidence": [
                f"Confiança {int(rec.confidence * 100)}%? Decide aí, {name} tá pilotando.",
                "Tá em cima do muro? Ou manda push ou manda economizar.",
                "Essa indecisão não ajuda. Fecha a porta ou abre.",
            ],
        }
        
        opts = responses.get(trigger, responses["low_confidence"])
        return random.choice(opts)

    def _check_message_coherence(self, rec: Recommendation, message_text: str) -> Dict[str, Any]:
        """
        Verifica se a mensagem faz sentido no contexto atual.
        Retorna dict com has_issue (bool) e issue (str descrição).
        """
        sit = self._driver_events.get(rec.driver_id)
        if not sit:
            return {"has_issue": False, "issue": ""}

        sim_ts = float(getattr(self.engine, "sim_ts", 0))
        last = self._last_message.get(rec.driver_id)
        
        issues = []

        # 1. Verifica se a mensagem contradiz o estado atual
        if rec.command == "defend" and sit.gap_behind_s is not None and sit.gap_behind_s > 3.0:
            issues.append("defend_without_threat")
        
        if rec.command == "overtake" and sit.gap_ahead_s is not None and sit.gap_ahead_s > 5.0:
            issues.append("overtake_too_far")
        
        if rec.command == "push" and sit.tyre_life_pct < 15 and sit.fuel_kg < 5:
            issues.append("push_on_critical_resources")
        
        if rec.command == "conserve" and sit.tyre_life_pct > 80 and sit.fuel_kg > 30 and self._in_pit_window(sit.lap / max(1, self.total_laps)) == False:
            issues.append("conserve_unnecessary")

        # 2. Verifica se mudou o contexto mas a mensagem é a mesma (stale message)
        if last:
            time_since_last = sim_ts - last.get("sim_ts", 0)
            if time_since_last > 60:  # mais de 1min sim sem mudança de contexto relevante
                # Verifica se gaps mudaram significativamente
                if sit.gap_ahead_s is not None and last.get("gap_ahead_s") is not None:
                    gap_change = abs(sit.gap_ahead_s - last["gap_ahead_s"])
                    if gap_change > 2.0 and last.get("command") == rec.command:
                        issues.append("stale_message_context_changed")
            
            # Salva gaps atuais para próxima comparação
            self._last_message[rec.driver_id]["gap_ahead_s"] = sit.gap_ahead_s
            self._last_message[rec.driver_id]["gap_behind_s"] = sit.gap_behind_s
            self._last_message[rec.driver_id]["tyre_life_pct"] = sit.tyre_life_pct

        # 3. Verifica repetição excessiva (mesmo comando 2+ vezes em janela curta)
        recent_same_cmd = self._count_recent_same_command(rec.driver_id, rec.command, sim_ts, window_s=60.0)
        if recent_same_cmd >= 2:
            issues.append("repetitive_context")

        # 4. Verifica mensagem genérica demais (baixa confiança + razão genérica)
        if rec.confidence < 0.5 and rec.reason in ("Ajuste de ritmo rotineiro", "Sem situação crítica detectada"):
            issues.append("generic_low_confidence")

        if issues:
            return {"has_issue": True, "issue": issues[0], "all_issues": issues}
        
        return {"has_issue": False, "issue": ""}

    def _count_recent_same_command(self, driver_id: str, command: str, sim_ts: float, window_s: float = 120.0) -> int:
        """Conta quantas vezes o mesmo comando foi enviado na janela de tempo recente."""
        # Usa histórico simplificado - verifica no _last_message e cooldowns
        count = 0
        cooldowns = self._command_cooldowns.get(driver_id, {})
        for cmd, ts in cooldowns.items():
            if cmd == command and sim_ts - ts < window_s:
                count += 1
        return count

    def _generate_corrected_message(self, rec: Recommendation) -> str:
        """Gera uma mensagem corrigida quando detecta repetição excessiva."""
        # Templates de correção por tipo de comando
        corrections = {
            "pace": [
                "Mantém o ritmo, mas atento às mudanças de pista",
                "Controla a vantagem — pneus e combustível estáveis por enquanto",
                "Ritmo constante, monitorando desgaste dos compostos",
            ],
            "defend": [
                "Protege a posição, mas sem exagerar na defesa",
                "Fecha a porta nas freadas, acelera nas saídas",
                "Linha interna tua — força o rival a arriscar por fora",
            ],
            "push": [
                "Aumenta o ritmo progressivamente, cuida dos pneus",
                "Push controlado — ganha tempo sem destruir os compostos",
                "Ritmo forte nas retas, limpo nas curvas",
            ],
            "conserve": [
                "Administra o equipamento — lift and coast nas retas longas",
                "Preserva pneus e combustível — evita curvas agressivas",
                "Modo economia inteligente — mantém volta consistente",
            ],
            "careful": [
                "Mais margem nas freadas, traçado limpo",
                "Condições exigem cautela — evita zebras e bordas",
                "Freia mais cedo, acelera progressivamente",
            ],
        }
        
        opts = corrections.get(rec.command, ["Mantém o plano atual, situação sob controle"])
        import random
        return random.choice(opts)

    # ==================== HELPERS ====================

    def _build_situations(
        self, positions: List[Dict[str, Any]], last_tick: Dict[str, Any], sim_ts: float
    ) -> List[DriverSituation]:
        """Constrói situação tática de cada piloto a partir do tick."""
        situations = []
        lap = int(last_tick.get("lap", 1))
        weather = last_tick.get("weather", {})
        weather_kind = weather.get("kind", "DRY")
        grip_factor = weather.get("grip_factor", 1.0)
        safety_car = last_tick.get("safety_car_active", False)

        for idx, pos in enumerate(positions):
            driver_id = pos.get("driver_id")
            if driver_id != self.user_driver_id:
                continue
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

            # Recupera eventos anteriores se existirem
            prev_sit = self._driver_events.get(driver_id)

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
                last_off_track=prev_sit.last_off_track if prev_sit else None,
                last_collision=prev_sit.last_collision if prev_sit else None,
                last_tyre_worn=prev_sit.last_tyre_worn if prev_sit else None,
                last_pit_stop=prev_sit.last_pit_stop if prev_sit else None,
                safety_car_active=safety_car,
                weather_kind=weather_kind,
                grip_factor=grip_factor,
            ))

        # Atualiza estado interno
        self._driver_events = {s.driver_id: s for s in situations}
        return situations

    # ==================== TEMPLATES DE MENSAGEM EXPANDIDOS ====================

    def _suggestion_text(self, command: str, reason: str, urgency: str, message_type: str = "tactical") -> str:
        """Gera texto natural da sugestão em português com MUITA variedade."""
        
        # Templates expandidos por tipo de comando
        templates = {
            "push": {
                "tactical": [
                    "Vamos lá, aumenta o ritmo!",
                    "Hora de atacar, {reason}",
                    "Push agora, {reason}",
                    "Pode acelerar mais, {reason}",
                    "Vamos pressionar, {reason}",
                    "Ritmo mais forte, {reason}",
                    "Abre o DRS e vai, {reason}",
                ],
                "event_reactive": [
                    "Pneus novos, vamos aquecer — {reason}",
                    "Undercut do rival, reage agora — {reason}",
                    "Pista livre à frente, {reason}",
                ],
                "routine": [
                    "Mantém a pressão, {reason}",
                    "Não deixa o ritmo cair, {reason}",
                ],
            },
            "overtake": {
                "tactical": [
                    "Tenta a ultrapassagem na próxima curva!",
                    "O carro à frente está ao alcance — vai por fora!",
                    "Momento de passar, {reason}",
                    "Freia mais tarde e passa por dentro, {reason}",
                    "DRS aberto, zona de ultrapassagem — {reason}",
                    "Cola nele e passa na reta, {reason}",
                    "Está mais rápido, faz a ultrapassagem limpa, {reason}",
                ],
                "event_reactive": [
                    "Rival com pneus gastos — {reason}",
                    "Rival errou na curva anterior — {reason}",
                ],
                "routine": [],
            },
            "defend": {
                "tactical": [
                    "Protege a linha interna, {reason}",
                    "Não deixa passar, fecha a porta!",
                    "Defesa ativa: {reason}",
                    "Mantém a trajetória defensiva, {reason}",
                    "Fecha a porta na freada, {reason}",
                    "Linha interna é tua, {reason}",
                    "Não abre espaço, {reason}",
                ],
                "event_reactive": [
                    "Rival com DRS — {reason}",
                    "Pressão vindo de trás — {reason}",
                ],
                "routine": [],
            },
            "conserve": {
                "tactical": [
                    "Cuida dos pneus, {reason}",
                    "Economiza um pouco: {reason}",
                    "Gerencia o equipamento: {reason}",
                    "Pé leve, {reason}",
                    "Preserva os pneus, {reason}",
                    "Lift and coast nas retas, {reason}",
                    "Não abuse da tração, {reason}",
                    "Modo economia ativado, {reason}",
                ],
                "event_reactive": [
                    "Pit window aberta, {reason}",
                    "Pneus no limite, {reason}",
                    "Combustível baixo, {reason}",
                ],
                "routine": [
                    "Administra o stint, {reason}",
                ],
            },
            "careful": {
                "tactical": [
                    "Cuidado aí, {reason}",
                    "Mais margem nas curvas: {reason}",
                    "Condições traiçoeiras, {reason}",
                    "Traçado limpo agora, {reason}",
                    "Evita as zebras, {reason}",
                    "Freia mais cedo, {reason}",
                    "Pista escorregadia, {reason}",
                ],
                "event_reactive": [
                    "Safety Car/VSC — {reason}",
                    "Saída de pista recente — {reason}",
                    "Contato detectado — {reason}",
                    "Chuva chegando — {reason}",
                ],
                "routine": [
                    "Mantém o carro na pista, {reason}",
                ],
            },
            "pace": {
                "tactical": [
                    "Mantém o ritmo atual, {reason}",
                    "Controla a vantagem: {reason}",
                    "Ritmo constante: {reason}",
                    "Não force, {reason}",
                    "Gerencia a diferença, {reason}",
                    "Volta consistente, {reason}",
                    "Administra a liderança, {reason}",
                ],
                "event_reactive": [
                    "Rival fez pit — {reason}",
                    "Vantagem estável — {reason}",
                ],
                "routine": [
                    "Tudo sob controle, {reason}",
                ],
            },
            "neutral": {
                "tactical": [
                    "Tudo normal, {reason}",
                    "Mantém o plano, {reason}",
                    "Sem novidades, {reason}",
                ],
                "event_reactive": [],
                "routine": [],
            },
        }

        # Se é mensagem reativa a evento, usa templates específicos
        if message_type == "event_reactive" and templates.get(command, {}).get("event_reactive"):
            opts = templates[command]["event_reactive"]
        elif message_type == "routine" and templates.get(command, {}).get("routine"):
            opts = templates[command]["routine"]
        else:
            opts = templates.get(command, {}).get("tactical", ["{reason}"])

        # Escolhe template aleatório
        template = random.choice(opts)
        
        # Formata com a razão
        try:
            return template.format(reason=reason)
        except KeyError:
            return reason

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