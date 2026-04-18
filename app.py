from flask import Flask, render_template, request, redirect, session, flash, send_file
import sqlite3, pandas as pd, os
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

# ⚠️ Safe import (prevents full crash if parser fails)
try:
    from parser import extract_timetable
except Exception as e:
    print("Parser import error:", e)
    extract_timetable = None


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fallback_secret_key_change_in_production")

# Upload folder
UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}


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

    conn.execute("""
    CREATE TABLE IF NOT EXISTS consolidated_timetable(
        DATE TEXT,
        DAY TEXT,
        BRANCH TEXT,
        SUBJECT_CODE TEXT,
        SUBJECT TEXT,
        EXAM_TYPE TEXT
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
        try:
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

            flash("Registration successful! Please login.", "success")
            return redirect("/login")
        except sqlite3.IntegrityError:
            flash("Email already exists!", "error")
        except Exception as e:
            flash(f"Registration failed: {str(e)}", "error")

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
            session["user_name"] = user[1]

            flash(f"Welcome back, {user[1]}!", "success")

            if user[4] == "admin":
                return redirect("/admin_dashboard")
            return redirect("/")
        else:
            flash("Invalid email or password!", "error")

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully!", "success")
    return redirect("/")


# ---------------- ADMIN DASHBOARD ----------------
@app.route("/admin_dashboard")
def admin_dashboard():
    if session.get("role") != "admin":
        flash("Admin access required!", "error")
        return redirect("/login")
    
    # Get statistics
    conn = get_db()
    
    upload_count = conn.execute("SELECT COUNT(*) FROM uploads").fetchone()[0]
    
    try:
        timetable_count = conn.execute("SELECT COUNT(*) FROM consolidated_timetable").fetchone()[0]
    except:
        timetable_count = 0
    
    conn.close()
    
    return render_template("admin_dashboard.html", 
                         upload_count=upload_count,
                         timetable_count=timetable_count)


# ---------------- UPLOAD ----------------
@app.route("/upload", methods=["POST"])
def upload():
    if session.get("role") != "admin":
        flash("Admin access required!", "error")
        return redirect("/login")

    files = request.files.getlist("file")

    if not files or files[0].filename == "":
        flash("No file selected!", "error")
        return redirect("/admin_dashboard")

    conn = get_db()
    merged_df = pd.DataFrame()
    successful_uploads = 0
    failed_uploads = 0

    for file in files:
        if file.filename == "" or not allowed_file(file.filename):
            failed_uploads += 1
            continue

        try:
            path = os.path.join(UPLOAD_FOLDER, file.filename)
            file.save(path)

            df = pd.DataFrame()

            # Safe parser call
            if extract_timetable:
                try:
                    print(f"Processing {file.filename}...")
                    df = extract_timetable(path)
                    print(f"Extracted {len(df)} records from {file.filename}")
                except Exception as e:
                    print(f"Parser error for {file.filename}:", e)
                    flash(f"Failed to parse {file.filename}: {str(e)}", "error")
                    failed_uploads += 1
                    continue
            else:
                flash("Parser not available!", "error")
                failed_uploads += 1
                continue

            if df is not None and not df.empty:
                merged_df = pd.concat([merged_df, df], ignore_index=True)
                successful_uploads += 1

            # Record upload
            conn.execute(
                "INSERT INTO uploads(filename,upload_time) VALUES (?,?)",
                (file.filename, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            )
            conn.commit()

        except Exception as e:
            print(f"Upload error for {file.filename}:", e)
            flash(f"Error uploading {file.filename}: {str(e)}", "error")
            failed_uploads += 1

    if merged_df.empty:
        conn.close()
        flash("No valid data extracted from uploaded files!", "error")
        return redirect("/admin_dashboard")

    # Clean and save data
    try:
        merged_df.drop_duplicates(inplace=True)
        
        # Ensure all required columns exist
        required_columns = ["DATE", "DAY", "BRANCH", "SUBJECT_CODE", "SUBJECT", "EXAM_TYPE"]
        for col in required_columns:
            if col not in merged_df.columns:
                merged_df[col] = ""
        
        merged_df = merged_df[required_columns]
        
        merged_df.to_sql("consolidated_timetable", conn, if_exists="replace", index=False)
        conn.commit()
        
        flash(f"Successfully processed {successful_uploads} file(s)! Extracted {len(merged_df)} timetable entries.", "success")
        
        if failed_uploads > 0:
            flash(f"{failed_uploads} file(s) failed to process.", "warning")
            
    except Exception as e:
        flash(f"Error saving data: {str(e)}", "error")
    
    conn.close()
    return redirect("/history")


# ---------------- HISTORY ----------------
@app.route("/history")
def history():
    if session.get("role") is None:
        flash("Please login to view history!", "error")
        return redirect("/login")

    conn = get_db()
    data = conn.execute("SELECT * FROM uploads ORDER BY upload_time DESC").fetchall()
    
    # Get timetable stats
    try:
        stats = conn.execute("""
            SELECT 
                COUNT(DISTINCT DATE) as total_dates,
                COUNT(DISTINCT BRANCH) as total_branches,
                COUNT(*) as total_exams
            FROM consolidated_timetable
        """).fetchone()
    except:
        stats = (0, 0, 0)
    
    conn.close()

    return render_template("history.html", data=data, stats=stats)


# ---------------- VIEW TABLE ----------------
@app.route("/view_consolidated")
def view_consolidated():
    if session.get("role") is None:
        flash("Please login to view timetable!", "error")
        return redirect("/login")

    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
    except Exception as e:
        conn.close()
        flash(f"No timetable available: {str(e)}", "error")
        return redirect("/admin_dashboard")

    conn.close()

    if df.empty:
        flash("No timetable data found!", "error")
        return redirect("/admin_dashboard")

    # Clean column names
    df.columns = [c.strip().upper() for c in df.columns]

    # Sort by date
    try:
        df['DATE_SORT'] = pd.to_datetime(df['DATE'], format='%d-%m-%Y')
        df.sort_values(['DATE_SORT', 'BRANCH'], inplace=True)
        df.drop('DATE_SORT', axis=1, inplace=True)
    except:
        pass

    # Generate HTML table
    table_html = df.to_html(classes='table table-striped table-bordered', 
                            index=False, 
                            escape=False)

    return render_template("timetable.html", 
                         table_html=table_html,
                         total_records=len(df))


# ---------------- VIEW BY DATE ----------------
@app.route("/view_by_date")
def view_by_date():
    if session.get("role") is None:
        flash("Please login!", "error")
        return redirect("/login")

    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
    except:
        conn.close()
        flash("No timetable available!", "error")
        return redirect("/admin_dashboard")

    conn.close()

    if df.empty:
        flash("No data found!", "error")
        return redirect("/admin_dashboard")

    # Group by date
    dates = df['DATE'].unique()
    
    date_tables = {}
    for date in dates:
        date_df = df[df['DATE'] == date]
        date_tables[date] = date_df.to_html(classes='table table-striped', 
                                            index=False)

    return render_template("view_by_date.html", date_tables=date_tables)


# ---------------- EXPORT EXCEL (ENHANCED) ----------------
@app.route("/export_excel")
def export_excel():
    if session.get("role") is None:
        flash("Please login to export!", "error")
        return redirect("/login")

    conn = get_db()

    try:
        df = pd.read_sql("SELECT * FROM consolidated_timetable", conn)
    except Exception as e:
        conn.close()
        flash(f"No data available: {str(e)}", "error")
        return redirect("/history")

    conn.close()

    if df.empty:
        flash("No data to export!", "error")
        return redirect("/history")

    # Create Excel with multiple sheets
    file_path = os.path.join(UPLOAD_FOLDER, "timetable_export.xlsx")
    
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
            # Sheet 1: Full Timetable
            df.to_excel(writer, sheet_name='Full Timetable', index=False)
            
            # Sheet 2: Day-wise breakdown
            if 'DATE' in df.columns and not df['DATE'].isna().all():
                for date in df['DATE'].unique():
                    if pd.notna(date) and date:
                        date_df = df[df['DATE'] == date]
                        # Excel sheet names have 31 char limit
                        sheet_name = str(date).replace('/', '-')[:31]
                        date_df.to_excel(writer, sheet_name=sheet_name, index=False)
            
            # Sheet 3: Branch Summary
            if 'BRANCH' in df.columns and 'DATE' in df.columns:
                try:
                    branch_summary = df.groupby(['DATE', 'BRANCH']).agg({
                        'SUBJECT': 'count',
                        'EXAM_TYPE': lambda x: ', '.join(x.unique())
                    }).reset_index()
                    branch_summary.columns = ['DATE', 'BRANCH', 'EXAM_COUNT', 'EXAM_TYPES']
                    branch_summary.to_excel(writer, sheet_name='Branch Summary', index=False)
                except:
                    pass
            
            # Sheet 4: Exam Type Summary
            if 'EXAM_TYPE' in df.columns:
                try:
                    exam_type_summary = df.groupby(['DATE', 'EXAM_TYPE']).size().reset_index(name='COUNT')
                    exam_type_summary.to_excel(writer, sheet_name='Exam Type Summary', index=False)
                except:
                    pass
        
        flash("Excel file generated successfully!", "success")
        return send_file(file_path, 
                        as_attachment=True, 
                        download_name=f'timetable_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx')
    
    except Exception as e:
        flash(f"Error generating Excel: {str(e)}", "error")
        return redirect("/history")


# ---------------- DELETE ----------------
@app.route("/delete/<int:file_id>")
def delete_file(file_id):
    if session.get("role") != "admin":
        flash("Admin access required!", "error")
        return redirect("/login")

    conn = get_db()
    
    file_record = conn.execute("SELECT filename FROM uploads WHERE id=?", (file_id,)).fetchone()
    
    if file_record:
        filename = file_record[0]
        
        conn.execute("DELETE FROM uploads WHERE id=?", (file_id,))
        conn.commit()
        
        path = os.path.join(UPLOAD_FOLDER, filename)
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass
        
        flash(f"Deleted {filename} successfully!", "success")
    else:
        flash("File not found!", "error")
    
    conn.close()
    return redirect("/history")


# ---------------- CLEAR ALL DATA ----------------
@app.route("/clear_all")
def clear_all():
    if session.get("role") != "admin":
        flash("Admin access required!", "error")
        return redirect("/login")

    conn = get_db()
    
    try:
        conn.execute("DELETE FROM uploads")
        conn.execute("DELETE FROM consolidated_timetable")
        conn.commit()
        
        # Clear upload folder
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
            except:
                pass
        
        flash("All data cleared successfully!", "success")
    except Exception as e:
        flash(f"Error clearing data: {str(e)}", "error")
    
    conn.close()
    return redirect("/admin_dashboard")


# ---------------- SEARCH ----------------
@app.route("/search", methods=["GET", "POST"])
def search():
    if session.get("role") is None:
        flash("Please login!", "error")
        return redirect("/login")

    if request.method == "POST":
        search_term = request.form.get("search_term", "").strip()
        search_type = request.form.get("search_type", "subject")
        
        if not search_term:
            flash("Please enter a search term!", "error")
            return redirect("/search")
        
        conn = get_db()
        
        try:
            if search_type == "subject":
                query = "SELECT * FROM consolidated_timetable WHERE SUBJECT LIKE ?"
            elif search_type == "branch":
                query = "SELECT * FROM consolidated_timetable WHERE BRANCH LIKE ?"
            elif search_type == "date":
                query = "SELECT * FROM consolidated_timetable WHERE DATE LIKE ?"
            else:
                query = "SELECT * FROM consolidated_timetable WHERE SUBJECT_CODE LIKE ?"
            
            df = pd.read_sql(query, conn, params=(f"%{search_term}%",))
            conn.close()
            
            if df.empty:
                flash(f"No results found for '{search_term}'", "warning")
                return render_template("search.html", results=None)
            
            table_html = df.to_html(classes='table table-striped', index=False)
            flash(f"Found {len(df)} result(s)", "success")
            
            return render_template("search.html", 
                                 results=table_html,
                                 search_term=search_term,
                                 search_type=search_type)
        
        except Exception as e:
            conn.close()
            flash(f"Search error: {str(e)}", "error")
    
    return render_template("search.html", results=None)


# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug_mode = os.environ.get("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug_mode)
