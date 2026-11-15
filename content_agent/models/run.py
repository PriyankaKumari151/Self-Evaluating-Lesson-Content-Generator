from datetime import datetime, timezone

from pydantic import Field

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import RunStatus

from content_agent.models.lesson import (
    Lesson,
    LearnerProfile
)


class LessonRequest(AppBaseModel):
    """
    Input received from the user.
    """

    topic: NonEmptyStr

    learner_profile: LearnerProfile = Field(
        default_factory=LearnerProfile
    )

    max_retries: int = Field(default=2, ge=0, le=5)


class RunRecord(AppBaseModel):
    """
    Represents one complete workflow execution.
    """

    id: int | None = None

    topic: NonEmptyStr

    learner_profile: LearnerProfile

    status: RunStatus = RunStatus.IN_PROGRESS

    max_retries: int = Field(default=2, ge=0)

    retry_count: int = Field(default=0, ge=0)

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    completed_at: datetime | None = None


class LessonVersionRecord(AppBaseModel):
    """
    Represents one generated version within a run.
    """

    id: int | None = None

    run_id: int = Field(gt=0)

    attempt_number: int = Field(ge=1)

    generator_prompt_id: int = Field(gt=0)

    regeneration_prompt_id: int | None = Field(
        default=None,
        gt=0
    )

    lesson: Lesson

    assembled_prompt: str | None = None

    memory_pattern_ids: list[int] = Field(
        default_factory=list
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class RejectionLogRecord(AppBaseModel):
    """
    Stores consolidated information about
    a rejected lesson and its regeneration.
    """

    id: int | None = None

    lesson_version_id: int = Field(gt=0)

    next_lesson_version_id: int | None = Field(
        default=None,
        gt=0
    )

    regeneration_prompt_id: int | None = Field(
        default=None,
        gt=0
    )

    failure_summary: NonEmptyStr

    feedback_sent: str | None = None

    changes_made: str | None = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )