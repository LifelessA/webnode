"""
core/errors.py — Node Error Reporting System

Jab koi bhi node fail hota hai, yeh module clearly batata hai:
  - Konsa node crash hua
  - Kya input tha
  - Kya error tha (readable)
  - Kahan fix karna hai

AI-Friendly Design:
  - Structured JSON format — AI directly parse kar sakta hai
  - No ambiguous stack traces — pinpointed node name
  - Context preserved — request path + method bhi log hota hai
"""
import traceback
import datetime
import json
import os
import settings


class NodeError(Exception):
    """
    Raised when a node fails during graph execution.
    Carries structured context so errors are easy to diagnose.
    """
    def __init__(self, node_name, node_type, original_error, input_data=None):
        self.node_name  = node_name
        self.node_type  = node_type
        self.original   = original_error
        self.input_data = input_data
        self.timestamp  = datetime.datetime.now().isoformat()
        super().__init__(str(original_error))

    def to_dict(self):
        return {
            "error":      "NodeError",
            "node":       self.node_name,
            "type":       self.node_type,
            "message":    str(self.original),
            "timestamp":  self.timestamp,
            "input_type": type(self.input_data).__name__,
        }

    def __str__(self):
        return (
            f"\n{'='*55}\n"
            f"  NODE ERROR DETECTED\n"
            f"{'='*55}\n"
            f"  Node     : {self.node_name} ({self.node_type})\n"
            f"  Error    : {type(self.original).__name__}: {self.original}\n"
            f"  Time     : {self.timestamp}\n"
            f"{'='*55}\n"
            f"  FIX HINT : Check the '{self.node_name}' node logic.\n"
            f"{'='*55}"
        )


class NodeErrorReporter:
    """
    Central error reporting hub for the node graph.

    Features:
      - Console output: colored, readable, pinpointed
      - File logging: structured JSON per error
      - HTML error page: shown in browser during DEBUG mode
      - AI summary: machine-readable JSON for AI agents to parse
    """

    LOG_DIR = os.path.join(settings.BASE_DIR, 'core', 'logs', 'errors')

    @classmethod
    def _ensure_dir(cls):
        os.makedirs(cls.LOG_DIR, exist_ok=True)

    @classmethod
    def report(cls, node_name, node_type, error, request=None, tb_str=None):
        """
        Report an error from a node.

        Args:
            node_name : str   — node variable name (e.g. 'urlnode_node_12')
            node_type : str   — node class name  (e.g. 'URLNode')
            error     : Exception
            request   : RequestWrapper | None
            tb_str    : str | None — traceback string
        """
        # Build structured record
        record = {
            "timestamp" : datetime.datetime.now().isoformat(),
            "node"      : node_name,
            "node_type" : node_type,
            "error_type": type(error).__name__,
            "message"   : str(error),
            "request"   : {
                "method": getattr(request, 'method', 'UNKNOWN'),
                "path"  : getattr(request, 'path',   'UNKNOWN'),
            } if request else None,
            "traceback" : tb_str or traceback.format_exc(),
        }

        # 1. Console
        cls._print_console(record)

        # 2. File log
        cls._write_log(record)

        # 3. Return HTML error page or JSON
        return cls._make_error_page(record)

    @classmethod
    def _print_console(cls, record):
        print(f"\n{'═'*55}")
        print(f"  ⚠️  NODE ERROR")
        print(f"{'═'*55}")
        print(f"  Node     : {record['node']} ({record['node_type']})")
        print(f"  Error    : {record['error_type']}: {record['message']}")
        print(f"  Request  : {record['request']['method'] if record['request'] else 'N/A'}"
              f" {record['request']['path'] if record['request'] else ''}")
        print(f"{'═'*55}")
        # Show only last 3 traceback lines to avoid noise
        if record['traceback']:
            lines = [l for l in record['traceback'].strip().splitlines() if l.strip()]
            for line in lines[-3:]:
                print(f"  {line.strip()}")
        print(f"{'═'*55}\n")

    @classmethod
    def _write_log(cls, record):
        try:
            cls._ensure_dir()
            # 1. Daily JSONL log
            date_str  = datetime.date.today().isoformat()
            log_file  = os.path.join(cls.LOG_DIR, f"{date_str}.jsonl")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')

            # 2. Live error state file — node editor reads this to highlight nodes red
            # Format: {"node_type": {"node": ..., "message": ..., "timestamp": ...}}
            state_file = os.path.join(settings.BASE_DIR, 'core', 'logs', 'error_state.json')
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
            except Exception:
                state = {}

            state[record['node_type']] = {
                "node"      : record['node'],
                "node_type" : record['node_type'],
                "message"   : record['message'],
                "error_type": record['error_type'],
                "timestamp" : record['timestamp'],
            }
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)

        except Exception as e:
            print(f"[ErrorReporter] Could not write log: {e}")

    @classmethod
    def clear_errors(cls):
        """Clear the live error state (call on successful deploy)."""
        state_file = os.path.join(settings.BASE_DIR, 'core', 'logs', 'error_state.json')
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump({}, f)
        except Exception:
            pass


    @classmethod
    def _make_error_page(cls, record):
        """Return an HTML error page (DEBUG mode) or minimal 500 page."""
        if not getattr(settings, 'DEBUG', False):
            return (
                '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;'
                'padding:60px;background:#0f172a;color:#e2e8f0">'
                '<h1 style="color:#f43f5e;font-size:3rem">500</h1>'
                '<p>An internal error occurred.</p></body></html>'
            )

        tb_html = (record['traceback'] or '').replace('<', '&lt;').replace('>', '&gt;')
        req     = record['request'] or {}
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Node Error — {record['node']}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0f172a; color: #e2e8f0; font-family: 'Segoe UI', sans-serif; padding: 2rem; }}
    .header {{ background: #f43f5e22; border: 1px solid #f43f5e55; border-radius: 12px;
               padding: 1.5rem 2rem; margin-bottom: 1.5rem; }}
    .badge {{ display: inline-block; background: #f43f5e; color: white; font-size: 0.75rem;
              font-weight: bold; padding: 2px 10px; border-radius: 20px; margin-bottom: 0.5rem; }}
    h1 {{ font-size: 1.6rem; color: #fca5a5; margin-bottom: 0.4rem; }}
    .meta {{ color: #94a3b8; font-size: 0.85rem; }}
    .card {{ background: #1e293b; border-radius: 10px; padding: 1.2rem 1.5rem; margin-bottom: 1rem; }}
    .card h3 {{ font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.1em;
                color: #64748b; margin-bottom: 0.6rem; }}
    .node-name {{ font-size: 1.1rem; font-weight: bold; color: #38bdf8; }}
    .error-msg  {{ font-size: 1rem; color: #fca5a5; }}
    pre {{ background: #0f172a; border-radius: 8px; padding: 1rem; overflow-x: auto;
           font-size: 0.8rem; color: #94a3b8; line-height: 1.6; border: 1px solid #1e293b; }}
    .fix-hint {{ background: #14532d33; border: 1px solid #16a34a55; border-radius: 10px;
                 padding: 1rem 1.5rem; color: #86efac; }}
    .fix-hint h3 {{ color: #4ade80; margin-bottom: 0.4rem; font-size: 0.9rem; }}
  </style>
</head>
<body>
  <div class="header">
    <div class="badge">NODE ERROR</div>
    <h1>⚠ {record['error_type']}: {record['message']}</h1>
    <div class="meta">{record['timestamp']} &nbsp;|&nbsp; {req.get('method','?')} {req.get('path','?')}</div>
  </div>

  <div class="card">
    <h3>Which Node Failed</h3>
    <div class="node-name">{record['node']}</div>
    <div class="meta" style="margin-top:4px">Type: {record['node_type']}</div>
  </div>

  <div class="card">
    <h3>Traceback</h3>
    <pre>{tb_html}</pre>
  </div>

  <div class="fix-hint">
    <h3>💡 How to Fix</h3>
    <p>Open the <strong>{record['node']}</strong> node in the Node Editor and check its
       logic. Each node is independent — only this node needs to be fixed.</p>
  </div>

  <div class="card" style="margin-top:1rem">
    <h3>AI-Readable JSON (for AI agents)</h3>
    <pre>{json.dumps(record, indent=2, ensure_ascii=False)}</pre>
  </div>
</body>
</html>"""


def wrap_node_process(node, method_name='process'):
    """
    Decorator utility — wraps a node's process() method with error reporting.
    Called automatically by BaseNode when ERROR_REPORTING is enabled in settings.

    Usage (manual):
        wrap_node_process(my_node)
    """
    original = getattr(node, method_name)

    def safe_process(data):
        try:
            return original(data)
        except Exception as e:
            tb = traceback.format_exc()
            node_name = getattr(node, '_node_name',
                                f"{type(node).__name__}_at_{id(node)}")
            return NodeErrorReporter.report(
                node_name  = node_name,
                node_type  = type(node).__name__,
                error      = e,
                request    = data if hasattr(data, 'path') else None,
                tb_str     = tb,
            )

    setattr(node, method_name, safe_process)
    return node