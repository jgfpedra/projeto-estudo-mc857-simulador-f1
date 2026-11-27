from unittest.mock import patch, MagicMock
from client import call_model


@patch("client.requests.post")
def test_call_model_sucesso(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"aviso": "ok"}'}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = call_model("prompt de teste")
    assert result["ok"] is True
    assert "aviso" in result["response"]


@patch("client.requests.post")
def test_call_model_timeout(mock_post):
    import requests
    mock_post.side_effect = requests.exceptions.Timeout()

    result = call_model("prompt de teste")
    assert result["ok"] is False
    assert "timeout" in result["error"]


@patch("client.requests.post")
def test_call_model_permite_opcoes_e_timeout_especificos(mock_post):
    mock_response = MagicMock()
    mock_response.json.return_value = {"response": '{"resumo_geral": "ok"}'}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = call_model(
        "prompt de debrief",
        options={"num_predict": 900},
        timeout=60,
    )

    assert result["ok"] is True
    request = mock_post.call_args
    assert request.kwargs["timeout"] == 60
    assert request.kwargs["json"]["options"]["num_predict"] == 900
    assert request.kwargs["json"]["options"]["keep_alive"] == "30m"
