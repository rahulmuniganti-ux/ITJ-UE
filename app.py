from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
import sqlite3
import os
from werkzeug.utils import secure_filename
import fitz  # PyMuPDF
import pandas as pd
import re
from datetime import datetime
from io import BytesIO

app = Flask(__name__)
app.secret_key = "your_secret_key_here_change_in_production"

# Configuration
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# ==================== HELPER FUNCTIONS ====================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def get_db_connection():
    """Get database connection"""
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

def log_admin_action(admin_id, action, description):
    """Log admin actions"""
    try:
        conn = get_db_connection()
        conn.execute("""
            INSERT INTO admin_logs (admin_id, action, description, ip_address)
            VALUES (?, ?, ?, ?)
        """, (admin_id, action, description, request.remote_addr))
        conn.commit()
        conn.close()
    except:
        pass

def extract_timetable_from_pdf(file_path):
    """Extract timetable data from PDF"""
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        return []

    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()

    lines = text.split("\n")
    data = []
    current_date = None

    date_pattern = r"(\d{2}[-/]\d{2}[-/]\d{4})"

    for line in lines:
        line = line.strip()
        if not line or len(line) < 3:
            continue

        date_match = re.search(date_pattern, line)
        
        if date_match:
            current_date = date_match.group(1).replace("/", "-")
            remaining = line[date_match.end():].strip()
            
            if len(remaining) > 3:
                parsed = parse_timetable_line(remaining, current_date)
                if parsed:
                    data.append(parsed)
        elif current_date:
            parsed = parse_timetable_line(line, current_date)
            if parsed:
                data.append(parsed)

    return data

def parse_timetable_line(line, date):
    """Parse a single timetable line"""
    if len(line) < 5:
        return None

    skip_keywords = ["DATE", "SESSION", "BRANCH", "SUBJECT", "CODE", "YEAR", "SEM", 
                     "EXAMINATION", "TIMETABLE", "JNTUH", "PAGE", "CONSOLIDATED"]
    
    if any(keyword in line.upper() for keyword in skip_keywords):
        return None

    data = {
        "date": date,
        "n_an": "AN",
        "college": "",
        "reg": "R22",
        "year": "",
        "sem": "",
        "type": "Regular",
        "code": "",
        "branch": "",
        "subject": "",
        "sub_code": "",
        "count": ""
    }

    # Extract session
    if "FN" in line.upper() or "FORENOON" in line.upper():
        data["n_an"] = "FN"

    # Extract regulation
    reg_match = re.search(r"R\d{2}", line, re.IGNORECASE)
    if reg_match:
        data["reg"] = reg_match.group().upper()

    # Extract year
    year_match = re.search(r"\b([1-4]|I{1,3}|IV)\s*(YEAR|YR|Y)?\b", line, re.IGNORECASE)
    if year_match:
        year = year_match.group(1)
        roman_to_arabic = {"I": "1", "II": "2", "III": "3", "IV": "4"}
        data["year"] = roman_to_arabic.get(year.upper(), year)

    # Extract semester
    sem_match = re.search(r"\b([1-2]|I{1,2})\s*(SEM|SEMESTER|S)?\b", line, re.IGNORECASE)
    if sem_match:
        sem = sem_match.group(1)
        roman_to_arabic = {"I": "1", "II": "2"}
        data["sem"] = roman_to_arabic.get(sem.upper(), sem)

    # Extract branch
    branch_pattern = r"\b(CSE|ECE|EEE|MECH|MECHANICAL|CIVIL|IT|CSE\(AI&ML\)|CSE\(DS\)|CSE\(AIML\)|AIDS|CSBS)\b"
    branch_match = re.search(branch_pattern, line, re.IGNORECASE)
    if branch_match:
        data["branch"] = branch_match.group().upper()

    # Extract subject code
    code_pattern = r"\b([A-Z]{2,4}\d{3,6}[A-Z]?)\b"
    code_match = re.search(code_pattern, line)
    if code_match:
        data["sub_code"] = code_match.group()

    # Extract count
    count_match = re.search(r"\b(\d{1,4})\s*$", line)
    if count_match:
        data["count"] = count_match.group(1)

    # Extract subject name
    subject = line
    for key in ["n_an", "reg", "year", "sem", "branch", "sub_code", "count"]:
        if data[key]:
            subject = subject.replace(str(data[key]), "")
    
    subject = re.sub(r"\s+", " ", subject).strip()
    subject = re.sub(r"[^\w\s\-\(\)&,]", "", subject)
    
    if len(subject) > 3:
        data["subject"] = subject
    else:
        return None

    return data

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Home page"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')

        if not all([name, email, password, role]):
            flash('All fields are required!', 'error')
            return redirect(url_for('register'))

        conn = get_db_connection()
        
        # Check if email exists
        existing = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered!', 'error')
            conn.close()
            return redirect(url_for('register'))

        try:
            conn.execute('''
                INSERT INTO users (name, email, password, role)
                VALUES (?, ?, ?, ?)
            ''', (name, email, password, role))
            conn.commit()
            flash('Registration successful! Please login.', 'success')
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            conn.close()
            return redirect(url_for('register'))

    return render_template('register.html')

@app.route('/register_admin', methods=['GET', 'POST'])
def register_admin():
    """Admin registration"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        department = request.form.get('department')

        if not all([name, email, password, department]):
            flash('All fields are required!', 'error')
            return redirect(url_for('register_admin'))

        conn = get_db_connection()
        
        existing = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered!', 'error')
            conn.close()
            return redirect(url_for('register_admin'))

        try:
            conn.execute('''
                INSERT INTO users (name, email, password, role, department)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, email, password, 'admin', department))
            conn.commit()
            flash('Admin registration successful! Please login.', 'success')
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            conn.close()
            return redirect(url_for('register_admin'))

    return render_template('register_admin.html')

@app.route('/register_student', methods=['GET', 'POST'])
def register_student():
    """Student registration"""
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        roll = request.form.get('roll')
        branch = request.form.get('branch')
        year = request.form.get('year')
        semester = request.form.get('semester')
        regulation = request.form.get('regulation', 'R22')

        if not all([name, email, password, roll, branch, year, semester]):
            flash('All fields are required!', 'error')
            return redirect(url_for('register_student'))

        conn = get_db_connection()
        
        existing = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        if existing:
            flash('Email already registered!', 'error')
            conn.close()
            return redirect(url_for('register_student'))

        try:
            conn.execute('''
                INSERT INTO users (name, email, password, role, roll, branch, year, semester, regulation)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (name, email, password, 'student', roll, branch, year, semester, regulation))
            conn.commit()
            flash('Student registration successful! Please login.', 'success')
            conn.close()
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Registration failed: {str(e)}', 'error')
            conn.close()
            return redirect(url_for('register_student'))

    return render_template('register_student.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email and password are required!', 'error')
            return redirect(url_for('login'))

        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND password = ?', 
                           (email, password)).fetchone()

        if user:
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['role'] = user['role']
            session['email'] = user['email']
            
            if user['role'] == 'student':
                session['branch'] = user['branch']
                session['year'] = user['year']
                session['semester'] = user['semester']
            
            # Update last login
            conn.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user['id']))
            conn.commit()
            conn.close()

            flash(f'Welcome back, {user["name"]}!', 'success')
            
            if user['role'] == 'admin':
                log_admin_action(user['id'], 'LOGIN', 'Admin logged in')
                return redirect(url_for('admin_dashboard'))
            else:
                return redirect(url_for('student_dashboard'))
        else:
            flash('Invalid email or password!', 'error')
            conn.close()
            return redirect(url_for('login'))

    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    if session.get('role') == 'admin':
        log_admin_action(session.get('user_id'), 'LOGOUT', 'Admin logged out')
    
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('index'))

@app.route('/admin_dashboard')
def admin_dashboard():
    """Admin dashboard"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as admin to access this page.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Get statistics
    total_uploads = conn.execute('SELECT COUNT(*) as count FROM uploads').fetchone()['count']
    total_records = conn.execute('SELECT COUNT(*) as count FROM timetable').fetchone()['count']
    total_students = conn.execute('SELECT COUNT(*) as count FROM users WHERE role = "student"').fetchone()['count']
    
    # Get recent uploads
    recent_uploads = conn.execute('''
        SELECT * FROM uploads 
        ORDER BY upload_time DESC 
        LIMIT 5
    ''').fetchall()
    
    conn.close()

    return render_template('admin_dashboard.html',
                         total_uploads=total_uploads,
                         total_records=total_records,
                         total_students=total_students,
                         recent_uploads=recent_uploads)

@app.route('/student_dashboard')
def student_dashboard():
    """Student dashboard"""
    if 'user_id' not in session or session.get('role') != 'student':
        flash('Please login as student to access this page.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Get statistics
    exam_count = conn.execute('SELECT COUNT(DISTINCT date) as count FROM timetable').fetchone()['count']
    subject_count = conn.execute('SELECT COUNT(DISTINCT subject) as count FROM timetable').fetchone()['count']
    
    conn.close()

    return render_template('student_dashboard.html',
                         exam_count=exam_count,
                         subject_count=subject_count)

@app.route('/upload', methods=['GET', 'POST'])
def upload():
    """Upload PDF timetable"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as admin to upload files.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected!', 'error')
            return redirect(url_for('upload'))

        file = request.files['file']

        if file.filename == '':
            flash('No file selected!', 'error')
            return redirect(url_for('upload'))

        if not allowed_file(file.filename):
            flash('Only PDF files are allowed!', 'error')
            return redirect(url_for('upload'))

        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            file.save(filepath)
            file_size = os.path.getsize(filepath)

            # Extract data from PDF
            extracted_data = extract_timetable_from_pdf(filepath)

            if not extracted_data:
                flash('No data could be extracted from the PDF!', 'warning')
                os.remove(filepath)
                return redirect(url_for('upload'))

            # Save to database
            conn = get_db_connection()
            
            # Save upload record
            conn.execute('''
                INSERT INTO uploads (filename, original_filename, file_path, file_size, 
                                   uploaded_by, records_extracted)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (filename, file.filename, filepath, file_size, session['user_id'], len(extracted_data)))

            # Save timetable records
            for record in extracted_data:
                conn.execute('''
                    INSERT INTO timetable (date, n_an, college, reg, year, sem, type, code,
                                         branch, subject, sub_code, count, pdf_name)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (record['date'], record['n_an'], record['college'], record['reg'],
                     record['year'], record['sem'], record['type'], record['code'],
                     record['branch'], record['subject'], record['sub_code'], 
                     record['count'], filename))

            conn.commit()
            conn.close()

            log_admin_action(session['user_id'], 'UPLOAD', 
                           f'Uploaded {filename} with {len(extracted_data)} records')

            flash(f'Successfully uploaded and extracted {len(extracted_data)} records!', 'success')
            return redirect(url_for('admin_dashboard'))

        except Exception as e:
            flash(f'Upload failed: {str(e)}', 'error')
            if os.path.exists(filepath):
                os.remove(filepath)
            return redirect(url_for('upload'))

    return render_template('upload.html')

@app.route('/view_consolidated')
def view_consolidated():
    """View consolidated timetable"""
    if 'user_id' not in session:
        flash('Please login to view timetable.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    records = conn.execute('SELECT * FROM timetable ORDER BY date, branch').fetchall()
    conn.close()

    # Generate HTML table
    table_html = ""
    for record in records:
        table_html += f"""
        <tr>
            <td>{record['date']}</td>
            <td>{record['n_an']}</td>
            <td>{record['college']}</td>
            <td>{record['reg']}</td>
            <td>{record['year']}</td>
            <td>{record['sem']}</td>
            <td>{record['type']}</td>
            <td>{record['code']}</td>
            <td>{record['branch']}</td>
            <td>{record['subject']}</td>
            <td>{record['sub_code']}</td>
            <td>{record['count']}</td>
        </tr>
        """

    return render_template('timetable.html', 
                         table_html=table_html,
                         total_records=len(records))

@app.route('/search', methods=['GET', 'POST'])
def search():
    """Search timetable"""
    if 'user_id' not in session:
        flash('Please login to search.', 'error')
        return redirect(url_for('login'))

    results = []
    search_query = ""

    if request.method == 'POST':
        search_query = request.form.get('query', '').strip()
        
        if search_query:
            conn = get_db_connection()
            
            results = conn.execute('''
                SELECT * FROM timetable 
                WHERE date LIKE ? OR branch LIKE ? OR subject LIKE ? 
                   OR sub_code LIKE ? OR reg LIKE ?
                ORDER BY date
            ''', (f'%{search_query}%', f'%{search_query}%', f'%{search_query}%',
                 f'%{search_query}%', f'%{search_query}%')).fetchall()
            
            # Log search
            conn.execute('''
                INSERT INTO search_history (user_id, search_query, results_count)
                VALUES (?, ?, ?)
            ''', (session['user_id'], search_query, len(results)))
            
            conn.commit()
            conn.close()

    return render_template('search.html', 
                         results=results, 
                         search_query=search_query)

@app.route('/view_by_date')
def view_by_date():
    """View timetable by date"""
    if 'user_id' not in session:
        flash('Please login to view timetable.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Get unique dates
    dates = conn.execute('SELECT DISTINCT date FROM timetable ORDER BY date').fetchall()
    
    # Get records grouped by date
    date_records = {}
    for date_row in dates:
        date = date_row['date']
        records = conn.execute('''
            SELECT * FROM timetable 
            WHERE date = ? 
            ORDER BY branch, subject
        ''', (date,)).fetchall()
        date_records[date] = records
    
    conn.close()

    return render_template('view_by_date.html', date_records=date_records)

@app.route('/export_excel')
def export_excel():
    """Export timetable to Excel"""
    if 'user_id' not in session:
        flash('Please login to download.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    records = conn.execute('SELECT * FROM timetable ORDER BY date, branch').fetchall()
    conn.close()

    # Convert to DataFrame
    df = pd.DataFrame([dict(record) for record in records])
    
    # Remove internal columns
    if 'id' in df.columns:
        df = df.drop('id', axis=1)
    if 'pdf_name' in df.columns:
        df = df.drop('pdf_name', axis=1)
    if 'upload_time' in df.columns:
        df = df.drop('upload_time', axis=1)

    # Create Excel file in memory
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Timetable', index=False)
    
    output.seek(0)

    return send_file(
        output,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'timetable_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

@app.route('/history')
def history():
    """View upload history"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Please login as admin to view history.', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    uploads = conn.execute('''
        SELECT u.*, us.name as uploader_name
        FROM uploads u
        LEFT JOIN users us ON u.uploaded_by = us.id
        ORDER BY u.upload_time DESC
    ''').fetchall()
    conn.close()

    return render_template('history.html', uploads=uploads)

@app.route('/delete_upload/<int:upload_id>')
def delete_upload(upload_id):
    """Delete an upload and its records"""
    if 'user_id' not in session or session.get('role') != 'admin':
        flash('Unauthorized access!', 'error')
        return redirect(url_for('login'))

    conn = get_db_connection()
    
    # Get upload info
    upload = conn.execute('SELECT * FROM uploads WHERE id = ?', (upload_id,)).fetchone()
    
    if upload:
        # Delete file
        if os.path.exists(upload['file_path']):
            os.remove(upload['file_path'])
        
        # Delete timetable records
        conn.execute('DELETE FROM timetable WHERE pdf_name = ?', (upload['filename'],))
        
        # Delete upload record
        conn.execute('DELETE FROM uploads WHERE id = ?', (upload_id,))
        
        conn.commit()
        
        log_admin_action(session['user_id'], 'DELETE', 
                        f'Deleted upload {upload["filename"]}')
        
        flash('Upload deleted successfully!', 'success')
    else:
        flash('Upload not found!', 'error')
    
    conn.close()
    return redirect(url_for('history'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
