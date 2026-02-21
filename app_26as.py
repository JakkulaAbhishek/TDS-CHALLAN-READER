import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from openpyxl.styles import Font
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import plotly.express as px

# ---------------- UI CONFIG ----------------
st.set_page_config(page_title="TDS Challan AI Extractor", layout="wide")

# ----------- ULTRA STYLISH CSS -----------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: #0f172a; color: #f8fafc; }

    .header-title {
        background: linear-gradient(90deg, #38bdf8, #22c55e);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 3rem; text-align: center; margin-bottom: 0px;
    }
    .quote {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 25px;
        backdrop-filter: blur(10px); color: #cbd5e1; font-style: italic;
    }
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        padding: 20px; border-radius: 16px;
    }
    .stButton>button {
        background: linear-gradient(90deg, #10b981, #3b82f6);
        color: white !important; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ----------- HEADER -----------
st.markdown('<div class="header-title">🕉️ TDS CHALLAN AI EXTRACTOR</div>', unsafe_allow_html=True)
st.markdown("""
<div class="quote">
    "One must elevate oneself by one’s own mind, not degrade oneself. 
    The mind can be the friend of the self, and the mind can also be the enemy." — <b>Lord Krishna</b>
</div>
""", unsafe_allow_html=True)

# ----------- MAPPING DICTIONARY -----------
SECTION_MAP = {
    "94C": "194C - Contractor",
    "94J": "194J - Professional",
    "94I": "194I - Rent",
    "94H": "194H - Commission",
    "92B": "192 - Salary",
    "94Q": "194Q - Goods Purchase"
}

# ----------- FILE UPLOAD -----------
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    files = st.file_uploader("📄 Drop your TDS Challan PDFs here", type="pdf", accept_multiple_files=True)

# ----------- EXCEL EXPORT -----------
def to_excel(df):
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TDS_Report")
        ws = writer.sheets["TDS_Report"]
        for cell in ws[1]:
            cell.font = Font(bold=True)
        # Auto-adjust width
        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try: max_length = max(max_length, len(str(cell.value)))
                except: pass
            ws.column_dimensions[column].width = max_length + 2
    return buf.getvalue()

# ----------- EXTRACTION ENGINE -----------
def extract_all(text):
    # Split by common challan receipt markers
    challans = re.split(r"Challan Receipt|Taxpayer Counterfoil", text)
    rows = []

    for ch in challans:
        if not re.search(r"Challan No\s*:\s*\d+", ch) and "CIN" not in ch:
            continue

        def get_val(pattern):
            m = re.search(pattern, ch, re.IGNORECASE)
            return m.group(1).replace(",", "").strip() if m else "0"

        # Date and Nature
        dep_date_str = get_val(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})")
        if dep_date_str == "0": continue
        
        dep_date = datetime.strptime(dep_date_str, "%d-%b-%Y")
        nature_code = get_val(r"Nature of Payment\s*:\s*(\w+)")
        nature_desc = SECTION_MAP.get(nature_code, nature_code)

        # Money Values
        tax = float(get_val(r"A\s*Tax\s*₹?\s*([\d,.]+)"))
        interest = float(get_val(r"D\s*Interest\s*₹?\s*([\d,.]+)"))
        total = float(get_val(r"Total\s*\(.*?\)\s*₹?\s*([\d,.]+)"))

        # TDS Month Logic
        tds_month_date = dep_date - relativedelta(months=1)
        tds_month = tds_month_date.strftime("%B")
        due_date = (tds_month_date + relativedelta(months=1)).replace(day=7)
        delay_days = (dep_date - due_date).days

        # Effective Month based on interest
        if interest > 0 and tax > 0:
            months_delay = math.ceil(interest / (tax * 0.015))
            eff_month = (dep_date - relativedelta(months=months_delay)).strftime("%B")
        else:
            eff_month = tds_month

        rows.append({
            "Financial Year": get_val(r"Financial Year\s*:\s*([\d\-]+)"),
            "Nature of Payment": nature_desc,
            "TDS Month": tds_month,
            "Effective Month": eff_month,
            "Deposit Date": dep_date_str,
            "Due Date": due_date.strftime("%d-%b-%Y"),
            "Delay (Days)": max(0, delay_days),
            "Status": "On Time ✅" if delay_days <= 0 else "Late ⚠️",
            "Challan No": get_val(r"Challan No\s*:\s*(\d+)"),
            "BSR Code": get_val(r"BSR Code\s*:\s*(\d+)"),
            "Tax Amount": tax,
            "Interest": interest,
            "Total Paid": total
        })
    return rows

# ----------- MAIN PROCESS -----------
if files:
    all_data = []
    for f in files:
        with pdfplumber.open(f) as pdf:
            text = "\n".join([p.extract_text() for p in pdf.pages if p.extract_text()])
            all_data += extract_all(text)

    if all_data:
        df = pd.DataFrame(all_data)
        
        # Dashboard Metrics
        st.markdown("### 📊 Extraction Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Challans", len(df))
        m2.metric("Total Tax", f"₹{df['Tax Amount'].sum():,.0f}")
        m3.metric("Total Paid", f"₹{df['Total Paid'].sum():,.0f}")
        late_count = len(df[df['Status'] == "Late ⚠️"])
        m4.metric("Late Payments", late_count, delta=late_count, delta_color="inverse")

        # Visuals
        st.markdown("---")
        c1, c2 = st.columns([1, 1])
        with c1:
            fig = px.pie(df, names='Nature of Payment', values='Tax Amount', 
                         title="TDS Distribution by Nature", hole=0.4,
                         color_discrete_sequence=px.colors.sequential.Greens_r)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", font=dict(color="white"))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 📥 Ready for Export")
            st.write("Review the data below. The Excel file is auto-formatted with bold headers and proper column widths.")
            st.download_button(
                "🚀 Download Formatted Excel Report",
                data=to_excel(df),
                file_name=f"TDS_Challan_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"
            )

        st.markdown("### 🔍 Data Preview")
        st.dataframe(df, use_container_width=True)

    else:
        st.error("❌ No valid TDS Challan patterns found in the uploaded PDFs.")

# ----------- FOOTER -----------
st.markdown("<br><hr>", unsafe_allow_html=True)
st.caption("⚙️ Pro Version developed by अभिषेक जक्कुला (Abhishek Jakkula)")
