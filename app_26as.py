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

    /* Header Styling */
    .main-header {
        background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3.5rem; text-align: center; margin-bottom: 5px;
    }
    .sub-header {
        text-align: center; color: #94a3b8; font-size: 1.1rem; margin-bottom: 30px; letter-spacing: 1px;
    }

    /* Card Styling */
    .stat-card {
        background: rgba(30, 41, 59, 0.7);
        padding: 20px; border-radius: 16px;
        border: 1px solid rgba(255, 255, 255, 0.1);
        transition: transform 0.3s ease;
    }
    
    /* Custom Button */
    .stButton>button {
        background: linear-gradient(90deg, #4f46e5, #7c3aed);
        color: white !important; border: none; border-radius: 10px;
        padding: 15px 30px; font-weight: 700; width: 100%;
        box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);
    }
    
    /* Branding Footer */
    .footer {
        position: fixed; bottom: 10px; right: 20px; 
        color: #64748b; font-size: 0.85rem; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ----------- BRANDING & HEADER -----------
st.markdown('<div class="main-header">⚖️ TDS AI AUDITOR PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">INTELLIGENT STATUTORY COMPLIANCE ENGINE v2.0</div>', unsafe_allow_html=True)

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
    return output.getvalue()

def extract_data(text):
    rows = []
    # Split by common challan delimiters
    blocks = re.split(r"Challan Receipt|Taxpayer Counterfoil|Income Tax", text, flags=re.IGNORECASE)
    
    for block in blocks:
        if not re.search(r"CIN|BSR|Amount", block, re.IGNORECASE): continue
        
        # Robust Regex Patterns
        date_match = re.search(r"(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4})", block)
        sec_match = re.search(r"(?:Nature of Payment|Section)\s*[:\-]?\s*(\w+)", block, re.IGNORECASE)
        tax_match = re.search(r"(?:Tax|Income Tax)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)
        int_match = re.search(r"(?:Interest)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)
        total_match = re.search(r"Total\s*.*?₹?\s*([\d,.]+)", block, re.IGNORECASE)
        bsr_match = re.search(r"BSR Code\s*[:\-]?\s*(\d+)", block, re.IGNORECASE)
        cin_match = re.search(r"(?:Challan No|CIN)\s*[:\-]?\s*(\d+)", block, re.IGNORECASE)

        if date_match:
            try:
                raw_date = date_match.group(1).replace("/", "-")
                dep_date = pd.to_datetime(raw_date)
            except: continue

            # Financial Logic
            tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
            paid_int = clean_num(int_match.group(1)) if int_match else 0.0
            
            # Due Date Logic (7th of next month)
            tds_month = dep_date - relativedelta(months=1)
            due_date = (tds_month + relativedelta(months=1)).replace(day=7)
            delay = (dep_date - due_date).days
            
            # AI Interest Audit (Statutory 1.5% per month or part of month)
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

# ----------- FILE UPLOAD SECTION -----------
col_l, col_m, col_r = st.columns([1, 2, 1])
with col_m:
    uploaded_files = st.file_uploader("🚀 DROP CHALLAN PDFs HERE", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_rows = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
            all_rows.extend(extract_data(text))
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        # --- DASHBOARD METRICS ---
        st.markdown("### 📊 AUDIT SNAPSHOT")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Files", len(uploaded_files))
        m2.metric("Total Tax", f"₹{df['Tax Paid (₹)'].sum():,.0f}")
        m3.metric("Interest Paid", f"₹{df['Interest Paid (₹)'].sum():,.0f}")
        
        leakage = df[df['Interest Gap (₹)'] < -5]['Interest Gap (₹)'].sum()
        m4.metric("Interest Leakage", f"₹{abs(leakage):,.0f}", delta="Action Required" if leakage < 0 else "Compliant")

        # --- VISUALS ---
        st.markdown("---")
        c1, c2 = st.columns([2, 1])
        with c1:
            fig = px.bar(df, x="TDS Month", y="Tax Paid (₹)", color="Section", 
                         title="Monthly Tax Contribution", template="plotly_dark")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 📥 Export Report")
            st.write("Generate a professional audit trail for your records.")
            st.download_button(
                label="📥 DOWNLOAD AUDIT EXCEL",
                data=to_excel(df),
                file_name=f"TDS_Audit_{datetime.now().year}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # --- DATA TABLE ---
        st.markdown("### 🔍 DETAILED AUDIT TRAIL")
        st.dataframe(df.style.background_gradient(subset=['Interest Gap (₹)'], cmap='RdYlGn'), use_container_width=True)
    else:
        st.error("🚨 No valid data found. Ensure these are digital PDF receipts and not scanned images.")

# ----------- FOOTER BRANDING -----------
st.markdown(f'<div class="footer">Engineered by Abhishek Jakkula | © {datetime.now().year}</div>', unsafe_allow_html=True)
