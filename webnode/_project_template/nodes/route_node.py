from nodes.base_node import BaseNode

class RouterNode(BaseNode):
    """
    Router Node that manages multiple route branches.
    It iterates through a list of route chains and executes the first one that matches.
    """
    def __init__(self, routes):
        super().__init__()
        self.routes = routes

    def process(self, request):
        for route in self.routes:
            # route is expected to be a URLNode (start of a chain)
            result = route.process(request)
            if result is not None:
                return result
        return None