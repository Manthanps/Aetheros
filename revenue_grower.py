"""
Revenue Growth Agent — primary decision-making agent for Mynat marketing strategy.

Merged from: revenue_growth_agent.py + content_strategy_engine.py +
             customer_insight_engine.py + product_opportunity_engine.py +
             revenue_recommendation_engine.py + seo_growth_engine.py

All outputs are status=draft and require human approval before action.
"""
from __future__ import annotations

# ── ContentStrategyEngine ──
import datetime
import json
import re
from collections import Counter
from typing import Any

from agents.product_knowledge import require_rag_context
from agents.claude_client import call_claude, is_queue_sentinel, parse_json_object
from agents.output_validator import safe_agent_fallback, validate_or_fallback
from agents.agent_schemas import AgentOutputBase

# ─── content_strategy_engine ─────────────────────────────────────────────────

_FUNNEL_ROTATION = ["awareness", "consideration", "conversion", "retention"]

_PLATFORM_FORMATS: dict[str, list[str]] = {
    "instagram": ["carousel post", "reel", "story", "static post"],
    "facebook": ["photo post", "video post", "story", "link post"],
    "whatsapp": ["broadcast message", "status update", "story"],
    "blog": ["how-to article", "ingredient spotlight", "customer story", "SEO listicle"],
    "email": ["product spotlight", "educational email", "offer email", "story email"],
}

_OBJECTIVES: dict[str, str] = {
    "awareness": "Reach new audiences and introduce the product",
    "consideration": "Educate and build trust with warm audiences",
    "conversion": "Drive immediate purchase with urgency and proof",
    "retention": "Reward existing customers, encourage repeat purchase",
}


def _rotate(lst: list, idx: int) -> Any:
    return lst[idx % len(lst)]


def _day_content(
    day: int,
    product: dict[str, Any],
    platform: str,
    rag_snippets: list[str],
) -> dict[str, Any]:
    funnel_stage = _rotate(_FUNNEL_ROTATION, day)
    fmt = _rotate(_PLATFORM_FORMATS.get(platform, ["post"]), day)
    rag_hint = rag_snippets[day % len(rag_snippets)] if rag_snippets else ""
    name = product.get("name", "product")
    benefit = product.get("description", "natural skincare")[:80]

    hooks = {
        "awareness": f"Did you know? {benefit[:60]}…",
        "consideration": f"Why {name} is your skin's new best friend 🌿",
        "conversion": f"Last chance: Transform your skin with {name} today",
        "retention": f"Already loving {name}? Here's your next step ✨",
    }

    ctas = {
        "awareness": "Save this post for later",
        "consideration": "Drop a ❤️ if your skin needs this",
        "conversion": "Shop now — link in bio",
        "retention": "Tag a friend who needs this",
    }

    return {
        "day": day,
        "date_offset": f"Day {day}",
        "platform": platform,
        "format": fmt,
        "funnel_stage": funnel_stage,
        "objective": _OBJECTIVES[funnel_stage],
        "product": name,
        "hook": hooks[funnel_stage],
        "body_direction": f"Highlight: {rag_hint or benefit}",
        "cta": ctas[funnel_stage],
        "target_audience": product.get("target_audience", "women 22-45 interested in Ayurvedic skincare"),
        "hashtag_theme": f"#{name.replace(' ', '')} #Mynat #AyurvedicSkincare",
    }


_REEL_TYPES = [
    ("educational", "How-to / ingredient deep-dive", "awareness"),
    ("product", "Product showcase / unboxing feel", "consideration"),
    ("testimonial", "Real customer result reveal", "conversion"),
    ("viral_hook", "Trending audio + relatable hook", "awareness"),
    ("conversion", "Before/after + limited offer", "conversion"),
]


def _build_reel(product: dict[str, Any], reel_type: tuple, rag_hint: str) -> dict[str, Any]:
    kind, description, funnel = reel_type
    name = product.get("name", "product")
    benefit = product.get("description", "natural Ayurvedic formula")[:100]

    scripts = {
        "educational": (
            f"[Hook] 'I was using the WRONG skincare until I found this…'\n"
            f"[Scene 1] Close-up of {name} bottle with ingredients\n"
            f"[Scene 2] Point to key ingredient — '{rag_hint or benefit}'\n"
            f"[Scene 3] Skin transformation montage\n"
            f"[CTA] 'Save this if you want clear skin! Link in bio 👆'"
        ),
        "product": (
            f"[Hook] 'This is the one product you need in your routine'\n"
            f"[Scene 1] Aesthetic flat-lay of {name}\n"
            f"[Scene 2] Texture/application ASMR\n"
            f"[Scene 3] Glowing skin result\n"
            f"[CTA] 'Shop now — link in bio'"
        ),
        "testimonial": (
            f"[Hook] 'She used {name} for 21 days… look at the result'\n"
            f"[Scene 1] Before skin (relatable problem)\n"
            f"[Scene 2] Routine clip with {name}\n"
            f"[Scene 3] After — glowing transformation\n"
            f"[CTA] 'Get yours before stock runs out — link in bio'"
        ),
        "viral_hook": (
            f"[Hook] 'POV: your skin after discovering Ayurvedic skincare'\n"
            f"[Scene 1] Trending audio overlay with product reveal\n"
            f"[Scene 2] Ingredient facts as text overlay\n"
            f"[Scene 3] Satisfied customer reaction clip\n"
            f"[CTA] 'Comment SKIN if you want the link 👇'"
        ),
        "conversion": (
            f"[Hook] 'Only 48 hours left to get {name} at this price'\n"
            f"[Scene 1] Before/after side-by-side\n"
            f"[Scene 2] Customer review read-aloud\n"
            f"[Scene 3] Discount code reveal\n"
            f"[CTA] 'Use code MYNAT10 — link in bio. Hurry!'"
        ),
    }

    return {
        "type": kind,
        "description": description,
        "funnel_stage": funnel,
        "product": name,
        "viral_hook": scripts[kind].split("\n")[0].replace("[Hook] ", ""),
        "script": scripts[kind],
        "scene_breakdown": [
            line.strip() for line in scripts[kind].split("\n") if line.strip()
        ],
        "cta": scripts[kind].split("\n")[-1].replace("[CTA] ", ""),
        "recommended_duration_seconds": 30 if kind in ("educational", "testimonial") else 15,
        "audio_style": "trending audio" if kind == "viral_hook" else "original/voiceover",
    }


_CONTENT_SYSTEM_PROMPT = (
    "You are a world-class Growth Marketing Strategist for Mynat, an Ayurvedic skincare brand. "
    "Generate specific, actionable, conversion-focused content strategies grounded in real product data. "
    "Always respond with valid JSON only."
)


def _llm_enhance_calendar(
    product: dict[str, Any],
    base_calendar: list[dict],
    rag_snippets: list[str],
) -> list[dict]:
    """Ask Claude to enrich the top 7 calendar entries with better copy."""
    prompt = (
        f"Product: {json.dumps(product, default=str)[:400]}\n"
        f"RAG context snippets: {rag_snippets[:3]}\n\n"
        f"Base calendar (first 7 days):\n{json.dumps(base_calendar[:7], default=str)}\n\n"
        "Rewrite each entry's 'hook' and 'body_direction' to be more specific, "
        "emotionally compelling, and conversion-focused. "
        "Return JSON array of 7 objects with fields: day, hook, body_direction, cta"
    )
    raw = call_claude(prompt, max_tokens=1200, system=_CONTENT_SYSTEM_PROMPT)
    if not raw or is_queue_sentinel(raw):
        return base_calendar
    try:
        match_start = raw.find("[")
        match_end = raw.rfind("]") + 1
        if match_start >= 0 and match_end > match_start:
            enriched = json.loads(raw[match_start:match_end])
            for item in enriched:
                day = item.get("day")
                orig = next((e for e in base_calendar if e["day"] == day), None)
                if orig and item.get("hook"):
                    orig["hook"] = item["hook"]
                    orig["body_direction"] = item.get("body_direction", orig["body_direction"])
                    orig["cta"] = item.get("cta", orig["cta"])
    except Exception:
        pass
    return base_calendar


def generate_content_strategy(
    products: list[dict[str, Any]],
    analytics: dict[str, Any] | None = None,
    campaign_history: list[dict[str, Any]] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Generate a 30-day multi-platform content strategy.

    Returns:
      - content_calendar: 30-day plan across all platforms
      - instagram_plan / facebook_plan / whatsapp_plan / blog_plan / email_plan
      - reel_strategy: 5 reel concepts with scripts
    """
    products = [p for p in (products or []) if isinstance(p, dict)]
    analytics = analytics or {}

    if not products:
        return {"success": False, "error": "No products provided", "content_calendar": []}

    # RAG grounding
    primary = products[0]
    rag_query = f"{primary.get('name', '')} content strategy benefits customer reviews {primary.get('category', '')}"
    rag_ctx = require_rag_context(rag_query, collection="mynat_products", n_results=8)
    rag_snippets: list[str] = []
    for item in rag_ctx.get("context_used", []):
        if isinstance(item, dict):
            snippet = item.get("document") or item.get("description") or str(item)[:120]
        else:
            snippet = str(item)[:120]
        if snippet:
            rag_snippets.append(snippet)
    if not rag_snippets:
        rag_snippets = [primary.get("description", "natural Ayurvedic formula")[:120]]

    # 30-day calendar — rotate products
    calendar: list[dict] = []
    platforms = ["instagram", "facebook", "whatsapp", "blog", "email"]
    for day in range(1, 31):
        product = products[(day - 1) % len(products)]
        platform = _rotate(platforms, day - 1)
        calendar.append(_day_content(day, product, platform, rag_snippets))

    # LLM enhancement of first 7 days
    if use_llm:
        calendar = _llm_enhance_calendar(primary, calendar, rag_snippets)

    # Per-platform splits
    def _filter(platform: str) -> list[dict]:
        return [e for e in calendar if e["platform"] == platform]

    # Reel strategy (5 concepts)
    reels = []
    for i, reel_type in enumerate(_REEL_TYPES):
        product = products[i % len(products)]
        hint = rag_snippets[i % len(rag_snippets)] if rag_snippets else ""
        reels.append(_build_reel(product, reel_type, hint))

    return {
        "success": True,
        "primary_product": primary.get("name"),
        "content_calendar": calendar,
        "instagram_plan": _filter("instagram"),
        "facebook_plan": _filter("facebook"),
        "whatsapp_plan": _filter("whatsapp"),
        "blog_plan": _filter("blog"),
        "email_plan": _filter("email"),
        "reel_strategy": reels,
        "total_pieces": len(calendar),
        "_meta": {
            "rag_available": rag_ctx["available"],
            "rag_confidence": rag_ctx["confidence"],
            "rag_sources": rag_ctx["sources"],
            "llm_enhanced": use_llm,
        },
    }


# ── CustomerInsightEngine ──

_CUSTOMER_SYSTEM = (
    "You are an expert Consumer Psychology Analyst for Mynat, an Ayurvedic skincare brand. "
    "Extract deep customer insights from reviews and product data. "
    "Return valid JSON only."
)

_PAIN_KEYWORDS: list[tuple[str, str]] = [
    ("dry skin", "Dry and dehydrated skin"),
    ("oily skin", "Excess oil / shine"),
    ("acne", "Acne and breakouts"),
    ("dark spot", "Hyperpigmentation / dark spots"),
    ("dark circle", "Dark circles and puffiness"),
    ("aging", "Premature aging / fine lines"),
    ("dull", "Dull / lack-lustre skin"),
    ("sensitive", "Sensitive / reactive skin"),
    ("tan", "Sun tan removal"),
    ("uneven", "Uneven skin tone"),
    ("chemical", "Fear of chemicals / parabens"),
    ("harsh", "Harsh ingredient concerns"),
]

_TRIGGER_KEYWORDS: list[tuple[str, str]] = [
    ("results", "Visible results / transformation"),
    ("natural", "Natural / chemical-free ingredients"),
    ("ayurved", "Ayurvedic / traditional heritage"),
    ("recommend", "Word-of-mouth recommendation"),
    ("price", "Value for money"),
    ("fast", "Fast-acting formula"),
    ("glow", "Instant glow / radiance"),
    ("routine", "Part of daily routine"),
    ("safe", "Safety and gentleness"),
    ("gift", "Gifting occasion"),
]

_OBJECTION_KEYWORDS: list[tuple[str, str]] = [
    ("expensive", "Price is too high"),
    ("small", "Product quantity feels small"),
    ("slow", "Results take too long"),
    ("smell", "Fragrance concerns"),
    ("greasy", "Greasy / heavy texture"),
    ("allerg", "Allergy / reaction concerns"),
    ("return", "Return / exchange policy concerns"),
    ("delivery", "Delivery time concerns"),
    ("fake", "Authenticity / counterfeit concerns"),
    ("work", "Doesn't work for my skin type"),
]


def _extract_deterministic(reviews: list[dict[str, Any]]) -> dict[str, Any]:
    all_text = " ".join(
        str(r.get("text") or r.get("comment") or r.get("body") or "").lower()
        for r in reviews
    )

    pain_counter: Counter = Counter()
    for kw, label in _PAIN_KEYWORDS:
        if kw in all_text:
            count = all_text.count(kw)
            pain_counter[label] += count

    trigger_counter: Counter = Counter()
    for kw, label in _TRIGGER_KEYWORDS:
        if kw in all_text:
            trigger_counter[label] += all_text.count(kw)

    objection_counter: Counter = Counter()
    for kw, label in _OBJECTION_KEYWORDS:
        if kw in all_text:
            objection_counter[label] += all_text.count(kw)

    ratings = [float(r.get("rating", 4)) for r in reviews if r.get("rating")]
    avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 4.0
    sentiment = "positive" if avg_rating >= 4 else "neutral" if avg_rating >= 3 else "negative"

    return {
        "pain_points": [{"pain": k, "frequency": v} for k, v in pain_counter.most_common(6)],
        "buying_triggers": [{"trigger": k, "frequency": v} for k, v in trigger_counter.most_common(6)],
        "objections": [{"objection": k, "frequency": v} for k, v in objection_counter.most_common(5)],
        "avg_rating": avg_rating,
        "sentiment": sentiment,
        "total_reviews_analyzed": len(reviews),
    }


def _llm_insights(
    products: list[dict[str, Any]],
    reviews: list[dict[str, Any]],
    deterministic: dict[str, Any],
    rag_snippets: list[str],
) -> dict[str, Any]:
    review_sample = [
        {"text": str(r.get("text") or r.get("comment") or "")[:200], "rating": r.get("rating")}
        for r in reviews[:10]
    ]
    prompt = (
        f"Products: {json.dumps([p.get('name') for p in products[:5]])}\n\n"
        f"Review sample: {json.dumps(review_sample, default=str)}\n\n"
        f"RAG context: {chr(10).join(rag_snippets[:3])}\n\n"
        f"Initial analysis: {json.dumps(deterministic, default=str)[:400]}\n\n"
        "Provide deep customer psychology analysis. Return JSON with:\n"
        "{\n"
        '  "pain_points": [{"pain": "...", "emotional_driver": "...", "messaging_hook": "..."}],\n'
        '  "buying_triggers": [{"trigger": "...", "psychological_driver": "...", "how_to_leverage": "..."}],\n'
        '  "objections": [{"objection": "...", "counter_message": "...", "proof_type": "..."}],\n'
        '  "emotional_motivations": [{"motivation": "...", "persona": "...", "content_angle": "..."}],\n'
        '  "customer_personas": [{"name": "...", "age": "...", "concern": "...", "buying_trigger": "...", "best_channel": "..."}],\n'
        '  "messaging_framework": {"primary_message": "...", "supporting_messages": ["..."], "tone": "..."}\n'
        "}\n"
        "Be specific, actionable, and grounded in the actual review data provided."
    )
    raw = call_claude(prompt, max_tokens=1800, system=_CUSTOMER_SYSTEM)
    if not raw or is_queue_sentinel(raw):
        return {}
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _fallback_insights(products: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "pain_points": [
            {"pain": "Dry and dehydrated skin", "emotional_driver": "Low confidence", "messaging_hook": "Wake up to visibly hydrated skin"},
            {"pain": "Hyperpigmentation / dark spots", "emotional_driver": "Desire for even skin tone", "messaging_hook": "Fade spots naturally with Ayurvedic actives"},
            {"pain": "Fear of chemicals / parabens", "emotional_driver": "Safety and trust", "messaging_hook": "100% natural — every ingredient has a purpose"},
        ],
        "buying_triggers": [
            {"trigger": "Visible results", "psychological_driver": "Need for efficacy proof", "how_to_leverage": "Before/after content and testimonials"},
            {"trigger": "Natural/Ayurvedic", "psychological_driver": "Heritage trust", "how_to_leverage": "Highlight ancient ingredient stories"},
            {"trigger": "Value for money", "psychological_driver": "Price-quality perception", "how_to_leverage": "Cost-per-day breakdowns"},
        ],
        "objections": [
            {"objection": "Price is too high", "counter_message": "Less than ₹25/day for visible transformation", "proof_type": "ROI calculation"},
            {"objection": "Results take too long", "counter_message": "See a difference in 7 days or money back", "proof_type": "Guarantee"},
            {"objection": "Doesn't work for my skin type", "counter_message": "Tested on all Indian skin tones", "proof_type": "Dermatologist statement"},
        ],
        "emotional_motivations": [
            {"motivation": "Confidence through clear skin", "persona": "Career woman 25-35", "content_angle": "Glow up your morning confidence"},
            {"motivation": "Natural wellness lifestyle", "persona": "Health-conscious millennial", "content_angle": "Skincare that aligns with your values"},
            {"motivation": "Affordable luxury", "persona": "Value-seeking shopper", "content_angle": "Premium Ayurvedic care at honest prices"},
        ],
        "customer_personas": [
            {"name": "Priya", "age": "26-32", "concern": "Pigmentation after pregnancy", "buying_trigger": "Natural + clinically tested", "best_channel": "Instagram + WhatsApp"},
            {"name": "Sneha", "age": "22-28", "concern": "Acne + oily skin", "buying_trigger": "Social proof / influencer", "best_channel": "Instagram Reels"},
            {"name": "Anita", "age": "35-45", "concern": "Anti-aging / fine lines", "buying_trigger": "Ayurvedic heritage + reviews", "best_channel": "Facebook + Email"},
        ],
        "messaging_framework": {
            "primary_message": "Ayurvedic wisdom. Modern skin results.",
            "supporting_messages": [
                "100% natural, 0% compromise",
                "Skincare rooted in 5000 years of Ayurveda",
                "Made for Indian skin, by Indians",
            ],
            "tone": "Warm, empowering, science-backed, heritage-inspired",
        },
    }


def generate_customer_insights(
    products: list[dict[str, Any]],
    reviews: list[dict[str, Any]] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Deep customer psychology analysis from reviews and RAG context.

    Returns pain_points, buying_triggers, objections, emotional_motivations,
    customer_personas, and messaging_framework.
    """
    products = [p for p in (products or []) if isinstance(p, dict)]
    reviews = [r for r in (reviews or []) if isinstance(r, dict)]

    # RAG
    rag_query = " ".join(
        [str(p.get("name", "")) for p in products[:4]]
        + ["customer reviews pain points buying triggers objections"]
    )
    rag_ctx = require_rag_context(rag_query, collection="mynat_products", n_results=6)
    rag_snippets = [
        (item.get("document") or item.get("description") or str(item))[:150]
        for item in rag_ctx.get("context_used", [])
        if isinstance(item, dict)
    ]

    deterministic = _extract_deterministic(reviews) if reviews else {}

    if use_llm and (reviews or rag_snippets):
        llm_result = _llm_insights(products, reviews, deterministic, rag_snippets)
    else:
        llm_result = {}

    # Merge: LLM enriches deterministic base; fallback fills missing keys
    fallback = _fallback_insights(products)
    base = {**fallback, **{k: v for k, v in llm_result.items() if v}}

    # Preserve deterministic ratings
    base["avg_rating"] = deterministic.get("avg_rating", 4.0)
    base["sentiment"] = deterministic.get("sentiment", "positive")
    base["total_reviews_analyzed"] = deterministic.get("total_reviews_analyzed", 0)

    return {
        "success": True,
        "products_analyzed": len(products),
        **base,
        "_meta": {
            "rag_available": rag_ctx["available"],
            "rag_confidence": rag_ctx["confidence"],
            "rag_sources": rag_ctx["sources"],
            "reviews_analyzed": len(reviews),
            "llm_enhanced": use_llm and bool(llm_result),
        },
    }


# ── ProductOpportunityEngine ──

_SEASON_MAP: dict[int, str] = {
    12: "winter", 1: "winter", 2: "winter",
    3: "spring", 4: "spring", 5: "spring",
    6: "summer", 7: "summer", 8: "summer",
    9: "autumn", 10: "autumn", 11: "autumn",
}

_SEASON_KEYWORDS: dict[str, list[str]] = {
    "summer": ["sunscreen", "cooling", "spf", "tan", "hydration", "matte", "oil control"],
    "winter": ["moisturiser", "nourishing", "dry skin", "lip balm", "repair", "rich cream"],
    "spring": ["brightening", "glow", "renewal", "vitamin c", "detox", "refresh"],
    "autumn": ["repair", "antioxidant", "protection", "serum", "pigmentation"],
}


def _current_season() -> str:
    return _SEASON_MAP.get(datetime.datetime.now().month, "summer")


def _season_score(product: dict[str, Any], season: str) -> float:
    keywords = _SEASON_KEYWORDS.get(season, [])
    text = " ".join([
        str(product.get("name", "")),
        str(product.get("description", "")),
        str(product.get("category", "")),
    ]).lower()
    hits = sum(1 for kw in keywords if kw in text)
    return round(hits * 15.0, 2)


def _num(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _revenue_score(product: dict[str, Any], analytics: dict[str, Any]) -> float:
    best_list: list[dict] = analytics.get("best_products") or []
    names = [p.get("name") for p in best_list]
    if product.get("name") in names:
        rank_bonus = max(0, (3 - names.index(product.get("name"))) * 10)
    else:
        rank_bonus = 0.0
    return _num(product.get("revenue")) * 0.3 + rank_bonus


def _margin_score(product: dict[str, Any]) -> float:
    return _num(product.get("margin_percent"), 35) * 1.5


def _review_score(product: dict[str, Any], reviews: list[dict[str, Any]]) -> float:
    product_reviews = [
        r for r in reviews
        if str(r.get("product_id") or r.get("product_name", "")).lower()
        in str(product.get("id", "") or product.get("name", "")).lower()
    ]
    if not product_reviews:
        return 0.0
    avg_rating = sum(_num(r.get("rating", 4)) for r in product_reviews) / len(product_reviews)
    return (avg_rating / 5) * 20


def _stock_penalty(product: dict[str, Any]) -> float:
    stock = _num(product.get("stock"))
    if stock <= 0:
        return -200.0
    if stock < 10:
        return -30.0
    return 0.0


def detect_product_opportunities(
    products: list[dict[str, Any]],
    analytics: dict[str, Any] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    campaign_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    Score every product and return ranked opportunity lists.

    Returns a dict with:
      - best_products_to_promote: top scored with priority labels
      - underperforming_products: lowest scored in-stock items
      - seasonal_products: strongest seasonal fit
      - high_margin_products: highest margin items
      - trending_products: recent revenue acceleration
      - rag_context: retrieval metadata
    """
    analytics = analytics or {}
    reviews = reviews or []
    campaign_history = campaign_history or []
    products = [p for p in (products or []) if isinstance(p, dict)]

    if not products:
        return {
            "success": False,
            "error": "No products provided",
            "best_products_to_promote": [],
            "underperforming_products": [],
            "seasonal_products": [],
            "high_margin_products": [],
            "trending_products": [],
        }

    # RAG — fetch context for all products
    rag_query = " ".join(
        [str(p.get("name", "")) for p in products[:6]] + ["Mynat product opportunity analysis"]
    )
    rag_ctx = require_rag_context(rag_query, collection="mynat_products", n_results=6)

    season = _current_season()

    scored: list[dict[str, Any]] = []
    for p in products:
        rev_s = _revenue_score(p, analytics)
        margin_s = _margin_score(p)
        season_s = _season_score(p, season)
        review_s = _review_score(p, reviews)
        penalty = _stock_penalty(p)

        total = rev_s + margin_s + season_s + review_s + penalty
        scored.append({
            **p,
            "_opportunity_score": round(total, 2),
            "_revenue_score": round(rev_s, 2),
            "_margin_score": round(margin_s, 2),
            "_season_score": round(season_s, 2),
            "_review_score": round(review_s, 2),
            "_stock_penalty": round(penalty, 2),
        })

    ranked = sorted(scored, key=lambda x: x["_opportunity_score"], reverse=True)

    # Trending: products with recent campaign revenue spike
    campaign_revenues: dict[str, float] = {}
    for c in campaign_history:
        name = str(c.get("product") or c.get("product_name") or "")
        campaign_revenues[name] = campaign_revenues.get(name, 0) + _num(c.get("revenue"))

    trending = sorted(
        [p for p in ranked if campaign_revenues.get(str(p.get("name")), 0) > 0],
        key=lambda x: campaign_revenues.get(str(x.get("name")), 0),
        reverse=True,
    )[:5]

    in_stock = [p for p in ranked if _num(p.get("stock")) > 0]

    def _label(score: float) -> str:
        if score >= 100:
            return "high"
        if score >= 50:
            return "medium"
        return "low"

    best = []
    for rank, p in enumerate(ranked[:8], 1):
        best.append({
            "rank": rank,
            "name": p.get("name"),
            "category": p.get("category"),
            "price": p.get("price"),
            "stock": p.get("stock"),
            "opportunity_score": p["_opportunity_score"],
            "promotion_priority": _label(p["_opportunity_score"]),
            "reasoning": (
                f"Revenue score {p['_revenue_score']:.0f} + "
                f"Margin score {p['_margin_score']:.0f} + "
                f"Seasonal fit {p['_season_score']:.0f} + "
                f"Review score {p['_review_score']:.0f}"
                + (f" (low stock penalty)" if p["_stock_penalty"] < 0 else "")
            ),
        })

    underperforming = [
        {
            "name": p.get("name"),
            "opportunity_score": p["_opportunity_score"],
            "promotion_priority": "low",
            "reasoning": "Low combined revenue + margin + seasonal signal",
            "recommended_action": "Refresh product page copy, add reviews, run targeted discount",
        }
        for p in in_stock[-4:][::-1]
        if p["_opportunity_score"] < 40
    ]

    seasonal = sorted(
        [p for p in ranked if p["_season_score"] > 0],
        key=lambda x: x["_season_score"],
        reverse=True,
    )[:5]
    seasonal_out = [
        {
            "name": p.get("name"),
            "season": season,
            "season_score": p["_season_score"],
            "opportunity_score": p["_opportunity_score"],
            "promotion_priority": _label(p["_opportunity_score"]),
            "reasoning": f"Strong {season} keyword match",
        }
        for p in seasonal
    ]

    high_margin = sorted(
        [p for p in in_stock if _num(p.get("margin_percent"), 35) >= 40],
        key=lambda x: _num(x.get("margin_percent"), 35),
        reverse=True,
    )[:5]
    high_margin_out = [
        {
            "name": p.get("name"),
            "margin_percent": p.get("margin_percent"),
            "opportunity_score": p["_opportunity_score"],
            "promotion_priority": _label(p["_opportunity_score"]),
            "reasoning": f"Margin {p.get('margin_percent', 35):.0f}% above 40% threshold",
        }
        for p in high_margin
    ]

    trending_out = [
        {
            "name": p.get("name"),
            "campaign_revenue": campaign_revenues.get(str(p.get("name")), 0),
            "opportunity_score": p["_opportunity_score"],
            "promotion_priority": _label(p["_opportunity_score"]),
            "reasoning": "Positive revenue acceleration in recent campaigns",
        }
        for p in trending
    ]

    return {
        "success": True,
        "season": season,
        "products_analyzed": len(products),
        "best_products_to_promote": best,
        "underperforming_products": underperforming,
        "seasonal_products": seasonal_out,
        "high_margin_products": high_margin_out,
        "trending_products": trending_out,
        "_meta": {
            "rag_available": rag_ctx["available"],
            "rag_confidence": rag_ctx["confidence"],
            "rag_sources": rag_ctx["sources"],
        },
    }


# ── RevenueRecommendationEngine ──

_REVENUE_SYSTEM = (
    "You are an expert E-commerce Revenue Strategist for Mynat, an Ayurvedic skincare brand. "
    "Generate specific, actionable revenue recommendations grounded in product data. "
    "All output is for human review — status is always 'draft'. "
    "Return valid JSON only."
)

_CATEGORY_AFFINITY: dict[str, list[str]] = {
    "face care": ["face care", "serums", "moisturiser", "toner", "eye care"],
    "hair care": ["hair care", "scalp care", "oil", "shampoo", "conditioner"],
    "body care": ["body care", "scrub", "lotion", "oil", "bath"],
    "lip care": ["lip care", "face care"],
    "eye care": ["face care", "eye care", "serums"],
}


def _related_categories(category: str) -> list[str]:
    cat = (category or "").lower()
    for key, related in _CATEGORY_AFFINITY.items():
        if key in cat:
            return related
    return [cat, "face care"]


def _build_bundles(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    in_stock = [p for p in products if _num(p.get("stock")) > 0]
    bundles: list[dict[str, Any]] = []

    # routine bundle: face care trio
    routine_products = [
        p for p in in_stock
        if any(kw in str(p.get("category", "")).lower() for kw in ["face", "serum", "toner", "moisturiser"])
    ][:3]
    if len(routine_products) >= 2:
        prices = [_num(p.get("price", 0)) for p in routine_products]
        total = sum(prices)
        discount_price = round(total * 0.85, 2)
        bundles.append({
            "bundle_name": "Mynat Daily Glow Routine",
            "products": [p.get("name") for p in routine_products],
            "original_price": total,
            "bundle_price": discount_price,
            "discount_percent": 15,
            "savings": round(total - discount_price, 2),
            "usp": "Complete Ayurvedic routine at 15% off",
            "target_audience": "Customers starting a skincare routine",
            "expected_aov_lift_percent": 35,
            "status": "draft",
        })

    # starter bundle: 2 entry-price products
    starter = sorted(in_stock, key=lambda p: _num(p.get("price", 9999)))[:2]
    if len(starter) >= 2:
        total = sum(_num(p.get("price", 0)) for p in starter)
        bundles.append({
            "bundle_name": "Mynat Starter Kit",
            "products": [p.get("name") for p in starter],
            "original_price": total,
            "bundle_price": round(total * 0.90, 2),
            "discount_percent": 10,
            "savings": round(total * 0.10, 2),
            "usp": "Perfect introduction to Ayurvedic skincare",
            "target_audience": "New customers, gifting",
            "expected_aov_lift_percent": 25,
            "status": "draft",
        })

    # premium bundle: top 2 high-margin products
    premium = sorted(
        [p for p in in_stock if _num(p.get("margin_percent"), 35) >= 40],
        key=lambda p: _num(p.get("price", 0)),
        reverse=True,
    )[:2]
    if len(premium) >= 2:
        total = sum(_num(p.get("price", 0)) for p in premium)
        bundles.append({
            "bundle_name": "Mynat Premium Collection",
            "products": [p.get("name") for p in premium],
            "original_price": total,
            "bundle_price": round(total * 0.88, 2),
            "discount_percent": 12,
            "savings": round(total * 0.12, 2),
            "usp": "Premium Ayurvedic indulgence at special price",
            "target_audience": "High-value customers, gifting",
            "expected_aov_lift_percent": 40,
            "status": "draft",
        })

    return bundles


def _build_upsells(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    in_stock = sorted(
        [p for p in products if _num(p.get("stock")) > 0],
        key=lambda p: _num(p.get("price", 0)),
    )
    upsells: list[dict[str, Any]] = []
    for i, product in enumerate(in_stock[:-1]):
        next_tier = next(
            (p for p in in_stock[i + 1:]
             if _num(p.get("price", 0)) > _num(product.get("price", 0)) * 1.2
             and _related_categories(product.get("category", ""))[0]
             in str(p.get("category", "")).lower()),
            None,
        )
        if next_tier:
            price_diff = _num(next_tier.get("price", 0)) - _num(product.get("price", 0))
            upsells.append({
                "from_product": product.get("name"),
                "upsell_to": next_tier.get("name"),
                "price_difference": round(price_diff, 2),
                "upsell_message": (
                    f"Upgrade to {next_tier.get('name')} for just ₹{price_diff:.0f} more "
                    f"and get {next_tier.get('description', 'enhanced results')[:80]}"
                ),
                "expected_revenue_lift_percent": 20,
                "trigger": "Add to cart / product page",
                "status": "draft",
            })
    return upsells[:5]


def _build_cross_sells(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    in_stock = [p for p in products if _num(p.get("stock")) > 0]
    cross_sells: list[dict[str, Any]] = []
    used_pairs: set[tuple] = set()

    for product in in_stock:
        cat = product.get("category", "")
        related_cats = _related_categories(cat)
        complements = [
            p for p in in_stock
            if p.get("name") != product.get("name")
            and any(rc in str(p.get("category", "")).lower() for rc in related_cats)
        ][:2]

        for comp in complements:
            pair = tuple(sorted([str(product.get("name")), str(comp.get("name"))]))
            if pair in used_pairs:
                continue
            used_pairs.add(pair)
            cross_sells.append({
                "primary_product": product.get("name"),
                "cross_sell_product": comp.get("name"),
                "reason": f"Customers who buy {product.get('name')} also need {comp.get('name')}",
                "cross_sell_message": (
                    f"Complete your routine: Add {comp.get('name')} — "
                    f"{comp.get('description', 'natural Ayurvedic formula')[:60]}…"
                ),
                "placement": "Product page / cart",
                "expected_conversion_lift_percent": 12,
                "status": "draft",
            })

    return cross_sells[:6]


def _build_discounts(
    products: list[dict[str, Any]],
    analytics: dict[str, Any],
) -> list[dict[str, Any]]:
    in_stock = [p for p in products if _num(p.get("stock")) > 0]
    worst = analytics.get("worst_products") or []
    worst_names = {str(p.get("name")) for p in worst}

    discounts: list[dict[str, Any]] = []

    # Flash sale for slow-movers
    slow_movers = [p for p in in_stock if p.get("name") in worst_names][:3]
    for p in slow_movers:
        price = _num(p.get("price", 0))
        if price > 0:
            discounts.append({
                "product": p.get("name"),
                "discount_type": "flash_sale",
                "discount_percent": 20,
                "original_price": price,
                "sale_price": round(price * 0.80, 2),
                "duration": "48 hours",
                "reason": "Low performance — clear inventory and generate cash flow",
                "expected_volume_lift_percent": 40,
                "status": "draft",
            })

    # First-order discount
    discounts.append({
        "product": "all products",
        "discount_type": "first_order",
        "discount_percent": 10,
        "coupon_code": "MYNAT10",
        "reason": "Convert first-time visitors",
        "expected_conversion_lift_percent": 25,
        "status": "draft",
    })

    # Seasonal offer
    discounts.append({
        "product": "all products",
        "discount_type": "seasonal_bundle",
        "discount_percent": 15,
        "coupon_code": "SEASON15",
        "reason": "Seasonal campaign to drive repeat purchases",
        "expected_revenue_lift_percent": 18,
        "status": "draft",
    })

    return discounts


def _build_email_campaigns(
    products: list[dict[str, Any]],
    rag_snippets: list[str],
) -> list[dict[str, Any]]:
    primary = products[0] if products else {}
    name = primary.get("name", "our latest product")
    benefit_hint = rag_snippets[0][:100] if rag_snippets else primary.get("description", "")[:100]

    return [
        {
            "campaign_type": "welcome_series",
            "sequence": [
                {
                    "email": 1,
                    "subject": "Welcome to Mynat — Your Ayurvedic Skin Journey Starts Now 🌿",
                    "objective": "Brand introduction + first purchase incentive",
                    "body_direction": "Story of Mynat's Ayurvedic heritage + 10% welcome discount",
                    "cta": "Shop now with code WELCOME10",
                    "send_timing": "Immediately on signup",
                },
                {
                    "email": 2,
                    "subject": f"The #1 product our customers can't stop talking about",
                    "objective": "Product introduction + social proof",
                    "body_direction": f"Feature {name}: {benefit_hint}. Customer reviews.",
                    "cta": "Shop the bestseller",
                    "send_timing": "Day 3",
                },
                {
                    "email": 3,
                    "subject": "Your personalised Ayurvedic skincare routine 🌸",
                    "objective": "Education + cross-sell",
                    "body_direction": "Morning/evening routine guide featuring 2-3 products",
                    "cta": "Build my routine",
                    "send_timing": "Day 7",
                },
            ],
            "expected_open_rate_percent": 45,
            "expected_conversion_percent": 8,
            "status": "draft",
        },
        {
            "campaign_type": "product_promotion",
            "subject": f"✨ New Drop: {name} — Limited Stock",
            "objective": "Drive immediate purchase",
            "body_direction": (
                f"Hero feature of {name}. Benefits: {benefit_hint}. "
                "Social proof section. Urgency trigger."
            ),
            "cta": "Shop now — limited stock",
            "expected_open_rate_percent": 30,
            "expected_conversion_percent": 5,
            "status": "draft",
        },
        {
            "campaign_type": "abandoned_cart",
            "sequence": [
                {
                    "email": 1,
                    "subject": "You left something behind… 👀",
                    "send_timing": "1 hour after abandonment",
                    "body_direction": "Cart reminder with product image + social proof",
                    "cta": "Complete your order",
                },
                {
                    "email": 2,
                    "subject": "Still thinking? Here's 10% off your cart 🎁",
                    "send_timing": "24 hours after abandonment",
                    "body_direction": "10% off coupon + urgency + review snippet",
                    "cta": "Claim your 10% off",
                },
                {
                    "email": 3,
                    "subject": "Last chance — your cart expires tonight",
                    "send_timing": "48 hours after abandonment",
                    "body_direction": "Final urgency + free shipping sweetener if applicable",
                    "cta": "Save my cart",
                },
            ],
            "expected_recovery_rate_percent": 15,
            "status": "draft",
        },
        {
            "campaign_type": "re_engagement",
            "subject": "We miss you! Here's a little something 💝",
            "target": "Customers inactive > 60 days",
            "objective": "Win back lapsed customers",
            "body_direction": "Personalised message + what's new + exclusive 15% re-engagement offer",
            "cta": "Come back and save 15%",
            "expected_reactivation_rate_percent": 10,
            "status": "draft",
        },
        {
            "campaign_type": "cross_sell",
            "subject": f"Loving {name}? Try this next 🌿",
            "target": "Customers who purchased in last 30 days",
            "objective": "Increase LTV with complementary product",
            "body_direction": "Thank-you message + recommendation of complementary product + bundle offer",
            "cta": "Complete your routine",
            "expected_conversion_percent": 12,
            "status": "draft",
        },
    ]


def _impact_score(
    bundles: list,
    upsells: list,
    cross_sells: list,
    discounts: list,
    rag_confidence: str,
) -> dict[str, Any]:
    base = {
        "revenue_lift_percent": 0,
        "aov_lift_percent": 0,
        "conversion_lift_percent": 0,
        "retention_lift_percent": 0,
    }
    if bundles:
        base["revenue_lift_percent"] += 15
        base["aov_lift_percent"] += bundles[0].get("expected_aov_lift_percent", 30)
    if upsells:
        base["revenue_lift_percent"] += 10
        base["aov_lift_percent"] += 15
    if cross_sells:
        base["revenue_lift_percent"] += 8
        base["conversion_lift_percent"] += 10
    if discounts:
        base["conversion_lift_percent"] += 20
        base["retention_lift_percent"] += 12

    confidence_multiplier = {"high": 1.0, "medium": 0.8, "low": 0.6}.get(rag_confidence, 0.7)
    return {
        k: round(v * confidence_multiplier, 1)
        for k, v in base.items()
    } | {"confidence": rag_confidence, "basis": "RAG + product + analytics data"}


def generate_revenue_recommendations(
    products: list[dict[str, Any]],
    analytics: dict[str, Any] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Generate complete revenue recommendations: bundles, upsells, cross-sells,
    discounts, email campaigns, and expected business impact.
    """
    products = [p for p in (products or []) if isinstance(p, dict)]
    analytics = analytics or {}

    if not products:
        return {
            "success": False,
            "error": "No products provided",
            "bundles": [], "upsells": [], "cross_sells": [],
            "discounts": [], "email_campaigns": [],
        }

    # RAG grounding
    rag_query = " ".join(
        [str(p.get("name", "")) for p in products[:5]]
        + ["Mynat cross-sell upsell bundle recommendation"]
    )
    rag_ctx = require_rag_context(rag_query, collection="mynat_products", n_results=6)
    rag_snippets = [
        (item.get("document") or item.get("description") or str(item))[:150]
        for item in rag_ctx.get("context_used", [])
        if isinstance(item, dict)
    ] or [products[0].get("description", "")[:150]]

    bundles = _build_bundles(products)
    upsells = _build_upsells(products)
    cross_sells = _build_cross_sells(products)
    discounts = _build_discounts(products, analytics)
    email_campaigns = _build_email_campaigns(products, rag_snippets)

    impact = _impact_score(bundles, upsells, cross_sells, discounts, rag_ctx["confidence"])

    return {
        "success": True,
        "products_analyzed": len(products),
        "bundles": bundles,
        "upsells": upsells,
        "cross_sells": cross_sells,
        "discounts": discounts,
        "email_campaigns": email_campaigns,
        "expected_business_impact": impact,
        "_meta": {
            "rag_available": rag_ctx["available"],
            "rag_confidence": rag_ctx["confidence"],
            "rag_sources": rag_ctx["sources"],
        },
    }


# ── SeoGrowthEngine ──

_SEO_SYSTEM = (
    "You are an expert SEO Strategist specialising in Ayurvedic skincare e-commerce. "
    "Generate technically correct, conversion-optimised SEO content. "
    "Return valid JSON only."
)


def _fallback_keywords(product: dict[str, Any]) -> list[str]:
    name = product.get("name", "skincare product").lower()
    cat = product.get("category", "skincare").lower()
    return [
        name,
        f"buy {name} online",
        f"{cat} products india",
        f"best {name}",
        f"natural {cat}",
        "ayurvedic skincare",
        "mynat skincare",
        f"{name} benefits",
    ]


def _fallback_longtail(product: dict[str, Any]) -> list[str]:
    name = product.get("name", "skincare product").lower()
    cat = product.get("category", "skincare").lower()
    return [
        f"how to use {name} for best results",
        f"{name} for sensitive skin india",
        f"best ayurvedic {cat} for glowing skin",
        f"is {name} good for oily skin",
        f"{name} ingredients and benefits",
        f"where to buy {name} online india",
        f"{name} vs chemical skincare",
        f"natural {cat} routine with {name}",
    ]


def _fallback_faq(product: dict[str, Any]) -> list[dict[str, str]]:
    name = product.get("name", "this product")
    return [
        {
            "question": f"What is {name} used for?",
            "answer": product.get("description", f"{name} is a natural Ayurvedic skincare product."),
        },
        {
            "question": f"Is {name} suitable for all skin types?",
            "answer": "Yes, it is formulated with natural ingredients suitable for all skin types.",
        },
        {
            "question": f"How long does it take to see results with {name}?",
            "answer": "Most customers see visible improvement within 3–4 weeks of regular use.",
        },
        {
            "question": f"Is {name} free from harmful chemicals?",
            "answer": "Yes, it is free from parabens, sulfates, and artificial fragrances.",
        },
        {
            "question": f"How do I use {name}?",
            "answer": "Apply a small amount to cleansed skin and massage gently until absorbed.",
        },
    ]


def _fallback_seo(product: dict[str, Any]) -> dict[str, Any]:
    name = product.get("name", "Skincare Product")
    cat = product.get("category", "Skincare")
    price = product.get("price", "")
    price_str = f" | ₹{price}" if price else ""
    return {
        "seo_title": f"Buy {name} Online{price_str} | Natural {cat} | Mynat",
        "meta_description": (
            f"Shop {name} — a 100% natural Ayurvedic {cat.lower()} product. "
            f"Free shipping above ₹499. COD available. Order now at Mynat."
        ),
        "h1": f"{name} — Natural Ayurvedic {cat}",
        "keywords": _fallback_keywords(product),
        "long_tail_keywords": _fallback_longtail(product),
        "faq": _fallback_faq(product),
        "page_improvements": [
            "Add high-quality ingredient close-up images",
            "Include customer before/after photos with consent",
            "Add 'How to use' video section",
            "Display trust badges (ISO, Cruelty-Free, Ayush approved)",
            "Add ingredient benefits section with icons",
            "Implement star rating schema markup",
            "Create size/variant comparison table",
        ],
        "schema_markup_type": "Product",
        "internal_linking_suggestions": [
            "Link to related category page",
            "Link to blog post about key ingredient",
            "Cross-link with complementary products",
        ],
    }


def _extract_json(text: str) -> dict[str, Any]:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {}


def _llm_seo(product: dict[str, Any], rag_snippets: list[str]) -> dict[str, Any]:
    prompt = (
        f"Product data:\n{json.dumps(product, default=str)[:500]}\n\n"
        f"RAG context:\n{chr(10).join(rag_snippets[:4])}\n\n"
        "Generate SEO content for this Ayurvedic skincare product page. Return JSON with:\n"
        "{\n"
        '  "seo_title": "...",\n'
        '  "meta_description": "...",\n'
        '  "h1": "...",\n'
        '  "keywords": ["...", ...],\n'
        '  "long_tail_keywords": ["...", ...],\n'
        '  "faq": [{"question": "...", "answer": "..."}, ...],\n'
        '  "page_improvements": ["...", ...]\n'
        "}\n"
        "Rules: seo_title max 65 chars, meta_description max 155 chars, "
        "include 8+ keywords, 8+ long_tail_keywords, 5 FAQs, 6 page improvements."
    )
    raw = call_claude(prompt, max_tokens=1500, system=_SEO_SYSTEM)
    if not raw or is_queue_sentinel(raw):
        return {}
    obj = _extract_json(raw)
    return obj if obj.get("seo_title") else {}


def generate_seo_recommendations(
    products: list[dict[str, Any]],
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Generate SEO recommendations for every product.

    Returns:
      - seo_recommendations: list of per-product SEO dicts
      - keyword_universe: deduplicated keyword list across all products
    """
    products = [p for p in (products or []) if isinstance(p, dict)]
    if not products:
        return {"success": False, "error": "No products provided", "seo_recommendations": []}

    all_keywords: list[str] = []
    results: list[dict[str, Any]] = []

    for product in products:
        rag_query = (
            f"{product.get('name', '')} {product.get('category', '')} "
            f"SEO keywords benefits ayurvedic"
        )
        rag_ctx = require_rag_context(rag_query, collection="mynat_products", n_results=5)
        rag_snippets = [
            (item.get("document") or item.get("description") or str(item))[:150]
            for item in rag_ctx.get("context_used", [])
            if isinstance(item, dict)
        ] or [product.get("description", "")[:150]]

        if use_llm:
            llm_result = _llm_seo(product, rag_snippets)
        else:
            llm_result = {}

        base = _fallback_seo(product)
        merged = {**base, **{k: v for k, v in llm_result.items() if v}}

        merged["product_name"] = product.get("name")
        merged["product_id"] = product.get("id")
        merged["_rag_available"] = rag_ctx["available"]
        merged["_rag_confidence"] = rag_ctx["confidence"]

        all_keywords.extend(merged.get("keywords", []))
        all_keywords.extend(merged.get("long_tail_keywords", []))
        results.append(merged)

    unique_kws = list(dict.fromkeys(all_keywords))

    return {
        "success": True,
        "products_analyzed": len(products),
        "seo_recommendations": results,
        "keyword_universe": unique_kws[:50],
        "total_keywords_identified": len(unique_kws),
    }


# ── RevenueGrowthAgent ──

_SYSTEM = (
    "You are the Revenue Growth AI for Mynat, an Ayurvedic skincare brand. "
    "You think like a Growth Marketing Manager, Performance Marketer, SEO Strategist, "
    "Product Analyst, and E-commerce Consultant combined. "
    "Your goal is to maximise: Revenue, Conversion Rate, Customer Retention, "
    "Average Order Value, Repeat Purchases, Organic Traffic, Campaign Performance. "
    "All recommendations are drafts for human review — never auto-publish. "
    "Return valid JSON only."
)


def _now_iso() -> str:
    from datetime import UTC, datetime as _dt
    return _dt.now(UTC).replace(tzinfo=None).isoformat()


def _llm_growth_recommendations(
    products: list[dict[str, Any]],
    analytics: dict[str, Any],
    opportunity_result: dict[str, Any],
    customer_insights: dict[str, Any],
    rag_snippets: list[str],
) -> list[dict[str, Any]]:
    """Ask Claude to synthesise all data into high-level growth recommendations."""
    top_products = [p.get("name") for p in opportunity_result.get("best_products_to_promote", [])[:3]]
    pain_points = [p.get("pain") for p in customer_insights.get("pain_points", [])[:3]]
    prompt = (
        f"Top products: {top_products}\n"
        f"Customer pain points: {pain_points}\n"
        f"Season: {opportunity_result.get('season')}\n"
        f"Analytics ROI%: {(analytics.get('roi') or {}).get('roi_percent', 'unknown')}\n"
        f"RAG context: {rag_snippets[0] if rag_snippets else 'no context'}\n\n"
        "Generate 6 high-impact growth recommendations for Mynat's next 30 days. "
        "Each should address: revenue, conversion rate, retention, AOV, organic traffic, "
        "or campaign performance. Return JSON array:\n"
        '[\n'
        '  {"priority": 1, "area": "...", "recommendation": "...", '
        '"expected_impact": "...", "effort": "low|medium|high", '
        '"timeframe": "...", "kpi": "..."}\n'
        ']\n'
        "Be specific, actionable, and data-grounded."
    )
    raw = call_claude(prompt, max_tokens=1500, system=_SYSTEM)
    if not raw or is_queue_sentinel(raw):
        return []
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if not match:
        return []
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return []


def _fallback_growth_recommendations(products: list[dict[str, Any]]) -> list[dict[str, Any]]:
    name = products[0].get("name", "top product") if products else "top product"
    return [
        {
            "priority": 1,
            "area": "Revenue",
            "recommendation": f"Launch 30-day content push for {name} with daily Instagram + WhatsApp posts",
            "expected_impact": "15-20% revenue lift",
            "effort": "medium",
            "timeframe": "30 days",
            "kpi": "Revenue, Conversion Rate",
        },
        {
            "priority": 2,
            "area": "Average Order Value",
            "recommendation": "Implement routine bundles and upsell prompts on all product pages",
            "expected_impact": "25-35% AOV increase",
            "effort": "medium",
            "timeframe": "2 weeks",
            "kpi": "AOV, Units per Order",
        },
        {
            "priority": 3,
            "area": "Organic Traffic",
            "recommendation": "Publish 4 SEO blog posts targeting long-tail Ayurvedic skincare keywords",
            "expected_impact": "20-30% organic traffic in 60 days",
            "effort": "medium",
            "timeframe": "60 days",
            "kpi": "Organic Sessions, Keyword Rankings",
        },
        {
            "priority": 4,
            "area": "Conversion Rate",
            "recommendation": "A/B test abandoned cart recovery sequence (3-email series with 10% discount)",
            "expected_impact": "12-18% cart recovery rate",
            "effort": "low",
            "timeframe": "2 weeks",
            "kpi": "Cart Recovery Rate, Conversion Rate",
        },
        {
            "priority": 5,
            "area": "Retention",
            "recommendation": "Launch monthly WhatsApp skincare routine tips to existing customers",
            "expected_impact": "10-15% repeat purchase lift",
            "effort": "low",
            "timeframe": "Ongoing",
            "kpi": "Repeat Purchase Rate, LTV",
        },
        {
            "priority": 6,
            "area": "Campaign Performance",
            "recommendation": "Test 3 reel concepts (educational, testimonial, viral hook) with ₹5k daily budget each",
            "expected_impact": "2-3x ROAS improvement vs static posts",
            "effort": "medium",
            "timeframe": "2 weeks",
            "kpi": "ROAS, CPM, CTR",
        },
    ]


def _budget_allocation(
    analytics: dict[str, Any],
    opportunity_result: dict[str, Any],
) -> dict[str, Any]:
    roi = _num((analytics.get("roi") or {}).get("roi_percent"))
    best = (opportunity_result.get("best_products_to_promote") or [{}])[0]
    best_name = best.get("name", "top product")

    if roi > 30:
        split = {"instagram_reels": 35, "facebook_ads": 25, "seo_content": 20, "email": 10, "whatsapp": 10}
        action = "scale"
    elif roi > 0:
        split = {"instagram_reels": 30, "facebook_ads": 20, "seo_content": 30, "email": 10, "whatsapp": 10}
        action = "test_and_learn"
    else:
        split = {"instagram_reels": 20, "facebook_ads": 15, "seo_content": 40, "email": 15, "whatsapp": 10}
        action = "organic_first"

    return {
        "action": action,
        "focus_product": best_name,
        "channel_split_percent": split,
        "reasoning": f"ROI {roi:.1f}% — {action.replace('_', ' ')} strategy recommended",
        "status": "draft",
    }


def _build_expected_impact(
    opportunity: dict[str, Any],
    revenue_recs: dict[str, Any],
    seo: dict[str, Any],
    rag_confidence: str,
) -> dict[str, Any]:
    base = revenue_recs.get("expected_business_impact", {})
    confidence_mult = {"high": 1.0, "medium": 0.8, "low": 0.6}.get(rag_confidence, 0.7)

    return {
        "revenue_lift_percent": round(_num(base.get("revenue_lift_percent", 20)) * confidence_mult, 1),
        "aov_lift_percent": round(_num(base.get("aov_lift_percent", 25)) * confidence_mult, 1),
        "conversion_lift_percent": round(_num(base.get("conversion_lift_percent", 15)) * confidence_mult, 1),
        "retention_lift_percent": round(_num(base.get("retention_lift_percent", 10)) * confidence_mult, 1),
        "organic_traffic_lift_percent": round(25 * confidence_mult, 1),
        "estimated_additional_revenue_per_month": "₹50,000–₹2,00,000 (based on current product range)",
        "confidence": rag_confidence,
        "products_with_seo_opportunity": len(seo.get("seo_recommendations", [])),
        "keywords_identified": seo.get("total_keywords_identified", 0),
        "basis": "RAG + Analytics + Customer Reviews + Product Data",
        "disclaimer": "All projections are estimates. Actual results depend on execution quality and market conditions.",
    }


def run_revenue_growth_agent(
    products: list[dict[str, Any]] | None = None,
    analytics: dict[str, Any] | None = None,
    reviews: list[dict[str, Any]] | None = None,
    campaign_history: list[dict[str, Any]] | None = None,
    shopify_data: dict[str, Any] | None = None,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Primary decision-making agent for Mynat marketing strategy.

    Runs all 5 sub-engines and synthesises a comprehensive growth plan.
    All outputs are draft — never auto-published.

    Args:
        products: Product catalog (from Shopify, DB, or scraper)
        analytics: Analytics agent output dict
        reviews: Customer reviews list
        campaign_history: Historical campaign data
        shopify_data: Shopify webhooks / catalog data
        use_llm: Whether to call Claude for LLM-enhanced outputs

    Returns:
        Comprehensive revenue growth plan with all sub-engine outputs.
    """
    products = [p for p in (products or []) if isinstance(p, dict)]
    analytics = analytics or {}
    reviews = [r for r in (reviews or []) if isinstance(r, dict)]
    campaign_history = [c for c in (campaign_history or []) if isinstance(c, dict)]
    shopify_data = shopify_data or {}

    # Merge Shopify catalog products if provided
    if shopify_data.get("products"):
        shopify_products = [p for p in shopify_data["products"] if isinstance(p, dict)]
        existing_names = {str(p.get("name")) for p in products}
        for sp in shopify_products:
            if str(sp.get("name")) not in existing_names:
                products.append(sp)

    if not products:
        return {
            "success": False,
            "error": "No product data provided. Supply products list or shopify_data.",
            "status": "draft",
            "best_products_to_promote": [],
            "content_calendar": [],
            "reel_strategy": [],
            "seo_recommendations": [],
            "email_campaigns": [],
            "bundles": [],
            "cross_sells": [],
            "upsells": [],
            "growth_recommendations": [],
            "expected_business_impact": {},
            "_meta": {"fallback_used": True, "confidence": "low"},
        }

    # ── Global RAG context ────────────────────────────────────────────────────
    global_rag_query = (
        " ".join([str(p.get("name", "")) for p in products[:8]])
        + " Mynat revenue growth marketing strategy"
    )
    global_rag = require_rag_context(global_rag_query, collection="mynat_products", n_results=8)
    rag_snippets = [
        (item.get("document") or item.get("description") or str(item))[:150]
        for item in global_rag.get("context_used", [])
        if isinstance(item, dict)
    ]

    # ── Sub-engine execution ──────────────────────────────────────────────────

    opportunity_result = detect_product_opportunities(
        products=products,
        analytics=analytics,
        reviews=reviews,
        campaign_history=campaign_history,
    )

    # Use ranked products for downstream engines
    ranked_products = [
        next((p for p in products if p.get("name") == item.get("name")), item)
        for item in opportunity_result.get("best_products_to_promote", [])[:8]
    ] or products

    content_result = generate_content_strategy(
        products=ranked_products,
        analytics=analytics,
        campaign_history=campaign_history,
        use_llm=use_llm,
    )

    seo_result = generate_seo_recommendations(
        products=ranked_products,
        use_llm=use_llm,
    )

    revenue_result = generate_revenue_recommendations(
        products=ranked_products,
        analytics=analytics,
        use_llm=use_llm,
    )

    customer_result = generate_customer_insights(
        products=ranked_products,
        reviews=reviews,
        use_llm=use_llm,
    )

    # ── Growth recommendations (LLM synthesis) ────────────────────────────────
    if use_llm:
        growth_recs = _llm_growth_recommendations(
            products=ranked_products,
            analytics=analytics,
            opportunity_result=opportunity_result,
            customer_insights=customer_result,
            rag_snippets=rag_snippets,
        )
    else:
        growth_recs = []

    if not growth_recs:
        growth_recs = _fallback_growth_recommendations(ranked_products)

    # ── Budget allocation & expected impact ───────────────────────────────────
    budget_allocation = _budget_allocation(analytics, opportunity_result)
    expected_impact = _build_expected_impact(
        opportunity_result, revenue_result, seo_result, global_rag["confidence"]
    )

    return {
        "success": True,
        "status": "draft",
        "generated_at": _now_iso(),
        "agent": "revenue_growth_agent",
        "products_analyzed": len(products),
        "season": opportunity_result.get("season"),

        # ── Core output contract ──────────────────────────────────────────────
        "best_products_to_promote": opportunity_result.get("best_products_to_promote", []),
        "underperforming_products": opportunity_result.get("underperforming_products", []),
        "seasonal_products": opportunity_result.get("seasonal_products", []),
        "high_margin_products": opportunity_result.get("high_margin_products", []),
        "trending_products": opportunity_result.get("trending_products", []),

        "content_calendar": content_result.get("content_calendar", []),
        "instagram_plan": content_result.get("instagram_plan", []),
        "facebook_plan": content_result.get("facebook_plan", []),
        "whatsapp_plan": content_result.get("whatsapp_plan", []),
        "blog_plan": content_result.get("blog_plan", []),
        "email_plan": content_result.get("email_plan", []),

        "reel_strategy": content_result.get("reel_strategy", []),

        "seo_recommendations": seo_result.get("seo_recommendations", []),
        "keyword_universe": seo_result.get("keyword_universe", []),

        "email_campaigns": revenue_result.get("email_campaigns", []),
        "bundles": revenue_result.get("bundles", []),
        "cross_sells": revenue_result.get("cross_sells", []),
        "upsells": revenue_result.get("upsells", []),
        "discounts": revenue_result.get("discounts", []),

        "pain_points": customer_result.get("pain_points", []),
        "buying_triggers": customer_result.get("buying_triggers", []),
        "objections": customer_result.get("objections", []),
        "emotional_motivations": customer_result.get("emotional_motivations", []),
        "customer_personas": customer_result.get("customer_personas", []),
        "messaging_framework": customer_result.get("messaging_framework", {}),

        "growth_recommendations": growth_recs,
        "budget_allocation": budget_allocation,
        "expected_business_impact": expected_impact,

        "_meta": {
            "fallback_used": False,
            "confidence": global_rag["confidence"],
            "rag_available": global_rag["available"],
            "rag_sources": global_rag["sources"],
            "llm_enhanced": use_llm,
            "sub_engines_run": [
                "product_opportunity_engine",
                "content_strategy_engine",
                "seo_growth_engine",
                "revenue_recommendation_engine",
                "customer_insight_engine",
            ],
        },
    }
