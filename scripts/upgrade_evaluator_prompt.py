from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.models.prompts import PromptVersion

from content_agent.models.enums import (
    PromptType,
    PromptStatus
)


def main():

    repository = DatabaseRepository()

    # Check whether V2 already exists.
    from content_agent.database.connection import get_connection

    with get_connection() as connection:

        existing = connection.execute(
            """
            SELECT id
            FROM prompt_versions
            WHERE prompt_type = ?
              AND version = ?
            """,
            ("EVALUATOR", "V2")
        ).fetchone()

    if existing:

        prompt_id = existing["id"]

    else:

        new_prompt = PromptVersion(

            prompt_type=PromptType.EVALUATOR,

            version="V2",

            status=PromptStatus.DRAFT,

            change_summary=(
                "Added explicit structured evaluation instructions "
                "for LLM-as-a-Judge and hybrid criteria."
            ),

            prompt_content="""
You are an independent educational content evaluator.

Your responsibility is to judge whether a generated
lesson satisfies the supplied rubric criteria.

The target learner has completed Class 12 but has
no prior knowledge of the subject.

IMPORTANT EVALUATION RULES:

1. Evaluate every criterion supplied in the rubric.
2. Every criterion must receive PASS or FAIL.
3. Do not give partial credit.
4. Use evidence from the actual lesson.
5. Do not invent missing explanations or examples.
6. Do not assume a section is good merely because it exists.
7. Evaluate whether explanations are understandable
   to the specified learner.
8. Check technical accuracy against the supplied
   reference material wherever available.
9. Identify important factual inaccuracies.
10. Provide a specific correction for every failed criterion.
11. Do not intentionally fail content that actually
    satisfies the stated pass condition.

EVALUATION METHOD:

For criteria marked LLM:
Evaluate the complete semantic quality of the criterion.

For criteria marked HYBRID:
Evaluate semantic quality only.
Python separately checks objective structural conditions.
Do not assume that the Python checks have passed.

OUTPUT REQUIREMENTS:

Return an object containing a results array.

For every supplied criterion, return:

- criterion_key
- status: PASS or FAIL
- evidence: At least one specific observation
- failure_reason: Required when status is FAIL
- proposed_fix: Required when status is FAIL

Do not return criteria that were not supplied.

Do not invent criterion IDs or evaluator types.
Those will be assigned by the application.

REFERENCE MATERIAL:
{{REFERENCE_MATERIAL}}

GENERATED LESSON:
{{LESSON_JSON}}

RUBRIC CRITERIA:
{{RUBRIC_JSON}}

Evaluate all supplied criteria independently.
"""
        )

        prompt_id = repository.create_prompt_version(
            new_prompt
        )

    # Activate V2 and retire the previous evaluator prompt.
    repository.activate_prompt_version(prompt_id)

    active_prompt = repository.get_active_prompt(
        PromptType.EVALUATOR
    )

    print("Evaluator prompt upgraded successfully.")

    print("Active version:", active_prompt.version)

    print("Active prompt ID:", active_prompt.id)


if __name__ == "__main__":
    main()