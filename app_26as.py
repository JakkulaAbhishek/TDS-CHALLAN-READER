import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
import time

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Krishna TDS Suite",
    layout="wide"
)

# ---------- PREMIUM KRISHNA UI ----------
st.markdown("""
<style>

.stApp {
background: linear-gradient(180deg,#020617,#0b1d3a,#020617);
color:white;
font-family: 'Segoe UI';
}

/* Title */
.title {
text-align:center;
font-size:52px;
font-weight:700;
color:#38bdf8;
text-shadow:0 0 25px #38bdf8;
}

/* Krishna card */
.krishna {
text-align:center;
padding:25px;
border-radius:18px;
background:rgba(56,189,248,0.08);
border:1px solid rgba(56,189,248,0.4);
box-shadow:0 0 40px rgba(56,189,248,0.25);
}

/* Glass */
.glass {
background:rgba(255,255,255,0.05);
padding:25px;
border-radius:15px;
}

/* Upload box */
[data-testid="stFileUploader"] {
background:rgba(56,189,248,0.05);
padding:20px;
border-radius:15px;
border:1px dashed #38bdf8;
}

footer {visibility:hidden;}

</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="title">🦚 TDS Challan Extractor</div>', unsafe_allow_html=True)

# ---------- PEACOCK ANIMATION ----------
ph = st.empty()
for i in range(3):
    ph.markdown(
        "<h3 style='text-align:center;color:#38bdf8'>🦚 Divine Compliance 🦚</h3>",
        unsafe_allow_html=True
    )
    time.sleep(0.4)

# ---------- KRISHNA SLOKA ----------
st.markdown("""
<div class="krishna">

🕉️ कर्मण्येवाधिकारस्ते मा फलेषु कदाचन |  
मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि ||

*"You have a right to perform your prescribed duties, but you are not entitled to the fruits of your actions. Never consider yourself to be the cause of the results of your activities, nor be attached to inaction."*

</div>
""", unsafe_allow_html=True)

st.write("")

# ---------- MAIN PARSER ----------
st.markdown('<div class="glass">', unsafe_allow_html=True)

files = st.file_uploader(
    "📄 Upload TDS Challans",
    type="pdf",
    accept_multiple_files=True
)

# ---------- FUNCTIONS ----------
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
        "Surcharge":find(r"B Surcharge ₹\s*([\d,]+)",t),
        "Cess":find(r"C Cess ₹\s*([\d,]+)",t),
        "Interest":find(r"D Interest ₹\s*([\d,]+)",t),
        "Penalty":find(r"E Penalty ₹\s*([\d,]+)",t),
        "Fee":find(r"F Fee under section 234E ₹\s*([\d,]+)",t),
        "Total":find(r"Total \(A\+B\+C\+D\+E\+F\) ₹\s*([\d,]+)",t)
    }

def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w:
        df.to_excel(w,index=False)
    return buf.getvalue()

# ---------- PROCESS ----------
if files:

    rows=[]
    s=1

    for f in files:

        text=""
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text+=p.extract_text()

        d=extract(text)

        if d["Date"]=="0":
            continue

        dep=datetime.strptime(d["Date"],"%d-%b-%Y")

        tax=float(d["Tax"])
        interest=float(d["Interest"])

        # Interest provision logic
        delay=round(interest/(tax*0.015)) if tax>0 and interest>0 else 1
        tds_month=(dep-relativedelta(months=delay)).strftime("%B")

        rows.append({
            "S.No":s,
            "Financial Year":d["FY"],
            "TDS Month":tds_month,
            "Deposit Date":d["Date"],
            "Nature":d["Nature"],
            "Challan No":d["Challan"],
            "Tax":tax,
            "Surcharge":float(d["Surcharge"]),
            "Cess":float(d["Cess"]),
            "Interest":interest,
            "Penalty":float(d["Penalty"]),
            "Fee 234E":float(d["Fee"]),
            "Total":float(d["Total"])
        })

        s+=1

    df=pd.DataFrame(rows)

    st.success("✅ Challans Processed Successfully")

    st.dataframe(df,use_container_width=True)

    st.download_button(
        "📥 Download Excel",
        data=excel(df),
        file_name="TDS_Report.xlsx"
    )

st.markdown('</div>', unsafe_allow_html=True)

st.caption("⚙️ Tool developed by Abhishek Jakkula")
