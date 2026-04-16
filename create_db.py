import sqlite3

conn = sqlite3.connect("database.db")

conn.execute("""
CREATE TABLE users(
id INTEGER PRIMARY KEY AUTOINCREMENT,
name TEXT,
email TEXT,
password TEXT,
role TEXT,
branch TEXT,
year TEXT,
semester TEXT,
roll TEXT
)
""")

conn.commit()
conn.close()

print("Database created successfully")