import sqlite3
conn = sqlite3.connect('database.sqlite3')
print('Settings Schema:', conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='settings'").fetchone()[0])
