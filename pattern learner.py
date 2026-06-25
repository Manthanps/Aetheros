"""Merged campaign learning engine."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mynat_ai_system.backend.database.db_connection import engine as app_engine
from mynat_ai_system.backend.database.db_models import Campaign, VerifierReview
from mynat_ai_system.campaign_pattern_learner import load_patterns, upsert_patterns

SEASON_BY_MONTH = {
    1: "new_year",
    2: "winter_wellness",
    3: "holi",
    4: "summer_care",
    5: "summer_care",
    6: "monsoon_prep",
    7: "monsoon_care",
    8: "raksha_bandhan",
    9: "festive_prep",
    10: "diwali_prep",
    11: "wedding_season",
    12: "winter_gifting",
}


def learn_from_completed_campaigns(days: int = 180, persist: bool = True) -> dict[str, Any]:
    result = _learn(days, persist)
    return {"success": True, "service": "campaign_pattern_learner_engine", "params": {"days": days, "persist": persist}, **result}


def get_campaign_pattern_learners(days: int = 180, persist: bool = True) -> dict[str, Any]:
    return learn_from_completed_campaigns(days=days, persist=persist)


def get_success_patterns(limit: int = 20) -> dict[str, Any]:
    return {
        "success": True,
        "service": "campaign_success_patterns",
        "params": {"limit": limit},
        "patterns": load_patterns("winning", limit),
        "pattern_type": "winning",
    }


def get_failure_patterns(limit: int = 20) -> dict[str, Any]:
    return {
        "success": True,
        "service": "campaign_failure_patterns",
        "params": {"limit": limit},
        "patterns": load_patterns("losing", limit),
        "pattern_type": "losing",
    }


def analyze_campaign_performance(campaign: Campaign, verifier_summary: dict[str, Any] | None = None) -> dict[str, Any]:
    verifier_summary = verifier_summary or {}
    impressions = int(campaign.impressions or 0)
    clicks = int(campaign.clicks or 0)
    conversions = int(campaign.conversions or 0)
    revenue = float(campaign.revenue or 0)
    spend = float(campaign.spend or 0)
    roi = float(campaign.roi or safe_divide(revenue - spend, spend) * 100)
    roas = float(campaign.roas or safe_divide(revenue, spend))
    ctr = percent(clicks, impressions)
    conversion_rate = percent(conversions, clicks)
    approval_rate = float(verifier_summary.get("approval_rate", 0))
    verifier_score = float(verifier_summary.get("verifier_score", 50))
    customer_engagement = clamp_score(ctr * 9 + conversion_rate * 5 + min(conversions, 30))
    performance_score = weighted_score(
        {
            "roi": (clamp_score(roi / 10 + 50), 0.18),
            "roas": (clamp_score(roas * 18), 0.22),
            "ctr": (clamp_score(ctr * 10), 0.16),
            "conversion": (clamp_score(conversion_rate * 8), 0.18),
            "approval": (approval_rate or verifier_score, 0.12),
            "engagement": (customer_engagement, 0.14),
        }
    )
    risk_score = clamp_score(100 - performance_score + (25 if spend > revenue and spend > 0 else 0))
    classification = "winning" if performance_score >= 70 and risk_score <= 55 else "losing" if risk_score >= 65 else "mixed"
    created_at = campaign.created_at or datetime.now(UTC).replace(tzinfo=None)
    content = campaign.content or {}
    return {
        "campaign_id": str(campaign.id),
        "campaign_name": campaign.campaign_name,
        "classification": classification,
        "channel": (campaign.campaign_type or content.get("platform") or "unknown").lower(),
        "audience": content.get("target_audience") or content.get("audience") or "unspecified",
        "season": content.get("season") or SEASON_BY_MONTH.get(created_at.month, "unknown"),
        "creative_type": content.get("content_type") or content.get("creative_type") or "social_post",
        "hook": content.get("headline") or content.get("hook") or _first_sentence(content.get("caption") or ""),
        "cta": content.get("cta") or content.get("button_text") or "",
        "metrics": {
            "roi": round(roi, 2),
            "roas": round(roas, 2),
            "ctr": ctr,
            "conversion_rate": conversion_rate,
            "approval_rate": round(approval_rate, 2),
            "verifier_score": round(verifier_score, 2),
            "customer_engagement": customer_engagement,
            "performance_score": performance_score,
            "risk_score": risk_score,
            "impressions": impressions,
            "clicks": clicks,
            "conversions": conversions,
            "revenue": round(revenue, 2),
            "spend": round(spend, 2),
        },
    }


def detect_patterns(performance_records: list[dict[str, Any]]) -> dict[str, Any]:
    winners = [item for item in performance_records if item["classification"] == "winning"]
    losers = [item for item in performance_records if item["classification"] == "losing"]
    return {
        "winning_campaigns": winners,
        "losing_campaigns": losers,
        "winning_hooks": _top_values(winners, "hook"),
        "winning_cta": _top_values(winners, "cta"),
        "winning_creative_types": _top_values(winners, "creative_type"),
        "winning_channels": _top_values(winners, "channel"),
        "winning_audiences": _top_values(winners, "audience"),
        "winning_seasons": _top_values(winners, "season"),
        "success_patterns": _success_patterns(winners),
        "failure_patterns": _failure_patterns(losers),
        "optimization_suggestions": _optimization_suggestions(winners, losers),
    }


def lessons_for_record(record: dict[str, Any]) -> list[str]:
    metrics = record["metrics"]
    lessons = []
    if record["classification"] == "winning":
        lessons.append(f"{record['channel']} worked with {metrics['roas']} ROAS and {metrics['conversion_rate']}% conversion.")
    if metrics["ctr"] >= 3:
        lessons.append("Hook generated above-baseline click interest.")
    if metrics["approval_rate"] >= 70 or metrics["verifier_score"] >= 75:
        lessons.append("Verifier/approval signal supports reuse with low compliance friction.")
    if record["classification"] == "losing":
        lessons.append(f"Campaign underperformed with risk score {metrics['risk_score']}; avoid scaling this pattern.")
    if metrics["spend"] > metrics["revenue"] and metrics["spend"] > 0:
        lessons.append("Spend exceeded revenue; budget should stay capped until creative improves.")
    return lessons or ["Insufficient signal; keep as a mixed learning pattern."]


def clamp_score(value: float | int | None, minimum: int = 0, maximum: int = 100) -> int:
    if value is None:
        return minimum
    try:
        return int(max(minimum, min(maximum, round(float(value)))))
    except (TypeError, ValueError):
        return minimum


def safe_divide(numerator: float | int | None, denominator: float | int | None) -> float:
    try:
        denominator_float = float(denominator or 0)
        if denominator_float <= 0:
            return 0.0
        return float(numerator or 0) / denominator_float
    except (TypeError, ValueError, ZeroDivisionError):
        return 0.0


def percent(numerator: float | int | None, denominator: float | int | None) -> float:
    return round(safe_divide(numerator, denominator) * 100, 2)


def weighted_score(parts: dict[str, tuple[float | int | None, float]]) -> int:
    total_weight = sum(weight for _, weight in parts.values())
    if total_weight <= 0:
        return 0
    return clamp_score(sum(float(score or 0) * weight for score, weight in parts.values()) / total_weight)


def _learn(days: int, persist: bool) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        campaigns = list(
            db.scalars(
                select(Campaign)
                .where(Campaign.status.in_(["completed", "published", "active"]), Campaign.created_at >= since)
                .order_by(Campaign.created_at.desc())
                .limit(500)
            ).all()
        )
        verifier_summary = _verifier_summary(db, since)
    performance_records = []
    for campaign in campaigns:
        record = analyze_campaign_performance(campaign, verifier_summary.get(str(campaign.id), {}))
        record["lessons"] = lessons_for_record(record)
        performance_records.append(record)
    detected = detect_patterns(performance_records)
    records_for_storage = []
    for record in performance_records:
        record = dict(record)
        record["success_patterns"] = detected["success_patterns"]
        record["failure_patterns"] = detected["failure_patterns"]
        record["optimization_suggestions"] = detected["optimization_suggestions"]
        records_for_storage.append(record)
    stored = upsert_patterns(records_for_storage) if persist and records_for_storage else []
    return {
        "campaigns_analyzed": len(performance_records),
        "patterns_stored": len(stored),
        "winning_campaigns": detected["winning_campaigns"],
        "losing_campaigns": detected["losing_campaigns"],
        "winning_hooks": detected["winning_hooks"],
        "winning_cta": detected["winning_cta"],
        "winning_creative_types": detected["winning_creative_types"],
        "winning_channels": detected["winning_channels"],
        "winning_audiences": detected["winning_audiences"],
        "winning_seasons": detected["winning_seasons"],
        "lessons_learned": [lesson for record in records_for_storage for lesson in record["lessons"]][:25],
        "success_patterns": detected["success_patterns"],
        "failure_patterns": detected["failure_patterns"],
        "optimization_suggestions": detected["optimization_suggestions"],
        "stored_patterns": stored[:25],
    }


def _verifier_summary(db: Session, since: datetime) -> dict[str, dict[str, float]]:
    reviews = list(db.scalars(select(VerifierReview).where(VerifierReview.created_at >= since)).all())
    summary: dict[str, dict[str, float]] = {}
    grouped: dict[str, list[VerifierReview]] = {}
    for review in reviews:
        grouped.setdefault(str(review.campaign_id or ""), []).append(review)
    for campaign_id, items in grouped.items():
        approved = sum(1 for item in items if item.safe_to_publish or item.approval_status == "approved")
        average_risk = sum(float(item.risk_score or 0) for item in items) / len(items)
        summary[campaign_id] = {
            "approval_rate": round(approved / len(items) * 100, 2),
            "verifier_score": round(max(0, 100 - average_risk), 2),
        }
    return summary


def _first_sentence(text: str) -> str:
    if not text:
        return ""
    return str(text).split(".")[0][:180]


def _top_values(records: list[dict[str, Any]], key: str, limit: int = 10) -> list[str]:
    counter = Counter(str(item.get(key) or "").strip() for item in records if str(item.get(key) or "").strip())
    return [value for value, _ in counter.most_common(limit)]


def _success_patterns(winners: list[dict[str, Any]]) -> list[str]:
    patterns = []
    for channel in _top_values(winners, "channel", 5):
        patterns.append(f"Prioritize {channel} when campaign metrics are similar to winning records.")
    for creative_type in _top_values(winners, "creative_type", 5):
        patterns.append(f"Reuse {creative_type} creative format for comparable audiences.")
    for season in _top_values(winners, "season", 5):
        patterns.append(f"Plan campaigns around {season} when product fit is strong.")
    return patterns


def _failure_patterns(losers: list[dict[str, Any]]) -> list[str]:
    patterns = []
    for channel in _top_values(losers, "channel", 5):
        patterns.append(f"Do not scale {channel} campaigns without stronger proof.")
    for audience in _top_values(losers, "audience", 5):
        patterns.append(f"Review audience fit for {audience} before repeating.")
    return patterns


def _optimization_suggestions(winners: list[dict[str, Any]], losers: list[dict[str, Any]]) -> list[str]:
    suggestions = []
    if winners:
        suggestions.append("Use winning hooks and CTA patterns as retrieval context before generating new campaign strategy.")
    if losers:
        suggestions.append("Down-rank channels, audiences, or creative types repeatedly found in losing patterns.")
    if winners and losers:
        suggestions.append("Compare losing creative against winning creative on CTR and verifier score before approval.")
    return suggestions or ["Collect more completed campaign data before changing strategy defaults."]


__all__ = [
    "analyze_campaign_performance",
    "detect_patterns",
    "get_campaign_pattern_learners",
    "get_failure_patterns",
    "get_success_patterns",
    "learn_from_completed_campaigns",
    "lessons_for_record",
]


# ── Campaign Patterns ────────────────────────────────────────────────────────
"""Campaign pattern persistence."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mynat_ai_system.backend.database.db_connection import engine as app_engine
from mynat_ai_system.backend.database.db_models import CampaignPatternLibrary


def upsert_patterns(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stored: list[dict[str, Any]] = []
    with Session(app_engine) as db:
        for record in records:
            pattern_id = _pattern_id(record)
            existing = db.scalar(select(CampaignPatternLibrary).where(CampaignPatternLibrary.pattern_id == pattern_id))
            if existing is None:
                existing = CampaignPatternLibrary(pattern_id=pattern_id)
                db.add(existing)
            _apply_record(existing, record)
            db.flush()
            stored.append(_to_dict(existing))
        db.commit()
    return stored


def load_patterns(pattern_type: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    with Session(app_engine) as db:
        query = select(CampaignPatternLibrary).where(CampaignPatternLibrary.status == "active")
        if pattern_type:
            query = query.where(CampaignPatternLibrary.pattern_type == pattern_type)
        rows = db.scalars(query.order_by(CampaignPatternLibrary.confidence_score.desc()).limit(max(limit, 1))).all()
        return [_to_dict(row) for row in rows]


def _apply_record(row: CampaignPatternLibrary, record: dict[str, Any]) -> None:
    metrics = record.get("metrics", {})
    row.pattern_type = record.get("classification") or "mixed"
    row.status = "active"
    row.campaign_id = record.get("campaign_id", "")
    row.campaign_name = record.get("campaign_name", "")
    row.channel = record.get("channel", "")
    row.audience = record.get("audience", "")
    row.season = record.get("season", "")
    row.creative_type = record.get("creative_type", "")
    row.hook = record.get("hook", "")
    row.cta = record.get("cta", "")
    row.metrics = metrics
    row.lessons = record.get("lessons", [])
    row.success_patterns = record.get("success_patterns", [])
    row.failure_patterns = record.get("failure_patterns", [])
    row.optimization_suggestions = record.get("optimization_suggestions", [])
    row.confidence_score = int(metrics.get("performance_score", 50))
    row.updated_at = datetime.now(UTC).replace(tzinfo=None)


def _to_dict(row: CampaignPatternLibrary) -> dict[str, Any]:
    return {
        "pattern_id": row.pattern_id,
        "pattern_type": row.pattern_type,
        "campaign_id": row.campaign_id,
        "campaign_name": row.campaign_name,
        "channel": row.channel,
        "audience": row.audience,
        "season": row.season,
        "creative_type": row.creative_type,
        "hook": row.hook,
        "cta": row.cta,
        "metrics": row.metrics or {},
        "lessons": row.lessons or [],
        "success_patterns": row.success_patterns or [],
        "failure_patterns": row.failure_patterns or [],
        "optimization_suggestions": row.optimization_suggestions or [],
        "confidence_score": row.confidence_score,
        "created_at": row.created_at.isoformat() if row.created_at else None,
        "updated_at": row.updated_at.isoformat() if row.updated_at else None,
    }


def _pattern_id(record: dict[str, Any]) -> str:
    key = "|".join(
        [
            str(record.get("campaign_id", "")),
            str(record.get("classification", "")),
            str(record.get("channel", "")),
            str(record.get("audience", "")),
            str(record.get("season", "")),
            str(record.get("creative_type", "")),
        ]
    )
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:32]


__all__ = ["load_patterns", "upsert_patterns"]

