import http.server
import socketserver
import json
import os
import subprocess
import signal
import sys
import socket

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

class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=EDITOR_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/status':
            self.handle_status()
        elif self.path == '/api/load':
            self.handle_load()
        elif self.path == '/api/errors':
            self.handle_errors()
        else:
            super().do_GET()

    def do_POST(self):
        if self.path == '/api/save':
            self.handle_save()
        elif self.path == '/api/deploy':
            self.handle_deploy()
        elif self.path == '/api/stop':
            self.handle_stop()
        else:
            self.send_error(404, "API endpoint not found")

    def handle_status(self):
        global active_process
        is_live = False
        if active_process and active_process.poll() is None:
            is_live = True
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'live' if is_live else 'offline'}).encode())

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
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'success'}).encode())

    def handle_stop(self):
        global active_process
        if active_process:
            active_process.terminate()
            active_process = None
        
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'status': 'stopped'}).encode())

    def handle_deploy(self):
        global active_process
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        
        # 1. Save JSON
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
            
        # 2. Compile JSON to main.py
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
            active_process.wait()
            
        # 3.5 Forcefully kill any stray background processes holding the port
        try:
            port = 8000
            for n in graph_data.get('nodes', []):
                if n['type'] == 'ServerNode':
                    port = int(n.get('config', {}).get('port', 8000))
                    break
            kill_cmd = f"Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess | ForEach-Object {{ Stop-Process -Id $_ -Force }}"
            subprocess.run(["powershell", "-Command", kill_cmd], capture_output=True)
        except Exception:
            pass
            
        # Check port is free before starting
        port = 8000  # get from graph_data
        for n in graph_data.get('nodes', []):
            if n['type'] == 'ServerNode':
                port = int(n.get('config', {}).get('port', 8000))
                break
        
        # Wait for port to be free
        # (old process may take time to die)
        import time
        for _ in range(20):  # max 2 seconds
            if is_port_free(port):
                break
            time.sleep(0.1)

        main_py_path = os.path.join(FRAMEWORK_DIR, 'main.py')
        active_process = subprocess.Popen([sys.executable, main_py_path], cwd=FRAMEWORK_DIR)
        
        # Verify server actually started
        if not wait_for_server(port, timeout=8):
            # Server failed to start
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(
                json.dumps({
                    'status': 'error',
                    'message': f'Server failed to start on port {port}. Check main.py for errors.'
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
        
        # Find starting node (ServerNode)
        server_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'ServerNode'), None)
        if not server_node_id:
            raise ValueError("No Server Node found in graph!")

        # Find mapping of source -> list of targets
        outgoing_map = {}
        for c in connections:
            source_id = c['source']
            target_id = c['target']
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
        
        imports.append("from nodes.response import Response")

        code_lines = [
            "# AUTO-GENERATED BY NODE EDITOR COMPILER",
            "\n".join(imports),
            "\n# Initialize Database if needed"
        ]
        
        if 'ModelNode' in types_used:
            code_lines.append("db = Database('node.db')")
            code_lines.append("db.connect()")
            
        code_lines.append("\n# Nodes Instantiation")
        
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
                css_filename = config.get('css_filename', 'style.css')
                css_code = config.get('css_code', '').replace("'", "\\'").replace('\n', '\\n')
                code_lines.append(f"{var_name} = CSSNode('{css_filename}', '{css_code}')")
                code_lines.append(f"{var_name}.apply()  # Writes CSS to /static/{css_filename}")
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
        code_lines.append(f"class ThreadedHTTPServer(ThreadingMixIn, HTTPServer): pass")
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
    class ThreadedHTTPServer(ThreadingMixIn, HTTPServer): pass
    with ThreadedHTTPServer(("", PORT), EditorHandler) as httpd:
        print(f"Node Editor running at http://localhost:{PORT}")
        httpd.serve_forever()