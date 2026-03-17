"""LLM client protocol — one method, any provider."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    @property
    def model(self) -> str: ...

    async def generate(self, system: str, user: str) -> str: ...
