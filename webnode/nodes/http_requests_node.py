"""
nodes/http_requests_node.py — Node Framework

HTTPRequestsNode : Converts raw http.server handler into a clean RequestWrapper.
RequestWrapper   : Mimics a real request object with helpers for params, JSON, files.
"""
import urllib.parse
import json as _json
import io
from nodes.base_node import BaseNode


class HTTPRequestsNode(BaseNode):
    """
    Converts the raw HTTP handler → RequestWrapper.

    Graph position: ServerNode → HTTPRequestsNode → RouterNode
    """

    def __init__(self):
        super().__init__()

    def process(self, handler):
        # If already wrapped by a security node placed before us, skip re-wrapping
        if hasattr(handler, 'context'):
            return super().process(handler)
        request = RequestWrapper(handler)
        # Store back-reference so server_node can retrieve _new_session / session_id
        handler._current_request = request
        return super().process(request)


class RequestWrapper:
    """
    A clean request object built from the low-level http.server handler.

    Attributes:
        path         : str   — URL path without query string (e.g. '/users')
        method       : str   — 'GET', 'POST', 'PUT', 'PATCH', 'DELETE'
        headers      : dict-like — HTTP request headers
        query_params : dict  — parsed URL query string (?key=value)
        params       : dict  — parsed form body (POST/PUT/PATCH)
        context      : dict  — shared context dict passed between nodes
        body_bytes   : bytes — raw request body
        url_params   : dict  — dynamic URL params e.g. {'id': '42'} from /users/<id>

    HTTP Method → CRUD Mapping:
        GET    → Read    (idempotent)
        POST   → Create
        PUT    → Update (full replace, idempotent)
        PATCH  → Update (partial)
        DELETE → Delete (idempotent)
    """

    def __init__(self, handler):
        self.handler = handler
        parsed_url = urllib.parse.urlparse(handler.path)

        self.path = parsed_url.path
        self.headers = handler.headers
        self.method = handler.command

        # URL query string: ?n=5&foo=bar → {'n': '5', 'foo': 'bar'}
        self.query_params = {
            k: v[0] if len(v) == 1 else v
            for k, v in urllib.parse.parse_qs(parsed_url.query).items()
        }

        self.params = {}       # form-encoded body params
        self.context = {}      # shared context dict for ContextNode/ModelNode
        self.body_bytes = b""
        self.url_params = {}   # dynamic URL segments set by URLNode

        # --- Session: read wn_session cookie ----------------------------
        self._new_session = False       # True if no existing session found
        self.session_id = None          # filled below
        raw_cookie = self.headers.get('Cookie', '') or ''
        for crumb in raw_cookie.split(';'):
            crumb = crumb.strip()
            if crumb.startswith('wn_session='):
                self.session_id = crumb[len('wn_session='):].strip()
                break
        # session validation / creation is deferred to get_session_id()
        # (called lazily by logic nodes via static/helpers.py)
        # ----------------------------------------------------------------

        # Parse body for methods that carry a payload
        if self.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            self._parse_body()

    # ------------------------------------------------------------------
    # Body Parsing
    # ------------------------------------------------------------------

    def _parse_body(self):
        content_length = int(self.headers.get('Content-Length', 0) or 0)
        if content_length <= 0:
            return
        self.body_bytes = self.handler.rfile.read(content_length)
        content_type = self.headers.get('Content-Type', '')

        if 'application/json' in content_type:
            # JSON body is lazy-parsed via get_json()
            pass
        elif 'application/x-www-form-urlencoded' in content_type:
            decoded = self.body_bytes.decode('utf-8', errors='replace')
            self.params = urllib.parse.parse_qs(decoded)
        elif 'multipart/form-data' in content_type:
            # Multipart — manual boundary parser (cgi removed in Python 3.13)
            boundary = None
            for part in content_type.split(';'):
                part = part.strip()
                if part.startswith('boundary='):
                    boundary = part[9:].strip().encode()
                    break

            if boundary:
                self._files = {}
                delimiter = b'--' + boundary
                end_delimiter = delimiter + b'--'
                parts_raw = self.body_bytes.split(delimiter)
                for raw_part in parts_raw[1:]:
                    if raw_part.startswith(b'--') or len(raw_part) < 4:
                        continue
                    # Separate headers from body
                    if b'\r\n\r\n' in raw_part:
                        header_sec, body_sec = raw_part.split(b'\r\n\r\n', 1)
                    elif b'\n\n' in raw_part:
                        header_sec, body_sec = raw_part.split(b'\n\n', 1)
                    else:
                        continue
                    # Strip trailing boundary delimiter
                    body_sec = body_sec.rstrip(b'\r\n')
                    # Parse Content-Disposition
                    header_text = header_sec.decode('utf-8', errors='replace')
                    name = None
                    filename = None
                    for hline in header_text.split('\r\n'):
                        if 'Content-Disposition' in hline:
                            for seg in hline.split(';'):
                                seg = seg.strip()
                                if seg.startswith('name='):
                                    name = seg[5:].strip('"')
                                elif seg.startswith('filename='):
                                    filename = seg[9:].strip('"')
                    if name is None:
                        continue
                    if filename is not None:
                        # File upload — store as simple object
                        class _UploadedFile:
                            def __init__(self, fname, data):
                                self.filename = fname
                                self._data = data
                                self.file = io.BytesIO(data)
                            def read(self):
                                return self._data
                        self._files[name] = _UploadedFile(filename, body_sec)
                    else:
                        self.params[name] = [body_sec.decode('utf-8', errors='replace')]

    # ------------------------------------------------------------------
    # Public Getters
    # ------------------------------------------------------------------

    @property
    def content_type(self):
        """Returns Content-Type header value (lowercase)."""
        return self.headers.get('Content-Type', '').lower()

    @property
    def query_string(self):
        """Raw query string from the URL (without leading '?')."""
        parsed = urllib.parse.urlparse(self.handler.path)
        return parsed.query

    @property
    def args(self):
        """Alias for query_params (Flask-compatible)."""
        return self.query_params

    @property
    def form(self):
        """Alias for parsed form params as flat dict (Flask-compatible)."""
        return self.get_form()

    def get_param(self, key, default=None):
        """Get a form-body or URL-param value by key."""
        # Check url_params first (dynamic route segments)
        if key in self.url_params:
            return self.url_params[key]
        val_list = self.params.get(key)
        if val_list:
            return val_list[0]
        return default

    def get_json(self):
        """
        Parse and return the JSON body as a Python dict/list.
        Returns None if body is not valid JSON.

        Example (LogicNode):
            data = request.get_json()
            name = data.get('name', '')
        """
        try:
            return _json.loads(self.body_bytes.decode('utf-8'))
        except (ValueError, UnicodeDecodeError):
            return None

    def get_form(self):
        """
        Return form-encoded POST body as a flat dict.
        Each value is unwrapped from the list that parse_qs produces.
        Returns empty dict if no form data.

        Example (LogicNode):
            data = request.get_form()
            name = data.get('name', '')
        """
        if not self.params:
            return {}
        return {
            k: v[0] if isinstance(v, list) and len(v) == 1 else v
            for k, v in self.params.items()
        }

    def get_file(self, key):
        """
        Get an uploaded file (from multipart/form-data) by field name.
        Returns a file-like object with:
            .filename  : str   — original filename
            .read()    : bytes — file contents

        Example (LogicNode):
            upload = request.get_file('avatar')
            if upload:
                data = upload.file.read()
        """
        return getattr(self, '_files', {}).get(key)

    def __repr__(self):
        return f'<Request {self.method} {self.path}>'
