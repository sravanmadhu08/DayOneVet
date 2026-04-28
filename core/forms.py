from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import (
    Flashcard,
    ForumReply,
    ForumTopic,
    SPECIES_CHOICES,
    SYSTEM_CHOICES,
    UserProfile,
)

SPECIES_FILTER_CHOICES = [("all", "All species")] + SPECIES_CHOICES
SYSTEM_FILTER_CHOICES = [("all", "All systems")] + SYSTEM_CHOICES


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=False)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class QuizStartForm(forms.Form):
    species = forms.MultipleChoiceField(
        choices=SPECIES_FILTER_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    systems = forms.MultipleChoiceField(
        choices=SYSTEM_FILTER_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Body systems",
    )
    question_count = forms.ChoiceField(
        choices=[
            ("5", "5"),
            ("10", "10"),
            ("20", "20"),
            ("30", "30"),
            ("60", "60"),
            ("100", "100"),
            ("all", "All available questions"),
        ],
        initial="10",
        label="Number of questions",
    )


class FlashcardForm(forms.ModelForm):
    class Meta:
        model = Flashcard
        fields = ["front", "back", "species", "system"]
        widgets = {
            "front": forms.Textarea(attrs={"rows": 3, "placeholder": "Question, prompt, or clinical clue"}),
            "back": forms.Textarea(attrs={"rows": 4, "placeholder": "Answer, explanation, or memory hook"}),
        }


class UserProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)
    email = forms.EmailField(required=False)

    class Meta:
        model = UserProfile
        fields = [
            "display_name",
            "profession",
            "target_exam_date",
            "weekly_goal_questions",
            "first_name",
            "last_name",
            "email",
        ]
        widgets = {
            "target_exam_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["first_name"].initial = self.user.first_name
        self.fields["last_name"].initial = self.user.last_name
        self.fields["email"].initial = self.user.email

    def save(self, commit=True):
        profile = super().save(commit=False)
        self.user.first_name = self.cleaned_data.get("first_name", "")
        self.user.last_name = self.cleaned_data.get("last_name", "")
        self.user.email = self.cleaned_data.get("email", "")
        if commit:
            self.user.save(update_fields=["first_name", "last_name", "email"])
            profile.save()
        return profile


class ThemePreferenceForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ["theme_scheme", "theme_mode"]


class QuestionImportForm(forms.Form):
    import_file = forms.FileField(
        label="Question file",
        help_text="Upload a .json or .docx file.",
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        label="Validate only",
        help_text="Preview the import without saving questions.",
    )
    skip_duplicates = forms.BooleanField(
        required=False,
        initial=True,
        label="Skip duplicate question text",
    )


class ForumTopicForm(forms.ModelForm):
    class Meta:
        model = ForumTopic
        fields = ["title", "body"]


class ForumReplyForm(forms.ModelForm):
    class Meta:
        model = ForumReply
        fields = ["body"]
