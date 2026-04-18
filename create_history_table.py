import sqlite3
import os

# Use environment variable for database path (Render compatibility)
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')

def create_history_tables():
    """Create history-related tables"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

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
    print(f"✅ History tables created successfully at: {DATABASE_PATH}")

if __name__ == '__main__':
    create_history_tables()

4. create_table.py ⚠️ NEEDS UPDATE
UPDATED create_table.py:

import sqlite3
import os

# Use environment variable for database path (Render compatibility)
DATABASE_PATH = os.environ.get('DATABASE_PATH', 'database.db')

def create_timetable_table():
    """Create timetable table for PDF extraction"""
    conn = sqlite3.connect(DATABASE_PATH)
    cursor = conn.cursor()

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

    conn.commit()
    conn.close()
    print(f"✅ Timetable table created successfully at: {DATABASE_PATH}")

if __name__ == '__main__':
    create_timetable_table()
