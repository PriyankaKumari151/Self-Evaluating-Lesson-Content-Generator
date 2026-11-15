from pathlib import Path

from content_agent.database.connection import get_connection

from content_agent.models.rubric import DEFAULT_RUBRIC

from content_agent.models.enums import (
    PromptType,
    PromptStatus
)


INITIAL_PROMPTS = [

    {
        "prompt_type": PromptType.GENERATOR,
        "version": "V1",

        "change_summary": "Initial generator prompt.",

        "prompt_content": """
You are an expert educator who specializes in
teaching beginners.

Your target audience consists of learners who may
have completed Class 12 but have no prior knowledge
of the requested technical subject.

YOUR OBJECTIVE:

Generate a complete, standalone beginner lesson
on the requested topic.

LEARNER REQUIREMENTS:

1. Use simple English.
2. Prefer short and clear sentences.
3. Do not assume prior technical knowledge.
4. Explain important technical terminology.
5. Use relatable practical examples.
6. Introduce concepts in a logical sequence.

CONTENT REQUIREMENTS:

1. Explain WHAT the topic is.
2. Explain WHY it matters.
3. Explain HOW it works.
4. Introduce the important concepts.
5. Include practical examples.
6. Explain the benefits and limitations.
7. End with a concise recap.

QUALITY REQUIREMENTS:

1. Maintain factual accuracy.
2. Avoid unexplained jargon.
3. Avoid overly complicated explanations.
4. Make the lesson understandable independently.
5. Do not introduce information that contradicts
   the supplied reference material.

INPUT TOPIC:
{{TOPIC}}

LEARNER PROFILE:
{{LEARNER_PROFILE}}

REFERENCE MATERIAL:
{{REFERENCE_MATERIAL}}

LEARNED GUIDELINES:
{{LEARNED_GUIDELINES}}

Return the complete lesson using the required
structured output schema.
"""
    },

    {
        "prompt_type": PromptType.EVALUATOR,
        "version": "V1",

        "change_summary": "Initial evaluator prompt.",

        "prompt_content": """
You are an independent educational content evaluator.

Your responsibility is to determine whether the
generated lesson is good enough to deliver to
the target learner.

You MUST evaluate the lesson against every supplied
rubric criterion.

EVALUATION RULES:

1. Each criterion must receive PASS or FAIL.
2. Do not provide partial credit.
3. A PASS must be supported by evidence.
4. A FAIL must include evidence and a specific reason.
5. Every failure must include an actionable proposed fix.
6. Do not approve content merely because it sounds fluent.
7. Evaluate the content from the perspective of the
   specified beginner learner.
8. Check factual claims against supplied references
   wherever applicable.
9. Do not invent factual errors.
10. Follow the supplied pass conditions strictly.

REFERENCE MATERIAL:
{{REFERENCE_MATERIAL}}

LESSON:
{{LESSON_JSON}}

RUBRIC:
{{RUBRIC_JSON}}

Return one evaluation result for each supplied
active rubric criterion.
"""
    },

    {
        "prompt_type": PromptType.REGENERATION,
        "version": "V1",

        "change_summary": "Initial regeneration prompt.",

        "prompt_content": """
You are an expert educational content editor.

Your task is to improve a previously generated
beginner lesson that failed evaluation.

You will receive:

1. The original topic.
2. The learner profile.
3. The previous lesson.
4. The evaluator's failure reasons.
5. The evaluator's proposed corrections.
6. Relevant historical learned guidelines.

INSTRUCTIONS:

1. Correct every identified failure.
2. Preserve sections that are already correct.
3. Do not remove important information unnecessarily.
4. Maintain simple English and beginner-friendly explanations.
5. Do not introduce new factual errors.
6. Follow the learned guidelines relevant to the topic.
7. Return the complete revised lesson.
8. Maintain the required structured output format.

TOPIC:
{{TOPIC}}

LEARNER PROFILE:
{{LEARNER_PROFILE}}

PREVIOUS LESSON:
{{PREVIOUS_LESSON}}

EVALUATION FEEDBACK:
{{EVALUATION_FEEDBACK}}

LEARNED GUIDELINES:
{{LEARNED_GUIDELINES}}

Return the complete revised lesson.
"""
    }

]


def seed_initial_data(
    db_path: str | Path | None = None
) -> None:
    """
    Inserts initial rubric criteria and prompt versions.

    This operation is idempotent:
    running it multiple times does not create duplicates.
    """

    with get_connection(db_path) as connection:

        # -----------------------------------------
        # Insert rubric criteria
        # -----------------------------------------

        for criterion in DEFAULT_RUBRIC:

            connection.execute(

                """
                INSERT OR IGNORE INTO rubric_criteria (

                    criterion_key,
                    criterion_name,
                    description,
                    pass_condition,
                    evaluation_method,
                    is_mandatory,
                    display_order,
                    is_active

                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,

                (
                    criterion.criterion_key,
                    criterion.criterion_name,
                    criterion.description,
                    criterion.pass_condition,
                    criterion.evaluation_method.value,
                    int(criterion.is_mandatory),
                    criterion.display_order,
                    int(criterion.is_active)
                )

            )

        # -----------------------------------------
        # Insert initial prompt versions
        # -----------------------------------------

        for prompt in INITIAL_PROMPTS:

            connection.execute(

                """
                INSERT OR IGNORE INTO prompt_versions (

                    prompt_type,
                    version,
                    prompt_content,
                    change_summary,
                    status

                )
                VALUES (?, ?, ?, ?, ?)
                """,

                (
                    prompt["prompt_type"].value,
                    prompt["version"],
                    prompt["prompt_content"].strip(),
                    prompt["change_summary"],
                    PromptStatus.ACTIVE.value
                )

            )

    print("Initial rubric and prompt data seeded successfully.")