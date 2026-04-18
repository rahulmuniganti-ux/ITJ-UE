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
