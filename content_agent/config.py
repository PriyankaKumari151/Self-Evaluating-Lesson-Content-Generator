import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


# Project root directory
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load environment variables from the project root
load_dotenv(PROJECT_ROOT / ".env")


def resolve_path(value: str) -> Path:
    """
    Resolve a path relative to the project root
    unless an absolute path is provided.
    """
    path = Path(value)

    if path.is_absolute():
        return path

    return PROJECT_ROOT / path


@dataclass(frozen=True)
class Settings:
    """
    Centralized application configuration.

    All application modules should read their configuration
    from this object instead of accessing environment
    variables independently.
    """

    # LLM settings
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_model: str = os.getenv("LLM_MODEL", "gpt-4o-mini")

    # Database settings
    database_path: Path = resolve_path(
        os.getenv(
            "DATABASE_PATH",
            "data/lesson_generator.db"
        )
    )

    # Workflow settings
    max_retries: int = int(
        os.getenv("MAX_RETRIES", "2")
    )

    # Model generation settings
    generation_temperature: float = float(
        os.getenv("GENERATION_TEMPERATURE", "0.3")
    )

    evaluation_temperature: float = float(
        os.getenv("EVALUATION_TEMPERATURE", "0.0")
    )

        # Structured output configuration
    structured_output_method: str = os.getenv(
        "LLM_STRUCTURED_OUTPUT_METHOD",
        "json_schema"
    )

    # API connection settings
    llm_timeout_seconds: int = int(
        os.getenv("LLM_TIMEOUT_SECONDS", "60")
    )

    llm_max_api_retries: int = int(
        os.getenv("LLM_MAX_API_RETRIES", "2")
    )

    def validate_llm_config(self) -> None:
        """
        Validate LLM configuration before making API calls.
        """

        if not self.llm_api_key or self.llm_api_key == "your_api_key_here":
            raise ValueError(
                "LLM_API_KEY is missing. "
                "Please configure it in your .env file."
            )

        if not self.llm_model:
            raise ValueError("LLM_MODEL is not configured.")

    def validate_workflow_config(self) -> None:
        """
        Validate workflow configuration.
        """

        if self.max_retries < 0:
            raise ValueError(
                "MAX_RETRIES cannot be negative."
            )

        if not 0 <= self.generation_temperature <= 2:
            raise ValueError(
                "GENERATION_TEMPERATURE must be between 0 and 2."
            )

        if not 0 <= self.evaluation_temperature <= 2:
            raise ValueError(
                "EVALUATION_TEMPERATURE must be between 0 and 2."
            )
    def validate_llm_runtime_config(self) -> None:
        """
        Validates LLM-specific runtime configuration.
        """

        self.validate_llm_config()

        if self.llm_timeout_seconds <= 0:
            raise ValueError(
                "LLM_TIMEOUT_SECONDS must be positive."
            )

        if self.llm_max_api_retries < 0:
            raise ValueError(
                "LLM_MAX_API_RETRIES cannot be negative."
            )

        allowed_methods = {
            "json_schema",
            "function_calling",
            "json_mode"
        }

        if self.structured_output_method not in allowed_methods:
            raise ValueError(
                f"Unsupported structured output method: "
                f"{self.structured_output_method}"
            )


# Single application-wide settings instance
settings = Settings()