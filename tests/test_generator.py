import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.anyio
async def test_generate_includes_example_sentence():
    from flux_lang.generator import GeminiGenerator

    mock_text = json.dumps([{
        "source": "coffee",
        "target": "caffè",
        "phonetic": "CAFF-eh",
        "example_sentence": "Vorrei un caffè, per favore."
    }])

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": mock_text}]}}]
    }

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        generator = GeminiGenerator(api_keys=["fake-key"])
        result = await generator.generate("en", "it", "food", count=1)

        assert len(result) == 1
        assert result[0]["example_sentence"] == "Vorrei un caffè, per favore."
