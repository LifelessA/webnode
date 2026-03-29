# static/helpers.py
from core.db import Database
from core.sessions import get_session_id  # cookie-based session (replaces IP-based)
from core.validators import (
    validate_int,
    validate_str,
    validate_email,
    validate_form,
    safe_int,
    safe_str,
    ValidationError
)

db = Database()

# get_session_id is re-exported here so all existing logic files can still do:
#   from static.helpers import get_session_id, db, compute_cart_totals
# without any changes.
__all__ = ['db', 'get_session_id', 'compute_cart_totals']

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