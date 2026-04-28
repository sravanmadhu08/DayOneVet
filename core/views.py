import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils import timezone

from .forms import (
    FlashcardForm,
    ForumReplyForm,
    ForumTopicForm,
    QuizStartForm,
    RegisterForm,
    ThemePreferenceForm,
    UserProfileForm,
)
from .models import (
    Flashcard,
    FlashcardReview,
    ForumTopic,
    Question,
    QuizAttempt,
    SPECIES_CHOICES,
    SYSTEM_CHOICES,
    StudyResource,
    UserAnswer,
    UserProfile,
)


def landing(request):
    if request.user.is_authenticated:
        return redirect("home")
    return render(request, "core/landing.html")


def register(request):
    if request.user.is_authenticated:
        return redirect("home")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, "Welcome to RC. Your account is ready.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("home")


def logout_view(request):
    logout(request)
    return redirect("landing")


@login_required
def profile(request):
    profile_obj, _ = UserProfile.objects.get_or_create(user=request.user)
    answers = UserAnswer.objects.filter(quiz_attempt__user=request.user)
    attempted = answers.filter(selected_choice__isnull=False).count()
    correct = answers.filter(is_correct=True).count()
    percent_correct = round((correct / attempted) * 100) if attempted else 0
    now = timezone.now()
    week_start = now - timedelta(days=now.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    weekly_answered = answers.filter(selected_choice__isnull=False, answered_at__gte=week_start).count()
    weekly_goal = max(profile_obj.weekly_goal_questions or 1, 1)
    weekly_goal_percent = min(round((weekly_answered / weekly_goal) * 100), 100)
    weekly_goal_remaining = max(weekly_goal - weekly_answered, 0)
    completed_quizzes = request.user.quiz_attempts.filter(is_completed=True).count()
    private_cards = request.user.private_flashcards.count()
    due_flashcards = FlashcardReview.objects.filter(
        user=request.user,
    ).filter(Q(next_review_at__lte=timezone.now()) | Q(review_count=0)).count()

    form = UserProfileForm(instance=profile_obj, user=request.user)
    theme_form = ThemePreferenceForm(instance=profile_obj)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "theme":
            theme_form = ThemePreferenceForm(request.POST, instance=profile_obj)
            if theme_form.is_valid():
                theme_form.save()
                messages.success(request, "Theme settings updated.")
                return redirect("profile")
        else:
            form = UserProfileForm(request.POST, instance=profile_obj, user=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, "Profile updated.")
                return redirect("profile")

    return render(
        request,
        "core/profile.html",
        {
            "profile_obj": profile_obj,
            "form": form,
            "theme_form": theme_form,
            "attempted": attempted,
            "percent_correct": percent_correct,
            "completed_quizzes": completed_quizzes,
            "private_cards": private_cards,
            "due_flashcards": due_flashcards,
            "weekly_answered": weekly_answered,
            "weekly_goal_percent": weekly_goal_percent,
            "weekly_goal_remaining": weekly_goal_remaining,
        },
    )


@login_required
def home(request):
    answers = UserAnswer.objects.filter(quiz_attempt__user=request.user)
    attempted = answers.filter(selected_choice__isnull=False).count()
    correct = answers.filter(is_correct=True).count()
    total_questions = Question.objects.count()
    seen_questions = answers.filter(Q(selected_choice__isnull=False) | Q(is_skipped=True)).values("question_id").distinct().count()
    remaining = max(total_questions - seen_questions, 0)
    percent_correct = round((correct / attempted) * 100) if attempted else 0
    recent_attempts = request.user.quiz_attempts.filter(is_completed=True)[:5]

    return render(
        request,
        "core/home.html",
        {
            "attempted": attempted,
            "correct": correct,
            "percent_correct": percent_correct,
            "remaining": remaining,
            "total_questions": total_questions,
            "recent_attempts": recent_attempts,
        },
    )


@login_required
def quiz_start(request):
    form = QuizStartForm(request.POST or None)
    available_count = Question.objects.count()
    mode = request.GET.get("mode")
    if mode not in {"species", "system"}:
        mode = None

    if request.method == "POST" and form.is_valid():
        questions = Question.objects.prefetch_related("choices").all()
        species = form.cleaned_data["species"]
        systems = form.cleaned_data["systems"]

        if "all" in species:
            species = []
        if "all" in systems:
            systems = []

        if species:
            questions = questions.filter(species__in=species)
        if systems:
            questions = questions.filter(system__in=systems)

        question_ids = list(questions.values_list("id", flat=True))
        random.shuffle(question_ids)
        requested_count = form.cleaned_data["question_count"]
        if requested_count != "all":
            question_ids = question_ids[: int(requested_count)]

        if not question_ids:
            messages.warning(request, "No questions match those filters yet.")
            return redirect("quiz_start")

        attempt = QuizAttempt.objects.create(
            user=request.user,
            total_questions=len(question_ids),
            question_order=question_ids,
        )
        request.session[f"quiz_{attempt.id}_index"] = 0
        return redirect("quiz_question", attempt_id=attempt.id)

    return render(
        request,
        "core/quiz_start.html",
        {
            "form": form,
            "available_count": available_count,
            "mode": mode,
            "species_choices": [("all", "All species")] + SPECIES_CHOICES,
            "system_choices": [("all", "All systems")] + SYSTEM_CHOICES,
        },
    )


@login_required
def quiz_question(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    question_ids = attempt.question_order or []
    index_key = f"quiz_{attempt.id}_index"
    index = request.session.get(index_key, 0)

    if attempt.is_completed or index >= len(question_ids):
        if not attempt.is_completed:
            attempt.complete()
        request.session.pop(index_key, None)
        return render(request, "core/quiz_complete.html", {"attempt": attempt})

    question = get_object_or_404(Question.objects.prefetch_related("choices"), id=question_ids[index])
    answer, _ = UserAnswer.objects.get_or_create(quiz_attempt=attempt, question=question)
    reveal = answer.selected_choice_id is not None or answer.is_skipped

    if request.method == "POST" and not reveal:
        action = request.POST.get("action")
        if action == "skip":
            answer.is_skipped = True
            answer.is_correct = False
            answer.save(update_fields=["is_skipped", "is_correct"])
        else:
            choice = question.choices.filter(id=request.POST.get("choice")).first()
            if not choice:
                messages.warning(request, "Choose an answer or skip this question.")
                return redirect("quiz_question", attempt_id=attempt.id)
            answer.selected_choice = choice
            answer.is_correct = choice.is_correct
            answer.is_skipped = False
            answer.save(update_fields=["selected_choice", "is_correct", "is_skipped"])
        answer.refresh_from_db()
        reveal = True

    if request.method == "POST" and request.POST.get("action") == "next" and reveal:
        request.session[index_key] = index + 1
        return redirect("quiz_question", attempt_id=attempt.id)

    correct_choice = question.choices.filter(is_correct=True).first() if reveal else None
    return render(
        request,
        "core/quiz_question.html",
        {
            "attempt": attempt,
            "answer": answer,
            "question": question,
            "choices": question.choices.all(),
            "correct_choice": correct_choice,
            "index": index + 1,
            "reveal": reveal,
        },
    )


@login_required
def quiz_stop(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    if not attempt.is_completed:
        answered_ids = set(attempt.answers.values_list("question_id", flat=True))
        missing_answers = [
            UserAnswer(quiz_attempt=attempt, question_id=question_id, is_skipped=True, is_correct=False)
            for question_id in attempt.question_order
            if question_id not in answered_ids
        ]
        UserAnswer.objects.bulk_create(missing_answers)
        attempt.answers.filter(selected_choice__isnull=True, is_skipped=False).update(is_skipped=True, is_correct=False)
        attempt.complete()
    request.session.pop(f"quiz_{attempt.id}_index", None)
    messages.info(request, "Quiz stopped and saved.")
    return redirect("home")


@login_required
def study_resources(request):
    resources = StudyResource.objects.all()
    species = request.GET.get("species")
    system = request.GET.get("system")
    if species:
        resources = resources.filter(Q(species=species) | Q(species=""))
    if system:
        resources = resources.filter(Q(system=system) | Q(system=""))
    return render(
        request,
        "core/study.html",
        {"resources": resources, "species_choices": SPECIES_CHOICES, "system_choices": SYSTEM_CHOICES},
    )


@login_required
def flashcards(request):
    cards = Flashcard.objects.filter(Q(owner__isnull=True) | Q(owner=request.user))
    deck = request.GET.get("deck", "all")
    if deck == "private":
        cards = cards.filter(owner=request.user)
    species = request.GET.get("species")
    system = request.GET.get("system")
    if species:
        cards = cards.filter(Q(species=species) | Q(species=""))
    if system:
        cards = cards.filter(Q(system=system) | Q(system=""))
    cards = list(cards)

    for card in cards:
        FlashcardReview.objects.get_or_create(user=request.user, flashcard=card)

    create_form = FlashcardForm()
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "create":
            create_form = FlashcardForm(request.POST)
            if create_form.is_valid():
                card = create_form.save(commit=False)
                card.owner = request.user
                card.save()
                FlashcardReview.objects.create(user=request.user, flashcard=card)
                messages.success(request, "Private flashcard added to your deck.")
                return redirect("flashcards")
        elif action == "review":
            card = get_object_or_404(
                Flashcard.objects.filter(Q(owner__isnull=True) | Q(owner=request.user)),
                id=request.POST.get("card_id"),
            )
            rating = request.POST.get("rating")
            valid_ratings = {choice for choice, _ in FlashcardReview.RATING_CHOICES}
            if rating not in valid_ratings:
                messages.warning(request, "Choose a review rating.")
                return redirect(f"{request.path}?{request.GET.urlencode()}")
            review, _ = FlashcardReview.objects.get_or_create(user=request.user, flashcard=card)
            review.schedule(rating)
            messages.success(request, "Reminder updated.")
            return redirect(f"{request.path}?{request.GET.urlencode()}")

    review_map = {
        review.flashcard_id: review
        for review in FlashcardReview.objects.filter(user=request.user, flashcard__in=cards)
    }
    card_items = sorted(
        [{"card": card, "review": review_map.get(card.id)} for card in cards],
        key=lambda item: (
            item["review"].next_review_at > timezone.now() if item["review"] else True,
            item["review"].next_review_at if item["review"] else timezone.now(),
        ),
    )
    due_count = sum(
        1
        for item in card_items
        if item["review"] and (item["review"].is_due or item["review"].review_count == 0)
    )
    new_count = sum(1 for item in card_items if item["review"] and item["review"].review_count == 0)
    learning_count = sum(1 for item in card_items if item["review"] and item["review"].review_count > 0 and item["review"].is_due)
    private_count = sum(1 for item in card_items if item["card"].owner_id == request.user.id)
    upcoming_reviews = (
        FlashcardReview.objects.filter(user=request.user, flashcard__in=cards, next_review_at__gt=timezone.now())
        .select_related("flashcard")
        .order_by("next_review_at")[:5]
    )
    return render(
        request,
        "core/flashcards.html",
        {
            "card_items": card_items,
            "create_form": create_form,
            "due_count": due_count,
            "new_count": new_count,
            "learning_count": learning_count,
            "private_count": private_count,
            "upcoming_reviews": upcoming_reviews,
            "species_choices": SPECIES_CHOICES,
            "system_choices": SYSTEM_CHOICES,
        },
    )


def forum_list(request):
    topics = ForumTopic.objects.annotate(reply_count=Count("replies"))
    return render(request, "core/forum_list.html", {"topics": topics})


def topic_detail(request, topic_id):
    topic = get_object_or_404(ForumTopic.objects.select_related("author"), id=topic_id)
    reply_form = ForumReplyForm(request.POST or None)
    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        if reply_form.is_valid():
            reply = reply_form.save(commit=False)
            reply.topic = topic
            reply.author = request.user
            reply.save()
            messages.success(request, "Reply posted.")
            return redirect("topic_detail", topic_id=topic.id)
    return render(request, "core/topic_detail.html", {"topic": topic, "reply_form": reply_form})


@login_required
def new_topic(request):
    form = ForumTopicForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        topic = form.save(commit=False)
        topic.author = request.user
        topic.save()
        messages.success(request, "Topic created.")
        return redirect("topic_detail", topic_id=topic.id)
    return render(request, "core/new_topic.html", {"form": form})
