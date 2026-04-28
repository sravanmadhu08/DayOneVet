from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path

from core import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.landing, name="landing"),
    path("register/", views.register, name="register"),
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.profile, name="profile"),
    path("home/", views.home, name="home"),
    path("quiz/start/", views.quiz_start, name="quiz_start"),
    path("quiz/<int:attempt_id>/question/", views.quiz_question, name="quiz_question"),
    path("quiz/<int:attempt_id>/stop/", views.quiz_stop, name="quiz_stop"),
    path("study/", views.study_resources, name="study"),
    path("flashcards/", views.flashcards, name="flashcards"),
    path("forum/", views.forum_list, name="forum"),
    path("forum/topic/<int:topic_id>/", views.topic_detail, name="topic_detail"),
    path("forum/new/", views.new_topic, name="new_topic"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
