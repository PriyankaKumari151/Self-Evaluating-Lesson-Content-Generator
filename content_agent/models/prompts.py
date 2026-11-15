from datetime import datetime, timezone

from pydantic import Field

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import (
    PromptType,
    PromptStatus
)


class PromptVersion(AppBaseModel):
    """
    Represents one immutable version of a prompt.
    """

    id: int | None = None

    prompt_type: PromptType

    version: NonEmptyStr

    prompt_content: NonEmptyStr

    change_summary: NonEmptyStr

    status: PromptStatus = PromptStatus.DRAFT

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )