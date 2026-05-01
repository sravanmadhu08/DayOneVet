import random
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from .forms import (
    EmailOrUsernameAuthenticationForm,
    FlashcardForm,
    ForumReplyForm,
    ForumTopicForm,
    QuizStartForm,
    RegisterForm,
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
    WeeklyStudyTopic,
    WeeklyTopicProgress,
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
        next_url = request.POST.get("next") or request.GET.get("next")
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


class CustomLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailOrUsernameAuthenticationForm
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
    if request.method == "POST":
        if request.POST.get("action") == "profile":
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
    question_bank_progress = round((seen_questions / total_questions) * 100) if total_questions else 0
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
            "question_bank_progress": question_bank_progress,
            "recent_attempts": recent_attempts,
        },
    )


@login_required
def quiz_start(request):
    form = QuizStartForm(request.POST or None)
    done_question_ids = set(
        UserAnswer.objects.filter(quiz_attempt__user=request.user, is_correct=True).values_list("question_id", flat=True)
    )
    total_count = Question.objects.count()
    available_questions = Question.objects.exclude(id__in=done_question_ids)
    available_count = available_questions.count()
    done_count = len(done_question_ids)

    def build_count_items(choice_list, field_name):
        items = []
        for value, label in choice_list:
            total_for_value = Question.objects.filter(**{field_name: value}).count()
            available_for_value = available_questions.filter(**{field_name: value}).count()
            if total_for_value:
                items.append(
                    {
                        "value": value,
                        "label": label,
                        "available": available_for_value,
                        "done": max(total_for_value - available_for_value, 0),
                        "total": total_for_value,
                    }
                )
        return items

    species_counts = build_count_items(SPECIES_CHOICES, "species")
    system_counts = build_count_items(SYSTEM_CHOICES, "system")

    species_choice_map = {item["value"]: item for item in species_counts}
    system_choice_map = {item["value"]: item for item in system_counts}

    form.fields["species"].choices = [
        (value, f"{label} ({species_choice_map[value]['available']})") if value in species_choice_map else (value, label)
        for value, label in form.fields["species"].choices
    ]
    form.fields["systems"].choices = [
        (value, f"{label} ({system_choice_map[value]['available']})") if value in system_choice_map else (value, label)
        for value, label in form.fields["systems"].choices
    ]

    if request.method == "POST" and form.is_valid():
        questions = available_questions.prefetch_related("choices")
        selected_species = form.cleaned_data["species"]
        selected_system = form.cleaned_data["systems"]
        quiz_mode = form.cleaned_data["quiz_mode"]

        if selected_species and selected_species != "all":
            questions = questions.filter(species=selected_species)
        if selected_system and selected_system != "all":
            questions = questions.filter(system=selected_system)

        question_ids = list(questions.values_list("id", flat=True))
        random.shuffle(question_ids)
        requested_count = form.cleaned_data["question_count"]
        if requested_count != "all":
            question_ids = question_ids[: int(requested_count)]

        if not question_ids:
            messages.warning(request, "No unanswered questions match those filters yet.")
            return redirect("quiz_start")

        attempt = QuizAttempt.objects.create(
            user=request.user,
            exam_mode=quiz_mode,
            duration_minutes=int(form.cleaned_data["duration_minutes"]) if quiz_mode == QuizStartForm.TIMED else None,
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
            "done_count": done_count,
            "total_count": total_count,
            "species_counts": species_counts,
            "system_counts": system_counts,
        },
    )


@login_required
def quiz_done_pile(request):
    form = QuizStartForm(request.POST or None)
    done_question_ids = set(
        UserAnswer.objects.filter(quiz_attempt__user=request.user, is_correct=True).values_list("question_id", flat=True)
    )
    done_questions = Question.objects.filter(id__in=done_question_ids).prefetch_related("choices")
    done_count = done_questions.count()

    if request.method == "POST" and form.is_valid():
        questions = done_questions
        selected_species = form.cleaned_data["species"]
        selected_system = form.cleaned_data["systems"]
        quiz_mode = form.cleaned_data["quiz_mode"]

        if selected_species and selected_species != "all":
            questions = questions.filter(species=selected_species)
        if selected_system and selected_system != "all":
            questions = questions.filter(system=selected_system)

        question_ids = list(questions.values_list("id", flat=True))
        random.shuffle(question_ids)
        requested_count = form.cleaned_data["question_count"]
        if requested_count != "all":
            question_ids = question_ids[: int(requested_count)]

        if not question_ids:
            messages.warning(request, "No done-pile questions match those filters yet.")
            return redirect("quiz_done_pile")

        attempt = QuizAttempt.objects.create(
            user=request.user,
            exam_mode=quiz_mode,
            duration_minutes=int(form.cleaned_data["duration_minutes"]) if quiz_mode == QuizStartForm.TIMED else None,
            total_questions=len(question_ids),
            question_order=question_ids,
        )
        request.session[f"quiz_{attempt.id}_index"] = 0
        return redirect("quiz_question", attempt_id=attempt.id)

    species = request.GET.get("species")
    system = request.GET.get("system")
    filtered_questions = done_questions
    if species:
        filtered_questions = filtered_questions.filter(species=species)
    if system:
        filtered_questions = filtered_questions.filter(system=system)

    return render(
        request,
        "core/quiz_done_pile.html",
        {
            "form": form,
            "done_count": done_count,
            "questions": filtered_questions[:100],
            "filtered_count": filtered_questions.count(),
            "species_choices": SPECIES_CHOICES,
            "system_choices": SYSTEM_CHOICES,
        },
    )


@login_required
def quiz_question(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    question_ids = attempt.question_order or []
    index_key = f"quiz_{attempt.id}_index"
    index = request.session.get(index_key, 0)

    if attempt.time_has_expired and not attempt.is_completed:
        complete_attempt_with_missing_answers(attempt)
        request.session.pop(index_key, None)
        messages.info(request, "Time is up. Your timed exam has been saved.")
        return render(request, "core/quiz_complete.html", {"attempt": attempt})

    if attempt.is_completed or index >= len(question_ids):
        if not attempt.is_completed:
            complete_attempt_with_missing_answers(attempt)
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
        if attempt.is_timed:
            request.session[index_key] = index + 1
            return redirect("quiz_question", attempt_id=attempt.id)
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
            "remaining_seconds": attempt.remaining_seconds,
        },
    )


def complete_attempt_with_missing_answers(attempt):
    answered_ids = set(attempt.answers.values_list("question_id", flat=True))
    missing_answers = [
        UserAnswer(quiz_attempt=attempt, question_id=question_id, is_skipped=True, is_correct=False)
        for question_id in attempt.question_order
        if question_id not in answered_ids
    ]
    UserAnswer.objects.bulk_create(missing_answers)
    attempt.answers.filter(selected_choice__isnull=True, is_skipped=False).update(is_skipped=True, is_correct=False)
    attempt.complete()


@login_required
def quiz_stop(request, attempt_id):
    attempt = get_object_or_404(QuizAttempt, id=attempt_id, user=request.user)
    if not attempt.is_completed:
        complete_attempt_with_missing_answers(attempt)
    request.session.pop(f"quiz_{attempt.id}_index", None)
    messages.info(request, "Quiz stopped and saved.")
    return redirect("home")


@login_required
def study_resources(request):
    if request.method == "POST":
        topic = get_object_or_404(WeeklyStudyTopic, id=request.POST.get("topic_id"), is_active=True)
        progress, created = WeeklyTopicProgress.objects.get_or_create(user=request.user, topic=topic)
        if created:
            messages.success(request, "Weekly topic marked complete.")
        else:
            progress.delete()
            messages.info(request, "Weekly topic marked incomplete.")
        return redirect(f"{request.path}?{request.GET.urlencode()}" if request.GET else request.path)

    species = request.GET.get("species")
    system = request.GET.get("system")

    resources = StudyResource.objects.all()
    if species:
        resources = resources.filter(Q(species=species) | Q(species=""))
    if system:
        resources = resources.filter(Q(system=system) | Q(system=""))

    weekly_topics = list(
        WeeklyStudyTopic.objects.filter(is_active=True)
        .prefetch_related("attachments")
        .order_by("display_order", "week_label", "title")
    )
    completed_ids = set(
        WeeklyTopicProgress.objects.filter(user=request.user, topic__in=weekly_topics).values_list("topic_id", flat=True)
    )
    weekly_sections = []
    for topic in weekly_topics:
        topic.is_completed = topic.id in completed_ids
        if not weekly_sections or weekly_sections[-1]["label"] != topic.week_label:
            weekly_sections.append({"label": topic.week_label, "topics": []})
        weekly_sections[-1]["topics"].append(topic)

    guidelines = resources.filter(resource_type=StudyResource.GUIDELINE)
    external_links = resources.filter(resource_type=StudyResource.EXTERNAL_LINK)
    weekly_total = len(weekly_topics)
    weekly_completed = len(completed_ids)
    return render(
        request,
        "core/study.html",
        {
            "weekly_sections": weekly_sections,
            "weekly_total": weekly_total,
            "weekly_completed": weekly_completed,
            "weekly_remaining": max(weekly_total - weekly_completed, 0),
            "guidelines": guidelines,
            "external_links": external_links,
            "species_choices": SPECIES_CHOICES,
            "system_choices": SYSTEM_CHOICES,
        },
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
