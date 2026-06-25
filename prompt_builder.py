"""
Prompt Generator
================
Generates copy-paste-ready prompts for the Claude desktop/web app.

When CLAUDE_APP_MODE=true the system never calls any AI API.
Instead it produces a richly-structured prompt that the user pastes into
Claude App, then pastes Claude's JSON response back via the import endpoint.

Nothing here depends on an API key.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any


# ─────────────────────────────────────────────────────────────────────────────
# Season / calendar helpers (no AI needed)
# ─────────────────────────────────────────────────────────────────────────────

MONTH_SEASON: dict[int, str] = {
    1: "winter", 2: "winter", 3: "summer", 4: "summer",
    5: "summer", 6: "monsoon", 7: "monsoon", 8: "monsoon",
    9: "festive", 10: "festive", 11: "festive", 12: "winter",
}
SEASON_THEMES: dict[str, str] = {
    "winter":  "Nourishing warmth, protection from cold & dryness",
    "summer":  "Cooling, oil-control, sun protection, hydration",
    "monsoon": "Fungal defense, deep cleanse, humidity care",
    "festive": "Glow for the season, gifting, premium self-care",
}
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}
SEASONAL_HASHTAGS: dict[str, list[str]] = {
    "winter":  ["#WinterSkincare", "#WinterGlow", "#DrySkincareRoutine"],
    "summer":  ["#SummerSkincare", "#SummerGlow", "#OilFreeSkin"],
    "monsoon": ["#MonsoonSkincare", "#RainySeasonSkin", "#ClearSkin"],
    "festive": ["#FestiveSkincare", "#DiwaliGlow", "#FestiveLook"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_content_prompt(
    product_data: dict[str, Any],
    creator_strategy: dict[str, Any] | None = None,
    review_data: dict[str, Any] | None = None,
    trend_keywords: list[str] | None = None,
    month: int | None = None,
) -> str:
    """
    Build a complete, copy-paste-ready prompt for Claude App.

    Args:
        product_data:      Product dict (name, description, price, category, image_url, benefits).
        creator_strategy:  Optional Creator Agent output for seasonal angle / audience.
        review_data:       Optional review sentiment (overall_sentiment, marketing_strengths).
        trend_keywords:    Extra trending keywords.
        month:             Current month (defaults to now).

    Returns:
        A multi-section plain-text prompt ready for Claude App.
    """
    month = month or datetime.now().month
    season = MONTH_SEASON.get(month, "festive")
    month_name = MONTH_NAMES.get(month, "Unknown")
    season_theme = SEASON_THEMES.get(season, "")
    season_tags = SEASONAL_HASHTAGS.get(season, [])

    creator = creator_strategy or {}
    review = review_data or {}

    name = product_data.get("name", "")
    description = product_data.get("description", "")
    price = product_data.get("price", "")
    category = product_data.get("category", "skincare")
    image_url = product_data.get("image_url", "")
    benefits = product_data.get("benefits", [])
    ingredients = product_data.get("ingredients", product_data.get("tags", []))

    seasonal_angle = creator.get("seasonal_angle", f"{season.title()} Ayurvedic skincare")
    target_audience = creator.get("target_audience", "Indian women 22–45, skincare conscious")
    platform = creator.get("platform", "instagram")
    confidence_score = creator.get("confidence_score", 0)
    risk_score = creator.get("risk_score", 0)

    review_sentiment = review.get("overall_sentiment", "positive")
    review_strengths = ", ".join(review.get("marketing_strengths", ["natural ingredients", "effective formula"])[:3])
    review_avoid = ", ".join(review.get("avoid_mentioning", [])[:2]) or "none"
    star_rating = review.get("star_rating", 4.0)

    extra_keywords = (trend_keywords or []) + season_tags
    keyword_str = ", ".join(extra_keywords[:10]) or "Ayurveda, natural skincare, India"

    benefits_str = (
        "\n".join(f"  - {b}" for b in benefits[:5])
        if benefits
        else "  - Natural Ayurvedic formula\n  - No harsh chemicals\n  - Suitable for Indian skin"
    )
    ingredients_str = (
        ", ".join(str(i) for i in ingredients[:8])
        if ingredients
        else "Ayurvedic botanicals"
    )

    strategy_block = ""
    if creator:
        strategy_block = f"""
CREATOR AGENT STRATEGY (already computed — use as-is):
  Seasonal angle   : {seasonal_angle}
  Target audience  : {target_audience}
  Platform         : {platform}
  Confidence score : {confidence_score}/100
  Risk score       : {risk_score}/100
"""

    prompt = f"""You are a senior D2C marketing strategist and copywriter for Mynat — an Ayurvedic skincare brand from India.

Brand voice: Natural, warm, trustworthy, vibrant. Indian audience.
Mix English with occasional Hindi phrases when it sounds natural.
NEVER use: "guaranteed", "cure", "whitening", "bleaching", "100% effective", "dermatologist-tested" (unless true).
All content must be brand-safe and suitable for Meta/WhatsApp.

══════════════════════════════════════════════════════════════
PRODUCT INFORMATION
══════════════════════════════════════════════════════════════
Name         : {name}
Description  : {description}
Price        : ₹{price}
Category     : {category}
Image URL    : {image_url}

Key Benefits :
{benefits_str}

Key Ingredients : {ingredients_str}

══════════════════════════════════════════════════════════════
SEASONAL CONTEXT
══════════════════════════════════════════════════════════════
Month   : {month_name}
Season  : {season.title()}
Theme   : {season_theme}
Keywords: {keyword_str}
{strategy_block}
══════════════════════════════════════════════════════════════
CUSTOMER SENTIMENT
══════════════════════════════════════════════════════════════
Overall sentiment : {review_sentiment}
Highlight these  : {review_strengths}
Avoid mentioning : {review_avoid}
Star rating      : {star_rating}/5

══════════════════════════════════════════════════════════════
YOUR TASK — Generate ALL of the following:
══════════════════════════════════════════════════════════════

1. instagram_captions  — 20 unique captions (80-120 words each, 2-3 emojis, end with CTA)
2. facebook_posts      — 10 unique posts (150-200 words, educational, Ayurvedic benefit-led)
3. whatsapp_messages   — 10 messages (max 150 chars each, personal, strong CTA)
4. ad_copies           — 10 ads (headline ≤6 words + body 30-40 words + CTA button label)
5. reel_scripts        — 5 scripts (30-sec: hook 3s / problem 5s / solution+product 15s / cta 7s)
6. seo_description     — 1 product page description (200-250 words, keyword-rich, no medical claims)
7. hashtags            — 20 tags (mix: high-volume + niche + seasonal + #mynat + product-specific)

══════════════════════════════════════════════════════════════
OUTPUT FORMAT — Return ONLY valid JSON, nothing else:
══════════════════════════════════════════════════════════════

{{
  "product_name": "{name}",
  "generated_at": "YYYY-MM-DD",
  "instagram_captions": [
    "caption 1 text...",
    "caption 2 text...",
    ... (20 total)
  ],
  "facebook_posts": [
    "post 1 text...",
    ... (10 total)
  ],
  "whatsapp_messages": [
    "message 1...",
    ... (10 total)
  ],
  "ad_copies": [
    {{
      "headline": "short headline",
      "body": "30-40 word ad body...",
      "cta_button": "Shop Now"
    }},
    ... (10 total)
  ],
  "reel_scripts": [
    {{
      "hook": "opening 3 seconds...",
      "problem": "5-second problem framing...",
      "solution": "15-second product solution...",
      "cta": "7-second closing CTA..."
    }},
    ... (5 total)
  ],
  "seo_description": "200-250 word product description...",
  "hashtags": [
    "#tag1", "#tag2", ... (20 total)
  ]
}}

IMPORTANT:
- Return ONLY the JSON object above — no intro text, no explanations, no markdown code blocks.
- Every array must have exactly the number of items specified.
- All content must be in English with natural Hindi phrases where appropriate.
- The JSON must be valid and parseable."""

    return prompt


# ─────────────────────────────────────────────────────────────────────────────
# Creator Agent prompt (Canva + Meta creative direction — no API needed)
# ─────────────────────────────────────────────────────────────────────────────

def generate_creator_prompt(
    product_data: dict[str, Any],
    content_output: dict[str, Any] | None = None,
    creator_strategy: dict[str, Any] | None = None,
) -> str:
    """
    Generate a Claude App prompt to produce Canva briefs and creative direction.

    The Creator Agent's intelligence (product scoring, season detection) runs
    locally. This prompt handles the creative/visual direction output.
    """
    creator = creator_strategy or {}
    name = product_data.get("name", "")
    price = product_data.get("price", "")
    category = product_data.get("category", "skincare")
    image_url = product_data.get("image_url", "")

    seasonal_angle = creator.get("seasonal_angle", "Ayurvedic skincare")
    platform = creator.get("platform", "instagram")
    content_type = creator.get("content_type", "post")

    sample_caption = ""
    if content_output:
        captions = content_output.get("instagram_captions", content_output.get("instagram_caption"))
        if isinstance(captions, list) and captions:
            sample_caption = captions[0]
        elif isinstance(captions, str):
            sample_caption = captions

    prompt = f"""You are a senior creative director for Mynat — a premium Indian Ayurvedic skincare brand.

Brand aesthetics: Warm earthy tones (#C8872A, #FFF5E1, #2D4A27), premium Ayurvedic luxury, clean Indian wellness.
No cluttered designs. No whitening/fairness themes. Natural ingredient motifs welcome.

══════════════════════════════════════════════════════════════
PRODUCT
══════════════════════════════════════════════════════════════
Name     : {name}
Price    : ₹{price}
Category : {category}
Image    : {image_url}
Campaign angle: {seasonal_angle}
Platform : {platform} ({content_type})

{"APPROVED CAPTION:" + chr(10) + sample_caption if sample_caption else ""}

══════════════════════════════════════════════════════════════
YOUR TASK — Generate creative direction package:
══════════════════════════════════════════════════════════════

1. canva_brief     — Canva design brief (dimensions, layout, colors, typography, elements)
2. headlines       — 5 punchy visual headlines (≤6 words each)
3. cta_options     — 5 CTA button labels
4. carousel_slides — If platform=instagram carousel: 5-slide breakdown (hook/benefit/benefit/proof/cta)
5. visual_concept  — 3 sentences describing the visual concept and mood
6. design_dos      — 5 specific things the designer must include
7. design_donts    — 5 specific things to avoid

══════════════════════════════════════════════════════════════
OUTPUT FORMAT — Return ONLY valid JSON:
══════════════════════════════════════════════════════════════

{{
  "product_name": "{name}",
  "platform": "{platform}",
  "canva_brief": {{
    "dimensions": {{"width": 1080, "height": 1080}},
    "layout": "describe the layout...",
    "primary_colors": ["#C8872A", "#FFF5E1"],
    "accent_colors": ["#2D4A27"],
    "typography": {{
      "headline_font": "...",
      "body_font": "...",
      "font_pairing_note": "..."
    }},
    "hero_element": "product image center / ingredient flat-lay / etc.",
    "background": "describe background treatment"
  }},
  "headlines": ["headline 1", "headline 2", "headline 3", "headline 4", "headline 5"],
  "cta_options": ["Shop Now", "Try It Today", "Get Yours", "Order Now", "Discover More"],
  "carousel_slides": [
    {{"slide": 1, "type": "hook", "headline": "...", "visual": "..."}},
    {{"slide": 2, "type": "benefit", "headline": "...", "visual": "..."}},
    {{"slide": 3, "type": "benefit", "headline": "...", "visual": "..."}},
    {{"slide": 4, "type": "social_proof", "headline": "...", "visual": "..."}},
    {{"slide": 5, "type": "cta", "headline": "...", "visual": "..."}}
  ],
  "visual_concept": "3-sentence visual concept description...",
  "design_dos": ["do 1", "do 2", "do 3", "do 4", "do 5"],
  "design_donts": ["dont 1", "dont 2", "dont 3", "dont 4", "dont 5"]
}}"""

    return prompt
