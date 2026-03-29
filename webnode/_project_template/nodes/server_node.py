"""
nodes/server_node.py — Node Framework

ServerNode  : Root graph node. Holds host/port config.
FrameworkHandler : Actual HTTP handler. Runs the node graph, applies
                   middleware chain, and serializes Response objects.
"""
import http.server
import importlib
import os
import settings
from nodes.base_node import BaseNode

import mimetypes
mimetypes.init()
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')
from nodes.response import Response
from core.sessions import set_session_cookie


# ---------------------------------------------------------------------------
# Utility: import_string
# ---------------------------------------------------------------------------

def import_string(dotted_path):
    """Import a class from a dotted module path string."""
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        print(f"[Import Error] {dotted_path}: {e}")
        return None


# ---------------------------------------------------------------------------
# ServerNode
# ---------------------------------------------------------------------------

class ServerNode(BaseNode):
    """
    Root Node — configures host/port and initiates the request graph.

    Graph Flow:
        ServerNode → HTTPRequestsNode → RouterNode → URLNode → … → RenderNode
    """

    def __init__(self, host='127.0.0.1', port=8000):
        super().__init__()
        self.host = host
        self.port = port

    def start_flow(self, handler):
        """Triggered by FrameworkHandler — passes raw handler into the graph."""
        return self.process(handler)


# ---------------------------------------------------------------------------
# FrameworkHandler
# ---------------------------------------------------------------------------

class FrameworkHandler(http.server.SimpleHTTPRequestHandler):
    """
    HTTP Handler injected into Python's http.server.
    Responsibilities:
      1. Build middleware chain (once, lazily cached)
      2. Run node graph for every request
      3. Serialize Response objects (or plain strings) to HTTP wire format
    """

    server_node = None          # Injected from main.py
    _middleware_chain = None    # Lazily built once
    protocol_version = "HTTP/1.1" # Required for Transfer-Encoding: chunked

    # ------------------------------------------------------------------
    # Middleware Chain (lazy build)
    # ------------------------------------------------------------------

    @classmethod
    def _build_middleware(cls):
        """
        Read settings.MIDDLEWARE list, instantiate each class with a
        get_response callable, and return the outermost middleware callable.
        This is called once the first time a request comes in.
        """
        middleware_classes = []
        for path in getattr(settings, 'MIDDLEWARE', []):
            klass = import_string(path)
            if klass:
                middleware_classes.append(klass)

        # Inner-most handler — just a no-op placeholder (graph handles real work)
        def _inner(request):
            return None

        # Wrap from inside out
        handler = _inner
        for klass in reversed(middleware_classes):
            try:
                handler = klass(handler)
            except Exception as e:
                print(f"[Middleware Warning] Could not load {klass}: {e}")

        cls._middleware_chain = handler
        return handler

    # ------------------------------------------------------------------
    # Core Request Dispatcher
    # ------------------------------------------------------------------

    def handle_graph_request(self, method):
        """
        Unified handler for all HTTP methods.
        1. Build middleware chain (once)
        2. Run middleware → node graph
        3. Serialize Response or string to HTTP
        """
        # 0. Intercept Server-Sent Events background stream
        if self.path.startswith('/__gf_stream__'):
            self._handle_sse_stream()
            return

        # Lazy-build middleware chain
        if FrameworkHandler._middleware_chain is None:
            FrameworkHandler._build_middleware()

        if not self.server_node:
            self._send_response(Response.server_error("ServerNode not configured."))
            return

        # Run middleware (logging, security headers, etc.)
        try:
            FrameworkHandler._middleware_chain(self)
        except Exception:
            pass  # Middleware errors are non-fatal; graph still runs

        # Run the node graph
        try:
            result = self.server_node.start_flow(self)
        except Exception as e:
            print(f"[Graph Error] {e}")
            self._send_response(Response.server_error(str(e)))
            return
        # Serialize result
        if result is None:
            # No route matched → check if it's a static file
            if self.path.startswith(settings.STATIC_URL):
                self._send_response(self._serve_static(self.path))
            else:
                self._send_response(Response.not_found(f"No route matched: {self.path}"))
        elif isinstance(result, Response):
            self._send_response(result)
        elif isinstance(result, str):
            # Backward-compatible: plain string → 200 HTML
            self._send_response(Response(body=result, status=200))
        else:
            # Anything else → try JSON serialize
            import json
            try:
                self._send_response(Response.json(result))
            except Exception:
                self._send_response(Response(body=str(result)))

    # Allowed static file extensions and their MIME types (whitelist only)
    _STATIC_MIME_TYPES = {
        '.css'  : 'text/css',
        '.js'   : 'application/javascript',
        '.png'  : 'image/png',
        '.jpg'  : 'image/jpeg',
        '.jpeg' : 'image/jpeg',
        '.svg'  : 'image/svg+xml',
        '.ico'  : 'image/x-icon',
        '.woff' : 'font/woff',
        '.woff2': 'font/woff2',
        '.ttf'  : 'font/ttf',
        '.webp' : 'image/webp',
        '.gif'  : 'image/gif',
    }

    def _serve_static(self, path: str) -> Response:
        """
        Securely serve a file from settings.STATIC_ROOT.

        Security model (8 layers):
          1. Strip STATIC_URL prefix to get relative path
          2. os.path.normpath() to collapse '..' sequences
          3. Block any path that starts with '..' or '/' after normalization
          4. Build absolute full path from STATIC_ROOT
          5. JAIL CHECK: abs(full_path) must be inside abs(STATIC_ROOT)
          6. File must exist and be a regular file
          7. Extension must be in _STATIC_MIME_TYPES whitelist
          8. Read and return file bytes with correct MIME type

        Always returns a Response — never raises.
        """
        try:
            static_prefix = settings.STATIC_URL  # e.g.  '/static/'

            # Step 1: Strip the URL prefix
            rel_path = path[len(static_prefix):]

            # Strip query string if present
            if '?' in rel_path:
                rel_path = rel_path.split('?')[0]

            # Step 2: Normalize (collapses ../../ etc.)
            safe_path = os.path.normpath(rel_path)

            # Step 3: Block obvious traversal attempts
            if safe_path.startswith('..') or safe_path.startswith('/'):
                if settings.DEBUG:
                    print(f"[Static] Traversal blocked: {path!r}")
                return Response.forbidden('Access denied.')

            # Step 4: Build the candidate full path
            full_path = os.path.join(settings.STATIC_ROOT, safe_path)

            # Step 5: Jail check — must stay inside STATIC_ROOT
            abs_static = os.path.abspath(settings.STATIC_ROOT)
            abs_full   = os.path.abspath(full_path)
            if not abs_full.startswith(abs_static + os.sep) and abs_full != abs_static:
                if settings.DEBUG:
                    print(f"[Static] Jail escape blocked: {abs_full!r}")
                return Response.forbidden('Access denied.')

            # Step 6: MIME type from whitelist only — checked BEFORE file existence
            # (so disallowed extensions always return 403, even if the file is missing,
            # which also prevents probing whether sensitive files exist)
            ext = os.path.splitext(full_path)[1].lower()
            content_type = self._STATIC_MIME_TYPES.get(ext)
            if content_type is None:
                if settings.DEBUG:
                    print(f"[Static] Blocked non-whitelisted extension {ext!r}: {path!r}")
                return Response.forbidden(f'File type not allowed: {ext}')

            # Step 7: Must exist and be a regular file (not a dir, symlink to dir, etc.)
            if not os.path.isfile(full_path):
                return Response.not_found(f'Static file not found: {safe_path}')

            # Step 8: Read and serve
            with open(full_path, 'rb') as f:
                body = f.read()

            return Response(body=body, content_type=content_type, status=200)

        except Exception as e:
            if settings.DEBUG:
                print(f"[Static] Unexpected error serving {path!r}: {e}")
            return Response.server_error('Error serving static file.')

    def _send_response(self, response: Response):
        """Write a Response object to the HTTP socket."""
        # Attach session cookie when a new session was created this request.
        # HTTPRequestsNode.process() stores the RequestWrapper on self._current_request.
        req = getattr(self, '_current_request', None)
        if getattr(req, '_new_session', False):
            sid = getattr(req, 'session_id', None)
            if sid:
                set_session_cookie(response, sid)
                req._new_session = False  # only emit cookie once per response

        body_bytes = response.to_bytes()
        self.send_response(response.status)
        self.send_header('Content-Type', response.content_type)
        self.send_header('Content-Length', str(len(body_bytes)))
        # Custom headers (e.g. Location for redirects, Set-Cookie)
        for key, value in response.headers.items():
            self.send_header(key, value)
        # Security headers (always applied)
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('X-Frame-Options', 'SAMEORIGIN')
        self.end_headers()
        self.wfile.write(body_bytes)
    def _handle_sse_stream(self):
        """Streams background data over a persistent SSE connection."""
        from nodes.response import StreamingResponse
        import urllib.parse
        import json
        
        query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        stream_id = query.get('id', [None])[0]
        
        if not stream_id or stream_id not in StreamingResponse._active_streams:
            self.send_response(404)
            self.end_headers()
            return
            
        gen = StreamingResponse._active_streams[stream_id]
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream')
        self.send_header('Cache-Control', 'no-cache')
        self.send_header('Connection', 'keep-alive')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        
        try:
            for item in gen:
                # SSE data must be a single string (no embedded raw newlines breaking format)
                data_str = json.dumps(str(item))
                # EventSource requires "data: <string>\n\n"
                self.wfile.write(f"data: {data_str}\n\n".encode('utf-8'))
                self.wfile.flush()
        except Exception as e:
            if settings.DEBUG:
                print(f"[SSE Error] {e}")
        finally:
            if stream_id in StreamingResponse._active_streams:
                del StreamingResponse._active_streams[stream_id]

    # ------------------------------------------------------------------
    # HTTP Method Handlers
    # ------------------------------------------------------------------

    def do_GET(self):    self.handle_graph_request('GET')
    def do_POST(self):   self.handle_graph_request('POST')
    def do_PUT(self):    self.handle_graph_request('PUT')
    def do_PATCH(self):  self.handle_graph_request('PATCH')
    def do_DELETE(self): self.handle_graph_request('DELETE')

    # Suppress default request logs (our middleware handles logging)
    def log_message(self, fmt, *args):
        pass