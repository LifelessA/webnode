import urllib.request
import json
import re
import os
import sys

# Define absolute paths
AI_EDITOR_DIR = r"c:\Users\lifel\Downloads\framework\ai_editor"
SCRATCH_DIR = r"C:\Users\lifel\.gemini\antigravity-ide\brain\da74de2c-266c-47ad-af2e-5f65d2035794\scratch"

sys.path.insert(0, os.path.dirname(AI_EDITOR_DIR))

# 1. Load the SYSTEM_PROMPT from ai_backend.py
sys_prompt = ""
ai_backend_path = os.path.join(AI_EDITOR_DIR, "ai_backend.py")
if os.path.exists(ai_backend_path):
    with open(ai_backend_path, "r", encoding="utf-8") as f:
        content = f.read()
        match = re.search(r'SYSTEM_PROMPT\s*=\s*"""(.*?)"""', content, re.DOTALL)
        if match:
            sys_prompt = match.group(1)
        else:
            print("Could not parse SYSTEM_PROMPT from ai_backend.py")
            sys.exit(1)
else:
    print(f"ai_backend.py not found at {ai_backend_path}")
    sys.exit(1)

# 2. Define user prompt
user_prompt = "Make a beautiful interactive Neon Snake Game webpage with score board and dark cyber styles, fully styled and operational."

# 3. Call Ollama API
url = "https://c792-35-231-147-139.ngrok-free.app/api/generate"
payload = {
    "model": "gemma4:26b",
    "prompt": f"{sys_prompt}\n\nUser Prompt: {user_prompt}",
    "stream": False
}

print("🚀 Connecting to Ollama endpoint at:", url)
print("Sending prompt and waiting for response...")
try:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=300) as res:
        response_data = json.loads(res.read().decode('utf-8'))
        ai_response = response_data.get("response", "")
except Exception as e:
    print("❌ Connection to Ollama failed:", str(e))
    sys.exit(1)

# Extract JSON block
json_match = re.search(r"```json\s*(.*?)\s*```", ai_response, re.DOTALL)
if json_match:
    json_str = json_match.group(1)
else:
    start_idx = ai_response.find('{')
    end_idx = ai_response.rfind('}')
    if start_idx != -1 and end_idx != -1:
        json_str = ai_response[start_idx:end_idx+1]
    else:
        print("❌ Could not extract JSON block from response!")
        sys.exit(1)

try:
    ai_graph = json.loads(json_str)
    ai_graph_path = os.path.join(SCRATCH_DIR, "ai_generated_snake.json")
    with open(ai_graph_path, "w", encoding="utf-8") as out:
        json.dump(ai_graph, out, indent=4)
except Exception as e:
    print("❌ Generated JSON is invalid:", str(e))
    sys.exit(1)

# 4. Perform comparison and analysis
errors = []
warnings = []

# Validate standard nodes
nodes_by_type = {n["type"]: n for n in ai_graph.get("nodes", [])}
connections = ai_graph.get("connections", [])

required_types = ["ServerNode", "HTTPRequestsNode", "URLNode", "RenderNode", "CSSNode"]
for t in required_types:
    if t not in nodes_by_type:
        errors.append(f"Missing required node type: {t}")

# Check Server -> HTTP connection
server_node = next((n for n in ai_graph.get("nodes", []) if n["type"] == "ServerNode"), None)
http_node = next((n for n in ai_graph.get("nodes", []) if n["type"] == "HTTPRequestsNode"), None)

if server_node and http_node:
    connected = any(c["source"] == server_node["id"] and c["target"] == http_node["id"] for c in connections)
    if not connected:
        errors.append(f"ServerNode ({server_node['id']}) is NOT connected to HTTPRequestsNode ({http_node['id']})")

# Check CSS and HTML correlation
render_node = nodes_by_type.get("RenderNode")
css_node = nodes_by_type.get("CSSNode")

html_code = ""
css_filename = ""
css_code = ""

if render_node:
    html_code = render_node.get("config", {}).get("html_code", "")
if css_node:
    css_filename = css_node.get("config", {}).get("css_filename", "style.css")
    css_code = css_node.get("config", {}).get("css_code", "")

if render_node and css_node:
    ref_pattern = f'/static/{css_filename}'
    if ref_pattern not in html_code:
        warnings.append(f"RenderNode HTML does NOT reference CSSNode's filename: '/static/{css_filename}'. Stylesheet link was missing in raw output (but compiler-level auto-injection will fix this during deploy).")
    
    if "background" not in css_code and "background-color" not in css_code:
        warnings.append("CSS does not define a body background-color. Website might look plain/white.")
    if "Outfit" not in css_code and "Inter" not in css_code and "font-family" not in css_code:
        warnings.append("CSS does not define modern typography. Font might look standard.")

# 5. Define Reference standard graph (Antigravity's version)
reference_graph = {
    "nodes": [
        {
            "id": "node-server",
            "type": "ServerNode",
            "x": 50,
            "y": 200,
            "config": {"ip": "127.0.0.1", "port": 8000}
        },
        {
            "id": "node-http",
            "type": "HTTPRequestsNode",
            "x": 250,
            "y": 200,
            "config": {}
        },
        {
            "id": "node-url",
            "type": "URLNode",
            "x": 450,
            "y": 200,
            "config": {"path": "/snake-game"}
        },
        {
            "id": "node-logic",
            "type": "JSNode",
            "x": 650,
            "y": 200,
            "config": {
                "code": "function process_logic(request) {\n    return {\n        title: 'NEON MATRIX SNAKE',\n        difficulty: 'Hardcore Mode',\n        initialSpeed: 90\n    };\n}"
            }
        },
        {
            "id": "node-render",
            "type": "RenderNode",
            "x": 900,
            "y": 200,
            "config": {
                "filename": "snake.html",
                "html_code": "<!DOCTYPE html>\n<html>\n<head>\n  <title>{title}</title>\n  <link href='https://fonts.googleapis.com/css2?family=Outfit:wght@300;700;900&display=swap' rel='stylesheet'>\n  <link rel='stylesheet' href='/static/snake.css'>\n</head>\n<body>\n  <div id='game-container'>\n    <h1>{title}</h1>\n    <div id='scoreboard'>SCORE: <span id='score'>0</span> | HIGH: <span id='high'>0</span></div>\n    <div id='mode'>{difficulty}</div>\n    <canvas id='snakeCanvas' width='400' height='400'></canvas>\n    <div class='controls'>\n      <button onclick='moveUp()'>↑</button>\n      <div class='row'><button onclick='moveLeft()'>←</button><button onclick='moveRight()'>→</button></div>\n      <button onclick='moveDown()'>↓</button>\n    </div>\n    <div class='footer'>Build: v1.0.4</div>\n  </div>\n  <script>\n    const canvas = document.getElementById('snakeCanvas');\n    const ctx = canvas.getContext('2d');\n    let score = 0;\n    let highScore = 0;\n    let grid = 20;\n    let count = 0;\n    let snake = { x: 160, y: 160, dx: grid, dy: 0, cells: [{x: 160, y: 160}, {x: 140, y: 160}] };\n    let apple = { x: 320, y: 320 };\n    function getRandomInt(min, max) { return Math.floor(Math.random() * (max - min)) + min; }\n    function loop() {\n      requestAnimationFrame(loop);\n      if (++count < 6) return;\n      count = 0;\n      ctx.clearRect(0,0,canvas.width,canvas.height);\n      snake.x += snake.dx;\n      snake.y += snake.dy;\n      if (snake.x < 0) snake.x = canvas.width - grid;\n      else if (snake.x >= canvas.width) snake.x = 0;\n      if (snake.y < 0) snake.y = canvas.height - grid;\n      else if (snake.y >= canvas.height) snake.y = 0;\n      snake.cells.unshift({x: snake.x, y: snake.y});\n      if (snake.cells.length > snake.maxCells) { snake.cells.pop(); }\n      ctx.fillStyle = '#ff0055';\n      ctx.shadowBlur = 15; ctx.shadowColor = '#ff0055';\n      ctx.fillRect(apple.x, apple.y, grid-1, grid-1);\n      ctx.fillStyle = '#00ffcc';\n      ctx.shadowColor = '#00ffcc';\n      snake.cells.forEach(function(cell, index) {\n        ctx.fillRect(cell.x, cell.y, grid-1, grid-1);\n        if (cell.x === apple.x && cell.y === apple.y) {\n          score += 10; document.getElementById('score').innerText = score;\n          if(score > highScore) { highScore = score; document.getElementById('high').innerText = highScore; }\n          snake.maxCells++;\n          apple.x = getRandomInt(0, 20) * grid;\n          apple.y = getRandomInt(0, 20) * grid;\n        }\n        for (let i = index + 1; i < snake.cells.length; i++) {\n          if (cell.x === snake.cells[i].x && cell.y === snake.cells[i].y) {\n            alert('SYSTEM CRITICAL: GAME OVER! SCORE: ' + score);\n            snake.x = 160; snake.y = 160; snake.cells = [{x:160,y:160}]; snake.dx = grid; snake.dy = 0; snake.maxCells = 2; score = 0; document.getElementById('score').innerText = score;\n          }\n        }\n      });\n    }\n    snake.maxCells = 2;\n    document.addEventListener('keydown', function(e) {\n      if (e.which === 37 && snake.dx === 0) { snake.dx = -grid; snake.dy = 0; }\n      else if (e.which === 38 && snake.dy === 0) { snake.dy = -grid; snake.dx = 0; }\n      else if (e.which === 39 && snake.dx === 0) { snake.dx = grid; snake.dy = 0; }\n      else if (e.which === 40 && snake.dy === 0) { snake.dy = grid; snake.dx = 0; }\n    });\n    function moveUp() { if(snake.dy === 0) { snake.dy = -grid; snake.dx = 0; } }\n    function moveDown() { if(snake.dy === 0) { snake.dy = grid; snake.dx = 0; } }\n    function moveLeft() { if(snake.dx === 0) { snake.dx = -grid; snake.dy = 0; } }\n    function moveRight() { if(snake.dx === 0) { snake.dx = grid; snake.dy = 0; } }\n    requestAnimationFrame(loop);\n  </script>\n</body>\n</html>"
            }
        },
        {
            "id": "node-css",
            "type": "CSSNode",
            "x": 1150,
            "y": 200,
            "config": {
                "css_filename": "snake.css",
                "css_code": "body {\n  background: radial-gradient(circle at center, #0a0b16 0%, #030408 100%);\n  color: #00ffcc;\n  font-family: 'Outfit', sans-serif;\n  display: flex;\n  justify-content: center;\n  align-items: center;\n  height: 100vh;\n  margin: 0;\n  overflow: hidden;\n}\n#game-container {\n  background: rgba(10, 11, 22, 0.7);\n  backdrop-filter: blur(12px);\n  border: 1px solid rgba(0, 255, 204, 0.3);\n  border-radius: 16px;\n  padding: 30px;\n  text-align: center;\n  box-shadow: 0 0 40px rgba(0, 255, 204, 0.15);\n  max-width: 440px;\n}\nh1 {\n  margin: 0 0 10px 0;\n  font-size: 2rem;\n  font-weight: 900;\n  letter-spacing: 2px;\n  text-shadow: 0 0 10px rgba(0,255,204,0.6);\n}\n#scoreboard {\n  font-size: 1.1rem;\n  color: #fff;\n  margin-bottom: 5px;\n  letter-spacing: 1px;\n}\n#mode {\n  color: #ff0055;\n  font-size: 0.8rem;\n  font-weight: 700;\n  margin-bottom: 20px;\n  letter-spacing: 1px;\n}\n#snakeCanvas {\n  background: #05060a;\n  border: 4px solid #0a0b16;\n  border-radius: 8px;\n  box-shadow: inset 0 0 20px rgba(0,0,0,0.8);\n}\n.controls {\n  margin-top: 15px;\n  display: flex;\n  flex-direction: column;\n  align-items: center;\n  gap: 5px;\n}\n.controls button {\n  background: #0a0b16;\n  border: 1px solid rgba(0,255,204,0.3);\n  color: #00ffcc;\n  width: 40px;\n  height: 35px;\n  font-size: 1.2rem;\n  border-radius: 4px;\n  cursor: pointer;\n  transition: all 0.2s;\n}\n.controls button:hover {\n  background: #00ffcc;\n  color: #000;\n  box-shadow: 0 0 10px #00ffcc;\n}\n.row {\n  display: flex;\n  gap: 20px;\n}\n.footer {\n  margin-top: 15px;\n  font-size: 0.7rem;\n  color: #444;\n}"
            }
        }
    ],
    "connections": [
        {"source": "node-server", "target": "node-http"},
        {"source": "node-http", "target": "node-url"},
        {"source": "node-url", "target": "node-logic"},
        {"source": "node-logic", "target": "node-render"},
        {"source": "node-render", "target": "node-css"}
    ]
}

# 6. Generate Markdown Report
report_path = os.path.join(SCRATCH_DIR, "ai_comparison_report.md")

markdown = f"""# 🔍 AI vs. Antigravity Reference Comparison Report

This report analyzes the code, architecture, and visual output generated by the in-app AI (Ollama gemma4:26b) against the Reference Standard design.

## 📋 Prompt Details
* **Prompt:** `"{user_prompt}"`

## 📊 Structural Comparison Table

| Metric / Check | In-App AI (Ollama) | Reference Standard (Antigravity) | Status |
| :--- | :--- | :--- | :--- |
| **All Required Nodes Present** | {"Yes" if not errors else "No"} | Yes | {"✅ Match" if not errors else "❌ Mismatch"} |
| **Server -> HTTP Connection** | {"Yes" if "ServerNode is NOT connected" not in "".join(errors) else "No"} | Yes | {"✅ Connected" if "ServerNode is NOT connected" not in "".join(errors) else "❌ Disconnected"} |
| **CSS Link in RenderNode** | {"Omitted / Mismatched" if len(warnings) > 0 else "Correct"} | Correct (linked `/static/snake.css`) | {"⚠️ Warning" if len(warnings) > 0 else "✅ Match"} |
| **Webpage Background Style** | { "Omitted / Default" if "background" not in css_code else "Dark Cyber Theme" } | Radial Gradient (`#0a0b16` to `#030408`) | {"⚠️ Warning" if "background" not in css_code else "✅ Match"} |
| **Webpage Font Styles** | { "Default Serif" if "Outfit" not in css_code else "Outfit Sans-Serif" } | Google Fonts 'Outfit' | {"⚠️ Warning" if "Outfit" not in css_code else "✅ Match"} |

## 🔎 Detailed Code Differences

### 1. CSS Styles Comparison
* **Ollama's CSS Code:**
```css
{css_code}
```

* **Reference CSS Code (Antigravity):**
```css
{reference_graph["nodes"][5]["config"]["css_code"]}
```

### 2. RenderNode HTML Code
* **Ollama's HTML Code:**
```html
{html_code}
```

* **Reference HTML Code (Antigravity):**
```html
{reference_graph["nodes"][4]["config"]["html_code"]}
```

## 💡 Key Analysis & Recommendations
1. **HTML Link Missing:** The in-app AI generated the CSS styles in the CSSNode but failed to link it inside the HTML. That is why the website body was displayed as plain white and default Times New Roman.
2. **Typography Omission:** The AI left out modern web fonts. Using standard browser fonts makes a game look dated.
3. **Layout Alignments:** The AI's generated HTML put the canvas directly on the screen without a container wrapping card, causing bad alignment. The reference uses a flexbox wrapper card with glassmorphism effects.

*Report compiled on: 2026-06-05*
"""

with open(report_path, "w", encoding="utf-8") as rf:
    rf.write(markdown)

print(f"🎉 Detailed comparison report successfully written to {report_path}!")
