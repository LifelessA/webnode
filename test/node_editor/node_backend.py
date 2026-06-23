import http.server
import json
import os
import subprocess
import sys
import socket
import webbrowser
import threading

sys.path.insert(
    0, 
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

def _disable_quick_edit():
    """Disables Windows Console/Terminal QuickEdit mode on startup to prevent clicked window freezing."""
    if sys.platform == 'win32':
        try:
            import ctypes
            # Get handle to stdin
            h = ctypes.windll.kernel32.GetStdHandle(-10) # STD_INPUT_HANDLE = -10
            if h and h != -1:
                mode = ctypes.c_uint()
                if ctypes.windll.kernel32.GetConsoleMode(h, ctypes.byref(mode)):
                    # Disable ENABLE_QUICK_EDIT_MODE (0x0040) and enable ENABLE_EXTENDED_FLAGS (0x0080)
                    ctypes.windll.kernel32.SetConsoleMode(h, (mode.value & ~0x0040) | 0x0080)
                    print("⚡ QuickEdit mode disabled to prevent Windows Terminal click freezes.")
        except Exception:
            pass

_disable_quick_edit()

def _check_production_lock():
    try:
        import settings
        if settings.is_production():
            print(
                "\n" + "="*55 +
                "\n  🔒 NODE EDITOR LOCKED" +
                "\n  ENV=production detected." +
                "\n  Node Editor cannot run in production mode." +
                "\n  Risk: Remote Code Execution" +
                "\n  Set ENV=development to enable editor." +
                "\n" + "="*55 + "\n"
            )
            sys.exit(1)
    except ImportError:
        pass  # settings not found — allow

_check_production_lock()

PORT = 8080  # Node Editor port
EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK_DIR = os.path.dirname(EDITOR_DIR)

import mimetypes
mimetypes.init()
mimetypes.add_type('application/javascript', '.js')
mimetypes.add_type('text/css', '.css')
mimetypes.add_type('text/html', '.html')

active_process = None

def _extract_function_name(code: str) -> str:
    """Extracts the first top-level function name from Python code robustly."""
    # Method 1: AST parsing (most reliable)
    import ast
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                return node.name
    except SyntaxError:
        pass
    
    # Method 2: Regex fallback
    import re
    match = re.search(
        r'^def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
        code,
        re.MULTILINE
    )
    if match:
        return match.group(1)
    
    # Method 3: Raise clear error
    raise ValueError(
        f"No valid function definition found "
        f"in LogicNode/ContextNode code.\n"
        f"Code preview: {code[:100]}"
    )

def is_port_free(port, host='127.0.0.1'):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((host, port))
            return True
        except OSError:
            return False

def wait_for_server(port, timeout=10, host='127.0.0.1'):
    import time
    start = time.time()
    while time.time() - start < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            time.sleep(0.3)
    return False

import urllib.request

FRAMEWORK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_rag_content(node_type):
    content = ""
    ui_rag_path = os.path.join(FRAMEWORK_DIR, 'core', 'ai', 'UI_SKILL_RAG.md')
    # UI_SKILL_RAG and skills only for visual nodes (RenderNode, TemplateNode, CSSNode, ClientJSNode)
    if node_type in ('RenderNode', 'TemplateNode', 'CSSNode', 'ClientJSNode'):
        if os.path.exists(ui_rag_path):
            try:
                with open(ui_rag_path, 'r', encoding='utf-8') as f:
                    content += f.read() + "\n\n"
            except Exception:
                pass
        
        # Load all additional skills from core/ai/skill/
        skill_dir = os.path.join(FRAMEWORK_DIR, 'core', 'ai', 'skill')
        if os.path.exists(skill_dir):
            for filename in sorted(os.listdir(skill_dir)):
                if filename.endswith('.md') and filename != 'UI_SKILL_RAG.md':
                    skill_path = os.path.join(skill_dir, filename)
                    try:
                        with open(skill_path, 'r', encoding='utf-8') as f:
                            content += f"\n--- SKILL MODULE: {filename} ---\n" + f.read() + "\n\n"
                    except Exception as e:
                        print(f"Failed to load skill {filename}: {e}")
    return content

class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=EDITOR_DIR, **kwargs)

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        if self.path == '/api/status':
            self.handle_status()
        elif self.path == '/api/load':
            self.handle_load()
        elif self.path == '/api/errors':
            self.handle_errors()
        elif self.path == '/api/settings/load':
            self.handle_settings_load()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            self.handle_save()
        elif self.path == '/api/deploy':
            self.handle_deploy()
        elif self.path == '/api/stop':
            self.handle_stop()
        elif self.path == '/api/settings/save':
            self.handle_settings_save()
        elif self.path == '/api/ai/generate':
            self.handle_ai_generate()
        elif self.path == '/api/node_file_save':
            self.handle_node_file_save()
        elif self.path == '/api/db/reset':
            self.handle_db_reset()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_status(self):
        global active_process
        is_live = False
        if active_process and active_process.poll() is None:
            is_live = True
        
        # Calculate graph hash
        graph_hash = ""
        graph_path = os.path.join(EDITOR_DIR, 'graph.json')
        if os.path.exists(graph_path):
            import hashlib
            try:
                with open(graph_path, 'rb') as f:
                    graph_hash = hashlib.md5(f.read()).hexdigest()
            except Exception:
                pass
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({
            'status': 'live' if is_live else 'offline',
            'graph_hash': graph_hash
        }).encode())

    def handle_load(self):
        graph_path = os.path.join(EDITOR_DIR, 'graph.json')
        if os.path.exists(graph_path):
            with open(graph_path, 'r') as f:
                graph_data = json.load(f)
        else:
            graph_data = {"nodes": [], "connections": []}
            
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(graph_data).encode())

    def handle_errors(self):
        """Serve live error state — which node types are currently erroring."""
        state_file = os.path.join(FRAMEWORK_DIR, 'core', 'logs', 'error_state.json')
        if os.path.exists(state_file):
            with open(state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
        else:
            state = {}
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(state).encode())

    def handle_save(self):
        try:
            import settings
            if settings.is_production():
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': 'Node Editor is locked in production mode. Set ENV=development to enable.'
                }).encode())
                return
        except ImportError:
            pass

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        # Auto-extract and save seed
        seeds = []
        for node in graph_data.get('nodes', []):
            if 'seed' in node.get('config', {}):
                seeds.append(node['config']['seed'])
        
        if seeds:
            seed_dump_path = os.path.join(FRAMEWORK_DIR, 'core', 'ai', 'seed_dump.json')
            os.makedirs(os.path.dirname(seed_dump_path), exist_ok=True)
            try:
                # Append to a list in seed_dump.json
                existing_seeds = []
                if os.path.exists(seed_dump_path):
                    with open(seed_dump_path, 'r', encoding='utf-8') as sf:
                        try:
                            existing_seeds = json.load(sf)
                            if not isinstance(existing_seeds, list):
                                existing_seeds = []
                        except json.JSONDecodeError:
                            pass
                existing_seeds.extend(seeds)
                with open(seed_dump_path, 'w', encoding='utf-8') as sf:
                    json.dump(existing_seeds, sf, indent=4)
                print(f"[AI Editor] Auto-saved {len(seeds)} seed(s) to core/ai/seed_dump.json")
            except Exception as e:
                print(f"[AI Editor] Failed to save seed: {e}")
        
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

    def handle_stop(self):
        try:
            import settings
            if settings.is_production():
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': 'Node Editor is locked in production mode. Set ENV=development to enable.'
                }).encode())
                return
        except ImportError:
            pass

        global active_process
        if active_process:
            active_process.terminate()
            try:
                active_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                active_process.kill()
                try:
                    active_process.wait(timeout=3)
                except Exception:
                    pass
            active_process = None
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'stopped'}).encode())

    def handle_settings_load(self):
        try:
            from ai_editor.ai_backend import load_ai_settings
            config = load_ai_settings()
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(config).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def handle_settings_save(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            settings_data = json.loads(post_data.decode('utf-8'))
            from ai_editor.ai_backend import save_ai_settings
            save_ai_settings(settings_data)
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())

    def handle_db_reset(self):
        try:
            import sys
            sys.path.append(FRAMEWORK_DIR)
            from database import reset_db
            success = reset_db()
            self.send_response(200 if success else 500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'success' if success else 'error'}).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())

    def handle_node_file_save(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            
            filename = payload.get('filename', '').strip()
            content = payload.get('content', '')
            node_type = payload.get('node_type', '')
            
            if not filename:
                raise ValueError("Filename is required")
                
            # Prevent path traversal
            if '..' in filename or '/' in filename or '\\' in filename:
                raise ValueError("Invalid filename: must not contain paths")
                
            # Determine target directory
            if node_type == 'RenderNode' or node_type == 'TemplateNode':
                target_dir = os.path.join(FRAMEWORK_DIR, 'templates')
            else:
                target_dir = os.path.join(FRAMEWORK_DIR, 'static')
                
            os.makedirs(target_dir, exist_ok=True)
            target_path = os.path.join(target_dir, filename)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'status': 'success', 
                'path': os.path.relpath(target_path, FRAMEWORK_DIR).replace('\\', '/')
            }).encode())
            
        except Exception as e:
            self.send_response(400)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'status': 'error', 'message': str(e)}).encode())


    def handle_ai_generate(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            payload = json.loads(post_data.decode('utf-8'))
            prompt = payload.get('prompt', '')
            code = payload.get('code', '')
            node_type = payload.get('node_type', '')

            from ai_editor.ai_backend import load_ai_settings, get_provider_request_details
            import urllib.request
            ai_config = load_ai_settings()
            provider = ai_config.get("SELECTED_AI_PROVIDER", "ollama").lower()
            
            api_key = ""
            if provider == "gemini": api_key = ai_config.get("GEMINI_API_KEY")
            elif provider == "gpt": api_key = ai_config.get("OPENAI_API_KEY")
            elif provider == "claude": api_key = ai_config.get("CLAUDE_API_KEY")
            elif provider == "deepseek": api_key = ai_config.get("DEEPSEEK_API_KEY")
            elif provider == "openrouter": api_key = ai_config.get("OPENROUTER_API_KEY")
            elif provider == "nvidia": api_key = ai_config.get("NVIDIA_API_KEY")
            elif provider == "glm": api_key = ai_config.get("GLM_API_KEY")
            elif provider == "dough": api_key = ai_config.get("DOUGH_API_KEY")
            elif provider == "custom": api_key = ai_config.get("CUSTOM_API_KEY")
            
            if provider != "ollama" and not api_key:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(f"API Key for '{provider}' is missing.".encode('utf-8'))
                return

            if node_type == 'Test':
                system_prompt = "You are a helpful AI assistant. The user is testing the API connection. Respond directly and concisely to the prompt."
                user_prompt = prompt
            else:
                rag_content = load_rag_content(node_type=node_type)
                system_prompt = f"You are an AI generating code for a {node_type} node in a visual Node Editor Framework.\n"
                if rag_content.strip():
                    system_prompt += f"\n### UI SKILL RAG CONTEXT:\n{rag_content}\n\n"
                
                if node_type == 'LogicNode' or node_type == 'ContextNode':
                    system_prompt += f"In `node_backend.py`, you are the {node_type} (Backend Python logic). You MUST return a dictionary to update `request.context`.\n"
                    system_prompt += "If the user prompt contains a SEED instruction from the RenderNode, use that context to write the required backend python logic for the HTML frontend.\n"
                    system_prompt += "CRITICAL: The function MUST be defined as `def process_logic(request):` taking EXACTLY one argument. Do not add a 'context' argument. Access context via `request.context` if needed.\n"
                    system_prompt += "IMPORTANT: NEVER import `from app import db` or use SQLAlchemy.\n"
                    system_prompt += "For database operations, ALWAYS import `from database import query_db, execute_db`.\n"
                    system_prompt += "Example Select: `users = query_db('SELECT * FROM users')`\n"
                    system_prompt += "Example Insert: `execute_db('INSERT INTO users (name) VALUES (?)', (name,))`\n"
                    system_prompt += "CRITICAL OUTPUT FORMAT: Output ONLY raw Python code starting with import statements or function definitions. Do NOT output JSON objects with keys like 'node_type', 'code', 'nodes', 'connections'. Do NOT wrap code in JSON. Just output the raw Python function code directly.\n"
                elif node_type == 'JSNode':
                    system_prompt += "In `node_backend.py`, you are the JSNode (Backend Node.js server logic). It MUST define `function process_logic(request) { ... }` returning an object.\n"
                    system_prompt += "If the user prompt contains a SEED instruction from the RenderNode, use that context to write the required backend Node.js logic.\n"
                    system_prompt += "CRITICAL: This runs in Node.js on the server! DO NOT write HTML, CSS, or browser DOM code (no `document`, `window`, etc.). If the user asks for a game/UI, return the initial state object.\n"
                    system_prompt += "CRITICAL OUTPUT FORMAT: Output ONLY raw JavaScript code. Do NOT output JSON objects with keys like 'node_type', 'code', 'nodes', 'connections'. Just output the raw JS function code directly.\n"
                elif node_type == 'ClientJSNode':
                    system_prompt += "In `node_backend.py`, you are the ClientJSNode. You write frontend client-side JavaScript that runs in the browser.\n"
                    system_prompt += "The user prompt will contain a SEED generated by the RenderNode describing the HTML structure.\n"
                    system_prompt += "Use this HTML context from the SEED to write the perfect frontend JavaScript (DOM manipulation, game loops, event listeners). DO NOT output HTML or CSS.\n"
                elif node_type == 'CSSNode':
                    system_prompt += "In `node_backend.py`, you are the CSSNode. Output pure CSS rules. The user prompt will contain a SEED generated by the RenderNode describing the HTML structure and classes.\n"
                    system_prompt += "Use this HTML context from the SEED to write the perfect CSS. Apply the UI_SKILL_RAG rules for modern aesthetics, gradients, glassmorphism, and hover sweeps.\n"
                elif node_type == 'RenderNode' or node_type == 'TemplateNode':
                    system_prompt += "In `node_backend.py`, you are the RenderNode (Template Node). You write the HTML frontend.\n"
                    system_prompt += "CRITICAL TEMPLATE SYNTAX: Use `{{ var }}` for variables (NOT {var}). Use `{% for x in list %}` and `{% endfor %}` for loops (NOT {# for #}). Use `{% if cond %}` and `{% endif %}` for conditions.\n"
                    system_prompt += "CRITICAL SEED INSTRUCTION: You are the MASTER node that generates the SEED context for the CSS, JS, and Python nodes. You MUST output exactly TWO sections separated by '---SEED_SEPARATOR---'.\n"
                    system_prompt += "Section 1: The raw HTML code ONLY. DO NOT write any `<style>` tags or `<script>` tags for application logic in the HTML. You MUST leave styling and logic to the CSS and JS nodes.\n"
                    system_prompt += "Section 2: A raw JSON dictionary with exactly 4 keys: 'css', 'js', 'py', 'path'. For 'css', give detailed styling instructions. For 'js', give detailed instructions to generate the frontend client-side JavaScript logic (DOM, events, game loop). For 'py', give instructions for any required Python backend logic. The user will use this seed in the CSS, ClientJS, and Python nodes.\n"
                    system_prompt += "CRITICAL: You are NOT the graph architect. Do NOT output JSON with 'nodes', 'connections', 'ServerNode', 'URLNode' etc. You output ONLY raw HTML code followed by ---SEED_SEPARATOR--- and then a seed JSON with keys 'css','js','py','path'. Nothing else.\n"
                
                system_prompt += "\nCRITICAL RULES:\n1. NEVER TRUNCATE CODE! If the user wants to fix or modify the code, you MUST output the ENTIRE updated code from start to finish. Do NOT skip lines, and do NOT use placeholders like `/* rest of code */` or `...`.\n2. Do NOT just output the changed lines or partial snippets.\n3. OUTPUT ONLY THE RAW TEXT/CODE REQUESTED. DO NOT WRAP IT IN MARKDOWN BACKTICKS (```) AND DO NOT INCLUDE ANY EXPLANATIONS."
                user_prompt = f"Current Code:\n{code}\n\nUser Request: {prompt}"
            
            url, headers, req_data = get_provider_request_details(
                provider=provider,
                ai_config=ai_config,
                api_key=api_key,
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                stream=True,
                chat_history=[]
            )

            self.send_response(200)
            self.send_header('Content-Type', 'text/plain; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()

            req = urllib.request.Request(url, data=json.dumps(req_data).encode('utf-8'), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=300) as res:
                buffer_t = b""
                while True:
                    chunk = res.read(1024)
                    if not chunk:
                        break
                    buffer_t += chunk
                    while b"\n" in buffer_t:
                        line_bytes_t, buffer_t = buffer_t.split(b"\n", 1)
                        line_str_t = line_bytes_t.decode('utf-8').strip()
                        if not line_str_t:
                            continue
                        
                        text_chunk = ""
                        if provider == "ollama":
                            try:
                                data_json_t = json.loads(line_str_t)
                                text_chunk = data_json_t.get('response', '')
                            except Exception: pass
                        else:
                            if line_str_t.startswith("data:"):
                                data_str_t = line_str_t[len("data:"):].strip()
                                if data_str_t == "[DONE]":
                                    break
                                try:
                                    data_json_t = json.loads(data_str_t)
                                    choices = data_json_t.get('choices', [])
                                    if choices:
                                        delta = choices[0].get('delta', {})
                                        text_chunk = delta.get('content', '')
                                except Exception: pass
                        
                        if text_chunk:
                            self.wfile.write(text_chunk.encode('utf-8'))
                            self.wfile.flush()

        except Exception as e:
            self.wfile.write(f"\\n[ERROR] {str(e)}".encode('utf-8'))

    def handle_deploy(self):
        try:
            import settings
            if settings.is_production():
                self.send_response(403)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'status': 'error',
                    'message': 'Node Editor is locked in production mode. Set ENV=development to enable.'
                }).encode())
                return
        except ImportError:
            pass

        global active_process
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        # 1. Clear previous error state
        try:
            from core.errors import NodeErrorReporter
            NodeErrorReporter.clear_errors()
        except Exception:
            pass

        # 2. Save JSON
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
            
        # 3. Compile JSON to main.py
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
            try:
                active_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                active_process.kill()
                active_process.wait(timeout=3)
            active_process = None
            
        # 3.5 Get configured port
        port = 8000
        for n in graph_data.get('nodes', []):
            if n['type'] == 'ServerNode':
                port = int(n.get('config', {}).get('port', 8000))
                break

        # 3.6 Forcefully kill any stray background processes holding the port
        try:
            kill_cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }}"
            subprocess.run(["powershell", "-Command", kill_cmd], capture_output=True, timeout=10)
        except Exception:
            pass
        
        # 3.7 Wait for port to be free (up to 5 seconds)
        import time
        port_free = False
        for _ in range(50):  # max 5 seconds
            if is_port_free(port):
                port_free = True
                break
            time.sleep(0.1)
        
        if not port_free:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'error',
                    'message': f'Port {port} is still in use. Please wait a moment and try deploying again.'
                }).encode()
            )
            return

        main_py_path = os.path.join(FRAMEWORK_DIR, 'main.py')
        # Capture stderr so we can show actual errors on failure
        active_process = subprocess.Popen(
            [sys.executable, main_py_path],
            cwd=FRAMEWORK_DIR,
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        
        # Verify server actually started
        if not wait_for_server(port, timeout=10):
            # Server failed to start — try to get the error output
            error_msg = ''
            try:
                # Give it a moment to flush stderr
                active_process.wait(timeout=2)
                stderr_out = active_process.stderr.read().decode('utf-8', errors='replace')
                if stderr_out.strip():
                    error_msg = stderr_out.strip()[-500:]  # last 500 chars
            except Exception:
                pass
            
            if not error_msg:
                error_msg = f'Server failed to start on port {port}. Check main.py for errors.'
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'error',
                    'message': error_msg
                }).encode()
            )
            return

        # Only NOW return success
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

    def compile_graph(self, graph_data):
        nodes = {n['id']: n for n in graph_data['nodes']}
        connections = graph_data['connections']
        
        # 0. Clean old generated files (static CSS + templates)
        #    This prevents disconnected CSSNodes from leaving stale files
        import glob
        static_dir = os.path.join(FRAMEWORK_DIR, 'static')
        if os.path.exists(static_dir):
            for css_file in glob.glob(os.path.join(static_dir, '*.css')):
                try:
                    os.remove(css_file)
                except OSError:
                    pass
        
        templates_dir = os.path.join(FRAMEWORK_DIR, 'templates')
        if os.path.exists(templates_dir):
            for html_file in glob.glob(os.path.join(templates_dir, '*.html')):
                try:
                    os.remove(html_file)
                except OSError:
                    pass

        js_code_dir = os.path.join(FRAMEWORK_DIR, 'nodes', 'js_code')
        if os.path.exists(js_code_dir):
            for js_file in glob.glob(os.path.join(js_code_dir, '*.js')):
                try:
                    os.remove(js_file)
                except OSError:
                    pass
        
        # Find starting node (ServerNode)
        server_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'ServerNode'), None)
        if not server_node_id:
            raise ValueError("No Server Node found in graph!")

        # Find mapping of source -> list of targets
        outgoing_map = {}
        for c in connections:
            source_id = c.get('source') or c.get('from')
            target_id = c.get('target') or c.get('to')
            if source_id and target_id:
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
        if 'JSNode' in types_used: imports.append("from nodes.js_node import JSNode")
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
        if 'CSSNode' in types_used: imports.append("from nodes.css_node import CSSNode")
        if 'ClientJSNode' in types_used: imports.append("from nodes.client_js_node import ClientJSNode")
        
        imports.append("from nodes.response import Response")
        imports.append("import json")
        imports.append("import urllib.parse")

        code_lines = [
            "# AUTO-GENERATED BY NODE EDITOR COMPILER",
            "\n".join(imports),
            "\n# Prevent click freezing in Windows terminals",
            "def _disable_quick_edit():",
            "    import sys",
            "    if sys.platform == 'win32':",
            "        try:",
            "            import ctypes",
            "            h = ctypes.windll.kernel32.GetStdHandle(-10)",
            "            if h and h != -1:",
            "                m = ctypes.c_uint()",
            "                if ctypes.windll.kernel32.GetConsoleMode(h, ctypes.byref(m)):",
            "                    ctypes.windll.kernel32.SetConsoleMode(h, (m.value & ~0x0040) | 0x0080)",
            "        except Exception: pass",
            "_disable_quick_edit()",
            "\n# Initialize Database if needed"
        ]
        
        if 'ModelNode' in types_used:
            code_lines.append("db = Database()")
            
        code_lines.append("\n# Nodes Instantiation")
        
        # Build a set of RenderNode IDs that are connected to a CSSNode
        # This ensures CSS only applies to templates explicitly wired to CSSNode
        render_ids_with_css = set()
        for nid in reachable_ids:
            if nodes[nid]['type'] == 'RenderNode':
                # Check if this RenderNode has a CSSNode as its target
                for tgt_id in outgoing_map.get(nid, []):
                    if tgt_id in nodes and nodes[tgt_id]['type'] == 'CSSNode':
                        render_ids_with_css.add(nid)
        
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
                html_code = config.get('html_code', '<h1>Hello World!</h1>')
                custom_filename = config.get('filename', '').strip()
                auto_filename = custom_filename if custom_filename else f"auto_template_{nid}.html"
                
                # If this RenderNode is NOT connected to a CSSNode,
                # strip the <link rel="stylesheet"> tag so CSS doesn't apply
                if nid not in render_ids_with_css:
                    import re as _re
                    html_code = _re.sub(
                        r'<link[^>]*rel=["\']stylesheet["\'][^>]*/?>',
                        '<!-- CSS not connected -->',
                        html_code
                    )
                else:
                    # Automatically inject stylesheet link
                    css_node_id = next((tgt_id for tgt_id in outgoing_map.get(nid, []) if nodes[tgt_id]['type'] == 'CSSNode'), None)
                    if css_node_id:
                        css_config = nodes[css_node_id].get('config', {})
                        css_filename = css_config.get('css_filename', '').strip()
                        if not css_filename:
                            css_filename = f"style_{css_node_id}.css"
                        if not css_filename.endswith('.css'):
                            css_filename += '.css'
                        
                        # Strip ALL hallucinated link tags and inject the correct one
                        import re as _re
                        html_code = _re.sub(
                            r'<link[^>]*rel=["\']stylesheet["\'][^>]*/?>',
                            '',
                            html_code
                        )
                        
                        ref_pattern = f"/static/{css_filename}"
                        link_tag = f'<link rel="stylesheet" href="{ref_pattern}">'
                        if "</head>" in html_code:
                            html_code = html_code.replace("</head>", f"    {link_tag}\n</head>")
                        elif "<body>" in html_code:
                            html_code = html_code.replace("<body>", f"    {link_tag}\n<body>")
                        else:
                            html_code = link_tag + "\n" + html_code

                    # Automatically inject client JS script
                    clientjs_node_id = next((tgt_id for tgt_id in outgoing_map.get(nid, []) if nodes[tgt_id]['type'] == 'ClientJSNode'), None)
                    if clientjs_node_id:
                        cjs_config = nodes[clientjs_node_id].get('config', {})
                        cjs_filename = cjs_config.get('filename', '').strip()
                        if not cjs_filename:
                            cjs_filename = f"script_{clientjs_node_id}.js"
                        if not cjs_filename.endswith('.js'):
                            cjs_filename += '.js'
                        
                        # Strip hallucinated script tags linking to this file
                        import re as _re
                        html_code = _re.sub(
                            r'<script[^>]*src=["\'][^>]*' + _re.escape(cjs_filename) + r'["\'][^>]*></script>',
                            '',
                            html_code
                        )
                        
                        script_tag = f'<script src="/static/{cjs_filename}"></script>'
                        if "</body>" in html_code:
                            html_code = html_code.replace("</body>", f"    {script_tag}\n</body>")
                        else:
                            html_code += "\n" + script_tag
                
                os.makedirs(os.path.join(FRAMEWORK_DIR, 'templates'), exist_ok=True)
                auto_filepath = os.path.join(FRAMEWORK_DIR, 'templates', auto_filename)
                
                with open(auto_filepath, 'w', encoding='utf-8') as tf:
                    tf.write(html_code)
                
                code_lines.append(f"{var_name} = RenderNode('{auto_filename}')")
            elif ntype == 'ModelNode':
                code_lines.append(f"{var_name} = ModelNode(db, query='{config.get('query', '')}', params_mapping=[x.strip() for x in '{config.get('paramsMap', '')}'.split(',')], context_key='{config.get('contextKey', 'data')}', is_write={config.get('isWrite', False)})")
            elif ntype == 'LogicNode':
                logic_counter += 1
                func_code = config.get('code', 'def process_logic(request):\n    return {}')
                func_def_name = _extract_function_name(func_code)
                code_lines.append(f"\n{func_code}\n")
                code_lines.append(f"{var_name} = LogicNode({func_def_name})")
            elif ntype == 'JSNode':
                logic_counter += 1
                js_code = config.get('code', 'function process_logic(request) {\n    return {};\n}')
                js_dir = os.path.join(FRAMEWORK_DIR, 'nodes', 'js_code')
                os.makedirs(js_dir, exist_ok=True)
                js_filename = f"js_logic_{nid.replace('-', '_')}.js"
                js_filepath = os.path.join(js_dir, js_filename)
                
                full_js_code = f"""// AUTO-GENERATED BY JS_NODE COMPILER
const Response = {{
    json: (data, status = 200) => ({{
        _is_response: true,
        body: JSON.stringify(data),
        status: status,
        content_type: 'application/json; charset=utf-8'
    }}),
    redirect: (url, status = 302) => ({{
        _is_response: true,
        body: `<html><body>Redirecting to <a href="${{url}}">${{url}}</a></body></html>`,
        status: status,
        content_type: 'text/html; charset=utf-8',
        headers: {{ 'Location': url }}
    }}),
    not_found: (message = '404 Not Found') => ({{
        _is_response: true,
        body: message,
        status: 404,
        content_type: 'text/html; charset=utf-8'
    }}),
    forbidden: (message = '403 Forbidden') => ({{
        _is_response: true,
        body: message,
        status: 403,
        content_type: 'text/html; charset=utf-8'
    }})
}};

{js_code}

// Runner
const fs = require('fs');
try {{
    const inputData = fs.readFileSync(0, 'utf-8');
    const payload = JSON.parse(inputData);
    
    // Find function to execute
    let execFunc = process_logic;
    if (typeof execFunc !== 'function') {{
        throw new Error("No process_logic function found.");
    }}
    const result = execFunc(payload);
    console.log(JSON.stringify({{ status: "success", result: result || {{}} }}));
}} catch (e) {{
    console.error(JSON.stringify({{ status: "error", error: e.message, stack: e.stack }}));
    process.exit(1);
}}
"""
                with open(js_filepath, 'w', encoding='utf-8') as jsf:
                    jsf.write(full_js_code)
                
                rel_js_path = f"nodes/js_code/{js_filename}"
                code_lines.append(f"{var_name} = JSNode('{rel_js_path}')")
            elif ntype == 'ContextNode':
                logic_counter += 1
                func_code = config.get('code', 'def node_logic(request):\n    return {}')
                func_def_name = _extract_function_name(func_code)
                code_lines.append(f"\n{func_code}\n")
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
            elif ntype == 'CSSNode':
                css_filename = config.get('css_filename', '').strip()
                if not css_filename:
                    css_filename = f"style_{nid}.css"
                if not css_filename.endswith('.css'):
                    css_filename += '.css'
                css_code = config.get('css_code', '').replace('\\', '\\\\').replace('\r', '').replace("'", "\\'").replace('\n', '\\n')
                code_lines.append(f"{var_name} = CSSNode('{css_filename}', '{css_code}')")
                code_lines.append(f"{var_name}.apply()  # Writes CSS to /static/{css_filename}")
            elif ntype == 'ClientJSNode':
                js_filename = config.get('filename', 'script.js')
                js_code = config.get('code', '').replace('\\', '\\\\').replace('\r', '').replace("'", "\\'").replace('\n', '\\n')
                code_lines.append(f"{var_name} = ClientJSNode('{js_filename}', '{js_code}')")
                code_lines.append(f"{var_name}.apply()  # Writes JS to /static/{js_filename}")
            else:
                code_lines.append(f"{var_name} = BaseNode()")  # Fallback
                
        # Connect Chain
        code_lines.append("\n# Node Connection Chain")
        router_counter = 1
        processed = set()
        
        for nid in reachable_ids:
            if nid in processed:
                continue
                
            targets = outgoing_map.get(nid, [])
            if not targets:
                continue
            
            src_var = f"{nodes[nid]['type'].lower()}_{nid.replace('-', '_')}"
            
            if len(targets) == 1:
                tgt_var = f"{nodes[targets[0]]['type'].lower()}_{targets[0].replace('-', '_')}"
                code_lines.append(f"{src_var}.connect({tgt_var})")
            else:
                route_list = [
                    f"{nodes[t]['type'].lower()}_{t.replace('-', '_')}"
                    for t in targets
                ]
                router_var = f"router_node_auto_{router_counter}"
                router_counter += 1
                code_lines.append(f"{router_var} = RouterNode([{', '.join(route_list)}])")
                code_lines.append(f"{src_var}.connect({router_var})")
            
            processed.add(nid)
        
        # Start Server
        code_lines.append("\n# Start Server")
        server_var = chain_vars[0]
        code_lines.append(f"print('Node Editor Generated Server starting...')")
        code_lines.append(f"print(f'  -> http://{{{server_var}.host}}:{{{server_var}.port}}')")
        code_lines.append('from nodes.server_node import FrameworkHandler')
        code_lines.append(f"FrameworkHandler.server_node = {server_var}")
        code_lines.append(f"FrameworkHandler._middleware_chain = None  # Reset cache on redeploy")
        code_lines.append(f"from http.server import HTTPServer")
        code_lines.append(f"from socketserver import ThreadingMixIn")
        code_lines.append(f"class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):")
        code_lines.append(f"    allow_reuse_address = True")
        code_lines.append(f"with ThreadedHTTPServer(({server_var}.host, {server_var}.port), FrameworkHandler) as httpd:")
        code_lines.append(f"    try:")
        code_lines.append(f"        httpd.serve_forever()")
        code_lines.append(f"    except KeyboardInterrupt:")
        code_lines.append(f"        pass")

        # Write main.py
        with open(os.path.join(FRAMEWORK_DIR, 'main.py'), 'w') as f:
            f.write("\n".join(code_lines))

if __name__ == '__main__':
    from http.server import HTTPServer
    from socketserver import ThreadingMixIn
    import atexit
    import signal

    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
        allow_reuse_address = True
        daemon_threads = True  # Threads die when main thread exits

    httpd_server = None  # Reference for shutdown handler

    def _graceful_shutdown(signum=None, frame=None):
        """Kill the deployed server (port 8000) and shut down Node Editor cleanly."""
        global active_process, httpd_server

        # 1. Kill the deployed main.py server if running
        if active_process and active_process.poll() is None:
            print("\n🧹 Stopping deployed server (main.py)...")
            try:
                active_process.terminate()
                active_process.wait(timeout=3)
            except Exception:
                try:
                    active_process.kill()
                    active_process.wait(timeout=2)
                except Exception:
                    pass
            active_process = None
            print("   ✅ Deployed server stopped.")

        # 2. Kill any stray processes on port 8000 (safety net)
        try:
            kill_cmd = (
                "Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue "
                "| Select-Object -ExpandProperty OwningProcess "
                "| ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-Command", kill_cmd],
                capture_output=True, timeout=5
            )
        except Exception:
            pass

        # 3. Shutdown the Node Editor HTTP server
        if httpd_server:
            print("🧹 Shutting down Node Editor server...")
            try:
                httpd_server.server_close()
            except Exception:
                pass
            httpd_server = None
            print("   ✅ Node Editor stopped.")

        print("👋 All resources cleaned up. Goodbye!")

    # Register cleanup for all exit scenarios
    atexit.register(_graceful_shutdown)

    # Ctrl+C (SIGINT) naturally raises KeyboardInterrupt which we catch below.
    # We no longer override signal.SIGINT to avoid deadlocks in server shutdown.

    print(f"⚡ Node Editor starting on http://localhost:{PORT}")
    print("⚠️  WARNING: Never expose port 8080 in production!")
    print("   Set ENV=production to lock this editor.")
    print("   Press Ctrl+C to stop (deployed server will also be cleaned up).")

    # Kill any stray processes on port 8080 (safety net)
    try:
        import subprocess
        kill_cmd = (
            f"Get-NetTCPConnection -LocalPort {PORT} -ErrorAction SilentlyContinue "
            "| Select-Object -ExpandProperty OwningProcess "
            "| ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
        )
        subprocess.run(
            ["powershell", "-Command", kill_cmd],
            capture_output=True, timeout=5
        )
    except Exception:
        pass

    # Auto-open browser after a short delay
    threading.Timer(0.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()

    httpd_server = ThreadedHTTPServer(("", PORT), EditorHandler)
    try:
        httpd_server.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        _graceful_shutdown()
