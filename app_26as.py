import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math

# ---------------- UI CONFIG ----------------
st.set_page_config("🦚 TDS Challan Extractor", layout="wide")

# ----------- CSS -----------
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#020617,#0f172a,#020617); color:white;}
h1 {text-align:center;font-size:48px;
background:linear-gradient(90deg,#38bdf8,#22c55e);
-webkit-background-clip:text;color:transparent;}
.quote{background:rgba(255,255,255,0.05);
padding:20px;border-radius:15px;text-align:center;}
</style>
""", unsafe_allow_html=True)

# ----------- TITLE -----------
st.markdown("<h1>🕉️ TDS CHALLAN EXTRACTOR</h1>", unsafe_allow_html=True)

# ----------- KRISHNA QUOTE -----------
st.markdown("""
<div class="quote">
कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।  
"You have the right to perform your duty, not the fruits." — Lord Krishna
</div>
""", unsafe_allow_html=True)

# ----------- FILE UPLOAD -----------
files = st.file_uploader("📄 Upload Challans in PDF", type="pdf", accept_multiple_files=True)

# ----------- EXCEL EXPORT -----------
def to_excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="TDS")
        ws=writer.sheets["TDS"]
        for c in ws[1]:
            c.font=Font(bold=True)
    return buf.getvalue()

# ----------- EXTRACTION -----------
def extract_all(text):

    challans=text.split("Challan Receipt")
    rows=[]

    for ch in challans:

        if not re.search(r"Challan No\s*:\s*\d+",ch):
            continue

        def f(p):
            m=re.search(p,ch)
            return m.group(1).replace(",","") if m else "0"

        dep_date_str=f(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})")
        if dep_date_str=="0":
            continue

        dep_date=datetime.strptime(dep_date_str,"%d-%b-%Y")

        # -------- TDS MONTH --------
        tds_month_date = dep_date - relativedelta(months=1)
        tds_month = tds_month_date.strftime("%B")

        # -------- DUE DATE --------
        due_date = (tds_month_date + relativedelta(months=1)).replace(day=7)

        # -------- DELAY DAYS --------
        delay_days = (dep_date - due_date).days

        tax=float(f(r"A Tax ₹\s*([\d,]+)"))
        interest=float(f(r"D Interest ₹\s*([\d,]+)"))

        # -------- EFFECTIVE MONTH --------
        if interest>0 and tax>0:
            months_delay = math.ceil(interest/(tax*0.015))
            eff_month = (dep_date - relativedelta(months=months_delay)).strftime("%B")
        else:
            eff_month = tds_month

        rows.append({
            "Financial Year":f(r"Financial Year\s*:\s*([\d\-]+)"),
            "TDS Month":tds_month,
            "Deposit Date":dep_date_str,
            "Delay (Days)":delay_days,
            "Effective Month":eff_month,
            "Nature":f(r"Nature of Payment\s*:\s*(\w+)"),
            "Challan No":f(r"Challan No\s*:\s*(\d+)"),
            "Tax":tax,
            "Surcharge":float(f(r"B Surcharge ₹\s*([\d,]+)")),
            "Cess":float(f(r"C Cess ₹\s*([\d,]+)")),
            "Interest":interest,
            "Penalty":float(f(r"E Penalty ₹\s*([\d,]+)")),
            "Fee 234E":float(f(r"F Fee under section 234E ₹\s*([\d,]+)")),
            "Total":float(f(r"Total \(A\+B\+C\+D\+E\+F\) ₹\s*([\d,]+)"))
        })

    return rows

# ----------- PROCESS -----------
if files:

    all_rows=[]

    for f in files:
        text=""
        with pdfplumber.open(f) as pdf:
            for p in pdf.pages:
                if p.extract_text():
                    text+=p.extract_text()+"\n"

        all_rows+=extract_all(text)

    if all_rows:

        df=pd.DataFrame(all_rows)

        st.success("🦚 Challans Extracted Successfully!")

        c1,c2,c3=st.columns(3)
        c1.metric("Total Challans",len(df))
        c2.metric("Total Tax ₹",f"{df['Tax'].sum():,.0f}")
        c3.metric("Total Deposit ₹",f"{df['Total'].sum():,.0f}")

        st.dataframe(df,use_container_width=True)

        st.download_button(
            "📥 Download Excel",
            data=to_excel(df),
            file_name="TDS_Challans.xlsx"
        )

    else:
        st.warning("⚠️ No challans detected.")

# ----------- FOOTER -----------
st.caption("⚙️ Tool developed by Abhishek Jakkula - jakkulaabhishek5@gmail.com 🦚")
