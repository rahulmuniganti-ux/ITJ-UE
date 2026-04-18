import sqlite3
import os

# Use environment variable for database path (Render compatibility)
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')

def create_database():
    """Create database and all required tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL,
            roll TEXT,
            branch TEXT,
            year TEXT,
            semester TEXT,
            regulation TEXT DEFAULT 'R22',
            department TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP
        )
    ''')

    # Timetable table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timetable (
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
    ''')

    # Uploads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            uploaded_by INTEGER,
            records_extracted INTEGER DEFAULT 0,
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (uploaded_by) REFERENCES users(id)
        )
    ''')

    # Admin logs table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            action TEXT NOT NULL,
            description TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
    ''')

    # Search history table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS search_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            search_query TEXT,
            results_count INTEGER,
            search_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Database created successfully at: {DATABASE_PATH}")

if __name__ == '__main__':
    create_database()
