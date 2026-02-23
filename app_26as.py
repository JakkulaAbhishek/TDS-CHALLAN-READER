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
st.markdown('<div class="branding-sub">Developed by Abhishek Jakkula</div>', unsafe_allow_html=True)
st.markdown('<div class="contact-sub">📧 Jakkulaabhishek5@gmail.com | Statutory Compliance Tool</div>', unsafe_allow_html=True)

# ----------- STATUTORY DATA & RATES -----------
SECTION_DATA = {
    "94C": {"desc": "194C (Contractor)", "rate": "1% / 2%"},
    "94J": {"desc": "194J (Professional)", "rate": "10%"},
    "194JB": {"desc": "194JB (Technical)", "rate": "2%"},
    "94I": {"desc": "194I (Rent)", "rate": "10%"},
    "94H": {"desc": "194H (Commission)", "rate": "5%"},
    "92": {"desc": "192 (Salary)", "rate": "Slab Rate"},
    "94Q": {"desc": "194Q (Goods)", "rate": "0.1%"},
    "94A": {"desc": "194A (Interest)", "rate": "10%"}
}

# ----------- EXCEL EXPORTER WITH DASHBOARD & AUTO-WIDTH -----------
def to_excel_with_charts(df):
    output = BytesIO()
    # Using xlsxwriter to support charts
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    
    # 1. Data Sheet
    df.to_excel(writer, sheet_name='Audit_Data', index=False)
    workbook = writer.book
    worksheet = writer.sheets['Audit_Data']
    
    # Auto-width logic
    for i, col in enumerate(df.columns):
        column_len = max(df[col].astype(str).map(len).max(), len(col)) + 2
        worksheet.set_column(i, i, column_len)

    # 2. Dashboard Sheet
    dashboard = workbook.add_worksheet('Dashboard')
    writer.sheets['Dashboard'] = dashboard
    
    # Summary Table for Charts
    summary = df.groupby('Section')['Tax Paid (₹)'].sum().reset_index()
    summary.to_excel(writer, sheet_name='Dashboard', startrow=1, startcol=0, index=False)
    
    # Create Chart
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name': 'Tax Distribution',
        'categories': ['Dashboard', 2, 0, len(summary)+1, 0],
        'values':     ['Dashboard', 2, 1, len(summary)+1, 1],
        'data_labels': {'percentage': True},
    })
    chart.set_title({'name': 'Tax Distribution by Section'})
    chart.set_style(10)
    dashboard.insert_chart('D2', chart)

    # Add Branding to Dashboard
    header_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#4f46e5'})
    dashboard.write('A0', f"TDS Audit Report - {Abhishek Jakkula}", header_fmt)
    dashboard.write('A20', "Statutory Rates Reference:")
    
    # 3. Add Rates per Act
    for row_num, (code, info) in enumerate(SECTION_DATA.items()):
        dashboard.write(row_num + 22, 0, info['desc'])
        dashboard.write(row_num + 22, 1, info['rate'])

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

            sec_code = sec_match.group(1).upper() if sec_match else ""
            sec_info = SECTION_DATA.get(sec_code, {"desc": "Other", "rate": "N/A"})
            
            tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
            paid_int = clean_num(int_match.group(1)) if int_match else 0.0
            
            tds_month = dep_date - relativedelta(months=1)
            due_date = (tds_month + relativedelta(months=1)).replace(day=7)
            delay = (dep_date - due_date).days
            
            rows.append({
                "Section": sec_info['desc'],
                "Rate as per Act": sec_info['rate'],
                "Deposit Date": dep_date.strftime("%d-%b-%Y"),
                "Status": "✅ On-Time" if delay <= 0 else f"⚠️ Late ({delay} Days)",
                "Tax Paid (₹)": tax_val,
                "Interest Paid (₹)": paid_int,
                "Interest Gap (₹)": round(paid_int - (tax_val * 0.015 * math.ceil(delay/30 if delay > 0 else 0)), 2)
            })
    return rows

# ----------- APP FLOW -----------
uploaded_files = st.file_uploader("📂 UPLOAD CHALLANS", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_rows = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_rows.extend(extract_data(text))
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        st.markdown("### 📊 DASHBOARD PREVIEW")
        st.plotly_chart(px.pie(df, names='Section', values='Tax Paid (₹)', template="plotly_dark"), use_container_width=True)

        st.download_button(
            "🚀 DOWNLOAD ENHANCED EXCEL (WITH CHARTS)",
            data=to_excel_with_charts(df),
            file_name=f"TDS_Audit_Abhishek_Jakkula.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        st.dataframe(df, use_container_width=True)

st.markdown(f'<div class="footer">© {datetime.now().year} | Designed by Abhishek Jakkula | Jakkulaabhishek5@gmail.com</div>', unsafe_allow_html=True)
