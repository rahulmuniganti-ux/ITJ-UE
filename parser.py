import fitz
import pandas as pd
import re

def extract_timetable(file_path):

    doc = fitz.open(file_path)
    text = ""

    for page in doc:
        text += page.get_text()

    lines = text.split("\n")

    data = []

    for line in lines:

        date = re.search(r"\d{2}-\d{2}-\d{4}", line)

        if date:

            subject = line.replace(date.group(), "").strip()

            if len(subject) < 3:
                continue

            data.append({
                "DATE": date.group(),
                "SESSION": "AN",
                "BRANCH": "CSE",
                "SUBJECT": subject
            })

    return pd.DataFrame(data)