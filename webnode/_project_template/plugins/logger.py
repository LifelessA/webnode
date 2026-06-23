#plugins/logger.py
from nodes.base_node import BaseNode
import settings

class ActionLoggerNode(BaseNode):
    """
    Logs every request using the core WebNodeLogger.
    Format: [TIMESTAMP] [INFO] METHOD PATH STATUS DURATION IP USER_AGENT
    """
    def __init__(self):
        super().__init__()

    def process(self, request):
        if not settings.LOGGING.get('ENABLED', True):
            return super().process(request)
        
        import time
        start = time.perf_counter()
        
        # Get request info BEFORE processing
        client_ip = request.handler.client_address[0]
        method = request.method
        path = request.path
        ua = request.headers.get('User-Agent', 'Unknown')
        
        # Pass to next node
        result = super().process(request)
        
        # Log AFTER processing (has timing)
        duration_ms = round((time.perf_counter() - start) * 1000)
        
        from core.logging import get_logger
        logger = get_logger()
        logger.request(
            method=method,
            path=path,
            duration_ms=duration_ms,
            ip=client_ip,
            user_agent=ua
        )
        
        return result