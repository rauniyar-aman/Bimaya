"""Assistant endpoints.

* ``POST /api/v1/assistant/recommend/`` — public, rule-based policy picks.
* ``POST /api/v1/assistant/chat/`` — authenticated, LLM insurance Q&A (off by
  default until a provider key is configured).
"""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from . import services
from .exceptions import AssistantDisabled
from .serializers import (
    ChatRequestSerializer,
    RecommendationRequestSerializer,
    RecommendedPolicySerializer,
)

ASSISTANT_TAG = ["assistant"]


@extend_schema(
    tags=ASSISTANT_TAG,
    summary="Recommend policies (rule-based)",
    description=(
        "Ranks the public catalogue against optional criteria (category, "
        "budget, age, coverage, term). Deterministic and free — no LLM."
    ),
    request=RecommendationRequestSerializer,
    responses=RecommendedPolicySerializer(many=True),
    auth=[],
)
class RecommendPoliciesView(GenericAPIView):
    permission_classes = [AllowAny]
    serializer_class = RecommendationRequestSerializer
    throttle_scope = "ai_recommend"

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        picks = services.recommend_policies(**serializer.validated_data)
        return Response(
            RecommendedPolicySerializer(picks, many=True).data,
            status=status.HTTP_200_OK,
        )


@extend_schema(
    tags=ASSISTANT_TAG,
    summary="Ask the insurance assistant",
    description=(
        "Free-form insurance Q&A grounded in the public catalogue. Requires "
        "sign-in. Returns 400 `assistant_disabled` when the assistant is not "
        "switched on, or 503 `assistant_unavailable` on a provider outage."
    ),
    request=ChatRequestSerializer,
)
class ChatView(GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChatRequestSerializer
    throttle_scope = "ai_chat"

    def post(self, request):
        if not services.chat_enabled():
            raise AssistantDisabled()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        reply = services.answer_question(
            data["message"], data.get("history", [])
        )
        return Response({"reply": reply}, status=status.HTTP_200_OK)
