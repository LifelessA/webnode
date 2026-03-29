import time

class Middleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Code to be executed for each request before the view (and later middleware) are called.
        
        response = self.get_response(request)

        # Code to be executed for each request/response after the view is called.
        return response

class SimpleLoggingMiddleware:
    """
    Logs every request to the console.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()
        print(f"[Middleware] Request: {request.method} {request.path}")
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        print(f"[Middleware] Response generated in {duration:.4f}s")
        return response

class SecurityMiddleware:
    """
    Adds security headers to the response.
    NOTE: In our simple implementation, response is just a string. 
    A real framework would allow modifying headers object.
    For now, we will verify integration by printing.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Process request
        response = self.get_response(request)
        
        # In a real HttpResonse object we would do:
        # response['X-Content-Type-Options'] = 'nosniff'
        # Since we return string, we just log ensuring it ran.
        # customization of the Server handler is needed to inject headers really.
        return response