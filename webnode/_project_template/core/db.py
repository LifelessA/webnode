import sqlite3
import threading
import os
import settings
from contextlib import contextmanager


class Database:
    """
    Thread-safe SQLite database wrapper using threading.local() for connections.

    Each thread gets its OWN persistent connection — created once, reused forever:
        - WAL mode + foreign keys configured ONCE per thread connection
        - No check_same_thread=False (removed — safe by design now)
        - No conn.close() in hot-path methods (execute/fetchall)
        - rollback() on errors to maintain consistent state
        - Singleton so all logic files share the same Database object

    Thread lifecycle:
        Thread starts → first query → get_connection() creates conn → stored in _local.conn
        Thread ends   → Python GC closes connection automatically
        (or call close_connection() explicitly for clean shutdown)
    """

    _instance = None
    _local    = threading.local()   # Each thread gets its own namespace

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_path = os.path.join(settings.BASE_DIR, 'db.sqlite3')
            cls._instance.setup_tables()
        return cls._instance

    # ------------------------------------------------------------------
    # Connection Management
    # ------------------------------------------------------------------

    def get_connection(self) -> sqlite3.Connection:
        """
        Return this thread's persistent connection, creating it if needed.
        Configuration (WAL, foreign keys, row_factory) is applied ONCE.
        """
        # Check if connection exists AND is still alive
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            # Verify connection is alive
            try:
                self._local.conn.execute("SELECT 1")
                # Connection is good!
                return self._local.conn
            except Exception:
                # Connection is stale/broken
                # Close it safely
                try:
                    self._local.conn.close()
                except Exception:
                    pass
                self._local.conn = None
                # Fall through to create new
                
        # Create fresh connection
        conn = sqlite3.connect(
            self.db_path,
            check_same_thread=True,
            timeout=30,
        )
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        self._local.conn = conn
        return self._local.conn

    def close_connection(self):
        """
        Explicitly close this thread's connection.
        Call after a request ends if running in a threaded server.
        """
        if hasattr(self._local, 'conn') and self._local.conn is not None:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    # ------------------------------------------------------------------
    # Core Query Methods (use persistent thread-local connection)
    # ------------------------------------------------------------------

    def execute(self, query, params=()):
        """
        Execute a write query (INSERT / UPDATE / DELETE / DDL).
        Uses the thread's persistent connection — does NOT close it.
        Rolls back on error.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return cursor
        except Exception as e:
            conn.rollback()
            
            # Check if connection error
            # If yes → retry ONCE with fresh connection
            err_str = str(e).lower()
            if any(x in err_str for x in ['closed', 'disk i/o', 'unable to open', 'locked']):
                print(f"[DB] Connection error, reconnecting: {e}")
                # Force new connection
                self._local.conn = None
                try:
                    conn2 = self.get_connection()
                    cursor2 = conn2.cursor()
                    cursor2.execute(query, params)
                    conn2.commit()
                    return cursor2
                except Exception as e2:
                    print(f"[DB] Retry failed: {e2}")
                    raise e2
            
            print(f"Database Error: {e}")
            raise e

    def executemany(self, query, params_list):
        """Bulk insert/update optimization. Uses persistent connection."""
        conn = self.get_connection()
        try:
            conn.executemany(query, params_list)
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Database Error (Bulk): {e}")
            raise e

    def executescript(self, script):
        """
        Run a raw SQL script (good for migrations/DDL/triggers).
        Uses a temporary dedicated connection because executescript()
        auto-commits and cannot run inside an existing transaction.
        """
        conn = sqlite3.connect(self.db_path, timeout=30)
        try:
            conn.executescript(script)
        except Exception as e:
            print(f"Database Error (Script): {e}")
            raise e
        finally:
            conn.close()  # Temporary connection — always close

    def fetchall(self, query, params=()):
        """
        Execute a SELECT and return a list of dicts.
        Uses the thread's persistent connection — does NOT close it.
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            # Same retry logic
            err_str = str(e).lower()
            if any(x in err_str for x in ['closed', 'disk i/o', 'unable to open', 'locked']):
                print(f"[DB] Connection error, reconnecting: {e}")
                self._local.conn = None
                try:
                    conn2 = self.get_connection()
                    cursor2 = conn2.cursor()
                    cursor2.execute(query, params)
                    return [dict(row) for row in cursor2.fetchall()]
                except Exception as e2:
                    print(f"[DB] Retry failed: {e2}")
                    return []
            
            print(f"Database Error: {e}")
            return []

    # ------------------------------------------------------------------
    # Transaction Context Manager
    # ------------------------------------------------------------------

    @contextmanager
    def transaction(self):
        """
        Atomic transaction context manager.

        Usage:
            with db.transaction() as conn:
                conn.execute(q1, params1)
                conn.execute(q2, params2)
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            print(f"Transaction Rolled Back: {e}")
            raise e
        # No conn.close() — thread keeps its connection

    # ------------------------------------------------------------------
    # Utility — Stored Procedure / Function Registration
    # ------------------------------------------------------------------

    def register_function(self, conn, name, num_params, func):
        """
        Registers a Python function as a SQL scalar function.
        Usage in SQL: SELECT my_func(col) FROM table
        """
        conn.create_function(name, num_params, func)

    # ------------------------------------------------------------------
    # DDL Convenience Methods
    # ------------------------------------------------------------------

    def setup_tables(self):
        create_schema = '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_premium BOOLEAN DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS highscores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            score INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''
        self.executescript(create_schema)

        create_trigger = '''
        CREATE TRIGGER IF NOT EXISTS validate_email_suffix
        BEFORE INSERT ON users
        BEGIN
            SELECT
            CASE
                WHEN NEW.email NOT LIKE '%@%' THEN
                RAISE (ABORT, 'Invalid email address')
            END;
        END;
        '''
        self.executescript(create_trigger)

    def create_table(self, table_name, columns_def):
        """Creates a table if it doesn't exist. columns_def: 'id INTEGER PRIMARY KEY, name TEXT'"""
        self.execute(f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_def});")

    def alter_table(self, table_name, operation, details):
        """Alters a table. operation: 'ADD' or 'RENAME'. details: column definition."""
        op = operation.upper()
        if op == 'ADD':
            self.execute(f"ALTER TABLE {table_name} ADD {details};")
        elif op == 'RENAME':
            self.execute(f"ALTER TABLE {table_name} RENAME TO {details};")
        else:
            raise ValueError(f"Unsupported ALTER operation: {operation}")

    def drop_table(self, table_name):
        """Drops a table if it exists."""
        self.execute(f"DROP TABLE IF EXISTS {table_name};")

    def create_view(self, view_name, select_query):
        """Creates a view."""
        self.execute(f"CREATE VIEW IF NOT EXISTS {view_name} AS {select_query};")

    def drop_view(self, view_name):
        """Drops a view."""
        self.execute(f"DROP VIEW IF EXISTS {view_name};")

    def create_index(self, index_name, table_name, columns, unique=False):
        """Creates an index."""
        unique_clause = "UNIQUE" if unique else ""
        self.execute(
            f"CREATE {unique_clause} INDEX IF NOT EXISTS {index_name} "
            f"ON {table_name} ({columns});"
        )