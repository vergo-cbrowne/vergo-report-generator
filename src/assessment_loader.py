from typing import Any, Dict, List
import google_drive


def _find_report_json(files: List[Dict[str, Any]]) -> Dict[str, Any] | None:
    normalized_target = "report.json"
    exact_match = next((item for item in files if item["name"] == normalized_target), None)
    if exact_match:
        return exact_match

    case_insensitive_matches = [
        item for item in files if item["name"].lower() == normalized_target.lower()
    ]
    return case_insensitive_matches[0] if case_insensitive_matches else None


def _print_files(title: str, files: List[Dict[str, Any]]) -> None:
    print(title)
    for item in files:
        print(
            f"- name={item.get('name')} mimeType={item.get('mimeType')} id={item.get('id')} "
            f"parents={item.get('parents')} driveId={item.get('driveId')}"
        )


def load_assessment_folder(service, folder_id: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
    files = google_drive.list_folder_files(service, folder_id)

    _print_files("Assessment folder contents:", files)
    report_file = _find_report_json(files)

    if report_file is None:
        folder_metadata = google_drive.get_file_metadata(
            service,
            folder_id,
            fields="id,name,mimeType,driveId,parents",
        )
        print(
            f"Selected folder metadata: id={folder_metadata.get('id')} name={folder_metadata.get('name')} "
            f"mimeType={folder_metadata.get('mimeType')} driveId={folder_metadata.get('driveId')}"
        )

        print("Fallback: searching globally for report.json files")
        global_report_files = google_drive.search_files_by_name_global(service, "report.json")

        if not global_report_files:
            raise FileNotFoundError(
                "report.json not found in assessment folder and no global report.json files were discovered"
            )

        print("Global report.json candidates:")
        for item in global_report_files:
            parent_ids = item.get("parents") or []
            parent_id = parent_ids[0] if parent_ids else "<none>"
            parent_name = (
                google_drive.get_folder_name(service, parent_id) if parent_ids else "<unknown>"
            )
            print(
                f"- fileId={item.get('id')} parentId={parent_id} parentName={parent_name} "
                f"driveId={item.get('driveId')}"
            )

        direct_matches = [
            item for item in global_report_files if folder_id in (item.get("parents") or [])
        ]
        if direct_matches:
            report_file = direct_matches[0]
            print("Found report.json with selected folder as parent.")
        else:
            fallback_candidate = global_report_files[0]
            fallback_parents = fallback_candidate.get("parents") or []
            if not fallback_parents:
                raise FileNotFoundError(
                    "report.json found globally, but no parent folder IDs were available for fallback"
                )

            fallback_parent_id = fallback_parents[0]
            fallback_parent_name = google_drive.get_folder_name(service, fallback_parent_id)
            print(
                f"No direct report.json parent match. Using fallback parent folder: "
                f"id={fallback_parent_id} name={fallback_parent_name}"
            )
            files = google_drive.list_folder_files(service, fallback_parent_id)
            _print_files("Fallback folder contents:", files)
            report_file = fallback_candidate
            folder_id = fallback_parent_id

    report_json = google_drive.download_json_file(service, report_file["id"])
    snapshot_files = [item for item in files if "snapshot" in item["name"].lower()]

    return report_json, snapshot_files
