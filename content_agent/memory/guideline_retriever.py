from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.models.evaluation import (
    EvaluationResult
)

from content_agent.models.enums import EvaluationStatus


class GuidelineRetriever:
    """
    Retrieves active learned guidelines for generation
    and regeneration prompts.
    """

    def __init__(
        self,
        repository: DatabaseRepository
    ):
        self.repository = repository

    def for_generation(self) -> list[dict]:
        """
        Retrieves all active guidelines for a fresh lesson.
        """

        return self.repository.get_active_guidelines()

    def for_regeneration(
        self,
        evaluation_results: list[EvaluationResult]
    ) -> list[dict]:
        """
        Retrieves guidelines only for criteria
        that failed in the current evaluation.
        """

        failed_criterion_ids = list({

            result.criterion_id

            for result in evaluation_results

            if result.status == EvaluationStatus.FAIL

        })

        if not failed_criterion_ids:
            return []

        return self.repository.get_active_guidelines(
            criterion_ids=failed_criterion_ids
        )