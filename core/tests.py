from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Question, QuizAttempt, UserAnswer, UserProfile


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
