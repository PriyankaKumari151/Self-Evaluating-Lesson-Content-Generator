from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.models.evaluation import (
    EvaluationResult
)

from content_agent.models.rubric import (
    RubricCriterion
)

from content_agent.models.memory import (
    MemoryProcessingResult
)

from content_agent.models.enums import (
    EvaluationStatus,
    FailurePatternStatus
)

from content_agent.memory.failure_classifier import (
    FailureClassifier
)

from content_agent.memory.guideline_validator import (
    GuidelineValidator
)


class PatternManager:
    """
    Orchestrates the complete failure-pattern learning process.

    Responsibilities:

    1. Receive an evaluation failure.
    2. Classify the failure into a canonical pattern.
    3. Save or update its occurrence counts.
    4. Check distinct-run recurrence.
    5. Validate the proposed guideline.
    6. Activate an approved guideline.
    """

    def __init__(
        self,
        repository: DatabaseRepository,
        classifier: FailureClassifier | None = None,
        validator: GuidelineValidator | None = None,
        minimum_distinct_runs: int = 2,
        minimum_confidence: float = 0.75
    ):

        if minimum_distinct_runs < 1:
            raise ValueError(
                "Minimum distinct runs must be positive."
            )

        if not 0 <= minimum_confidence <= 1:
            raise ValueError(
                "Minimum confidence must be between 0 and 1."
            )

        self.repository = repository

        self.classifier = (
            classifier or FailureClassifier()
        )

        self.validator = (
            validator or GuidelineValidator()
        )

        self.minimum_distinct_runs = minimum_distinct_runs

        self.minimum_confidence = minimum_confidence

    def process_failure(
        self,
        evaluation_id: int,
        result: EvaluationResult,
        criterion: RubricCriterion
    ) -> MemoryProcessingResult:
        """
        Processes one failed evaluation and updates learning memory.
        """

        if result.status != EvaluationStatus.FAIL:

            raise ValueError(
                "Only failed evaluations can be processed."
            )

        if result.criterion_id != criterion.id:

            raise ValueError(
                "Evaluation criterion does not match rubric."
            )

        # -----------------------------------------
        # 1. Retrieve existing patterns
        # -----------------------------------------

        existing_patterns = (
            self.repository.get_failure_patterns(
                criterion_id=criterion.id
            )
        )

        # -----------------------------------------
        # 2. Classify the failure
        # -----------------------------------------

        candidate = self.classifier.classify(
            result=result,
            criterion=criterion,
            existing_patterns=existing_patterns
        )

        # Do not store uncertain classifications.
        if candidate.confidence < self.minimum_confidence:

            return MemoryProcessingResult(

                processed=False,

                evaluation_id=evaluation_id,

                message=(
                    "Failure classification confidence "
                    "was below the configured threshold."
                )

            )

        # -----------------------------------------
        # 3. Record failure pattern
        # -----------------------------------------

        pattern = self.repository.record_failure_pattern(
            evaluation_id=evaluation_id,
            candidate=candidate
        )

        # Already active patterns do not need revalidation.
        if pattern.status == FailurePatternStatus.ACTIVE:

            return MemoryProcessingResult(

                processed=True,

                evaluation_id=evaluation_id,

                failure_pattern_id=pattern.id,

                pattern_key=pattern.pattern_key,

                occurrence_count=pattern.occurrence_count,

                distinct_run_count=pattern.distinct_run_count,

                guideline_activated=True,

                message=(
                    "Existing active failure pattern updated."
                )

            )

        # -----------------------------------------
        # 4. Check recurrence threshold
        # -----------------------------------------

        if (
            pattern.distinct_run_count
            < self.minimum_distinct_runs
        ):

            return MemoryProcessingResult(

                processed=True,

                evaluation_id=evaluation_id,

                failure_pattern_id=pattern.id,

                pattern_key=pattern.pattern_key,

                occurrence_count=pattern.occurrence_count,

                distinct_run_count=pattern.distinct_run_count,

                guideline_activated=False,

                message=(
                    "Pattern recorded, but it has not yet "
                    "occurred in enough distinct runs."
                )

            )

        # -----------------------------------------
        # 5. Retrieve historical evidence
        # -----------------------------------------

        historical_evidence = (
            self.repository.get_failure_pattern_evidence(
                pattern.id
            )
        )

        # -----------------------------------------
        # 6. Validate the learned guideline
        # -----------------------------------------

        validation = self.validator.validate(

            pattern=pattern,

            criterion=criterion,

            historical_evidence=historical_evidence

        )

        # -----------------------------------------
        # 7. Persist validation and activate if approved
        # -----------------------------------------

        self.repository.record_failure_pattern_validation(

            pattern_id=pattern.id,

            approved=validation.approved,

            reason=validation.reason,

            revised_guideline=validation.revised_guideline,

            minimum_distinct_runs=self.minimum_distinct_runs,

            validator_version=(
                self.validator.VALIDATOR_VERSION
            )

        )

        # Retrieve updated status.
        updated_patterns = (
            self.repository.get_failure_patterns(
                criterion_id=criterion.id
            )
        )

        updated_pattern = next(

            pattern_record

            for pattern_record in updated_patterns

            if pattern_record.id == pattern.id

        )

        return MemoryProcessingResult(

            processed=True,

            evaluation_id=evaluation_id,

            failure_pattern_id=updated_pattern.id,

            pattern_key=updated_pattern.pattern_key,

            occurrence_count=updated_pattern.occurrence_count,

            distinct_run_count=updated_pattern.distinct_run_count,

            guideline_activated=(
                updated_pattern.status
                == FailurePatternStatus.ACTIVE
            ),

            message=validation.reason

        )