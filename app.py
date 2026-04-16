from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3, pandas as pd, os, re
from parser import extract_timetable

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret")

# Upload folder

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Database connection

def get_db():
return sqlite3.connect(os.path.join(os.getcwd(), "database.db"))

# HOME

@app.route("/")
def home():
return render_template("index.html")

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
flash("Registration successful")
return redirect("/login")
return render_template("register.html")

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

```
    if user:
        session["role"] = user[4]
        flash("Login successful")
        return redirect("/")
    else:
        flash("Invalid login")

return render_template("login.html")
```

# LOGOUT

@app.route("/logout")
def logout():
session.clear()
return redirect("/")

# ADMIN DASHBOARD

@app.route("/admin_dashboard")
def admin_dashboard():
return render_template("admin_dashboard.html")

# MULTI PDF UPLOAD + MERGE

@app.route("/upload", methods=["POST"])
def upload():

```
files = request.files.getlist("file")

if not files:
    flash("Select PDFs")
    return redirect("/admin_dashboard")

conn = get_db()
merged_df = pd.DataFrame()

for file in files:

    if file.filename == "":
        continue

    path = os.path.join(UPLOAD_FOLDER, file.filename)
    file.save(path)

    df = extract_timetable(path)

    if not df.empty:
        merged_df = pd.concat([merged_df, df])

    conn.execute(
        "INSERT INTO uploads(filename,upload_time) VALUES (?,datetime('now'))",
        (file.filename,)
    )

if merged_df.empty:
    flash("No data extracted")
    return redirect("/admin_dashboard")

merged_df.drop_duplicates(inplace=True)
merged_df.to_sql("consolidated_timetable", conn, if_exists="replace", index=False)

conn.commit()
conn.close()

flash("PDFs uploaded & merged successfully")
return redirect("/history")
```

# HISTORY

@app.route("/history")
def history():
conn = get_db()
data = conn.execute("SELECT * FROM uploads").fetchall()
conn.close()
return render_template("history.html", data=data)

# VIEW CONSOLIDATED

@app.route("/view_consolidated")
def view_consolidated():

```
conn = get_db()
df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
conn.close()

if df.empty:
    flash("No data available")
    return redirect("/admin_dashboard")

df.columns = [c.strip().upper() for c in df.columns]

date_col = "DATEOFEXAM" if "DATEOFEXAM" in df.columns else "DATE"
branch_col = "BRANCHCODE" if "BRANCHCODE" in df.columns else "BRANCH"
subject_col = "SUBJECTNAME" if "SUBJECTNAME" in df.columns else "SUBJECT"

df = df.sort_values(by=[date_col])

grouped_html = ""

for date, group in df.groupby(date_col):

    grouped_html += f"""
    <tr>
        <td rowspan="{len(group)}">{date}</td>
    """

    first = True

    for _, row in group.iterrows():

        if not first:
            grouped_html += "<tr>"

        grouped_html += f"""
            <td>{row.get('FN_AN','AN')}</td>
            <td>{row.get('HOSTCOLLEGE','XW')}</td>
            <td>{row.get('REGULATION','R22')}</td>
            <td>{row.get('EXAM_YEAR','2')}</td>
            <td>{row.get('SEMESTER','1')}</td>
            <td>{row.get('REG_SUP','REG')}</td>
            <td>{row.get(branch_col,'')}</td>
            <td>{row.get('BRANCHNAME', row.get(branch_col,''))}</td>
            <td>{row.get(subject_col,'')}</td>
            <td>{row.get('SUBJECTCODE','')}</td>
            <td>{row.get('COUNT','')}</td>
        </tr>
        """

        first = False

return render_template("timetable.html", table_html=grouped_html)
```

# DOWNLOAD PAGE

@app.route("/download_excel")
def download_excel():
conn = get_db()
data = conn.execute("SELECT * FROM uploads").fetchall()
conn.close()
return render_template("download_excel.html", data=data)

# EXPORT EXCEL

@app.route("/export_excel/<filename>")
def export_excel(filename):

```
conn = get_db()

try:
    df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
except:
    conn.close()
    flash("No timetable available")
    return redirect("/download_excel")

conn.close()

excel_file = os.path.join("/tmp", "output.xlsx")
df.to_excel(excel_file, index=False)

return send_file(excel_file, as_attachment=True)
```

# DELETE

@app.route("/delete/<filename>")
def delete_file(filename):
conn = get_db()
conn.execute("DELETE FROM uploads WHERE filename=?", (filename,))
conn.commit()
conn.close()

```
path = os.path.join(UPLOAD_FOLDER, filename)
if os.path.exists(path):
    os.remove(path)

flash("Deleted successfully")
return redirect("/history")
```

# RUN APP

if **name** == "**main**":
port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
