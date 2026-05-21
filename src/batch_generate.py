import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def parse_folder_ids(raw: str) -> list[str]:
    if not raw:
        return []

    # Accept comma-separated, newline-separated, or space-separated folder IDs.
    cleaned = raw.replace(",", " ").replace("\n", " ")
    return [item.strip() for item in cleaned.split(" ") if item.strip()]


def run_one(folder_id: str, credentials_path: str, prompt_path: str, model: str) -> dict:
    command = [
        sys.executable,
        "src/main.py",
        "--assessment-folder-id",
        folder_id,
        "--credentials-path",
        credentials_path,
        "--prompt-path",
        prompt_path,
        "--model",
        model,
    ]

    started_at = datetime.now().isoformat(timespec="seconds")

    print("")
    print("=" * 80)
    print(f"Running assessment folder: {folder_id}")
    print("=" * 80)

    result = subprocess.run(
        command,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )

    output = result.stdout or ""

    # Print the full output for visibility while still capturing summary.
    print(output)

    success = result.returncode == 0 and "Done." in output

    company = extract_html_value("Company")
    site = extract_html_value("Site / Location")
    assessment_date = extract_html_value("Assessment Date")
    method = extract_html_value("Assessment Method")
    assessor = extract_html_value("Assessor")

    return {
        "folder_id": folder_id,
        "success": success,
        "returncode": result.returncode,
        "company": company,
        "site": site,
        "assessment_date": assessment_date,
        "method": method,
        "assessor": assessor,
        "started_at": started_at,
    }


def extract_html_value(label: str) -> str:
    """
    Read the latest local output/vergo_report.html and extract a metadata value.
    This is intentionally simple and only used for the batch summary.
    """
    html_path = Path("output/vergo_report.html")

    if not html_path.exists():
        return "Not available"

    html = html_path.read_text(encoding="utf-8", errors="replace")

    marker = f'<div class="label">{label}:</div><div>'
    start = html.find(marker)

    if start == -1:
        return "Not found"

    start += len(marker)
    end = html.find("</div>", start)

    if end == -1:
        return "Not found"

    return html[start:end].strip()


def main():
    parser = argparse.ArgumentParser(description="Batch-generate Vergo PDF reports from Google Drive assessment folders.")

    parser.add_argument(
        "--folder-ids",
        required=True,
        help="Comma, space, or newline separated Google Drive assessment folder IDs.",
    )

    parser.add_argument(
        "--credentials-path",
        default="credentials/service-account.json",
        help="Path to Google service account credentials.",
    )

    parser.add_argument(
        "--prompt-path",
        default="prompts/vergo_master_report_prompt.md",
        help="Path to the master report prompt.",
    )

    parser.add_argument(
        "--model",
        default="gpt-4.1",
        help="OpenAI model to use.",
    )

    args = parser.parse_args()

    folder_ids = parse_folder_ids(args.folder_ids)

    if not folder_ids:
        raise SystemExit("No folder IDs provided.")

    print("")
    print("Batch Vergo report generation")
    print(f"Folders to process: {len(folder_ids)}")
    print(f"Model: {args.model}")

    results = []

    for folder_id in folder_ids:
        try:
            result = run_one(
                folder_id=folder_id,
                credentials_path=args.credentials_path,
                prompt_path=args.prompt_path,
                model=args.model,
            )
            results.append(result)
        except Exception as exc:
            print("")
            print(f"ERROR: Batch runner failed for {folder_id}: {exc}")
            results.append(
                {
                    "folder_id": folder_id,
                    "success": False,
                    "returncode": "exception",
                    "company": "Not available",
                    "site": "Not available",
                    "assessment_date": "Not available",
                    "method": "Not available",
                    "assessor": "Not available",
                    "started_at": datetime.now().isoformat(timespec="seconds"),
                }
            )

    print("")
    print("=" * 80)
    print("Batch summary")
    print("=" * 80)

    for item in results:
        status = "SUCCESS" if item["success"] else "FAILED"
        print("")
        print(f"[{status}] {item['folder_id']}")
        print(f"  Company: {item['company']}")
        print(f"  Site: {item['site']}")
        print(f"  Assessment Date: {item['assessment_date']}")
        print(f"  Assessment Method: {item['method']}")
        print(f"  Assessor: {item['assessor']}")
        print(f"  Return code: {item['returncode']}")

    failed = [item for item in results if not item["success"]]

    print("")
    print(f"Completed: {len(results) - len(failed)} successful, {len(failed)} failed, {len(results)} total.")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
