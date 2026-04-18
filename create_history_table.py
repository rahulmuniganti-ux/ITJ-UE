import sqlite3
import os
from datetime import datetime

def create_history_table():
    """Create or update the uploads/history table"""
    
    print("📦 Creating upload history table...")
    
    # Connect to database
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        # ==================== CREATE UPLOADS TABLE ====================
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS uploads(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
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
        print("✅ Uploads table created/verified")
        
        # ==================== CREATE INDEX ====================
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_uploads_filename 
        ON uploads(filename)
        """)
        
        cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_uploads_upload_time 
        ON uploads(upload_time)
        """)
        print("✅ Indexes created")
        
        # ==================== MIGRATE OLD DATA (if pdf_uploads exists) ====================
        # Check if pdf_uploads table exists
        cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='pdf_uploads'
        """)
        
        if cursor.fetchone():
            print("\n📋 Found pdf_uploads table, checking for migration...")
            
            # Check if data needs to be migrated
            cursor.execute("SELECT COUNT(*) FROM pdf_uploads")
            pdf_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM uploads")
            upload_count = cursor.fetchone()[0]
            
            if pdf_count > 0 and upload_count == 0:
                print(f"🔄 Migrating {pdf_count} records from pdf_uploads to uploads...")
                
                cursor.execute("""
                INSERT INTO uploads (filename, original_filename, file_path, file_size, 
                                   upload_time, uploaded_by, status, records_extracted)
                SELECT pdf_name, original_filename, file_path, file_size, 
                       upload_time, uploaded_by, status, records_extracted
                FROM pdf_uploads
                """)
                
                print(f"✅ Migrated {pdf_count} records successfully")
            else:
                print("ℹ️  No migration needed")
        
        # Commit changes
        conn.commit()
        
        # ==================== DISPLAY STATISTICS ====================
        print("\n" + "="*60)
        print("📊 UPLOAD HISTORY TABLE STATISTICS")
        print("="*60)
        
        cursor.execute("SELECT COUNT(*) FROM uploads")
        total_uploads = cursor.fetchone()[0]
        print(f"📄 Total Uploads: {total_uploads}")
        
        if total_uploads > 0:
            cursor.execute("""
            SELECT filename, upload_time, records_extracted 
            FROM uploads 
            ORDER BY upload_time DESC 
            LIMIT 5
            """)
            recent_uploads = cursor.fetchall()
            
            print("\n📋 Recent Uploads:")
            for idx, (filename, upload_time, records) in enumerate(recent_uploads, 1):
                print(f"   {idx}. {filename}")
                print(f"      ⏰ {upload_time}")
                print(f"      📊 {records} records extracted")
        
        cursor.execute("""
        SELECT SUM(records_extracted) FROM uploads
        """)
        total_records = cursor.fetchone()[0] or 0
        print(f"\n📊 Total Timetable Records: {total_records}")
        
        print("="*60)
        
        print("\n✅ Upload history table created successfully!")
        
    except sqlite3.Error as e:
        print(f"\n❌ Database error: {e}")
        conn.rollback()
        raise
    
    finally:
        conn.close()

def verify_table_structure():
    """Verify the table structure"""
    
    print("\n🔍 Verifying table structure...")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(uploads)")
        columns = cursor.fetchall()
        
        print("\n📋 Table Structure:")
        print("-" * 60)
        print(f"{'Column':<20} {'Type':<15} {'Not Null':<10} {'Default'}")
        print("-" * 60)
        
        for col in columns:
            col_id, name, col_type, not_null, default_val, pk = col
            not_null_str = "YES" if not_null else "NO"
            default_str = str(default_val) if default_val else "-"
            print(f"{name:<20} {col_type:<15} {not_null_str:<10} {default_str}")
        
        print("-" * 60)
        
    finally:
        conn.close()

def add_sample_data():
    """Add sample upload data for testing (optional)"""
    
    print("\n❓ Would you like to add sample data for testing? (y/n): ", end="")
    choice = input().strip().lower()
    
    if choice != 'y':
        print("ℹ️  Skipping sample data")
        return
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        sample_data = [
            ('timetable_2024_sem1.pdf', 'timetable_2024_sem1.pdf', 'uploads/timetable_2024_sem1.pdf', 524288, 'processed', 150),
            ('exam_schedule_2024.pdf', 'exam_schedule_2024.pdf', 'uploads/exam_schedule_2024.pdf', 612352, 'processed', 200),
            ('final_timetable.pdf', 'final_timetable.pdf', 'uploads/final_timetable.pdf', 458752, 'processed', 175),
        ]
        
        for filename, original, path, size, status, records in sample_data:
            cursor.execute("""
            INSERT INTO uploads (filename, original_filename, file_path, file_size, status, records_extracted)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (filename, original, path, size, status, records))
        
        conn.commit()
        print(f"✅ Added {len(sample_data)} sample records")
        
    except sqlite3.IntegrityError:
        print("ℹ️  Sample data already exists")
    
    finally:
        conn.close()

if __name__ == "__main__":
    try:
        # Create the table
        create_history_table()
        
        # Verify structure
        verify_table_structure()
        
        # Optional: Add sample data
        add_sample_data()
        
        print("\n🎉 All done! Your upload history table is ready.")
        print("📁 Database file: database.db")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
