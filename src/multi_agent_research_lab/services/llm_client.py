"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import logging
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError, APITimeoutError, InternalServerError, OpenAI, RateLimitError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.errors import AgentExecutionError, LabError

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client supporting Groq (via OpenAI-compatible API) and OpenAI."""

    def __init__(
        self,
        settings: Settings | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.client: OpenAI | None = None
        self.provider: str = "none"

        # Determine credentials: prioritize Groq, then OpenAI
        resolved_key = (api_key or "").strip() or None
        resolved_base_url = (base_url or "").strip() or None
        resolved_model = (model or "").strip() or None

        groq_key = (self.settings.groq_api_key or "").strip() or None
        openai_key = (self.settings.openai_api_key or "").strip() or None

        if resolved_key:
            self.provider = "custom"
        elif groq_key:
            self.provider = "groq"
            resolved_key = groq_key
            resolved_base_url = resolved_base_url or self.settings.groq_base_url
            resolved_model = resolved_model or self.settings.groq_model
        elif openai_key:
            self.provider = "openai"
            resolved_key = openai_key
            resolved_model = resolved_model or self.settings.openai_model

        self.api_key = resolved_key
        self.base_url = resolved_base_url
        self.default_model = (
            resolved_model
            or (self.settings.groq_model if self.provider == "groq" else self.settings.openai_model)
        )
        self.timeout_seconds = self.settings.timeout_seconds

        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=self.timeout_seconds,
            )

    def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str | None = None,
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> LLMResponse:
        """Return a model completion with automatic retry on rate limits and network errors."""
        if not self.client:
            raise LabError(
                "Chưa cấu hình API Key. Vui lòng điền GROQ_API_KEY (khuyên dùng) hoặc "
                "OPENAI_API_KEY vào file .env."
            )

        target_model = model or self.default_model

        @retry(
            retry=retry_if_exception_type(
                (RateLimitError, APIConnectionError, APITimeoutError, InternalServerError)
            ),
            wait=wait_exponential(multiplier=1, min=2, max=10),
            stop=stop_after_attempt(3),
            reraise=True,
        )
        def _call_api() -> LLMResponse:
            try:
                response = self.client.chat.completions.create(  # type: ignore[union-attr]
                    model=target_model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=temperature,
                    **kwargs,
                )
            except Exception as exc:
                logger.error(f"LLM API call failed ({target_model}): {exc}")
                raise AgentExecutionError(f"LLM call failed: {exc}") from exc

            content = response.choices[0].message.content or ""
            input_tokens = response.usage.prompt_tokens if response.usage else None
            output_tokens = response.usage.completion_tokens if response.usage else None

            # For Groq free tier, cost is ~0.0 USD
            cost_usd = 0.0 if self.provider == "groq" else None

            return LLMResponse(
                content=content,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
            )

        return _call_api()
