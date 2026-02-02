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

# ---------- GOOGLE STYLE UI ----------
st.markdown("""
<style>

.stApp {
background:#f6f8fc;
font-family:'Inter',sans-serif;
color:#202124 !important;
}

/* Force dark text everywhere */
html, body, [class*="css"] {
color:#202124 !important;
}

/* Header */
.header {
text-align:center;
font-size:42px;
font-weight:700;
color:#1a73e8;
}

/* Quote Card */
.quote {
text-align:center;
padding:18px;
background:white;
border-radius:12px;
box-shadow:0 4px 20px rgba(0,0,0,0.08);
margin-bottom:25px;
color:#202124;
}

/* Animated Button */
.stDownloadButton button {
background:#1a73e8;
color:white;
border:none;
padding:12px 22px;
border-radius:8px;
font-size:16px;
transition:0.3s;
}
.stDownloadButton button:hover {
transform:scale(1.08);
background:#1558c0;
}

/* Upload box */
[data-testid="stFileUploader"] {
background:white;
padding:20px;
border-radius:12px;
border:1px solid #e0e3eb;
box-shadow:0 4px 15px rgba(0,0,0,0.05);
color:#202124;
}

footer {visibility:hidden;}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="header">🧾 TDS Challan Extractor</div>', unsafe_allow_html=True)

# ---------- KRISHNA QUOTE ----------
st.markdown("""
<div class="quote">

🕉️ <b>कर्मण्येवाधिकारस्ते मा फलेषु कदाचन</b><br>
<i>You have the right to perform your duty, but not to the results — Lord Krishna</i>

</div>
""", unsafe_allow_html=True)

# ---------- FILE UPLOAD ----------
files = st.file_uploader(
    "📄 Upload TDS Challans pdfs",
    type="pdf",
    accept_multiple_files=True
)

# ---------- REGEX ----------
def find(p,t):
    m=re.search(p,t)
    return m.group(1).replace(",","") if m else "0"

def extract(t):
    return {
        "FY":find(r"Financial Year\s*:\s*([\d\-]+)",t),
        "Nature":find(r"Nature of Payment\s*:\s*(\S+)",t),
        "Challan":find(r"Challan No\s*:\s*(\d+)",t),
        "Date":find(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})",t),
        "Tax":find(r"A Tax ₹\s*([\d,]+)",t),
        "Interest":find(r"D Interest ₹\s*([\d,]+)",t),
        "Total":find(r"Total \(A\+B\+C\+D\+E\+F\) ₹\s*([\d,]+)",t)
    }

# ---------- EXCEL ----------
def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False)
        ws=writer.active

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
            continue

        d=extract(text)
        if d["Date"]=="0":
            continue

        dep=datetime.strptime(d["Date"],"%d-%b-%Y")

        tax=float(d["Tax"])
        interest=float(d["Interest"])

        delay_months=math.ceil(interest/(tax*0.015)) if tax>0 and interest>0 else 1
        tds_month=(dep-relativedelta(months=delay_months)).strftime("%B")

        due=dep.replace(day=7)
        delay_days=(dep-due).days

        rows.append({
            "Financial Year":d["FY"],
            "TDS Month":tds_month,
            "Deposit Date":d["Date"],
            "Delay Days":delay_days,
            "Nature":d["Nature"],
            "Challan No":d["Challan"],
            "Tax":tax,
            "Interest":interest,
            "Total":float(d["Total"]),
            "Status":"Late" if interest>0 else "On Time"
        })

        progress.progress((i+1)/len(files))

    df=pd.DataFrame(rows)

    st.success("✅ Processing Complete")

    # ---------- METRICS ----------
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Challans",len(df))
    c2.metric("Total Tax",f"₹ {df['Tax'].sum():,.0f}")
    c3.metric("Total Interest",f"₹ {df['Interest'].sum():,.0f}")
    c4.metric("Late Cases",(df["Interest"]>0).sum())

    # ---------- TABLE ----------
    st.dataframe(df,use_container_width=True)

    # ---------- CHARTS ----------
    st.subheader("📊 Analytics Dashboard")
    st.bar_chart(df[["Tax","Interest"]])
    st.bar_chart(df["Status"].value_counts())

    # ---------- DOWNLOAD ----------
    st.download_button(
        "📥 Download Excel",
        data=excel(df),
        file_name="TDS_Report.xlsx"
    )

st.caption("⚙️ Tool developed by Abhishek Jakkula")
