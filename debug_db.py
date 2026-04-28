import sqlite3
import os

DB_PATH = os.path.join("database", "unisphere.db")

print("Using DB:", DB_PATH)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("\n=== USERS TABLE ===")
rows = cursor.execute("SELECT * FROM users").fetchall()

if len(rows) == 0:
    print("NO DATA FOUND - DB NOT INITIALIZED PROPERLY")
else:
    for row in rows:
        print(row)

conn.close()