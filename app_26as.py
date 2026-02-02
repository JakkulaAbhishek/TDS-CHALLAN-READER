import streamlit as st
import pdfplumber
import re
import pandas as pd
import math
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
from openpyxl.styles import Font

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="TDS Challan Extractor", layout="wide")

# ---------- LUXURY GLASSMORPHISM UI ----------
st.markdown("""
<style>

.stApp {
background: linear-gradient(135deg,#e3f2fd,#ffffff,#e3f2fd);
font-family:'Segoe UI',sans-serif;
color:#1f2937;
}

/* Header */
.header {
text-align:center;
font-size:46px;
font-weight:800;
background:linear-gradient(90deg,#1a73e8,#00c6ff);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
}

/* Glass card */
.glass {
background: rgba(255,255,255,0.55);
backdrop-filter: blur(14px);
padding:22px;
border-radius:16px;
box-shadow:0 8px 32px rgba(31,38,135,0.2);
margin-bottom:20px;
}

/* Metric cards */
.metric {
background:linear-gradient(135deg,#1a73e8,#42a5f5);
padding:20px;
border-radius:14px;
color:white;
text-align:center;
box-shadow:0 6px 18px rgba(0,0,0,0.15);
}

/* Upload */
[data-testid="stFileUploader"] {
background: rgba(255,255,255,0.6);
backdrop-filter: blur(10px);
padding:20px;
border-radius:14px;
}

/* Button */
.stDownloadButton button {
background:linear-gradient(90deg,#1a73e8,#42a5f5);
color:white;
border:none;
padding:12px 22px;
border-radius:10px;
font-size:16px;
transition:0.3s;
}
.stDownloadButton button:hover {
transform:scale(1.07);
}

footer {visibility:hidden;}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="header">🧾 TDS Challan Extractor</div>', unsafe_allow_html=True)

# ---------- KRISHNA QUOTE ----------
st.markdown("""
<div class="glass" style="text-align:center">

🕉️ <b>नियतं कुरु कर्म त्वं कर्म ज्यायो ह्यकर्मणः</b><br>
<i>Perform your duty, for action is superior to inaction — Lord Krishna</i>

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

        rows.append({
            "FY":d["FY"],
            "TDS Month":tds_month,
            "Deposit Date":d["Date"],
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

    # ---------- ANIMATED METRICS ----------
    c1,c2,c3,c4=st.columns(4)

    def animate_metric(col,label,value):
        for i in range(0,value+1,max(1,value//30 or 1)):
            col.markdown(f'<div class="metric"><h4>{label}</h4><h2>{i}</h2></div>',unsafe_allow_html=True)
            time.sleep(0.01)
        col.markdown(f'<div class="metric"><h4>{label}</h4><h2>{value}</h2></div>',unsafe_allow_html=True)

    animate_metric(c1,"Challans",len(df))
    animate_metric(c2,"Late Cases",(df["Interest"]>0).sum())
    animate_metric(c3,"Total Tax ₹",int(df["Tax"].sum()))
    animate_metric(c4,"Interest ₹",int(df["Interest"].sum()))

    # ---------- TABLE ----------
    st.markdown('<div class="glass">',unsafe_allow_html=True)
    st.dataframe(df,use_container_width=True)
    st.markdown('</div>',unsafe_allow_html=True)

    # ---------- DOWNLOAD ----------
    st.download_button(
        "📥 Download Excel",
        data=excel(df),
        file_name="TDS_Report.xlsx"
    )

st.caption("⚙️ Tool developed by Abhishek Jakkula")
