from content_agent.models.run import LessonRequest

from content_agent.models.lesson import LearnerProfile

from content_agent.services.lesson_service import (
    generate_lesson
)


def main():

    request = LessonRequest(

        topic="Introduction to RAG",

        learner_profile=LearnerProfile(

            education="12th-grade graduate",

            technical_background="No AI knowledge",

            english_level="Basic",

            learning_goal=(
                "Understand RAG from scratch "
                "with practical examples."
            )

        ),

        max_retries=2

    )

    print("=" * 60)

    print("SELF-EVALUATING LESSON CONTENT GENERATOR")

    print("=" * 60)

    # Execute the complete LangGraph workflow.
    result = generate_lesson(
        request=request
    )

    print("\n" + "=" * 60)

    print("FINAL WORKFLOW RESULT")

    print("=" * 60)

    print("Run ID:", result["run_id"])

    print("Final Status:", result["final_status"])

    print("Total Attempts:", result["total_attempts"])

    print(
        "Final Lesson Version ID:",
        result["final_lesson_version_id"]
    )

    print("\nLESSON TITLE:")

    print(result["final_lesson"].title)

    print("\nATTEMPT HISTORY:")

    for attempt in result["attempt_history"]:

        print(
            f"\nAttempt {attempt['attempt_number']}:"
        )

        print(
            "Lesson:",
            attempt["lesson_title"]
        )

        print(
            "Passed:",
            attempt["passed"]
        )

        print(
            "Failed criteria:",
            attempt["failed_criteria"]
        )

    print("\nMEMORY PROCESSING:")

    for memory in result["memory_results"]:

        print(
            memory.pattern_key,
            "=>",
            memory.message
        )

    if result["warnings"]:

        print("\nWORKFLOW WARNINGS:")

        for warning in result["warnings"]:
            print("-", warning)

    print("\n" + "=" * 60)

    if result["final_status"] == "APPROVED":

        print("LESSON APPROVED FOR DELIVERY")

    else:

        print("LESSON REJECTED")

    print("=" * 60)


if __name__ == "__main__":
    main()