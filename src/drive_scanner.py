import streamlit as st
import argparse
import csv
import json
from pathlib import Path
from typing import Any

from google.oauth2 import service_account
from googleapiclient.discovery import build


DEFAULT_CREDENTIALS_PATH = "credentials/service-account.json"
DEFAULT_ROOT_FOLDER_ID = "1zRTHGXHKpNDB2yqubgfXKqd2r6qO-92_"
DEFAULT_OUTPUT_CSV = "output/drive_scan.csv"


def create_drive_service(credentials_path: str):
    creds = service_account.Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/drive"]
    )
    return build("drive", "v3", credentials=creds)


def list_children(service, folder_id: str) -> list[dict[str, Any]]:
    results = service.files().list(
        q=f"'{folder_id}' in parents and trashed = false",
        fields="files(id, name, mimeType, modifiedTime, webViewLink)",
        orderBy="name",
        supportsAllDrives=True,
        includeItemsFromAllDrives=True,
    ).execute()

    return results.get("files", [])


def list_child_folders(service, folder_id: str) -> list[dict[str, Any]]:
    return [
        item for item in list_children(service, folder_id)
        if item.get("mimeType") == "application/vnd.google-apps.folder"
    ]


def read_json_file(service, file_id: str) -> dict[str, Any]:
    try:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        content = request.execute()
        return json.loads(content.decode("utf-8"))
    except Exception:
        return {}


def summarize_assessment_folder(
    service,
    company_name: str,
    account_name: str,
    folder: dict[str, Any],
) -> dict[str, Any]:
    folder_id = folder["id"]
    files = list_children(service, folder_id)

    names = [file.get("name", "") for file in files]

    report_json = next((f for f in files if f.get("name") == "report.json"), None)
    status_json = next((f for f in files if f.get("name") == "status.json"), None)
    pdf = next((f for f in files if f.get("name") == "vergo_report.pdf"), None)

    has_report_json = report_json is not None
    has_status_json = status_json is not None
    has_pdf = pdf is not None

    has_snapshots = any(
        f.get("name") == "snapshots"
        and f.get("mimeType") == "application/vnd.google-apps.folder"
        for f in files
    )

    has_video = any(
        f.get("mimeType", "").startswith("video/")
        or f.get("name", "").lower().endswith((".mp4", ".mov", ".m4v"))
        for f in files
    )

    status_value = ""
    report_file_id = ""
    pdf_link = ""

    if status_json:
        status_data = read_json_file(service, status_json["id"])
        status_value = str(status_data.get("status", ""))
        report_file_id = str(status_data.get("reportFileId", ""))

    if pdf:
        pdf_link = pdf.get("webViewLink", "")

    is_valid_assessment = has_report_json and has_snapshots

    return {
        "company": company_name,
        "account": account_name,
        "assessment_folder": folder.get("name", ""),
        "folder_id": folder_id,
        "folder_link": folder.get("webViewLink", ""),
        "is_valid_assessment": is_valid_assessment,
        "has_report_json": has_report_json,
        "has_snapshots": has_snapshots,
        "has_video": has_video,
        "has_pdf": has_pdf,
        "has_status_json": has_status_json,
        "status": status_value,
        "report_file_id": report_file_id,
        "pdf_link": pdf_link,
        "modified_time": folder.get("modifiedTime", ""),
        "file_count": len(files),
        "file_names": "; ".join(names),
    }


def scan_drive(
    credentials_path: str,
    root_folder_id: str,
    max_companies: int | None = None,
    max_accounts_per_company: int | None = None,
    max_assessments_per_account: int | None = None,
) -> list[dict[str, Any]]:
    service = create_drive_service(credentials_path)

    rows = []

    company_folders = list_child_folders(service, root_folder_id)

    if max_companies:
        company_folders = company_folders[:max_companies]

    print(f"Found company folders: {len(company_folders)}")

    for company_index, company in enumerate(company_folders, start=1):
        company_name = company.get("name", "")
        print(f"\n[{company_index}/{len(company_folders)}] Company: {company_name}")

        account_folders = list_child_folders(service, company["id"])

        if max_accounts_per_company:
            account_folders = account_folders[:max_accounts_per_company]

        print(f"  Account/user folders: {len(account_folders)}")

        for account_index, account in enumerate(account_folders, start=1):
            account_name = account.get("name", "")
            print(f"  - [{account_index}/{len(account_folders)}] Account: {account_name}")

            assessment_folders = list_child_folders(service, account["id"])

            if max_assessments_per_account:
                assessment_folders = assessment_folders[:max_assessments_per_account]

            print(f"    Assessment folders found: {len(assessment_folders)}")

            for assessment in assessment_folders:
                row = summarize_assessment_folder(
                    service=service,
                    company_name=company_name,
                    account_name=account_name,
                    folder=assessment,
                )
                rows.append(row)

                marker = "VALID" if row["is_valid_assessment"] else "SKIP"
                print(f"    [{marker}] {row['assessment_folder']}")

    return rows


def write_csv(rows: list[dict[str, Any]], output_csv: str) -> None:
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "company",
        "account",
        "assessment_folder",
        "folder_id",
        "folder_link",
        "is_valid_assessment",
        "has_report_json",
        "has_snapshots",
        "has_video",
        "has_pdf",
        "has_status_json",
        "status",
        "report_file_id",
        "pdf_link",
        "modified_time",
        "file_count",
        "file_names",
    ]

    with output_path.open("w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in rows:
            writer.writerow(row)

    print(f"\nDrive scan CSV saved to: {output_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="Scan Vergo processed-video folders in Google Drive.")

    parser.add_argument(
        "--credentials-path",
        default=DEFAULT_CREDENTIALS_PATH,
        help="Path to Google service account credentials.",
    )

    parser.add_argument(
        "--root-folder-id",
        default=DEFAULT_ROOT_FOLDER_ID,
        help="Root Google Drive folder ID for processed-videos.",
    )

    parser.add_argument(
        "--output-csv",
        default=DEFAULT_OUTPUT_CSV,
        help="Output CSV path.",
    )

    parser.add_argument(
        "--max-companies",
        type=int,
        default=0,
        help="Optional limit for faster testing. 0 means no limit.",
    )

    parser.add_argument(
        "--max-accounts-per-company",
        type=int,
        default=0,
        help="Optional limit for faster testing. 0 means no limit.",
    )

    parser.add_argument(
        "--max-assessments-per-account",
        type=int,
        default=0,
        help="Optional limit for faster testing. 0 means no limit.",
    )

    args = parser.parse_args()

    rows = scan_drive(
        credentials_path=args.credentials_path,
        root_folder_id=args.root_folder_id,
        max_companies=args.max_companies or None,
        max_accounts_per_company=args.max_accounts_per_company or None,
        max_assessments_per_account=args.max_assessments_per_account or None,
    )

    write_csv(rows, args.output_csv)

    valid = [row for row in rows if row["is_valid_assessment"]]
    missing_pdf = [row for row in valid if not row["has_pdf"]]
    completed = [row for row in valid if row["status"] == "completed"]

    print("")
    print("Scan summary")
    print(f"Total assessment-like folders scanned: {len(rows)}")
    print(f"Valid assessment folders: {len(valid)}")
    print(f"Valid folders missing PDF: {len(missing_pdf)}")
    print(f"Completed folders: {len(completed)}")


if __name__ == "__main__":
    main()
