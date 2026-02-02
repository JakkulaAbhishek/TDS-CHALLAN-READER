import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="TDS Divine Parser PRO",
    page_icon="🦚",
    layout="wide"
)

# ---------- BEAUTIFUL UI ----------
st.markdown("""
<style>

.stApp {
    background: linear-gradient(135deg,#141e30,#243b55);
    color:white;
}

.title {
    text-align:center;
    font-size:42px;
    font-weight:bold;
    background: linear-gradient(45deg,gold,white);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}

.glass {
    background: rgba(255,255,255,0.12);
    padding:25px;
    border-radius:15px;
    backdrop-filter: blur(12px);
    box-shadow: 0 0 25px rgba(255,255,255,0.15);
}

.footer {
    text-align:center;
    color:#ccc;
}

</style>
""", unsafe_allow_html=True)

st.markdown('<p class="title">🦚 TDS Divine Parser PRO</p>', unsafe_allow_html=True)

st.markdown('<div class="glass">', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📄 Upload TDS Challan PDFs",
    type="pdf",
    accept_multiple_files=True
)

# ---------- FUNCTIONS ----------
def find(pattern,text):
    m=re.search(pattern,text)
    return m.group(1).replace(",","").strip() if m else "0"

def extract(text):
    return {
        "FY": find(r"Financial Year\s*:\s*([\d\-]+)",text),
        "Nature": find(r"Nature of Payment\s*:\s*(\S+)",text),
        "Challan": find(r"Challan No\s*:\s*(\d+)",text),
        "Date": find(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})",text),

        "Tax": find(r"A Tax ₹\s*([\d,]+)",text),
        "Surcharge": find(r"B Surcharge ₹\s*([\d,]+)",text),
        "Cess": find(r"C Cess ₹\s*([\d,]+)",text),
        "Interest": find(r"D Interest ₹\s*([\d,]+)",text),
        "Penalty": find(r"E Penalty ₹\s*([\d,]+)",text),
        "Fee234E": find(r"F Fee under section 234E ₹\s*([\d,]+)",text),
        "Total": find(r"Total \(A\+B\+C\+D\+E\+F\) ₹\s*([\d,]+)",text)
    }

def excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as w:
        df.to_excel(w,index=False)
    return buf.getvalue()

# ---------- MAIN ----------
if uploaded_files:

    rows=[]
    s=1

    for file in uploaded_files:
        try:
            text=""
            with pdfplumber.open(file) as pdf:
                for p in pdf.pages:
                    if p.extract_text():
                        text+=p.extract_text()

            d=extract(text)

            if d["Date"]=="0":
                continue

            dep_date=datetime.strptime(d["Date"],"%d-%b-%Y")

            tax=float(d["Tax"])
            interest=float(d["Interest"])

            # ---------- INTEREST PROVISION LOGIC ----------
            delay_months=0
            if interest>0 and tax>0:
                delay_months=round(interest/(tax*0.015))

            tds_month=(dep_date-relativedelta(months=delay_months if delay_months>0 else 1)).strftime("%B")

            rows.append({
                "S.No":s,
                "Financial Year":d["FY"],
                "TDS Month":tds_month,
                "Date of Deposit":d["Date"],
                "Nature of Payment":d["Nature"],
                "Challan No":d["Challan"],

                "Tax (₹)":tax,
                "Surcharge (₹)":float(d["Surcharge"]),
                "Cess (₹)":float(d["Cess"]),
                "Interest (₹)":interest,
                "Penalty (₹)":float(d["Penalty"]),
                "Fee 234E (₹)":float(d["Fee234E"]),
                "Total (₹)":float(d["Total"])
            })

            s+=1

        except:
            st.warning(f"Error in {file.name}")

    if rows:

        df=pd.DataFrame(rows)

        st.success(f"✅ Processed {len(df)} Challans")

        st.dataframe(df,use_container_width=True)

        st.download_button(
            "📥 Download Excel",
            data=excel(df),
            file_name="TDS_Full_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("""
        <h3 style='text-align:center;color:gold;'>
        🌸 “Perform your duty with integrity.” – Lord Krishna
        </h3>
        """,unsafe_allow_html=True)

st.markdown("</div>",unsafe_allow_html=True)

st.markdown("---")
st.markdown('<p class="footer">⚙️ Tool developed by Abhishek Jakkula</p>',unsafe_allow_html=True)
