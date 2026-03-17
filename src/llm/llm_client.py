"""LLM client protocol — one method, any provider."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    async def generate(self, system: str, user: str) -> str: ...
