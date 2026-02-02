import streamlit as st
import pdfplumber
import re
import pandas as pd
import math
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
from openpyxl.styles import Font

st.set_page_config(page_title="TDS Challan Extractor", layout="wide")

files = st.file_uploader("Upload Challans", type="pdf", accept_multiple_files=True)

def find(p,t):
    m=re.search(p,t,re.S)
    return m.group(1).replace(",","").strip() if m else "0"

# --------- STRONG CHALLAN PATTERN ----------
CHALLAN_PATTERN = re.compile(
    r"(Challan No\s*:.*?Total \(A\+B\+C\+D\+E\+F\).*?\d+)",
    re.S
)

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

def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False)
        ws=writer.active
        for cell in ws[1]:
            cell.font=Font(bold=True)
    return buf.getvalue()

# -------- PROCESS ----------
if files:

    rows=[]

    for f in files:

        text=""
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text+=p.extract_text()+"\n"

        # 🔥 Extract each challan properly
        challans = CHALLAN_PATTERN.findall(text)

        for ch in challans:

            d=extract_block(ch)

            if d["Date"]=="0":
                continue

            dep=datetime.strptime(d["Date"],"%d-%b-%Y")

            tax=float(d["Tax"])
            interest=float(d["Interest"])

            # Interest months
            delay_months = math.ceil(
                interest/(tax*0.015)
            ) if tax>0 and interest>0 else 0

            tds_month=(dep-relativedelta(months=delay_months)).strftime("%B")

            # ✅ Correct due date = 7th of NEXT month
            due=(dep.replace(day=1)+relativedelta(months=1)).replace(day=7)

            delay_days=max((dep-due).days,0)

            rows.append({
                "Financial Year":d["FY"],
                "TDS Month":tds_month,
                "Deposit Date":d["Date"],
                "Delay (Days)":delay_days,
                "Nature":d["Nature"],
                "Challan No":d["Challan"],
                "Tax":float(d["Tax"]),
                "Surcharge":float(d["Surcharge"]),
                "Cess":float(d["Cess"]),
                "Interest":interest,
                "Penalty":float(d["Penalty"]),
                "Fee 234E":float(d["Fee"]),
                "Total":float(d["Total"]),
                "Status":"Late ⚠️" if interest>0 else "On Time ✅"
            })

    df=pd.DataFrame(rows)

    st.dataframe(df,use_container_width=True)

    st.download_button(
        "Download Excel",
        data=excel(df),
        file_name="TDS_Report.xlsx"
    )

st.caption("Tool developed by Abhishek Jakkula - ABHISHEKJAKKULA5@GMAIL.COM")
