"""Single-file agent facade for Mynat AI.

This file is the simplified entry point for all agents. It keeps imports lazy so
loading the module does not initialize databases, API clients, or model
providers until a specific agent is called.

The old agent folders remain as compatibility internals while routes, MCP
tools, and tests are migrated gradually.
"""

from __future__ import annotations

from typing import Any


def run_analytics_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.analytics_agent.agent import run_analytics_agent as _run

    return _run(*args, **kwargs)


def run_canva_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.design_builder.agent import run_canva_agent as _run

    return _run(*args, **kwargs)


def run_content_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.caption_writer.agent import run_content_agent as _run

    return _run(*args, **kwargs)


def run_creator_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.campaign_creator.creator_agent import run_creator_agent as _run

    return _run(*args, **kwargs)


def route_event(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.workflow_router.router import route_event as _run

    return _run(*args, **kwargs)


def publish_instagram(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.social_publisher.agent import publish_instagram as _run

    return _run(*args, **kwargs)


def publish_facebook(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.social_publisher.agent import publish_facebook as _run

    return _run(*args, **kwargs)


def publish_linkedin(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.social_publisher.agent import publish_linkedin as _run

    return _run(*args, **kwargs)


def publish_whatsapp(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.social_publisher.agent import publish_whatsapp as _run

    return _run(*args, **kwargs)


def publish_email(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.social_publisher.agent import publish_email as _run

    return _run(*args, **kwargs)


def run_recommendation_engine(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.recommendation_engine.agent import run_recommendation_engine as _run

    return _run(*args, **kwargs)


def run_revenue_growth_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.revenue_growth_agent import run_revenue_growth_agent as _run

    return _run(*args, **kwargs)


def detect_product_opportunities(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.product_opportunity_engine import detect_product_opportunities as _run

    return _run(*args, **kwargs)


def generate_content_strategy(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.content_strategy_engine import generate_content_strategy as _run

    return _run(*args, **kwargs)


def generate_seo_recommendations(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.seo_growth_engine import generate_seo_recommendations as _run

    return _run(*args, **kwargs)


def generate_revenue_recommendations(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.revenue_recommendation_engine import (
        generate_revenue_recommendations as _run,
    )

    return _run(*args, **kwargs)


def generate_customer_insights(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.revenue_growth_agent.customer_insight_engine import generate_customer_insights as _run

    return _run(*args, **kwargs)


def run_support_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.support_agent.agent import run_support_agent as _run

    return _run(*args, **kwargs)


def run_verifier_agent(*args: Any, **kwargs: Any) -> dict[str, Any]:
    from mynat_ai_system.agents.content_verifier.agent import run_verifier_agent as _run

    return _run(*args, **kwargs)


def create_seo_agent(*args: Any, **kwargs: Any) -> Any:
    from mynat_ai_system.agents.seo_optimizer.deepseek.seo_analysis_agent import SEOAnalysisAgent

    return SEOAnalysisAgent(*args, **kwargs)


__all__ = [
    "create_seo_agent",
    "detect_product_opportunities",
    "generate_content_strategy",
    "generate_customer_insights",
    "generate_revenue_recommendations",
    "generate_seo_recommendations",
    "publish_email",
    "publish_facebook",
    "publish_instagram",
    "publish_linkedin",
    "publish_whatsapp",
    "route_event",
    "run_analytics_agent",
    "run_canva_agent",
    "run_content_agent",
    "run_creator_agent",
    "run_recommendation_engine",
    "run_revenue_growth_agent",
    "run_support_agent",
    "run_verifier_agent",
]



# ── Analytics Agent ──────────────────────────────────────────────────────────
"""Internal analytics agent with mock-safe fallbacks."""
from typing import Any
from agents.agent_schemas import AnalyticsAgentOutput, utc_now
from agents.output_validator import safe_agent_fallback, validate_or_fallback

def _as_number(value: Any, default: float=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _fallback(reason: str) -> dict[str, Any]:
    return safe_agent_fallback('analytics', reason, campaign_performance={'status': 'mock_fallback', 'campaigns_analyzed': 0}, roi={'roi_percent': 0, 'confidence': 'low'}, profit_loss={'profit': 0, 'loss': 0, 'margin_percent': 0}, best_products=[], worst_products=[], budget_recommendations=[{'action': 'hold', 'reason': 'Insufficient validated analytics data'}], seasonal_insights=['Analytics fallback active until reliable internal data is available.'])

def run_analytics_agent(campaigns: list[dict[str, Any]] | None=None, products: list[dict[str, Any]] | None=None, sales: list[dict[str, Any]] | None=None, season: str | None=None) -> dict[str, Any]:
    """Analyze campaign performance, ROI, product winners/losers, and budgets.

    This agent intentionally uses caller-provided/internal data and deterministic
    mock fallbacks. It does not connect to Google, Meta, Shopify, or ad APIs.
    """
    campaigns = campaigns or []
    products = products or []
    sales = sales or []
    season = season or 'current'
    try:
        spend = sum((_as_number(c.get('spend') or c.get('budget')) for c in campaigns))
        revenue = sum((_as_number(c.get('revenue')) for c in campaigns))
        conversions = sum((int(_as_number(c.get('conversions'))) for c in campaigns))
        profit = revenue - spend
        roi_percent = round(profit / spend * 100, 2) if spend else 0
        product_scores: list[dict[str, Any]] = []
        product_sales = {str(s.get('product_id') or s.get('name')): s for s in sales}
        for product in products:
            key = str(product.get('id') or product.get('name'))
            sale = product_sales.get(key, {})
            units = _as_number(sale.get('units') or product.get('units_sold'))
            product_revenue = _as_number(sale.get('revenue') or product.get('revenue'))
            margin = _as_number(product.get('margin_percent'), 35)
            stock = _as_number(product.get('stock'), 0)
            score = product_revenue * 0.5 + units * 25 + margin * 10 - (0 if stock else 100)
            product_scores.append({'name': product.get('name', key), 'score': round(score, 2), 'revenue': product_revenue, 'units': units, 'stock': stock, 'margin_percent': margin})
        ranked = sorted(product_scores, key=lambda item: item['score'], reverse=True)
        weak = list(reversed(ranked[-3:])) if ranked else []
        budget_recommendations = []
        if roi_percent > 30 and ranked:
            budget_recommendations.append({'action': 'increase', 'percent': 15, 'target': ranked[0]['name'], 'reason': 'Positive ROI and strong product score'})
        elif roi_percent < 0:
            budget_recommendations.append({'action': 'decrease', 'percent': 20, 'target': 'lowest-performing campaigns', 'reason': 'Campaign spend exceeds attributed revenue'})
        else:
            budget_recommendations.append({'action': 'hold', 'percent': 0, 'reason': 'ROI is neutral or data is limited'})
        output = {'success': True, 'campaign_performance': {'campaigns_analyzed': len(campaigns), 'total_spend': spend, 'total_revenue': revenue, 'conversions': conversions, 'conversion_value': round(revenue / conversions, 2) if conversions else 0}, 'roi': {'roi_percent': roi_percent, 'spend': spend, 'revenue': revenue}, 'profit_loss': {'profit': round(max(profit, 0), 2), 'loss': round(abs(min(profit, 0)), 2), 'margin_percent': round(profit / revenue * 100, 2) if revenue else 0}, 'best_products': ranked[:3], 'worst_products': weak, 'budget_recommendations': budget_recommendations, 'recommended_budget': budget_recommendations[0] if budget_recommendations else {}, 'forecast': {'next_period_revenue': round(revenue * 1.08, 2) if revenue else 0, 'next_period_spend': round(spend * 1.05, 2) if spend else 0, 'confidence': 'medium' if campaigns else 'low'}, 'next_best_action': budget_recommendations[0].get('reason', 'Collect more analytics data') if budget_recommendations else 'Collect more analytics data', 'seasonal_insights': [f'{season.title()} campaigns should prioritize high-margin products with available stock.', 'Keep all publishing actions in draft/approval mode until external API credentials are connected.'], '_meta': {'generated_at': utc_now(), 'fallback_used': False, 'confidence': 'medium' if campaigns or products or sales else 'low', 'data_mode': 'internal_mock_safe'}}
        return validate_or_fallback(AnalyticsAgentOutput, output, _fallback, retry_factory=lambda failed: {**failed, 'success': True})
    except Exception as exc:
        error_message = str(exc)
        return validate_or_fallback(AnalyticsAgentOutput, {}, lambda reason: _fallback(error_message or reason))

# ── Support Agent ────────────────────────────────────────────────────────────
"""Customer support agent grounded in RAG plus mock-safe order lookup."""
from typing import Any
from agents.product_knowledge import require_rag_context
from agents.agent_schemas import SupportAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback
FAQ = {'shipping': 'Mynat orders are usually processed in 1-2 business days. Share the order ID for exact status.', 'return': 'Return requests should be reviewed by support with the order ID and issue details.', 'ingredients': 'Mynat focuses on Ayurvedic skincare ingredients. Check the product label for exact ingredients.'}
ESCALATION_KEYWORDS = {'refund', 'allergy', 'rash', 'payment failed', 'legal', 'angry', 'complaint'}

def _mock_order_lookup(order_id: str | None, orders: dict[str, Any] | None=None) -> dict[str, Any]:
    if not order_id:
        return {'available': False, 'reason': 'No order ID provided'}
    orders = orders or {}
    return orders.get(order_id) or {'available': False, 'order_id': order_id, 'reason': 'Order lookup is in mock fallback mode'}

def _fallback(reason: str) -> dict[str, Any]:
    return safe_agent_fallback('support', reason, answer='I could not verify enough product or order context. Please escalate this to human support.', intent='escalation', confidence='low', escalation_required=True, escalation_reason=reason, order_lookup={'available': False}, suggested_products=[])

def run_support_agent(customer_message: str, order_id: str | None=None, orders: dict[str, Any] | None=None) -> dict[str, Any]:
    """Answer support questions with product RAG context, FAQ, and mock orders."""
    if not customer_message:
        return validate_or_fallback(SupportAgentOutput, {'success': False, 'error': 'No customer message provided'}, _fallback)
    message = customer_message.lower()
    sentiment = _sentiment(message)
    rag_context = require_rag_context(customer_message)
    matched_faq = next((answer for key, answer in FAQ.items() if key in message), '')
    order_lookup = _mock_order_lookup(order_id, orders)
    escalation_required = any((keyword in message for keyword in ESCALATION_KEYWORDS))
    escalation_reason = 'Sensitive support intent detected' if escalation_required else ''
    if rag_context['available']:
        product_context = rag_context['context_used'][0].get('document', '')
        answer = f'Based on Mynat product context: {product_context[:240]} Please verify the final response before sending to the customer.'
    elif matched_faq:
        answer = matched_faq
    else:
        answer = 'I need more verified product context before giving a confident answer.'
        escalation_required = True
        escalation_reason = escalation_reason or 'RAG context unavailable'
    output = {'success': True, 'answer': answer, 'intent': 'order' if order_id else 'faq' if matched_faq else 'product_question', 'confidence': 'high' if rag_context['available'] else 'low', 'escalation_required': escalation_required, 'escalation_flag': escalation_required, 'escalation_reason': escalation_reason, 'sentiment': sentiment, 'order_lookup': order_lookup, 'suggested_products': [item.get('metadata', {}) for item in rag_context['context_used'][:3] if isinstance(item.get('metadata'), dict)], '_meta': {'fallback_used': False, 'confidence': rag_context['confidence'], 'context_used': rag_context['context_used'], 'sources': rag_context['sources'], 'rag_required': True, 'rag_available': rag_context['available'], 'rag_error': rag_context['error']}}
    return validate_or_fallback(SupportAgentOutput, output, _fallback, retry_factory=lambda failed: {**failed, 'success': bool(failed.get('answer'))})

def _sentiment(message: str) -> str:
    if any((word in message for word in ('angry', 'bad', 'refund', 'complaint', 'hate', 'upset'))):
        return 'negative'
    if any((word in message for word in ('love', 'good', 'great', 'thanks', 'happy'))):
        return 'positive'
    return 'neutral'

# ── Recommendation Engine ────────────────────────────────────────────────────
"""Recommendation engine using internal analytics, SEO, RAG, and inventory data."""
from typing import Any
from agents.product_knowledge import require_rag_context
from agents.agent_schemas import RecommendationEngineOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback

def _num(value: Any, default: float=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def _fallback(reason: str) -> dict[str, Any]:
    return safe_agent_fallback('recommendation', reason, next_best_action='Hold campaign changes until validated product and analytics context is available.', recommended_product={}, recommended_budget_change={'action': 'hold', 'percent': 0}, seo_opportunities=[], campaign_opportunities=[], cross_sell_opportunities=[])

def run_recommendation_engine(analytics_output: dict[str, Any] | None=None, seo_output: dict[str, Any] | None=None, products: list[dict[str, Any]] | None=None, campaign_history: list[dict[str, Any]] | None=None, inventory: dict[str, Any] | None=None) -> dict[str, Any]:
    """Return the next best marketing action without external API calls."""
    analytics_output = analytics_output or {}
    seo_output = seo_output or {}
    products = products or []
    campaign_history = campaign_history or []
    inventory = inventory or {}
    rag_query = ' '.join([str(p.get('name', '')) for p in products[:5]] + ['Mynat product recommendation context'])
    rag_context = require_rag_context(rag_query)
    best_products = analytics_output.get('best_products') or []
    candidate_name = (best_products[0] or {}).get('name') if best_products else ''
    candidate = next((p for p in products if p.get('name') == candidate_name), None)
    if not candidate and products:
        candidate = max(products, key=lambda p: _num(p.get('revenue')) + _num(p.get('margin_percent'), 30) * 10)
    candidate = candidate or {}
    stock_key = str(candidate.get('id') or candidate.get('name') or '')
    stock = _num(inventory.get(stock_key, candidate.get('stock', 0)))
    roi_percent = _num((analytics_output.get('roi') or {}).get('roi_percent'))
    seo_opportunities = seo_output.get('keyword_opportunities') or seo_output.get('priority_action_plan') or []
    if stock <= 0:
        next_action = 'Do not promote out-of-stock product; choose backup campaign.'
        budget_change = {'action': 'decrease', 'percent': 100, 'reason': 'No available stock'}
    elif roi_percent > 30:
        next_action = f"Scale draft campaign for {candidate.get('name', 'top product')} with human approval."
        budget_change = {'action': 'increase', 'percent': 15, 'reason': 'Positive ROI'}
    elif seo_opportunities:
        next_action = 'Create SEO-led content draft before increasing paid budget.'
        budget_change = {'action': 'hold', 'percent': 0, 'reason': 'SEO opportunity should be tested first'}
    else:
        next_action = 'Refresh product content draft and collect more performance data.'
        budget_change = {'action': 'hold', 'percent': 0, 'reason': 'Insufficient advantage signal'}
    campaign_opportunities = [{'campaign': item.get('name', 'historical_campaign'), 'action': 'reuse_angle', 'reason': 'Historical campaign had positive revenue signal'} for item in campaign_history if _num(item.get('revenue')) > _num(item.get('spend') or item.get('budget'))][:3]
    product_names = [p.get('name') for p in products if p.get('name')]
    cross_sell = [{'primary': candidate.get('name'), 'cross_sell': name, 'reason': 'Complementary product bundle'} for name in product_names if name != candidate.get('name')][:3]
    output = {'success': True, 'next_best_action': next_action, 'recommended_product': candidate, 'recommended_budget_change': budget_change, 'seo_opportunities': seo_opportunities[:5] if isinstance(seo_opportunities, list) else [], 'campaign_opportunities': campaign_opportunities, 'cross_sell_opportunities': cross_sell, 'expected_impact': {'revenue_lift_percent': 8 if roi_percent > 30 else 3, 'confidence': rag_context['confidence'] if rag_context['available'] else 'low', 'basis': 'analytics + SEO + inventory + product context'}, 'pricing_recommendations': [{'product': candidate.get('name'), 'action': 'hold', 'reason': 'No live pricing elasticity data yet'}] if candidate else [], 'inventory_recommendations': [{'product': candidate.get('name'), 'stock': stock, 'action': 'promote' if stock > 0 else 'pause'}] if candidate else [], '_meta': {'fallback_used': False, 'confidence': rag_context['confidence'] if rag_context['available'] else 'low', 'context_used': rag_context['context_used'], 'sources': rag_context['sources'], 'rag_required': True, 'rag_available': rag_context['available'], 'rag_error': rag_context['error']}}
    return validate_or_fallback(RecommendationEngineOutput, output, _fallback, retry_factory=lambda failed: {**failed, 'success': bool(failed.get('next_best_action'))})
