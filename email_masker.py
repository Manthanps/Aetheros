"""Small wrapper for handling configured email addresses safely."""
from __future__ import annotations
import os
from mcp_server.env_loader import load_env_file

def get_approval_recipient_email() -> str:
    """
    Return the current approval recipient from mail config.

    This deliberately reloads `configs/mail.env` so changing NOTIFICATION_EMAIL
    can take effect for the next approval email without tying delivery to the
    Gmail account active on the local laptop.
    """
    mail_values = load_env_file('mail.env', override=True)
    return (mail_values.get('NOTIFICATION_EMAIL') or os.environ.get('NOTIFICATION_EMAIL', '') or os.environ.get('APPROVAL_RECIPIENT_EMAIL', '')).strip()

def mask_email(email: str) -> str:
    """Mask an email address for logs, JSON stores, and API responses."""
    email = (email or '').strip()
    if '@' not in email:
        return ''
    local, domain = email.split('@', 1)
    if not local or not domain:
        return ''
    visible_local = local[:2] if len(local) > 2 else local[:1]
    visible_domain = domain[:1]
    return f'{visible_local}***@{visible_domain}***'

def get_masked_approval_recipient_email() -> str:
    """Return the masked approval recipient for non-secret surfaces."""
    return mask_email(get_approval_recipient_email())
