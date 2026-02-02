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

# ---------- UI ----------
st.markdown("""
<style>
.stApp {
background: linear-gradient(180deg,#020617,#0b1d3a,#020617);
color:white;
font-family:Segoe UI;
}
.title {
text-align:center;
font-size:48px;
font-weight:700;
color:#38bdf8;
text-shadow:0 0 20px #38bdf8;
}
.quote {
text-align:center;
padding:20px;
background:rgba(56,189,248,0.08);
border-radius:15px;
font-size:18px;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🧾 TDS Challan Extractor</div>', unsafe_allow_html=True)

# ---------- KRISHNA QUOTE ----------
st.markdown("""
<div class="quote">

🕉️ **यउद्धरेदात्मनात्मानं नात्मानमवसादयेत् । आत्मैव ह्यात्मनो बन्धुरात्मैव रिपुरात्मनः ॥**  
*uddhared ātmanātmānaṁ nātmānam avasādayet | ātmaiva hyātmano bandhur ātmaiva ripur ātmanaḥ ||*  

"Elevate yourself through the power of your mind, and do not degrade yourself. For the mind can be the friend of the soul, and the mind can also be the enemy of the soul." — Lord Krishna

</div>
""", unsafe_allow_html=True)

# ---------- FILE UPLOAD ----------
files = st.file_uploader(
    "📄 Upload TDS Challans",
    type="pdf",
    accept_multiple_files=True
)

# ---------- REGEX HELPER ----------
def find(p,t):
    m=re.search(p,t)
    return m.group(1).replace(",","") if m else "0"

# ---------- EXTRACTION ----------
def extract(t):
    return {
        "FY":find(r"Financial Year\s*:\s*([\d\-]+)",t),
        "Nature":find(r"Nature of Payment\s*:\s*(\S+)",t),
        "Challan":find(r"Challan No\s*:\s*(\d+)",t),
        "Date":find(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})",t),

        "Tax":find(r"A Tax ₹\s*([\d,]+)",t),
        "Surcharge":find(r"B Surcharge ₹\s*([\d,]+)",t),
        "Cess":find(r"C Cess ₹\s*([\d,]+)",t),
        "Interest":find(r"D Interest ₹\s*([\d,]+)",t),
        "Penalty":find(r"E Penalty ₹\s*([\d,]+)",t),
        "Fee":find(r"F Fee under section 234E ₹\s*([\d,]+)",t),
        "Total":find(r"Total \(A\+B\+C\+D\+E\+F\) ₹\s*([\d,]+)",t)
    }

# ---------- EXCEL EXPORT ----------
def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="TDS Data")
        ws=writer.sheets["TDS Data"]

        for cell in ws[1]:
            cell.font=Font(bold=True)

        for col in ws.columns:
            max_len=max(len(str(c.value)) for c in col)
            ws.column_dimensions[col[0].column_letter].width=max_len+2

    return buf.getvalue()

# ---------- PROCESS ----------
if files:

    rows=[]
    progress=st.progress(0)

    for i,f in enumerate(files):

        text=""
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text+=p.extract_text()

        if not text.strip():
            st.warning(f"OCR needed: {f.name}")
            continue

        d=extract(text)

        if d["Date"]=="0":
            continue

        dep=datetime.strptime(d["Date"],"%d-%b-%Y")

        tax=float(d["Tax"])
        interest=float(d["Interest"])

        # Interest-month logic
        delay_months = math.ceil(
            interest/(tax*0.015)
        ) if tax>0 and interest>0 else 1

        tds_month=(dep-relativedelta(months=delay_months)).strftime("%B")

        # Due date & delay days
        due=dep.replace(day=7)
        delay_days=(dep-due).days

        # Validation
        total_calc=sum([
            float(d["Tax"]),
            float(d["Surcharge"]),
            float(d["Cess"]),
            float(d["Interest"]),
            float(d["Penalty"]),
            float(d["Fee"])
        ])

        if abs(total_calc-float(d["Total"]))>1:
            st.warning(f"⚠️ Total mismatch in {f.name}")

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

        progress.progress((i+1)/len(files))

    df=pd.DataFrame(rows)

    # ---------- DASHBOARD ----------
    st.success("✅ Processing Complete")

    c1,c2,c3,c4=st.columns(4)
    c1.metric("Challans",len(df))
    c2.metric("Total Tax",f"₹ {df['Tax'].sum():,.0f}")
    c3.metric("Total Interest",f"₹ {df['Interest'].sum():,.0f}")
    c4.metric("Late Cases",(df["Interest"]>0).sum())

    st.dataframe(df,use_container_width=True)

    st.download_button(
        "📥 Download Excel",
        data=excel(df),
        file_name="TDS_Report.xlsx"
    )

st.caption("⚙️ Tool developed by Abhishek Jakkula 🦚  "mail" - "jakkulaabhishek5@gmail.com")
