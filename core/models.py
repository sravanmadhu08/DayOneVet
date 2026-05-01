from django.conf import settings
from django.db import models
from django.utils import timezone


SPECIES_CHOICES = [
    ("general", "General"),
    ("dog", "Dog"),
    ("cat", "Cat"),
    ("horse", "Horse"),
    ("cow", "Cow"),
    ("sheep", "Sheep"),
    ("goat", "Goat"),
    ("pig", "Pig"),
    ("poultry", "Poultry"),
    ("exotic", "Exotic"),
    ("wildlife", "Wildlife"),
]

SYSTEM_CHOICES = [
    ("general", "General"),
    ("respiratory", "Respiratory"),
    ("neurology", "Neurology"),
    ("cardiology", "Cardiology"),
    ("gastrointestinal", "Gastrointestinal"),
    ("musculoskeletal", "Musculoskeletal"),
    ("reproductive", "Reproductive"),
    ("urinary", "Urinary"),
    ("dermatology", "Dermatology"),
    ("ophthalmology", "Ophthalmology"),
    ("endocrine", "Endocrine"),
    ("infectious_disease", "Infectious disease"),
    ("pharmacology", "Pharmacology"),
    ("surgery", "Surgery"),
    ("anaesthesia", "Anaesthesia"),
    ("emergency_critical_care", "Emergency and critical care"),
    ("public_health", "Public health"),
]


class UserProfile(models.Model):
    FREE = "free"
    PRO = "pro"
    INSTITUTION = "institution"

    PLAN_CHOICES = [
        (FREE, "Free"),
        (PRO, "Pro"),
        (INSTITUTION, "Institution"),
    ]

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (TRIALING, "Trialing"),
        (PAST_DUE, "Past due"),
        (CANCELED, "Canceled"),
    ]

    CLASSIC = "classic"
    OCEAN = "ocean"
    PLUM = "plum"
    CONTRAST = "contrast"

    THEME_CHOICES = [
        (CLASSIC, "Classic"),
        (OCEAN, "Ocean"),
        (PLUM, "Plum"),
        (CONTRAST, "High contrast"),
    ]

    LIGHT = "light"
    DARK = "dark"

    THEME_MODE_CHOICES = [
        (LIGHT, "Light"),
        (DARK, "Dark"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")
    display_name = models.CharField(max_length=120, blank=True)
    profession = models.CharField(max_length=120, blank=True)
    target_exam_date = models.DateField(null=True, blank=True)
    weekly_goal_questions = models.PositiveIntegerField(default=50)
    theme_scheme = models.CharField(max_length=30, choices=THEME_CHOICES, default=CLASSIC)
    theme_mode = models.CharField(max_length=20, choices=THEME_MODE_CHOICES, default=LIGHT)
    plan = models.CharField(max_length=30, choices=PLAN_CHOICES, default=FREE)
    subscription_status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=TRIALING)
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    stripe_subscription_id = models.CharField(max_length=120, blank=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        return self.display_name or self.user.get_full_name() or self.user.username

    @property
    def is_paid(self):
        return self.plan in {self.PRO, self.INSTITUTION} and self.subscription_status in {self.ACTIVE, self.TRIALING}

    def __str__(self):
        return f"{self.user} profile"


class Question(models.Model):
    text = models.TextField()
    image = models.FileField(upload_to="question_images/", blank=True, null=True)
    species = models.CharField(max_length=40, choices=SPECIES_CHOICES)
    system = models.CharField(max_length=60, choices=SYSTEM_CHOICES)
    explanation = models.TextField()
    exam_tip = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.text[:80]


class Choice(models.Model):
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="choices")
    text = models.CharField(max_length=500)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return self.text[:80]


class QuizAttempt(models.Model):
    PRACTICE = "practice"
    TIMED = "timed"

    QUIZ_MODE_CHOICES = [
        (PRACTICE, "Practice"),
        (TIMED, "Timed exam"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="quiz_attempts")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    exam_mode = models.CharField(max_length=20, choices=QUIZ_MODE_CHOICES, default=PRACTICE)
    duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    total_questions = models.PositiveIntegerField(default=0)
    attempted_count = models.PositiveIntegerField(default=0)
    correct_count = models.PositiveIntegerField(default=0)
    skipped_count = models.PositiveIntegerField(default=0)
    is_completed = models.BooleanField(default=False)
    question_order = models.JSONField(default=list, blank=True)
    questions = models.ManyToManyField(Question, through="UserAnswer", related_name="quiz_attempts")

    class Meta:
        ordering = ["-started_at"]

    @property
    def percent_correct(self):
        if self.attempted_count == 0:
            return 0
        return round((self.correct_count / self.attempted_count) * 100)

    @property
    def is_timed(self):
        return self.exam_mode == self.TIMED and self.duration_minutes

    @property
    def ends_at(self):
        if not self.is_timed:
            return None
        return self.started_at + timezone.timedelta(minutes=self.duration_minutes)

    @property
    def remaining_seconds(self):
        if not self.ends_at:
            return None
        return max(int((self.ends_at - timezone.now()).total_seconds()), 0)

    @property
    def time_has_expired(self):
        return self.is_timed and self.remaining_seconds == 0

    def complete(self):
        answers = self.answers.all()
        self.attempted_count = answers.filter(selected_choice__isnull=False).count()
        self.correct_count = answers.filter(is_correct=True).count()
        self.skipped_count = answers.filter(is_skipped=True).count()
        self.completed_at = timezone.now()
        self.is_completed = True
        self.save(update_fields=[
            "attempted_count",
            "correct_count",
            "skipped_count",
            "completed_at",
            "is_completed",
        ])

    def __str__(self):
        return f"{self.user} - {self.started_at:%Y-%m-%d %H:%M}"


class UserAnswer(models.Model):
    quiz_attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name="answers")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="user_answers")
    selected_choice = models.ForeignKey(Choice, null=True, blank=True, on_delete=models.SET_NULL)
    is_correct = models.BooleanField(default=False)
    is_skipped = models.BooleanField(default=False)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("quiz_attempt", "question")
        ordering = ["answered_at"]

    def __str__(self):
        return f"{self.quiz_attempt} - {self.question_id}"


class StudyResource(models.Model):
    GUIDELINE = "guideline"
    EXTERNAL_LINK = "external_link"

    RESOURCE_TYPE_CHOICES = [
        (GUIDELINE, "General guideline"),
        (EXTERNAL_LINK, "External link"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    resource_type = models.CharField(max_length=30, choices=RESOURCE_TYPE_CHOICES, default=GUIDELINE)
    file = models.FileField(upload_to="study_resources/", blank=True, null=True)
    external_url = models.URLField(blank=True)
    species = models.CharField(max_length=40, choices=SPECIES_CHOICES, blank=True)
    system = models.CharField(max_length=60, choices=SYSTEM_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["resource_type", "title"]

    def __str__(self):
        return self.title


class WeeklyStudyTopic(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    week_label = models.CharField(max_length=120)
    display_order = models.PositiveIntegerField(default=0)
    species = models.CharField(max_length=40, choices=SPECIES_CHOICES, blank=True)
    system = models.CharField(max_length=60, choices=SYSTEM_CHOICES, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["display_order", "week_label", "title"]

    def __str__(self):
        return f"{self.week_label} - {self.title}"


class WeeklyTopicAttachment(models.Model):
    topic = models.ForeignKey(WeeklyStudyTopic, on_delete=models.CASCADE, related_name="attachments")
    title = models.CharField(max_length=200)
    file = models.FileField(upload_to="weekly_topics/")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["display_order", "title"]

    def __str__(self):
        return self.title


class WeeklyTopicProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="weekly_topic_progress")
    topic = models.ForeignKey(WeeklyStudyTopic, on_delete=models.CASCADE, related_name="progress")
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("user", "topic")
        ordering = ["-completed_at"]

    def __str__(self):
        return f"{self.user} completed {self.topic}"


class Flashcard(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="private_flashcards",
        null=True,
        blank=True,
    )
    front = models.TextField()
    back = models.TextField()
    species = models.CharField(max_length=40, choices=SPECIES_CHOICES, blank=True)
    system = models.CharField(max_length=60, choices=SYSTEM_CHOICES, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.front[:80]


class FlashcardReview(models.Model):
    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"

    RATING_CHOICES = [
        (AGAIN, "Again"),
        (HARD, "Hard"),
        (GOOD, "Good"),
        (EASY, "Easy"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="flashcard_reviews")
    flashcard = models.ForeignKey(Flashcard, on_delete=models.CASCADE, related_name="reviews")
    next_review_at = models.DateTimeField(default=timezone.now)
    interval_days = models.PositiveIntegerField(default=0)
    review_count = models.PositiveIntegerField(default=0)
    last_rating = models.CharField(max_length=20, choices=RATING_CHOICES, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("user", "flashcard")
        ordering = ["next_review_at"]

    @property
    def is_due(self):
        return self.next_review_at <= timezone.now()

    def schedule(self, rating):
        current_interval = max(self.interval_days, 1)
        intervals = {
            self.AGAIN: 0,
            self.HARD: 1 if self.review_count == 0 else current_interval + 1,
            self.GOOD: 3 if self.review_count == 0 else current_interval * 2,
            self.EASY: 7 if self.review_count == 0 else current_interval * 3,
        }
        self.last_rating = rating
        self.interval_days = intervals[rating]
        self.reviewed_at = timezone.now()
        self.review_count += 1
        if rating == self.AGAIN:
            self.next_review_at = self.reviewed_at + timezone.timedelta(minutes=10)
        else:
            self.next_review_at = self.reviewed_at + timezone.timedelta(days=self.interval_days)
        self.save(update_fields=["last_rating", "interval_days", "review_count", "reviewed_at", "next_review_at"])

    def __str__(self):
        return f"{self.user} - {self.flashcard}"


class ForumTopic(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="forum_topics")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self):
        return self.title


class ForumReply(models.Model):
    topic = models.ForeignKey(ForumTopic, on_delete=models.CASCADE, related_name="replies")
    body = models.TextField()
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="forum_replies")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        verbose_name_plural = "Forum replies"

    def __str__(self):
        return f"Reply by {self.author} on {self.topic}"


class SiteSettings(models.Model):
    product_name = models.CharField(max_length=120, default="RCVS Prep")
    tagline = models.CharField(max_length=180, default="Clinical exam practice")
    header_brand_text = models.CharField(max_length=120, default="RCVS Prep")
    logo_text = models.CharField(max_length=12, default="RC")
    logo_image = models.ImageField(upload_to="site_brand/", blank=True, null=True)
    landing_headline = models.CharField(max_length=200, default="Clinical exam prep for modern veterinary teams")
    landing_subheadline = models.TextField(default="Prepare with focused MCQs, flashcards, and study resources designed for RCVS success.")
    support_text = models.CharField(max_length=180, blank=True, default="Support: support@example.com")
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Site settings"
        verbose_name_plural = "Site settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return "Site settings"
