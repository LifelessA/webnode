# WebNode Framework

A custom, lightweight, node-based web framework for Python. Built on top of `http.server`, it envisions web request processing as a flowchart of connected nodes.

**New in v0.3.0:**
*   **Visual Node Editor**: A built-in GUI (runs at `http://localhost:8080`) to visually wire nodes, write logic, and deploy your web app — no code needed!
*   **Database Support**: Built-in SQLite wrapper (FKs, Triggers, Stored Procedures, DDL).
*   **MVC Architecture**: Dedicated `ModelNode` for database interactions.
*   **Full HTTP Support**: GET, POST, PUT, PATCH, DELETE methods fully supported.
*   **Security Suite**: Rate Limiting, CSRF Protection, Anti-Bot, and Screen Protection.
*   **Logging**: Request logging per IP to `core/logs/`.

## 📦 Installation

### From GitHub
You can install WebNode directly from this repository:

```bash
pip install git+https://github.com/LifelessA/webnode.git
```

## 🚀 Getting Started

### 1. Create a Project
Use the CLI command to generate a new project structure:

```bash
# If installed via pip
node-web startproject my_website

# OR if you prefer the module method
python -m webnode.cli startproject my_website
```

### 2. Run the Server
Navigate to your project and run `main.py`:

```bash
cd my_website
python main.py
```
Visit `http://localhost:8000` in your browser.

## 🧠 Core Concepts & "Technique"

WebNode is different from Flask or Django. Instead of decorators (like `@app.route`), we use a **Graph of Nodes**.

**The Flow:**
`Server` -> `Request Processor` -> `Router` -> `[Your Custom Chain]` -> `Response`

Every component is a **Node**. You connect them together like a chain to define how data moves:

```python
# The "Technique": Chaining Nodes
node_a.connect(node_b).connect(node_c)
```

Data flows through this chain. Each node receives the `request` object, processes it, and passes it to the next node.

### How to Code in WebNode

1.  **Define Logic**: Write simple Python functions that take a `request` object and return a dictionary of data.
2.  **Create Nodes**: Wrap your functions in specific Node classes (like `LogicNode`).
3.  **Wire it Up**: Connect your nodes in `main.py` using `.connect()`.

## 📚 Node Reference

Here is how to use each node available in the framework:

### 1. ServerNode (`nodes.server_node`)
The **Root Node**. It starts the web server and listens for connections.
*   **Purpose**: Initializes the server.
*   **Usage**: `server_node = ServerNode(port=8000)`
*   **Next Step**: Must connect to `HTTPRequestsNode`.

### 2. HTTPRequestsNode (`nodes.http_requests_node`)
The **Translator**. Converts raw server data into a friendly `request` object.
*   **Purpose**: Creates the `request` object used by all other nodes.
*   **Key Properties on `request`**:
    *   `request.path`: The URL path (e.g., `/home`).
    *   `request.method`: GET or POST.
    *   `request.context`: A dictionary for sharing data between nodes.
    *   `request.get_param('key')`: Helper to get POST form data.

### 3. URLNode (`nodes.url_node`)
The **Router/Gatekeeper**.
*   **Purpose**: specific branch of nodes is only executed if the URL matches.
*   **Usage**: `url_home = URLNode('/')`
*   **Logic**: If `request.path == '/'`, it passes the request to the next node. If not, it stops.

### 4. LogicNode (`nodes.logic_node`)
The **Brain**. Executes your custom Python functions.
*   **Purpose**: To run business logic (calculations, database calls, etc.).
*   **Usage**: `node = LogicNode(my_python_function)`
*   **Coding Technique**:
    Define a function that returns a `dict`. This dict is automatically merged into `request.context`.
    ```python
    def my_logic(request):
        return {'username': 'Aniket'} # Available as {username} in templates
    ```

### 5. ContextNode (`nodes.context_node`)
The **Setup**. Very similar to LogicNode, but conceptually used for setting up the environment.
*   **Purpose**: Prepare data needed for rendering.
*   **Usage**: `node = ContextNode(setup_function)`

### 6. RenderNode (`nodes.template_node`)
The **Viewer**. Renders an HTML template.
*   **Purpose**: Returns the final HTML to the browser.
*   **Usage**: `render = RenderNode('index.html')`
*   **Technique**: It looks for `{placeholders}` in your HTML file and replaces them with values from `request.context`.

### 7. RouterNode (`nodes.route_node`)
The **Traffic Controller**.
*   **Purpose**: Manages multiple URL branches.
*   **Usage**: `router = RouterNode([url_branch1, url_branch2])`
*   **Technique**: Pass a list of `URLNode` instances (the start of each chain) to the router. It checks each one in order.

### 8. ModelNode (`nodes.model_node`)
The **Data Layer**.
*   **Purpose**: Executes SQL queries against the internal SQLite database.
*   **Usage**: `model = ModelNode(query="SELECT * FROM users", context_key='users')`
*   **Features**:
    *   **Read**: Fetches results and stores them in `request.context[context_key]`.
    *   **Write**: Executes INSERT/UPDATE/DELETE when `is_write=True`.
    *   **Bulk**: Automatically handles bulk inserts if the expected parameter is a list.

---

## 🛡️ Security & Plugins (v0.2.0+)

WebNode includes a suite of security nodes in `plugins/`. These are enabled by default in `settings.SECURITY`.

### Security Nodes
*   **RateLimitNode**: Limits requests per IP (Default: 50 requests / 60s).
*   **CSRFNode**: Token-based protection for POST requests.
*   **AntiBotNode**: Blocks requests from known bot User-Agents.
*   **ScreenProtectionNode**: Client-side privacy overlay (black screen on screenshot/blur).

### Logging
*   **ActionLoggerNode**: Logs all requests to `core/logs/{client_ip}.txt`.

---

## ⚡ Node Editor (v0.3.0 — New!)

WebNode 0.3.0 includes a **visual, browser-based Node Editor** — a graphical interface for building your web application without writing code.

### How to Run the Node Editor

After creating your project with `node-web startproject my_project`:

```bash
cd my_project
python node_editor/node_backend.py
```

Open your browser at **http://localhost:8080**.

### Features
*   **Drag & Drop Nodes** from the sidebar Library panel onto the canvas.
*   **Connect Nodes** by dragging from the `▶` out-port to the `●` in-port of another node.
*   **Inline Python Logic** — `LogicNode` and `ContextNode` have a built-in Monaco editor (same engine as VS Code).
*   **Deploy & Run** — Click **"Deploy & Run"** to compile your node graph into `main.py` and start the server automatically.
*   **Stop Server** — Click **"Stop Server"** to terminate the running process.
*   **Save JSON** — Saves your canvas as `node_editor/graph.json` (auto-loaded on restart).
*   **Visual Flow** — Nodes glow 🟢 green when the server is live and connected, 🔴 red when offline.
*   **Delete** — Double-click a node or wire to delete it.
*   **Pan & Zoom** — Pan by clicking and dragging the canvas; zoom with `Ctrl + Scroll`.

### Node Palette Categories
| Category | Nodes |
|---|---|
| **Core** | Server Node, HTTP Request, URL Router, Logic (Python), Context (Python) |
| **Views & DB** | Render Template, Model (SQL) |
| **Security & Logging** | Action Logger, Anti-Bot, Rate Limit, CSRF Token, Screen Protection |

---


## 💡 Example: Adding a New "About" Page

Follow this technique to add a new page:

### Step 1: Create Logic (optional)
In `static/logic.py`:
```python
def about_page_logic(request):
    return {'page_title': 'About WebNode', 'message': 'This is a node-based framework.'}
```

### Step 2: Create Template
Create `templates/about.html`:
```html
<h1>{page_title}</h1>
<p>{message}</p>
```

### Step 3: Wire it in `main.py`
```python
from static.logic import about_page_logic

# 1. Create the Nodes for this branch
url_about = URLNode('/about')                 # Branch for /about
logic_about = LogicNode(about_page_logic)     # Run logic
render_about = RenderNode('about.html')       # Show page

# 2. Connect the chain
url_about.connect(logic_about).connect(render_about)

# 3. Add to the Router
# Assuming you already have a RouterNode list:
router_node = RouterNode([url_index, url_about])
```
