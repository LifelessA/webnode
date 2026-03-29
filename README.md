# WebNode Framework (v0.4.0)

A custom, powerful, node-based web framework for Python. Built around a "Graph of Nodes" architecture, WebNode provides a visual and code-based way to process HTTP requests just like a flowchart.

**🔥 New in v0.4.0 — The "Production Ready" Update:**
*   **Full Framework Structure**: Built-in architecture with `nodes/`, `core/`, `plugins/`, and `static/`.
*   **Middleware Chain**: Django-style request/response middleware architecture (`nodes/middleware/`).
*   **Advanced Engine Hooks**: Cookie-based sessions, Rotating file loggers, and HTML-styled Error pages.
*   **WSGI Support**: Ready for production deployment using Gunicorn or uWSGI via `wsgi.py`.
*   **Response Objects**: Return `Response` or `StreamingResponse` (for Server-Sent Events / Live Data) directly from nodes.
*   **CSS Node Integration**: Write and manage CSS directly from the visual Node Editor.

---

## 📦 Installation

WebNode is available directly from GitHub.

```bash
pip install git+https://github.com/LifelessA/webnode.git
```

## 🚀 Getting Started

### 1. Create a Project
Use the CLI command to generate a complete project structure:

```bash
node-web startproject my_website
cd my_website
```

### 2. Initialize the Project
Run the setup script once to generate secret keys, databases, and log directories:
```bash
python setup_project.py
```

### 3. Run the Server
Start the development server:
```bash
python main.py
```
Visit `http://localhost:8000` in your browser.

---

## 📂 Framework Directory Structure

When you create a project, WebNode auto-generates this scalable architecture:

```text
my_website/
├── main.py                 # Graph connection & Server entry point
├── wsgi.py                 # Production WSGI adapter
├── settings.py             # Global configurations, Middleware, DB, Security
├── setup_project.py        # Environment initiator
├── core/                   # Engine internals
│   ├── db.py               # Thread-safe SQLite singleton
│   ├── sessions.py         # Cookie-based session handling
│   ├── logging.py          # Rotating access/error logs
│   ├── errors.py           # Custom HTML debug pages
│   └── validators.py       # Helper functions for form validation
├── nodes/                  # Core Node Classes
│   ├── base_node.py
│   ├── url_node.py
│   ├── logic_node.py
│   ├── template_node.py
│   ├── response.py         # Response & StreamingResponse
│   └── middleware/         # Middleware chain pipeline
├── plugins/                # Security & Addons
│   ├── security.py         # RateLimit, CSRF, AntiBot, ScreenProtection
│   └── logger.py           # Request action logger
├── static/                 # Business Logic & Public Assets
│   └── shop_logic.py       # (Example logic handlers)
├── templates/              # HTML Templates
└── node_editor/            # ⚡ Visual Web Interface
```

---

## 🧠 Core Concepts & "Technique"

Instead of decorators (like `@app.route`), WebNode uses a **Graph of Nodes**.

**The Flow:**
`Server` -> `Middleware` -> `HTTP Request Processor` -> `[Your Custom Chain]` -> `Response`

Every component is a **Node**. You connect them together like a chain to define how data moves:

```python
# The "Technique": Chaining Nodes
node_a.connect(node_b).connect(node_c)
```

Data flows through this chain. Each node receives the `request` object, processes it, and passes it to the next node. If a node returns a `Response` object, the chain short-circuits and immediately replies to the browser.

### How to Code in WebNode

1.  **Define Logic**: Write Python functions that take a `request` wrapper.
2.  **Return Data**: Return a `dict` (for templates) OR a `Response` object (for immediate HTTP reply).
3.  **Create Nodes**: Wrap your functions in specific Node classes (like `LogicNode`).
4.  **Wire it Up**: Connect your nodes in `main.py` using `.connect()`.

---

## ⚡ Visual Node Editor

WebNode includes a **visual, browser-based Node Editor** — a graphical interface for building your web application without writing connection code manually.

### Accessing the Editor
```bash
python node_editor/node_backend.py
```
Open your browser at **http://localhost:8080**.

### Features
*   **Drag & Drop Nodes**: Drag URL routers, Logic nodes, Python compilers, and HTML renderers onto a canvas.
*   **Connect Nodes**: Draw connection lines between nodes to dictate data flow.
*   **Integrated Code Editing**: Code your Python logic directly inside the browser using the embedded Monaco Editor.
*   **Deploy**: Click "Deploy" to compile your visual graph instantly into `main.py` and restart the backend server.

---

## 📚 Core Nodes Reference

### 1. ServerNode (`nodes.server_node`)
The **Root Node**. Starts the web server and listens for connections.
*   **Usage**: `server_node = ServerNode(port=8000)`

### 2. HTTPRequestsNode (`nodes.http_requests_node`)
The **Translator**. Parses raw WSGI data and sets up the `request` context, sessions, and multipart forms.
*   **Methods**: `req.get_param('key')`, `req.get_file('file')`, `req.session_id`.

### 3. URLNode (`nodes.url_node`)
The **Router/Gatekeeper**.
*   **Usage**: `url_home = URLNode('/product/<id>')`
*   **Logic**: Executes the branch only if the URL and HTTP Method match. Automatically parses `<id>` into `request.url_params`.

### 4. LogicNode (`nodes.logic_node`)
The **Brain**. Executes your custom Python functions.
*   **Usage**: `node = LogicNode(my_logic_func)`

### 5. RenderNode (`nodes.template_node`)
The **Viewer**. Renders HTML templates using the internal Jinja-style Template Engine.
*   **Features**: Supports `{% extends %}`, `{% include %}`, `{% for %}`, and `{{ variables }}`.

### 6. RouterNode (`nodes.route_node`)
The **Traffic Controller**. Groups multiple `URLNode` branches together and executes the first one that matches.

---

## 🛡️ Security & Middleware

Security is built-in and configured via `settings.py`:

*   **RateLimitNode**: Limits requests per IP natively.
*   **CSRFNode**: Token-based protection for POST requests automatically validated in the graph.
*   **AntiBotNode**: Blocks malicious scraper User-Agents.
*   **ScreenProtectionNode**: Client-side privacy overlay.

---

## 🌐 Production Deployment (WSGI)

WebNode v0.4.0 is fully WSGI compatible. For production environments, do not run `main.py`. Instead, point your production runner (like `gunicorn`) to `wsgi.py`.

```bash
# Example using Gunicorn
pip install gunicorn
gunicorn wsgi:application --workers 4 --bind 0.0.0.0:8000
```
