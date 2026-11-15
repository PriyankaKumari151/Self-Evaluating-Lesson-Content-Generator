import json

from content_agent.models.prompts import PromptVersion

from content_agent.models.lesson import (
    Lesson,
    LearnerProfile
)

from content_agent.models.evaluation import EvaluationResult

from content_agent.models.enums import (
    PromptType,
    EvaluationStatus
)

from content_agent.prompts.template import (
    render_template,
    format_learned_guidelines
)


def build_regeneration_prompt(
    standard_prompt: PromptVersion,
    topic: str,
    learner_profile: LearnerProfile,
    previous_lesson: Lesson,
    evaluation_results: list[EvaluationResult],
    learned_guidelines: list[dict] | None = None,
    base_generation_prompt: str | None = None
) -> str:
    """
    Constructs the regeneration prompt.

    Combines:
    1. Standard regeneration prompt.
    2. Previous generated lesson.
    3. Current-run failure feedback.
    4. Relevant learned guidelines.
    """

    if standard_prompt.prompt_type != PromptType.REGENERATION:
        raise ValueError(
            "Expected a REGENERATION prompt version."
        )

    failed_results = [
        result
        for result in evaluation_results
        if result.status == EvaluationStatus.FAIL
    ]

    if not failed_results:
        raise ValueError(
            "Regeneration cannot be requested "
            "without failed evaluation criteria."
        )

    feedback = []

    for result in failed_results:

        feedback.append({

            "criterion": result.criterion_name,

            "criterion_key": result.criterion_key,

            "evidence": result.evidence,

            "failure_reason": result.failure_reason,

            "proposed_fix": result.proposed_fix

        })

    feedback_json = json.dumps(
        feedback,
        indent=2
    )

    guidelines = format_learned_guidelines(
        learned_guidelines or []
    )

    variables = {

        "TOPIC": topic,

        "LEARNER_PROFILE": (
            learner_profile.model_dump_json(indent=2)
        ),

        "PREVIOUS_LESSON": (
            previous_lesson.model_dump_json(indent=2)
        ),

        "EVALUATION_FEEDBACK": feedback_json,

        "LEARNED_GUIDELINES": guidelines

    }

    regeneration_instructions = render_template(
            template=standard_prompt.prompt_content,
            variables=variables
        )

    if base_generation_prompt:

            return f"""
    {base_generation_prompt}

    ==================================================
    REGENERATION INSTRUCTIONS
    ==================================================

    {regeneration_instructions}
    """

    return regeneration_instructions