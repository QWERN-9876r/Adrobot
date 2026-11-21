"""Keitaro Admin API transport."""
import json
import logging
import os
from time import monotonic
from uuid import uuid4
from http.client import HTTPException
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, parse_qsl, urlencode
from urllib.request import HTTPRedirectHandler, Request, build_opener
from adrobot.domain.errors import Problem
from .schemas import validate_response
from .debug import diagnostic, response_body

logger = logging.getLogger('adrobot.keitaro')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class Keitaro:
    mode = "live"

    @property
    def identity(self):
        return self.base

    def __init__(self, base, key):
        url = urlsplit(base)
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise SystemExit("Укажите HTTPS-адрес трекера в KEITARO_URL.")
        self.base = base.rstrip("/") + "/admin_api/v1"
        self.key = key

    def call(self, path, method="GET", body=None):
        parsed = urlsplit(path)
        if method == 'GET' and parsed.path == '/campaigns':
            query = dict(parse_qsl(parsed.query, keep_blank_values=True))
            if 'offset' in query or 'limit' in query:
                query.setdefault('offset', '0')
                query.setdefault('limit', '1000')
                return self._request(parsed._replace(query=urlencode(query)).geturl(), method, body)
            campaigns = {}
            offset = 0
            while True:
                page_path = parsed._replace(query=urlencode({**query, 'offset': offset, 'limit': 1000})).geturl()
                page = self._request(page_path, method, body)
                if not page:
                    return list(campaigns.values())
                if all(row['id'] in campaigns for row in page):
                    raise Problem('Keitaro повторно вернул ту же страницу кампаний.', 502, 'upstream_contract')
                campaigns.update((row['id'], row) for row in page)
                offset += len(page)
        return self._request(path, method, body)

    def _request(self, path, method, body):
        request_id = uuid4().hex[:12]
        # Queries may contain tokens or user input. Log only the API route.
        route = path.split('?', 1)[0].split('#', 1)[0].replace(self.key, '[REDACTED]')
        route = ''.join(char for char in route if char.isprintable())
        started = monotonic()
        status = None
        outcome = 'error'
        failure = '-'
        verbose = os.getenv('KEITARO_DEBUG_HTTP', '1') == '1'
        logger.info('request_started id=%s method=%s path=%s', request_id, method, route)
        try:
            headers = {"Accept": "application/json", "Api-Key": self.key,
                       "User-Agent": "Adrobot/0.1"}
            if body is not None:
                headers["Content-Type"] = "application/json"
            request = Request(self.base + path, method=method,
                              data=None if body is None else json.dumps(body).encode())
            # Request.add_header normalizes capitalization. Keep conventional
            # spelling here as well so diagnostic output matches Swagger.
            request.headers.update(headers)
            if verbose:
                logger.info('http_request id=%s data=%s', request_id, diagnostic({
                    'method': method, 'url': request.full_url, 'headers': dict(request.header_items()),
                    'body': body, 'timeout_seconds': 12,
                }, self.key))
            with build_opener(NoRedirect()).open(request, timeout=12) as response:
                status = response.status
                raw = response.read()
                if verbose:
                    logger.info('http_response id=%s data=%s', request_id, diagnostic({
                        'url': response.geturl(), 'status': status, 'reason': response.reason,
                        'headers': dict(response.headers.items()), 'body': response_body(raw),
                        'body_bytes': len(raw),
                    }, self.key))
                result = validate_response(path, method, json.loads(raw))
                outcome = 'success'
                return result
        except HTTPError as error:
            status = error.code
            failure = 'HTTPError'
            if verbose:
                try:
                    raw = error.read()
                    details = {'body': response_body(raw), 'body_bytes': len(raw)}
                except (OSError, HTTPException) as read_error:
                    details = {'body_read_error': str(read_error)}
                logger.warning('http_response id=%s data=%s', request_id, diagnostic({
                    'url': error.geturl(), 'status': error.code, 'reason': error.reason,
                    'headers': dict(error.headers.items()) if error.headers else {}, **details,
                }, self.key))
            error.close()
            raise Problem(f"Keitaro вернул код HTTP {error.code} для запроса {method} {path}.", 502) from error
        except Problem as error:
            failure = error.code
            if verbose:
                logger.warning('http_validation_error id=%s data=%s', request_id, diagnostic({'code': error.code, 'message': str(error)}, self.key))
            raise
        except (URLError, OSError, HTTPException, ValueError) as error:
            # Classify the cause without logging exception text, which may
            # contain credentials, proxy URLs or fragments of a response.
            failure = type(getattr(error, 'reason', error)).__name__
            if verbose:
                logger.warning('http_error id=%s data=%s', request_id, diagnostic({
                    'type': type(error).__name__, 'message': str(error),
                    'cause_type': failure, 'cause': str(getattr(error, 'reason', error)),
                }, self.key))
            raise Problem(f"Не удалось проверить ответ Keitaro на запрос {method} {path}.", 502) from error
        finally:
            logger.log(logging.INFO if outcome == 'success' else logging.WARNING,
                       'request_finished id=%s method=%s path=%s status=%s outcome=%s duration_ms=%.1f error=%s',
                       request_id, method, route, status if status is not None else '-',
                       outcome, (monotonic() - started) * 1000, failure)
