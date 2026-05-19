import json
import os
from pathlib import Path
from openai import OpenAI


def _ensure_api_key() -> str:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is required")
    return api_key


def generate_report(prompt_path: str, report_data: dict, snapshot_files: list[dict], model: str) -> str:
    api_key = _ensure_api_key()
    prompt_template = Path(prompt_path).read_text(encoding="utf-8")
    snapshot_list = "\n".join(
        f"- {item['name']} ({item.get('mimeType', 'unknown')})" for item in snapshot_files
    )

    if not snapshot_list:
        snapshot_list = "- No snapshots found"

    user_content = (
        f"{prompt_template}\n\n"
        "Assessment JSON:\n"
        f"{json.dumps(report_data, indent=2)}\n\n"
        "Snapshot files:\n"
        f"{snapshot_list}\n\n"
        "Please generate a clear, structured report for this assessment."
    )

    client = OpenAI(api_key=api_key)

    print("Calling OpenAI model...")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a helpful assistant that creates professional assessment reports."},
            {"role": "user", "content": user_content},
        ],
        temperature=0.2,
    )
    print("OpenAI report generation complete.")

    if not getattr(response, "choices", None):
        raise ValueError("OpenAI response contained no choices")

    report_text = getattr(response.choices[0].message, "content", None)
    if not report_text:
        raise ValueError("OpenAI response choice had no message content")

    return report_text.strip()
