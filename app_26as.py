import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
import os

# ---------- SAFE AI SETUP ----------
api_key = st.secrets.get("OPENAI_API_KEY", None) if hasattr(st,"secrets") else None
client=None

if api_key:
    from openai import OpenAI
    client=OpenAI(api_key=api_key)

# ---------- PAGE CONFIG ----------
st.set_page_config(layout="wide",page_title="TDS Krishna Suite")

# ---------- PREMIUM UI ----------
st.markdown("""
<style>

.stApp {
background: radial-gradient(circle at top,#0f172a,#020617);
color:white;
font-family: 'Segoe UI';
}

/* Title */
.title {
text-align:center;
font-size:52px;
font-weight:700;
background:linear-gradient(90deg,#facc15,#fde68a);
-webkit-background-clip:text;
-webkit-text-fill-color:transparent;
margin-bottom:10px;
}

/* Krishna card */
.krishna {
text-align:center;
padding:20px;
border-radius:20px;
background:rgba(255,215,0,0.08);
border:1px solid rgba(255,215,0,0.3);
box-shadow:0 0 30px rgba(255,215,0,0.2);
}

/* Glass container */
.glass {
background:rgba(255,255,255,0.05);
padding:25px;
border-radius:18px;
box-shadow:0 0 40px rgba(0,0,0,0.6);
}

/* Hide default uploader text */
[data-testid="stFileUploader"] {
background: rgba(255,215,0,0.05);
padding:20px;
border-radius:15px;
border:1px dashed gold;
}

footer {visibility:hidden;}

</style>
""",unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<div class="title">🦚 TDS Krishna AI Suite</div>',unsafe_allow_html=True)

# ---------- KRISHNA SLOKA ----------
st.markdown("""
<div class="krishna">

🕉️ **कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।**  
**मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥**

*"Focus on duty, not results." – Lord Krishna*

</div>
""",unsafe_allow_html=True)

st.write("")

# ---------- AI CHAT ----------
st.sidebar.title("🦚 Krishna AI")

if client is None:
    st.sidebar.info("Add API key to enable AI")

if "msgs" not in st.session_state:
    st.session_state.msgs=[]

prompt=st.sidebar.chat_input("Ask tax doubt...")

if prompt and client:
    st.session_state.msgs.append(("user",prompt))

    res=client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}]
    )

    reply=res.choices[0].message.content
    st.session_state.msgs.append(("assistant",reply))

for r,m in st.session_state.msgs:
    with st.sidebar.chat_message(r):
        st.write(m)

# ---------- PARSER ----------
st.markdown('<div class="glass">',unsafe_allow_html=True)

files=st.file_uploader("📄 Upload TDS Challans",type="pdf",accept_multiple_files=True)

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

        delay=round(interest/(tax*0.015)) if tax>0 and interest>0 else 1
        tds_month=(dep-relativedelta(months=delay)).strftime("%B")

        rows.append({
            "S.No":s,
            "FY":d["FY"],
            "TDS Month":tds_month,
            "Deposit Date":d["Date"],
            "Nature":d["Nature"],
            "Challan":d["Challan"],
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

    st.dataframe(df,use_container_width=True)

    st.download_button("📥 Download Excel",data=excel(df))

st.markdown('</div>',unsafe_allow_html=True)

st.write("")
st.caption("⚙️ Tool developed by Abhishek Jakkula")
