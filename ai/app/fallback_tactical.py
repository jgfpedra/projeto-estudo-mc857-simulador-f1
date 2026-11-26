"""
Fallback tático determinístico para quando o Ollama falha (timeout, erro, JSON inválido).

Mapeia condições objetivas da corrida para comandos e frases pré-definidas,
garantindo que o rádio continue operacional mesmo sem LLM.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional


@dataclass
class TacticalResponse:
    """Resposta tática pré-definida."""
    aviso: str
    comando_tipo: str
    comando_valor: float
    comando_motivo: str
    urgencia: str
    previsao_pit: bool
    previsao_volta: Optional[int]
    previsao_composto: Optional[str]


@dataclass
class FallbackRule:
    """Regra de fallback com condição e gerador de resposta."""
    condicao: Callable[[dict], bool]
    # Função que recebe o contexto e retorna a resposta
    gerar_resposta: Callable[[dict], TacticalResponse]


def _resposta_ultimas_voltas(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Últimas voltas! Ataque total, não economiza nada!",
        comando_tipo="push",
        comando_valor=0.0,
        comando_motivo="Últimas voltas - tudo ou nada",
        urgencia="alta",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_safety_car(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Safety Car na pista! Reduz ritmo, mantém distância e aquece pneus.",
        comando_tipo="careful",
        comando_valor=0.0,
        comando_motivo="Safety Car ativo - cautela máxima",
        urgencia="media",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_rival_frente(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Rival a menos de 1 segundo! Tenta a ultrapassagem na próxima zona de DRS.",
        comando_tipo="overtake",
        comando_valor=0.0,
        comando_motivo="Rival colado à frente - modo ataque",
        urgencia="alta",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_rival_tras(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Carro colado atrás! Fecha a porta, protege a linha interna.",
        comando_tipo="defend",
        comando_valor=0.0,
        comando_motivo="Rival pressionando - defesa de posição",
        urgencia="media",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_pneus_criticos(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Pneus abaixo de 35%! Cuida deles, evita curvas agressivas e poupa tração.",
        comando_tipo="conserve",
        comando_valor=0.85,
        comando_motivo="Pneus desgastados - preservação obrigatória",
        urgencia="alta",
        previsao_pit=True,
        previsao_volta=ctx.get("volta_atual", 0) + 2 if ctx.get("volta_atual") else None,
        previsao_composto=ctx.get("pneu_composto"),
    )


def _resposta_combustivel_critico(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Combustível crítico! Levanta o pé nas retas, faz lift and coast nas frenagens.",
        comando_tipo="conserve",
        comando_valor=0.80,
        comando_motivo="Combustível baixo - economia forçada",
        urgencia="alta",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_pista_molhada(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Pista molhada! Mais margem nas frenagens, evita zebras e traça limpa.",
        comando_tipo="careful",
        comando_valor=0.0,
        comando_motivo="Condições de chuva - aderência reduzida",
        urgencia="media",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_lider_confortavel(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Líder tranquilo! Mantém o ritmo, não force, gerencia a vantagem.",
        comando_tipo="pace",
        comando_valor=0.95,
        comando_motivo="Líder com vantagem - gestão de ritmo",
        urgencia="baixa",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


def _resposta_janela_pit(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Janela de pit aberta e pneus gastos. Recomendo box na próxima volta para composto fresco.",
        comando_tipo="conserve",
        comando_valor=0.85,
        comando_motivo="Janela de pit + pneus gastos - prepara box",
        urgencia="media",
        previsao_pit=True,
        previsao_volta=ctx.get("volta_atual", 0) + 1 if ctx.get("volta_atual") else None,
        previsao_composto="MEDIUM",
    )


def _resposta_padrao(ctx: dict) -> TacticalResponse:
    return TacticalResponse(
        aviso="Tudo sob controle. Mantém o ritmo atual, sem incidentes.",
        comando_tipo="neutral",
        comando_valor=0.0,
        comando_motivo="Sem situação crítica detectada",
        urgencia="baixa",
        previsao_pit=False,
        previsao_volta=None,
        previsao_composto=None,
    )


# --- Mapeamento de condições para respostas ---

FALLBACK_RULES = [
    # 1. Últimas voltas - prioridade máxima
    FallbackRule(
        condicao=lambda ctx: ctx.get("voltas_restantes", 999) <= 3,
        gerar_resposta=_resposta_ultimas_voltas,
    ),

    # 2. Safety Car / Bandeira Vermelha
    FallbackRule(
        condicao=lambda ctx: ctx.get("safety_car_ativo", False),
        gerar_resposta=_resposta_safety_car,
    ),

    # 3. Rival muito próximo à frente (< 0.9s) - oportunidade de ultrapassagem
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("gap_frente") is not None
            and ctx["gap_frente"] < 0.9
            and ctx.get("posicao", 99) > 1
        ),
        gerar_resposta=_resposta_rival_frente,
    ),

    # 4. Rival pressionando por trás (< 0.9s) - defesa
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("gap_tras") is not None
            and ctx["gap_tras"] < 0.9
        ),
        gerar_resposta=_resposta_rival_tras,
    ),

    # 5. Pneus críticos (< 35%) - conservar
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("pneu_vida_pct") is not None
            and ctx["pneu_vida_pct"] < 35
        ),
        gerar_resposta=_resposta_pneus_criticos,
    ),

    # 6. Combustível crítico (< 40kg) - economizar
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("combustivel_kg") is not None
            and ctx["combustivel_kg"] < 40
        ),
        gerar_resposta=_resposta_combustivel_critico,
    ),

    # 7. Pista molhada / chuva - cautela
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("clima_tipo") in ("rain", "wet", "intermediate", "heavy_rain")
            or ctx.get("aderencia", 1.0) < 0.85
        ),
        gerar_resposta=_resposta_pista_molhada,
    ),

    # 8. Líder confortável (gap > 3s) - gerenciar vantagem
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("posicao") == 1
            and ctx.get("gap_tras") is not None
            and ctx["gap_tras"] > 3.0
        ),
        gerar_resposta=_resposta_lider_confortavel,
    ),

    # 9. Janela de pit aberta + pneus gastos - recomendar pit
    FallbackRule(
        condicao=lambda ctx: (
            ctx.get("janela_pit_aberta", False)
            and ctx.get("pneu_vida_pct") is not None
            and ctx["pneu_vida_pct"] < 50
        ),
        gerar_resposta=_resposta_janela_pit,
    ),

    # 10. Padrão - tudo sob controle
    FallbackRule(
        condicao=lambda ctx: True,  # sempre verdadeiro (último)
        gerar_resposta=_resposta_padrao,
    ),
]


def get_fallback_tactical(race_context: dict) -> dict:
    """
    Retorna a primeira regra que casa com o contexto atual.

    Args:
        race_context: Dicionário com estado da corrida contendo chaves como:
            - volta_atual, total_laps, voltas_restantes
            - posicao, gap_frente, gap_tras
            - pneu_vida_pct, pneu_composto
            - combustivel_kg
            - clima_tipo, aderencia
            - safety_car_ativo
            - janela_pit_aberta

    Returns:
        Dict compatível com schemas.validate_agent_output
    """
    for rule in FALLBACK_RULES:
        try:
            if rule.condicao(race_context):
                resp = rule.gerar_resposta(race_context)
                return {
                    "aviso": resp.aviso,
                    "previsao": {
                        "pit_stop_recomendado": resp.previsao_pit,
                        "volta_estimada": resp.previsao_volta,
                        "composto_sugerido": resp.previsao_composto,
                    },
                    "urgencia": resp.urgencia,
                    "comando": {
                        "tipo": resp.comando_tipo,
                        "valor": resp.comando_valor,
                        "motivo": resp.comando_motivo,
                    },
                    "fallback": True,
                    "fallback_tactical": True,
                }
        except Exception:
            # Se a condição falhar por chave faltando, continua para próxima regra
            continue

    # Nunca deve chegar aqui (última regra sempre casa)
    resp = _resposta_padrao(race_context)
    return {
        "aviso": resp.aviso,
        "previsao": {
            "pit_stop_recomendado": resp.previsao_pit,
            "volta_estimada": resp.previsao_volta,
            "composto_sugerido": resp.previsao_composto,
        },
        "urgencia": resp.urgencia,
        "comando": {
            "tipo": resp.comando_tipo,
            "valor": resp.comando_valor,
            "motivo": resp.comando_motivo,
        },
        "fallback": True,
        "fallback_tactical": True,
    }


def build_race_context_from_state(state, followed_driver_id: str) -> dict:
    """
    Extrai contexto tático do LiveRaceState para o fallback.
    """
    ctx = {}

    # Volta atual e restantes
    ctx["volta_atual"] = getattr(state, "lap", None)
    total_laps = getattr(state, "total_laps", None)
    if ctx["volta_atual"] and total_laps:
        ctx["voltas_restantes"] = total_laps - ctx["volta_atual"]
    ctx["total_laps"] = total_laps

    # Posição e gaps
    ctx["posicao"] = getattr(state, "position", None)
    ctx["gap_frente"] = getattr(state, "gap_ahead", None)
    ctx["gap_tras"] = getattr(state, "gap_behind", None)

    # Pneus
    ctx["pneu_vida_pct"] = getattr(state, "tyre_life_pct", None)
    ctx["pneu_composto"] = getattr(state, "tyre_compound", None)

    # Combustível
    ctx["combustivel_kg"] = getattr(state, "fuel_kg", None)

    # Clima
    ctx["clima_tipo"] = getattr(state, "weather_kind", None)
    ctx["aderencia"] = getattr(state, "grip_factor", None)

    # Safety Car
    ctx["safety_car_ativo"] = getattr(state, "safety_car_active", False)

    # Janela de pit (heurística: 25% a 75% da corrida)
    if ctx["volta_atual"] and total_laps:
        pct = ctx["volta_atual"] / total_laps
        ctx["janela_pit_aberta"] = 0.25 <= pct <= 0.75

    return ctx