import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO
import os
from openai import OpenAI

client = OpenAI()

# ---------- PAGE CONFIG ----------
st.set_page_config(page_title="TDS Divine AI Suite", page_icon="🦚", layout="wide")

# ---------- BEAUTIFUL UI ----------
st.markdown("""
<style>

.stApp {
background: linear-gradient(135deg,#0f2027,#203a43,#2c5364);
color:white;
animation: fadeIn 1.5s ease-in;
}

@keyframes fadeIn {
0% {opacity:0;}
100% {opacity:1;}
}

.title {
text-align:center;
font-size:46px;
font-weight:bold;
background: linear-gradient(45deg,gold,white);
-webkit-background-clip: text;
-webkit-text-fill-color: transparent;
}

.glass {
background: rgba(255,255,255,0.1);
padding:25px;
border-radius:18px;
backdrop-filter: blur(15px);
box-shadow: 0 0 40px rgba(255,215,0,0.3);
}

.krishna {
text-align:center;
font-size:20px;
color:gold;
line-height:1.8;
}

</style>
""", unsafe_allow_html=True)

st.markdown('<div class="title">🦚 TDS Divine AI Suite</div>', unsafe_allow_html=True)

# ---------- KRISHNA SHLOKA ----------
st.markdown("""
<div class="krishna">
🕉️ कर्मण्येवाधिकारस्ते मा फलेषु कदाचन।<br>
मा कर्मफलहेतुर्भूर्मा ते सङ्गोऽस्त्वकर्मणि॥
<br><br>
"You have a right to perform your duty, but not to the results."
</div>
""", unsafe_allow_html=True)

# ---------- AI ASSISTANT ----------
st.sidebar.title("🤖 Krishna AI Assistant")

if "chat" not in st.session_state:
    st.session_state.chat=[]

user_msg = st.sidebar.chat_input("Ask tax/compliance doubt...")

if user_msg:
    st.session_state.chat.append(("user",user_msg))

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":user_msg}]
    )

    reply = resp.choices[0].message.content
    st.session_state.chat.append(("ai",reply))

for role,msg in st.session_state.chat:
    with st.sidebar.chat_message(role):
        st.write(msg)

# ---------- MAIN PARSER ----------
st.markdown('<div class="glass">', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📄 Upload TDS Challans",
    type="pdf",
    accept_multiple_files=True
)

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

if uploaded_files:

    rows=[]
    s=1

    for f in uploaded_files:

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

        delay= round(interest/(tax*0.015)) if tax>0 and interest>0 else 1

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

    st.success("✅ Challans Processed")
    st.dataframe(df,use_container_width=True)

    st.download_button(
        "📥 Download Excel",
        data=excel(df),
        file_name="TDS_AI_Report.xlsx"
    )

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("---")
st.markdown("⚙️ Tool developed by Abhishek Jakkula")
