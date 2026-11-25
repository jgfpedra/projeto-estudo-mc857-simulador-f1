"""Testes do CoachController: comandos de alto nível e eventos de pista."""

from __future__ import annotations

from dataclasses import dataclass

from backend.engine.coach_controller import CommandBus, CoachController
from backend.engine.controllers import CarController, CarInput, EnvironmentState
from backend.engine.events import AiCommandEvent, OffTrackEvent, OnTrackEvent


class RecordingPublisher:
    def __init__(self) -> None:
        self.events = []

    def publish(self, event) -> None:
        self.events.append(event)


@dataclass
class FakeDriver:
    driver_id: str = "drv_01"
    name: str = "Piloto 1"
    lap: int = 0
    position_x: float = 0.0
    position_y: float = 0.0
    velocity_mps: float = 40.0
    heading_rad: float = 0.0


class FakeBase(CarController):
    """Controlador determinístico com projeto (s, lat) controlável."""

    def __init__(self) -> None:
        self._half_width = 10.0
        self.signed_lat = 0.0
        self.throttle = 0.5

    def _project(self, _driver_id, _x, _y):
        return 100.0, self.signed_lat

    def compute_input(self, _env, _driver_state):
        return CarInput(
            steering_yaw_rad=0.0,
            brake=0.0,
            throttle=self.throttle,
            grip_override=None,
        )

    def reset(self) -> None:
        pass


def make_env(sim_ts: float) -> EnvironmentState:
    return EnvironmentState(
        sim_ts=sim_ts,
        lap=0,
        weather=None,
        track=None,
        all_driver_states={},
    )


def test_command_changes_throttle_and_publishes_event():
    base = FakeBase()
    bus = CommandBus()
    publisher = RecordingPublisher()
    coach = CoachController(base, "drv_01", publisher=publisher, bus=bus)
    driver = FakeDriver()

    bus.push("drv_01", "push", reason="atacar", issued_by="llm")
    out = coach.compute_input(make_env(1.0), driver)
    assert out.throttle == 0.55  # 0.5 * 1.10
    assert [e.type for e in publisher.events] == ["ai_command"]
    assert isinstance(publisher.events[0], AiCommandEvent)
    assert publisher.events[0].command == "push"

    base.throttle = 0.5
    bus.push("drv_01", "conserve", reason="pneu", issued_by="llm")
    out = coach.compute_input(make_env(1.1), driver)
    assert out.throttle == 0.45
    assert publisher.events[-1].command == "conserve"


def test_neutral_command_clears_and_is_published():
    base = FakeBase()
    bus = CommandBus()
    publisher = RecordingPublisher()
    coach = CoachController(base, "drv_01", publisher=publisher, bus=bus)
    driver = FakeDriver()

    bus.push("drv_01", "push")
    coach.compute_input(make_env(1.0), driver)
    bus.push("drv_01", "neutral", reason="ok")
    out = coach.compute_input(make_env(1.1), driver)

    assert out.throttle == 0.5
    assert publisher.events[-1].command == "neutral"


def test_off_and_on_track_transitions_publish_events():
    base = FakeBase()
    bus = CommandBus()
    publisher = RecordingPublisher()
    coach = CoachController(base, "drv_01", publisher=publisher, bus=bus)
    driver = FakeDriver()

    base.signed_lat = 15.0  # 5 m além da borda
    coach.compute_input(make_env(2.0), driver)
    assert isinstance(publisher.events[-1], OffTrackEvent)
    assert publisher.events[-1].side == "esquerda"
    assert publisher.events[-1].distance_m == 5.0
    assert publisher.events[-1].severity == "grave"

    # Repetir fora da pista não duplica o evento.
    count = len(publisher.events)
    coach.compute_input(make_env(2.1), driver)
    assert len(publisher.events) == count

    base.signed_lat = 0.0
    coach.compute_input(make_env(4.0), driver)
    assert isinstance(publisher.events[-1], OnTrackEvent)
    assert publisher.events[-1].duration_s == 2.0
