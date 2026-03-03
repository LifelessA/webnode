import http.server
import socketserver
import json
import os
import subprocess
import sys

PORT = 8080  # Node Editor port
EDITOR_DIR = os.path.dirname(os.path.abspath(__file__))
FRAMEWORK_DIR = os.path.dirname(EDITOR_DIR)

active_process = None


class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=EDITOR_DIR, **kwargs)

    def do_GET(self):
        if self.path == '/api/status':
            self.handle_status()
        elif self.path == '/api/load':
            self.handle_load()
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
        self._send_json({'status': 'live' if is_live else 'offline'})

    def handle_load(self):
        graph_path = os.path.join(EDITOR_DIR, 'graph.json')
        if os.path.exists(graph_path):
            with open(graph_path, 'r') as f:
                graph_data = json.load(f)
        else:
            graph_data = {"nodes": [], "connections": []}
        self._send_json(graph_data)

    def handle_save(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        graph_data = json.loads(post_data.decode('utf-8'))
        with open(os.path.join(EDITOR_DIR, 'graph.json'), 'w') as f:
            json.dump(graph_data, f, indent=4)
        self._send_json({'status': 'success'})

    def handle_stop(self):
        global active_process
        if active_process:
            active_process.terminate()
            active_process = None
        self._send_json({'status': 'stopped'})

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

        # 3. Stop old server
        if active_process:
            active_process.terminate()
            active_process.wait()

        # 3.5 Kill any process holding the port
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

        main_py_path = os.path.join(FRAMEWORK_DIR, 'main.py')
        active_process = subprocess.Popen([sys.executable, main_py_path], cwd=FRAMEWORK_DIR)

        self._send_json({'status': 'success'})

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def compile_graph(self, graph_data):
        nodes = {n['id']: n for n in graph_data['nodes']}
        connections = graph_data['connections']

        server_node_id = next((n['id'] for n in nodes.values() if n['type'] == 'ServerNode'), None)
        if not server_node_id:
            raise ValueError("No Server Node found in graph!")

        outgoing_map = {}
        for c in connections:
            outgoing_map.setdefault(c['source'], []).append(c['target'])

        reachable_ids = []
        queue = [server_node_id]
        while queue:
            curr = queue.pop(0)
            if curr not in reachable_ids:
                reachable_ids.append(curr)
                for tgt in outgoing_map.get(curr, []):
                    queue.append(tgt)

        types_used = set(nodes[nid]['type'] for nid in reachable_ids)
        needs_router = any(len(targets) > 1 for src, targets in outgoing_map.items() if src in reachable_ids)

        imports = [
            "import socketserver",
            "from nodes.server_node import ServerNode, FrameworkHandler",
            "from nodes.http_requests_node import HTTPRequestsNode",
        ]
        if 'URLNode' in types_used: imports.append("from nodes.url_node import URLNode")
        if 'RenderNode' in types_used: imports.append("from nodes.template_node import RenderNode")
        if 'LogicNode' in types_used: imports.append("from nodes.logic_node import LogicNode")
        if 'ModelNode' in types_used:
            imports.append("from nodes.model_node import ModelNode")
            imports.append("from core.db import Database")
        if needs_router: imports.append("from nodes.route_node import RouterNode")
        if 'ContextNode' in types_used: imports.append("from nodes.context_node import ContextNode")
        if 'ActionLoggerNode' in types_used: imports.append("from plugins.logger import ActionLoggerNode")
        if 'AntiBotNode' in types_used: imports.append("from plugins.security import AntiBotNode")
        if 'RateLimitNode' in types_used: imports.append("from plugins.security import RateLimitNode")
        if 'CSRFNode' in types_used: imports.append("from plugins.security import CSRFNode")
        if 'ScreenProtectionNode' in types_used: imports.append("from plugins.security import ScreenProtectionNode")

        code_lines = ["# AUTO-GENERATED BY NODE EDITOR COMPILER"] + imports + ["\n# Nodes Instantiation"]

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
            elif ntype == 'HTTPRequestsNode':
                code_lines.append(f"{var_name} = HTTPRequestsNode()")
            elif ntype == 'URLNode':
                code_lines.append(f"{var_name} = URLNode('{config.get('path', '/')}')")
            elif ntype == 'RenderNode':
                html_code = config.get('html_code', '<h1>Hello World!</h1>')
                custom_filename = config.get('filename', '').strip()
                auto_filename = custom_filename if custom_filename else f"auto_template_{nid}.html"
                os.makedirs(os.path.join(FRAMEWORK_DIR, 'templates'), exist_ok=True)
                with open(os.path.join(FRAMEWORK_DIR, 'templates', auto_filename), 'w', encoding='utf-8') as tf:
                    tf.write(html_code)
                code_lines.append(f"{var_name} = RenderNode('{auto_filename}')")
            elif ntype == 'ModelNode':
                code_lines.append(f"{var_name} = ModelNode(query='{config.get('query', '')}', params_mapping=[x.strip() for x in '{config.get('paramsMap', '')}'.split(',') if x.strip()], context_key='{config.get('contextKey', 'data')}', is_write={config.get('isWrite', False)})")
            elif ntype == 'LogicNode':
                logic_counter += 1
                func_code = config.get('code', 'def process_logic(request):\n    return {}')
                func_def_name = func_code.split('def ')[1].split('(')[0].strip()
                code_lines.append(f"\n{func_code}\n")
                code_lines.append(f"{var_name} = LogicNode({func_def_name})")
            elif ntype == 'ContextNode':
                logic_counter += 1
                func_code = config.get('code', 'def node_logic(request):\n    return {}')
                func_def_name = func_code.split('def ')[1].split('(')[0].strip()
                code_lines.append(f"\n{func_code}\n")
                code_lines.append(f"{var_name} = ContextNode({func_def_name})")
            elif ntype == 'ActionLoggerNode': code_lines.append(f"{var_name} = ActionLoggerNode()")
            elif ntype == 'AntiBotNode': code_lines.append(f"{var_name} = AntiBotNode()")
            elif ntype == 'RateLimitNode': code_lines.append(f"{var_name} = RateLimitNode()")
            elif ntype == 'CSRFNode': code_lines.append(f"{var_name} = CSRFNode()")
            elif ntype == 'ScreenProtectionNode': code_lines.append(f"{var_name} = ScreenProtectionNode()")

        code_lines.append("\n# Node Connection Chain")
        router_counter = 1
        for nid in reachable_ids:
            targets = outgoing_map.get(nid, [])
            if not targets: continue
            src_var = f"{nodes[nid]['type'].lower()}_{nid.replace('-', '_')}"
            if len(targets) == 1:
                tgt_var = f"{nodes[targets[0]]['type'].lower()}_{targets[0].replace('-', '_')}"
                code_lines.append(f"{src_var}.connect({tgt_var})")
            else:
                route_list = [f"{nodes[tgt]['type'].lower()}_{tgt.replace('-', '_')}" for tgt in targets]
                router_var = f"router_node_auto_{router_counter}"
                router_counter += 1
                code_lines.append(f"{router_var} = RouterNode([{', '.join(route_list)}])")
                code_lines.append(f"{src_var}.connect({router_var})")

        server_var = chain_vars[0]
        code_lines += [
            "\n# Start Server",
            f"print('Node Editor Generated Server starting...')",
            f"FrameworkHandler.server_node = {server_var}",
            f"from http.server import HTTPServer",
            f"with HTTPServer(({server_var}.host, {server_var}.port), FrameworkHandler) as httpd:",
            f"    try:",
            f"        httpd.serve_forever()",
            f"    except KeyboardInterrupt:",
            f"        pass"
        ]

        with open(os.path.join(FRAMEWORK_DIR, 'main.py'), 'w') as f:
            f.write("\n".join(code_lines))

    def log_message(self, format, *args):
        pass  # Suppress request logs


if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), EditorHandler) as httpd:
        print(f"⚡ Node Editor running at http://localhost:{PORT}")
        print(f"   Framework directory: {FRAMEWORK_DIR}")
        httpd.serve_forever()
