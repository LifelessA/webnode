"""
core/sessions.py — WebNode Framework Session Management

Cookie-based session system.
- Session IDs are generated using secrets.token_urlsafe(32)
- Sessions are stored in memory (Python dict) with 24-hour expiry
- Thread-safe using threading.Lock()
- Cookie name: wn_session

Usage:
    from core.sessions import get_session_id, set_session_cookie

    # In RequestWrapper (http_requests_node.py): get_session_id(request)
    # In _send_response (server_node.py): set_session_cookie(response, session_id)
"""
import secrets
import time
import threading

# ---------------------------------------------------------------------------
# Session Store
# ---------------------------------------------------------------------------

SESSION_STORE = {}          # { session_id: { '_created': timestamp, ...data } }
_lock = threading.RLock()  # Re-entrant — safe for nested acquisitions in same thread
SESSION_EXPIRY = 86400      # 24 hours in seconds
COOKIE_NAME = 'wn_session'


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _cleanup_expired():
    """
    Remove sessions older than SESSION_EXPIRY.
    CONTRACT: Must be called while holding _lock (assumes lock is already acquired).
    """
    now = time.time()
    expired = [
        sid for sid, data in SESSION_STORE.items()
        if now - data.get('_created', now) > SESSION_EXPIRY
    ]
    for sid in expired:
        del SESSION_STORE[sid]


def _create_session():
    """
    Create a brand-new session and return its ID.
    Called from within get_session_id() which already holds _lock.
    Uses _lock via RLock re-entrancy — safe to call while lock is held.
    """
    session_id = secrets.token_urlsafe(32)
    with _lock:  # RLock: safe even if caller already holds it
        SESSION_STORE[session_id] = {'_created': time.time()}
    return session_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_session_id(request) -> str:
    """
    Returns the session ID for this request.

    Priority:
      1. request.session_id (set by RequestWrapper from Cookie header)
      2. If session_id exists in SESSION_STORE → return it
      3. Otherwise create a new session and mark request._new_session = True

    Signature is identical to the old IP-based get_session_id(request)
    so all existing logic files (cart_logic.py etc.) work unchanged.
    """
    with _lock:
        _cleanup_expired()

    # RequestWrapper sets request.session_id from the Cookie header
    existing_id = getattr(request, 'session_id', None)

    if existing_id:
        with _lock:
            if existing_id in SESSION_STORE:
                # Refresh the session timestamp (rolling expiry)
                SESSION_STORE[existing_id]['_created'] = time.time()
                return existing_id

    # No valid session found → create a new one
    new_id = _create_session()
    # Mark on the request so server_node.py knows to Set-Cookie
    try:
        request._new_session = True
        request.session_id = new_id
    except (AttributeError, TypeError):
        pass  # WSGI wrapper or raw handler — best effort

    return new_id


def set_session_cookie(response, session_id: str):
    """
    Adds a Set-Cookie header to a Response object.
    Called from server_node._send_response() when request._new_session is True.

    Cookie attributes:
        HttpOnly    — not accessible via JavaScript (XSS protection)
        SameSite=Strict — CSRF protection
        Path=/      — valid for entire site
        Max-Age=86400 — 24 hours
    """
    cookie_value = (
        f"{COOKIE_NAME}={session_id}; "
        f"HttpOnly; SameSite=Strict; Path=/; Max-Age={SESSION_EXPIRY}"
    )
    response.headers['Set-Cookie'] = cookie_value


def get_session_data(session_id: str) -> dict:
    """Return the data dict for a session (excluding internal keys)."""
    with _lock:
        data = SESSION_STORE.get(session_id, {})
        return {k: v for k, v in data.items() if not k.startswith('_')}


def set_session_data(session_id: str, key: str, value):
    """Store a key-value pair in the session."""
    with _lock:
        if session_id not in SESSION_STORE:
            SESSION_STORE[session_id] = {'_created': time.time()}
        SESSION_STORE[session_id][key] = value


def delete_session(session_id: str):
    """Remove a session from the store (e.g. on logout)."""
    with _lock:
        SESSION_STORE.pop(session_id, None)