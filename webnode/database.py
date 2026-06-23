import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'database.sqlite3')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def query_db(query, args=(), one=False):
    """
    Executes a SELECT query and returns the results as a list of dictionaries.
    If one=True, returns a single dictionary.
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(query, args)
        rv = [dict((cur.description[i][0], value) for i, value in enumerate(row)) for row in cur.fetchall()]
        return (rv[0] if rv else None) if one else rv
    except Exception as e:
        print(f"Database Query Error: {e}")
        return None
    finally:
        conn.close()

def execute_db(query, args=()):
    """
    Executes an INSERT/UPDATE/DELETE query.
    Returns the rowcount (number of affected rows).
    """
    conn = get_db()
    cur = conn.cursor()
    try:
        cur.execute(query, args)
        conn.commit()
        return cur.rowcount
    except Exception as e:
        print(f"Database Execute Error: {e}")
        conn.rollback()
        return -1
    finally:
        conn.close()

def reset_db():
    """
    Deletes the database file to completely reset the database.
    """
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            return True
        except Exception as e:
            print(f"Database Reset Error: {e}")
            return False
    return True
