from pathlib import Path
from typing import Any

from content_agent.config import PROJECT_ROOT

from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.graph.nodes import (
    LessonWorkflowNodes
)

from content_agent.graph.workflow import (
    build_lesson_graph
)

from content_agent.models.run import LessonRequest


def load_reference_material(
    reference_path: str | Path | None = None
) -> str:
    """
    Loads reference material from a Markdown file.

    This is our initial static reference implementation.
    """

    path = (
        Path(reference_path)
        if reference_path is not None
        else PROJECT_ROOT / "reference_materials" / "rag_reference.md"
    )

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    if not path.exists():
        return ""

    return path.read_text(
        encoding="utf-8"
    )


def generate_lesson(
    request: LessonRequest,
    reference_material: str | None = None,
    reference_path: str | Path | None = None,
    db_path: str | Path | None = None,
    generator: Any | None = None,
    evaluator: Any | None = None,
    pattern_manager: Any | None = None
) -> dict:
    """
    Executes the complete lesson-generation workflow.

    Dependencies can be injected for testing.
    """

    # 1. Initialize repository.
    repository = DatabaseRepository(
        db_path=db_path
    )

    # 2. Load reference material if it wasn't
    # explicitly supplied.
    if reference_material is None:

        reference_material = load_reference_material(
            reference_path
        )

    # 3. Build workflow nodes.
    nodes = LessonWorkflowNodes(

        repository=repository,

        generator=generator,

        evaluator=evaluator,

        pattern_manager=pattern_manager

    )

    # 4. Compile LangGraph.
    graph = build_lesson_graph(nodes)

    # 5. Prepare initial graph state.
    initial_state = {

        "request": request,

        "reference_material": reference_material

    }

    # 6. Execute the complete workflow.
    final_state = graph.invoke(
        initial_state
    )

    # 7. Return a user-friendly result.
    lesson = final_state["current_lesson"]

    report = final_state["evaluation_report"]

    return {

        "run_id": final_state["run_id"],

        "final_status": final_state["final_status"],

        "total_attempts": len(
            final_state.get("attempt_history", [])
        ),

        "final_lesson_version_id": (
            final_state["current_lesson_version_id"]
        ),

        "final_lesson": lesson,

        "evaluation_report": report,

        "attempt_history": (
            final_state.get("attempt_history", [])
        ),

        "rejection_log_ids": (
            final_state.get("rejection_log_ids", [])
        ),

        "memory_results": (
            final_state.get("memory_results", [])
        ),

        "warnings": (
            final_state.get("warnings", [])
        )

    }