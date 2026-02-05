import os
import secrets
import argparse
import sys

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
        raise RuntimeError("Secret key file not found. Run 'node startproject <name>' first.")

SECRET_KEY = get_secret_key()
DEBUG = True
ALLOWED_HOSTS = ['*']

INSTALLED_NODES = [
    'nodes',
]
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
from static.logic import check_odd_even, weather_logic, time_logic

# --- Application Logic Functions ---
def index_logic(request):
    print(request.get_param('number'))
    if request.method == 'POST':
        number_input = request.get_param('number')
        result_html = ""
        if number_input and number_input.isdigit():
            number = int(number_input)
            result_type = check_odd_even(number)
            result_html = f'''
            <div class="result {result_type}">
                <span class="number-display">{number}</span> is <strong>{result_type}</strong>
            </div>
            '''
        else:
            result_html = '''
            <div class="result" style="border-color: red; color: red;">
                Please enter a valid number.
            </div>
            '''
        return {'result_section': result_html}
    else:
        return {'result_section': ''}

def r1_logic(request):
    return {'r1': 'Hello World'}

def text_logic(request):
    return {'result_text': 'Hello World'}

# --- Node Graph Construction ---

# 1. Server Configuration Node (The Root)
server_node = ServerNode(port=settings.PORT)

# 2. HTTP Request Processor Node
http_request_node = HTTPRequestsNode()

class RouterNode(BaseNode):
    def __init__(self, routes):
        super().__init__()
        self.routes = routes
    def process(self, request):
        for route in self.routes:
            result = route.process(request)
            if result is not None:
                return result
        return None

# 3. Define Branches
url_index = URLNode('/')
logic_index = LogicNode(index_logic)
context_text = LogicNode(text_logic)
logic_r1 = LogicNode(r1_logic)
node_weather = LogicNode(weather_logic)
node_time = LogicNode(time_logic)
render_index = RenderNode('index.html')

# Wiring: URLIndex -> Logic -> Context -> Weather -> Time -> Render
url_index.connect(logic_index).connect(context_text).connect(logic_r1).connect(node_weather).connect(node_time).connect(render_index)

# Router
router_node = RouterNode([url_index])

# Connect Main Line
server_node.connect(http_request_node).connect(router_node)

if __name__ == "__main__":
    PORT = settings.PORT
    
    # Inject the Root Node (ServerNode) into the Handler
    FrameworkHandler.server_node = server_node
    
    print(f"Starting n8n-style Node Graph Server at http://localhost:{PORT}")
    print("Graph: Server -> Request -> Router -> [URL Chains] -> Logic -> Render")
    print("Press Ctrl+C to stop.")
    
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), FrameworkHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\\nStopping server...")
        httpd.server_close()
"""

# --- Creation Logic ---

def create_project(project_name):
    base_path = os.path.join(os.getcwd(), project_name)
    
    if os.path.exists(base_path):
        print(f"Error: Directory '{project_name}' already exists.")
        sys.exit(1)
        
    print(f"Initializing Framework Project '{project_name}'...")
    create_directory(base_path)

    # Create Subdirectories
    create_directory(os.path.join(base_path, "nodes"))
    create_directory(os.path.join(base_path, "static"))
    create_directory(os.path.join(base_path, "templates"))

    # Write Settings
    write_file(os.path.join(base_path, "settings.py"), SETTINGS_PY)

    # Write Nodes
    write_file(os.path.join(base_path, "nodes", "__init__.py"), "")
    write_file(os.path.join(base_path, "nodes", "base_node.py"), BASE_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "server_node.py"), SERVER_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "http_requests_node.py"), HTTP_REQUESTS_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "context_node.py"), CONTEXT_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "logic_node.py"), LOGIC_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "template_node.py"), TEMPLATE_NODE_PY)
    write_file(os.path.join(base_path, "nodes", "url_node.py"), URL_NODE_PY)

    # Write Static Files
    write_file(os.path.join(base_path, "static", "logic.py"), STATIC_LOGIC_PY)
    write_file(os.path.join(base_path, "static", "style.css"), STATIC_STYLE_CSS)

    # Write Template Files
    write_file(os.path.join(base_path, "templates", "index.html"), TEMPLATE_INDEX_HTML)

    # Write Main.py
    write_file(os.path.join(base_path, "main.py"), MAIN_PY)

    # Secret Key
    secret_file = os.path.join(base_path, ".secret_key")
    key = secrets.token_urlsafe(50)
    with open(secret_file, 'w') as f:
        f.write(key)
    print("Generated new secret key.")

    print(f"\\nProject '{project_name}' created successfully.")
    print(f"To start the server, run:\\n  cd {project_name}\\n  python main.py")

def main():
    parser = argparse.ArgumentParser(description="WebNode Framework CLI")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # startproject command
    startproject_parser = subparsers.add_parser('startproject', help='Create a new WebNode project')
    startproject_parser.add_argument('name', help='Name of the project directory')

    args = parser.parse_args()

    if args.command == 'startproject':
        create_project(args.name)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
