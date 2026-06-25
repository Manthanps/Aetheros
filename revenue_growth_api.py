"""Revenue Growth Agent — FastAPI route."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class RevenueGrowthRequest(BaseModel):
    products: list[dict[str, Any]] = Field(default_factory=list)
    analytics: dict[str, Any] = Field(default_factory=dict)
    reviews: list[dict[str, Any]] = Field(default_factory=list)
    campaign_history: list[dict[str, Any]] = Field(default_factory=list)
    shopify_data: dict[str, Any] = Field(default_factory=dict)
    use_llm: bool = True


@router.post("/revenue-growth")
async def run_revenue_growth(request: RevenueGrowthRequest):
    """
    Run the Revenue Growth Agent.

    Returns a comprehensive 30-day growth plan including:
    - Best products to promote (with opportunity scores)
    - 30-day content calendar (Instagram, Facebook, WhatsApp, Blog, Email)
    - Reel strategy with scripts and scene breakdowns
    - SEO recommendations per product
    - Email campaign sequences (welcome, cart recovery, re-engagement, etc.)
    - Bundles, upsells, cross-sells with expected AOV impact
    - Customer insights (pain points, objections, personas)
    - Growth recommendations with KPIs
    - Expected business impact projections

    All outputs are status=draft — nothing is auto-published.
    """
    from agents.revenue_growth_agent import run_revenue_growth_agent
    return run_revenue_growth_agent(
        products=request.products,
        analytics=request.analytics,
        reviews=request.reviews,
        campaign_history=request.campaign_history,
        shopify_data=request.shopify_data,
        use_llm=request.use_llm,
    )


@router.post("/revenue-growth/opportunities")
async def product_opportunities(request: RevenueGrowthRequest):
    """Run only the Product Opportunity Engine."""
    from agents.revenue_grower import detect_product_opportunities
    return detect_product_opportunities(
        products=request.products,
        analytics=request.analytics,
        reviews=request.reviews,
        campaign_history=request.campaign_history,
    )


@router.post("/revenue-growth/content-strategy")
async def content_strategy(request: RevenueGrowthRequest):
    """Run only the Content Strategy Engine (30-day calendar + reel strategy)."""
    from agents.revenue_grower import generate_content_strategy
    return generate_content_strategy(
        products=request.products,
        analytics=request.analytics,
        campaign_history=request.campaign_history,
        use_llm=request.use_llm,
    )


@router.post("/revenue-growth/seo")
async def seo_growth(request: RevenueGrowthRequest):
    """Run only the SEO Growth Engine."""
    from agents.revenue_grower import generate_seo_recommendations
    return generate_seo_recommendations(
        products=request.products,
        use_llm=request.use_llm,
    )


@router.post("/revenue-growth/recommendations")
async def revenue_recommendations(request: RevenueGrowthRequest):
    """Run only the Revenue Recommendation Engine (bundles, upsells, email campaigns)."""
    from agents.revenue_grower import generate_revenue_recommendations
    return generate_revenue_recommendations(
        products=request.products,
        analytics=request.analytics,
        use_llm=request.use_llm,
    )


@router.post("/revenue-growth/customer-insights")
async def customer_insights(request: RevenueGrowthRequest):
    """Run only the Customer Insight Engine."""
    from agents.revenue_grower import generate_customer_insights
    return generate_customer_insights(
        products=request.products,
        reviews=request.reviews,
        use_llm=request.use_llm,
    )
