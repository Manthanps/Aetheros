"""Agent output validation helpers."""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any, Callable, Type
from pydantic import BaseModel, ValidationError

def validate_or_fallback(schema: Type[BaseModel], output: dict[str, Any], fallback_factory: Callable[[str], dict[str, Any]], retry_factory: Callable[[dict[str, Any]], dict[str, Any]] | None=None) -> dict[str, Any]:
    """Validate output, retry once on failure, then return a safe fallback."""
    retry_count = 0
    output = _with_universal_fields(output)
    agent_name = _agent_name(schema)
    try:
        validated = schema.model_validate(output).model_dump(by_alias=True)
        _persist_agent_execution(agent_name, validated, retry_count)
        return validated
    except ValidationError as first_error:
        retry_count = 1
        if retry_factory:
            try:
                retried = _with_universal_fields(retry_factory(output), retry_count=retry_count)
                validated = schema.model_validate(retried).model_dump(by_alias=True)
                validated.setdefault('_meta', {})['validation_retry_count'] = retry_count
                _persist_agent_execution(agent_name, validated, retry_count)
                return validated
            except ValidationError as second_error:
                reason = str(second_error)
            except Exception as exc:
                reason = str(exc)
        else:
            reason = str(first_error)
    fallback = fallback_factory(reason)
    fallback.setdefault('_meta', {})
    fallback['_meta'].update({'fallback_used': True, 'validation_retry_count': retry_count, 'confidence': 'low'})
    fallback = _with_universal_fields(fallback, retry_count=retry_count, fallback=True)
    validated = schema.model_validate(fallback).model_dump(by_alias=True)
    _persist_agent_execution(agent_name, validated, retry_count)
    return validated

def safe_agent_fallback(agent_name: str, reason: str, **extra: Any) -> dict[str, Any]:
    """Generic non-publishing fallback shape."""
    return {'success': False, 'status': 'draft', 'error': f'{agent_name} validation failed: {reason}', **extra, '_meta': {'fallback_used': True, 'confidence': 'low', 'context_used': [], 'sources': []}}

def _with_universal_fields(output: dict[str, Any], *, retry_count: int=0, fallback: bool=False) -> dict[str, Any]:
    output = dict(output or {})
    meta = dict(output.get('_meta', {}) or {})
    confidence = meta.get('confidence', 'low' if fallback else 'medium')
    confidence_score = output.get('confidence_score')
    if confidence_score is None:
        confidence_score = {'high': 90, 'medium': 70, 'low': 30}.get(confidence, 50)
    risk_score = output.get('risk_score')
    if risk_score is None:
        risk_score = 90 if fallback or not output.get('success', False) else 20
    output.setdefault('workflow_id', meta.get('workflow_id', 'untracked'))
    output.setdefault('status', 'draft')
    output['confidence_score'] = int(confidence_score)
    output['risk_score'] = int(risk_score)
    output.setdefault('generated_at', datetime.now(UTC).replace(tzinfo=None))
    meta.setdefault('generated_at', output['generated_at'])
    meta.setdefault('validation_retry_count', retry_count)
    output['_meta'] = meta
    return output

def _agent_name(schema: Type[BaseModel]) -> str:
    explicit_names = {'CreatorAgentOutput': 'creator', 'ContentAgentOutput': 'content', 'CanvaAgentOutput': 'canva', 'SEOAgentOutput': 'seo', 'OrchestratorAgentOutput': 'orchestrator', 'AnalyticsAgentOutput': 'analytics', 'SupportAgentOutput': 'support', 'RecommendationEngineOutput': 'recommendation', 'VerifierAgentOutput': 'verifier'}
    if schema.__name__ in explicit_names:
        return explicit_names[schema.__name__]
    name = schema.__name__.replace('AgentOutput', '').replace('Output', '')
    return name.lower() or 'unknown'

def _persist_agent_execution(agent_name: str, output: dict[str, Any], retry_count: int) -> None:
    if (output.get('_meta') or {}).get('skip_persistence'):
        return
    try:
        from backend.database.workflow_approval_store import create_agent_execution
        create_agent_execution(agent_name=agent_name, output=output, retry_count=retry_count)
    except Exception:
        pass
    try:
        from backend.agent_memory import store_agent_execution_memory
        store_agent_execution_memory(agent_name=agent_name, output=output, retry_count=retry_count)
    except Exception:
        return
