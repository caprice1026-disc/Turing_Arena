from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q, Sum
from django.shortcuts import render

from apps.quiz.models import SessionQuestion


User = get_user_model()


def ranking_view(request):
    phase1_rows = (
        SessionQuestion.objects.values("session__user")
        .annotate(
            total=Count("id", filter=Q(phase1_is_correct__isnull=False)),
            correct=Count("id", filter=Q(phase1_is_correct=True)),
        )
        .filter(total__gte=settings.RANKING_MIN_PHASE1)
        .order_by("-correct", "-total")
    )

    phase2_rows = (
        SessionQuestion.objects.filter(session__choice_count=4)
        .values("session__user")
        .annotate(
            total=Count("id", filter=Q(phase2_score__isnull=False)),
            points=Sum("phase2_score"),
        )
        .filter(total__gte=settings.RANKING_MIN_PHASE2)
        .order_by("-points", "-total")
    )

    users = {user.id: user for user in User.objects.filter(id__in=[row["session__user"] for row in phase1_rows] + [row["session__user"] for row in phase2_rows])}

    phase1_ranking = []
    for row in phase1_rows:
        user = users.get(row["session__user"])
        if not user:
            continue
        rate = row["correct"] / row["total"] * 100 if row["total"] else 0
        phase1_ranking.append({"user": user, "rate": rate, **row})

    phase2_ranking = []
    for row in phase2_rows:
        user = users.get(row["session__user"])
        if not user:
            continue
        points = row["points"] or 0
        rate = points / (row["total"] * 3) * 100 if row["total"] else 0
        phase2_ranking.append({"user": user, "rate": rate, "points": points, **row})

    return render(
        request,
        "ranking/index.html",
        {"phase1_ranking": phase1_ranking, "phase2_ranking": phase2_ranking},
    )

# Create your views here.
