from content_agent.database.repository import DatabaseRepository

from content_agent.models import (
    LessonRequest,
    LearnerProfile
)

from content_agent.models.enums import PromptType

from content_agent.prompts import build_generator_prompt

from content_agent.llm import LessonGenerator


def main():

    repository = DatabaseRepository()

    # 1. Define the user request.

    request = LessonRequest(
        topic="Introduction to RAG",
        learner_profile=LearnerProfile(
            education="12th-grade graduate",
            technical_background="No AI knowledge",
            english_level="Basic",
            learning_goal="Understand RAG from scratch"
        ),
        max_retries=2
    )

    # 2. Retrieve the active standard prompt.

    generator_prompt = repository.get_active_prompt(
        PromptType.GENERATOR
    )

    if generator_prompt is None:
        raise RuntimeError(
            "No active generator prompt found."
        )

    # 3. Retrieve active learned guidelines.

    guidelines = repository.get_active_guidelines()

    # 4. Construct the generation prompt.

    final_prompt = build_generator_prompt(
        standard_prompt=generator_prompt,
        topic=request.topic,
        learner_profile=request.learner_profile,
        reference_material=(
            "RAG combines information retrieval "
            "with language generation. "
            "Retrieved information is supplied "
            "to the language model as context."
        ),
        learned_guidelines=guidelines
    )

    # 5. Generate the lesson using the actual LLM.

    generator = LessonGenerator()

    print("Generating lesson...")

    lesson = generator.generate(final_prompt)

    # 6. Create a run after successful generation
    # for this initial integration smoke test.

    run_id = repository.create_run(request)

    # 7. Store the generated lesson.

    lesson_version_id = repository.create_lesson_version(
        run_id=run_id,
        lesson=lesson,
        attempt_number=1,
        generator_prompt_id=generator_prompt.id,
        assembled_prompt=final_prompt,
        memory_pattern_ids=[
            guideline["id"]
            for guideline in guidelines
        ]
    )

    print("\nGeneration successful!")

    print("Run ID:", run_id)

    print("Lesson Version ID:", lesson_version_id)

    print("\nLesson Title:", lesson.title)

    print("\nIntroduction:\n")
    print(lesson.introduction)

    print("\nPractical Examples:")
    for example in lesson.practical_examples:
        print("-", example.title)


if __name__ == "__main__":
    main()