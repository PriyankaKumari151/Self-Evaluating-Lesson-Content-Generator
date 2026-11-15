from pydantic import Field
from datetime import datetime

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)

from content_agent.models.enums import EvaluationMethod


class RubricCriterion(AppBaseModel):
    """
    Defines one mandatory quality criterion.
    """

    id: int | None = None

    criterion_key: NonEmptyStr

    criterion_name: NonEmptyStr

    description: NonEmptyStr

    pass_condition: NonEmptyStr

    evaluation_method: EvaluationMethod

    is_mandatory: bool = True

    display_order: int = Field(ge=1)

    is_active: bool = True

    created_at: datetime | None = None

    updated_at: datetime | None = None

# Initial rubric for the content-generation system

DEFAULT_RUBRIC = [

    RubricCriterion(
        criterion_key="TECHNICAL_ACCURACY",
        criterion_name="Technical accuracy and grounding",
        description=(
            "The lesson must explain the topic accurately "
            "and remain consistent with reliable references."
        ),
        pass_condition=(
            "No materially incorrect explanations or "
            "unsupported factual claims."
        ),
        evaluation_method=EvaluationMethod.LLM,
        display_order=1
    ),

    RubricCriterion(
        criterion_key="BEGINNER_FRIENDLINESS",
        criterion_name="Beginner friendliness",
        description=(
            "The lesson must be understandable to a learner "
            "with no prior technical knowledge."
        ),
        pass_condition=(
            "The explanations use simple English, short sentences "
            "and assume no prior knowledge."
        ),
        evaluation_method=EvaluationMethod.LLM,
        display_order=2
    ),

    RubricCriterion(
        criterion_key="PRACTICAL_EXAMPLES",
        criterion_name="Practical examples",
        description=(
            "The lesson must demonstrate concepts through "
            "relatable and relevant examples."
        ),
        pass_condition=(
            "At least one relevant practical example is included "
            "and explained clearly."
        ),
        evaluation_method=EvaluationMethod.HYBRID,
        display_order=3
    ),

    RubricCriterion(
        criterion_key="JARGON_HANDLING",
        criterion_name="Jargon handling",
        description=(
            "Technical terminology must be explained "
            "before or when it is introduced."
        ),
        pass_condition=(
            "Important technical terms are explained in simple "
            "language without assuming prior knowledge."
        ),
        evaluation_method=EvaluationMethod.LLM,
        display_order=4
    ),

    RubricCriterion(
        criterion_key="KEY_POINT_COVERAGE",
        criterion_name="Key point coverage",
        description=(
            "The lesson must cover the essential aspects "
            "of the requested topic."
        ),
        pass_condition=(
            "The lesson explains what the topic is, why it matters "
            "and how it works or is applied."
        ),
        evaluation_method=EvaluationMethod.HYBRID,
        display_order=5
    ),

    RubricCriterion(
        criterion_key="TEACHING_FLOW",
        criterion_name="Coherent teaching flow",
        description=(
            "The lesson must introduce concepts in a logical "
            "and understandable sequence."
        ),
        pass_condition=(
            "The lesson progresses from fundamental concepts "
            "to more advanced explanations without confusing jumps."
        ),
        evaluation_method=EvaluationMethod.LLM,
        display_order=6
    ),

    RubricCriterion(
        criterion_key="STANDALONE_QUALITY",
        criterion_name="Standalone lesson quality",
        description=(
            "The lesson should be complete enough to be understood "
            "without requiring external explanations."
        ),
        pass_condition=(
            "The lesson provides sufficient context, definitions "
            "and explanations to understand the topic independently."
        ),
        evaluation_method=EvaluationMethod.LLM,
        display_order=7
    )
]