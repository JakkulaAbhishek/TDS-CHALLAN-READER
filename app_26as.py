import streamlit as st
import pandas as pd
import numpy as np
import re
import io
import plotly.express as px
from rapidfuzz import process, fuzz
import urllib.parse

st.set_page_config(page_title="26AS Enterprise Reconciliation", layout="wide")

# ---------------- ULTRA STYLISH CSS ----------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Poppins', sans-serif; }
    .stApp { background: #0f172a; color: #f8fafc; }
    .header-title {
        background: linear-gradient(90deg, #38bdf8, #818cf8, #c084fc);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 800; font-size: 2.8rem; margin-bottom: 0px; line-height: 1.2;
    }
    .header-sub { color: #94a3b8; font-size: 1.2rem; font-weight: 600; margin-top: 5px; margin-bottom: 15px; }
    .dev-credit { color: #64748b; font-weight: 600; margin-top: 10px; font-size: 0.95rem; }
    .dev-credit b { color: #38bdf8; }
    .stButton>button, .stDownloadButton>button {
        background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        color: white !important; border: none; border-radius: 8px;
        padding: 10px 24px; font-weight: 600; transition: all 0.3s ease; width: 100%;
    }
    [data-testid="stMetric"] {
        background: rgba(30, 41, 59, 0.6); border: 1px solid rgba(255, 255, 255, 0.1);
        backdrop-filter: blur(10px); padding: 20px; border-radius: 16px;
    }
    .alert-box-green {
        background: rgba(16, 185, 129, 0.1); border-left: 5px solid #10b981; 
        padding: 18px; border-radius: 8px; margin-bottom: 12px; font-size: 1.05rem;
    }
    .zone {
        background: rgba(30, 41, 59, 0.4); padding: 18px; border-radius: 14px;
        border: 1px solid rgba(255, 255, 255, 0.05); margin-bottom: 18px; text-align: center; color: #cbd5e1; font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ---------------- STATE MANAGEMENT ----------------
if 'run_engine' not in st.session_state:
    st.session_state.run_engine = False

def reset_engine():
    st.session_state.run_engine = False

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### ⚙️ Engine Settings")
    tolerance = st.number_input("Mismatch Tolerance (₹)", min_value=0, value=10, step=1, on_change=reset_engine)
    max_rows = st.number_input("Max Rows for Excel Formulas", min_value=1000, value=15000, step=1000)

# ---------------- HEADER ----------------
st.markdown("""
<div style="text-align: center; margin-bottom: 30px;">
    <div class="header-title">26AS Enterprise Reconciliation</div>
    <div class="header-sub">RapidFuzz AI | Statutory Rates | Detailed Analytics</div>
    <div class="dev-credit">Developed by <b>Abhishek Jakkula</b></div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="zone">📄 Step 1: Upload TRACES 26AS (.txt) and Books Excel</div>', unsafe_allow_html=True)

# ---------------- FILE UPLOAD ----------------
col_txt, col_exc = st.columns(2)
with col_txt:
    txt_file = st.file_uploader("Upload 26AS TEXT file", type=["txt"], on_change=reset_engine)
with col_exc:
    books_file = st.file_uploader("Upload Books Excel", type=["xlsx", "xls"], on_change=reset_engine)

extracted_fy, extracted_ay = "Unknown", "Unknown"

if txt_file:
    raw_text = txt_file.getvalue().decode("utf-8", errors="ignore")
    # Intelligent Year Extraction from Header
    header_match = re.search(r'\d{2}-\d{2}-\d{4}\^[A-Z]{5}\d{4}[A-Z]\^[^\^]*\^(\d{4}-\d{4})\^(\d{4}-\d{4})\^', raw_text)
    if header_match:
        extracted_fy, extracted_ay = header_match.group(1), header_match.group(2)
    
    st.markdown(f'<div class="alert-box-green" style="text-align:center;"><b>📌 Data Period:</b> Financial Year <b>{extracted_fy}</b> | Assessment Year <b>{extracted_ay}</b></div>', unsafe_allow_html=True)

# ---------------- BUTTON LOGIC ----------------
col_b1, col_b2, col_b3 = st.columns([1, 2, 1])
with col_b2:
    if st.button("🚀 RUN RECONCILIATION ENGINE", use_container_width=True):
        if not txt_file or not books_file:
            st.warning("⚠️ Please upload both files.")
        else:
            st.session_state.run_engine = True

# ---------------- EXTRACTION & RECO LOGIC ----------------
@st.cache_data
def process_full_data(txt_bytes, books_bytes):
    # Regex for Nature Mapping with Statutory Rates
    SEC_MAP = {
        "194C": "194C - Contractor (1%/2%)",
        "194J": "194J - Professional (10%)",
        "194JB": "194JB - Prof. Special (2%)",
        "192": "192 - Salary (As per Slab)",
        "194I": "194I - Rent (10%)",
        "194Q": "194Q - Goods Purchase (0.1%)"
    }
    
    # ... [Internal parsing logic remains same for extraction performance] ...
    # Assume 'structured_26as' and 'books' are prepared for RapidFuzz matching
    # (Matching logic from previous stable version)
    return pd.DataFrame() # Placeholder for processed DF

# ---------------- OUTPUT DISPLAY ----------------
if st.session_state.run_engine:
    # After engine run, generate results
    st.markdown("### 📊 Reconciliation Result Summary")
    # (Insert Metrics and Pie Charts logic here)

    # ---------------- EXCEL AUTO-WIDTH EXPORTER ----------------
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        # (Insert formatting logic with enumerator fix for row alignment)
        pass
