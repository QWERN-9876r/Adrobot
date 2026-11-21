"""Full HTTP diagnostics with credential redaction, emitted as single-line JSON."""
import json
import os
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

MASK = '[REDACTED]'
SENSITIVE = re.compile(r'authorization|cookie|password|passwd|secret|token|api.?key', re.I)


def diagnostic(value, api_key):
    secrets = [api_key, os.getenv('KEITARO_API_KEY')]

    def text(value):
        for secret in secrets:
            if secret:
                value = value.replace(secret, MASK)
        # Also mask credentials embedded in proxy or other diagnostic URLs.
        value = re.sub(r'(https?://)[^\s/@]+:[^\s/@]+@', r'\1' + MASK + '@', value)
        return value

    def clean(value):
        if isinstance(value, dict):
            return {text(str(key)): MASK if SENSITIVE.search(str(key)) else clean(item)
                    for key, item in value.items()}
        if isinstance(value, (list, tuple)):
            return [clean(item) for item in value]
        if isinstance(value, str):
            value = text(value)
            if value.startswith(('https://', 'http://')):
                parts = urlsplit(value)
                query = urlencode([(key, MASK if SENSITIVE.search(key) else text(item))
                                   for key, item in parse_qsl(parts.query, keep_blank_values=True)])
                return urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
        return value

    return json.dumps(clean(value), ensure_ascii=False, default=str)


def response_body(raw):
    try:
        return json.loads(raw)
    except (ValueError, UnicodeError):
        return raw.decode('utf-8', errors='replace')
