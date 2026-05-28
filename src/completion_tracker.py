from __future__ import annotations

import base64
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st
from googleapiclient.http import MediaIoBaseDownload

import drive_scanner


HISTORICAL_COUNTS_PATH = Path("data/historical_report_counts.json")
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
MAX_RECURSION_DEPTH = 5


def _image_to_base64(path: str) -> str:
    file_path = Path(path)
    if not file_path.exists():
        return ""
    return base64.b64encode(file_path.read_bytes()).decode("utf-8")



def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _clean_text(value: Any) -> str:
    text = _safe_str(value)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_bad_metadata_value(value: Any) -> bool:
    text = _clean_text(value).lower()
    return text in {
        "",
        "unknown",
        "none",
        "n/a",
        "na",
        "not specified",
        "confidential",
        "client",
        "company",
        "task",
        "assessment",
        "null",
        "undefined",
    }


def _normalise_client_name(value: Any) -> str:
    text = _clean_text(value)
    if _is_bad_metadata_value(text):
        return "Unknown Client"
    return text


def _normalise_task_name(value: Any) -> str:
    text = _clean_text(value)
    if _is_bad_metadata_value(text):
        return "Unknown Assessment"
    return text


def _parse_date(value: Any) -> str:
    text = _safe_str(value)
    if not text:
        return ""

    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return text[:10] if len(text) >= 10 else text


def _parse_sortable_date(value: Any) -> pd.Timestamp:
    parsed = pd.to_datetime(_safe_str(value), errors="coerce", utc=True)
    if pd.isna(parsed):
        return pd.NaT
    return parsed


def _deep_find_value(data: Any, keys: List[str]) -> Optional[str]:
    """
    Recursively search a JSON-like object for the first useful value matching
    any of the supplied keys. This keeps the tracker resilient to changing
    report.json/OpenAI output structures.
    """
    wanted = {key.lower() for key in keys}

    if isinstance(data, dict):
        for key, value in data.items():
            if str(key).lower() in wanted:
                if isinstance(value, (str, int, float)):
                    text = _clean_text(value)
                    if not _is_bad_metadata_value(text):
                        return text

                if isinstance(value, dict):
                    # Handle structures like cover_details: {client: "..."}
                    nested = _deep_find_value(value, keys)
                    if nested:
                        return nested

        for value in data.values():
            nested = _deep_find_value(value, keys)
            if nested:
                return nested

    if isinstance(data, list):
        for item in data:
            nested = _deep_find_value(item, keys)
            if nested:
                return nested

    return None


def _extract_client_from_cover_details(report_json: Dict[str, Any]) -> Optional[str]:
    cover_details = None

    if isinstance(report_json, dict):
        cover_details = (
            report_json.get("cover_details")
            or report_json.get("coverDetails")
            or report_json.get("metadata", {}).get("cover_details")
            or report_json.get("metadata", {}).get("coverDetails")
        )

    if not isinstance(cover_details, dict):
        return None

    value = _deep_find_value(
        cover_details,
        [
            "client",
            "client_name",
            "company",
            "company_name",
            "organization",
            "site",
        ],
    )

    if value and _normalise_client_name(value) != "Unknown Client":
        return _normalise_client_name(value)

    return None


def _extract_client_from_json(
    report_json: Dict[str, Any],
    status_json: Dict[str, Any],
) -> Optional[str]:
    candidates = [
        _extract_client_from_cover_details(report_json),
        _deep_find_value(
            report_json,
            [
                "client",
                "client_name",
                "company",
                "company_name",
                "organization",
                "customer",
                "site_company",
            ],
        ),
        _deep_find_value(
            status_json,
            [
                "client",
                "client_name",
                "company",
                "company_name",
                "organization",
                "customer",
            ],
        ),
    ]

    for candidate in candidates:
        client = _normalise_client_name(candidate)
        if client != "Unknown Client":
            return client

    return None


def _extract_task_from_json(
    report_json: Dict[str, Any],
    status_json: Dict[str, Any],
) -> Optional[str]:
    candidates = [
        _deep_find_value(
            report_json,
            [
                "task_name",
                "task_title",
                "task",
                "assessment_name",
                "assessment",
                "video_name",
                "movement_task",
                "title",
            ],
        ),
        _deep_find_value(
            status_json,
            [
                "task_name",
                "task_title",
                "task",
                "assessment_name",
                "assessment",
                "video_name",
                "title",
            ],
        ),
    ]

    for candidate in candidates:
        task = _normalise_task_name(candidate)
        if task != "Unknown Assessment":
            return task

    return None


def _extract_client_from_folder_name(folder_name: Any) -> str:
    """
    Fallback examples:
    - Cameco_Vergo_3 - b5ee8 -> Cameco
    - Oxford_Frozen_Foods_Vergo_12 -> Oxford Frozen Foods
    - Client Name - abc123 -> Client Name
    """
    name = _clean_text(folder_name)
    if not name:
        return "Unknown Client"

    name = re.sub(r"\s+-\s+[A-Za-z0-9_-]{4,}$", "", name).strip()
    name = re.sub(r"_?Vergo_?\d*.*$", "", name, flags=re.IGNORECASE).strip()
    name = name.replace("_", " ").strip()

    return _normalise_client_name(name)


def _extract_task_from_folder_name(folder_name: Any) -> str:
    name = _clean_text(folder_name)
    if not name:
        return "Unknown Assessment"

    name = re.sub(r"\s+-\s+[A-Za-z0-9_-]{4,}$", "", name).strip()
    name = name.replace("_", " ").strip()

    return _normalise_task_name(name)


def _list_children(service: Any, folder_id: str) -> List[Dict[str, Any]]:
    children: List[Dict[str, Any]] = []
    page_token = None

    while True:
        response = (
            service.files()
            .list(
                q=f"'{folder_id}' in parents and trashed = false",
                spaces="drive",
                fields=(
                    "nextPageToken, files("
                    "id, name, mimeType, modifiedTime, createdTime, webViewLink"
                    ")"
                ),
                pageToken=page_token,
                supportsAllDrives=True,
                includeItemsFromAllDrives=True,
                orderBy="name",
            )
            .execute()
        )

        children.extend(response.get("files", []))
        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return children


def _download_json_file(service: Any, file_id: str) -> Dict[str, Any]:
    try:
        request = service.files().get_media(fileId=file_id, supportsAllDrives=True)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        buffer.seek(0)
        raw_text = buffer.read().decode("utf-8", errors="replace")
        parsed = json.loads(raw_text)

        return parsed if isinstance(parsed, dict) else {}

    except Exception:
        return {}


def _is_pdf_report(file_item: Dict[str, Any]) -> bool:
    name = _safe_str(file_item.get("name"))
    mime_type = _safe_str(file_item.get("mimeType")).lower()

    is_pdf = name.lower().endswith(".pdf") or mime_type == "application/pdf"
    if not is_pdf:
        return False

    lower_name = name.lower()

    if lower_name.endswith("_vergo_report.pdf"):
        return True

    if lower_name == "vergo_report.pdf":
        return True

    if "vergo" in lower_name and "report" in lower_name:
        return True

    if "movement" in lower_name and "analysis" in lower_name and "report" in lower_name:
        return True

    return False


def _status_is_completed(status_json: Dict[str, Any]) -> bool:
    return _safe_str(status_json.get("status")).lower() == "completed"


def _find_named_file(files: List[Dict[str, Any]], filename: str) -> Optional[Dict[str, Any]]:
    target = filename.lower()
    return next((file for file in files if _safe_str(file.get("name")).lower() == target), None)


def _completion_date(
    status_json: Dict[str, Any],
    report_file: Optional[Dict[str, Any]],
    folder_item: Dict[str, Any],
) -> str:
    for key in ["uploadedAt", "completedAt", "updatedAt", "createdAt"]:
        value = status_json.get(key)
        if value:
            return _parse_date(value)

    if report_file and report_file.get("modifiedTime"):
        return _parse_date(report_file.get("modifiedTime"))

    if folder_item.get("modifiedTime"):
        return _parse_date(folder_item.get("modifiedTime"))

    return ""


def _scan_folder_tree(
    service: Any,
    root_folder_id: str,
    max_depth: int = MAX_RECURSION_DEPTH,
) -> List[Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]]:
    """
    Returns:
    - folder item
    - ancestor folder items
    - immediate children

    This scans flexibly because the processed Drive structure may vary.
    """
    root_item = {
        "id": root_folder_id,
        "name": "Processed Videos Root",
        "mimeType": GOOGLE_FOLDER_MIME,
        "modifiedTime": "",
        "createdTime": "",
        "webViewLink": "",
    }

    scanned: List[Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]] = []
    queue: List[Tuple[Dict[str, Any], List[Dict[str, Any]], int]] = [(root_item, [], 0)]

    while queue:
        folder_item, ancestors, depth = queue.pop(0)

        try:
            children = _list_children(service, folder_item["id"])
        except Exception:
            continue

        scanned.append((folder_item, ancestors, children))

        if depth >= max_depth:
            continue

        for child in children:
            if child.get("mimeType") == GOOGLE_FOLDER_MIME:
                queue.append((child, ancestors + [folder_item], depth + 1))

    return scanned


def scan_current_completed_reports(
    credentials_path: str,
    root_folder_id: str,
) -> List[Dict[str, Any]]:
    service = drive_scanner.create_drive_service(credentials_path)

    reports: List[Dict[str, Any]] = []
    scanned_folders = _scan_folder_tree(service, root_folder_id)

    for folder_item, ancestors, children in scanned_folders:
        files = [item for item in children if item.get("mimeType") != GOOGLE_FOLDER_MIME]

        status_file = _find_named_file(files, "status.json")
        report_json_file = _find_named_file(files, "report.json")

        status_json = _download_json_file(service, status_file["id"]) if status_file else {}
        report_json = _download_json_file(service, report_json_file["id"]) if report_json_file else {}

        pdf_reports = [file for file in files if _is_pdf_report(file)]
        primary_pdf = pdf_reports[0] if pdf_reports else None

        evidence: List[str] = []

        if status_file and _status_is_completed(status_json):
            evidence.append("status.json completed")

        if primary_pdf:
            pdf_name = _safe_str(primary_pdf.get("name"))
            lower_pdf_name = pdf_name.lower()

            if lower_pdf_name.endswith("_vergo_report.pdf"):
                evidence.append("*_Vergo_Report.pdf")
            elif lower_pdf_name == "vergo_report.pdf":
                evidence.append("vergo_report.pdf")
            else:
                evidence.append("Vergo report PDF")

        if not evidence:
            continue

        client = _extract_client_from_json(report_json, status_json)
        task = _extract_task_from_json(report_json, status_json)

        folder_name = folder_item.get("name", "")
        usable_ancestors = [
            ancestor
            for ancestor in ancestors
            if _safe_str(ancestor.get("name")) not in {"", "Processed Videos Root"}
        ]

        parent_name = usable_ancestors[-1].get("name", "") if usable_ancestors else ""
        grandparent_name = usable_ancestors[-2].get("name", "") if len(usable_ancestors) >= 2 else ""

        if not client:
            # Prefer company-level folder if present, then parent, then assessment folder.
            client = _extract_client_from_folder_name(grandparent_name or parent_name or folder_name)

        if not task:
            task = _extract_task_from_folder_name(folder_name)

        reports.append(
            {
                "Client": _normalise_client_name(client),
                "Task / Assessment": _normalise_task_name(task),
                "Completion Evidence": ", ".join(evidence),
                "Completion Date": _completion_date(status_json, primary_pdf, folder_item),
                "Report File Name": primary_pdf.get("name", "") if primary_pdf else "",
                "Folder ID": folder_item.get("id", ""),
            }
        )

    seen_folder_ids = set()
    unique_reports: List[Dict[str, Any]] = []

    for report in reports:
        folder_id = report.get("Folder ID", "")
        if folder_id in seen_folder_ids:
            continue
        seen_folder_ids.add(folder_id)
        unique_reports.append(report)

    unique_reports.sort(
        key=lambda row: (
            row.get("Client", ""),
            row.get("Completion Date", ""),
            row.get("Task / Assessment", ""),
        )
    )

    return unique_reports


@st.cache_data(ttl=300, show_spinner=False)
def cached_scan_current_completed_reports(
    credentials_path: str,
    root_folder_id: str,
    refresh_token: int,
) -> List[Dict[str, Any]]:
    return scan_current_completed_reports(
        credentials_path=credentials_path,
        root_folder_id=root_folder_id,
    )


def load_historical_counts() -> List[Dict[str, Any]]:
    if not HISTORICAL_COUNTS_PATH.exists():
        return []

    try:
        payload = json.loads(HISTORICAL_COUNTS_PATH.read_text(encoding="utf-8"))

        if isinstance(payload, dict) and isinstance(payload.get("clients"), list):
            return payload["clients"]

        if isinstance(payload, list):
            return payload

    except Exception:
        return []

    return []


def save_historical_counts(rows: List[Dict[str, Any]]) -> None:
    HISTORICAL_COUNTS_PATH.parent.mkdir(parents=True, exist_ok=True)

    cleaned: List[Dict[str, Any]] = []

    for row in rows:
        client = _normalise_client_name(row.get("Client", ""))
        if client == "Unknown Client":
            continue

        try:
            historical_count = int(row.get("Historical Word Reports Completed", 0) or 0)
        except Exception:
            historical_count = 0

        historical_count = max(historical_count, 0)
        notes = _clean_text(row.get("Notes", ""))

        cleaned.append(
            {
                "Client": client,
                "Historical Word Reports Completed": historical_count,
                "Notes": notes,
            }
        )

    cleaned.sort(key=lambda item: item["Client"].lower())

    payload = {
        "version": 1,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
        "clients": cleaned,
    }

    HISTORICAL_COUNTS_PATH.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def build_historical_table_seed(current_reports: List[Dict[str, Any]]) -> pd.DataFrame:
    saved_rows = load_historical_counts()

    by_client: Dict[str, Dict[str, Any]] = {}

    for row in saved_rows:
        client = _normalise_client_name(row.get("Client", ""))
        if client == "Unknown Client":
            continue

        try:
            count = int(row.get("Historical Word Reports Completed", 0) or 0)
        except Exception:
            count = 0

        by_client[client] = {
            "Client": client,
            "Historical Word Reports Completed": max(count, 0),
            "Notes": _clean_text(row.get("Notes", "")),
        }

    current_clients = sorted(
        {
            _normalise_client_name(report.get("Client", ""))
            for report in current_reports
            if _normalise_client_name(report.get("Client", "")) != "Unknown Client"
        }
    )

    for client in current_clients:
        by_client.setdefault(
            client,
            {
                "Client": client,
                "Historical Word Reports Completed": 0,
                "Notes": "",
            },
        )

    rows = sorted(by_client.values(), key=lambda item: item["Client"].lower())

    return pd.DataFrame(
        rows,
        columns=["Client", "Historical Word Reports Completed", "Notes"],
    )


def build_summary_table(
    current_reports: List[Dict[str, Any]],
    historical_rows: List[Dict[str, Any]],
) -> pd.DataFrame:
    current_df = pd.DataFrame(current_reports)

    if current_df.empty:
        current_summary = pd.DataFrame(
            columns=[
                "Client",
                "Current PDF Reports",
                "Most Recent Current Report Date",
                "Last Current Report Task",
            ]
        )
    else:
        current_df = current_df.copy()
        current_df["Completion Date Sort"] = current_df["Completion Date"].apply(_parse_sortable_date)

        counts = (
            current_df.groupby("Client", dropna=False)
            .size()
            .reset_index(name="Current PDF Reports")
        )

        most_recent = (
            current_df.sort_values(
                ["Client", "Completion Date Sort"],
                ascending=[True, False],
            )
            .groupby("Client", as_index=False)
            .first()
        )

        current_summary = counts.merge(
            most_recent[
                [
                    "Client",
                    "Completion Date",
                    "Task / Assessment",
                ]
            ],
            on="Client",
            how="left",
        ).rename(
            columns={
                "Completion Date": "Most Recent Current Report Date",
                "Task / Assessment": "Last Current Report Task",
            }
        )

    historical_df = pd.DataFrame(historical_rows)

    if historical_df.empty:
        historical_df = pd.DataFrame(
            columns=["Client", "Historical Word Reports Completed", "Notes"]
        )

    for column in ["Client", "Historical Word Reports Completed"]:
        if column not in historical_df.columns:
            historical_df[column] = "" if column == "Client" else 0

    historical_df = historical_df.copy()
    historical_df["Client"] = historical_df["Client"].apply(_normalise_client_name)
    historical_df = historical_df[historical_df["Client"] != "Unknown Client"]

    historical_df["Historical Word Reports Completed"] = pd.to_numeric(
        historical_df["Historical Word Reports Completed"],
        errors="coerce",
    ).fillna(0).astype(int)

    historical_summary = (
        historical_df.groupby("Client", as_index=False)["Historical Word Reports Completed"]
        .sum()
        .rename(columns={"Historical Word Reports Completed": "Historical Word Reports"})
    )

    all_clients = sorted(
        set(current_summary["Client"].dropna().tolist())
        | set(historical_summary["Client"].dropna().tolist())
    )

    summary = pd.DataFrame({"Client": all_clients})

    summary = summary.merge(current_summary, on="Client", how="left")
    summary = summary.merge(historical_summary, on="Client", how="left")

    summary["Current PDF Reports"] = summary["Current PDF Reports"].fillna(0).astype(int)
    summary["Historical Word Reports"] = summary["Historical Word Reports"].fillna(0).astype(int)
    summary["Total Completed Reports"] = (
        summary["Current PDF Reports"] + summary["Historical Word Reports"]
    )

    summary["Most Recent Current Report Date"] = summary["Most Recent Current Report Date"].fillna("")
    summary["Last Current Report Task"] = summary["Last Current Report Task"].fillna("")

    summary = summary[
        [
            "Client",
            "Current PDF Reports",
            "Historical Word Reports",
            "Total Completed Reports",
            "Most Recent Current Report Date",
            "Last Current Report Task",
        ]
    ]

    return summary.sort_values(
        ["Total Completed Reports", "Client"],
        ascending=[False, True],
    ).reset_index(drop=True)


def build_tracker_metrics(summary_df: pd.DataFrame) -> Dict[str, Any]:
    if summary_df.empty:
        return {
            "total_clients": 0,
            "current_pdf_reports": 0,
            "historical_word_reports": 0,
            "total_completed_reports": 0,
            "most_recent_current_report": "—",
        }

    most_recent_dates = pd.to_datetime(
        summary_df["Most Recent Current Report Date"],
        errors="coerce",
    )

    most_recent = "—"
    if not most_recent_dates.dropna().empty:
        most_recent = most_recent_dates.max().strftime("%Y-%m-%d")

    return {
        "total_clients": int(len(summary_df)),
        "current_pdf_reports": int(summary_df["Current PDF Reports"].sum()),
        "historical_word_reports": int(summary_df["Historical Word Reports"].sum()),
        "total_completed_reports": int(summary_df["Total Completed Reports"].sum()),
        "most_recent_current_report": most_recent,
    }


def _csv_bytes(df: pd.DataFrame) -> bytes:
    return df.to_csv(index=False).encode("utf-8")


def _metric_card(label: str, value: Any, accent: bool = False) -> str:
    accent_class = " metric-accent" if accent else ""
    return f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value{accent_class}">{value}</div>
    </div>
    """


def _apply_tracker_styles() -> None:
    st.markdown(
        """
        <style>
        .tracker-note {
            padding: 0.85rem 1rem;
            border-radius: 16px;
            border: 1px solid rgba(255, 255, 255, 0.12);
            background: #06080c;
            color: rgba(255, 255, 255, 0.76);
            margin: 0.2rem 0 1rem 0;
        }

        .tracker-section {
            padding: 1rem 0;
            border-top: 1px solid rgba(255, 255, 255, 0.14);
            border-bottom: 1px solid rgba(255, 255, 255, 0.08);
            background: transparent;
            margin: 1.25rem 0 0.95rem 0;
            box-shadow: none;
        }

        .tracker-section-title {
            font-size: 1rem;
            font-weight: 750;
            color: #ffffff;
            margin-bottom: 0.3rem;
            letter-spacing: 0.01em;
            text-transform: uppercase;
        }

        .tracker-section-copy {
            color: rgba(255, 255, 255, 0.64);
            font-size: 0.92rem;
            line-height: 1.55;
        }

        
        .print-report {
            background: #ffffff;
            color: #050505;
            border-radius: 18px;
            padding: 28px 30px;
            border: 1px solid #e5e7eb;
            font-family: "Space Grotesk", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }

        .print-report-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 1px solid #d9dde5;
            padding-bottom: 18px;
            margin-bottom: 22px;
        }

        .print-logo {
            color: #0f4a7c;
            font-size: 28px;
            font-weight: 800;
            letter-spacing: -0.04em;
        }

        .print-logo-img {
            width: 118px;
            height: auto;
            display: block;
        }

        .print-kicker {
            margin-top: 8px;
            color: #5f6b7a;
            font-size: 10px;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 700;
        }

        .print-date {
            color: #5f6b7a;
            font-size: 12px;
            text-align: right;
        }

        .print-report-title {
            font-family: "Helvetica Neue", Helvetica, Arial, sans-serif;
            font-size: 38px;
            line-height: 1.05;
            font-weight: 300;
            letter-spacing: -0.055em;
            color: #050505;
            margin-bottom: 8px;
        }

        .print-report-subtitle {
            color: #334155;
            font-size: 13px;
            margin-bottom: 22px;
        }

        .print-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin: 18px 0 24px 0;
        }

        .print-metric {
            border: 1px solid #d9dde5;
            border-radius: 12px;
            padding: 12px;
            background: #f8fafc;
        }

        .print-metric-label {
            color: #64748b;
            font-size: 9px;
            letter-spacing: 0.12em;
            text-transform: uppercase;
            font-weight: 700;
            margin-bottom: 8px;
        }

        .print-metric-value {
            color: #050505;
            font-size: 24px;
            font-weight: 500;
        }

        .print-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11px;
            margin-top: 10px;
        }

        .print-table th {
            background: #f1f5f9;
            color: #334155;
            text-align: left;
            padding: 9px 8px;
            border: 1px solid #d9dde5;
            font-size: 9px;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }

        .print-table td {
            color: #0f172a;
            padding: 9px 8px;
            border: 1px solid #e2e8f0;
            vertical-align: top;
        }

        .print-table .num {
            text-align: right;
            font-variant-numeric: tabular-nums;
        }

        .print-table .total {
            font-weight: 800;
        }

        .print-empty {
            text-align: center;
            color: #64748b;
            padding: 18px;
        }

        .print-footer {
            margin-top: 24px;
            border-top: 1px solid #d9dde5;
            padding-top: 12px;
            text-align: right;
            color: #0f4a7c;
            font-weight: 800;
            font-size: 12px;
        }

        @media print {
            header, footer, [data-testid="stSidebar"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
                display: none !important;
            }

            .block-container {
                padding: 0 !important;
                max-width: 100% !important;
            }

            .print-report {
                border: none !important;
                border-radius: 0 !important;
                padding: 0 !important;
                width: 100% !important;
            }

            .print-metrics {
                grid-template-columns: repeat(4, minmax(0, 1fr));
            }
        }
        </style>

        """,
        unsafe_allow_html=True,
    )



def render_print_friendly_view(summary_df: pd.DataFrame, metrics: Dict[str, Any]) -> None:
    generated = datetime.now().strftime("%Y-%m-%d")

    logo_b64 = _image_to_base64("assets/vergo-logo.png")
    if logo_b64:
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" class="print-logo-img" alt="Vergo" />'
    else:
        logo_html = '<div class="print-logo">Vergo</div>'

    if summary_df.empty:
        rows_html = """
            <tr>
                <td colspan="6" class="print-empty">No completed reports found.</td>
            </tr>
        """
    else:
        rows = []
        for _, row in summary_df.iterrows():
            rows.append(
                f"""
                <tr>
                    <td>{_clean_text(row.get("Client", ""))}</td>
                    <td class="num">{int(row.get("Current PDF Reports", 0) or 0)}</td>
                    <td class="num">{int(row.get("Historical Word Reports", 0) or 0)}</td>
                    <td class="num total">{int(row.get("Total Completed Reports", 0) or 0)}</td>
                    <td>{_clean_text(row.get("Most Recent Current Report Date", ""))}</td>
                    <td>{_clean_text(row.get("Last Current Report Task", ""))}</td>
                </tr>
                """
            )
        rows_html = "\n".join(rows)

    html = f"""
    <div class="print-report">
        <div class="print-report-header">
            <div>
                {logo_html}
                <div class="print-kicker">Client Reporting</div>
            </div>
            <div class="print-date">Date generated: {generated}</div>
        </div>

        <div class="print-report-title">Client Completion Tracker</div>
        <div class="print-report-subtitle">
            Summary of completed movement analysis reports by client.
        </div>

        <div class="print-metrics">
            <div class="print-metric">
                <div class="print-metric-label">Total Clients</div>
                <div class="print-metric-value">{metrics["total_clients"]}</div>
            </div>
            <div class="print-metric">
                <div class="print-metric-label">Current PDF Reports</div>
                <div class="print-metric-value">{metrics["current_pdf_reports"]}</div>
            </div>
            <div class="print-metric">
                <div class="print-metric-label">Historical Word Reports</div>
                <div class="print-metric-value">{metrics["historical_word_reports"]}</div>
            </div>
            <div class="print-metric">
                <div class="print-metric-label">Total Completed Reports</div>
                <div class="print-metric-value">{metrics["total_completed_reports"]}</div>
            </div>
        </div>

        <table class="print-table">
            <thead>
                <tr>
                    <th>Client</th>
                    <th>Current PDF Reports</th>
                    <th>Historical Word Reports</th>
                    <th>Total Completed Reports</th>
                    <th>Most Recent Current Report Date</th>
                    <th>Last Current Report Task</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="print-footer">
            <span>www.vergo.ai</span>
        </div>
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)




# === VERGO QUALITY REVIEW HELPERS ===

def _deep_text_blob(data: Any) -> str:
    parts: List[str] = []

    def walk(value: Any) -> None:
        if value is None:
            return

        if isinstance(value, dict):
            for key, item in value.items():
                parts.append(str(key))
                walk(item)
            return

        if isinstance(value, list):
            for item in value:
                walk(item)
            return

        parts.append(str(value))

    walk(data)
    return " ".join(parts).lower()


def _yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def _has_video_file(files: List[Dict[str, Any]]) -> bool:
    for file in files:
        name = _safe_str(file.get("name")).lower()
        mime_type = _safe_str(file.get("mimeType")).lower()

        if mime_type.startswith("video/"):
            return True

        if name.endswith((".mp4", ".mov", ".m4v", ".avi", ".mpeg", ".mpg", ".webm")):
            return True

    return False


def _has_snapshots_folder(children: List[Dict[str, Any]]) -> bool:
    return any(
        _safe_str(item.get("name")).lower() == "snapshots"
        and item.get("mimeType") == GOOGLE_FOLDER_MIME
        for item in children
    )


def _has_task_notes_or_context(files: List[Dict[str, Any]]) -> bool:
    note_patterns = [
        "task_context",
        "task context",
        "task_notes",
        "task notes",
        "task_information",
        "task information",
        "assessment_context",
        "assessment context",
        "notes",
    ]

    for file in files:
        name = _safe_str(file.get("name")).lower()
        if any(pattern in name for pattern in note_patterns):
            if name.endswith((".txt", ".md", ".doc", ".docx", ".pdf")):
                return True

    return False


def _unexpected_file_names(files: List[Dict[str, Any]], child_folders: List[Dict[str, Any]]) -> List[str]:
    unexpected: List[str] = []

    expected_exact = {
        "report.json",
        "status.json",
        "task_context.txt",
        "task_notes.txt",
        "notes.txt",
        ".ds_store",
    }

    expected_folder_names = {
        "snapshots",
    }

    for folder in child_folders:
        folder_name = _safe_str(folder.get("name")).lower()
        if folder_name not in expected_folder_names:
            unexpected.append(folder.get("name", ""))

    for file in files:
        name = _safe_str(file.get("name"))
        lower = name.lower()
        mime_type = _safe_str(file.get("mimeType")).lower()

        is_expected = (
            lower in expected_exact
            or lower.endswith((".mp4", ".mov", ".m4v", ".avi", ".mpeg", ".mpg", ".webm"))
            or lower.endswith((".txt", ".md", ".doc", ".docx", ".csv"))
            or _is_pdf_report(file)
            or mime_type.startswith("video/")
        )

        if not is_expected:
            unexpected.append(name)

    return [item for item in unexpected if item]


def _has_reba_rula_scores(report_json: Dict[str, Any]) -> bool:
    blob = _deep_text_blob(report_json)
    return "reba" in blob and "rula" in blob


def _has_section_2_scoring_summary(report_json: Dict[str, Any]) -> bool:
    blob = _deep_text_blob(report_json)
    return (
        "section 2" in blob
        or "scoring summary" in blob
        or "score distribution" in blob
        or "reba" in blob and "rula" in blob and "risk band" in blob
    )


def _has_section_3_movement_analysis(report_json: Dict[str, Any]) -> bool:
    blob = _deep_text_blob(report_json)
    return (
        "section 3" in blob
        or "movement analysis" in blob
        or "movement pattern" in blob
        or "posture" in blob and "movement" in blob
    )


def _has_section_5_recommendations(report_json: Dict[str, Any]) -> bool:
    blob = _deep_text_blob(report_json)
    return (
        "section 5" in blob
        or "recommendation" in blob
        or "recommendations" in blob
        or "control measure" in blob
    )


def _extract_assessment_date_for_quality(
    report_json: Dict[str, Any],
    status_json: Dict[str, Any],
    report_file: Optional[Dict[str, Any]],
    folder_item: Dict[str, Any],
) -> str:
    candidate = _deep_find_value(
        report_json,
        [
            "assessment_date",
            "assessment date",
            "date",
            "date_assessed",
            "date assessed",
            "completed_at",
            "completedAt",
        ],
    )

    if candidate:
        return _parse_date(candidate)

    return _completion_date(status_json, report_file, folder_item)


def _is_candidate_assessment_folder(
    files: List[Dict[str, Any]],
    child_folders: List[Dict[str, Any]],
) -> bool:
    has_report_json = any(_safe_str(f.get("name")).lower() == "report.json" for f in files)
    has_status_json = any(_safe_str(f.get("name")).lower() == "status.json" for f in files)
    has_pdf = any(_is_pdf_report(f) for f in files)
    has_video = _has_video_file(files)
    has_snapshots = _has_snapshots_folder(child_folders)

    return has_report_json or has_status_json or has_pdf or has_video or has_snapshots


def scan_quality_review(
    credentials_path: str,
    root_folder_id: str,
) -> List[Dict[str, Any]]:
    service = drive_scanner.create_drive_service(credentials_path)
    scanned_folders = _scan_folder_tree(service, root_folder_id)

    rows: List[Dict[str, Any]] = []

    for folder_item, ancestors, children in scanned_folders:
        files = [item for item in children if item.get("mimeType") != GOOGLE_FOLDER_MIME]
        child_folders = [item for item in children if item.get("mimeType") == GOOGLE_FOLDER_MIME]

        if not _is_candidate_assessment_folder(files, child_folders):
            continue

        folder_name = folder_item.get("name", "")
        folder_id = folder_item.get("id", "")

        report_json_file = _find_named_file(files, "report.json")
        status_file = _find_named_file(files, "status.json")
        pdf_reports = [file for file in files if _is_pdf_report(file)]
        primary_pdf = pdf_reports[0] if pdf_reports else None

        report_json = _download_json_file(service, report_json_file["id"]) if report_json_file else {}
        status_json = _download_json_file(service, status_file["id"]) if status_file else {}

        usable_ancestors = [
            ancestor
            for ancestor in ancestors
            if _safe_str(ancestor.get("name")) not in {"", "Processed Videos Root"}
        ]

        parent_name = usable_ancestors[-1].get("name", "") if usable_ancestors else ""
        grandparent_name = usable_ancestors[-2].get("name", "") if len(usable_ancestors) >= 2 else ""

        client = _extract_client_from_json(report_json, status_json)
        if not client:
            client = _extract_client_from_folder_name(grandparent_name or parent_name or folder_name)

        task = _extract_task_from_json(report_json, status_json)
        if not task:
            task = _extract_task_from_folder_name(folder_name)

        assessment_date = _extract_assessment_date_for_quality(
            report_json=report_json,
            status_json=status_json,
            report_file=primary_pdf,
            folder_item=folder_item,
        )

        has_pdf = len(pdf_reports) > 0
        has_client = _normalise_client_name(client) != "Unknown Client"
        has_task = _normalise_task_name(task) != "Unknown Assessment"
        has_assessment_date = bool(_safe_str(assessment_date))
        has_report_json = report_json_file is not None
        has_status_json = status_file is not None
        has_snapshots = _has_snapshots_folder(child_folders)
        has_video = _has_video_file(files)
        has_task_notes = _has_task_notes_or_context(files)
        has_client_profile = bool(status_json.get("hasClientProfile")) or any(
            _safe_str(file.get("name")).lower()
            in {"client_profile.md", "client_profile.txt", "company_profile.md", "company_profile.txt"}
            for file in files
        )
        client_profile_file = _safe_str(status_json.get("clientProfileFile"))
        has_reba_rula = _has_reba_rula_scores(report_json)
        has_section_2 = _has_section_2_scoring_summary(report_json)
        has_section_3 = _has_section_3_movement_analysis(report_json)
        has_section_5 = _has_section_5_recommendations(report_json)
        has_footer_page_numbers = has_pdf

        multiple_pdfs = len(pdf_reports) > 1
        unexpected_files = _unexpected_file_names(files, child_folders)

        blocker_flags: List[str] = []
        review_flags: List[str] = []

        if not has_report_json:
            blocker_flags.append("No report.json")

        if not has_snapshots:
            blocker_flags.append("No snapshots folder")

        if not has_video:
            blocker_flags.append("No processed video")

        if not has_status_json:
            review_flags.append("No status.json")

        if not has_task_notes:
            review_flags.append("No task notes/context file")

        if not has_client_profile:
            review_flags.append("No client profile")

        if multiple_pdfs:
            review_flags.append("Multiple PDFs found")

        if unexpected_files:
            review_flags.append("Unexpected file names")

        quality_checks = {
            "Has PDF": has_pdf,
            "Has Client Name": has_client,
            "Has Task Name": has_task,
            "Has Assessment Date": has_assessment_date,
            "Has REBA/RULA Scores": has_reba_rula,
            "Has Section 2 Scoring Summary": has_section_2,
            "Has Section 3 Movement Analysis": has_section_3,
            "Has Section 5 Recommendations": has_section_5,
            "Has Footer/Page Numbers": has_footer_page_numbers,
            "Has Client Profile": has_client_profile,
        }

        for label, passed in quality_checks.items():
            if not passed:
                review_flags.append(label.replace("Has ", "Missing "))

        if blocker_flags:
            quality_status = "Failed"
        elif review_flags:
            quality_status = "Needs Review"
        else:
            quality_status = "Ready"

        rows.append(
            {
                "Status": quality_status,
                "Client": _normalise_client_name(client),
                "Task / Assessment": _normalise_task_name(task),
                "Assessment Date": assessment_date,
                "Folder Name": folder_name,
                "Folder ID": folder_id,
                "Has PDF": _yes_no(has_pdf),
                "Has Client Name": _yes_no(has_client),
                "Has Task Name": _yes_no(has_task),
                "Has Assessment Date": _yes_no(has_assessment_date),
                "Has REBA/RULA Scores": _yes_no(has_reba_rula),
                "Has Section 2 Scoring Summary": _yes_no(has_section_2),
                "Has Section 3 Movement Analysis": _yes_no(has_section_3),
                "Has Section 5 Recommendations": _yes_no(has_section_5),
                "Has Footer/Page Numbers": _yes_no(has_footer_page_numbers),
                "Has Client Profile": _yes_no(has_client_profile),
                "Client Profile File": client_profile_file,
                "No client profile": _yes_no(not has_client_profile),
                "No report.json": _yes_no(not has_report_json),
                "No snapshots folder": _yes_no(not has_snapshots),
                "No processed video": _yes_no(not has_video),
                "No status.json": _yes_no(not has_status_json),
                "No task notes/context file": _yes_no(not has_task_notes),
                "Multiple PDFs found": _yes_no(multiple_pdfs),
                "Unexpected file names": _yes_no(bool(unexpected_files)),
                "Unexpected Files": "; ".join(unexpected_files),
                "Issues": "; ".join(dict.fromkeys(blocker_flags + review_flags)),
            }
        )

    status_order = {"Failed": 0, "Needs Review": 1, "Ready": 2}
    rows.sort(
        key=lambda row: (
            status_order.get(row.get("Status", ""), 9),
            row.get("Client", ""),
            row.get("Task / Assessment", ""),
        )
    )

    return rows


@st.cache_data(ttl=300, show_spinner=False)
def cached_scan_quality_review(
    credentials_path: str,
    root_folder_id: str,
    refresh_token: int,
) -> List[Dict[str, Any]]:
    return scan_quality_review(
        credentials_path=credentials_path,
        root_folder_id=root_folder_id,
    )


def build_quality_metrics(quality_df: pd.DataFrame) -> Dict[str, int]:
    if quality_df.empty or "Status" not in quality_df.columns:
        return {
            "ready": 0,
            "needs_review": 0,
            "failed": 0,
            "total": 0,
        }

    return {
        "ready": int((quality_df["Status"] == "Ready").sum()),
        "needs_review": int((quality_df["Status"] == "Needs Review").sum()),
        "failed": int((quality_df["Status"] == "Failed").sum()),
        "total": int(len(quality_df)),
    }



def render_client_completion_tracker_page(
    credentials_path: str,
    root_folder_id: str,
) -> None:
    _apply_tracker_styles()

    st.markdown(
        """
        <div class="hero-card">
            <div class="hero-kicker">Client Reporting</div>
            <h1 class="hero-title">Client Completion Tracker</h1>
            <div class="hero-subtitle">
                Track completed Vergo movement analysis reports by client, combining current PDF reports from the live workflow with manually entered historical Word report counts.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if not root_folder_id.strip():
        st.warning("Enter the processed videos root folder ID in the sidebar first.")
        return

    if not Path(credentials_path).exists():
        st.error(f"Credentials file not found: {credentials_path}")
        return

    if "completion_tracker_refresh_token" not in st.session_state:
        st.session_state["completion_tracker_refresh_token"] = 0

    try:
        with st.spinner("Scanning current processed videos folder..."):
            current_reports = cached_scan_current_completed_reports(
                credentials_path=credentials_path,
                root_folder_id=root_folder_id,
                refresh_token=st.session_state["completion_tracker_refresh_token"],
            )

            quality_rows = cached_scan_quality_review(
                credentials_path=credentials_path,
                root_folder_id=root_folder_id,
                refresh_token=st.session_state["completion_tracker_refresh_token"],
            )

    except Exception as exc:
        st.error(f"Tracker scan failed: {exc}")
        st.caption(
            "The report generation page was not changed. Check the folder ID, service account access, and Google Drive permissions."
        )
        return

    detailed_df = pd.DataFrame(
        current_reports,
        columns=[
            "Client",
            "Task / Assessment",
            "Completion Evidence",
            "Completion Date",
            "Report File Name",
            "Folder ID",
        ],
    )

    quality_df = pd.DataFrame(quality_rows)

    if quality_df.empty:
        quality_df = pd.DataFrame(
            columns=[
                "Status",
                "Client",
                "Task / Assessment",
                "Assessment Date",
                "Folder Name",
                "Folder ID",
                "Has PDF",
                "Has Client Name",
                "Has Task Name",
                "Has Assessment Date",
                "Has REBA/RULA Scores",
                "Has Section 2 Scoring Summary",
                "Has Section 3 Movement Analysis",
                "Has Section 5 Recommendations",
                "Has Footer/Page Numbers",
                "Has Client Profile",
                "Client Profile File",
                "No client profile",
                "No report.json",
                "No snapshots folder",
                "No processed video",
                "No status.json",
                "No task notes/context file",
                "Multiple PDFs found",
                "Unexpected file names",
                "Unexpected Files",
                "Issues",
            ]
        )

    historical_seed_df = build_historical_table_seed(current_reports)

    saved_historical_rows = historical_seed_df.to_dict(orient="records")
    summary_df = build_summary_table(
        current_reports=current_reports,
        historical_rows=saved_historical_rows,
    )
    metrics = build_tracker_metrics(summary_df)
    quality_metrics = build_quality_metrics(quality_df)

    # ---------------------------------------------------------------------
    # 1. Top-level metrics.
    # ---------------------------------------------------------------------
    st.markdown(
        f"""
        <div class="metric-grid">
            {_metric_card("Total Clients", metrics["total_clients"])}
            {_metric_card("Current PDF Reports", metrics["current_pdf_reports"], accent=True)}
            {_metric_card("Needs Review", quality_metrics["needs_review"])}
            {_metric_card("Failed", quality_metrics["failed"])}
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.caption(
        f"Total completed reports: {metrics['total_completed_reports']} · "
        f"Historical Word reports: {metrics['historical_word_reports']} · "
        f"Most recent current report date: {metrics['most_recent_current_report']}"
    )

    # ---------------------------------------------------------------------
    # 2. Current scan controls.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Current PDF Scan</div>
            <div class="tracker-section-copy">
                Scan the current processed videos folder for completed Vergo PDF reports, folder health issues, and report quality checks.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scan_col, note_col = st.columns([1, 3])

    with scan_col:
        if st.button("Refresh tracker scan"):
            st.session_state["completion_tracker_refresh_token"] += 1
            cached_scan_current_completed_reports.clear()
            cached_scan_quality_review.clear()
            st.rerun()

    with note_col:
        st.markdown(
            """
            <div class="tracker-note">
                Historical Word report folders are not scanned automatically yet. Add older Word-format report counts manually below.
            </div>
            """,
            unsafe_allow_html=True,
        )

    # ---------------------------------------------------------------------
    # 3. Quality review queue.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Quality Review Queue</div>
            <div class="tracker-section-copy">
                Automated quality checks for required report fields, scoring sections, recommendations, and completed PDF evidence.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    status_filter = st.selectbox(
        "Quality status filter",
        ["All", "Failed", "Needs Review", "Ready"],
        index=0,
    )

    filtered_quality_df = quality_df.copy()

    if status_filter != "All" and not filtered_quality_df.empty:
        filtered_quality_df = filtered_quality_df[filtered_quality_df["Status"] == status_filter]

    review_display_columns = [
        "Status",
        "Client",
        "Task / Assessment",
        "Assessment Date",
        "Has PDF",
        "Has Client Name",
        "Has Task Name",
        "Has Assessment Date",
        "Has REBA/RULA Scores",
        "Has Section 2 Scoring Summary",
        "Has Section 3 Movement Analysis",
        "Has Section 5 Recommendations",
        "Has Footer/Page Numbers",
        "Has Client Profile",
        "Client Profile File",
        "Issues",
        "Folder ID",
    ]

    st.dataframe(
        filtered_quality_df[review_display_columns],
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        label="Download quality review CSV",
        data=_csv_bytes(quality_df),
        file_name="client_completion_tracker_quality_review.csv",
        mime="text/csv",
        use_container_width=False,
    )

    # ---------------------------------------------------------------------
    # 4. Folder health check.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Folder Health Check</div>
            <div class="tracker-section-copy">
                Flags missing input files, missing status files, multiple PDFs, and unexpected file names in assessment folders.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    health_columns = [
        "Status",
        "Client",
        "Task / Assessment",
        "Folder Name",
        "No report.json",
        "No snapshots folder",
        "No processed video",
        "No status.json",
        "No task notes/context file",
        "No client profile",
        "Multiple PDFs found",
        "Unexpected file names",
        "Unexpected Files",
        "Folder ID",
    ]

    health_issue_columns = [
        "No report.json",
        "No snapshots folder",
        "No processed video",
        "No status.json",
        "No task notes/context file",
        "No client profile",
        "Multiple PDFs found",
        "Unexpected file names",
    ]

    health_df = quality_df.copy()

    if not health_df.empty:
        mask = False
        for column in health_issue_columns:
            mask = mask | (health_df[column] == "Yes")
        health_df = health_df[mask]

    if health_df.empty:
        st.success("No folder health issues found.")
    else:
        st.dataframe(
            health_df[health_columns],
            use_container_width=True,
            hide_index=True,
        )

    st.download_button(
        label="Download folder health CSV",
        data=_csv_bytes(health_df),
        file_name="client_completion_tracker_folder_health.csv",
        mime="text/csv",
        use_container_width=False,
    )

    # ---------------------------------------------------------------------
    # 5. Completion summary.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Completion Summary</div>
            <div class="tracker-section-copy">
                Client-level totals combining current PDF reports and saved historical Word report counts.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if summary_df.empty:
        st.info("No completed reports found yet. You can still add manual historical counts below.")
    else:
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

    st.download_button(
        label="Download summary CSV",
        data=_csv_bytes(summary_df),
        file_name="client_completion_tracker_summary.csv",
        mime="text/csv",
        use_container_width=False,
    )

    # ---------------------------------------------------------------------
    # 6. Manual historical counts.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Manual Historical Counts</div>
            <div class="tracker-section-copy">
                Enter older Word-format reports completed before the current PDF workflow. These counts are stored locally in data/historical_report_counts.json.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    edited_historical_df = st.data_editor(
        historical_seed_df,
        num_rows="dynamic",
        use_container_width=True,
        hide_index=True,
        column_config={
            "Client": st.column_config.TextColumn("Client", required=True),
            "Historical Word Reports Completed": st.column_config.NumberColumn(
                "Historical Word Reports Completed",
                min_value=0,
                step=1,
                required=True,
            ),
            "Notes": st.column_config.TextColumn("Notes"),
        },
        key="historical_report_counts_editor",
    )

    save_left, save_right = st.columns([1, 3])

    with save_left:
        if st.button("Save historical counts", type="primary"):
            save_historical_counts(edited_historical_df.to_dict(orient="records"))
            st.success("Historical counts saved.")
            st.rerun()

    with save_right:
        st.caption("Only client names, counts, notes, version, and updatedAt are saved.")

    edited_summary_df = build_summary_table(
        current_reports=current_reports,
        historical_rows=edited_historical_df.to_dict(orient="records"),
    )
    edited_metrics = build_tracker_metrics(edited_summary_df)

    with st.expander("Preview totals using current manual table edits", expanded=False):
        st.dataframe(edited_summary_df, use_container_width=True, hide_index=True)

    # ---------------------------------------------------------------------
    # 7. Detailed current PDF reports.
    # ---------------------------------------------------------------------
    st.markdown(
        """
        <div class="tracker-section">
            <div class="tracker-section-title">Detailed Current PDF Reports</div>
            <div class="tracker-section-copy">
                Folder-level view of completed current PDF reports found in the processed videos root folder.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if detailed_df.empty:
        st.info("No current completed PDF reports were found in the scanned folder.")
    else:
        st.dataframe(detailed_df, use_container_width=True, hide_index=True)

    st.download_button(
        label="Download detailed CSV",
        data=_csv_bytes(detailed_df),
        file_name="client_completion_tracker_detailed.csv",
        mime="text/csv",
        use_container_width=False,
    )

    # ---------------------------------------------------------------------
    # 8. Print-friendly view.
    # ---------------------------------------------------------------------
    with st.expander("Print-friendly tracker view", expanded=False):
        st.caption("Use your browser print function to print this section or save it as a PDF.")
        render_print_friendly_view(edited_summary_df, edited_metrics)

    # Future enhancement:
    # Add optional scanning of the historical Word reports Drive folder here.
    # Keep it separate from the current PDF scan so the user can turn it on only when ready.
