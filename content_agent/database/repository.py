import json
import sqlite3

from pathlib import Path

from content_agent.database.connection import get_connection

from content_agent.models.enums import (
    RunStatus,
    EvaluationStatus,
    EvaluatorType,
    PromptType,
    PromptStatus,
    FailurePatternStatus
)

from content_agent.models.run import (
    LessonRequest,
    RunRecord,
    LessonVersionRecord,
    RejectionLogRecord
)

from content_agent.models.lesson import Lesson

from content_agent.models.evaluation import (
    EvaluationReport,
    EvaluationResult
)

from content_agent.models.memory import (
    FailurePattern,
    FailurePatternCandidate
)

from content_agent.models.prompts import PromptVersion

from content_agent.models.rubric import RubricCriterion


class DatabaseRepository:
    """
    Encapsulates all database operations.

    Every method manages its own database connection
    and returns validated Python models where applicable.
    """

    def __init__(
        self,
        db_path: str | Path | None = None
    ):
        self.db_path = Path(db_path) if db_path else None

    def create_run(self, request: LessonRequest) -> int:
        """
        Creates a new workflow execution.

        Returns the generated run ID.
        """

        with get_connection(self.db_path) as connection:

            cursor = connection.execute(
                """
                INSERT INTO runs (
                    topic,
                    learner_profile_json,
                    max_retries,
                    retry_count,
                    status
                )
                VALUES (?, ?, ?, 0, ?)
                """,
                (
                    request.topic,
                    request.learner_profile.model_dump_json(),
                    request.max_retries,
                    RunStatus.IN_PROGRESS.value
                )
            )

            return cursor.lastrowid

    def get_run(self, run_id: int) -> RunRecord | None:
        """
        Retrieves a run and converts it into a RunRecord.
        """

        with get_connection(self.db_path) as connection:

            row = connection.execute(
                """
                SELECT *
                FROM runs
                WHERE id = ?
                """,
                (run_id,)
            ).fetchone()

        if row is None:
            return None

        data = dict(row)

        profile = json.loads(
            data.pop("learner_profile_json")
        )

        data["learner_profile"] = profile

        return RunRecord.model_validate(data)

    def increment_retry_count(self, run_id: int) -> int:
        """
        Increments the retry count if regeneration is allowed.

        Returns the updated retry count.
        """

        with get_connection(self.db_path) as connection:

            cursor = connection.execute(
                """
                UPDATE runs

                SET retry_count = retry_count + 1

                WHERE id = ?
                  AND status = 'IN_PROGRESS'
                  AND retry_count < max_retries
                """,
                (run_id,)
            )

            if cursor.rowcount == 0:

                row = connection.execute(
                    """
                    SELECT *
                    FROM runs
                    WHERE id = ?
                    """,
                    (run_id,)
                ).fetchone()

                if row is None:
                    raise ValueError(
                        f"Run {run_id} does not exist."
                    )

                raise ValueError(
                    "Retry limit reached or run is not in progress."
                )

            row = connection.execute(
                """
                SELECT retry_count
                FROM runs
                WHERE id = ?
                """,
                (run_id,)
            ).fetchone()

            return row["retry_count"]

    def update_run_status(
        self,
        run_id: int,
        status: RunStatus
    ) -> None:
        """
        Updates the final status of a run.

        An approved run must have a latest lesson version
        for which every active mandatory criterion passed.

        A rejected run must have exhausted its retry allowance.
        """

        if status == RunStatus.IN_PROGRESS:
            raise ValueError(
                "Use this method only for terminal run statuses."
            )

        with get_connection(self.db_path) as connection:

            run = connection.execute(
                """
                SELECT *
                FROM runs
                WHERE id = ?
                """,
                (run_id,)
            ).fetchone()

            if run is None:
                raise ValueError(
                    f"Run {run_id} does not exist."
                )

            if run["status"] != RunStatus.IN_PROGRESS.value:

                raise ValueError(
                    "A completed run cannot change its final status."
                )

            latest_version = connection.execute(
                """
                SELECT id
                FROM lesson_versions
                WHERE run_id = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                (run_id,)
            ).fetchone()

            if latest_version is None:
                raise ValueError(
                    "Cannot complete a run without a generated lesson."
                )

            if status == RunStatus.APPROVED:

                invalid_evaluation = connection.execute(
                    """
                    SELECT rc.id

                    FROM rubric_criteria rc

                    LEFT JOIN evaluations e
                        ON e.criterion_id = rc.id
                        AND e.lesson_version_id = ?

                    WHERE rc.is_active = 1
                      AND rc.is_mandatory = 1
                      AND (
                          e.id IS NULL
                          OR e.status != 'PASS'
                      )

                    LIMIT 1
                    """,
                    (latest_version["id"],)
                ).fetchone()

                if invalid_evaluation:

                    raise ValueError(
                        "Cannot approve run: "
                        "some mandatory criteria are missing or failed."
                    )

            if status == RunStatus.REJECTED:

                if run["retry_count"] < run["max_retries"]:

                    raise ValueError(
                        "Cannot reject run before exhausting retries."
                    )

            connection.execute(
                """
                UPDATE runs

                SET status = ?,
                    completed_at = strftime(
                        '%Y-%m-%dT%H:%M:%fZ',
                        'now'
                    )

                WHERE id = ?
                """,
                (status.value, run_id)
            )

    def get_active_prompt(
        self,
        prompt_type: PromptType
    ) -> PromptVersion | None:
        """
        Retrieves the active prompt for a given prompt type.
        """

        with get_connection(self.db_path) as connection:

            row = connection.execute(
                """
                SELECT *
                FROM prompt_versions

                WHERE prompt_type = ?
                  AND status = 'ACTIVE'
                """,
                (prompt_type.value,)
            ).fetchone()

        if row is None:
            return None

        return PromptVersion.model_validate(dict(row))

    def create_prompt_version(
        self,
        prompt: PromptVersion
    ) -> int:
        """
        Creates a new prompt version.

        New versions should normally be created as DRAFT.
        """

        if prompt.status != PromptStatus.DRAFT:
            raise ValueError(
                "New prompt versions must initially be DRAFT."
            )

        with get_connection(self.db_path) as connection:

            cursor = connection.execute(
                """
                INSERT INTO prompt_versions (
                    prompt_type,
                    version,
                    prompt_content,
                    change_summary,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prompt.prompt_type.value,
                    prompt.version,
                    prompt.prompt_content,
                    prompt.change_summary,
                    PromptStatus.DRAFT.value
                )
            )

            return cursor.lastrowid

    def activate_prompt_version(
        self,
        prompt_id: int
    ) -> None:
        """
        Activates a prompt version.

        The previously active version of the same type
        is retired in the same database transaction.
        """

        with get_connection(self.db_path) as connection:

            target = connection.execute(
                """
                SELECT *
                FROM prompt_versions
                WHERE id = ?
                """,
                (prompt_id,)
            ).fetchone()

            if target is None:
                raise ValueError(
                    f"Prompt version {prompt_id} does not exist."
                )

            if target["status"] == PromptStatus.ACTIVE.value:
                return

            prompt_type = target["prompt_type"]

            # Retire the currently active version.
            connection.execute(
                """
                UPDATE prompt_versions

                SET status = 'RETIRED'

                WHERE prompt_type = ?
                  AND status = 'ACTIVE'
                """,
                (prompt_type,)
            )

            # Activate the selected version.
            connection.execute(
                """
                UPDATE prompt_versions

                SET status = 'ACTIVE'

                WHERE id = ?
                """,
                (prompt_id,)
            )

    def create_lesson_version(
        self,
        run_id: int,
        lesson: Lesson,
        attempt_number: int,
        generator_prompt_id: int,
        regeneration_prompt_id: int | None = None,
        assembled_prompt: str | None = None,
        memory_pattern_ids: list[int] | None = None
    ) -> int:
        """
        Stores one generated lesson version.
        """

        if attempt_number < 1:
            raise ValueError(
                "Attempt number must be at least 1."
            )

        if attempt_number == 1 and regeneration_prompt_id is not None:
            raise ValueError(
                "Initial generation cannot have a regeneration prompt."
            )

        if attempt_number > 1 and regeneration_prompt_id is None:
            raise ValueError(
                "Regenerated lessons must reference a regeneration prompt."
            )

        pattern_ids = memory_pattern_ids or []

        if any(pattern_id <= 0 for pattern_id in pattern_ids):
            raise ValueError(
                "Memory pattern IDs must be positive integers."
            )

        with get_connection(self.db_path) as connection:

            run = connection.execute(
                """
                SELECT *
                FROM runs
                WHERE id = ?
                """,
                (run_id,)
            ).fetchone()

            if run is None:
                raise ValueError(
                    f"Run {run_id} does not exist."
                )

            if run["status"] != RunStatus.IN_PROGRESS.value:
                raise ValueError(
                    "Cannot add a lesson to a completed run."
                )

            expected_attempt = run["retry_count"] + 1

            if attempt_number != expected_attempt:
                raise ValueError(
                    f"Expected attempt {expected_attempt}, "
                    f"received attempt {attempt_number}."
                )

            if attempt_number > run["max_retries"] + 1:
                raise ValueError(
                    "Maximum generation attempts exceeded."
                )

            # Validate the generator prompt type.
            generator_prompt = connection.execute(
                """
                SELECT prompt_type
                FROM prompt_versions
                WHERE id = ?
                """,
                (generator_prompt_id,)
            ).fetchone()

            if (
                generator_prompt is None
                or generator_prompt["prompt_type"] != PromptType.GENERATOR.value
            ):
                raise ValueError(
                    "Invalid generator prompt reference."
                )

            # Validate the regeneration prompt type.
            if regeneration_prompt_id is not None:

                regen_prompt = connection.execute(
                    """
                    SELECT prompt_type
                    FROM prompt_versions
                    WHERE id = ?
                    """,
                    (regeneration_prompt_id,)
                ).fetchone()

                if (
                    regen_prompt is None
                    or regen_prompt["prompt_type"]
                    != PromptType.REGENERATION.value
                ):
                    raise ValueError(
                        "Invalid regeneration prompt reference."
                    )

            cursor = connection.execute(
                """
                INSERT INTO lesson_versions (
                    run_id,
                    generator_prompt_id,
                    regeneration_prompt_id,
                    attempt_number,
                    generated_content_json,
                    assembled_prompt,
                    memory_pattern_ids_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    generator_prompt_id,
                    regeneration_prompt_id,
                    attempt_number,
                    lesson.model_dump_json(),
                    assembled_prompt,
                    json.dumps(pattern_ids)
                )
            )

            return cursor.lastrowid

    def get_lesson_version(
        self,
        lesson_version_id: int
    ) -> LessonVersionRecord | None:
        """
        Retrieves a lesson version and reconstructs
        the nested Pydantic Lesson object.
        """

        with get_connection(self.db_path) as connection:

            row = connection.execute(
                """
                SELECT *
                FROM lesson_versions
                WHERE id = ?
                """,
                (lesson_version_id,)
            ).fetchone()

        if row is None:
            return None

        data = dict(row)

        data["lesson"] = Lesson.model_validate_json(
            data.pop("generated_content_json")
        )

        data["memory_pattern_ids"] = json.loads(
            data.pop("memory_pattern_ids_json")
        )

        return LessonVersionRecord.model_validate(data)

    def save_evaluation_report(
        self,
        lesson_version_id: int,
        report: EvaluationReport,
        evaluator_prompt_id: int | None = None
    ) -> list[int]:
        """
        Saves all criterion-wise evaluation results
        within one database transaction.

        Returns the IDs of inserted evaluation records.
        """

        if (
            report.lesson_version_id is not None
            and report.lesson_version_id != lesson_version_id
        ):
            raise ValueError(
                "Evaluation report belongs to a different lesson version."
            )

        with get_connection(self.db_path) as connection:

            lesson_version = connection.execute(
                """
                SELECT *
                FROM lesson_versions
                WHERE id = ?
                """,
                (lesson_version_id,)
            ).fetchone()

            if lesson_version is None:
                raise ValueError(
                    f"Lesson version {lesson_version_id} does not exist."
                )

            if report.attempt_number != lesson_version["attempt_number"]:
                raise ValueError(
                    "Evaluation attempt number does not match the lesson version."
                )

            # Verify the evaluator prompt if provided.
            if evaluator_prompt_id is not None:

                prompt = connection.execute(
                    """
                    SELECT prompt_type
                    FROM prompt_versions
                    WHERE id = ?
                    """,
                    (evaluator_prompt_id,)
                ).fetchone()

                if (
                    prompt is None
                    or prompt["prompt_type"] != PromptType.EVALUATOR.value
                ):
                    raise ValueError(
                        "Invalid evaluator prompt reference."
                    )

            results = report.results

            # Verify that an LLM evaluation has an evaluator prompt.
            requires_llm = any(
                result.evaluator_type
                in (EvaluatorType.LLM, EvaluatorType.HYBRID)
                for result in results
            )

            if requires_llm and evaluator_prompt_id is None:
                raise ValueError(
                    "An evaluator prompt ID is required for LLM evaluation."
                )

            # Retrieve active rubric criteria.
            rubric_rows = connection.execute(
                """
                SELECT id, evaluation_method, is_mandatory
                FROM rubric_criteria
                WHERE is_active = 1
                """
            ).fetchall()

            rubric_map = {
                row["id"]: row
                for row in rubric_rows
            }

            supplied_ids = {
                result.criterion_id
                for result in results
            }

            mandatory_ids = {
                row["id"]
                for row in rubric_rows
                if row["is_mandatory"]
            }

            if not mandatory_ids.issubset(supplied_ids):
                raise ValueError(
                    "Evaluation report is missing mandatory criteria."
                )

            for result in results:

                criterion = rubric_map.get(result.criterion_id)

                if criterion is None:
                    raise ValueError(
                        f"Inactive or unknown criterion: "
                        f"{result.criterion_id}"
                    )

                if (
                    result.evaluator_type.value
                    != criterion["evaluation_method"]
                ):
                    raise ValueError(
                        f"Evaluator type mismatch for "
                        f"{result.criterion_key}."
                    )

                connection.execute(
                    """
                    INSERT INTO evaluations (
                        lesson_version_id,
                        criterion_id,
                        evaluator_prompt_id,
                        status,
                        evaluator_type,
                        evidence_json,
                        failure_reason,
                        proposed_fix
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        lesson_version_id,
                        result.criterion_id,
                        evaluator_prompt_id,
                        result.status.value,
                        result.evaluator_type.value,
                        json.dumps(result.evidence),
                        result.failure_reason,
                        result.proposed_fix
                    )
                )

            rows = connection.execute(
                """
                SELECT id
                FROM evaluations
                WHERE lesson_version_id = ?
                ORDER BY id
                """,
                (lesson_version_id,)
            ).fetchall()

            return [row["id"] for row in rows]

    def get_evaluations(
        self,
        lesson_version_id: int
    ) -> list[dict]:

        with get_connection(self.db_path) as connection:

            rows = connection.execute(
                """
                SELECT
                    e.*,
                    rc.criterion_key,
                    rc.criterion_name

                FROM evaluations e

                JOIN rubric_criteria rc
                    ON rc.id = e.criterion_id

                WHERE e.lesson_version_id = ?

                ORDER BY rc.display_order
                """,
                (lesson_version_id,)
            ).fetchall()

        results = []

        for row in rows:

            data = dict(row)

            data["evidence"] = json.loads(
                data.pop("evidence_json")
            )

            results.append(data)

        return results

    def create_rejection_log(
        self,
        lesson_version_id: int,
        failure_summary: str,
        feedback_sent: str | None = None,
        regeneration_prompt_id: int | None = None
    ) -> int:
        """
        Creates a rejection record.

        For a regenerating rejection, feedback and a regeneration
        prompt must be provided.

        For a final rejection, both can be NULL.
        """

        if bool(feedback_sent) != bool(regeneration_prompt_id):
            raise ValueError(
                "Feedback and regeneration prompt must either "
                "both be supplied or both be NULL."
            )

        with get_connection(self.db_path) as connection:

            lesson = connection.execute(
                """
                SELECT id
                FROM lesson_versions
                WHERE id = ?
                """,
                (lesson_version_id,)
            ).fetchone()

            if lesson is None:
                raise ValueError(
                    "Lesson version does not exist."
                )

            failed_count = connection.execute(
                """
                SELECT COUNT(*) AS count
                FROM evaluations
                WHERE lesson_version_id = ?
                  AND status = 'FAIL'
                """,
                (lesson_version_id,)
            ).fetchone()["count"]

            if failed_count == 0:
                raise ValueError(
                    "Cannot create a rejection log "
                    "without failed evaluation criteria."
                )

            if regeneration_prompt_id is not None:

                prompt = connection.execute(
                    """
                    SELECT prompt_type
                    FROM prompt_versions
                    WHERE id = ?
                    """,
                    (regeneration_prompt_id,)
                ).fetchone()

                if (
                    prompt is None
                    or prompt["prompt_type"] != PromptType.REGENERATION.value
                ):
                    raise ValueError(
                        "Invalid regeneration prompt reference."
                    )

            cursor = connection.execute(
                """
                INSERT INTO rejection_logs (
                    lesson_version_id,
                    regeneration_prompt_id,
                    failure_summary,
                    feedback_sent
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    lesson_version_id,
                    regeneration_prompt_id,
                    failure_summary,
                    feedback_sent
                )
            )

            return cursor.lastrowid

    def link_rejection_to_next_version(
        self,
        rejection_log_id: int,
        next_lesson_version_id: int,
        changes_made: str | None = None
    ) -> None:
        """
        Links a rejected lesson version to the regenerated version.
        """

        with get_connection(self.db_path) as connection:

            rejection = connection.execute(
                """
                SELECT *
                FROM rejection_logs
                WHERE id = ?
                """,
                (rejection_log_id,)
            ).fetchone()

            if rejection is None:
                raise ValueError(
                    "Rejection log does not exist."
                )

            if rejection["next_lesson_version_id"] is not None:
                raise ValueError(
                    "This rejection is already linked to another version."
                )

            if rejection["regeneration_prompt_id"] is None:
                raise ValueError(
                    "This rejection was final; regeneration was not initiated."
                )

            previous = connection.execute(
                """
                SELECT *
                FROM lesson_versions
                WHERE id = ?
                """,
                (rejection["lesson_version_id"],)
            ).fetchone()

            following = connection.execute(
                """
                SELECT *
                FROM lesson_versions
                WHERE id = ?
                """,
                (next_lesson_version_id,)
            ).fetchone()

            if previous is None or following is None:
                raise ValueError(
                    "One of the lesson versions does not exist."
                )

            if previous["run_id"] != following["run_id"]:
                raise ValueError(
                    "Both lesson versions must belong to the same run."
                )

            if following["attempt_number"] != previous["attempt_number"] + 1:
                raise ValueError(
                    "The next version must be the immediately "
                    "following attempt."
                )

            if (
                following["regeneration_prompt_id"]
                != rejection["regeneration_prompt_id"]
            ):
                raise ValueError(
                    "Regeneration prompt does not match the rejection log."
                )

            connection.execute(
                """
                UPDATE rejection_logs

                SET next_lesson_version_id = ?,
                    changes_made = ?

                WHERE id = ?
                """,
                (
                    next_lesson_version_id,
                    changes_made,
                    rejection_log_id
                )
            )

    def record_failure_pattern(
        self,
        evaluation_id: int,
        candidate: FailurePatternCandidate
    ) -> FailurePattern:
        """
        Maps an evaluation failure to a recurring pattern.

        Total occurrences count individual evaluation mappings.

        Distinct-run count tracks how many different user
        requests exhibited this pattern.
        """

        with get_connection(self.db_path) as connection:

            evaluation = connection.execute(
                """
                SELECT
                    e.id,
                    e.criterion_id,
                    e.status,
                    lv.run_id

                FROM evaluations e

                JOIN lesson_versions lv
                    ON lv.id = e.lesson_version_id

                WHERE e.id = ?
                """,
                (evaluation_id,)
            ).fetchone()

            if evaluation is None:
                raise ValueError(
                    f"Evaluation {evaluation_id} does not exist."
                )

            if evaluation["status"] != EvaluationStatus.FAIL.value:
                raise ValueError(
                    "Only failed evaluations can be mapped "
                    "to failure patterns."
                )

            if evaluation["criterion_id"] != candidate.criterion_id:
                raise ValueError(
                    "Failure pattern criterion does not match "
                    "the evaluation criterion."
                )

            # Check whether the pattern already exists.
            pattern = connection.execute(
                """
                SELECT id

                FROM failure_patterns

                WHERE criterion_id = ?
                  AND pattern_key = ?
                """,
                (
                    candidate.criterion_id,
                    candidate.pattern_key
                )
            ).fetchone()

            if pattern is None:

                cursor = connection.execute(
                    """
                    INSERT INTO failure_patterns (
                        criterion_id,
                        pattern_key,
                        failure_pattern,
                        learned_guideline,
                        occurrence_count,
                        distinct_run_count,
                        status
                    )
                    VALUES (?, ?, ?, ?, 0, 0, ?)
                    """,
                    (
                        candidate.criterion_id,
                        candidate.pattern_key,
                        candidate.failure_pattern,
                        candidate.proposed_guideline,
                        FailurePatternStatus.PROPOSED.value
                    )
                )

                pattern_id = cursor.lastrowid

            else:
                pattern_id = pattern["id"]

            # Map this evaluation to the failure pattern.
            connection.execute(
                """
                INSERT OR IGNORE INTO evaluation_failure_patterns (
                    evaluation_id,
                    failure_pattern_id
                )
                VALUES (?, ?)
                """,
                (evaluation_id, pattern_id)
            )

            # Recalculate counts from the mapping table.
            #
            # This prevents duplicate calls from artificially
            # increasing the occurrence counts.

            counts = connection.execute(
                """
                SELECT
                    COUNT(*) AS occurrence_count,
                    COUNT(DISTINCT lv.run_id) AS distinct_run_count

                FROM evaluation_failure_patterns efp

                JOIN evaluations e
                    ON e.id = efp.evaluation_id

                JOIN lesson_versions lv
                    ON lv.id = e.lesson_version_id

                WHERE efp.failure_pattern_id = ?
                """,
                (pattern_id,)
            ).fetchone()

            connection.execute(
                """
                UPDATE failure_patterns

                SET occurrence_count = ?,
                    distinct_run_count = ?,
                    updated_at = strftime(
                        '%Y-%m-%dT%H:%M:%fZ',
                        'now'
                    )

                WHERE id = ?
                """,
                (
                    counts["occurrence_count"],
                    counts["distinct_run_count"],
                    pattern_id
                )
            )

            updated_pattern = connection.execute(
                """
                SELECT *
                FROM failure_patterns
                WHERE id = ?
                """,
                (pattern_id,)
            ).fetchone()

            return FailurePattern.model_validate(
                dict(updated_pattern)
            )

    def set_failure_pattern_status(
        self,
        pattern_id: int,
        status: FailurePatternStatus,
        minimum_distinct_runs: int = 2
    ) -> None:
        """
        Updates the status of a failure pattern.

        Activation requires recurrence across at least
        the configured number of distinct runs.

        Guideline quality validation must happen before
        calling this method.
        """

        if minimum_distinct_runs < 1:
            raise ValueError(
                "Minimum distinct runs must be at least 1."
            )

        with get_connection(self.db_path) as connection:

            pattern = connection.execute(
                """
                SELECT *
                FROM failure_patterns
                WHERE id = ?
                """,
                (pattern_id,)
            ).fetchone()

            if pattern is None:
                raise ValueError(
                    f"Failure pattern {pattern_id} does not exist."
                )

            if status == FailurePatternStatus.ACTIVE:

                if (
                    pattern["distinct_run_count"]
                    < minimum_distinct_runs
                ):
                    raise ValueError(
                        "Failure pattern has not occurred "
                        "in enough distinct runs."
                    )

            connection.execute(
                """
                UPDATE failure_patterns

                SET status = ?,
                    updated_at = strftime(
                        '%Y-%m-%dT%H:%M:%fZ',
                        'now'
                    )

                WHERE id = ?
                """,
                (status.value, pattern_id)
            )

    def get_active_guidelines(
        self,
        criterion_ids: list[int] | None = None
    ) -> list[dict]:
        """
        Retrieves active learned guidelines.

        If criterion IDs are provided, only guidelines
        associated with those criteria are returned.
        """

        if criterion_ids == []:
            return []

        with get_connection(self.db_path) as connection:

            query = """
                SELECT
                    fp.id,
                    fp.criterion_id,
                    rc.criterion_key,
                    rc.criterion_name,
                    fp.pattern_key,
                    fp.failure_pattern,
                    fp.learned_guideline,
                    fp.occurrence_count,
                    fp.distinct_run_count

                FROM failure_patterns fp

                JOIN rubric_criteria rc
                    ON rc.id = fp.criterion_id

                WHERE fp.status = 'ACTIVE'
                  AND rc.is_active = 1
            """

            params = []

            if criterion_ids is not None:

                placeholders = ",".join(
                    "?" for _ in criterion_ids
                )

                query += (
                    f" AND fp.criterion_id IN ({placeholders})"
                )

                params.extend(criterion_ids)

            query += """
                ORDER BY
                    rc.display_order,
                    fp.distinct_run_count DESC
            """

            rows = connection.execute(
                query,
                params
            ).fetchall()

        return [
            dict(row)
            for row in rows
        ]

    def get_rubric_criteria(
        self,
        active_only: bool = True
    ) -> list[RubricCriterion]:
        """
        Retrieves rubric criteria from SQLite.

        Returns criteria in their defined display order.
        """

        with get_connection(self.db_path) as connection:

            query = """
                SELECT *
                FROM rubric_criteria
            """

            if active_only:
                query += " WHERE is_active = 1"

            query += " ORDER BY display_order"

            rows = connection.execute(query).fetchall()

        return [
            RubricCriterion.model_validate(dict(row))
            for row in rows
        ]

    def get_failure_patterns(
        self,
        criterion_id: int,
        include_retired: bool = False
    ) -> list[FailurePattern]:
        """
        Retrieves existing failure patterns for a criterion.

        Retired patterns are excluded by default.
        """

        with get_connection(self.db_path) as connection:

            query = """
                SELECT *
                FROM failure_patterns
                WHERE criterion_id = ?
            """

            if not include_retired:
                query += " AND status != 'RETIRED'"

            query += " ORDER BY id"

            rows = connection.execute(
                query,
                (criterion_id,)
            ).fetchall()

        return [
            FailurePattern.model_validate(dict(row))
            for row in rows
        ]

    def get_failure_pattern_evidence(
        self,
        pattern_id: int
    ) -> list[dict]:
        """
        Retrieves all evaluation failures mapped to
        a particular failure pattern.
        """

        with get_connection(self.db_path) as connection:

            rows = connection.execute(
                """
                SELECT
                    e.id AS evaluation_id,

                    e.status,

                    e.evidence_json,

                    e.failure_reason,

                    e.proposed_fix,

                    lv.id AS lesson_version_id,

                    lv.attempt_number,

                    lv.run_id,

                    r.topic

                FROM evaluation_failure_patterns efp

                JOIN evaluations e
                    ON e.id = efp.evaluation_id

                JOIN lesson_versions lv
                    ON lv.id = e.lesson_version_id

                JOIN runs r
                    ON r.id = lv.run_id

                WHERE efp.failure_pattern_id = ?

                ORDER BY e.id
                """,
                (pattern_id,)
            ).fetchall()

        results = []

        for row in rows:

            data = dict(row)

            data["evidence"] = json.loads(
                data.pop("evidence_json")
            )

            results.append(data)

        return results

    def record_failure_pattern_validation(
        self,
        pattern_id: int,
        approved: bool,
        reason: str,
        revised_guideline: str | None = None,
        minimum_distinct_runs: int = 2,
        validator_version: str = "V1"
    ) -> None:
        """
        Saves a guideline-validation decision.

        If approved:
        - Checks the recurrence threshold.
        - Updates the learned guideline.
        - Activates the failure pattern.

        If rejected:
        - Saves the validation result.
        - Keeps the pattern proposed.
        """

        if not reason.strip():
            raise ValueError(
                "Validation reason cannot be empty."
            )

        if approved and not revised_guideline:
            raise ValueError(
                "An approved guideline must have "
                "a revised/final guideline."
            )

        with get_connection(self.db_path) as connection:

            pattern = connection.execute(
                """
                SELECT *
                FROM failure_patterns
                WHERE id = ?
                """,
                (pattern_id,)
            ).fetchone()

            if pattern is None:
                raise ValueError(
                    "Failure pattern does not exist."
                )

            if pattern["status"] == FailurePatternStatus.RETIRED.value:
                raise ValueError(
                    "A retired failure pattern cannot be validated."
                )

            if approved:

                if (
                    pattern["distinct_run_count"]
                    < minimum_distinct_runs
                ):
                    raise ValueError(
                        "Guideline cannot be activated before "
                        "the recurrence threshold is reached."
                    )

            connection.execute(
                """
                INSERT INTO failure_pattern_validations (
                    failure_pattern_id,
                    approved,
                    reason,
                    revised_guideline,
                    validator_version
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    pattern_id,
                    int(approved),
                    reason,
                    revised_guideline,
                    validator_version
                )
            )

            if approved:

                connection.execute(
                    """
                    UPDATE failure_patterns

                    SET learned_guideline = ?,
                        status = 'ACTIVE',
                        updated_at = strftime(
                            '%Y-%m-%dT%H:%M:%fZ',
                            'now'
                        )

                    WHERE id = ?
                    """,
                    (revised_guideline, pattern_id)
                )

