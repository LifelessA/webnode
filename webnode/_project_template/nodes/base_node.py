"""
nodes/base_node.py — Node Framework

BaseNode : Foundation class for ALL nodes.

Key Design Principles (AI-Friendly Architecture):
  1. Single Responsibility — har node ek kaam karta hai
  2. Chain Pattern       — nodes doubly linked list ki tarah connect hote hain
  3. Error Isolation     — ek node fail ho to sirf wahi crash ho, baaki nahi
  4. Named Nodes         — har node ka ek readable name hota hai (debug ke liye)

Graph Flow:
  node_A.connect(node_B).connect(node_C)
  node_A.process(data) → node_B.process(data) → node_C.process(data)
"""
import traceback


class BaseNode:
    """
    Base class for all nodes in the framework.

    Attributes:
        next_node  : BaseNode | None — next node in the chain
        prev_node  : BaseNode | None — previous node (back-reference)
        _node_name : str             — human-readable name for error reporting
        _debug     : bool            — if True, errors are caught and reported; else re-raised

    Sub-classes should override process() and call super().process(result)
    at the end to pass data to the next node.
    """

    def __init__(self):
        self.next_node  = None
        self.prev_node  = None
        # Auto-generated readable name: "URLNode_at_<short_id>"
        self._node_name = f"{self.__class__.__name__}_at_{hex(id(self))[-4:]}"
        self._debug     = True   # Catch + report errors by default
        self._fallback  = None  # ← ADD THIS

    def set_fallback(self, handler):
        """
        Set a fallback handler for errors.
        
        handler signature:
            def my_fallback(request, error):
                return Response.server_error(
                    "Custom error message"
                )
        
        Usage:
            node.set_fallback(my_handler)
            # or chained:
            URLNode('/shop')\
                .set_fallback(handler)\
                .connect(logic)
        
        Returns self for chaining.
        """
        self._fallback = handler
        return self

    # ------------------------------------------------------------------
    # Node Naming (for clear error messages)
    # ------------------------------------------------------------------

    def set_name(self, name):
        """
        Give this node a human-readable name for error reporting.
        Example:
            URLNode('/users').set_name('user_url')
        """
        self._node_name = name
        return self  # allow chaining: URLNode('/').set_name('index').connect(...)

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def connect(self, node):
        """
        Connect this node to the next node in the graph chain.
        Returns the next node to allow fluent chaining:
            node_a.connect(node_b).connect(node_c)
        """
        self.next_node  = node
        node.prev_node  = self
        return node

    # ------------------------------------------------------------------
    # Processing (with error isolation)
    # ------------------------------------------------------------------

    def process(self, data):
        """
        Process data and pass to next node.
        Errors are caught and handled 
        gracefully via _on_error().
        """
        if self.next_node:
            try:
                return self.next_node.process(data)
            except Exception as e:
                return self._on_error(
                    e, data, 
                    node=self.next_node
                )
        return data

    def _on_error(self, error, data, node=None):
        """
        Handle error from this node 
        or next_node.
        
        Priority:
        1. If _fallback is set → call it
        2. Otherwise → NodeErrorReporter
        3. Always return valid response
        """
        target = node or self
        
        # Priority 1: Custom fallback
        if self._fallback is not None:
            try:
                return self._fallback(data, error)
            except Exception as fb_err:
                # Fallback itself failed
                print(
                    f"[BaseNode] Fallback "
                    f"error in "
                    f"{target._node_name}: "
                    f"{fb_err}"
                )
        
        # Priority 2: NodeErrorReporter
        import traceback
        tb_str = traceback.format_exc()
        try:
            from core.errors import NodeErrorReporter
            return NodeErrorReporter.report(
                node_name=target._node_name,
                node_type=type(target).__name__,
                error=error,
                request=data if hasattr(data, 'path') else None,
                tb_str=tb_str,
            )
        except Exception:
            # Absolute fallback
            print(
                f"[NodeError] "
                f"{type(target).__name__}: "
                f"{error}"
            )
            return (
                f"<h1>500 — "
                f"{type(target).__name__} "
                f"Error</h1>"
                f"<pre>{tb_str}</pre>"
            )

    def safe_process(self, data):
        """
        Wrapped version of process() — always catches errors.
        Used as the entry point for the graph.
        """
        try:
            return self.process(data)
        except Exception as e:
            return self._handle_error(e, data, node=self)

    def _handle_error(self, error, data, node=None):
        """
        Handle a node error: log it, print it, return HTML error page.
        """
        target = node or self
        tb_str = traceback.format_exc()

        # Lazy import to avoid circular imports
        try:
            from core.errors import NodeErrorReporter
            return NodeErrorReporter.report(
                node_name = target._node_name,
                node_type = type(target).__name__,
                error     = error,
                request   = data if hasattr(data, 'path') else None,
                tb_str    = tb_str,
            )
        except Exception:
            # Absolute fallback — never crash the reporter
            print(f"[NodeError] {type(target).__name__}: {error}")
            return f"<h1>500 — {type(target).__name__} Error</h1><pre>{tb_str}</pre>"

    # ------------------------------------------------------------------
    # Graph Introspection (AI-Readable)
    # ------------------------------------------------------------------

    def describe(self):
        """
        Return a structured dict describing this node.
        Used by AI agents and the Node Editor to understand graph structure.
        """
        return {
            "name"      : self._node_name,
            "type"      : self.__class__.__name__,
            "has_next"  : self.next_node is not None,
            "has_prev"  : self.prev_node is not None,
            "next_name" : self.next_node._node_name if self.next_node else None,
        }

    def describe_chain(self):
        """
        Return a list describing the entire chain from this node forward.
        Useful for AI to understand the full flow.

        Example output:
            [
              {"name": "server_1", "type": "ServerNode", ...},
              {"name": "http_parser", "type": "HTTPRequestsNode", ...},
              {"name": "url_home", "type": "URLNode", ...},
              ...
            ]
        """
        chain = []
        current = self
        seen = set()
        while current is not None:
            nid = id(current)
            if nid in seen:
                break  # Cycle guard
            seen.add(nid)
            chain.append(current.describe())
            current = current.next_node
        return chain

    def __repr__(self):
        return f"<{self.__class__.__name__} name={self._node_name!r}>"