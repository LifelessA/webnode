"""
nodes/template_node.py — Node Framework

RenderNode : Template rendering node. Reads HTML files and injects context.

Template Syntax (in HTML files):
    {{ var }}              — variable substitution (HTML-escaped)
    {{ var | safe }}       — variable substitution (raw/unescaped)
    {% for x in items %}   — loop block
    {% endfor %}
    {% if condition %}     — conditional block (evaluates Python expression)
    {% elif condition %}
    {% else %}
    {% endif %}
    {% extends "base.html" %}  — template inheritance (first line of child)
    {% block name %}           — define/override a named block
    {% endblock %}
    {% include "partial.html" %} — include another template

Backward compatible: {key} style (no spaces) still works.
"""
import os
import re
import ast
import html
import threading
import settings
from nodes.base_node import BaseNode


# ---------------------------------------------------------------------------
# DotDict — makes dict keys accessible via dot notation for templates
# ---------------------------------------------------------------------------

class DotDict(dict):
    """Dict subclass that allows attribute-style access (d.key == d['key'])."""
    def __getattr__(self, key):
        try:
            val = self[key]
            return _wrap_value(val)
        except KeyError:
            return ''
    def __setattr__(self, key, value):
        self[key] = value


def _wrap_value(val):
    """Recursively wrap dicts/lists so dot-access works in templates."""
    if isinstance(val, dict) and not isinstance(val, DotDict):
        return DotDict(val)
    if isinstance(val, list):
        return [_wrap_value(item) for item in val]
    return val


def _wrap_context(ctx):
    """Wrap top-level context dict values for dot-access in templates."""
    return {k: _wrap_value(v) for k, v in ctx.items()}


# ---------------------------------------------------------------------------
# Mini Template Engine
# ---------------------------------------------------------------------------

class TemplateEngine:
    """
    Processes Node template syntax.
    Single-pass renderer: inheritance → includes → tags → variables.
    """

    _file_cache = {}
    _cache_lock = threading.Lock()

    BLOCK_RE    = re.compile(r'\{%\s*block\s+(\w+)\s*%\}(.*?)\{%\s*endblock\s*%\}', re.DOTALL)
    EXTENDS_RE  = re.compile(r'^\s*\{%\s*extends\s+["\']([^"\']+)["\']\s*%\}')
    INCLUDE_RE  = re.compile(r'\{%\s*include\s+["\']([^"\']+)["\']\s*%\}')
    VAR_RE      = re.compile(r'\{\{\s*(.+?)\s*\}\}')
    TAG_RE      = re.compile(r'\{%\s*(.+?)\s*%\}')

    # Legacy {key} style (no spaces) — handled last for backward compat
    LEGACY_RE   = re.compile(r'\{(\w+)\}')

    def __init__(self, template_dir):
        self.template_dir = template_dir

    def _read_file(self, name):
        import settings
        
        # In DEBUG mode — always read fresh
        # (developer wants live changes)
        if settings.DEBUG:
            path = os.path.join(self.template_dir, name)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except FileNotFoundError:
                return f'<!-- Template not found: {html.escape(name)} -->'
        
        # In PRODUCTION mode — use cache
        cache_key = f"{self.template_dir}:{name}"
        
        with TemplateEngine._cache_lock:
            if cache_key in TemplateEngine._file_cache:
                return TemplateEngine._file_cache[cache_key]
        
        # Not in cache — read from disk
        path = os.path.join(self.template_dir, name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
        except FileNotFoundError:
            content = f'<!-- Template not found: {html.escape(name)} -->'
        
        # Store in cache
        with TemplateEngine._cache_lock:
            TemplateEngine._file_cache[cache_key] = content
        
        return content

    @classmethod
    def cache_clear(cls):
        with cls._cache_lock:
            cls._file_cache.clear()
            print("[TemplateEngine] Cache cleared.")

    # ---------------------------------------------------------------------------
    # Safe Expression Evaluator
    # ---------------------------------------------------------------------------

    # Whitelist of AST node types safe for template expressions
    _SAFE_NODES = (
        ast.Expression,
        # Operators
        ast.BoolOp, ast.BinOp, ast.UnaryOp,
        # Comparisons
        ast.Compare, ast.Subscript,
        # Names & literals
        ast.Attribute, ast.Name, ast.Constant,
        # Collections
        ast.List, ast.Dict, ast.Tuple, ast.Set,
        # Boolean operators
        ast.And, ast.Or, ast.Not,
        # Comparison operators
        ast.Eq, ast.NotEq, ast.Lt, ast.LtE,
        ast.Gt, ast.GtE, ast.In, ast.NotIn,
        # Arithmetic operators
        ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Mod, ast.USub,
        # Misc
        ast.Index, ast.Load, ast.IfExp,
    )

    def _safe_eval(self, expr: str, context: dict) -> str:
        """
        Safely evaluate a template expression.

        Security model:
          1. Immediate block if '__' appears anywhere (dunder attack prevention)
          2. AST whitelist: only explicitly allowed node types are permitted
          3. eval() run with empty __builtins__ as final safety net

        Returns '' for any blocked or errored expression.
        """
        # Rule 1: Block ALL dunder access (__class__, __import__, etc.)
        if '__' in expr:
            if settings.DEBUG:
                print(f"[Template] Blocked dunder expression: {expr!r}")
            return ''

        # Rule 2: Parse and walk AST — only whitelisted node types allowed
        try:
            tree = ast.parse(expr, mode='eval')
        except SyntaxError:
            return ''

        for node in ast.walk(tree):
            if not isinstance(node, self._SAFE_NODES):
                if settings.DEBUG:
                    print(
                        f"[Template] Blocked unsafe AST node "
                        f"{type(node).__name__!r} in expression: {expr!r}"
                    )
                return ''

        # Rule 3: Compile + eval with empty builtins (belt-and-suspenders)
        try:
            result = eval(
                compile(tree, '<template>', 'eval'),
                {'__builtins__': {}},
                context,
            )
            return str(result)
        except Exception:
            return ''

    def render(self, template_name, context=None):
        if context is None:
            context = {}
        context = _wrap_context(context)
        source = self._read_file(template_name)
        rendered_html = self._process(source, context, template_name)
        return self._inject_pyscript(rendered_html)

    def _inject_pyscript(self, html_content):
        # Auto-detect Python-First frontend (PyScript)
        # Scan for <script type="py">, <py-script>, py-click, etc.
        if not re.search(r'<script\s+type=[\'"]py[\'"]|<py-script>|py-[a-z]+=|<py-env>', html_content, re.IGNORECASE):
            return html_content
            
        pyscript_tags = (
            '\n    <!-- PyScript Auto-Injected by Node -->\n'
            '    <link rel="stylesheet" href="https://pyscript.net/releases/2024.1.1/core.css" />\n'
            '    <script type="module" src="https://pyscript.net/releases/2024.1.1/core.js"></script>\n'
        )
        
        # Inject right before </head>
        if re.search(r'</head>', html_content, re.IGNORECASE):
            return re.sub(r'(?i)</head>', f'{pyscript_tags}</head>', html_content, count=1)
        return pyscript_tags + html_content

    def _process(self, source, context, template_name=''):
        # 1. Template inheritance
        ext_match = self.EXTENDS_RE.match(source)
        if ext_match:
            parent_name = ext_match.group(1)
            parent_src  = self._read_file(parent_name)
            # Extract child blocks
            child_blocks = {}
            for m in self.BLOCK_RE.finditer(source):
                child_blocks[m.group(1)] = m.group(2)
            # Fill parent blocks with child overrides
            def replace_block(m):
                name    = m.group(1)
                default = m.group(2)
                return child_blocks.get(name, default)
            source = self.BLOCK_RE.sub(replace_block, parent_src)

        # 2. Includes
        def replace_include(m):
            inc_name = m.group(1)
            inc_src  = self._read_file(inc_name)
            return self._process(inc_src, context)

        source = self.INCLUDE_RE.sub(replace_include, source)

        # 3. Control flow tags — for / if, and variable substitution inside text nodes
        source = self._process_tags(source, context)

        return source

    def _process_vars(self, text, context):
        import re, html
        def replace_var(m):
            expr = m.group(1)
            safe = False
            if expr.endswith('| safe') or expr.endswith('|safe'):
                expr = re.sub(r'\|\s*safe$', '', expr).strip()
                safe = True
            value = self._safe_eval(expr, context)
            return value if safe else html.escape(value)

        def replace_legacy(m):
            key = m.group(1)
            val = context.get(key)
            if val is not None:
                return html.escape(str(val)) if isinstance(val, str) else str(val)
            return m.group(0)

        text = self.VAR_RE.sub(replace_var, text)
        return self.LEGACY_RE.sub(replace_legacy, text)

    def _process_tags(self, source, context):
        """
        Process {% for %}, {% if %}, {% elif %}, {% else %}, {% endif %},
        {% endfor %} — recursive descent tokenizer.
        """
        # Parse source into (type, value) parts directly using finditer
        # This avoids the split/re-join bug where {% %} delimiters are lost.
        parts = []
        pos = 0
        for m in self.TAG_RE.finditer(source):
            if m.start() > pos:
                parts.append(('text', source[pos:m.start()]))
            parts.append(('tag', m.group(1).strip()))
            pos = m.end()
        if pos < len(source):
            parts.append(('text', source[pos:]))

        return ''.join(self._run_parts(parts, context))


    def _eval_tokens(self, tokens, context, start=0):
        """
        Walk tokens linearly; handle for/if blocks via recursion.
        tokens alternates: [text, tag, text, tag, ...]
        """
        result = []
        i = start
        tag_re = self.TAG_RE

        # Re-split into (text, tag) pairs for easier processing
        parts = []
        full = ''.join(tokens)
        pos = 0
        for m in self.TAG_RE.finditer(full):
            parts.append(('text', full[pos:m.start()]))
            parts.append(('tag', m.group(1).strip()))
            pos = m.end()
        parts.append(('text', full[pos:]))

        return self._run_parts(parts, context)

    def _run_parts(self, parts, context, idx=0):
        result = []
        while idx < len(parts):
            kind, value = parts[idx]
            if kind == 'text':
                result.append(self._process_vars(value, context))
                idx += 1

            elif kind == 'tag':
                tag = value

                if tag.startswith('for ') and ' in ' in tag:
                    # {% for item in collection %}
                    loop_expr = tag[4:]   # 'item in collection'
                    var_name, iter_expr = [x.strip() for x in loop_expr.split(' in ', 1)]
                    try:
                        if '__' in iter_expr:
                            collection = []
                        else:
                            collection = eval(iter_expr, {'__builtins__': {}}, context)
                    except Exception:
                        collection = []

                    # Collect body until endfor
                    body_parts, idx = self._collect_until(parts, idx + 1, 'endfor')
                    for item in collection:
                        loop_ctx = dict(context)
                        loop_ctx[var_name] = item
                        result.append(''.join(self._run_parts(body_parts, loop_ctx)))

                elif tag.startswith('if '):
                    condition = tag[3:].strip()
                    body_parts, else_parts, idx = self._collect_if(parts, idx + 1)
                    try:
                        if '__' in condition:
                            test = False
                        else:
                            test = bool(eval(condition, {'__builtins__': {}}, context))
                    except Exception:
                        test = False
                    if test:
                        result.append(''.join(self._run_parts(body_parts, context)))
                    elif else_parts:
                        result.append(''.join(self._run_parts(else_parts, context)))

                elif tag in ('endfor', 'endif', 'endblock', 'else') or tag.startswith('elif '):
                    # These are handled by their parent collectors
                    break

                elif tag.startswith('block '):
                    block_name = tag[6:].strip()
                    try:
                        body_parts, idx = \
                            self._collect_until(
                                parts, idx + 1, 
                                'endblock'
                            )
                        result.append(
                            ''.join(
                                self._run_parts(
                                    body_parts, context
                                )
                            )
                        )
                    except Exception as e:
                        # Log the error
                        if settings.DEBUG:
                            print(
                                f"[Template] Block error "
                                f"in '{block_name}': {e}"
                            )
                        # Show HTML comment in DEBUG
                        # Silent in production
                        if settings.DEBUG:
                            result.append(
                                f'<!-- Block Error '
                                f'[{block_name}]: '
                                f'{html.escape(str(e))} -->'
                            )
                        # Always advance idx safely
                        # to prevent infinite loop
                        try:
                            _, idx = self._collect_until(
                                parts, idx + 1,
                                'endblock'
                            )
                        except Exception:
                            idx = len(parts)

                else:
                    idx += 1  # Unknown tag — skip

            else:
                idx += 1

        return result

    def _collect_until(self, parts, start, end_tag):
        """Collect parts until a specific end tag. Returns (body_parts, next_idx)."""
        depth = 0
        body = []
        i = start
        opener = end_tag.replace('end', '')  # e.g. 'for' from 'endfor'
        while i < len(parts):
            kind, value = parts[i]
            if kind == 'tag':
                if value == end_tag and depth == 0:
                    return body, i + 1
                if value.startswith(opener + ' '):
                    depth += 1
                elif value == end_tag:
                    depth -= 1
            body.append((kind, value))
            i += 1
        return body, i

    def _collect_if(self, parts, start):
        """Collect if body and optional else body."""
        if_body = []
        else_body = []
        in_else = False
        i = start
        depth = 0
        while i < len(parts):
            kind, value = parts[i]
            if kind == 'tag':
                if value == 'endif' and depth == 0:
                    return if_body, else_body, i + 1
                if value.startswith('if '):
                    depth += 1
                elif value == 'endif':
                    depth -= 1
                elif value == 'else' and depth == 0:
                    in_else = True
                    i += 1
                    continue
            if in_else:
                else_body.append((kind, value))
            else:
                if_body.append((kind, value))
            i += 1
        return if_body, else_body, i


# ---------------------------------------------------------------------------
# RenderNode
# ---------------------------------------------------------------------------

class RenderNode(BaseNode):
    """
    Template rendering node.
    Reads an HTML template, injects context from request, returns HTML string.
    """

    # Shared engine instance (reads templates from settings.TEMPLATES_DIR)
    _engine = None

    @classmethod
    def _get_engine(cls):
        if cls._engine is None:
            cls._engine = TemplateEngine(settings.TEMPLATES_DIR)
        return cls._engine

    def __init__(self, template_name):
        super().__init__()
        self.template_name = template_name

    def process(self, request):
        """
        Receive request from upstream node.
        Execute any attached downstream logic nodes to populate context.
        Extract context from request.context.
        Render template and return HTML string.
        """
        if self.next_node:
            nodes_to_process = []
            from nodes.route_node import RouterNode
            if isinstance(self.next_node, RouterNode):
                nodes_to_process = self.next_node.routes
            else:
                nodes_to_process = [self.next_node]
                
            for n in nodes_to_process:
                try:
                    n.process(request)
                except Exception as e:
                    return self._on_error(e, request, node=n)

        if hasattr(request, 'context'):
            context = request.context
        elif isinstance(request, dict):
            context = request
        else:
            context = {}

        engine = self._get_engine()
        return engine.render(self.template_name, context)

    @staticmethod
    def render(template_name, context=None):
        """
        Static convenience method — render without a node instance.
        Example:
            html = RenderNode.render('index.html', {'title': 'Home'})
        """
        engine = TemplateEngine(settings.TEMPLATES_DIR)
        return engine.render(template_name, context or {})