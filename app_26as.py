import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font, Alignment, PatternFill
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import plotly.express as px

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="TDS AI Auditor | Abhishek Jakkula", layout="wide", page_icon="⚖️")

# ----------- ULTRA STYLISH MODERN UI -----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #0b0f19; color: #e2e8f0; }

    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.5rem; text-align: center; margin-bottom: 5px;
    }
    .branding-sub {
        text-align: center; color: #38bdf8; font-size: 1.2rem; font-weight: 600; margin-bottom: 2px;
    }
    .contact-sub {
        text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 30px;
    }
    .footer {
        position: fixed; bottom: 10px; left: 20px; 
        color: #64748b; font-size: 0.85rem; font-weight: 600; background: rgba(11, 15, 25, 0.8); padding: 5px;
    }
</style>
""", unsafe_allow_html=True)

# ----------- BRANDING & HEADER -----------
st.markdown('<div class="main-header">⚖️ TDS AI AUDITOR PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="branding-sub">Developed by Abhishek Jakkula</div>', unsafe_allow_html=True)
st.markdown('<div class="contact-sub">📧 Jakkulaabhishek5@gmail.com | IT Act 2026 Compliant</div>', unsafe_allow_html=True)

# ----------- STATUTORY DATA -----------
SECTION_MAP = {
    "94C": "194C (Contractor)", "94J": "194J (Professional)", "94I": "194I (Rent)",
    "94H": "194H (Commission)", "92": "192 (Salary)", "92B": "192 (Salary)", 
    "94Q": "194Q (Goods)", "94A": "194A (Interest)", "194JB": "194JB (Tech Services)"
}

# ----------- UTILITY FUNCTIONS -----------
def clean_num(text):
    if not text: return 0.0
    num = re.sub(r'[^\d.]', '', str(text))
    return float(num) if num else 0.0

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Audit_Report')
        # Metadata
        ws = writer.sheets['Audit_Report']
        ws.set_printer_settings(paper_size=ws.PAPERSIZE_A4, orientation=ws.ORIENTATION_LANDSCAPE)
    return output.getvalue()

def extract_data(text):
    rows = []
    blocks = re.split(r"Challan Receipt|Taxpayer Counterfoil|Income Tax", text, flags=re.IGNORECASE)
    
    for block in blocks:
        if not re.search(r"CIN|BSR|Amount", block, re.IGNORECASE): continue
        
        date_match = re.search(r"(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4})", block)
        sec_match = re.search(r"(?:Nature of Payment|Section)\s*[:\-]?\s*(\w+)", block, re.IGNORECASE)
        tax_match = re.search(r"(?:Tax|Income Tax)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)
        int_match = re.search(r"(?:Interest)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)
        bsr_match = re.search(r"BSR Code\s*[:\-]?\s*(\d+)", block, re.IGNORECASE)
        cin_match = re.search(r"(?:Challan No|CIN)\s*[:\-]?\s*(\d+)", block, re.IGNORECASE)

        if date_match:
            try:
                raw_date = date_match.group(1).replace("/", "-")
                dep_date = pd.to_datetime(raw_date)
            except: continue

            tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
            paid_int = clean_num(int_match.group(1)) if int_match else 0.0
            
            tds_month = dep_date - relativedelta(months=1)
            due_date = (tds_month + relativedelta(months=1)).replace(day=7)
            delay = (dep_date - due_date).days
            
            months_late = math.ceil(delay / 30) if delay > 0 else 0
            expected_int = tax_val * 0.015 * months_late
            int_gap = paid_int - expected_int

            rows.append({
                "Section": SECTION_MAP.get(sec_match.group(1).upper() if sec_match else "", "Other"),
                "Deposit Date": dep_date.strftime("%d-%b-%Y"),
                "TDS Month": tds_month.strftime("%B %Y"),
                "Status": "✅ On-Time" if delay <= 0 else f"⚠️ Late ({delay} Days)",
                "Tax Paid (₹)": tax_val,
                "Interest Paid (₹)": paid_int,
                "Interest Gap (₹)": round(int_gap, 2),
                "BSR Code": bsr_match.group(1) if bsr_match else "N/A",
                "Challan/CIN": cin_match.group(1) if cin_match else "N/A"
            })
    return rows

# ----------- PROCESS FLOW -----------
col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    uploaded_files = st.file_uploader("📂 UPLOAD TDS CHALLANS", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_rows = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_rows.extend(extract_data(text))
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        st.markdown("### 📊 AUDIT SUMMARY")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Tax Paid", f"₹{df['Tax Paid (₹)'].sum():,.2f}")
        m2.metric("Total Interest", f"₹{df['Interest Paid (₹)'].sum():,.2f}")
        leakage = df[df['Interest Gap (₹)'] < -1]['Interest Gap (₹)'].sum()
        m3.metric("Audit Flag (Leakage)", f"₹{abs(leakage):,.2f}", delta="Action Required" if leakage < 0 else "All Good")

        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.pie(df, names='Section', values='Tax Paid (₹)', hole=0.4, template="plotly_dark", title="Tax Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 📄 Export Audit Report")
            st.download_button(
                "📥 DOWNLOAD EXCEL REPORT",
                data=to_excel(df),
                file_name=f"TDS_Audit_Abhishek_Jakkula_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        st.markdown("### 🔍 TRANSACTION AUDIT")
        # Simplified display to avoid ImportError
        st.dataframe(df, use_container_width=True)
    else:
        st.error("No valid data found. Please check PDF quality.")

# ----------- PERMANENT FOOTER -----------
st.markdown(f'<div class="footer">© {datetime.now().year} | Designed by Abhishek Jakkula | 📧 Jakkulaabhishek5@gmail.com</div>', unsafe_allow_html=True)
