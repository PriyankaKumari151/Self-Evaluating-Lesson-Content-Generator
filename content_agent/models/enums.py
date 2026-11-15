from enum import Enum


class RunStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"


class EvaluatorType(str, Enum):
    LLM = "LLM"
    RULE_BASED = "RULE_BASED"
    HYBRID = "HYBRID"


class PromptType(str, Enum):
    GENERATOR = "GENERATOR"
    EVALUATOR = "EVALUATOR"
    REGENERATION = "REGENERATION"


class PromptStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class FailurePatternStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class EvaluationMethod(str, Enum):
    LLM = "LLM"
    RULE_BASED = "RULE_BASED"
    HYBRID = "HYBRID"