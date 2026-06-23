"""
nodes/url_node.py — Node Framework

URLNode : Route matching node. Supports both exact and dynamic paths.

Exact match:
    URLNode('/about')          -> matches only '/about'

Dynamic segments:
    URLNode('/users/<id>')     -> matches '/users/42',  url_params = {'id': '42'}
    URLNode('/files/<pk:int>') -> matches '/files/7',   url_params = {'pk': 7}  (int cast)
    URLNode('/p/<slug:str>')   -> matches '/p/hello',   url_params = {'slug': 'hello'}

Dynamic segments extracted from the URL are stored in request.url_params dict.
They can also be accessed via request.get_param('id').
"""
import re
from nodes.base_node import BaseNode


# ---------------------------------------------------------------------------
# Internal: compile a URL pattern into a regex
# ---------------------------------------------------------------------------

_TYPE_PATTERNS = {
    'int': r'(\d+)',
    'str': r'([^/]+)',
    '':    r'([^/]+)',   # default — same as str
}


def _compile_pattern(path_pattern):
    """
    Convert a URL pattern string into a (compiled_regex, param_names, param_types) tuple.

    Examples:
        '/users/<id>'       →  regex: r'^/users/([^/]+)$'   params: ['id']
        '/items/<pk:int>'   →  regex: r'^/items/(\d+)$'     params: ['pk']
        '/about'            →  regex: r'^/about$'            params: []
    """
    param_names = []
    param_types = []

    def replace_segment(m):
        full = m.group(1)          # e.g. 'id' or 'pk:int'
        if ':' in full:
            name, type_hint = full.split(':', 1)
        else:
            name, type_hint = full, ''
        param_names.append(name.strip())
        param_types.append(type_hint.strip())
        pattern = _TYPE_PATTERNS.get(type_hint.strip(), _TYPE_PATTERNS['str'])
        return pattern

    # Escape the rest of the path, then un-escape our placeholders
    escaped = re.escape(path_pattern)
    # re.escape turns < > into \< \> — handle both escaped and raw
    escaped = escaped.replace(r'\<', '<').replace(r'\>', '>')
    regex_str = re.sub(r'<([^>]+)>', replace_segment, escaped)
    regex_str = f'^{regex_str}$'

    return re.compile(regex_str), param_names, param_types


# ---------------------------------------------------------------------------
# URLNode
# ---------------------------------------------------------------------------

class URLNode(BaseNode):
    """
    Route matching node in the graph.

    - Exact match  : URLNode('/about')
    - Dynamic      : URLNode('/users/<id>'),  URLNode('/items/<pk:int>')
    """

    def __init__(self, path, methods=None):
        super().__init__()
        self.path_pattern = path
        # Default: GET and POST both allowed. None means allow ALL methods
        self.allowed_methods = methods
        self._regex, self._param_names, self._param_types = _compile_pattern(path)
        self._is_exact = len(self._param_names) == 0

    def _match(self, request_path):
        """
        Try to match request_path against this node's pattern.
        Returns a dict of url params on match, or None on no match.
        """
        if self._is_exact:
            return {} if request_path == self.path_pattern else None

        m = self._regex.match(request_path)
        if not m:
            return None

        url_params = {}
        for i, name in enumerate(self._param_names):
            raw = m.group(i + 1)
            type_hint = self._param_types[i]
            if type_hint == 'int':
                try:
                    raw = int(raw)
                except ValueError:
                    return None  # Path matched pattern but value isn't int
            url_params[name] = raw

        return url_params

    def process(self, request):
        """
        Check if request.path matches this node's pattern and if method is allowed.
        On match:  populate request.url_params, pass to next node.
        No match:  return None (RouterNode tries next branch).
        """
        # Step 1: Path match
        url_params = self._match(request.path)
        if url_params is None:
            return None

        # Step 2: Method check
        if self.allowed_methods is not None:
            method = request.method.upper()
            if method not in self.allowed_methods:
                from nodes.response import Response
                return Response(
                    body='Method Not Allowed',
                    status=405,
                    headers={
                        'Allow': ', '.join(self.allowed_methods)
                    }
                )

        # Step 3: Pass through
        request.url_params = url_params
        return super().process(request)

    def __repr__(self):
        return f'<URLNode pattern={self.path_pattern!r}>'