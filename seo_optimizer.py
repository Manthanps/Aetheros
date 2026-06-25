"""
SEO Agent — flat module (merged from agents/seo_agent/ package).
Contains SEOAnalysisAgent (DeepSeek R1-powered) and CLI runner.
"""

# ── seo_agent/__init__.py ──────────────────────────────────────────────────────
# (was just a docstring — nothing to export here beyond the classes below)

# ── seo_agent/deepseek/__init__.py ────────────────────────────────────────────
# (was just a docstring)

# ── seo_agent/deepseek/seo_analysis_agent.py ──────────────────────────────────

import json
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from typing import Optional
from agents.agent_schemas import SEOAgentOutput
from agents.output_validator import safe_agent_fallback, validate_or_fallback
from backend.deepseek_client import DeepSeekR1Client, DeepSeekProvider

SEO_SYSTEM_PROMPT = '\nYou are an elite SEO strategist with 15+ years of experience in:\n- Indian e-commerce SEO (Google India, Bing India)\n- E-commerce platforms: Shopify, WooCommerce, custom stores\n- Technical SEO: Core Web Vitals, structured data, crawlability\n- Content SEO: topical authority, keyword clustering, E-E-A-T\n- Local SEO for Indian cities and regional markets\n- Competitive intelligence: SEMrush-level analysis\n\nYou are analysing Mynat.in — an Indian e-commerce brand.\nTarget market: Urban India, age 18-45, mobile-first shoppers.\nPrimary language: English, with Hindi/Hinglish secondary.\n\nALWAYS:\n- Think step-by-step before giving your final answer\n- Give specific, actionable recommendations — not generic advice\n- Include real example keywords, titles, and meta descriptions\n- Prioritise recommendations by HIGH / MEDIUM / LOW impact\n- Format all JSON outputs as valid parseable JSON\n'


class SEOAnalysisAgent:

    def __init__(self, provider: DeepSeekProvider = DeepSeekProvider.DEEPSEEK_NATIVE):
        self.llm = DeepSeekR1Client(provider=provider, max_tokens=8000)
        self.headers = {'User-Agent': 'Mozilla/5.0 (compatible; MynatSEOBot/2.0)', 'Accept-Language': 'en-IN,en;q=0.9'}

    def audit_page(self, url: str) -> dict:
        """Deep SEO audit of any URL."""
        print(f'\n🔍 Auditing: {url}')
        signals = self._scrape_seo_signals(url)
        prompt = f'\nPerform a comprehensive SEO audit for this web page.\n\nURL: {url}\nDomain: {urlparse(url).netloc}\n\nRAW SEO SIGNALS EXTRACTED:\n{json.dumps(signals, indent=2)}\n\nAnalyse these signals and return a JSON audit report with this structure:\n{{\n    "overall_score": <0-100>,\n    "grade": "<A|B|C|D|F>",\n    "executive_summary": "<3-4 sentence overview>",\n    "critical_issues": [\n        {{"issue": "...", "impact": "HIGH", "fix": "...", "effort": "Easy|Medium|Hard"}}\n    ],\n    "on_page_seo": {{\n        "title_tag":        {{"score": <0-10>, "current": "...", "recommended": "...", "notes": "..."}},\n        "meta_description": {{"score": <0-10>, "current": "...", "recommended": "...", "notes": "..."}},\n        "h1_tag":           {{"score": <0-10>, "current": "...", "recommended": "...", "notes": "..."}},\n        "url_structure":    {{"score": <0-10>, "notes": "..."}},\n        "keyword_density":  {{"score": <0-10>, "top_keywords": [], "notes": "..."}},\n        "image_alt_tags":   {{"score": <0-10>, "missing_count": 0, "notes": "..."}},\n        "internal_links":   {{"score": <0-10>, "count": 0, "notes": "..."}},\n        "content_length":   {{"score": <0-10>, "word_count": 0, "recommended_min": 0}}\n    }},\n    "technical_seo": {{\n        "page_speed_estimate": "<Fast|Medium|Slow>",\n        "mobile_friendly":     <true|false>,\n        "https":               <true|false>,\n        "canonical_tag":       "<present|missing>",\n        "robots_meta":         "...",\n        "schema_markup":       "<present|missing|partial>",\n        "open_graph":          "<present|missing>"\n    }},\n    "keyword_opportunities": [\n        {{"keyword": "...", "search_volume": "...", "difficulty": "Low|Medium|High", "intent": "..."}}\n    ],\n    "recommended_schema": "<full JSON-LD schema markup string>",\n    "optimised_title":    "...",\n    "optimised_meta":     "...",\n    "content_suggestions": ["suggestion1", "suggestion2"],\n    "quick_wins": ["quick win 1", "quick win 2", "quick win 3"],\n    "priority_action_plan": [\n        {{"week": 1, "actions": []}},\n        {{"week": 2, "actions": []}},\n        {{"week": 3, "actions": []}},\n        {{"week": 4, "actions": []}}\n    ]\n}}\n\nReturn ONLY valid JSON — no markdown fences, no extra text.\n'
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'url': url, 'reasoning_preview': response.reasoning[:300] + '…' if response.reasoning else '', 'tokens_used': response.total_tokens, 'duration_seconds': response.duration_seconds, 'model': response.model}
        return self._finalize(result)

    def keyword_research(self, product_or_topic: str, category: str = '', location: str = 'India', count: int = 40) -> dict:
        """Full keyword strategy using DeepSeek R1's reasoning."""
        print(f'\n🔑 Keyword research: {product_or_topic}')
        prompt = f"""\nBuild a complete keyword strategy for:\n\nProduct/Topic : {product_or_topic}\nCategory      : {category or 'E-commerce'}\nLocation      : {location}\nTarget Count  : {count} keywords total\n\nReturn JSON with this exact structure:\n{{\n    "seed_keyword": "...",\n    "primary_keywords": [\n        {{"keyword": "...", "monthly_searches": "...", "difficulty": "Low|Medium|High",\n          "cpc_inr": "...", "intent": "informational|navigational|transactional|commercial"}}\n    ],\n    "long_tail_keywords": [\n        {{"keyword": "...", "monthly_searches": "...", "difficulty": "Low",\n          "intent": "...", "why_valuable": "..."}}\n    ],\n    "lsi_keywords": ["keyword1", "keyword2"],\n    "question_keywords": [\n        {{"question": "...", "featured_snippet_opportunity": true}}\n    ],\n    "local_keywords": [\n        {{"keyword": "...", "city": "Mumbai|Delhi|Bangalore|..."}}\n    ],\n    "negative_keywords": ["keyword1", "keyword2"],\n    "keyword_clusters": [\n        {{"cluster_name": "...", "keywords": [], "recommended_page": "..."}}\n    ],\n    "content_calendar_ideas": [\n        {{"title": "...", "target_keyword": "...", "content_type": "blog|product|category"}}\n    ],\n    "competitor_keywords_to_target": ["keyword1", "keyword2"],\n    "quick_win_keywords": [\n        {{"keyword": "...", "reason": "low difficulty + decent volume"}}\n    ]\n}}\n\nReturn ONLY valid JSON.\n"""
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'query': product_or_topic, 'tokens_used': response.total_tokens, 'reasoning_preview': response.reasoning[:300] + '…' if response.reasoning else ''}
        return self._finalize(result)

    def analyse_competitor(self, competitor_url: str, our_url: str = 'https://mynat.in') -> dict:
        """Scrape competitor and run DeepSeek R1 gap analysis."""
        print(f'\n🕵️ Competitor analysis: {competitor_url}')
        our_signals = self._scrape_seo_signals(our_url)
        comp_signals = self._scrape_seo_signals(competitor_url)
        prompt = f'\nCompare these two e-commerce websites from an SEO perspective.\n\nOUR SITE ({our_url}):\n{json.dumps(our_signals, indent=2)}\n\nCOMPETITOR ({competitor_url}):\n{json.dumps(comp_signals, indent=2)}\n\nReturn a JSON competitive analysis:\n{{\n    "competitor_url": "{competitor_url}",\n    "our_url":        "{our_url}",\n    "summary":        "...",\n    "competitor_strengths": ["strength1", "strength2"],\n    "competitor_weaknesses": ["weakness1", "weakness2"],\n    "our_advantages":   ["advantage1", "advantage2"],\n    "our_gaps":         ["gap1", "gap2"],\n    "keyword_gaps": [\n        {{"keyword": "...", "competitor_ranks": "~position", "our_rank": "not ranking",\n          "opportunity_score": "High|Medium|Low"}}\n    ],\n    "content_gaps": [\n        {{"topic": "...", "competitor_coverage": "...", "our_action": "..."}}\n    ],\n    "technical_comparison": {{\n        "our_score":        <0-100>,\n        "competitor_score": <0-100>,\n        "winner":           "us|them|tie"\n    }},\n    "steal_these_strategies": [\n        {{"strategy": "...", "implementation": "...", "priority": "HIGH|MEDIUM|LOW"}}\n    ],\n    "differentiation_opportunities": ["opportunity1", "opportunity2"],\n    "30_day_action_plan": ["action1", "action2", "action3"]\n}}\n\nReturn ONLY valid JSON.\n'
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'tokens_used': response.total_tokens, 'reasoning_preview': response.reasoning[:300] + '…' if response.reasoning else ''}
        return self._finalize(result)

    def generate_blog_outline(self, topic: str, target_keyword: str, word_count: int = 1500) -> dict:
        """Generate a full SEO-optimised blog outline with DeepSeek R1."""
        print(f'\n📝 Blog outline: {topic}')
        prompt = f'\nCreate a detailed SEO blog outline for Mynat.in\n\nTopic          : {topic}\nTarget Keyword : {target_keyword}\nTarget Length  : {word_count} words\nAudience       : Indian online shoppers, 20-35 years old\n\nReturn JSON:\n{{\n    "seo_title":        "...(max 60 chars, keyword near start)",\n    "meta_description": "...(max 155 chars, includes keyword + CTA)",\n    "url_slug":         "keyword-rich-slug",\n    "focus_keyword":    "...",\n    "secondary_keywords": ["kw1", "kw2", "kw3"],\n    "lsi_keywords":     ["lsi1", "lsi2"],\n    "estimated_word_count": {word_count},\n    "outline": [\n        {{\n            "section":    "Introduction",\n            "heading":    "H1: ...",\n            "word_count": 150,\n            "key_points": ["point1", "point2"],\n            "keywords_to_use": ["kw1"],\n            "content_tips": "Hook the reader with a relatable problem"\n        }},\n        {{\n            "section":    "Section 1",\n            "heading":    "H2: ...",\n            "word_count": 200,\n            "subsections": [\n                {{"heading": "H3: ...", "key_points": [], "word_count": 100}}\n            ],\n            "keywords_to_use": [],\n            "content_tips": ""\n        }}\n    ],\n    "faq_section": [\n        {{"question": "...(natural language query)", "answer_hint": "..."}}\n    ],\n    "internal_links": [\n        {{"anchor": "...", "suggested_target": "/product-category/..."}}\n    ],\n    "schema_type":    "Article|HowTo|FAQPage",\n    "call_to_action": "...",\n    "featured_snippet_target": "...(the exact H2 to optimise for a featured snippet)",\n    "content_checklist": ["✅ item1", "✅ item2"]\n}}\n\nReturn ONLY valid JSON.\n'
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'tokens_used': response.total_tokens, 'model': response.model}
        return self._finalize(result)

    def technical_seo_audit(self, url: str = 'https://mynat.in') -> dict:
        """Deep technical SEO audit using scraped data + R1 reasoning."""
        print(f'\n⚙️ Technical SEO audit: {url}')
        signals = self._scrape_seo_signals(url)
        prompt = f'\nPerform a technical SEO audit for {url}\n\nPAGE DATA:\n{json.dumps(signals, indent=2)}\n\nReturn JSON technical audit:\n{{\n    "technical_score": <0-100>,\n    "checklist": [\n        {{\n            "category": "Core Web Vitals|Crawlability|Indexability|Security|Mobile|Structured Data|Performance",\n            "item":     "...",\n            "status":   "PASS|FAIL|WARNING|UNKNOWN",\n            "impact":   "HIGH|MEDIUM|LOW",\n            "fix":      "Exact steps to fix this",\n            "code_example": "..."\n        }}\n    ],\n    "robots_txt_recommendations": "...",\n    "sitemap_recommendations":    "...",\n    "structured_data_to_add": [\n        {{"type": "Product|BreadcrumbList|FAQPage|...", "priority": "HIGH"}}\n    ],\n    "page_speed_tips": [\n        {{"tip": "...", "estimated_improvement": "... ms"}}\n    ],\n    "mobile_issues":  ["issue1", "issue2"],\n    "security_issues": ["issue1"],\n    "canonical_strategy": "...",\n    "hreflang_needed": false,\n    "javascript_seo_issues": ["issue1"],\n    "crawl_budget_tips": ["tip1", "tip2"],\n    "priority_fixes": [\n        {{"rank": 1, "fix": "...", "impact": "...", "estimated_traffic_gain": "..."}}\n    ]\n}}\n\nReturn ONLY valid JSON.\n'
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'tokens_used': response.total_tokens, 'model': response.model}
        return self._finalize(result)

    def generate_monthly_plan(self, current_issues: list[str] = None, target_keywords: list[str] = None, budget_inr: int = 10000) -> dict:
        """Generate a full month-by-month SEO roadmap."""
        print('\n📅 Generating monthly SEO plan...')
        prompt = f'\nCreate a 3-month SEO action plan for Mynat.in\n\nCurrent Issues    : {json.dumps(current_issues or [])}\nTarget Keywords   : {json.dumps(target_keywords or [])}\nMonthly Budget    : ₹{budget_inr:,}\n\nReturn JSON:\n{{\n    "goal":    "Increase organic traffic by X% in 90 days",\n    "kpis":    ["KPI1", "KPI2", "KPI3"],\n    "months": [\n        {{\n            "month":    1,\n            "theme":    "Foundation & Technical Fixes",\n            "budget":   "₹...",\n            "tasks": [\n                {{\n                    "week":     1,\n                    "category": "Technical|Content|Links|Analytics",\n                    "task":     "...",\n                    "owner":    "Developer|Content Writer|SEO Analyst",\n                    "hours":    2,\n                    "priority": "HIGH"\n                }}\n            ],\n            "expected_outcomes": ["outcome1"],\n            "tools_needed":      ["Google Search Console", "Screaming Frog"]\n        }},\n        {{"month": 2, "theme": "Content Expansion", "budget": "₹...", "tasks": [], "expected_outcomes": []}},\n        {{"month": 3, "theme": "Authority & Scale",  "budget": "₹...", "tasks": [], "expected_outcomes": []}}\n    ],\n    "content_plan": [\n        {{"month": 1, "articles": [\n            {{"title": "...", "keyword": "...", "word_count": 1200, "type": "blog|product|category"}}\n        ]}}\n    ],\n    "link_building_strategy": ["strategy1", "strategy2"],\n    "tools_recommended": [\n        {{"tool": "Google Search Console", "cost": "Free", "use": "..."}}\n    ],\n    "success_metrics": {{\n        "month_1": {{"organic_traffic": "+10%", "keywords_ranking": "+20"}},\n        "month_2": {{"organic_traffic": "+25%", "keywords_ranking": "+50"}},\n        "month_3": {{"organic_traffic": "+50%", "keywords_ranking": "+100"}}\n    }}\n}}\n\nReturn ONLY valid JSON.\n'
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'tokens_used': response.total_tokens, 'model': response.model}
        return self._finalize(result)

    def generate_schema(self, product_data: dict, schema_type: str = 'Product') -> dict:
        """Generate JSON-LD structured data for any product or page."""
        print(f'\n🏷️ Generating {schema_type} schema...')
        prompt = f'''\nGenerate complete JSON-LD structured data markup.\n\nSchema Type   : {schema_type}\nProduct Data  : {json.dumps(product_data, indent=2)}\nWebsite       : https://mynat.in\n\nReturn JSON:\n{{\n    "schema_jsonld": {{\n        "@context": "https://schema.org",\n        "@type":    "{schema_type}",\n        ... (complete valid schema.org markup)\n    }},\n    "html_snippet":   "<script type='application/ld+json'>...</script>",\n    "additional_schemas": [\n        {{"type": "BreadcrumbList", "jsonld": {{}}}}\n    ],\n    "validation_tips": ["tip1", "tip2"],\n    "rich_result_types": ["Product Rich Result", "Review Snippet"]\n}}\n\nReturn ONLY valid JSON.\n'''
        response = self.llm.think(prompt=prompt, system=SEO_SYSTEM_PROMPT)
        result = self._parse_json(response.content)
        result['_meta'] = {'tokens_used': response.total_tokens}
        return self._finalize(result)

    def _scrape_seo_signals(self, url: str) -> dict:
        """Extract raw SEO signals from a URL for the LLM to analyse."""
        try:
            resp = requests.get(url, headers=self.headers, timeout=20)
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.find('title')
            title_text = title.get_text(strip=True) if title else ''
            metas = {}
            for tag in soup.find_all('meta'):
                name = tag.get('name') or tag.get('property') or ''
                content = tag.get('content') or ''
                if name and content:
                    metas[name] = content
            headings = {}
            for level in ['h1', 'h2', 'h3', 'h4']:
                headings[level] = [h.get_text(strip=True) for h in soup.find_all(level)][:10]
            all_images = soup.find_all('img')
            no_alt = sum((1 for img in all_images if not img.get('alt')))
            all_links = soup.find_all('a', href=True)
            internal = [a['href'] for a in all_links if 'mynat.in' in a.get('href', '') or a['href'].startswith('/')]
            external = [a['href'] for a in all_links if a['href'].startswith('http') and 'mynat.in' not in a['href']]
            body_text = soup.get_text(separator=' ')
            word_count = len(re.findall('\\b\\w+\\b', body_text))
            schemas = [s.get_text() for s in soup.find_all('script', type='application/ld+json')]
            canonical = soup.find('link', rel='canonical')
            return {'url': url, 'status_code': resp.status_code, 'title': title_text, 'title_length': len(title_text), 'meta_description': metas.get('description', ''), 'meta_desc_length': len(metas.get('description', '')), 'meta_robots': metas.get('robots', ''), 'canonical': canonical['href'] if canonical else '', 'open_graph': {k: v for k, v in metas.items() if k.startswith('og:')}, 'twitter_card': {k: v for k, v in metas.items() if k.startswith('twitter:')}, 'headings': headings, 'h1_count': len(headings.get('h1', [])), 'word_count': word_count, 'image_count': len(all_images), 'images_missing_alt': no_alt, 'internal_links': len(internal), 'external_links': len(external), 'has_schema': len(schemas) > 0, 'schema_count': len(schemas), 'https': url.startswith('https://'), 'response_time_ms': round(resp.elapsed.total_seconds() * 1000), 'page_size_kb': round(len(resp.content) / 1024, 1)}
        except Exception as e:
            return {'url': url, 'error': str(e)}

    def _parse_json(self, text: str) -> dict:
        """Robustly parse JSON from LLM output."""
        text = re.sub('```json\\s*', '', text)
        text = re.sub('```\\s*', '', text)
        text = text.strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            match = re.search('\\{.*\\}', text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
            return {'raw_response': text, 'parse_error': True}

    def _finalize(self, result: dict) -> dict:
        """Validate SEO output while preserving method-specific extra fields."""
        result = {'success': not bool(result.get('error') or result.get('parse_error')), **result}
        return validate_or_fallback(SEOAgentOutput, result, lambda reason: safe_agent_fallback('seo', reason, overall_score=None, grade='', executive_summary='SEO output could not be validated.', critical_issues=[], keyword_opportunities=[], priority_action_plan=[]), retry_factory=lambda failed: {**failed, 'success': not bool(failed.get('error') or failed.get('parse_error'))})


# ── seo_agent/deepseek/run_seo_agent.py ───────────────────────────────────────

import argparse
import sys
from datetime import datetime
from pathlib import Path


def print_header(title: str):
    print('\n' + '═' * 60)
    print(f'  🔍 {title}')
    print('═' * 60)


def save_result(result: dict, task_name: str):
    """Save JSON result to reports/ folder."""
    folder = Path('reports/seo')
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = folder / f'{task_name}_{timestamp}.json'
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f'\n💾 Report saved: {path}')
    return path


def run_audit(args, agent):
    print_header(f'Full SEO Audit: {args.url}')
    result = agent.audit_page(args.url)
    print(f"\n📊 Overall Score : {result.get('overall_score', 'N/A')} / 100")
    print(f"📊 Grade         : {result.get('grade', 'N/A')}")
    print(f"\n📋 Summary:\n{result.get('executive_summary', '')}")
    issues = result.get('critical_issues', [])
    if issues:
        print(f'\n🚨 Critical Issues ({len(issues)}):')
        for i in issues[:3]:
            print(f"  [{i.get('impact', '?')}] {i.get('issue', '')}")
            print(f"       Fix: {i.get('fix', '')}")
    wins = result.get('quick_wins', [])
    if wins:
        print('\n⚡ Quick Wins:')
        for w in wins:
            print(f'  • {w}')
    save_result(result, 'audit')


def run_keywords(args, agent):
    print_header(f'Keyword Research: {args.product}')
    result = agent.keyword_research(product_or_topic=args.product, category=args.category or '', location=args.location or 'India', count=args.count or 40)
    primaries = result.get('primary_keywords', [])
    print(f'\n🎯 Top Primary Keywords:')
    for kw in primaries[:5]:
        print(f"  • {kw.get('keyword'):<40} Vol: {kw.get('monthly_searches'):<15} Difficulty: {kw.get('difficulty')}")
    long_tails = result.get('long_tail_keywords', [])
    print(f'\n🐛 Top Long-tail Keywords:')
    for kw in long_tails[:5]:
        print(f"  • {kw.get('keyword')}")
    quick_wins = result.get('quick_win_keywords', [])
    print(f'\n⚡ Quick Win Keywords:')
    for kw in quick_wins[:5]:
        print(f"  • {kw.get('keyword')} — {kw.get('reason')}")
    save_result(result, 'keywords')


def run_compete(args, agent):
    print_header(f'Competitor Analysis: {args.url}')
    result = agent.analyse_competitor(args.url)
    print(f'\n📊 Their Strengths:')
    for s in result.get('competitor_strengths', [])[:3]:
        print(f'  ✅ {s}')
    print(f'\n🎯 Steal These Strategies:')
    for s in result.get('steal_these_strategies', [])[:3]:
        print(f"  [{s.get('priority')}] {s.get('strategy')}")
        print(f"    → {s.get('implementation')}")
    save_result(result, 'competitor')


def run_blog(args, agent):
    print_header(f'Blog Outline: {args.topic}')
    result = agent.generate_blog_outline(topic=args.topic, target_keyword=args.keyword or args.topic, word_count=args.words or 1500)
    print(f"\n📄 SEO Title     : {result.get('seo_title', '')}")
    print(f"📄 Meta Desc     : {result.get('meta_description', '')}")
    print(f"📄 URL Slug      : {result.get('url_slug', '')}")
    print(f"📄 Focus Keyword : {result.get('focus_keyword', '')}")
    print('\n📚 Article Outline:')
    for section in result.get('outline', []):
        print(f"\n  {section.get('heading', '')}")
        for sub in section.get('subsections', []):
            print(f"    └─ {sub.get('heading', '')}")
    save_result(result, 'blog_outline')


def run_technical(args, agent):
    print_header(f'Technical SEO Audit: {args.url}')
    result = agent.technical_seo_audit(args.url)
    print(f"\n⚙️ Technical Score: {result.get('technical_score', 'N/A')} / 100")
    checklist = result.get('checklist', [])
    fails = [c for c in checklist if c.get('status') == 'FAIL']
    print(f'\n❌ Failed Checks ({len(fails)}):')
    for c in fails[:5]:
        print(f"  [{c.get('impact')}] {c.get('item')}")
        print(f"       Fix: {c.get('fix')}")
    priority = result.get('priority_fixes', [])
    print(f'\n🏆 Top Priority Fixes:')
    for f in priority[:3]:
        print(f"  #{f.get('rank')} {f.get('fix')} → {f.get('estimated_traffic_gain', '')}")
    save_result(result, 'technical')


def run_plan(args, agent):
    print_header('3-Month SEO Roadmap')
    result = agent.generate_monthly_plan(budget_inr=args.budget or 10000)
    print(f"\n🎯 Goal: {result.get('goal', '')}")
    print(f'\n📊 KPIs:')
    for kpi in result.get('kpis', []):
        print(f'  • {kpi}')
    for month in result.get('months', []):
        print(f"\n📅 Month {month.get('month')}: {month.get('theme')}")
        for task in month.get('tasks', [])[:3]:
            print(f"  Week {task.get('week')}: [{task.get('priority')}] {task.get('task')}")
    save_result(result, 'roadmap')


def main():
    parser = argparse.ArgumentParser(description='Mynat SEO Agent — DeepSeek R1')
    sub = parser.add_subparsers(dest='command')
    p = sub.add_parser('audit')
    p.add_argument('--url', default='https://mynat.in')
    p = sub.add_parser('keywords')
    p.add_argument('--product', required=True)
    p.add_argument('--category', default='')
    p.add_argument('--location', default='India')
    p.add_argument('--count', type=int, default=40)
    p = sub.add_parser('compete')
    p.add_argument('--url', required=True)
    p = sub.add_parser('blog')
    p.add_argument('--topic', required=True)
    p.add_argument('--keyword', default='')
    p.add_argument('--words', type=int, default=1500)
    p = sub.add_parser('technical')
    p.add_argument('--url', default='https://mynat.in')
    p = sub.add_parser('plan')
    p.add_argument('--budget', type=int, default=10000)
    for sp in sub.choices.values():
        sp.add_argument('--provider', choices=['deepseek', 'openrouter', 'ollama'], default='deepseek')
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)
    provider_map = {'deepseek': DeepSeekProvider.DEEPSEEK_NATIVE, 'openrouter': DeepSeekProvider.OPENROUTER, 'ollama': DeepSeekProvider.OLLAMA}
    agent = SEOAnalysisAgent(provider=provider_map[args.provider])
    dispatch = {'audit': run_audit, 'keywords': run_keywords, 'compete': run_compete, 'blog': run_blog, 'technical': run_technical, 'plan': run_plan}
    dispatch[args.command](args, agent)


if __name__ == '__main__':
    main()
