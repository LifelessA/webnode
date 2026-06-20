"""
WebNode AI Dual-Model Pipeline
================================
Uses two specialized local models via Ollama:
  - gemma4:e4b     → Thinker (architecture, planning, design decisions)
  - qwen2.5-coder  → Coder  (writes actual Python logic, HTML, CSS)

Flow:
  1. Thinker (gemma4) analyzes user idea → plans routes, features, design
  2. Thinker (gemma4) designs each route → architecture, variables, layout
  3. Coder (qwen2.5-coder) writes code per route → logic, HTML, CSS
  4. Graph assembler builds final graph.json
"""
import sys
import requests
import json
import os
import re

# =============================================
# Ollama Configuration
# =============================================
OLLAMA_URL = "http://localhost:11434/api/generate"

# Model Roles
THINKER_MODEL = "gemma4:e4b"         # Architecture & planning
CODER_MODEL   = "qwen2.5-coder:latest"  # Code generation

# Load the framework API rules for the coder
PROMPT_DIR = os.path.dirname(__file__)
GRAPH_PROMPT_PATH = os.path.join(PROMPT_DIR, "GRAPH_PROMPT.md")

def load_graph_prompt():
    """Load GRAPH_PROMPT.md with all framework API rules."""
    try:
        with open(GRAPH_PROMPT_PATH, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        print("[!] GRAPH_PROMPT.md not found. Coder will run without framework rules.")
        return ""

FRAMEWORK_RULES = load_graph_prompt()


def call_ollama(model, prompt, print_prefix, temp=0.6, max_tokens=8192):
    """Call local Ollama model with streaming output."""
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": temp,
            "num_predict": max_tokens,
        }
    }
    
    print(print_prefix)
    full_response = ""
    
    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=600)
        response.raise_for_status()
        
        for line in response.iter_lines():
            if line:
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    token = chunk.get("response", "")
                    if token:
                        full_response += token
                        sys.stdout.write(token)
                        sys.stdout.flush()
                    if chunk.get("done", False):
                        break
                except json.JSONDecodeError:
                    pass
        
        print("\n")
        return full_response
        
    except requests.ConnectionError:
        print(f"\n[!] Cannot connect to Ollama at {OLLAMA_URL}")
        print("    Make sure 'ollama serve' is running!")
        return ""
    except Exception as e:
        print(f"\n[!] Ollama Error: {e}")
        return ""


def extract_json_from_text(text):
    """Extract the first JSON object/array from LLM output."""
    if not text:
        return None
    # Try ```json ... ``` blocks first
    match = re.search(r"```(?:json)?\s*([\{\[].*?[\}\]])\s*```", text, re.DOTALL)
    if match:
        raw = match.group(1)
    else:
        # Try finding raw { ... }
        s, e = text.find('{'), text.rfind('}')
        if s != -1 and e > s:
            raw = text[s:e+1]
        else:
            s, e = text.find('['), text.rfind(']')
            if s != -1 and e > s:
                raw = text[s:e+1]
            else:
                raw = text
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # Try fixing common issues
        try:
            # Remove trailing commas
            cleaned = re.sub(r',\s*([}\]])', r'\1', raw)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            print("[!] Failed to parse JSON from model output")
            return None


# =============================================
# PHASE 1: THINKER — Architecture & Planning
# =============================================

def thinker_research(idea):
    """Gemma4 analyzes the idea and plans all routes/features."""
    prompt = f"""You are a senior web architect planning a website. The user wants: "{idea}"

Analyze this and plan ALL the pages/routes needed for a complete, functional website.
Think about: what pages are needed, what data each page shows, what forms it has.

IMPORTANT: This is a PURE PYTHON backend framework with NO database and NO ORM.
All data must be hardcoded as Python dicts/lists. No imports like SQLAlchemy, bcrypt, etc.

Output ONLY a JSON object:
{{
  "project_name": "Name of the project",
  "description": "Short description of the full website",
  "design_system": "Describe the visual design: colors, fonts, style (e.g., dark mode glassmorphism, light modern, etc.)",
  "routes": [
    {{
      "path": "/",
      "name": "home",
      "purpose": "What this page shows and does",
      "has_form": false,
      "data_needed": "What hardcoded data this page needs (rooms list, products, etc.)"
    }}
  ]
}}
Output ONLY valid JSON, nothing else."""
    
    raw = call_ollama(THINKER_MODEL, prompt, "\n[🧠 Thinker] Analyzing requirements...", temp=0.7, max_tokens=4096)
    return extract_json_from_text(raw)


def thinker_design(route_info, project_description, design_system):
    """Gemma4 designs the architecture for a single route."""
    prompt = f"""You are a web architect designing ONE page for this project: "{project_description}"
Design system: {design_system}

Design this specific page:
- Path: {route_info['path']}
- Name: {route_info['name']}  
- Purpose: {route_info['purpose']}
- Has form: {route_info.get('has_form', False)}
- Data needed: {route_info.get('data_needed', 'None')}

CRITICAL RULES:
- No database, no ORM, no external imports (only Python stdlib: re, json, datetime)
- All data must be hardcoded Python dicts/lists
- Forms need csrf_token hidden field
- Logic function must return dict with 'csrf_token' key

Output ONLY a JSON object:
{{
  "route": "{route_info['path']}",
  "page_name": "{route_info['name']}",
  "template_variables": ["list of variables the template will use, e.g. 'rooms', 'csrf_token'"],
  "hardcoded_data": "Describe exact sample data structure (e.g., list of 4 room dicts with id, name, price, rating)",
  "form_fields": ["list of form field names if has_form, else empty"],
  "html_sections": ["navbar", "hero", "card-grid", "form", "footer"],
  "css_classes_needed": ["list of CSS class names this page needs"]
}}
Output ONLY valid JSON, nothing else."""
    
    raw = call_ollama(THINKER_MODEL, prompt, f"\n[📐 Thinker] Designing route '{route_info['path']}'...", temp=0.6, max_tokens=4096)
    return extract_json_from_text(raw)


# =============================================
# PHASE 2: CODER — Code Generation
# =============================================

def coder_build(arch_plan, route_info, design_system):
    """Qwen2.5-Coder writes the actual code based on architect's plan."""
    prompt = f"""{FRAMEWORK_RULES}

---

Now build the code for this route based on the architect's design:

ARCHITECT'S PLAN:
{json.dumps(arch_plan, indent=2)}

ROUTE INFO:
- Path: {route_info['path']}
- Page Name: {route_info['name']}
- Purpose: {route_info.get('purpose', '')}
- Design: {design_system}

YOUR TASK: Generate ONLY a JSON object with three keys:

{{
  "logic_code": "def {route_info['name']}_logic(req):\\n    ...\\n    return {{'csrf_token': req.context.get('csrf_token', '')}}",
  "html_code": "<!DOCTYPE html>\\n<html>...full HTML page...</html>",
  "css_code": "/* page-specific CSS */"
}}

MANDATORY RULES:
1. logic_code: Pure Python function, NO imports except re/json/datetime. Use hardcoded data. Use req.get_param() for forms. MUST return dict with csrf_token.
2. html_code: Full valid HTML with <link rel="stylesheet" href="/static/style.css">. Forms MUST have <input type="hidden" name="csrf_token" value="{{{{ csrf_token }}}}">
3. css_code: Modern, premium CSS with animations. Use the design system described above.
4. Do NOT use any ORM, database, bcrypt, or external library calls.
5. For request data: req.get_param('field', ''), req.query_params, req.method, req.context

Output ONLY the JSON object. No explanations."""
    
    raw = call_ollama(CODER_MODEL, prompt, f"\n[💻 Coder] Writing code for '{route_info['path']}'...", temp=0.4, max_tokens=16384)
    return extract_json_from_text(raw)


# =============================================
# GRAPH ASSEMBLER
# =============================================

def init_graph():
    """Create base graph with server, HTTP, and CSRF nodes."""
    return {
        "nodes": [
            {"id": "server_1", "type": "ServerNode", "x": -112, "y": 293,
             "config": {"ip": "127.0.0.1", "port": 8000}},
            {"id": "http_1", "type": "HTTPRequestsNode", "x": -111, "y": 557,
             "config": {}},
            {"id": "csrf_1", "type": "CSRFNode", "x": -106, "y": 669,
             "config": {}},
            {"id": "css_main", "type": "CSSNode", "x": 2454, "y": 550,
             "config": {"css_filename": "style.css", "css_code": ""}}
        ],
        "connections": [
            {"source": "server_1", "target": "http_1"},
            {"source": "http_1", "target": "csrf_1"}
        ]
    }


def append_route_to_graph(graph, route_info, build_data, index):
    """Add a route's nodes (URL, Logic, Render) to the graph."""
    pid = route_info['name']
    path = route_info['path']
    
    # Spread nodes vertically for visual clarity
    y_base = -900 + (index * 400)
    
    url_id    = f"url_{pid}"
    logic_id  = f"logic_{pid}"
    render_id = f"render_{pid}"
    
    # URL Router Node
    graph["nodes"].append({
        "id": url_id, "type": "URLNode",
        "x": 470, "y": y_base,
        "config": {"path": path}
    })
    
    # Logic Node
    logic_code = build_data.get("logic_code", f"def {pid}_logic(req):\n    return {{'csrf_token': req.context.get('csrf_token', '')}}")
    graph["nodes"].append({
        "id": logic_id, "type": "LogicNode",
        "x": 1000, "y": y_base - 150,
        "config": {"code": logic_code}
    })
    
    # Render Template Node
    html_code = build_data.get("html_code", f"<!DOCTYPE html><html><body><h1>{pid}</h1></body></html>")
    graph["nodes"].append({
        "id": render_id, "type": "RenderNode",
        "x": 1660, "y": y_base,
        "config": {"filename": f"{pid}.html", "html_code": html_code}
    })
    
    # Append CSS to global CSS node
    css_node = next(n for n in graph["nodes"] if n["id"] == "css_main")
    new_css = build_data.get("css_code", "")
    if new_css:
        css_node["config"]["css_code"] += f"\n/* CSS for {pid} */\n{new_css}\n"
    
    # Wire connections
    graph["connections"].extend([
        {"source": "csrf_1", "target": url_id},
        {"source": url_id, "target": logic_id},
        {"source": logic_id, "target": render_id},
        {"source": render_id, "target": "css_main"}
    ])
    
    return graph


# =============================================
# MAIN PIPELINE
# =============================================

def main():
    if len(sys.argv) < 2:
        print("Usage: python core/ai/agent.py \"Your website idea here\"")
        sys.exit(1)
    
    idea = sys.argv[1]
    
    print("=" * 60)
    print("🚀 WebNode AI Agent v5.0 — Dual-Model Pipeline")
    print(f"   🧠 Thinker: {THINKER_MODEL}")
    print(f"   💻 Coder:   {CODER_MODEL}")
    print("=" * 60)
    
    # ── Phase 1: Thinker researches the idea ──
    research = thinker_research(idea)
    if not research or 'routes' not in research:
        print("[!] Thinker failed to produce a valid plan. Exiting.")
        sys.exit(1)
    
    project_name = research.get('project_name', 'Untitled')
    design_system = research.get('design_system', 'Modern dark theme with gradients')
    
    print(f"\n{'─' * 40}")
    print(f"📋 Project: {project_name}")
    print(f"🎨 Design:  {design_system}")
    print(f"📄 Routes:  {len(research['routes'])}")
    for r in research['routes']:
        print(f"   • {r['path']:20s} → {r['name']}")
    print(f"{'─' * 40}")
    
    graph = init_graph()
    success_count = 0
    
    # ── Phase 2 & 3: Process each route ──
    for i, route in enumerate(research['routes']):
        print(f"\n{'═' * 50}")
        print(f"  Route {i+1}/{len(research['routes'])}: {route['path']} ({route['name']})")
        print(f"{'═' * 50}")
        
        # Phase 2: Thinker designs the architecture
        arch_plan = thinker_design(route, research.get('description', idea), design_system)
        if not arch_plan:
            print(f"  [!] Thinker failed to design {route['path']}. Using fallback.")
            arch_plan = {
                "route": route['path'],
                "page_name": route['name'],
                "template_variables": ["csrf_token"],
                "hardcoded_data": "None",
                "form_fields": [],
                "html_sections": ["header", "main", "footer"],
                "css_classes_needed": ["container"]
            }
        
        # Phase 3: Coder writes the code
        build_data = coder_build(arch_plan, route, design_system)
        if not build_data:
            print(f"  [!] Coder failed for {route['path']}. Skipping.")
            continue
        
        # Append to graph
        graph = append_route_to_graph(graph, route, build_data, i)
        success_count += 1
        print(f"  [✓] Route '{route['path']}' added to graph")
    
    if success_count == 0:
        print("\n[!] No routes were successfully built. Exiting.")
        sys.exit(1)
    
    # ── Save graph.json ──
    framework_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    output_path = os.path.join(framework_dir, "node_editor", "graph.json")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(graph, f, indent=4)
    
    print(f"\n{'═' * 60}")
    print(f"🎉 Done! Built {success_count}/{len(research['routes'])} routes")
    print(f"📁 graph.json saved to: {output_path}")
    print(f"\n👉 Next steps:")
    print(f"   1. Go to Node Editor → http://localhost:8080")
    print(f"   2. Click 'Deploy & Run'")
    print(f"   3. Open website → http://localhost:8000")
    print(f"{'═' * 60}")


if __name__ == "__main__":
    main()
