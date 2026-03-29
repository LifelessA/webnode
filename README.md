# WebNode Framework (v0.4.0) — The AI-Friendly Documentation

Welcome to **WebNode**, a lightweight, high-performance, graph-based Python web framework. WebNode abandons traditional decorators (like Flask or Django) in favor of a **Node Graph Architecture**. In WebNode, every phase of an HTTP request is a "Node", and you wire these nodes together to create a flowchart of data.

> **🤖 FOR AI ASSISTANTS:** If a user provides this README and asks you to build a website, **read this document carefully**. This framework is NOT Flask or Django. Do NOT use `@app.route` decorators. WebNode is 100% Python-based for the backend. Follow the "Graph of Nodes" pattern explained below.

---

## 🏗️ Directory Structure Overview

When a new WebNode project is created, it looks like this:

```text
my_project/
├── main.py                 # The ENTRY POINT. Here we wire nodes together.
├── wsgi.py                 # For production servers (Gunicorn/uWSGI).
├── settings.py             # Global configurations.
├── setup_project.py        # Run once to initialize DB, Keys, and Logs.
├── core/                   # Framework utilities (do not modify).
│   ├── db.py               # Singleton SQLite wrapper.
│   ├── sessions.py         # Cookie-based session tracking.
│   ├── validators.py       # Helper functions to sanitize inputs.
│   └── errors.py           # HTML error tracing.
├── nodes/                  # The Node classes.
├── plugins/                # Security (CSRF, RateLimit, AntiBot) & Loggers.
├── static/                 # Put your PYTHON business logic and CSS here.
│   ├── app_logic.py        # (Example) Your Python functions go here.
│   └── main.css
├── templates/              # Put your HTML files here (Jinja-style).
└── node_editor/            # The visual GUI editor (runs on port 8080).
```

---

## 🚀 How to Build a Web Page in WebNode (The Code Way)

To build a feature in WebNode, you must follow the **Node Chain** methodology.
A standard page consists of: `URLNode` ➔ `LogicNode` ➔ `RenderNode`.

### Step 1: Write Python Business Logic (in `static/my_logic.py`)
Logic functions take a `request` wrapper object and return either:
1. A **Dictionary** (passed to the HTML template as context variables).
2. A **Response** object (to immediately abort the graph and send HTTP data like JSON or Redirects).

```python
# static/my_logic.py
from core.db import Database
from nodes.response import Response
from core.sessions import get_session_id

db = Database()

def profile_logic(request):
    # 1. Get URL parameters (e.g., from /profile/<user_id>)
    user_id = request.url_params.get('user_id')
    
    # 2. Get Query parameters (e.g., from ?tab=settings)
    tab = request.query_params.get('tab', 'overview')
    
    # 3. Get POST Form data
    if request.method == 'POST':
        new_name = request.get_param('name')
        db.execute("UPDATE users SET name=? WHERE id=?", (new_name, user_id))
        return Response.redirect(f'/profile/{user_id}?success=1')
    
    # 4. Fetch Data
    user_data = db.fetchall("SELECT * FROM users WHERE id=?", (user_id,))
    if not user_data:
        return Response.not_found("User does not exist")
        
    # 5. Return data to the HTML template
    return {
        'user': user_data[0],
        'current_tab': tab,
        'csrf_token': request.context.get('csrf_token', '') # From CSRFMiddleware
    }
```

### Step 2: Create the HTML Template (in `templates/profile.html`)
WebNode includes a custom rendering engine supporting `{{ variables }}`, `{% for %}`, `{% if %}`, and `{% extends %}`.

```html
<!-- templates/profile.html -->
<!DOCTYPE html>
<html>
<head><title>Profile: {{ user.name }}</title></head>
<body>
    <h1>Welcome, {{ user.name }}!</h1>
    
    {% if current_tab == 'settings' %}
        <form method="POST">
            <input type="hidden" name="csrf_token" value="{{ csrf_token }}">
            <input type="text" name="name" value="{{ user.name }}">
            <button type="submit">Update</button>
        </form>
    {% else %}
        <p>Email: {{ user.email }}</p>
    {% endif %}
</body>
</html>
```

### Step 3: Wire the Nodes in `main.py`
In `main.py`, you tie the URL, the Logic, and the Template together in a chain, then add it to the Router.

```python
# main.py
from nodes.server_node import ServerNode
from nodes.http_requests_node import HTTPRequestsNode
from nodes.url_node import URLNode
from nodes.logic_node import LogicNode
from nodes.template_node import RenderNode
from nodes.route_node import RouterNode

from static.my_logic import profile_logic

# 1. Instantiate the Server and Request Parser
server = ServerNode(host='127.0.0.1', port=8000)
http_parser = HTTPRequestsNode()

# 2. Instantiate Your Branch Nodes
# URLNode handles dynamic segments using <variable_name>
url_profile = URLNode('/profile/<user_id>')
logic_profile = LogicNode(profile_logic)
render_profile = RenderNode('profile.html')

# 3. Connect the Chain together! 
# Flow: If URL matches -> Run Logic -> Render HTML
url_profile.connect(logic_profile).connect(render_profile)

# 4. Add the branch to the main Router
router = RouterNode([url_profile])

# 5. Connect the core pipeline
server.connect(http_parser).connect(router)

# 6. Start the server
from nodes.server_node import FrameworkHandler
FrameworkHandler.server_node = server
from http.server import HTTPServer
with HTTPServer((server.host, server.port), FrameworkHandler) as httpd:
    httpd.serve_forever()
```

---

## 🛠️ The WebNode Toolkit for AI & Developers

### 1. Database Operations (`core.db.Database`)
WebNode comes with a built-in, thread-safe SQLite wrapper.
A global database instance is easy to use:

```python
from core.db import Database
db = Database() # Singleton

# Read Multi
rows = db.fetchall("SELECT * FROM products WHERE price > ?", (50.0,))

# Write Single
db.execute("INSERT INTO logs (action) VALUES (?)", ("login",))

# Write Multi (Bulk Insert)
db.executemany("INSERT INTO data (val) VALUES (?)", [("A",), ("B",)])
```

### 2. Sessions (`core.sessions`)
Secure, server-side caching tied to an HttpOnly, SameSite cookie.

```python
from core.sessions import get_session_id, get_session_data, set_session_data

def cart_logic(request):
    # This automatically tracks the user locally and sets cookies
    sid = get_session_id(request)
    
    # Store data
    set_session_data(sid, 'account_type', 'premium')
    
    # Retrieve data
    data = get_session_data(sid)
    user_type = data.get('account_type', 'guest')
```

### 3. Returning JSON or Errors (`nodes.response`)
Usually, `LogicNode` returns a dictionary for the HTML. But if you want to build an API, return a `Response` object to short-circuit the graph.

```python
from nodes.response import Response

def my_api(request):
    data = {"status": "success", "items": [1, 2, 3]}
    return Response.json(data)

def delete_user(request):
    if not request.get_param('admin'):
        return Response.forbidden("Admins only!")
    return Response.redirect('/dashboard')
```

### 4. Live Streaming / SSE Support
WebNode natively supports Server-Sent Events (SSE) via Python Generators. Use this instead of complex JavaScript WebSockets.

```python
import time
from nodes.response import StreamingResponse

def live_clock(request):
    def generator():
        while True:
            yield f"Current Time: {time.time()}"
            time.sleep(1)
            
    # The browser will stream this data dynamically
    return {"stream": StreamingResponse(generator())}
```
*In HTML:* Just output `{{ stream | safe }}`.

### 5. Form Validation (`core.validators`)
Always validate POST inputs securely.

```python
from core.validators import validate_form

def process_form(request):
    rules = {
        'age': {'type': 'int', 'min': 18, 'max': 99},
        'email': {'type': 'email', 'required': True},
        'username': {'type': 'str', 'min_length': 3, 'max_length': 20}
    }
    cleaned_data, errors = validate_form(request, rules)
    
    if errors:
        return {'error_message': ", ".join(errors)}
        
    db.execute("INSERT INTO users (email, age) VALUES (?, ?)", 
               (cleaned_data['email'], cleaned_data['age']))
```

---

## ⚡ Visual Node Editor (Zero Code Routing)

Don't want to type `url_node.connect(logic_node)` manually in `main.py`? 
WebNode includes a **Visual GUI IDE** that runs right in your browser!

1. Start the visual editor:
   ```bash
   python node_editor/node_backend.py
   ```
2. Open `http://localhost:8080`.
3. Drag **URL Router**, **Python Logic**, and **HTML Template** blocks onto the visual canvas.
4. Draw lines to connect them.
5. Click **Deploy**. The GUI will auto-generate your entire `main.py` file perfectly and restart your active web server.

---

## 🤖 CHEATSHEET FOR AI AGENTS
If the user asks you to implement a feature in WebNode, respect these rules exactly:

1. **NO FLASK OR DJANGO**: Do not import flask, django, or fastapi.
2. **Directory Rules**: 
   - Business logic always goes in `static/<name>_logic.py`. 
   - HTML files always go in `templates/<name>.html`.
3. **Logic Functions**: All logic functions take `(request)` and must return exactly `dict` or `Response`.
4. **Data Access**: Use `request.get_param('key')` for POST forms, and `request.url_params.get('key')` for dynamic URL segments like `/users/<id>`.
5. **Database**: Import `from core.db import Database` and use `db = Database()`. Call `db.execute()` or `db.fetchall()`.
6. **Routing**: To expose a new URL, you MUST edit `main.py`, create a `URLNode`, a `LogicNode`, and a `RenderNode`, chain them together with `.connect()`, and append the `URLNode` to the `RouterNode([])` array. 
7. **Responses**: For JSON APIs or Redirects, use `from nodes.response import Response` and return `Response.json(dict)` or `Response.redirect(url)`.

**Example Prompt Response:**
"I will create the backend logic in `static/cart_logic.py`, design the interface in `templates/cart.html`, and wire the nodes together inside `main.py` using `URLNode('/cart') -> LogicNode -> RenderNode`."
