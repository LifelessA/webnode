"""
plugins/security.py — Node Framework Security Nodes

RateLimitNode       : Block IPs exceeding request rate limits.
CSRFNode            : Per-session CSRF token validation (real tokens, not hardcoded).
AntiBotNode         : Block known bots/scrapers by User-Agent.
ScreenProtectionNode: Inject JS/CSS to block screenshots, copy, right-click.

NOTE: Security nodes work at ANY position in the graph — before OR after HTTPRequestsNode.
"""
from nodes.base_node import BaseNode
import time
import time
import secrets
# threading is already imported above in the file if following standard lib
import threading
import settings


# ---------------------------------------------------------------------------
# Internal helpers — handle both raw FrameworkHandler and RequestWrapper
# ---------------------------------------------------------------------------

def _get_client_ip(request):
    """Return client IP regardless of whether request is raw handler or RequestWrapper."""
    # RequestWrapper: has .handler.client_address
    if hasattr(request, 'handler') and hasattr(request.handler, 'client_address'):
        return request.handler.client_address[0]
    # Raw FrameworkHandler (http.server): has .client_address directly
    if hasattr(request, 'client_address'):
        return request.client_address[0]
    return '0.0.0.0'


def _get_header(request, name, default=''):
    """Get a header value from either RequestWrapper or raw FrameworkHandler."""
    # RequestWrapper: request.headers.get(name)
    if hasattr(request, 'headers') and request.headers is not None:
        return request.headers.get(name, default) or default
    return default


def _get_method(request):
    """Get HTTP method from either RequestWrapper or raw FrameworkHandler."""
    if hasattr(request, 'method'):
        return request.method
    if hasattr(request, 'command'):
        return request.command
    return 'GET'


def _get_context(request):
    """Get or create context dict on request (works on raw handler too)."""
    if not hasattr(request, 'context'):
        request.context = {}
    return request.context


def _get_param(request, key, default=None):
    """Get a form param safely — raw handler has no get_param()."""
    if hasattr(request, 'get_param'):
        return request.get_param(key, default)
    return default


def _ensure_request_wrapper(request):
    """
    If request is a raw FrameworkHandler (placed before HTTPRequestsNode),
    convert it to a RequestWrapper — same as HTTPRequestsNode.process() does.

    This allows security nodes to work at ANY position in the graph.
    """
    # Already a RequestWrapper (has .context, .params, etc.)
    if hasattr(request, 'context'):
        return request
    # Raw FrameworkHandler — convert it
    try:
        from nodes.http_requests_node import RequestWrapper
        return RequestWrapper(request)
    except Exception as e:
        print(f"[Security] Could not wrap handler: {e}")
        return request


# ---------------------------------------------------------------------------
# Rate Limit Node
# ---------------------------------------------------------------------------

class RateLimitNode(BaseNode):
    """
    Blocks IPs that exceed request limits.
    Config via settings.SECURITY:
        RATE_LIMIT_MAX    — max requests per window (default: 50)
        RATE_LIMIT_WINDOW — window in seconds        (default: 60)
    """

    def __init__(self):
        super().__init__()
        self._registry = {}   # {ip: [timestamps]}

    def process(self, request):
        request = _ensure_request_wrapper(request)  # works before OR after HTTPRequestsNode
        if not settings.SECURITY.get('RATE_LIMIT_ENABLED', True):
            return super().process(request)

        client_ip = _get_client_ip(request)
        now       = time.time()
        window    = settings.SECURITY.get('RATE_LIMIT_WINDOW', 60)
        limit     = settings.SECURITY.get('RATE_LIMIT_MAX', 50)

        history = self._registry.get(client_ip, [])
        history = [t for t in history if t > now - window]

        if len(history) >= limit:
            print(f"⚠️  [RateLimit] {client_ip} exceeded {limit} req/{window}s")
            return (
                '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;'
                'padding:60px;background:#0f172a;color:#e2e8f0">'
                '<h1 style="color:#f87171;font-size:3rem">429</h1>'
                '<p>Too Many Requests. Please wait.</p></body></html>'
            )

        history.append(now)
        self._registry[client_ip] = history
        return super().process(request)


# ---------------------------------------------------------------------------
# CSRF Node  (per-session real tokens)
# ---------------------------------------------------------------------------

class CSRFNode(BaseNode):
    """
    Per-session CSRF protection (Fixed Memory Leak).
    """

    _token_store = {}
    _lock = threading.RLock()
    TOKEN_EXPIRY = 3600

    @classmethod
    def _cleanup_expired(cls):
        # Called while _lock is held
        now = time.time()
        expired = [
            ip for ip, data in cls._token_store.items()
            if now - data['created'] > cls.TOKEN_EXPIRY
        ]
        for ip in expired:
            del cls._token_store[ip]

    @classmethod
    def get_or_create_token(cls, client_ip):
        with cls._lock:
            cls._cleanup_expired()
            now = time.time()
            existing = cls._token_store.get(client_ip)
            if existing and now - existing['created'] < cls.TOKEN_EXPIRY:
                return existing['token']
            
            token = secrets.token_hex(32)
            cls._token_store[client_ip] = {
                'token': token,
                'created': now
            }
            return token

    def process(self, request):
        request = _ensure_request_wrapper(request)
        if not settings.SECURITY.get('CSRF_ENABLED', True):
            return super().process(request)

        client_ip = _get_client_ip(request)
        method = _get_method(request)

        if method == 'GET':
            token = CSRFNode.get_or_create_token(client_ip)
            _get_context(request)['csrf_token'] = token
            return super().process(request)

        elif method == 'POST':
            expected = CSRFNode.get_or_create_token(client_ip)
            submitted = _get_param(request, 'csrf_token')
            
            if not expected or not submitted:
                print(f"⚠️  [CSRF] Missing token from {client_ip}")
                return (
                    '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;'
                    'padding:60px;background:#0f172a;color:#e2e8f0">'
                    '<h1 style="color:#fb923c;font-size:3rem">403</h1>'
                    '<p>CSRF token missing.</p></body></html>'
                )

            # Constant-time comparison
            if not secrets.compare_digest(expected, submitted):
                print(f"⚠️  [CSRF] Token mismatch from {client_ip}")
                return (
                    '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;'
                    'padding:60px;background:#0f172a;color:#e2e8f0">'
                    '<h1 style="color:#fb923c;font-size:3rem">403</h1>'
                    '<p>CSRF validation failed. Please go back and try again.</p></body></html>'
                )

            # Do NOT rotate token to allow AJAX and multiple tabs
            _get_context(request)['csrf_token'] = expected
            return super().process(request)

        else:
            return super().process(request)


# ---------------------------------------------------------------------------
# Anti-Bot Node
# ---------------------------------------------------------------------------

class AntiBotNode(BaseNode):
    """
    Blocks requests from known bots and scrapers based on User-Agent.
    """

    _BOT_KEYWORDS = [
        'curl', 'wget', 'python-requests', 'python-urllib',
        'scrapy', 'bot', 'spider', 'crawler', 'http-kit',
        'java/', 'go-http', 'libwww', 'lwp-',
    ]

    def process(self, request):
        request = _ensure_request_wrapper(request)  # works before OR after HTTPRequestsNode
        if not settings.SECURITY.get('ANTI_SCRAPING_ENABLED', True):
            return super().process(request)

        user_agent = _get_header(request, 'User-Agent', '').lower()

        if any(kw in user_agent for kw in self._BOT_KEYWORDS):
            print(f"⚠️  [AntiBot] Blocked: {user_agent[:60]}")
            return (
                '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;'
                'padding:60px;background:#0f172a;color:#e2e8f0">'
                '<h1 style="color:#fb923c;font-size:3rem">403</h1>'
                '<p>Automated requests are not allowed.</p></body></html>'
            )

        return super().process(request)


# ---------------------------------------------------------------------------
# Screen Protection Node
# ---------------------------------------------------------------------------

class ScreenProtectionNode(BaseNode):
    """
    Injects JS + CSS into the response HTML to:
    - Disable right-click context menu
    - Disable text selection
    - Show black overlay on window blur (screen switch)
    - Show black overlay on PrintScreen key
    """

    _PROTECTION_SCRIPT = """
<style>
  body {
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
  }
  #__gf_overlay {
    position: fixed; top: 0; left: 0;
    width: 100%; height: 100%;
    background: #000;
    color: #fff;
    display: none;
    align-items: center;
    justify-content: center;
    flex-direction: column;
    z-index: 2147483647;
    font-family: sans-serif;
  }
</style>
<div id="__gf_overlay">
  <h2 style="margin-bottom:8px">🔒 Protected Content</h2>
  <p style="color:#aaa;font-size:0.9rem">Click the window to continue</p>
</div>
<script>
(function() {
  var overlay = document.getElementById('__gf_overlay');
  document.addEventListener('contextmenu', function(e) { e.preventDefault(); });
  document.addEventListener('keyup', function(e) {
    if (e.key === 'PrintScreen') {
      overlay.style.display = 'flex';
      setTimeout(function() { overlay.style.display = 'none'; }, 3000);
    }
  });
  document.addEventListener('keydown', function(e) {
    // Block Ctrl+S, Ctrl+U, Ctrl+P
    if (e.ctrlKey && ['s', 'u', 'p'].includes(e.key.toLowerCase())) {
      e.preventDefault();
    }
  });
  window.addEventListener('blur', function() { overlay.style.display = 'flex'; });
  window.addEventListener('focus', function() { overlay.style.display = 'none'; });
})();
</script>
"""

    def process(self, request):
        request = _ensure_request_wrapper(request)  # works before OR after HTTPRequestsNode
        if not settings.SECURITY.get('SCREEN_PROTECTION_ENABLED', True):
            return super().process(request)

        result = super().process(request)

        if isinstance(result, str) and '</body>' in result:
            return result.replace('</body>', self._PROTECTION_SCRIPT + '</body>')

        return result