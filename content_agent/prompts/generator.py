from content_agent.models.prompts import PromptVersion

from content_agent.models.lesson import LearnerProfile

from content_agent.models.enums import PromptType

from content_agent.prompts.template import (
    render_template,
    format_learned_guidelines
)


def build_generator_prompt(
    standard_prompt: PromptVersion,
    topic: str,
    learner_profile: LearnerProfile,
    reference_material: str = "",
    learned_guidelines: list[dict] | None = None
) -> str:
    """
    Constructs the complete generation prompt.

    Combines:
    1. Standard generator prompt from Prompt_Versions.
    2. User topic.
    3. Learner profile.
    4. Reference material.
    5. Active learned guidelines.

    Does not modify the stored standard prompt.
    """

    if standard_prompt.prompt_type != PromptType.GENERATOR:
        raise ValueError(
            "Expected a GENERATOR prompt version."
        )

    if not topic.strip():
        raise ValueError("Topic cannot be empty.")

    guidelines = format_learned_guidelines(
        learned_guidelines or []
    )

    variables = {

        "TOPIC": topic.strip(),

        "LEARNER_PROFILE": (
            learner_profile.model_dump_json(indent=2)
        ),

        "REFERENCE_MATERIAL": (
            reference_material.strip()
            if reference_material.strip()
            else "No external reference material was supplied."
        ),

        "LEARNED_GUIDELINES": guidelines

    }

    return render_template(
        template=standard_prompt.prompt_content,
        variables=variables
    )