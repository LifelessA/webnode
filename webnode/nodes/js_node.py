from nodes.base_node import BaseNode
from nodes.response import Response
import subprocess
import json
import os

class JSNode(BaseNode):
    """
    Executes a server-side JavaScript logic function.
    If the function returns a Response-like object (redirect, JSON, 404, etc.),
    it short-circuits immediately — bypassing any downstream nodes.
    If it returns a dict, the dict is merged into request.context and
    processing continues to the next node.
    """
    def __init__(self, js_filepath):
        super().__init__()
        self.js_filepath = js_filepath

    def process(self, request):
        # 1. Serialize request details
        payload = {
            "path": request.path,
            "method": request.method,
            "headers": dict(request.headers),
            "query_params": request.query_params,
            "params": request.params,
            "context": request.context,
            "url_params": request.url_params
        }
        
        # 2. Get absolute path to the JS file
        framework_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        abs_js_path = os.path.join(framework_dir, self.js_filepath)
        
        # 3. Run Node.js with the code.
        try:
            res = subprocess.run(
                ["node", abs_js_path],
                input=json.dumps(payload).encode('utf-8'),
                capture_output=True,
                check=False
            )
        except FileNotFoundError:
            raise RuntimeError("Node.js is not installed or not in the system PATH. Please install Node.js to execute JSNode.")
        
        if res.returncode != 0:
            err_msg = res.stderr.decode('utf-8', errors='replace')
            # Check if err_msg contains JSON error response
            try:
                err_data = json.loads(err_msg.strip())
                if err_data.get('status') == 'error':
                    raise RuntimeError(f"JS execution error: {err_data.get('error')}\n{err_data.get('stack')}")
            except json.JSONDecodeError:
                pass
            raise RuntimeError(f"JS execution failed:\n{err_msg}")
            
        stdout_str = res.stdout.decode('utf-8', errors='replace').strip()
        try:
            output = json.loads(stdout_str)
        except json.JSONDecodeError:
            raise RuntimeError(f"JS did not return valid JSON. Output was:\n{stdout_str}")
            
        if output.get('status') == 'error':
            raise RuntimeError(f"JS execution error: {output.get('error')}\n{output.get('stack')}")
            
        result = output.get('result', {})
        
        # Short-circuit: Response-like objects bypass the rest of the chain
        if isinstance(result, dict) and result.get('_is_response'):
            return Response(
                body=result.get('body', ''),
                status=result.get('status', 200),
                content_type=result.get('content_type', 'text/html; charset=utf-8'),
                headers=result.get('headers', {})
            )
            
        if isinstance(result, dict):
            request.context.update(result)
            
        return super().process(request)
