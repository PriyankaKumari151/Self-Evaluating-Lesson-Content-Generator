from pydantic import Field

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import EvaluationStatus

from content_agent.models.lesson import Lesson

from content_agent.models.rubric import RubricCriterion


class RuleCheckResult(AppBaseModel):
    """
    Output of a deterministic rule-based check.
    """

    criterion_id: int

    criterion_key: NonEmptyStr

    status: EvaluationStatus

    evidence: list[NonEmptyStr] = Field(min_length=1)

    failure_reason: NonEmptyStr | None = None

    proposed_fix: NonEmptyStr | None = None


class RuleBasedEvaluator:
    """
    Evaluates objective structural requirements
    of a generated lesson.
    """

    def evaluate(
        self,
        lesson: Lesson,
        criterion: RubricCriterion
    ) -> RuleCheckResult:

        if criterion.criterion_key == "PRACTICAL_EXAMPLES":

            return self._check_practical_examples(
                lesson,
                criterion
            )

        if criterion.criterion_key == "KEY_POINT_COVERAGE":

            return self._check_key_point_coverage(
                lesson,
                criterion
            )

        raise NotImplementedError(
            f"No deterministic rule is defined for "
            f"{criterion.criterion_key}."
        )

    def _check_practical_examples(
        self,
        lesson: Lesson,
        criterion: RubricCriterion
    ) -> RuleCheckResult:

        example_count = len(
            lesson.practical_examples
        )

        if example_count >= 1:

            return RuleCheckResult(

                criterion_id=criterion.id,

                criterion_key=criterion.criterion_key,

                status=EvaluationStatus.PASS,

                evidence=[
                    f"Found {example_count} practical example(s).",
                    "Example sections contain the required structured fields."
                ]

            )

        return RuleCheckResult(

            criterion_id=criterion.id,

            criterion_key=criterion.criterion_key,

            status=EvaluationStatus.FAIL,

            evidence=[
                "The practical_examples section is empty."
            ],

            failure_reason=(
                "The lesson does not contain any practical examples."
            ),

            proposed_fix=(
                "Add at least one relatable practical example "
                "that demonstrates the concept."
            )

        )

    def _check_key_point_coverage(
        self,
        lesson: Lesson,
        criterion: RubricCriterion
    ) -> RuleCheckResult:

        missing_sections = []

        if not lesson.introduction.strip():
            missing_sections.append("Introduction")

        if not lesson.why_it_matters.strip():
            missing_sections.append("Why it matters")

        if not lesson.how_it_works:
            missing_sections.append("How it works")

        if not missing_sections:

            return RuleCheckResult(

                criterion_id=criterion.id,

                criterion_key=criterion.criterion_key,

                status=EvaluationStatus.PASS,

                evidence=[
                    "Introduction section is present.",
                    "Why it matters section is present.",
                    "How it works contains at least one step."
                ]

            )

        return RuleCheckResult(

            criterion_id=criterion.id,

            criterion_key=criterion.criterion_key,

            status=EvaluationStatus.FAIL,

            evidence=[
                f"Missing required sections: "
                f"{', '.join(missing_sections)}."
            ],

            failure_reason=(
                "The lesson does not contain all required "
                "foundational sections."
            ),

            proposed_fix=(
                "Add the missing sections explaining what "
                "the topic is, why it matters and how it works."
            )

        )