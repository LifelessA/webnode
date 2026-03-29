from nodes.base_node import BaseNode
from nodes.response import Response
import sys

class LogicNode(BaseNode):
    """
    Executes a callable logic function.
    If the function returns a Response (redirect, JSON, 404, etc.),
    it short-circuits immediately — bypassing any downstream nodes.
    If it returns a dict, the dict is merged into request.context and
    processing continues to the next node.
    """
    def __init__(self, logic_func):
        super().__init__()
        self.logic_func = logic_func

    def process(self, request):
        """
        Executes business logic.
        - Response object  → return immediately (redirect / JSON / error)
        - dict             → merge into request.context, continue chain
        - anything else    → continue chain unchanged
        """
        result = self.logic_func(request)

        # Short-circuit: Response objects bypass the rest of the chain
        if isinstance(result, Response):
            return result

        if isinstance(result, dict):
            request.context.update(result)

        return super().process(request)