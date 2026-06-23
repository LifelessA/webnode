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
import sqlite3
import json
import os

# ---------------------------------------------------------------------------
# Session Store (SQLite)
# ---------------------------------------------------------------------------

_lock = threading.RLock()  # Safe over-wrap for concurrent thread actions
SESSION_EXPIRY = 86400      # 24 hours in seconds
COOKIE_NAME = 'wn_session'

def _get_db_path():
    import settings
    return os.path.join(settings.BASE_DIR, 'sessions.db')

def _init_db():
    conn = sqlite3.connect(_get_db_path())
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            data       TEXT NOT NULL DEFAULT '{}',
            created_at REAL NOT NULL,
            last_active REAL NOT NULL
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS 
        idx_last_active 
        ON sessions(last_active)
    """)
    conn.commit()
    conn.close()

_init_db()  # Initialize on import

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------

def _cleanup_expired():
    """Remove sessions older than SESSION_EXPIRY."""
    now = time.time()
    conn = sqlite3.connect(_get_db_path())
    try:
        conn.execute("DELETE FROM sessions WHERE last_active < ?", (now - SESSION_EXPIRY,))
        conn.commit()
    finally:
        conn.close()

def _create_session():
    """Create a new DB session and return ID."""
    session_id = secrets.token_urlsafe(32)
    now = time.time()
    with _lock:
        conn = sqlite3.connect(_get_db_path())
        try:
            conn.execute(
                "INSERT INTO sessions (session_id, data, created_at, last_active) VALUES (?, ?, ?, ?)",
                (session_id, '{}', now, now)
            )
            conn.commit()
        finally:
            conn.close()
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
            conn = sqlite3.connect(_get_db_path())
            try:
                row = conn.execute("SELECT session_id FROM sessions WHERE session_id = ?", (existing_id,)).fetchone()
                if row:
                    # Session verified, update activity timestamp
                    conn.execute("UPDATE sessions SET last_active = ? WHERE session_id = ?", (time.time(), existing_id))
                    conn.commit()
                    return existing_id
            finally:
                conn.close()

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
    """Return the data dict for a session."""
    with _lock:
        conn = sqlite3.connect(_get_db_path())
        try:
            row = conn.execute("SELECT data FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                return json.loads(row[0])
            return {}
        finally:
            conn.close()


def set_session_data(session_id: str, key: str, value):
    """Store a key-value pair in the session."""
    with _lock:
        conn = sqlite3.connect(_get_db_path())
        try:
            now = time.time()
            row = conn.execute("SELECT data, created_at FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                data = json.loads(row[0])
                created_at = row[1]
            else:
                data = {}
                created_at = now
            
            data[key] = value
            conn.execute(
                "INSERT OR REPLACE INTO sessions (session_id, data, created_at, last_active) VALUES (?, ?, ?, ?)",
                (session_id, json.dumps(data), created_at, now)
            )
            conn.commit()
        finally:
            conn.close()


def delete_session(session_id: str):
    """Remove a session from the store."""
    with _lock:
        conn = sqlite3.connect(_get_db_path())
        try:
            conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
            conn.commit()
        finally:
            conn.close()
