from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Choice,
    Question,
    QuizAttempt,
    StudyResource,
    UserAnswer,
    UserProfile,
    WeeklyStudyTopic,
    WeeklyTopicAttachment,
    WeeklyTopicProgress,
)


class AuthenticationFlowTests(TestCase):
    def test_registration_creates_user_profile_and_logs_in(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "newvet",
                "email": "newvet@example.com",
                "first_name": "New",
                "last_name": "Vet",
                "profession": "Small animal vet",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("home"))
        user = get_user_model().objects.get(username="newvet")
        self.assertEqual(user.email, "newvet@example.com")
        self.assertEqual(user.profile.profession, "Small animal vet")
        self.assertEqual(user.profile.display_name, "New Vet")

    def test_registration_rejects_duplicate_email(self):
        get_user_model().objects.create_user(
            username="existing",
            email="taken@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("register"),
            {
                "username": "another",
                "email": "TAKEN@example.com",
                "password1": "StrongPass123!",
                "password2": "StrongPass123!",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context["form"], "email", "An account with this email already exists.")

    def test_user_can_login_with_email(self):
        get_user_model().objects.create_user(
            username="emailvet",
            email="emailvet@example.com",
            password="StrongPass123!",
        )

        response = self.client.post(
            reverse("login"),
            {
                "username": "emailvet@example.com",
                "password": "StrongPass123!",
            },
        )

        self.assertRedirects(response, reverse("home"))


class ProfileWeeklyGoalTests(TestCase):
    def test_profile_shows_current_week_goal_progress(self):
        user = get_user_model().objects.create_user(username="weekly", password="pass12345")
        UserProfile.objects.create(user=user, weekly_goal_questions=5)
        question = Question.objects.create(
            text="What is the most likely diagnosis?",
            species="dog",
            system="cardiology",
            explanation="Demo explanation.",
        )
        choice = Choice.objects.create(question=question, text="Correct answer", is_correct=True)
        attempt = QuizAttempt.objects.create(user=user, total_questions=1)

        UserAnswer.objects.create(
            quiz_attempt=attempt,
            question=question,
            selected_choice=choice,
            is_correct=True,
        )
        old_question = Question.objects.create(
            text="Older question",
            species="cat",
            system="neurology",
            explanation="Older explanation.",
        )
        old_choice = Choice.objects.create(question=old_question, text="Old answer", is_correct=True)
        last_week_answer = UserAnswer.objects.create(
            quiz_attempt=QuizAttempt.objects.create(user=user, total_questions=1),
            question=old_question,
            selected_choice=old_choice,
            is_correct=True,
        )
        UserAnswer.objects.filter(id=last_week_answer.id).update(answered_at=timezone.now() - timedelta(days=8))

        self.client.login(username="weekly", password="pass12345")
        response = self.client.get(reverse("profile"))

        self.assertEqual(response.context["weekly_answered"], 1)
        self.assertEqual(response.context["weekly_goal_percent"], 20)
        self.assertEqual(response.context["weekly_goal_remaining"], 4)
        self.assertContains(response, "4 questions left")


class QuizModeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="quizzer", password="pass12345")
        self.client.login(username="quizzer", password="pass12345")
        self.question = Question.objects.create(
            text="Which drug is commonly used for canine CHF?",
            species="dog",
            system="cardiology",
            explanation="Pimobendan is commonly used in canine congestive heart failure.",
        )
        self.correct_choice = Choice.objects.create(question=self.question, text="Pimobendan", is_correct=True)
        Choice.objects.create(question=self.question, text="Maropitant", is_correct=False)

    def test_timed_mode_creates_attempt_with_duration(self):
        response = self.client.post(
            reverse("quiz_start"),
            {
                "quiz_mode": QuizAttempt.TIMED,
                "species": "dog",
                "systems": "cardiology",
                "question_count": "5",
                "duration_minutes": "30",
            },
        )

        attempt = QuizAttempt.objects.get(user=self.user)
        self.assertRedirects(response, reverse("quiz_question", args=[attempt.id]))
        self.assertEqual(attempt.exam_mode, QuizAttempt.TIMED)
        self.assertEqual(attempt.duration_minutes, 30)

    def test_timed_answer_advances_without_practice_feedback(self):
        attempt = QuizAttempt.objects.create(
            user=self.user,
            exam_mode=QuizAttempt.TIMED,
            duration_minutes=30,
            total_questions=1,
            question_order=[self.question.id],
        )
        session = self.client.session
        session[f"quiz_{attempt.id}_index"] = 0
        session.save()

        response = self.client.post(
            reverse("quiz_question", args=[attempt.id]),
            {"action": "answer", "choice": self.correct_choice.id},
        )

        self.assertRedirects(response, reverse("quiz_question", args=[attempt.id]), fetch_redirect_response=False)
        self.assertEqual(self.client.session[f"quiz_{attempt.id}_index"], 1)
        answer = attempt.answers.get(question=self.question)
        self.assertTrue(answer.is_correct)

    def test_correctly_answered_questions_are_removed_from_new_quiz_pool(self):
        done_attempt = QuizAttempt.objects.create(user=self.user, total_questions=1, question_order=[self.question.id])
        UserAnswer.objects.create(
            quiz_attempt=done_attempt,
            question=self.question,
            selected_choice=self.correct_choice,
            is_correct=True,
        )
        Question.objects.create(
            text="Which species commonly gets hypertrophic cardiomyopathy?",
            species="cat",
            system="cardiology",
            explanation="Cats commonly develop hypertrophic cardiomyopathy.",
        )

        response = self.client.get(reverse("quiz_start"))

        self.assertEqual(response.context["done_count"], 1)
        self.assertEqual(response.context["available_count"], 1)
        dog_counts = [item for item in response.context["species_counts"] if item["value"] == "dog"][0]
        self.assertEqual(dog_counts["available"], 0)
        self.assertEqual(dog_counts["done"], 1)
        cardio_counts = [item for item in response.context["system_counts"] if item["value"] == "cardiology"][0]
        self.assertEqual(cardio_counts["available"], 1)
        self.assertEqual(cardio_counts["done"], 1)
        self.assertIn(("dog", "Dog (0)"), response.context["form"].fields["species"].choices)
        self.assertIn(("cardiology", "Cardiology (1)"), response.context["form"].fields["systems"].choices)

    def test_done_pile_page_can_start_quiz_from_correctly_answered_questions(self):
        done_attempt = QuizAttempt.objects.create(user=self.user, total_questions=1, question_order=[self.question.id])
        UserAnswer.objects.create(
            quiz_attempt=done_attempt,
            question=self.question,
            selected_choice=self.correct_choice,
            is_correct=True,
        )

        response = self.client.post(
            reverse("quiz_done_pile"),
            {
                "quiz_mode": QuizAttempt.PRACTICE,
                "species": "dog",
                "systems": "cardiology",
                "question_count": "5",
                "duration_minutes": "60",
            },
        )

        new_attempt = QuizAttempt.objects.exclude(id=done_attempt.id).get(user=self.user)
        self.assertRedirects(response, reverse("quiz_question", args=[new_attempt.id]))
        self.assertEqual(new_attempt.question_order, [self.question.id])


class StudySectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="study", password="pass12345")
        self.client.login(username="study", password="pass12345")

    def test_weekly_topic_completion_is_user_specific_and_toggleable(self):
        other_user = get_user_model().objects.create_user(username="other", password="pass12345")
        topic = WeeklyStudyTopic.objects.create(title="Week 1 cardio", week_label="Week 1")

        response = self.client.post(reverse("study"), {"topic_id": topic.id})

        self.assertRedirects(response, reverse("study"))
        self.assertTrue(WeeklyTopicProgress.objects.filter(user=self.user, topic=topic).exists())
        self.assertFalse(WeeklyTopicProgress.objects.filter(user=other_user, topic=topic).exists())

        self.client.post(reverse("study"), {"topic_id": topic.id})

        self.assertFalse(WeeklyTopicProgress.objects.filter(user=self.user, topic=topic).exists())

    def test_weekly_topic_can_have_multiple_pdf_attachments(self):
        topic = WeeklyStudyTopic.objects.create(title="Week 2 respiratory", week_label="Week 2")

        WeeklyTopicAttachment.objects.create(topic=topic, title="Core notes", file="weekly_topics/core.pdf")
        WeeklyTopicAttachment.objects.create(topic=topic, title="Case review", file="weekly_topics/cases.pdf")

        response = self.client.get(reverse("study"))

        self.assertEqual(topic.attachments.count(), 2)
        self.assertContains(response, "Core notes")
        self.assertContains(response, "Case review")

    def test_study_page_filters_guidelines_and_links_by_species_and_system(self):
        StudyResource.objects.create(
            title="Dog cardio guideline",
            description="Canine cardiology notes.",
            resource_type=StudyResource.GUIDELINE,
            species="dog",
            system="cardiology",
        )
        StudyResource.objects.create(
            title="Cat neurology guideline",
            description="Feline neurology notes.",
            resource_type=StudyResource.GUIDELINE,
            species="cat",
            system="neurology",
        )
        StudyResource.objects.create(
            title="Dog cardio link",
            description="External canine cardiology reference.",
            resource_type=StudyResource.EXTERNAL_LINK,
            external_url="https://example.com/cardio",
            species="dog",
            system="cardiology",
        )

        response = self.client.get(reverse("study"), {"species": "dog", "system": "cardiology"})

        self.assertContains(response, "Dog cardio guideline")
        self.assertContains(response, "Dog cardio link")
        self.assertNotContains(response, "Cat neurology guideline")
