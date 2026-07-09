import json
import zipfile
import tempfile
import subprocess
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="Vergo ZIP Report Builder", layout="wide")

st.title("Vergo ZIP Report Builder")
st.caption("Upload one assessment ZIP, add optional context, generate a Vergo PDF report.")

uploaded_zip = st.file_uploader(
    "Upload assessment ZIP",
    type=["zip"],
    accept_multiple_files=False,
)

if uploaded_zip is None:
    st.info("Upload a ZIP containing report.json, video, and snapshots.")
    st.stop()

tmp_dir = Path(tempfile.mkdtemp(prefix="vergo_zip_"))
zip_path = tmp_dir / uploaded_zip.name
zip_path.write_bytes(uploaded_zip.getbuffer())

extract_dir = tmp_dir / "extracted"
extract_dir.mkdir(exist_ok=True)

with zipfile.ZipFile(zip_path, "r") as z:
    z.extractall(extract_dir)

report_jsons = list(extract_dir.rglob("report.json"))

if not report_jsons:
    st.error("No report.json found inside the ZIP.")
    st.stop()

assessment_folder = report_jsons[0].parent

try:
    report_preview = json.loads(report_jsons[0].read_text())
except Exception:
    report_preview = {}

auto_company = report_preview.get("company") or report_preview.get("client") or ""
auto_site = report_preview.get("site") or report_preview.get("site_location") or assessment_folder.name
auto_assessor = report_preview.get("assessor") or report_preview.get("assessor_name") or "Vergo Ergonomics Team"

auto_assessment_type = (
    report_preview.get("assessment_type")
    or report_preview.get("assessmentType")
    or report_preview.get("method")
    or report_preview.get("assessment_method")
    or "Auto-detect"
)

if isinstance(auto_assessment_type, str):
    method_upper = auto_assessment_type.upper()
    if "REBA" in method_upper:
        auto_assessment_type = "REBA"
    elif "RULA" in method_upper:
        auto_assessment_type = "RULA"

st.success(f"ZIP loaded: {uploaded_zip.name}")
st.write(f"Assessment folder detected: `{assessment_folder.name}`")

st.subheader("Detected / Editable Report Details")

company = st.text_input("Company / Client Name", value=auto_company)
site = st.text_input("Site / Task Name", value=auto_site)
assessor = st.text_input("Assessor", value=auto_assessor)
assessment_type = st.text_input("Assessment Type", value=auto_assessment_type, disabled=True)

st.subheader("Additional Report Context")

industry = st.text_input("Industry / sector")
work_setting = st.text_input("Work setting")
worker_role = st.text_input("Worker role / job title")
task_frequency = st.text_input("Task frequency")
load_force = st.text_input("Load / force handled")
equipment_used = st.text_input("Equipment / tools used")
site_constraints = st.text_area("Site constraints or realities")
client_priorities = st.text_area("Client priorities")
notes = st.text_area("Additional notes / task context")

if st.button("Generate Report", type="primary"):
    report_json_path = assessment_folder / "report.json"

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

    report_data = report_preview.copy()
    report_data.update({
        "company": company,
        "client": company,
        "site": site,
        "site_location": site,
        "assessor": assessor,
        "assessment_type": None if assessment_type == "Auto-detect" else assessment_type,
        "task_notes": notes,
        "report_context": report_context,
    })

    report_json_path.write_text(json.dumps(report_data, indent=2))

    (assessment_folder / "task_context.txt").write_text(f"""
Company / Client: {company}
Site / Task: {site}
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
""".strip())

    st.info("Generating report...")

    result = subprocess.run(
        [
            "python3",
            "src/main.py",
            "--assessment-folder",
            str(assessment_folder),
            "--prompt-path",
            "prompts/vergo_master_report_prompt.md",
            "--model",
            "gpt-4.1",
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        st.error("Report generation failed.")
        st.text_area("Error output", result.stderr + "\n" + result.stdout, height=400)
        st.stop()

    pdf_path = Path("output/vergo_report.pdf")
    html_path = Path("output/vergo_report.html")

    st.success("Report generated successfully.")

    if pdf_path.exists():
        st.download_button(
            "Download PDF Report",
            data=pdf_path.read_bytes(),
            file_name=f"{site or assessment_folder.name}_Vergo_Report.pdf",
            mime="application/pdf",
        )

    if html_path.exists():
        st.download_button(
            "Download HTML Report",
            data=html_path.read_bytes(),
            file_name=f"{site or assessment_folder.name}_Vergo_Report.html",
            mime="text/html",
        )
