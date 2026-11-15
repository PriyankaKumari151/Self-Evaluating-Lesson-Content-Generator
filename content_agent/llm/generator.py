from typing import Any

from pydantic import ValidationError

from content_agent.models.lesson import Lesson

from content_agent.config import settings

from content_agent.llm.client import (
    create_structured_model
)


class LessonGenerationError(Exception):
    """
    Represents a failure during lesson generation.

    This is separate from a quality rejection.

    API errors and output-format errors should not
    automatically consume lesson regeneration attempts.
    """


class LessonGenerator:
    """
    Generates structured beginner lessons using an LLM.
    """

    def __init__(
        self,
        model: Any | None = None
    ):
        """
        Allows dependency injection for testing.

        If a model is supplied, it is used directly.
        Otherwise, the configured structured LLM is created.
        """

        self.model = model

    def generate(
        self,
        prompt: str
    ) -> Lesson:
        """
        Generates a lesson from the assembled prompt.

        Returns a validated Lesson object.
        """

        if not prompt or not prompt.strip():

            raise ValueError(
                "Generation prompt cannot be empty."
            )

        try:

            # Create the structured LLM lazily.
            # This also allows tests to inject a fake model.

            if self.model is None:

                structured_llm = create_structured_model(
                    schema=Lesson,
                    temperature=settings.generation_temperature
                )

            else:

                structured_llm = self.model.with_structured_output(
                    Lesson,
                    method=settings.structured_output_method,
                    strict=False
                )

            # Invoke the LLM.
            result = structured_llm.invoke(prompt)

            # Support both Pydantic objects and dictionaries.
            if isinstance(result, Lesson):

                lesson = result

            elif isinstance(result, dict):

                lesson = Lesson.model_validate(result)

            else:

                raise LessonGenerationError(
                    "LLM returned an unexpected output type: "
                    f"{type(result).__name__}"
                )

            # Additional sanity checks.
            if not lesson.title.strip():
                raise LessonGenerationError(
                    "Generated lesson has an empty title."
                )

            return lesson

        except ValidationError as exc:

            raise LessonGenerationError(
                "LLM output failed Lesson schema validation."
            ) from exc

        except LessonGenerationError:

            raise

        except Exception as exc:

            raise LessonGenerationError(
                f"Lesson generation failed: {exc}"
            ) from exc