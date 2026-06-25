"""
Verifier Agent — flat module (merged from agents/verifier_agent/ package).
Contains models, prompts, tools, and the main run_verifier_agent function.
"""
from __future__ import annotations

# ── verifier_agent/models.py ──────────────────────────────────────────────────

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field


class VerifierInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    product: dict[str, Any] = Field(default_factory=dict)
    creator_output: dict[str, Any] = Field(default_factory=dict)
    content_output: dict[str, Any] = Field(default_factory=dict)
    canva_output: dict[str, Any] = Field(default_factory=dict)
    seo_output: dict[str, Any] = Field(default_factory=dict)
    campaign_metadata: dict[str, Any] = Field(default_factory=dict)
    campaign_type: Literal["post", "ad", "video"] = "post"
    platform: Literal["instagram", "facebook", "linkedin", "whatsapp", "email"] = "instagram"
    brand_theme: dict[str, Any] = Field(default_factory=dict)
    seasonal_angle: str = ""
    target_audience: str = ""
    approval_policy: Literal["human_required", "AUTO_VERIFIED"] = "human_required"


class VerificationIssue(BaseModel):
    category: str
    message: str
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class RebuiltCampaign(BaseModel):
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    cta: str = ""
    design_brief: dict[str, Any] = Field(default_factory=dict)
    storyboard: list[dict[str, Any]] = Field(default_factory=list)
    canva_payload: dict[str, Any] = Field(default_factory=dict)
    video_payload: dict[str, Any] = Field(default_factory=dict)
    preview_asset: str = ""


class VerifiedPostOutput(BaseModel):
    post_type: Literal["image", "short_video_ad"]
    caption: str = ""
    hashtags: list[str] = Field(default_factory=list)
    design_brief: dict[str, Any] = Field(default_factory=dict)
    canva_payload: dict[str, Any] = Field(default_factory=dict)
    preview_asset: str = ""
    status: Literal["awaiting_human_approval"] = "awaiting_human_approval"


class VerifiedVideoOutput(VerifiedPostOutput):
    post_type: Literal["short_video_ad"] = "short_video_ad"
    duration_seconds: int = Field(default=15, ge=10, le=20)
    storyboard: list[dict[str, Any]] = Field(default_factory=list)
    video_payload: dict[str, Any] = Field(default_factory=dict)


# ── verifier_agent/prompts.py ─────────────────────────────────────────────────

VERIFIER_SYSTEM_PROMPT = """
You are Mynat's final campaign verifier. You are strict, conservative, and
never publish. Validate strategy/content/design alignment, product truth,
platform suitability, and safety. Return JSON only.

Current mode is human approval only:
Verifier Agent -> Email notification -> Human approval -> Draft ready.
Do not auto-publish and do not call live social APIs.

Statuses allowed:
approved, rejected, needs_human_review, rebuild_required.

Reject unsafe medical, disease cure, guaranteed result, exaggerated before/after,
misleading discount, or unsupported doctor/clinical approval claims.
"""

REBUILD_PROMPT = """
Rebuild this Mynat campaign draft so it matches the approved strategy.
Keep claims factual, avoid medical guarantees, and return draft-only JSON.

For image posts return caption, hashtags, CTA, design_brief, canva_payload,
preview_asset, and status=awaiting_human_approval.

For ads/videos return a 10-20 second storyboard with hook in first 2 seconds,
product visible early, on-screen text, voiceover, CTA, video_payload, and
status=awaiting_human_approval.
"""


# ── verifier_agent/tools.py ───────────────────────────────────────────────────

import re

UNSAFE_CLAIM_PATTERNS = [
    r"\bcures?\b",
    r"\bpermanent(?:ly)?\b",
    r"\bguarantee(?:d|s)?\b",
    r"\b100%\s*(?:cure|result|guarantee)\b",
    r"\b(?:fake|false|misleading)\s+discount\b",
    r"\bdoctor approved\b",
    r"\bclinically proven\b",
    r"\bdisease cure\b",
    r"\b(?:treats?|prevents?)\s+(?:disease|eczema|psoriasis|infection|diabetes)\b",
    r"\bhair growth in\s*\d+\s*days\b",
    r"\bbefore\s*/?\s*after\b",
    r"\bmiracle\b",
    r"\binstant(?:ly)?\b",
    r"\bno side effects\b",
    r"\bfda approved\b",
    r"\bdermatologist guaranteed\b",
    r"\b(?:heal|heals|healing)\s+(?:eczema|psoriasis|infection|diabetes|disease)\b",
]

FALSE_CLAIM_PATTERNS = [
    r"\b(?:best|number\s*1|#1)\s+in\s+(?:india|world|market)\b",
    r"\bonly\s+brand\b",
    r"\bcertified\s+organic\b",
    r"\bgovernment\s+approved\b",
]

MISLEADING_DISCOUNT_PATTERNS = [
    r"\b(?:free|0)\s*(?:rupees|rs|inr|₹)\b",
    r"\b(?:90|95|99|100)%\s*off\b",
    r"\blimited\s+time\b.*\bforever\b",
    r"\bprice\s+guaranteed\b",
]

SPAM_PATTERNS = [
    r"(?:!!!|\?\?\?)",
    r"\b(?:buy now|shop now|click here)\b.*\b(?:buy now|shop now|click here)\b",
    r"(?:🔥|😍|💥|✨){3,}",
    r"\bfree free\b",
]

UNSAFE_LANGUAGE_PATTERNS = [
    r"\b(?:hate|idiot|stupid|ugly|shame)\b",
    r"\b(?:fairer|whitening|skin lightening)\b",
]

BRAND_WORDS = {"ayurvedic", "natural", "wellness", "glow", "skin", "mynat", "herbal", "botanical"}
PREMIUM_VISUAL_WORDS = {
    "clean", "premium", "vibrant", "attractive", "readable", "mobile",
    "product", "high contrast", "visibility", "cta", "typography",
}


def text_blob(*items: Any) -> str:
    return " ".join(str(item or "") for item in items).lower().strip()


def find_unsafe_claims(*texts: Any) -> list[str]:
    blob = text_blob(*texts)
    issues = []
    for pattern in UNSAFE_CLAIM_PATTERNS + FALSE_CLAIM_PATTERNS + MISLEADING_DISCOUNT_PATTERNS + SPAM_PATTERNS + UNSAFE_LANGUAGE_PATTERNS:
        if re.search(pattern, blob, flags=re.IGNORECASE):
            issues.append(f"Safety/compliance issue matched: {pattern}")
    return issues


def check_creator_content_match(product: dict[str, Any], creator_output: dict[str, Any], content_output: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    product_name = str(product.get("name") or product.get("product_name") or creator_output.get("recommended_product") or "")
    primary_caption = text_blob(content_output.get("instagram_caption") or content_output.get("facebook_caption") or content_output.get("ad_copy"))
    content_blob = text_blob(content_output.get("instagram_caption"), content_output.get("facebook_caption"), content_output.get("whatsapp_message"), " ".join(content_output.get("hashtags", []) or []))
    creator_angle = str(creator_output.get("seasonal_angle", "")).lower()
    creator_cta = str(creator_output.get("cta", "")).lower()
    creator_audience = str(creator_output.get("target_audience", "")).lower()
    claimed_facts = text_blob(product.get("description"), product.get("short_description"), product.get("category"), " ".join(product.get("tags", []) or []), product.get("specifications"))

    if product_name and product_name.lower() not in primary_caption:
        issues.append("Primary caption does not clearly mention the selected product.")
    if creator_angle and not _has_overlap(creator_angle, primary_caption):
        issues.append("Content does not reflect Creator Agent seasonal/campaign angle.")
    if creator_cta and not _has_overlap(creator_cta, primary_caption):
        issues.append("Content CTA does not match Creator Agent objective.")
    if creator_audience and not _has_overlap(creator_audience, content_blob):
        issues.append("Content target audience does not match Creator Agent strategy.")
    if claimed_facts and _mentions_unsupported_content(content_blob, claimed_facts):
        issues.append("Content appears to make product claims not supported by product facts.")
    return not issues, issues


def check_audience_alignment(creator_output: dict[str, Any], content_output: dict[str, Any], campaign_metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    audience = text_blob(creator_output.get("target_audience"), campaign_metadata.get("target_audience"), campaign_metadata.get("audience"))
    content = text_blob(content_output)
    if not audience:
        return False, ["Target audience is missing from campaign strategy/metadata."]
    if not _has_overlap(audience, content):
        return False, ["Content does not speak to the selected audience."]
    return True, []


def check_cta_alignment(creator_output: dict[str, Any], content_output: dict[str, Any], campaign_metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    expected_cta = text_blob(creator_output.get("cta"), campaign_metadata.get("cta"))
    content = text_blob(content_output)
    if not expected_cta:
        return False, ["CTA is missing from Creator Strategy or campaign metadata."]
    if not _has_overlap(expected_cta, content):
        return False, ["CTA in content does not align with approved strategy."]
    return True, []


def check_campaign_alignment(creator_output: dict[str, Any], content_output: dict[str, Any], campaign_metadata: dict[str, Any]) -> tuple[bool, list[str]]:
    objective = text_blob(creator_output.get("campaign_goal"), creator_output.get("campaign_objective"), campaign_metadata.get("campaign_goal"), campaign_metadata.get("objective"))
    angle = text_blob(creator_output.get("seasonal_angle"), creator_output.get("campaign_angle"), campaign_metadata.get("campaign_angle"), campaign_metadata.get("seasonal_angle"))
    content = text_blob(content_output)
    issues = []
    if objective and not _has_overlap(objective, content):
        issues.append("Content does not align with campaign objective.")
    if angle and not _has_overlap(angle, content):
        issues.append("Content does not align with campaign angle.")
    if not objective and not angle:
        issues.append("Campaign objective/angle metadata is missing.")
    return not issues, issues


def check_seo_alignment(seo_output: dict[str, Any], content_output: dict[str, Any], platform: str) -> tuple[bool, list[str]]:
    if platform not in {"instagram", "facebook", "linkedin"}:
        return True, []
    keywords = []
    for key in ("primary_keywords", "keywords", "keyword_opportunities", "content_opportunities"):
        value = seo_output.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    keywords.extend(str(v) for v in item.values() if isinstance(v, str))
                else:
                    keywords.append(str(item))
        elif isinstance(value, str):
            keywords.append(value)
    if not keywords:
        return True, []
    content = text_blob(content_output)
    if not any(_has_overlap(keyword, content) for keyword in keywords[:10]):
        return False, ["SEO keywords/opportunities are not reflected in content output."]
    return True, []


def score_verification_dimensions(*, unsafe: list[str], creator_issues: list[str], theme_issues: list[str], platform_issues: list[str], audience_issues: list[str], cta_issues: list[str], campaign_issues: list[str], seo_issues: list[str], low_confidence: bool) -> dict[str, int]:
    visual_score = _score_from_issues(theme_issues, 20)
    audience_score = _score_from_issues(audience_issues, 25)
    cta_score = _score_from_issues(cta_issues, 25)
    seo_score = _score_from_issues(seo_issues, 20)
    campaign_score = _score_from_issues(creator_issues + campaign_issues + platform_issues, 15)
    brand_score = _score_from_issues(theme_issues + unsafe, 18)
    quality_score = _score_from_issues(unsafe + creator_issues + theme_issues + platform_issues + audience_issues + cta_issues + campaign_issues + seo_issues, 10)
    if low_confidence:
        quality_score = max(0, quality_score - 20)
        campaign_score = max(0, campaign_score - 15)
    return {"quality_score": quality_score, "brand_score": brand_score, "campaign_alignment_score": campaign_score, "audience_alignment_score": audience_score, "visual_alignment_score": visual_score, "cta_alignment_score": cta_score, "seo_alignment_score": seo_score}


def check_theme_match(canva_output: dict[str, Any], brand_theme: dict[str, Any], seasonal_angle: str) -> tuple[bool, list[str]]:
    blob = text_blob(canva_output, brand_theme, seasonal_angle)
    issues = []
    if not any(word in blob for word in BRAND_WORDS):
        issues.append("Design brief does not strongly match Mynat natural/Ayurvedic wellness theme.")
    if not any(word in blob for word in PREMIUM_VISUAL_WORDS):
        issues.append("Design brief does not prove vibrant, clean, premium, mobile-friendly visual direction.")
    if "cta" not in blob:
        issues.append("CTA placement is missing from design direction.")
    if "product" not in blob and "hero" not in blob:
        issues.append("Product visibility is missing from design direction.")
    return not issues, issues


def check_platform(platform: str, campaign_type: str, content_output: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    caption = str(content_output.get("instagram_caption") or content_output.get("facebook_caption") or "")
    hashtags = content_output.get("hashtags") or []

    if platform == "instagram":
        if len(caption) > 2200:
            issues.append("Instagram caption exceeds platform limit.")
        if not 1 <= len(hashtags) <= 20:
            issues.append("Instagram should use 1-20 relevant hashtags.")
        if caption and len(caption.split()) > 160:
            issues.append("Instagram caption should stay short and visual-first.")
    elif platform == "linkedin":
        if len(hashtags) > 5:
            issues.append("LinkedIn should use fewer, professional hashtags.")
        if any(symbol in caption for symbol in ["🔥", "😍", "💥"]):
            issues.append("LinkedIn tone should be more professional.")
    elif platform == "facebook":
        if len(caption) > 5000:
            issues.append("Facebook caption is too long for readable community posting.")

    if campaign_type in {"ad", "video"}:
        if len(caption) > 700:
            issues.append("Short video ad caption should be concise.")
        ad_copy = content_output.get("ad_copy") or {}
        if isinstance(ad_copy, dict):
            ad_blob = text_blob(ad_copy, content_output.get("reel_script"))
        else:
            ad_blob = text_blob(ad_copy, content_output.get("reel_script"))
        if not any(word in ad_blob or word in caption.lower() for word in ("hook", "cta", "shop", "review", "try")):
            issues.append("Short video ad needs a clear hook and CTA.")
    return not issues, issues


def rebuild_campaign_content(*, creator_output: dict[str, Any], product: dict[str, Any], brand_theme: dict[str, Any], campaign_type: str, platform: str) -> dict[str, Any]:
    product_name = product.get("name") or product.get("product_name") or creator_output.get("recommended_product") or "Mynat skincare"
    angle = creator_output.get("seasonal_angle") or "Natural Ayurvedic skincare glow"
    audience = creator_output.get("target_audience") or "Mynat skincare customers"
    cta = creator_output.get("cta") or "Review this draft and shop Mynat when ready."
    hashtags = _platform_hashtags(platform, product_name, angle)
    caption = (f"{product_name}: {angle}. Crafted for {audience} with Mynat's natural wellness theme. {cta}")
    design_brief = {"visual_style": "vibrant, attractive, clean, premium, natural Ayurvedic wellness", "layout": "product-focused hero image with high product visibility and generous whitespace", "colors": brand_theme.get("colors") or ["warm gold", "leaf green", "soft ivory"], "typography": "readable premium headline with clean supporting text, no overcrowding", "cta_placement": "bottom-right, high contrast, mobile-readable", "background_style": "natural ingredients and soft seasonal texture", "product_visibility": "hero product visible early and unobstructed", "image_placement": "center or lower-third product with clear label visibility", "mobile_safety": "all text fits 9:16 and 1:1 crops with high contrast", "status": "draft"}
    canva_payload = {"mock": True, "status": "draft", "platform": platform, "campaign_type": campaign_type, "format": "1080x1080 image post" if campaign_type == "post" else "1080x1920 short video", "design_brief": design_brief, "preview_asset": f"mock://mynat/{platform}/{campaign_type}/{_slug(product_name)}"}
    rebuilt = {"caption": caption, "hashtags": hashtags, "cta": cta, "design_brief": design_brief, "canva_payload": canva_payload, "preview_asset": canva_payload["preview_asset"]}
    if campaign_type in {"ad", "video"}:
        rebuilt["storyboard"] = build_short_video_storyboard(product_name, angle, cta)
        rebuilt["video_payload"] = {"mock": True, "duration_seconds": 15, "aspect_ratio": "9:16", "status": "draft", "platform": platform, "scenes": rebuilt["storyboard"], "preview_asset": canva_payload["preview_asset"]}
    return rebuilt


def build_short_video_storyboard(product_name: str, angle: str, cta: str) -> list[dict[str, str]]:
    return [
        {"scene": 1, "duration": "0-3s", "visual": f"Bright product close-up of {product_name} with natural ingredients.", "on_screen_text": "Glow starts naturally", "voiceover": f"Meet {product_name} from Mynat."},
        {"scene": 2, "duration": "3-9s", "visual": f"Show texture, ingredient cues, and seasonal mood: {angle}.", "on_screen_text": "Ayurvedic wellness care", "voiceover": "A clean, natural routine made for everyday skincare."},
        {"scene": 3, "duration": "9-15s", "visual": "Product hero shot with Mynat branding and CTA.", "on_screen_text": "Review draft before publishing", "voiceover": cta},
    ]


def _platform_hashtags(platform: str, product_name: str, angle: str) -> list[str]:
    base = ["#mynat", "#ayurveda", "#skincare", "#naturalbeauty", "#wellness"]
    if platform == "linkedin":
        return ["#Mynat", "#Ayurveda", "#Wellness"]
    if "summer" in angle.lower():
        base.append("#summerskincare")
    token = re.sub(r"[^a-z0-9]", "", product_name.lower())
    if token:
        base.append(f"#{token[:24]}")
    return base[:12]


def _has_overlap(source: str, target: str) -> bool:
    words = {word for word in re.findall(r"[a-z0-9]+", source.lower()) if len(word) > 3}
    return bool(words and words.intersection(set(re.findall(r"[a-z0-9]+", target.lower()))))


def _score_from_issues(issues: list[str], penalty: int) -> int:
    return max(0, min(100, 100 - len(issues) * penalty))


def _mentions_unsupported_content(content_blob: str, fact_blob: str) -> bool:
    sensitive_claim_words = {"antiaging", "acne", "pigmentation", "hairfall", "growth", "spf", "organic"}
    content_words = _claim_tokens(content_blob)
    fact_words = _claim_tokens(fact_blob)
    return bool((content_words & sensitive_claim_words) - fact_words)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:48] or "campaign"


def _claim_tokens(value: str) -> set[str]:
    words = set(re.findall(r"[a-z0-9]+", value.lower()))
    compact = re.sub(r"[^a-z0-9]+", "", value.lower())
    if "hairfall" in compact:
        words.add("hairfall")
    if "antiaging" in compact or "antiageing" in compact:
        words.add("antiaging")
    return words


# ── verifier_agent/agent.py ───────────────────────────────────────────────────

from agents.agent_schemas import VerifierAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback


def run_verifier_agent(*, product: dict[str, Any], creator_output: dict[str, Any], content_output: dict[str, Any], canva_output: dict[str, Any] | None = None, seo_output: dict[str, Any] | None = None, campaign_type: str = 'post', platform: str = 'instagram', brand_theme: dict[str, Any] | None = None, seasonal_angle: str = '', target_audience: str = '', approval_policy: str = 'human_required') -> dict[str, Any]:
    """Verify campaign alignment, safety, platform fit, and rebuild if needed."""
    try:
        data = VerifierInput.model_validate({'product': product or {}, 'creator_output': creator_output or {}, 'content_output': content_output or {}, 'canva_output': canva_output or {}, 'seo_output': seo_output or {}, 'campaign_metadata': {**(creator_output.get('campaign_metadata', {}) if isinstance(creator_output.get('campaign_metadata'), dict) else {}), 'campaign_type': campaign_type, 'platform': platform, 'seasonal_angle': seasonal_angle or creator_output.get('seasonal_angle', ''), 'target_audience': target_audience or creator_output.get('target_audience', '')}, 'campaign_type': campaign_type, 'platform': platform, 'brand_theme': brand_theme or {}, 'seasonal_angle': seasonal_angle or creator_output.get('seasonal_angle', ''), 'target_audience': target_audience or creator_output.get('target_audience', ''), 'approval_policy': approval_policy})
    except Exception as exc:
        return _fallback(str(exc))

    content_text = [data.content_output.get('instagram_caption'), data.content_output.get('facebook_caption'), data.content_output.get('whatsapp_message'), data.content_output.get('ad_copy'), data.content_output.get('reel_script'), data.content_output.get('story_text'), ' '.join(data.content_output.get('hashtags', []) or [])]
    unsafe = find_unsafe_claims(*content_text)
    creator_match, creator_issues = check_creator_content_match(data.product, data.creator_output, data.content_output)
    theme_match, theme_issues = check_theme_match(data.canva_output or data.creator_output.get('canva_design_brief', {}), data.brand_theme, data.seasonal_angle)
    platform_match, platform_issues = check_platform(data.platform, data.campaign_type, data.content_output)
    audience_match, audience_issues = check_audience_alignment(data.creator_output, data.content_output, data.campaign_metadata)
    cta_match, cta_issues = check_cta_alignment(data.creator_output, data.content_output, data.campaign_metadata)
    campaign_match, campaign_issues = check_campaign_alignment(data.creator_output, data.content_output, data.campaign_metadata)
    seo_match, seo_issues = check_seo_alignment(data.seo_output, data.content_output, data.platform)
    dimension_scores = score_verification_dimensions(unsafe=unsafe, creator_issues=creator_issues, theme_issues=theme_issues, platform_issues=platform_issues, audience_issues=audience_issues, cta_issues=cta_issues, campaign_issues=campaign_issues, seo_issues=seo_issues, low_confidence=_low_confidence(data))
    issues = unsafe + creator_issues + theme_issues + platform_issues + audience_issues + cta_issues + campaign_issues + seo_issues
    required_fixes = _required_fixes(unsafe, creator_issues, theme_issues, platform_issues, audience_issues, cta_issues, campaign_issues, seo_issues)
    rebuild_required = bool(creator_issues or theme_issues or platform_issues or audience_issues or cta_issues or campaign_issues or seo_issues)
    rebuilt = {}
    if rebuild_required:
        rebuilt = rebuild_campaign_content(creator_output=data.creator_output, product=data.product, brand_theme=data.brand_theme, campaign_type=data.campaign_type, platform=data.platform)
    risk_score = _risk_score(unsafe=unsafe, creator_issues=creator_issues, theme_issues=theme_issues, platform_issues=platform_issues, audience_issues=audience_issues, cta_issues=cta_issues, campaign_issues=campaign_issues, seo_issues=seo_issues, low_confidence=_low_confidence(data))
    safe_to_publish = not unsafe and creator_match and theme_match and platform_match and audience_match and cta_match and campaign_match and seo_match and (risk_score <= 20) and (min(dimension_scores.values()) >= 70)
    if unsafe:
        verifier_status = 'rejected'
        reason = 'Unsafe medical, guaranteed, or unsupported claim detected.'
    elif _low_confidence(data):
        verifier_status = 'needs_human_review'
        reason = 'Verifier confidence is low because upstream context is incomplete.'
    elif rebuild_required:
        verifier_status = 'needs_revision'
        reason = 'Campaign content/design/platform output did not fully match approved strategy.'
    else:
        verifier_status = 'approved'
        reason = 'Campaign is verifier-safe and ready for human approval.'
    post_type = 'short_video_ad' if data.campaign_type in {'ad', 'video'} else 'image'
    if not rebuilt:
        rebuilt = _draft_from_existing(data, post_type)
    if post_type == 'short_video_ad' and 'storyboard' not in rebuilt:
        product_name = data.product.get('name') or data.creator_output.get('recommended_product', 'Mynat product')
        rebuilt['storyboard'] = build_short_video_storyboard(product_name, data.seasonal_angle or data.creator_output.get('seasonal_angle', 'Natural skincare'), data.creator_output.get('cta', 'Review this draft before publishing.'))
        rebuilt['video_payload'] = {'mock': True, 'duration_seconds': 15, 'status': 'draft'}
        rebuilt.setdefault('preview_asset', _preview_asset(data.canva_output, rebuilt, post_type))
    preview_asset = _preview_asset(data.canva_output, rebuilt, post_type)
    design_brief = rebuilt.get('design_brief', data.canva_output or {})
    canva_payload = rebuilt.get('canva_payload') or data.canva_output.get('canva_payload', {})
    rebuilt_content = _build_rebuilt_output(post_type=post_type, caption=rebuilt.get('caption', data.content_output.get('instagram_caption', '')), hashtags=rebuilt.get('hashtags', data.content_output.get('hashtags', [])), cta=rebuilt.get('cta', data.creator_output.get('cta', '')), design_brief=design_brief, canva_payload=canva_payload, preview_asset=preview_asset, storyboard=rebuilt.get('storyboard', []), video_payload=rebuilt.get('video_payload', {}))
    output = {'success': True, 'verifier_status': verifier_status, 'approval_required': True, 'creator_content_match': creator_match, 'theme_match': theme_match, 'platform_match': platform_match, 'audience_match': audience_match, 'cta_match': cta_match, 'campaign_match': campaign_match, 'seo_match': seo_match, 'safe_to_publish': safe_to_publish, 'confidence_score': 30 if _low_confidence(data) else max(0, 100 - risk_score), 'risk_score': risk_score, **dimension_scores, 'severity': _severity(risk_score, unsafe), 'issues_found': issues, 'required_fixes': required_fixes, 'rebuilt_content': rebuilt_content, 'rebuilt_design_brief': design_brief, 'post_type': post_type, 'preview_asset': preview_asset, 'approval_status': 'pending', 'reason': reason, '_meta': {'fallback_used': False, 'confidence': 'medium' if not _low_confidence(data) else 'low', 'approval_policy': data.approval_policy, 'future_safe_to_publish': safe_to_publish, 'current_mode': 'human_required'}}
    return validate_or_fallback(VerifierAgentOutput, output, _fallback, retry_factory=lambda failed: {**failed, 'success': True, 'approval_status': 'pending'})


def _risk_score(*, unsafe: list[str], creator_issues: list[str], theme_issues: list[str], platform_issues: list[str], audience_issues: list[str], cta_issues: list[str], campaign_issues: list[str], seo_issues: list[str], low_confidence: bool) -> int:
    score = len(unsafe) * 45 + len(creator_issues) * 15 + len(theme_issues) * 10 + len(platform_issues) * 10 + len(audience_issues) * 12 + len(cta_issues) * 12 + len(campaign_issues) * 12 + len(seo_issues) * 8
    if low_confidence:
        score += 20
    return min(100, score)


def _severity(risk_score: int, unsafe: list[str]) -> str:
    if unsafe or risk_score >= 80:
        return 'CRITICAL'
    if risk_score >= 50:
        return 'HIGH'
    if risk_score >= 25:
        return 'MEDIUM'
    return 'LOW'


def _required_fixes(*issue_groups: list[str]) -> list[str]:
    fixes = []
    for issue in [item for group in issue_groups for item in group]:
        if 'claim' in issue.lower():
            fixes.append('Remove unsafe or unsupported claims.')
        elif 'design' in issue.lower() or 'cta placement' in issue.lower() or 'product visibility' in issue.lower():
            fixes.append('Rebuild Canva design brief with Mynat premium natural theme.')
        elif 'product' in issue.lower() or 'angle' in issue.lower() or 'cta' in issue.lower():
            fixes.append('Rebuild caption and hashtags from Creator Agent strategy.')
        else:
            fixes.append('Adjust platform formatting and tone.')
    return sorted(set(fixes))


def _low_confidence(data: VerifierInput) -> bool:
    return not data.product or not data.creator_output or (not data.content_output)


def _draft_from_existing(data: VerifierInput, post_type: str) -> dict[str, Any]:
    caption = data.content_output.get('instagram_caption') or data.content_output.get('facebook_caption') or str(data.content_output.get('ad_copy') or '')
    canva_payload = data.canva_output.get('canva_payload', {})
    return {'caption': caption, 'hashtags': data.content_output.get('hashtags', []), 'cta': data.creator_output.get('cta', ''), 'design_brief': data.canva_output or data.creator_output.get('canva_design_brief', {}), 'canva_payload': canva_payload, 'preview_asset': _preview_asset(data.canva_output, {}, post_type)}


def _build_rebuilt_output(*, post_type: str, caption: str, hashtags: list[str], cta: str, design_brief: dict[str, Any], canva_payload: dict[str, Any], preview_asset: str, storyboard: list[dict[str, Any]], video_payload: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {'post_type': post_type, 'caption': caption, 'hashtags': hashtags, 'cta': cta, 'design_brief': design_brief, 'canva_payload': canva_payload, 'preview_asset': preview_asset, 'status': 'awaiting_human_approval'}
    if post_type == 'short_video_ad':
        output.update({'duration_seconds': int(video_payload.get('duration_seconds', 15) or 15), 'storyboard': storyboard, 'video_payload': video_payload})
    return output


def _preview_asset(canva_output: dict[str, Any], rebuilt: dict[str, Any], post_type: str) -> str:
    if rebuilt.get('preview_asset'):
        return str(rebuilt['preview_asset'])
    if rebuilt.get('video_payload', {}).get('preview_asset'):
        return str(rebuilt['video_payload']['preview_asset'])
    if rebuilt.get('canva_payload', {}).get('preview_asset'):
        return str(rebuilt['canva_payload']['preview_asset'])
    if canva_output.get('preview_asset'):
        return str(canva_output['preview_asset'])
    if canva_output.get('canva_payload', {}).get('preview_asset'):
        return str(canva_output['canva_payload']['preview_asset'])
    return f'mock://mynat/{post_type}/awaiting-human-approval'


def _fallback(reason: str) -> dict[str, Any]:
    return safe_agent_fallback('verifier', reason, verifier_status='needs_human_review', approval_status='pending', creator_content_match=False, theme_match=False, platform_match=False, safe_to_publish=False, risk_score=100, issues_found=[reason], required_fixes=['Human review required before any publishing action.'], rebuilt_content={}, rebuilt_design_brief={}, post_type='image', preview_asset='', reason='Verifier fallback requires human review.')
