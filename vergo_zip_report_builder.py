import json
import mimetypes
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ZIP_DIR = Path("incoming_zips")
RUNS_DIR = Path("zip_report_runs")
ZIP_DIR.mkdir(exist_ok=True)
RUNS_DIR.mkdir(exist_ok=True)

DEFAULT_ROOT_FOLDER_ID = "1zRTHGXHKpNDB2yqubgfXKqd2r6qO-92_"

st.set_page_config(page_title="Vergo ZIP Report Builder", layout="wide")
st.title("Vergo ZIP Report Builder")
st.caption("Select a ZIP, upload it to Drive as an assessment folder, generate the PDF report.")

def drive_service():
    creds = service_account.Credentials.from_service_account_file(
        "credentials/service-account.json",
        scopes=["https://www.googleapis.com/auth/drive"],
    )
    return build("drive", "v3", credentials=creds)

def create_drive_folder(service, name, parent_id):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id],
    }
    return service.files().create(
        body=metadata,
        fields="id",
        supportsAllDrives=True,
    ).execute()["id"]

def upload_file(service, local_path, parent_id):
    mime_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    metadata = {"name": local_path.name, "parents": [parent_id]}
    media = MediaFileUpload(str(local_path), mimetype=mime_type, resumable=True)
    return service.files().create(
        body=metadata,
        media_body=media,
        fields="id",
        supportsAllDrives=True,
    ).execute()["id"]

def upload_folder_tree(service, local_folder, drive_parent_id):
    folder_map = {local_folder: drive_parent_id}

    for path in sorted(local_folder.rglob("*")):
        parent_drive_id = folder_map[path.parent]

        if path.is_dir():
            folder_map[path] = create_drive_folder(service, path.name, parent_drive_id)
        else:
            upload_file(service, path, parent_drive_id)

zips = sorted(ZIP_DIR.glob("*.zip"))

if not zips:
    st.warning("No ZIP files found in incoming_zips.")
    st.stop()

selected_zip = st.selectbox("Select ZIP", zips, format_func=lambda p: p.name)
root_folder_id = st.text_input("Google Drive destination root folder ID", value=DEFAULT_ROOT_FOLDER_ID)

def read_report_json_from_zip(zip_path):
    try:
        with zipfile.ZipFile(zip_path, "r") as z:
            report_name = next(
                name for name in z.namelist()
                if name.lower().endswith("report.json")
            )
            return json.loads(z.read(report_name))
    except Exception:
        return {}

report_preview = read_report_json_from_zip(selected_zip)

auto_company = (
    report_preview.get("company")
    or report_preview.get("client")
    or report_preview.get("company_name")
    or ""
)

auto_site = (
    report_preview.get("site")
    or report_preview.get("site_location")
    or report_preview.get("task_name")
    or report_preview.get("task")
    or selected_zip.stem
)

auto_assessor = (
    report_preview.get("assessor")
    or report_preview.get("assessor_name")
    or "Vergo Ergonomics Team"
)

auto_assessment_type = (
    report_preview.get("assessment_type")
    or report_preview.get("assessmentType")
    or report_preview.get("method")
    or report_preview.get("assessment_method")
    or "Auto-detect"
)

if isinstance(auto_assessment_type, str):
    upper_method = auto_assessment_type.upper()
    if "REBA" in upper_method:
        auto_assessment_type = "REBA"
    elif "RULA" in upper_method:
        auto_assessment_type = "RULA"

st.subheader("Detected Assessment Details")
company = st.text_input("Company / Client Name", value=auto_company)
site = st.text_input("Site / Task Name", value=auto_site)
assessor = st.text_input("Assessor", value=auto_assessor)
assessment_type = st.text_input("Assessment Type", value=auto_assessment_type, disabled=True)

st.subheader("Additional Report Context")

industry = st.text_input("Industry / sector", placeholder="e.g., healthcare, warehousing, manufacturing, food processing")
work_setting = st.text_input("Work setting", placeholder="e.g., long-term care room, warehouse line, production floor")
worker_role = st.text_input("Worker role / job title", placeholder="e.g., CCA, warehouse associate, machine operator")
task_frequency = st.text_input("Task frequency", placeholder="e.g., repeated every shift, 20 times/day, occasional")
load_force = st.text_input("Load / force handled", placeholder="e.g., 10 kg tote, patient transfer, light parts handling")
equipment_used = st.text_input("Equipment / tools used", placeholder="e.g., sling, cart, tote, workstation, handheld scanner")
site_constraints = st.text_area("Site constraints or realities", placeholder="e.g., limited space, fixed bed height, staffing constraints, production pace")
client_priorities = st.text_area("Client priorities", placeholder="e.g., reduce shoulder strain, improve transfer setup, minimize disruption")
notes = st.text_area("Additional notes / task context")

if st.button("Generate Report", type="primary"):
    run_dir = RUNS_DIR / datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(selected_zip, "r") as z:
        z.extractall(run_dir)

    report_jsons = list(run_dir.rglob("report.json"))
    if not report_jsons:
        st.error("No report.json found inside ZIP.")
        st.stop()

    assessment_folder = report_jsons[0].parent

    report_json_path = assessment_folder / "report.json"

    try:
        report_json = json.loads(report_json_path.read_text())
    except Exception:
        report_json = {}

    report_context = {
        "industry": industry,
        "work_setting": work_setting,
        "worker_role": worker_role,
        "task_frequency": task_frequency,
        "load_force": load_force,
        "equipment_used": equipment_used,
        "site_constraints": site_constraints,
        "client_priorities": client_priorities,
        "additional_notes": notes,
    }

    metadata = {
        "company": company,
        "client": company,
        "site": site or assessment_folder.name,
        "site_location": site or assessment_folder.name,
        "assessor": assessor,
        "assessment_type": assessment_type if assessment_type != "Auto-detect" else None,
        "task_notes": notes,
        "report_context": report_context,
    }

    report_json.update(metadata)
    report_json_path.write_text(json.dumps(report_json, indent=2))

    (assessment_folder / "metadata.json").write_text(json.dumps(metadata, indent=2))

    task_context_text = f"""
Company / Client: {company}
Site / Task: {site or assessment_folder.name}
Assessor: {assessor}
Assessment Type: {assessment_type}

Industry / sector: {industry}
Work setting: {work_setting}
Worker role / job title: {worker_role}
Task frequency: {task_frequency}
Load / force handled: {load_force}
Equipment / tools used: {equipment_used}

Site constraints or realities:
{site_constraints}

Client priorities:
{client_priorities}

Additional notes:
{notes}
""".strip()

    (assessment_folder / "task_context.txt").write_text(task_context_text)

    with st.status("Uploading ZIP contents to Google Drive...", expanded=True) as status:
        service = drive_service()
        drive_folder_name = f"{assessment_folder.name} - quick report {datetime.now().strftime('%Y%m%d-%H%M%S')}"
        assessment_drive_id = create_drive_folder(service, drive_folder_name, root_folder_id)

        st.write(f"Created Drive folder: {assessment_drive_id}")
        upload_folder_tree(service, assessment_folder, assessment_drive_id)

        status.update(label="Uploaded to Drive", state="complete")

    with st.status("Generating report...", expanded=True) as status:
        result = subprocess.run(
            [
                "python3",
                "src/main.py",
                "--assessment-folder-id",
                assessment_drive_id,
                "--credentials-path",
                "credentials/service-account.json",
                "--prompt-path",
                "prompts/vergo_master_report_prompt.md",
                "--model",
                "gpt-4.1",
            ],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            status.update(label="Report generation failed", state="error")
            st.error("Report generation failed.")
            st.text_area("Error output", result.stderr + "\n" + result.stdout, height=400)
            st.stop()

        status.update(label="Report generated", state="complete")

    pdf_path = Path("output/vergo_report.pdf")
    html_path = Path("output/vergo_report.html")

    st.success("Report generated successfully.")

    if pdf_path.exists():
        st.download_button(
            "Download PDF Report",
            data=pdf_path.read_bytes(),
            file_name=f"{assessment_folder.name}_Vergo_Report.pdf",
            mime="application/pdf",
        )

    if html_path.exists():
        st.download_button(
            "Download HTML Report",
            data=html_path.read_bytes(),
            file_name=f"{assessment_folder.name}_Vergo_Report.html",
            mime="text/html",
        )
