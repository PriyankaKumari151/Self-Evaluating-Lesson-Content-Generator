from pydantic import Field, model_validator

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import (
    EvaluationStatus,
    EvaluatorType
)


class EvaluationResult(AppBaseModel):
    """
    Evaluation result for one criterion.
    """

    criterion_id: int = Field(gt=0)

    criterion_key: NonEmptyStr

    criterion_name: NonEmptyStr

    status: EvaluationStatus

    evaluator_type: EvaluatorType

    evidence: list[NonEmptyStr] = Field(min_length=1)

    failure_reason: NonEmptyStr | None = None

    proposed_fix: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_failure_details(self):

        if self.status == EvaluationStatus.FAIL:

            if not self.failure_reason:
                raise ValueError(
                    "A failed criterion must contain "
                    "a failure reason."
                )

            if not self.proposed_fix:
                raise ValueError(
                    "A failed criterion must contain "
                    "a proposed fix."
                )

        return self


class EvaluationReport(AppBaseModel):
    """
    Combined report containing all criterion-wise results.
    """

    lesson_version_id: int | None = None

    attempt_number: int = Field(ge=1)

    results: list[EvaluationResult] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_unique_criteria(self):

        criterion_ids = [
            result.criterion_id
            for result in self.results
        ]

        if len(criterion_ids) != len(set(criterion_ids)):
            raise ValueError(
                "Duplicate criterion evaluations are not allowed."
            )

        return self

    @property
    def all_passed(self) -> bool:
        """
        Returns True only if every criterion passes.
        """

        return all(
            result.status == EvaluationStatus.PASS
            for result in self.results
        )

    @property
    def failed_results(self) -> list[EvaluationResult]:

        return [
            result
            for result in self.results
            if result.status == EvaluationStatus.FAIL
        ]

    @property
    def failed_criteria_count(self) -> int:

        return len(self.failed_results)


from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import EvaluationStatus


class LLMJudgeCriterionResult(AppBaseModel):
    """
    Semantic evaluation of one rubric criterion
    by the LLM judge.
    """

    criterion_key: NonEmptyStr = Field(
        description="Unique key of the rubric criterion."
    )

    status: EvaluationStatus = Field(
        description="PASS or FAIL based on the rubric."
    )

    evidence: list[NonEmptyStr] = Field(
        min_length=1,
        description="Evidence from the lesson supporting the verdict."
    )

    failure_reason: NonEmptyStr | None = None

    proposed_fix: NonEmptyStr | None = None

    @model_validator(mode="after")
    def validate_failure_details(self):

        if self.status == EvaluationStatus.FAIL:

            if not self.failure_reason:
                raise ValueError(
                    "A failed LLM judgment requires a failure reason."
                )

            if not self.proposed_fix:
                raise ValueError(
                    "A failed LLM judgment requires a proposed fix."
                )

        return self


class LLMJudgeReport(AppBaseModel):
    """
    Complete output produced by the LLM evaluator.
    """

    results: list[LLMJudgeCriterionResult] = Field(
        min_length=1
    )

    @model_validator(mode="after")
    def validate_unique_criteria(self):

        keys = [
            result.criterion_key
            for result in self.results
        ]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Duplicate criterion judgments are not allowed."
            )

        return self