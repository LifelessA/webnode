from nodes.base_node import BaseNode
from core.db import Database

class ModelNode(BaseNode):
    """
    Model Component of MVC.
    Interacts with the Database.
    """
    def __init__(self, *args, **kwargs):
        super().__init__()
        
        # Flexible argument handling to support both ModelNode(db, query, ...) and ModelNode(query, ...)
        remaining_args = list(args)
        first_is_db = False
        if remaining_args:
            first_arg = remaining_args[0]
            if hasattr(first_arg, 'execute') or hasattr(first_arg, 'fetchall') or type(first_arg).__name__ == 'Database':
                first_is_db = True
                
        if first_is_db:
            self.db = remaining_args.pop(0)
        else:
            self.db = Database()
            
        # Parse keyword arguments
        query = kwargs.get('query')
        params_mapping = kwargs.get('params_mapping') or kwargs.get('paramsMap') or kwargs.get('params_map')
        context_key = kwargs.get('context_key', 'data')
        is_write = kwargs.get('is_write', False)
        
        # Parse remaining positional arguments
        if remaining_args:
            query = remaining_args.pop(0)
        if remaining_args:
            params_mapping = remaining_args.pop(0)
        if remaining_args:
            context_key = remaining_args.pop(0)
        if remaining_args:
            is_write = remaining_args.pop(0)
            
        self.query = query
        self.params_mapping = params_mapping or []
        self.context_key = context_key
        self.is_write = is_write

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