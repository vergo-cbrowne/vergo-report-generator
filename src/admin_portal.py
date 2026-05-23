import base64
import hmac
import os
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

import drive_scanner
try:
    from completion_tracker import render_client_completion_tracker_page
except Exception:
    render_client_completion_tracker_page = None


DEFAULT_ROOT_FOLDER_ID = "1zRTHGXHKpNDB2yqubgfXKqd2r6qO-92_"
DEFAULT_CREDENTIALS_PATH = "credentials/service-account.json"
DEFAULT_PROMPT_PATH = "prompts/vergo_master_report_prompt.md"
DEFAULT_MODEL = "gpt-4.1"

SCAN_CSV = "output/drive_scan.csv"
BATCH_SUMMARY_CSV = "output/portal_batch_summary.csv"
LOGO_PATH = "assets/vergo-logo-white-transparent.png"


st.set_page_config(page_title="Vergo Report Admin", page_icon="✅", layout="wide")


def image_to_base64(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return base64.b64encode(file_path.read_bytes()).decode("utf-8")


def load_local_env_file():
    env_path = Path(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def apply_vergo_theme():
    if "vergo_dark_mode" not in st.session_state:
        st.session_state.vergo_dark_mode = True

    dark_mode = st.sidebar.toggle("Dark mode", value=st.session_state.vergo_dark_mode)
    st.session_state.vergo_dark_mode = dark_mode

    light = not dark_mode
    bg = "#f6f7f2" if light else "#02060a"
    sidebar = "#ffffff" if light else "#050a11"
    panel = "#ffffff" if light else "#0b111b"
    panel2 = "#f1f2ee" if light else "#101827"
    text = "#101010" if light else "#f6f7f4"
    muted = "rgba(0,0,0,0.62)" if light else "rgba(255,255,255,0.66)"
    border = "rgba(0,0,0,0.14)" if light else "rgba(255,255,255,0.14)"
    input_bg = "#ffffff" if light else "#111827"

    st.markdown(
        f"""
        <style>
        @import url("https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap");

        :root {{
            --bg: {bg};
            --sidebar: {sidebar};
            --panel: {panel};
            --panel2: {panel2};
            --text: {text};
            --muted: {muted};
            --border: {border};
            --input: {input_bg};
            --green: #58d34f;
            --red: #ff4b4b;
            --blue: #6fb2ff;
            --orange: #f59e2f;
        }}

        header[data-testid="stHeader"], div[data-testid="stToolbar"], div[data-testid="stDecoration"] {{
            display: none !important;
        }}

        html, body, .stApp {{
            background: var(--bg) !important;
            color: var(--text) !important;
            font-family: "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif !important;
        }}

        [data-testid="stAppViewContainer"], [data-testid="stMain"] {{
            background:
                radial-gradient(circle at 78% 4%, rgba(47, 150, 94, 0.24), transparent 28%),
                radial-gradient(circle at 15% 12%, rgba(72, 130, 180, 0.14), transparent 22%),
                var(--bg) !important;
            color: var(--text) !important;
        }}

        .block-container {{
            max-width: 1320px !important;
            padding-top: 2rem !important;
            padding-bottom: 4rem !important;
        }}

        section[data-testid="stSidebar"] {{
            background: linear-gradient(180deg, var(--sidebar), #03070c) !important;
            border-right: 1px solid var(--border) !important;
        }}

        section[data-testid="stSidebar"] * {{ color: var(--text) !important; }}
        section[data-testid="stSidebar"] > div {{ padding-top: 1.6rem !important; }}

        .sidebar-welcome {{
            margin: 1.25rem 0 1.35rem 0;
            padding-bottom: 1.2rem;
            border-bottom: 1px solid var(--border);
        }}
        .eyebrow, .sidebar-eyebrow {{
            color: var(--muted);
            font-size: 0.74rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
        }}
        .sidebar-name {{
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 1.6rem;
            font-weight: 360;
            letter-spacing: -0.04em;
            margin-top: 0.45rem;
        }}
        .sidebar-divider {{ height: 1px; background: var(--border); margin: 1.35rem 0; }}

        .top-logo {{ width: 150px; margin-bottom: 1rem; }}
        .top-rule {{ height: 1px; background: var(--border); margin: 1rem 0 2.4rem 0; }}

        .hero {{
            padding-bottom: 2rem;
            margin-bottom: 1.8rem;
            border-bottom: 1px solid var(--border);
            background: transparent !important;
            border-radius: 0 !important;
        }}
        .hero-title {{
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: clamp(3rem, 5.1vw, 5rem);
            line-height: 1.02;
            font-weight: 300;
            letter-spacing: -0.065em;
            margin: 1.2rem 0 1.2rem 0;
            color: var(--text);
        }}
        .hero-subtitle {{
            max-width: 780px;
            color: var(--muted);
            font-size: 1.03rem;
            line-height: 1.55;
        }}

        h1, h2, h3 {{ color: var(--text) !important; }}
        h2 {{ font-size: 1.35rem !important; }}
        h3 {{ font-size: 1.05rem !important; }}

        .stTabs [data-baseweb="tab-list"] {{ border-bottom: 1px solid var(--border); gap: 1.6rem; }}
        .stTabs [data-baseweb="tab"] {{
            color: var(--muted) !important;
            font-size: 0.94rem !important;
            font-weight: 600 !important;
            padding-left: 0 !important;
            padding-right: 0 !important;
        }}
        .stTabs [aria-selected="true"] {{ color: var(--text) !important; border-bottom: 4px solid var(--green) !important; }}

        input, textarea, select, div[data-baseweb="input"], div[data-baseweb="select"] > div {{
            background: var(--input) !important;
            color: var(--text) !important;
            border-color: var(--border) !important;
            border-radius: 12px !important;
        }}
        div[data-baseweb="input"] input, div[data-baseweb="select"] * {{ color: var(--text) !important; }}

        .metric-grid {{
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 1rem;
            margin: 1.45rem 0 1.75rem 0;
        }}
        .metric-card {{
            background: linear-gradient(145deg, var(--panel), var(--panel2));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.25rem;
            min-height: 118px;
            display: flex;
            align-items: center;
            gap: 1rem;
        }}
        .metric-icon {{
            width: 48px; height: 48px; border-radius: 999px;
            display:flex; align-items:center; justify-content:center;
            font-size: 1.35rem; flex: 0 0 auto;
        }}
        .icon-blue {{ color: var(--blue); background: rgba(111,178,255,0.15); border: 1px solid rgba(111,178,255,0.42); }}
        .icon-green {{ color: var(--green); background: rgba(88,211,79,0.15); border: 1px solid rgba(88,211,79,0.42); }}
        .icon-orange {{ color: var(--orange); background: rgba(245,158,47,0.16); border: 1px solid rgba(245,158,47,0.42); }}
        .icon-red {{ color: #ff6b6b; background: rgba(255,75,75,0.14); border: 1px solid rgba(255,75,75,0.42); }}
        .metric-label {{ color: var(--muted); font-size: 0.74rem; font-weight: 700; letter-spacing: 0.12em; text-transform: uppercase; }}
        .metric-value {{ font-size: 2.25rem; line-height: 1; font-weight: 600; color: var(--text); margin-top: 0.4rem; }}
        .metric-green {{ color: var(--green); }}
        .metric-red {{ color: #ff6b6b; }}

        .summary-card, .action-bar, .table-shell {{
            background: linear-gradient(145deg, var(--panel), var(--panel2));
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.25rem;
            margin: 1.25rem 0;
        }}
        .summary-title {{ font-size: 1.1rem; font-weight: 700; margin-bottom: 0.7rem; border-left: 4px solid var(--green); padding-left: 0.75rem; }}
        .summary-copy, .muted, .action-copy {{ color: var(--muted); line-height: 1.55; }}
        .summary-dot {{ color: var(--green); margin: 0 0.45rem; }}

        .link-table {{ width: 100%; border-collapse: collapse; font-size: 0.88rem; }}
        .link-table th {{ text-align: left; color: var(--muted); font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.11em; padding: 0.75rem; border-bottom: 1px solid var(--border); }}
        .link-table td {{ padding: 0.75rem; border-bottom: 1px solid var(--border); color: var(--text); }}
        .link-table a {{ color: var(--green) !important; font-weight: 700; text-decoration: none; }}

        .status-chip {{ display: inline-flex; align-items: center; gap: 0.35rem; border-radius: 999px; padding: 0.25rem 0.55rem; font-size: 0.78rem; font-weight: 700; }}
        .chip-ready {{ color: var(--green); background: rgba(88, 211, 79, 0.12); }}
        .chip-completed {{ color: var(--blue); background: rgba(77, 151, 255, 0.12); }}
        .chip-review {{ color: var(--orange); background: rgba(245, 158, 47, 0.12); }}
        .chip-failed {{ color: #ff6b6b; background: rgba(255, 75, 75, 0.12); }}

        .stButton > button {{
            border-radius: 12px !important;
            min-height: 44px !important;
            font-weight: 700 !important;
            border: 1px solid var(--border) !important;
            background: #ffffff !important;
            color: #050505 !important;
        }}
        .stButton > button * {{ color: inherit !important; }}
        section[data-testid="stSidebar"] .stButton:nth-of-type(1) button {{
            background: linear-gradient(135deg, #1c7a34, #2d9c46) !important;
            color: #ffffff !important;
            border: 1px solid rgba(88, 211, 79, 0.55) !important;
        }}
        section[data-testid="stSidebar"] .stButton:nth-of-type(2) button {{
            background: #12213a !important;
            color: #ffffff !important;
            border: 1px solid rgba(111, 178, 255, 0.35) !important;
        }}
        section[data-testid="stSidebar"] .stButton:last-of-type button {{
            background: transparent !important;
            color: var(--red) !important;
            border: 1px solid var(--red) !important;
        }}

        div[data-testid="stDataFrame"], div[data-testid="stDataEditor"] {{ border-radius: 18px; border: 1px solid var(--border); overflow: hidden; }}

        @media (max-width: 1100px) {{ .metric-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }} }}
        @media print {{
            section[data-testid="stSidebar"], header, footer, .stButton, .stDownloadButton, div[role="tablist"] {{ display: none !important; }}
            [data-testid="stAppViewContainer"], [data-testid="stMain"], .main, section, .block-container {{ background: #ffffff !important; color: #000000 !important; max-width: 100% !important; padding: 0.45in !important; }}
            * {{ color: #000000 !important; box-shadow: none !important; text-shadow: none !important; }}
            .metric-card, .summary-card, .action-bar, .table-shell {{ border: 1px solid #bbbbbb !important; background: #ffffff !important; }}
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def require_admin_login():
    admin_user = os.environ.get("VERGO_ADMIN_USER", "")
    admin_password = os.environ.get("VERGO_ADMIN_PASSWORD", "")
    if not admin_user or not admin_password:
        st.error("Admin login is not configured. Set VERGO_ADMIN_USER and VERGO_ADMIN_PASSWORD in .env.")
        st.stop()
    if st.session_state.get("vergo_admin_authenticated") is True:
        return

    logo_b64 = image_to_base64(LOGO_PATH)
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="top-logo" />' if logo_b64 else ""
    st.markdown(
        f"""
        {logo_html}
        <div class="eyebrow">Secure Access</div>
        <div class="top-rule"></div>
        <div class="hero">
            <div class="eyebrow">Vergo Operations</div>
            <div class="hero-title">Vergo Admin Login</div>
            <div class="hero-subtitle">Sign in to access the report operations dashboard.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("vergo_admin_login_form"):
        st.markdown("### Sign in")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Sign in", use_container_width=True)
    if submitted:
        user_ok = hmac.compare_digest(username.strip().lower(), admin_user.strip().lower())
        password_ok = hmac.compare_digest(password, admin_password)
        if user_ok and password_ok:
            st.session_state["vergo_admin_authenticated"] = True
            st.rerun()
        st.error("Invalid username or password.")
    st.stop()


def render_sidebar_controls():
    st.sidebar.markdown(
        """
        <div class="sidebar-welcome">
            <div class="sidebar-eyebrow">Welcome back</div>
            <div class="sidebar-name">Vergo Admin</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scan_clicked = st.sidebar.button("△  Scan Google Drive", use_container_width=True)
    load_existing_clicked = st.sidebar.button("▣  Load existing scan CSV", use_container_width=True)
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)
    st.sidebar.header("Configuration")

    credentials_path = st.sidebar.text_input("Credentials path", DEFAULT_CREDENTIALS_PATH)
    root_folder_id = st.sidebar.text_input("Processed videos root folder ID", DEFAULT_ROOT_FOLDER_ID)
    prompt_path = st.sidebar.text_input("Prompt path", DEFAULT_PROMPT_PATH)
    model = st.sidebar.text_input("OpenAI model", DEFAULT_MODEL)
    full_scan = st.sidebar.checkbox("Full Drive scan", value=False, help="Leave off for faster testing. Turn on when you want to scan everything.")
    assessment_date_required = st.sidebar.checkbox("Require assessment date", value=False, help="If off, missing assessment dates are not treated as a review warning.")
    st.sidebar.markdown('<div class="sidebar-divider"></div>', unsafe_allow_html=True)

    if st.sidebar.button("⏻  Log Out", use_container_width=True):
        st.session_state["vergo_admin_authenticated"] = False
        st.rerun()

    return credentials_path, root_folder_id, prompt_path, model, full_scan, assessment_date_required, scan_clicked, load_existing_clicked


def render_page_header():
    logo_b64 = image_to_base64(LOGO_PATH)
    logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="top-logo" />' if logo_b64 else ""
    st.markdown(
        f"""
        {logo_html}
        <div class="eyebrow">Report Operations</div>
        <div class="top-rule"></div>
        <div class="hero">
            <div class="eyebrow" style="color: var(--green);">Vergo Operations</div>
            <div class="hero-title">Report Admin Portal</div>
            <div class="hero-subtitle">
                Scan Google Drive, review processed assessment folders, generate Vergo movement analysis reports,
                and monitor batch results from one operations dashboard.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def load_scan_csv(path: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        return pd.DataFrame()
    return pd.read_csv(csv_path).fillna("")


def run_drive_scan(credentials_path: str, root_folder_id: str, full_scan: bool) -> pd.DataFrame:
    max_companies = None if full_scan else 5
    max_accounts = None if full_scan else 3
    max_assessments = None if full_scan else 10
    rows = drive_scanner.scan_drive(credentials_path=credentials_path, root_folder_id=root_folder_id, max_companies=max_companies, max_accounts_per_company=max_accounts, max_assessments_per_account=max_assessments)
    drive_scanner.write_csv(rows, SCAN_CSV)
    return load_scan_csv(SCAN_CSV)


def run_batch(folder_ids: list[str], credentials_path: str, prompt_path: str, model: str, root_folder_id: str):
    selected_file = Path("output/portal_selected_folders.txt")
    selected_file.parent.mkdir(parents=True, exist_ok=True)
    selected_file.write_text("\n".join(folder_ids) + "\n", encoding="utf-8")
    command = [sys.executable, "src/batch_generate.py", "--folders-file", str(selected_file), "--credentials-path", credentials_path, "--prompt-path", prompt_path, "--model", model, "--summary-csv", BATCH_SUMMARY_CSV, "--root-folder-id", root_folder_id]
    result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    output = result.stdout or ""
    summary = pd.DataFrame()
    if Path(BATCH_SUMMARY_CSV).exists():
        summary = pd.read_csv(BATCH_SUMMARY_CSV).fillna("")
    return result.returncode, output, summary


def make_link(url: str, label: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return '<span class="muted">—</span>'
    return f'<a href="{url}" target="_blank">{label}</a>'


def build_status_badge(row) -> str:
    has_pdf = str(row.get("has_pdf", "")).lower() == "true"
    status = str(row.get("status", "")).strip().lower()
    has_json = str(row.get("has_report_json", "")).lower() == "true"
    has_snapshots = str(row.get("has_snapshots", "")).lower() == "true"
    if not has_json or not has_snapshots:
        return "Failed"
    if has_pdf and status == "completed":
        return "Completed"
    if has_pdf and status != "completed":
        return "Needs Review"
    return "Ready"


def chip_html(status: str) -> str:
    css = {"Ready": "chip-ready", "Completed": "chip-completed", "Needs Review": "chip-review", "Failed": "chip-failed"}.get(status or "Ready", "chip-ready")
    return f'<span class="status-chip {css}">● {status or "Ready"}</span>'


def clean_batch_summary(summary_df: pd.DataFrame, assessment_date_required: bool) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df
    df = summary_df.copy()
    if not assessment_date_required and "weak_metadata" in df.columns:
        df["weak_metadata"] = df["weak_metadata"].astype(str).str.replace("assessment_date", "", regex=False).str.replace(";;", ";", regex=False).str.strip(";")
    return df


def format_bool(value) -> str:
    return "Yes" if str(value).lower() == "true" else "No"


def format_date(value) -> str:
    text = str(value or "")
    return text.split("T", 1)[0] if "T" in text else text or "—"


def render_metric_cards(total: int, ready: int, completed: int, missing: int):
    st.markdown(
        f"""
        <div class="metric-grid">
            <div class="metric-card"><div class="metric-icon icon-blue">□</div><div><div class="metric-label">Visible Folders</div><div class="metric-value">{total}</div></div></div>
            <div class="metric-card"><div class="metric-icon icon-green">✓</div><div><div class="metric-label">Ready to Generate</div><div class="metric-value metric-green">{ready}</div></div></div>
            <div class="metric-card"><div class="metric-icon icon-orange">▤</div><div><div class="metric-label">Completed Reports</div><div class="metric-value">{completed}</div></div></div>
            <div class="metric-card"><div class="metric-icon icon-red">!</div><div><div class="metric-label">Missing PDFs</div><div class="metric-value metric-red">{missing}</div></div></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def main():
    load_local_env_file()
    apply_vergo_theme()
    require_admin_login()
    credentials_path, root_folder_id, prompt_path, model, full_scan, assessment_date_required, scan_clicked, load_existing_clicked = render_sidebar_controls()
    render_page_header()

    if not Path(credentials_path).exists():
        st.error(f"Credentials file not found: {credentials_path}")
        st.stop()

    tab_names = ["Report Generation"]
    if render_client_completion_tracker_page is not None:
        tab_names.append("Client Completion Tracker")
    tabs = st.tabs(tab_names)

    with tabs[0]:
        if scan_clicked:
            with st.spinner("Scanning Google Drive folders..."):
                try:
                    st.session_state["scan_df"] = run_drive_scan(credentials_path=credentials_path, root_folder_id=root_folder_id, full_scan=full_scan)
                    st.success("Drive scan complete.")
                except Exception as exc:
                    st.error(f"Drive scan failed: {exc}")
                    st.stop()
        elif load_existing_clicked:
            st.session_state["scan_df"] = load_scan_csv(SCAN_CSV)

        scan_df = st.session_state.get("scan_df", load_scan_csv(SCAN_CSV))
        if scan_df.empty:
            st.info("Click **Scan Google Drive** to load assessment folders.")
            return

        st.subheader("Assessment folder scan")
        valid_df = scan_df[scan_df["is_valid_assessment"].astype(str) == "True"].copy()
        if valid_df.empty:
            st.warning("No valid assessment folders found.")
            st.dataframe(scan_df, use_container_width=True)
            return

        valid_df["status_badge"] = valid_df.apply(build_status_badge, axis=1)
        valid_df["Folder Link"] = valid_df.apply(lambda row: make_link(row.get("folder_link", ""), "Open Folder"), axis=1)
        valid_df["PDF Link"] = valid_df.apply(lambda row: make_link(row.get("pdf_link", ""), "Open PDF"), axis=1)

        col1, col2, col3, col4 = st.columns(4)
        with col1:
            companies = ["All"] + sorted(valid_df["company"].dropna().unique().tolist())
            company_filter = st.selectbox("Company", companies)
        with col2:
            account_source = valid_df[valid_df["company"] == company_filter] if company_filter != "All" else valid_df
            accounts = ["All"] + sorted(account_source["account"].dropna().unique().tolist())
            account_filter = st.selectbox("Account/User", accounts)
        with col3:
            status_options = ["All", "Ready", "Completed", "Needs Review", "Missing PDF"]
            status_filter = st.selectbox("Status filter", status_options)
        with col4:
            search = st.text_input("Search assessment name", "")

        filtered = valid_df.copy()
        if company_filter != "All":
            filtered = filtered[filtered["company"] == company_filter]
        if account_filter != "All":
            filtered = filtered[filtered["account"] == account_filter]
        if status_filter == "Ready":
            filtered = filtered[filtered["status_badge"] == "Ready"]
        elif status_filter == "Completed":
            filtered = filtered[filtered["status_badge"] == "Completed"]
        elif status_filter == "Needs Review":
            filtered = filtered[filtered["status_badge"] == "Needs Review"]
        elif status_filter == "Missing PDF":
            filtered = filtered[filtered["has_pdf"].astype(str) != "True"]
        if search.strip():
            filtered = filtered[filtered["assessment_folder"].str.contains(search.strip(), case=False, na=False)]

        completed_count = len(filtered[filtered["status_badge"] == "Completed"])
        ready_count = len(filtered[filtered["status_badge"] == "Ready"])
        missing_pdf_count = len(filtered[filtered["has_pdf"].astype(str) != "True"])
        render_metric_cards(len(filtered), ready_count, completed_count, missing_pdf_count)

        last_modified = "—"
        if len(filtered) > 0 and "modified_time" in filtered.columns:
            last_modified = format_date(filtered["modified_time"].max())
        st.markdown(
            f"""
            <div class="summary-card">
                <div class="summary-title">Last scan summary</div>
                <div class="summary-copy">Showing {len(filtered)} folders <span class="summary-dot">•</span>{ready_count} ready to generate <span class="summary-dot">•</span>{completed_count} completed <span class="summary-dot">•</span>{missing_pdf_count} missing PDFs <span class="summary-dot">•</span>Latest modified: {last_modified}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        missing_pdf_rows = filtered[filtered["has_pdf"].astype(str) != "True"]
        missing_pdf_folder_ids = missing_pdf_rows["folder_id"].tolist()
        top_action_left, top_action_right = st.columns([1, 2])
        with top_action_left:
            generate_missing_top_clicked = st.button("Generate all visible missing PDFs", key="generate_missing_top", disabled=len(missing_pdf_folder_ids) == 0, use_container_width=True)
        with top_action_right:
            st.caption("Use filters first, then generate every visible folder that does not already have a PDF.")

        table_rows = []
        for _, row in filtered.iterrows():
            table_rows.append({"Company": row.get("company", ""), "Account": row.get("account", ""), "Assessment Folder": row.get("assessment_folder", ""), "Status": chip_html(row.get("status_badge", "")), "PDF": format_bool(row.get("has_pdf", "")), "Drive Folder": row.get("Folder Link", ""), "Report PDF": row.get("PDF Link", ""), "Last Modified": format_date(row.get("modified_time", ""))})
        preview_df = pd.DataFrame(table_rows)
        st.markdown(f'<div class="table-shell">{preview_df.to_html(escape=False, index=False, classes="link-table")}</div>', unsafe_allow_html=True)

        st.markdown('<div class="action-bar"><strong>Report generation</strong><br><span class="action-copy">Select specific folders below, or generate all visible folders that are missing PDFs.</span></div>', unsafe_allow_html=True)

        select_columns = ["company", "account", "assessment_folder", "status_badge", "has_pdf", "status", "modified_time", "folder_id"]
        filtered_display = filtered[select_columns].copy().rename(columns={"company": "Company", "account": "Account", "assessment_folder": "Assessment Folder", "status_badge": "Status", "has_pdf": "Has PDF", "status": "Drive Status", "modified_time": "Last Modified", "folder_id": "Folder ID"})
        filtered_display.insert(0, "Select", False)
        edited = st.data_editor(filtered_display, use_container_width=True, hide_index=True, height=560, column_config={"Select": st.column_config.CheckboxColumn("Select"), "Folder ID": st.column_config.TextColumn("Folder ID", disabled=True)}, disabled=[col for col in filtered_display.columns if col != "Select"])
        selected_rows = edited[edited["Select"] == True]
        selected_folder_ids = selected_rows["Folder ID"].tolist()
        st.write(f"Selected **{len(selected_folder_ids)}** folders.")
        st.write(f"Visible missing-PDF folders: **{len(missing_pdf_folder_ids)}**")

        left, middle, right = st.columns([1, 1, 2])
        with left:
            generate_clicked = st.button("Generate selected reports", type="primary", disabled=len(selected_folder_ids) == 0, use_container_width=True)
        with middle:
            generate_missing_clicked = st.button("Generate all visible missing PDFs", disabled=len(missing_pdf_folder_ids) == 0, use_container_width=True)
        with right:
            if len(selected_folder_ids) > 0:
                st.caption("Selected folders")
                st.write(", ".join(selected_rows["Assessment Folder"].tolist()))

        folders_to_run = []
        run_label = ""
        if generate_clicked:
            folders_to_run = selected_folder_ids
            run_label = "selected reports"
        if generate_missing_clicked or generate_missing_top_clicked:
            folders_to_run = missing_pdf_folder_ids
            run_label = "visible missing PDFs"
        if folders_to_run:
            with st.spinner(f"Generating {len(folders_to_run)} {run_label}..."):
                returncode, output, summary_df = run_batch(folders_to_run, credentials_path, prompt_path, model, root_folder_id)
            summary_df = clean_batch_summary(summary_df, assessment_date_required)
            if returncode == 0:
                st.success("Batch generation completed.")
            else:
                st.error("Batch generation completed with one or more failures.")
            if not summary_df.empty:
                st.subheader("Batch summary")
                st.dataframe(summary_df, use_container_width=True)
                weak = summary_df[(summary_df["success"].astype(str) != "True") | (summary_df["weak_metadata"].astype(str).str.len() > 0)]
                if not weak.empty:
                    st.warning("Some rows need review.")
                    st.dataframe(weak, use_container_width=True)
                else:
                    st.success("No failed rows or weak metadata found.")
            with st.expander("Raw run log"):
                st.code(output)

    if len(tabs) > 1 and render_client_completion_tracker_page is not None:
        with tabs[1]:
            render_client_completion_tracker_page(credentials_path=credentials_path, root_folder_id=root_folder_id)


if __name__ == "__main__":
    main()
