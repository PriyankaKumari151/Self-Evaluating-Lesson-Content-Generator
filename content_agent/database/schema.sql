-- =====================================================
-- 1. RUNS
-- One record per user request
-- =====================================================

CREATE TABLE IF NOT EXISTS runs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    topic TEXT NOT NULL,

    learner_profile_json TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'IN_PROGRESS'
        CHECK (
            status IN (
                'IN_PROGRESS',
                'APPROVED',
                'REJECTED'
            )
        ),

    max_retries INTEGER NOT NULL DEFAULT 2
        CHECK (max_retries >= 0),

    retry_count INTEGER NOT NULL DEFAULT 0
        CHECK (
            retry_count >= 0
            AND retry_count <= max_retries
        ),

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    completed_at TEXT

);


-- =====================================================
-- 2. RUBRIC CRITERIA
-- Defines what good content means
-- =====================================================

CREATE TABLE IF NOT EXISTS rubric_criteria (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    criterion_key TEXT NOT NULL UNIQUE,

    criterion_name TEXT NOT NULL,

    description TEXT NOT NULL,

    pass_condition TEXT NOT NULL,

    evaluation_method TEXT NOT NULL
        CHECK (
            evaluation_method IN (
                'LLM',
                'RULE_BASED',
                'HYBRID'
            )
        ),

    is_mandatory INTEGER NOT NULL DEFAULT 1
        CHECK (is_mandatory IN (0, 1)),

    display_order INTEGER NOT NULL UNIQUE
        CHECK (display_order > 0),

    is_active INTEGER NOT NULL DEFAULT 1
        CHECK (is_active IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    updated_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))

);


-- =====================================================
-- 3. PROMPT VERSIONS
-- Stores versioned LLM prompts
-- =====================================================

CREATE TABLE IF NOT EXISTS prompt_versions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    prompt_type TEXT NOT NULL
        CHECK (
            prompt_type IN (
                'GENERATOR',
                'EVALUATOR',
                'REGENERATION'
            )
        ),

    version TEXT NOT NULL,

    prompt_content TEXT NOT NULL,

    change_summary TEXT NOT NULL,

    status TEXT NOT NULL DEFAULT 'DRAFT'
        CHECK (
            status IN (
                'DRAFT',
                'ACTIVE',
                'RETIRED'
            )
        ),

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    UNIQUE(prompt_type, version)

);


-- Only one active prompt per prompt type

CREATE UNIQUE INDEX IF NOT EXISTS
idx_one_active_prompt_per_type

ON prompt_versions(prompt_type)

WHERE status = 'ACTIVE';


-- =====================================================
-- 4. LESSON VERSIONS
-- Every generated version of a lesson
-- =====================================================

CREATE TABLE IF NOT EXISTS lesson_versions (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    run_id INTEGER NOT NULL,

    generator_prompt_id INTEGER NOT NULL,

    regeneration_prompt_id INTEGER,

    attempt_number INTEGER NOT NULL
        CHECK (attempt_number >= 1),

    generated_content_json TEXT NOT NULL,

    assembled_prompt TEXT,

    memory_pattern_ids_json TEXT NOT NULL DEFAULT '[]',

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (run_id)
        REFERENCES runs(id),

    FOREIGN KEY (generator_prompt_id)
        REFERENCES prompt_versions(id),

    FOREIGN KEY (regeneration_prompt_id)
        REFERENCES prompt_versions(id),

    UNIQUE(run_id, attempt_number),

    CHECK (
        (attempt_number = 1 AND regeneration_prompt_id IS NULL)
        OR
        (attempt_number > 1 AND regeneration_prompt_id IS NOT NULL)
    )

);


-- =====================================================
-- 5. EVALUATIONS
-- Criterion-wise PASS/FAIL results
-- =====================================================

CREATE TABLE IF NOT EXISTS evaluations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    lesson_version_id INTEGER NOT NULL,

    criterion_id INTEGER NOT NULL,

    evaluator_prompt_id INTEGER,

    status TEXT NOT NULL
        CHECK (
            status IN ('PASS', 'FAIL')
        ),

    evaluator_type TEXT NOT NULL
        CHECK (
            evaluator_type IN (
                'LLM',
                'RULE_BASED',
                'HYBRID'
            )
        ),

    evidence_json TEXT NOT NULL,

    failure_reason TEXT,

    proposed_fix TEXT,

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (lesson_version_id)
        REFERENCES lesson_versions(id),

    FOREIGN KEY (criterion_id)
        REFERENCES rubric_criteria(id),

    FOREIGN KEY (evaluator_prompt_id)
        REFERENCES prompt_versions(id),

    UNIQUE(lesson_version_id, criterion_id),

    CHECK (
        (status = 'PASS')
        OR
        (
            status = 'FAIL'
            AND failure_reason IS NOT NULL
            AND proposed_fix IS NOT NULL
        )
    )

);


-- =====================================================
-- 6. REJECTION LOGS
-- Consolidated failure and regeneration history
-- =====================================================

CREATE TABLE IF NOT EXISTS rejection_logs (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    lesson_version_id INTEGER NOT NULL UNIQUE,

    next_lesson_version_id INTEGER,

    regeneration_prompt_id INTEGER,

    failure_summary TEXT NOT NULL,

    feedback_sent TEXT,

    changes_made TEXT,

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (lesson_version_id)
        REFERENCES lesson_versions(id),

    FOREIGN KEY (next_lesson_version_id)
        REFERENCES lesson_versions(id),

    FOREIGN KEY (regeneration_prompt_id)
        REFERENCES prompt_versions(id),

    CHECK (
        next_lesson_version_id IS NULL
        OR next_lesson_version_id != lesson_version_id
    )

);


-- =====================================================
-- 7. FAILURE PATTERNS
-- Recurring failures + learned guidelines
-- =====================================================

CREATE TABLE IF NOT EXISTS failure_patterns (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    criterion_id INTEGER NOT NULL,

    pattern_key TEXT NOT NULL,

    failure_pattern TEXT NOT NULL,

    learned_guideline TEXT NOT NULL,

    occurrence_count INTEGER NOT NULL DEFAULT 0
        CHECK (occurrence_count >= 0),

    distinct_run_count INTEGER NOT NULL DEFAULT 0
        CHECK (
            distinct_run_count >= 0
            AND distinct_run_count <= occurrence_count
        ),

    status TEXT NOT NULL DEFAULT 'PROPOSED'
        CHECK (
            status IN (
                'PROPOSED',
                'ACTIVE',
                'RETIRED'
            )
        ),

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    updated_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (criterion_id)
        REFERENCES rubric_criteria(id),

    UNIQUE(criterion_id, pattern_key)

);


-- =====================================================
-- 8. EVALUATION FAILURE PATTERN MAPPING
-- Connects individual failures to recurring patterns
-- =====================================================

CREATE TABLE IF NOT EXISTS evaluation_failure_patterns (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    evaluation_id INTEGER NOT NULL,

    failure_pattern_id INTEGER NOT NULL,

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (evaluation_id)
        REFERENCES evaluations(id),

    FOREIGN KEY (failure_pattern_id)
        REFERENCES failure_patterns(id),

    UNIQUE(evaluation_id, failure_pattern_id)

);


-- =====================================================
-- INDEXES
-- Improve common query performance
-- =====================================================

CREATE INDEX IF NOT EXISTS idx_lesson_versions_run
ON lesson_versions(run_id);

CREATE INDEX IF NOT EXISTS idx_evaluations_lesson
ON evaluations(lesson_version_id);

CREATE INDEX IF NOT EXISTS idx_evaluations_criterion
ON evaluations(criterion_id, status);

CREATE INDEX IF NOT EXISTS idx_failure_patterns_criterion
ON failure_patterns(criterion_id, status);

CREATE INDEX IF NOT EXISTS idx_failure_mapping_pattern
ON evaluation_failure_patterns(failure_pattern_id);

-- =====================================================
-- 9. FAILURE PATTERN VALIDATIONS
-- Stores guideline validation history
-- =====================================================

CREATE TABLE IF NOT EXISTS failure_pattern_validations (

    id INTEGER PRIMARY KEY AUTOINCREMENT,

    failure_pattern_id INTEGER NOT NULL,

    approved INTEGER NOT NULL
        CHECK (approved IN (0, 1)),

    reason TEXT NOT NULL,

    revised_guideline TEXT,

    validator_version TEXT NOT NULL DEFAULT 'V1',

    created_at TEXT NOT NULL DEFAULT
        (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),

    FOREIGN KEY (failure_pattern_id)
        REFERENCES failure_patterns(id)

);


CREATE INDEX IF NOT EXISTS idx_pattern_validations_pattern

ON failure_pattern_validations(failure_pattern_id);