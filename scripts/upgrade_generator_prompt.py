
from content_agent.database.repository import DatabaseRepository

from content_agent.database.connection import get_connection

from content_agent.models.prompts import PromptVersion

from content_agent.models.enums import (
    PromptType,
    PromptStatus,
)


SCHEMA_INSTRUCTIONS = """

==================================================
STRICT LESSON OUTPUT SCHEMA REQUIREMENTS
==================================================

You MUST follow the exact data types defined in the
Lesson structured-output schema.

The following field types are mandatory:

1. STRING FIELDS

These fields MUST contain a single string, never an array
or list:

- topic
- title
- introduction
- why_it_matters

IMPORTANT:
why_it_matters MUST be one non-empty string.

If there are multiple reasons why the topic matters,
combine them into one concise paragraph.

NEVER return why_it_matters as a JSON array.

2. STRING ARRAY FIELDS

These fields MUST contain arrays of strings:

- learning_objectives
- benefits
- limitations
- recap

3. KEY CONCEPTS

key_concepts MUST be an array of objects.

Each object must contain:
- term: string
- explanation: string
- analogy: string or null

4. HOW IT WORKS

how_it_works MUST be an array of objects.

Each object must contain:
- step_number: integer
- title: string
- explanation: string
- example: string or null

Step numbers must start at 1 and be sequential.

5. PRACTICAL EXAMPLES

practical_examples MUST be an array of objects.

Each object must contain:
- title: string
- situation: string
- explanation: string
- takeaway: string

6. GLOSSARY

glossary MUST be an array of objects.

Each object must contain:
- term: string
- simple_definition: string
- analogy: string or null

FINAL VALIDATION BEFORE RESPONDING:

- Do not change the type of any field.
- Do not return arrays where strings are expected.
- Do not return strings where arrays are expected.
- Use null only for fields that allow null.
- Include all required fields.
- Follow the structured-output schema exactly.

If multiple points need to be explained in a string field,
combine them into one clear and readable paragraph.

The structured-output schema has priority over any
formatting preference in the lesson instructions.
"""


def main():

    repository = DatabaseRepository()

    # Get the currently active generator prompt.
    active_prompt = repository.get_active_prompt(
        PromptType.GENERATOR
    )

    if active_prompt is None:
        raise RuntimeError(
            "No active generator prompt found in the database."
        )

    print("Current generator prompt:", active_prompt.version)

    # Avoid creating another version if the instructions
    # have already been added.
    marker = "STRICT LESSON OUTPUT SCHEMA REQUIREMENTS"

    if marker in active_prompt.prompt_content:

        print(
            "The active generator prompt already contains "
            "the schema instructions."
        )

        return

    # Determine the next available prompt version.
    with get_connection() as connection:

        existing_versions = connection.execute(
            """
            SELECT version
            FROM prompt_versions
            WHERE prompt_type = ?
            """,
            ("GENERATOR",),
        ).fetchall()

    version_numbers = []

    for row in existing_versions:

        version = row["version"]

        if (
            isinstance(version, str)
            and version.upper().startswith("V")
            and version[1:].isdigit()
        ):
            version_numbers.append(int(version[1:]))

    next_version = max(version_numbers, default=0) + 1

    version_name = f"V{next_version}"

    # Preserve the original prompt and append the schema contract.
    updated_content = (
        active_prompt.prompt_content.rstrip()
        + "\n\n"
        + SCHEMA_INSTRUCTIONS
    )

    new_prompt = PromptVersion(

        prompt_type=PromptType.GENERATOR,

        version=version_name,

        status=PromptStatus.DRAFT,

        change_summary=(
            "Added explicit structured-output data type "
            "requirements for every lesson section."
        ),

        prompt_content=updated_content,

    )

    prompt_id = repository.create_prompt_version(
        new_prompt
    )

    # Activate the new generator prompt.
    repository.activate_prompt_version(prompt_id)

    updated_prompt = repository.get_active_prompt(
        PromptType.GENERATOR
    )

    print()
    print("Generator prompt upgraded successfully.")
    print("Previous version:", active_prompt.version)
    print("New active version:", updated_prompt.version)
    print("New prompt ID:", updated_prompt.id)


if __name__ == "__main__":
    main()
