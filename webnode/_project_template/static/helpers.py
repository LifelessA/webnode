from core.db import Database

db = Database()

def get_session_id(request):
    """Use client IP as session identifier."""
    if hasattr(request, 'handler') and hasattr(request.handler, 'client_address'):
        return f"sess_{request.handler.client_address[0].replace('.', '_')}"
    return 'sess_default'

def compute_cart_totals(cart_items):
    subtotal_raw = sum(item['price'] * item['quantity'] for item in cart_items)
    shipping     = 0.0 if subtotal_raw >= 50.0 else 5.99
    tax          = round(subtotal_raw * 0.08, 2)
    total        = round(subtotal_raw + shipping + tax, 2)
    # Add subtotal per line
    for item in cart_items:
        item['subtotal'] = f"{item['price'] * item['quantity']:.2f}"
    return {
        'subtotal':     f"{subtotal_raw:.2f}",
        'subtotal_raw': subtotal_raw,
        'tax':          f"{tax:.2f}",
        'total':        f"{total:.2f}",
        'total_raw':    total,
        'item_count':   sum(item['quantity'] for item in cart_items),
    }
