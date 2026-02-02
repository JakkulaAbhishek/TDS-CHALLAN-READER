import streamlit as st
import pdfplumber
import re
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta
from io import BytesIO

st.set_page_config(page_title="TDS Divine Bulk Parser", page_icon="🦚", layout="wide")

# ---------- HEADER UI ----------
st.markdown("""
<h1 style='text-align:center;color:#1e3c72;'>
🦚 TDS Divine Bulk Parser
</h1>

<h4 style='text-align:center;color:gold;'>
“Like Krishna guiding Arjuna, this tool guides your compliance.”
</h4>
""", unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    "📄 Upload One or More TDS Challan PDFs",
    type="pdf",
    accept_multiple_files=True
)

# ---------- FUNCTIONS ----------
def extract_data(text):

    def search(pattern):
        m = re.search(pattern, text)
        return m.group(1) if m else ""

    data = {}

    data["Financial Year"] = search(r"Financial Year\s*:\s*([\d\-]+)")
    data["Nature of Payment"] = search(r"Nature of Payment\s*:\s*(\S+)")
    data["Amount"] = search(r"Amount \(in Rs.\)\s*:\s*₹?\s*([\d,]+)")
    data["Challan No"] = search(r"Challan No\s*:\s*(\d+)")
    data["Deposit Date"] = search(r"Date of Deposit\s*:\s*(\d{2}-[A-Za-z]{3}-\d{4})")
    data["Interest"] = search(r"Interest ₹\s*([\d,]+)")

    return data


def convert_to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name="TDS Data")
    return output.getvalue()


# ---------- MAIN ----------
if uploaded_files:

    all_rows = []
    s_no = 1

    for file in uploaded_files:

        try:
            with pdfplumber.open(file) as pdf:
                text = ""
                for page in pdf.pages:
                    if page.extract_text():
                        text += page.extract_text()

            d = extract_data(text)

            # Skip if key fields missing
            if not d["Deposit Date"] or not d["Amount"]:
                continue

            # Date logic
            dep_date = datetime.strptime(d["Deposit Date"], "%d-%b-%Y")
            tds_month = (dep_date - relativedelta(months=1)).strftime("%B")

            # Amount
            amount = float(d["Amount"].replace(",", ""))

            # Interest
            interest_present = float(d["Interest"].replace(",", "")) if d["Interest"] else 0
            calc_interest = round(amount * 0.015, 2) if interest_present > 0 else 0

            row = {
                "S.No": s_no,
                "Financial Year": d["Financial Year"],
                "TDS Month": tds_month,
                "Date of Deposit": d["Deposit Date"],
                "Nature of Payment": d["Nature of Payment"],
                "Challan No": d["Challan No"],
                "Amount (₹)": amount,
                "1.5% Interest (₹)": calc_interest
            }

            all_rows.append(row)
            s_no += 1

        except:
            st.warning(f"⚠️ Could not read file: {file.name}")

    # ---------- OUTPUT ----------
    if all_rows:

        df = pd.DataFrame(all_rows)

        st.success(f"✨ Successfully extracted {len(df)} challans")

        st.dataframe(df, use_container_width=True)

        # Excel Download
        excel_file = convert_to_excel(df)

        st.download_button(
            label="📥 Download All as Excel",
            data=excel_file,
            file_name="Bulk_TDS_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.markdown("""
        <h3 style='color:purple;text-align:center;'>
        🌸 “Dharma in taxation leads to peace in life.” – Lord Krishna
        </h3>
        """, unsafe_allow_html=True)

# ---------- FOOTER ----------
st.markdown("""
---
<h5 style='text-align:center;color:grey;'>
⚙️ Tool developed by Abhishek Jakkula
</h5>
""", unsafe_allow_html=True)
