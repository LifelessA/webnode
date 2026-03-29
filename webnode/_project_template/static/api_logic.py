import json
from nodes.response import Response
from static.helpers import db, get_session_id

def api_cart_add_logic(req):
    session_id = get_session_id(req)
    product_id = req.get_param('product_id')
    quantity   = int(req.get_param('quantity') or 1)
    if not product_id:
        return json.dumps({'error': 'No product_id'})
    product_id = int(product_id)
    rows = db.fetchall("SELECT * FROM products WHERE id=?", (product_id,))
    if not rows:
        return json.dumps({'error': 'Product not found'})
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
    cart_count = db.fetchall(
        "SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE session_id=?",
        (session_id,)
    )[0]['cnt']
    return Response.json({'cart_count': cart_count, 'status': 'added'})


def api_cart_count_logic(req):
    session_id = get_session_id(req)
    cnt = db.fetchall(
        "SELECT COALESCE(SUM(quantity),0) as cnt FROM cart WHERE session_id=?",
        (session_id,)
    )[0]['cnt']
    return Response.json({'count': cnt})