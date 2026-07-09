import argparse
import json
from pathlib import Path

from dotenv import load_dotenv

import report_generator
import pdf_builder

load_dotenv()


def load_local_assessment(folder_path: str):
    folder = Path(folder_path)

    report_json = folder / "report.json"
    if not report_json.exists():
        matches = list(folder.rglob("report.json"))
        if not matches:
            raise FileNotFoundError(f"No report.json found in {folder}")
        report_json = matches[0]
        folder = report_json.parent

    report_data = json.loads(report_json.read_text())

    task_context = folder / "task_context.txt"
    if task_context.exists():
        report_data["task_context"] = task_context.read_text()

    snapshots_dir = folder / "snapshots"
    snapshot_files = []
    if snapshots_dir.exists():
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            snapshot_files.extend(snapshots_dir.glob(ext))

    if not snapshot_files:
        for ext in ("*.png", "*.jpg", "*.jpeg"):
            snapshot_files.extend(folder.rglob(ext))

    snapshot_files = [str(p) for p in snapshot_files if "__MACOSX" not in str(p)]

    return report_data, snapshot_files


def main():
    parser = argparse.ArgumentParser(description="Run Vergo report generation from a local assessment folder.")
    parser.add_argument("--local-assessment-folder", required=True)
    parser.add_argument("--prompt-path", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    print("Loading local assessment folder...")
    report_data, snapshot_files = load_local_assessment(args.local_assessment_folder)

    print(f"Found {len(snapshot_files)} snapshot(s).")
    print("Generating report...")

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    html_path = output_dir / "vergo_report.html"
    pdf_path = output_dir / "vergo_report.pdf"

    # Try the most common existing generator signatures
    try:
        html = report_generator.generate_report_html(
            report_data=report_data,
            snapshot_files=snapshot_files,
            prompt_path=args.prompt_path,
            model=args.model,
        )
    except TypeError:
        try:
            html = report_generator.generate_report_html(
                report_data,
                snapshot_files,
                args.prompt_path,
                args.model,
            )
        except AttributeError:
            html = report_generator.generate_html_report(
                report_data,
                snapshot_files,
                args.prompt_path,
                args.model,
            )

    html_path.write_text(html)

    print("Building PDF...")
    try:
        pdf_builder.build_pdf(str(html_path), str(pdf_path))
    except AttributeError:
        try:
            pdf_builder.create_pdf(str(html_path), str(pdf_path))
        except AttributeError:
            pdf_builder.html_to_pdf(str(html_path), str(pdf_path))

    print(f"Report complete: {pdf_path}")


if __name__ == "__main__":
    main()
