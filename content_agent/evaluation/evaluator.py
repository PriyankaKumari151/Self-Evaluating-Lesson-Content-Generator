from typing import Any

from pydantic import ValidationError

from content_agent.config import settings

from content_agent.llm.client import (
    create_structured_model
)

from content_agent.models.lesson import Lesson

from content_agent.models.rubric import RubricCriterion

from content_agent.models.evaluation import (
    EvaluationReport,
    EvaluationResult,
    LLMJudgeReport,
    LLMJudgeCriterionResult
)

from content_agent.models.enums import (
    EvaluationStatus,
    EvaluationMethod,
    EvaluatorType,
    PromptType
)

from content_agent.models.prompts import PromptVersion

from content_agent.prompts.evaluator import (
    build_evaluator_prompt
)

from content_agent.evaluation.rule_checks import (
    RuleBasedEvaluator,
    RuleCheckResult
)


class EvaluationError(Exception):
    """
    Raised when the evaluation process cannot be completed.
    """


class LessonEvaluator:
    """
    Hybrid evaluator combining LLM-based semantic judgment
    and deterministic Python checks.
    """

    def __init__(
        self,
        model: Any | None = None,
        rule_evaluator: RuleBasedEvaluator | None = None
    ):

        # Optional dependency injection for testing.
        self.model = model

        self.rule_evaluator = (
            rule_evaluator or RuleBasedEvaluator()
        )

    def _get_llm_judgment(
        self,
        prompt: str
    ) -> LLMJudgeReport:
        """
        Calls the LLM and obtains a structured judgment.
        """

        if self.model is None:

            structured_model = create_structured_model(
                schema=LLMJudgeReport,
                temperature=settings.evaluation_temperature
            )

        else:

            structured_model = self.model.with_structured_output(
                LLMJudgeReport,
                method=settings.structured_output_method,
                strict=False
            )

        try:

            result = structured_model.invoke(prompt)

            if isinstance(result, LLMJudgeReport):
                return result

            if isinstance(result, dict):
                return LLMJudgeReport.model_validate(result)

            raise EvaluationError(
                "LLM returned an unexpected evaluation format."
            )

        except ValidationError as exc:

            raise EvaluationError(
                "LLM evaluation output failed schema validation."
            ) from exc

        except EvaluationError:

            raise

        except Exception as exc:

            raise EvaluationError(
                f"LLM evaluation failed: {exc}"
            ) from exc

    def evaluate(
        self,
        lesson: Lesson,
        rubric_criteria: list[RubricCriterion],
        evaluator_prompt: PromptVersion,
        attempt_number: int,
        reference_material: str = "",
        lesson_version_id: int | None = None
    ) -> EvaluationReport:
        """
        Evaluates a complete lesson against active rubric criteria.
        """

        if evaluator_prompt.prompt_type != PromptType.EVALUATOR:

            raise ValueError(
                "Expected an EVALUATOR prompt."
            )

        active_criteria = [
            criterion
            for criterion in rubric_criteria
            if criterion.is_active
        ]

        if not active_criteria:

            raise ValueError(
                "No active rubric criteria are available."
            )

        criterion_ids = [
            criterion.id
            for criterion in active_criteria
        ]

        if None in criterion_ids or len(criterion_ids) != len(
            set(criterion_ids)
        ):

            raise ValueError(
                "Every active rubric criterion must have "
                "a unique database ID."
            )

        # ---------------------------------------------
        # 1. Identify criteria requiring LLM evaluation
        # ---------------------------------------------

        llm_criteria = [

            criterion

            for criterion in active_criteria

            if criterion.evaluation_method in (
                EvaluationMethod.LLM,
                EvaluationMethod.HYBRID
            )

        ]

        llm_results = {}

        if llm_criteria:

            prompt = build_evaluator_prompt(

                standard_prompt=evaluator_prompt,

                lesson=lesson,

                rubric_criteria=llm_criteria,

                reference_material=reference_material

            )

            judge_report = self._get_llm_judgment(
                prompt
            )

            # Map results using criterion_key.
            llm_results = {
                result.criterion_key: result
                for result in judge_report.results
            }

            expected_keys = {
                criterion.criterion_key
                for criterion in llm_criteria
            }

            received_keys = set(llm_results.keys())

            if expected_keys != received_keys:

                missing = expected_keys - received_keys

                unexpected = received_keys - expected_keys

                raise EvaluationError(
                    f"Invalid LLM evaluation coverage. "
                    f"Missing: {missing}. "
                    f"Unexpected: {unexpected}."
                )

        # ---------------------------------------------
        # 2. Run deterministic checks
        # ---------------------------------------------

        rule_results = {}

        for criterion in active_criteria:

            if criterion.evaluation_method in (
                EvaluationMethod.HYBRID,
                EvaluationMethod.RULE_BASED
            ):

                rule_result = self.rule_evaluator.evaluate(
                    lesson,
                    criterion
                )

                rule_results[
                    criterion.criterion_key
                ] = rule_result

        # ---------------------------------------------
        # 3. Combine all evaluation results
        # ---------------------------------------------

        final_results = []

        for criterion in active_criteria:

            key = criterion.criterion_key

            method = criterion.evaluation_method

            llm_result = llm_results.get(key)

            rule_result = rule_results.get(key)

            if method == EvaluationMethod.LLM:

                final_result = self._build_llm_result(
                    criterion,
                    llm_result
                )

            elif method == EvaluationMethod.RULE_BASED:

                final_result = self._build_rule_result(
                    criterion,
                    rule_result
                )

            elif method == EvaluationMethod.HYBRID:

                final_result = self._build_hybrid_result(
                    criterion,
                    llm_result,
                    rule_result
                )

            else:

                raise EvaluationError(
                    f"Unsupported evaluation method: {method}"
                )

            final_results.append(final_result)

        # ---------------------------------------------
        # 4. Build combined evaluation report
        # ---------------------------------------------

        return EvaluationReport(

            lesson_version_id=lesson_version_id,

            attempt_number=attempt_number,

            results=final_results

        )

    @staticmethod
    def _build_llm_result(
        criterion: RubricCriterion,
        result: LLMJudgeCriterionResult
    ) -> EvaluationResult:

        return EvaluationResult(

            criterion_id=criterion.id,

            criterion_key=criterion.criterion_key,

            criterion_name=criterion.criterion_name,

            status=result.status,

            evaluator_type=EvaluatorType.LLM,

            evidence=result.evidence,

            failure_reason=result.failure_reason,

            proposed_fix=result.proposed_fix

        )

    @staticmethod
    def _build_rule_result(
        criterion: RubricCriterion,
        result: RuleCheckResult
    ) -> EvaluationResult:

        return EvaluationResult(

            criterion_id=criterion.id,

            criterion_key=criterion.criterion_key,

            criterion_name=criterion.criterion_name,

            status=result.status,

            evaluator_type=EvaluatorType.RULE_BASED,

            evidence=result.evidence,

            failure_reason=result.failure_reason,

            proposed_fix=result.proposed_fix

        )

    @staticmethod
    def _build_hybrid_result(
        criterion: RubricCriterion,
        llm_result: LLMJudgeCriterionResult,
        rule_result: RuleCheckResult
    ) -> EvaluationResult:
        """
        A hybrid criterion passes only when BOTH
        its LLM and rule-based evaluations pass.
        """

        passed = (

            llm_result.status == EvaluationStatus.PASS

            and

            rule_result.status == EvaluationStatus.PASS

        )

        evidence = (
            llm_result.evidence
            + rule_result.evidence
        )

        failure_reasons = []

        proposed_fixes = []

        if llm_result.status == EvaluationStatus.FAIL:

            failure_reasons.append(
                llm_result.failure_reason
            )

            proposed_fixes.append(
                llm_result.proposed_fix
            )

        if rule_result.status == EvaluationStatus.FAIL:

            failure_reasons.append(
                rule_result.failure_reason
            )

            proposed_fixes.append(
                rule_result.proposed_fix
            )

        return EvaluationResult(

            criterion_id=criterion.id,

            criterion_key=criterion.criterion_key,

            criterion_name=criterion.criterion_name,

            status=(
                EvaluationStatus.PASS
                if passed
                else EvaluationStatus.FAIL
            ),

            evaluator_type=EvaluatorType.HYBRID,

            evidence=evidence,

            failure_reason=(
                " ".join(failure_reasons)
                if failure_reasons else None
            ),

            proposed_fix=(
                " ".join(proposed_fixes)
                if proposed_fixes else None
            )

        )