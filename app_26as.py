import streamlit as st
import pdfplumber
import re
import pandas as pd
from io import BytesIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
import math
import plotly.express as px
import plotly.graph_objects as go

# ---------------- UI CONFIG ----------------
st.set_page_config(
    page_title="TDS AI Auditor Pro | Abhishek Jakkula",
    layout="wide",
    page_icon="⚖️",
    initial_sidebar_state="expanded"
)

# ----------- ULTRA PREMIUM UI V2 -----------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
    --accent: #6366f1;
    --accent-2: #8b5cf6;
    --glass: rgba(255, 255, 255, 0.08);
    --glass-border: rgba(255, 255, 255, 0.12);
    --text-main: #ffffff;
    --text-muted: rgba(255,255,255,0.7);
}

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.stApp {
    background: radial-gradient(at 0% 0%, #6366f1 0px, transparent 50%),
                radial-gradient(at 100% 0%, #ec4899 0px, transparent 50%),
                radial-gradient(at 100% 100%, #06b6d4 0px, transparent 50%),
                radial-gradient(at 0% 100%, #8b5cf6 0px, transparent 50%),
                #0f0f23;
    background-attachment: fixed;
}

.main-header {
    font-weight: 800;
    font-size: clamp(2.2rem, 5vw, 3.8rem);
    text-align: center;
    background: linear-gradient(90deg, #fff 0%, #c7d2fe 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    letter-spacing: -0.03em;
    margin-bottom: 0;
}
.sub-brand {
    text-align:center; color: var(--text-muted);
    font-weight: 500; letter-spacing: 0.2em; text-transform: uppercase;
    font-size: 0.85rem; margin-top: 8px;
}

.glass-card {
    background: linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.05));
    backdrop-filter: blur(24px);
    -webkit-backdrop-filter: blur(24px);
    border-radius: 24px;
    border: 1px solid var(--glass-border);
    padding: 1.8rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.1);
}

.metric-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.2rem;
    backdrop-filter: blur(12px);
}

.stFileUploader > div {
    background: rgba(255,255,255,0.05)!important;
    border: 2px dashed rgba(139, 92, 246, 0.5)!important;
    border-radius: 20px!important;
    padding: 2.5rem!important;
}

.stButton>button,.stDownloadButton>button {
    background: linear-gradient(90deg, #6366f1, #8b5cf6)!important;
    color: white!important;
    border-radius: 999px!important;
    padding: 0.75rem 1.8rem!important;
    font-weight: 700!important;
    border: none!important;
    letter-spacing: 0.05em;
    box-shadow: 0 8px 20px rgba(99,102,241,0.4);
    transition: all 0.2s ease!important;
}
.stButton>button:hover { transform: translateY(-2px); box-shadow: 0 12px 28px rgba(99,102,241,0.6); }

[data-testid="stDataFrame"] { border-radius: 16px; overflow: hidden; }
.warn-pill {
    display:inline-block; background:rgba(239,68,68,0.15); color:#fca5a5;
    border:1px solid rgba(239,68,68,0.4); border-radius:999px; padding:2px 10px;
    font-size:0.75rem; font-weight:600; margin-left:8px;
}
footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

# ----------- MASTER TDS DATA (FY 25-26) -----------
SECTION_DATA = {
    "192": {"desc": "Salary", "rate": "Slab", "limit": "Exemption limit"},
    "192A": {"desc": "Premature EPF withdrawal", "rate": "10%", "limit": "₹50,000"},
    "193": {"desc": "Interest on Securities", "rate": "10%", "limit": "₹10,000"},
    "194": {"desc": "Dividends", "rate": "10%", "limit": "₹10,000"},
    "194A": {"desc": "Interest (Bank/PO)", "rate": "10%", "limit": "₹50k/₹1L Senior"},
    "194B": {"desc": "Lottery/Puzzle winnings", "rate": "30%", "limit": "₹10,000"},
    "194BA": {"desc": "Online gaming winnings", "rate": "30%", "limit": "No threshold"},
    "194BB": {"desc": "Horse race winnings", "rate": "30%", "limit": "₹10,000"},
    "194C": {"desc": "Contractor payment", "rate": "1%/2%", "limit": "₹30k/₹1L FY"},
    "194D": {"desc": "Insurance commission", "rate": "2%/10%", "limit": "₹20,000"},
    "194DA": {"desc": "Life Insurance payout", "rate": "2%", "limit": "₹1 Lakh"},
    "194G": {"desc": "Lottery commission", "rate": "2%", "limit": "₹20,000"},
    "194H": {"desc": "Commission/Brokerage", "rate": "2%", "limit": "₹20,000"},
    "194I(a)": {"desc": "Rent - Plant & Machinery", "rate": "2%", "limit": "₹6L FY"},
    "194I(b)": {"desc": "Rent - Land/Building", "rate": "10%", "limit": "₹6L FY"},
    "194IA": {"desc": "Immovable property sale", "rate": "1%", "limit": "₹50L"},
    "194IB": {"desc": "Rent by Ind/HUF (>50k pm)", "rate": "2%", "limit": "₹50k/month"},
    "194J(a)": {"desc": "Fees for Tech Services", "rate": "2%", "limit": "₹50,000"},
    "194J(b)": {"desc": "Professional Fees/Royalty", "rate": "10%", "limit": "₹50,000"},
    "194M": {"desc": "Contract/Prof fee by Ind/HUF", "rate": "2%", "limit": "₹50L"},
    "194O": {"desc": "E-commerce", "rate": "1%", "limit": "₹5L"},
    "194Q": {"desc": "Purchase of Goods", "rate": "0.1%", "limit": "₹50L"},
    "194R": {"desc": "Business perquisites", "rate": "10%", "limit": "₹20,000"},
    "194S": {"desc": "Virtual Digital Assets", "rate": "1%", "limit": "₹10k/₹50k"},
    "194T": {"desc": "Payment to Partner", "rate": "10%", "limit": "₹20,000"},
}

TAN_RE = re.compile(r"\b([A-Z]{4}\d{5}[A-Z])\b")
PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
CHALLAN_SERIAL_RE = re.compile(r"(?:Challan\s*(?:Serial\s*)?No\.?|CIN\s*No\.?)\s*[:\-]?\s*([A-Z0-9\-/]{6,25})", re.IGNORECASE)


def clean_num(text):
    if not text:
        return 0.0
    s = re.sub(r"[^\d.]", "", str(text))
    try:
        return float(s) if s else 0.0
    except Exception:
        return 0.0


def get_due_date(tds_month_date: datetime) -> datetime:
    """Statutory TDS deposit due date for a given TDS deduction month.
    7th of the following month, except March deductions which are due 30th April."""
    if tds_month_date.month == 3:
        return datetime(tds_month_date.year + 1, 4, 30)
    nxt = tds_month_date + relativedelta(months=1)
    return nxt.replace(day=7)


def calculate_interest(tax, delay_days, monthly_rate_pct=1.5):
    if delay_days <= 0 or tax <= 0:
        return 0.0
    months = math.ceil(delay_days / 30)
    return round(tax * (monthly_rate_pct / 100.0) * months, 2)


def extract_section(block: str) -> str:
    """Try several patterns, in order of reliability, to find the TDS section code."""
    patterns = [
        r"(?:Nature of Payment|Section Code|Section)\s*[:\-]?\s*(194[A-Z]{0,2}(?:\([ab]\))?|192[A]?|19[34])",
        r"\b(194[A-Z]{0,2}(?:\([ab]\))?)\b",
        r"\b(192[A]?)\b",
        r"\b(19[34])\b",
    ]
    for p in patterns:
        m = re.search(p, block, re.IGNORECASE)
        if m:
            raw = re.sub(r"[^0-9A-Za-z()]", "", m.group(1)).upper()
            if raw.startswith("94"):
                raw = "1" + raw
            return raw
    return ""


def extract_date(block: str):
    patterns = [
        r"(?:Date of Deposit|Deposit Date|Tender Date)\s*[:\-]?\s*(\d{2}[-/]\d{2}[-/]\d{4}|\d{2}-[A-Za-z]{3}-\d{2,4})",
        r"(\d{2}[-/][A-Za-z]{3}[-/]\d{2,4})",
        r"(\d{2}[-/]\d{2}[-/]\d{4})",
    ]
    for p in patterns:
        m = re.search(p, block, re.IGNORECASE)
        if m:
            raw = m.group(1).replace("/", "-")
            dt = pd.to_datetime(raw, dayfirst=True, errors="coerce")
            if not pd.isna(dt):
                return dt
    return None


@st.cache_data(show_spinner=False)
def extract_data_from_text(text: str, interest_rate_pct: float):
    rows = []
    blocks = re.split(r"CIN No|Taxpayer Counterfoil|Challan No", text, flags=re.IGNORECASE)

    for block in blocks:
        if len(block) < 100:
            continue

        dep_date = extract_date(block)
        if dep_date is None:
            continue

        raw_sec = extract_section(block) or "194C"
        section_guessed = raw_sec == "194C" and not re.search(r"194C", block, re.IGNORECASE)

        sec_key = raw_sec if raw_sec in SECTION_DATA else (
            re.match(r"194[A-Z]*", raw_sec).group(0) if re.match(r"194[A-Z]*", raw_sec) else None
        )
        sec_info = SECTION_DATA.get(sec_key) or {"desc": "Other", "rate": "As per Act", "limit": "Check Act"}

        tax_match = re.search(r"(?:Income Tax|Tax Amount|Amount of Tax).*?₹?\s*([\d,]+\.?\d*)", block, re.IGNORECASE)
        tax_val = clean_num(tax_match.group(1)) if tax_match else 0.0
        if tax_val == 0:
            nums = [clean_num(x) for x in re.findall(r"₹\s*([\d,]+)", block)]
            tax_val = max(nums) if nums else 0.0

        int_match = re.search(r"Interest\s*₹?\s*([\d,]+\.?\d*)", block, re.IGNORECASE)
        paid_int = clean_num(int_match.group(1)) if int_match else 0.0

        bsr_match = re.search(r"BSR\s*Code.*?(\d+)", block, re.IGNORECASE)
        tan_match = TAN_RE.search(block)
        pan_match = PAN_RE.search(block)
        serial_match = CHALLAN_SERIAL_RE.search(block)

        # TDS deduction month is assumed to be the month prior to the deposit month.
        # This is a heuristic (challans don't always state the deduction period explicitly)
        # and is flagged for review when the resulting delay looks unusually long.
        tds_month = dep_date - relativedelta(months=1)
        due = get_due_date(tds_month)
        delay = (dep_date.date() - due.date()).days
        interest_should = calculate_interest(tax_val, delay, interest_rate_pct)

        needs_review = (tax_val == 0) or section_guessed or (delay > 180)

        rows.append({
            "Deposit Date": dep_date,
            "TDS Month": tds_month.strftime("%b %Y"),
            "TDS Month Date": tds_month,
            "Due Date": due,
            "Delay Days": max(delay, 0),
            "Section Code": raw_sec,
            "Nature": sec_info["desc"],
            "Rate per Act": sec_info["rate"],
            "Threshold": sec_info["limit"],
            "Tax Paid (₹)": tax_val,
            "Interest Paid (₹)": paid_int,
            "Interest As Per Act (₹)": interest_should,
            "Interest Gap (₹)": round(paid_int - interest_should, 2),
            "Status": "On-Time" if delay <= 0 else f"Late {delay}D",
            "BSR": bsr_match.group(1) if bsr_match else "",
            "TAN": tan_match.group(1) if tan_match else "",
            "PAN": pan_match.group(1) if pan_match else "",
            "Challan Serial": serial_match.group(1) if serial_match else "",
            "Needs Review": needs_review,
        })
    return rows


def recompute_derived(df: pd.DataFrame, interest_rate_pct: float) -> pd.DataFrame:
    """Recalculate due date / delay / interest columns after manual edits."""
    df = df.copy()
    df["Deposit Date"] = pd.to_datetime(df["Deposit Date"], errors="coerce", dayfirst=True)
    df["Tax Paid (₹)"] = df["Tax Paid (₹)"].apply(clean_num)
    df["Interest Paid (₹)"] = df["Interest Paid (₹)"].apply(clean_num)

    tds_month = df["Deposit Date"] - pd.DateOffset(months=1)
    df["TDS Month Date"] = tds_month
    df["TDS Month"] = tds_month.dt.strftime("%b %Y")
    df["Due Date"] = tds_month.apply(get_due_date)
    df["Delay Days"] = (df["Deposit Date"].dt.date.apply(lambda d: pd.Timestamp(d)) - df["Due Date"]).dt.days
    df["Delay Days"] = df["Delay Days"].clip(lower=0)
    df["Interest As Per Act (₹)"] = df.apply(
        lambda r: calculate_interest(r["Tax Paid (₹)"], r["Delay Days"], interest_rate_pct), axis=1
    )
    df["Interest Gap (₹)"] = (df["Interest Paid (₹)"] - df["Interest As Per Act (₹)"]).round(2)
    df["Status"] = df["Delay Days"].apply(lambda d: "On-Time" if d <= 0 else f"Late {d}D")
    df["Needs Review"] = df["Tax Paid (₹)"].eq(0)
    return df


def to_excel_pro(df: pd.DataFrame):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_export = df.drop(columns=["TDS Month Date"], errors="ignore").copy()
        df_export["Deposit Date"] = pd.to_datetime(df_export["Deposit Date"]).dt.strftime("%d-%b-%Y")
        df_export["Due Date"] = pd.to_datetime(df_export["Due Date"]).dt.strftime("%d-%b-%Y")

        df_export.to_excel(writer, sheet_name="Audit_Data", index=False)
        workbook = writer.book

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#6366f1", "font_color": "white", "border": 1})
        money_fmt = workbook.add_format({"num_format": "₹ #,##0.00"})

        ws = writer.sheets["Audit_Data"]
        ws.freeze_panes(1, 0)
        for col_num, value in enumerate(df_export.columns.values):
            ws.write(0, col_num, value, header_fmt)
            ws.set_column(col_num, col_num, 18, money_fmt if "₹" in value else None)

        # Dashboard
        dash = workbook.add_worksheet("Dashboard")
        summary = df.groupby("Section Code")["Tax Paid (₹)"].sum().reset_index()
        summary.to_excel(writer, sheet_name="Dashboard", startrow=3, startcol=0, index=False)

        chart = workbook.add_chart({"type": "doughnut"})
        chart.add_series({
            "name": "Tax by Section",
            "categories": ["Dashboard", 4, 0, len(summary) + 3, 0],
            "values": ["Dashboard", 4, 1, len(summary) + 3, 1],
        })
        chart.set_title({"name": "Tax Distribution"})
        dash.insert_chart("D2", chart)

        monthly = df.groupby("TDS Month")["Interest Gap (₹)"].sum().reset_index()
        start_row = len(summary) + 6
        monthly.to_excel(writer, sheet_name="Dashboard", startrow=start_row, startcol=0, index=False)
        gap_chart = workbook.add_chart({"type": "column"})
        gap_chart.add_series({
            "name": "Interest Shortfall by Month",
            "categories": ["Dashboard", start_row + 1, 0, start_row + len(monthly), 0],
            "values": ["Dashboard", start_row + 1, 1, start_row + len(monthly), 1],
        })
        gap_chart.set_title({"name": "Interest Shortfall Trend"})
        dash.insert_chart("D20", gap_chart)

        # Compliance
        comp = workbook.add_worksheet("Compliance")
        comp.write("A1", f"TDS Compliance Report - Generated {datetime.now():%d-%b-%Y}",
                    workbook.add_format({"bold": True, "font_size": 14}))
        late = df[df["Delay Days"] > 0]
        review = df[df.get("Needs Review", False) == True]
        comp.write("A3", f"Total Late Challans: {len(late)} / {len(df)}")
        comp.write("A4", f"Total Interest Shortfall: ₹ {df['Interest Gap (₹)'].sum():,.2f}")
        comp.write("A5", f"Rows Flagged for Review: {len(review)}")

    return output.getvalue()


# ---------------- SESSION STATE ----------------
if "df" not in st.session_state:
    st.session_state.df = None
if "file_status" not in st.session_state:
    st.session_state.file_status = []

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.markdown("### ⚖️ TDS Auditor Pro")
    st.caption("Abhishek Jakkula | FY 25-26 Ready")
    st.divider()
    interest_rate = st.number_input(
        "Interest rate (% per month, u/s 201(1A))", min_value=0.5, max_value=5.0,
        value=1.5, step=0.5,
        help="Statutory default is 1.5% per month (or part thereof) for late deposit."
    )
    st.info("💡 Tip: Upload all challan PDFs at once. Supports 50+ files. Auto-detects 192, 194A to 194T.")
    st.caption("⚠️ The TDS deduction month is inferred as one month before the deposit date, "
               "since challans don't always print the deduction period. Rows with an unusually "
               "long delay are flagged for manual review.")

st.markdown('<div class="glass-card">', unsafe_allow_html=True)
st.markdown('<div class="main-header">TDS AI AUDITOR PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-brand">Developed by Abhishek Jakkula • Statutory Compliance Engine</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("📂 DROP YOUR CHALLAN PDFs HERE", type="pdf", accept_multiple_files=True, label_visibility="collapsed")

if uploaded:
    with st.spinner("🔍 Parsing challans with AI engine..."):
        all_rows = []
        file_status = []
        for f in uploaded:
            try:
                with pdfplumber.open(f) as pdf:
                    text = "\n".join([p.extract_text() or "" for p in pdf.pages])
                extracted = extract_data_from_text(text, interest_rate)
                all_rows.extend(extracted)
                file_status.append({"File": f.name, "Rows Found": len(extracted), "Status": "✅ OK" if extracted else "⚠️ No data found"})
            except Exception as e:
                file_status.append({"File": f.name, "Rows Found": 0, "Status": f"❌ Error: {e}"})

    st.session_state.file_status = file_status

    if not all_rows:
        st.error("No challan data found. Try clearer scanned PDFs.")
        with st.expander("📋 Per-file parse status"):
            st.dataframe(pd.DataFrame(file_status), use_container_width=True)
        st.stop()

    st.session_state.df = pd.DataFrame(all_rows).sort_values("Deposit Date").reset_index(drop=True)

df = st.session_state.df

if df is not None:
    with st.expander("📋 Per-file parse status", expanded=False):
        st.dataframe(pd.DataFrame(st.session_state.file_status), use_container_width=True)

    # ---- Filters ----
    with st.sidebar:
        st.divider()
        st.markdown("#### 🔎 Filters")
        min_d, max_d = df["Deposit Date"].min(), df["Deposit Date"].max()
        date_range = st.date_input("Deposit date range", value=(min_d.date(), max_d.date()))
        sections = st.multiselect("Section Code", sorted(df["Section Code"].unique()))
        status_filter = st.multiselect("Status", ["On-Time", "Late"])

    fdf = df.copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        fdf = fdf[(fdf["Deposit Date"].dt.date >= date_range[0]) & (fdf["Deposit Date"].dt.date <= date_range[1])]
    if sections:
        fdf = fdf[fdf["Section Code"].isin(sections)]
    if status_filter:
        mask = pd.Series(False, index=fdf.index)
        if "On-Time" in status_filter:
            mask |= fdf["Delay Days"] <= 0
        if "Late" in status_filter:
            mask |= fdf["Delay Days"] > 0
        fdf = fdf[mask]

    # Metrics
    m1, m2, m3, m4, m5 = st.columns(5)
    with m1: st.metric("Total Tax Paid", f"₹{fdf['Tax Paid (₹)'].sum():,.0f}")
    with m2: st.metric("Interest Paid", f"₹{fdf['Interest Paid (₹)'].sum():,.0f}")
    with m3: st.metric("Interest Gap", f"₹{fdf['Interest Gap (₹)'].sum():,.0f}", delta_color="inverse")
    with m4: st.metric("Late Challans", f"{len(fdf[fdf['Delay Days']>0])} / {len(fdf)}")
    with m5: st.metric("Flagged for Review", int(fdf["Needs Review"].sum()) if "Needs Review" in fdf else 0)

    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Dashboard", "📑 Detailed Table", "✏️ Edit & Fix", "🚨 Compliance", "🔍 Needs Review"])

    with tab1:
        c1, c2 = st.columns([1, 1])
        with c1:
            fig1 = px.pie(fdf, names="Section Code", values="Tax Paid (₹)", hole=0.55, title="Tax by Section")
            fig1.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig1, use_container_width=True)
        with c2:
            fig2 = px.bar(fdf, x="TDS Month", y="Tax Paid (₹)", color="Section Code", title="Monthly TDS Trend")
            fig2.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig2, use_container_width=True)

        c3, c4 = st.columns([1, 1])
        with c3:
            total = len(fdf)
            ontime = len(fdf[fdf["Delay Days"] <= 0])
            pct = (ontime / total * 100) if total else 0
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=pct,
                title={"text": "On-Time Compliance %"},
                gauge={"axis": {"range": [0, 100]}, "bar": {"color": "#8b5cf6"}}
            ))
            gauge.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(gauge, use_container_width=True)
        with c4:
            monthly_gap = fdf.groupby("TDS Month Date")["Interest Gap (₹)"].sum().reset_index().sort_values("TDS Month Date")
            monthly_gap["TDS Month"] = monthly_gap["TDS Month Date"].dt.strftime("%b %Y")
            fig3 = px.bar(monthly_gap, x="TDS Month", y="Interest Gap (₹)", title="Interest Shortfall by Month")
            fig3.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig3, use_container_width=True)

    with tab2:
        display_cols = [c for c in fdf.columns if c not in ("TDS Month Date",)]
        st.dataframe(
            fdf[display_cols].style.background_gradient(subset=["Interest Gap (₹)"], cmap="RdYlGn_r")
            .format({"Tax Paid (₹)": "₹{:,.2f}"}),
            use_container_width=True, height=500
        )
        colA, colB = st.columns(2)
        with colA:
            st.download_button("🚀 DOWNLOAD PRO EXCEL REPORT", data=to_excel_pro(fdf),
                                file_name=f"TDS_Audit_PRO_{datetime.now():%Y%m%d}.xlsx",
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with colB:
            csv_bytes = fdf.drop(columns=["TDS Month Date"], errors="ignore").to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ DOWNLOAD CSV", data=csv_bytes,
                                file_name=f"TDS_Audit_{datetime.now():%Y%m%d}.csv", mime="text/csv")

    with tab3:
        st.caption("Fix any misread Section Code, Deposit Date, or Tax Paid amount below, then recalculate.")
        editable_cols = ["Deposit Date", "Section Code", "Tax Paid (₹)", "Interest Paid (₹)", "BSR", "TAN", "PAN"]
        edited = st.data_editor(
            df[editable_cols], num_rows="dynamic", use_container_width=True, key="editor"
        )
        if st.button("🔄 Recalculate Due Dates & Interest"):
            merged = df.copy()
            merged.update(edited)
            merged = recompute_derived(merged, interest_rate)
            st.session_state.df = merged
            st.success("Recalculated. Switch to Dashboard / Detailed Table to see updated results.")
            st.rerun()

    with tab4:
        late_df = fdf[fdf["Delay Days"] > 0].sort_values("Delay Days", ascending=False)
        if late_df.empty:
            st.success("✅ No late deposits in current filter. 100% Compliant!")
        else:
            st.error(f"Found {len(late_df)} late deposits - Interest u/s 201(1A) @{interest_rate}% p.m. applicable")
            st.dataframe(
                late_df[["Deposit Date", "Due Date", "Delay Days", "Section Code", "Tax Paid (₹)",
                         "Interest As Per Act (₹)", "Interest Paid (₹)", "Interest Gap (₹)"]],
                use_container_width=True
            )

    with tab5:
        review_df = fdf[fdf["Needs Review"] == True] if "Needs Review" in fdf else pd.DataFrame()
        if review_df.empty:
            st.success("✅ No rows flagged for review.")
        else:
            st.warning(f"{len(review_df)} rows have low-confidence extraction (₹0 tax, guessed section, or "
                       f"unusually long delay). Fix these in the Edit & Fix tab.")
            st.dataframe(
                review_df[["Deposit Date", "Section Code", "Tax Paid (₹)", "Delay Days", "Status"]],
                use_container_width=True
            )

else:
    st.markdown('<div class="glass-card" style="text-align:center; margin-top:20px;">Upload PDFs to start audit. Pro engine reads BSR, CIN, TAN, PAN, Section, Interest automatically.</div>', unsafe_allow_html=True)

st.markdown("""
<div style="text-align:center; margin-top:40px; padding:18px; background:rgba(255,255,255,0.06); border-radius:999px; border:1px solid rgba(255,255,255,0.1); color:rgba(255,255,255,0.6)">
Built by <b style="color:white">Abhishek Jakkula</b> • <a href="mailto:jakkulaabhishek5@gmail.com" style="color:#a5b4fc; text-decoration:none">jakkulaabhishek5@gmail.com</a>
</div>
""", unsafe_allow_html=True)
