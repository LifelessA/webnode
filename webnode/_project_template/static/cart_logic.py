import urllib.parse
from nodes.response import Response
from static.helpers import db, get_session_id, compute_cart_totals

def cart_logic(req):
    session_id = get_session_id(req)
    cart_items = db.fetchall("""
        SELECT c.id as cart_id, c.quantity, p.name, p.price, p.image_url, p.category
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.session_id = ?
        ORDER BY c.id
    """, (session_id,))
    totals = compute_cart_totals(cart_items)
    flash_success = req.query_params.get('added', '')
    flash_name = req.query_params.get('name', '')
    totals.update({
        'cart_items':    cart_items,
        'cart_count':    totals['item_count'],
        'csrf_token':    req.context.get('csrf_token', ''),
        'flash_success': f"'{flash_name}' added to cart!" if flash_success else '',
        'flash_error':   '',
    })
    return totals

def cart_add_logic(req):
    session_id = get_session_id(req)
    product_id = req.get_param('product_id')
    quantity   = int(req.get_param('quantity') or 1)
    if not product_id:
        return Response.redirect('/cart')
    product_id = int(product_id)
    # Check if product exists
    rows = db.fetchall("SELECT * FROM products WHERE id=?", (product_id,))
    if not rows:
        return Response.redirect('/cart')
    product = rows[0]
    # Check if already in cart (same session)
    existing = db.fetchall(
        "SELECT id, quantity FROM cart WHERE session_id=? AND product_id=?",
        (session_id, product_id)
    )
    if existing:
        new_qty = existing[0]['quantity'] + quantity
        db.execute("UPDATE cart SET quantity=? WHERE id=?", (new_qty, existing[0]['id']))
    else:
        db.execute(
            "INSERT INTO cart (session_id, product_id, quantity) VALUES (?,?,?)",
            (session_id, product_id, quantity)
        )
    # Redirect back with flash message
    name_enc = urllib.parse.quote(product['name'])
    return Response.redirect(f'/cart?added=1&name={name_enc}')

def cart_add_from_shop_logic(req):
    session_id = get_session_id(req)
    product_id = req.get_param('product_id')
    quantity   = int(req.get_param('quantity') or 1)
    
    if not product_id:
        return Response.redirect('/shop')
        
    product_id = int(product_id)
    
    # Check if product exists
    rows = db.fetchall("SELECT * FROM products WHERE id=?", (product_id,))
    if not rows:
        return Response.redirect('/shop')
        
    # Check if already in cart
    existing = db.fetchall(
        "SELECT id, quantity FROM cart WHERE session_id=? AND product_id=?",
        (session_id, product_id)
    )
    
    redirect_url = req.get_param('redirect_url') or '/shop'
    
    if existing:
        new_qty = existing[0]['quantity'] + quantity
        db.execute("UPDATE cart SET quantity=? WHERE id=?", (new_qty, existing[0]['id']))
    else:
        db.execute(
            "INSERT INTO cart (session_id, product_id, quantity) VALUES (?,?,?)",
            (session_id, product_id, quantity)
        )
        
    # Redirect back locally
    return Response.redirect(redirect_url)

def cart_remove_logic(req):
    cart_id = req.get_param('cart_id')
    if cart_id:
        db.execute("DELETE FROM cart WHERE id=?", (int(cart_id),))
    return Response.redirect('/cart')