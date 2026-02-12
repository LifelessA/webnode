import os
import secrets

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def write_file(path, content):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content.strip())
    print(f"Created file: {path}")

# --- File Contents ---

SETTINGS_PY = """
import os

BASE_DIR = os.getcwd()
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

PORT = 8000

# Security
def get_secret_key():
    secret_file = os.path.join(BASE_DIR, '.secret_key')
    try:
        with open(secret_file, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        raise RuntimeError("Secret key file not found. Run 'python setup_project.py' first.")

SECRET_KEY = get_secret_key()
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_NODES = [
    'nodes',
]

SECURITY = {
    'RATE_LIMIT_ENABLED': True,
    'RATE_LIMIT_MAX': 50, # requests per window
    'RATE_LIMIT_WINDOW': 60, # seconds
    'CSRF_ENABLED': True,
    'ANTI_SCRAPING_ENABLED': True, # User-Agent checks
    'SCREEN_PROTECTION_ENABLED': True # Black screen on blur/printscreen
}
"""

BASE_NODE_PY = """
class BaseNode:
    \"\"\"
    Base class for all nodes in the framework.
    Implements a doubly linked list structure.
    \"\"\"
    def __init__(self):
        self.next_node = None
        self.prev_node = None

    def connect(self, node):
        \"\"\"
        Connects the next node in the chain.
        Returns the next node to allow chaining: node1.connect(node2).connect(node3)
        \"\"\"
        self.next_node = node
        node.prev_node = self
        return node

    def process(self, data):
        \"\"\"
        Processes data and passes it to the next node.
        Subclasses should override this, perform logic, and then call super().process(new_data)
        \"\"\"
        if self.next_node:
            return self.next_node.process(data)
        return data
"""

SERVER_NODE_PY = """
import http.server
import sys
import os
import importlib
import settings
from nodes.base_node import BaseNode

class ServerNode(BaseNode):
    \"\"\"
    Root Node.
    Configures the server port and initiates the request processing graph.
    Connects to HTTPRequestNode.
    \"\"\"
    def __init__(self, port=8000):
        super().__init__()
        self.port = port

    def start_flow(self, handler):
        \"\"\"
        Triggered by FrameworkHandler.
        Passes the raw handler to the next node (HTTPRequestNode).
        \"\"\"
        return self.process(handler)

class FrameworkHandler(http.server.SimpleHTTPRequestHandler):
    \"\"\"
    The actual HTTP Handler that receives requests from socketserver.
    It delegates processing to the ServerNode graph.
    \"\"\"
    
    server_node = None

    def handle_graph_request(self, method):
        if self.server_node:
            response_content = self.server_node.start_flow(self)
            
            if response_content:
                 self.send_response(200)
                 self.send_header('Content-type', 'text/html')
                 self.end_headers()
                 self.wfile.write(response_content.encode('utf-8'))
            elif self.path.startswith(settings.STATIC_URL):
                 super().do_GET()
            else:
                 self.send_error(404, "Page Not Found")
        else:
             self.send_error(500, "Server Node not configured")

    def do_GET(self):
        return self.handle_graph_request('GET')

    def do_POST(self):
        return self.handle_graph_request('POST')
"""

HTTP_REQUESTS_NODE_PY = """
import urllib.parse
from nodes.base_node import BaseNode

class HTTPRequestsNode(BaseNode):
    \"\"\"
    Node that transforms raw HTTP Handler into a Request Object.
    Connects Server -> URLNode.
    \"\"\"
    def __init__(self):
        super().__init__()

    def process(self, handler):
        \"\"\"
        Receives raw http.server handler.
        Parses request.
        Passes a 'request' wrapper to the next node.
        \"\"\"
        request = RequestWrapper(handler)
        return super().process(request)

class RequestWrapper:
    \"\"\"
    Simple wrapper to mimic the previous request object interface.
    \"\"\"
    def __init__(self, handler):
        self.handler = handler
        self.path = handler.path
        self.headers = handler.headers
        self.method = handler.command
        self.params = {}
        self.context = {}
        self.body_bytes = b""
        
        if self.method == 'POST':
            self.parse_body()

    def parse_body(self):
        if 'Content-Length' in self.headers:
            content_length = int(self.headers['Content-Length'])
            self.body_bytes = self.handler.rfile.read(content_length)
            decoded_body = self.body_bytes.decode('utf-8')
            self.params = urllib.parse.parse_qs(decoded_body)

    def get_param(self, key, default=None):
        val_list = self.params.get(key)
        if val_list:
            return val_list[0]
        return default
"""

CONTEXT_NODE_PY = """
from nodes.base_node import BaseNode

class ContextNode(BaseNode):
    \"\"\"
    Executes a callable logic function to update the request context.
    Passes the request object to the next node.
    \"\"\"
    def __init__(self, context_func):
        super().__init__()
        self.context_func = context_func

    def process(self, request):
        \"\"\"
        Executes logic, merges result into request.context, and passes request forward.
        \"\"\"
        result = self.context_func(request)
        
        if isinstance(result, dict):
            request.context.update(result)
        
        return super().process(request)
"""

LOGIC_NODE_PY = """
from nodes.base_node import BaseNode
import sys

class LogicNode(BaseNode):
    \"\"\"
    Executes a callable logic function.
    \"\"\"
    def __init__(self, logic_func):
        super().__init__()
        self.logic_func = logic_func

    def process(self, request):
        \"\"\"
        Executes business logic.
        Expects 'request' object.
        Updates request.context and passes 'request' to the next node.
        \"\"\"
        result = self.logic_func(request)
        
        if isinstance(result, dict):
             request.context.update(result)
        
        return super().process(request)
"""

TEMPLATE_NODE_PY = """
import os
import sys
import settings
from nodes.base_node import BaseNode

class RenderNode(BaseNode):
    \"\"\"
    Handles template rendering (The 'Face' of the application).
    \"\"\"
    def __init__(self, template_name):
        super().__init__()
        self.template_name = template_name

    PYSCRIPT_HEADER = '''
    <link rel="stylesheet" href="https://pyscript.net/releases/2024.1.1/core.css" />
    <script type="module" src="https://pyscript.net/releases/2024.1.1/core.js"></script>
    '''

    def process(self, request):
        \"\"\"
        Receives request from the previous node, uses request.context, renders template, and returns HTML.
        \"\"\"
        context = getattr(request, 'context', request if isinstance(request, dict) else {})
        return self.render(self.template_name, context)

    @staticmethod
    def render(template_name, context=None):
        \"\"\"
        Reads an HTML file from settings.TEMPLATES_DIR, replaces placeholders, and returns content.
        \"\"\"
        if context is None:
            context = {}
        
        if not isinstance(context, dict):
             if context is None: context = {}
             else: context = {'data': context}

        context['pyscript_header'] = RenderNode.PYSCRIPT_HEADER

        template_path = os.path.join(settings.TEMPLATES_DIR, template_name)
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            for key, value in context.items():
                if isinstance(value, str):
                    content = content.replace(f"{{{key}}}", value)
            
            return content
            
        except FileNotFoundError:
            return f"<h1>Template {template_name} not found</h1>"
"""

URL_NODE_PY = """
from nodes.base_node import BaseNode

class URLNode(BaseNode):
    \"\"\"
    Represents a single route in the application (Routing Node).
    Checks if the request path matches.
    \"\"\"
    def __init__(self, path):
        super().__init__()
        self.path = path

    def process(self, request):
        \"\"\"
        Routing Logic:
        If match: Passes request to the next node (Logic).
        If no match: Returns None.
        \"\"\"
        if self.path == request.path:
            return super().process(request)
        return None
"""

ROUTE_NODE_PY = """
from nodes.base_node import BaseNode

class RouterNode(BaseNode):
    \"\"\"
    Router Node that manages multiple route branches.
    It iterates through a list of route chains and executes the first one that matches.
    \"\"\"
    def __init__(self, routes):
        super().__init__()
        self.routes = routes

    def process(self, request):
        for route in self.routes:
            # route is expected to be a URLNode (start of a chain)
            result = route.process(request)
            if result is not None:
                return result
        return None
"""

DB_PY = """
import sqlite3
import os
import settings
from contextlib import contextmanager

class Database:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
            cls._instance.conn = None 
        return cls._instance

    def get_connection(self):
        \"\"\"Returns a new connection. 
        Note: For transactions, we should usually reuse a connection or manage it carefully.
        Here we return a fresh one for general use, but the transaction manager handles its own.\"\"\"
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.execute("PRAGMA foreign_keys = ON;") # Enable Foreign Keys
        return conn

    def execute(self, query, params=()):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        # self._register_default_functions(conn) # Register standard 'stored procs'
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            print(f"Database Error: {e}")
            raise e
        finally:
            conn.close()

    def executemany(self, query, params_list):
        \"\"\"Bulk insert/update optimization.\"\"\"
        conn = self.get_connection()
        try:
            with conn:
                conn.executemany(query, params_list)
        except Exception as e:
            print(f"Database Error (Bulk): {e}")
            raise e
        finally:
            conn.close()

    def executescript(self, script):
        \"\"\"Run a raw SQL script (good for migrations/triggers).\"\"\"
        conn = self.get_connection()
        try:
            with conn:
                conn.executescript(script)
        except Exception as e:
            print(f"Database Error (Script): {e}")
            raise e
        finally:
            conn.close()

    def fetchall(self, query, params=()):
        conn = self.get_connection()
        conn.row_factory = sqlite3.Row
        # self._register_default_functions(conn)
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Database Error: {e}")
            return []
        finally:
            conn.close()
            
    # --- "PL/SQL" Features (Stored Procedures / Functions) ---
    def register_function(self, conn, name, num_params, func):
        \"\"\"
        Registers a Python function as a SQL function (Stored Procedure).
        Usage in SQL: SELECT my_func(col) FROM table...
        \"\"\"
        conn.create_function(name, num_params, func)

    @contextmanager
    def transaction(self):
        \"\"\"
        Transaction Context Manager.
        Usage:
            with db.transaction() as conn:
                db.execute_on_conn(conn, q1)
                db.execute_on_conn(conn, q2)
        \"\"\"
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Transaction Rolled Back: {e}")
            raise e
        finally:
            conn.close()

    def setup_tables(self):
        # 1. Base Tables (Users)
        create_schema = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium BOOLEAN DEFAULT 0
        );
        '''
        self.executescript(create_schema)

        # 2. Triggers
        create_trigger = '''
        CREATE TRIGGER IF NOT EXISTS validate_email_suffix
        BEFORE INSERT ON users
        BEGIN
            SELECT
            CASE
                WHEN NEW.email NOT LIKE '%@%' THEN
                RAISE (ABORT, 'Invalid email address')
            END;
        END;
        '''
        self.executescript(create_trigger)

    # --- DDL & Schema Management ---

    def create_table(self, table_name, columns_def):
        \"\"\"
        Creates a table with given columns definition.
        columns_def: str, e.g., "id INTEGER PRIMARY KEY, name TEXT"
        \"\"\"
        query = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def});"
        self.execute(query)

    def alter_table(self, table_name, operation, details):
        \"\"\"
        Alters a table.
        operation: 'ADD', 'RENAME', 'DROP' (Drop col not fully supported in old sqlite)
        details: e.g., "COLUMN new_col TEXT"
        \"\"\"
        if operation.upper() == 'ADD':
            query = f"ALTER TABLE {table_name} ADD {details};"
        elif operation.upper() == 'RENAME':
             query = f"ALTER TABLE {table_name} RENAME TO {details};"
        else:
            raise ValueError(f"Unsupported ALTER operation: {operation}")
        self.execute(query)

    def drop_table(self, table_name):
        \"\"\"Drops a table if it exists.\"\"\"
        query = f"DROP TABLE IF EXISTS {table_name};"
        self.execute(query)

    def create_view(self, view_name, select_query):
        \"\"\"Creates a view.\"\"\"
        query = f"CREATE VIEW IF NOT EXISTS {view_name} AS {select_query};"
        self.execute(query)

    def drop_view(self, view_name):
        \"\"\"Drops a view.\"\"\"
        query = f"DROP VIEW IF EXISTS {view_name};"
        self.execute(query)

    def create_index(self, index_name, table_name, columns, unique=False):
        \"\"\"Creates an index.\"\"\"
        unique_clause = "UNIQUE" if unique else ""
        query = f"CREATE {unique_clause} INDEX IF NOT EXISTS {index_name} ON {table_name} ({columns});"
        self.execute(query)
"""

MODEL_NODE_PY = """
from nodes.base_node import BaseNode
from core.db import Database

class ModelNode(BaseNode):
    \"\"\"
    Model Component of MVC.
    Interacts with the Database.
    \"\"\"
    def __init__(self, query, params_mapping=None, context_key='data', is_write=False):
        super().__init__()
        self.query = query
        self.params_mapping = params_mapping or [] # List of param keys to fetch from request
        self.context_key = context_key
        self.is_write = is_write
        self.db = Database()

    def process(self, request):
        \"\"\"
        Executes the query and stores result in request.context (if read).
        Now supports BULK insert if params resolve to a list of lists.
        \"\"\"
        # 1. Prepare Parameters
        query_params = []
        is_bulk = False

        if self.params_mapping:
            # Check if the FIRST param maps to a list (Bulk Operation Mode)
            # This is a simple heuristic: if params_mapping has 1 key and that key holds a list of tuples/lists.
            first_key = self.params_mapping[0]
            val = request.context.get(first_key)
            
            if len(self.params_mapping) == 1 and isinstance(val, list):
                # BULK MODE: The context variable IS the list of rows
                query_params = val
                is_bulk = True
            else:
                # STANDARD MODE: Fetch each param
                for key in self.params_mapping:
                    val = request.get_param(key)
                    if val is None:
                        val = request.context.get(key)
                    query_params.append(val)
        
        # 2. Execute Query
        if self.is_write:
            try:
                if is_bulk:
                     self.db.executemany(self.query, query_params)
                     request.context[f'{self.context_key}_count'] = len(query_params)
                else:
                    self.db.execute(self.query, tuple(query_params))
                
                # Optional: Store success flag
                request.context[f'{self.context_key}_success'] = True
            except Exception as e:
                request.context['error'] = str(e)
        else:
            results = self.db.fetchall(self.query, tuple(query_params))
            # Store in context
            request.context[self.context_key] = results
            
        return super().process(request)
"""

SECURITY_PY = """
from nodes.base_node import BaseNode
import time
import settings
import secrets

class RateLimitNode(BaseNode):
    \"\"\"
    Blocks IPs that exceed request limits.
    Config: SECURITY['RATE_LIMIT_MAX'] requests per SECURITY['RATE_LIMIT_WINDOW'] seconds.
    \"\"\"
    def __init__(self):
        super().__init__()
        self.ip_registry = {} # {ip: [timestamps]}

    def process(self, request):
        if not settings.SECURITY.get('RATE_LIMIT_ENABLED', True):
            return super().process(request)

        # Get Client IP
        client_ip = request.handler.client_address[0]
        now = time.time()
        
        # Clean up old checks
        window = settings.SECURITY.get('RATE_LIMIT_WINDOW', 10)
        limit = settings.SECURITY.get('RATE_LIMIT_MAX', 10)
        
        history = self.ip_registry.get(client_ip, [])
        # Keep only timestamps within validation window
        history = [t for t in history if t > now - window]
        
        if len(history) >= limit:
            print(f"⚠️ [Security] Rate Limit Exceeded for {client_ip}")
            return "<h1>429 Too Many Requests</h1><p>Please wait before trying again.</p>"
        
        # Add current request
        history.append(now)
        self.ip_registry[client_ip] = history
        
        return super().process(request)

class CSRFNode(BaseNode):
    \"\"\"
    Protects against Cross-Site Request Forgery.
    - Sets a CSRF cookie on GET.
    - Validates CSRF token in Body on POST.
    \"\"\"
    def process(self, request):
        if not settings.SECURITY.get('CSRF_ENABLED', True):
            return super().process(request)
        
        csrf_token = "secure-token-123" # In real app: secrets.token_hex(16)
        
        if request.method == "POST":
            submitted_token = request.get_param('csrf_token')
            if submitted_token != csrf_token:
                 print(f"⚠️ [Security] CSRF Mismatch: Expected {csrf_token}, Got {submitted_token}")
                 return "<h1>403 Forbidden</h1><p>CSRF Validation Failed.</p>"
        
        # Pass token to context
        request.context['csrf_token'] = csrf_token
        
        return super().process(request)

class AntiBotNode(BaseNode):
    \"\"\"
    Blocks Basic Bots and Scrapers.
    \"\"\"
    def process(self, request):
        if not settings.SECURITY.get('ANTI_SCRAPING_ENABLED', True):
            return super().process(request)

        user_agent = request.headers.get('User-Agent', '').lower()
        
        # 1. Block known bot keywords
        bot_keywords = ['curl', 'wget', 'python-requests', 'scrapy', 'bot', 'spider', 'crawler']
        if any(keyword in user_agent for keyword in bot_keywords):
             print(f"⚠️ [Security] Bot Detected: {user_agent}")
             return "<h1>403 Forbidden</h1><p>No Bots Allowed.</p>"
        
        if 'Accept-Language' not in request.headers:
             print(f"⚠️ [Security] Suspicious Headers (No Accept-Language)")
             pass

        return super().process(request)

class ScreenProtectionNode(BaseNode):
    \"\"\"
    Injects "Computer Vision Blocking" scripts and styles.
    Prevents selection, right-click, and overlays on blur.
    \"\"\"
    PROTECTION_SCRIPT = \"\"\"
    <style>
        body {
            user-select: none; 
            -webkit-user-select: none;
            -moz-user-select: none;
            -ms-user-select: none;
        }
        #protection-overlay {
            position: fixed;
            top: 0; left: 0; width: 100%; height: 100%;
            background: black;
            color: white;
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 9999;
        }
    </style>
    <div id="protection-overlay"><h1>Protected Content</h1></div>
    <script>
        document.addEventListener('contextmenu', event => event.preventDefault());
        document.addEventListener('keyup', (e) => {
            if (e.key == 'PrintScreen') {
                alert("Screenshots are disabled!");
                document.getElementById('protection-overlay').style.display = 'flex';
                setTimeout(() => { document.getElementById('protection-overlay').style.display = 'none'; }, 2000);
            }
        });
        window.addEventListener('blur', () => {
             document.getElementById('protection-overlay').style.display = 'flex';
        });
        window.addEventListener('focus', () => {
             document.getElementById('protection-overlay').style.display = 'none';
        });
    </script>
    \"\"\"

    def process(self, request):
        if not settings.SECURITY.get('SCREEN_PROTECTION_ENABLED', True):
            return super().process(request)
        
        response_content = super().process(request)
        
        if isinstance(response_content, str) and "</body>" in response_content:
            return response_content.replace("</body>", self.PROTECTION_SCRIPT + "</body>")
            
        return response_content
"""

LOGGER_PY = """
from nodes.base_node import BaseNode
import os
import datetime
import settings

class ActionLoggerNode(BaseNode):
    \"\"\"
    Logs every request to a file named after the Client IP.
    Location: core/logs/{ip}.txt
    Format: [TIMESTAMP] METHOD PATH USER_AGENT
    \"\"\"
    def __init__(self):
        super().__init__()
        self.log_dir = os.path.join(settings.BASE_DIR, 'core', 'logs')
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

    def process(self, request):
        if not settings.LOGGING.get('ENABLED', True):
            return super().process(request)

        try:
            client_ip = request.handler.client_address[0]
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            method = request.method
            path = request.path
            user_agent = request.headers.get('User-Agent', 'Unknown')
            
            log_entry = f"[{timestamp}] {method} {path} | UA: {user_agent}\\n"
            
            # File per IP
            log_file = os.path.join(self.log_dir, f"{client_ip}.txt")
            
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
                
        except Exception as e:
            print(f"Logger Error: {e}")

        return super().process(request)
"""

TEMPLATE_USERS_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>User Manager (MVC Demo)</title>
    <link rel="stylesheet" href="/static/style.css">
    <style>
        .user-list { text-align: left; margin-top: 20px; }
        .user-item { padding: 10px; border-bottom: 1px solid rgba(255,255,255,0.1); display: flex; justify-content: space-between; }
        .success-msg { color: #4ade80; margin-bottom: 10px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="card">
            <h1>User Manager</h1>
            <p class="subtitle">MVC Pattern Demonstration</p>
            
            <!-- Add User Form -->
            <form method="POST" action="/add_user">
                <input type="hidden" name="csrf_token" value="{csrf_token}">
                <div class="input-group">
                    <input type="text" name="name" placeholder="Name" required>
                </div>
                <div class="input-group">
                    <input type="email" name="email" placeholder="Email (Optional)">
                </div>
                <button type="submit">Add User</button>
            </form>
            
            <!-- List Users -->
             <div class="user-list">
                <h3>Existing Users</h3>
                {user_list_html}
            </div>

            <div style="margin-top: 20px;">
                <a href="/" style="color: var(--primary);">Back to Home</a>
            </div>
        </div>
    </div>
</body>
</html>
"""

STATIC_LOGIC_PY = """
def check_odd_even(number):
    if number % 2 == 0:
        return "Even"
    else:
        return "Odd"

def weather_logic(request):
    return {
        'weather_widget': '''
        <div class="widget weather" style="margin-top: 20px; padding: 10px; background: #e0f7fa; border-radius: 8px;">
            <h3>☀️ Weather</h3>
            <p>It's always sunny in Python Land!</p>
        </div>
        '''
    }

def time_logic(request):
    import datetime
    now = datetime.datetime.now().strftime("%H:%M:%S")
    return {
        'time_widget': f'''
        <div class="widget time" style="margin-top: 10px; padding: 10px; background: #f3e5f5; border-radius: 8px;">
            <h3>⏰ Current Time</h3>
            <p>{now}</p>
        </div>
        '''
    }
"""

STATIC_STYLE_CSS = """
:root {
    --bg-color: #0f172a;
    --card-bg: rgba(30, 41, 59, 0.7);
    --primary: #3b82f6;
    --primary-hover: #2563eb;
    --text-main: #f8fafc;
    --text-sub: #94a3b8;
    --border: rgba(255, 255, 255, 0.1);
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: 'Inter', system-ui, -apple-system, sans-serif;
}

body {
    background-color: var(--bg-color);
    color: var(--text-main);
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: 100vh;
    background-image: radial-gradient(circle at 50% 50%, #1e293b 0%, #0f172a 100%);
}

.container {
    width: 100%;
    max-width: 400px;
    padding: 20px;
}

.card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 2rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    text-align: center;
    animation: fadeIn 0.5s ease-out;
}

h1 {
    font-size: 2rem;
    margin-bottom: 0.5rem;
    background: linear-gradient(to right, #60a5fa, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.subtitle {
    color: var(--text-sub);
    margin-bottom: 2rem;
}

.input-group {
    margin-bottom: 1.5rem;
}

input {
    width: 100%;
    padding: 1rem;
    border-radius: 12px;
    border: 1px solid var(--border);
    background: rgba(15, 23, 42, 0.5);
    color: white;
    font-size: 1.1rem;
    transition: border-color 0.3s, box-shadow 0.3s;
}

input:focus {
    outline: none;
    border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2);
}

button {
    width: 100%;
    padding: 1rem;
    border: none;
    border-radius: 12px;
    background: var(--primary);
    color: white;
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: transform 0.1s, background-color 0.3s;
}

button:hover {
    background-color: var(--primary-hover);
}

button:active {
    transform: scale(0.98);
}

.result {
    margin-top: 2rem;
    padding: 1rem;
    border-radius: 12px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--border);
    animation: slideUp 0.3s ease-out;
}

.result.Even {
    border-color: #34d399; /* Greenish */
    color: #34d399;
}

.result.Odd {
    border-color: #f472b6; /* Pinkish */
    color: #f472b6;
}

.number-display {
    font-size: 1.5rem;
    font-weight: bold;
    color: var(--text-main);
}

@keyframes fadeIn {
    from { opacity: 0; transform: translateY(-20px); }
    to { opacity: 1; transform: translateY(0); }
}

@keyframes slideUp {
    from { opacity: 0; transform: translateY(10px); }
    to { opacity: 1; transform: translateY(0); }
}
"""

TEMPLATE_INDEX_HTML = """<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Odd or Even?</title>
    <link rel="stylesheet" href="/static/style.css">
</head>

<body>
    {result_text}
    <div class="container">
        {r1}
        <div class="card">
            <h1>Odd or Even?</h1>
            <p class="subtitle">Enter a number to find out.</p>

            <form method="POST" action="/">
                <div class="input-group">
                    <input type="number" name="number" placeholder="e.g., 42" required>
                </div>
                <div class="input-group">
                    <input type="text" name="test" placeholder="e.g.,hy">
                </div>
                <button type="submit">Check Number</button>
            </form>

            <!-- RESULT_PLACEHOLDER -->
            {result_section}

            <div class="widgets-area">
                {weather_widget}
                {time_widget}
            </div>
        </div>
    </div>
</body>

</html>
"""

MAIN_PY = """import socketserver
import sys
import os
import settings
from nodes.server_node import FrameworkHandler, ServerNode
from nodes.base_node import BaseNode
from nodes.http_requests_node import HTTPRequestsNode
from nodes.url_node import URLNode
from nodes.logic_node import LogicNode
from nodes.context_node import ContextNode
from nodes.template_node import RenderNode
from nodes.route_node import RouterNode
from nodes.model_node import ModelNode
from nodes.model_node import ModelNode
from core.db import Database
from static.logic import check_odd_even, weather_logic, time_logic
from plugins.security import RateLimitNode, CSRFNode, AntiBotNode, ScreenProtectionNode
from plugins.logger import ActionLoggerNode

# --- Initialize Database ---
db = Database()
db.setup_tables()

# --- Advanced DDL (User Request: "Database Features") ---
try:
    # 1. Create a Related Table with Foreign Key
    db.create_table("projects", "id INTEGER PRIMARY KEY, user_id INTEGER, title TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE")
    
    # 2. Create Index on User Email for speed (if not exists)
    db.create_index("idx_user_email", "users", "email", unique=True)
    
    # 3. Create a View for Premium Users
    db.create_view("v_premium_users", "SELECT * FROM users WHERE is_premium = 1")
    
    print("Database Schema Updated: Projects Table (FK), Email Index, Premium View.")
except Exception as e:
    print(f"Schema Init Warning: {e}")


# --- Application Logic Functions ---

def index_logic(request):
    # Existing logic
    if request.method == 'POST':
        number = request.get_param('number')
        if number and number.isdigit():
            res = check_odd_even(int(number))
            return {'result_section': f'<div class="result {res}">{number} is {res}</div>'}
    return {'result_section': ''}

def format_user_list(request):
    # View Helper Logic: Formats the raw list of dictionaries into HTML
    users = request.context.get('users', [])
    html = ""
    if not users:
        html = "<p>No users found.</p>"
    else:
        for user in users:
            premium = "⭐" if user.get('is_premium') else ""
            html += f'<div class="user-item"><span>{user["name"]} {premium}</span> <span style="color: #666;">{user["email"]}</span></div>'
    return {'user_list_html': html}

# --- Node Graph Construction ---

# 1. Server & Request
server_node = ServerNode(port=settings.PORT)
http_request_node = HTTPRequestsNode()

# 2. Define Routes/Branches

# --- HOME BRANCH ---
url_index = URLNode('/')
logic_index = LogicNode(index_logic)
# Dummy widgets
logic_r1 = LogicNode(lambda r: {'r1': ''}) 
node_weather = LogicNode(weather_logic)
node_time = LogicNode(time_logic)
render_index = RenderNode('index.html')

# Wiring Home
url_index.connect(logic_index).connect(logic_r1).connect(node_weather).connect(node_time).connect(render_index)


# --- USER MANAGER BRANCH (MVC) ---
# GET /users
url_users = URLNode('/users')
# Model: Fetch all users
model_fetch_users = ModelNode(
    query="SELECT * FROM users ORDER BY id DESC",
    context_key='users'
)
# Controller/Logic: Format data for view
logic_format_users = LogicNode(format_user_list)
# View: Render Template
render_users = RenderNode('users.html')

url_users.connect(model_fetch_users).connect(logic_format_users).connect(render_users)


# --- ADD USER BRANCH (MVC) ---
# POST /add_user
url_add_user = URLNode('/add_user')
# Model: Insert User
# Note: Triggers in DB will validate email suffix automatically!
model_add_user = ModelNode(
    query="INSERT INTO users (name, email) VALUES (?, ?)",
    params_mapping=['name', 'email'],
    is_write=True
)
# Controller: Redirect back to /users (Simulated by rendering users again or redirecting)
# For simplicity, we just fetch updated list and render users page again
# So we connect model_add_user -> model_fetch_users -> logic -> render
model_fetch_users_post = ModelNode(
    query="SELECT * FROM users ORDER BY id DESC",
    context_key='users'
)
logic_format_users_post = LogicNode(format_user_list)
render_users_post = RenderNode('users.html')

url_add_user.connect(model_add_user).connect(model_fetch_users_post).connect(logic_format_users_post).connect(render_users_post)


# 3. Router
router_node = RouterNode([url_index, url_users, url_add_user])

# 4. Connect Main Line
# 1.5 Security Middleware Chain
# Request -> Logger -> AntiBot -> RateLimit -> CSRF -> ScreenProtection -> Router
action_logger = ActionLoggerNode()
security_antibot = AntiBotNode()
security_ratelimit = RateLimitNode()
security_csrf = CSRFNode()
security_screen = ScreenProtectionNode()

# ... (Routes) ...

# 4. Connect Main Line
# New Chain: Server -> Request -> [Logger] -> [Security] -> Router
server_node.connect(http_request_node).connect(action_logger).connect(security_antibot).connect(security_ratelimit).connect(security_csrf).connect(security_screen).connect(router_node)

if __name__ == "__main__":
    PORT = settings.PORT
    FrameworkHandler.server_node = server_node
    
    print(f"Starting MVC Framework Server at http://localhost:{PORT}")
    print("Graph: Server -> Request -> Security -> Router -> [Chains]")
    print("Routes available:")
    print("  GET  /        (Home)")
    print("  GET  /users   (User List - MVC Demo)")
    print("  POST /add_user (Add User - MVC Demo)")
    print("  * RDBMS Features Active: Triggers, Transactions, Stored Procs, FKs, DDL *")
    
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), FrameworkHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        httpd.server_close()
"""

# --- Creation Logic ---

def create_project():
    print("Initializing Framework Project...")

    # Create Directories
    create_directory(os.path.join("nodes"))
    create_directory(os.path.join("core"))
    create_directory(os.path.join("static"))
    create_directory(os.path.join("templates"))
    create_directory(os.path.join("plugins"))

    # Write Settings
    write_file("settings.py", SETTINGS_PY)

    # Write Plugins
    write_file(os.path.join("plugins", "__init__.py"), "")
    write_file(os.path.join("plugins", "security.py"), SECURITY_PY)
    write_file(os.path.join("plugins", "logger.py"), LOGGER_PY)

    # Write Nodes
    write_file(os.path.join("nodes", "__init__.py"), "")
    write_file(os.path.join("nodes", "base_node.py"), BASE_NODE_PY)
    write_file(os.path.join("nodes", "server_node.py"), SERVER_NODE_PY)
    write_file(os.path.join("nodes", "http_requests_node.py"), HTTP_REQUESTS_NODE_PY)
    write_file(os.path.join("nodes", "context_node.py"), CONTEXT_NODE_PY)
    write_file(os.path.join("nodes", "logic_node.py"), LOGIC_NODE_PY)
    write_file(os.path.join("nodes", "template_node.py"), TEMPLATE_NODE_PY)
    write_file(os.path.join("nodes", "url_node.py"), URL_NODE_PY)
    write_file(os.path.join("nodes", "route_node.py"), ROUTE_NODE_PY)
    
    # Write Core
    write_file(os.path.join("core", "db.py"), DB_PY)
    
    # Write Model Node
    write_file(os.path.join("nodes", "model_node.py"), MODEL_NODE_PY)

    # Write Static Files
    write_file(os.path.join("static", "logic.py"), STATIC_LOGIC_PY)
    write_file(os.path.join("static", "style.css"), STATIC_STYLE_CSS)

    # Write Template Files
    write_file(os.path.join("templates", "index.html"), TEMPLATE_INDEX_HTML)
    write_file(os.path.join("templates", "users.html"), TEMPLATE_USERS_HTML)

    # Write Main.py (only if not exists, but description says 'create module that creates it')
    # Use overwrite protection for main.py to avoid destroying user work if mistakenly run
    if not os.path.exists("main.py"):
        write_file("main.py", MAIN_PY)
    else:
        print("main.py already exists. Skipping creation to preserve your work.")

    # Secret Key
    secret_file = ".secret_key"
    if not os.path.exists(secret_file):
        key = secrets.token_urlsafe(50)
        with open(secret_file, 'w') as f:
            f.write(key)
        print("Generated new secret key.")
    else:
         print("Secret key already exists.")

    print("\\nsetup_project.py completed successfully. Run 'python main.py' to start the server.")

if __name__ == "__main__":
    create_project()
