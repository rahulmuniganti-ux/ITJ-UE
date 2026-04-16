import sqlite3

conn = sqlite3.connect("database.db")

conn.execute("""

CREATE TABLE IF NOT EXISTS uploads(

id INTEGER PRIMARY KEY AUTOINCREMENT,
filename TEXT,
upload_time TEXT

)

""")

conn.commit()
conn.close()

print("Upload history table created")