"""Health, alerting, and dashboard summaries built from platform metrics."""
from __future__ import annotations
import os
import time
from typing import Any
from sqlalchemy import text
from backend.database.db_connection import engine
from backend.database.db_migrator import get_current_revision, get_head_revision
from backend.services.metrics_collector import collect_platform_metrics
DEFAULT_THRESHOLDS = {'agent_failure_rate': 20.0, 'workflow_failure_rate': 20.0, 'dead_letter_rate': 10.0, 'approval_pending': 25, 'publishing_queue_length': 50, 'average_workflow_duration_seconds': 900.0}

def get_thresholds() -> dict[str, float]:
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key in list(thresholds):
        env_key = f'OBS_{key.upper()}'
        if os.getenv(env_key):
            thresholds[key] = float(os.getenv(env_key, thresholds[key]))
    return thresholds

def evaluate_alerts(metrics: dict[str, Any], thresholds: dict[str, float] | None=None) -> list[dict[str, Any]]:
    thresholds = thresholds or get_thresholds()
    alerts: list[dict[str, Any]] = []
    checks = [('agent_failure_rate', metrics['agents']['failure_rate'], 'Agent failure rate is above threshold'), ('workflow_failure_rate', metrics['workflows']['failure_rate'], 'Workflow failure rate is above threshold'), ('dead_letter_rate', metrics['queues']['dead_letters']['dead_letter_rate'], 'Creator dead letter rate is above threshold'), ('approval_pending', metrics['approvals']['pending'], 'Approval backlog is above threshold'), ('publishing_queue_length', metrics['queues']['publishing_queue_length'], 'Publishing queue length is above threshold'), ('average_workflow_duration_seconds', metrics['workflows']['average_duration_seconds'], 'Average workflow duration is above threshold')]
    for key, value, message in checks:
        threshold = thresholds[key]
        if float(value or 0) > threshold:
            alerts.append({'key': key, 'severity': 'critical' if float(value or 0) >= threshold * 2 else 'warning', 'value': value, 'threshold': threshold, 'message': message})
    return alerts

def system_status() -> dict[str, Any]:
    metrics = collect_platform_metrics()
    alerts = evaluate_alerts(metrics)
    return {'status': 'degraded' if alerts else 'ok', 'metrics': metrics, 'thresholds': get_thresholds(), 'alerts': alerts}

def workflow_status() -> dict[str, Any]:
    metrics = collect_platform_metrics()
    return {'status': 'ok' if metrics['workflows']['failure_rate'] <= get_thresholds()['workflow_failure_rate'] else 'degraded', 'workflows': metrics['workflows'], 'agents': metrics['agents']['by_agent'], 'queues': metrics['queues'], 'approvals': metrics['approvals']}

def health_status() -> tuple[int, dict[str, Any]]:
    checks: dict[str, dict[str, Any]] = {}
    overall = 'ok'
    try:
        started = time.perf_counter()
        with engine.connect() as conn:
            conn.execute(text('SELECT 1'))
        checks['database'] = {'status': 'ok', 'latency_ms': round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        checks['database'] = {'status': 'error', 'detail': str(exc)}
        overall = 'degraded'
    try:
        current = get_current_revision()
        head = get_head_revision()
        checks['migrations'] = {'status': 'ok' if current == head else 'stale', 'current_revision': current, 'head_revision': head}
        if current != head:
            overall = 'degraded'
    except Exception as exc:
        checks['migrations'] = {'status': 'error', 'detail': str(exc)}
        overall = 'degraded'
    try:
        import redis as redis_lib
        started = time.perf_counter()
        redis = redis_lib.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'), socket_connect_timeout=2, socket_timeout=2)
        redis.ping()
        checks['redis'] = {'status': 'ok', 'latency_ms': round((time.perf_counter() - started) * 1000, 1)}
    except Exception as exc:
        checks['redis'] = {'status': 'error', 'detail': str(exc)}
        overall = 'degraded'
    status_code = 200 if overall == 'ok' else 503
    return (status_code, {'status': overall, 'checks': checks, 'version': '1.0.0'})

def dashboard_context() -> dict[str, Any]:
    status = system_status()
    metrics = status['metrics']
    return {'system': {'status': status['status'], 'alerts': status['alerts']}, 'metrics': metrics, 'agent_cards': metrics['agents']['by_agent'], 'thresholds': status['thresholds']}
