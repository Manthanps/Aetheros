from pydantic_settings import BaseSettings
from functools import lru_cache
from mcp_server.env_loader import load_environment
load_environment()

class Settings(BaseSettings):
    app_name: str = 'Mynat Automation Server'
    app_env: str = 'development'
    mynat_website_url: str = 'https://mynat.in/'
    security_mode: str = 'relaxed'
    api_mode: str = 'mock'
    anthropic_api_key: str = ''
    openai_api_key: str = ''
    google_ai_api_key: str = ''
    default_llm_provider: str = 'anthropic'
    default_model: str = 'claude-sonnet-4-6'
    creator_agent_model: str = 'claude-sonnet-4-6'
    creator_agent_temperature: float = 0.2
    creator_agent_max_tokens: int = 1600
    database_url: str = 'sqlite:///./mynat.db'
    redis_url: str = 'redis://localhost:6379/0'
    chroma_persist_dir: str = './chroma_db'
    vector_db_path: str = './chroma_db'
    rag_collection_name: str = 'mynat_products'
    meta_app_id: str = ''
    meta_app_secret: str = ''
    meta_access_token: str = ''
    instagram_business_account_id: str = ''
    facebook_page_id: str = ''
    sendgrid_api_key: str = ''
    resend_api_key: str = ''
    mailchimp_api_key: str = ''
    mailchimp_server_prefix: str = 'us1'
    from_email: str = 'marketing@mynat.in'
    smtp_host: str = ''
    smtp_port: int = 587
    smtp_user: str = ''
    smtp_username: str = ''
    smtp_password: str = ''
    smtp_use_tls: bool = True
    notification_email: str = ''
    approval_required: bool = True
    approval_recipient_email: str = ''
    approval_email_provider: str = 'auto'
    approval_base_url: str = 'http://localhost:8000'
    approval_store_path: str = './mcp_approvals.json'
    approval_ttl_minutes: int = 30
    ga_property_id: str = ''
    google_service_account_json: str = './google-service-account.json'
    whatsapp_phone_number_id: str = ''
    whatsapp_access_token: str = ''
    canva_api_key: str = ''
    canva_access_token: str = ''
    canva_team_id: str = ''
    canva_brand_id: str = ''
    canva_workspace_id: str = ''
    shopify_store_url: str = ''
    shopify_access_token: str = ''
    shopify_api_version: str = '2025-01'
    api_keys: str = ''
    api_key: str = ''
    allowed_origins: str = 'http://localhost:8000,http://127.0.0.1:8000'
    allowed_ips: str = '127.0.0.1,::1'
    rate_limit_per_minute: int = 100
    mcp_server_secret: str = ''
    log_level: str = 'INFO'

    class Config:
        extra = 'ignore'

@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if settings.smtp_user and (not settings.smtp_username):
        settings.smtp_username = settings.smtp_user
    if settings.notification_email and (not settings.approval_recipient_email):
        settings.approval_recipient_email = settings.notification_email
    return settings

def validate_strict_security(settings: Settings | None=None) -> None:
    """Refuse unsafe startup in strict mode."""
    settings = settings or get_settings()
    if settings.security_mode.lower() != 'strict':
        return
    api_keys = [key.strip() for key in settings.api_keys.split(',') if key.strip()]
    if settings.api_key:
        api_keys.append(settings.api_key)
    missing = []
    if not api_keys:
        missing.append('API_KEYS or API_KEY')
    if not settings.mcp_server_secret:
        missing.append('MCP_SERVER_SECRET')
    if settings.allowed_origins.strip() == '*':
        missing.append('ALLOWED_ORIGINS must not be *')
    if not settings.allowed_ips.strip():
        missing.append('ALLOWED_IPS must list owner/faculty IPs')
    if missing:
        raise RuntimeError(f"Strict security mode refused startup. Missing/unsafe: {', '.join(missing)}")
