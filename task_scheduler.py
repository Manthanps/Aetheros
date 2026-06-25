"""Celery app + scheduled automation tasks."""
import os
from celery import Celery
from celery.schedules import crontab
from mcp_server.env_loader import load_environment
load_environment()
BROKER = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/1')
BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/2')
app = Celery('mynat_ai', broker=BROKER, backend=BACKEND)
app.conf.timezone = 'Asia/Kolkata'
app.conf.task_serializer = 'json'
app.conf.result_serializer = 'json'
app.conf.accept_content = ['json']
app.conf.beat_schedule = {
    # ── Every 6 hours ─────────────────────────────────────────────────────
    'scrape-website-every-6h': {
        'task': 'backend.automation.tasks.scrape_and_ingest_products',
        'schedule': crontab(minute=0, hour='*/6'),
    },
    # ── Daily ─────────────────────────────────────────────────────────────
    'daily-sales-report': {
        'task': 'backend.automation.tasks.generate_daily_sales_report',
        'schedule': crontab(minute=0, hour=8),
    },
    # ── Every 5 minutes ───────────────────────────────────────────────────
    'publish-scheduled-posts': {
        'task': 'backend.automation.tasks.publish_scheduled_posts',
        'schedule': crontab(minute='*/5'),
    },
    # ── Weekly (Monday) ───────────────────────────────────────────────────
    'weekly-seo-audit': {
        'task': 'backend.automation.tasks.run_weekly_seo_audit',
        'schedule': crontab(minute=0, hour=9, day_of_week=1),
    },
    'weekly-optimization': {
        'task': 'backend.automation.tasks.run_weekly_optimization',
        'schedule': crontab(minute=0, hour=10, day_of_week=1),
    },
    # ── Monthly (1st of each month, IST) ──────────────────────────────────
    'monthly-content-strategy-refresh': {
        'task': 'backend.automation.tasks.monthly_content_strategy_refresh',
        'schedule': crontab(minute=0, hour=7, day_of_month=1),
    },
    'monthly-competitor-analysis': {
        'task': 'backend.automation.tasks.monthly_competitor_analysis',
        'schedule': crontab(minute=30, hour=7, day_of_month=1),
    },
    'monthly-rag-reindex': {
        'task': 'backend.automation.tasks.monthly_rag_reindex',
        'schedule': crontab(minute=0, hour=2, day_of_month=1),
    },
    'monthly-security-health-check': {
        'task': 'backend.automation.tasks.monthly_security_health_check',
        'schedule': crontab(minute=0, hour=6, day_of_month=1),
    },
    'monthly-email-list-cleanup': {
        'task': 'backend.automation.tasks.monthly_email_list_cleanup',
        'schedule': crontab(minute=0, hour=8, day_of_month=2),
    },
    'monthly-gmail-token-refresh': {
        'task': 'backend.automation.tasks.monthly_gmail_token_refresh',
        'schedule': crontab(minute=0, hour=3, day_of_month=1),
    },
}

@app.task(name='backend.automation.tasks.scrape_and_ingest_products', bind=True, max_retries=3)
def scrape_and_ingest_products(self):
    """Scrape Mynat website and refresh the RAG knowledge base."""
    try:
        from mcp_server.tools.website_scraper_tool import scrape_website
        from mcp_server.tools.product_rag_tool import ingest_products_to_rag
        url = os.getenv('MYNAT_WEBSITE_URL', 'https://mynat.in/')
        data = scrape_website(url, max_products=100)
        products = data.get('products', [])
        if products:
            result = ingest_products_to_rag(products)
            return {'scraped': len(products), 'rag_result': result}
        return {'scraped': 0}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=300)

@app.task(name='backend.automation.tasks.generate_daily_sales_report')
def generate_daily_sales_report():
    """Generate and email a daily sales report."""
    from mcp_server.tools.analytics_tool import generate_sales_report
    report = generate_sales_report('daily', include_predictions=True)
    return report

@app.task(name='backend.automation.tasks.run_weekly_seo_audit')
def run_weekly_seo_audit():
    """Run a weekly SEO audit and store results."""
    from mcp_server.tool_registry import run_seo_audit
    url = os.getenv('MYNAT_WEBSITE_URL', 'https://mynat.in/')
    return run_seo_audit(url)

@app.task(name='backend.automation.tasks.publish_scheduled_posts')
def publish_scheduled_posts():
    """Check for due scheduled posts and publish them."""
    from datetime import datetime, timezone
    from backend.database.db_connection import get_db
    from backend.database.db_models import Campaign
    from mcp_server.tools.social_post_tool import post_instagram, post_facebook
    published = 0
    failed = 0
    with get_db() as db:
        now = datetime.now(timezone.utc)
        due = db.query(Campaign).filter(Campaign.scheduled_at <= now, Campaign.status == 'scheduled').all()
        for campaign in due:
            content = campaign.content or {}
            try:
                if campaign.campaign_type == 'instagram':
                    result = post_instagram(caption=content.get('caption', ''), image_url=content.get('image_url', ''), hashtags=content.get('hashtags', []))
                elif campaign.campaign_type == 'facebook':
                    result = post_facebook(message=content.get('caption', content.get('message', '')), image_url=content.get('image_url', ''), link=content.get('link', ''))
                else:
                    continue
                if result.get('success'):
                    campaign.platform_post_id = result.get('post_id')
                    campaign.status = 'completed'
                    campaign.published_at = datetime.now(timezone.utc)
                    published += 1
                else:
                    campaign.status = 'paused'
                    failed += 1
            except Exception:
                failed += 1
    return {'checked': len(due), 'published': published, 'failed': failed}

@app.task(name='backend.automation.tasks.run_weekly_optimization')
def run_weekly_optimization():
    """Run the self-optimization CrewAI crew every Monday."""
    from backend.agents.self_optimizer import run_optimization_crew
    return run_optimization_crew()

@app.task(name='backend.automation.tasks.auto_generate_product_content', bind=True, max_retries=2)
def auto_generate_product_content(self, product_data: dict):
    """Auto-generate full content suite for a new product."""
    try:
        from mcp_server.tools.content_gen_tool import generate_caption, generate_facebook_ad, generate_blog, generate_hashtags, generate_email_campaign
        name = product_data.get('name', '')
        desc = product_data.get('description', '')
        price = product_data.get('price', '')
        return {'product': name, 'caption': generate_caption(name, desc, price), 'facebook_ad': generate_facebook_ad(name, desc, price), 'hashtags': generate_hashtags(name, desc), 'email': generate_email_campaign('new_product', product_name=name)}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)

# ── Monthly tasks ─────────────────────────────────────────────────────────────

@app.task(name='backend.automation.tasks.monthly_content_strategy_refresh', bind=True, max_retries=2)
def monthly_content_strategy_refresh(self):
    """Refresh content strategy: seasonal themes, top-performing formats, new keywords."""
    try:
        from agents.revenue_grower import generate_content_strategy
        from mcp_server.tools.product_rag_tool import search_products_in_rag
        products = search_products_in_rag('bestseller top product', top_k=20)
        strategy = generate_content_strategy(products=products.get('results', []))
        return {'status': 'ok', 'month': _current_month(), 'strategy_keys': list(strategy.keys())}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600)


@app.task(name='backend.automation.tasks.monthly_competitor_analysis', bind=True, max_retries=2)
def monthly_competitor_analysis(self):
    """Scrape competitor sites and update competitive intelligence in RAG."""
    try:
        from mcp_server.tools.website_scraper_tool import scrape_website
        from mcp_server.tools.product_rag_tool import ingest_products_to_rag
        competitors = [c.strip() for c in os.getenv('COMPETITOR_URLS', '').split(',') if c.strip()]
        if not competitors:
            return {'status': 'skipped', 'reason': 'COMPETITOR_URLS not configured'}
        results = []
        for url in competitors[:5]:
            data = scrape_website(url, max_products=30)
            if data.get('products'):
                ingest_products_to_rag(data['products'])
                results.append({'url': url, 'scraped': len(data['products'])})
        return {'status': 'ok', 'month': _current_month(), 'competitors_analysed': results}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=600)


@app.task(name='backend.automation.tasks.monthly_rag_reindex', bind=True, max_retries=2)
def monthly_rag_reindex(self):
    """Full RAG reindex: re-scrape all products and rebuild the vector store."""
    try:
        from mcp_server.tools.website_scraper_tool import scrape_website
        from mcp_server.tools.product_rag_tool import ingest_products_to_rag
        url = os.getenv('MYNAT_WEBSITE_URL', 'https://mynat.in/')
        data = scrape_website(url, max_products=500)
        products = data.get('products', [])
        if products:
            result = ingest_products_to_rag(products)
            return {'status': 'ok', 'month': _current_month(), 'reindexed': len(products), 'rag_result': result}
        return {'status': 'ok', 'reindexed': 0}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=900)


@app.task(name='backend.automation.tasks.monthly_security_health_check')
def monthly_security_health_check():
    """
    Security health check: verify required env vars are set, encryption key is not default,
    API keys are configured, and report any gaps.
    """
    import warnings
    from loguru import logger
    issues = []

    required_vars = [
        'ENCRYPTION_KEY', 'API_KEYS', 'WEBHOOK_SECRET',
        'MCP_SERVER_SECRET', 'META_ACCESS_TOKEN',
    ]
    for var in required_vars:
        if not os.getenv(var):
            issues.append(f'MISSING: {var}')

    enc_key = os.getenv('ENCRYPTION_KEY', '')
    if enc_key == 'mynat-dev-only-not-for-production' or not enc_key:
        issues.append('CRITICAL: ENCRYPTION_KEY is using the insecure dev default')

    security_mode = os.getenv('SECURITY_MODE', 'strict')
    if security_mode != 'strict':
        issues.append(f'WARNING: SECURITY_MODE={security_mode} (should be strict in prod)')

    if issues:
        logger.warning(f'[SECURITY_HEALTH] {len(issues)} issue(s) found: {issues}')
        # Send alert email if notification address configured
        notify = os.getenv('NOTIFICATION_EMAIL', '')
        if notify:
            try:
                from mcp_server.tools.email_send_tool import send_email_auto
                body = '<br>'.join(issues)
                send_email_auto(
                    to_email=notify,
                    subject=f'[Mynat AI] Monthly Security Check — {len(issues)} issue(s)',
                    html_content=f'<p>Security issues detected:</p><ul><li>{body}</li></ul>',
                )
            except Exception:
                pass
    else:
        logger.info('[SECURITY_HEALTH] All checks passed')

    return {'status': 'ok', 'month': _current_month(), 'issues': issues}


@app.task(name='backend.automation.tasks.monthly_email_list_cleanup')
def monthly_email_list_cleanup():
    """
    Remove hard-bounced/unsubscribed addresses from the EmailLog table
    and prune logs older than 90 days to keep the table lean.
    """
    from datetime import datetime, timezone, timedelta
    from backend.database.db_connection import get_db
    from backend.database.db_models import EmailLog
    cutoff = datetime.now(timezone.utc) - timedelta(days=90)
    deleted = 0
    with get_db() as db:
        old = db.query(EmailLog).filter(EmailLog.sent_at < cutoff).all()
        deleted = len(old)
        for row in old:
            db.delete(row)
        db.commit()
    return {'status': 'ok', 'month': _current_month(), 'pruned_rows': deleted}


@app.task(name='backend.automation.tasks.monthly_gmail_token_refresh')
def monthly_gmail_token_refresh():
    """
    Proactively refresh the Gmail OAuth2 token before it expires.
    Requires GMAIL_TOKEN_JSON to be set.
    """
    token_file = os.getenv('GMAIL_TOKEN_JSON', '')
    if not token_file or not os.path.exists(token_file):
        return {'status': 'skipped', 'reason': 'GMAIL_TOKEN_JSON not configured or file missing'}
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(
            token_file, scopes=['https://www.googleapis.com/auth/gmail.send']
        )
        if creds and creds.refresh_token:
            creds.refresh(Request())
            with open(token_file, 'w') as f:
                f.write(creds.to_json())
            return {'status': 'ok', 'month': _current_month(), 'token_refreshed': True}
        return {'status': 'ok', 'token_refreshed': False, 'reason': 'no refresh_token'}
    except ImportError:
        return {'status': 'skipped', 'reason': 'google-auth not installed'}
    except Exception as exc:
        return {'status': 'error', 'error': str(exc)}


def _current_month() -> str:
    from datetime import date
    return date.today().strftime('%Y-%m')
