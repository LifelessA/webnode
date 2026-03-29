from nodes.base_node import BaseNode
from core.db import Database

class ModelNode(BaseNode):
    """
    Model Component of MVC.
    Interacts with the Database.
    """
    def __init__(self, query, params_mapping=None, context_key='data', is_write=False):
        super().__init__()
        self.query = query
        self.params_mapping = params_mapping or [] # List of param keys to fetch from request
        self.context_key = context_key
        self.is_write = is_write
        self.db = Database()

    def process(self, request):
        """
        Executes the query and stores result in request.context (if read).
        Now supports BULK insert if params resolve to a list of lists.
        """
        # 1. Prepare Parameters
        query_params = []
        is_bulk = False

        if self.params_mapping:
            # Check if the FIRST param maps to a list (Bulk Operation Mode)
            # This is a simple heuristic: if params_mapping has 1 key and that key holds a list of tuples/lists.
            first_key = self.params_mapping[0]
            val = request.context.get(first_key)
            
            if len(self.params_mapping) == 1 and isinstance(val, list):
                # BULK MODE: The context variable IS the list of rows
                query_params = val
                is_bulk = True
            else:
                # STANDARD MODE: Fetch each param
                for key in self.params_mapping:
                    val = request.get_param(key)
                    if val is None:
                        val = request.context.get(key)
                    query_params.append(val)
        
        # 2. Execute Query
        if self.is_write:
            try:
                if is_bulk:
                     self.db.executemany(self.query, query_params)
                     request.context[f'{self.context_key}_count'] = len(query_params)
                else:
                    self.db.execute(self.query, tuple(query_params))
                
                # Optional: Store success flag
                request.context[f'{self.context_key}_success'] = True
            except Exception as e:
                request.context['error'] = str(e)
        else:
            results = self.db.fetchall(self.query, tuple(query_params))
            # Store in context
            request.context[self.context_key] = results
            
        return super().process(request)