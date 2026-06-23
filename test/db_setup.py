"""
db_setup.py — Initialize ECommerce Database Tables
Run once: python db_setup.py
"""
from core.db import Database

db = Database()

schema = """
-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    price REAL NOT NULL,
    image_url TEXT,
    category TEXT DEFAULT 'general',
    stock INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Cart Table  
CREATE TABLE IF NOT EXISTS cart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT,
    name TEXT NOT NULL,
    email TEXT NOT NULL,
    address TEXT NOT NULL,
    phone TEXT,
    total REAL NOT NULL,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);
"""

db.executescript(schema)
print("✅ Tables created successfully.")

# Seed dummy products
existing = db.fetchall("SELECT COUNT(*) as cnt FROM products;")
if existing[0]['cnt'] == 0:
    products = [
        ("Gravity Pro Headphones", "Premium wireless headphones with 40-hour battery and ANC technology. Crystal clear sound with deep bass.", 149.99, "/static/img/headphones.svg", "Electronics"),
        ("NovaPulse Smartwatch", "Track your fitness, get notifications, and look great doing it. 7-day battery life.", 299.99, "/static/img/watch.svg", "Electronics"),
        ("AeroFloat Sneakers", "Lightweight performance sneakers with memory foam insole. Perfect for running or casual wear.", 89.99, "/static/img/sneakers.svg", "Footwear"),
        ("ZenCore Backpack", "Weather-resistant backpack with laptop compartment, USB charging port, and 30L capacity.", 69.99, "/static/img/backpack.svg", "Bags"),
        ("LuminaDesk LED Keyboard", "RGB mechanical keyboard with anti-ghosting, 100% rollover, and customizable macros.", 119.99, "/static/img/keyboard.svg", "Electronics"),
        ("CloudPillow Travel Set", "Memory foam travel pillow + eye mask + earplugs combo for the ultimate travel comfort.", 34.99, "/static/img/pillow.svg", "Travel"),
        ("SolarCharge Power Bank", "20000mAh solar power bank with dual USB-C and fast charging. Works in direct sunlight.", 59.99, "/static/img/powerbank.svg", "Electronics"),
        ("FrostBrew Coffee Maker", "Smart drip coffee maker with app control, built-in grinder, and thermal carafe.", 189.99, "/static/img/coffee.svg", "Kitchen"),
    ]
    db.executemany(
        "INSERT INTO products (name, description, price, image_url, category) VALUES (?,?,?,?,?)",
        products
    )
    print(f"✅ Seeded {len(products)} products.")
else:
    print("ℹ️  Products already seeded.")

print("\n🚀 Database ready. Run: python main.py")
