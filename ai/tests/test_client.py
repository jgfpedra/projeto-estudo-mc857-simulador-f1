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
