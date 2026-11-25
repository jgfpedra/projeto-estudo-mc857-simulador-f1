from redis_listener import _should_stay_silent


def test_evento_real_com_comando_novo_fala():
    # Rádio pediu ataque e o comando mudou: não pode ser engolido.
    assert not _should_stay_silent(
        True, "push", "Ataque agora", "defend", "Defenda a posição")


def test_evento_real_com_texto_novo_fala():
    assert not _should_stay_silent(
        True, "defend", "Outra frase", "defend", "Defenda a posição")


def test_duplicata_exata_fica_silenciosa_mesmo_com_evento():
    # Mesmo comando e mesmo texto: repetir não muda o carro nem o HUD.
    assert _should_stay_silent(
        True, "defend", "Defenda a posição", "defend", "Defenda a posição")


def test_periodico_com_mesmo_comando_fica_silencioso():
    assert _should_stay_silent(
        False, "defend", "Outra mensagem", "defend", "Outra anterior")


def test_periodico_com_texto_repetido_fica_silencioso():
    assert _should_stay_silent(
        False, "push", "Mesma frase", "defend", "Mesma frase")


def test_periodico_com_comando_novo_fala():
    assert not _should_stay_silent(
        False, "push", "Ataque agora", "defend", "Defenda a posição")


def test_primeira_mensagem_fala():
    assert not _should_stay_silent(False, "neutral", "Mantenha o ritmo", None, None)
