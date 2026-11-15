from pathlib import Path

from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.database.connection import (
    get_connection
)

from content_agent.models.enums import PromptType

from content_agent.evaluation import LessonEvaluator


def main():

    repository = DatabaseRepository()

    # Use the lesson generated in Phase 6.
    lesson_version_id = 1

    # Avoid accidentally saving duplicate evaluations.
    with get_connection() as connection:

        existing = connection.execute(
            """
            SELECT COUNT(*)
            FROM evaluations
            WHERE lesson_version_id = ?
            """,
            (lesson_version_id,)
        ).fetchone()[0]

    if existing > 0:
        raise RuntimeError(
            "This lesson version has already been evaluated. "
            "Generate a new lesson or choose another lesson version."
        )

    # Retrieve the previous generated lesson.
    lesson_record = repository.get_lesson_version(
        lesson_version_id
    )

    if lesson_record is None:
        raise RuntimeError("Lesson version not found.")

    # Retrieve the active evaluator prompt.
    evaluator_prompt = repository.get_active_prompt(
        PromptType.EVALUATOR
    )

    if evaluator_prompt is None:
        raise RuntimeError("No active evaluator prompt found.")

    # Retrieve the rubric from SQLite.
    rubric = repository.get_rubric_criteria()

    # Load reference material if available.
    reference_path = (
        Path("reference_materials") / "rag_reference.md"
    )

    reference_material = (
        reference_path.read_text(encoding="utf-8")
        if reference_path.exists()
        else ""
    )

    # Execute hybrid evaluation.
    evaluator = LessonEvaluator()

    print("Evaluating lesson...")

    report = evaluator.evaluate(

        lesson=lesson_record.lesson,

        rubric_criteria=rubric,

        evaluator_prompt=evaluator_prompt,

        attempt_number=lesson_record.attempt_number,

        lesson_version_id=lesson_record.id,

        reference_material=reference_material

    )

    # Save all criterion-wise results.
    evaluation_ids = repository.save_evaluation_report(

        lesson_version_id=lesson_record.id,

        report=report,

        evaluator_prompt_id=evaluator_prompt.id

    )

    print("\nEvaluation completed.")

    print("Evaluation IDs:", evaluation_ids)

    print("\nCriterion-wise results:\n")

    for result in report.results:

        print(
            result.criterion_name,
            "=>",
            result.status.value,
            f"({result.evaluator_type.value})"
        )

        if result.status.value == "FAIL":

            print("Reason:", result.failure_reason)

            print("Proposed fix:", result.proposed_fix)

        print()

    print("=" * 50)

    print(
        "FINAL VERDICT:",
        "PASS" if report.all_passed else "FAIL"
    )


if __name__ == "__main__":
    main()