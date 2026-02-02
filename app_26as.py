import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font
from datetime import datetime

# ---------------- UI CONFIG ----------------
st.set_page_config("TDS Challan Extractor", layout="wide")

# ----------- ANIMATED CSS -----------
st.markdown("""
<style>

.stApp {
background: linear-gradient(135deg,#020617,#0f172a,#020617);
color:white;
font-family:Segoe UI;
}

h1 {
text-align:center;
font-size:50px;
background: linear-gradient(90deg,#38bdf8,#22c55e);
-webkit-background-clip:text;
color:transparent;
animation: glow 2s infinite alternate;
}

@keyframes glow {
from { text-shadow:0 0 10px #38bdf8;}
to { text-shadow:0 0 25px #22c55e;}
}

.quote{
background:rgba(255,255,255,0.05);
padding:20px;
border-radius:15px;
text-align:center;
font-size:18px;
}

</style>
""", unsafe_allow_html=True)

# ----------- TITLE -----------
st.markdown("<h1>🧾 TDS CHALLAN EXTRACTOR</h1>", unsafe_allow_html=True)

# ----------- LORD KRISHNA QUOTE -----------
st.markdown("""
<div class="quote">

🕉️ **कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।**  
**मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥**

*"You have the right to perform your duty,  
but not to the fruits of your actions."*  
— Lord Krishna

</div>
""", unsafe_allow_html=True)

# ----------- FILE UPLOAD -----------
files = st.file_uploader("📄 Upload ITNS 281 Challans", type="pdf", accept_multiple_files=True)

# ----------- EXCEL EXPORT -----------
def to_excel(df):
    buf=BytesIO()
    with pd.ExcelWriter(buf,engine="openpyxl") as writer:
        df.to_excel(writer,index=False,sheet_name="TDS")
        ws=writer.sheets["TDS"]
        for c in ws[1]:
            c.font=Font(bold=True)
    return buf.getvalue()

# ----------- EXTRACTION LOGIC -----------
def extract_all(text):

    challans=text.split("Challan Receipt")

    rows=[]

    for ch in challans:

        challan_no=re.search(r"Challan No\s*:\s*(\d+)",ch)
        if not challan_no:
            continue

        def f(p):
            m=re.search(p,ch)
            return m.group(1).replace(",","") if m else "0"

        rows.append({
            "Financial Year":f(r"Financial Year\s*:\s*([\d\-]+)"),
            "Nature":f(r"Nature of Payment\s*:\s*(\w+)"),
            "Challan No":f(r"Challan No\s*:\s*(\d+)"),
            "Deposit Date":f(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})"),
            "Tax":float(f(r"A Tax ₹\s*([\d,]+)")),
            "Surcharge":float(f(r"B Surcharge ₹\s*([\d,]+)")),
            "Cess":float(f(r"C Cess ₹\s*([\d,]+)")),
            "Interest":float(f(r"D Interest ₹\s*([\d,]+)")),
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

        st.success("✅ Challans Extracted Successfully!")

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
        st.warning("⚠️ No challans detected. Try another file.")

# ----------- FOOTER -----------
st.caption("⚙️ Tool developed by Abhishek Jakkula - ABHISHEKJAKKULA5@GMAIL.COM 🦚")
