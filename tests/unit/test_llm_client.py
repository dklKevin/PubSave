"""Unit tests for LLMClient protocol and OpenAI implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.llm_client import LLMClient
from src.llm.openai_llm import OpenAILLM


class TestLLMClientProtocol:
    def test_openai_llm_satisfies_protocol(self):
        """OpenAILLM must be a valid LLMClient."""
        llm = OpenAILLM(api_key="test-key")
        assert isinstance(llm, LLMClient)


class TestOpenAILLM:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        message = MagicMock()
        message.content = "CRISPR uses lipid nanoparticles [PMID:12345678]."
        choice = MagicMock()
        choice.message = message
        response = MagicMock()
        response.choices = [choice]
        client.chat.completions.create = AsyncMock(return_value=response)
        return client

    async def test_generate_returns_string(self, mock_client):
        with patch("src.llm.openai_llm.AsyncOpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key")

        result = await llm.generate(system="You are helpful.", user="What is CRISPR?")

        assert isinstance(result, str)
        assert len(result) > 0

    async def test_generate_passes_system_and_user_messages(self, mock_client):
        with patch("src.llm.openai_llm.AsyncOpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key")

        await llm.generate(system="Answer concisely.", user="What is CRISPR?")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"
        messages = call_kwargs["messages"]
        assert len(messages) == 2
        assert messages[0] == {"role": "system", "content": "Answer concisely."}
        assert messages[1] == {"role": "user", "content": "What is CRISPR?"}

    async def test_generate_uses_custom_model(self, mock_client):
        with patch("src.llm.openai_llm.AsyncOpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key", model="gpt-4o")

        await llm.generate(system="sys", user="usr")

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o"

    async def test_generate_propagates_openai_error(self, mock_client):
        mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API error"))
        with patch("src.llm.openai_llm.AsyncOpenAI", return_value=mock_client):
            llm = OpenAILLM(api_key="test-key")

        with pytest.raises(Exception, match="API error"):
            await llm.generate(system="sys", user="usr")
