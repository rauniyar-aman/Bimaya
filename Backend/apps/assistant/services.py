"""Assistant business logic, kept out of the views.

Two independent halves:

* :func:`recommend_policies` — a deterministic, rule-based ranking over the
  live public catalogue. No LLM: it cannot invent a policy or misquote a
  premium, it is instant, private, and always available at no cost.

* :func:`answer_question` — a free-form insurance Q&A backed by an LLM, wired
  behind a provider seam (``AI_CHAT_PROVIDER``) and an off-by-default feature
  flag (``AI_CHAT_ENABLED``), mirroring ``apps/notifications/sms.py``. It ships
  dormant and only calls out once a key is configured. No customer PII is ever
  sent to the provider — only the typed question, a few prior turns, and a
  summary of the public catalogue.
"""

import logging
from decimal import Decimal

from django.conf import settings

from apps.policies.models import InsuranceCategory, Policy

from .exceptions import AssistantUnavailable

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Part A — rule-based recommendations (no LLM, always on)
# ---------------------------------------------------------------------------

# Scoring weights. Documented and deterministic so results are explainable and
# reproducible. They sum to 100 when every signal is present; signals that do
# not apply to a given query (e.g. no budget given) are simply skipped and the
# remaining weights are renormalised.
_WEIGHTS = {
    "budget": 35,      # how comfortably the premium fits the stated budget
    "coverage": 30,    # how well the sum assured meets the requested minimum
    "category": 25,    # exact category match
    "featured": 10,    # small nudge toward popular/curated plans
}


def recommend_policies(
    *,
    category=None,
    budget_max=None,
    age=None,
    coverage_min=None,
    term_max=None,
    limit=6,
):
    """Rank public policies against a customer's stated needs.

    All criteria are optional. ``category`` may be a slug or an id. Returns a
    list of ``Policy`` instances (top ``limit`` by score) each annotated with
    two transient attributes the serializer reads:

    * ``match_score`` — an integer 0–100.
    * ``reasons`` — a short list of plain-language strings.

    Hard filters (budget/age/coverage/term/category) exclude policies that
    cannot fit at all; the score then ranks whatever remains.
    """
    qs = Policy.objects.public().select_related("provider", "category")

    category_obj = _resolve_category(category)
    if category_obj is not None:
        qs = qs.filter(category=category_obj)

    if budget_max is not None:
        qs = qs.filter(premium__lte=budget_max)

    if coverage_min is not None:
        qs = qs.filter(coverage_amount__gte=coverage_min)

    if term_max is not None:
        qs = qs.filter(term_months__lte=term_max)

    if age is not None:
        # Keep policies whose age band includes the customer (nulls = no bound).
        from django.db.models import Q

        qs = qs.filter(
            Q(min_age__isnull=True) | Q(min_age__lte=age)
        ).filter(Q(max_age__isnull=True) | Q(max_age__gte=age))

    scored = []
    for policy in qs:
        score, reasons = _score_policy(
            policy,
            budget_max=budget_max,
            coverage_min=coverage_min,
            category_obj=category_obj,
        )
        policy.match_score = score
        policy.reasons = reasons
        scored.append(policy)

    # Highest score first; ties fall back to featured then cheaper premium.
    scored.sort(
        key=lambda p: (p.match_score, p.is_featured, -p.premium),
        reverse=True,
    )
    return scored[:limit]


def _resolve_category(category):
    """Accept a slug, an id, or ``None`` and return a category or ``None``."""
    if category in (None, ""):
        return None
    lookup = {"pk": category} if str(category).isdigit() else {"slug": category}
    return InsuranceCategory.objects.filter(is_active=True, **lookup).first()


def _score_policy(policy, *, budget_max, coverage_min, category_obj):
    """Return ``(int_score, reasons)`` for one policy against the query."""
    parts = {}
    reasons = []

    if budget_max is not None:
        budget = Decimal(str(budget_max))
        if policy.premium <= budget:
            # Closer to (but under) budget scores full marks; well under is fine.
            ratio = float(policy.premium / budget) if budget else 1.0
            parts["budget"] = 1.0 if ratio <= 1 else 0.0
            reasons.append("Fits your budget")
        else:
            parts["budget"] = 0.0

    if coverage_min is not None:
        target = Decimal(str(coverage_min))
        if policy.coverage_amount >= target:
            parts["coverage"] = 1.0
            reasons.append("Meets your coverage need")
        else:
            # Partial credit for getting close.
            parts["coverage"] = max(
                0.0, float(policy.coverage_amount / target) if target else 0.0
            )

    if category_obj is not None:
        matched = policy.category_id == category_obj.id
        parts["category"] = 1.0 if matched else 0.0
        if matched:
            reasons.append(f"{category_obj.name} cover")

    # Featured is always available as a light signal.
    parts["featured"] = 1.0 if policy.is_featured else 0.0
    if policy.is_featured:
        reasons.append("Popular plan")

    # Renormalise over only the signals that applied to this query.
    total_weight = sum(_WEIGHTS[k] for k in parts)
    if total_weight == 0:
        return 0, reasons
    earned = sum(_WEIGHTS[k] * frac for k, frac in parts.items())
    score = round(earned / total_weight * 100)

    if not reasons:
        reasons.append("Available on Bimaya")
    return score, reasons


# ---------------------------------------------------------------------------
# Part B — LLM chat assistant (off by default, provider seam)
# ---------------------------------------------------------------------------

_MAX_HISTORY_TURNS = 6
_MAX_CATALOG_POLICIES = 40

_SYSTEM_INSTRUCTION = (
    "You are Bimaya's friendly insurance advisor for customers in Nepal. "
    "Only discuss insurance and the plans listed in the catalogue provided to "
    "you. When suggesting cover, recommend from that catalogue and mention the "
    "plan name. Amounts are in Nepali Rupees (NPR). Never ask for, store, or "
    "repeat sensitive identifiers such as citizenship numbers, national ID, "
    "card numbers, or specific medical records — if the user shares any, gently "
    "tell them not to and continue with general guidance. If you are unsure or "
    "the question is outside insurance, say so briefly and suggest contacting "
    "Bimaya support. Keep answers concise and easy to understand."
)


def chat_enabled():
    """The chat assistant only runs when switched on *and* a key is present."""
    return bool(getattr(settings, "AI_CHAT_ENABLED", False)) and bool(
        getattr(settings, "GEMINI_API_KEY", "")
    )


def answer_question(message, history=None):
    """Answer one insurance question. Returns the assistant's reply text.

    ``history`` is an optional list of ``{"role", "content"}`` turns; it is
    capped server-side to bound token use. Raises :class:`AssistantUnavailable`
    on any provider error so the request never 500s and no internal detail
    leaks to the client.
    """
    history = _cap_history(history)
    catalog = _catalog_summary()
    provider = getattr(settings, "AI_CHAT_PROVIDER", "gemini")
    try:
        if provider == "gemini":
            return _gemini_reply(message, history, catalog)
        # Provider seam: a future "claude"/"openai" branch drops in here.
        raise ValueError(f"Unknown AI_CHAT_PROVIDER: {provider!r}")
    except AssistantUnavailable:
        raise
    except Exception:
        # Never surface provider internals or user text in logs.
        logger.exception("Assistant provider %r failed", provider)
        raise AssistantUnavailable()


def _cap_history(history):
    """Keep only the last few valid turns to bound tokens and cost."""
    if not history:
        return []
    valid = [
        {"role": t["role"], "content": t["content"]}
        for t in history
        if isinstance(t, dict)
        and t.get("role") in ("user", "assistant")
        and isinstance(t.get("content"), str)
        and t["content"].strip()
    ]
    return valid[-_MAX_HISTORY_TURNS:]


def _catalog_summary():
    """A compact, PII-free text summary of the public catalogue for grounding."""
    policies = (
        Policy.objects.public()
        .select_related("category")
        .order_by("-is_featured", "category__name", "name")[:_MAX_CATALOG_POLICIES]
    )
    lines = []
    for p in policies:
        lines.append(
            f"- {p.name} ({p.category.name}): premium NPR {p.premium} "
            f"{p.get_premium_frequency_display().lower()}, "
            f"covers up to NPR {p.coverage_amount}, term {p.term_months} months."
        )
    if not lines:
        return "The catalogue is currently empty."
    return "Available plans on Bimaya:\n" + "\n".join(lines)


def _gemini_reply(message, history, catalog):
    """Call the Google Gemini API and return the reply text.

    Uses the official ``google-genai`` SDK. The system instruction and the
    catalogue summary ground the model in Bimaya's real plans; conversation
    history is replayed as prior turns.
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:  # pragma: no cover - only when dep missing
        logger.error("google-genai is not installed: %s", exc)
        raise AssistantUnavailable()

    client = genai.Client(api_key=settings.GEMINI_API_KEY)

    contents = []
    for turn in history:
        role = "model" if turn["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=turn["content"])])
        )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=message)])
    )

    response = client.models.generate_content(
        model=getattr(settings, "GEMINI_MODEL", "gemini-flash-latest"),
        contents=contents,
        config=types.GenerateContentConfig(
            system_instruction=f"{_SYSTEM_INSTRUCTION}\n\n{catalog}",
            max_output_tokens=800,
            temperature=0.4,
        ),
    )

    text = (getattr(response, "text", None) or "").strip()
    if not text:
        raise AssistantUnavailable()
    return text
