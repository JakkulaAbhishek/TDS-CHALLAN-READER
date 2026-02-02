import streamlit as st
import pdfplumber
import re
import pandas as pd
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
from openpyxl.styles import Font

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="TDS Challan Extractor", layout="wide")

# ---------- LORD KRISHNA QUOTE ----------
st.markdown("""
### 🕉️ Bhagavad Gita Wisdom

**यउद्धरेदात्मनात्मानं नात्मानमवसादयेत् ।  
आत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः ॥**

*“Elevate yourself through your mind.  
The mind can be your best friend or your worst enemy.”* — Lord Krishna
""")

# ---------- FILE UPLOAD ----------
files = st.file_uploader(
    "📄 Upload TDS Challans",
    type="pdf",
    accept_multiple_files=True
)

# ---------- REGEX HELPER ----------
def find(p,t):
    m=re.search(p,t,re.S)
    return m.group(1).replace(",","").strip() if m else "0"

# ---------- CHALLAN BLOCK PATTERN ----------
CHALLAN_PATTERN = re.compile(
    r"(Challan No\s*:.*?Total.*?\d+)",
    re.S
)

# ---------- EXTRACTION ----------
def extract_block(t):
    return {
        "FY":find(r"Financial Year\s*:\s*([\d\-]+)",t),
        "Nature":find(r"Nature of Payment\s*:\s*([A-Za-z0-9]+)",t),
        "Challan":find(r"Challan No\s*:\s*(\d+)",t),
        "Date":find(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})",t),

        "Tax":find(r"A Tax.*?₹\s*([\d,]+)",t),
        "Surcharge":find(r"B Surcharge.*?₹\s*([\d,]+)",t),
        "Cess":find(r"C Cess.*?₹\s*([\d,]+)",t),
        "Interest":find(r"D Interest.*?₹\s*([\d,]+)",t),
        "Penalty":find(r"E Penalty.*?₹\s*([\d,]+)",t),
        "Fee":find(r"F Fee.*?₹\s*([\d,]+)",t),
        "Total":find(r"Total.*?₹\s*([\d,]+)",t)
    }

# ---------- EXCEL EXPORT ----------
def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="TDS Data")
        ws = writer.sheets["TDS Data"]

        for cell in ws[1]:
            cell.font = Font(bold=True)

        for col in ws.columns:
            max_len=max(len(str(c.value)) for c in col)
            ws.column_dimensions[col[0].column_letter].width=max_len+2

    return buf.getvalue()

# ---------- PROCESS ----------
if files:

    rows=[]

    for f in files:

        text=""
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text+=p.extract_text()+"\n"

        challans = CHALLAN_PATTERN.findall(text)

        for ch in challans:

            d=extract_block(ch)

            if d["Date"]=="0":
                continue

            dep=datetime.strptime(d["Date"],"%d-%b-%Y")

            tax=float(d["Tax"])
            interest=float(d["Interest"])

            delay_months = math.ceil(
                interest/(tax*0.015)
            ) if tax>0 and interest>0 else 0

            tds_month=(dep-relativedelta(months=delay_months)).strftime("%B")

            # Due date = 7th next month
            due=(dep.replace(day=1)+relativedelta(months=1)).replace(day=7)
            delay_days=max((dep-due).days,0)

            rows.append({
                "Financial Year":d["FY"],
                "TDS Month":tds_month,
                "Deposit Date":d["Date"],
                "Delay (Days)":delay_days,
                "Nature":d["Nature"],
                "Challan No":d["Challan"],
                "Tax":tax,
                "Surcharge":float(d["Surcharge"]),
                "Cess":float(d["Cess"]),
                "Interest":interest,
                "Penalty":float(d["Penalty"]),
                "Fee 234E":float(d["Fee"]),
                "Total":float(d["Total"]),
                "Status":"Late ⚠️" if interest>0 else "On Time ✅"
            })

    if rows:

        df=pd.DataFrame(rows)

        st.success("✅ Extraction Complete")

        st.dataframe(df,use_container_width=True)

        st.download_button(
            "📥 Download Excel",
            data=excel(df),
            file_name="TDS_Report.xlsx"
        )

    else:
        st.warning("No challans detected")

st.caption("⚙️ Tool developed by Abhishek Jakkula - ABHISHEKJAKKULA5@GMAIL.COM 🦚")
