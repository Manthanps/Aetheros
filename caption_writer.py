"""
Content Agent — flat module (merged from agents/content_agent/ package).
Takes Creator Agent strategic output + product data and generates
polished, brand-safe marketing content for all 10 channels in one Claude call.
"""
from __future__ import annotations

# ── content_agent/prompts.py ──────────────────────────────────────────────────

MASTER_CONTENT_PROMPT = """You are the content specialist for Mynat — an Ayurvedic skincare brand from India.

Your job: Take the marketing strategy below and produce polished, channel-ready content for every format.

Brand voice: Natural, warm, trustworthy. Indian audience. Mix English with occasional Hindi phrases when it sounds natural.
Always be concise, punchy, and conversion-focused. Never make medical claims. Never use: "guaranteed", "cure", "whitening", "bleaching", "100% effective".

---

PRODUCT:
Name: {product_name}
Description: {product_description}
Price: ₹{product_price}
Category: {product_category}
Image: {image_url}

STRATEGY (from Creator Agent):
Seasonal angle: {seasonal_angle}
Target audience: {target_audience}
Platform: {platform}
Content type: {content_type}

SEASON CONTEXT:
Season: {season} | Month: {month_name}
Trending keywords: {trend_keywords}
Seasonal theme: {season_theme}

CUSTOMER SENTIMENT (public response):
Overall: {review_sentiment}
Strengths to highlight: {review_strengths}
Topics to avoid: {review_avoid}
Rating: {customer_rating}/5
{urgency_note}

---

Generate content for ALL channels. Follow these format rules exactly:

1. instagram_caption — 80-120 words, 2-3 emojis, end with CTA, warm + punchy tone
2. facebook_caption — 150-200 words, educational, explain Ayurvedic benefit, include price naturally
3. whatsapp_message — max 150 chars total, personal, direct, strong CTA (for broadcast list)
4. reel_script — 30-second structure with hook(3s) / problem(5s) / solution+product(15s) / cta(7s)
5. story_text — 3 slides: slide 1 = attention hook, slide 2 = key benefit + price, slide 3 = CTA only
6. ad_copy — headline ≤6 words, body 30-40 words, CTA button label
7. hashtags — exactly 25 tags: mix high/mid/low volume + seasonal + #mynat + product-specific
8. cta_options — 4 CTAs from softest to most urgent
9. seo_title — product page title optimised for search (max 60 chars, include main keyword + Mynat)
10. meta_description — SEO meta (max 155 chars, brand + key benefit + CTA keyword)

Return ONLY valid JSON in this EXACT structure — no extra keys, no markdown, no preamble:
{{
  "instagram_caption": "full caption text",
  "facebook_caption": "full Facebook caption text",
  "whatsapp_message": "short message ≤150 chars",
  "reel_script": {{
    "hook": "opening 3-second text or action description",
    "problem": "5-second problem statement",
    "solution": "15-second product solution with name + key benefit",
    "cta": "7-second closing call to action",
    "on_screen_text": ["overlay line 1", "overlay line 2", "overlay line 3"],
    "music_suggestion": "trending audio style description"
  }},
  "story_text": {{
    "slide_1": "attention-grabbing hook (one line)",
    "slide_2": "key benefit + price mention (one line)",
    "slide_3": "CTA only — e.g. Tap the link in bio 🛒"
  }},
  "ad_copy": {{
    "headline": "short headline ≤6 words",
    "body": "ad body text 30-40 words",
    "cta_button": "Shop Now"
  }},
  "hashtags": ["#tag1", "#tag2", "#tag3"],
  "cta_options": [
    "soft CTA — discovery/curiosity",
    "medium CTA — benefit-led",
    "direct CTA — shop now style",
    "urgency CTA — scarcity or time-based"
  ],
  "seo_title": "SEO product title ≤60 chars",
  "meta_description": "SEO meta description ≤155 chars"
}}"""


# ── content_agent/tools.py ────────────────────────────────────────────────────

from typing import Any

SEASON_CONTENT_CONTEXT: dict[str, dict] = {
    "summer": {
        "theme": "Beat the heat with nature",
        "seasonal_hashtags": [
            "#SummerSkincare", "#GlowSeason", "#SummerGlow",
            "#HydrationStation", "#SummerBeauty", "#CoolSkin",
        ],
        "reel_style": "fast cuts, bright outdoor lighting, terrace or park shots",
        "whatsapp_tone": "cooling + protective benefit, urgency if stock low",
        "story_hook_style": "problem-first (sweating, tanning, oily skin?)",
        "ad_angle": "Beat the heat, protect your skin naturally",
    },
    "monsoon": {
        "theme": "Fresh, clear skin through the rains",
        "seasonal_hashtags": [
            "#MonsoonSkincare", "#RainySeason", "#ClearSkin",
            "#PurifyYourSkin", "#MonsoonBeauty", "#FreshSkin",
        ],
        "reel_style": "cozy indoor setting, rain sounds in background, warm lighting",
        "whatsapp_tone": "protection from humidity + pollution",
        "story_hook_style": "environmental trigger (humidity, excess oil, breakouts?)",
        "ad_angle": "Monsoon-proof skin with Ayurvedic herbs",
    },
    "winter": {
        "theme": "Nourish and protect in the cold",
        "seasonal_hashtags": [
            "#WinterSkincare", "#DrySkinTips", "#NourishYourSkin",
            "#WinterGlow", "#WinterBeauty", "#SkinRepair",
        ],
        "reel_style": "cozy morning routine, warm-toned, soft natural light",
        "whatsapp_tone": "nourishing + healing, winter dryness solved",
        "story_hook_style": "solution-first (your winter skin rescue is here)",
        "ad_angle": "Winter skin repaired — deep nourishment from nature",
    },
    "festive": {
        "theme": "Glow for every celebration",
        "seasonal_hashtags": [
            "#FestiveSkin", "#DiwaliGlow", "#FestiveReady",
            "#NaturalGlamour", "#FestiveBeauty", "#GlowForDiwali",
        ],
        "reel_style": "celebratory, gold accents, festive ambience, warm tones",
        "whatsapp_tone": "gifting + celebratory, glow for the occasion",
        "story_hook_style": "aspiration-first (look radiant this festive season ✨)",
        "ad_angle": "Natural glow for every festive moment",
    },
}

AUDIENCE_TONE_MAP: dict[str, dict] = {
    "college": {
        "language_mix": "English-heavy, casual, relatable, Gen-Z friendly",
        "hindi_phrases": ["skingame strong hai ✨", "vibe toh dekho 🌿"],
        "content_length": "shorter — punchy and visual",
    },
    "working": {
        "language_mix": "English with occasional Hindi phrases",
        "hindi_phrases": ["baaki sab baad mein, skin pehle 🌿", "natural hi sabse acha"],
        "content_length": "medium — benefit-led with proof",
    },
    "homemaker": {
        "language_mix": "Hindi-English mix, warm and familiar",
        "hindi_phrases": ["ghar ki dekhbhal ke saath skin ki bhi", "prakritik formula"],
        "content_length": "medium — emotional + trust-building",
    },
    "default": {
        "language_mix": "English with occasional Hindi phrases",
        "hindi_phrases": ["naturally yours 🌿", "ayurveda ki shakti"],
        "content_length": "medium",
    },
}

BLOCKED_PHRASES: list[str] = [
    "guaranteed cure", "treat disease", "clinically proven", "fda approved",
    "100% effective", "instant results", "lose weight", "whitening", "bleaching",
    "skin lightening", "fairness cream",
]


def get_season_context(season: str, month: int, extra_keywords: list[str] | None = None) -> dict[str, Any]:
    """Return seasonal content guidance and hashtag suggestions."""
    ctx = SEASON_CONTENT_CONTEXT.get(season, SEASON_CONTENT_CONTEXT["festive"])
    hashtags = ctx["seasonal_hashtags"] + (extra_keywords or [])
    return {
        "season": season,
        "theme": ctx["theme"],
        "trend_keywords_str": ", ".join(hashtags[:8]),
        "reel_style": ctx["reel_style"],
        "whatsapp_tone": ctx["whatsapp_tone"],
        "story_hook_style": ctx["story_hook_style"],
        "ad_angle": ctx["ad_angle"],
        "seasonal_hashtags": hashtags,
    }


def get_audience_profile(target_audience: str) -> dict[str, Any]:
    """Detect audience type from a plain-text description and return tone settings."""
    lower = target_audience.lower()
    if any(w in lower for w in ("college", "student", "18-22", "gen z")):
        key = "college"
    elif any(w in lower for w in ("working", "professional", "career", "corporate")):
        key = "working"
    elif any(w in lower for w in ("homemaker", "housewife", "stay-at-home")):
        key = "homemaker"
    else:
        key = "default"
    return {**AUDIENCE_TONE_MAP[key], "detected_segment": key, "raw_description": target_audience}


def build_content_fallback(product_name: str, product_description: str, product_price: float | str, seasonal_angle: str, target_audience: str, season: str, cta: str = "Shop now — link in bio") -> dict[str, Any]:
    """Template-based content used when the Claude API is unavailable."""
    season_ctx = get_season_context(season, 1)
    price_str = str(product_price)
    desc_short = (product_description or "")[:80]
    desc_medium = (product_description or "")[:140]

    base_hashtags = [
        "#mynat", "#ayurveda", "#skincare", "#naturalbeauty", "#indianskincare",
        "#ayurvedicskincare", "#glowskin", "#skincareRoutine", "#herbalcare",
        "#beautytips", "#organicskincare", "#skincareIndia", "#mynatofficial",
        "#naturalingredients", "#ayurvedaforlife",
    ]
    hashtags = (base_hashtags + season_ctx["seasonal_hashtags"])[:25]
    audience_label = target_audience.split(",")[0].strip() if target_audience else "skincare lovers"

    return {
        "instagram_caption": (
            f"✨ Introducing {product_name} — {season_ctx['theme']}!\n\n"
            f"{desc_short}...\n\n"
            f"Only ₹{price_str} | 100% Natural & Ayurvedic 🌿\n\n{cta}"
        ),
        "facebook_caption": (
            f"Discover the power of Ayurveda with {product_name}.\n\n"
            f"{desc_medium}...\n\n"
            f"Crafted from time-tested Ayurvedic herbs, {product_name} is "
            f"perfect for {audience_label} who want naturally radiant skin.\n\n"
            f"🌿 ₹{price_str} | Free shipping | Shop at mynat.in\n\n"
            f"Why Mynat? Every ingredient is plant-based, ethically sourced, "
            f"and formulated for Indian skin types."
        ),
        "whatsapp_message": (
            f"Hi! {product_name} by Mynat — ₹{price_str}. "
            f"Ayurvedic formula for glowing skin. Shop: mynat.in 🌿"
        )[:150],
        "reel_script": {
            "hook": f"Your skin deserves better this {season}! 👀",
            "problem": "Harsh chemicals, seasonal damage, dull skin... sound familiar?",
            "solution": (f"{product_name} — pure Ayurvedic care at just ₹{price_str}. {desc_short}"),
            "cta": "Shop now at mynat.in — link in bio! 🛒",
            "on_screen_text": [f"Meet {product_name} 🌿", f"Only ₹{price_str}", "Shop at mynat.in"],
            "music_suggestion": "Soft trending lo-fi or upbeat indie track",
        },
        "story_text": {
            "slide_1": f"Struggling with {season} skin damage? 🤔",
            "slide_2": f"{product_name} | ₹{price_str} | 100% Ayurvedic ✨",
            "slide_3": "Tap the link in bio to shop now 🛒",
        },
        "ad_copy": {
            "headline": f"Natural {season.title()} Skincare",
            "body": (
                f"{product_name} by Mynat — Ayurvedic formula for glowing skin. "
                f"Only ₹{price_str}. Trusted by thousands of Indian women. "
                f"Free shipping across India."
            ),
            "cta_button": "Shop Now",
        },
        "hashtags": hashtags,
        "cta_options": [
            f"Discover more about {product_name} at mynat.in 🌿",
            cta,
            "Order today — link in bio! 🛒",
            f"Only ₹{price_str} — shop before it sells out! ⚡",
        ],
        "seo_title": f"{product_name} — Natural Ayurvedic Skincare | Mynat",
        "meta_description": (
            f"Buy {product_name} online at Mynat. {desc_short}... "
            f"₹{price_str}. Free shipping. Shop now at mynat.in"
        )[:155],
    }


def apply_brand_safety(content: dict[str, Any]) -> dict[str, Any]:
    """Scan text fields for blocked phrases and flag violations."""
    violations: list[str] = []
    text_fields = ["instagram_caption", "facebook_caption", "whatsapp_message"]
    for field in text_fields:
        text = (content.get(field) or "").lower()
        for phrase in BLOCKED_PHRASES:
            if phrase in text:
                violations.append(f"{field}: '{phrase}'")
    content["_brand_safety"] = {"brand_safe": len(violations) == 0, "violations": violations}
    return content


# ── content_agent/agent.py ────────────────────────────────────────────────────

import json
import logging
import os
import re
from datetime import datetime

from agents.shared import call_claude, parse_json_object, is_queue_sentinel
from agents.product_knowledge import require_rag_context
from agents.agent_schemas import ContentAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback

logger = logging.getLogger(__name__)

MONTH_TO_SEASON: dict[int, str] = {
    1: 'winter', 2: 'winter', 3: 'summer', 4: 'summer', 5: 'summer',
    6: 'monsoon', 7: 'monsoon', 8: 'monsoon',
    9: 'festive', 10: 'festive', 11: 'festive', 12: 'winter',
}
MONTH_NAMES: dict[int, str] = {
    1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June',
    7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December',
}
OUTPUT_FIELDS = [
    'instagram_caption', 'facebook_caption', 'whatsapp_message', 'reel_script',
    'story_text', 'ad_copy', 'hashtags', 'cta_options', 'seo_title', 'meta_description',
]


def _content_fallback(reason: str, product_data: dict[str, Any] | None = None) -> dict[str, Any]:
    product_data = product_data or {}
    product_name = product_data.get('name', 'Mynat skincare')
    fallback = build_content_fallback(product_name=product_name, product_description=product_data.get('description', ''), product_price=product_data.get('price', ''), seasonal_angle='Seasonal Ayurvedic skincare', target_audience='Mynat skincare customers', season='festive', cta='Review this draft before publishing.')
    return safe_agent_fallback('content', reason, **fallback, _brand_safety={'brand_safe': True, 'violations': []})


def _call_claude(prompt: str, max_tokens: int = 2048) -> str:
    return call_claude(prompt, max_tokens=max_tokens, system='You are the content specialist for Mynat (mynat.in), an Indian Ayurvedic skincare brand. Write warm, vibrant, relatable marketing content for Indian audiences. Mix English with occasional Hindi phrases when natural. Always return valid JSON exactly as instructed.')


def _parse_json(text: str) -> dict:
    return parse_json_object(text)


def run_content_agent(product_data: dict[str, Any], creator_output: dict[str, Any] | None = None, trend_keywords: list[str] | None = None, public_response: dict[str, Any] | None = None, month: int | None = None) -> dict[str, Any]:
    """Generate complete marketing content for all channels."""
    if not product_data:
        return validate_or_fallback(ContentAgentOutput, {'success': False, 'error': 'No product data provided'}, lambda reason: _content_fallback(reason, product_data))
    month = month or datetime.now().month
    season = MONTH_TO_SEASON.get(month, 'festive')
    month_name = MONTH_NAMES.get(month, 'Unknown')
    creator = creator_output or {}
    review = public_response or {}
    product_name = product_data.get('name', '')
    logger.info(f"[CONTENT AGENT] Starting — Product: '{product_name}', Season: {season}")
    rag_context = require_rag_context(' '.join((str(value) for value in (product_name, product_data.get('category', ''), product_data.get('description', ''), 'Mynat Ayurvedic skincare brand content context') if value)))
    seasonal_angle = creator.get('seasonal_angle') or f'{season.title()} skincare essentials'
    target_audience = creator.get('target_audience') or 'Women 22-35, skincare conscious'
    platform = creator.get('platform', 'instagram')
    content_type = creator.get('content_type', 'post')
    cta_from_creator = creator.get('cta', 'Shop now — link in bio')
    urgency = creator.get('_meta', {}).get('urgency_note', '')
    season_ctx = get_season_context(season, month, trend_keywords)
    audience_profile = get_audience_profile(target_audience)
    review_sentiment = review.get('overall_sentiment', 'positive')
    review_strengths = ', '.join(review.get('marketing_strengths', ['natural ingredients', 'effective Ayurvedic formula'])[:3])
    review_avoid = ', '.join(review.get('avoid_mentioning', [])[:2]) or 'none'
    customer_rating = review.get('star_rating', 4.0)
    trend_str = ', '.join((trend_keywords or []) + season_ctx['seasonal_hashtags'][:5])
    prompt = MASTER_CONTENT_PROMPT.format(product_name=product_name, product_description=(product_data.get('description') or '')[:200], product_price=product_data.get('price', ''), product_category=product_data.get('category', 'skincare'), image_url=product_data.get('image_url', ''), seasonal_angle=seasonal_angle, target_audience=target_audience, platform=platform, content_type=content_type, season=season, month_name=month_name, trend_keywords=trend_str, season_theme=season_ctx['theme'], review_sentiment=review_sentiment, review_strengths=review_strengths, review_avoid=review_avoid, customer_rating=customer_rating, urgency_note=f'\nURGENCY NOTE: {urgency}' if urgency else '')
    logger.info('[CONTENT AGENT] Calling Claude for all content formats...')
    raw = _call_claude(prompt, max_tokens=2048)

    if is_queue_sentinel(raw):
        import json as _json
        sentinel = _json.loads(raw)
        logger.info('[CONTENT AGENT] CLAUDE_APP_MODE active — prompt queued, returning pending status')
        return {
            'success': False,
            'status': 'pending_claude_generation',
            'prompt_id': sentinel.get('prompt_id'),
            'prompt_file': sentinel.get('prompt_file'),
            'product_id': product_data.get('id') or product_data.get('product_id'),
            'product_name': product_name,
            'message': ('Prompt saved to data/pending_prompts/. Paste it into Claude App, then import the JSON response via POST /api/claude-queue/import.'),
            '_meta': {'month': month, 'season': season, 'queued': True},
        }

    content = _parse_json(raw)
    used_fallback = False
    if not content or not content.get('instagram_caption'):
        logger.warning('[CONTENT AGENT] Claude returned empty/invalid — using fallback content')
        content = build_content_fallback(product_name=product_name, product_description=product_data.get('description', ''), product_price=product_data.get('price', ''), seasonal_angle=seasonal_angle, target_audience=target_audience, season=season, cta=cta_from_creator)
        used_fallback = True
    for field in OUTPUT_FIELDS:
        if field not in content:
            content[field] = [] if field in ('hashtags', 'cta_options') else {}
    content = apply_brand_safety(content)
    variants = _build_variants(content, product_name, seasonal_angle, cta_from_creator)
    selected_variant = max(variants, key=lambda item: item['total_score']) if variants else {}
    output = {'success': True, **{k: content[k] for k in OUTPUT_FIELDS if k in content}, '_brand_safety': content.get('_brand_safety', {'brand_safe': True, 'violations': []}), 'variants': variants, 'selected_variant': selected_variant, 'hook_score': selected_variant.get('hook_score', 0), 'clarity_score': selected_variant.get('clarity_score', 0), 'conversion_score': selected_variant.get('conversion_score', 0), 'brand_score': selected_variant.get('brand_score', 0), '_meta': {'month': month, 'month_name': month_name, 'season': season, 'seasonal_angle': seasonal_angle, 'target_audience': target_audience, 'audience_segment': audience_profile['detected_segment'], 'audience_language_mix': audience_profile['language_mix'], 'review_sentiment': review_sentiment, 'customer_rating': customer_rating, 'trend_keywords': trend_keywords or [], 'fallback_used': used_fallback, 'confidence': rag_context['confidence'], 'context_used': rag_context['context_used'], 'sources': rag_context['sources'], 'rag_required': True, 'rag_available': rag_context['available'], 'rag_error': rag_context['error']}}
    logger.info(f"[CONTENT AGENT] Done — brand_safe={output['_brand_safety']['brand_safe']}, fallback={used_fallback}")
    return validate_or_fallback(ContentAgentOutput, output, lambda reason: _content_fallback(reason, product_data), retry_factory=lambda failed: {**failed, 'success': bool(failed.get('instagram_caption'))})


def _build_variants(content: dict[str, Any], product_name: str, seasonal_angle: str, cta: str) -> list[dict[str, Any]]:
    base_caption = content.get('instagram_caption', '')
    hashtags = content.get('hashtags', [])
    templates = [
        ('hook_first', f'{product_name}: {seasonal_angle}. {base_caption} {cta}'),
        ('story_first', f'Your skincare ritual deserves a natural upgrade. {base_caption} {cta}'),
        ('benefit_first', f'Natural Ayurvedic care, made easy. {base_caption} {cta}'),
    ]
    variants = []
    for name, caption in templates:
        hook_score = min(100, 50 + (20 if product_name.lower() in caption.lower() else 0) + (10 if len(caption.split()) < 90 else 0))
        clarity_score = min(100, 60 + (15 if cta.lower().split()[0] in caption.lower() else 0))
        conversion_score = min(100, 55 + (20 if any((word in caption.lower() for word in ['shop', 'try', 'review'])) else 0))
        brand_score = min(100, 60 + (20 if any((word in caption.lower() for word in ['ayurvedic', 'natural', 'skincare'])) else 0))
        total_score = round((hook_score + clarity_score + conversion_score + brand_score) / 4, 2)
        variants.append({'name': name, 'caption': caption.strip(), 'hashtags': hashtags, 'hook_score': hook_score, 'clarity_score': clarity_score, 'conversion_score': conversion_score, 'brand_score': brand_score, 'total_score': total_score})
    return variants
