import fitz
import pandas as pd
import re
from datetime import datetime


def extract_timetable(file_path):
    """
    Extract timetable from PDF with table structure
    Returns DataFrame with columns: DATE, DAY, BRANCH, SUBJECT_CODE, SUBJECT, EXAM_TYPE
    """
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print("Error opening file:", e)
        return pd.DataFrame()

    all_data = []
    
    for page_num, page in enumerate(doc):
        print(f"Processing page {page_num + 1}")
        
        # Extract tables from page
        page_data = extract_table_from_page(page)
        all_data.extend(page_data)
    
    doc.close()
    
    if not all_data:
        print("No data extracted")
        return pd.DataFrame(columns=["DATE", "DAY", "BRANCH", "SUBJECT_CODE", "SUBJECT", "EXAM_TYPE"])
    
    df = pd.DataFrame(all_data)
    
    # Remove duplicates
    df.drop_duplicates(inplace=True)
    
    # Sort by date
    try:
        df['DATE_SORT'] = pd.to_datetime(df['DATE'], format='%d-%m-%Y')
        df.sort_values('DATE_SORT', inplace=True)
        df.drop('DATE_SORT', axis=1, inplace=True)
    except:
        pass
    
    print(f"Extracted {len(df)} records")
    return df


def extract_table_from_page(page):
    """
    Extract table structure from a single page
    """
    data = []
    
    # Get text with position information
    text_instances = page.get_text("dict")
    blocks = text_instances.get("blocks", [])
    
    # Extract all text with coordinates
    text_elements = []
    
    for block in blocks:
        if "lines" in block:
            for line in block["lines"]:
                for span in line["spans"]:
                    text = span["text"].strip()
                    if text:
                        text_elements.append({
                            "text": text,
                            "x": span["bbox"][0],
                            "y": span["bbox"][1],
                            "x1": span["bbox"][2],
                            "y1": span["bbox"][3]
                        })
    
    # Sort by vertical position (y coordinate)
    text_elements.sort(key=lambda x: (x["y"], x["x"]))
    
    # Find date headers (dates in format DD-MM-YYYY)
    date_pattern = r'\d{2}-\d{2}-\d{4}'
    date_columns = []
    
    for elem in text_elements:
        if re.match(date_pattern, elem["text"]):
            date_columns.append({
                "date": elem["text"],
                "x_start": elem["x"],
                "x_end": elem["x1"],
                "x_center": (elem["x"] + elem["x1"]) / 2
            })
    
    # Remove duplicate dates (keep unique by x position)
    unique_dates = []
    for dc in date_columns:
        is_duplicate = False
        for ud in unique_dates:
            if abs(dc["x_center"] - ud["x_center"]) < 50:  # Within 50 points
                is_duplicate = True
                break
        if not is_duplicate:
            unique_dates.append(dc)
    
    date_columns = sorted(unique_dates, key=lambda x: x["x_center"])
    
    print(f"Found {len(date_columns)} date columns: {[d['date'] for d in date_columns]}")
    
    if not date_columns:
        print("No dates found, trying alternative extraction")
        return extract_simple_format(page)
    
    # Group text elements by rows (similar y coordinates)
    rows = []
    current_row = []
    last_y = None
    
    for elem in text_elements:
        if last_y is None or abs(elem["y"] - last_y) < 10:  # Same row
            current_row.append(elem)
            last_y = elem["y"]
        else:
            if current_row:
                rows.append(current_row)
            current_row = [elem]
            last_y = elem["y"]
    
    if current_row:
        rows.append(current_row)
    
    # Process each row to find branch and subjects
    for row in rows:
        row_text = " ".join([elem["text"] for elem in row])
        
        # Check if this is a branch row
        branch_match = None
        subject_code = ""
        
        # Look for branch patterns
        if "COMPUTER SCIENCE" in row_text.upper() or "ENGINEERING" in row_text.upper():
            branch_match = row_text
            
            # Extract subject code (format: (XX-YYY) or (XX-YYY/ZZZ))
            code_pattern = r'\((\d{2}-[A-Z/()&\s]+)\)'
            code_search = re.search(code_pattern, row_text)
            if code_search:
                subject_code = code_search.group(1).strip()
        
        if not branch_match:
            continue
        
        # For this branch row, find subjects under each date column
        for date_col in date_columns:
            # Find text elements that fall under this date column
            subjects_in_column = []
            
            for elem in row:
                elem_center = (elem["x"] + elem["x1"]) / 2
                
                # Check if element is within this date column (with tolerance)
                if abs(elem_center - date_col["x_center"]) < 100:
                    text = elem["text"].strip()
                    
                    # Filter out branch names and codes from subjects
                    if text and len(text) > 2:
                        if "COMPUTER SCIENCE" not in text.upper() and not re.match(r'\(\d{2}-', text):
                            if text not in ["----", "---", "--", "BRANCH"]:
                                subjects_in_column.append(text)
            
            # Combine subjects for this cell
            if subjects_in_column:
                subject_text = " ".join(subjects_in_column)
                
                # Determine exam type (Regular or Supply)
                exam_type = "Regular"
                if "SUPPLY" in subject_text.upper() or "SUPPL" in subject_text.upper():
                    exam_type = "Supply"
                
                # Get day name
                day_name = get_day_name(date_col["date"])
                
                data.append({
                    "DATE": date_col["date"],
                    "DAY": day_name,
                    "BRANCH": branch_match.strip(),
                    "SUBJECT_CODE": subject_code,
                    "SUBJECT": subject_text.strip(),
                    "EXAM_TYPE": exam_type
                })
    
    return data


def extract_simple_format(page):
    """
    Fallback: Simple line-by-line extraction
    """
    text = page.get_text()
    lines = text.split("\n")
    
    data = []
    date_pattern = r'\d{2}-\d{2}-\d{4}'
    
    dates = []
    for line in lines:
        found_dates = re.findall(date_pattern, line)
        dates.extend(found_dates)
    
    # Remove duplicates
    dates = list(dict.fromkeys(dates))
    
    current_branch = ""
    current_code = ""
    
    for line in lines:
        line = line.strip()
        
        if not line or len(line) < 3:
            continue
        
        # Skip headers
        if any(x in line.upper() for x in ["JAWAHARLAL", "UNIVERSITY", "TIMETABLE", "DIRECTORATE", "TIME→"]):
            continue
        
        # Detect branch
        if "COMPUTER SCIENCE" in line.upper() or "ENGINEERING" in line.upper():
            current_branch = line
            
            code_pattern = r'\((\d{2}-[A-Z/()&\s]+)\)'
            code_search = re.search(code_pattern, line)
            if code_search:
                current_code = code_search.group(1).strip()
            continue
        
        # Detect subjects
        if current_branch and len(line) > 5:
            # Check if line contains a date
            date_in_line = re.search(date_pattern, line)
            
            if not date_in_line:
                # This is likely a subject
                for date in dates:
                    day_name = get_day_name(date)
                    
                    data.append({
                        "DATE": date,
                        "DAY": day_name,
                        "BRANCH": current_branch,
                        "SUBJECT_CODE": current_code,
                        "SUBJECT": line,
                        "EXAM_TYPE": "Regular"
                    })
                    break  # Only add to first date to avoid duplication
    
    return data


def get_day_name(date_str):
    """
    Convert date string (DD-MM-YYYY) to day name
    """
    try:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        return date_obj.strftime("%A").upper()
    except Exception as e:
        print(f"Error parsing date {date_str}: {e}")
        return ""

Now, let's also UPDATE app.py to improve the Excel export with better formatting:

Add this function to app.py (replace the /export_excel route):

# ---------------- EXPORT EXCEL (ENHANCED) ----------------
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

    if df.empty:
        flash("No data to export")
        return redirect("/history")

    # Create Excel with formatting
    file_path = os.path.join("/tmp", "timetable.xlsx")
    
    with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
        # Write main sheet
        df.to_excel(writer, sheet_name='Full Timetable', index=False)
        
        # Create day-wise sheets
        if 'DATE' in df.columns:
            for date in df['DATE'].unique():
                date_df = df[df['DATE'] == date]
                sheet_name = f"{date}"[:31]  # Excel sheet name limit
                date_df.to_excel(writer, sheet_name=sheet_name, index=False)
        
        # Create branch-wise sheet
        if 'BRANCH' in df.columns:
            branch_summary = df.groupby(['DATE', 'BRANCH']).size().reset_index(name='Exam Count')
            branch_summary.to_excel(writer, sheet_name='Branch Summary', index=False)

    return send_file(file_path, as_attachment=True, download_name='timetable_export.xlsx')
