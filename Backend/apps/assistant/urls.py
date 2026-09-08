"""Assistant routes, mounted at ``/api/v1/`` by :mod:`bimaya.urls`."""

from django.urls import path

from .views import ChatView, RecommendPoliciesView

urlpatterns = [
    path(
        "assistant/recommend/",
        RecommendPoliciesView.as_view(),
        name="assistant-recommend",
    ),
    path("assistant/chat/", ChatView.as_view(), name="assistant-chat"),
]
