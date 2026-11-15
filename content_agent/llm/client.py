from typing import TypeVar

from pydantic import BaseModel
from langchain_openai import ChatOpenAI

from content_agent.config import settings


SchemaType = TypeVar(
    "SchemaType",
    bound=BaseModel
)


def create_chat_model(
    temperature: float | None = None
) -> ChatOpenAI:
    """
    Creates a configured LangChain ChatOpenAI client.

    Supports:
    - Official OpenAI API
    - Compatible Chat Completions endpoints
    - Configurable model and base URL
    """

    settings.validate_llm_runtime_config()

    model_kwargs = {

        "model": settings.llm_model,

        "api_key": settings.llm_api_key,

        "temperature": (
            temperature
            if temperature is not None
            else settings.generation_temperature
        ),

        "timeout": settings.llm_timeout_seconds,

        "max_retries": settings.llm_max_api_retries,

        # Use Chat Completions for predictable
        # OpenAI-compatible endpoint behaviour.
        "use_responses_api": False,
        "max_tokens": 2096
    }

    # Only supply base_url when explicitly configured.
    if settings.llm_base_url.strip():

        model_kwargs["base_url"] = settings.llm_base_url.strip()

    return ChatOpenAI(**model_kwargs)


def create_structured_model(
    schema: type[SchemaType],
    temperature: float | None = None
):
    """
    Creates a structured-output LLM.

    The returned model produces responses conforming
    to the supplied Pydantic schema.
    """

    model = create_chat_model(
        temperature=temperature
    )

    return model.with_structured_output(
        schema,
        method=settings.structured_output_method,
        strict=False
    )