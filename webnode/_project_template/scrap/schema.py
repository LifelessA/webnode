import sqlite3
import os

DB_PATH = os.path.join(r'c:\Users\lifel\Downloads\framework', 'database.sqlite3')
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT type, name, sql FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()

for t_type, t_name, t_sql in tables:
    print(f'Table: {t_name}')
    print(f'SQL: {t_sql}\n')
