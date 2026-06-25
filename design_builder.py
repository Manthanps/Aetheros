"""
Canva Agent — flat module (merged from agents/canva_agent/ package).
Mynat's visual design brain: generates complete visual design packages.
"""
from __future__ import annotations

# ── canva_agent/prompts.py ────────────────────────────────────────────────────

POST_DESIGN_PROMPT = """You are a visual art director for Mynat — an Ayurvedic skincare brand from India.

Your task: Write the creative text and image direction for a social media post design.

Brand personality: Natural, warm, trustworthy, celebratory of Indian beauty traditions.
Color anchors: Gold (#C8872A), Cream (#FFF5E1), Forest Green (#2D4A27).

---

PRODUCT: {product_name}
Description: {product_description}
Price: ₹{product_price}
Category: {product_category}

CAMPAIGN CONTEXT:
Platform: {platform}
Season: {season}
Seasonal angle: {seasonal_angle}
Target audience: {target_audience}
Campaign type: {campaign_type}
Visual mood: {visual_mood}

CAPTION (already written — design must match this):
{instagram_caption}

---

Return ONLY valid JSON. No extra text, no markdown.

{{
  "headline_text": "Short punchy headline for the design (max 8 words, for the image itself — NOT the caption)",
  "subtext": "One supporting line below the headline (max 12 words)",
  "image_concept": "Detailed description of the ideal hero photo for this design",
  "image_concept_alternative": "Alternative photo concept if first is not available",
  "background_treatment": "How to treat the background: solid color | gradient | lifestyle image | texture",
  "color_mood": "2-3 adjectives describing the visual feel (e.g. warm golden glow)",
  "text_overlay_style": "How the text sits on the image: bottom overlay | top banner | center bold | side panel",
  "visual_element_suggestions": ["Ayurvedic herb or ingredient as prop", "second visual element", "third"],
  "design_tip": "One practical tip for the designer to make this design stand out"
}}"""


CAROUSEL_PROMPT = """You are a visual art director for Mynat — an Ayurvedic skincare brand from India.

Your task: Write the creative text and image direction for each slide of a 6-slide Instagram carousel.

The carousel should tell a complete story: Hook → Problem → Solution → Benefits → Proof → CTA.
Keep each slide's text SHORT — people swipe fast.

---

PRODUCT: {product_name}
Description: {product_description}
Price: ₹{product_price}

CAMPAIGN CONTEXT:
Season: {season}
Seasonal angle: {seasonal_angle}
Target audience: {target_audience}
Key benefits: {key_benefits}
CTA: {cta}

---

Return ONLY valid JSON. Exactly 6 slides.

{{
  "carousel_title": "Series title (shown as first slide top text, max 6 words)",
  "slides": [
    {{
      "slide": 1,
      "type": "hook",
      "headline": "Stop-the-scroll headline (max 6 words, bold, punchy)",
      "subtext": "Supporting line (max 8 words)",
      "image_concept": "Specific photo concept for this slide",
      "background_color": "hex code or color name",
      "text_color": "hex code or color name",
      "swipe_cue": "Visual or text element that prompts swiping (e.g. 'Swipe to see →')"
    }},
    {{
      "slide": 2,
      "type": "problem",
      "headline": "Relatable problem statement (max 8 words, question format)",
      "subtext": "Empathetic acknowledgement (max 10 words)",
      "image_concept": "Photo concept: shows the problem or pain point visually",
      "background_color": "light neutral",
      "text_color": "dark",
      "swipe_cue": "→ Swipe for the solution"
    }},
    {{
      "slide": 3,
      "type": "product_intro",
      "headline": "Product introduction headline (max 6 words)",
      "subtext": "One-line brand promise",
      "image_concept": "Clean product hero shot description",
      "background_color": "#FFF5E1",
      "text_color": "#C8872A",
      "swipe_cue": "→ See why it works"
    }},
    {{
      "slide": 4,
      "type": "benefits",
      "headline": "Why it works headline",
      "bullets": ["Benefit 1 (max 5 words)", "Benefit 2 (max 5 words)", "Benefit 3 (max 5 words)"],
      "image_concept": "Ingredient or process photo concept",
      "background_color": "light green tint",
      "text_color": "#2D4A27",
      "swipe_cue": "→ See what customers say"
    }},
    {{
      "slide": 5,
      "type": "social_proof",
      "headline": "Customer love headline",
      "quote": "A realistic 1-line customer testimonial (15-20 words)",
      "rating": "5 stars",
      "image_concept": "Happy customer photo or product-in-use shot",
      "background_color": "warm cream",
      "text_color": "#2C2C2C",
      "swipe_cue": "→ Get yours now"
    }},
    {{
      "slide": 6,
      "type": "cta",
      "headline": "Price + urgency headline (include ₹{product_price})",
      "cta_button_text": "Buy Now / Shop Now / Order Today",
      "subtext": "{cta}",
      "image_concept": "Product with brand logo, clean CTA-focused design",
      "background_color": "#C8872A",
      "text_color": "#FFF5E1",
      "swipe_cue": null
    }}
  ]
}}"""


STORY_PROMPT = """You are a visual art director for Mynat — an Ayurvedic skincare brand from India.

Your task: Write creative text and image direction for a 3-slide Instagram Story sequence.

Story format: Hook (3-4s) → Product reveal (4-5s) → CTA (3s).
Each slide must work on its own AND flow naturally to the next.
Text must be large and bold — stories are viewed on small screens.

---

PRODUCT: {product_name}
Price: ₹{product_price}
Key benefit: {key_benefit}

CAMPAIGN CONTEXT:
Season: {season}
Seasonal angle: {seasonal_angle}
Target audience: {target_audience}
CTA: {cta}
Visual mood: {visual_mood}

---

Return ONLY valid JSON. Exactly 3 slides.

{{
  "story_series_hook": "Overarching theme of this 3-slide story (max 5 words)",
  "slides": [
    {{
      "slide": 1,
      "type": "hook",
      "top_text": "Short attention hook — large text at top (max 5 words)",
      "mid_text": "",
      "bottom_text": "Teaser or swipe cue (max 4 words)",
      "image_concept": "Full-bleed image concept — vibrant and immediate",
      "sticker_ideas": ["Interactive sticker suggestion", "optional second sticker"],
      "animation_suggestion": "Subtle animation idea (e.g. fade in, bounce)",
      "color_vibe": "2-3 words"
    }},
    {{
      "slide": 2,
      "type": "product_reveal",
      "top_text": "Product name or category (max 4 words)",
      "mid_text": "Key benefit statement (max 8 words)",
      "bottom_text": "Price with currency — ₹{product_price}",
      "image_concept": "Clean product shot or lifestyle photo description",
      "sticker_ideas": ["Countdown timer if sale", "Link sticker to mynat.in"],
      "animation_suggestion": "Slide in from right or pop scale animation",
      "color_vibe": "cream and gold"
    }},
    {{
      "slide": 3,
      "type": "cta",
      "top_text": "",
      "mid_text": "{cta}",
      "bottom_text": "mynat.in",
      "image_concept": "Brand color background with large CTA and logo",
      "sticker_ideas": ["Link sticker: mynat.in", "DM us sticker"],
      "animation_suggestion": "Pulsing CTA button animation",
      "color_vibe": "gold and cream",
      "swipe_up_label": "Shop Now 🛒"
    }}
  ]
}}"""


REEL_COVER_PROMPT = """You are a visual art director for Mynat — an Ayurvedic skincare brand from India.

Your task: Design a Reel cover thumbnail that stops people on the Instagram profile grid.

The cover must:
- Work as a standalone image (no audio, no motion)
- Have ONE clear bold hook text
- Show the product or a lifestyle shot
- Be readable at profile grid thumbnail size (approx 100x180px)

---

PRODUCT: {product_name}
Description: {product_description}

REEL CONTEXT:
Hook (first 3 seconds): {reel_hook}
Season: {season}
Seasonal angle: {seasonal_angle}
Target audience: {target_audience}
Visual mood: {visual_mood}

---

Return ONLY valid JSON.

{{
  "cover_hook_text": "The main text on the cover — short, bold, curiosity-driving (max 5 words)",
  "cover_sub_text": "{product_name} — shown below hook text, smaller",
  "image_concept": "Specific photo description for the cover — must be high contrast and bold",
  "text_position": "lower_third | center | upper_third",
  "text_style": "How the text looks: bold white on dark overlay | gold on cream | etc.",
  "background_treatment": "How to treat the background image",
  "color_vibe": "2-3 words",
  "grid_tip": "One tip to make this thumbnail stand out on the profile grid",
  "a_b_variant": {{
    "cover_hook_text": "Alternative hook text option",
    "image_concept": "Alternative image concept"
  }}
}}"""


# ── canva_agent/tools.py ──────────────────────────────────────────────────────

from typing import Any

MYNAT_BRAND: dict[str, str] = {
    "gold":         "#C8872A",
    "cream":        "#FFF5E1",
    "forest_green": "#2D4A27",
    "soft_rose":    "#F5C2C7",
    "charcoal":     "#2C2C2C",
    "warm_white":   "#FEFEFE",
}

DESIGN_DIMENSIONS: dict[str, dict] = {
    "instagram_post":     {"width": 1080, "height": 1080, "unit": "px", "dpi": 72,  "aspect": "1:1"},
    "instagram_carousel": {"width": 1080, "height": 1080, "unit": "px", "dpi": 72,  "aspect": "1:1"},
    "instagram_story":    {"width": 1080, "height": 1920, "unit": "px", "dpi": 72,  "aspect": "9:16"},
    "facebook_post":      {"width": 1200, "height": 630,  "unit": "px", "dpi": 72,  "aspect": "1.91:1"},
    "reel_cover":         {"width": 1080, "height": 1920, "unit": "px", "dpi": 72,  "aspect": "9:16"},
    "product_banner":     {"width": 1200, "height": 400,  "unit": "px", "dpi": 96,  "aspect": "3:1"},
}

SEASON_PALETTES: dict[str, dict[str, dict[str, str]]] = {
    "summer": {
        "face_care": {"primary": "#FF8C42", "secondary": "#FFF3E0", "accent": "#2D4A27",  "background": "#FFFAF5", "text": "#2C2C2C", "gradient_from": "#FF8C42", "gradient_to": "#FFD166"},
        "hair_care": {"primary": "#F4A460", "secondary": "#FFF8DC", "accent": "#8B4513",  "background": "#FFFEF5", "text": "#2C2C2C", "gradient_from": "#F4A460", "gradient_to": "#FFDAB9"},
        "body_care": {"primary": "#E8A838", "secondary": "#FFF5E0", "accent": "#1A5C38",  "background": "#FFFFF0", "text": "#2C2C2C", "gradient_from": "#E8A838", "gradient_to": "#FFE47A"},
        "default":   {"primary": "#FF8C42", "secondary": "#FFF5E1", "accent": "#C8872A",  "background": "#FFFAF5", "text": "#2C2C2C", "gradient_from": "#FF8C42", "gradient_to": "#C8872A"},
    },
    "monsoon": {
        "face_care": {"primary": "#4A8C6F", "secondary": "#E8F5E9", "accent": "#C8872A",  "background": "#F0FFF4", "text": "#1A3A2A", "gradient_from": "#4A8C6F", "gradient_to": "#2D4A27"},
        "hair_care": {"primary": "#5B8C5A", "secondary": "#E8F5E9", "accent": "#8B4513",  "background": "#F5FFF5", "text": "#1A3A2A", "gradient_from": "#5B8C5A", "gradient_to": "#2D4A27"},
        "body_care": {"primary": "#3D7A6E", "secondary": "#E0F2F1", "accent": "#C8872A",  "background": "#F0FFFD", "text": "#1A3A2A", "gradient_from": "#3D7A6E", "gradient_to": "#1B5E5A"},
        "default":   {"primary": "#4A8C6F", "secondary": "#E8F5E9", "accent": "#C8872A",  "background": "#F0FFF4", "text": "#1A3A2A", "gradient_from": "#4A8C6F", "gradient_to": "#2D4A27"},
    },
    "winter": {
        "face_care": {"primary": "#C8872A", "secondary": "#FFF5E1", "accent": "#2D4A27",  "background": "#FFFDF5", "text": "#2C2C2C", "gradient_from": "#C8872A", "gradient_to": "#8B5E3C"},
        "hair_care": {"primary": "#8B6C42", "secondary": "#FDF6E3", "accent": "#2D4A27",  "background": "#FFFEF5", "text": "#2C2C2C", "gradient_from": "#8B6C42", "gradient_to": "#5C3A1E"},
        "body_care": {"primary": "#A0785A", "secondary": "#FFF5EA", "accent": "#2D4A27",  "background": "#FFFFF5", "text": "#2C2C2C", "gradient_from": "#A0785A", "gradient_to": "#6B4226"},
        "default":   {"primary": "#C8872A", "secondary": "#FFF5E1", "accent": "#2D4A27",  "background": "#FFFDF5", "text": "#2C2C2C", "gradient_from": "#C8872A", "gradient_to": "#8B5E3C"},
    },
    "festive": {
        "face_care": {"primary": "#D4AF37", "secondary": "#FFF9E6", "accent": "#8B0000",  "background": "#FFFEF0", "text": "#2C2C2C", "gradient_from": "#D4AF37", "gradient_to": "#C8872A"},
        "hair_care": {"primary": "#C9A227", "secondary": "#FFF8E0", "accent": "#700C0C",  "background": "#FFFEF5", "text": "#2C2C2C", "gradient_from": "#C9A227", "gradient_to": "#A07820"},
        "body_care": {"primary": "#D4AF37", "secondary": "#FFF8E0", "accent": "#2D4A27",  "background": "#FFFEF5", "text": "#2C2C2C", "gradient_from": "#D4AF37", "gradient_to": "#A07820"},
        "default":   {"primary": "#D4AF37", "secondary": "#FFF9E6", "accent": "#8B0000",  "background": "#FFFEF0", "text": "#2C2C2C", "gradient_from": "#D4AF37", "gradient_to": "#C8872A"},
    },
}

TYPOGRAPHY_PAIRINGS: dict[str, dict] = {
    "luxury":      {"headline_font": "Playfair Display", "body_font": "Lato",           "cta_font": "Cormorant Garamond", "style_name": "Elegant Serif",       "headline_weight": "Bold",      "body_weight": "Regular", "cta_weight": "SemiBold", "letter_spacing": "wide",   "text_transform": "none"},
    "minimal":     {"headline_font": "Montserrat",       "body_font": "Open Sans",       "cta_font": "Montserrat",         "style_name": "Clean Sans",          "headline_weight": "SemiBold",  "body_weight": "Light",   "cta_weight": "Bold",     "letter_spacing": "normal", "text_transform": "uppercase"},
    "fun":         {"headline_font": "Nunito",           "body_font": "Poppins",         "cta_font": "Nunito",             "style_name": "Rounded Friendly",    "headline_weight": "ExtraBold", "body_weight": "Regular", "cta_weight": "Bold",     "letter_spacing": "normal", "text_transform": "none"},
    "enthusiastic":{"headline_font": "Anton",            "body_font": "Roboto",          "cta_font": "Anton",              "style_name": "Bold Impact",         "headline_weight": "Regular",   "body_weight": "Regular", "cta_weight": "Regular",  "letter_spacing": "tight",  "text_transform": "uppercase"},
    "educational": {"headline_font": "Merriweather",     "body_font": "Source Sans Pro", "cta_font": "Montserrat",         "style_name": "Trustworthy Readable","headline_weight": "Bold",      "body_weight": "Regular", "cta_weight": "SemiBold", "letter_spacing": "normal", "text_transform": "none"},
    "default":     {"headline_font": "Playfair Display", "body_font": "Poppins",         "cta_font": "Montserrat",         "style_name": "Natural Warmth",      "headline_weight": "Bold",      "body_weight": "Regular", "cta_weight": "SemiBold", "letter_spacing": "normal", "text_transform": "none"},
}

FONT_SIZES: dict[str, dict[str, int]] = {
    "instagram_post":     {"headline": 52,  "subheadline": 30, "body": 20, "cta": 24, "price": 34, "logo": 18},
    "instagram_carousel": {"headline": 52,  "subheadline": 30, "body": 18, "cta": 22, "price": 30, "logo": 16},
    "instagram_story":    {"headline": 64,  "subheadline": 36, "body": 24, "cta": 30, "price": 40, "logo": 20},
    "facebook_post":      {"headline": 48,  "subheadline": 28, "body": 18, "cta": 22, "price": 32, "logo": 16},
    "reel_cover":         {"headline": 72,  "subheadline": 40, "body": 28, "cta": 34, "price": 44, "logo": 22},
    "product_banner":     {"headline": 56,  "subheadline": 32, "body": 20, "cta": 26, "price": 36, "logo": 18},
}

LAYOUT_ZONES: dict[str, dict[str, dict]] = {
    "product_center":   {"description": "Product hero at center, brand text above, CTA below", "best_for": ["instagram_post", "facebook_post"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "product_image": {"x": 15, "y": 22, "w": 70, "h": 55, "z": 2}, "headline": {"x": 5, "y": 5, "w": 90, "h": 14, "z": 3}, "subheadline": {"x": 10, "y": 79, "w": 80, "h": 8, "z": 3}, "cta_button": {"x": 25, "y": 88, "w": 50, "h": 7, "z": 4}, "logo": {"x": 78, "y": 2, "w": 20, "h": 5, "z": 4}, "price_tag": {"x": 2, "y": 85, "w": 22, "h": 8, "z": 4}}},
    "lifestyle_scene":  {"description": "Full bleed lifestyle photo with text overlay at bottom", "best_for": ["instagram_post", "instagram_story", "reel_cover"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "lifestyle_image": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 1}, "gradient_overlay": {"x": 0, "y": 55, "w": 100, "h": 45, "z": 2}, "headline": {"x": 5, "y": 60, "w": 90, "h": 15, "z": 3}, "subheadline": {"x": 5, "y": 76, "w": 75, "h": 8, "z": 3}, "cta_button": {"x": 5, "y": 86, "w": 45, "h": 7, "z": 4}, "logo": {"x": 78, "y": 3, "w": 20, "h": 5, "z": 4}}},
    "split_panel":      {"description": "Left panel: product photo. Right panel: text and CTA.", "best_for": ["facebook_post", "product_banner"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "left_image": {"x": 0, "y": 0, "w": 50, "h": 100, "z": 1}, "right_panel": {"x": 50, "y": 0, "w": 50, "h": 100, "z": 1}, "headline": {"x": 53, "y": 15, "w": 44, "h": 25, "z": 3}, "subheadline": {"x": 53, "y": 43, "w": 44, "h": 15, "z": 3}, "price_tag": {"x": 53, "y": 60, "w": 30, "h": 10, "z": 4}, "cta_button": {"x": 53, "y": 75, "w": 40, "h": 10, "z": 4}, "logo": {"x": 53, "y": 5, "w": 20, "h": 6, "z": 4}}},
    "quote_overlay":    {"description": "Strong quote in center with subtle product in background", "best_for": ["instagram_story", "instagram_post"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "bg_image": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 1}, "color_overlay": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 2}, "quote_text": {"x": 8, "y": 20, "w": 84, "h": 45, "z": 3}, "attribution": {"x": 8, "y": 68, "w": 50, "h": 8, "z": 3}, "cta_button": {"x": 25, "y": 80, "w": 50, "h": 8, "z": 4}, "logo": {"x": 78, "y": 3, "w": 20, "h": 5, "z": 4}}},
    "ingredient_focus": {"description": "Key ingredient hero shot with product + educational copy", "best_for": ["instagram_post", "instagram_carousel"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "ingredient_img": {"x": 0, "y": 0, "w": 100, "h": 55, "z": 1}, "gradient": {"x": 0, "y": 45, "w": 100, "h": 20, "z": 2}, "product_image": {"x": 65, "y": 35, "w": 30, "h": 35, "z": 3}, "headline": {"x": 5, "y": 58, "w": 90, "h": 12, "z": 3}, "body_text": {"x": 5, "y": 72, "w": 90, "h": 12, "z": 3}, "cta_button": {"x": 25, "y": 87, "w": 50, "h": 7, "z": 4}, "logo": {"x": 78, "y": 3, "w": 20, "h": 5, "z": 4}}},
    "story_full":       {"description": "Full-screen vertical story with stacked text zones", "best_for": ["instagram_story", "reel_cover"], "zones": {"background": {"x": 0, "y": 0, "w": 100, "h": 100, "z": 0}, "product_image": {"x": 10, "y": 20, "w": 80, "h": 55, "z": 1}, "top_text": {"x": 5, "y": 5, "w": 90, "h": 12, "z": 3}, "mid_text": {"x": 5, "y": 78, "w": 90, "h": 10, "z": 3}, "price_badge": {"x": 70, "y": 60, "w": 25, "h": 12, "z": 4}, "cta_button": {"x": 20, "y": 90, "w": 60, "h": 7, "z": 4}, "logo": {"x": 5, "y": 3, "w": 18, "h": 5, "z": 4}}},
}

VISUAL_MOODS: dict[str, str] = {
    "summer":  "bright, airy, sun-kissed, warm tones, outdoor glow",
    "monsoon": "fresh, dewy, green, earthy, rain-cleansed",
    "winter":  "cozy, warm-lit, golden hour, rich textures, intimate",
    "festive": "celebratory, golden, festive lights, vibrant, joyful",
}

CTA_PLACEMENT_GUIDE: dict[str, str] = {
    "instagram_post":     "bottom_center — sits in lower 15% of frame, full-width button with rounded corners",
    "instagram_carousel": "last_slide_only — prominent on final slide, centered with arrow indicator",
    "instagram_story":    "bottom_sticky — tappable swipe-up area at very bottom, 80% width",
    "facebook_post":      "bottom_right — alongside price tag on right side of split panel",
    "reel_cover":         "bottom_third — large hook text in bottom third, no CTA button needed",
    "product_banner":     "right_aligned — clear button on far right of banner",
}

DESIGN_HIERARCHY: dict[str, list[str]] = {
    "instagram_post":     ["hero_image", "headline", "price_tag", "product_benefit", "cta_button", "brand_logo"],
    "instagram_carousel": ["hook_slide_headline", "slide_images", "benefit_bullets", "social_proof", "cta_button"],
    "instagram_story":    ["hero_image", "hook_text", "product_name", "price_badge", "cta_swipe"],
    "facebook_post":      ["product_image", "headline", "benefit_copy", "price_tag", "cta_button", "brand_logo"],
    "reel_cover":         ["hook_text", "product_image", "brand_logo"],
    "product_banner":     ["product_image", "headline", "key_benefit", "price", "cta_button"],
}


def suggest_layout(content_type: str, platform: str = "instagram", campaign_type: str = "product_launch") -> dict[str, Any]:
    design_type_map = {
        ("post",     "instagram"): "instagram_post",
        ("carousel", "instagram"): "instagram_carousel",
        ("story",    "instagram"): "instagram_story",
        ("post",     "facebook"):  "facebook_post",
        ("reel",     "instagram"): "reel_cover",
        ("banner",   "any"):       "product_banner",
    }
    design_type = design_type_map.get((content_type, platform), design_type_map.get((content_type, "instagram"), "instagram_post"))
    dims = DESIGN_DIMENSIONS.get(design_type, DESIGN_DIMENSIONS["instagram_post"])
    layout_map = {"product_launch": "product_center", "awareness": "lifestyle_scene", "sale": "product_center", "seasonal": "lifestyle_scene", "testimonial": "quote_overlay", "ingredients": "ingredient_focus"}
    if content_type == "story":
        layout_name = "story_full"
    elif content_type in ("reel",):
        layout_name = "lifestyle_scene"
    elif platform == "facebook" and content_type == "post":
        layout_name = "split_panel"
    else:
        layout_name = layout_map.get(campaign_type, "product_center")
    layout_zones = LAYOUT_ZONES.get(layout_name, LAYOUT_ZONES["product_center"])
    return {"design_type": design_type, "layout_name": layout_name, "dimensions": dims, "zones": layout_zones["zones"], "zone_description": layout_zones["description"], "best_for": layout_zones["best_for"], "cta_placement": CTA_PLACEMENT_GUIDE.get(design_type, "bottom_center"), "hierarchy": DESIGN_HIERARCHY.get(design_type, DESIGN_HIERARCHY["instagram_post"])}


def suggest_color_palette(season: str = "summer", category: str = "default", tone: str = "enthusiastic") -> dict[str, Any]:
    season_palette = SEASON_PALETTES.get(season, SEASON_PALETTES["summer"])
    palette = season_palette.get(category, season_palette["default"])
    result = {"primary": palette["primary"], "secondary": palette["secondary"], "accent": palette["accent"], "background": palette["background"], "text": palette["text"], "brand_gold": MYNAT_BRAND["gold"], "brand_cream": MYNAT_BRAND["cream"], "brand_forest_green": MYNAT_BRAND["forest_green"], "brand_soft_rose": MYNAT_BRAND["soft_rose"], "gradient_from": palette.get("gradient_from", palette["primary"]), "gradient_to": palette.get("gradient_to", palette["secondary"])}
    if tone == "luxury":
        result["text"] = "#1A1A1A"
        result["accent"] = MYNAT_BRAND["gold"]
    flat_palette = [{"name": "Primary", "hex": result["primary"], "usage": "headline, main button"}, {"name": "Secondary", "hex": result["secondary"], "usage": "background panels, cards"}, {"name": "Accent", "hex": result["accent"], "usage": "icon accents, dividers"}, {"name": "Background", "hex": result["background"], "usage": "canvas background"}, {"name": "Text", "hex": result["text"], "usage": "body copy, captions"}, {"name": "Brand Gold", "hex": MYNAT_BRAND["gold"], "usage": "CTA button, price tag"}, {"name": "Brand Cream", "hex": MYNAT_BRAND["cream"], "usage": "light overlay text"}]
    return {"palette": flat_palette, "named_colors": result, "visual_mood": VISUAL_MOODS.get(season, "warm and natural"), "season": season, "category": category}


def suggest_typography(tone: str = "default", audience: str = "", design_type: str = "instagram_post") -> dict[str, Any]:
    pairing = TYPOGRAPHY_PAIRINGS.get(tone, TYPOGRAPHY_PAIRINGS["default"])
    sizes = FONT_SIZES.get(design_type, FONT_SIZES["instagram_post"])
    if audience and any(w in audience.lower() for w in ("college", "teen", "young", "gen z")):
        if tone not in ("luxury", "minimal"):
            pairing = TYPOGRAPHY_PAIRINGS["fun"]
    return {"headline": {"font": pairing["headline_font"], "weight": pairing["headline_weight"], "size_px": sizes["headline"], "color": "primary"}, "subheadline": {"font": pairing["body_font"], "weight": "SemiBold", "size_px": sizes["subheadline"], "color": "text"}, "body": {"font": pairing["body_font"], "weight": pairing["body_weight"], "size_px": sizes["body"], "color": "text"}, "cta": {"font": pairing["cta_font"], "weight": pairing["cta_weight"], "size_px": sizes["cta"], "color": "brand_cream"}, "price": {"font": pairing["headline_font"], "weight": "Bold", "size_px": sizes["price"], "color": "brand_gold"}, "style_name": pairing["style_name"], "letter_spacing": pairing["letter_spacing"], "text_transform": pairing["text_transform"]}


def create_design_brief(product_data: dict[str, Any], creator_output: dict[str, Any], content_output: dict[str, Any], campaign_type: str = "product_launch", season: str = "summer", tone: str = "enthusiastic") -> dict[str, Any]:
    platform = creator_output.get("platform", "instagram")
    content_type = creator_output.get("content_type", "post")
    target_audience = creator_output.get("target_audience", "Women 22-35")
    seasonal_angle = creator_output.get("seasonal_angle", "Natural beauty")
    product_name = product_data.get("name", "")
    product_price = product_data.get("price", "")
    product_category = product_data.get("category", "default").lower().replace(" ", "_")
    image_url = product_data.get("image_url", "")
    cta_options = content_output.get("cta_options", [])
    best_cta = cta_options[1] if len(cta_options) > 1 else "Shop now — link in bio"
    layout_data = suggest_layout(content_type, platform, campaign_type)
    color_data = suggest_color_palette(season, product_category, tone)
    type_data = suggest_typography(tone, target_audience, layout_data["design_type"])
    image_suggestions = creator_output.get("canva_design_brief", {}).get("image_suggestions", [])
    if not image_suggestions:
        image_suggestions = [f"Hero product shot of {product_name} on {color_data['named_colors']['background']} background", f"Indian woman with glowing skin, {VISUAL_MOODS.get(season, 'natural')} lighting", f"Close-up of Ayurvedic ingredients matching {season} theme"]
    return {"design_type": layout_data["design_type"], "visual_style": f"{VISUAL_MOODS.get(season, 'warm natural')} — {tone}", "layout_name": layout_data["layout_name"], "dimensions": layout_data["dimensions"], "zones": layout_data["zones"], "color_palette": color_data["palette"], "named_colors": color_data["named_colors"], "typography": type_data, "image_suggestions": image_suggestions, "cta_text": best_cta, "cta_placement": layout_data["cta_placement"], "design_hierarchy": layout_data["hierarchy"], "headline_context": seasonal_angle, "product_name": product_name, "product_price": product_price, "image_url": image_url, "target_audience": target_audience, "campaign_type": campaign_type, "season": season}


def build_carousel_structure(product_name: str, seasonal_angle: str, key_benefits: list[str], price: str | float, cta: str, hashtags: list[str]) -> list[dict[str, Any]]:
    benefits = key_benefits[:3] if key_benefits else ["Natural ingredients", "Ayurvedic formula", "Visible results"]
    top_tags = " ".join(hashtags[:3]) if hashtags else "#mynat #ayurveda #skincare"
    return [
        {"slide": 1, "type": "hook", "purpose": "Stop the scroll — make them tap to see more", "headline": seasonal_angle or "Your skin deserves better 🌿", "subtext": "Swipe to discover →", "image_concept": f"Bold text overlay on {product_name} lifestyle shot", "layout_note": "Full-bleed image with text at bottom third", "background": "lifestyle_scene"},
        {"slide": 2, "type": "problem", "purpose": "Identify the pain point the audience feels", "headline": "Struggling with seasonal skin problems?", "subtext": "Harsh chemicals make it worse. Nature has the answer.", "image_concept": "Split image: dull skin vs glowing skin, subtle comparison", "layout_note": "Clean white background, icon or illustration of the problem", "background": "white_clean"},
        {"slide": 3, "type": "product_intro", "purpose": "Introduce the product as the solution", "headline": f"Meet {product_name}", "subtext": "100% Ayurvedic. Crafted for Indian skin.", "image_concept": f"Clean product hero shot of {product_name} on cream background", "layout_note": "product_center layout — product is the hero", "background": "brand_cream"},
        {"slide": 4, "type": "benefits", "purpose": "Show the 3 key reasons to buy", "headline": "Why your skin will love it", "bullets": benefits, "image_concept": "Ingredient flat lay or ingredient close-up photo", "layout_note": "ingredient_focus layout — icons beside each benefit", "background": "light_green_tint"},
        {"slide": 5, "type": "social_proof", "purpose": "Build trust with real customer voices", "headline": "Loved by 1000s of Indian women ⭐", "subtext": '"My skin has completely transformed!" — real customer', "image_concept": "Real customer photo or before/after (with permission), star rating badge", "layout_note": "quote_overlay layout — customer quote prominent", "background": "warm_cream"},
        {"slide": 6, "type": "cta", "purpose": "Drive the action — link in bio or DM to order", "headline": f"₹{price} only", "subtext": cta, "image_concept": "Product with a clear 'Shop Now' button overlay and Mynat logo", "layout_note": "Large CTA button, price prominent, brand logo bottom", "hashtags_preview": top_tags, "background": "brand_gold_gradient"},
    ]


def build_story_structure(product_name: str, key_benefit: str, price: str | float, cta: str, seasonal_angle: str) -> list[dict[str, Any]]:
    return [
        {"slide": 1, "type": "hook", "duration_seconds": 4, "purpose": "Grab attention in the first second", "top_text": seasonal_angle or "Your skin is calling 🌿", "mid_text": "", "bottom_text": "Tap to see more →", "image_concept": f"Bold lifestyle image with {product_name} as supporting element", "sticker_suggestion": "Question sticker: 'Is your skin ready for this?'", "layout": "story_full"},
        {"slide": 2, "type": "product", "duration_seconds": 5, "purpose": "Show the product and its single biggest benefit", "top_text": f"Introducing {product_name}", "mid_text": key_benefit, "bottom_text": f"Only ₹{price} ✨", "image_concept": f"Clean product shot of {product_name} on brand cream background", "sticker_suggestion": "Countdown timer sticker (if limited offer)", "layout": "product_center"},
        {"slide": 3, "type": "cta", "duration_seconds": 4, "purpose": "Drive the action — one clear next step only", "top_text": "", "mid_text": cta, "bottom_text": "mynat.in", "image_concept": "Brand color background with logo and CTA button", "sticker_suggestion": "Link sticker pointing to mynat.in", "swipe_up_text": "Shop now 🛒", "layout": "cta_slide"},
    ]


def build_reel_cover(product_name: str, hook_text: str, seasonal_angle: str) -> dict[str, Any]:
    return {"type": "reel_cover", "purpose": "Profile grid thumbnail — must stop scrolling on its own", "main_text": hook_text or seasonal_angle or f"Meet {product_name} 🌿", "sub_text": product_name, "image_concept": f"Bright, high-contrast shot of {product_name} with bold hook text", "text_position": "lower_third", "font_size": "extra_large", "background": "lifestyle_or_product", "color_treatment": "gradient_overlay_bottom", "logo_position": "top_right", "dimensions": DESIGN_DIMENSIONS["reel_cover"], "grid_safe_zone": "ensure no important content in top/bottom 10%"}


def prepare_canva_payload(design_brief: dict[str, Any], product_data: dict[str, Any], headline_text: str = "", subtext: str = "") -> dict[str, Any]:
    design_type = design_brief.get("design_type", "instagram_post")
    dims = design_brief.get("dimensions", DESIGN_DIMENSIONS["instagram_post"])
    palette = design_brief.get("named_colors", {})
    typography = design_brief.get("typography", {})
    product_name = product_data.get("name", "Product")
    price = product_data.get("price", "")
    image_url = product_data.get("image_url", "")
    elements = [
        {"id": "background", "type": "rectangle", "z_index": 0, "position": {"x": 0, "y": 0, "width": dims["width"], "height": dims["height"]}, "fill": {"type": "color", "value": palette.get("background", MYNAT_BRAND["cream"])}},
        {"id": "hero_image", "type": "image", "z_index": 1, "position": {"x": int(dims["width"] * 0.15), "y": int(dims["height"] * 0.22), "width": int(dims["width"] * 0.70), "height": int(dims["height"] * 0.55)}, "src": image_url or "placeholder_product", "description": design_brief.get("image_suggestions", ["Product hero shot"])[0], "placeholder": not bool(image_url)},
        {"id": "gradient_overlay", "type": "gradient", "z_index": 2, "position": {"x": 0, "y": int(dims["height"] * 0.55), "width": dims["width"], "height": int(dims["height"] * 0.45)}, "fill": {"type": "linear_gradient", "from": {"color": "transparent", "position": 0}, "to": {"color": palette.get("background", MYNAT_BRAND["cream"]), "position": 1}, "angle": 180}, "opacity": 0.85},
        {"id": "headline", "type": "text", "z_index": 3, "position": {"x": int(dims["width"] * 0.05), "y": int(dims["height"] * 0.05), "width": int(dims["width"] * 0.90), "height": int(dims["height"] * 0.14)}, "content": headline_text or design_brief.get("headline_context", f"Natural Beauty for {product_name}"), "font_family": typography.get("headline", {}).get("font", "Playfair Display"), "font_size": typography.get("headline", {}).get("size_px", 52), "font_weight": typography.get("headline", {}).get("weight", "Bold"), "color": palette.get("primary", MYNAT_BRAND["gold"]), "alignment": "center", "letter_spacing": typography.get("letter_spacing", "normal")},
        {"id": "subtext", "type": "text", "z_index": 3, "position": {"x": int(dims["width"] * 0.05), "y": int(dims["height"] * 0.79), "width": int(dims["width"] * 0.90), "height": int(dims["height"] * 0.08)}, "content": subtext or f"100% Ayurvedic · ₹{price} · mynat.in", "font_family": typography.get("body", {}).get("font", "Poppins"), "font_size": typography.get("body", {}).get("size_px", 20), "font_weight": typography.get("body", {}).get("weight", "Regular"), "color": palette.get("text", MYNAT_BRAND["charcoal"]), "alignment": "center"},
        {"id": "cta_button", "type": "button", "z_index": 4, "position": {"x": int(dims["width"] * 0.25), "y": int(dims["height"] * 0.88), "width": int(dims["width"] * 0.50), "height": int(dims["height"] * 0.07)}, "content": design_brief.get("cta_text", "Shop Now"), "background": MYNAT_BRAND["gold"], "text_color": MYNAT_BRAND["cream"], "border_radius": "50px", "font_family": typography.get("cta", {}).get("font", "Montserrat"), "font_size": typography.get("cta", {}).get("size_px", 22), "font_weight": "Bold"},
        {"id": "brand_logo", "type": "image", "z_index": 4, "position": {"x": int(dims["width"] * 0.78), "y": int(dims["height"] * 0.02), "width": int(dims["width"] * 0.20), "height": int(dims["height"] * 0.05)}, "src": "mynat_logo", "description": "Mynat brand logo — white or gold variant"},
    ]
    return {"mock": True, "api_version": "v1", "design_name": f"Mynat — {product_name} — {design_type.replace('_', ' ').title()}", "design_type": design_type, "dimensions": dims, "template_query": f"ayurvedic skincare {product_data.get('category', 'beauty')} {design_type.replace('_', ' ')}", "color_palette": [c["hex"] for c in design_brief.get("color_palette", [])[:5]], "elements": elements, "export_formats": ["PNG", "JPG", "PDF"], "status": "draft", "canva_note": "TODO: Replace mock=True and pass this payload to the Canva Connect API or use mcp__claude_ai_Canva__generate-design when credentials are ready."}


# ── canva_agent/agent.py ──────────────────────────────────────────────────────

import logging
from datetime import datetime

from agents.shared import call_claude, parse_json_object
from agents.agent_schemas import CanvaAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback

logger = logging.getLogger(__name__)

MONTH_TO_SEASON: dict[int, str] = {1: 'winter', 2: 'winter', 3: 'summer', 4: 'summer', 5: 'summer', 6: 'monsoon', 7: 'monsoon', 8: 'monsoon', 9: 'festive', 10: 'festive', 11: 'festive', 12: 'winter'}
MONTH_NAMES: dict[int, str] = {1: 'January', 2: 'February', 3: 'March', 4: 'April', 5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September', 10: 'October', 11: 'November', 12: 'December'}
CAMPAIGN_TONE_MAP: dict[str, str] = {'product_launch': 'enthusiastic', 'awareness': 'educational', 'sale': 'enthusiastic', 'seasonal': 'luxury', 'testimonial': 'minimal', 'default': 'enthusiastic'}
SEASON_VISUAL_MOODS: dict[str, str] = {'summer': 'bright, airy, sun-kissed, warm tones, outdoor glow', 'monsoon': 'fresh, dewy, green, earthy, rain-cleansed', 'winter': 'cozy, warm-lit, golden hour, rich textures, intimate', 'festive': 'celebratory, golden, festive lights, vibrant, joyful'}
_DEFAULT_BENEFITS: dict[str, list[str]] = {'face': ['Reduces dark spots with turmeric & saffron', 'Ayurvedic herbs for visibly glowing skin', 'Gentle on sensitive and Indian skin types'], 'hair': ['Strengthens hair from root to tip naturally', 'Reduces hair fall with bhringraj & amla', 'Nourishes deeply with cold-pressed Ayurvedic oils'], 'body': ['Deep moisturizing that lasts all day', 'Non-sticky, fast-absorbing Ayurvedic formula', 'Softens and protects skin in every season']}


def _canva_fallback(reason: str, product_data: dict[str, Any] | None = None) -> dict[str, Any]:
    product_data = product_data or {}
    product_name = product_data.get('name', 'Mynat Campaign')
    return safe_agent_fallback('canva', reason, design_type='instagram_post', visual_style='warm natural Ayurvedic skincare', layout='product_center', color_palette=[{'name': 'Mynat Gold', 'hex': '#C8872A', 'usage': 'accent'}], fonts={'headline': 'Serif', 'body': 'Sans'}, headline_text=product_name, subtext='Draft visual brief for review', image_suggestions=['Use clean product photography with natural ingredients.'], canva_payload={'mock': True, 'status': 'draft'})


def _call_claude(prompt: str, max_tokens: int = 1024) -> str:
    return call_claude(prompt, max_tokens=max_tokens, system='You are the visual art director for Mynat (mynat.in), an Indian Ayurvedic skincare brand. Your designs are warm, natural, and celebratory of Indian beauty traditions. Always return valid JSON exactly as instructed — no markdown, no preamble.')


def _parse_json(text: str) -> dict:
    return parse_json_object(text)


def _get_key_benefits(product_data: dict, content_output: dict) -> list[str]:
    ad_body = content_output.get('ad_copy', {}).get('body', '')
    if ad_body:
        sentences = ad_body.split('. ')
        if len(sentences) >= 2:
            return [sentences[0], sentences[1], sentences[-1]][:3]
    category = product_data.get('category', 'face').lower()
    key = next((k for k in _DEFAULT_BENEFITS if k in category), 'face')
    return _DEFAULT_BENEFITS[key]


def _get_key_benefit(product_data: dict, content_output: dict) -> str:
    return _get_key_benefits(product_data, content_output)[0]


def _call_claude_for_creative(content_type: str, platform: str, product_data: dict, season: str, seasonal_angle: str, target_audience: str, campaign_type: str, visual_mood: str, instagram_caption: str, cta: str, hashtags: list[str], reel_script: dict, content_output: dict) -> dict:
    product_name = product_data.get('name', '')
    product_desc = (product_data.get('description') or '')[:200]
    product_price = str(product_data.get('price', ''))
    product_category = product_data.get('category', 'skincare')
    key_benefits = _get_key_benefits(product_data, content_output)
    key_benefits_str = ', '.join(key_benefits)
    key_benefit = key_benefits[0]
    reel_hook = reel_script.get('hook', seasonal_angle)
    try:
        if content_type == 'carousel':
            prompt = CAROUSEL_PROMPT.format(product_name=product_name, product_description=product_desc, product_price=product_price, season=season, seasonal_angle=seasonal_angle, target_audience=target_audience, key_benefits=key_benefits_str, cta=cta)
            return _parse_json(_call_claude(prompt, max_tokens=1500))
        elif content_type == 'story':
            prompt = STORY_PROMPT.format(product_name=product_name, product_price=product_price, key_benefit=key_benefit, season=season, seasonal_angle=seasonal_angle, target_audience=target_audience, cta=cta, visual_mood=visual_mood)
            return _parse_json(_call_claude(prompt, max_tokens=1000))
        elif content_type in ('reel', 'reel_cover'):
            prompt = REEL_COVER_PROMPT.format(product_name=product_name, product_description=product_desc, reel_hook=reel_hook, season=season, seasonal_angle=seasonal_angle, target_audience=target_audience, visual_mood=visual_mood)
            return _parse_json(_call_claude(prompt, max_tokens=700))
        else:
            prompt = POST_DESIGN_PROMPT.format(product_name=product_name, product_description=product_desc, product_price=product_price, product_category=product_category, platform=platform, season=season, seasonal_angle=seasonal_angle, target_audience=target_audience, campaign_type=campaign_type, visual_mood=visual_mood, instagram_caption=instagram_caption or f'Discover {product_name} — natural Ayurvedic care.')
            return _parse_json(_call_claude(prompt, max_tokens=700))
    except (KeyError, ValueError) as e:
        logger.error(f'[CANVA AGENT] Prompt formatting failed: {e}')
        return {}


def _enrich_carousel_with_claude(tool_slides: list[dict], claude_response: dict) -> list[dict]:
    claude_slides = claude_response.get('slides', [])
    if not claude_slides:
        return tool_slides
    enriched = []
    for i, tool_slide in enumerate(tool_slides):
        if i < len(claude_slides):
            cs = claude_slides[i]
            merged = {**tool_slide, 'headline': cs.get('headline', tool_slide.get('headline', '')), 'subtext': cs.get('subtext', tool_slide.get('subtext', '')), 'image_concept': cs.get('image_concept', tool_slide.get('image_concept', ''))}
            if cs.get('bullets'):
                merged['bullets'] = cs['bullets']
            if cs.get('quote'):
                merged['customer_quote'] = cs['quote']
            if cs.get('cta_button_text'):
                merged['cta_button_text'] = cs['cta_button_text']
            if cs.get('swipe_cue'):
                merged['swipe_cue'] = cs['swipe_cue']
            enriched.append(merged)
        else:
            enriched.append(tool_slide)
    return enriched


def _enrich_story_with_claude(tool_slides: list[dict], claude_response: dict) -> list[dict]:
    claude_slides = claude_response.get('slides', [])
    if not claude_slides:
        return tool_slides
    enriched = []
    for i, tool_slide in enumerate(tool_slides):
        if i < len(claude_slides):
            cs = claude_slides[i]
            merged = {**tool_slide, 'top_text': cs.get('top_text', tool_slide.get('top_text', '')), 'mid_text': cs.get('mid_text', tool_slide.get('mid_text', '')), 'bottom_text': cs.get('bottom_text', tool_slide.get('bottom_text', '')), 'image_concept': cs.get('image_concept', tool_slide.get('image_concept', ''))}
            if cs.get('sticker_ideas'):
                merged['sticker_ideas'] = cs['sticker_ideas']
            if cs.get('animation_suggestion'):
                merged['animation_suggestion'] = cs['animation_suggestion']
            enriched.append(merged)
        else:
            enriched.append(tool_slide)
    return enriched


def _merge_image_suggestions(brief: dict, claude_creative: dict) -> list[str]:
    suggestions: list[str] = []
    if claude_creative.get('image_concept'):
        suggestions.append(claude_creative['image_concept'])
    if claude_creative.get('image_concept_alternative'):
        suggestions.append(claude_creative['image_concept_alternative'])
    for suggestion in brief.get('image_suggestions', []):
        if suggestion not in suggestions:
            suggestions.append(suggestion)
    return suggestions[:4]


def run_canva_agent(product_data: dict[str, Any], creator_output: dict[str, Any] | None = None, content_output: dict[str, Any] | None = None, campaign_type: str = 'product_launch', target_audience: str | None = None, seasonal_angle: str | None = None, month: int | None = None) -> dict[str, Any]:
    """Generate a complete visual design package for a Mynat marketing campaign."""
    if not product_data:
        return validate_or_fallback(CanvaAgentOutput, {'success': False, 'error': 'No product data provided'}, lambda reason: _canva_fallback(reason, product_data))
    month = month or datetime.now().month
    season = MONTH_TO_SEASON.get(month, 'festive')
    month_name = MONTH_NAMES.get(month, 'Unknown')
    creator = creator_output or {}
    content = content_output or {}
    platform = creator.get('platform', 'instagram')
    content_type = creator.get('content_type', 'post')
    resolved_angle = seasonal_angle or creator.get('seasonal_angle') or f'{season.title()} skincare essentials'
    resolved_audience = target_audience or creator.get('target_audience') or 'Women 22-35, skincare conscious'
    tone = CAMPAIGN_TONE_MAP.get(campaign_type, 'enthusiastic')
    visual_mood = SEASON_VISUAL_MOODS.get(season, 'warm and natural')
    product_name = product_data.get('name', '')
    product_price = str(product_data.get('price', ''))
    instagram_caption = content.get('instagram_caption', '')
    cta_options = content.get('cta_options', [])
    best_cta = cta_options[1] if len(cta_options) > 1 else 'Shop now — link in bio'
    hashtags = content.get('hashtags', [])
    reel_script = content.get('reel_script', {})
    logger.info(f"[CANVA AGENT] Starting — Product: '{product_name}', Type: {content_type}, Platform: {platform}, Season: {season}")
    brief = create_design_brief(product_data=product_data, creator_output=creator, content_output=content, campaign_type=campaign_type, season=season, tone=tone)
    claude_creative = _call_claude_for_creative(content_type=content_type, platform=platform, product_data=product_data, season=season, seasonal_angle=resolved_angle, target_audience=resolved_audience, campaign_type=campaign_type, visual_mood=visual_mood, instagram_caption=instagram_caption, cta=best_cta, hashtags=hashtags, reel_script=reel_script, content_output=content)
    if not claude_creative:
        logger.warning('[CANVA AGENT] Claude returned empty — using tool-only brief as fallback')
    carousel_structure: list[dict] = []
    story_structure: list[dict] = []
    reel_cover: dict = {}
    if content_type == 'carousel':
        tool_carousel = build_carousel_structure(product_name=product_name, seasonal_angle=resolved_angle, key_benefits=_get_key_benefits(product_data, content), price=product_price, cta=best_cta, hashtags=hashtags)
        carousel_structure = _enrich_carousel_with_claude(tool_carousel, claude_creative)
    elif content_type == 'story':
        tool_story = build_story_structure(product_name=product_name, key_benefit=_get_key_benefit(product_data, content), price=product_price, cta=best_cta, seasonal_angle=resolved_angle)
        story_structure = _enrich_story_with_claude(tool_story, claude_creative)
    elif content_type in ('reel', 'reel_cover'):
        reel_hook = reel_script.get('hook', resolved_angle)
        reel_cover = build_reel_cover(product_name=product_name, hook_text=claude_creative.get('cover_hook_text', reel_hook), seasonal_angle=resolved_angle)
        if claude_creative.get('a_b_variant'):
            reel_cover['a_b_variant'] = claude_creative['a_b_variant']
        if claude_creative.get('grid_tip'):
            reel_cover['grid_tip'] = claude_creative['grid_tip']
    headline_text = claude_creative.get('headline_text') or resolved_angle[:50]
    subtext_text = claude_creative.get('subtext') or f'₹{product_price} · mynat.in'
    canva_payload = prepare_canva_payload(design_brief=brief, product_data=product_data, headline_text=headline_text, subtext=subtext_text)
    output = {'success': True, 'design_type': brief['design_type'], 'visual_style': brief['visual_style'], 'layout': brief['layout_name'], 'color_palette': brief['color_palette'], 'fonts': brief['typography'], 'headline_text': headline_text, 'subtext': subtext_text, 'image_suggestions': _merge_image_suggestions(brief, claude_creative), 'image_concept': claude_creative.get('image_concept', ''), 'design_tip': claude_creative.get('design_tip', ''), 'cta_placement': brief['cta_placement'], 'design_hierarchy': brief['design_hierarchy'], 'zones': brief.get('zones', {}), 'carousel_structure': carousel_structure, 'story_structure': story_structure, 'reel_cover': reel_cover, 'video_storyboard': _build_video_storyboard(product_name, resolved_angle, best_cta), 'visual_hierarchy_score': _visual_hierarchy_score(brief, headline_text, subtext_text), 'canva_payload': canva_payload, 'status': 'draft', '_meta': {'month': month, 'month_name': month_name, 'season': season, 'seasonal_angle': resolved_angle, 'target_audience': resolved_audience, 'platform': platform, 'content_type': content_type, 'campaign_type': campaign_type, 'tone': tone, 'visual_mood': visual_mood, 'claude_used': bool(claude_creative)}}
    logger.info(f"[CANVA AGENT] Complete — Design: {brief['design_type']}, Layout: {brief['layout_name']}, Claude: {bool(claude_creative)}")
    return validate_or_fallback(CanvaAgentOutput, output, lambda reason: _canva_fallback(reason, product_data), retry_factory=lambda failed: {**failed, 'success': bool(failed.get('canva_payload'))})


def _build_video_storyboard(product_name: str, seasonal_angle: str, cta: str) -> list[dict[str, Any]]:
    return [
        {'scene': 1, 'duration': '0-3s', 'visual': f'Hero product shot of {product_name}', 'voiceover': f'Meet {product_name}.', 'text': 'Natural glow', 'CTA': ''},
        {'scene': 2, 'duration': '3-10s', 'visual': f'Ingredient and texture shot aligned to {seasonal_angle}', 'voiceover': 'A clean Ayurvedic ritual for everyday care.', 'text': seasonal_angle[:42], 'CTA': ''},
        {'scene': 3, 'duration': '10-15s', 'visual': 'Mynat branded end frame with product and CTA', 'voiceover': cta, 'text': cta[:42], 'CTA': cta},
    ]


def _visual_hierarchy_score(brief: dict[str, Any], headline: str, subtext: str) -> int:
    score = 50
    if brief.get('cta_placement'):
        score += 15
    if brief.get('design_hierarchy'):
        score += 15
    if headline and len(headline) <= 60:
        score += 10
    if subtext and len(subtext) <= 80:
        score += 10
    return min(100, score)
