# Project Recreation Context

This document contains the full source code and directory structure for the Modular Custom Web Framework project, refactored into an n8n-style Node Graph architecture.
Please recreate the project with the following structure and file contents.

## Directory Structure

```text
framework/
├── main.py
├── settings.py
├── setup_project.py
├── nodes/
│   ├── __init__.py
│   ├── base_node.py
│   ├── http_requests_node.py
│   ├── logic_node.py
│   ├── server_node.py
│   ├── template_node.py
│   ├── url_node.py
│   └── middleware/
│       └── common.py
├── static/
│   ├── animation.py
│   ├── logic.py
│   └── style.css
└── templates/
    ├── animation.html
    ├── index.html
    └── test.html
```

## File Contents

### main.py
```python
import socketserver
import sys
import os
import settings
from nodes.server_node import FrameworkHandler, ServerNode
from nodes.base_node import BaseNode
from nodes.http_requests_node import HTTPRequestsNode
from nodes.url_node import URLNode
from nodes.logic_node import LogicNode
from nodes.template_node import RenderNode
from static.logic import check_odd_even

# --- Application Logic Functions ---
def index_logic(request):
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

def simple_logic(request):
    return {}

# --- Node Graph Construction (n8n Style) ---

# 1. Server Configuration Node (The Root)
server_node = ServerNode(port=settings.PORT)

# 2. HTTP Request Processor Node
http_request_node = HTTPRequestsNode()

# 3. Connect Server -> Request
server_node.connect(http_request_node)

# 4. Define Branches (URL -> Logic -> Render)
# Branch 1: Index
url_index = URLNode('/')
logic_index = LogicNode(index_logic)
render_index = RenderNode('index.html')

# Branch 2: Animation
url_anim = URLNode('/animation')
logic_anim = LogicNode(simple_logic)
render_anim = RenderNode('animation.html')

# Branch 3: Test
url_test = URLNode('/test')
logic_test = LogicNode(simple_logic)
render_test = RenderNode('test.html')

# 5. Connect the Graph Chains (Doubly Linked List)
# URLNode -> LogicNode -> RenderNode
url_index.connect(logic_index).connect(render_index)
url_anim.connect(logic_anim).connect(render_anim)
url_test.connect(logic_test).connect(render_test)

# 6. Router Logic (Simulated Route Dispatcher)
# Acts as a hub to connect Request to multiple Route Entry Points
class RouterNode(BaseNode):
    def __init__(self, routes):
        super().__init__()
        self.routes = routes
    def process(self, request):
        for route in self.routes:
            # route is the start of a chain (URLNode)
            result = route.process(request)
            if result is not None:
                return result
        return None

router_node = RouterNode([url_index, url_anim, url_test])

# 7. Connect Main Graph Line
# Server -> Request -> Router -> [Chains]
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
        print("\nStopping server...")
        httpd.server_close()
```

### nodes/base_node.py
```python
class BaseNode:
    """
    Base class for all nodes in the framework.
    Implements a doubly linked list structure.
    """
    def __init__(self):
        self.next_node = None
        self.prev_node = None

    def connect(self, node):
        """
        Connects the next node in the chain.
        Returns the next node to allow chaining: node1.connect(node2).connect(node3)
        """
        self.next_node = node
        node.prev_node = self
        return node

    def process(self, data):
        """
        Processes data and passes it to the next node.
        Subclasses should override this, perform logic, and then call super().process(new_data)
        """
        if self.next_node:
            return self.next_node.process(data)
        return data
```

### nodes/server_node.py
```python
import http.server
import sys
import os
import importlib
import settings
from nodes.base_node import BaseNode

def import_string(dotted_path):
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        print(f"Import Error: {e}")
        return None

class ServerNode(BaseNode):
    """
    Root Node.
    Configures the server port and initiates the request processing graph.
    Connects to HTTPRequestNode.
    """
    def __init__(self, port=8000):
        super().__init__()
        self.port = port

    def start_flow(self, handler):
        """
        Triggered by FrameworkHandler.
        Passes the raw handler to the next node (HTTPRequestNode).
        """
        return self.process(handler)

class FrameworkHandler(http.server.SimpleHTTPRequestHandler):
    """
    The actual HTTP Handler that receives requests from socketserver.
    It delegates processing to the ServerNode graph.
    """
    
    # The ServerNode instance will be injected here
    server_node = None

    def __init__(self, *args, **kwargs):
        self.middleware_chain = self.load_middleware()
        super().__init__(*args, **kwargs)

    def load_middleware(self):
        """
        Builds the middleware chain ending with the graph execution.
        """
        def get_response(request):
            # In Graph architecture, middleware logic might need to be converted to nodes.
            # Currently acting as a placeholder or wrapper if needed.
            pass

        return None

    def handle_graph_request(self, method):
        if self.server_node:
            # 1. Start Graph Execution
            # ServerNode -> pass handler
            # Expectation: The graph returns the final HTML or Response content
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
        self.handle_graph_request('GET')

    def do_POST(self):
        self.handle_graph_request('POST')
```

### nodes/http_requests_node.py
```python
import urllib.parse
from nodes.base_node import BaseNode

class HTTPRequestsNode(BaseNode):
    """
    Node that transforms raw HTTP Handler into a Request Object.
    Connects Server -> URLNode.
    """
    def __init__(self):
        super().__init__()

    def process(self, handler):
        """
        Receives raw http.server handler.
        Parses request.
        Passes a 'request' wrapper to the next node.
        """
        # Create a lightweight request wrapper/dict
        request = RequestWrapper(handler)
        
        # Pass to next node (URLNode/Router)
        return super().process(request)

class RequestWrapper:
    """
    Simple wrapper to mimic the previous request object interface.
    """
    def __init__(self, handler):
        self.handler = handler
        self.path = handler.path
        self.headers = handler.headers
        self.method = handler.command
        self.params = {}
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
```

### nodes/url_node.py
```python
from nodes.base_node import BaseNode

class URLNode(BaseNode):
    """
    Represents a single route in the application (Routing Node).
    Checks if the request path matches.
    """
    def __init__(self, path):
        super().__init__()
        self.path = path

    def process(self, request):
        """
        Routing Logic:
        If match: Passes request to the next node (Logic).
        If no match: Returns None.
        """
        if self.path == request.path:
            return super().process(request)
        return None
```

### nodes/logic_node.py
```python
from nodes.base_node import BaseNode

class LogicNode(BaseNode):
    """
    Executes a callable logic function.
    """
    def __init__(self, logic_func):
        super().__init__()
        self.logic_func = logic_func

    def process(self, request):
        """
        Executes business logic.
        Expects 'request' object.
        Passes the result (context or response) to the next node.
        """
        # Execute the logic function passing the request
        result = self.logic_func(request)
        
        # Pass the result to the next node (RenderNode)
        return super().process(result)
```

### nodes/template_node.py
```python
import os
import settings
from nodes.base_node import BaseNode

class RenderNode(BaseNode):
    """
    Handles template rendering (The 'Face' of the application).
    """
    def __init__(self, template_name):
        super().__init__()
        self.template_name = template_name

    # Define the PyScript assets as a reusable component
    PYSCRIPT_HEADER = '''
    <link rel="stylesheet" href="https://pyscript.net/releases/2024.1.1/core.css" />
    <script type="module" src="https://pyscript.net/releases/2024.1.1/core.js"></script>
    '''

    def process(self, context=None):
        """
        Receives context from the previous node (LogicNode), renders template, and returns HTML.
        """
        return self.render(self.template_name, context)

    @staticmethod
    def render(template_name, context=None):
        """
        Reads an HTML file from settings.TEMPLATES_DIR, replaces placeholders, and returns content.
        """
        if context is None:
            context = {}
        
        # If context came from LogicNode as a tuple or non-dict (just in case), safely handle
        if not isinstance(context, dict):
             if context is None: context = {}
             else: context = {'data': context} # Fallback

        # Auto-inject PyScript header into every template
        context['pyscript_header'] = RenderNode.PYSCRIPT_HEADER

        template_path = os.path.join(settings.TEMPLATES_DIR, template_name)
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Simple string replacement templating
            for key, value in context.items():
                if isinstance(value, str):
                    content = content.replace(f"{{{key}}}", value)
            
            return content
            
        except FileNotFoundError:
            return f"<h1>Template {template_name} not found</h1>"
```

### settings.py
```python
import os

BASE_DIR = os.getcwd()
TEMPLATES_DIR = os.path.join(BASE_DIR, 'templates')
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# PORT Configuration
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

# Middleware (Note: Currently bypassed in simple Graph implementation)
MIDDLEWARE = [
    'nodes.middleware.common.SimpleLoggingMiddleware',
    'nodes.middleware.common.SecurityMiddleware',
]

# Database
DATABASES = {
    'default': {
        'ENGINE': 'sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}
```

### setup_project.py
```python
import secrets
import os

BASE_DIR = os.getcwd()
SECRET_FILE = os.path.join(BASE_DIR, '.secret_key')

def generate_secret_key():
    if os.path.exists(SECRET_FILE):
        print("Secret key already exists.")
        return

    key = secrets.token_urlsafe(50)
    with open(SECRET_FILE, 'w') as f:
        f.write(key)
    print("Generated new secret key and saved to .secret_key")

if __name__ == "__main__":
    generate_secret_key()
```
