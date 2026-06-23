from nodes.base_node import BaseNode

class ContextNode(BaseNode):
    """
    Executes a callable logic function to update the request context.
    Passes the request object to the next node.
    """
    def __init__(self, context_func):
        super().__init__()
        self.context_func = context_func

    def process(self, request):
        """
        Executes logic, merges result into request.context, and passes request forward.
        """
        result = self.context_func(request)
        
        if isinstance(result, dict):
            request.context.update(result)
        
        return super().process(request)