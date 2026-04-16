from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3, pandas as pd, os
from werkzeug.security import generate_password_hash, check_password_hash

# ⚠️ Safe import (prevents full crash if parser fails)
try:
    from parser import extract_timetable
except Exception as e:
    print("Parser import error:", e)
    extract_timetable = None


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

# Upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf"}


# ---------------- DB ----------------
def get_db():
    conn = sqlite3.connect(os.path.join(os.getcwd(), "database.db"))

    conn.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS uploads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT,
        upload_time TEXT
    )
    """)

    return conn


# ---------------- FILE CHECK ----------------
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("index.html")


# ---------------- REGISTER ----------------
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        conn = get_db()

        hashed_password = generate_password_hash(request.form["password"])

        conn.execute(
            "INSERT INTO users(name,email,password,role) VALUES(?,?,?,?)",
            (
                request.form["name"],
                request.form["email"],
                hashed_password,
                request.form["role"]
            )
        )

        conn.commit()
        conn.close()

        flash("Registration successful")
        return redirect("/login")

    return render_template("register.html")


# ---------------- LOGIN ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (request.form["email"],)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user[3], request.form["password"]):
            session["role"] = user[4]
            session["user_id"] = user[0]

            flash("Login successful")

            if user[4] == "admin":
                return redirect("/admin_dashboard")
            return redirect("/")
        else:
            flash("Invalid login")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect("/login")
    return render_template("admin_dashboard.html")


# ---------------- UPLOAD ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if session.get("role") != "admin":
        return redirect("/login")

    files = request.files.getlist("file")

    conn = get_db()
    merged_df = pd.DataFrame()

    for file in files:
        if file.filename == "" or not allowed_file(file.filename):
            continue

        path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(path)

        df = pd.DataFrame()

        # safe parser call
        if extract_timetable:
            try:
                df = extract_timetable(path)
            except Exception as e:
                print("Parser error:", e)
                flash(f"Failed to parse {file.filename}")

        if df is not None and not df.empty:
            merged_df = pd.concat([merged_df, df])

        conn.execute(
            "INSERT INTO uploads(filename,upload_time) VALUES (?,datetime('now'))",
            (file.filename,)
        )

    if merged_df.empty:
        conn.close()
        flash("No valid data extracted")
        return redirect("/admin_dashboard")

    merged_df.drop_duplicates(inplace=True)
    merged_df.to_sql("consolidated_timetable", conn, if_exists="replace", index=False)

    conn.commit()
    conn.close()

    flash("Upload successful")
    return redirect("/history")


# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if session.get("role") is None:
        return redirect("/login")

    conn = get_db()
    data = conn.execute("SELECT * FROM uploads").fetchall()
    conn.close()

    return render_template("history.html", data=data)


# ---------------- VIEW TABLE ----------------
@app.route("/view_consolidated")
def view_consolidated():
    if session.get("role") is None:
        return redirect("/login")

    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
    except:
        conn.close()
        flash("No timetable available")
        return redirect("/admin_dashboard")

    conn.close()

    if df.empty:
        flash("No data found")
        return redirect("/admin_dashboard")

    df.columns = [c.strip().upper() for c in df.columns]

    date_col = "DATEOFEXAM" if "DATEOFEXAM" in df.columns else "DATE"

    rows = ""
    for _, row in df.iterrows():
        rows += f"""
        <tr>
            <td>{row.get(date_col,'')}</td>
            <td>{row.get('SUBJECT','')}</td>
            <td>{row.get('BRANCH','')}</td>
        </tr>
        """

    return render_template("timetable.html", table_html=rows)


# ---------------- EXPORT EXCEL ----------------
@app.route("/export_excel")
def export_excel():
    if session.get("role") is None:
        return redirect("/login")

    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
    except:
        conn.close()
        flash("No data available")
        return redirect("/history")

    conn.close()

    file_path = os.path.join("/tmp", "timetable.xlsx")
    df.to_excel(file_path, index=False)

    return send_file(file_path, as_attachment=True)


# ---------------- DELETE ----------------
@app.route("/delete/<filename>")
def delete_file(filename):
    if session.get("role") != "admin":
        return redirect("/login")

    conn = get_db()
    conn.execute("DELETE FROM uploads WHERE filename=?", (filename,))
    conn.commit()
    conn.close()

    path = os.path.join(UPLOAD_FOLDER, filename)
    if os.path.exists(path):
        os.remove(path)

    flash("Deleted successfully")
    return redirect("/history")


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
