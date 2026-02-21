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
st.set_page_config(page_title="TDS Challan AI Auditor", layout="wide")

# ----------- ULTRA STYLISH CSS -----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: #0f172a; color: #f8fafc; }

    .header-title {
        background: linear-gradient(90deg, #38bdf8, #22c55e);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3rem; text-align: center; margin-bottom: 10px;
    }
    .zone {
        background: rgba(30, 41, 59, 0.4); padding: 20px; border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 18px; text-align: center; color: #cbd5e1; font-weight: 600;
    }
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 16px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important; border: none; border-radius: 8px;
        padding: 12px 24px; font-weight: 600; width: 100%; transition: 0.3s;
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(16, 185, 129, 0.4); }
</style>
""", unsafe_allow_html=True)

# ----------- HEADER -----------
st.markdown('<div class="header-title">🕉️ TDS CHALLAN AI AUDITOR</div>', unsafe_allow_html=True)

# ----------- IT ACT 2026 STATUTORY RATES -----------
SECTION_DATA = {
    "94C": {"desc": "194C - Contractor", "rate": 1.0}, # General/Indv rate
    "94J": {"desc": "194J - Professional", "rate": 10.0},
    "194JB": {"desc": "194JB - Prof. Special", "rate": 2.0},
    "94I": {"desc": "194I - Rent", "rate": 10.0},
    "94H": {"desc": "194H - Commission", "rate": 5.0},
    "92B": {"desc": "192 - Salary", "rate": 0.0}, # Variable
    "94Q": {"desc": "194Q - Goods", "rate": 0.1},
    "94A": {"desc": "194A - Interest", "rate": 10.0}
}

# ----------- FILE UPLOAD -----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    files = st.file_uploader("📄 Upload PDF Challans (Supports all bank layouts)", type="pdf", accept_multiple_files=True)

# ----------- EXCEL EXPORTER -----------
def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TDS_Audit")
        ws = writer.sheets["TDS_Audit"]
        
        header_fill = PatternFill(start_color="1e293b", end_color="1e293b", fill_type="solid")
        header_font = Font(bold=True, color="FFFFFF")
        
        for cell in ws[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try: max_length = max(max_length, len(str(cell.value)))
                except: pass
                if isinstance(cell.value, (int, float)) and cell.row > 1:
                    cell.number_format = '#,##0.00'
            ws.column_dimensions[column].width = max_length + 4
            
        ws.freeze_panes = "A2"
    return buf.getvalue()

# ----------- EXTRACTION ENGINE -----------
def extract_all(text):
    challans = re.split(r"Challan Receipt|Taxpayer Counterfoil|Income Tax|Challan Summary", text, flags=re.IGNORECASE)
    rows = []

    for ch in challans:
        ch = re.sub(r'[^\x00-\x7F]+', ' ', ch) 
        if not re.search(r"Challan No|CIN|BSR|Amount", ch, re.IGNORECASE):
            continue

        def get_val(patterns):
            for p in patterns:
                m = re.search(p, ch, re.IGNORECASE)
                if m: return m.group(1).replace(",", "").strip()
            return "0"

        dep_date_str = get_val([
            r"Date of Deposit\s*[:\-]?\s*(\d{2}-[A-Za-z]{3}-\d{4})", 
            r"Deposit Date\s*(\d{2}/\d{2}/\d{4})",
            r"Paid on\s*(\d{2}-\d{2}-\d{4})"
        ])
        if dep_date_str == "0": continue
        
        try: dep_date = datetime.strptime(dep_date_str, "%d-%b-%Y")
        except:
            try: dep_date = datetime.strptime(dep_date_str, "%d/%m/%Y")
            except:
                try: dep_date = datetime.strptime(dep_date_str, "%d-%m-%Y")
                except: continue

        nature_code = get_val([r"Nature of Payment\s*[:\-]?\s*(\w+)", r"Section\s*[:\-]?\s*(\w+)"]).upper()
        sec_info = SECTION_DATA.get(nature_code, {"desc": nature_code, "rate": 0.0})

        tax = float(get_val([r"A\s*Tax\s*₹?\s*([\d,.]+)"]))
        interest = float(get_val([r"D\s*Interest\s*₹?\s*([\d,.]+)"]))
        total = float(get_val([r"Total\s*.*?₹?\s*([\d,.]+)"]))

        tds_month_date = dep_date - relativedelta(months=1)
        due_date = (tds_month_date + relativedelta(months=1)).replace(day=7)
        delay_days = max(0, (dep_date - due_date).days)
        
        base_amount = float(get_val([r"Paid\s*/\s*Credited\s*₹?\s*([\d,.]+)"]))
        eff_rate = (tax / base_amount * 100) if base_amount > 0 else 0
        statutory_rate = sec_info["rate"]
        
        compliance = "Correct ✅"
        if statutory_rate > 0 and abs(eff_rate - statutory_rate) > 0.05:
            compliance = "Anomaly ⚠️"

        rows.append({
            "Financial Year": get_val([r"Financial Year\s*[:\-]?\s*([\d\-]+)"]),
            "Section": sec_info["desc"],
            "Statutory Rate (%)": statutory_rate,
            "Effective Rate (%)": round(eff_rate, 2),
            "Rate Compliance": compliance,
            "TDS Month": tds_month_date.strftime("%B"),
            "Deposit Date": dep_date.strftime("%d-%b-%Y"),
            "Status": "On Time ✅" if delay_days <= 0 else f"Late ({delay_days} days) ⚠️",
            "Tax (₹)": tax,
            "Interest (₹)": interest,
            "Total Paid (₹)": total,
            "Challan No": get_val([r"Challan No\s*[:\-]?\s*(\d+)"]),
            "BSR Code": get_val([r"BSR Code\s*[:\-]?\s*(\d+)"])
        })
    return rows

# ----------- PROCESS FLOW -----------
if files:
    all_data = []
    for f in files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_data += extract_all(text)

    if all_data:
        df = pd.DataFrame(all_data)
        
        st.markdown("### 📊 Auditor Insights")
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Challans", len(df))
        m2.metric("Total Tax", f"₹{df['Tax (₹)'].sum():,.2f}")
        late_count = len(df[df['Status'].str.contains("Late")])
        m3.metric("Late Payments", late_count, delta=late_count, delta_color="inverse")

        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.pie(df, names='Section', values='Tax (₹)', 
                         title="Tax Contribution by Section", hole=0.4,
                         color_discrete_sequence=px.colors.qualitative.Prism)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown('<div class="zone">📥 Audit Report Ready (IT Act 2026 Compliant)</div>', unsafe_allow_html=True)
            st.download_button("🚀 Download Excel with Statutory Rate Audit", data=to_excel(df), file_name="TDS_Challan_Statutory_Audit.xlsx")

        st.dataframe(df.style.format({"Tax (₹)": "{:,.2f}", "Total Paid (₹)": "{:,.2f}", "Effective Rate (%)": "{:.2f}%", "Statutory Rate (%)": "{:.2f}%"}), use_container_width=True)
    else:
        st.error("❌ No valid patterns found. Ensure your PDF is not a scanned image.")

st.caption("⚙️ Statutory Auditor Pro developed by Abhishek Jakkula")
