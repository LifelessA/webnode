from static.helpers import db

def process_logic(req):
    # Initialize products table
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            image_url TEXT,
            description TEXT
        )""")
        sample_products = [
            {"name": "ProRunner Shoes", "price": 129.99, "image_url": "https://images.unsplash.com/photo-1542291026-7eec264c27ea?w=600&q=80"},
            {"name": "UltraSmart Watch", "price": 249.00, "image_url": "https://images.unsplash.com/photo-1523293182092-99047b3c5e0f?w=600&q=80"},
            {"name": "SoundPulse Headphones", "price": 199.50, "image_url": "https://images.unsplash.com/photo-1512295767273-ac4ee89f5b13?w=600&q=80"},
            {"name": "TurboPhone X", "price": 799.00, "image_url": "https://images.unsplash.com/photo-1511467687858-23d96c6b5e0c?w=600&q=80"}
        ]
        for prod in sample_products:
            # Insert only if a product with the same name does not already exist
            db.execute(
                "INSERT OR IGNORE INTO products (name, price, image_url) VALUES (?, ?, ?)",
                (prod["name"], prod["price"], prod["image_url"])
            )
    except Exception as e:
        # Log or handle initialization errors silently in production
        pass

from static.helpers import db

def process_logic(req):
    rows = db.fetchall("SELECT id, name, price, image_url FROM products")
    product_list = []
    for row in rows:
        product_list.append({
            "id": row["id"],
            "name": row["name"],
            "price": row["price"],
          “image”: row[\"image_url\"]   # note: quoting uses Unicode straight double quotes
        })
    return {"products": product_list}

from static.helpers import db
import json

def process_logic(req):
    # Expect a JSON body with product_id and quantity
    data = req.get_json() if hasattr(req, "get_json") else {}
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not product_id or quantity <= 0:
        return {"error": "Invalid payload"}

    # Ensure the cart table exists (simple in-memory session would be used in production)
    db.execute("""CREATE TABLE IF NOT EXISTS cart (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        product_id INTEGER NOT NULL,
        quantity INTEGER NOT NULL
    )""")

    existing = db.fetchone("SELECT quantity FROM cart WHERE product_id = ?", (product_id,))
    if existing:
        new_qty = existing["quantity"] + quantity
        db.execute("UPDATE cart SET quantity = ? WHERE product_id = ?", (new_qty, product_id))
    else:
        db.execute("INSERT INTO cart (product_id, quantity) VALUES (?, ?)", (product_id, quantity))

    # Compute total items in cart
    totals = db.fetchone("SELECT SUM(quantity) as total FROM cart")
    total_quantity = totals["total"] if totals and totals["total"] else 0

    return {"cart_total": total_quantity}