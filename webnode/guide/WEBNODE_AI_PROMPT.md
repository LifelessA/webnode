# WebNode Framework - AI Coding Guidelines

You are an autonomous AI agent building a web application using the **WebNode** framework. 

**CRITICAL RULE**: WebNode uses a **Pure Python, JS-Free Architecture**. You must strictly adhere to the following principles when implementing features or fixing bugs.

## 1. Core Architecture
WebNode is a node-based backend framework. The flow of a request is always:
`ServerNode -> RouterNode -> URLNode -> LogicNode -> RenderNode (or Response)`

- `main.py` is the orchestrator where nodes are instantiated and connected.
- All routing happens visually or programmatically via connecting `URLNode(path)` to `LogicNode(function)`.

## 2. The "Pure Python Frontend" Philosophy
Do **NOT** write JavaScript. Do **NOT** use PyScript DOM manipulations (e.g., `document.getElementById`). Do not write inline `<script type="py">` code to update the DOM.

If the user asks for "frontend logic" or "interactivity":
1. Write a pure Python function in the `static/` directory (e.g., `static/shop_logic.py`).
2. The function footprint must be: `def my_logic(request):` and it MUST return a dictionary `{'key': 'value'}`.
3. Hook this function to a `LogicNode` in `main.py`.
4. In the HTML template, use standard HTML forms (`<form method="POST" action="/my-route">`) or links to trigger the backend route. 
5. The `RenderNode` will automatically receive the returned dictionary from the `LogicNode` and substitute variables in the HTML (using `{{ key }}` or `{key}`).

## 3. Example Implementation Pattern

**Wrong Way (JS/PyScript DOM Manipulation):**
```html
<!-- DO NOT DO THIS -->
<button py-click="update_text">Click</button>
<script type="py">
    def update_text(e): document.getElementById("msg").innerText = "Done!"
</script>
```

**Right Way (WebNode Pure Python Pattern):**

`static/message_logic.py`:
```python
# Pure python logic! No DOM imports.
def update_message_logic(request):
    return {"message": "Done! Updated purely via backend Python."}
```

`main.py`:
```python
from static.message_logic import update_message_logic

url_msg = URLNode('/update-message')
logic_msg = LogicNode(update_message_logic)
render_msg = RenderNode('message.html')

url_msg.connect(logic_msg)
logic_msg.connect(render_msg)
router_node.connect(url_msg) # Add to router
```

`templates/message.html`:
```html
<!-- Standard HTML form submission instead of JS onClick -->
<form method="POST" action="/update-message">
    <button type="submit">Click</button>
</form>

<p id="msg">{{ message }}</p>
```

This pattern ensures the entire application logic lives in `static/*.py` files as clean, testable pure Python functions.
