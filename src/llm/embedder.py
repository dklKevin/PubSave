"""Embedder protocol — one method, any provider."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
