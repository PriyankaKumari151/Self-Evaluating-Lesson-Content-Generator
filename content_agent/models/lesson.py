from pydantic import Field, field_validator, model_validator

from content_agent.models.base import (
    AppBaseModel,
    NonEmptyStr
)


class LearnerProfile(AppBaseModel):
    education: NonEmptyStr = "12th-grade graduate"

    technical_background: NonEmptyStr = (
        "No prior technical knowledge"
    )

    english_level: NonEmptyStr = "Basic"

    learning_goal: NonEmptyStr = (
        "Understand the given topic from scratch"
    )


class LessonConcept(AppBaseModel):
    """
    Represents one important concept covered in the lesson.
    """

    term: NonEmptyStr

    explanation: NonEmptyStr

    analogy: str | None = None


class LessonStep(AppBaseModel):
    """
    Represents one step in the explanation of a concept
    or its working process.
    """

    step_number: int = Field(ge=1)

    title: NonEmptyStr

    explanation: NonEmptyStr

    example: str | None = None


class PracticalExample(AppBaseModel):
    """
    Represents a relatable practical example.
    """

    title: NonEmptyStr

    situation: NonEmptyStr

    explanation: NonEmptyStr

    takeaway: NonEmptyStr


class GlossaryTerm(AppBaseModel):
    term: NonEmptyStr

    simple_definition: NonEmptyStr

    analogy: str | None = None


class Lesson(AppBaseModel):
    """
    Complete structured beginner lesson.
    """

    topic: NonEmptyStr

    title: NonEmptyStr

    introduction: NonEmptyStr

    why_it_matters: NonEmptyStr

    learning_objectives: list[NonEmptyStr]

    key_concepts: list[LessonConcept]

    how_it_works: list[LessonStep]

    practical_examples: list[PracticalExample]

    benefits: list[NonEmptyStr]

    limitations: list[NonEmptyStr]

    glossary: list[GlossaryTerm]

    recap: list[NonEmptyStr]

    @model_validator(mode="after")
    def validate_step_order(self):
        """
        Ensure step numbers are unique and sequential.
        """

        step_numbers = [
            step.step_number
            for step in self.how_it_works
        ]

        expected = list(range(1, len(step_numbers) + 1))

        if sorted(step_numbers) != expected:
            raise ValueError(
                "Lesson steps must have unique, "
                "sequential numbering starting from 1."
            )

        return self