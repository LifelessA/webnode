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
    def __init__(self, host='127.0.0.1', port=8000):
        super().__init__()
        self.host = host
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

    def do_PUT(self):
        return self.handle_graph_request('PUT')

    def do_PATCH(self):
        return self.handle_graph_request('PATCH')

    def do_DELETE(self):
        return self.handle_graph_request('DELETE')
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
    
    Supported HTTP Methods and CRUD Mapping:
    Method | CRUD Action      | Idempotent?* | Description
    -------|------------------|--------------|---------------------------------------------
    GET    | Read             | Yes          | Requests data from a resource.
    POST   | Create           | No           | Submits data to be processed.
    PUT    | Update (Full)    | Yes          | Replaces the target resource with the request payload.
    PATCH  | Update (Partial) | No           | Applies partial modifications to a resource.
    DELETE | Delete           | Yes          | Deletes the specified resource.
    \"\"\"
    def __init__(self, handler):
        self.handler = handler
        parsed_url = urllib.parse.urlparse(handler.path)
        self.path = parsed_url.path
        self.headers = handler.headers
        self.method = handler.command
        
        # Parse query parameters from URL
        self.query_params = {k: v[0] if len(v) == 1 else v for k, v in urllib.parse.parse_qs(parsed_url.query).items()}
        
        self.params = {}
        self.context = {}
        self.body_bytes = b""
        
        # Parse body for methods that typically include a payload
        if self.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
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
        # Standardize paths to single leading slash for comparison
        req_path = request.path if request.path.startswith('/') else '/' + request.path
        config_path = self.path if self.path.startswith('/') else '/' + self.path
        
        # Remove trailing slashes for identical matching unless root
        req_path_clean = req_path.rstrip('/') if req_path != '/' else '/'
        config_path_clean = config_path.rstrip('/') if config_path != '/' else '/'

        if req_path_clean == config_path_clean:
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
                <input type="hidden" name="csrf_token" value="{csrf_token}">
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




# --- NODE EDITOR GUI STRINGS ---

WEBNODE_HTML = """
<!DOCTYPE html>
<html lang="en">

<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>WebNode Editor</title>
  <link rel="stylesheet" href="styles.css">
  <!-- Monaco Editor Core -->
  <script>var require = { paths: { 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs' } };</script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/loader.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/editor/editor.main.nls.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.45.0/min/vs/editor/editor.main.js"></script>
</head>

<body>

  <!-- Top Toolbar -->
  <div id="toolbar">
    <div class="logo">⚡ Node Editor</div>
    <div class="controls">
      <button class="btn btn-primary" id="btn-deploy">Deploy & Run</button>
      <button class="btn btn-danger" id="btn-stop">Stop Server</button>
      <button class="btn btn-secondary" id="btn-save">Save JSON</button>
      <button class="btn btn-secondary" id="btn-clear">Clear Array</button>
    </div>
    <div id="status-indicator">● Offline</div>
  </div>

  <!-- Main Workspace -->
  <div id="workspace">
    <!-- Sidebar: Node Palette -->
    <div id="sidebar">
      <h3>Library</h3>
      <p style="font-size: 0.75rem; color: #aaa; margin-bottom: 15px;">
        Drag to add nodes.<br>
        Double-click node or wire to delete.
      </p>

      <div class="category">Core</div>
      <div class="palette-node" draggable="true" data-type="ServerNode">Server Node</div>
      <div class="palette-node" draggable="true" data-type="HTTPRequestsNode">HTTP Request</div>
      <div class="palette-node" draggable="true" data-type="URLNode">URL Router</div>
      <div class="palette-node" draggable="true" data-type="LogicNode">Logic (Python)</div>
      <div class="palette-node" draggable="true" data-type="ContextNode">Context (Python)</div>

      <div class="category">Views & DB</div>
      <div class="palette-node" draggable="true" data-type="RenderNode">Render Template</div>
      <div class="palette-node" draggable="true" data-type="ModelNode">Model (SQL)</div>

      <div class="category">Security & Logging</div>
      <div class="palette-node" draggable="true" data-type="ActionLoggerNode">Action Logger</div>
      <div class="palette-node" draggable="true" data-type="AntiBotNode">Anti-Bot</div>
      <div class="palette-node" draggable="true" data-type="RateLimitNode">Rate Limit</div>
      <div class="palette-node" draggable="true" data-type="CSRFNode">CSRF Token</div>
      <div class="palette-node" draggable="true" data-type="ScreenProtectionNode">Screen Protection</div>
    </div>

    <!-- Canvas Area -->
    <div id="canvas-container">
      <!-- SVG for Wires (Noodles) -->
      <svg id="wire-layer" width="100%" height="100%"></svg>

      <!-- Nodes Container (Pan/Zoom layer) -->
      <div id="canvas-layer">
        <!-- Nodes will be injected here dynamically -->

        <!-- Default Server Node Example -->
        <div class="node server-node status-green" id="node-1" style="left: 100px; top: 100px;" data-type="ServerNode">
          <div class="node-header">
            Server Node
            <div class="port out-port" data-node="node-1" data-port="out"></div>
          </div>
          <div class="node-body">
            <label>IP Address</label>
            <input type="text" value="127.0.0.1" class="node-input ip-input">
            <label>Port</label>
            <input type="number" value="8000" class="node-input port-input">
            <div class="node-actions">
              <button class="node-btn">Live/Stop</button>
            </div>
          </div>
        </div>

        <!-- Example URL Node -->
        <div class="node url-node status-red" id="node-2" style="left: 450px; top: 100px;" data-type="URLNode">
          <div class="node-header">
            <div class="port in-port" data-node="node-2" data-port="in"></div>
            URL Router
            <div class="port out-port" data-node="node-2" data-port="out"></div>
          </div>
          <div class="node-body">
            <label>Path</label>
            <input type="text" value="/api/data" class="node-input path-input">
          </div>
        </div>

      </div>
    </div>
  </div>

  <!-- Node Templates for Drag & Drop -->
  <div id="node-templates" style="display: none;">

    <!-- ServerNode Template -->
    <div class="node server-node status-red" data-type="ServerNode">
      <div class="node-header">
        Server Node
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <label>IP Address</label>
        <input type="text" value="127.0.0.1" class="node-input ip-input">
        <label>Port</label>
        <input type="number" value="8000" class="node-input port-input">
        <div class="node-actions"><button class="node-btn">Live/Stop</button></div>
      </div>
    </div>

    <!-- HTTPRequest Template -->
    <div class="node http-node status-red" data-type="HTTPRequestsNode">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        HTTP Request
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Parses raw request</p>
      </div>
    </div>

    <!-- URLNode Template -->
    <div class="node url-node status-red" data-type="URLNode">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        URL Router
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <label>Path</label>
        <input type="text" value="/" class="node-input path-input">
      </div>
    </div>

    <!-- LogicNode Template (Monaco) -->
    <div class="node logic-node status-red" data-type="LogicNode" style="width: 400px;">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        Logic (Python)
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <label>Function Logic (def node_logic(request):)</label>
        <!-- Monaco instance will mount here -->
        <div class="monaco-container"></div>
      </div>
    </div>

    <!-- RenderNode Template -->
    <div class="node render-node status-red" data-type="RenderNode" style="width: 400px;">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        Render Template
      </div>
      <div class="node-body">
        <label>Template Filename (Optional)</label>
        <input type="text" placeholder="e.g. index.html" class="node-input filename-input">
        <label>HTML Content</label>
        <div class="monaco-container"></div>
      </div>
    </div>

    <!-- ModelNode Template -->
    <div class="node model-node status-red" data-type="ModelNode" style="width: 320px;">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        Model (SQL Database)
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <label>SQL Query</label>
        <input type="text" value="SELECT * FROM users" class="node-input query-input">
        <label>Params Mapping (comma separated)</label>
        <input type="text" placeholder="e.g., id, name" class="node-input params-input">
        <label>Context Key</label>
        <input type="text" value="data" class="node-input context-input">
        <div style="display:flex; align-items:center; gap:5px; margin-top:5px;">
          <input type="checkbox" class="is-write-input"> <label style="margin:0;">Is Write Query?</label>
        </div>
      </div>
    </div>

    <!-- ContextNode Template (Monaco) -->
    <div class="node context-node status-red" data-type="ContextNode" style="width: 400px;">
      <div class="node-header">
        <div class="port in-port" data-port="in"></div>
        Context (Python)
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <label>Update request.context (def node_logic(request):)</label>
        <div class="monaco-container"></div>
      </div>
    </div>

    <!-- Security specific Templates -->
    <div class="node logger-node status-green" data-type="ActionLoggerNode">
      <div class="node-header bg-dark">
        <div class="port in-port" data-port="in"></div>
        Action Logger
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Logs requests to /core/logs</p>
      </div>
    </div>

    <div class="node antibot-node status-green" data-type="AntiBotNode">
      <div class="node-header bg-dark">
        <div class="port in-port" data-port="in"></div>
        Anti-Bot Filter
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Blocks scrapers/crawlers</p>
      </div>
    </div>

    <div class="node ratelimit-node status-green" data-type="RateLimitNode">
      <div class="node-header bg-dark">
        <div class="port in-port" data-port="in"></div>
        Rate Limiter
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Prevents spam / DDoS</p>
      </div>
    </div>

    <div class="node csrf-node status-green" data-type="CSRFNode">
      <div class="node-header bg-dark">
        <div class="port in-port" data-port="in"></div>
        CSRF Shield
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Validates POST token</p>
      </div>
    </div>

    <div class="node screen-node status-green" data-type="ScreenProtectionNode">
      <div class="node-header bg-dark">
        <div class="port in-port" data-port="in"></div>
        Screen Protection
        <div class="port out-port" data-port="out"></div>
      </div>
      <div class="node-body">
        <p style="font-size: 0.8rem; color: #666; text-align: center;">Blocks screenshots/copy</p>
      </div>
    </div>

  </div>

  <!-- Right Click Menu (Optional Future Use) -->
  <div id="context-menu" class="hidden">
    <div class="menu-item" id="delete-node">Delete Node</div>
  </div>

  <script src="canvas.js"></script>
</body>

</html>
"""

WEBNODE_CSS = """
:root {
    --bg-dark: #1e1e1e;
    --bg-panel: #2d2d2d;
    --border-color: #3e3e42;
    --text-main: #d4d4d4;
    --text-muted: #858585;
    --accent: #007acc;

    /* Status Colors based on user image */
    --status-green: #10b981;
    /* Emerald */
    --status-red: #ef4444;
    /* Red */
    --port-color: #000000;
}

* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

body {
    background-color: var(--bg-dark);
    color: var(--text-main);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    height: 100vh;
}

/* Toolbar */
#toolbar {
    height: 50px;
    background-color: var(--bg-panel);
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    z-index: 10;
}

.logo {
    font-weight: bold;
    font-size: 1.2rem;
    color: white;
}

.controls button {
    background-color: #3c3c3c;
    color: white;
    border: 1px solid #555;
    padding: 6px 12px;
    margin-right: 8px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 0.9rem;
}

.controls button:hover {
    background-color: #505050;
}

.btn-primary {
    background-color: var(--accent) !important;
    border-color: var(--accent) !important;
}

.btn-primary:hover {
    background-color: #005f9e !important;
}

.btn-danger {
    background-color: #b91c1c !important;
    border-color: #991b1b !important;
}

#status-indicator {
    color: var(--text-muted);
    font-size: 0.9rem;
}

#status-indicator.live {
    color: var(--status-green);
}

/* Workspace */
#workspace {
    display: flex;
    flex: 1;
    overflow: hidden;
}

/* Sidebar */
#sidebar {
    width: 250px;
    background-color: var(--bg-panel);
    border-right: 1px solid var(--border-color);
    padding: 15px;
    overflow-y: auto;
    z-index: 5;
}

#sidebar h3 {
    font-size: 1rem;
    margin-bottom: 15px;
    color: white;
}

.category {
    font-size: 0.8rem;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 15px 0 5px 0;
    letter-spacing: 0.05em;
}

.palette-node {
    background-color: #3b3b3b;
    border: 1px solid #555;
    padding: 10px;
    margin-bottom: 8px;
    border-radius: 6px;
    cursor: grab;
    font-size: 0.9rem;
    transition: background 0.2s;
}

.palette-node:hover {
    background-color: #4a4a4a;
    border-color: #666;
}

/* Canvas */
#canvas-container {
    flex: 1;
    position: relative;
    overflow: hidden;
    background-color: #1a1a1a;
    background-image:
        linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
    background-size: 20px 20px;
    cursor: grab;
    /* For panning */
}

#canvas-container:active {
    cursor: grabbing;
}

#wire-layer {
    position: absolute;
    top: 0;
    left: 0;
    z-index: 1;
    pointer-events: none;
    /* Let clicks pass through to nodes */
}

.wire {
    fill: none;
    stroke: #888;
    stroke-width: 4;
    transition: stroke 0.3s;
    pointer-events: stroke;
    cursor: pointer;
}

.wire:hover {
    stroke: #b91c1c;
    /* red hover for deletion clue */
}

.wire.active {
    stroke: var(--accent);
}

.wire.error {
    stroke: var(--status-red);
    stroke-dasharray: 5, 5;
    animation: dash 1s linear infinite;
}

@keyframes dash {
    to {
        stroke-dashoffset: -10;
    }
}

#canvas-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 2;
    transform-origin: 0 0;
}

/* Nodes */
.node {
    position: absolute;
    width: 280px;
    background-color: white;
    /* Per user image, nodes are white */
    border: 5px solid var(--border-color);
    /* The Thick Border */
    border-radius: 4px;
    color: black;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
    cursor: default;
    user-select: none;
}

/* Status Borders (Green/Red) */
.node.status-green {
    border-color: var(--status-green);
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.6);
}

.node.status-red {
    border-color: var(--status-red);
    box-shadow: 0 0 20px rgba(239, 68, 68, 0.6);
}

.node-header {
    background-color: transparent;
    padding: 10px;
    font-weight: bold;
    text-align: center;
    border-bottom: 2px solid black;
    cursor: grab;
    position: relative;
}

.node-header:active {
    cursor: grabbing;
}

.node-body {
    padding: 15px;
    display: flex;
    flex-direction: column;
    gap: 10px;
}

.node-body label {
    font-size: 0.8rem;
    color: #444;
}

.node-input {
    padding: 6px;
    border: 1px solid black;
    border-radius: 2px;
    font-family: monospace;
    width: 100%;
}

.node-actions {
    display: flex;
    justify-content: flex-end;
    margin-top: 5px;
}

.node-btn {
    background: white;
    border: 1px solid black;
    border-radius: 12px;
    padding: 4px 12px;
    cursor: pointer;
    font-size: 0.8rem;
}

.node-btn:hover {
    background: #eee;
}

/* Ports */
.port {
    width: 14px;
    height: 14px;
    background-color: white;
    border: 4px solid var(--port-color);
    border-radius: 50%;
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    cursor: crosshair;
    z-index: 10;
}

.port:hover {
    transform: translateY(-50%) scale(1.2);
}

.in-port {
    left: -9px;
}

.out-port {
    right: -9px;
}

/* Monaco Container inside Logic Node */
.monaco-container {
    height: 150px;
    width: 100%;
    border: 1px solid #ccc;
    margin-top: 5px;
}
"""

WEBNODE_JS = """
// State
let panX = 0, panY = 0, scale = 1;
let isPanning = false, startX, startY;
let activeNode = null;
let isWiring = false;
let startPort = null;
let wires = [];
let nodeIdCounter = 10; // Reserve < 10 for defaults

const canvasLayer = document.getElementById('canvas-layer');
const canvasContainer = document.getElementById('canvas-container');
const wireLayer = document.getElementById('wire-layer');

// --- Initialization ---
function init() {
    // Bind existing nodes
    document.querySelectorAll('#canvas-layer .node').forEach(node => bindNodeEvents(node));
    updateAllWires();

    // Bind wire deletion to the wire layer
    wireLayer.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('wire')) {
            deleteWire(e.target);
        }
    });

    // Load graph automatically
    loadGraphJSON();
}

// --- Panning & Zooming ---
canvasContainer.addEventListener('mousedown', (e) => {
    if (e.target.closest('.node') || e.target.closest('.port')) return;
    if (e.button === 1 || e.button === 0) {
        isPanning = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
    }
});

window.addEventListener('mousemove', (e) => {
    if (isPanning) {
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateCanvasTransform();
    }
    if (isWiring && startPort) {
        drawTempWire(e.clientX, e.clientY);
    }
});

window.addEventListener('mouseup', () => {
    isPanning = false;
    stopWiring();
});

canvasContainer.addEventListener('wheel', (e) => {
    if (e.ctrlKey || e.metaKey) {
        e.preventDefault();
        const zoomIntensity = 0.1;
        const wheel = e.deltaY < 0 ? 1 : -1;

        let newScale = scale * Math.exp(wheel * zoomIntensity);
        newScale = Math.min(Math.max(0.2, newScale), 3);
        scale = newScale;
        updateCanvasTransform();
    }
});

function updateCanvasTransform() {
    canvasLayer.style.transform = `translate(${panX}px, ${panY}px) scale(${scale})`;
    updateAllWires();
}

// --- Dynamic Node Event Binding ---
function bindNodeEvents(node) {
    const header = node.querySelector('.node-header');
    if (header) {
        header.addEventListener('mousedown', startNodeDrag);
    }

    node.querySelectorAll('.port').forEach(port => {
        port.addEventListener('mousedown', onPortMouseDown);
        port.addEventListener('mouseup', onPortMouseUp);
    });

    // Delete node on double click (anywhere on the node except interactive elements)
    node.addEventListener('dblclick', (e) => {
        if (e.target.classList.contains('port') || e.target.closest('input') || e.target.closest('button') || e.target.closest('.monaco-container')) return;
        if (confirm('Delete this node?')) {
            deleteNode(node.id);
        }
    });
}

// --- Deletion Handlers ---
function deleteNode(nodeId) {
    const nodeEl = document.getElementById(nodeId);
    if (!nodeEl) return;

    // Remove all wires associated with this node exactly
    wires = wires.filter(w => {
        if (w.sourceNode === nodeId || w.targetNode === nodeId) {
            w.path.remove();
            return false;
        }
        return true;
    });

    nodeEl.remove();
}

function deleteWire(pathEl) {
    wires = wires.filter(w => {
        if (w.path === pathEl) {
            w.path.remove();
            return false;
        }
        return true;
    });
}


// --- Drag & Drop from Palette ---
document.querySelectorAll('.palette-node').forEach(item => {
    item.addEventListener('dragstart', (e) => {
        e.dataTransfer.setData('text/plain', e.target.getAttribute('data-type'));
    });
});

canvasContainer.addEventListener('dragover', (e) => {
    e.preventDefault(); // Allow drop
});

canvasContainer.addEventListener('drop', (e) => {
    e.preventDefault();
    const nodeType = e.dataTransfer.getData('text/plain');
    if (!nodeType) return;

    const template = document.querySelector(`#node-templates [data-type="${nodeType}"]`);
    if (!template) return;

    const newNode = template.cloneNode(true);
    const newId = `node-${nodeIdCounter++}`;
    newNode.id = newId;

    // Bind port IDs
    newNode.querySelectorAll('.port').forEach(port => {
        port.dataset.node = newId;
    });

    // Calculate drop position relative to scaled canvas
    const rect = canvasLayer.getBoundingClientRect();
    const x = (e.clientX - rect.left) / scale;
    const y = (e.clientY - rect.top) / scale;
    newNode.style.left = `${x}px`;
    newNode.style.top = `${y}px`;

    canvasLayer.appendChild(newNode);
    bindNodeEvents(newNode);

    // Initialize Monaco if Logic, Context or Render Node
    if (['LogicNode', 'ContextNode', 'RenderNode'].includes(nodeType)) {
        initMonacoEditor(newNode, nodeType);
    }
});

// --- Monaco Editor ---
function initMonacoEditor(nodeElement, type) {
    const container = nodeElement.querySelector('.monaco-container');
    if (!container) return;

    let initConfig = {
        value: '',
        language: 'python',
        theme: 'vs-dark',
        minimap: { enabled: false },
        scrollBeyondLastLine: false,
        fontSize: 12
    };

    if (type === 'LogicNode') {
        initConfig.value = 'def process_logic(request):\\\n    # Write Python logic here\\\n    # e.g., request.context["result"] = "<h1>Hello</h1>"\\\n    return {}';
    } else if (type === 'ContextNode') {
        initConfig.value = 'def node_logic(request):\\\n    # Add global variables here\\\n    return {"key": "value"}';
    } else if (type === 'RenderNode') {
        initConfig.value = '<!DOCTYPE html>\\\n<html lang="en">\\\n<head>\\\n    <title>Document</title>\\\n</head>\\\n<body>\\\n    {result}\\\n</body>\\\n</html>';
        initConfig.language = 'html';
    }

    // Ensure AMD require is available (loaded in index.html)
    if (window.require) {
        require(['vs/editor/editor.main'], function () {
            const editor = monaco.editor.create(container, initConfig);
            nodeElement._monacoEditor = editor;

            // Resize block
            const resizeObserver = new ResizeObserver(() => editor.layout());
            resizeObserver.observe(container);
        });
    }
}

// --- Node Dragging (Canvas) ---
function startNodeDrag(e) {
    if (e.target.classList.contains('port')) return;

    activeNode = e.target.closest('.node');
    canvasLayer.appendChild(activeNode); // Bring to front

    const rect = activeNode.getBoundingClientRect();
    const offsetX = (e.clientX - rect.left) / scale;
    const offsetY = (e.clientY - rect.top) / scale;

    function onMouseMove(moveEvent) {
        const canvasRect = canvasLayer.getBoundingClientRect();
        let newX = (moveEvent.clientX - canvasRect.left) / scale - offsetX;
        let newY = (moveEvent.clientY - canvasRect.top) / scale - offsetY;

        activeNode.style.left = `${newX}px`;
        activeNode.style.top = `${newY}px`;
        updateAllWires();
    }

    function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
        activeNode = null;
    }

    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
}

// --- Wiring (SVGs) ---
function onPortMouseDown(e) {
    e.stopPropagation();
    isWiring = true;
    startPort = e.target;

    const tempPath = document.createElementNS("http://www.w3.org/2000/svg", "path");
    tempPath.classList.add('wire');
    tempPath.id = 'temp-wire';
    wireLayer.appendChild(tempPath);
}

function onPortMouseUp(e) {
    if (isWiring && startPort && startPort !== e.target) {
        const isStartOut = startPort.classList.contains('out-port');
        const isEndIn = e.target.classList.contains('in-port');

        if (isStartOut && isEndIn && startPort.dataset.node !== e.target.dataset.node) {
            createWire(startPort, e.target);
        }
    }
}

function stopWiring() {
    isWiring = false;
    startPort = null;
    const temp = document.getElementById('temp-wire');
    if (temp) temp.remove();
}

function getPortCoords(portEl) {
    const rect = portEl.getBoundingClientRect();
    const canvasRect = canvasContainer.getBoundingClientRect();
    return {
        x: rect.left - canvasRect.left + (rect.width / 2),
        y: rect.top - canvasRect.top + (rect.height / 2)
    };
}

function drawTempWire(mouseX, mouseY) {
    if (!startPort) return;
    const start = getPortCoords(startPort);
    const canvasRect = canvasContainer.getBoundingClientRect();
    const endX = mouseX - canvasRect.left;
    const endY = mouseY - canvasRect.top;

    drawBezier(document.getElementById('temp-wire'), start.x, start.y, endX, endY);
}

function createWire(fromPort, toPort) {
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.classList.add('wire');
    wireLayer.appendChild(path);

    wires.push({
        sourceNode: fromPort.dataset.node,
        sourcePort: fromPort.dataset.port,
        targetNode: toPort.dataset.node,
        targetPort: toPort.dataset.port,
        path: path,
        fromEl: fromPort,
        toEl: toPort
    });

    updateAllWires();
}

function updateAllWires() {
    wires.forEach(wire => {
        const start = getPortCoords(wire.fromEl);
        const end = getPortCoords(wire.toEl);
        drawBezier(wire.path, start.x, start.y, end.x, end.y);
    });
}

function drawBezier(pathEl, x1, y1, x2, y2) {
    const curvature = Math.abs(x2 - x1) * 0.5;
    const d = `M ${x1} ${y1} C ${x1 + curvature} ${y1}, ${x2 - curvature} ${y2}, ${x2} ${y2}`;
    pathEl.setAttribute('d', d);
}

// --- Graph Serialization & Deserialization ---

async function loadGraphJSON() {
    try {
        const res = await fetch('/api/load');
        const data = await res.json();

        if (!data || !data.nodes || data.nodes.length === 0) return;

        // Clear canvas first
        document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
        document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
        wires = [];

        // Determine highest Node ID to avoid collisions
        let maxId = 10;

        // Reconstruct Nodes
        data.nodes.forEach(nodeData => {
            const template = document.querySelector(`#node-templates [data-type="${nodeData.type}"]`);
            if (!template) return;

            const newNode = template.cloneNode(true);
            newNode.id = nodeData.id;

            // Extract numeric ID for counter
            const nId = parseInt(nodeData.id.replace('node-', ''));
            if (!isNaN(nId) && nId > maxId) maxId = nId;

            newNode.querySelectorAll('.port').forEach(port => {
                port.dataset.node = nodeData.id;
            });

            newNode.style.left = `${nodeData.x}px`;
            newNode.style.top = `${nodeData.y}px`;

            canvasLayer.appendChild(newNode);
            bindNodeEvents(newNode);

            // Initialize Monaco early so it's ready to accept value
            if (['LogicNode', 'ContextNode', 'RenderNode'].includes(nodeData.type)) {
                initMonacoEditor(newNode, nodeData.type);
            }

            // Reapply Configuration
            setTimeout(() => {
                const config = nodeData.config || {};
                const type = nodeData.type;

                if (type === 'ServerNode') {
                    if (config.ip) newNode.querySelector('.ip-input').value = config.ip;
                    if (config.port) newNode.querySelector('.port-input').value = config.port;
                } else if (type === 'URLNode') {
                    if (config.path) newNode.querySelector('.path-input').value = config.path;
                } else if (type === 'ModelNode') {
                    if (config.query) newNode.querySelector('.query-input').value = config.query;
                    if (config.paramsMap) newNode.querySelector('.params-input').value = config.paramsMap;
                    if (config.contextKey) newNode.querySelector('.context-input').value = config.contextKey;
                    if (config.isWrite !== undefined) newNode.querySelector('.is-write-input').checked = config.isWrite;
                } else if (type === 'RenderNode') {
                    if (config.filename) newNode.querySelector('.filename-input').value = config.filename;
                    if (config.html_code && newNode._monacoEditor) {
                        newNode._monacoEditor.setValue(config.html_code);
                    }
                } else if (type === 'LogicNode' || type === 'ContextNode') {
                    if (config.code && newNode._monacoEditor) {
                        newNode._monacoEditor.setValue(config.code);
                    }
                }
            }, 100); // Slight delay to ensure Monaco is instantiated
        });

        nodeIdCounter = maxId + 1;

        // Reconstruct Connections
        setTimeout(() => {
            data.connections.forEach(conn => {
                const sourceNodeEl = document.getElementById(conn.source);
                const targetNodeEl = document.getElementById(conn.target);

                if (!sourceNodeEl || !targetNodeEl) {
                    console.warn(`Could not find source or target node for connection: ${conn.source} -> ${conn.target}`);
                    return;
                }

                // Find the actual port elements. Assuming default 'out' and 'in' ports for simplicity
                // In a more complex system, port IDs would also be serialized.
                const fromPort = sourceNodeEl.querySelector('.out-port');
                const toPort = targetNodeEl.querySelector('.in-port');

                if (fromPort && toPort) {
                    createWire(fromPort, toPort);
                } else {
                    console.warn(`Could not find ports for connection: ${conn.source} -> ${conn.target}`);
                }
            });
            updateAllWires();
        }, 150);

    } catch (e) {
        console.error("Failed to load graph:", e);
    }
}

// --- Serialization & Backend API ---
function extractGraphJSON() {
    const nodes = [];
    document.querySelectorAll('#canvas-layer .node').forEach(nodeEl => {
        const id = nodeEl.id;
        const type = nodeEl.dataset.type;
        const x = parseFloat(nodeEl.style.left) || 0;
        const y = parseFloat(nodeEl.style.top) || 0;

        let config = {};
        if (type === 'ServerNode') {
            config.ip = nodeEl.querySelector('.ip-input').value;
            config.port = parseInt(nodeEl.querySelector('.port-input').value, 10);
        } else if (type === 'URLNode') {
            config.path = nodeEl.querySelector('.path-input').value;
        } else if (type === 'RenderNode') {
            config.filename = nodeEl.querySelector('.filename-input').value;
            if (nodeEl._monacoEditor) {
                config.html_code = nodeEl._monacoEditor.getValue();
            }
        } else if (type === 'ModelNode') {
            config.query = nodeEl.querySelector('.query-input').value;
            config.paramsMap = nodeEl.querySelector('.params-input').value;
            config.contextKey = nodeEl.querySelector('.context-input').value;
            config.isWrite = nodeEl.querySelector('.is-write-input').checked;
        } else if (type === 'LogicNode' || type === 'ContextNode') {
            if (nodeEl._monacoEditor) {
                config.code = nodeEl._monacoEditor.getValue();
            }
        }

        nodes.push({ id, type, x, y, config });
    });

    const connections = wires.map(w => ({
        source: w.sourceNode,
        target: w.targetNode
    }));

    return { nodes, connections };
}

// Bind Toolbar Buttons
document.getElementById('btn-save').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    console.log("Saving graph:", payload);
    try {
        await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        alert('Graph JSON saved locally!');
    } catch (e) {
        alert('Failed to save. Is webnode_backend.py running?');
    }
});

document.getElementById('btn-deploy').addEventListener('click', async () => {
    const payload = extractGraphJSON();
    try {
        const res = await fetch('/api/deploy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await res.json();
        if (result.status === 'success') {
            document.getElementById('status-indicator').innerText = '● Live';
            document.getElementById('status-indicator').className = 'live';
            alert('Deployed successfully! main.py generated and server is running.');
        } else {
            alert('Failed to deploy: ' + result.message);
        }
    } catch (e) {
        alert('Cannot connect to backend compiler.');
    }
});

document.getElementById('btn-stop').addEventListener('click', async () => {
    try {
        await fetch('/api/stop', { method: 'POST' });
        document.getElementById('status-indicator').innerText = '● Offline';
        document.getElementById('status-indicator').className = '';
    } catch (e) { }
});

document.getElementById('btn-clear').addEventListener('click', () => {
    document.querySelectorAll('#canvas-layer .node').forEach(n => n.remove());
    document.querySelectorAll('#wire-layer .wire').forEach(w => w.remove());
    wires = [];
    nodeIdCounter = 10;
});

// --- Polling & Flow Traversal ---
async function pollServerStatus() {
    try {
        const res = await fetch('/api/status');
        const data = await res.json();

        const isLive = (data.status === 'live');
        updateVisualFlow(isLive);

        const indicator = document.getElementById('status-indicator');
        if (isLive) {
            indicator.innerText = '● Live';
            indicator.className = 'live';
        } else {
            indicator.innerText = '● Offline';
            indicator.className = '';
        }
    } catch (e) {
        updateVisualFlow(false);
    }
}

function updateVisualFlow(isLive) {
    const allNodes = document.querySelectorAll('#canvas-layer > .node');

    // Default all to red
    allNodes.forEach(n => {
        n.classList.remove('status-green');
        n.classList.add('status-red');
    });
    wires.forEach(w => {
        w.path.classList.remove('active');
        w.path.classList.add('error');
    });

    if (!isLive) return;

    // Find Server Node by traversing active nodes
    let serverNodeEl = null;
    for (let i = 0; i < allNodes.length; i++) {
        if (allNodes[i].dataset.type === 'ServerNode') {
            serverNodeEl = allNodes[i];
            break;
        }
    }

    if (!serverNodeEl) return;

    const reachableNodes = new Set();
    const reachableWires = new Set();

    reachableNodes.add(serverNodeEl.id);
    const queue = [serverNodeEl.id];

    while (queue.length > 0) {
        const curr = queue.shift();
        wires.forEach(w => {
            if (w.sourceNode === curr) {
                reachableWires.add(w);
                if (!reachableNodes.has(w.targetNode)) {
                    reachableNodes.add(w.targetNode);
                    queue.push(w.targetNode);
                }
            }
        });
    }

    // Apply green to reachable nodes
    allNodes.forEach(n => {
        if (reachableNodes.has(n.id)) {
            n.classList.remove('status-red');
            n.classList.add('status-green');
        }
    });

    // Apply active to reachable wires
    wires.forEach(w => {
        if (reachableWires.has(w)) {
            w.path.classList.remove('error');
            w.path.classList.add('active');
        }
    });
}



setInterval(pollServerStatus, 2000);

// Start
init();

"""

WEBNODE_BACKEND_PY = """
import http.server
import socketserver
import json
import os
import subprocess
import signal
import sys

PORT = 8080 # Node Editor port
EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK_DIR = os.path.dirname(EDITOR_DIR)

active_process = None

class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=EDITOR_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/status':
            self.handle_status()
        elif self.path == '/api/load':
            self.handle_load()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            self.handle_save()
        elif self.path == '/api/deploy':
            self.handle_deploy()
        elif self.path == '/api/stop':
            self.handle_stop()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_status(self):
        global active_process
        is_live = False
        if active_process and active_process.poll() is None:
            is_live = True
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'live' if is_live else 'offline'}).encode())

    def handle_load(self):
        graph_path = os.path.join(EDITOR_DIR, 'graph.json')
        if os.path.exists(graph_path):
            with open(graph_path, 'r') as f:
                graph_data = json.load(f)
        else:
            graph_data = {"nodes": [], "connections": []}
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(graph_data).encode())

    def handle_save(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

    def handle_stop(self):
        global active_process
        if active_process:
            active_process.terminate()
            active_process = None
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'stopped'}).encode())

    def handle_deploy(self):
        global active_process
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        # 1. Save JSON
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
            
        # 2. Compile JSON to main.py
        try:
            self.compile_graph(graph_data)
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())
            return

        # 3. Restart Server
        if active_process:
            active_process.terminate()
            active_process.wait()
            
        # 3.5 Forcefully kill any stray background processes holding the port (e.g. user manual runs)
        try:
            port = 8000
            for n in graph_data.get('nodes', []):
                if n['type'] == 'ServerNode':
                    port = int(n.get('config', {}).get('port', 8000))
                    break
            kill_cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force }}"
            subprocess.run(["powershell", "-Command", kill_cmd], capture_output=True)
        except Exception:
            pass
            
        main_py_path = os.path.join(FRAMEWORK_DIR, 'main.py')
        active_process = subprocess.Popen([sys.executable, main_py_path], cwd=FRAMEWORK_DIR)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

    def compile_graph(self, graph_data):
        nodes = {n['id']: n for n in graph_data['nodes']}
        connections = graph_data['connections']
        
        # Find starting node (ServerNode)
        server_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'ServerNode'), None)
        if not server_node_id:
            raise ValueError("No Server Node found in graph!")

        # Find mapping of source -> list of targets
        outgoing_map = {}
        for c in connections:
            source_id = c['source']
            target_id = c['target']
            if source_id not in outgoing_map:
                outgoing_map[source_id] = []
            outgoing_map[source_id].append(target_id)
            
        # BFS to find all reachable nodes
        reachable_ids = []
        queue = [server_node_id]
        while queue:
            curr = queue.pop(0)
            if curr not in reachable_ids:
                reachable_ids.append(curr)
                for tgt in outgoing_map.get(curr, []):
                    queue.append(tgt)
                    
        # Gather Imports based on reachable node types
        types_used = set(nodes[nid]['type'] for nid in reachable_ids)
        needs_router = any(len(targets) > 1 for src, targets in outgoing_map.items() if src in reachable_ids)
        
        imports = [
            "import socketserver",
            "from nodes.server_node import ServerNode",
            "from nodes.http_requests_node import HTTPRequestsNode"
        ]
        
        if 'URLNode' in types_used: imports.append("from nodes.url_node import URLNode")
        if 'RenderNode' in types_used: imports.append("from nodes.template_node import RenderNode")
        if 'LogicNode' in types_used: imports.append("from nodes.logic_node import LogicNode")
        if 'ModelNode' in types_used:
            imports.append("from nodes.model_node import ModelNode")
            imports.append("from core.db import Database")
        if needs_router:
            imports.append("from nodes.route_node import RouterNode")
        if 'ContextNode' in types_used: imports.append("from nodes.context_node import ContextNode")
        if 'ActionLoggerNode' in types_used: imports.append("from plugins.logger import ActionLoggerNode")
        if 'AntiBotNode' in types_used: imports.append("from plugins.security import AntiBotNode")
        if 'RateLimitNode' in types_used: imports.append("from plugins.security import RateLimitNode")
        if 'CSRFNode' in types_used: imports.append("from plugins.security import CSRFNode")
        if 'ScreenProtectionNode' in types_used: imports.append("from plugins.security import ScreenProtectionNode")
        
        code_lines = [
            "# AUTO-GENERATED BY NODE EDITOR COMPILER",
            "\\\n".join(imports),
            "\\\n# Initialize Database if needed"
        ]
        
        if 'ModelNode' in types_used:
            code_lines.append("db = Database('node.db')")
            code_lines.append("db.connect()")
            
        code_lines.append("\\\n# Nodes Instantiation")
        
        # Initialize variables
        chain_vars = []
        logic_counter = 1
        for nid in reachable_ids:
            node = nodes[nid]
            ntype = node['type']
            config = node.get('config', {})
            var_name = f"{ntype.lower()}_{nid.replace('-', '_')}"
            chain_vars.append(var_name)
            
            if ntype == 'ServerNode':
                code_lines.append(f"{var_name} = ServerNode(host='{config.get('ip', '127.0.0.1')}', port={config.get('port', 8000)})")
            elif ntype == 'URLNode':
                code_lines.append(f"{var_name} = URLNode('{config.get('path', '/')}')")
            elif ntype == 'RenderNode':
                # Dynamically write the template file from GUI code
                html_code = config.get('html_code', '<h1>Hello World!</h1>')
                custom_filename = config.get('filename', '').strip()
                auto_filename = custom_filename if custom_filename else f"auto_template_{nid}.html"
                
                # Ensure the auto_filepath exists in templates/
                os.makedirs(os.path.join(FRAMEWORK_DIR, 'templates'), exist_ok=True)
                auto_filepath = os.path.join(FRAMEWORK_DIR, 'templates', auto_filename)
                
                # Write the actual HTML file that main.py will use
                with open(auto_filepath, 'w', encoding='utf-8') as tf:
                    tf.write(html_code)
                
                code_lines.append(f"{var_name} = RenderNode('{auto_filename}')")
            elif ntype == 'ModelNode':
                code_lines.append(f"{var_name} = ModelNode(db, query='{config.get('query', '')}', params_mapping=[x.strip() for x in '{config.get('paramsMap', '')}'.split(',')], context_key='{config.get('contextKey', 'data')}', is_write={config.get('isWrite', False)})")
            elif ntype == 'LogicNode':
                # Write custom logic function directly into main.py
                logic_counter += 1
                func_code = config.get('code', 'def process_logic(request):\\\n    return {}')
                func_def_name = func_code.split('def ')[1].split('(')[0].strip()
                code_lines.append(f"\\\n{func_code}\\\n")
                code_lines.append(f"{var_name} = LogicNode({func_def_name})")
            elif ntype == 'ContextNode':
                logic_counter += 1
                func_code = config.get('code', 'def node_logic(request):\\\n    return {}')
                func_def_name = func_code.split('def ')[1].split('(')[0].strip()
                code_lines.append(f"\\\n{func_code}\\\n")
                code_lines.append(f"{var_name} = ContextNode({func_def_name})")
            elif ntype == 'HTTPRequestsNode':
                code_lines.append(f"{var_name} = HTTPRequestsNode()")
            elif ntype == 'ActionLoggerNode':
                code_lines.append(f"{var_name} = ActionLoggerNode()")
            elif ntype == 'AntiBotNode':
                code_lines.append(f"{var_name} = AntiBotNode()")
            elif ntype == 'RateLimitNode':
                code_lines.append(f"{var_name} = RateLimitNode()")
            elif ntype == 'CSRFNode':
                code_lines.append(f"{var_name} = CSRFNode()")
            elif ntype == 'ScreenProtectionNode':
                code_lines.append(f"{var_name} = ScreenProtectionNode()")
            else:
                code_lines.append(f"{var_name} = BaseNode()") # Fallback
                
        # Connect Chain
        code_lines.append("\\\n# Node Connection Chain")
        router_counter = 1
        for nid in reachable_ids:
            targets = outgoing_map.get(nid, [])
            if not targets:
                continue
            
            src_var = f"{nodes[nid]['type'].lower()}_{nid.replace('-', '_')}"
            
            if len(targets) == 1:
                tgt_var = f"{nodes[targets[0]]['type'].lower()}_{targets[0].replace('-', '_')}"
                code_lines.append(f"{src_var}.connect({tgt_var})")
            else:
                # Multiple targets -> Create RouterNode
                route_list = []
                for tgt in targets:
                    tgt_var = f"{nodes[tgt]['type'].lower()}_{tgt.replace('-', '_')}"
                    route_list.append(tgt_var)
                
                router_var = f"router_node_auto_{router_counter}"
                router_counter += 1
                code_lines.append(f"{router_var} = RouterNode([{', '.join(route_list)}])")
                code_lines.append(f"{src_var}.connect({router_var})")
        
        # Start Server
        code_lines.append("\\\n# Start Server")
        server_var = chain_vars[0]
        code_lines.append(f"print('Node Editor Generated Server starting...')")
        code_lines.append('from nodes.server_node import FrameworkHandler')
        code_lines.append(f"FrameworkHandler.server_node = {server_var}")
        code_lines.append(f"from http.server import HTTPServer")
        code_lines.append(f"with HTTPServer(({server_var}.host, {server_var}.port), FrameworkHandler) as httpd:")
        code_lines.append(f"    try:")
        code_lines.append(f"        httpd.serve_forever()")
        code_lines.append(f"    except KeyboardInterrupt:")
        code_lines.append(f"        pass")

        # Write main.py
        with open(os.path.join(FRAMEWORK_DIR, 'main.py'), 'w') as f:
            f.write("\\\n".join(code_lines))

if __name__ == '__main__':
    from http.server import HTTPServer
    with HTTPServer(("", PORT), EditorHandler) as httpd:
        print(f"Node Editor running at http://localhost:{PORT}")
        httpd.serve_forever()

"""

def create_project():
    print("Initializing Framework Project...")

    # Create Directories
    create_directory(os.path.join("nodes"))
    create_directory(os.path.join("core"))
    create_directory(os.path.join("static"))
    create_directory(os.path.join("templates"))
    create_directory(os.path.join("plugins"))
    create_directory(os.path.join("node_editor"))

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

    # Write Node Editor GUI
    write_file(os.path.join("node_editor", "index.html"), WEBNODE_HTML)
    write_file(os.path.join("node_editor", "styles.css"), WEBNODE_CSS)
    write_file(os.path.join("node_editor", "canvas.js"), WEBNODE_JS)
    write_file(os.path.join("node_editor", "node_backend.py"), WEBNODE_BACKEND_PY)

    # Main.py (only if not exists)
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

    print("\\nnode_setup_project.py completed successfully. Run 'python main.py' to start the server.")
    print("To launch the interactive graphical Node Editor, run 'python node_editor/node_backend.py'.")

if __name__ == "__main__":
    create_project()
