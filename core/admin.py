from django.contrib import admin
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.urls import path, reverse

from .forms import QuestionImportForm
from .models import (
    Choice,
    Flashcard,
    FlashcardReview,
    ForumReply,
    ForumTopic,
    Question,
    QuizAttempt,
    StudyResource,
    UserAnswer,
    UserProfile,
    WeeklyStudyTopic,
    WeeklyTopicAttachment,
    WeeklyTopicProgress,
)
from .question_importer import load_and_validate_questions


class ChoiceInline(admin.TabularInline):
    model = Choice
    extra = 4


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "display_name", "plan", "subscription_status", "weekly_goal_questions", "target_exam_date")
    list_filter = ("plan", "subscription_status")
    search_fields = ("user__username", "user__email", "display_name", "profession")


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("text", "species", "system", "created_at")
    list_filter = ("species", "system")
    search_fields = ("text", "explanation", "exam_tip")
    inlines = [ChoiceInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "import/",
                self.admin_site.admin_view(self.import_questions_view),
                name="core_question_import",
            ),
        ]
        return custom_urls + urls

    def import_questions_view(self, request):
        form = QuestionImportForm(request.POST or None, request.FILES or None)
        preview = None

        if request.method == "POST" and form.is_valid():
            uploaded_file = form.cleaned_data["import_file"]
            try:
                questions = load_and_validate_questions(uploaded_file, uploaded_file.name)
                existing_texts = set()
                if form.cleaned_data["skip_duplicates"]:
                    existing_texts = set(
                        Question.objects.filter(text__in=[item["text"] for item in questions]).values_list("text", flat=True)
                    )
                    questions = [item for item in questions if item["text"] not in existing_texts]

                preview = {
                    "questions": questions[:10],
                    "count": len(questions),
                    "duplicates": len(existing_texts),
                }

                if form.cleaned_data["dry_run"]:
                    messages.info(request, f"Validation passed. {len(questions)} questions ready to import.")
                else:
                    with transaction.atomic():
                        for item in questions:
                            question = Question.objects.create(
                                text=item["text"],
                                species=item["species"],
                                system=item["system"],
                                explanation=item["explanation"],
                                exam_tip=item.get("exam_tip", ""),
                            )
                            for choice in item["choices"]:
                                Choice.objects.create(
                                    question=question,
                                    text=choice["text"],
                                    is_correct=choice["is_correct"],
                                )
                    messages.success(request, f"Imported {len(questions)} questions.")
                    return redirect(reverse("admin:core_question_changelist"))
            except Exception as exc:
                messages.error(request, str(exc))

        context = {
            **self.admin_site.each_context(request),
            "title": "Import questions",
            "form": form,
            "preview": preview,
            "opts": self.model._meta,
        }
        return render(request, "admin/core/question/import_questions.html", context)


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ("user", "started_at", "exam_mode", "duration_minutes", "is_completed", "total_questions", "attempted_count", "correct_count", "skipped_count")
    list_filter = ("exam_mode", "is_completed", "started_at")
    readonly_fields = ("started_at", "completed_at", "question_order")


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ("quiz_attempt", "question", "selected_choice", "is_correct", "is_skipped", "answered_at")
    list_filter = ("is_correct", "is_skipped", "answered_at")


@admin.register(StudyResource)
class StudyResourceAdmin(admin.ModelAdmin):
    list_display = ("title", "resource_type", "species", "system", "created_at")
    list_filter = ("resource_type", "species", "system")
    search_fields = ("title", "description", "external_url")


class WeeklyTopicAttachmentInline(admin.TabularInline):
    model = WeeklyTopicAttachment
    extra = 1


@admin.register(WeeklyStudyTopic)
class WeeklyStudyTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "week_label", "display_order", "species", "system", "is_active", "created_at")
    list_filter = ("week_label", "species", "system", "is_active")
    search_fields = ("title", "description", "week_label")
    inlines = [WeeklyTopicAttachmentInline]


@admin.register(WeeklyTopicProgress)
class WeeklyTopicProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "topic", "completed_at")
    list_filter = ("completed_at", "topic__week_label")
    search_fields = ("user__username", "user__email", "topic__title", "topic__week_label")


@admin.register(Flashcard)
class FlashcardAdmin(admin.ModelAdmin):
    list_display = ("front", "owner", "species", "system", "created_at")
    list_filter = ("owner", "species", "system")
    search_fields = ("front", "back")


@admin.register(FlashcardReview)
class FlashcardReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "flashcard", "next_review_at", "interval_days", "review_count", "last_rating")
    list_filter = ("last_rating", "next_review_at")


class ForumReplyInline(admin.StackedInline):
    model = ForumReply
    extra = 0


@admin.register(ForumTopic)
class ForumTopicAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "created_at", "updated_at")
    search_fields = ("title", "body")
    inlines = [ForumReplyInline]


@admin.register(ForumReply)
class ForumReplyAdmin(admin.ModelAdmin):
    list_display = ("topic", "author", "created_at")
    search_fields = ("body",)
