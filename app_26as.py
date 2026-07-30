import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import math
import plotly.express as px

# ---------- UI CONFIG ----------
st.set_page_config(page_title="TDS AI Auditor Pro | Abhishek Jakkula", layout="wide", page_icon="⚖️")

# ---------- CUSTOM GLASSMORPHIC CSS (same as original, omitted for brevity) ----------
st.markdown("""
<style>
    ... (keep your original CSS here) ...
</style>
""", unsafe_allow_html=True)

# ---------- COMPREHENSIVE TDS RATES (FY 2025-26) ----------
SECTION_DATA = {
    "192":  {"desc": "Salary",                     "rate": "Slab rates",            "limit": "Basic exemption limit"},
    "192A": {"desc": "Premature EPF withdrawal",   "rate": "10%",                  "limit": "₹ 50,000"},
    "193":  {"desc": "Interest on Securities",      "rate": "10%",                  "limit": "₹ 10,000"},
    "194":  {"desc": "Dividends",                   "rate": "10%",                  "limit": "₹ 10,000"},
    "194A": {"desc": "Interest (Bank/Post Office)", "rate": "10%",                  "limit": "₹ 50,000 (Gen) / ₹ 1,00,000 (Sr. Citizen)"},
    "194B": {"desc": "Winnings (Lottery/Puzzle)",   "rate": "30%",                  "limit": "₹ 10,000 (Single)"},
    "194BA":{"desc": "Online gaming winnings",      "rate": "30%",                  "limit": "N/A"},
    "194BB":{"desc": "Winnings from horse races",   "rate": "30%",                  "limit": "₹ 10,000 (Aggregate)"},
    "194C": {"desc": "Payment to contractors",      "rate": "1% (Ind/HUF) / 2%",    "limit": "₹ 30,000 / ₹ 1 Lakh"},
    "194D": {"desc": "Insurance Commission",        "rate": "2% (Ind/HUF) / 10%",   "limit": "₹ 20,000"},
    "194DA":{"desc": "Life Insurance Policy",       "rate": "2%",                   "limit": "₹ 1 Lakh"},
    "194EE":{"desc": "NSS Deposits",               "rate": "10%",                  "limit": "₹ 2,500"},
    "194G": {"desc": "Lottery Commission",          "rate": "2%",                   "limit": "₹ 20,000"},
    "194H": {"desc": "Commission or Brokerage",     "rate": "2%",                   "limit": "₹ 20,000"},
    "194I": {"desc": "Rent (Plant & Machinery)",    "rate": "2%",                   "limit": "₹ 6,00,000"},
    "194IA":{"desc": "Rent (Immovable Property)",   "rate": "10%",                  "limit": "₹ 6,00,000"},
    "194IB":{"desc": "Rent (Ind/HUF)",              "rate": "2%",                   "limit": "₹ 50,000 pm"},
    "194J(a)":{"desc":"Tech Services/Royalty/Call Centre","rate":"2%","limit":"₹ 50,000"},
    "194J(b)":{"desc":"Professional Services",      "rate":"10%",                  "limit":"₹ 50,000"},
    "194LA":{"desc": "Enhanced Compensation",       "rate": "10%",                  "limit": "₹ 5 Lakhs"},
    "194M": {"desc": "Payment for Contracts/Prof.", "rate": "2%",                   "limit": "₹ 50 Lakhs"},
    "194N": {"desc": "Cash withdrawal",             "rate": "2% / 5%",              "limit": "₹ 20 Lakh / ₹ 1 Cr"},
    "194O": {"desc": "E‑commerce participants",     "rate": "0.10%",                "limit": "₹ 5 Lakhs"},
    "194P": {"desc": "Specified Senior Citizen",    "rate": "Slab Rates",           "limit": "Basic Exemption"},
    "194Q": {"desc": "Purchase of Goods",           "rate": "0.10%",                "limit": "₹ 50 Lakhs"},
    "194R": {"desc": "Benefits/Perquisites",        "rate": "10%",                  "limit": "₹ 20,000"},
    "194S": {"desc": "Virtual Digital Assets",      "rate": "1%",                   "limit": "₹ 10,000 / ₹ 50,000"},
    "194T": {"desc": "Payment to Partner of Firm",  "rate": "10%",                  "limit": "₹ 20,000"}
}

# ---------- HELPER: Clean numeric ----------
def clean_num(text):
    if not text: return 0.0
    return float(re.sub(r'[^\d.]', '', str(text)))

# ---------- ADVANCED CHALLAN PARSER ----------
def parse_challans(pdf_path):
    """
    Extract all challans from a PDF, returning list of dicts with:
    - cin, bsr, challan_date, section_raw, tax, surcharge, cess, interest, late_fee, total,
      deduction_date (if found), assessment_year
    """
    challans = []
    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                full_text += t + "\n"

    # Split by CIN pattern: BSRCODE + 5digits + Date (DDMMYYYY)
    cin_pattern = re.compile(r'(\d{7})\s*(\d{5})\s*(\d{8})')  # BSR (7 digits), Challan Sr.No. (5), Deposit Date (DDMMYYYY)
    splits = cin_pattern.split(full_text)

    if len(splits) < 4:  # no CIN found, treat whole text as one block (legacy)
        blocks = [full_text]
    else:
        blocks = []
        for i in range(1, len(splits)-2, 3):
            cin = splits[i] + splits[i+1] + splits[i+2]
            text_block = splits[i+3] if (i+3) < len(splits) else ""
            blocks.append(cin + " " + text_block)

    for block in blocks:
        # Extract CIN components
        cin_match = re.search(r'(\d{7})\s*(\d{5})\s*(\d{8})', block)
        if not cin_match:
            continue
        bsr = cin_match.group(1)
        ch_sr = cin_match.group(2)
        dep_date_str = cin_match.group(3)
        try:
            dep_date = datetime.strptime(dep_date_str, "%d%m%Y")
        except:
            continue

        # Extract Section
        section_raw = ""
        sec_match = re.search(r'(?:Section|Nature\s*of\s*Payment)\s*[:\-]?\s*(\d{3,4}[A-Z]?(?:\([a-z]\))?)', block, re.I)
        if sec_match:
            section_raw = sec_match.group(1).upper()

        # Amounts
        def find_amount(label):
            m = re.search(rf'{label}\s*[:\-]?\s*₹?\s*([\d,]+\.?\d*)', block, re.I)
            return clean_num(m.group(1)) if m else 0.0

        tax = find_amount(r'(?:Income\s*)?Tax')
        surcharge = find_amount(r'Surcharge')
        cess = find_amount(r'(?:Education\s*)?Cess')
        interest = find_amount(r'Interest')
        late_fee = find_amount(r'(?:Late\s*)?Filing\s*Fee')
        total = find_amount(r'(?:Total|Amount\s*Paid)')

        # Try to get deduction date (often "Tax Deducted" date)
        ded_match = re.search(r'(?:Date\s*of\s*Deduction|Tax\s*Deducted\s*on)\s*[:\-]?\s*(\d{2}[/-]\w{3}[/-]\d{4})', block, re.I)
        deduction_date = None
        if ded_match:
            try:
                deduction_date = datetime.strptime(ded_match.group(1).replace("/", "-"), "%d-%b-%Y")
            except:
                pass

        # Assessment Year
        ay_match = re.search(r'Assessment\s*Year\s*[:\-]?\s*(\d{4}-\d{2,4})', block, re.I)
        ay = ay_match.group(1) if ay_match else ""

        challans.append({
            "CIN": f"{bsr}{ch_sr}{dep_date_str}",
            "BSR": bsr,
            "Challan Sr.No.": ch_sr,
            "Deposit Date": dep_date.strftime("%d-%b-%Y"),
            "Section Raw": section_raw,
            "Tax": tax,
            "Surcharge": surcharge,
            "Cess": cess,
            "Interest Paid": interest,
            "Late Fee Paid": late_fee,
            "Total Amount": total,
            "Deduction Date": deduction_date.strftime("%d-%b-%Y") if deduction_date else "",
            "Assessment Year": ay
        })
    return challans

# ---------- INTEREST CALCULATION ----------
def compute_interest(deduction_date, deposit_date, tds_amount):
    """
    Interest under Section 201(1A): 1.5% per month or part of month
    from date of deduction to date of payment.
    """
    if not deduction_date or tds_amount == 0:
        return 0.0, "N/A"
    # Count complete months and any part thereof
    delta = relativedelta(deposit_date, deduction_date)
    months = delta.years * 12 + delta.months
    if delta.days > 0:
        months += 1  # part of month counts as full
    interest = tds_amount * 0.015 * months
    return round(interest, 2), f"{months} month(s)"

def get_due_date(tds_month_end):
    """TDS due date: 7th of next month, except for March → 30th April."""
    m = tds_month_end.month
    y = tds_month_end.year
    if m == 3:
        return datetime(y, 4, 30)
    else:
        return (datetime(y, m, 1) + relativedelta(months=1)).replace(day=7)

# ---------- BUILD AUDIT ROWS ----------
def build_audit_rows(challans):
    rows = []
    for ch in challans:
        # Determine section code for lookup
        raw = ch["Section Raw"]
        # Clean up: e.g., "194A" or "0194A" → "194A"
        code = re.sub(r'^0*', '', raw)
        if code in SECTION_DATA:
            sec_info = SECTION_DATA[code]
        else:
            # fallback
            sec_info = {"desc": "Other Transaction", "rate": "Verify per Act", "limit": "N/A"}

        # Tax paid = Tax + Surcharge + Cess
        tax_paid = ch["Tax"] + ch["Surcharge"] + ch["Cess"]
        interest_paid = ch["Interest Paid"]

        # Determine deduction date: if available, use it; else assume last day of TDS month
        if ch["Deduction Date"]:
            ded_date = datetime.strptime(ch["Deduction Date"], "%d-%b-%Y")
        else:
            # estimate: deposit date minus 1 month, last day
            dep = datetime.strptime(ch["Deposit Date"], "%d-%b-%Y")
            ded_date = (dep - relativedelta(months=1)).replace(day=1) + relativedelta(day=31)
            # ensure it's the correct month end
            ded_date = ded_date - timedelta(days=ded_date.day)  # last day of previous month

        # Correct interest as per act
        required_interest, months_str = compute_interest(ded_date, datetime.strptime(ch["Deposit Date"], "%d-%b-%Y"), tax_paid)
        interest_gap = round(required_interest - interest_paid, 2)

        # TDS Month label
        tds_month = ded_date.strftime("%B %Y") if ded_date else "Unknown"

        rows.append({
            "CIN": ch["CIN"],
            "Section Code": code,
            "Nature of Transaction": sec_info["desc"],
            "Rate per Act": sec_info["rate"],
            "Exemption Limit": sec_info["limit"],
            "Deduction Date": ded_date.strftime("%d-%b-%Y"),
            "TDS Month": tds_month,
            "Deposit Date": ch["Deposit Date"],
            "Due Date": get_due_date(ded_date).strftime("%d-%b-%Y") if ded_date else "",
            "Tax Paid (₹)": tax_paid,
            "Interest Paid (₹)": interest_paid,
            "Required Interest (₹)": required_interest,
            "Interest Gap (₹)": interest_gap,
            "Delay Reason": f"{months_str} delay" if required_interest > 0 else "On time",
            "Assessment Year": ch["Assessment Year"]
        })
    return rows

# ---------- EXCEL EXPORT (ENHANCED) ----------
def to_excel_with_dashboard(df):
    output = BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Audit Data', index=False)

    workbook = writer.book
    worksheet = writer.sheets['Audit Data']

    # Add data bars for Interest Gap
    worksheet.conditional_format('J2:J{}'.format(len(df)+1), {'type': 'data_bar',
                                  'bar_color': '#63C384'})

    # Dashboard sheet
    dash = workbook.add_worksheet('Dashboard')
    summary = df.groupby('Section Code').agg(
        Total_Tax=('Tax Paid (₹)', 'sum'),
        Total_Interest_Paid=('Interest Paid (₹)', 'sum'),
        Interest_Gap=('Interest Gap (₹)', 'sum')
    ).reset_index()
    summary.to_excel(writer, sheet_name='Dashboard', startrow=1, startcol=0, index=False)

    # Chart
    chart = workbook.add_chart({'type': 'pie'})
    chart.add_series({
        'name': 'Tax Distribution',
        'categories': ['Dashboard', 2, 0, 1+len(summary), 0],
        'values':     ['Dashboard', 2, 1, 1+len(summary), 1],
        'data_labels': {'percentage': True, 'position': 'outside_end'},
    })
    chart.set_title({'name': 'Tax by Section'})
    dash.insert_chart('F2', chart)

    # Interest Working sheet (for full transparency)
    working = workbook.add_worksheet('Interest Working')
    working.write(0, 0, "CIN")
    working.write(0, 1, "Tax Amount")
    working.write(0, 2, "Deduction Date")
    working.write(0, 3, "Deposit Date")
    working.write(0, 4, "Months Delayed")
    working.write(0, 5, "Interest @1.5%")
    working.write(0, 6, "Paid Interest")
    working.write(0, 7, "Gap")

    for i, row in df.iterrows():
        working.write(i+1, 0, row['CIN'])
        working.write(i+1, 1, row['Tax Paid (₹)'])
        working.write(i+1, 2, row['Deduction Date'])
        working.write(i+1, 3, row['Deposit Date'])
        # Months delayed derived from required interest formula
        tax = row['Tax Paid (₹)']
        req_int = row['Required Interest (₹)']
        months = round(req_int / (tax * 0.015)) if tax else 0
        working.write(i+1, 4, months)
        working.write(i+1, 5, req_int)
        working.write(i+1, 6, row['Interest Paid (₹)'])
        working.write(i+1, 7, row['Interest Gap (₹)'])

    # Full TDS Reference
    ref_sheet = workbook.add_worksheet('TDS Rates Reference')
    ref_sheet.write(0, 0, 'Section Code')
    ref_sheet.write(0, 1, 'Nature of Transaction')
    ref_sheet.write(0, 2, 'Rate')
    ref_sheet.write(0, 3, 'Threshold Limit')
    for i, (code, info) in enumerate(SECTION_DATA.items()):
        ref_sheet.write(i+1, 0, code)
        ref_sheet.write(i+1, 1, info['desc'])
        ref_sheet.write(i+1, 2, info['rate'])
        ref_sheet.write(i+1, 3, info['limit'])

    writer.close()
    return output.getvalue()

# ---------- STREAMLIT UI ----------
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="main-header">⚖️ TDS AI AUDITOR PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="branding-sub">Developed by Abhishek Jakkula</div>', unsafe_allow_html=True)
st.markdown('<div class="contact-sub">Statutory Compliance & Interest Analyzer (FY 2025-26)</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader("📂 Upload TDS Challan PDFs (ITNS 280/281)", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_challans = []
    with st.status("🔍 Parsing uploaded PDFs...", expanded=True) as status:
        for f in uploaded_files:
            st.write(f"Processing: **{f.name}**")
            try:
                challans = parse_challans(f)
                all_challans.extend(challans)
                st.write(f"✅ Found {len(challans)} challan(s)")
            except Exception as e:
                st.error(f"❌ Error reading {f.name}: {e}")
        status.update(label="Parsing complete!", state="complete")

    if all_challans:
        df_raw = pd.DataFrame(all_challans)
        st.subheader("📋 Extracted Data (Edit if needed)")
        edited_df = st.data_editor(df_raw, num_rows="dynamic", use_container_width=True)

        if st.button("🔍 Run TDS Audit"):
            with st.spinner("Calculating interest and compliance gaps..."):
                audit_rows = build_audit_rows(edited_df.to_dict('records'))
                df_audit = pd.DataFrame(audit_rows)

            st.markdown("### 📊 Audit Dashboard")
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(px.pie(df_audit, names='Section Code', values='Tax Paid (₹)', hole=0.4,
                                       title="Tax by Section", template="plotly_dark"),
                                use_container_width=True)
            with col2:
                st.plotly_chart(px.bar(df_audit, x='TDS Month', y='Tax Paid (₹)', color='Section Code',
                                       title="Monthly Trend", template="plotly_dark"),
                                use_container_width=True)

            st.download_button(
                label="📥 Download Excel Report (with working)",
                data=to_excel_with_dashboard(df_audit),
                file_name=f"TDS_Audit_Pro_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            st.markdown("### 📜 Detailed Audit Table")
            # Highlight gaps
            def highlight_gap(val):
                color = 'red' if val > 0 else 'green'
                return f'color: {color}; font-weight: bold'
            styled_df = df_audit.style.applymap(highlight_gap, subset=['Interest Gap (₹)'])
            st.dataframe(styled_df, use_container_width=True)

            with st.expander("📖 View Full TDS Rate Card"):
                rates_df = pd.DataFrame(SECTION_DATA).T.reset_index().rename(
                    columns={"index":"Code","desc":"Nature of Transaction","rate":"Rate","limit":"Threshold"})
                st.table(rates_df)

    else:
        st.warning("No valid challans detected. Please check the PDF format or upload manually.")

st.markdown('</div>', unsafe_allow_html=True)
st.markdown("""
<div class="footer">
    <span style="font-weight:700;">Tool Developed by Abhishek Jakkula</span><br>
    <span>📧 <a href="mailto:jakkulaabhishek5@gmail.com">jakkulaabhishek5@gmail.com</a></span>
</div>
""", unsafe_allow_html=True)
