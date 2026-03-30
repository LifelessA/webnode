"""
nodes/response.py — Node Response Object

Each node can now return a Response object instead of a plain string.
Isse status code, content-type, aur custom headers control mein aate hain.

Usage examples:
    return Response('<h1>Hello</h1>')
    return Response.json({'status': 'ok'})
    return Response.redirect('/login')
    return Response.not_found('User not found')
    return Response.forbidden('Access denied')
"""
import json as _json
import html as _html


class Response:
    """
    A structured HTTP response object.
    Can be returned from any node (LogicNode, ContextNode, etc.)
    FrameworkHandler automatically detects and serializes it.
    """

    def __init__(self, body='', status=200, content_type='text/html; charset=utf-8', headers=None):
        """
        Args:
            body          : str or bytes — response body
            status        : int          — HTTP status code (200, 201, 302, 404 …)
            content_type  : str          — MIME type header value
            headers       : dict         — extra headers to send, e.g. {'Location': '/foo'}
        """
        self.body = body
        self.status = status
        self.content_type = content_type
        self.headers = headers or {}

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    @staticmethod
    def json(data, status=200):
        """Return a JSON response.
        Example:
            return Response.json({'users': []})
        """
        body = _json.dumps(data, ensure_ascii=False, indent=2)
        return Response(body=body, status=status, content_type='application/json; charset=utf-8')

    @staticmethod
    def redirect(url, status=302):
        """Return an HTTP redirect.
        Example:
            return Response.redirect('/dashboard')
        """
        body = f'<html><body>Redirecting to <a href="{url}">{_html.escape(url)}</a></body></html>'
        return Response(body=body, status=status, content_type='text/html; charset=utf-8',
                        headers={'Location': url})

    @staticmethod
    def not_found(message='404 Not Found'):
        """Return a 404 response."""
        body = (
            f'<!DOCTYPE html><html><head><title>404 Not Found</title>'
            f'<style>body{{font-family:sans-serif;text-align:center;padding:60px;'
            f'background:#0f172a;color:#e2e8f0}}'
            f'h1{{color:#f87171;font-size:4rem;margin:0}}p{{color:#94a3b8}}</style></head>'
            f'<body><h1>404</h1><p>{_html.escape(message)}</p></body></html>'
        )
        return Response(body=body, status=404)

    @staticmethod
    def forbidden(message='403 Forbidden'):
        """Return a 403 response."""
        body = (
            f'<!DOCTYPE html><html><head><title>403 Forbidden</title>'
            f'<style>body{{font-family:sans-serif;text-align:center;padding:60px;'
            f'background:#0f172a;color:#e2e8f0}}'
            f'h1{{color:#fb923c;font-size:4rem;margin:0}}p{{color:#94a3b8}}</style></head>'
            f'<body><h1>403</h1><p>{_html.escape(message)}</p></body></html>'
        )
        return Response(body=body, status=403)

    @staticmethod
    def server_error(message='500 Internal Server Error'):
        """Return a 500 response."""
        body = (
            f'<!DOCTYPE html><html><head><title>500 Server Error</title>'
            f'<style>body{{font-family:sans-serif;text-align:center;padding:60px;'
            f'background:#0f172a;color:#e2e8f0}}'
            f'h1{{color:#f43f5e;font-size:4rem;margin:0}}p{{color:#94a3b8}}</style></head>'
            f'<body><h1>500</h1><p>{_html.escape(message)}</p></body></html>'
        )
        return Response(body=body, status=500)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def to_bytes(self):
        """Convert body to bytes for writing to socket."""
        if isinstance(self.body, bytes):
            return self.body
        return self.body.encode('utf-8')

    def __repr__(self):
        return f'<Response status={self.status} content_type={self.content_type!r}>'

class StreamingResponse(Response):
    """
    A response that streams data to the browser progressively via Server-Sent Events (SSE).
    """
    _active_streams = {}

    def __init__(self, generator, headers=None):
        super().__init__(body='', status=200, content_type='text/html; charset=utf-8', headers=headers)
        self.generator = generator
        self.is_stream = True
        self.stream_id = f"gfs_{id(self)}"
        StreamingResponse._active_streams[self.stream_id] = self.generator

    def __str__(self):
        # Native proxy into HTML templates. Instantiates a background SSE EventSource JS socket!
        return (
            f"<div id='{self.stream_id}' style='display:contents;'></div>"
            f"<script>"
            f"new EventSource('/__gf_stream__?id={self.stream_id}').onmessage = function(e){{"
            f"  document.getElementById('{self.stream_id}').innerHTML = JSON.parse(e.data);"
            f"}};"
            f"</script>"
        )

    def __repr__(self):
        return f'<StreamingResponse status={self.status}>'