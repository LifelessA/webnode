from static.helpers import db, get_session_id

def home_logic(req):
    category    = req.query_params.get('cat', '')
    session_id  = get_session_id(req)
    if category:
        products = db.fetchall(
            "SELECT * FROM products WHERE category=? ORDER BY id",
            (category,)
        )
    else:
        products = db.fetchall("SELECT * FROM products ORDER BY id")
    product_count = db.fetchall("SELECT COUNT(*) as cnt FROM products")[0]['cnt']
    cart_count_row = db.fetchall(
        "SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE session_id=?",
        (session_id,)
    )
    return {
        'products':         products,
        'product_count':    product_count,
        'current_category': category,
        'cart_count':       cart_count_row[0]['cnt'],
        'csrf_token':       req.context.get('csrf_token', ''),
    }

def product_detail_logic(req):
    pid        = req.get_param('id') or req.url_params.get('id', 0)
    session_id = get_session_id(req)
    rows       = db.fetchall("SELECT * FROM products WHERE id=?", (int(pid),))
    if not rows:
        return {'product_name': 'Not Found', 'product_id': 0, 'product_price': '0',
                'product_description': '', 'product_image': '', 'product_category': '',
                'cart_count': 0, 'csrf_token': ''}
    p = rows[0]
    cart_count_row = db.fetchall(
        "SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE session_id=?",
        (session_id,)
    )
    return {
        'product_id':          p['id'],
        'product_name':        p['name'],
        'product_price':       f"{p['price']:.2f}",
        'product_description': p['description'],
        'product_image':       p['image_url'],
        'product_category':    p['category'],
        'cart_count':          cart_count_row[0]['cnt'],
        'csrf_token':          req.context.get('csrf_token', ''),
    }