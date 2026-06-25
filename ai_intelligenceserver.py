"""Unified Marketing Intelligence Bus.

All agents should consume these functions through MCP instead of calculating
business-critical intelligence independently.
"""
from __future__ import annotations
import re
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.database.db_connection import engine as app_engine
from backend.database.db_models import Campaign, Customer, EmailLog, GeneratedContent, Product, ProductAnalytics, Review, VerifierReview
from backend.database.workflow_approval_store import AgentExecutionRecord, ApprovalRecord, SessionLocal as WorkflowSessionLocal, WorkflowRecord
from mynat_ai_system.campaign_pattern_learner_engine import campaign_pattern_learner, campaign_patterns
from mcp_server.ai_intelligence import clamp_score, percent, runtime, safe_divide, utc_now, weighted_score
CHANNELS = ['instagram', 'facebook', 'linkedin', 'whatsapp', 'email']
SEASONAL_MONTHS = {1: ('new_year', 72), 2: ('winter_wellness', 64), 3: ('holi', 78), 4: ('summer_care', 82), 5: ('summer_care', 80), 6: ('monsoon_prep', 70), 7: ('monsoon_care', 76), 8: ('raksha_bandhan', 74), 9: ('festive_prep', 82), 10: ('diwali_prep', 90), 11: ('wedding_season', 86), 12: ('winter_gifting', 80)}

def get_product_intelligence(product_id: int | str | None=None, category: str | None=None, limit: int=10, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'product_id': product_id, 'category': category, 'limit': limit, 'context': context or {}}
    return runtime.run('product_intelligence', params, lambda: _product_intelligence(product_id, category, limit))

def get_customer_intelligence(customer_id: int | str | None=None, segment: str | None=None, limit: int=50, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'customer_id': customer_id, 'segment': segment, 'limit': limit, 'context': context or {}}
    return runtime.run('customer_intelligence', params, lambda: _customer_intelligence(customer_id, segment, limit))

def get_campaign_intelligence(campaign_id: int | str | None=None, days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'campaign_id': campaign_id, 'days': days, 'context': context or {}}
    return runtime.run('campaign_intelligence', params, lambda: _campaign_intelligence(campaign_id, days))

def get_market_intelligence(category: str | None=None, days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'category': category, 'days': days, 'context': context or {}}
    return runtime.run('market_intelligence', params, lambda: _market_intelligence(category, days))

def get_channel_intelligence(campaign_goal: str | None=None, days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'campaign_goal': campaign_goal, 'days': days, 'context': context or {}}
    return runtime.run('channel_intelligence', params, lambda: _channel_intelligence(campaign_goal, days))

def get_seo_intelligence(keyword: str | None=None, product_id: int | str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'keyword': keyword, 'product_id': product_id, 'context': context or {}}
    return runtime.run('seo_intelligence', params, lambda: _seo_intelligence(keyword, product_id))

def get_pricing_intelligence(product_id: int | str | None=None, category: str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'product_id': product_id, 'category': category, 'context': context or {}}
    return runtime.run('pricing_intelligence', params, lambda: _pricing_intelligence(product_id, category))

def get_inventory_intelligence(product_id: int | str | None=None, category: str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'product_id': product_id, 'category': category, 'context': context or {}}
    return runtime.run('inventory_intelligence', params, lambda: _inventory_intelligence(product_id, category))

def get_competitor_intelligence(category: str | None=None, competitor_data: list[dict[str, Any]] | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'category': category, 'competitor_data': competitor_data or [], 'context': context or {}}
    return runtime.run('competitor_intelligence', params, lambda: _competitor_intelligence(category, competitor_data or []))

def get_trend_intelligence(category: str | None=None, days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'category': category, 'days': days, 'context': context or {}}
    return runtime.run('trend_intelligence', params, lambda: _trend_intelligence(category, days))

def get_profit_intelligence(days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'days': days, 'context': context or {}}
    return runtime.run('profit_intelligence', params, lambda: _profit_intelligence(days))

def get_recommendation_intelligence(campaign_goal: str='sales', category: str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'campaign_goal': campaign_goal, 'category': category, 'context': context or {}}
    return runtime.run('recommendation_intelligence', params, lambda: _recommendation_intelligence(campaign_goal, category, context or {}))

def get_content_intelligence(platform: str | None=None, content_type: str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'platform': platform, 'content_type': content_type, 'context': context or {}}
    return runtime.run('content_intelligence', params, lambda: _content_intelligence(platform, content_type))

def get_verifier_intelligence(days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'days': days, 'context': context or {}}
    return runtime.run('verifier_intelligence', params, lambda: _verifier_intelligence(days))

def get_workflow_intelligence(days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'days': days, 'context': context or {}}
    return runtime.run('workflow_intelligence', params, lambda: _workflow_intelligence(days))

def get_learning_intelligence(days: int=180, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'days': days, 'context': context or {}}
    return runtime.run('learning_intelligence', params, lambda: _learning_intelligence(days))

def get_strategy_intelligence(campaign_goal: str='sales', category: str | None=None, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'campaign_goal': campaign_goal, 'category': category, 'context': context or {}}
    return runtime.run('strategy_intelligence', params, lambda: _strategy_intelligence(campaign_goal, category, context or {}))

def get_executive_intelligence(days: int=90, context: dict[str, Any] | None=None) -> dict[str, Any]:
    params = {'days': days, 'context': context or {}}
    return runtime.run('executive_intelligence', params, lambda: _executive_intelligence(days))

def get_intelligence_bus_metrics() -> dict[str, Any]:
    return runtime.metrics()

def _product_intelligence(product_id: int | str | None, category: str | None, limit: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=90)
    with Session(app_engine) as db:
        query = select(Product).where(Product.is_active.is_(True))
        if product_id is not None:
            query = query.where(Product.id == _as_int(product_id))
        if category:
            query = query.where(Product.category == category)
        products = list(db.scalars(query.order_by(Product.updated_at.desc()).limit(max(limit, 1))).all())
        product_ids = [item.id for item in products]
        analytics = _analytics_by_product(db, product_ids, since)
        reviews = _reviews_by_product(db, product_ids)
    product_reports = [_score_product(product, analytics.get(product.id, {}), reviews.get(product.id, {})) for product in products]
    top_products = sorted(product_reports, key=lambda item: item['campaign_readiness_score'], reverse=True)
    return {'products_analyzed': len(product_reports), 'top_products': top_products[:min(limit, len(top_products))], 'products': product_reports, 'summary': _summary_from_scores(product_reports, 'campaign_readiness_score')}

def _customer_intelligence(customer_id: int | str | None, segment: str | None, limit: int) -> dict[str, Any]:
    with Session(app_engine) as db:
        query = select(Customer)
        if customer_id is not None:
            query = query.where(Customer.id == _as_int(customer_id))
        if segment:
            query = query.where(Customer.segment == segment)
        customers = list(db.scalars(query.order_by(Customer.total_spent.desc()).limit(max(limit, 1))).all())
        logs = list(db.scalars(select(EmailLog).limit(1000)).all())
    segments = Counter((item.segment or 'unknown' for item in customers))
    total_spent = sum((float(item.total_spent or 0) for item in customers))
    total_orders = sum((int(item.total_orders or 0) for item in customers))
    repeat_buyers = sum((1 for item in customers if int(item.total_orders or 0) > 1))
    email_open_rate = percent(sum((1 for item in logs if item.opened)), len(logs))
    email_click_rate = percent(sum((1 for item in logs if item.clicked)), len(logs))
    profiles = [{'customer_id': item.id, 'name': item.name or '', 'segment': item.segment or 'unknown', 'interests': item.interests or [], 'lifetime_value': round(float(item.total_spent or 0), 2), 'orders': int(item.total_orders or 0), 'customer_segment_score': clamp_score(45 + min(float(item.total_spent or 0) / 20, 30) + min(int(item.total_orders or 0) * 6, 25))} for item in customers[:25]]
    return {'customers_analyzed': len(customers), 'segment_distribution': dict(segments), 'customer_profiles': profiles, 'ltv_score': clamp_score(safe_divide(total_spent, len(customers)) / 10), 'retention_score': clamp_score(percent(repeat_buyers, len(customers))), 'loyalty_score': clamp_score(percent(repeat_buyers, len(customers)) + email_click_rate * 0.5), 'conversion_score': clamp_score(email_open_rate * 0.4 + email_click_rate * 1.2 + min(total_orders, 50)), 'summary': f'{len(customers)} customers analyzed; {repeat_buyers} repeat buyers found.'}

def _campaign_intelligence(campaign_id: int | str | None, days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        query = select(Campaign).where(Campaign.created_at >= since)
        if campaign_id is not None:
            query = query.where(Campaign.id == _as_int(campaign_id))
        campaigns = list(db.scalars(query.order_by(Campaign.created_at.desc()).limit(500)).all())
    reports = []
    for item in campaigns:
        ctr = percent(item.clicks, item.impressions)
        conversion_rate = percent(item.conversions, item.clicks)
        roas = float(item.roas or safe_divide(item.revenue, item.spend))
        success = weighted_score({'roi': (clamp_score(float(item.roi or 0) + 50), 0.25), 'roas': (clamp_score(roas * 20), 0.25), 'ctr': (clamp_score(ctr * 10), 0.2), 'conversion': (clamp_score(conversion_rate * 8), 0.2), 'status': (85 if (item.status or '').lower() in {'completed', 'active', 'published'} else 45, 0.1)})
        risk = clamp_score(100 - success + (20 if float(item.spend or 0) > float(item.revenue or 0) else 0))
        reports.append({'campaign_id': item.id, 'campaign_name': item.campaign_name, 'channel': item.campaign_type or 'unknown', 'roi': round(float(item.roi or 0), 2), 'roas': round(roas, 2), 'ctr': ctr, 'conversion_rate': conversion_rate, 'campaign_success_score': success, 'campaign_risk_score': risk, 'campaign_confidence_score': clamp_score(55 + min(item.impressions or 0, 5000) / 100), 'campaign_readiness_score': clamp_score(success - risk * 0.2 + 30), 'explanation': _campaign_explanation(success, risk)})
    return {'campaigns_analyzed': len(reports), 'top_campaigns': sorted(reports, key=lambda item: item['campaign_success_score'], reverse=True)[:10], 'campaigns': reports, 'summary': _summary_from_scores(reports, 'campaign_success_score')}

def _market_intelligence(category: str | None, days: int) -> dict[str, Any]:
    product_data = _product_intelligence(None, category, 50)
    campaign_data = _campaign_intelligence(None, days)
    season_name, season_score = SEASONAL_MONTHS[datetime.now(UTC).month]
    avg_product = _average_score(product_data['products'], 'campaign_readiness_score')
    avg_campaign = _average_score(campaign_data['campaigns'], 'campaign_success_score')
    competition_pressure = clamp_score(100 - min(len(product_data['products']) * 4, 45) + _average_score(campaign_data['campaigns'], 'campaign_risk_score') * 0.2)
    market_opportunity = weighted_score({'season': (season_score, 0.25), 'product': (avg_product, 0.35), 'campaign': (avg_campaign, 0.25), 'competition': (100 - competition_pressure, 0.15)})
    return {'category': category or 'all', 'season': season_name, 'market_opportunity_score': market_opportunity, 'trend_score': clamp_score((avg_product + season_score) / 2), 'seasonal_alignment_score': season_score, 'competition_pressure_score': competition_pressure, 'market_confidence_score': clamp_score(45 + len(product_data['products']) * 2 + len(campaign_data['campaigns'])), 'explanation': f'{season_name} gives a seasonal baseline of {season_score}; product readiness averages {avg_product}.'}

def _channel_intelligence(campaign_goal: str | None, days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        campaigns = list(db.scalars(select(Campaign).where(Campaign.created_at >= since)).all())
    by_channel: dict[str, list[Campaign]] = defaultdict(list)
    for item in campaigns:
        by_channel[(item.campaign_type or 'unknown').lower()].append(item)
    report = []
    for channel in CHANNELS:
        items = by_channel.get(channel, [])
        impressions = sum((int(item.impressions or 0) for item in items))
        clicks = sum((int(item.clicks or 0) for item in items))
        conversions = sum((int(item.conversions or 0) for item in items))
        revenue = sum((float(item.revenue or 0) for item in items))
        spend = sum((float(item.spend or 0) for item in items))
        historical_score = weighted_score({'ctr': (clamp_score(percent(clicks, impressions) * 10), 0.25), 'conversion': (clamp_score(percent(conversions, clicks) * 8), 0.3), 'roas': (clamp_score(safe_divide(revenue, spend) * 20), 0.3), 'volume': (clamp_score(len(items) * 12), 0.15)})
        default_fit = {'instagram': 82, 'facebook': 76, 'linkedin': 48, 'whatsapp': 72, 'email': 78}[channel]
        if campaign_goal and campaign_goal.lower() in {'lead_generation', 'b2b'} and (channel == 'linkedin'):
            default_fit += 25
        channel_priority = clamp_score(historical_score * 0.6 + default_fit * 0.4)
        report.append({'channel': channel, 'campaigns_analyzed': len(items), 'channel_performance_score': historical_score, 'channel_conversion_score': clamp_score(percent(conversions, clicks) * 8), 'channel_priority_score': channel_priority, 'channel_recommendation': _channel_recommendation(channel, channel_priority), 'expected_reach': 'high' if channel in {'instagram', 'facebook'} else 'medium', 'expected_engagement': 'high' if channel in {'instagram', 'whatsapp'} else 'medium'})
    return {'campaign_goal': campaign_goal or 'general', 'channels': sorted(report, key=lambda item: item['channel_priority_score'], reverse=True)}

def _seo_intelligence(keyword: str | None, product_id: int | str | None) -> dict[str, Any]:
    with Session(app_engine) as db:
        products_query = select(Product)
        if product_id is not None:
            products_query = products_query.where(Product.id == _as_int(product_id))
        products = list(db.scalars(products_query.limit(100)).all())
        content = list(db.scalars(select(GeneratedContent).where(GeneratedContent.content_type.in_(['blog', 'caption', 'hashtags'])).limit(200)).all())
    keyword_text = (keyword or '').lower()
    keyword_hits = sum((1 for product in products if keyword_text and keyword_text in f'{product.product_name} {product.description}'.lower()))
    tag_count = sum((len(product.tags or []) for product in products))
    content_score = _average_float([float(item.performance_score or 0) for item in content if item.performance_score is not None])
    return {'seo_score': clamp_score(45 + tag_count + keyword_hits * 8 + content_score * 0.2), 'keyword_opportunity_score': clamp_score(55 + max(0, len(products) - keyword_hits) * 2), 'ranking_score': clamp_score(40 + content_score * 0.4 + keyword_hits * 5), 'traffic_opportunity_score': clamp_score(50 + len(content) * 1.5 + tag_count * 0.5), 'keywords_detected': sorted({tag for product in products for tag in product.tags or []})[:25], 'explanation': f'Analyzed {len(products)} products and {len(content)} content records for SEO signals.'}

def _pricing_intelligence(product_id: int | str | None, category: str | None) -> dict[str, Any]:
    with Session(app_engine) as db:
        query = select(Product)
        if product_id is not None:
            query = query.where(Product.id == _as_int(product_id))
        if category:
            query = query.where(Product.category == category)
        products = list(db.scalars(query.limit(100)).all())
    prices = [_money(product.price) for product in products if _money(product.price) > 0]
    avg_price = _average_float(prices)
    report = []
    for product in products:
        price = _money(product.price)
        original = _money(product.original_price)
        discount = percent(max(original - price, 0), original)
        premium = clamp_score(percent(price, avg_price) if avg_price else 50)
        pricing_score = clamp_score(85 - abs(100 - premium) * 0.35 + discount * 0.3)
        report.append({'product_id': product.id, 'product_name': product.product_name, 'price': price, 'category_average_price': round(avg_price, 2), 'pricing_score': pricing_score, 'premium_positioning_score': premium, 'pricing_risk_score': clamp_score(abs(100 - premium) * 0.7 - discount * 0.2), 'pricing_advantage_score': clamp_score(100 - premium + discount), 'price_position': _price_position(premium)})
    return {'products': report, 'summary': _summary_from_scores(report, 'pricing_score')}

def _inventory_intelligence(product_id: int | str | None, category: str | None) -> dict[str, Any]:
    product_data = _product_intelligence(product_id, category, 100)
    items = []
    for product in product_data['products']:
        stock = int(product['stock_level'])
        velocity = float(product['sales_velocity'])
        risk = clamp_score(velocity * 8 - stock * 1.5 + (30 if stock == 0 else 0))
        health = clamp_score(stock * 4 - velocity * 2 + 40)
        readiness = clamp_score(product['campaign_readiness_score'] - risk * 0.25 + health * 0.15)
        items.append({'product_id': product['product_id'], 'product_name': product['product_name'], 'stock_level': stock, 'sales_velocity': velocity, 'inventory_risk_score': risk, 'inventory_health_score': health, 'campaign_readiness_score': readiness, 'recommendation': _inventory_recommendation(stock, velocity, risk)})
    return {'products': items, 'summary': _summary_from_scores(items, 'campaign_readiness_score')}

def _competitor_intelligence(category: str | None, competitor_data: list[dict[str, Any]]) -> dict[str, Any]:
    pricing = _pricing_intelligence(None, category)
    avg_internal_price = _average_score(pricing['products'], 'price')
    competitor_prices = [_money(item.get('price')) for item in competitor_data if _money(item.get('price')) > 0]
    avg_competitor_price = _average_float(competitor_prices)
    price_advantage = clamp_score(60 if not avg_competitor_price else 100 - percent(avg_internal_price, avg_competitor_price) + 60)
    competitor_pressure = clamp_score(len(competitor_data) * 12 + (100 - price_advantage) * 0.4)
    return {'competitors_analyzed': len(competitor_data), 'competitor_pressure_score': competitor_pressure, 'market_gap_score': clamp_score(80 - competitor_pressure * 0.35 + price_advantage * 0.3), 'competitive_advantage_score': price_advantage, 'explanation': 'Uses supplied competitor data when available; otherwise falls back to internal category pressure.'}

def _trend_intelligence(category: str | None, days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        query = select(ProductAnalytics).where(ProductAnalytics.date >= since)
        analytics = list(db.scalars(query).all())
    recent_views = sum((int(item.views or 0) for item in analytics))
    recent_sales = sum((int(item.purchases or 0) for item in analytics))
    trend_score = clamp_score(45 + min(recent_views / 100, 30) + min(recent_sales * 3, 25))
    season_name, season_score = SEASONAL_MONTHS[datetime.now(UTC).month]
    return {'category': category or 'all', 'season': season_name, 'trend_score': trend_score, 'growth_score': clamp_score((trend_score + season_score) / 2), 'trend_confidence_score': clamp_score(40 + len(analytics) * 2), 'explanation': f'Trend score is based on {len(analytics)} product analytics records and current seasonality.'}

def _profit_intelligence(days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as db:
        campaigns = list(db.scalars(select(Campaign).where(Campaign.created_at >= since)).all())
        analytics = list(db.scalars(select(ProductAnalytics).where(ProductAnalytics.date >= since)).all())
    revenue = sum((float(item.revenue or 0) for item in campaigns)) + sum((float(item.revenue or 0) for item in analytics))
    spend = sum((float(item.spend or 0) for item in campaigns))
    roas = safe_divide(revenue, spend)
    profit_proxy = revenue - spend
    return {'revenue': round(revenue, 2), 'ad_spend': round(spend, 2), 'profit_proxy': round(profit_proxy, 2), 'profit_score': clamp_score(50 + safe_divide(profit_proxy, max(revenue, 1)) * 50), 'roas_score': clamp_score(roas * 20), 'growth_score': clamp_score(45 + min(revenue / 1000, 40)), 'efficiency_score': clamp_score(100 - percent(spend, revenue) if revenue else 45)}

def _recommendation_intelligence(campaign_goal: str, category: str | None, context: dict[str, Any]) -> dict[str, Any]:
    products = _product_intelligence(None, category, 10)['top_products']
    channels = _channel_intelligence(campaign_goal, 90)['channels']
    market = _market_intelligence(category, 90)
    best_product = products[0] if products else {}
    best_channel = channels[0] if channels else {}
    budget_score = weighted_score({'market': (market['market_opportunity_score'], 0.45), 'product': (best_product.get('campaign_readiness_score', 50), 0.35), 'channel': (best_channel.get('channel_priority_score', 50), 0.2)})
    return {'best_product_to_promote': best_product, 'best_audience': context.get('audience') or _audience_from_product(best_product), 'best_budget': _budget_recommendation(budget_score), 'best_channel': best_channel, 'best_campaign_strategy': _strategy_from_goal(campaign_goal, market, best_product), 'recommendation_confidence_score': clamp_score(budget_score), 'reason': 'Recommendation combines product readiness, market timing, and channel priority from the MCP bus.'}

def _content_intelligence(platform: str | None, content_type: str | None) -> dict[str, Any]:
    with Session(app_engine) as db:
        query = select(GeneratedContent)
        if platform:
            query = query.where(GeneratedContent.platform == platform)
        if content_type:
            query = query.where(GeneratedContent.content_type == content_type)
        content = list(db.scalars(query.order_by(GeneratedContent.created_at.desc()).limit(300)).all())
        campaigns = list(db.scalars(select(Campaign).limit(300)).all())
    hooks = Counter()
    ctas = Counter()
    hashtags = Counter()
    scores = []
    for item in content:
        body = item.content or {}
        scores.append(float(item.performance_score or 0))
        hooks.update(_extract_phrases(body.get('headline') or body.get('hook') or body.get('caption') or ''))
        ctas.update(_extract_phrases(body.get('cta') or ''))
        hashtags.update((tag.lower() for tag in body.get('hashtags', []) if isinstance(tag, str)))
    for campaign in campaigns:
        body = campaign.content or {}
        hooks.update(_extract_phrases(body.get('headline') or body.get('caption') or ''))
        ctas.update(_extract_phrases(body.get('cta') or ''))
    return {'content_records_analyzed': len(content), 'best_hook_patterns': [item for item, _ in hooks.most_common(10)], 'best_cta_patterns': [item for item, _ in ctas.most_common(10)], 'best_hashtags': [item for item, _ in hashtags.most_common(15)], 'content_success_score': clamp_score(_average_float(scores) or 50)}

def _verifier_intelligence(days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with Session(app_engine) as adb, WorkflowSessionLocal() as wdb:
        app_reviews = list(adb.scalars(select(VerifierReview).where(VerifierReview.created_at >= since)).all())
        workflow_reviews = list(wdb.scalars(select(ApprovalRecord).where(ApprovalRecord.created_at >= since)).all())
    approved = sum((1 for item in app_reviews if bool(item.safe_to_publish)))
    rejected = sum((1 for item in app_reviews if (item.verifier_status or '').lower() in {'rejected', 'failed'}))
    avg_risk = _average_float([float(item.risk_score or 0) for item in app_reviews]) or 50
    approval_probability = percent(approved, len(app_reviews)) if app_reviews else percent(sum((1 for item in workflow_reviews if item.status == 'approved')), len(workflow_reviews))
    return {'reviews_analyzed': len(app_reviews), 'approval_probability': clamp_score(approval_probability), 'risk_score': clamp_score(avg_risk), 'compliance_score': clamp_score(100 - avg_risk + approval_probability * 0.2), 'risk_patterns': _risk_patterns(app_reviews), 'rejection_count': rejected}

def _workflow_intelligence(days: int) -> dict[str, Any]:
    since = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=max(days, 1))
    with WorkflowSessionLocal() as db:
        workflows = list(db.scalars(select(WorkflowRecord).where(WorkflowRecord.created_at >= since)).all())
        agents = list(db.scalars(select(AgentExecutionRecord).where(AgentExecutionRecord.started_at >= since)).all())
    completed = sum((1 for item in workflows if (item.status or '').lower() in {'completed', 'approved', 'published'}))
    failed = sum((1 for item in workflows if (item.status or '').lower() in {'failed', 'error', 'dead_lettered'}))
    retries = sum((int(item.retry_count or 0) for item in workflows)) + sum((int(item.retry_count or 0) for item in agents))
    durations = [max((item.completed_at - item.created_at).total_seconds(), 0) for item in workflows if item.created_at and item.completed_at]
    health = clamp_score(percent(completed, len(workflows)) - percent(failed, len(workflows)) * 0.5 + 50)
    return {'workflow_runs_analyzed': len(workflows), 'agent_executions_analyzed': len(agents), 'workflow_health_score': health, 'workflow_risk_score': clamp_score(percent(failed, len(workflows)) + min(retries * 4, 40)), 'workflow_efficiency_score': clamp_score(100 - (_average_float(durations) / 10 if durations else 0)), 'retry_count': retries}

def _learning_intelligence(days: int) -> dict[str, Any]:
    campaign_pattern_learner.app_engine = app_engine
    campaign_patterns.app_engine = app_engine
    learning = campaign_pattern_learner.learn_from_completed_campaigns(days=days, persist=True)
    return {'winning_campaigns': learning.get('winning_campaigns', [])[:10], 'losing_campaigns': learning.get('losing_campaigns', [])[:10], 'winning_hooks': learning.get('winning_hooks', [])[:5], 'winning_cta': learning.get('winning_cta', [])[:5], 'winning_creative_types': learning.get('winning_creative_types', [])[:5], 'winning_channels': learning.get('winning_channels', [])[:5], 'winning_audiences': learning.get('winning_audiences', [])[:5], 'winning_seasons': learning.get('winning_seasons', [])[:5], 'lessons_learned': learning.get('lessons_learned', [])[:10], 'failure_patterns': learning.get('failure_patterns', [])[:10], 'success_patterns': learning.get('success_patterns', [])[:10], 'optimization_suggestions': learning.get('optimization_suggestions', [])[:10], 'learning_patterns': {'campaigns_analyzed': learning.get('campaigns_analyzed', 0), 'patterns_stored': learning.get('patterns_stored', 0), 'winner_count': len(learning.get('winning_campaigns', [])), 'loser_count': len(learning.get('losing_campaigns', []))}}

def _strategy_intelligence(campaign_goal: str, category: str | None, context: dict[str, Any]) -> dict[str, Any]:
    recommendation = _recommendation_intelligence(campaign_goal, category, context)
    market = _market_intelligence(category, 90)
    content = _content_intelligence(recommendation.get('best_channel', {}).get('channel'), None)
    return {'campaign_goal': campaign_goal, 'recommended_product': recommendation['best_product_to_promote'], 'recommended_channel': recommendation['best_channel'], 'campaign_angle': _campaign_angle(campaign_goal, market), 'message_strategy': {'hook_patterns': content['best_hook_patterns'][:3], 'cta_patterns': content['best_cta_patterns'][:3], 'avoid': ['unsupported medical claims', 'misleading discounts', 'overly broad guarantees']}, 'confidence_score': recommendation['recommendation_confidence_score']}

def _executive_intelligence(days: int) -> dict[str, Any]:
    product_data = _product_intelligence(None, None, 10)
    campaign_data = _campaign_intelligence(None, days)
    profit = _profit_intelligence(days)
    workflow = _workflow_intelligence(days)
    market = _market_intelligence(None, days)
    return {'top_products': product_data['top_products'][:5], 'top_campaigns': campaign_data['top_campaigns'][:5], 'top_risks': _executive_risks(workflow, market, profit), 'revenue_forecast': {'basis': 'recent revenue proxy', 'next_period_estimate': round(float(profit['revenue']) * 1.08, 2), 'confidence_score': clamp_score((market['market_confidence_score'] + workflow['workflow_health_score']) / 2)}, 'growth_forecast': {'growth_score': profit['growth_score'], 'market_opportunity_score': market['market_opportunity_score']}, 'recommended_actions': _executive_actions(product_data, campaign_data, workflow, market)}

def _analytics_by_product(db: Session, product_ids: list[int], since: datetime) -> dict[int, dict[str, float]]:
    if not product_ids:
        return {}
    rows = list(db.scalars(select(ProductAnalytics).where(ProductAnalytics.product_id.in_(product_ids), ProductAnalytics.date >= since)).all())
    result: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        data = result[row.product_id]
        data['views'] += int(row.views or 0)
        data['add_to_cart'] += int(row.add_to_cart or 0)
        data['purchases'] += int(row.purchases or 0)
        data['revenue'] += float(row.revenue or 0)
        data['engagement_score'] += float(row.engagement_score or 0)
        data['records'] += 1
    return {key: dict(value) for key, value in result.items()}

def _reviews_by_product(db: Session, product_ids: list[int]) -> dict[int, dict[str, float]]:
    if not product_ids:
        return {}
    rows = list(db.scalars(select(Review).where(Review.product_id.in_(product_ids))).all())
    result: dict[int, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in rows:
        data = result[row.product_id]
        data['count'] += 1
        data['rating_total'] += float(row.rating or 0)
        data['sentiment_total'] += float(row.sentiment_score or 0)
    return {key: dict(value) for key, value in result.items()}

def _score_product(product: Product, analytics: dict[str, float], reviews: dict[str, float]) -> dict[str, Any]:
    views = float(analytics.get('views', 0))
    purchases = float(analytics.get('purchases', 0))
    revenue = float(analytics.get('revenue', 0))
    engagement = safe_divide(analytics.get('engagement_score', 0), analytics.get('records', 0))
    rating = safe_divide(reviews.get('rating_total', 0), reviews.get('count', 0))
    sentiment = safe_divide(reviews.get('sentiment_total', 0), reviews.get('count', 0))
    stock = _stock_level(product.specifications or {})
    sales_score = clamp_score(min(purchases * 8, 40) + min(views / 50, 25) + engagement * 0.35)
    inventory_score = clamp_score(20 + stock * 4 - purchases * 1.5)
    profit_score = clamp_score(min(revenue / 100, 45) + _money(product.price) / 20)
    customer_interest = clamp_score(min(views / 40, 35) + min(reviews.get('count', 0) * 8, 25) + rating * 8 + sentiment * 20)
    product_score = weighted_score({'sales': (sales_score, 0.25), 'inventory': (inventory_score, 0.2), 'profit': (profit_score, 0.2), 'interest': (customer_interest, 0.25), 'content': (70 if product.description else 45, 0.1)})
    readiness = weighted_score({'product': (product_score, 0.35), 'sales': (sales_score, 0.2), 'inventory': (inventory_score, 0.25), 'interest': (customer_interest, 0.2)})
    return {'product_id': product.id, 'product_name': product.product_name, 'category': product.category or 'uncategorized', 'price': product.price or '', 'product_score': product_score, 'sales_score': sales_score, 'inventory_score': inventory_score, 'profit_score': profit_score, 'customer_interest_score': customer_interest, 'campaign_readiness_score': readiness, 'confidence_score': clamp_score(45 + min(analytics.get('records', 0) * 8, 30) + min(reviews.get('count', 0) * 6, 25)), 'stock_level': stock, 'sales_velocity': round(purchases / 13, 2), 'explanations': {'sales_score': f'{int(purchases)} purchases and {int(views)} views in the analysis window.', 'inventory_score': f'Detected stock level {stock}; higher sales velocity reduces promotion safety.', 'profit_score': f'Revenue proxy {round(revenue, 2)} and price {_money(product.price)}.', 'customer_interest_score': f"Rating {round(rating, 2)} across {int(reviews.get('count', 0))} reviews.", 'campaign_readiness_score': 'Weighted blend of product strength, sales, inventory safety, and customer interest.'}}

def _summary_from_scores(items: list[dict[str, Any]], score_key: str) -> dict[str, Any]:
    if not items:
        return {'status': 'insufficient_data', 'average_score': 0, 'message': 'No records available.'}
    avg = _average_score(items, score_key)
    return {'status': 'strong' if avg >= 75 else 'watch' if avg >= 55 else 'weak', 'average_score': avg, 'message': f'{len(items)} records analyzed with average {score_key} of {avg}.'}

def _as_int(value: int | str | None) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0

def _money(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, int | float):
        return float(value)
    match = re.findall('\\d+(?:\\.\\d+)?', str(value).replace(',', ''))
    return float(match[0]) if match else 0.0

def _stock_level(specifications: dict[str, Any]) -> int:
    for key in ('stock', 'inventory', 'quantity', 'available_quantity', 'available'):
        if key in specifications:
            try:
                return max(int(specifications.get(key) or 0), 0)
            except (TypeError, ValueError):
                return 0
    return 25

def _average_score(items: list[dict[str, Any]], key: str) -> int:
    return clamp_score(_average_float([float(item.get(key) or 0) for item in items]))

def _average_float(values: list[float]) -> float:
    values = [float(item) for item in values if item is not None]
    return round(sum(values) / len(values), 2) if values else 0.0

def _campaign_explanation(success: int, risk: int) -> str:
    if success >= 75 and risk <= 45:
        return 'Strong performance with manageable risk.'
    if risk >= 70:
        return 'Campaign needs review because risk is higher than performance quality.'
    return 'Campaign has usable signal but needs more optimization data.'

def _channel_recommendation(channel: str, score: int) -> str:
    if score >= 75:
        return f'Prioritize {channel} for near-term campaigns.'
    if score >= 55:
        return f'Use {channel} as a supporting channel with controlled spend.'
    return f'Keep {channel} experimental until performance improves.'

def _price_position(premium_score: int) -> str:
    if premium_score >= 135:
        return 'premium_priced'
    if premium_score >= 110:
        return 'fairly_premium'
    if premium_score >= 80:
        return 'fairly_priced'
    return 'undervalued'

def _inventory_recommendation(stock: int, velocity: float, risk: int) -> str:
    if stock <= 0:
        return 'Do not promote until restocked.'
    if risk >= 70:
        return 'Protect inventory; use waitlist or limited campaign.'
    if velocity <= 1 and stock >= 20:
        return 'Bundle or discount to increase movement.'
    return 'Safe to promote with normal monitoring.'

def _audience_from_product(product: dict[str, Any]) -> str:
    category = (product.get('category') or '').lower()
    if 'hair' in category:
        return 'hair care buyers seeking natural wellness products'
    if 'skin' in category:
        return 'skincare buyers interested in gentle, natural routines'
    return 'existing Mynat wellness shoppers and lookalike audiences'

def _budget_recommendation(score: int) -> dict[str, Any]:
    if score >= 80:
        tier = 'scale'
        daily_budget = 2500
    elif score >= 60:
        tier = 'controlled_test'
        daily_budget = 1000
    else:
        tier = 'learning_only'
        daily_budget = 400
    return {'tier': tier, 'suggested_daily_budget_inr': daily_budget, 'score_basis': score}

def _strategy_from_goal(campaign_goal: str, market: dict[str, Any], product: dict[str, Any]) -> dict[str, Any]:
    goal = (campaign_goal or 'sales').lower()
    if goal in {'awareness', 'brand_building'}:
        angle = 'educational authority'
    elif goal in {'retention', 'upsell', 'cross_sell'}:
        angle = 'routine upgrade'
    else:
        angle = 'problem solution'
    return {'objective': campaign_goal, 'angle': angle, 'narrative': f"Promote {product.get('product_name', 'the selected product')} around {market.get('season')} timing."}

def _extract_phrases(text: str) -> list[str]:
    if not text:
        return []
    cleaned = re.sub('[^\\w\\s#]', ' ', str(text).lower())
    words = [word for word in cleaned.split() if len(word) > 3]
    return [' '.join(words[index:index + 3]) for index in range(0, min(len(words), 12), 3)]

def _risk_patterns(reviews: list[VerifierReview]) -> list[str]:
    counter: Counter[str] = Counter()
    for review in reviews:
        for issue in review.issues_found or []:
            counter[str(issue)] += 1
    return [item for item, _ in counter.most_common(10)]

def _campaign_angle(campaign_goal: str, market: dict[str, Any]) -> str:
    if market['seasonal_alignment_score'] >= 85:
        return 'seasonal urgency'
    if (campaign_goal or '').lower() in {'lead_generation', 'awareness'}:
        return 'educational value'
    return 'problem solution'

def _executive_risks(workflow: dict[str, Any], market: dict[str, Any], profit: dict[str, Any]) -> list[dict[str, Any]]:
    risks = []
    if workflow['workflow_risk_score'] >= 60:
        risks.append({'area': 'workflow', 'score': workflow['workflow_risk_score'], 'reason': 'Workflow failures or retries are elevated.'})
    if market['competition_pressure_score'] >= 70:
        risks.append({'area': 'market', 'score': market['competition_pressure_score'], 'reason': 'Competition pressure is high.'})
    if profit['efficiency_score'] <= 45:
        risks.append({'area': 'profit', 'score': 100 - profit['efficiency_score'], 'reason': 'Spend efficiency is weak.'})
    return risks

def _executive_actions(product_data: dict[str, Any], campaign_data: dict[str, Any], workflow: dict[str, Any], market: dict[str, Any]) -> list[str]:
    actions = []
    if product_data['top_products']:
        actions.append(f"Prioritize {product_data['top_products'][0]['product_name']} for the next campaign package.")
    if campaign_data['top_campaigns']:
        actions.append(f"Reuse winning patterns from {campaign_data['top_campaigns'][0]['campaign_name']}.")
    if workflow['workflow_risk_score'] >= 60:
        actions.append('Reduce automation risk before scaling publishing volume.')
    if market['market_opportunity_score'] >= 75:
        actions.append('Increase campaign testing while market timing is favorable.')
    return actions or ['Collect more product and campaign data before scaling spend.']

"""Runtime safeguards for the MCP Intelligence Bus."""


import json
import logging
import time
from collections import defaultdict, deque
from collections.abc import Callable
from datetime import UTC, datetime
from threading import RLock
from typing import Any

logger = logging.getLogger("mynat.mcp.intelligence")


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


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
    value = sum(float(score or 0) * weight for score, weight in parts.values()) / total_weight
    return clamp_score(value)


class IntelligenceRuntime:
    """In-memory operating layer for intelligence calls.

    This is intentionally process-local. It avoids duplicate calculations inside
    one MCP worker, while the function contracts stay stable for Redis-backed
    caching later.
    """

    def __init__(
        self,
        ttl_seconds: int = 300,
        max_requests_per_minute: int = 120,
        max_retries: int = 2,
        circuit_failure_threshold: int = 3,
        circuit_reset_seconds: int = 60,
    ) -> None:
        self.ttl_seconds = ttl_seconds
        self.max_requests_per_minute = max_requests_per_minute
        self.max_retries = max_retries
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_reset_seconds = circuit_reset_seconds
        self._cache: dict[str, tuple[float, dict[str, Any]]] = {}
        self._requests: dict[str, deque[float]] = defaultdict(deque)
        self._circuits: dict[str, dict[str, Any]] = defaultdict(lambda: {"failures": 0, "opened_at": None})
        self._metrics: dict[str, dict[str, float]] = defaultdict(
            lambda: {
                "request_count": 0,
                "cache_hits": 0,
                "errors": 0,
                "rate_limited": 0,
                "circuit_open": 0,
                "total_latency_ms": 0.0,
            }
        )
        self._lock = RLock()

    def run(
        self,
        service_name: str,
        params: dict[str, Any],
        compute: Callable[[], dict[str, Any]],
        *,
        fallback: dict[str, Any] | None = None,
        ttl_seconds: int | None = None,
    ) -> dict[str, Any]:
        started = time.perf_counter()
        normalized_params = self._normalize_params(params)
        cache_key = self._cache_key(service_name, normalized_params)
        with self._lock:
            self._metrics[service_name]["request_count"] += 1
            cached = self._cache.get(cache_key)
            if cached and cached[0] > time.time():
                self._metrics[service_name]["cache_hits"] += 1
                payload = dict(cached[1])
                payload["cached"] = True
                payload["generated_at"] = utc_now()
                return payload
            if not self._allow_request(service_name):
                self._metrics[service_name]["rate_limited"] += 1
                return self._failure(service_name, "rate_limited", "Intelligence rate limit exceeded", fallback)
            if self._circuit_open(service_name):
                self._metrics[service_name]["circuit_open"] += 1
                return self._failure(service_name, "circuit_open", "Circuit breaker is open", fallback)

        last_error = ""
        for attempt in range(1, self.max_retries + 2):
            try:
                result = compute()
                payload = self._success(service_name, normalized_params, result, started)
                with self._lock:
                    self._circuits[service_name] = {"failures": 0, "opened_at": None}
                    self._metrics[service_name]["total_latency_ms"] += payload["runtime"]["latency_ms"]
                    self._cache[cache_key] = (time.time() + (ttl_seconds or self.ttl_seconds), dict(payload))
                logger.info(
                    "mcp_intelligence_success",
                    extra={"service": service_name, "latency_ms": payload["runtime"]["latency_ms"]},
                )
                return payload
            except Exception as exc:  # pragma: no cover - defensive guard around arbitrary service failures
                last_error = str(exc)
                if attempt <= self.max_retries:
                    time.sleep(min(0.05 * attempt, 0.2))

        with self._lock:
            circuit = self._circuits[service_name]
            circuit["failures"] += 1
            if circuit["failures"] >= self.circuit_failure_threshold:
                circuit["opened_at"] = time.time()
            self._metrics[service_name]["errors"] += 1
            self._metrics[service_name]["total_latency_ms"] += round((time.perf_counter() - started) * 1000, 2)
        logger.exception("mcp_intelligence_failure", extra={"service": service_name, "error": last_error})
        return self._failure(service_name, "failed", last_error, fallback)

    def metrics(self) -> dict[str, Any]:
        with self._lock:
            services = {}
            for service_name, values in self._metrics.items():
                request_count = int(values["request_count"])
                services[service_name] = {
                    "request_count": request_count,
                    "cache_hits": int(values["cache_hits"]),
                    "cache_hit_rate": percent(values["cache_hits"], request_count),
                    "errors": int(values["errors"]),
                    "error_rate": percent(values["errors"], request_count),
                    "rate_limited": int(values["rate_limited"]),
                    "circuit_open": int(values["circuit_open"]),
                    "average_latency_ms": round(safe_divide(values["total_latency_ms"], request_count), 2),
                }
            totals = {
                "request_count": sum(item["request_count"] for item in services.values()),
                "cache_hits": sum(item["cache_hits"] for item in services.values()),
                "errors": sum(item["errors"] for item in services.values()),
            }
            totals["cache_hit_rate"] = percent(totals["cache_hits"], totals["request_count"])
            totals["error_rate"] = percent(totals["errors"], totals["request_count"])
            return {
                "success": True,
                "generated_at": utc_now(),
                "cache": {
                    "ttl_seconds": self.ttl_seconds,
                    "entries": len(self._cache),
                    "hit_rate": totals["cache_hit_rate"],
                },
                "rate_limit": {"max_requests_per_minute": self.max_requests_per_minute},
                "circuit_breakers": {
                    name: {"failures": int(state["failures"]), "open": state["opened_at"] is not None}
                    for name, state in self._circuits.items()
                },
                "totals": totals,
                "services": services,
            }

    def clear(self) -> None:
        with self._lock:
            self._cache.clear()
            self._requests.clear()
            self._circuits.clear()
            self._metrics.clear()

    def _success(
        self, service_name: str, params: dict[str, Any], result: dict[str, Any], started: float
    ) -> dict[str, Any]:
        payload = dict(result)
        payload.update(
            {
                "success": payload.get("success", True),
                "service": service_name,
                "cached": False,
                "generated_at": utc_now(),
                "params": params,
                "runtime": {
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "cache_ttl_seconds": self.ttl_seconds,
                    "source": "mcp_intelligence_bus",
                },
            }
        )
        return payload

    def _failure(
        self, service_name: str, status: str, message: str, fallback: dict[str, Any] | None
    ) -> dict[str, Any]:
        return {
            "success": False,
            "service": service_name,
            "status": status,
            "error": message,
            "fallback": fallback or {},
            "cached": False,
            "generated_at": utc_now(),
        }

    def _allow_request(self, service_name: str) -> bool:
        now = time.time()
        window = self._requests[service_name]
        while window and window[0] < now - 60:
            window.popleft()
        if len(window) >= self.max_requests_per_minute:
            return False
        window.append(now)
        return True

    def _circuit_open(self, service_name: str) -> bool:
        state = self._circuits[service_name]
        opened_at = state.get("opened_at")
        if not opened_at:
            return False
        if time.time() - float(opened_at) >= self.circuit_reset_seconds:
            state["opened_at"] = None
            state["failures"] = 0
            return False
        return True

    def _cache_key(self, service_name: str, params: dict[str, Any]) -> str:
        return f"{service_name}:{json.dumps(params, sort_keys=True, default=str)}"

    def _normalize_params(self, params: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(params, sort_keys=True, default=str))


runtime = IntelligenceRuntime()
