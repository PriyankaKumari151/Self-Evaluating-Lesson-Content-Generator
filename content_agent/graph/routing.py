from content_agent.graph.state import LessonGraphState


def route_after_evaluation(
    state: LessonGraphState
) -> str:
    """
    Decides whether to approve, regenerate or reject.

    Returns:
        approve: Every mandatory criterion passed.
        retry: At least one criterion failed and retries remain.
        reject: Criteria failed and retry limit was reached.
    """

    report = state["evaluation_report"]

    # First priority: quality approval.
    if report.all_passed:
        return "approve"

    # Second priority: check retry availability.
    retry_count = state["retry_count"]

    max_retries = state["max_retries"]

    if retry_count < max_retries:
        return "retry"

    # No more regeneration attempts.
    return "reject"