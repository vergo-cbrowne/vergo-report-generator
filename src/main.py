from googleapiclient.http import MediaIoBaseDownload
import argparse
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import google_drive
import assessment_loader
import report_generator
import html_report_builder
import pdf_builder
import re
import training_modules
import risk_interpretation


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Vergo PDF report generator workflow.")
    parser.add_argument("--assessment-folder-id", required=True, help="Google Drive folder ID for the assessment")
    parser.add_argument("--credentials-path", required=True, help="Path to service-account.json credentials")
    parser.add_argument("--prompt-path", required=True, help="Path to the prompt markdown file")
    parser.add_argument("--model", required=True, help="OpenAI model to use")
    return parser.parse_args()


def _clean_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "\n\n".join(_clean_text(item) for item in value if _clean_text(item))

    if isinstance(value, dict):
        parts = []
        for _, val in value.items():
            cleaned = _clean_text(val)
            if cleaned:
                parts.append(cleaned)
        return "\n\n".join(parts)

    return str(value).strip()


def _item_has_heading_and_content(item: dict) -> bool:
    if not isinstance(item, dict):
        return False

    heading = (
        item.get("heading")
        or item.get("Heading")
        or item.get("title")
        or item.get("Title")
        or item.get("module")
        or item.get("Module")
    )

    content = (
        item.get("content")
        or item.get("Content")
        or item.get("body")
        or item.get("Body")
        or item.get("details")
        or item.get("Details")
        or item.get("explanation")
        or item.get("Explanation")
        or item.get("description")
        or item.get("Description")
        or item.get("recommendation")
        or item.get("Recommendation")
        or item.get("reason")
        or item.get("Reason")
        or item.get("rationale")
        or item.get("Rationale")
        or item.get("paragraph")
        or item.get("Paragraph")
        or item.get("paragraphs")
        or item.get("Paragraphs")
    )

    return bool(_clean_text(heading)) and bool(_clean_text(content))


def _list_has_complete_items(data: dict, key: str) -> bool:
    items = data.get(key)

    if not isinstance(items, list) or not items:
        return False

    return all(_item_has_heading_and_content(item) for item in items)


def _report_has_complete_sections(data: dict) -> bool:
    return (
        isinstance(data, dict)
        and _list_has_complete_items(data, "risk_exposure_analysis")
        and _list_has_complete_items(data, "recommendations")
    )


def _load_raw_parsed_response_if_better(generated_report: dict) -> dict:
    """
    report_generator.py currently normalizes the AI response and may strip body/content
    from Section 3 and Section 5. The raw parsed response is saved in debug/.
    If the normalized report is missing content but the raw parsed response is complete,
    use the raw parsed response for HTML/PDF generation.
    """
    debug_path = Path("debug/latest_parsed_response.json")

    if not debug_path.exists():
        print("DEBUG: latest_parsed_response.json not found; using generated report.")
        return generated_report

    try:
        raw_report = json.loads(debug_path.read_text(encoding="utf-8"))
    except Exception as exc:
        print(f"DEBUG: Could not read raw parsed response: {exc}")
        return generated_report

    generated_complete = _report_has_complete_sections(generated_report)
    raw_complete = _report_has_complete_sections(raw_report)

    print(f"DEBUG: generated report has complete Section 3/5 content: {generated_complete}")
    print(f"DEBUG: raw parsed response has complete Section 3/5 content: {raw_complete}")

    if raw_complete and not generated_complete:
        print("Using raw parsed response for HTML/PDF rendering because it preserves Section 3 and Section 5 content.")
        return raw_report

    return generated_report


BAD_METADATA_VALUES = {
    "",
    "unknown",
    "none",
    "n/a",
    "na",
    "not applicable",
    "not specified",
    "confidential",
    "[put client/company name here]",
    "[put facility/location here]",
    "[put date here if known]",
    "[briefly describe where the task happens. example: production floor, warehouse, healthcare setting, manufacturing station, construction area, etc.]",
    "[add any useful context for the report. example: repetitive handling, reaching, wrist movement, lifting, bending, standing work, overhead work, tool use, awkward posture, etc.]",
}


def _clean_metadata_value(value: str | None) -> str:
    if value is None:
        return ""

    cleaned = str(value).strip()

    # Remove common markdown / doc formatting leftovers.
    cleaned = cleaned.strip("*").strip()

    if not cleaned:
        return ""

    if cleaned.lower() in BAD_METADATA_VALUES:
        return ""

    # Ignore generic square-bracket placeholders.
    if cleaned.startswith("[") and cleaned.endswith("]"):
        return ""

    return cleaned


def _load_task_context_text(service, assessment_folder_id: str) -> str:
    """
    Load task_context.txt from the assessment folder.

    Supports both:
    - Google Docs named task_context.txt
    - uploaded plain text files named task_context.txt
    """
    try:
        results = service.files().list(
            q=f"'{assessment_folder_id}' in parents and trashed = false",
            fields="files(id, name, mimeType, modifiedTime)",
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
        ).execute()

        files = results.get("files", [])
        matches = [
            f for f in files
            if f.get("name", "").strip().lower() == "task_context.txt"
        ]

        if not matches:
            print("Metadata: No task_context.txt found in assessment folder.")
            return ""

        matches.sort(key=lambda f: f.get("modifiedTime", ""), reverse=True)
        task_context_file = matches[0]

        file_id = task_context_file["id"]
        file_name = task_context_file.get("name", "")
        mime_type = task_context_file.get("mimeType", "")

        print(f"Metadata: Found task_context.txt: {file_name} ({mime_type})")

        if mime_type == "application/vnd.google-apps.document":
            request = service.files().export_media(
                fileId=file_id,
                mimeType="text/plain",
            )
        else:
            request = service.files().get_media(
                fileId=file_id,
                supportsAllDrives=True,
            )

        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        loaded_text = fh.getvalue().decode("utf-8", errors="replace").strip()

        if not loaded_text:
            print("Metadata: task_context.txt was found but is empty.")
            return ""

        print("Metadata: Loaded task_context.txt successfully.")
        return loaded_text

    except Exception as exc:
        print(f"Metadata: Could not load task_context.txt: {exc}")
        return ""


def _extract_label_value(text: str, labels: list[str]) -> str:
    for label in labels:
        pattern = rf"^\s*{re.escape(label)}\s*:\s*(.+?)\s*$"
        match = re.search(pattern, text, flags=re.IGNORECASE | re.MULTILINE)
        if match:
            value = _clean_metadata_value(match.group(1))
            if value:
                return value
    return ""


def _extract_task_context_metadata(text: str) -> dict:
    if not text:
        return {}

    company = _extract_label_value(text, ["Client", "Company", "Company/Client name"])
    site = _extract_label_value(text, ["Site", "Site / Location", "Location", "Facility", "Site location or facility name"])
    assessment_date = _extract_label_value(text, ["Assessment Date", "Date"])
    assessor = _extract_label_value(text, ["Assessor", "Assessor Name"])
    assessment_method = _extract_label_value(text, ["Assessment Method", "Method"])

    metadata = {}

    if company:
        metadata["Company/Client name"] = company
        metadata["company"] = company
        metadata["client"] = company

    if site:
        metadata["Site location or facility name"] = site
        metadata["site_location"] = site
        metadata["site"] = site

    if assessment_date:
        metadata["Assessment date"] = assessment_date
        metadata["assessment_date"] = assessment_date

    if assessor:
        metadata["Assessor name"] = assessor
        metadata["assessor"] = assessor

    if assessment_method:
        metadata["Assessment method"] = assessment_method
        metadata["assessment_method"] = assessment_method

    return metadata



def _find_first_metadata_value(data, possible_keys: list[str]) -> str:
    """
    Search report.json recursively for likely metadata fields.
    """
    possible = {k.lower().replace(" ", "_").replace("/", "_") for k in possible_keys}

    def normalize_key(key):
        return str(key).lower().strip().replace(" ", "_").replace("/", "_")

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if normalize_key(key) in possible:
                    cleaned = _clean_metadata_value(item)
                    if cleaned:
                        return cleaned

            for item in value.values():
                found = walk(item)
                if found:
                    return found

        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found:
                    return found

        return ""

    return walk(data)


def _extract_report_json_metadata_auto(report_data: dict) -> dict:
    """
    Pull metadata from report.json when available.
    """
    if not isinstance(report_data, dict):
        return {}

    company = _find_first_metadata_value(
        report_data,
        [
            "client",
            "client_name",
            "company",
            "company_name",
            "customer",
            "customer_name",
            "organization",
            "organization_name",
            "employer",
        ],
    )

    site = _find_first_metadata_value(
        report_data,
        [
            "site",
            "site_name",
            "site_location",
            "location",
            "facility",
            "facility_name",
            "worksite",
            "work_area",
        ],
    )

    task = _find_first_metadata_value(
        report_data,
        [
            "task",
            "task_name",
            "task_title",
            "activity",
            "activity_name",
            "assessment_name",
            "video_name",
            "file_name",
            "filename",
        ],
    )

    assessment_date = _find_first_metadata_value(
        report_data,
        [
            "assessment_date",
            "date",
            "created_date",
            "analysis_date",
            "recorded_date",
        ],
    )

    metadata = {}

    if company:
        metadata["Company/Client name"] = company
        metadata["company"] = company
        metadata["client"] = company

    if site:
        metadata["Site location or facility name"] = site
        metadata["site_location"] = site
        metadata["site"] = site

    if task:
        metadata["Task name/title"] = task
        metadata["task_name"] = task
        metadata["task"] = task

    if assessment_date:
        metadata["Assessment date"] = assessment_date
        metadata["assessment_date"] = assessment_date

    if metadata:
        print(f"Metadata: Extracted from report.json fields: {metadata}")

    return metadata



def _infer_company_from_folder_name(folder_name: str) -> str:
    """
    Infer client/company from processed assessment folder names.

    Examples:
    - Cameco_Vergo_3 - b5ee8 -> Cameco
    - EastCut_Vergo_1 - abc123 -> EastCut
    - VenRez Lift Assist Counter Top Feed - ae484 -> ""
      because this is a task name, not a company name.
    """
    cleaned = _clean_metadata_value(folder_name)
    if not cleaned:
        return ""

    # Remove trailing generated IDs, e.g. " - b5ee8"
    cleaned = re.sub(r"\s*-\s*[a-zA-Z0-9]{4,}$", "", cleaned).strip()

    if "_Vergo" in cleaned:
        return _clean_metadata_value(cleaned.split("_Vergo", 1)[0].replace("_", " "))

    if "- Vergo" in cleaned:
        return _clean_metadata_value(cleaned.split("- Vergo", 1)[0])

    return ""


def _get_drive_folder_metadata(service, assessment_folder_id: str) -> dict:
    """
    Use Vergo's Google Drive folder structure for fallback metadata.

    Expected structure:
    Company folder
      └── Account detail / user folder
          └── Processed assessment folder

    Therefore:
    - Company should usually be the grandparent folder.
    - Site / Location should be the processed assessment folder name.
    - If no grandparent exists, fall back to inferring from the processed folder name.
    - If that fails, fall back to the immediate parent.
    """
    try:
        folder = service.files().get(
            fileId=assessment_folder_id,
            fields="id,name,parents,mimeType",
            supportsAllDrives=True,
        ).execute()

        assessment_folder_name = _clean_metadata_value(folder.get("name", ""))
        parents = folder.get("parents", []) or []

        immediate_parent_name = ""
        grandparent_name = ""

        if parents:
            parent = service.files().get(
                fileId=parents[0],
                fields="id,name,parents,mimeType",
                supportsAllDrives=True,
            ).execute()

            immediate_parent_name = _clean_metadata_value(parent.get("name", ""))
            grandparent_ids = parent.get("parents", []) or []

            if grandparent_ids:
                grandparent = service.files().get(
                    fileId=grandparent_ids[0],
                    fields="id,name,mimeType",
                    supportsAllDrives=True,
                ).execute()
                grandparent_name = _clean_metadata_value(grandparent.get("name", ""))

        inferred_from_processed_folder = _infer_company_from_folder_name(assessment_folder_name)

        company = grandparent_name or inferred_from_processed_folder or immediate_parent_name

        metadata = {}

        if company:
            metadata["Company/Client name"] = company
            metadata["company"] = company
            metadata["client"] = company

        if assessment_folder_name:
            metadata["Site location or facility name"] = assessment_folder_name
            metadata["site_location"] = assessment_folder_name
            metadata["site"] = assessment_folder_name

        if metadata:
            print(f"Metadata: Extracted folder metadata: {metadata}")

        return metadata

    except Exception as exc:
        print(f"Metadata: Could not extract Drive folder metadata: {exc}")
        return {}


def _merge_auto_metadata(folder_metadata: dict, report_json_metadata: dict, task_context_metadata: dict) -> dict:
    """
    Priority:
    1. Folder metadata provides fallback client/site.
    2. report.json overrides folder metadata when it has client/site/task/date.
    3. task_context.txt only overrides date, assessor, and method.

    task_context.txt should not override company, client, site, or task name because those
    should come from report.json or the Google Drive folder/file structure.
    """
    merged = {}
    merged.update(folder_metadata or {})
    merged.update(report_json_metadata or {})

    allowed_task_context_keys = {
        "Assessment date",
        "assessment_date",
        "Assessor name",
        "assessor",
        "Assessment method",
        "assessment_method",
    }

    for key, value in (task_context_metadata or {}).items():
        if key in allowed_task_context_keys:
            merged[key] = value

    return merged


def _apply_task_context_metadata(report: dict, metadata: dict) -> dict:
    if not metadata:
        print("Metadata: No usable metadata extracted from task_context.txt.")
        return report

    print(f"Metadata: Applying final report metadata: {metadata}")

    cover_details = report.get("cover_details")
    if not isinstance(cover_details, dict):
        cover_details = {}

    cover_details.update(metadata)
    report["cover_details"] = cover_details

    return report


def _is_weak_metadata_value(value) -> bool:
    if value is None:
        return True

    cleaned = str(value).strip()

    return cleaned.lower() in {
        "",
        "unknown",
        "none",
        "n/a",
        "na",
        "not applicable",
        "not specified",
        "confidential",
    }


def _normalize_date_value(value) -> str:
    """
    Normalize common date strings to YYYY-MM-DD when possible.
    """
    if value is None:
        return ""

    text = str(value).strip()

    if _is_weak_metadata_value(text):
        return ""

    # Reject time-only values. These are usually video durations, not assessment dates.
    if re.fullmatch(r"\d{1,2}:\d{2}:\d{2}", text):
        return ""

    # Match YYYY-MM-DD inside ISO/date strings.
    match = re.search(r"\b(20\d{2}-\d{2}-\d{2})\b", text)
    if match:
        return match.group(1)

    # Match YYYY/MM/DD and convert.
    match = re.search(r"\b(20\d{2})/(\d{2})/(\d{2})\b", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    return text


def _find_assessment_date_in_report_json(data) -> str:
    """
    Recursively search report.json for likely assessment/analysis date fields.
    """
    preferred_keys = {
        "assessment_date",
        "assessmentdate",
        "analysis_date",
        "analysisdate",
        "recorded_date",
        "recordeddate",
        "created_date",
        "createddate",
        "date",
    }

    secondary_keys = {
        "created_at",
        "createdat",
        "updated_at",
        "updatedat",
        "timestamp",
        "time",
    }

    def normalize_key(key) -> str:
        return str(key).lower().replace(" ", "_").replace("-", "_").replace("/", "_")

    def walk(value, keys_to_match):
        if isinstance(value, dict):
            for key, item in value.items():
                norm = normalize_key(key)
                compact = norm.replace("_", "")

                if norm in keys_to_match or compact in keys_to_match:
                    date_value = _normalize_date_value(item)
                    if date_value:
                        return date_value

            for item in value.values():
                found = walk(item, keys_to_match)
                if found:
                    return found

        elif isinstance(value, list):
            for item in value:
                found = walk(item, keys_to_match)
                if found:
                    return found

        return ""

    return walk(data, preferred_keys) or walk(data, secondary_keys)


def _slugify_report_filename(value: str) -> str:
    """
    Convert an assessment folder/task name into a safe PDF filename.

    Example:
    Sorting and marking paper - 86074
    -> Sorting_and_marking_paper_Vergo_Report.pdf
    """
    if not value:
        return "Vergo_Report.pdf"

    cleaned = str(value).strip()

    # Remove common generated suffixes, e.g. " - 86074", " - ae484", " - b5ee8"
    cleaned = re.sub(r"\s*-\s*[A-Za-z0-9]{4,}$", "", cleaned).strip()

    # Keep letters, numbers, spaces, hyphens, and underscores.
    cleaned = re.sub(r"[^A-Za-z0-9 _-]+", "", cleaned)

    # Convert spaces and hyphens to underscores.
    cleaned = re.sub(r"[\s-]+", "_", cleaned)

    # Collapse repeated underscores.
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")

    if not cleaned:
        cleaned = "Vergo_Report"

    return f"{cleaned}_Vergo_Report.pdf"


def _get_assessment_folder_name(service, assessment_folder_id: str) -> str:
    try:
        folder = service.files().get(
            fileId=assessment_folder_id,
            fields="id,name",
            supportsAllDrives=True,
        ).execute()
        return folder.get("name", "")
    except Exception as exc:
        print(f"Could not read assessment folder name for PDF filename: {exc}")
        return ""


def main():
    args = parse_args()

    load_dotenv()
    print("Loaded environment variables.")

    print("Connecting to Google Drive...")
    service = google_drive.create_drive_service(args.credentials_path)

    print("Loading assessment folder...")
    report_data, snapshot_files = assessment_loader.load_assessment_folder(
        service,
        args.assessment_folder_id,
    )

    print("Found report.json")
    print("Found snapshots")

    print("Loading task notes if available...")
    task_notes = assessment_loader.load_task_notes(
        service,
        args.assessment_folder_id,
    )

    print("Generating report with OpenAI...")
    generated_report = report_generator.generate_report(
        args.prompt_path,
        report_data,
        snapshot_files,
        args.model,
        style_guide_path="prompts/vergo_writing_style_guide.md",
        task_notes=task_notes,
    )

    report_for_rendering = _load_raw_parsed_response_if_better(generated_report)

    print("Loading task_context.txt metadata if available...")
    task_context_text = _load_task_context_text(service, args.assessment_folder_id)
    task_context_metadata = _extract_task_context_metadata(task_context_text)
    report_json_metadata = _extract_report_json_metadata_auto(report_data)
    folder_metadata = _get_drive_folder_metadata(service, args.assessment_folder_id)
    combined_metadata = _merge_auto_metadata(folder_metadata, report_json_metadata, task_context_metadata)

    # Vergo processed folder names often contain the client name, e.g.
    # Cameco_Vergo_3 - b5ee8 -> Cameco.
    # This prevents account/user folders like "Kenil Patel" from being used as the company.
    site_name = combined_metadata.get("Site location or facility name") or combined_metadata.get("site_location") or ""
    if "_Vergo" in site_name:
        inferred_company = site_name.split("_Vergo", 1)[0].replace("_", " ").strip()
        if inferred_company:
            combined_metadata["Company/Client name"] = inferred_company
            combined_metadata["company"] = inferred_company
            combined_metadata["client"] = inferred_company
            print(f"Metadata: Inferred company from processed folder name: {inferred_company}")

    # Default assessor if missing.
    if _is_weak_metadata_value(combined_metadata.get("Assessor name")) and _is_weak_metadata_value(combined_metadata.get("assessor")):
        combined_metadata["Assessor name"] = "Vergo Ergonomics Team"
        combined_metadata["assessor"] = "Vergo Ergonomics Team"
        print("Metadata: Defaulted assessor to Vergo Ergonomics Team")

    # Improve assessment date from report.json if missing.
    existing_date = combined_metadata.get("Assessment date") or combined_metadata.get("assessment_date")
    if _is_weak_metadata_value(existing_date):
        inferred_date = _find_assessment_date_in_report_json(report_data)
        if inferred_date:
            combined_metadata["Assessment date"] = inferred_date
            combined_metadata["assessment_date"] = inferred_date
            print(f"Metadata: Inferred assessment date from report.json: {inferred_date}")

    report_for_rendering = _apply_task_context_metadata(report_for_rendering, combined_metadata)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating HTML report...")
    html_report_path = output_dir / "vergo_report.html"
    print("Normalizing risk interpretation and assessment method...")
    report_for_rendering = risk_interpretation.normalize_risk_language(report_for_rendering)

    print("Validating targeted Vergo training modules...")
    report_for_rendering = training_modules.normalize_training_videos(report_for_rendering)
    html_report_builder.build_html_report(report_for_rendering, html_report_path)
    print(f"Local HTML report saved to: {html_report_path.resolve()}")

    print("Creating PDF report...")
    pdf_report_path = output_dir / "vergo_report.pdf"
    pdf_builder.build_pdf_from_html(html_report_path, pdf_report_path)
    print(f"Local PDF report saved to: {pdf_report_path.resolve()}")

    print("Uploading PDF report...")
    assessment_folder_name = _get_assessment_folder_name(service, args.assessment_folder_id)
    report_filename = _slugify_report_filename(assessment_folder_name)
    print(f"PDF Drive filename: {report_filename}")

    pdf_bytes = pdf_report_path.read_bytes()

    uploaded_file = google_drive.upload_file(
        service,
        args.assessment_folder_id,
        report_filename,
        pdf_bytes,
        "application/pdf",
    )

    if report_filename != "vergo_report.pdf":
        print("Cleaning old generic vergo_report.pdf files from assessment folder...")
        trashed_old_reports = google_drive.trash_files_by_name(
            service=service,
            folder_id=args.assessment_folder_id,
            name="vergo_report.pdf",
            keep_file_id=uploaded_file.get("id"),
        )
        print(f"Old generic PDF files trashed: {trashed_old_reports}")

    print("Updating status.json...")
    status_payload = {
        "status": "completed",
        "reportFile": report_filename,
        "reportFileId": uploaded_file.get("id"),
        "htmlReportFile": "vergo_report.html",
        "pdfReportFile": report_filename,
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }

    google_drive.create_or_update_json_file(
        service,
        args.assessment_folder_id,
        "status.json",
        status_payload,
    )

    print("Done.")
    print(f"HTML output: {html_report_path.resolve()}")
    print(f"PDF output: {pdf_report_path.resolve()}")


if __name__ == "__main__":
    main()
