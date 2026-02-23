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

# ----------- FULL STATUTORY TDS RATES & LIMITS (IT ACT) -----------
SECTION_DATA = {
  "192": {"desc": "192 (Salary)", "rate": "Slab Rates", "limit": "Basic Exemption Limit"},
  "192A": {"desc": "192A (Premature EPF Withdrawal)", "rate": "10%", "limit": "₹50,000"},
  "193": {"desc": "193 (Interest on Securities)", "rate": "10%", "limit": "₹10,000"},
  "194": {"desc": "194 (Dividend)", "rate": "10%", "limit": "₹10,000"},
  "194A": {"desc": "194A (Interest other than Securities)", "rate": "10%", "limit": "₹50,000 (Senior Citizen) / ₹50,000 (Others – Bank) / ₹10,000 (Others)"},
  "194B": {"desc": "194B (Lottery/Crossword Winnings)", "rate": "30%", "limit": "₹10,000"},
  "194BA": {"desc": "194BA (Online Gaming Winnings)", "rate": "30%", "limit": "No Threshold"},
  "194BB": {"desc": "194BB (Horse Race Winnings)", "rate": "30%", "limit": "₹10,000 (Aggregate)"},
  "194C": {"desc": "194C (Contractor)", "rate": "1% (Ind/HUF) / 2% (Others)", "limit": "₹30,000 Single / ₹1,00,000 Aggregate"},
  "194D": {"desc": "194D (Insurance Commission)", "rate": "2% (Ind/HUF) / 10% (Others)", "limit": "₹20,000"},
  "194DA": {"desc": "194DA (Life Insurance Payout)", "rate": "2%", "limit": "₹1,00,000"},
  "194EE": {"desc": "194EE (NSS Withdrawal)", "rate": "10%", "limit": "₹2,500"},
  "194G": {"desc": "194G (Lottery Commission)", "rate": "2%", "limit": "₹20,000"},
  "194H": {"desc": "194H (Commission/Brokerage)", "rate": "2%", "limit": "₹20,000"},
  "194I(a)": {"desc": "194I(a) (Rent – Plant & Machinery)", "rate": "2%", "limit": "₹6,00,000"},
  "194I(b)": {"desc": "194I(b) (Rent – Land/Building/Furniture)", "rate": "10%", "limit": "₹6,00,000"},
  "194IA": {"desc": "194IA (Immovable Property Transfer)", "rate": "1%", "limit": "₹50,00,000"},
  "194IB": {"desc": "194IB (Rent by Individual/HUF not under 194I)", "rate": "2%", "limit": "₹50,000 per month"},
  "194IC": {"desc": "194IC (Joint Development Agreement)", "rate": "10%", "limit": "No Threshold"},
  "194J(a)": {"desc": "194J(a) (Technical Services / Royalty etc.)", "rate": "2%", "limit": "₹50,000"},
  "194J(b)": {"desc": "194J(b) (Professional Services)", "rate": "10%", "limit": "₹50,000"},
  "194K": {"desc": "194K (Mutual Fund Income)", "rate": "10%", "limit": "₹10,000"},
  "194LA": {"desc": "194LA (Compensation – Immovable Property)", "rate": "10%", "limit": "₹5,00,000"},
  "194LBA": {"desc": "194LBA (Business Trust Income)", "rate": "10% / 30%", "limit": "No Threshold"},
  "194LBB": {"desc": "194LBB (Investment Fund Income)", "rate": "30%", "limit": "No Threshold"},
  "194LBC": {"desc": "194LBC (Securitisation Trust Income – Resident)", "rate": "10%", "limit": "No Threshold"},
  "194LB": {"desc": "194LB (Infra Debt Fund Interest)", "rate": "5%", "limit": "No Threshold"},
  "194LC": {"desc": "194LC (Foreign Currency Borrowing Interest)", "rate": "4% / 9%", "limit": "No Threshold"},
  "194LD": {"desc": "194LD (Interest on Rupee Bonds/Govt Securities to FII)", "rate": "5%", "limit": "No Threshold"},
  "194M": {"desc": "194M (Payment by Individual/HUF > ₹50L)", "rate": "2%", "limit": "₹50,00,000"},
  "194N": {"desc": "194N (Cash Withdrawal)", "rate": "2% / 5%", "limit": "₹20L / ₹1Cr"},
  "194O": {"desc": "194O (E-commerce Participant)", "rate": "0.10%", "limit": "₹5,00,000"},
  "194P": {"desc": "194P (Specified Senior Citizen)", "rate": "Slab Rates", "limit": "No Threshold"},
  "194Q": {"desc": "194Q (Purchase of Goods)", "rate": "0.10%", "limit": "₹50,00,000"},
  "194R": {"desc": "194R (Business Perquisites)", "rate": "10%", "limit": "₹20,000"},
  "194S": {"desc": "194S (Virtual Digital Asset)", "rate": "1%", "limit": "₹10,000 / ₹50,000"},
  "194T": {"desc": "194T (Partner Remuneration)", "rate": "10%", "limit": "₹20,000"},
  "195": {"desc": "195 (Payment to Non-Resident)", "rate": "As per Act/DTAA", "limit": "No Threshold"},
  "196A": {"desc": "196A (Income of Units – Non Resident)", "rate": "20%", "limit": "₹10,000"},
  "196B": {"desc": "196B (Units to Offshore Fund)", "rate": "10% / 12.5%", "limit": "No Threshold"},
  "196C": {"desc": "196C (Foreign Company Income)", "rate": "12.5%", "limit": "No Threshold"},
  "196D": {"desc": "196D (FII Income)", "rate": "20% / 10%", "limit": "No Threshold"}
}

# ----------- EXCEL EXPORTER WITH DASHBOARD, CHARTS, & LIMITS -----------
def to_excel_with_charts(df):
    output = BytesIO()
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
    
    summary = df.groupby('Section')['Tax Paid (₹)'].sum().reset_index()
    summary.to_excel(writer, sheet_name='Dashboard', startrow=2, startcol=0, index=False)
    
    # Pie Chart in Excel
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name': 'Tax Distribution',
        'categories': ['Dashboard', 3, 0, len(summary)+2, 0],
        'values':     ['Dashboard', 3, 1, len(summary)+2, 1],
        'data_labels': {'percentage': True, 'position': 'outside_end'},
    })
    chart.set_title({'name': 'Tax Distribution by Section'})
    dashboard.insert_chart('D2', chart)

    # Styling for Excel
    title_fmt = workbook.add_format({'bold': True, 'font_size': 14, 'font_color': '#4f46e5', 'border': 1})
    header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
    
    dashboard.write('A1', "TDS Audit Report", title_fmt)
    dashboard.write('A18', "Statutory Rates & Threshold Limits Reference:", title_fmt)
    
    # Header for Limits Table
    dashboard.write('A19', 'Section Description', header_fmt)
    dashboard.write('B19', 'Rate', header_fmt)
    dashboard.write('C19', 'Threshold Limit', header_fmt)

    for row_num, (code, info) in enumerate(SECTION_DATA.items()):
        dashboard.write(row_num + 20, 0, info['desc'])
        dashboard.write(row_num + 20, 1, info['rate'])
        dashboard.write(row_num + 20, 2, info['limit'])

    # Auto-width for Dashboard columns
    dashboard.set_column(0, 2, 35)

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
            sec_info = SECTION_DATA.get(sec_code, {"desc": f"Sec {sec_code}", "rate": "Manual Check", "limit": "N/A"})
            
            tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
            paid_int = clean_num(int_match.group(1)) if int_match else 0.0
            
            tds_month = dep_date - relativedelta(months=1)
            due_date = (tds_month + relativedelta(months=1)).replace(day=7)
            delay = (dep_date - due_date).days
            
            rows.append({
                "Section": sec_info['desc'],
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
uploaded_files = st.file_uploader("📂 UPLOAD TDS CHALLAN PDFs", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_rows = []
    for f in uploaded_files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_rows.extend(extract_data(text))
    
    if all_rows:
        df = pd.DataFrame(all_rows)
        
        st.markdown("### 📊 AUDIT DASHBOARD")
        col1, col2 = st.columns([1, 1])
        
        with col1:
            fig_pie = px.pie(df, names='Section', values='Tax Paid (₹)', hole=0.4, title="Tax Distribution", template="plotly_dark")
            st.plotly_chart(fig_pie, use_container_width=True)
            
        with col2:
            fig_bar = px.bar(df, x='TDS Month', y='Tax Paid (₹)', color='Section', title="Monthly Tax Trend", template="plotly_dark")
            st.plotly_chart(fig_bar, use_container_width=True)

        st.download_button(
            "🚀 DOWNLOAD EXCEL WITH DASHBOARD & RATES",
            data=to_excel_with_charts(df),
            file_name=f"TDS_Audit_Abhishek_Jakkula_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("### 🔍 DETAILED AUDIT TABLE")
        try:
            st.dataframe(df.style.background_gradient(subset=['Interest Gap (₹)'], cmap='RdYlGn'), use_container_width=True)
        except:
            st.dataframe(df, use_container_width=True)

        # Statutory Reference Table on Web
        with st.expander("📖 View Statutory TDS Rates & Limits (2025-26)"):
            rates_df = pd.DataFrame(SECTION_DATA).T.reset_index()
            rates_df.columns = ["Code", "Description", "Rate", "Threshold Limit"]
            st.table(rates_df)

st.markdown(f'<div class="footer">© {datetime.now().year} | Designed by Abhishek Jakkula | Jakkulaabhishek5@gmail.com</div>', unsafe_allow_html=True)
