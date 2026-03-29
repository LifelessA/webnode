"""
core/ai_graph.py — AI-Readable Graph Format

Ye module graph.json ko ek clear, structured format mein export karta hai
jisse AI agents (GPT, Claude, Gemini) directly padhh ke samjhein:
  - Konsa node konse se connected hai
  - Har node ki responsibility kya hai
  - Request kahan se aati hai, kahan jaati hai
  - Agar error ho, kahan fix karna hai

Usage:
    from core.ai_graph import GraphReader, GraphSummary

    # node_editor/graph.json se load karo
    reader  = GraphReader.from_file('node_editor/graph.json')
    summary = reader.to_ai_summary()
    print(summary)        # Human-readable
    print(reader.to_json())  # Machine-readable for AI

    # Live running nodes se bhi describe kar sako
    from core.ai_graph import describe_live_graph
    describe_live_graph(server_node)   # prints chain
"""
import json
import os
import settings


# ---------------------------------------------------------------------------
# Node Type Descriptions (for AI context)
# ---------------------------------------------------------------------------

_NODE_DESCRIPTIONS = {
    'ServerNode'         : 'HTTP server root. Listens on host:port. Entry point of the graph.',
    'HTTPRequestsNode'   : 'Parses raw HTTP request into RequestWrapper (path, method, params, body).',
    'URLNode'            : 'Route matcher. Passes request forward only if path matches. Supports /path/<param>.',
    'RouterNode'         : 'Distributes request to multiple URL branches. Acts as a hub.',
    'LogicNode'          : 'Executes a Python function. Takes request, returns dict context. Business logic lives here.',
    'ContextNode'        : 'Updates request.context dict with function result. Used for chained data building.',
    'RenderNode'         : 'Reads an HTML template, injects context, returns final HTML string.',
    'ModelNode'          : 'Runs a SQL query. Results stored in request.context[key]. Reads or writes DB.',
    'ActionLoggerNode'   : 'Logs every request to core/logs/{ip}.txt. Transparent pass-through.',
    'AntiBotNode'        : 'Blocks known bots and scrapers by User-Agent header.',
    'RateLimitNode'      : 'Blocks IPs exceeding request rate. Config in settings.SECURITY.',
    'CSRFNode'           : 'Validates CSRF token on POST requests. Generates token on GET.',
    'ScreenProtectionNode': 'Injects JS to disable right-click, screenshots, and text selection.',
}


def _describe_node_type(node_type):
    return _NODE_DESCRIPTIONS.get(node_type, f'{node_type} — custom node.')


# ---------------------------------------------------------------------------
# GraphReader — parses graph.json
# ---------------------------------------------------------------------------

class GraphReader:
    """
    Reads and understands a node_editor graph.json file.

    graph.json structure:
        {
          "nodes": [{"id": "node-10", "type": "ServerNode", "config": {...}}, ...],
          "connections": [{"source": "node-10", "target": "node-11"}, ...]
        }
    """

    def __init__(self, graph_data):
        self.nodes       = {n['id']: n for n in graph_data.get('nodes', [])}
        self.connections = graph_data.get('connections', [])
        self._out_map    = self._build_out_map()

    @classmethod
    def from_file(cls, path=None):
        if path is None:
            path = os.path.join(settings.BASE_DIR, 'node_editor', 'graph.json')
        with open(path, 'r', encoding='utf-8') as f:
            return cls(json.load(f))

    @classmethod
    def from_dict(cls, data):
        return cls(data)

    def _build_out_map(self):
        out = {}
        for c in self.connections:
            out.setdefault(c['source'], []).append(c['target'])
        return out

    def _find_root(self):
        """Find the ServerNode (root of the graph)."""
        for nid, node in self.nodes.items():
            if node['type'] == 'ServerNode':
                return nid
        return next(iter(self.nodes)) if self.nodes else None

    def _bfs_order(self):
        """Return node IDs in BFS order from root."""
        root = self._find_root()
        if not root:
            return []
        visited = []
        queue   = [root]
        seen    = set()
        while queue:
            curr = queue.pop(0)
            if curr in seen:
                continue
            seen.add(curr)
            visited.append(curr)
            queue.extend(self._out_map.get(curr, []))
        return visited

    # ------------------------------------------------------------------
    # AI Summary outputs
    # ------------------------------------------------------------------

    def to_ai_summary(self):
        """
        Generate a human + AI readable text summary of the graph.
        This can be pasted into an AI prompt for context.
        """
        order  = self._bfs_order()
        lines  = [
            "═" * 55,
            "  NODE GRAPH SUMMARY",
            "  (AI-readable node-by-node description)",
            "═" * 55,
            f"  Total Nodes      : {len(self.nodes)}",
            f"  Total Connections: {len(self.connections)}",
            "═" * 55,
            "",
            "  REQUEST FLOW (top to bottom):",
            "",
        ]

        for i, nid in enumerate(order):
            node    = self.nodes[nid]
            ntype   = node['type']
            config  = node.get('config', {})
            targets = self._out_map.get(nid, [])

            lines.append(f"  [{i+1}] {ntype}  (id: {nid})")
            lines.append(f"       Role   : {_describe_node_type(ntype)}")

            # Config details
            if ntype == 'ServerNode':
                lines.append(f"       Config : host={config.get('ip','127.0.0.1')} port={config.get('port',8000)}")
            elif ntype == 'URLNode':
                lines.append(f"       Config : path={config.get('path','/')}")
            elif ntype == 'RenderNode':
                lines.append(f"       Config : template={config.get('filename','auto')}")
            elif ntype == 'ModelNode':
                lines.append(f"       Config : query={config.get('query','')[:50]}")
            elif ntype in ('LogicNode', 'ContextNode'):
                code_preview = config.get('code', '')[:80].replace('\n', ' ')
                lines.append(f"       Logic  : {code_preview}...")

            # Connections
            if targets:
                target_types = [self.nodes[t]['type'] for t in targets if t in self.nodes]
                lines.append(f"       Next   : {' + '.join(target_types)}")
            else:
                lines.append(f"       Next   : [END — response returned here]")
            lines.append("")

        lines.append("═" * 55)
        lines.append("  HOW TO EDIT:")
        lines.append("  - Open node_editor/index.html to visually modify the graph")
        lines.append("  - Or edit node_editor/graph.json directly")
        lines.append("  - Then Deploy to regenerate main.py")
        lines.append("═" * 55)
        return '\n'.join(lines)

    def to_json(self):
        """
        Return a structured JSON string for AI agents to parse.
        Contains: nodes, connections, flow_order, node_descriptions.
        """
        order = self._bfs_order()
        output = {
            "framework"        : "Node Graph Framework",
            "total_nodes"      : len(self.nodes),
            "total_connections": len(self.connections),
            "flow_order"       : [
                {
                    "step"       : i + 1,
                    "id"         : nid,
                    "type"       : self.nodes[nid]['type'],
                    "description": _describe_node_type(self.nodes[nid]['type']),
                    "config"     : self.nodes[nid].get('config', {}),
                    "connects_to": [
                        self.nodes[t]['type']
                        for t in self._out_map.get(nid, [])
                        if t in self.nodes
                    ],
                }
                for i, nid in enumerate(order)
            ],
            "raw_connections": self.connections,
            "ai_instructions": (
                "This is a node graph web framework. Each node has ONE responsibility. "
                "To fix an error in a specific node, locate the node by 'id' or 'type' "
                "in flow_order and edit its 'config'. "
                "To add a route: add a URLNode → LogicNode → RenderNode chain and connect it. "
                "After editing graph.json, Deploy from the Node Editor to regenerate main.py."
            ),
        }
        return json.dumps(output, indent=2, ensure_ascii=False)

    def routes(self):
        """Return all URLNode routes for quick reference."""
        return [
            {
                'id'  : nid,
                'path': node.get('config', {}).get('path', '?'),
            }
            for nid, node in self.nodes.items()
            if node['type'] == 'URLNode'
        ]

    def print_routes(self):
        print("\n  📍 Registered Routes:")
        for r in self.routes():
            print(f"     GET/POST  {r['path']}  (node: {r['id']})")
        print()


# ---------------------------------------------------------------------------
# Live Graph Describer (from running nodes, not graph.json)
# ---------------------------------------------------------------------------

def describe_live_graph(root_node, indent=0):
    """
    Print the live node graph structure from a running ServerNode.
    Works on the actual Python objects (not graph.json).

    Usage (in main.py or shell):
        from core.ai_graph import describe_live_graph
        describe_live_graph(server_node)
    """
    chain = root_node.describe_chain()
    print(f"\n{'─'*50}")
    print(f"  Live Node Graph")
    print(f"{'─'*50}")
    for i, node_info in enumerate(chain):
        prefix = '  ' + ('└─' if i == len(chain) - 1 else '├─')
        name   = node_info.get('name', '?')
        ntype  = node_info.get('type', '?')
        nxt    = node_info.get('next_name', None)
        print(f"{prefix} [{i+1}] {ntype}  ({name})")
        if i < len(chain) - 1:
            print(f"  {'│' if i < len(chain) - 2 else ' '}")
    print(f"{'─'*50}\n")