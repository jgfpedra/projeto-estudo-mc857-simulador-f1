"""Event types published by the simulation engine.

Todos os eventos derivam de :class:`Event` e são serializáveis via
``to_dict()``. O ``Publisher`` é responsável por enviá-los
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Event:
    """Evento base. ``ts`` é timestamp Unix; ``sim_ts`` é tempo simulado (s)."""

    type: str
    ts: float = field(default_factory=time.time)
    sim_ts: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class RaceStartEvent(Event):
    type: str = "race_start"
    race_id: str = ""
    track_name: str = ""
    num_laps: int = 0
    num_drivers: int = 0
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RaceEndEvent(Event):
    type: str = "race_end"
    race_id: str = ""
    final_classification: List[Dict[str, Any]] = field(default_factory=list)
    total_time_s: float = 0.0


@dataclass
class LapCompletedEvent(Event):
    type: str = "lap_completed"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    lap_time_s: float = 0.0
    best_lap_time_s: float = 0.0
    fuel_kg: float = 0.0
    tyre: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WeatherChangedEvent(Event):
    type: str = "weather_changed"
    lap: int = 0
    previous: Dict[str, Any] = field(default_factory=dict)
    current: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TyreWornEvent(Event):
    """Emitido quando a vida do pneu cruza um threshold crítico."""
    type: str = "tyre_worn"
    driver_id: str = ""
    driver_name: str = ""
    compound: str = ""
    tyre_life_pct: float = 0.0
    age_laps: float = 0.0


@dataclass
class PitStopEvent(Event):
    type: str = "pit_stop"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    new_compound: str = ""
    fuel_added_kg: float = 0.0
    pit_time_s: float = 0.0


@dataclass
class PitRequestedEvent(Event):
    """Confirma que a engine registrou um pedido manual ou automático."""
    type: str = "pit_requested"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    tyre_compound: str = ""
    source: str = "user"


@dataclass
class PitCancelledEvent(Event):
    type: str = "pit_cancelled"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    source: str = "user"


@dataclass
class PitCancelRejectedEvent(Event):
    type: str = "pit_cancel_rejected"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    reason: str = "already_in_pit_lane"


@dataclass
class PositionUpdateEvent(Event):
    """Snapshot periódico com a posição de todos os pilotos."""
    type: str = "position_update"
    lap: int = 0
    positions: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class TickEvent(Event):
    """Tick de simulação (frequência menor que PositionUpdate)."""
    type: str = "tick"
    lap: int = 0
    tick_in_lap: int = 0
    positions: List[Dict[str, Any]] = field(default_factory=list)
    weather: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CollisionEvent(Event):
    """Emitido UMA vez quando dois carros entram em contato físico.

    Só avisa: a física do choque já é resolvida pelo PyBullet e nenhuma
    consequência (penalidade, dano, safety car) é aplicada por este evento.

    ``driver_a_id`` / ``driver_b_id`` vêm em ordem alfabética de ``driver_id``
    (par não-ordenado: o evento não diz quem "bateu em quem").
    ``lap`` é a maior volta entre os dois pilotos. ``impact_force_n`` é a soma
    das forças normais dos pontos de contato no passo em que o contato começou
    e ``penetration_m`` é a maior penetração entre os dois chassis nesse passo.

    Atenção: a força é lida no último sub-passo de física do tick, então numa
    batida moderada ela pode vir 0,0 mesmo com o choque tendo acontecido (o
    impulso foi aplicado num sub-passo anterior). Para "quão forte foi" prefira
    ``penetration_m`` junto com ``impact_force_n``, não só a força.
    """
    type: str = "collision"
    lap: int = 0
    driver_a_id: str = ""
    driver_a_name: str = ""
    driver_b_id: str = ""
    driver_b_name: str = ""
    position_xy: List[float] = field(default_factory=list)
    impact_force_n: float = 0.0
    penetration_m: float = 0.0


@dataclass
class OffTrackEvent(Event):
    """Emitido quando um carro sai da pista."""
    type: str = "off_track"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    side: str = ""
    distance_m: float = 0.0
    speed_mps: float = 0.0
    severity: str = ""


@dataclass
class OnTrackEvent(Event):
    """Emitido quando um carro retorna à pista."""
    type: str = "on_track"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    duration_s: float = 0.0


@dataclass
class AiCommandEvent(Event):
    """Comando do engenheiro de IA aplicado ao piloto.

    Publicado quando um comando novo (push, conserve, defend, overtake, careful, pace, neutral)
    entra em vigor. O HUD mostra o comando e o motivo.
    """
    type: str = "ai_command"
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    command: str = ""
    value: float = 0.0
    reason: str = ""
    issued_by: str = "ai"


@dataclass
class AiSuggestionEvent(Event):
    """Sugestão textual do engenheiro de IA (o que ele 'diz').

    Publicado periodicamente ou quando há mudança de estratégia. O HUD mostra
    a mensagem, a urgência (baixa/media/alta) e um comando sugerido opcional.
    """
    type: str = "ai_suggestion"
    race_id: str = ""
    driver_id: str = ""
    driver_name: str = ""
    lap: int = 0
    aviso: str = ""
    urgencia: str = "media"  # "baixa" | "media" | "alta"
    previsao: Optional[Dict[str, Any]] = None
    comando: Optional[Dict[str, Any]] = None
    fallback: bool = False


# ==================== EVENTOS DE CICLO DE VIDA DO AI ENGINEER ====================

@dataclass
class AiStartedEvent(Event):
    """Emitido quando o AiEngineer é iniciado para uma corrida."""
    type: str = "ai_started"
    race_id: str = ""
    total_laps: int = 0
    user_driver_id: Optional[str] = None
    num_drivers: int = 0
    decision_interval_s: float = 5.0


@dataclass
class AiMonitoringEvent(Event):
    """Emitido periodicamente como heartbeat do AiEngineer.

    Indica que a IA está ativa e monitorando, mesmo sem recomendações novas.
    O frontend pode usar isso para mostrar status "IA analisando..." em vez de "sem dados".
    """
    type: str = "ai_monitoring"
    race_id: str = ""
    status: str = "running"  # "waiting_for_race_start" | "running" | "paused"
    sim_ts: float = 0.0
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AiStoppedEvent(Event):
    """Emitido quando o AiEngineer é encerrado (fim da corrida, erro, etc.)."""
    type: str = "ai_stopped"
    race_id: str = ""
    reason: str = "race_ended"  # "race_ended" | "error" | "cancelled"
    stats: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AiErrorEvent(Event):
    """Emitido quando ocorre erro no processamento do AiEngineer.

    Não indica falha fatal - o engenheiro continua rodando.
    O frontend pode exibir avisos ou métricas de saúde.
    """
    type: str = "ai_error"
    race_id: str = ""
    error: str = ""
    error_type: str = ""
    cycle: int = 0
    driver_id: Optional[str] = None
