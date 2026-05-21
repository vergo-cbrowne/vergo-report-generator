import argparse
import csv
import subprocess
import sys
from pathlib import Path
from datetime import datetime


def parse_folder_ids(raw: str | None) -> list[str]:
    if not raw:
        return []

    cleaned = raw.replace(",", " ").replace("\n", " ")
    return [item.strip() for item in cleaned.split(" ") if item.strip()]


def parse_folders_file(path: str | None) -> list[str]:
    if not path:
        return []

    file_path = Path(path)

    if not file_path.exists():
        raise FileNotFoundError(f"Folders file not found: {path}")

    folder_ids = []

    for line in file_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        # Allow either raw folder IDs or full Google Drive folder URLs.
        if "/folders/" in line:
            line = line.split("/folders/", 1)[1]
            line = line.split("?", 1)[0]
            line = line.split("/", 1)[0]

        folder_ids.append(line)

    return folder_ids


def extract_html_value(label: str) -> str:
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
    print(output)

    success = result.returncode == 0 and "Done." in output

    error_tail = ""
    if not success:
        error_tail = "\n".join(output.splitlines()[-20:])

    company = extract_html_value("Company") if success else "Not available"
    site = extract_html_value("Site / Location") if success else "Not available"
    assessment_date = extract_html_value("Assessment Date") if success else "Not available"
    method = extract_html_value("Assessment Method") if success else "Not available"
    assessor = extract_html_value("Assessor") if success else "Not available"

    weak_values = {"", "Not specified", "Confidential", "Not found", "Not available"}

    weak_metadata_items = []

    if company in weak_values:
        weak_metadata_items.append("company")

    if site in weak_values:
        weak_metadata_items.append("site")

    if assessment_date in weak_values:
        weak_metadata_items.append("assessment_date")

    if method in weak_values:
        weak_metadata_items.append("method")

    if assessor in weak_values:
        weak_metadata_items.append("assessor")

    return {
        "folder_id": folder_id,
        "success": success,
        "returncode": result.returncode,
        "company": company,
        "site": site,
        "assessment_date": assessment_date,
        "method": method,
        "assessor": assessor,
        "weak_metadata": ";".join(weak_metadata_items),
        "started_at": started_at,
        "error_tail": error_tail,
    }


def write_summary_csv(results: list[dict], output_path: str) -> None:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "folder_id",
        "success",
        "returncode",
        "company",
        "site",
        "assessment_date",
        "method",
        "assessor",
        "weak_metadata",
        "started_at",
        "error_tail",
    ]

    with path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fields)
        writer.writeheader()

        for result in results:
            writer.writerow({field: result.get(field, "") for field in fields})

    print(f"\nBatch summary CSV saved to: {path.resolve()}")


def main():
    parser = argparse.ArgumentParser(
        description="Batch-generate Vergo PDF reports from Google Drive assessment folders."
    )

    parser.add_argument(
        "--folder-ids",
        default="",
        help="Comma, space, or newline separated Google Drive assessment folder IDs.",
    )

    parser.add_argument(
        "--folders-file",
        default="",
        help="Text file with one Google Drive assessment folder ID or folder URL per line.",
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

    parser.add_argument(
        "--summary-csv",
        default="output/batch_summary.csv",
        help="Path for the batch summary CSV.",
    )

    args = parser.parse_args()

    folder_ids = []
    folder_ids.extend(parse_folder_ids(args.folder_ids))
    folder_ids.extend(parse_folders_file(args.folders_file))

    # Deduplicate while preserving order.
    seen = set()
    unique_folder_ids = []

    for folder_id in folder_ids:
        if folder_id not in seen:
            unique_folder_ids.append(folder_id)
            seen.add(folder_id)

    folder_ids = unique_folder_ids

    if not folder_ids:
        raise SystemExit("No folder IDs provided. Use --folder-ids or --folders-file.")

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
                    "error_tail": str(exc),
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
        print(f"  Weak Metadata: {item.get('weak_metadata', '') or 'None'}")
        print(f"  Return code: {item['returncode']}")

    failed = [item for item in results if not item["success"]]
    weak = [item for item in results if item.get("weak_metadata")]

    print("")
    print(f"Completed: {len(results) - len(failed)} successful, {len(failed)} failed, {len(results)} total.")

    if weak:
        print("")
        print("Weak metadata review list:")
        for item in weak:
            print(f"- {item['folder_id']}: {item.get('weak_metadata')}")

    write_summary_csv(results, args.summary_csv)

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
