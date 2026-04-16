```python
import fitz
import pandas as pd
import re

def extract_timetable(file_path):
    try:
        doc = fitz.open(file_path)
    except Exception as e:
        print("Error opening file:", e)
        return pd.DataFrame(columns=["DATE","SESSION","BRANCH","SUBJECT"])

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

    # ✅ Correct place (OUTSIDE loop)
    if not data:
        return pd.DataFrame(columns=["DATE","SESSION","BRANCH","SUBJECT"])

    return pd.DataFrame(data)
```
