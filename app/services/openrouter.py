from dataclasses import dataclass

from app.config.settings import settings


@dataclass(frozen=True)
class OpenRouterConfig:
    """Configuration for future OpenRouter LLM integration."""

    api_key: str
    base_url: str
    default_model: str

    @classmethod
    def from_settings(cls) -> "OpenRouterConfig":
        return cls(
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            default_model=settings.openrouter_default_model,
        )

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)


class OpenRouterClient:
    """
    Placeholder client for OpenRouter API integration.

    Not implemented — extend when LLM-based qualification or message
    generation is added.
    """

    def __init__(self, config: OpenRouterConfig | None = None) -> None:
        self.config = config or OpenRouterConfig.from_settings()

    async def chat_completion(self, messages: list[dict[str, str]], *, model: str | None = None) -> str:
        raise NotImplementedError(
            "OpenRouter integration is not implemented yet. "
            "Configure OPENROUTER_API_KEY and implement chat_completion()."
        )
