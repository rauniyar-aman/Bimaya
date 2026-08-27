import django_filters

from .models import Policy


class PolicyFilter(django_filters.FilterSet):
    """Query filters for the public policy list.

    ``category`` matches on the category slug so the frontend can filter with
    the same slugs it uses in URLs. Price/coverage bounds are inclusive.
    """

    category = django_filters.CharFilter(field_name="category__slug", lookup_expr="exact")
    premium_min = django_filters.NumberFilter(field_name="premium", lookup_expr="gte")
    premium_max = django_filters.NumberFilter(field_name="premium", lookup_expr="lte")
    coverage_min = django_filters.NumberFilter(field_name="coverage_amount", lookup_expr="gte")
    featured = django_filters.BooleanFilter(field_name="is_featured")

    class Meta:
        model = Policy
        fields = ["category", "premium_frequency", "featured"]
