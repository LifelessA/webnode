"""
core/testing.py — Node Testing Framework

Test every node ISOLATED without running the entire server.

AI-Friendly Design:
  - AI can write a test for one node without knowing other nodes
  - Build a MockRequest, pass it to the node, and check the output
  - Clear pass/fail output with node name

Usage:
    from core.testing import NodeTestCase, MockRequest, run_tests

    class MyTest(NodeTestCase):
        def test_url_match(self):
            from nodes.url_node import URLNode
            node = URLNode('/users/<id>')
            req  = MockRequest(path='/users/42')
            # Manually check matching
            params = node._match('/users/42')
            self.assert_equal(params, {'id': '42'}, 'Dynamic URL param extraction')

        def test_logic_node(self):
            from nodes.logic_node import LogicNode
            def my_logic(req):
                return {'name': req.query_params.get('n', 'World')}

            node   = LogicNode(my_logic)
            req    = MockRequest(query_params={'n': 'Ali'})
            result = node.process(req)
            self.assert_equal(result, {'name': 'Ali'}, 'LogicNode output')

    run_tests(MyTest)
"""
import time
import traceback
import datetime


# ---------------------------------------------------------------------------
# MockRequest  — Fake request for testing nodes
# ---------------------------------------------------------------------------

class MockRequest:
    """
    A fake RequestWrapper for unit testing nodes.
    Pass it to any node's process() method without starting a server.

    Example:
        req = MockRequest(
            method='POST',
            path='/login',
            params={'username': ['ali'], 'password': ['1234']},
            query_params={'next': '/dashboard'},
            json_body={'key': 'value'},
            context={'user_id': 1},
            url_params={'id': '42'},
            headers={'Content-Type': 'application/json'},
        )
    """

    class _FakeHandler:
        client_address = ('127.0.0.1', 9999)

    def __init__(self,
                 method='GET',
                 path='/',
                 params=None,
                 query_params=None,
                 json_body=None,
                 context=None,
                 url_params=None,
                 headers=None):
        self.method       = method.upper()
        self.path         = path
        self.params       = params or {}
        self.query_params = query_params or {}
        self.context      = context or {}
        self.url_params   = url_params or {}
        self.headers      = MockHeaders(headers or {})
        self.body_bytes   = b''
        self.handler      = self._FakeHandler()
        self._json_body   = json_body

        # Pre-encode JSON body if provided
        if json_body is not None:
            import json
            self.body_bytes = json.dumps(json_body).encode('utf-8')

    def get_param(self, key, default=None):
        if key in self.url_params:
            return self.url_params[key]
        v = self.params.get(key)
        if isinstance(v, list):
            return v[0] if v else default
        return v if v is not None else default

    def get_json(self):
        if self._json_body is not None:
            return self._json_body
        import json
        try:
            return json.loads(self.body_bytes)
        except Exception:
            return None

    def get_file(self, key):
        return None

    @property
    def content_type(self):
        return self.headers.get('Content-Type', '').lower()

    def __repr__(self):
        return f'<MockRequest {self.method} {self.path}>'


class MockHeaders(dict):
    """Dict subclass with case-insensitive .get()"""
    def get(self, key, default=None):
        for k, v in self.items():
            if k.lower() == key.lower():
                return v
        return default

    def __contains__(self, key):
        return self.get(key) is not None


# ---------------------------------------------------------------------------
# Test Result
# ---------------------------------------------------------------------------

class TestResult:
    def __init__(self, test_name, node_name=''):
        self.test_name  = test_name
        self.node_name  = node_name
        self.passed     = False
        self.message    = ''
        self.duration   = 0.0
        self.error      = None

    def __repr__(self):
        status = '✅ PASS' if self.passed else '❌ FAIL'
        base   = f"  {status}  {self.test_name}"
        if self.node_name:
            base += f"  [{self.node_name}]"
        if not self.passed:
            base += f"\n         → {self.message}"
        base += f"  ({self.duration*1000:.1f}ms)"
        return base


# ---------------------------------------------------------------------------
# NodeTestCase — Base class for writing node tests
# ---------------------------------------------------------------------------

class NodeTestCase:
    """
    Base class for all node test suites.
    Write test_* methods — they are auto-discovered and run.

    Example:
        class URLTests(NodeTestCase):
            def test_exact_match(self):
                node = URLNode('/home')
                req  = MockRequest(path='/home')
                result = node.process(req)
                self.assert_not_none(result, 'Exact match should pass')

            def test_no_match(self):
                node = URLNode('/home')
                req  = MockRequest(path='/about')
                result = node.process(req)
                self.assert_none(result, 'Wrong path should return None')
    """

    def assert_equal(self, actual, expected, label=''):
        if actual != expected:
            raise AssertionError(
                f"{label}: Expected {expected!r}, got {actual!r}"
            )

    def assert_not_equal(self, actual, expected, label=''):
        if actual == expected:
            raise AssertionError(f"{label}: Expected values to differ, both are {actual!r}")

    def assert_true(self, expr, label=''):
        if not expr:
            raise AssertionError(f"{label}: Expected True, got {expr!r}")

    def assert_false(self, expr, label=''):
        if expr:
            raise AssertionError(f"{label}: Expected False, got {expr!r}")

    def assert_none(self, val, label=''):
        if val is not None:
            raise AssertionError(f"{label}: Expected None, got {val!r}")

    def assert_not_none(self, val, label=''):
        if val is None:
            raise AssertionError(f"{label}: Expected not-None, got None")

    def assert_contains(self, container, item, label=''):
        if item not in container:
            raise AssertionError(f"{label}: {item!r} not found in {container!r}")

    def assert_status(self, response, status_code, label=''):
        """Assert a Response object has the given status code."""
        actual = getattr(response, 'status', None)
        if actual != status_code:
            raise AssertionError(
                f"{label}: Expected status {status_code}, got {actual}"
            )

    def assert_json_key(self, response, key, label=''):
        """Assert a Response.json() contains a key."""
        import json
        try:
            data = json.loads(response.body)
            if key not in data:
                raise AssertionError(f"{label}: Key {key!r} missing in JSON response")
        except Exception as e:
            raise AssertionError(f"{label}: Could not parse JSON — {e}")


# ---------------------------------------------------------------------------
# Test Runner
# ---------------------------------------------------------------------------

def run_tests(*test_classes, verbose=True):
    """
    Discover and run all test_* methods in given test classes.

    Usage:
        run_tests(URLTests, LogicTests, ModelTests)

    Returns:
        dict with 'passed', 'failed', 'total', 'results'
    """
    results = []
    total   = passed = failed = 0

    print(f"\n{'━'*55}")
    print(f"  🧪  Node Test Runner")
    print(f"  {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'━'*55}")

    for cls in test_classes:
        instance   = cls()
        class_name = cls.__name__
        methods    = [m for m in dir(instance) if m.startswith('test_')]

        if verbose:
            print(f"\n  📦 {class_name} ({len(methods)} tests)")

        for method_name in sorted(methods):
            res = TestResult(
                test_name = method_name.replace('test_', '').replace('_', ' '),
                node_name = class_name,
            )
            total += 1
            t0 = time.perf_counter()
            try:
                getattr(instance, method_name)()
                res.passed   = True
                passed      += 1
            except AssertionError as e:
                res.passed   = False
                res.message  = str(e)
                failed      += 1
            except Exception as e:
                res.passed   = False
                res.message  = f"{type(e).__name__}: {e}"
                res.error    = traceback.format_exc()
                failed      += 1
            finally:
                res.duration = time.perf_counter() - t0

            results.append(res)
            if verbose:
                print(res)

    print(f"\n{'━'*55}")
    icon = '✅' if failed == 0 else '❌'
    print(f"  {icon}  Results: {passed}/{total} passed  |  {failed} failed")
    print(f"{'━'*55}\n")

    return {
        'total'  : total,
        'passed' : passed,
        'failed' : failed,
        'results': results,
    }


# ---------------------------------------------------------------------------
# Quick Test Utility (for single node ad-hoc testing)
# ---------------------------------------------------------------------------

def test_node(node, input_data, expected_type=None, label=''):
    """
    Quick one-liner to test a single node.

    Example:
        from core.testing import test_node, MockRequest
        from nodes.url_node import URLNode

        result = test_node(
            URLNode('/home'),
            MockRequest(path='/home'),
            expected_type=dict,
            label='URL match test'
        )
    """
    t0   = time.perf_counter()
    try:
        result = node.process(input_data)
        ms     = (time.perf_counter() - t0) * 1000
        status = '✅'
        msg    = f"returned {type(result).__name__}"
        if expected_type and not isinstance(result, expected_type):
            status = '⚠️'
            msg    = f"expected {expected_type.__name__}, got {type(result).__name__}"
        print(f"  {status}  {label or node._node_name}  →  {msg}  ({ms:.1f}ms)")
        return result
    except Exception as e:
        ms = (time.perf_counter() - t0) * 1000
        print(f"  ❌  {label or node._node_name}  →  {type(e).__name__}: {e}  ({ms:.1f}ms)")
        return None