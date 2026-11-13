"""Modelos Pydantic usados pelos endpoints da api."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class RaceSetupRequest(BaseModel):
    """Payload enviado pelo front para configurar/criar uma corrida.

    ``track`` e ``year`` seguem a mesma semântica de ``config.load_track``:
    omitidos -> usa o preset local de Interlagos.
    """

    laps: int = Field(default=10, ge=1, le=200)
    track: Optional[str] = None
    year: Optional[int] = None


class RaceSetupResponse(BaseModel):
    """Resposta devolvida após criar a corrida.

    O front usa ``race_id`` para abrir a conexão WebSocket em
    ``/ws/races/{race_id}``.
    """

    race_id: str
    track_name: str
    num_laps: int
