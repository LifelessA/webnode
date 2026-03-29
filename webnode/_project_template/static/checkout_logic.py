import urllib.parse
from nodes.response import Response
from static.helpers import db, get_session_id, compute_cart_totals

def checkout_logic(req):
    session_id = get_session_id(req)
    cart_items = db.fetchall("""
        SELECT c.id as cart_id, c.quantity, p.name, p.price, p.image_url, p.category
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.session_id = ?
        ORDER BY c.id
    """, (session_id,))
    if not cart_items:
        return Response.redirect('/cart')
    totals = compute_cart_totals(cart_items)
    totals.update({
        'cart_items':  cart_items,
        'cart_count':  totals['item_count'],
        'csrf_token':  req.context.get('csrf_token', ''),
        'flash_error': req.query_params.get('error', ''),
    })
    return totals


def checkout_place_logic(req):
    session_id = get_session_id(req)
    name       = req.get_param('name', '').strip()
    email      = req.get_param('email', '').strip()
    address    = req.get_param('address', '').strip()
    phone      = req.get_param('phone', '').strip()

    if not name or not email or not address:
        return Response.redirect('/checkout?error=Please+fill+all+required+fields')

    # Get cart items
    cart_items = db.fetchall("""
        SELECT c.id as cart_id, c.quantity, p.id as product_id, p.name, p.price
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.session_id = ?
    """, (session_id,))

    if not cart_items:
        return Response.redirect('/cart?error=Cart+is+empty')

    totals = compute_cart_totals(cart_items)
    total  = totals['total_raw']

    # Insert order
    db.execute(
        "INSERT INTO orders (session_id, name, email, address, phone, total) VALUES (?,?,?,?,?,?)",
        (session_id, name, email, address, phone, total)
    )
    # Get the order id
    order_row = db.fetchall("SELECT id FROM orders WHERE session_id=? ORDER BY id DESC LIMIT 1", (session_id,))
    order_id  = order_row[0]['id'] if order_row else '??'

    # Insert order items
    items_data = [(order_id, item['product_id'], item['quantity'], item['price']) for item in cart_items]
    db.executemany(
        "INSERT INTO order_items (order_id, product_id, quantity, unit_price) VALUES (?,?,?,?)",
        items_data
    )

    # Clear the cart
    db.execute("DELETE FROM cart WHERE session_id=?", (session_id,))

    # Store order info in context for redirect
    name_enc    = urllib.parse.quote(name)
    email_enc   = urllib.parse.quote(email)
    addr_enc    = urllib.parse.quote(address)
    total_enc   = urllib.parse.quote(f"{total:.2f}")
    return Response.redirect(
        f'/order/success?order_id={order_id}&name={name_enc}'
        f'&email={email_enc}&address={addr_enc}&total={total_enc}'
    )


def order_success_logic(req):
    session_id = get_session_id(req)
    order_id   = req.query_params.get('order_id', '???')
    name       = req.query_params.get('name', 'Customer')
    email      = req.query_params.get('email', '')
    address    = req.query_params.get('address', '')
    total      = req.query_params.get('total', '0.00')
    return {
        'order_id':         order_id,
        'customer_name':    name,
        'customer_email':   email,
        'customer_address': address,
        'order_total':      total,
        'cart_count':       0,
        'csrf_token':       req.context.get('csrf_token', ''),
    }