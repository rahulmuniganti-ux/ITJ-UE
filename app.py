```python
from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3, pandas as pd, os

# SAFE IMPORT (prevents crash if parser fails)
try:
    from parser import extract_timetable
except Exception as e:
    print("Parser load error:", e)
    def extract_timetable(x):
        return pd.DataFrame(columns=["DATE","SESSION","BRANCH","SUBJECT"])

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

# Upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database setup (AUTO CREATE TABLES)
def get_db():
    conn = sqlite3.connect(os.path.join(os.getcwd(), "database.db"))
    conn.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT, email TEXT, password TEXT, role TEXT
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS uploads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT, upload_time TEXT
    )""")
    return conn

# HOME
@app.route("/")
def home():
    return "App Running Successfully 🚀"

# REGISTER
@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        conn = get_db()
        conn.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (request.form["name"], request.form["email"], request.form["password"], request.form["role"])
        )
        conn.commit()
        conn.close()
        return "Registered"

    return "Register Page"

# LOGIN
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email=? AND password=?",
            (request.form["email"], request.form["password"])
        ).fetchone()
        conn.close()

        if user:
            session["role"] = user[4]
            return "Login Success"
        else:
            return "Invalid Login"

    return "Login Page"

# UPLOAD
@app.route("/upload", methods=["POST"])
def upload():
    files = request.files.getlist("file")

    if not files:
        return "No files selected"

    conn = get_db()
    merged_df = pd.DataFrame()

    for file in files:
        if file.filename == "":
            continue

        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        try:
            df = extract_timetable(path)
        except Exception as e:
            print("Parser error:", e)
            df = pd.DataFrame()

        if not df.empty:
            merged_df = pd.concat([merged_df, df])

        conn.execute(
            "INSERT INTO uploads(filename,upload_time) VALUES (?,datetime('now'))",
            (file.filename,)
        )

    conn.commit()
    conn.close()

    return "Upload Process Completed"

# EXPORT
@app.route("/export")
def export():
    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM uploads", conn)
    except:
        conn.close()
        return "No data"

    conn.close()

    file_path = "/tmp/output.xlsx"
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)

# RUN
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
```
