import json

import debrief


RACE_META = {
    "race_id": "race_test",
    "season": 2024,
    "num_laps": 3,
    "num_drivers": 2,
    "track": {"name": "Interlagos"},
    "drivers": [
        {"driver_id": "drv_01", "name": "Piloto Um"},
        {"driver_id": "drv_02", "name": "Piloto Dois"},
    ],
}
CLASSIFICATION = [
    {"position": 1, "driver_id": "drv_01", "laps_completed": 3, "total_time_s": 91.2, "pit_stops": 1},
    {"position": 2, "driver_id": "drv_02", "laps_completed": 3, "total_time_s": 93.4, "pit_stops": 0},
]
EVENTS = [
    {"type": "race_start", "sim_ts": 0.0, "lap": 0},
    {"type": "pit_stop", "sim_ts": 30.0, "lap": 1, "driver_id": "drv_01", "new_compound":"MEDIUM"},
    {"type": "collision", "sim_ts": 62.0, "lap": 2, "driver_a_id": "drv_01", "driver_b_id": "drv_02"},
    {"type": "ai_suggestion", "sim_ts": 65.0, "lap": 2, "driver_id": "drv_01", "aviso": "Defenda"},
]
AI_COMMANDS = [
    {"type": "ai_command", "sim_ts": 64.0, "lap": 2, "driver_id": "drv_01", "command": "defend", "reason": "Rival próximo"},
]
VALID_OUTPUT = {
    "resumo_geral": "Piloto Um venceu em Interlagos.",
    "largada": "A largada ocorreu sem contatos registrados.",
    "estrategia_pneus": "Piloto Um fez uma parada para MEDIUM.",
    "combustivel": "Não houve dados suficientes para uma análise detalhada.",
    "momentos_chave": [
        {"volta": 2, "evento": "Contato entre os dois pilotos", "impacto": "alto"},
    ],
    "contatos_incidentes": "Houve um contato na segunda volta.",
    "performance_pilotos": {"vencedor": "Piloto Um manteve a liderança."},
    "decisoes_engenheiro": "O comando defend foi coerente com o rival próximo.",
    "licoes_aprendidas": "Evitar contato nas disputas seguintes.",
}


def test_prompt_usa_dados_reais_da_corrida():
    stats = debrief.build_debrief_stats(EVENTS, AI_COMMANDS, total_time_s=91.2)
    prompt = debrief.generate_debrief_prompt(
        RACE_META, CLASSIFICATION, EVENTS, AI_COMMANDS, stats
    )

    assert "Interlagos" in prompt
    assert "Piloto Um" not in prompt or "drv_01" in prompt
    assert '"new_compound":"MEDIUM"' in prompt
    assert '"colisoes":1' in prompt
    assert '"pit_stops":1' in prompt
    assert "Rival próximo" in prompt
    assert '"circuit": "Autódromo"' not in prompt


def test_prompt_limita_eventos_e_preserva_largada_e_desfecho():
    events = [
        {"type": "race_start", "sim_ts": 0, "lap": 0},
        *[
            {"type": "race_control", "sim_ts": index + 1, "message": f"controle {index}"}
            for index in range(30)
        ],
        {"type": "race_end", "sim_ts": 31, "lap": 3},
    ]
    prompt = debrief.generate_debrief_prompt(
        RACE_META, CLASSIFICATION, events, AI_COMMANDS, {}
    )

    assert prompt.count('"type":') == 16
    assert '"type":"race_start"' in prompt
    assert '"type":"race_end"' in prompt
    assert '"message":"controle 0"' not in prompt
    assert '"message":"controle 29"' in prompt
    assert "eventos omitidos" in prompt


def test_validate_debrief_output_aceita_contrato_e_normaliza_impacto():
    raw = json.dumps({
        **VALID_OUTPUT,
        "momentos_chave": [{"volta": "2", "evento": "Contato", "impacto": "alta"}],
    })
    result = debrief.validate_debrief_output(raw)

    assert result is not None
    assert result["momentos_chave"] == [
        {"volta": 2, "evento": "Contato", "impacto": "alto"}
    ]
    assert result["licoes_aprendidas"] == VALID_OUTPUT["licoes_aprendidas"]


def test_validate_debrief_output_rejeita_schema_de_sugestao():
    suggestion = {"aviso": "ok", "previsao": {}, "urgencia": "baixa"}
    assert debrief.validate_debrief_output(json.dumps(suggestion)) is None
    assert debrief.validate_debrief_output("json inválido") is None


def test_generate_debrief_usa_opcoes_ampliadas_e_retorna_contrato(monkeypatch):
    captured = {}

    def fake_call_model(prompt, options=None, timeout=None):
        captured["prompt"] = prompt
        captured["options"] = options
        captured["timeout"] = timeout
        return {"ok": True, "response": json.dumps(VALID_OUTPUT), "elapsed": 1.0}

    monkeypatch.setattr(debrief, "call_model", fake_call_model)
    result = debrief.generate_debrief(
        "race_test", RACE_META, CLASSIFICATION, EVENTS, AI_COMMANDS,
        {"total_time_s": 91.2},
    )

    assert captured["options"] == {
        "num_predict": 512,
        "num_ctx": 3072,
        "temperature": 0.1,
    }
    assert captured["timeout"] == debrief.DEBRIEF_OLLAMA_TIMEOUT
    assert '"new_compound":"MEDIUM"' in captured["prompt"]
    assert result["fallback"] is False
    assert result["race_id"] == "race_test"
    assert result["resumo_geral"] == VALID_OUTPUT["resumo_geral"]
    assert result["gerado_em"] > 0


def test_fallback_contem_resultado_e_incidentes_reais(monkeypatch):
    monkeypatch.setattr(
        debrief,
        "call_model",
        lambda *_args, **_kwargs: {"ok": False, "error": "timeout", "elapsed": 30.0},
    )
    result = debrief.generate_debrief(
        "race_test", RACE_META, CLASSIFICATION, EVENTS, AI_COMMANDS, {}
    )

    assert result["fallback"] is True
    assert result["fallback_motivo"] == "timeout"
    assert "Piloto Um venceu" in result["resumo_geral"]
    assert result["performance_pilotos"]["vencedor"] == "Piloto Um"
    assert result["momentos_chave"]
    assert "1 colisão" in result["contatos_incidentes"]


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def setex(self, key, ttl, value):
        self.values[key] = value
        self.ttls[key] = ttl

    def get(self, key):
        return self.values.get(key)


def test_generate_and_save_debrief_persiste_json_no_namespace_da_corrida(monkeypatch):
    monkeypatch.setattr(
        debrief,
        "call_model",
        lambda *_args, **_kwargs: {
            "ok": True,
            "response": json.dumps(VALID_OUTPUT),
            "elapsed": 1.0,
        },
    )
    client = FakeRedis()
    result = debrief.generate_and_save_debrief(
        race_id="race_test",
        race_meta=RACE_META,
        classification=CLASSIFICATION,
        events=EVENTS,
        ai_commands=AI_COMMANDS,
        stats={"total_time_s": 91.2},
        redis_client=client,
    )

    assert result["fallback"] is False
    assert client.ttls["race:race_test:debrief"] == debrief.DEBRIEF_TTL_SECONDS
    saved = debrief.get_debrief(client, "race_test")
    assert saved is not None
    assert saved["race_id"] == "race_test"
    assert saved["estrategia_pneus"] == VALID_OUTPUT["estrategia_pneus"]
