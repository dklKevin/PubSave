"""Unit tests for Embedder protocol and OpenAI implementation."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.llm.embedder import Embedder
from src.llm.openai_embedder import OpenAIEmbedder

EMBEDDING_DIM = 1536


class TestEmbedderProtocol:
    def test_openai_embedder_satisfies_protocol(self):
        """OpenAIEmbedder must be a valid Embedder."""
        embedder = OpenAIEmbedder(api_key="test-key")
        assert isinstance(embedder, Embedder)


class TestOpenAIEmbedder:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock()
        embedding_obj = MagicMock()
        embedding_obj.embedding = [0.1] * EMBEDDING_DIM
        response = MagicMock()
        response.data = [embedding_obj]
        client.embeddings.create = AsyncMock(return_value=response)
        return client

    async def test_embed_returns_correct_shape(self, mock_client):
        with patch("src.llm.openai_embedder.AsyncOpenAI", return_value=mock_client):
            embedder = OpenAIEmbedder(api_key="test-key")

        result = await embedder.embed("test text")

        assert isinstance(result, list)
        assert len(result) == EMBEDDING_DIM
        assert all(isinstance(v, float) for v in result)

    async def test_embed_calls_openai_with_correct_params(self, mock_client):
        with patch("src.llm.openai_embedder.AsyncOpenAI", return_value=mock_client):
            embedder = OpenAIEmbedder(api_key="test-key")

        await embedder.embed("gene therapy")

        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input="gene therapy",
        )

    async def test_embed_uses_custom_model(self, mock_client):
        with patch("src.llm.openai_embedder.AsyncOpenAI", return_value=mock_client):
            embedder = OpenAIEmbedder(api_key="test-key", model="text-embedding-3-large")

        await embedder.embed("test")

        mock_client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-large",
            input="test",
        )

    async def test_embed_propagates_openai_error(self, mock_client):
        mock_client.embeddings.create = AsyncMock(side_effect=Exception("API rate limit"))
        with patch("src.llm.openai_embedder.AsyncOpenAI", return_value=mock_client):
            embedder = OpenAIEmbedder(api_key="test-key")

        with pytest.raises(Exception, match="API rate limit"):
            await embedder.embed("test")

    async def test_embed_batch_returns_multiple_embeddings(self):
        client = MagicMock()
        items = []
        for i in range(3):
            item = MagicMock()
            item.embedding = [float(i)] * EMBEDDING_DIM
            items.append(item)
        response = MagicMock()
        response.data = items
        client.embeddings.create = AsyncMock(return_value=response)

        with patch("src.llm.openai_embedder.AsyncOpenAI", return_value=client):
            embedder = OpenAIEmbedder(api_key="test-key")

        texts = ["text one", "text two", "text three"]
        result = await embedder.embed_batch(texts)

        assert len(result) == 3
        assert all(len(emb) == EMBEDDING_DIM for emb in result)
        client.embeddings.create.assert_called_once_with(
            model="text-embedding-3-small",
            input=texts,
        )
