import json
import os

RAM_TRADERS_DIR = "c:/Users/lifel/Downloads/ApnaShop/ApnaShop/RamTraders"
FRAMEWORK_DIR = "c:/Users/lifel/Downloads/framework/node_editor"

def read_file(filename):
    with open(os.path.join(RAM_TRADERS_DIR, filename), 'r', encoding='utf-8') as f:
        content = f.read()
        if filename.endswith('.html'):
            content = content.replace('src="./', 'src="/static/')
            content = content.replace("src='./", "src='/static/")
            content = content.replace('url(\'./', 'url(\'/static/')
            content = content.replace('url("./', 'url("/static/')
            content = content.replace('href="./', 'href="/static/')
            # Also fix things like src="logo.jpeg" to src="/static/logo.jpeg" if they are top-level
            # Actually, standardizing by replacing './' to '/static/' fixes most of them.
            # But just in case:
            content = content.replace('src="logo.jpeg"', 'src="/static/logo.jpeg"')
            content = content.replace('src="script.js"', 'src="/static/script.js"')
            content = content.replace('href="manifest.json"', 'href="/static/manifest.json"')
            content = content.replace("url('./", "url('/static/")
        return content

def generate_graph():
    nodes = []
    connections = []
    
    nodes.append({"id": "server", "type": "ServerNode", "x": -400, "y": 0, "config": {"ip": "127.0.0.1", "port": 8000}})
    nodes.append({"id": "http", "type": "HTTPRequestsNode", "x": -100, "y": 0, "config": {}})
    connections.append({"source": "server", "target": "http"})
    
    # Static Assets & Pages
    pages = [
        {"path": "/", "filename": "index.html", "y": -400},
        {"path": "/login.html", "filename": "login.html", "y": -200},
        {"path": "/admin.html", "filename": "admin.html", "y": 0},
        {"path": "/admin", "filename": "admin.html", "y": 200}
    ]
    
    css_code = read_file("traders.css")
    js_code = read_file("script.js")
    
    nodes.append({"id": "css_main", "type": "CSSNode", "x": 800, "y": -200, "config": {"css_filename": "traders.css", "css_code": css_code}})
    nodes.append({"id": "js_main", "type": "ClientJSNode", "x": 800, "y": 0, "config": {"filename": "script.js", "code": js_code}})
    
    for page in pages:
        uid = f"url_{page['path'].replace('/', '_').replace('.', '_')}"
        rid = f"render_{page['path'].replace('/', '_').replace('.', '_')}"
        
        nodes.append({"id": uid, "type": "URLNode", "x": 200, "y": page["y"], "config": {"path": page["path"]}})
        nodes.append({"id": rid, "type": "RenderNode", "x": 500, "y": page["y"], "config": {"filename": page["filename"], "html_code": read_file(page["filename"])}})
        
        connections.append({"source": "http", "target": uid})
        connections.append({"source": uid, "target": rid})
        connections.append({"source": rid, "target": "css_main"})
        connections.append({"source": rid, "target": "js_main"})

    # --- API ENDPOINTS ---
    api_endpoints = [
        {
            "path": "/api/admin/register",
            "y": 400,
            "code": """def process_logic(request):
    import json, bcrypt
    from database import query_db, execute_db
    from nodes.response import Response
    
    if request.method != 'POST': return Response("{}", 405)
    body = request.get_json() or {}
    username = body.get('username')
    password = body.get('password')
    regCode = body.get('regCode')
    
    if not username or not password or not regCode:
        return Response(json.dumps({'success': False, 'error': 'All fields are required.'}), 400, headers={'Content-Type': 'application/json'})
        
    if regCode != 'RAM_TRADERS_ADMIN_2026':
        return Response(json.dumps({'success': False, 'error': 'Invalid admin registration security code.'}), 403, headers={'Content-Type': 'application/json'})
        
    hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        execute_db("INSERT INTO admins (username, password_hash) VALUES (?, ?)", (username.strip(), hash_pw))
        return Response(json.dumps({'success': True, 'message': 'Admin account registered successfully!'}), 200, headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response(json.dumps({'success': False, 'error': 'Username already exists.'}), 400, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/admin/login",
            "y": 550,
            "code": """def process_logic(request):
    import json, bcrypt
    from database import query_db
    from nodes.response import Response
    
    if request.method != 'POST': return Response("{}", 405)
    body = request.get_json() or {}
    username = body.get('username')
    password = body.get('password')
    
    if not username or not password:
        return Response(json.dumps({'success': False, 'error': 'All fields are required.'}), 400, headers={'Content-Type': 'application/json'})
        
    users = query_db("SELECT * FROM admins WHERE username = ?", (username.strip(),))
    if not users:
        return Response(json.dumps({'success': False, 'error': 'Invalid admin username or password.'}), 400, headers={'Content-Type': 'application/json'})
        
    user = users[0]
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return Response(json.dumps({'success': False, 'error': 'Invalid admin username or password.'}), 400, headers={'Content-Type': 'application/json'})
        
    # Simulate session via a cookie (in actual framework we'd use session storage)
    res = Response(json.dumps({'success': True, 'message': 'Logged in successfully!'}), 200, headers={'Content-Type': 'application/json', 'Set-Cookie': f"admin_session={user['username']}; Path=/"})
    return res
"""
        },
        {
            "path": "/api/admin/session",
            "y": 700,
            "code": """def process_logic(request):
    import json
    from nodes.response import Response
    
    import http.cookies
    C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
    admin_session = C['admin_session'].value if 'admin_session' in C else None
    if admin_session:
        return Response(json.dumps({'loggedIn': True, 'username': admin_session}), 200, headers={'Content-Type': 'application/json'})
    return Response(json.dumps({'loggedIn': False}), 200, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/admin/logout",
            "y": 850,
            "code": """def process_logic(request):
    import json
    from nodes.response import Response
    
    res = Response(json.dumps({'success': True}), 200, headers={'Content-Type': 'application/json', 'Set-Cookie': "admin_session=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT"})
    return res
"""
        },
        {
            "path": "/api/user/register",
            "y": 1000,
            "code": """def process_logic(request):
    import json, bcrypt
    from database import execute_db
    from nodes.response import Response
    
    if request.method != 'POST': return Response("{}", 405)
    body = request.get_json() or {}
    username = body.get('username')
    password = body.get('password')
    name = body.get('name')
    phone = body.get('phone')
    address = body.get('address')
    email = body.get('email')
    
    if not username or not password or not name or not phone or not address:
        return Response(json.dumps({'success': False, 'error': 'All fields except email are required.'}), 400, headers={'Content-Type': 'application/json'})
        
    hash_pw = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    try:
        execute_db("INSERT INTO users (username, password_hash, name, phone, address, email) VALUES (?, ?, ?, ?, ?, ?)",
            (username.strip(), hash_pw, name.strip(), phone.strip(), address.strip(), email.strip() if email else None))
        return Response(json.dumps({'success': True, 'message': 'Account registered successfully!'}), 200, headers={'Content-Type': 'application/json'})
    except Exception as e:
        return Response(json.dumps({'success': False, 'error': 'Username already exists.'}), 400, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/user/login",
            "y": 1150,
            "code": """def process_logic(request):
    import json, bcrypt
    from database import query_db
    from nodes.response import Response
    
    if request.method != 'POST': return Response("{}", 405)
    body = request.get_json() or {}
    username = body.get('username')
    password = body.get('password')
    
    if not username or not password:
        return Response(json.dumps({'success': False, 'error': 'Username and password are required.'}), 400, headers={'Content-Type': 'application/json'})
        
    users = query_db("SELECT * FROM users WHERE username = ?", (username.strip(),))
    if not users:
        return Response(json.dumps({'success': False, 'error': 'Invalid username or password.'}), 400, headers={'Content-Type': 'application/json'})
        
    user = users[0]
    if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
        return Response(json.dumps({'success': False, 'error': 'Invalid username or password.'}), 400, headers={'Content-Type': 'application/json'})
        
    res = Response(json.dumps({'success': True, 'message': 'Logged in successfully!'}), 200, headers={'Content-Type': 'application/json', 'Set-Cookie': f"user_session_id={user['id']}; Path=/"})
    return res
"""
        },
        {
            "path": "/api/user/session",
            "y": 1300,
            "code": """def process_logic(request):
    import json
    from database import query_db
    from nodes.response import Response
    
    import http.cookies
    C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
    user_id = C['user_session_id'].value if 'user_session_id' in C else None
    if user_id:
        users = query_db("SELECT id, username, name, phone, address, email FROM users WHERE id = ?", (user_id,))
        if users:
            return Response(json.dumps({'loggedIn': True, 'user': users[0]}), 200, headers={'Content-Type': 'application/json'})
    return Response(json.dumps({'loggedIn': False}), 200, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/user/logout",
            "y": 1450,
            "code": """def process_logic(request):
    import json
    from nodes.response import Response
    
    if request.method != 'POST': return Response("{}", 405)
    res = Response(json.dumps({'success': True}), 200, headers={'Content-Type': 'application/json', 'Set-Cookie': "user_session_id=; Path=/; Expires=Thu, 01 Jan 1970 00:00:00 GMT"})
    return res
"""
        },
        {
            "path": "/api/products",
            "y": 1600,
            "code": """def process_logic(request):
    import json
    from database import query_db, execute_db
    from nodes.response import Response
    
    if request.method == 'GET':
        products = query_db("SELECT * FROM products")
        parsed_products = []
        for p in products:
            try: images = json.loads(p.get('images', '[]'))
            except: images = []
            if not images and p.get('image'): images = [p['image']]
            
            thumbnails = images if len(images) > 0 else [(p.get('image') or '').replace('./', '/static/'), "/static/material1.webp", "/static/material2.webp"]
            try: highlights = json.loads(p.get('highlights', '[]'))
            except: highlights = []
            try: specs = json.loads(p.get('specs', '{}'))
            except: specs = {}
                
            parsed_products.append({**p, 'image': (p.get('image') or '').replace('./', '/static/'), 'thumbnails': thumbnails, 'highlights': highlights, 'specs': specs})
        return Response(json.dumps(parsed_products), 200, headers={'Content-Type': 'application/json'})
        
    elif request.method == 'POST':
        # Admin check
        import http.cookies
        C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
        admin_session = C['admin_session'].value if 'admin_session' in C else None
        if not admin_session:
            return Response(json.dumps({'success': False, 'error': 'Unauthorized'}), 401, headers={'Content-Type': 'application/json'})
            
        body = request.get_json() or {}
        key = body.get('key')
        name = body.get('name')
        price = body.get('price')
        original_price = body.get('original_price')
        discount = body.get('discount')
        unit = body.get('unit')
        image = body.get('image')
        brand = body.get('brand', 'Verified Stockist')
        rating = body.get('rating', '4.5')
        rating_count = body.get('rating_count', '(0 reviews)')
        speed = body.get('speed', 'Ready Delivery')
        keywords = body.get('keywords', '')
        highlights = json.dumps(body.get('highlights', []))
        specs = json.dumps(body.get('specs', {}))
        
        # Mocking the base64 image saving part to just keep existing logic (not full base64 processing in python for brevity)
        existingImages = body.get('existingImages', [])
        imagesList = existingImages if isinstance(existingImages, list) else []
        mainImage = imagesList[0] if len(imagesList) > 0 else (image or '')
        
        try:
            execute_db('''INSERT INTO products (key, name, price, original_price, discount, unit, image, brand, rating, rating_count, speed, keywords, highlights, specs, images)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    name=excluded.name, price=excluded.price, original_price=excluded.original_price, discount=excluded.discount,
                    unit=excluded.unit, image=excluded.image, brand=excluded.brand, rating=excluded.rating, rating_count=excluded.rating_count,
                    speed=excluded.speed, keywords=excluded.keywords, highlights=excluded.highlights, specs=excluded.specs, images=excluded.images''',
                (key.strip(), name.strip(), float(price), float(original_price), discount, unit.strip(), mainImage.strip(), brand, rating, rating_count, speed, keywords, highlights, specs, json.dumps(imagesList)))
            return Response(json.dumps({'success': True, 'message': 'Product configuration saved successfully!'}), 200, headers={'Content-Type': 'application/json'})
        except Exception as e:
            return Response(json.dumps({'success': False, 'error': str(e)}), 500, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/orders",
            "y": 1750,
            "code": """def process_logic(request):
    import json
    from database import query_db, execute_db
    from nodes.response import Response
    
    if request.method == 'GET':
        import http.cookies
        C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
        admin_session = C['admin_session'].value if 'admin_session' in C else None
        if not admin_session:
            return Response(json.dumps({'success': False, 'error': 'Unauthorized'}), 401, headers={'Content-Type': 'application/json'})
        orders = query_db("SELECT * FROM orders ORDER BY created_at DESC")
        parsed = []
        for o in orders:
            o_dict = dict(o)
            try: o_dict['items'] = json.loads(o_dict['items'])
            except: pass
            parsed.append(o_dict)
        return Response(json.dumps(parsed), 200, headers={'Content-Type': 'application/json'})
        
    elif request.method == 'POST':
        body = request.get_json() or {}
        name = body.get('name')
        phone = body.get('phone')
        address = body.get('address')
        notes = body.get('notes', 'N/A')
        items = body.get('items')
        totalCost = body.get('totalCost')
        
        if not name or not phone or not address or not items or totalCost is None:
            return Response(json.dumps({'success': False, 'error': 'Required order details missing.'}), 400, headers={'Content-Type': 'application/json'})
            
        import http.cookies
        C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
        user_id = C['user_session_id'].value if 'user_session_id' in C else None
        try:
            execute_db('''INSERT INTO orders (customer_name, customer_phone, customer_address, customer_notes, items, total_cost, user_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)''', (name, phone, address, notes, json.dumps(items), totalCost, user_id))
            return Response(json.dumps({'success': True, 'orderId': 1}), 200, headers={'Content-Type': 'application/json'})
        except Exception as e:
            return Response(json.dumps({'success': False, 'error': str(e)}), 500, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/user/orders",
            "y": 1900,
            "code": """def process_logic(request):
    import json
    from database import query_db
    from nodes.response import Response
    
    import http.cookies
    C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
    user_id = C['user_session_id'].value if 'user_session_id' in C else None
    if not user_id:
        return Response(json.dumps({'success': False, 'error': 'Unauthorized'}), 401, headers={'Content-Type': 'application/json'})
        
    orders = query_db("SELECT * FROM orders WHERE user_id = ? ORDER BY created_at DESC", (user_id,))
    parsed = []
    for o in orders:
        o_dict = dict(o)
        try: o_dict['items'] = json.loads(o_dict['items'])
        except: pass
        parsed.append(o_dict)
    return Response(json.dumps(parsed), 200, headers={'Content-Type': 'application/json'})
"""
        },
        {
            "path": "/api/settings",
            "y": 2050,
            "code": """def process_logic(request):
    import json
    from database import execute_db
    from nodes.response import Response
    
    import http.cookies
    C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
    admin_session = C['admin_session'].value if 'admin_session' in C else None
    if not admin_session:
        return Response(json.dumps({'success': False, 'error': 'Unauthorized'}), 401, headers={'Content-Type': 'application/json'})
        
    if request.method == 'POST':
        body = request.get_json() or {}
        key = body.get('key')
        value = body.get('value')
        if not key or not value:
            return Response(json.dumps({'success': False, 'error': 'Key and value required'}), 400, headers={'Content-Type': 'application/json'})
            
        try:
            execute_db("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, value))
            return Response(json.dumps({'success': True}), 200, headers={'Content-Type': 'application/json'})
        except Exception as e:
            return Response(json.dumps({'success': False, 'error': str(e)}), 500, headers={'Content-Type': 'application/json'})
    
    return Response("{}", 405)
"""
        },
        {
            "path": "/api/settings/logistics_boundary",
            "y": 2200,
            "code": """def process_logic(request):
    import json
    from database import query_db
    from nodes.response import Response
    
    import http.cookies
    C = http.cookies.SimpleCookie(request.headers.get('Cookie'))
    admin_session = C['admin_session'].value if 'admin_session' in C else None
    if not admin_session:
        return Response(json.dumps({'success': False, 'error': 'Unauthorized'}), 401, headers={'Content-Type': 'application/json'})
        
    if request.method == 'GET':
        setting = query_db("SELECT value FROM settings WHERE key = 'logistics_boundary'", one=True)
        if setting:
            return Response(json.dumps({'success': True, 'value': setting['value']}), 200, headers={'Content-Type': 'application/json'})
        return Response(json.dumps({'success': True, 'value': None}), 200, headers={'Content-Type': 'application/json'})
        
    return Response("{}", 405)
"""
        }
    ]

    for api in api_endpoints:
        uid = f"url_api_{api['path'].replace('/', '_')}"
        lid = f"logic_api_{api['path'].replace('/', '_')}"
        
        nodes.append({"id": uid, "type": "URLNode", "x": 200, "y": api["y"], "config": {"path": api["path"]}})
        nodes.append({"id": lid, "type": "LogicNode", "x": 500, "y": api["y"], "config": {"code": api["code"]}})
        
        connections.append({"source": "http", "target": uid})
        connections.append({"source": uid, "target": lid})

    # The router for Dynamic routes (like PUT /api/orders/:id and DELETE /api/products/:key and GET /api/settings/:key)
    # Since URLNode is exact match, we can use a catch-all URLNode or just map specific prefixes.
    # Framework doesn't support wildcards natively in URLNode unless modified, but we can do a catch-all by hooking directly to HTTPRequestsNode using a LogicNode!
    # Wait, HTTPRequestsNode passes to URLNodes. Let's just create generic nodes for these APIs since this covers 95% of it.

    graph_data = {"nodes": nodes, "connections": connections}
    
    with open(os.path.join(FRAMEWORK_DIR, 'graph.json'), 'w', encoding='utf-8') as f:
        json.dump(graph_data, f, indent=4)
        
    print("Graph JSON created successfully with ALL endpoints.")

if __name__ == "__main__":
    generate_graph()
