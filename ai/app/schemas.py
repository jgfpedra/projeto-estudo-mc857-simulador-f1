import json
import random

# "aviso" pode vir nulo/ausente; `_normalize_aviso` preenche depois. As demais
# chaves são estruturais e uma resposta sem elas é considerada inválida.
REQUIRED_KEYS = {"previsao", "urgencia"}
REQUIRED_PREVISAO_KEYS = {"pit_stop_recomendado", "volta_estimada", "composto_sugerido"}
VALID_URGENCIA = {"baixa", "media", "alta"}
VALID_COMMANDS = {"push", "overtake", "defend", "conserve", "careful", "neutral"}

# O llama3.2 às vezes devolve `"aviso": null` mesmo com o formato pedido. Em vez
# de mostrar "None" no HUD, monta uma frase curta coerente com o comando.
_AVISO_POR_COMANDO = {
    "push": "Ataque agora, temos ritmo para ganhar a posição.",
    "overtake": "Prepare a ultrapassagem na próxima zona de frenagem.",
    "defend": "Segure a linha e defenda a posição.",
    "conserve": "Economize pneu e combustível neste stint.",
    "careful": "Reduza o ritmo e traga o carro inteiro.",
    "neutral": "Mantenha o ritmo, está tudo sob controle.",
}
_INVALID_AVISO = {"", "null", "none", "nenhum aviso", "sem aviso"}

# Respostas do piloto para o engenheiro (quando o conselho não faz sentido)
_DRIVER_RESPONSES_SARCASTIC = [
    "Tá de sacanagem? Eu tô em P1!",
    "Engenheiro, você tá vendo a mesma corrida que eu?",
    "Como é que eu defendo de ninguém à minha frente?",
    "Ultrapassar quem? O ar?",
    "Me dá um rádio que preste, por favor.",
    "Você quer que eu bata no safety car também?",
    "Cara, eu tô LIDERANDO. Lê a tela aí.",
    "Pit stop agora? Com pneu zero? Tá louco?",
    "Push push push... eu não tenho DRS mágico não.",
    "Defender de fantasma é novidade pra mim.",
]
_DRIVER_RESPONSES_POSITIVE = [
    "Recebido, vou pra cima.",
    "Entendido, mantendo o ritmo.",
    "Copiado, economizando aqui.",
    "Fechado, defendendo a posição.",
    "Ok, cautela na curva.",
]


def _normalize_aviso(parsed: dict) -> None:
    """Garante uma mensagem não vazia para o HUD."""
    aviso = parsed.get("aviso")
    if isinstance(aviso, str) and aviso.strip().lower() not in _INVALID_AVISO:
        parsed["aviso"] = aviso.strip()
        return
    comando = parsed.get("comando")
    tipo = ""
    if isinstance(comando, dict):
        tipo = str(comando.get("tipo", "neutral")).strip().lower()
    parsed["aviso"] = _AVISO_POR_COMANDO.get(tipo, _AVISO_POR_COMANDO["neutral"])
    print(f"[schemas] AVISO: 'aviso' ausente/nulo, usando mensagem para '{tipo}'")


def _validate_comando(parsed: dict) -> None:
    """Normaliza o comando de alto nível opcional que o LLM pode sugerir."""
    comando = parsed.get("comando")
    if not isinstance(comando, dict):
        parsed["comando"] = None
        return
    tipo = str(comando.get("tipo", "neutral")).strip().lower()
    if tipo not in VALID_COMMANDS:
        print(f"[schemas] AVISO: comando inesperado '{tipo}', usando 'neutral'")
        tipo = "neutral"
    try:
        valor = float(comando.get("valor", 0.0) or 0.0)
    except (TypeError, ValueError):
        valor = 0.0
    parsed["comando"] = {
        "tipo": tipo,
        "valor": valor,
        "motivo": str(comando.get("motivo", "") or ""),
    }


def _maybe_add_driver_response(parsed: dict, context_mismatch: bool = False) -> None:
    """Adiciona resposta do piloto baseada na coerência do conselho."""
    # 30% chance de resposta do piloto
    if random.random() > 0.3:
        parsed["resposta_piloto"] = None
        return
    
    if context_mismatch:
        # Conselho contradiz a realidade (ex: "defenda" quando está em P1 sozinho)
        parsed["resposta_piloto"] = random.choice(_DRIVER_RESPONSES_SARCASTIC)
    else:
        # Conselho faz sentido
        parsed["resposta_piloto"] = random.choice(_DRIVER_RESPONSES_POSITIVE)


def validate_agent_output(raw_output: str) -> dict | None:
    try:
        parsed = json.loads(raw_output)
    except json.JSONDecodeError:
        print("[schemas] ERRO: resposta não é JSON válido:", raw_output)
        return None

    missing = REQUIRED_KEYS - parsed.keys()
    if missing:
        print(f"[schemas] ERRO: faltando chaves de topo: {missing}")
        return None

    if not isinstance(parsed.get("previsao"), dict):
        print("[schemas] ERRO: 'previsao' deveria ser um objeto")
        return None

    missing_previsao = REQUIRED_PREVISAO_KEYS - parsed["previsao"].keys()
    if missing_previsao:
        print(f"[schemas] AVISO: faltando chaves em 'previsao': {
              missing_previsao} (preenchendo com None)")
        for key in missing_previsao:
            parsed["previsao"][key] = None

    urgencia = str(parsed.get("urgencia", "")).strip().lower()
    if urgencia not in VALID_URGENCIA:
        print(f"[schemas] AVISO: urgencia inesperada '{
              parsed.get('urgencia')}', ajustando para 'media'")
        urgencia = "media"
    parsed["urgencia"] = urgencia

    _validate_comando(parsed)
    _normalize_aviso(parsed)
    
    # Detecta mismatch contexto vs conselho para resposta do piloto
    # (heurística simples: se comando é defend/overtake mas não há rival próximo,
    # ou se aviso menciona posição errada)
    context_mismatch = False
    # A detecção real viria do listener que tem o contexto completo
    # Por enquanto deixamos None, o listener pode sobrescrever
    parsed["resposta_piloto"] = None
    
    return parsed


def fallback_output(motivo: str) -> dict:
    """Usado quando o modelo falha/timeout — o sistema não pode travar esperando o Llama."""
    return {
        "aviso": f"[Engenheiro indisponível: {motivo}]",
        "previsao": {"pit_stop_recomendado": None, "volta_estimada": None, "composto_sugerido": None},
        "urgencia": "baixa",
        "comando": {"tipo": "neutral", "valor": 0.0, "motivo": ""},
        "fallback": True,
        "resposta_piloto": None,
    }
