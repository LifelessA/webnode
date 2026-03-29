"""
nodes/middleware/chain.py — Node Framework

MiddlewareChain : Reads settings.MIDDLEWARE list, instantiates each class,
                  and executes them in order around the node graph.

Each middleware class expects Django-style signature:
    class MyMiddleware:
        def __init__(self, get_response):
            self.get_response = get_response
        def __call__(self, request):
            # before graph
            response = self.get_response(request)
            # after graph
            return response
"""
import importlib
import settings


def _import_string(dotted_path):
    """Import a class/function from a dotted string path."""
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
        module = importlib.import_module(module_path)
        return getattr(module, class_name)
    except (ValueError, ImportError, AttributeError) as e:
        print(f"[Middleware] Could not import {dotted_path!r}: {e}")
        return None


class MiddlewareChain:
    """
    Builds and executes the middleware chain defined in settings.MIDDLEWARE.

    Usage in FrameworkHandler:
        chain = MiddlewareChain.build(final_handler=graph_runner)
        chain(request)

    The chain executes: MW1 → MW2 → … → final_handler → … → MW2 → MW1
    (Django-style, innermost-first wrapping).
    """

    def __init__(self, handler):
        self._handler = handler

    def __call__(self, request):
        return self._handler(request)

    @classmethod
    def build(cls, final_handler):
        """
        Build the middleware chain from settings.MIDDLEWARE.

        Args:
            final_handler : callable(request) → response
                            The innermost function (runs the node graph).

        Returns:
            MiddlewareChain instance wrapping all middleware.
        """
        middleware_list = getattr(settings, 'MIDDLEWARE', [])
        handler = final_handler

        for path in reversed(middleware_list):
            klass = _import_string(path)
            if klass is None:
                continue
            try:
                handler = klass(handler)
            except Exception as e:
                print(f"[Middleware] Could not instantiate {path!r}: {e}")

        return cls(handler)

    @staticmethod
    def resolve_middleware_class(path):
        """Utility — import and return a middleware class by its dotted path."""
        return _import_string(path)