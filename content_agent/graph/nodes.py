from pathlib import Path
from typing import Any

from content_agent.database.repository import (
    DatabaseRepository
)

from content_agent.models.run import LessonRequest

from content_agent.models.enums import (
    PromptType,
    RunStatus,
    EvaluationStatus
)

from content_agent.models.memory import (
    MemoryProcessingResult
)

from content_agent.models.evaluation import (
    EvaluationReport
)

from content_agent.models.lesson import (
    LearnerProfile
)

from content_agent.models.prompts import PromptVersion

from content_agent.llm.generator import LessonGenerator

from content_agent.evaluation.evaluator import LessonEvaluator

from content_agent.memory.pattern_manager import PatternManager

from content_agent.memory.guideline_retriever import (
    GuidelineRetriever
)

from content_agent.prompts.generator import (
    build_generator_prompt
)

from content_agent.prompts.evaluator import (
    build_evaluator_prompt
)

from content_agent.prompts.regeneration import (
    build_regeneration_prompt
)

from content_agent.prompts.template import (
    get_memory_pattern_ids
)

from content_agent.graph.state import LessonGraphState


class LessonWorkflowNodes:
    """
    Contains all executable nodes of the LangGraph workflow.

    Dependencies are injected so individual nodes can be
    tested without making real LLM API calls.
    """

    def __init__(
        self,
        repository: DatabaseRepository,
        generator: Any | None = None,
        evaluator: Any | None = None,
        pattern_manager: Any | None = None
    ):

        self.repository = repository

        self.generator = (
            generator or LessonGenerator()
        )

        self.evaluator = (
            evaluator or LessonEvaluator()
        )

        self.pattern_manager = (
            pattern_manager or PatternManager(repository)
        )

        self.guideline_retriever = GuidelineRetriever(
            repository
        )

    # =========================================
    # NODE 1: INITIALIZE
    # =========================================

    def initialize(
        self,
        state: LessonGraphState
    ) -> dict:

        request: LessonRequest = state["request"]

        print("\n[Graph] Initializing workflow...")

        # Create the run before any LLM execution.
        run_id = self.repository.create_run(request)

        # Retrieve the rubric.
        rubric = self.repository.get_rubric_criteria()

        if not rubric:
            raise ValueError(
                "No active rubric criteria found."
            )

        # Retrieve all active prompts once.
        # This freezes prompt versions for this run.

        generator_prompt = self.repository.get_active_prompt(
            PromptType.GENERATOR
        )

        evaluator_prompt = self.repository.get_active_prompt(
            PromptType.EVALUATOR
        )

        regeneration_prompt = self.repository.get_active_prompt(
            PromptType.REGENERATION
        )

        if not all([
            generator_prompt,
            evaluator_prompt,
            regeneration_prompt
        ]):

            raise ValueError(
                "One or more active prompt versions are missing."
            )

        print(f"[Graph] Run created: {run_id}")

        return {

            "run_id": run_id,

            "topic": request.topic,

            "learner_profile": request.learner_profile,

            "max_retries": request.max_retries,

            "retry_count": 0,

            "attempt_number": 1,

            "rubric_criteria": rubric,

            "generator_prompt": generator_prompt,

            "evaluator_prompt": evaluator_prompt,

            "regeneration_prompt": regeneration_prompt,

            "reference_material": state.get(
                "reference_material", ""
            ),

            "final_status": "IN_PROGRESS",

            "rejection_log_ids": [],

            "memory_results": [],

            "attempt_history": [],

            "warnings": []

        }

    # =========================================
    # NODE 2: PREPARE GENERATION PROMPT
    # =========================================

    def prepare_generation(
        self,
        state: LessonGraphState
    ) -> dict:

        retry_count = state["retry_count"]

        attempt_number = retry_count + 1

        print(
            f"\n[Graph] Preparing generation "
            f"for attempt {attempt_number}..."
        )

        # Retrieve active learned guidelines.

        if attempt_number == 1:

            guidelines = (
                self.guideline_retriever.for_generation()
            )

        else:

            previous_report = state["evaluation_report"]

            guidelines = (
                self.guideline_retriever.for_regeneration(
                    previous_report.results
                )
            )

        memory_pattern_ids = get_memory_pattern_ids(
            guidelines
        )

        # Reuse the prompts frozen during initialization.
        generator_prompt: PromptVersion = state[
            "generator_prompt"
        ]

        regeneration_prompt: PromptVersion | None = (
            state["regeneration_prompt"]
            if attempt_number > 1
            else None
        )

        learner_profile = state["learner_profile"]

        # Build standard generator instructions.

        base_prompt = build_generator_prompt(

            standard_prompt=generator_prompt,

            topic=state["topic"],

            learner_profile=learner_profile,

            reference_material=state["reference_material"],

            learned_guidelines=guidelines

        )

        # On retries, append current-run feedback.

        if attempt_number > 1:

            previous_lesson = state["current_lesson"]

            evaluation_report: EvaluationReport = (
                state["evaluation_report"]
            )

            final_prompt = build_regeneration_prompt(

                standard_prompt=regeneration_prompt,

                topic=state["topic"],

                learner_profile=learner_profile,

                previous_lesson=previous_lesson,

                evaluation_results=evaluation_report.results,

                learned_guidelines=guidelines,

                base_generation_prompt=base_prompt

            )

        else:

            final_prompt = base_prompt

        print(
            f"[Graph] Retrieved {len(guidelines)} "
            f"active learned guidelines."
        )

        return {

            "attempt_number": attempt_number,

            "assembled_prompt": final_prompt,

            "current_memory_pattern_ids": memory_pattern_ids,

            "generator_prompt_id": generator_prompt.id,

            "regeneration_prompt_id": (
                regeneration_prompt.id
                if regeneration_prompt
                else None
            )

        }

    # =========================================
    # NODE 3: GENERATE AND SAVE LESSON
    # =========================================

    def generate_and_save(
        self,
        state: LessonGraphState
    ) -> dict:

        attempt_number = state["attempt_number"]

        print(
            f"\n[Graph] Generating lesson V{attempt_number}..."
        )

        # Generate structured lesson.
        lesson = self.generator.generate(
            state["assembled_prompt"]
        )

        # Persist the lesson.
        lesson_version_id = (
            self.repository.create_lesson_version(

                run_id=state["run_id"],

                lesson=lesson,

                attempt_number=attempt_number,

                generator_prompt_id=state["generator_prompt_id"],

                regeneration_prompt_id=state.get(
                    "regeneration_prompt_id"
                ),

                assembled_prompt=state["assembled_prompt"],

                memory_pattern_ids=state[
                    "current_memory_pattern_ids"
                ]

            )
        )

        # If this lesson was regenerated, link the
        # previous rejection to the new lesson version.

        pending_rejection_id = state.get(
            "pending_rejection_log_id"
        )

        if pending_rejection_id is not None:

            self.repository.link_rejection_to_next_version(

                rejection_log_id=pending_rejection_id,

                next_lesson_version_id=lesson_version_id,

                changes_made=(
                    "A new lesson version was generated "
                    "using the previous evaluation feedback."
                )

            )

        print(
            f"[Graph] Lesson version saved: "
            f"{lesson_version_id}"
        )

        return {

        "current_lesson": lesson,

        "current_lesson_version_id": lesson_version_id,

        "pending_rejection_log_id": None

        }

    # =========================================
    # NODE 4: EVALUATE AND SAVE
    # =========================================

    def evaluate_and_save(
        self,
        state: LessonGraphState
    ) -> dict:

        print("\n[Graph] Evaluating generated lesson...")

        evaluation_report = self.evaluator.evaluate(

            lesson=state["current_lesson"],

            rubric_criteria=state["rubric_criteria"],

            evaluator_prompt=state["evaluator_prompt"],

            attempt_number=state["attempt_number"],

            reference_material=state["reference_material"],

            lesson_version_id=state[
                "current_lesson_version_id"
            ]

        )

        # Persist all criterion-wise results.
        evaluation_ids = (
            self.repository.save_evaluation_report(

                lesson_version_id=state[
                    "current_lesson_version_id"
                ],

                report=evaluation_report,

                evaluator_prompt_id=state[
                    "evaluator_prompt"
                ].id

            )
        )

        history = state.get("attempt_history", [])

        history.append({

            "attempt_number": state["attempt_number"],

            "lesson_version_id": state[
                "current_lesson_version_id"
            ],

            "lesson_title": state["current_lesson"].title,

            "passed": evaluation_report.all_passed,

            "failed_criteria": [
                result.criterion_key
                for result in evaluation_report.failed_results
            ]

        })

        print(
            f"[Graph] Evaluation completed. "
            f"Failed criteria: "
            f"{evaluation_report.failed_criteria_count}"
        )

        return {

            "evaluation_report": evaluation_report,

            "evaluation_ids": evaluation_ids,

            "attempt_history": history

        }

    # =========================================
    # NODE 5: PROCESS LEARNING MEMORY
    # =========================================

    def process_memory(
        self,
        state: LessonGraphState
    ) -> dict:

        print("\n[Graph] Processing evaluation failures...")

        report: EvaluationReport = state[
            "evaluation_report"
        ]

        if report.all_passed:

            print("[Graph] No failures to learn from.")

            return {
            "memory_results": state.get("memory_results", [])
            }

        results = []

        warnings = list(
            state.get("warnings", [])
        )

        criteria_map = {
            criterion.id: criterion
            for criterion in state["rubric_criteria"]
        }

        # Evaluation IDs are returned in the same insertion
        # order as report.results by the repository.

        for result, evaluation_id in zip(
            report.results,
            state["evaluation_ids"]
        ):

            if result.status != EvaluationStatus.FAIL:
                continue

            criterion = criteria_map.get(
                result.criterion_id
            )

            if criterion is None:

                warnings.append(
                    "Criterion missing while processing "
                    f"evaluation {evaluation_id}."
                )

                continue

            try:

                memory_result = (
                    self.pattern_manager.process_failure(

                        evaluation_id=evaluation_id,

                        result=result,

                        criterion=criterion

                    )
                )

                results.append(memory_result)

                print(
                    f"[Graph] Memory pattern processed: "
                    f"{memory_result.message}"
                )

            except Exception as exc:

                # Memory processing should never decide
                # whether the lesson itself passes.

                warning = (
                    f"Memory processing failed for "
                    f"evaluation {evaluation_id}: {exc}"
                )

                warnings.append(warning)

                print(f"[Graph Warning] {warning}")

        return {

            "memory_results": (
                state.get("memory_results", []) + results
            ),

            "warnings": warnings

        }

    # =========================================
    # NODE 6: PREPARE REGENERATION
    # =========================================

    def prepare_regeneration(
        self,
        state: LessonGraphState
    ) -> dict:

        print("\n[Graph] Preparing regeneration...")

        report: EvaluationReport = state[
            "evaluation_report"
        ]

        failed_results = report.failed_results

        if not failed_results:
            raise ValueError(
                "Regeneration requested without failed criteria."
            )

        regeneration_prompt: PromptVersion = state[
            "regeneration_prompt"
        ]

        failure_summary_parts = []

        feedback_parts = []

        for result in failed_results:

            failure_summary_parts.append(
                f"{result.criterion_name}: "
                f"{result.failure_reason}"
            )

            feedback_parts.append(

                f"Criterion: {result.criterion_name}\n"

                f"Evidence: {'; '.join(result.evidence)}\n"

                f"Failure: {result.failure_reason}\n"

                f"Required correction: {result.proposed_fix}"

            )

        failure_summary = "\n".join(
            failure_summary_parts
        )

        feedback = "\n\n".join(
            feedback_parts
        )

        # Create rejection record for the failed version.
        rejection_log_id = (
            self.repository.create_rejection_log(

                lesson_version_id=state[
                    "current_lesson_version_id"
                ],

                failure_summary=failure_summary,

                feedback_sent=feedback,

                regeneration_prompt_id=regeneration_prompt.id

            )
        )

        # Only after the rejection is recorded do we
        # consume one regeneration attempt.

        retry_count = (
            self.repository.increment_retry_count(
                state["run_id"]
            )
        )

        rejection_ids = (
            state.get("rejection_log_ids", [])
            + [rejection_log_id]
        )

        print(
            f"[Graph] Retry count updated: "
            f"{retry_count}/{state['max_retries']}"
        )

        return {

            "retry_count": retry_count,

            "pending_rejection_log_id": rejection_log_id,

            "rejection_log_ids": rejection_ids

        }

    # =========================================
    # NODE 7: APPROVE RUN
    # =========================================

    def approve_run(
        self,
        state: LessonGraphState
    ) -> dict:

        print("\n[Graph] All mandatory criteria passed.")

        self.repository.update_run_status(

            run_id=state["run_id"],

            status=RunStatus.APPROVED

        )

        print("[Graph] Run approved.")

        return {

            "final_status": RunStatus.APPROVED.value

        }

    # =========================================
    # NODE 8: REJECT RUN
    # =========================================

    def reject_run(
        self,
        state: LessonGraphState
    ) -> dict:

        print("\n[Graph] Retry limit reached.")

        report: EvaluationReport = state[
            "evaluation_report"
        ]

        failure_summary = "\n".join(

            f"{result.criterion_name}: "
            f"{result.failure_reason}"

            for result in report.failed_results

        )

        # Save the final rejection.
        # No regeneration is initiated, so these fields
        # are intentionally NULL.

        rejection_log_id = (
            self.repository.create_rejection_log(

                lesson_version_id=state[
                    "current_lesson_version_id"
                ],

                failure_summary=failure_summary,

                feedback_sent=None,

                regeneration_prompt_id=None

            )
        )

        self.repository.update_run_status(

            run_id=state["run_id"],

            status=RunStatus.REJECTED

        )

        return {

            "final_status": RunStatus.REJECTED.value,

            "rejection_log_ids": (
                state.get("rejection_log_ids", [])
                + [rejection_log_id]
            )

        }