import argparse
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

import google_drive
import assessment_loader
import report_generator
import docx_builder
import html_report_builder


def parse_args():
    parser = argparse.ArgumentParser(description="Run the Vergo report generator workflow.")
    parser.add_argument("--assessment-folder-id", required=True, help="Google Drive folder ID for the assessment")
    parser.add_argument("--credentials-path", required=True, help="Path to service-account.json credentials")
    parser.add_argument("--prompt-path", required=True, help="Path to the prompt markdown file")
    parser.add_argument("--model", required=True, help="OpenAI model to use")
    return parser.parse_args()


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

    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("Creating HTML report...")
    html_report_path = output_dir / "vergo_report.html"
    html_report_builder.build_html_report(generated_report, html_report_path)
    print(f"Local HTML report saved to: {html_report_path.resolve()}")

    print("Creating Word document...")
    docx_bytes = docx_builder.build_docx(generated_report)

    local_report_path = output_dir / "vergo_report.docx"
    with local_report_path.open("wb") as output_file:
        output_file.write(docx_bytes)

    print(f"Local Word report saved to: {local_report_path.resolve()}")

    print("Uploading Word report...")
    report_filename = "vergo_report.docx"
    uploaded_file = google_drive.upload_file(
        service,
        args.assessment_folder_id,
        report_filename,
        docx_bytes,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )

    print("Updating status.json...")
    status_payload = {
        "status": "completed",
        "reportFile": report_filename,
        "reportFileId": uploaded_file.get("id"),
        "htmlReportFile": "vergo_report.html",
        "uploadedAt": datetime.now(timezone.utc).isoformat(),
    }

    google_drive.create_or_update_json_file(
        service,
        args.assessment_folder_id,
        "status.json",
        status_payload,
    )

    print("Done.")


if __name__ == "__main__":
    main()