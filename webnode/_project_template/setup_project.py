"""
setup_project.py — Node Framework Setup Script
Run this ONCE before starting the server:
    python setup_project.py
"""
import secrets
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SECRET_FILE = os.path.join(BASE_DIR, '.secret_key')
DB_FILE = os.path.join(BASE_DIR, 'db.sqlite3')
LOG_DIR = os.path.join(BASE_DIR, 'core', 'logs')


def generate_secret_key():
    if os.path.exists(SECRET_FILE):
        print("  [skip] Secret key already exists.")
        return
    key = secrets.token_urlsafe(64)
    with open(SECRET_FILE, 'w') as f:
        f.write(key)
    print("  [ok]   Secret key generated → .secret_key")


def create_log_directory():
    os.makedirs(LOG_DIR, exist_ok=True)
    print(f"  [ok]   Log directory ready  → core/logs/")


def create_database():
    import sqlite3
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.close()
    print(f"  [ok]   Database initialized → db.sqlite3")


def setup_all():
    print("\n🚀 Node Framework — Project Setup")
    print("=" * 45)
    generate_secret_key()
    create_log_directory()
    create_database()
    print("=" * 45)
    print("✅  Setup complete! Run: python main.py\n")


if __name__ == "__main__":
    setup_all()
