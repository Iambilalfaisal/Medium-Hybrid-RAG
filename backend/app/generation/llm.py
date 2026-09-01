from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI

from app.config import settings


def _to_gemini_contents(messages: list[dict[str, str]]) -> tuple[str | None, list[genai_types.Content]]:
    """Gemini has no 'system' role in `contents` (system prompts go through a
    separate config field) and calls the assistant turn 'model', not 'assistant'."""
    system_parts: list[str] = []
    contents: list[genai_types.Content] = []
    for msg in messages:
        if msg["role"] == "system":
            system_parts.append(msg["content"])
            continue
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(genai_types.Content(role=role, parts=[genai_types.Part(text=msg["content"])]))
    system = "\n".join(system_parts) if system_parts else None
    return system, contents


class GeminiClient:
    name = "gemini"

    def __init__(self):
        self._client = genai.Client(api_key=settings.GOOGLE_API_KEY)

    async def complete(self, messages: list[dict[str, str]]) -> str:
        system, contents = _to_gemini_contents(messages)
        config = genai_types.GenerateContentConfig(system_instruction=system) if system else None
        response = await self._client.aio.models.generate_content(
            model=settings.GEMINI_CHAT_MODEL, contents=contents, config=config
        )
        return response.text or ""

    async def start_stream(self, messages: list[dict[str, str]]):
        system, contents = _to_gemini_contents(messages)
        config = genai_types.GenerateContentConfig(system_instruction=system) if system else None
        raw_stream = await self._client.aio.models.generate_content_stream(
            model=settings.GEMINI_CHAT_MODEL, contents=contents, config=config
        )
        return raw_stream.__aiter__(), (lambda chunk: chunk.text)


class OpenRouterClient:
    name = "openrouter"

    def __init__(self):
        self._client = AsyncOpenAI(api_key=settings.OPENROUTER_API_KEY, base_url="https://openrouter.ai/api/v1")

    async def complete(self, messages: list[dict[str, str]]) -> str:
        response = await self._client.chat.completions.create(
            model=settings.OPENROUTER_FALLBACK_MODEL, messages=messages
        )
        return response.choices[0].message.content or ""

    async def start_stream(self, messages: list[dict[str, str]]):
        raw_stream = await self._client.chat.completions.create(
            model=settings.OPENROUTER_FALLBACK_MODEL, messages=messages, stream=True
        )

        def extract(chunk):
            return chunk.choices[0].delta.content if chunk.choices else None

        return raw_stream.__aiter__(), extract
