import json
import os
import re
from pathlib import Path
from typing import Any

from openai import OpenAI


def _read_text_file(path: str | Path) -> str:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Prompt/style file not found: {path}")
    return path.read_text(encoding="utf-8")


def _safe_json_dumps(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def _snapshot_summary(snapshot_files: list[Any]) -> list[dict[str, Any]]:
    summaries = []

    for item in snapshot_files or []:
        if isinstance(item, dict):
            summaries.append(
                {
                    "name": item.get("name") or item.get("filename") or item.get("file_name") or "snapshot",
                    "mimeType": item.get("mimeType") or item.get("mime_type") or "",
                    "id": item.get("id") or item.get("file_id") or "",
                }
            )
        else:
            summaries.append({"name": str(item), "mimeType": "", "id": ""})

    return summaries


def _extract_response_text(response: Any) -> str:
    """
    Supports the current OpenAI Responses API object and a few common fallbacks.
    """
    output_text = getattr(response, "output_text", None)
    if output_text:
        return output_text

    try:
        chunks = []
        for output_item in response.output:
            for content_item in output_item.content:
                text = getattr(content_item, "text", None)
                if text:
                    chunks.append(text)
        if chunks:
            return "\n".join(chunks)
    except Exception:
        pass

    if isinstance(response, dict):
        if response.get("output_text"):
            return response["output_text"]

        try:
            chunks = []
            for output_item in response.get("output", []):
                for content_item in output_item.get("content", []):
                    text = content_item.get("text")
                    if text:
                        chunks.append(text)
            if chunks:
                return "\n".join(chunks)
        except Exception:
            pass

    return str(response)


def _strip_code_fences(text: str) -> str:
    text = text.strip()

    if text.startswith("```json"):
        text = text[len("```json") :].strip()

    if text.startswith("```"):
        text = text[len("```") :].strip()

    if text.endswith("```"):
        text = text[:-3].strip()

    return text


def _parse_json_response(text: str) -> dict[str, Any]:
    cleaned = _strip_code_fences(text)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not match:
            raise ValueError("OpenAI response did not contain a JSON object.")

        parsed = json.loads(match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError("OpenAI response JSON must be an object.")

    return parsed


def _clean_text(value: Any) -> str:
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


def _first_value(item: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = item.get(key)
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _ensure_heading_content_items(items: Any, section_name: str) -> list[dict[str, str]]:
    """
    Normalizes only the shape needed by the HTML builder.
    It does NOT strip or discard content.
    """
    if not isinstance(items, list):
        return []

    normalized = []

    for item in items:
        if isinstance(item, dict):
            heading = _first_value(
                item,
                [
                    "heading",
                    "Heading",
                    "title",
                    "Title",
                    "module",
                    "Module",
                ],
            )

            content = _first_value(
                item,
                [
                    "content",
                    "Content",
                    "body",
                    "Body",
                    "details",
                    "Details",
                    "explanation",
                    "Explanation",
                    "description",
                    "Description",
                    "recommendation",
                    "Recommendation",
                    "reason",
                    "Reason",
                    "rationale",
                    "Rationale",
                    "paragraph",
                    "Paragraph",
                    "paragraphs",
                    "Paragraphs",
                ],
            )

            if not heading and len(item) == 1:
                key, value = next(iter(item.items()))
                heading = _clean_text(key)
                content = _clean_text(value)

            normalized_item = dict(item)

            if heading:
                if section_name == "training_videos":
                    normalized_item["module"] = heading
                else:
                    normalized_item["heading"] = heading

            if content:
                normalized_item["content"] = content

            normalized.append(normalized_item)

        elif isinstance(item, str):
            normalized.append(
                {
                    "heading": item.strip(),
                    "content": "",
                }
            )

    return normalized


def _normalize_report(parsed: dict[str, Any]) -> dict[str, Any]:
    """
    Preserve the OpenAI JSON structure while ensuring key section names exist.
    This replaces the earlier normalization that was stripping Section 3/5 body text.
    """
    report = dict(parsed)

    report.setdefault("cover_details", {})
    report.setdefault("assessment_overview", [])
    report.setdefault("score_summary", {})
    report.setdefault("overall_observations", [])
    report.setdefault("training_videos", [])

    report["risk_exposure_analysis"] = _ensure_heading_content_items(
        report.get("risk_exposure_analysis", []),
        "risk_exposure_analysis",
    )

    report["recommendations"] = _ensure_heading_content_items(
        report.get("recommendations", []),
        "recommendations",
    )

    report["training_videos"] = _ensure_heading_content_items(
        report.get("training_videos", []),
        "training_videos",
    )

    return report


def _debug_section_counts(report: dict[str, Any]) -> None:
    assessment_overview = report.get("assessment_overview", [])
    risk_exposure_analysis = report.get("risk_exposure_analysis", [])
    overall_observations = report.get("overall_observations", [])
    recommendations = report.get("recommendations", [])
    training_videos = report.get("training_videos", [])

    print(
        "DEBUG: output section counts: "
        f"assessment_overview={len(assessment_overview) if isinstance(assessment_overview, list) else 'not-list'}, "
        f"risk_exposure_analysis={len(risk_exposure_analysis) if isinstance(risk_exposure_analysis, list) else 'not-list'}, "
        f"overall_observations={len(overall_observations) if isinstance(overall_observations, list) else 'not-list'}, "
        f"recommendations={len(recommendations) if isinstance(recommendations, list) else 'not-list'}, "
        f"training_videos={len(training_videos) if isinstance(training_videos, list) else 'not-list'}"
    )


def _debug_content_presence(report: dict[str, Any]) -> None:
    def complete_items(items: Any) -> bool:
        if not isinstance(items, list) or not items:
            return False

        for item in items:
            if not isinstance(item, dict):
                return False

            content = _first_value(
                item,
                [
                    "content",
                    "Content",
                    "body",
                    "Body",
                    "details",
                    "Details",
                    "explanation",
                    "Explanation",
                    "description",
                    "Description",
                    "recommendation",
                    "Recommendation",
                    "reason",
                    "Reason",
                    "rationale",
                    "Rationale",
                    "paragraph",
                    "Paragraph",
                    "paragraphs",
                    "Paragraphs",
                ],
            )

            if not content:
                return False

        return True

    print(
        "DEBUG: normalized report has complete Section 3/5 content: "
        f"{complete_items(report.get('risk_exposure_analysis')) and complete_items(report.get('recommendations'))}"
    )


def generate_report(
    prompt_path: str | Path,
    report_data: dict[str, Any],
    snapshot_files: list[Any],
    model: str,
    style_guide_path: str | Path | None = None,
) -> dict[str, Any]:
    print("Generating report with OpenAI...")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set. Check your .env file.")

    prompt = _read_text_file(prompt_path)
    style_guide = _read_text_file(style_guide_path) if style_guide_path else ""

    snapshot_summary = _snapshot_summary(snapshot_files)

    user_input = f"""
Generate a Vergo Movement Analysis Risk Report using the required JSON schema.

STYLE GUIDE:
{style_guide}

ASSESSMENT REPORT.JSON DATA:
{_safe_json_dumps(report_data)}

SNAPSHOT FILE SUMMARY:
{_safe_json_dumps(snapshot_summary)}

IMPORTANT:
- Return valid JSON only.
- Preserve all required fields.
- For risk_exposure_analysis, every item must include heading and content.
- For recommendations, every item must include heading and content.
- For training_videos, every item must include module and content.
"""

    client = OpenAI(api_key=api_key)

    print("Calling OpenAI model...")
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "system",
                "content": prompt,
            },
            {
                "role": "user",
                "content": user_input,
            },
        ],
        temperature=0.2,
    )

    print("OpenAI report generation complete.")

    response_text = _extract_response_text(response)

    debug_dir = Path("debug")
    debug_dir.mkdir(parents=True, exist_ok=True)

    raw_text_path = debug_dir / "latest_raw_response.txt"
    raw_text_path.write_text(response_text, encoding="utf-8")

    parsed = _parse_json_response(response_text)

    print(f"DEBUG: Successfully parsed JSON response as dict with keys: {list(parsed.keys())}")

    parsed_path = debug_dir / "latest_parsed_response.json"
    parsed_path.write_text(_safe_json_dumps(parsed), encoding="utf-8")

    normalized = _normalize_report(parsed)

    normalized_path = debug_dir / "latest_normalized_report.json"
    normalized_path.write_text(_safe_json_dumps(normalized), encoding="utf-8")

    _debug_section_counts(normalized)
    _debug_content_presence(normalized)

    return normalized