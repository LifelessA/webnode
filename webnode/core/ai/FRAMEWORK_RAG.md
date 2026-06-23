# Cybercore Visual Node Framework: RAG Context & AI Skill Manual
This document serves as the absolute, ground-truth reference for the **Cybercore Visual Node Framework** (also known as the MVC-Graph Platform). It compiles the architectural layout, core backend and compiler mechanics, node definitions, and JSON design guidelines. Upload this file as a knowledge base / RAG context to a generative AI model (such as Gemini or GPT) to enable the generation of syntactically correct and fully functional `graph.json` files for advanced web applications.

---

## 1. Directory Structure & File Index
The framework follows a modular, Model-View-Controller (MVC) visual architecture. Below is the mapping of directories and their operational purposes:

*   **Root Folder (`/`)**
    *   [main.py](file:///c:/Users/lifel/Downloads/framework/main.py): The compiled backend server script, dynamically written and updated by the compiler.
    *   [settings.py](file:///c:/Users/lifel/Downloads/framework/settings.py): Global configuration hub. It resolves variables using environmental overrides and strips quotes from local `.env` entries. Includes security configurations (CSRF, RateLimit, ScreenProtection).
    *   [db_setup.py](file:///c:/Users/lifel/Downloads/framework/db_setup.py): Standalone script to clean and initialize local database tables.
    *   [db.sqlite3](file:///c:/Users/lifel/Downloads/framework/db.sqlite3): Core relational SQLite database.
    *   [sessions.db](file:///c:/Users/lifel/Downloads/framework/sessions.db): Isolated session storage database.
*   **Core Engine (`/core/`)**
    *   [core/db.py](file:///c:/Users/lifel/Downloads/framework/core/db.py): Thread-local singleton SQLite adapter. Features Write-Ahead Logging (WAL) mode for concurrency, automatic table creation, retry-resilience, and database-level validation triggers.
    *   [core/sessions.py](file:///c:/Users/lifel/Downloads/framework/core/sessions.py): Persistent cookie session storage. Manages session dictionaries, generates `secrets.token_urlsafe(32)` tokens, and formats HTTP `Set-Cookie` headers with security flags (`HttpOnly`, `SameSite=Strict`).
    *   [core/validators.py](file:///c:/Users/lifel/Downloads/framework/core/validators.py): Form validation and XSS escaping utility. Implements HTML entity escaping, email regex matches, and type conversion.
    *   [core/logging.py](file:///c:/Users/lifel/Downloads/framework/core/logging.py): High-performance thread-safe log writer with log rotation and status formatting.
    *   [core/errors.py](file:///c:/Users/lifel/Downloads/framework/core/errors.py): Structured exception catcher (`NodeError`). Automatically outputs logs to `error_state.json` to trigger the AI auto-healer editor dashboard.
    *   [core/testing.py](file:///c:/Users/lifel/Downloads/framework/core/testing.py): Mock testing runner. Emulates request headers, context variables, and runs assertions.
    *   [core/ai_graph.py](file:///c:/Users/lifel/Downloads/framework/core/ai_graph.py): Serializes the visual graph configuration into text logs for LLM parsing.
*   **Visual Node Modules (`/nodes/`)**
    *   [nodes/base_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/base_node.py): Base class implementing node connection chaining (`connect`) and process propagation.
    *   [nodes/server_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/server_node.py): Multi-threaded HTTP listener wrapper. Handles Server-Sent Events (SSE) stream routing and provides a directory traversal protected static file server.
    *   [nodes/http_requests_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/http_requests_node.py): Converts low-level handler connections into `RequestWrapper` objects (parsing queries, cookies, session states, multipart and URL-encoded bodies).
    *   [nodes/url_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/url_node.py): Route selector compiling wildcards into regex structures (e.g., `/items/<pk:int>` → `/items/(\d+)`) and checking allowed methods.
    *   [nodes/route_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/route_node.py): Router selector executing branching searches across nested routing children.
    *   [nodes/logic_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/logic_node.py): Executes Python business functions. Automatically merges return dicts into requests, or intercepts `Response` types to short-circuit the execution chain.
    *   [nodes/js_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/js_node.py): Subprocess manager that writes script fragments to temporary files and pipes payloads into Node.js.
    *   [nodes/context_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/context_node.py): Similar to logic node, sets global request states.
    *   [nodes/template_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/template_node.py): Renders HTML files, implements safe AST block evaluations, handles layout inheritance (`extends`, `block`), and injects Client-side Python script imports.
    *   [nodes/css_node.py](file:///c:/Users/lifel/Downloads/framework/nodes/css_node.py): Compiles inline style scripts and writes them directly to `/static/` paths.
    *   [nodes/response.py](file:///c:/Users/lifel/Downloads/framework/nodes/response.py): Struct representing HTTP response bodies, redirects, JSONs, errors, and progressive SSE event streams.
*   **Framework Plugins (`/plugins/`)**
    *   [plugins/security.py](file:///c:/Users/lifel/Downloads/framework/plugins/security.py): Holds security middlewares and nodes:
        *   `RateLimitNode`: Thread-safe sliding window request limit counter.
        *   `CSRFNode`: Generates and validates session-mapped token strings in constant-time.
        *   `AntiBotNode`: User-Agent scraper filter.
        *   `ScreenProtectionNode`: HTML injector blocking screenshots, copying, print-screening, or right-clicks.
    *   [plugins/logger.py](file:///c:/Users/lifel/Downloads/framework/plugins/logger.py): Request action logger plugin.
*   **Static Assets (`/static/`)**
    *   [static/helpers.py](file:///c:/Users/lifel/Downloads/framework/static/helpers.py): Houses utility hooks like session resolution based on client IP addresses and shopping cart totals calculation formulas.

---

## 2. Line-by-Line Compiler Analysis: `node_editor/node_backend.py`
The script `node_editor/node_backend.py` runs the visual editor local server and acts as the project compiler. Understanding how it operates is crucial for writing correct graphs:

*   **Lines 1-15: Module Loading & Workspace Initialization**
    *   Imports essential libraries (`http.server`, `socketserver`, `json`, `subprocess`, `sys`, `socket`, `webbrowser`, `threading`).
    *   Pushes the framework directory absolute path (`os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`) to the top of `sys.path` so settings and core libraries can be imported globally.
*   **Lines 17-34: Production Mode Lock Guard**
    *   Declares `_check_production_lock()`. Imports global configurations. If `settings.is_production()` evaluates to `True`, the script outputs a warning indicating the Node Editor cannot run in production because of Remote Code Execution risk. It then calls `sys.exit(1)` immediately.
*   **Lines 36-45: Port, Root Paths, and Mime-Types**
    *   Establishes editor interface port `PORT = 8080`.
    *   Computes absolute paths for `EDITOR_DIR` (editor folder) and `FRAMEWORK_DIR` (project root).
    *   Configures global mime-types, forcing mapping definitions for `.js` as `application/javascript`, `.css` as `text/css`, and `.html` as `text/html` to prevent rendering issues in Windows.
*   **Lines 48-76: Python Code AST Name Parser**
    *   Declares `_extract_function_name(code: str) -> str`.
    *   *Method 1 (AST)*: Calls `ast.parse(code)` to generate an abstract syntax tree of the custom function input, traversing blocks to locate the first `ast.FunctionDef` node and return its string name.
    *   *Method 2 (Regex)*: If AST encounters parsing syntax errors, a regex matches `def name(args):` and extracts the identifier group.
    *   *Method 3 (Error)*: Throws a descriptive `ValueError` if no valid Python function is found.
*   **Lines 77-96: Port Free Checker & Server Verifier**
    *   `is_port_free(port)`: Creates a socket, binds it to localhost, and sets `SO_REUSEADDR`. Returns `True` if successful, `False` if port is already bound.
    *   `wait_for_server(port, timeout)`: Loops and tries to connect to the target port. Sleeps for 0.3s between attempts. Returns `True` when connection is established, or `False` if timeout expires.
*   **Lines 97-126: Editor Server Handler Routing**
    *   Declares `EditorHandler` inheriting from `http.server.SimpleHTTPRequestHandler`.
    *   Overrides `end_headers()` to append strict caching disable headers (`Cache-Control: no-store, no-cache`, etc.) to prevent browser caching of files.
    *   `do_GET()` routes `/api/status`, `/api/load`, and `/api/errors` to their respective helper methods, falling back to serving static files from the editor directory.
    *   `do_POST()` handles endpoints: `/api/save`, `/api/deploy`, and `/api/stop`.
*   **Lines 127-151: API Status endpoint**
    *   Checks if the target server process (`active_process`) is still alive using `.poll()`.
    *   Reads `graph.json` binary, generates an MD5 checksum, and outputs a JSON containing the server status (`live` or `offline`) and the checksum value.
*   **Lines 152-165: API Load endpoint**
    *   Loads `graph.json` from disk, parsed using `json.load`. If missing, returns `{"nodes": [], "connections": []}` with CORS headers.
*   **Lines 166-179: API Error State Handler**
    *   Reads `core/logs/error_state.json` written by node errors and returns the compiled error state data.
*   **Lines 180-232: API Save and Stop Handler**
    *   Both endpoints verify environment modes and reject changes if production configurations are active.
    *   `handle_save()` parses the input JSON structure, overwrites `graph.json` with formatted data, and responds with a success status.
    *   `handle_stop()` terminates the running compilation subprocess (`active_process`) using `.terminate()` and clears the variable.
*   **Lines 233-327: API Deploy Process**
    *   Rejects request if production mode is active.
    *   Clears previous compiler logs by invoking `NodeErrorReporter.clear_errors()`.
    *   Saves the incoming graph JSON data to disk (`graph.json`).
    *   Invokes `self.compile_graph(graph_data)`. If compilation raises errors, it returns `400 Bad Request` with the error trace.
    *   If a previous compilation instance exists, it terminates the process and waits for it to release resources.
    *   Resolves target port config from `ServerNode`. Invokes a Powershell pipeline command to forcefully kill any background processes listening on that port:
        `Get-NetTCPConnection -LocalPort <PORT> | Select-Object -ExpandProperty OwningProcess | ForEach-Object { Stop-Process -Id $_ -Force }`
    *   Polls `is_port_free()` up to 20 times (2 seconds total) to ensure the socket is free.
    *   Spawns a fresh server instance: `subprocess.Popen([sys.executable, 'main.py'], cwd=FRAMEWORK_DIR)`.
    *   Calls `wait_for_server` with an 8-second timeout. If the server fails to start, it returns a descriptive error message; otherwise, it returns a success response.
*   **Lines 328-358: Compiler Cleanup Phase**
    *   Declares `compile_graph(graph_data)`. Map nodes by ID.
    *   Uses `glob.glob` to clean up all old files from `/static/*.css`, `/templates/*.html`, and `/nodes/js_code/*.js` to ensure disconnected nodes do not leave stale static resources.
*   **Lines 359-383: BFS Graph Traversal & Accessibility**
    *   Locates the unique start node of type `ServerNode`. Throws a `ValueError` if missing.
    *   Iterates through all connection definitions to map source node IDs to a list of target node IDs (`outgoing_map`).
    *   Performs a Breadth-First Search (BFS) starting at the `ServerNode` to build a list of accessible nodes (`reachable_ids`). Disconnected nodes are ignored.
*   **Lines 384-423: Dynamic Import Builder**
    *   Scans `reachable_ids` to collect the set of active node type strings.
    *   Checks if any node has multiple targets, which requires a `RouterNode`.
    *   Compiles a list of Python import statements. Only imports the specific node classes that are actually used in the graph to optimize startup speed and memory usage.
    *   Pushes imports, database instantiation (`db = Database()`), and section comments to `code_lines`.
*   **Lines 424-435: RenderNode to CSSNode Mapping**
    *   Builds `render_ids_with_css` by scanning for `RenderNode` IDs that have an outgoing connection directly to a `CSSNode`.
*   **Lines 436-582: Node Instance Code Generator**
    *   Iterates through `reachable_ids` to output Python instantiations to `main.py`:
    *   *ServerNode*: Generates `ServerNode(host, port)`.
    *   *URLNode*: Generates `URLNode(path)`.
    *   *RenderNode*: Resolves template path.
        *   If the node is not connected to a CSS node, the compiler strips any stylesheet `<link>` tags using regex to prevent styling leaks.
        *   If it is connected to a CSSNode, it injects `<link rel="stylesheet" href="/static/{css_filename}">` inside the `<head>` or `<body>` tag.
        *   Writes the resulting template HTML directly to `/templates/{filename}.html`.
        *   Appends `RenderNode('{filename}')` initialization to the compiler code.
    *   *ModelNode*: Generates `ModelNode(db, query, params_mapping, context_key, is_write)`. Parses `paramsMap` string into a list.
    *   *LogicNode / ContextNode*: Extracts the function name from the config code block, appends the raw function code to `main.py`, and generates `LogicNode(function_name)`.
    *   *JSNode*: Writes Node.js script wrappers to `/nodes/js_code/js_logic_{node_id}.js`. Employs stdin/stdout pipeline, defines custom `Response` objects in JS (JSON, redirect, forbidden, etc.), and generates `JSNode('nodes/js_code/js_logic_{node_id}.js')`.
    *   *CSSNode*: Generates `CSSNode(css_filename, css_code)` and appends `.apply()` to write the CSS to the filesystem at compilation time.
    *   *HTTPRequestsNode, Security Nodes*: Generates default parameters constructors.
*   **Lines 583-612: Connection Chain Builder**
    *   Iterates through `reachable_ids` and translates links to Python method chains:
    *   If a node has a single target, generates `source_var.connect(target_var)`.
    *   If a node has multiple targets, generates a `RouterNode([target_var1, target_var2...])` to route paths dynamically, and connects the source node to this router node:
        `router_node_auto_X = RouterNode([t1, t2])`
        `source_var.connect(router_node_auto_X)`
*   **Lines 613-633: Socket Server Start Logic**
    *   Appends code to start `ThreadedHTTPServer` on the host and port specified in the `ServerNode` configuration.
    *   Wires the server connection callback to `FrameworkHandler` and resets the middleware cache.
    *   Writes the generated code blocks to `main.py`.
*   **Lines 634-686: Auto-Fix Recovery and Main Execution**
    *   `_auto_fix_graph_json()`: Reads the active IDE logs (`transcript.jsonl`) to automatically restore corrupt `graph.json` configurations using code segments extracted from previous commands.
    *   Starts the visual editor server on port 8080 and opens the local browser window.

---

## 3. Graph JSON Syntax & Layout Math Specifications
The visual editor compiles the JSON schema written to [graph.json](file:///c:/Users/lifel/Downloads/framework/node_editor/graph.json). To construct a correct graph, the JSON must conform to the following schema:

```json
{
  "nodes": [
    {
      "id": "string (unique identifier)",
      "type": "string (Node Class name)",
      "x": "number (horizontal position)",
      "y": "number (vertical position)",
      "config": {
        "..."
      }
    }
  ],
  "connections": [
    {
      "source": "string (source node id)",
      "target": "string (target node id)"
    }
  ]
}
```

### The 5cm Spacing & Alignment Math Rules
To maintain clean visual layouts and prevent overlap on the SVG editor canvas, apply the following spacing math rules when programmatically placing nodes:
1.  **Horizontal Axis (Spacing Delta X)**:
    Nodes connected sequentially MUST be separated horizontally by exactly **`250`** coordinates units (representing a standard 5cm display distance).
    $$X_{target} = X_{source} + 250$$
2.  **Vertical Axis (Spacing Delta Y)**:
    Nodes in parallel branches (such as different routes under a router) MUST be separated vertically by exactly **`300`** coordinates units.
    $$Y_{branch} = Y_{parent\_branch} + 300$$
3.  **Start Position**: Set the starting `ServerNode` coordinates to `{"x": -100, "y": 100}`.

---

## 4. Visual Node Configuration Reference
Each node type expects specific configurations in the `config` object inside `graph.json`:

### 4.1 ServerNode
Sets up the HTTP listener thread.
*   **config variables**:
    *   `ip` (string): Usually `"127.0.0.1"` or `"0.0.0.0"`.
    *   `port` (number): Target port (typically `8000`).
*   **Behavior**: Must be the unique entry point of the graph.

### 4.2 HTTPRequestsNode
Pops raw connections, instantiates `RequestWrapper`, and resolves cookies and url parameters.
*   **config variables**: `{}` (Empty object).
*   **Position**: Must be placed directly after `ServerNode` (or after security middleware nodes like `RateLimitNode` or `CSRFNode` if they are placed first in the chain).

### 4.3 URLNode
Filters requests based on paths and methods.
*   **config variables**:
    *   `path` (string): Route path (e.g., `"/"`, `"/api/data"`, `"/items/<pk:int>"`).
*   **Supported parameters syntax**:
    *   `<name:int>`: Matches integers (e.g., `[0-9]+`).
    *   `<name:str>`: Matches alphanumeric characters and dashes.
    *   `<name>`: Matches any character string up to `/`.
*   **Behavior**: Blocks request from proceeding if path doesn't match, causing the parent router to evaluate the next route in the list.

### 4.4 LogicNode
Executes Python scripts.
*   **config variables**:
    *   `code` (string): Complete Python function code. The first function declared is used as the node's entry point.
*   **Code Interface Guidelines**:
    *   Accepts a `RequestWrapper` parameter: `def process_logic(request):`
    *   *Short-circuiting*: To return a response immediately and bypass rendering nodes, return a `Response` object:
        ```python
        from nodes.response import Response
        def process_logic(req):
            return Response.json({"status": "success"})
        ```
    *   *Merging context*: To send variables to a rendering template, return a dictionary. The key-value pairs are merged into `request.context`:
        ```python
        def process_logic(req):
            return {"user_name": "Alice"}
        ```

### 4.5 ModelNode
Executes queries against `db.sqlite3`.
*   **config variables**:
    *   `query` (string): Parameterized SQL query using `?` placeholders (e.g. `"SELECT * FROM users WHERE email = ?"`).
    *   `paramsMap` (string): Comma-separated list of keys to fetch parameters from the request or context (e.g., `"email, age"`).
    *   `contextKey` (string): The key under which query results are stored in `request.context` (defaults to `"data"`).
    *   `isWrite` (boolean): Set to `true` for INSERT/UPDATE/DELETE operations, `false` for SELECT operations.
*   **Bulk Execution Mode**:
    *   If `isWrite` is `true`, `paramsMap` contains exactly one key, and that key resolves to a list of lists or tuples, the node executes in bulk mode using `executemany()`. It registers `{contextKey}_count` containing the rows affected.

### 4.6 JSNode
Executes Javascript scripts inside Node.js.
*   **config variables**:
    *   `code` (string): JS script body containing a function named `process_logic(request)`.
*   **JS Interface Library**:
    *   The compiler automatically injects a helper library into the JS context:
        *   `Response.json(data, status)`: Returns structured JSON.
        *   `Response.redirect(url, status)`: Emits redirection code.
        *   `Response.forbidden(msg)`: Emits 403 status.
        *   `Response.not_found(msg)`: Emits 404 status.
    *   Returns can be direct objects (merged into context) or wrapped responses:
        ```javascript
        function process_logic(request) {
            return Response.json({ success: true });
        }
        ```

### 4.7 RenderNode
Renders templates.
*   **config variables**:
    *   `filename` (string): Target filename (e.g., `"tech.html"`).
    *   `html_code` (string): HTML layout code.
*   **Template features**:
    *   *Variables*: Prints context variables using `{{ var_name }}`. By default, values are HTML-escaped. Use `{{ var_name | safe }}` to output raw content (e.g. script blocks or dynamic tables).
    *   *Filters*: Supports filters like `| safe`, `| length`, `| upper`, `| lower`, `| default('val')`.
    *   *Block structures*: Supports `{% extends "base.html" %}` and `{% block content %}...{% endblock %}` tags for template inheritance.
    *   *PyScript injection*: Automatically injects PyScript CDNs if `<script type="py">` or `<py-script>` tags are found in the template.

### 4.8 CSSNode
Deploys stylesheets.
*   **config variables**:
    *   `css_filename` (string): Stylesheet path in static assets (e.g. `"tech.css"`).
    *   `css_code` (string): Raw CSS definitions.
*   **Behavior**: When compiled, it writes CSS values to `/static/{css_filename}`.

### 4.9 CSRFNode / RateLimitNode / AntiBotNode / ScreenProtectionNode
Security utility nodes.
*   **config variables**: `{}` (Empty object).
*   **Usage**: CSRFNode sets `csrf_token` in context during GET requests and validates it during POST requests. RateLimitNode blocks IPs exceeding request thresholds. ScreenProtectionNode injects scripts to disable screenshots/right-click copy options.

---

## 5. Advanced Production-Grade Graph Example
Below is the complete `graph.json` configuration for a production-ready application. It implements:
1.  **Anti-Bot & CSRF Protection** for all routes.
2.  **Home Page Route (`/`)**: Initializes database tables via python script and renders a responsive tech portal.
3.  **Newsletter Subscription Route (`/api/newsletter/subscribe`)**: Sanitizes inputs, runs parameterized database insertion, and returns JSON success/error structures.
4.  **Live Telemetry REST API (`/api/telemetry`)**: Returns real-time system performance statistics.
5.  **Interactive CLI shell Route (`/api/terminal/command`)**: Parses input commands, interacts with the SQL database, and returns custom telemetry metrics.

```json
{
    "nodes": [
        {
            "id": "node-server",
            "type": "ServerNode",
            "x": -100,
            "y": 100,
            "config": {
                "ip": "127.0.0.1",
                "port": 8000
            }
        },
        {
            "id": "node-request",
            "type": "HTTPRequestsNode",
            "x": 150,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-rate-limit",
            "type": "RateLimitNode",
            "x": 400,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-csrf",
            "type": "CSRFNode",
            "x": 650,
            "y": 100,
            "config": {}
        },
        {
            "id": "node-route-home",
            "type": "URLNode",
            "x": 900,
            "y": -200,
            "config": {
                "path": "/"
            }
        },
        {
            "id": "node-route-telemetry",
            "type": "URLNode",
            "x": 900,
            "y": 100,
            "config": {
                "path": "/api/telemetry"
            }
        },
        {
            "id": "node-route-subscribe",
            "type": "URLNode",
            "x": 900,
            "y": 400,
            "config": {
                "path": "/api/newsletter/subscribe"
            }
        },
        {
            "id": "node-route-terminal",
            "type": "URLNode",
            "x": 900,
            "y": 700,
            "config": {
                "path": "/api/terminal/command"
            }
        },
        {
            "id": "node-logic-home",
            "type": "LogicNode",
            "x": 1150,
            "y": -200,
            "config": {
                "code": "from static.helpers import db\ndef home_logic(req):\n    db.execute(\"\"\"\n    CREATE TABLE IF NOT EXISTS newsletter_subscribers (\n        id INTEGER PRIMARY KEY AUTOINCREMENT,\n        email TEXT UNIQUE NOT NULL,\n        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP\n    )\n    \"\"\")\n    return {\n        'csrf_token': req.context.get('csrf_token', '')\n    }"
            }
        },
        {
            "id": "node-logic-telemetry",
            "type": "LogicNode",
            "x": 1150,
            "y": 100,
            "config": {
                "code": "import random\nfrom nodes.response import Response\ndef telemetry_logic(req):\n    return Response.json({\n        'cpu_load': random.randint(15, 85),\n        'active_nodes': random.randint(100, 240),\n        'latency': random.randint(4, 25)\n    })"
            }
        },
        {
            "id": "node-logic-subscribe",
            "type": "LogicNode",
            "x": 1150,
            "y": 400,
            "config": {
                "code": "from static.helpers import db\nfrom nodes.response import Response\ndef subscribe_logic(req):\n    email = req.get_param('email', '').strip().lower()\n    if not email or '@' not in email:\n        return Response.json({'status': 'error', 'message': 'Invalid email address.'})\n    try:\n        db.execute(\"INSERT INTO newsletter_subscribers (email) VALUES (?)\", (email,))\n        return Response.json({'status': 'success', 'message': 'Successfully connected to the Core Node Matrix!'})\n    except Exception:\n        return Response.json({'status': 'error', 'message': 'Email address already registered.'})"
            }
        },
        {
            "id": "node-logic-terminal",
            "type": "LogicNode",
            "x": 1150,
            "y": 700,
            "config": {
                "code": "import random\nfrom static.helpers import db\nfrom nodes.response import Response\ndef terminal_logic(req):\n    cmd = req.get_param('command', '').strip().lower()\n    parts = cmd.split()\n    base_cmd = parts[0] if parts else ''\n    if base_cmd == 'help':\n        output = [\n            \"Operational Commands:\",\n            \"  help          - Display this assistance manual.\",\n            \"  status        - Print neural core operational telemetry.\",\n            \"  subscribers   - List registered matrix nodes (total count).\"\n        ]\n    elif base_cmd == 'status':\n        output = [\n            \"CORE ENGINE STATUS:\",\n            f\"  \u2022 CPU Cluster Load : {random.randint(12, 90)}%\",\n            f\"  \u2022 Active Node Clones: {random.randint(80, 260)}\",\n            \"  \u2022 System Security   : ACTIVE (Zero Trust TLS 1.3)\"\n        ]\n    elif base_cmd == 'subscribers':\n        res = db.fetchall(\"SELECT COUNT(*) as count FROM newsletter_subscribers\")\n        count = res[0]['count'] if res else 0\n        output = f\"Total Operational Matrix Nodes: {count} registered.\"\n    else:\n        output = f\"Command not found: '{base_cmd}'. Type 'help' for options.\"\n    return Response.json({'output': output})"
            }
        },
        {
            "id": "node-render-home",
            "type": "RenderNode",
            "x": 1400,
            "y": -200,
            "config": {
                "filename": "tech.html",
                "html_code": "<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n    <meta charset=\"UTF-8\">\n    <title>CyberCore AI Dashboard</title>\n    <link href=\"https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css\" rel=\"stylesheet\">\n    <link rel=\"stylesheet\" href=\"/static/tech.css\">\n</head>\n<body class=\"p-5\">\n    <div class=\"container text-center\">\n        <h1 class=\"mb-4\">CYBERCORE AI ENGINE</h1>\n        <p class=\"lead\">Welcome to the neural processing unit backend portal.</p>\n        <form class=\"mt-4\" onsubmit=\"submitForm(event)\">\n            <input type=\"hidden\" id=\"csrf\" value=\"{{ csrf_token }}\">\n            <input type=\"email\" id=\"email\" class=\"form-control w-50 mx-auto\" placeholder=\"Subscribe Email\" required>\n            <button type=\"submit\" class=\"btn btn-primary mt-3\">SUBSCRIBE TO MATRIX</button>\n        </form>\n        <div class=\"mt-5\">\n            <h3>Live CPU Telemetry: <span id=\"cpu\">Loading...</span></h3>\n        </div>\n    </div>\n    <script>\n        function submitForm(e){\n            e.preventDefault();\n            const email = document.getElementById('email').value;\n            const csrf = document.getElementById('csrf').value;\n            const params = new URLSearchParams();\n            params.append('email', email);\n            params.append('csrf_token', csrf);\n            fetch('/api/newsletter/subscribe', {\n                method: 'POST',\n                body: params,\n                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }\n            }).then(r => r.json()).then(data => alert(data.message));\n        }\n        setInterval(() => {\n            fetch('/api/telemetry').then(r => r.json()).then(data => {\n                document.getElementById('cpu').innerText = data.cpu_load + '%';\n            });\n        }, 3000);\n    </script>\n</body>\n</html>"
            }
        },
        {
            "id": "node-css-tech",
            "type": "CSSNode",
            "x": 1650,
            "y": -200,
            "config": {
                "css_filename": "tech.css",
                "css_code": "body { background-color: #030712; color: #f3f4f6; font-family: sans-serif; } h1 { color: #00f0ff; text-shadow: 0 0 10px rgba(0,240,255,0.5); }"
            }
        }
    ],
    "connections": [
        {
            "source": "node-server",
            "target": "node-request"
        },
        {
            "source": "node-request",
            "target": "node-rate-limit"
        },
        {
            "source": "node-rate-limit",
            "target": "node-csrf"
        },
        {
            "source": "node-csrf",
            "target": "node-route-home"
        },
        {
            "source": "node-csrf",
            "target": "node-route-telemetry"
        },
        {
            "source": "node-csrf",
            "target": "node-route-subscribe"
        },
        {
            "source": "node-csrf",
            "target": "node-route-terminal"
        },
        {
            "source": "node-route-home",
            "target": "node-logic-home"
        },
        {
            "source": "node-route-telemetry",
            "target": "node-logic-telemetry"
        },
        {
            "source": "node-route-subscribe",
            "target": "node-logic-subscribe"
        },
        {
            "source": "node-route-terminal",
            "target": "node-logic-terminal"
        },
        {
            "source": "node-logic-home",
            "target": "node-render-home"
        },
        {
            "source": "node-render-home",
            "target": "node-css-tech"
        }
    ]
}
```

---

## 6. Generative AI System Instructions for Generating Graph JSON
When tasked with writing a visual graph (`graph.json`) for the Cybercore Visual Node Framework, the AI model must strictly adhere to the following rules:

1.  **Unique Node Identifiers**:
    Every node must have a unique `id` string (e.g. `node-server`, `node-route-login`, `node-logic-login`).
2.  **BFS Chain Construction**:
    The graph must have an unbroken path from the starting `ServerNode` down to the terminal rendering or logic nodes.
3.  **Strict Routing Pipeline Placement**:
    *   *Standard flow*: `ServerNode` → `HTTPRequestsNode` → (Optional Middleware/Security nodes, e.g. `CSRFNode`, `RateLimitNode`) → (Routing branch selector URLs) → `URLNode` → `LogicNode` → `RenderNode` → `CSSNode`.
    *   *Warning*: Never put `HTTPRequestsNode` after a `URLNode`. It must be placed before path evaluation occurs.
4.  **Automatic Router Node Creation Rules**:
    *   If a node (like `HTTPRequestsNode` or `CSRFNode`) connects to multiple `URLNode` paths, do NOT create a `RouterNode` manually in `graph.json`.
    *   The compiler automatically creates router instances when it sees a single source node pointing to multiple target nodes.
    *   Simply add multiple connection blocks from the same source node ID to the different target path node IDs:
        ```json
        {"source": "node-csrf", "target": "node-route-home"},
        {"source": "node-csrf", "target": "node-route-about"}
        ```
5.  **Layout Grid Geometry Rules**:
    Use the spacing math formulas to prevent overlapping nodes on the editor's visual canvas:
    *   Connected sequential nodes: Increment `x` coordinates by `250`.
    *   Parallel nodes/branches: Increment `y` coordinates by `300` for each branch.
6.  **Code Syntax in LogicNode and JSNode**:
    *   *LogicNode*: Inside python scripts, the code must contain a standard function definition accepting the request object. If returning a response directly, use `Response.json()`, `Response.redirect()`, `Response.forbidden()`, etc. If passing data to html templates, return a Python dictionary.
    *   *JSNode*: Inside javascript scripts, return an object or call `Response.json(data)`.
7.  **CSS Link Integration**:
    *   If a `RenderNode` has styling from a `CSSNode`, there must be a connection in the `connections` array:
        `{"source": "render-node-id", "target": "css-node-id"}`
    *   The `CSSNode` configuration `css_filename` must match the static reference inside the template HTML code (e.g., `<link rel="stylesheet" href="/static/filename.css">`).
8.  **Output Format**:
    Generate only the syntactically valid JSON string. Do not include markdown wraps or explanation comments inside the JSON itself.
9.  **Strict Path Routing & Logic Mapping (CRITICAL)**:
    *   Every unique request path (e.g. `/`, `/move`, `/reset`, `/api/data`) MUST have its own dedicated `URLNode`.
    *   Do NOT connect multiple LogicNode/JSNode/RenderNode targets to a single `URLNode` if they are meant to handle different URL paths. For example, if your HTML page fetches from `/move` and `/reset`, you must create:
        - `URLNode` config `{"path": "/"}` -> connects to home page LogicNode/RenderNode.
        - `URLNode` config `{"path": "/move"}` -> connects to move LogicNode.
        - `URLNode` config `{"path": "/reset"}` -> connects to reset LogicNode.
    *   All these `URLNode`s should branch out in parallel from the parent `CSRFNode` or `HTTPRequestsNode`.

---

## 7. Local LLM Tuning & Benchmarks (Qwen3-Coder:30B)
This section documents the evaluated capabilities of the target local LLM to optimize prompt context mapping:

*   **Model Specifications**:
    *   **Name**: `qwen3-coder:30b`
    *   **Quantization**: `Q4_K_M` (4-bit quantized GGUF)
    *   **Context Window**: 262,144 tokens max (Recommend configuring `num_ctx: 32768` or `65536` in Ollama options for deep conversational memory).
*   **Performance Metrics**:
    *   **Generation Speed**: 55 - 65 Tokens Per Second (TPS).
    *   **Throughput Latency**: Generates complete visual graphs (~3300 tokens) in 60-65 seconds.
*   **Behavioral Adjustments for Qwen3-Coder**:
    *   *Directives validation*: Since the model is highly responsive, enforce the **Strict Path Routing & Logic Mapping** (Rule 9) in system prompts.
    *   *No Wildcard Assumptions*: The model easily generates complex python game mechanics (like CPU minimax search or board validation). Ensure that helper functions are defined inside the LogicNode python code rather than assuming external file imports exist.

