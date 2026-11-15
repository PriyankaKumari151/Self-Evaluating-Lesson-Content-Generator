import json

from content_agent.models.prompts import PromptVersion

from content_agent.models.lesson import Lesson

from content_agent.models.rubric import RubricCriterion

from content_agent.models.enums import PromptType

from content_agent.prompts.template import render_template


def build_evaluator_prompt(
    standard_prompt: PromptVersion,
    lesson: Lesson,
    rubric_criteria: list[RubricCriterion],
    reference_material: str = ""
) -> str:
    """
    Constructs the evaluator prompt.

    Supplies the generated lesson and active rubric
    criteria to the LLM-as-a-Judge.
    """

    if standard_prompt.prompt_type != PromptType.EVALUATOR:
        raise ValueError(
            "Expected an EVALUATOR prompt version."
        )

    if not rubric_criteria:
        raise ValueError(
            "At least one rubric criterion is required."
        )

    active_criteria = [
        criterion.model_dump(mode="json")
        for criterion in rubric_criteria
        if criterion.is_active
    ]

    if not active_criteria:
        raise ValueError(
            "No active rubric criteria are available."
        )

    lesson_json = lesson.model_dump_json(
        indent=2
    )

    rubric_json = json.dumps(
        active_criteria,
        indent=2
    )

    variables = {

        "REFERENCE_MATERIAL": (
            reference_material.strip()
            if reference_material.strip()
            else "No external reference material was supplied."
        ),

        "LESSON_JSON": lesson_json,

        "RUBRIC_JSON": rubric_json

    }

    return render_template(
        template=standard_prompt.prompt_content,
        variables=variables
    )