import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import google_drive
import assessment_loader
import report_generator
import html_report_builder
import pdf_builder


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

    print("Generating report with OpenAI...")
    generated_report = report_generator.generate_report(
        args.prompt_path,
        report_data,
        snapshot_files,
        args.model,
        style_guide_path="prompts/vergo_writing_style_guide.md",
    )

    report_for_rendering = _load_raw_parsed_response_if_better(generated_report)

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating HTML report...")
    html_report_path = output_dir / "vergo_report.html"
    html_report_builder.build_html_report(report_for_rendering, html_report_path)
    print(f"Local HTML report saved to: {html_report_path.resolve()}")

    print("Creating PDF report...")
    pdf_report_path = output_dir / "vergo_report.pdf"
    pdf_builder.build_pdf_from_html(html_report_path, pdf_report_path)
    print(f"Local PDF report saved to: {pdf_report_path.resolve()}")

    print("Uploading PDF report...")
    report_filename = "vergo_report.pdf"
    pdf_bytes = pdf_report_path.read_bytes()

    uploaded_file = google_drive.upload_file(
        service,
        args.assessment_folder_id,
        report_filename,
        pdf_bytes,
        "application/pdf",
    )

    print("Updating status.json...")
    status_payload = {
        "status": "completed",
        "reportFile": report_filename,
        "reportFileId": uploaded_file.get("id"),
        "htmlReportFile": "vergo_report.html",
        "pdfReportFile": "vergo_report.pdf",
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