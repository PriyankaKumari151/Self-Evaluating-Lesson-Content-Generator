from langgraph.graph import (
    StateGraph,
    START,
    END
)

from content_agent.graph.state import LessonGraphState

from content_agent.graph.nodes import LessonWorkflowNodes

from content_agent.graph.routing import route_after_evaluation


def build_lesson_graph(
    nodes: LessonWorkflowNodes
):
    """
    Constructs and compiles the complete lesson-generation graph.
    """

    workflow = StateGraph(LessonGraphState)

    # -----------------------------------------
    # Register nodes
    # -----------------------------------------

    workflow.add_node(
        "initialize",
        nodes.initialize
    )

    workflow.add_node(
        "prepare_generation",
        nodes.prepare_generation
    )

    workflow.add_node(
        "generate_lesson",
        nodes.generate_and_save
    )

    workflow.add_node(
        "evaluate_lesson",
        nodes.evaluate_and_save
    )

    workflow.add_node(
        "process_memory",
        nodes.process_memory
    )

    workflow.add_node(
        "prepare_regeneration",
        nodes.prepare_regeneration
    )

    workflow.add_node(
        "approve_run",
        nodes.approve_run
    )

    workflow.add_node(
        "reject_run",
        nodes.reject_run
    )

    # -----------------------------------------
    # Define initial execution path
    # -----------------------------------------

    workflow.add_edge(
        START,
        "initialize"
    )

    workflow.add_edge(
        "initialize",
        "prepare_generation"
    )

    workflow.add_edge(
        "prepare_generation",
        "generate_lesson"
    )

    workflow.add_edge(
        "generate_lesson",
        "evaluate_lesson"
    )

    workflow.add_edge(
        "evaluate_lesson",
        "process_memory"
    )

    # -----------------------------------------
    # Conditional routing
    # -----------------------------------------

    workflow.add_conditional_edges(

        "process_memory",

        route_after_evaluation,

        {

            "approve": "approve_run",

            "retry": "prepare_regeneration",

            "reject": "reject_run"

        }

    )

    # -----------------------------------------
    # Regeneration loop
    # -----------------------------------------

    workflow.add_edge(
        "prepare_regeneration",
        "prepare_generation"
    )

    # -----------------------------------------
    # Terminal paths
    # -----------------------------------------

    workflow.add_edge(
        "approve_run",
        END
    )

    workflow.add_edge(
        "reject_run",
        END
    )

    # Compile the graph.
    return workflow.compile()