"""
AES-256-GCM encryption utilities for sensitive fields with key rotation support.

Usage:
    from backend.utils.data_encryption import encrypt, decrypt, mask, rotate_key

    token = encrypt("sk-abc123")   # encrypts with current key version
    original = decrypt(token)      # auto-detects key version from prefix

Key rotation:
    1. Generate new key: python -c "import secrets; print(secrets.token_hex(32))"
    2. Set ENCRYPTION_KEY_v2=<new> and ENCRYPTION_KEY=<new> in env
    3. Old ciphertext (prefixed v1:) is still decryptable via ENCRYPTION_KEY_v1
    4. Re-encrypt old values by calling rotate_key(old_token)

Generate a key:
    python -c "import secrets; print(secrets.token_hex(32))"
"""
from __future__ import annotations
import base64
import hashlib
import os
import warnings
from mcp_server.env_loader import load_environment
load_environment()

_NONCE_LEN = 12
_CURRENT_VERSION = 'v1'

def _derive_key(raw: str) -> bytes:
    return hashlib.sha256(raw.encode()).digest()

def _get_key(version: str | None = None) -> bytes:
    """Return AES key for the requested version. Warns loudly if unconfigured in prod."""
    ver = version or _CURRENT_VERSION
    raw = os.getenv(f'ENCRYPTION_KEY_{ver}') or os.getenv('ENCRYPTION_KEY', '')
    if not raw:
        env = os.getenv('ENVIRONMENT', os.getenv('ENV', 'development')).lower()
        if env in ('production', 'prod', 'staging'):
            raise RuntimeError(
                f'ENCRYPTION_KEY or ENCRYPTION_KEY_{ver} must be set in {env}. '
                'Run: python -c "import secrets; print(secrets.token_hex(32))"'
            )
        warnings.warn(
            'ENCRYPTION_KEY not set — using insecure dev key. '
            'Set ENCRYPTION_KEY env var before deploying.',
            stacklevel=3,
        )
        raw = 'mynat-dev-only-not-for-production'
    return _derive_key(raw)

def encrypt(plaintext: str, version: str | None = None) -> str:
    """Encrypt with AES-256-GCM. Returns '<version>:<base64url>'."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        ver = version or _CURRENT_VERSION
        nonce = os.urandom(_NONCE_LEN)
        ct = AESGCM(_get_key(ver)).encrypt(nonce, plaintext.encode(), None)
        payload = base64.urlsafe_b64encode(nonce + ct).decode()
        return f'{ver}:{payload}'
    except ImportError:
        return f'UNENCRYPTED:{plaintext}'

def decrypt(token: str) -> str:
    """
    Decrypt a token from encrypt(). Auto-detects key version from prefix.
    Raises ValueError on tamper or wrong key.
    """
    if token.startswith('UNENCRYPTED:'):
        return token[len('UNENCRYPTED:'):]
    # Legacy tokens (no version prefix) — treat as v1
    if ':' not in token or token.split(':', 1)[0] not in ('v1', 'v2', 'v3'):
        version, payload = _CURRENT_VERSION, token
    else:
        version, payload = token.split(':', 1)
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        raw = base64.urlsafe_b64decode(payload.encode())
        nonce, ct = raw[:_NONCE_LEN], raw[_NONCE_LEN:]
        return AESGCM(_get_key(version)).decrypt(nonce, ct, None).decode()
    except Exception as e:
        raise ValueError(f'Decryption failed: {e}') from e

def rotate_key(old_token: str, new_version: str | None = None) -> str:
    """Decrypt with old key version, re-encrypt with new version. Use during key rotation."""
    plaintext = decrypt(old_token)
    return encrypt(plaintext, new_version)

def mask(value: str, visible: int = 4) -> str:
    """Return a masked version safe for logging: 'sk-a****'."""
    if not value:
        return '****'
    if len(value) <= visible:
        return '****'
    return value[:visible] + '****'
