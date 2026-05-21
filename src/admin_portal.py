import csv
import subprocess
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

import drive_scanner


DEFAULT_ROOT_FOLDER_ID = "1zRTHGXHKpNDB2yqubgfXKqd2r6qO-92_"
DEFAULT_CREDENTIALS_PATH = "credentials/service-account.json"
DEFAULT_PROMPT_PATH = "prompts/vergo_master_report_prompt.md"
DEFAULT_MODEL = "gpt-4.1"
SCAN_CSV = "output/drive_scan.csv"
BATCH_SUMMARY_CSV = "output/portal_batch_summary.csv"


st.set_page_config(
    page_title="Vergo Report Admin",
    page_icon="✅",
    layout="wide",
)

st.title("Vergo Report Admin Portal")
st.caption("Scan Google Drive, select assessment folders, and generate Vergo PDF reports.")


def load_scan_csv(path: str) -> pd.DataFrame:
    csv_path = Path(path)

    if not csv_path.exists():
        return pd.DataFrame()

    return pd.read_csv(csv_path).fillna("")


def run_drive_scan(credentials_path: str, root_folder_id: str, full_scan: bool) -> pd.DataFrame:
    max_companies = None if full_scan else 5
    max_accounts = None if full_scan else 3
    max_assessments = None if full_scan else 10

    rows = drive_scanner.scan_drive(
        credentials_path=credentials_path,
        root_folder_id=root_folder_id,
        max_companies=max_companies,
        max_accounts_per_company=max_accounts,
        max_assessments_per_account=max_assessments,
    )

    drive_scanner.write_csv(rows, SCAN_CSV)

    return load_scan_csv(SCAN_CSV)


def run_batch(folder_ids: list[str], credentials_path: str, prompt_path: str, model: str):
    selected_file = Path("output/portal_selected_folders.txt")
    selected_file.parent.mkdir(parents=True, exist_ok=True)
    selected_file.write_text("\n".join(folder_ids) + "\n", encoding="utf-8")

    command = [
        sys.executable,
        "src/batch_generate.py",
        "--folders-file",
        str(selected_file),
        "--credentials-path",
        credentials_path,
        "--prompt-path",
        prompt_path,
        "--model",
        model,
        "--summary-csv",
        BATCH_SUMMARY_CSV,
    ]

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    output = result.stdout or ""

    summary = pd.DataFrame()
    if Path(BATCH_SUMMARY_CSV).exists():
        summary = pd.read_csv(BATCH_SUMMARY_CSV).fillna("")

    return result.returncode, output, summary


def make_link(url: str, label: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return ""
    return f'<a href="{url}" target="_blank">{label}</a>'


def build_status_badge(row) -> str:
    has_pdf = str(row.get("has_pdf", "")).lower() == "true"
    status = str(row.get("status", "")).strip().lower()
    has_json = str(row.get("has_report_json", "")).lower() == "true"
    has_snapshots = str(row.get("has_snapshots", "")).lower() == "true"

    if not has_json or not has_snapshots:
        return "⚫ Invalid"

    if has_pdf and status == "completed":
        return "🟢 Completed"

    if has_pdf and status != "completed":
        return "🟡 Needs Review"

    return "🔵 Ready"


def clean_batch_summary(summary_df: pd.DataFrame, assessment_date_required: bool) -> pd.DataFrame:
    if summary_df.empty:
        return summary_df

    df = summary_df.copy()

    if not assessment_date_required and "weak_metadata" in df.columns:
        df["weak_metadata"] = (
            df["weak_metadata"]
            .astype(str)
            .str.replace("assessment_date", "", regex=False)
            .str.replace(";;", ";", regex=False)
            .str.strip(";")
        )

    return df


with st.sidebar:
    st.header("Settings")

    credentials_path = st.text_input("Credentials path", DEFAULT_CREDENTIALS_PATH)
    root_folder_id = st.text_input("Processed videos root folder ID", DEFAULT_ROOT_FOLDER_ID)
    prompt_path = st.text_input("Prompt path", DEFAULT_PROMPT_PATH)
    model = st.text_input("OpenAI model", DEFAULT_MODEL)

    full_scan = st.checkbox(
        "Full Drive scan",
        value=False,
        help="Leave off for faster testing. Turn on when you want to scan everything.",
    )

    assessment_date_required = st.checkbox(
        "Require assessment date",
        value=False,
        help="If off, missing assessment dates are not treated as a review warning.",
    )

    st.divider()

    scan_clicked = st.button("Scan Google Drive", type="primary", use_container_width=True)
    load_existing_clicked = st.button("Load existing scan CSV", use_container_width=True)


if not Path(credentials_path).exists():
    st.error(f"Credentials file not found: {credentials_path}")
    st.stop()


if scan_clicked:
    with st.spinner("Scanning Google Drive folders..."):
        try:
            st.session_state["scan_df"] = run_drive_scan(
                credentials_path=credentials_path,
                root_folder_id=root_folder_id,
                full_scan=full_scan,
            )
            st.success("Drive scan complete.")
        except Exception as exc:
            st.error(f"Drive scan failed: {exc}")
            st.stop()

elif load_existing_clicked:
    st.session_state["scan_df"] = load_scan_csv(SCAN_CSV)


scan_df = st.session_state.get("scan_df", load_scan_csv(SCAN_CSV))

if scan_df.empty:
    st.info("Click **Scan Google Drive** to load assessment folders.")
    st.stop()


st.subheader("Assessment folder scan")

valid_df = scan_df[scan_df["is_valid_assessment"].astype(str) == "True"].copy()

if valid_df.empty:
    st.warning("No valid assessment folders found.")
    st.dataframe(scan_df, use_container_width=True)
    st.stop()


valid_df["status_badge"] = valid_df.apply(build_status_badge, axis=1)
valid_df["folder"] = valid_df.apply(lambda row: make_link(row.get("folder_link", ""), "Folder"), axis=1)
valid_df["pdf"] = valid_df.apply(lambda row: make_link(row.get("pdf_link", ""), "PDF"), axis=1)


col1, col2, col3, col4 = st.columns(4)

with col1:
    companies = ["All"] + sorted(valid_df["company"].dropna().unique().tolist())
    company_filter = st.selectbox("Company", companies)

with col2:
    if company_filter != "All":
        account_source = valid_df[valid_df["company"] == company_filter]
    else:
        account_source = valid_df

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
    filtered = filtered[filtered["status_badge"] == "🔵 Ready"]
elif status_filter == "Completed":
    filtered = filtered[filtered["status_badge"] == "🟢 Completed"]
elif status_filter == "Needs Review":
    filtered = filtered[filtered["status_badge"] == "🟡 Needs Review"]
elif status_filter == "Missing PDF":
    filtered = filtered[filtered["has_pdf"].astype(str) != "True"]

if search.strip():
    filtered = filtered[
        filtered["assessment_folder"].str.contains(search.strip(), case=False, na=False)
    ]


st.write(f"Showing **{len(filtered)}** valid assessment folders.")

display_columns = [
    "company",
    "account",
    "assessment_folder",
    "status_badge",
    "has_pdf",
    "status",
    "folder",
    "pdf",
    "has_report_json",
    "has_snapshots",
    "has_video",
    "modified_time",
    "folder_id",
]

link_display = filtered[
    [
        "company",
        "account",
        "assessment_folder",
        "status_badge",
        "has_pdf",
        "status",
        "folder",
        "pdf",
        "modified_time",
    ]
].copy()

st.markdown(
    link_display.to_html(escape=False, index=False),
    unsafe_allow_html=True,
)

st.caption("Use the selectable table below to choose folders for generation.")

filtered_display = filtered[display_columns].copy()
filtered_display.insert(0, "select", False)

edited = st.data_editor(
    filtered_display,
    use_container_width=True,
    hide_index=True,
    column_config={
        "select": st.column_config.CheckboxColumn("Select"),
        "folder_id": st.column_config.TextColumn("Folder ID", disabled=True),
    },
    disabled=[col for col in filtered_display.columns if col != "select"],
)

selected_rows = edited[edited["select"] == True]
selected_folder_ids = selected_rows["folder_id"].tolist()

missing_pdf_rows = filtered[filtered["has_pdf"].astype(str) != "True"]
missing_pdf_folder_ids = missing_pdf_rows["folder_id"].tolist()

st.write(f"Selected **{len(selected_folder_ids)}** folders.")
st.write(f"Visible missing-PDF folders: **{len(missing_pdf_folder_ids)}**")


left, middle, right = st.columns([1, 1, 2])

with left:
    generate_clicked = st.button(
        "Generate selected reports",
        type="primary",
        disabled=len(selected_folder_ids) == 0,
        use_container_width=True,
    )

with middle:
    generate_missing_clicked = st.button(
        "Generate all visible missing PDFs",
        disabled=len(missing_pdf_folder_ids) == 0,
        use_container_width=True,
    )

with right:
    if len(selected_folder_ids) > 0:
        st.caption("Selected folders:")
        st.write(", ".join(selected_rows["assessment_folder"].tolist()))


folders_to_run = []
run_label = ""

if generate_clicked:
    folders_to_run = selected_folder_ids
    run_label = "selected reports"

if generate_missing_clicked:
    folders_to_run = missing_pdf_folder_ids
    run_label = "visible missing PDFs"


if folders_to_run:
    with st.spinner(f"Generating {len(folders_to_run)} {run_label}..."):
        returncode, output, summary_df = run_batch(
            folder_ids=folders_to_run,
            credentials_path=credentials_path,
            prompt_path=prompt_path,
            model=model,
        )

    summary_df = clean_batch_summary(summary_df, assessment_date_required)

    if returncode == 0:
        st.success("Batch generation completed.")
    else:
        st.error("Batch generation completed with one or more failures.")

    if not summary_df.empty:
        st.subheader("Batch summary")
        st.dataframe(summary_df, use_container_width=True)

        weak = summary_df[
            (summary_df["success"].astype(str) != "True")
            | (summary_df["weak_metadata"].astype(str).str.len() > 0)
        ]

        if not weak.empty:
            st.warning("Some rows need review.")
            st.dataframe(weak, use_container_width=True)
        else:
            st.success("No failed rows or weak metadata found.")

    with st.expander("Raw run log"):
        st.code(output)
