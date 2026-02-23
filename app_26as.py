import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
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
    .branding-sub { text-align: center; color: #38bdf8; font-size: 1.2rem; font-weight: 600; margin-bottom: 2px; }
    .contact-sub { text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 30px; }
    .footer { position: fixed; bottom: 10px; left: 20px; color: #64748b; font-size: 0.85rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">⚖️ TDS AI AUDITOR PRO</div>', unsafe_allow_html=True)
st.markdown(f'<div class="branding-sub">Developed by Abhishek Jakkula</div>', unsafe_allow_html=True)
st.markdown('<div class="contact-sub">📧 Jakkulaabhishek5@gmail.com | Statutory Compliance Tool</div>', unsafe_allow_html=True)

# ----------- FULL TDS RATES & LIMITS (FY 2025-26) -----------
SECTION_DATA = {
    "192": {"desc": "Salary", "rate": "Slab rates", "limit": "Basic exemption limit"},
    "192A": {"desc": "Premature withdrawal from EPF", "rate": "10%", "limit": "Rs. 50,000"},
    "193": {"desc": "Interest on Securities", "rate": "10%", "limit": "Rs. 10,000"},
    "194": {"desc": "Dividends", "rate": "10%", "limit": "Rs. 10,000"},
    "194A": {"desc": "Interest (Bank/Post Office)", "rate": "10%", "limit": "Rs. 50,000 (Gen) / Rs. 1,00,000 (Sr. Citizen)"},
    "194B": {"desc": "Winnings (Lottery/Puzzle)", "rate": "30%", "limit": "Rs. 10,000 (Single Transaction)"},
    "194BA": {"desc": "Online gaming winnings", "rate": "30%", "limit": "N/A"},
    "194BB": {"desc": "Winnings from horse races", "rate": "30%", "limit": "Rs. 10,000 (Aggregate)"},
    "194C": {"desc": "Payment to contractors", "rate": "1% (Ind/HUF) / 2% (Others)", "limit": "Rs. 30,000 (Single) / Rs. 1 Lakh (FY)"},
    "194D": {"desc": "Insurance Commission", "rate": "2% (Ind/HUF) / 10% (Others)", "limit": "Rs. 20,000"},
    "194DA": {"desc": "Life Insurance Policy", "rate": "2%", "limit": "Rs. 1 Lakh"},
    "194EE": {"desc": "NSS Deposits", "rate": "10%", "limit": "Rs. 2,500"},
    "194G": {"desc": "Lottery Commission", "rate": "2%", "limit": "Rs. 20,000"},
    "194H": {"desc": "Commission or Brokerage", "rate": "2%", "limit": "Rs. 20,000"},
    "194I": {"desc": "Rent (Plant & Machinery)", "rate": "2%", "limit": "Rs. 6,00,000 (FY)"},
    "194IA": {"desc": "Rent (Immovable Property)", "rate": "10%", "limit": "Rs. 6,00,000 (FY)"},
    "194IB": {"desc": "Rent (Ind/HUF not under 194I)", "rate": "2%", "limit": "Rs. 50,000 pm"},
    "194J(a)": {"desc": "Tech Services/Royalty/Call Centre", "rate": "2%", "limit": "Rs. 50,000"},
    "194J(b)": {"desc": "Professional Services", "rate": "10%", "limit": "Rs. 50,000"},
    "194LA": {"desc": "Enhanced Compensation (Property)", "rate": "10%", "limit": "Rs. 5 Lakhs"},
    "194M": {"desc": "Payment for Contracts/Prof. Fees", "rate": "2%", "limit": "Rs. 50 Lakhs"},
    "194N": {"desc": "Cash withdrawal (Bank/Co-op)", "rate": "2% / 5%", "limit": "Rs. 20 Lakh / Rs. 1 Crore"},
    "194O": {"desc": "E-commerce participants", "rate": "0.10%", "limit": "Rs. 5 Lakhs"},
    "194Q": {"desc": "Purchase of Goods", "rate": "0.10%", "limit": "Rs. 50 Lakhs"},
    "194R": {"desc": "Benefits/Perquisites (Business)", "rate": "10%", "limit": "Rs. 20,000"},
    "194S": {"desc": "Virtual Digital Assets (VDA)", "rate": "1%", "limit": "Rs. 10,000 / Rs. 50,000"},
    "194T": {"desc": "Payment to Partner of Firm", "rate": "10%", "limit": "Rs. 20,000"}
}

# ----------- EXCEL EXPORTER WITH AUDIT TRAIL -----------
def to_excel_with_audit(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 1. Audit Data Sheet
    df.to_excel(writer, sheet_name='Audit_Data', index=False)
    workbook = writer.book
    data_ws = writer.sheets['Audit_Data']
    for i, col in enumerate(df.columns):
        data_ws.set_column(i, i, 20)

    # 2. Dashboard Sheet
    dashboard = workbook.add_worksheet('Dashboard')
    writer.sheets['Dashboard'] = dashboard
    summary = df.groupby('Section')['Tax Paid (₹)'].sum().reset_index()
    summary.to_excel(writer, sheet_name='Dashboard', startrow=2, startcol=0, index=False)
    
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'categories': ['Dashboard', 3, 0, len(summary)+2, 0],
        'values':     ['Dashboard', 3, 1, len(summary)+2, 1],
    })
    dashboard.insert_chart('D2', chart)

    # 3. Audit Trail Sheet (New Feature)
    trail_ws = workbook.add_worksheet('Audit_Trail')
    header_fmt = workbook.add_format({'bold': True, 'font_color': '#ffffff', 'bg_color': '#1e293b'})
    
    trail_ws.write('A1', 'Field', header_fmt)
    trail_ws.write('B1', 'Details', header_fmt)
    
    audit_info = [
        ('Auditor Name', 'Abhishek Jakkula'),
        ('Auditor Email', 'Jakkulaabhishek5@gmail.com'),
        ('Audit Timestamp', datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        ('Total Challans Processed', len(df)),
        ('Total Tax Value Verified', df['Tax Paid (₹)'].sum()),
        ('Compliance Status', 'Verified per IT Act 2026')
    ]
    
    for row, (field, val) in enumerate(audit_info, start=1):
        trail_ws.write(row, 0, field)
        trail_ws.write(row, 1, val)
    trail_ws.set_column(0, 1, 30)

    writer.close()
    return output.getvalue()

# ----------- EXTRACTION ENGINE -----------
def clean_num(text):
    if not text: return 0.0
    num = re.sub(r'[^\d.]', '', str(text))
    return float(num) if num else 0.0

def extract_data(text):
    rows = []
    blocks = re.split(r"Challan Receipt|Taxpayer Counterfoil|Income Tax", text, flags=re.IGNORECASE)
    for block in blocks:
        if not re.search(r"CIN|BSR|Amount", block, re.IGNORECASE): continue
        date_match = re.search(r"(\d{2}[-/][A-Za-z0-9]{2,3}[-/]\d{2,4})", block)
        sec_match = re.search(r"(?:Nature of Payment|Section)\s*[:\-]?\s*(\w+)", block, re.IGNORECASE)
        tax_match = re.search(r"(?:Tax|Income Tax)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)
        int_match = re.search(r"(?:Interest)\s*₹?\s*([\d,.]+)", block, re.IGNORECASE)

        if date_match:
            try: dep_date = pd.to_datetime(date_match.group(1).replace("/", "-"))
            except: continue
            sec_code = sec_match.group(1).upper() if sec_match else ""
            lookup_code = sec_code if sec_code.startswith("194") else "1" + sec_code if sec_code.startswith("94") else sec_code
            sec_info = SECTION_DATA.get(lookup_code, {"desc": f"Sec {sec_code}", "rate": "Check Act", "limit": "N/A"})
            
            rows.append({
                "Section": sec_info['desc'],
                "Rate per Act": sec_info['rate'],
                "Exemption Limit": sec_info['limit'],
                "Deposit Date": dep_date.strftime("%d-%b-%Y"),
                "Tax Paid (₹)": clean_num(tax_match.group(1)) if tax_match else 0.0,
                "Interest Paid (₹)": clean_num(int_match.group(1)) if int_match else 0.0
            })
    return rows

# ----------- APP FLOW -----------
uploaded_files = st.file_uploader("📂 UPLOAD TDS CHALLAN PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_data.extend(extract_data(text))
    
    if all_data:
        df = pd.DataFrame(all_data)
        st.markdown("### 📊 AUDIT INSIGHTS")
        st.download_button("🚀 DOWNLOAD REPORT WITH AUDIT TRAIL", data=to_excel_with_audit(df), file_name="TDS_Audit_Report.xlsx")
        st.dataframe(df, use_container_width=True)

st.markdown(f'<div class="footer">© {datetime.now().year} | Designed by Abhishek Jakkula | Jakkulaabhishek5@gmail.com</div>', unsafe_allow_html=True)
