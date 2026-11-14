"""Modelos Pydantic usados pelos endpoints da api."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RaceSetupRequest(BaseModel):
    """Payload enviado pelo front para configurar/criar uma corrida.

    Interlagos 2023 e Monza 2024 usam traçados locais derivados de telemetria;
    outros anos ou circuitos seguem ``config.load_track``.
    """

    laps: int = Field(default=10, ge=1, le=200)
    num_drivers: int = Field(default=2, ge=1, le=24)
    track: Optional[str] = None
    layout_id: Optional[str] = None
    year: Optional[int] = None
    season: Optional[int] = None


class RaceSetupResponse(BaseModel):
    """Resposta devolvida após criar a corrida.

    O front usa ``race_id`` para abrir a conexão WebSocket em
    ``/ws/races/{race_id}``.
    """

    race_id: str
    track_name: str
    num_laps: int
