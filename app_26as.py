import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="TDS Divine Bulk Parser",
    page_icon="🦚",
    layout="wide"
)

# ---------- STYLING ----------
st.markdown("""
<style>
.big-title {
    text-align:center;
    color:#1e3c72;
    font-size:40px;
    font-weight:bold;
}
.subtitle {
    text-align:center;
    color:gold;
    font-size:20px;
}
.footer {
    text-align:center;
    color:grey;
}
</style>
""", unsafe_allow_html=True)

# ---------- HEADER ----------
st.markdown('<p class="big-title">🦚 TDS Divine Bulk Parser</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">"Like Krishna guiding Arjuna, this tool guides your compliance."</p>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📄 Upload One or More TDS Challan PDFs",
    type="pdf",
    accept_multiple_files=True
)

# ---------- FUNCTIONS ----------
def extract_data(text):

    def search(pattern):
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    return {
        "Financial Year": search(r"Financial Year\s*:\s*([\d\-]+)"),
        "Nature of Payment": search(r"Nature of Payment\s*:\s*(\S+)"),
        "Amount": search(r"Amount \(in Rs.\)\s*:\s*₹?\s*([\d,]+)"),
        "Challan No": search(r"Challan No\s*:\s*(\d+)"),
        "Deposit Date": search(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})"),
        "Interest": search(r"Interest ₹\s*([\d,]+)")
    }

def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

# ---------- MAIN ----------
if uploaded_files:

    rows = []
    s_no = 1

    for file in uploaded_files:

        try:
            with pdfplumber.open(file) as pdf:
                text = ""
                for page in pdf.pages:
                    if page.extract_text():
                        text += page.extract_text()

            data = extract_data(text)

            if not data["Deposit Date"] or not data["Amount"]:
                continue

            deposit_date = datetime.strptime(
                data["Deposit Date"], "%d-%b-%Y"
            )

            tds_month = (
                deposit_date - relativedelta(months=1)
            ).strftime("%B")

            amount = float(data["Amount"].replace(",", ""))

            interest_present = (
                float(data["Interest"].replace(",", ""))
                if data["Interest"] else 0
            )

            calc_interest = (
                round(amount * 0.015, 2)
                if interest_present > 0 else 0
            )

            rows.append({
                "S.No": s_no,
                "Financial Year": data["Financial Year"],
                "TDS Month": tds_month,
                "Date of Deposit": data["Deposit Date"],
                "Nature of Payment": data["Nature of Payment"],
                "Challan No": data["Challan No"],
                "Amount (₹)": amount,
                "1.5% Interest (₹)": calc_interest
            })

            s_no += 1

        except:
            st.warning(f"⚠️ Error reading {file.name}")

    # ---------- OUTPUT ----------
    if rows:

        df = pd.DataFrame(rows)

        st.success(f"✅ Extracted {len(df)} challans")

        st.dataframe(df, use_container_width=True)

        excel = convert_to_excel(df)

        st.download_button(
            "📥 Download Excel",
            data=excel,
            file_name="TDS_Bulk_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("""
        <h3 style='text-align:center;color:purple;'>
        🌸 "Dharma in taxation leads to peace in life." – Lord Krishna
        </h3>
        """, unsafe_allow_html=True)

# ---------- FOOTER ----------
st.markdown("---")
st.markdown(
    '<p class="footer">⚙️ Tool developed by Abhishek Jakkula</p>',
    unsafe_allow_html=True
)
