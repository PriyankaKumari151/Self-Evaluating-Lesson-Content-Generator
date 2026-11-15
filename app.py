import streamlit as st

from content_agent.models.run import LessonRequest
from content_agent.models.lesson import LearnerProfile
from content_agent.services.lesson_service import generate_lesson


# --------------------------------------------------
# Page configuration
# --------------------------------------------------

st.set_page_config(
    page_title="AI Lesson Generator",
    page_icon="📚",
    layout="wide",
)

st.title("📚 Self-Evaluating Lesson Content Generator")
st.caption(
    "Generate, evaluate, and approve beginner-friendly "
    "learning content using an AI-powered workflow."
)


# --------------------------------------------------
# Utility functions
# These handle both Pydantic models and dictionaries.
# --------------------------------------------------

def to_dict(value):
    """Convert an object into a dictionary where possible."""

    if isinstance(value, dict):
        return value

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    if hasattr(value, "dict"):
        return value.dict()

    if hasattr(value, "__dict__"):
        return vars(value)

    return {"value": value}


def get_field(obj, *names, default=None):
    """Read the first available field from an object or dictionary."""

    for name in names:
        if isinstance(obj, dict) and name in obj:
            return obj[name]

        if hasattr(obj, name):
            return getattr(obj, name)

    return default


def display_value(value):
    """Convert enums and other objects into readable text."""

    if hasattr(value, "value"):
        value = value.value

    return str(value)


def humanize(text):
    """Convert field_name into Field Name."""

    return str(text).replace("_", " ").title()


def normalize_keys(record):
    """Normalize dictionary keys for reliable content detection."""

    return {
        str(key).strip().lower().replace(" ", "_").replace("-", "_"): val
        for key, val in record.items()
    }


def format_cell_value(value):
    """Convert list/dict values into readable table-cell text."""

    if value is None:
        return ""

    if isinstance(value, list):
        return "; ".join(format_cell_value(item) for item in value)

    if isinstance(value, dict):
        return "; ".join(
            f"{humanize(key)}: {format_cell_value(item)}"
            for key, item in value.items()
        )

    return display_value(value)


# --------------------------------------------------
# Lesson rendering
# --------------------------------------------------

def render_content(value):
    """Render lesson content, using tables for structured sections."""

    if value is None:
        return

    if isinstance(value, str):
        if value.strip():
            st.markdown(value)
        return

    if isinstance(value, (int, float, bool)):
        st.write(value)
        return

    if isinstance(value, list):
        # Convert Pydantic objects and dictionaries into dictionaries.
        records = [to_dict(item) for item in value]

        # Table 1: How It Works / workflow steps.
        # Expected fields: step_number, title, explanation, example.
        workflow_rows = []

        for record in records:
            if not isinstance(record, dict):
                continue

            item = normalize_keys(record)

            step_number = item.get(
                "step_number",
                item.get("step", item.get("step_no")),
            )
            title = item.get("title")
            explanation = item.get("explanation")
            example = item.get("example", item.get("examples", ""))

            if (
                step_number is not None
                and title is not None
                and explanation is not None
            ):
                workflow_rows.append({
                    "Step Number": format_cell_value(step_number),
                    "Title": format_cell_value(title),
                    "Explanation": format_cell_value(explanation),
                    "Example": format_cell_value(example),
                })

        if workflow_rows and len(workflow_rows) == len(records):
            st.dataframe(
                workflow_rows,
                use_container_width=True,
                hide_index=True,
            )
            return

        # Table 2: Glossary.
        # Expected fields: term, simple_definition, analogy.
        glossary_rows = []

        for record in records:
            if not isinstance(record, dict):
                continue

            item = normalize_keys(record)
            definition = item.get(
                "simple_definition",
                item.get("definition"),
            )

            if "term" in item and definition is not None:
                glossary_rows.append({
                    "Term": format_cell_value(item["term"]),
                    "Simple Definition": format_cell_value(definition),
                    "Analogy": format_cell_value(item.get("analogy", "")),
                })

        if glossary_rows and len(glossary_rows) == len(records):
            st.dataframe(
                glossary_rows,
                use_container_width=True,
                hide_index=True,
            )
            return

        # Table 3: Key Concepts.
        # Expected fields: term, explanation, examples and/or analogy.
        is_concept_list = (
            len(records) > 0
            and all(
                isinstance(item, dict)
                and "term" in normalize_keys(item)
                and "explanation" in normalize_keys(item)
                for item in records
            )
        )

        if is_concept_list:
            table_rows = []

            for record in records:
                item = normalize_keys(record)
                examples = item.get("examples", item.get("example"))
                analogy = item.get("analogy")

                example_parts = []

                if examples:
                    example_parts.append(format_cell_value(examples))

                if analogy:
                    example_parts.append(
                        f"Analogy: {format_cell_value(analogy)}"
                    )

                table_rows.append({
                    "Term": format_cell_value(item["term"]),
                    "Explanation": format_cell_value(item["explanation"]),
                    "Examples": "\n".join(example_parts),
                })

            st.dataframe(
                table_rows,
                use_container_width=True,
                hide_index=True,
            )
            return

        # Practical Examples: render each example as a compact card.
        # Expected fields: title, situation, explanation, takeaway, benefits.
        practical_examples = []

        for record in records:
            if not isinstance(record, dict):
                continue

            item = normalize_keys(record)
            title = item.get("title", item.get("example_title"))
            has_example_details = any(
                key in item
                for key in (
                    "situation",
                    "explanation",
                    "takeaway",
                    "benefits",
                )
            )

            if title is None or not has_example_details:
                continue

            practical_examples.append(item)

        if (
            practical_examples
            and len(practical_examples) == len(records)
        ):
            for index, item in enumerate(practical_examples, start=1):
                with st.container(border=True):
                    title = item.get("title", item.get("example_title"))
                    st.markdown(
                        f"**Example {index}: {format_cell_value(title)}**"
                    )

                    # Keep labels on the same line as their content.
                    # This avoids large repeated subheadings.
                    compact_fields = (
                        ("Situation", item.get("situation")),
                        ("Explanation", item.get("explanation")),
                        ("Takeaway", item.get("takeaway")),
                    )

                    for label, field_value in compact_fields:
                        if field_value is not None and field_value != "":
                            st.markdown(
                                f"**{label}:** {format_cell_value(field_value)}"
                            )

                    benefits = item.get("benefits")
                    if benefits:
                        st.markdown("**Benefits**")

                        benefit_items = (
                            benefits
                            if isinstance(benefits, list)
                            else [benefits]
                        )

                        for benefit in benefit_items:
                            st.markdown(
                                f"- {format_cell_value(benefit)}"
                            )

                    # Preserve any additional fields the generator may return.
                    known_fields = {
                        "title",
                        "example_title",
                        "situation",
                        "explanation",
                        "takeaway",
                        "benefits",
                    }

                    for key, field_value in item.items():
                        if key in known_fields or field_value is None or field_value == "":
                            continue

                        st.markdown(
                            f"**{humanize(key)}:** "
                            f"{format_cell_value(field_value)}"
                        )
            return

        # Normal list rendering for all other lesson sections.
        for item in value:
            if isinstance(item, str):
                st.markdown(f"- {item}")
            elif isinstance(item, dict) or hasattr(item, "model_dump"):
                render_content(item)
            else:
                st.write(item)

        return

    data = to_dict(value)

    ignored_fields = {
        "id",
        "created_at",
        "updated_at",
        "metadata",
    }

    for key, item in data.items():
        if key.lower() in ignored_fields:
            continue

        if item is None or item == "":
            continue

        st.markdown(f"#### {humanize(key)}")
        render_content(item)


def render_lesson(lesson):
    if lesson is None:
        st.warning("No lesson content is available.")
        return

    lesson_data = to_dict(lesson)

    title = get_field(
        lesson,
        "title",
        default="Generated Lesson",
    )

    st.header(title)

    ignored_fields = {
        "title",
        "id",
        "created_at",
        "updated_at",
        "metadata",
    }

    for key, value in lesson_data.items():
        if key.lower() in ignored_fields:
            continue

        if value is None or value == "":
            continue

        st.markdown(f"### {humanize(key)}")
        render_content(value)


# --------------------------------------------------
# Evaluation rendering
# --------------------------------------------------

def render_evaluation(report):
    if report is None:
        st.warning("No evaluation report is available.")
        return

    all_passed = get_field(
        report,
        "all_passed",
        "passed",
        default=None,
    )

    results = get_field(
        report,
        "results",
        "criterion_results",
        "evaluations",
        default=[],
    )

    if all_passed is not None:
        if all_passed:
            st.success("All evaluation criteria passed.")
        else:
            st.error("One or more evaluation criteria failed.")

    if not results:
        st.info(
            "The evaluation report does not expose a criterion "
            "results list. Inspect the raw report below."
        )
        st.json(to_dict(report))
        return

    rows = []

    for item in results:
        criterion = get_field(
            item,
            "criterion_name",
            "criterion_id",
            "criterion",
            "name",
            default="Unknown criterion",
        )

        passed = get_field(
            item,
            "passed",
            "is_passed",
            default=None,
        )

        status = get_field(item, "status", default=None)

        if passed is not None:
            result_status = "PASS" if passed else "FAIL"
        elif status is not None:
            result_status = display_value(status).upper()
        else:
            result_status = "UNKNOWN"

        method = get_field(
            item,
            "evaluation_method",
            "method",
            default="",
        )

        rows.append({
            "Criterion": display_value(criterion),
            "Result": result_status,
            "Method": display_value(method) if method else "",
        })

    st.dataframe(
        rows,
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("### Evaluation details")

    for index, item in enumerate(results, start=1):
        criterion = get_field(
            item,
            "criterion_name",
            "criterion_id",
            "criterion",
            "name",
            default=f"Criterion {index}",
        )

        passed = get_field(
            item,
            "passed",
            "is_passed",
            default=None,
        )

        status = get_field(item, "status", default=None)

        if passed is not None:
            is_passed = bool(passed)
        else:
            is_passed = (
                display_value(status).upper()
                in {"PASS", "PASSED", "TRUE"}
            )

        icon = "✅" if is_passed else "❌"

        with st.expander(f"{icon} {display_value(criterion)}"):
            evidence = get_field(item, "evidence", default=None)
            failure_reason = get_field(
                item,
                "failure_reason",
                "reason",
                default=None,
            )
            proposed_fix = get_field(
                item,
                "proposed_fix",
                "suggested_fix",
                "improvement_suggestion",
                default=None,
            )

            if evidence:
                st.markdown("**Evidence**")
                st.write(evidence)

            if failure_reason:
                st.markdown("**Failure reason**")
                st.write(failure_reason)

            if proposed_fix:
                st.markdown("**Proposed correction**")
                st.write(proposed_fix)

            st.markdown("**Complete criterion result**")
            st.json(to_dict(item))


# --------------------------------------------------
# Workflow history rendering
# --------------------------------------------------

def render_workflow(result):
    st.subheader("Workflow summary")

    # Show only the information that is meaningful to the end user.
    st.metric(
        "Generation attempts",
        result["total_attempts"],
    )

    st.markdown("### Attempt history")

    history = result.get("attempt_history", [])

    if not history:
        st.info("No attempt history available.")

    for attempt in history:
        attempt_data = to_dict(attempt)

        attempt_number = attempt_data.get(
            "attempt_number",
            "Unknown",
        )

        title = attempt_data.get(
            "lesson_title",
            "Lesson",
        )

        passed = attempt_data.get("passed", False)

        failed_criteria = attempt_data.get(
            "failed_criteria",
            [],
        )

        status = "Passed" if passed else "Failed"

        with st.expander(
            f"Attempt {attempt_number}: {title} — {status}"
        ):
            st.write("Failed criteria:")

            if failed_criteria:
                for criterion in failed_criteria:
                    st.write(f"- {criterion}")
            else:
                st.write("None")

            st.json(attempt_data)

    st.markdown("### Rejection logs")

    rejection_ids = result.get("rejection_log_ids", [])

    if rejection_ids:
        for log_id in rejection_ids:
            st.write(f"Rejection Log ID: {log_id}")
    else:
        st.info("No rejection logs for this run.")

    st.markdown("### Learning memory")

    memory_results = result.get("memory_results", [])

    if memory_results:
        for memory in memory_results:
            memory_data = to_dict(memory)

            pattern_key = memory_data.get(
                "pattern_key",
                "Memory pattern",
            )

            message = memory_data.get("message", "")

            st.write(f"**{pattern_key}**")
            st.write(message)
    else:
        st.info(
            "No evaluation failures were available for "
            "memory processing in this run."
        )

    warnings = result.get("warnings", [])

    if warnings:
        st.markdown("### Workflow warnings")

        for warning in warnings:
            st.warning(warning)


# --------------------------------------------------
# Input form
# --------------------------------------------------

with st.form("lesson_generation_form"):
    st.subheader("Create a lesson")

    topic = st.text_input(
        "Lesson topic",
        value="Introduction to RAG",
        help="Enter the subject you want the system to teach.",
    )

    st.markdown("### Learner profile")

    education = st.text_input(
        "Education level",
        value="12th-grade graduate",
    )

    technical_background = st.text_input(
        "Technical background",
        value="No AI knowledge",
    )

    english_level = st.selectbox(
        "English proficiency",
        ["Basic", "Intermediate", "Advanced"],
        index=0,
    )

    learning_goal = st.text_area(
        "Learning goal",
        value=(
            "Understand the topic from scratch "
            "with practical examples."
        ),
    )

    max_retries = st.slider(
        "Maximum regeneration attempts",
        min_value=0,
        max_value=2,
        value=2,
        help=(
            "A retry is an additional generation after "
            "the initial attempt."
        ),
    )

    submitted = st.form_submit_button(
        "Generate and Evaluate Lesson",
        type="primary",
        use_container_width=True,
    )


# --------------------------------------------------
# Execute workflow
# --------------------------------------------------

if submitted:
    # Avoid showing an old result if this new request fails.
    st.session_state.pop("last_result", None)

    if not topic.strip():
        st.error("Please enter a lesson topic.")
    else:
        try:
            request = LessonRequest(
                topic=topic.strip(),
                learner_profile=LearnerProfile(
                    education=education.strip(),
                    technical_background=technical_background.strip(),
                    english_level=english_level,
                    learning_goal=learning_goal.strip(),
                ),
                max_retries=max_retries,
            )

            with st.spinner(
                "Generating and evaluating your lesson..."
            ):
                result = generate_lesson(request=request)

            st.session_state["last_result"] = result
            st.success("Workflow execution completed.")

        except Exception as exc:
            st.error("The workflow could not be completed.")

            with st.expander("Technical error details"):
                st.exception(exc)


# --------------------------------------------------
# Display most recent result
# --------------------------------------------------

result = st.session_state.get("last_result")

if result:
    st.divider()

    final_status = display_value(
        result.get("final_status", "UNKNOWN")
    ).upper()

    if final_status == "APPROVED":
        st.success("✅ LESSON APPROVED FOR DELIVERY")
    elif final_status == "REJECTED":
        st.error(
            "❌ LESSON REJECTED — Rubric requirements "
            "were not satisfied."
        )
    else:
        st.warning(f"Workflow status: {final_status}")

    lesson_tab, evaluation_tab, workflow_tab = st.tabs(
        [
            "📖 Generated Lesson",
            "🔍 Evaluation",
            "⚙️ Workflow Details",
        ]
    )

    with lesson_tab:
        render_lesson(result.get("final_lesson"))

    with evaluation_tab:
        render_evaluation(result.get("evaluation_report"))

    with workflow_tab:
        render_workflow(result)
