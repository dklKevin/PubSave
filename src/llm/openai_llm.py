"""OpenAI LLM client — gpt-4o-mini by default.

Pure transport layer: takes system and user strings, sends them to the model,
returns the response. Prompt engineering belongs in the service layer.
"""

import logging

from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAILLM:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self._model = model

    async def generate(self, system: str, user: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content
