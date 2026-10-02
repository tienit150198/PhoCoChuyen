"""Optional public Google configuration; secrets and saves never enter this module."""
from __future__ import annotations

import html
import json
import os
import re
from urllib.parse import urlsplit

PUBLIC_FIELDS = {
    'apiKey': 'FIREBASE_API_KEY',
    'projectId': 'FIREBASE_PROJECT_ID',
    'appId': 'FIREBASE_APP_ID',
    'messagingSenderId': 'FIREBASE_MESSAGING_SENDER_ID',
    'measurementId': 'FIREBASE_MEASUREMENT_ID',
}


def public_origin() -> str:
    """Only an HTTPS origin, without credentials, paths or query strings."""
    value = os.environ.get('SITE_URL', '').strip()
    try:
        parsed = urlsplit(value)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.path not in ('', '/') or parsed.query or parsed.fragment):
            return ''
        # Also rejects invalid port syntax.
        if parsed.port not in (None, 443):
            return ''
        return 'https://' + parsed.hostname.lower()
    except ValueError:
        return ''


def public_config() -> dict:
    origin = public_origin()
    firebase = {name: os.environ.get(env, '').strip() for name, env in PUBLIC_FIELDS.items()}
    if (not origin or not all(firebase.get(key) for key in ('apiKey', 'projectId', 'appId', 'measurementId'))
            or not re.fullmatch(r'G-[A-Z0-9]+', firebase['measurementId'])
            or not re.fullmatch(r'[a-z0-9][a-z0-9-]{4,61}[a-z0-9]', firebase['projectId'])
            or any(len(value) > 256 for value in firebase.values())):
        return {}
    return {'origin': origin, 'firebase': {k: v for k, v in firebase.items() if v},
            'performance': os.environ.get('FIREBASE_PERFORMANCE', '1').lower() in ('1', 'true', 'yes', 'on')}


def head_tags() -> list[str]:
    tags = []
    origin = public_origin()
    if origin:
        tags.append(f'<link rel="canonical" href="{html.escape(origin, quote=True)}/">')
    verification = os.environ.get('GOOGLE_SITE_VERIFICATION', '').strip()
    if re.fullmatch(r'[A-Za-z0-9_-]{1,256}', verification):
        tags.append(f'<meta name="google-site-verification" content="{verification}">')
    config = public_config()
    if config:
        encoded = html.escape(json.dumps(config, separators=(',', ':')), quote=True)
        tags.append(f'<meta name="mnl-observability" content="{encoded}">')
    return tags


def content_security_policy(base: str) -> str:
    if not public_config():
        return base
    # Restrict scripts to the official SDK and GA tag host. No unsafe-inline/eval or generic https: source.
    base = base.replace("script-src 'self'", "script-src 'self' https://www.gstatic.com https://www.googletagmanager.com", 1)
    base = base.replace("connect-src 'self'", "connect-src 'self' https://*.google-analytics.com https://www.googletagmanager.com "
                        "https://firebase.googleapis.com "
                        "https://firebaseinstallations.googleapis.com https://firebaseremoteconfig.googleapis.com "
                        "https://firebaselogging.googleapis.com", 1)
    return base.replace("img-src 'self'", "img-src 'self' https://*.google-analytics.com https://www.googletagmanager.com", 1)
