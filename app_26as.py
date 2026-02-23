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

# ----------- COMPREHENSIVE TDS RATES & LIMITS (FY 2025-26) -----------
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
    "194DA": {"desc": "Life Insurance Policy payment", "rate": "2%", "limit": "Rs. 1 Lakh"},
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
    "194P": {"desc": "Specified Senior Citizen", "rate": "Slab Rates", "limit": "Basic Exemption"},
    "194Q": {"desc": "Purchase of Goods", "rate": "0.10%", "limit": "Rs. 50 Lakhs"},
    "194R": {"desc": "Benefits/Perquisites (Business)", "rate": "10%", "limit": "Rs. 20,000"},
    "194S": {"desc": "Virtual Digital Assets (VDA)", "rate": "1%", "limit": "Rs. 10,000 / Rs. 50,000"},
    "194T": {"desc": "Payment to Partner of Firm", "rate": "10%", "limit": "Rs. 20,000"}
}

# ----------- EXCEL EXPORTER -----------
def to_excel_with_charts(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Audit_Data', index=False)
    workbook = writer.book
    worksheet = writer.sheets['Audit_Data']
    
    for i, col in enumerate(df.columns):
        column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(i, i, column_len)

    dashboard = workbook.add_worksheet('Dashboard')
    writer.sheets['Dashboard'] = dashboard
    # Summary by Section Code for dashboard
    summary = df.groupby('Section Code')['Tax Paid (₹)'].sum().reset_index()
    summary.to_excel(writer, sheet_name='Dashboard', startrow=2, startcol=0, index=False)
    
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name': 'Tax Distribution',
        'categories': ['Dashboard', 3, 0, len(summary)+2, 0],
        'values':     ['Dashboard', 3, 1, len(summary)+2, 1],
        'data_labels': {'percentage': True, 'position': 'outside_end'},
    })
    chart.set_title({'name': 'Tax Distribution by Section'})
    dashboard.insert_chart('D2', chart)

    title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#4f46e5', 'border': 1})
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    
    dashboard.write('A1', "TDS Audit Report - Abhishek Jakkula", title_fmt)
    dashboard.write('A18', "Full Statutory Rates & Limits Reference (FY 2025-26):", title_fmt)
    dashboard.write('A19', 'Section Code', header_fmt)
    dashboard.write('B19', 'Nature of Transaction', header_fmt)
    dashboard.write('C19', 'Rate', header_fmt)
    dashboard.write('D19', 'Threshold Limit', header_fmt)

    for row_num, (code, info) in enumerate(SECTION_DATA.items()):
        dashboard.write(row_num + 20, 0, code)
        dashboard.write(row_num + 20, 1, info['desc'])
        dashboard.write(row_num + 20, 2, info['rate'])
        dashboard.write(row_num + 20, 3, info['limit'])

    dashboard.set_column(0, 3, 30)
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
            try:
                dep_date = pd.to_datetime(date_match.group(1).replace("/", "-"))
            except: continue
            
            raw_sec = sec_match.group(1).upper() if sec_match else ""
            lookup_code = raw_sec if raw_sec.startswith("194") else "1" + raw_sec if raw_sec.startswith("94") else raw_sec
            sec_info = SECTION_DATA.get(lookup_code, {"desc": "Other Transaction", "rate": "Verify per Act", "limit": "N/A"})
            
            tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
            paid_int = clean_num(int_match.group(1)) if int_match else 0.0
            tds_month = dep_date - relativedelta(months=1)
            due_date = (tds_month + relativedelta(months=1)).replace(day=7)
            delay = (dep_date - due_date).days
            
            rows.append({
                "Section Code": lookup_code,
                "Nature of Transaction": sec_info['desc'],
                "Rate per Act": sec_info['rate'],
                "Exemption Limit": sec_info['limit'],
                "Deposit Date": dep_date.strftime("%d-%b-%Y"),
                "TDS Month": tds_month.strftime("%B %Y"),
                "Status": "✅ On-Time" if delay <= 0 else f"⚠️ Late ({delay} Days)",
                "Tax Paid (₹)": tax_val,
                "Interest Paid (₹)": paid_int,
                "Interest Gap (₹)": round(paid_int - (tax_val * 0.015 * math.ceil(delay/30 if delay > 0 else 0)), 2)
            })
    return rows

# ----------- WEB DASHBOARD FLOW -----------
uploaded_files = st.file_uploader("📂 UPLOAD CHALLAN PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_rows = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_rows.extend(extract_data(text))
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        st.markdown("### 📊 AUDIT DASHBOARD")
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(px.pie(df, names='Section Code', values='Tax Paid (₹)', hole=0.4, title="Tax by Section Code", template="plotly_dark"), use_container_width=True)
        with col2:
            st.plotly_chart(px.bar(df, x='TDS Month', y='Tax Paid (₹)', color='Section Code', title="Monthly Trend", template="plotly_dark"), use_container_width=True)

        st.download_button(
            "🚀 DOWNLOAD EXCEL WITH DASHBOARD & RATES",
            data=to_excel_with_charts(df),
            file_name=f"TDS_Audit_Abhishek_Jakkula_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("### 🔍 DETAILED AUDIT TABLE")
        try:
            st.dataframe(df.style.background_gradient(subset=['Interest Gap (₹)'], cmap='RdYlGn'), use_container_width=True)
        except Exception:
            st.dataframe(df, use_container_width=True)

        with st.expander("📖 View Statutory TDS Rates & Limits (FY 2025-26)"):
            rates_df = pd.DataFrame(SECTION_DATA).T.reset_index().rename(columns={"index": "Code", "desc": "Nature of Transaction", "rate": "Rate", "limit": "Threshold"})
            st.table(rates_df)

st.markdown(f'<div class="footer">© {datetime.now().year} | Designed by Abhishek Jakkula | Jakkulaabhishek5@gmail.com</div>', unsafe_allow_html=True)
