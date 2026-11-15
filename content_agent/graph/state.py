from typing import TypedDict, Any

from content_agent.models.run import LessonRequest

from content_agent.models.lesson import Lesson

from content_agent.models.evaluation import (
    EvaluationReport
)

from content_agent.models.rubric import (
    RubricCriterion
)

from content_agent.models.prompts import (
    PromptVersion
)

from content_agent.models.memory import (
    MemoryProcessingResult
)


class LessonGraphState(TypedDict, total=False):
    """
    Shared state maintained throughout LangGraph execution.
    """

    # -----------------------------------------
    # User input
    # -----------------------------------------

    request: LessonRequest

    topic: str
    from content_agent.models.lesson import LearnerProfile

    learner_profile: LearnerProfile

    reference_material: str

    # -----------------------------------------
    # Run management
    # -----------------------------------------

    run_id: int

    retry_count: int

    max_retries: int

    attempt_number: int

    final_status: str

    # -----------------------------------------
    # Database configuration/context
    # -----------------------------------------

    rubric_criteria: list[RubricCriterion]

    # -----------------------------------------
    # Active prompts
    # -----------------------------------------

    generator_prompt: PromptVersion

    evaluator_prompt: PromptVersion

    regeneration_prompt: PromptVersion | None

    # -----------------------------------------
    # Generation
    # -----------------------------------------

    current_lesson: Lesson

    current_lesson_version_id: int

    assembled_prompt: str

    generator_prompt_id: int

    regeneration_prompt_id: int | None

    current_memory_pattern_ids: list[int]

    # -----------------------------------------
    # Evaluation
    # -----------------------------------------

    evaluation_report: EvaluationReport

    evaluation_ids: list[int]

    # -----------------------------------------
    # Regeneration history
    # -----------------------------------------

    pending_rejection_log_id: int | None

    rejection_log_ids: list[int]

    # -----------------------------------------
    # Self-learning memory
    # -----------------------------------------

    memory_results: list[MemoryProcessingResult]

    # -----------------------------------------
    # Execution history
    # -----------------------------------------

    attempt_history: list[dict[str, Any]]

    # Non-fatal errors and warnings
    warnings: list[str]