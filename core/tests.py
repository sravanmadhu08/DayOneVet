from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Choice, Question, QuizAttempt, UserAnswer, UserProfile


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
