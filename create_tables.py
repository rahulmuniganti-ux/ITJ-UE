import fitz  # PyMuPDF
import pandas as pd
import re
import sqlite3
from datetime import datetime
import os

def extract_timetable(file_path):
    """
    Extract timetable data from PDF file
    Returns: pandas DataFrame with extracted data
    """
    
    print(f"📄 Opening PDF: {file_path}")
    
    try:
        doc = fitz.open(file_path)
        print(f"✅ PDF opened successfully ({len(doc)} pages)")
    except Exception as e:
        print(f"❌ Error opening file: {e}")
        return pd.DataFrame(columns=[
            "DATE", "N/AN", "COLLEGE", "REG", "YEAR", "SEM", 
            "TYPE", "CODE", "BRANCH", "SUBJECT", "SUB_CODE", "COUNT"
        ])

    text = ""
    
    # Extract text from all pages
    for page_num, page in enumerate(doc, 1):
        page_text = page.get_text()
        text += page_text
        print(f"📖 Extracted page {page_num}/{len(doc)}")
    
    doc.close()
    
    # Split into lines
    lines = text.split("\n")
    print(f"📝 Total lines extracted: {len(lines)}")
    
    data = []
    current_date = None
    
    # Enhanced patterns for better extraction
    date_pattern = r"(\d{2}[-/]\d{2}[-/]\d{4})"
    
    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        
        # Skip empty lines
        if not line or len(line) < 3:
            continue
        
        # Check for date
        date_match = re.search(date_pattern, line)
        
        if date_match:
            current_date = date_match.group(1)
            # Normalize date format to DD-MM-YYYY
            current_date = current_date.replace("/", "-")
            print(f"📅 Found date: {current_date}")
            
            # Extract remaining content after date
            remaining = line[date_match.end():].strip()
            
            if len(remaining) > 3:
                # Try to parse the line
                parsed_data = parse_timetable_line(remaining, current_date)
                if parsed_data:
                    data.append(parsed_data)
        
        elif current_date:
            # Line without date but we have a current date
            parsed_data = parse_timetable_line(line, current_date)
            if parsed_data:
                data.append(parsed_data)
    
    print(f"✅ Extracted {len(data)} records")
    
    # Create DataFrame
    if not data:
        print("⚠️  No data extracted from PDF")
        return pd.DataFrame(columns=[
            "DATE", "N/AN", "COLLEGE", "REG", "YEAR", "SEM", 
            "TYPE", "CODE", "BRANCH", "SUBJECT", "SUB_CODE", "COUNT"
        ])
    
    df = pd.DataFrame(data)
    return df


def parse_timetable_line(line, date):
    """
    Parse a single timetable line and extract fields
    Returns: dict with extracted fields or None
    """
    
    # Skip header lines and short lines
    if len(line) < 5:
        return None
    
    # Skip common header keywords
    skip_keywords = [
        "DATE", "SESSION", "BRANCH", "SUBJECT", "CODE", "YEAR", "SEM",
        "EXAMINATION", "TIMETABLE", "JNTUH", "PAGE", "CONSOLIDATED"
    ]
    
    if any(keyword in line.upper() for keyword in skip_keywords):
        return None
    
    # Initialize data dictionary
    data = {
        "DATE": date,
        "N/AN": "AN",  # Default to Afternoon
        "COLLEGE": "",
        "REG": "R22",  # Default regulation
        "YEAR": "",
        "SEM": "",
        "TYPE": "Regular",
        "CODE": "",
        "BRANCH": "",
        "SUBJECT": "",
        "SUB_CODE": "",
        "COUNT": ""
    }
    
    # Extract session (FN/AN)
    if "FN" in line.upper() or "FORENOON" in line.upper():
        data["N/AN"] = "FN"
    elif "AN" in line.upper() or "AFTERNOON" in line.upper():
        data["N/AN"] = "AN"
    
    # Extract regulation (R22, R20, R18, etc.)
    reg_match = re.search(r"R\d{2}", line, re.IGNORECASE)
    if reg_match:
        data["REG"] = reg_match.group().upper()
    
    # Extract year (1, 2, 3, 4 or I, II, III, IV)
    year_match = re.search(r"\b([1-4]|I{1,3}|IV)\s*(YEAR|YR|Y)?\b", line, re.IGNORECASE)
    if year_match:
        year = year_match.group(1)
        # Convert Roman to Arabic
        roman_to_arabic = {"I": "1", "II": "2", "III": "3", "IV": "4"}
        data["YEAR"] = roman_to_arabic.get(year.upper(), year)
    
    # Extract semester (1, 2 or I, II)
    sem_match = re.search(r"\b([1-2]|I{1,2})\s*(SEM|SEMESTER|S)?\b", line, re.IGNORECASE)
    if sem_match:
        sem = sem_match.group(1)
        roman_to_arabic = {"I": "1", "II": "2"}
        data["SEM"] = roman_to_arabic.get(sem.upper(), sem)
    
    # Extract branch codes (CSE, ECE, EEE, MECH, CIVIL, IT, etc.)
    branch_pattern = r"\b(CSE|ECE|EEE|MECH|MECHANICAL|CIVIL|IT|CSE\(AI&ML\)|CSE\(DS\)|CSE\(AIML\)|AIDS|CSBS)\b"
    branch_match = re.search(branch_pattern, line, re.IGNORECASE)
    if branch_match:
        data["BRANCH"] = branch_match.group().upper()
    
    # Extract subject code (usually alphanumeric like CS101, 15A05301, etc.)
    code_pattern = r"\b([A-Z]{2,4}\d{3,6}[A-Z]?)\b"
    code_match = re.search(code_pattern, line)
    if code_match:
        data["SUB_CODE"] = code_match.group()
    
    # Extract count (number of students)
    count_match = re.search(r"\b(\d{1,4})\s*$", line)
    if count_match:
        data["COUNT"] = count_match.group(1)
    
    # Extract subject name (remaining text)
    # Remove all extracted parts and keep the rest as subject
    subject = line
    for key in ["N/AN", "REG", "YEAR", "SEM", "BRANCH", "SUB_CODE", "COUNT"]:
        if data[key]:
            subject = subject.replace(str(data[key]), "")
    
    # Clean up subject name
    subject = re.sub(r"\s+", " ", subject).strip()
    subject = re.sub(r"[^\w\s\-\(\)&,]", "", subject)
    
    if len(subject) > 3:
        data["SUBJECT"] = subject
    else:
        return None  # Skip if no valid subject found
    
    return data


def save_to_database(df, pdf_filename):
    """
    Save extracted data to SQLite database
    """
    
    if df.empty:
        print("⚠️  No data to save")
        return 0
    
    print(f"\n💾 Saving {len(df)} records to database...")
    
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()
    
    try:
        # Insert records
        for idx, row in df.iterrows():
            cursor.execute("""
            INSERT INTO timetable (
                date, n_an, college, reg, year, sem, type, code, 
                branch, subject, sub_code, count, pdf_name, upload_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                row.get("DATE", ""),
                row.get("N/AN", ""),
                row.get("COLLEGE", ""),
                row.get("REG", ""),
                row.get("YEAR", ""),
                row.get("SEM", ""),
                row.get("TYPE", ""),
                row.get("CODE", ""),
                row.get("BRANCH", ""),
                row.get("SUBJECT", ""),
                row.get("SUB_CODE", ""),
                row.get("COUNT", ""),
                pdf_filename,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
        
        conn.commit()
        print(f"✅ Successfully saved {len(df)} records")
        
        return len(df)
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        conn.rollback()
        return 0
    
    finally:
        conn.close()


def export_to_excel(df, output_file="timetable_output.xlsx"):
    """
    Export DataFrame to Excel file
    """
    
    if df.empty:
        print("⚠️  No data to export")
        return False
    
    try:
        df.to_excel(output_file, index=False, sheet_name="Timetable")
        print(f"✅ Exported to Excel: {output_file}")
        return True
    except Exception as e:
        print(f"❌ Error exporting to Excel: {e}")
        return False


def display_summary(df):
    """
    Display summary statistics of extracted data
    """
    
    if df.empty:
        print("⚠️  No data to summarize")
        return
    
    print("\n" + "="*60)
    print("📊 EXTRACTION SUMMARY")
    print("="*60)
    
    print(f"📋 Total Records: {len(df)}")
    
    if "DATE" in df.columns:
        unique_dates = df["DATE"].nunique()
        print(f"📅 Unique Dates: {unique_dates}")
    
    if "BRANCH" in df.columns:
        unique_branches = df["BRANCH"].nunique()
        print(f"🏢 Unique Branches: {unique_branches}")
        print(f"   Branches: {', '.join(df['BRANCH'].unique())}")
    
    if "SUBJECT" in df.columns:
        unique_subjects = df["SUBJECT"].nunique()
        print(f"📚 Unique Subjects: {unique_subjects}")
    
    print("="*60)
    
    # Display first few records
    print("\n📋 Sample Records (first 5):")
    print(df.head().to_string(index=False))


# Main execution
if __name__ == "__main__":
    print("="*60)
    print("🎓 JNTUH TIMETABLE EXTRACTOR")
    print("="*60)
    
    # Get PDF file path
    pdf_file = input("\n📁 Enter PDF file path: ").strip()
    
    if not os.path.exists(pdf_file):
        print(f"❌ File not found: {pdf_file}")
        exit(1)
    
    # Extract data
    df = extract_timetable(pdf_file)
    
    # Display summary
    display_summary(df)
    
    # Save to database
    if not df.empty:
        pdf_filename = os.path.basename(pdf_file)
        records_saved = save_to_database(df, pdf_filename)
        
        # Export to Excel
        export_to_excel(df)
    
    print("\n✅ Processing complete!")
