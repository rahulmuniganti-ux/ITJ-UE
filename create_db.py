import sqlite3
import os
from datetime import datetime

def create_database():
    """Create database with all required tables"""
    
    # Remove existing database if it exists (optional - comment out if you want to keep existing data)
    # if os.path.exists("database.db"):
    #     os.remove("database.db")
    #     print("🗑️  Existing database removed")
    
    # Connect to database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    print("📦 Creating database tables...")
    
    # ==================== USERS TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'student')),
        branch TEXT,
        year TEXT,
        semester TEXT,
        roll TEXT,
        department TEXT,
        regulation TEXT DEFAULT 'R22',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    """)
    print("✅ Users table created")
    
    # ==================== TIMETABLE TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS timetable(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        n_an TEXT,
        college TEXT,
        reg TEXT,
        year TEXT,
        sem TEXT,
        type TEXT,
        code TEXT,
        branch TEXT,
        subject TEXT,
        sub_code TEXT,
        count TEXT,
        pdf_name TEXT,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✅ Timetable table created")
    
    # ==================== PDF UPLOADS TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pdf_uploads(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        pdf_name TEXT NOT NULL,
        original_filename TEXT,
        file_path TEXT,
        file_size INTEGER,
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        uploaded_by INTEGER,
        status TEXT DEFAULT 'processed',
        records_extracted INTEGER DEFAULT 0,
        FOREIGN KEY (uploaded_by) REFERENCES users(id)
    )
    """)
    print("✅ PDF uploads table created")
    
    # ==================== ADMIN LOGS TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        admin_id INTEGER,
        action TEXT NOT NULL,
        description TEXT,
        ip_address TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (admin_id) REFERENCES users(id)
    )
    """)
    print("✅ Admin logs table created")
    
    # ==================== SEARCH HISTORY TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS search_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        search_query TEXT NOT NULL,
        search_type TEXT,
        results_count INTEGER,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)
    print("✅ Search history table created")
    
    # ==================== SYSTEM SETTINGS TABLE ====================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_settings(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        setting_key TEXT UNIQUE NOT NULL,
        setting_value TEXT,
        description TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    print("✅ System settings table created")
    
    # ==================== CREATE INDEXES FOR PERFORMANCE ====================
    print("\n📊 Creating indexes for better performance...")
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timetable_date ON timetable(date)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timetable_branch ON timetable(branch)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timetable_subject ON timetable(subject)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_timetable_pdf_name ON timetable(pdf_name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_pdf_uploads_upload_time ON pdf_uploads(upload_time)")
    
    print("✅ Indexes created")
    
    # ==================== INSERT DEFAULT SYSTEM SETTINGS ====================
    print("\n⚙️  Inserting default system settings...")
    
    default_settings = [
        ('app_name', 'ITJ-UE Portal', 'Application name'),
        ('app_version', '1.0.0', 'Application version'),
        ('max_upload_size', '10485760', 'Maximum upload size in bytes (10 MB)'),
        ('allowed_file_types', 'pdf', 'Allowed file types for upload'),
        ('maintenance_mode', 'false', 'Maintenance mode status'),
        ('registration_enabled', 'true', 'User registration enabled'),
    ]
    
    for key, value, desc in default_settings:
        cursor.execute("""
            INSERT OR IGNORE INTO system_settings (setting_key, setting_value, description)
            VALUES (?, ?, ?)
        """, (key, value, desc))
    
    print("✅ Default settings inserted")
    
    # ==================== INSERT DEFAULT ADMIN USER (OPTIONAL) ====================
    print("\n👤 Creating default admin user...")
    
    try:
        # Default admin credentials (CHANGE THESE IN PRODUCTION!)
        cursor.execute("""
            INSERT INTO users (name, email, password, role, department)
            VALUES (?, ?, ?, ?, ?)
        """, ('Admin', 'admin@jntuh.ac.in', 'admin123', 'admin', 'Administration'))
        print("✅ Default admin user created")
        print("   📧 Email: admin@jntuh.ac.in")
        print("   🔒 Password: admin123")
        print("   ⚠️  IMPORTANT: Change this password after first login!")
    except sqlite3.IntegrityError:
        print("ℹ️  Default admin user already exists")
    
    # Commit all changes
    conn.commit()
    
    # ==================== DISPLAY DATABASE STATISTICS ====================
    print("\n" + "="*60)
    print("📊 DATABASE STATISTICS")
    print("="*60)
    
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    print(f"👥 Total Users: {user_count}")
    
    cursor.execute("SELECT COUNT(*) FROM timetable")
    timetable_count = cursor.fetchone()[0]
    print(f"📋 Timetable Records: {timetable_count}")
    
    cursor.execute("SELECT COUNT(*) FROM pdf_uploads")
    pdf_count = cursor.fetchone()[0]
    print(f"📄 PDF Uploads: {pdf_count}")
    
    cursor.execute("SELECT COUNT(*) FROM admin_logs")
    log_count = cursor.fetchone()[0]
    print(f"📝 Admin Logs: {log_count}")
    
    cursor.execute("SELECT COUNT(*) FROM search_history")
    search_count = cursor.fetchone()[0]
    print(f"🔍 Search History: {search_count}")
    
    print("="*60)
    
    # Close connection
    conn.close()
    
    print("\n✅ Database created successfully!")
    print("📁 Database file: database.db")
    print("🚀 You can now run your Flask application!")

if __name__ == "__main__":
    try:
        create_database()
    except Exception as e:
        print(f"\n❌ Error creating database: {e}")
        import traceback
        traceback.print_exc()
