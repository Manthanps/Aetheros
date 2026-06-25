"""
Creator Agent — flat module (merged from agents/creator_agent/ package).
Mynat's campaign strategy brain: product intelligence, seasonal analysis, channel strategy.
"""
from __future__ import annotations

# ── creator_agent/creator_models.py ──────────────────────────────────────────

from datetime import datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator

Platform = Literal["instagram", "facebook", "meta", "whatsapp", "email", "blog"]
AssetType = Literal["social_post", "story", "reel_cover", "carousel", "banner", "ad_creative"]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


class ContentAgentInput(BaseModel):
    headline: str = ""
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""
    target_audience: str = ""
    campaign_goal: str = ""
    platform: Platform = "instagram"

    @classmethod
    def from_content_output(cls, content_output: dict[str, Any] | None, creator_output: dict[str, Any] | None = None) -> "ContentAgentInput":
        content = content_output or {}
        creator = creator_output or {}
        cta_options = content.get("cta_options") or []
        caption = (content.get("instagram_caption") or content.get("facebook_caption") or content.get("whatsapp_message") or "")
        headline = ""
        ad_copy = content.get("ad_copy") or {}
        if isinstance(ad_copy, dict):
            headline = ad_copy.get("headline", "")
        return cls(headline=headline or content.get("seo_title", "") or creator.get("recommended_product", ""), caption=caption, hashtags=content.get("hashtags", []) or [], cta=(cta_options[0] if cta_options else creator.get("cta", "")), target_audience=creator.get("target_audience") or (content.get("_meta") or {}).get("target_audience", ""), campaign_goal=(creator.get("campaign_strategy") or {}).get("campaign_objective", ""), platform=creator.get("platform", "instagram"))


class CreatorAssetRequest(BaseModel):
    product_data: dict[str, Any]
    content_input: ContentAgentInput | None = None
    content_output: dict[str, Any] | None = None
    creator_strategy: dict[str, Any] | None = None
    business_context: dict[str, Any] = Field(default_factory=dict)
    campaign_goals: dict[str, Any] = Field(default_factory=dict)
    rag_context: dict[str, Any] | None = None
    platform: Platform = "instagram"
    asset_type: AssetType = "social_post"
    workflow_id: str = "untracked"
    approval_required: bool = True
    create_canva_design: bool = False
    persist: bool = True

    @field_validator("product_data")
    @classmethod
    def require_product_name(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not value or not value.get("name"):
            raise ValueError("product_data.name is required")
        return value


class CanvaInstruction(BaseModel):
    design_prompt: str
    design_type: AssetType
    dimensions: dict[str, int]
    layout: dict[str, Any]
    colors: list[str]
    typography: dict[str, Any]
    elements: list[dict[str, Any]]
    cta_placement: str
    image_requirements: list[str]
    brand_alignment: dict[str, Any]
    api_payload: dict[str, Any]
    canva_result: dict[str, Any] = Field(default_factory=dict)


class MetaAsset(BaseModel):
    platform: Platform
    asset_type: AssetType
    meta_payload: dict[str, Any]
    instagram_payload: dict[str, Any]
    facebook_payload: dict[str, Any]
    approval_required: bool = True
    status: Literal["draft", "queued_for_approval"] = "draft"


class CreativePackage(BaseModel):
    success: bool = True
    job_id: str = Field(default_factory=lambda: new_id("creator_job"))
    asset_id: str = Field(default_factory=lambda: new_id("creative_asset"))
    workflow_id: str = "untracked"
    product: dict[str, Any]
    content_input: ContentAgentInput
    creative_strategy: dict[str, Any]
    visual_strategy: dict[str, Any]
    cta_strategy: dict[str, Any]
    canva: CanvaInstruction
    meta: MetaAsset
    publishing_assets: dict[str, Any]
    rag_summary: dict[str, Any]
    approval: dict[str, Any]
    status: Literal["draft", "queued_for_approval"] = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


class CreatorJobRecord(BaseModel):
    job_id: str
    workflow_id: str
    status: str
    creative_package: dict[str, Any]


# ── creator_agent/prompts.py ──────────────────────────────────────────────────

STRATEGY_REVIEW_PROMPT = """You are Mynat's senior campaign strategist.

Review the campaign intelligence report below and improve only the strategy.
Do not write final captions, hashtags, ad copy, email copy, or publishing copy.

Campaign intelligence report:
{campaign_report}

Return ONLY valid JSON:
{{
  "strategy_strengths": ["..."],
  "strategy_gaps": ["..."],
  "recommended_adjustments": ["..."],
  "confidence_adjustment": -5,
  "risk_adjustment": 5
}}"""


# ── creator_agent/tools.py ────────────────────────────────────────────────────

import math
import re
from statistics import mean

MONTH_TO_SEASON: dict[int, str] = {1: "winter", 2: "winter", 3: "summer", 4: "summer", 5: "summer", 6: "monsoon", 7: "monsoon", 8: "monsoon", 9: "festive", 10: "festive", 11: "festive", 12: "winter"}

SEASON_ANGLES: dict[str, dict[str, str]] = {
    "summer":  {"theme": "Beat the heat with nature", "problem": "sun damage, oily skin, sweating, tanning", "benefit_angle": "cooling, hydrating, lightweight, SPF-friendly", "trending_keywords": ["summer skincare", "glow", "hydration", "sun protection"]},
    "monsoon": {"theme": "Keep your skin fresh through the rains", "problem": "humidity, fungal issues, dull skin, excess oil", "benefit_angle": "anti-fungal herbs, balancing, non-sticky, purifying", "trending_keywords": ["monsoon skincare", "clear skin", "natural ingredients"]},
    "winter":  {"theme": "Nourish and protect in the cold", "problem": "dry skin, chapped lips, rough texture, dullness", "benefit_angle": "deeply moisturizing, rich oils, protective, healing", "trending_keywords": ["winter skincare", "moisturizer", "nourishing", "dry skin"]},
    "festive": {"theme": "Glow for every celebration", "problem": "dull skin before events, party prep, gifting", "benefit_angle": "radiance, glow-boosting, festive gift sets, natural glamour", "trending_keywords": ["festive glow", "Diwali skincare", "gift set", "natural beauty"]},
}

SKINCARE_PROBLEM_KEYWORDS = {
    "acne": {"pain": 88, "urgency": 82, "emotion": 90, "frequency": 78}, "pimple": {"pain": 84, "urgency": 80, "emotion": 88, "frequency": 75}, "dark spot": {"pain": 76, "urgency": 65, "emotion": 84, "frequency": 70}, "pigmentation": {"pain": 78, "urgency": 64, "emotion": 82, "frequency": 68}, "tan": {"pain": 68, "urgency": 70, "emotion": 72, "frequency": 72}, "dry": {"pain": 70, "urgency": 74, "emotion": 66, "frequency": 82}, "dull": {"pain": 64, "urgency": 58, "emotion": 78, "frequency": 76}, "oil": {"pain": 67, "urgency": 66, "emotion": 68, "frequency": 80}, "hair fall": {"pain": 90, "urgency": 86, "emotion": 94, "frequency": 82}, "frizz": {"pain": 66, "urgency": 58, "emotion": 64, "frequency": 75}, "glow": {"pain": 58, "urgency": 54, "emotion": 76, "frequency": 64}, "aging": {"pain": 72, "urgency": 56, "emotion": 82, "frequency": 64}, "wrinkle": {"pain": 75, "urgency": 58, "emotion": 84, "frequency": 66},
}

INGREDIENT_SIGNALS = {
    "turmeric": {"scientific": 72, "marketing": 86, "customer": 82, "unique": 58}, "haldi": {"scientific": 72, "marketing": 86, "customer": 82, "unique": 58}, "saffron": {"scientific": 62, "marketing": 90, "customer": 84, "unique": 72}, "kesar": {"scientific": 62, "marketing": 90, "customer": 84, "unique": 72}, "rose": {"scientific": 58, "marketing": 82, "customer": 78, "unique": 60}, "neem": {"scientific": 78, "marketing": 82, "customer": 84, "unique": 62}, "aloe": {"scientific": 76, "marketing": 80, "customer": 82, "unique": 50}, "kumkumadi": {"scientific": 68, "marketing": 92, "customer": 78, "unique": 88}, "amla": {"scientific": 80, "marketing": 76, "customer": 78, "unique": 60}, "bhringraj": {"scientific": 74, "marketing": 78, "customer": 76, "unique": 74}, "ashwagandha": {"scientific": 70, "marketing": 82, "customer": 72, "unique": 70}, "sandalwood": {"scientific": 60, "marketing": 84, "customer": 78, "unique": 64}, "chandan": {"scientific": 60, "marketing": 84, "customer": 78, "unique": 64}, "tea tree": {"scientific": 78, "marketing": 76, "customer": 80, "unique": 50}, "vitamin c": {"scientific": 84, "marketing": 86, "customer": 84, "unique": 48},
}

CHANNEL_BASELINES = {
    "instagram": {"reach": 82, "engagement": 86, "conversion": 68, "suitability": 88}, "facebook": {"reach": 70, "engagement": 62, "conversion": 60, "suitability": 66}, "linkedin": {"reach": 42, "engagement": 36, "conversion": 28, "suitability": 25}, "whatsapp": {"reach": 58, "engagement": 84, "conversion": 82, "suitability": 70}, "email": {"reach": 54, "engagement": 58, "conversion": 76, "suitability": 64}, "blog": {"reach": 48, "engagement": 44, "conversion": 46, "suitability": 72},
}


def clamp_score(value: float, minimum: int = 0, maximum: int = 100) -> int:
    return int(max(minimum, min(maximum, round(value))))


def parse_price(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    cleaned = re.sub(r"[^0-9.]", "", str(value))
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0


def product_text(product: dict[str, Any]) -> str:
    values = [product.get("name", ""), product.get("description", ""), product.get("short_description", ""), product.get("category", ""), " ".join(map(str, product.get("tags", []) or [])), " ".join(map(str, product.get("ingredients", []) or []))]
    specifications = product.get("specifications") or {}
    if isinstance(specifications, dict):
        values.extend(str(v) for v in specifications.values())
    return " ".join(str(v) for v in values if v).lower()


def extract_ingredients(product: dict[str, Any]) -> list[str]:
    raw = product.get("ingredients") or product.get("key_ingredients") or []
    if isinstance(raw, str):
        ingredients = re.split(r"[,;/|]+", raw)
    elif isinstance(raw, list):
        ingredients = [str(item) for item in raw]
    else:
        ingredients = []
    text = product_text(product)
    detected = [name for name in INGREDIENT_SIGNALS if name in text]
    merged = []
    for item in ingredients + detected:
        clean = item.strip().lower()
        if clean and clean not in merged:
            merged.append(clean)
    return merged


def detect_seasonal_opportunity(month: int, products: list[dict]) -> dict[str, Any]:
    season = MONTH_TO_SEASON.get(month, "festive")
    season_info = SEASON_ANGLES.get(season, SEASON_ANGLES["festive"])
    scored_products = []
    for product in products:
        score = 0
        product_text_val = (f"{product.get('name', '')} {product.get('description', '')} {product.get('category', '')} {' '.join(product.get('tags', []))}").lower()
        for keyword in season_info["trending_keywords"]:
            if keyword.lower() in product_text_val:
                score += 2
        for problem_word in season_info["problem"].split(", "):
            if problem_word.lower() in product_text_val:
                score += 1
        scored_products.append({**product, "_seasonal_score": score})
    scored_products.sort(key=lambda p: p["_seasonal_score"], reverse=True)
    return {"month": month, "season": season, "theme": season_info["theme"], "problem": season_info["problem"], "benefit_angle": season_info["benefit_angle"], "trending_keywords": season_info["trending_keywords"], "top_seasonal_products": scored_products[:5]}


def analyze_social_reviews(report: dict) -> dict[str, Any]:
    if not report:
        return {"overall_sentiment": "neutral", "marketing_strengths": ["natural ingredients", "Ayurvedic formula"], "concerns_to_address": [], "star_rating": 4.0, "best_content_angle": "natural and effective skincare", "avoid_mentioning": []}
    sentiment = report.get("sentiment", {})
    positive_pct = sentiment.get("positive", 70)
    if positive_pct >= 70:
        overall = "very_positive"
    elif positive_pct >= 50:
        overall = "positive"
    elif positive_pct >= 30:
        overall = "mixed"
    else:
        overall = "negative"
    positives = report.get("key_positives", [])
    best_angle = positives[0] if positives else "natural Ayurvedic formula"
    negatives = report.get("key_negatives", [])
    return {"overall_sentiment": overall, "marketing_strengths": positives[:3], "concerns_to_address": negatives[:2], "star_rating": report.get("average_rating", 4.0), "best_content_angle": best_angle, "key_themes": report.get("key_themes", []), "avoid_mentioning": negatives, "summary": report.get("summary", "")}


def choose_best_product(products: list[dict], season_data: dict, review_insights: dict, performance_report: dict | None = None) -> dict[str, Any]:
    if not products:
        return {}
    seasonal_top = {p.get("name", ""): p.get("_seasonal_score", 0) for p in season_data.get("top_seasonal_products", [])}
    performance_top = {}
    if performance_report:
        for product_perf in performance_report.get("top_products", []):
            performance_top[product_perf.get("name", "")] = product_perf.get("sales", 0)
    scored = []
    for product in products:
        name = product.get("name", "")
        score = 0
        breakdown = {}
        seasonal_score = min(seasonal_top.get(name, 0) * 5, 30)
        breakdown["seasonal_fit"] = seasonal_score
        score += seasonal_score
        sentiment_map = {"very_positive": 25, "positive": 18, "mixed": 10, "negative": 0}
        sentiment_score = sentiment_map.get(review_insights.get("overall_sentiment", "mixed"), 10)
        breakdown["sentiment"] = sentiment_score
        score += sentiment_score
        max_sales = max(performance_top.values(), default=1)
        perf_score = int((performance_top.get(name, 0) / max_sales) * 25) if max_sales else 0
        breakdown["past_performance"] = perf_score
        score += perf_score
        stock = product.get("stock", 50)
        stock_score = 10 if stock >= 50 else 7 if stock >= 20 else 4 if stock >= 10 else 2 if stock > 0 else 0
        breakdown["stock"] = stock_score
        score += stock_score
        price = float(product.get("price", 0))
        price_score = 10 if 200 <= price <= 500 else 7 if 100 <= price <= 800 else 4
        breakdown["price"] = price_score
        score += price_score
        scored.append({**product, "_total_score": score, "_score_breakdown": breakdown})
    best = max(scored, key=lambda p: p["_total_score"])
    urgency_note = f"Only {best['stock']} units left — add urgency to the copy!" if 0 < best.get("stock", 50) < 10 else ""
    return {"product": best, "total_score": best["_total_score"], "score_breakdown": best["_score_breakdown"], "urgency_note": urgency_note}


def create_canva_design_brief(product: dict, seasonal_angle: str, platform: str = "instagram", content_type: str = "post") -> dict[str, Any]:
    name = product.get("name", "Product")
    category = product.get("category", "skincare").lower()
    price = parse_price(product.get("price", 0))
    layout_map = {"post": "product_center", "reel": "lifestyle_scene", "story": "quote_overlay", "carousel": "before_after"}
    layout = layout_map.get(content_type, "product_center")
    color_map = {"hair": ["#C8872A", "#FFF5E1", "#8B4513"], "face": ["#F5C2C7", "#FFF5E1", "#C8872A"], "body": ["#2D4A27", "#FFF5E1", "#C8872A"], "skin": ["#F5C2C7", "#FFF5E1", "#C8872A"], "oil": ["#C8872A", "#8B4513", "#FFF5E1"]}
    color_key = next((k for k in color_map if k in category), "face")
    colors = color_map[color_key]
    size_map = {"instagram": "1080x1080 (square post)", "facebook": "1200x630 (landscape)", "story": "1080x1920 (vertical story)"}
    size = size_map.get(platform, "1080x1080")
    return {"title": f"{name} — {seasonal_angle[:30]}", "size": size, "layout": layout, "text_overlay": seasonal_angle[:40] if seasonal_angle else f"Natural {category.title()} Care", "sub_text": f"₹{price:.0f} | mynat.in", "colors": colors, "font_style": "elegant_serif", "image_suggestions": [f"Product shot of {name} on a {colors[1]} background", "Indian woman with glowing skin in natural light", "Ayurvedic herbs/ingredients relevant to the product"], "mood": "natural", "product_placement": "center_hero", "execution_owner": "canva_agent"}


def prepare_meta_post_payload(caption: str, platform: str = "instagram", image_url: str = "", content_type: str = "post") -> dict[str, Any]:
    media_type_map = {"post": "IMAGE", "reel": "VIDEO", "story": "IMAGE", "carousel": "CAROUSEL"}
    media_type = media_type_map.get(content_type, "IMAGE")
    return {"platform": platform, "caption": caption, "media_type": media_type, "media_url": image_url, "status": "draft", "scheduled_publish_time": None, "targeting": {"age_min": 18, "age_max": 45, "genders": [2], "geo_locations": {"countries": ["IN"], "cities": [{"key": "2295424", "name": "Mumbai"}, {"key": "2295423", "name": "Delhi"}]}}, "call_to_action": {"type": "SHOP_NOW", "value": {"link": "https://mynat.in"}}, "execution_owner": "content_agent_and_publishing_guard"}


def analyze_commercial_viability(product: dict[str, Any]) -> dict[str, Any]:
    text = product_text(product)
    matched = [data for key, data in SKINCARE_PROBLEM_KEYWORDS.items() if key in text]
    if not matched:
        matched = [{"pain": 58, "urgency": 48, "emotion": 58, "frequency": 55}]
    pain = mean(item["pain"] for item in matched)
    urgency = mean(item["urgency"] for item in matched)
    emotion = mean(item["emotion"] for item in matched)
    frequency = mean(item["frequency"] for item in matched)
    price = parse_price(product.get("price"))
    willingness = 78 if 250 <= price <= 899 else 62 if price < 1500 else 48
    competition = 72 if any(word in text for word in ("glow", "acne", "hair", "face", "serum")) else 56
    ignore_resistance = mean([pain, urgency, emotion, frequency])
    score = mean([pain, urgency, emotion, frequency, willingness, 100 - (competition * 0.35)])
    return {"commercial_viability_score": clamp_score(score), "commercial_viability_reason": f"The product addresses a customer problem with measurable emotional and practical value. Pain={clamp_score(pain)}, urgency={clamp_score(urgency)}, emotion={clamp_score(emotion)}, frequency={clamp_score(frequency)}, willingness_to_pay={clamp_score(willingness)}.", "problem_pain_score": clamp_score(pain), "problem_urgency_score": clamp_score(urgency), "problem_emotional_score": clamp_score(emotion), "problem_frequency_score": clamp_score(frequency), "can_customer_ignore_problem": ignore_resistance < 62, "customer_willingness_to_pay_score": clamp_score(willingness), "competition_intensity_score": clamp_score(competition)}


def analyze_ingredient_intelligence(product: dict[str, Any]) -> dict[str, Any]:
    ingredients = extract_ingredients(product)
    rows = []
    for ingredient in ingredients:
        signal = next((v for key, v in INGREDIENT_SIGNALS.items() if key in ingredient), None)
        if not signal:
            signal = {"scientific": 50, "marketing": 52, "customer": 48, "unique": 42}
        strength = mean([signal["scientific"], signal["customer"]])
        rows.append({"ingredient": ingredient, "scientific_relevance_score": signal["scientific"], "marketing_relevance_score": signal["marketing"], "customer_relevance_score": signal["customer"], "competitive_uniqueness_score": signal["unique"], "ingredient_strength_score": clamp_score(strength), "ingredient_differentiation_score": clamp_score(signal["unique"]), "ingredient_marketing_value": "High customer familiarity and Ayurvedic relevance make this useful for proof-led positioning." if signal["marketing"] >= 75 else "Useful as supporting proof, but it should not carry the campaign alone.", "why_customers_care": "Customers connect it with visible skincare benefits, natural safety, and Indian beauty traditions."})
    aggregate_strength = mean([row["ingredient_strength_score"] for row in rows]) if rows else 45
    aggregate_diff = mean([row["ingredient_differentiation_score"] for row in rows]) if rows else 35
    return {"ingredients": rows, "ingredient_strength_score": clamp_score(aggregate_strength), "ingredient_differentiation_score": clamp_score(aggregate_diff), "ingredient_marketing_value": "Ingredient story can support the campaign narrative." if aggregate_strength >= 55 else "Ingredient proof is thin from available product data; lean on benefits and customer outcomes."}


def analyze_benefit_intelligence(product: dict[str, Any]) -> dict[str, Any]:
    text = product_text(product)
    benefit_terms = {"hydration": ("functional", 78), "moistur": ("functional", 76), "glow": ("emotional", 86), "radiance": ("emotional", 84), "acne": ("functional", 88), "pimple": ("functional", 84), "dark spot": ("functional", 82), "pigmentation": ("functional", 82), "anti aging": ("lifestyle", 74), "wrinkle": ("lifestyle", 78), "confidence": ("emotional", 88), "natural": ("lifestyle", 72), "ayurvedic": ("social", 76), "hair fall": ("functional", 90), "smooth": ("emotional", 70), "soft": ("emotional", 68), "tan": ("functional", 76)}
    rows = []
    for term, (category, base) in benefit_terms.items():
        if term in text:
            uniqueness = 72 if term in ("ayurvedic", "hair fall", "pigmentation", "dark spot") else 55
            emotional = base + 8 if category == "emotional" else base - 4
            rows.append({"benefit": term.replace("moistur", "moisturizing"), "classification": category, "persuasion_score": clamp_score(base), "emotional_weight_score": clamp_score(emotional), "uniqueness_score": clamp_score(uniqueness), "marketability_score": clamp_score(mean([base, emotional, uniqueness]))})
    if not rows:
        rows.append({"benefit": "natural Ayurvedic skincare care", "classification": "lifestyle", "persuasion_score": 58, "emotional_weight_score": 60, "uniqueness_score": 52, "marketability_score": 57})
    rows.sort(key=lambda row: row["marketability_score"], reverse=True)
    return {"benefit_priority_matrix": rows, "most_marketable_benefit": rows[0]["benefit"], "most_emotional_benefit": max(rows, key=lambda row: row["emotional_weight_score"])["benefit"], "most_persuasive_benefit": max(rows, key=lambda row: row["persuasion_score"])["benefit"], "most_unique_benefit": max(rows, key=lambda row: row["uniqueness_score"])["benefit"]}


def analyze_pricing_intelligence(product: dict[str, Any], products: list[dict[str, Any]]) -> dict[str, Any]:
    price = parse_price(product.get("price"))
    peer_prices = [parse_price(item.get("price")) for item in products if item is not product and parse_price(item.get("price")) > 0]
    category = str(product.get("category", "")).lower()
    category_peers = [parse_price(item.get("price")) for item in products if item is not product and str(item.get("category", "")).lower() == category and parse_price(item.get("price")) > 0]
    baseline = mean(category_peers or peer_prices or [699])
    ratio = price / baseline if baseline and price else 1
    if ratio <= 0.75:
        position = "undervalued"
    elif ratio <= 1.2:
        position = "fairly_priced"
    elif ratio <= 1.7:
        position = "premium_priced"
    else:
        position = "overpriced"
    affordability = 88 if price <= 499 else 74 if price <= 899 else 58 if price <= 1499 else 38
    premium = clamp_score(45 + ratio * 28)
    risk = 28 if position == "fairly_priced" else 38 if position in ("undervalued", "premium_priced") else 72
    opportunity = 82 if position == "undervalued" else 76 if position == "fairly_priced" else 62 if position == "premium_priced" else 42
    return {"price": price, "reference_price": round(baseline, 2), "pricing_position": position, "customer_perceived_value": "strong" if affordability >= 70 else "moderate" if affordability >= 50 else "weak", "price_competitiveness_score": clamp_score(100 - abs(1 - ratio) * 55), "price_advantage_score": clamp_score(100 - ratio * 45), "premium_positioning_score": premium, "pricing_risk_score": risk, "pricing_opportunity_score": opportunity, "pricing_reason": f"Price is {round(ratio, 2)}x the available peer baseline, so the product is classified as {position}."}


def analyze_inventory_intelligence(product: dict[str, Any], performance_report: dict[str, Any] | None = None) -> dict[str, Any]:
    stock = int(parse_price(product.get("stock", 0)))
    sales_velocity = 0.0
    demand_trend = "unknown"
    performance_report = performance_report or {}
    for item in performance_report.get("top_products", []) or []:
        if item.get("name") == product.get("name"):
            sales_velocity = float(item.get("sales", item.get("units", 0)) or 0)
            demand_trend = "rising" if sales_velocity >= 20 else "steady"
            break
    if stock <= 0:
        action, readiness, risk, opportunity = "protect", 0, 95, 10
    elif stock < 10:
        action, readiness, risk, opportunity = "protect", 34, 82, 45
    elif stock < 25:
        action, readiness, risk, opportunity = "bundle", 62, 56, 68
    elif stock > 100:
        action, readiness, risk, opportunity = "aggressively_promote", 88, 28, 82
    else:
        action, readiness, risk, opportunity = "promote", 76, 35, 72
    if sales_velocity > stock and stock > 0:
        risk = clamp_score(risk + 20)
        action = "protect"
    return {"current_stock": stock, "sales_velocity": sales_velocity, "restock_frequency": performance_report.get("restock_frequency", "unknown"), "demand_trend": demand_trend, "recommended_inventory_action": action, "should_aggressively_promote": action == "aggressively_promote", "should_protect_inventory": action == "protect", "should_bundle": action == "bundle", "should_discount": action in ("bundle", "aggressively_promote") and stock >= 25, "inventory_campaign_readiness_score": readiness, "inventory_risk_score": risk, "inventory_opportunity_score": opportunity}


def analyze_market_intelligence(product: dict[str, Any], season_data: dict[str, Any], performance_report: dict[str, Any] | None = None) -> dict[str, Any]:
    text = product_text(product)
    season = season_data.get("season", "festive")
    seasonal_keywords = season_data.get("trending_keywords", [])
    seasonal_hits = sum(1 for keyword in seasonal_keywords if keyword.lower() in text)
    seasonal_alignment = clamp_score(48 + seasonal_hits * 14 + (12 if season in text else 0))
    trend_terms = (performance_report or {}).get("trend_keywords", []) or seasonal_keywords
    trend_hits = sum(1 for keyword in trend_terms if str(keyword).lower() in text)
    trend_alignment = clamp_score(50 + trend_hits * 10)
    competition = 78 if any(word in text for word in ("serum", "glow", "face", "acne")) else 58
    opportunity = clamp_score(mean([seasonal_alignment, trend_alignment, 100 - competition * 0.35]))
    return {"market_opportunity_score": opportunity, "competition_pressure_score": competition, "seasonal_alignment_score": seasonal_alignment, "trend_alignment_score": trend_alignment, "industry_trends": trend_terms[:8], "seasonality": season, "festival_relevance": "high" if season == "festive" else "medium", "consumer_psychology": "The campaign should connect product benefits to visible self-confidence and ritual-led self-care.", "why_now": f"{season.title()} context supports this product through {season_data.get('theme', 'seasonal relevance')}."}


def build_customer_personas(product: dict[str, Any], benefit_data: dict[str, Any], pricing: dict[str, Any]) -> dict[str, Any]:
    primary_benefit = benefit_data.get("most_emotional_benefit") or benefit_data.get("most_marketable_benefit", "natural care")
    price = pricing.get("price", 0)
    income = "middle income" if price <= 799 else "upper middle income"
    primary = {"name": "Urban Ritual Builder", "age": "24-38", "lifestyle": "Skincare-aware, digitally influenced, prefers natural but effective products", "income": income, "pain_points": [primary_benefit, "confusing product choices", "trust and ingredient safety"], "buying_triggers": ["visible benefit", "Ayurvedic credibility", "seasonal relevance", "clear value"], "objections": ["Will it work for my skin?", "Is it worth the price?", "Is it genuinely natural?"], "motivations": ["healthy glow", "confidence", "simple self-care ritual"], "emotional_drivers": ["feeling seen", "beauty confidence", "trust in Indian traditions"]}
    secondary = {"name": "Practical Family Buyer", "age": "32-50", "lifestyle": "Value-conscious buyer looking for reliable wellness products", "income": "middle income", "pain_points": ["skin/hair concern in family", "product safety", "price-value balance"], "buying_triggers": ["trusted ingredients", "offer or bundle", "reviews", "repeat-use value"], "objections": ["Delivery reliability", "proof of benefit", "price versus quantity"], "motivations": ["family care", "natural products", "low-risk purchase"], "emotional_drivers": ["responsibility", "trust", "practical wellness"]}
    confidence = 74 if product.get("description") else 58
    return {"primary_audience": primary, "secondary_audience": secondary, "customer_persona_report": [primary, secondary], "audience_confidence_score": confidence}


def build_campaign_strategy(product: dict[str, Any], commercial: dict[str, Any], benefits: dict[str, Any], pricing: dict[str, Any], inventory: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    if inventory["should_protect_inventory"]:
        objective, angle = "Retention", "Educational"
    elif commercial["commercial_viability_score"] >= 78 and pricing["price_advantage_score"] >= 60:
        objective, angle = "Sales", "Problem Solution"
    elif market["seasonal_alignment_score"] >= 72:
        objective, angle = "Brand Building", "Seasonal"
    else:
        objective, angle = "Awareness", "Educational"
    narrative = (f"Position {product.get('name', 'the product')} around {benefits.get('most_marketable_benefit')} with a {angle.lower()} narrative. The strategy should explain the customer problem, build trust through ingredient and Ayurvedic relevance, then move to a low-friction shopping CTA.")
    return {"campaign_objective": objective, "campaign_objective_reason": f"Selected because commercial viability is {commercial['commercial_viability_score']}, inventory readiness is {inventory['inventory_campaign_readiness_score']}, and market opportunity is {market['market_opportunity_score']}.", "campaign_angle": angle, "campaign_narrative": narrative, "what_should_be_marketed": product.get("name", ""), "why_should_it_be_marketed": commercial["commercial_viability_reason"], "who_should_see_it": "Primary and secondary personas defined in customer_personas.", "when_should_it_be_marketed": market["why_now"], "where_should_it_be_marketed": "Prioritize channels based on channel_strategy_report.", "how_should_it_be_marketed": narrative, "opportunities": [benefits.get("most_marketable_benefit", "benefit-led positioning"), pricing.get("pricing_position", "value positioning"), market.get("seasonality", "seasonal timing")], "risks": ["Inventory pressure" if inventory["inventory_risk_score"] >= 60 else "Low inventory risk", "Competitive category" if market["competition_pressure_score"] >= 70 else "Moderate competition", "Audience assumptions require validation through analytics"]}


def build_channel_strategy(product: dict[str, Any], campaign_strategy: dict[str, Any], personas: dict[str, Any], market: dict[str, Any]) -> dict[str, Any]:
    category = str(product.get("category", "")).lower()
    rows = {}
    for channel, baseline in CHANNEL_BASELINES.items():
        suitability = baseline["suitability"]
        if channel == "linkedin" and any(word in category for word in ("beauty", "skin", "hair", "face")):
            suitability -= 12
        if channel in ("blog", "email") and campaign_strategy["campaign_angle"] == "Educational":
            suitability += 10
        if channel == "whatsapp" and campaign_strategy["campaign_objective"] in ("Sales", "Retention"):
            suitability += 8
        score = clamp_score(mean([baseline["reach"], baseline["engagement"], baseline["conversion"], suitability]))
        rows[channel] = {"expected_reach_score": baseline["reach"], "expected_engagement_score": baseline["engagement"], "expected_conversion_score": baseline["conversion"], "content_suitability_score": clamp_score(suitability), "channel_priority_score": score, "recommended_use": "primary" if score >= 75 else "supporting" if score >= 55 else "deprioritize"}
    priority = sorted(rows, key=lambda key: rows[key]["channel_priority_score"], reverse=True)
    return {"channel_strategy_report": rows, "channel_priority_score": rows[priority[0]]["channel_priority_score"], "primary_channel": priority[0], "secondary_channels": priority[1:3]}


def build_critique_report(strategy: dict[str, Any], confidence_inputs: dict[str, int]) -> dict[str, Any]:
    weak = []
    if confidence_inputs.get("audience", 0) < 70:
        weak.append("Audience assumptions are inferred from product data rather than customer-level analytics.")
    if confidence_inputs.get("market", 0) < 70:
        weak.append("Market trend evidence is limited; campaign should be measured with a small test.")
    if confidence_inputs.get("ingredients", 0) < 55:
        weak.append("Ingredient proof is not strong enough to be the main promise.")
    return {"what_is_weak": weak or ["No major weakness found; still validate with live campaign metrics."], "what_is_missing": ["Live competitor pricing", "Recent platform engagement benchmarks", "Customer segment purchase history"], "assumptions_made": ["Product descriptions accurately represent customer-facing benefits.", "Available product catalog is the full current assortment.", "Performance report, when provided, is recent enough to guide channel decisions."], "risks_ignored": [], "uncertain_audience_insights": ["Exact income and lifestyle segments need validation through analytics and purchase data."], "low_confidence_campaign_decisions": [key for key, value in confidence_inputs.items() if value < 60], "improvement_applied": "Strategy prioritizes channels and messaging with the strongest deterministic evidence."}


def build_self_improvement_report() -> list[dict[str, Any]]:
    return [{"current_problem": "Creator Agent previously generated final captions and hashtags.", "business_impact": "Blurred ownership made strategy less rigorous and duplicated Content Agent work.", "technical_impact": "Prompt cost and validation risk increased because strategy and execution were mixed.", "recommended_fix": "Keep Creator output strategy-only and pass strategic context to Content Agent.", "priority": "critical", "status": "applied"}, {"current_problem": "Product choice used a narrow seasonal, sentiment, performance, stock, and price formula.", "business_impact": "Campaigns could miss stronger products with better customer psychology or pricing leverage.", "technical_impact": "Limited explainability and weaker tests around scoring.", "recommended_fix": "Add product, ingredient, benefit, pricing, inventory, market, channel, risk, and confidence engines.", "priority": "critical", "status": "applied"}, {"current_problem": "Persistence was focused on campaign drafts rather than strategy intelligence.", "business_impact": "Harder to audit why a campaign was recommended.", "technical_impact": "Weak workflow traceability.", "recommended_fix": "Persist Creator executions through workflow agent execution records.", "priority": "high", "status": "applied"}, {"current_problem": "MCP boundary was implied but not explicit.", "business_impact": "Future changes could bypass approved data channels.", "technical_impact": "External data access risk.", "recommended_fix": "Keep Creator deterministic and use only provided reports/RAG context, with no direct external API calls.", "priority": "high", "status": "applied"}]


def calculate_confidence_score(commercial: dict[str, Any], ingredients: dict[str, Any], market: dict[str, Any], personas: dict[str, Any], rag_available: bool) -> int:
    base = mean([commercial["commercial_viability_score"], ingredients["ingredient_strength_score"], market["market_opportunity_score"], personas["audience_confidence_score"]])
    if rag_available:
        base += 6
    else:
        base -= 8
    return clamp_score(base)


def calculate_risk_score(pricing: dict[str, Any], inventory: dict[str, Any], market: dict[str, Any], confidence_score: int) -> int:
    return clamp_score(mean([pricing["pricing_risk_score"], inventory["inventory_risk_score"], market["competition_pressure_score"] * 0.65, 100 - confidence_score]))


def analyze_product_strategy(product: dict[str, Any], products: list[dict[str, Any]], season_data: dict[str, Any], performance_report: dict[str, Any] | None = None) -> dict[str, Any]:
    commercial = analyze_commercial_viability(product)
    ingredients = analyze_ingredient_intelligence(product)
    benefits = analyze_benefit_intelligence(product)
    pricing = analyze_pricing_intelligence(product, products)
    inventory = analyze_inventory_intelligence(product, performance_report)
    market = analyze_market_intelligence(product, season_data, performance_report)
    personas = build_customer_personas(product, benefits, pricing)
    campaign = build_campaign_strategy(product, commercial, benefits, pricing, inventory, market)
    channels = build_channel_strategy(product, campaign, personas, market)
    product_score = clamp_score(mean([commercial["commercial_viability_score"], ingredients["ingredient_strength_score"], benefits["benefit_priority_matrix"][0]["marketability_score"], pricing["pricing_opportunity_score"], inventory["inventory_campaign_readiness_score"], market["market_opportunity_score"], channels["channel_priority_score"]]))
    return {"product": product, "product_score": product_score, "commercial": commercial, "ingredients": ingredients, "benefits": benefits, "pricing": pricing, "inventory": inventory, "market": market, "personas": personas, "campaign": campaign, "channels": channels}


def rank_campaign_products(products: list[dict[str, Any]], season_data: dict[str, Any], review_insights: dict[str, Any], performance_report: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    ranked = []
    sentiment_bonus = {"very_positive": 6, "positive": 3, "mixed": -2, "negative": -10}.get(review_insights.get("overall_sentiment", "mixed"), 0)
    for product in products:
        analysis = analyze_product_strategy(product, products, season_data, performance_report)
        analysis["product_score"] = clamp_score(analysis["product_score"] + sentiment_bonus)
        ranked.append(analysis)
    ranked.sort(key=lambda item: item["product_score"], reverse=True)
    return ranked


# ── creator_agent/services.py ─────────────────────────────────────────────────

import logging
import time
import httpx
from agents.product_knowledge import require_rag_context
from mcp_server.live_or_mock import should_use_live_api
from mcp_server.mcp_settings import get_settings
from backend.database.creator_asset_store import save_creator_dead_letter

logger = logging.getLogger(__name__)

CANVA_BASE_URL = 'https://api.canva.com/rest/v1'
GRAPH_API_BASE = 'https://graph.facebook.com/v19.0'
DIMENSIONS: dict[AssetType, dict[str, int]] = {'social_post': {'width': 1080, 'height': 1080}, 'story': {'width': 1080, 'height': 1920}, 'reel_cover': {'width': 1080, 'height': 1920}, 'carousel': {'width': 1080, 'height': 1080}, 'banner': {'width': 1200, 'height': 630}, 'ad_creative': {'width': 1080, 'height': 1080}}
BRAND_COLORS = ['#C8872A', '#FFF5E1', '#2D4A27', '#F5C2C7']


def compact_rag_summary(rag_context: dict[str, Any]) -> dict[str, Any]:
    context = rag_context.get('context_used') or []
    snippets: list[str] = []
    for item in context[:5]:
        if isinstance(item, dict):
            snippets.append(str(item.get('text') or item.get('summary') or item.get('name') or item)[:240])
        else:
            snippets.append(str(item)[:240])
    return {'available': bool(context), 'confidence': rag_context.get('confidence', 'low'), 'sources': rag_context.get('sources', []), 'snippets': snippets, 'error': rag_context.get('error', '')}


class CanvaService:
    """Prepare Canva design instructions and optionally create a Canva design."""

    def __init__(self, access_token: str | None = None) -> None:
        settings = get_settings()
        self.access_token = access_token or getattr(settings, 'canva_access_token', '')

    def generate_design_prompt(self, *, product: dict[str, Any], content: ContentAgentInput, asset_type: AssetType, rag_summary: dict[str, Any], visual_strategy: dict[str, Any]) -> str:
        product_name = product.get('name', 'Mynat product')
        category = product.get('category', 'Ayurvedic skincare')
        ingredients = ', '.join(map(str, product.get('ingredients', []) or product.get('tags', []) or []))
        rag_hint = '; '.join(rag_summary.get('snippets', [])[:2]) or 'Use Mynat premium Ayurvedic wellness brand context.'
        return f"Create a premium {category} {content.platform} {asset_type.replace('_', ' ')} for {product_name}. Use warm Ayurvedic luxury aesthetics, earthy herbal details, and clean Indian wellness branding. Place the product as the hero, keep the headline short: '{content.headline}', and reserve a clear CTA area for '{content.cta}'. Use Mynat colors {', '.join(BRAND_COLORS)} with {visual_strategy['mood']} mood. Ingredient cues: {ingredients or 'natural Ayurvedic botanicals'}. RAG context: {rag_hint}. Avoid medical claims, whitening/fairness language, clutter, and unreadable text."

    def build_instruction(self, *, product: dict[str, Any], content: ContentAgentInput, asset_type: AssetType, rag_summary: dict[str, Any], visual_strategy: dict[str, Any]) -> CanvaInstruction:
        dimensions = DIMENSIONS[asset_type]
        layout = {'structure': 'hero_product_center' if asset_type != 'carousel' else 'multi_slide_benefit_sequence', 'safe_zones': {'top': 96, 'bottom': 140, 'left': 72, 'right': 72}, 'headline_position': 'upper_third', 'product_position': 'center', 'cta_position': 'bottom_center', 'whitespace': 'generous'}
        typography = {'headline': {'family': 'premium serif or clean display', 'weight': 'bold', 'max_words': 7}, 'body': {'family': 'modern sans', 'weight': 'regular', 'max_lines': 2}, 'cta': {'family': 'modern sans', 'weight': 'semibold'}}
        elements = [{'type': 'product_image', 'role': 'hero', 'source': product.get('image_url', ''), 'required': True}, {'type': 'headline', 'text': content.headline, 'required': True}, {'type': 'cta', 'text': content.cta, 'required': bool(content.cta)}, {'type': 'ingredient_motifs', 'style': 'subtle botanical frame', 'required': False}, {'type': 'brand_mark', 'text': 'Mynat', 'required': True}]
        api_payload = {'type': 'type_and_asset', 'design_type': {'type': 'custom', 'width': dimensions['width'], 'height': dimensions['height']}, 'title': f"Mynat {product.get('name', 'Product')} {asset_type.replace('_', ' ').title()}"}
        return CanvaInstruction(design_prompt=self.generate_design_prompt(product=product, content=content, asset_type=asset_type, rag_summary=rag_summary, visual_strategy=visual_strategy), design_type=asset_type, dimensions=dimensions, layout=layout, colors=BRAND_COLORS, typography=typography, elements=elements, cta_placement='bottom_center', image_requirements=['Product image must be sharp, well-lit, and unobstructed.', 'Use ingredient imagery only as supporting accents.', 'No dense paragraph text inside the design.'], brand_alignment={'tone': 'premium Ayurvedic, trustworthy, natural, warm', 'avoid': ['medical claims', 'fairness or whitening language', 'visual clutter']}, api_payload=api_payload)

    def create_design(self, instruction: CanvaInstruction) -> dict[str, Any]:
        if not should_use_live_api('canva', ['canva_access_token']):
            return {'success': True, 'mode': 'prepared', 'api_payload': instruction.api_payload}
        headers = {'Authorization': f'Bearer {self.access_token}', 'Content-Type': 'application/json'}
        last_error: Any = ''
        try:
            with httpx.Client(timeout=20) as client:
                for attempt in range(3):
                    response = client.post(f'{CANVA_BASE_URL}/designs', headers=headers, json=instruction.api_payload)
                    data = response.json()
                    if response.status_code in (200, 201):
                        return {'success': True, 'provider': 'canva', **data}
                    last_error = data
                    if response.status_code not in (408, 425, 429, 500, 502, 503, 504):
                        break
                    time.sleep(0.4 * (attempt + 1))
        except Exception as exc:
            logger.exception('Canva design creation failed')
            save_creator_dead_letter(failure_type='canva.create_design', payload=instruction.model_dump(mode='json'), error=str(exc))
            return {'success': False, 'error': str(exc), 'api_payload': instruction.api_payload}
        save_creator_dead_letter(failure_type='canva.create_design', payload=instruction.model_dump(mode='json'), error=str(last_error))
        return {'success': False, 'status_code': response.status_code, 'error': last_error}

    def create_social_post(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)

    def create_story(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)

    def create_reel_cover(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)

    def create_carousel(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)

    def create_banner(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)

    def create_ad_creative(self, instruction: CanvaInstruction) -> dict[str, Any]:
        return self.create_design(instruction)


class MetaService:
    """Prepare Meta/Instagram/Facebook assets without publishing."""

    def create_campaign_asset(self, *, product: dict[str, Any], content: ContentAgentInput, objective: str) -> dict[str, Any]:
        return {'name': f"Mynat {product.get('name', 'Product')} {objective or 'Campaign'}", 'objective': objective or 'OUTCOME_SALES', 'status': 'PAUSED', 'special_ad_categories': []}

    def prepare_instagram_payload(self, *, product: dict[str, Any], content: ContentAgentInput, asset_type: AssetType) -> dict[str, Any]:
        media_type = 'REELS' if asset_type == 'reel_cover' else 'CAROUSEL' if asset_type == 'carousel' else 'IMAGE'
        return {'endpoint': f'{GRAPH_API_BASE}/{{instagram_business_account_id}}/media', 'method': 'POST', 'params': {'image_url': product.get('image_url', ''), 'caption': self._short_caption(content), 'media_type': media_type}, 'publish_step': {'endpoint': f'{GRAPH_API_BASE}/{{instagram_business_account_id}}/media_publish', 'method': 'POST', 'params': {'creation_id': '{creation_id}'}}, 'status': 'draft'}

    def prepare_facebook_payload(self, *, product: dict[str, Any], content: ContentAgentInput) -> dict[str, Any]:
        return {'endpoint': f'{GRAPH_API_BASE}/{{facebook_page_id}}/photos', 'method': 'POST', 'params': {'url': product.get('image_url', ''), 'caption': self._short_caption(content)}, 'status': 'draft'}

    def prepare_reel_payload(self, *, product: dict[str, Any], content: ContentAgentInput) -> dict[str, Any]:
        payload = self.prepare_instagram_payload(product=product, content=content, asset_type='reel_cover')
        payload['params']['cover_url'] = product.get('image_url', '')
        return payload

    def create_post_asset(self, *, product: dict[str, Any], content: ContentAgentInput, asset_type: AssetType, platform: Platform) -> MetaAsset:
        instagram_payload = self.prepare_instagram_payload(product=product, content=content, asset_type=asset_type)
        facebook_payload = self.prepare_facebook_payload(product=product, content=content)
        return MetaAsset(platform=platform, asset_type=asset_type, meta_payload={'campaign': self.create_campaign_asset(product=product, content=content, objective=content.campaign_goal), 'creative': self.create_ad_creative(product=product, content=content), 'status': 'draft'}, instagram_payload=instagram_payload, facebook_payload=facebook_payload, approval_required=True, status='queued_for_approval')

    def create_ad_creative(self, *, product: dict[str, Any], content: ContentAgentInput) -> dict[str, Any]:
        return {'object_story_spec': {'page_id': '{facebook_page_id}', 'instagram_actor_id': '{instagram_business_account_id}', 'link_data': {'message': self._short_caption(content), 'name': content.headline or product.get('name', ''), 'link': product.get('product_url') or 'https://mynat.in', 'call_to_action': {'type': 'SHOP_NOW', 'value': {'link': product.get('product_url') or 'https://mynat.in'}}}}, 'status': 'draft'}

    def _short_caption(self, content: ContentAgentInput) -> str:
        caption = content.caption.strip()
        if len(caption) > 500:
            caption = caption[:497].rstrip() + '...'
        tags = ' '.join(content.hashtags[:12])
        return f'{caption}\n\n{tags}'.strip()


class CreatorAssetService:
    """Orchestrates creative strategy, Canva instructions, and Meta assets."""

    def __init__(self, canva_service: CanvaService | None = None, meta_service: MetaService | None = None) -> None:
        self.canva_service = canva_service or CanvaService()
        self.meta_service = meta_service or MetaService()

    def generate_package(self, request: CreatorAssetRequest) -> CreativePackage:
        content = request.content_input or ContentAgentInput.from_content_output(request.content_output, request.creator_strategy)
        rag_context = request.rag_context or self._load_rag(request, content)
        rag_summary = compact_rag_summary(rag_context)
        visual_strategy = self.generate_visual_strategy(request, content, rag_summary)
        creative_strategy = self.generate_creative_strategy(request, content, rag_summary)
        cta_strategy = self.generate_cta_strategy(request, content)
        canva_instruction = self.canva_service.build_instruction(product=request.product_data, content=content, asset_type=request.asset_type, rag_summary=rag_summary, visual_strategy=visual_strategy)
        if request.create_canva_design:
            canva_instruction.canva_result = self.canva_service.create_design(canva_instruction)
        meta_asset = self.meta_service.create_post_asset(product=request.product_data, content=content, asset_type=request.asset_type, platform=request.platform)
        status = 'queued_for_approval' if request.approval_required else 'draft'
        return CreativePackage(workflow_id=request.workflow_id, product=request.product_data, content_input=content, creative_strategy=creative_strategy, visual_strategy=visual_strategy, cta_strategy=cta_strategy, canva=canva_instruction, meta=meta_asset, publishing_assets={'instagram': meta_asset.instagram_payload, 'facebook': meta_asset.facebook_payload, 'primary_platform': request.platform, 'approval_required': request.approval_required}, rag_summary=rag_summary, approval={'required': request.approval_required, 'status': 'pending' if request.approval_required else 'not_required', 'mechanism': 'approval_gate'}, status=status)

    def generate_creative_strategy(self, request: CreatorAssetRequest, content: ContentAgentInput, rag_summary: dict[str, Any]) -> dict[str, Any]:
        strategy = request.creator_strategy or {}
        campaign = strategy.get('campaign_strategy', {}) if isinstance(strategy, dict) else {}
        return {'goal': content.campaign_goal or campaign.get('campaign_objective') or request.campaign_goals.get('objective', 'Sales'), 'message_hierarchy': [content.headline or request.product_data.get('name', ''), 'product benefit proof', content.cta or 'Shop Now'], 'creative_angle': campaign.get('campaign_angle', 'Problem Solution'), 'audience': content.target_audience or request.campaign_goals.get('target_audience', ''), 'rag_influence': rag_summary.get('snippets', []), 'approval_note': 'Prepared as draft creative assets only; publishing requires approval.'}

    def generate_visual_strategy(self, request: CreatorAssetRequest, content: ContentAgentInput, rag_summary: dict[str, Any]) -> dict[str, Any]:
        category = str(request.product_data.get('category', '')).lower()
        mood = 'earthy premium herbal' if any((word in category for word in ('hair', 'oil', 'body'))) else 'fresh premium glow'
        return {'mood': mood, 'composition': 'hero product, clean headline, ingredient accents, visible CTA', 'lighting': 'soft natural premium studio light', 'background': 'warm ivory with subtle botanical texture', 'do_not_use': ['clutter', 'medical symbols', 'before-after claims without proof', 'fairness language'], 'rag_visual_cues': rag_summary.get('snippets', [])[:2]}

    def generate_cta_strategy(self, request: CreatorAssetRequest, content: ContentAgentInput) -> dict[str, Any]:
        cta = content.cta or 'Shop Now'
        return {'primary_cta': cta, 'placement': 'bottom_center', 'visual_weight': 'high', 'alternatives': ['Shop Now', 'Explore Mynat', 'Order Today', 'View Product'], 'risk_control': 'Avoid false urgency unless inventory data supports it.'}

    def _load_rag(self, request: CreatorAssetRequest, content: ContentAgentInput) -> dict[str, Any]:
        query = ' '.join((str(value) for value in (request.product_data.get('name', ''), request.product_data.get('category', ''), request.product_data.get('description', ''), content.headline, content.target_audience, 'Mynat brand guidelines historical campaigns best creatives') if value))
        return require_rag_context(query)


# ── creator_agent/creator_agent.py ────────────────────────────────────────────

import json
import logging as _logging
from uuid import uuid4

from agents.shared import call_claude, parse_json_object
from agents.product_knowledge import require_rag_context
from agents.agent_schemas import CreatorAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback

_logger = logging.getLogger(__name__)
MONTH_NAMES = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}


def _creator_fallback(reason: str, products: list[dict] | None = None) -> dict[str, Any]:
    product = (products or [{}])[0] if products else {}
    name = product.get('name', '')
    return safe_agent_fallback('creator', reason, recommended_product=name, reason='Fallback recommendation used because validated generation was unavailable.', seasonal_angle='Seasonal Ayurvedic skincare', target_audience='Mynat skincare customers', platform='instagram', content_type='post', instagram_caption='', facebook_caption='', hashtags=[], cta='', canva_design_brief={'title': f'{name} Campaign' if name else 'Mynat Campaign'}, meta_post_payload={'status': 'draft'}, selected_product=product, top_products=[], product_analysis={}, market_analysis={}, customer_personas={}, campaign_strategy={}, channel_strategy={}, confidence_score=30, risk_score=85, campaign_confidence_score=30, campaign_risk_score=85, critique_report={'what_is_weak': [reason]}, self_improvement_report=build_self_improvement_report())


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    return call_claude(prompt, max_tokens=max_tokens)


def _parse_json(text: str) -> dict:
    return parse_json_object(text)


def run_creator_agent(products: list[dict], social_review_report: dict | None = None, month: int | None = None, performance_report: dict | None = None, content_output: dict[str, Any] | None = None, content_input: dict[str, Any] | None = None, business_context: dict[str, Any] | None = None, campaign_goals: dict[str, Any] | None = None, asset_type: str = 'social_post', create_canva_design: bool = False, workflow_id: str = 'untracked', campaign_id: str | None = None, persist_execution: bool = True) -> dict[str, Any]:
    """Run the Creator Agent to produce a campaign intelligence strategy."""
    if not products:
        return validate_or_fallback(CreatorAgentOutput, {'success': False, 'error': 'No products provided'}, lambda reason: _creator_fallback(reason, products))
    if month is None:
        month = datetime.now().month
    month_name = MONTH_NAMES.get(month, 'Unknown')
    season = MONTH_TO_SEASON.get(month, 'festive')
    _logger.info(f'[CREATOR AGENT] Starting — Month: {month_name}, Season: {season}')
    season_data = detect_seasonal_opportunity(month, products)
    review_insights = analyze_social_reviews(social_review_report or {})
    best_product_data = choose_best_product(products, season_data, review_insights, performance_report)
    best_product = best_product_data.get('product', products[0])
    urgency_note = best_product_data.get('urgency_note', '')
    ranked_products = rank_campaign_products(products, season_data, review_insights, performance_report)
    selected_analysis = ranked_products[0] if ranked_products else {}
    recommended_product = selected_analysis.get('product') or best_product
    recommended_name = recommended_product.get('name', best_product.get('name', ''))
    rag_query = ' '.join((str(value) for value in (recommended_product.get('name', ''), recommended_product.get('category', ''), recommended_product.get('description', ''), 'Mynat Ayurvedic skincare brand context') if value))
    rag_context = require_rag_context(rag_query)
    commercial = selected_analysis.get('commercial', {})
    ingredients = selected_analysis.get('ingredients', {})
    benefits = selected_analysis.get('benefits', {})
    pricing = selected_analysis.get('pricing', {})
    inventory = selected_analysis.get('inventory', {})
    market = selected_analysis.get('market', {})
    personas = selected_analysis.get('personas', {})
    campaign_strategy = selected_analysis.get('campaign', {})
    channel_strategy = selected_analysis.get('channels', {})
    confidence_score = calculate_confidence_score(commercial, ingredients, market, personas, rag_context['available'])
    risk_score = calculate_risk_score(pricing, inventory, market, confidence_score)
    critique_report = build_critique_report(campaign_strategy, {'audience': personas.get('audience_confidence_score', 50), 'market': market.get('market_opportunity_score', 50), 'ingredients': ingredients.get('ingredient_strength_score', 50), 'pricing': pricing.get('pricing_opportunity_score', 50)})
    platform = channel_strategy.get('primary_channel', 'instagram')
    if platform not in {'instagram', 'facebook', 'linkedin', 'whatsapp', 'email', 'blog'}:
        platform = 'instagram'
    content_type = 'carousel' if campaign_strategy.get('campaign_angle') == 'Educational' else 'reel' if platform == 'instagram' and confidence_score >= 75 else 'post'
    seasonal_angle = campaign_strategy.get('campaign_angle', season_data.get('theme', ''))
    target_audience = personas.get('primary_audience', {}).get('lifestyle', 'Mynat skincare customers')
    reason = campaign_strategy.get('why_should_it_be_marketed', 'Best available campaign opportunity.')
    tool_brief = create_canva_design_brief(recommended_product, campaign_strategy.get('campaign_narrative', seasonal_angle), platform, content_type)
    tool_payload = prepare_meta_post_payload('', platform, recommended_product.get('image_url', ''), content_type)
    tool_payload['caption'] = ''
    tool_payload['status'] = 'draft'
    creative_package: dict[str, Any] = {}
    try:
        content_model = ContentAgentInput.model_validate(content_input) if content_input else None
        package_request = CreatorAssetRequest(product_data=recommended_product, content_input=content_model, content_output=content_output, creator_strategy={'recommended_product': recommended_name, 'seasonal_angle': seasonal_angle, 'target_audience': target_audience, 'platform': platform, 'content_type': content_type, 'campaign_strategy': campaign_strategy, 'channel_strategy': channel_strategy}, business_context=business_context or {}, campaign_goals=campaign_goals or {}, rag_context=rag_context, platform=platform if platform in {'instagram', 'facebook', 'meta', 'whatsapp', 'email', 'blog'} else 'instagram', asset_type=asset_type if asset_type in {'social_post', 'story', 'reel_cover', 'carousel', 'banner', 'ad_creative'} else 'social_post', workflow_id=workflow_id, approval_required=True, create_canva_design=create_canva_design, persist=persist_execution)
        creative_package = CreatorAssetService().generate_package(package_request).model_dump(mode='json')
    except Exception as exc:
        _logger.warning('[CREATOR AGENT] Creative package generation failed: %s', exc)
        creative_package = {'success': False, 'error': str(exc), 'status': 'draft', 'approval': {'required': True, 'status': 'pending'}}
    campaign_id = campaign_id or f'creator-{uuid4()}'
    top_products = [{'name': item.get('product', {}).get('name', ''), 'score': item.get('product_score', 0), 'reason': item.get('campaign', {}).get('campaign_objective_reason', '')} for item in ranked_products[:5]]
    output = {'success': True, 'workflow_id': workflow_id, 'campaign_id': campaign_id, 'status': 'draft', 'selected_product': recommended_product, 'top_products': top_products, 'product_analysis': {'commercial_viability': commercial, 'ingredient_intelligence': ingredients, 'benefit_intelligence': benefits, 'pricing_intelligence': pricing, 'inventory_intelligence': inventory}, 'market_analysis': market, 'customer_personas': personas, 'campaign_strategy': campaign_strategy, 'channel_strategy': channel_strategy, 'creative_package': creative_package, 'canva_design_prompt': (creative_package.get('canva') or {}).get('design_prompt', ''), 'canva_layout': (creative_package.get('canva') or {}).get('layout', {}), 'canva_elements': (creative_package.get('canva') or {}).get('elements', []), 'visual_strategy': creative_package.get('visual_strategy', {}), 'meta_payload': (creative_package.get('meta') or {}).get('meta_payload', {}), 'instagram_payload': (creative_package.get('meta') or {}).get('instagram_payload', {}), 'facebook_payload': (creative_package.get('meta') or {}).get('facebook_payload', {}), 'publishing_assets': creative_package.get('publishing_assets', {}), 'confidence_score': confidence_score, 'risk_score': risk_score, 'critique_report': critique_report, 'self_improvement_report': build_self_improvement_report(), 'recommended_product': recommended_name, 'reason': reason, 'seasonal_angle': seasonal_angle, 'target_audience': target_audience, 'platform': platform, 'content_type': content_type, 'instagram_caption': '', 'facebook_caption': '', 'hashtags': [], 'cta': '', 'canva_design_brief': {'title': tool_brief.get('title', f'{recommended_name} Campaign'), 'layout': tool_brief.get('layout', 'product_center'), 'text_overlay': tool_brief.get('text_overlay', seasonal_angle[:40]), 'colors': tool_brief.get('colors', ['#C8872A', '#FFF5E1']), 'image_suggestions': tool_brief.get('image_suggestions', []), 'execution_owner': 'canva_agent'}, 'meta_post_payload': {'platform': platform, 'caption': '', 'media_type': tool_payload.get('media_type', 'IMAGE'), 'status': 'draft', 'execution_owner': 'content_agent_and_publishing_guard'}, 'campaign_confidence_score': confidence_score, 'campaign_risk_score': risk_score, 'why_product_selected': reason, 'why_campaign_selected': campaign_strategy.get('campaign_narrative', seasonal_angle), 'why_audience_selected': target_audience, 'budget_suggestions': {'mode': 'strategy_estimate', 'recommended_daily_budget_inr': 900 if confidence_score >= 80 and risk_score <= 35 else 500, 'rationale': 'Budget is proportional to confidence, risk, channel priority, and inventory readiness.'}, 'launch_plan': [{'step': 'verify', 'owner': 'verifier_agent', 'status': 'required'}, {'step': 'human_approval', 'owner': 'owner_or_faculty', 'status': 'required'}, {'step': 'publish', 'owner': 'publishing_agent', 'status': 'blocked_until_approved'}], '_meta': {'month': month, 'month_name': month_name, 'season': season, 'product_score': selected_analysis.get('product_score', best_product_data.get('total_score', 0)), 'score_breakdown': {'legacy': best_product_data.get('score_breakdown', {}), 'commercial_viability': commercial.get('commercial_viability_score', 0), 'ingredient_strength': ingredients.get('ingredient_strength_score', 0), 'pricing_opportunity': pricing.get('pricing_opportunity_score', 0), 'inventory_readiness': inventory.get('inventory_campaign_readiness_score', 0), 'market_opportunity': market.get('market_opportunity_score', 0), 'channel_priority': channel_strategy.get('channel_priority_score', 0)}, 'urgency_note': urgency_note, 'review_sentiment': review_insights.get('overall_sentiment', 'unknown'), 'confidence': rag_context['confidence'], 'context_used': rag_context['context_used'], 'sources': rag_context['sources'], 'rag_required': True, 'rag_available': rag_context['available'], 'rag_error': rag_context['error'], 'skip_persistence': not persist_execution}}
    _logger.info(f'[CREATOR AGENT] Complete — Product: {recommended_name}, Platform: {platform}, Content: {content_type}')
    validated = validate_or_fallback(CreatorAgentOutput, output, lambda reason: _creator_fallback(reason, products), retry_factory=lambda failed: {**failed, 'success': bool(failed.get('recommended_product'))})
    if persist_execution:
        try:
            from backend.database.workflow_approval_store import audit_log
            audit_log(action='creator.strategy_generated', workflow_id=workflow_id, resource_type='campaign_strategy', resource_id=campaign_id, new_value={'recommended_product': recommended_name, 'confidence_score': confidence_score, 'risk_score': risk_score, 'primary_channel': platform}, severity='INFO' if validated.get('success') else 'WARNING', message='Creator Agent campaign strategy generated')
        except Exception as exc:
            _logger.warning('[CREATOR AGENT] Persistence skipped: %s', exc)
    return validated


# ── creator_agent/creator_workflow.py ─────────────────────────────────────────

from backend.database.creator_asset_store import save_creative_package, save_creator_dead_letter as _save_dead_letter


def run_creator_workflow(*, event_type: str, product_data: dict[str, Any], content_output: dict[str, Any] | None = None, creator_strategy: dict[str, Any] | None = None, campaign_goals: dict[str, Any] | None = None, business_context: dict[str, Any] | None = None, workflow_id: str = 'untracked', platform: str = 'instagram', asset_type: str = 'social_post', persist: bool = True) -> dict[str, Any]:
    """Run the Creator package workflow for a normalized event."""
    request_payload = {'event_type': event_type, 'product_data': product_data, 'content_output': content_output or {}, 'creator_strategy': creator_strategy or {}, 'campaign_goals': campaign_goals or {}, 'business_context': business_context or {}, 'workflow_id': workflow_id, 'platform': platform, 'asset_type': asset_type, 'persist': persist}
    try:
        request = CreatorAssetRequest(product_data=product_data, content_output=content_output, creator_strategy=creator_strategy, campaign_goals=campaign_goals or {}, business_context=business_context or {}, workflow_id=workflow_id, platform=platform, asset_type=asset_type, persist=persist)
        package = CreatorAssetService().generate_package(request).model_dump(mode='json')
        if persist:
            package['persistence'] = save_creative_package(package, request_payload)
        return {'success': True, 'event_type': event_type, 'creative_package': package}
    except Exception as exc:
        dead = _save_dead_letter(workflow_id=workflow_id, failure_type=event_type, payload=request_payload, error=str(exc))
        return {'success': False, 'event_type': event_type, 'error': str(exc), 'dead_letter': dead}


def on_product_created(product_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return run_creator_workflow(event_type='product.created', product_data=product_data, **kwargs)


def on_product_updated(product_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return run_creator_workflow(event_type='product.updated', product_data=product_data, **kwargs)


def on_inventory_changed(product_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return run_creator_workflow(event_type='inventory.changed', product_data=product_data, **kwargs)


def on_campaign_created(product_data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
    return run_creator_workflow(event_type='campaign.created', product_data=product_data, **kwargs)
