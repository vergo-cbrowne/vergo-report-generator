import argparse
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/drive"]


def create_drive_service(credentials_path: str):
    credentials = service_account.Credentials.from_service_account_file(
        credentials_path,
        scopes=SCOPES,
    )
    return build("drive", "v3", credentials=credentials, cache_discovery=False)


def print_section(title: str):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def get_file_metadata(service, file_id: str) -> dict:
    return service.files().get(
        fileId=file_id,
        supportsAllDrives=True,
        fields="id,name,mimeType,driveId,parents",
    ).execute()


def run_diagnostics(service, folder_id: str):
    print_section("1) files().get on the folder")
    try:
        folder_info = get_file_metadata(service, folder_id)
        print("Folder information:")
        for key, value in folder_info.items():
            print(f"- {key}: {value}")
    except Exception as exc:
        print(f"Error while getting folder info: {exc}")

    print_section("2) files().list for children of the folder")
    try:
        query = f"'{folder_id}' in parents and trashed = false"
        response = service.files().list(
            q=query,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            fields="nextPageToken, files(id, name, mimeType, parents, driveId)",
        ).execute()
        children = response.get("files", [])
        print(f"Found {len(children)} child items")
        for item in children:
            print(f"- name={item.get('name')} mimeType={item.get('mimeType')} id={item.get('id')} parents={item.get('parents')} driveId={item.get('driveId')}")
    except Exception as exc:
        print(f"Error while listing folder children: {exc}")

    print_section("3) files().list for report.json anywhere")
    try:
        query = "name = 'report.json' and trashed = false"
        response = service.files().list(
            q=query,
            supportsAllDrives=True,
            includeItemsFromAllDrives=True,
            corpora="allDrives",
            fields="nextPageToken, files(id, name, mimeType, parents, driveId)",
        ).execute()
        matches = response.get("files", [])
        print(f"Found {len(matches)} report.json matches")

        parent_matches = []
        for item in matches:
            parent_ids = item.get("parents") or []
            if not parent_ids:
                print(f"- report.json id={item.get('id')} has no parent IDs")
                continue

            for parent_id in parent_ids:
                try:
                    parent_info = get_file_metadata(service, parent_id)
                    print(
                        f"- report.json id={item.get('id')} parentId={parent_info.get('id')} "
                        f"parentName={parent_info.get('name')} driveId={parent_info.get('driveId')}"
                    )
                    parent_matches.append(parent_info)
                except Exception as exc:
                    print(
                        f"- report.json id={item.get('id')} parentId={parent_id} "
                        f"error fetching parent metadata: {exc}"
                    )

        print_section("Matching likely assessment folders")
        likely_folders = [
            parent for parent in parent_matches
            if parent and isinstance(parent.get('name'), str)
            and (
                'Cameco_Vergo_3' in parent['name']
                or 'b5ee8' in parent['name']
                or 'Cameco_Vergo_3'.lower() in parent['name'].lower()
                or 'b5ee8'.lower() in parent['name'].lower()
            )
        ]

        if likely_folders:
            for parent in likely_folders:
                print(
                    f"- id={parent.get('id')} name={parent.get('name')} driveId={parent.get('driveId')}"
                )
        else:
            print("No likely assessment folders found by name match.")
    except Exception as exc:
        print(f"Error while searching for report.json: {exc}")


def parse_args():
    parser = argparse.ArgumentParser(description="Diagnose Google Drive Shared Drive access.")
    parser.add_argument("--folder-id", required=True, help="Google Drive folder ID to diagnose")
    parser.add_argument("--credentials-path", required=True, help="Path to service account credentials JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    service = create_drive_service(args.credentials_path)
    run_diagnostics(service, args.folder_id)


if __name__ == "__main__":
    main()
