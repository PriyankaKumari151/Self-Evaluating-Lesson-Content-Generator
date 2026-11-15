import re


PLACEHOLDER_PATTERN = re.compile(
    r"\{\{([A-Z][A-Z0-9_]*)\}\}"
)


def render_template(
    template: str,
    variables: dict[str, str]
) -> str:
    """
    Replaces named placeholders in a prompt template.

    Raises ValueError if a required placeholder is missing
    or if an unresolved placeholder remains.
    """

    if not template.strip():
        raise ValueError("Prompt template cannot be empty.")

    placeholders = set(
        PLACEHOLDER_PATTERN.findall(template)
    )

    supplied_variables = set(variables.keys())

    missing_variables = placeholders - supplied_variables

    if missing_variables:
        raise ValueError(
            "Missing prompt variables: "
            + ", ".join(sorted(missing_variables))
        )

    rendered = PLACEHOLDER_PATTERN.sub(
        lambda match: variables[match.group(1)],
        template
    )

    unresolved = PLACEHOLDER_PATTERN.findall(rendered)

    if unresolved:
        raise ValueError(
            "Unresolved placeholders: "
            + ", ".join(unresolved)
        )

    return rendered.strip()


def format_learned_guidelines(
    guidelines: list[dict]
) -> str:
    """
    Formats active learned guidelines into a readable
    prompt section, grouped by rubric criterion.
    """

    if not guidelines:
        return (
            "No active learned guidelines are available. "
            "Follow the standard instructions strictly."
        )

    grouped_guidelines = {}

    for guideline in guidelines:

        criterion = guideline.get(
            "criterion_name",
            guideline.get("criterion_key", "General")
        )

        instruction = guideline.get("learned_guideline")

        if not instruction:
            continue

        grouped_guidelines.setdefault(
            criterion, []
        ).append(
            instruction
        )

    if not grouped_guidelines:
        return (
            "No active learned guidelines are available. "
            "Follow the standard instructions strictly."
        )

    sections = []

    for criterion, instructions in grouped_guidelines.items():

        section = f"CRITERION: {criterion}\n"

        section += "\n".join(
            f"- {instruction}"
            for instruction in instructions
        )

        sections.append(section)

    return "\n\n".join(sections)


def get_memory_pattern_ids(
    guidelines: list[dict]
) -> list[int]:
    """
    Extracts unique memory pattern IDs used in prompt construction.
    """

    pattern_ids = {
        guideline["id"]
        for guideline in guidelines
        if guideline.get("id") is not None
    }

    return sorted(pattern_ids)