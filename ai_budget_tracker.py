"""Merged AI cost intelligence.

This is the canonical single file for:
- AI usage logging
- token estimation
- provider/model cost estimation
- cost dashboard aggregation
- monthly budget guardrails
"""

from __future__ import annotations

import os
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from mynat_ai_system.backend.database.db_connection import engine as app_engine
from mynat_ai_system.backend.database.db_models import AICostLog

USD_TO_INR = 83.0
MODEL_PRICING: dict[str, tuple[float, float]] = {
    "claude-sonnet-4-6": (3.0, 15.0),
    "claude": (3.0, 15.0),
    "gpt-4o-mini": (0.15, 0.60),
    "gpt-4o": (2.50, 10.0),
    "openai": (0.15, 0.60),
    "deepseek-reasoner": (0.55, 2.19),
    "deepseek/deepseek-r1": (0.55, 2.19),
    "deepseek": (0.55, 2.19),
    "ollama": (0.0, 0.0),
    "mock": (0.0, 0.0),
}


def record_ai_usage(
    *,
    provider: str,
    model: str = "",
    agent_name: str = "unknown",
    workflow_id: str = "untracked",
    campaign_id: str = "",
    operation: str = "",
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int | None = None,
    success: bool = True,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total = int(total_tokens if total_tokens is not None else input_tokens + output_tokens)
    cost_usd = estimate_cost_usd(provider=provider, model=model, input_tokens=input_tokens, output_tokens=output_tokens)
    now = datetime.now(UTC).replace(tzinfo=None)
    record = AICostLog(
        provider=(provider or "unknown").lower(),
        model=model or "",
        agent_name=agent_name or "unknown",
        workflow_id=workflow_id or "untracked",
        campaign_id=campaign_id or "",
        operation=operation or "",
        input_tokens=int(input_tokens or 0),
        output_tokens=int(output_tokens or 0),
        total_tokens=total,
        estimated_cost_usd=cost_usd,
        estimated_cost_inr=round(cost_usd * USD_TO_INR, 6),
        success=success,
        metadata_json=metadata or {},
        created_at=now,
    )
    try:
        with Session(app_engine) as db:
            db.add(record)
            db.commit()
            db.refresh(record)
            return cost_log_to_dict(record)
    except Exception:
        return {
            "id": None,
            "provider": record.provider,
            "model": record.model,
            "agent_name": record.agent_name,
            "workflow_id": record.workflow_id,
            "campaign_id": record.campaign_id,
            "operation": record.operation,
            "input_tokens": record.input_tokens,
            "output_tokens": record.output_tokens,
            "total_tokens": record.total_tokens,
            "estimated_cost_usd": record.estimated_cost_usd,
            "estimated_cost_inr": record.estimated_cost_inr,
            "success": bool(record.success),
            "metadata": {"persistence_error": True, **(metadata or {})},
            "created_at": now.isoformat(),
        }


def estimate_cost_usd(*, provider: str, model: str, input_tokens: int, output_tokens: int) -> float:
    input_rate, output_rate = _pricing(provider, model)
    return round((max(input_tokens, 0) / 1_000_000 * input_rate) + (max(output_tokens, 0) / 1_000_000 * output_rate), 8)


def estimate_tokens(text: str) -> int:
    return max(1, round(len(text or "") / 4))


def usage_from_anthropic_response(response: Any, prompt: str = "", output_text: str = "") -> tuple[int, int, int]:
    usage = getattr(response, "usage", None)
    input_tokens = int(getattr(usage, "input_tokens", 0) or 0) if usage else 0
    output_tokens = int(getattr(usage, "output_tokens", 0) or 0) if usage else 0
    if not input_tokens:
        input_tokens = estimate_tokens(prompt)
    if not output_tokens:
        output_tokens = estimate_tokens(output_text)
    return input_tokens, output_tokens, input_tokens + output_tokens


def cost_dashboard_summary(days: int = 30) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        rows = db.scalars(select(AICostLog).where(AICostLog.created_at >= since).order_by(AICostLog.created_at.desc())).all()
    return summarize_cost_logs(list(rows), days=days)


def summarize_cost_logs(rows: list[AICostLog], days: int = 30) -> dict[str, Any]:
    by_agent: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_workflow: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_campaign: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_provider: dict[str, dict[str, Any]] = defaultdict(_bucket)
    by_month: dict[str, dict[str, Any]] = defaultdict(_bucket)
    for row in rows:
        _add(by_agent[row.agent_name or "unknown"], row)
        _add(by_workflow[row.workflow_id or "untracked"], row)
        _add(by_campaign[row.campaign_id or "uncampaignned"], row)
        _add(by_provider[row.provider or "unknown"], row)
        month = row.created_at.strftime("%Y-%m") if row.created_at else "unknown"
        _add(by_month[month], row)
    return {
        "success": True,
        "window_days": days,
        "usage_count": len(rows),
        "total_tokens": sum(int(row.total_tokens or 0) for row in rows),
        "monthly_cost": _format_map(by_month),
        "cost_per_agent": _format_map(by_agent),
        "cost_per_workflow": _format_map(by_workflow),
        "cost_per_campaign": _format_map(by_campaign),
        "cost_per_provider": _format_map(by_provider),
        "total_cost_usd": round(sum(float(row.estimated_cost_usd or 0) for row in rows), 8),
        "total_cost_inr": round(sum(float(row.estimated_cost_inr or 0) for row in rows), 6),
    }


def budget_status(days: int = 30) -> dict[str, Any]:
    try:
        summary = cost_dashboard_summary(days=days)
    except Exception:
        summary = {
            "success": False,
            "window_days": days,
            "usage_count": 0,
            "total_tokens": 0,
            "monthly_cost": {},
            "cost_per_agent": {},
            "cost_per_workflow": {},
            "cost_per_campaign": {},
            "cost_per_provider": {},
            "total_cost_usd": 0.0,
            "total_cost_inr": 0.0,
        }
    monthly_budget = _float_env("AI_MONTHLY_BUDGET_USD", 100.0)
    warning_ratio = _float_env("AI_BUDGET_WARNING_RATIO", 0.8)
    spent = float(summary["total_cost_usd"])
    return {
        "success": True,
        "monthly_budget_usd": monthly_budget,
        "spent_usd": round(spent, 8),
        "remaining_usd": round(max(monthly_budget - spent, 0), 8),
        "usage_percent": round((spent / monthly_budget * 100) if monthly_budget else 0, 2),
        "warning": bool(monthly_budget and spent >= monthly_budget * warning_ratio),
        "blocked": bool(monthly_budget and spent >= monthly_budget),
        "summary": summary,
    }


def check_budget_before_request(
    *,
    provider: str,
    model: str,
    estimated_input_tokens: int,
    estimated_output_tokens: int,
) -> tuple[bool, dict[str, Any]]:
    status = budget_status()
    projected = estimate_cost_usd(
        provider=provider,
        model=model,
        input_tokens=estimated_input_tokens,
        output_tokens=estimated_output_tokens,
    )
    if status["spent_usd"] + projected > status["monthly_budget_usd"]:
        return False, {"reason": "AI monthly budget would be exceeded", "projected_request_cost_usd": projected, **status}
    return True, {"projected_request_cost_usd": projected, **status}


def cost_log_to_dict(record: AICostLog) -> dict[str, Any]:
    return {
        "id": record.id,
        "provider": record.provider,
        "model": record.model,
        "agent_name": record.agent_name,
        "workflow_id": record.workflow_id,
        "campaign_id": record.campaign_id,
        "operation": record.operation,
        "input_tokens": record.input_tokens,
        "output_tokens": record.output_tokens,
        "total_tokens": record.total_tokens,
        "estimated_cost_usd": round(float(record.estimated_cost_usd or 0), 8),
        "estimated_cost_inr": round(float(record.estimated_cost_inr or 0), 6),
        "success": bool(record.success),
        "metadata": record.metadata_json or {},
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


def _pricing(provider: str, model: str) -> tuple[float, float]:
    key = (model or provider or "").lower()
    for pattern, pricing in MODEL_PRICING.items():
        if pattern in key:
            return pricing
    provider_key = (provider or "").lower()
    for pattern, pricing in MODEL_PRICING.items():
        if pattern in provider_key:
            return pricing
    return (1.0, 3.0)


def _bucket() -> dict[str, Any]:
    return {"requests": 0, "tokens": 0, "cost_usd": 0.0, "cost_inr": 0.0}


def _add(bucket: dict[str, Any], row: AICostLog) -> None:
    bucket["requests"] += 1
    bucket["tokens"] += int(row.total_tokens or 0)
    bucket["cost_usd"] += float(row.estimated_cost_usd or 0)
    bucket["cost_inr"] += float(row.estimated_cost_inr or 0)


def _format_map(data: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        key: {
            "requests": value["requests"],
            "tokens": value["tokens"],
            "cost_usd": round(value["cost_usd"], 8),
            "cost_inr": round(value["cost_inr"], 6),
        }
        for key, value in sorted(data.items(), key=lambda item: item[1]["cost_usd"], reverse=True)
    }


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


__all__ = [
    "MODEL_PRICING",
    "USD_TO_INR",
    "budget_status",
    "check_budget_before_request",
    "cost_dashboard_summary",
    "cost_log_to_dict",
    "estimate_cost_usd",
    "estimate_tokens",
    "record_ai_usage",
    "summarize_cost_logs",
    "usage_from_anthropic_response",
]

