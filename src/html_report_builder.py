from pathlib import Path
from html import escape
import re
from typing import Any


DISCLAIMER_TEXT = (
    "This movement analysis provides general guidance based on the video provided at the time of review. "
    "It is not intended to replace medical advice, diagnosis, or professional ergonomic evaluation. "
    "Postural risk levels may vary depending on actual workplace conditions and individual worker factors. "
    "Employers remain responsible for complying with the Nova Scotia Occupational Health and Safety Act, "
    "related regulations, CSA Z1004-12, and all applicable standards.\n\n"
    "Vergo’s motion-analysis results support proactive identification of movement-related risks but are not "
    "a substitute for assessments conducted by certified ergonomists or occupational health professionals. "
    "Any images or video content included must be used in accordance with organizational privacy and "
    "data-protection policies."
)


BODY_KEYS = [
    "body", "Body", "content", "Content", "details", "Details",
    "explanation", "Explanation", "description", "Description",
    "recommendation", "Recommendation", "reason", "Reason",
    "rationale", "Rationale", "paragraph", "Paragraph",
    "paragraphs", "Paragraphs",
]

HEADING_KEYS = ["heading", "Heading", "module", "Module", "title", "Title"]




def _render_heading_content_block(value) -> str:
    """Render structured heading/content dicts instead of leaking raw 'heading:'/'content:' text."""
    if isinstance(value, dict) and ("heading" in value or "content" in value):
        heading = _clean_text(value.get("heading") or "")
        content = _clean_text(value.get("content") or "")
        html = ""
        if heading:
            html += f"<h3>{escape(heading)}</h3>"
        if content:
            html += f"<p>{escape(content)}</p>"
        return html
    return ""

def _clean_text(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return "\n\n".join(_clean_text(item) for item in value if _clean_text(item))

    if isinstance(value, dict):
        parts = []
        for key, val in value.items():
            cleaned_key = _clean_text(key)
            cleaned_val = _clean_text(val)
            if cleaned_key and cleaned_val:
                parts.append(f"{cleaned_key}: {cleaned_val}")
            elif cleaned_val:
                parts.append(cleaned_val)
        return "\n\n".join(parts)

    text = str(value).strip()
    text = text.replace("```json", "").replace("```", "")
    text = text.replace("**", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")
    return text.strip()


def _display_value(value) -> str:
    text = _clean_text(value)
    if not text or text.lower() in {"none", "null", "n/a", "not available", "not specified"}:
        return "Not specified"
    return text


def _get_first_value(data: dict, keys: list[str]) -> str:
    for key in keys:
        value = data.get(key)
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return ""


def _get_body_value(item: dict) -> str:
    return _get_first_value(item, BODY_KEYS)


def _get_heading_value(item: dict) -> str:
    return _get_first_value(item, HEADING_KEYS)


def _p(value) -> str:
    text = _clean_text(value)
    if not text:
        return ""

    paragraphs = [part.strip() for part in text.split("\n\n") if part.strip()]
    return "\n".join(f"<p>{escape(paragraph)}</p>" for paragraph in paragraphs)


def _ul(items) -> str:
    if not items:
        return ""

    if isinstance(items, str):
        items = [items]

    lis = "\n".join(
        f"<li>{escape(_clean_text(item))}</li>"
        for item in items
        if _clean_text(item)
    )

    return f"<ul>\n{lis}\n</ul>" if lis else ""


def _section(title: str, body: str, css_class: str = "") -> str:
    class_attr = "report-section"
    if css_class:
        class_attr += f" {css_class}"

    return f"""
<section class="{class_attr}">
  <h2>{escape(title)}</h2>
  {body}
</section>
"""


def _normalise_key(key: str) -> str:
    return str(key).lower().replace(" ", "_").replace("/", "_").replace("-", "_").strip()


def _find_value_recursive(data: Any, possible_keys: list[str]) -> Any:
    wanted = {_normalise_key(key) for key in possible_keys}

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if _normalise_key(key) in wanted:
                    return item

            for item in value.values():
                found = walk(item)
                if found not in ("", None):
                    return found

        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found not in ("", None):
                    return found

        return ""

    return walk(data)


def _to_float(value) -> float | None:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = _clean_text(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except ValueError:
        return None


def _to_int(value) -> int | None:
    number = _to_float(value)
    if number is None:
        return None
    return int(round(number))


def _method_type(method: str) -> str:
    method_lower = method.lower()

    if "reba" in method_lower:
        return "REBA"

    if "rula" in method_lower:
        return "RULA"

    return "REBA/RULA"


def _get_cover_details(report_data: dict) -> dict:
    cover = report_data.get("cover_details", {}) or {}

    task_name = (
        cover.get("Task name/title")
        or cover.get("Task Name")
        or cover.get("Task")
        or report_data.get("task_name")
        or report_data.get("task")
        or report_data.get("title")
        or ""
    )

    client_name = (
        cover.get("Company/Client name")
        or cover.get("Company")
        or cover.get("Client")
        or report_data.get("client_name")
        or report_data.get("company")
        or report_data.get("client")
        or ""
    )

    site_location = (
        cover.get("Site location or facility name")
        or cover.get("Site / Location")
        or cover.get("Site Location")
        or cover.get("Location")
        or report_data.get("site_location")
        or report_data.get("location")
        or ""
    )

    assessment_date = (
        cover.get("Assessment date")
        or cover.get("Assessment Date")
        or report_data.get("assessment_date")
        or report_data.get("date")
        or ""
    )

    assessment_method = (
        cover.get("Assessment method")
        or cover.get("Assessment Method")
        or report_data.get("assessment_method")
        or report_data.get("method")
        or "RULA"
    )

    video_duration = (
        cover.get("Video duration")
        or cover.get("Video Duration")
        or report_data.get("video_duration")
        or report_data.get("duration")
        or ""
    )

    assessor = (
        cover.get("Assessor name")
        or cover.get("Assessor")
        or report_data.get("assessor")
        or report_data.get("assessor_name")
        or ""
    )

    return {
        "task_name": _display_value(task_name),
        "client_name": _display_value(client_name),
        "site_location": _display_value(site_location),
        "assessment_date": _display_value(assessment_date),
        "assessment_method": _display_value(assessment_method),
        "video_duration": _display_value(video_duration),
        "assessor": _display_value(assessor),
    }


def _risk_level_from_average(method_type: str, average_score: float | None) -> str:
    if average_score is None:
        return "Not available"

    if method_type == "REBA":
        if average_score <= 3:
            return "Low"
        if average_score <= 7:
            if average_score >= 6.5:
                return "Medium, near the upper end of the Medium band"
            return "Medium"
        if average_score <= 10:
            return "High"
        return "Very High"

    if method_type == "RULA":
        if average_score <= 2:
            return "Acceptable if not maintained or repeated for long periods"
        if average_score <= 4:
            return "Further investigation; changes may be needed"
        if average_score <= 6:
            return "Investigation and changes needed soon"
        return "Investigation and changes needed immediately"

    return "Interpret with the selected screening method"


def _score_label(method_type: str) -> str:
    if method_type == "REBA":
        return "Average REBA Score"
    if method_type == "RULA":
        return "Average RULA Score"
    return "Average Score"


def _scores_from_report_json(report_data: dict) -> list[float]:
    scores = []

    score_key_terms = [
        "reba_score",
        "rula_score",
        "final_reba",
        "final_rula",
        "final_score",
        "overall_score",
        "risk_score",
    ]

    excluded_key_terms = [
        "average",
        "mean",
        "median",
        "min",
        "max",
        "summary",
        "distribution",
        "risk_level",
        "risk_band",
    ]

    def looks_like_frame_score_key(key: str) -> bool:
        norm = _normalise_key(key)
        if any(term in norm for term in excluded_key_terms):
            return False
        return any(term in norm for term in score_key_terms)

    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if looks_like_frame_score_key(key):
                    number = _to_float(item)
                    if number is not None and 0 <= number <= 15:
                        scores.append(number)
                walk(item)

        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(report_data)

    return [score for score in scores if score is not None]


def _get_score_summary_data(report_data: dict, metadata: dict) -> dict:
    score_summary = report_data.get("score_summary")
    method_type = _method_type(metadata.get("assessment_method", ""))

    if isinstance(score_summary, dict):
        method_from_summary = _clean_text(
            score_summary.get("assessment_method_type")
            or score_summary.get("method_type")
            or score_summary.get("score_type")
            or ""
        )

        if method_from_summary.upper() in {"REBA", "RULA"}:
            method_type = method_from_summary.upper()

        total_frames = _to_int(
            score_summary.get("total_frames_analyzed")
            or score_summary.get("total_frames")
            or score_summary.get("frames_analyzed")
        )

        average_score = _to_float(
            score_summary.get("average_score")
            or score_summary.get("average_reba_score")
            or score_summary.get("average_rula_score")
        )

        if average_score is not None:
            average_score = round(average_score, 1)

        overall_risk = _clean_text(
            score_summary.get("overall_risk_level")
            or score_summary.get("risk_level")
            or ""
        )

        if not overall_risk or overall_risk.lower() in {"none", "unknown", "not available"}:
            overall_risk = _risk_level_from_average(method_type, average_score)

        distribution = score_summary.get("score_distribution") or score_summary.get("distribution") or []

        if not isinstance(distribution, list):
            distribution = []

        extracted_scores = _scores_from_report_json(report_data)

        if total_frames is None and extracted_scores:
            total_frames = len(extracted_scores)

        if average_score is None and extracted_scores:
            average_score = round(sum(extracted_scores) / len(extracted_scores), 1)
            overall_risk = _risk_level_from_average(method_type, average_score)

        return {
            "method_type": method_type,
            "total_frames": total_frames,
            "average_score": average_score,
            "overall_risk": overall_risk,
            "score_distribution": distribution,
            "extracted_scores": extracted_scores,
        }

    extracted_scores = _scores_from_report_json(report_data)
    total_frames = len(extracted_scores) if extracted_scores else None
    average_score = round(sum(extracted_scores) / len(extracted_scores), 1) if extracted_scores else None
    overall_risk = _risk_level_from_average(method_type, average_score)

    return {
        "method_type": method_type,
        "total_frames": total_frames,
        "average_score": average_score,
        "overall_risk": overall_risk,
        "score_distribution": [],
        "extracted_scores": extracted_scores,
    }


def _format_number(value: float | int | None) -> str:
    if value is None:
        return "Not available"

    if isinstance(value, float) and value.is_integer():
        return str(int(value))

    return f"{value:.1f}" if isinstance(value, float) else str(value)


def _count_scores_by_band(scores: list[float], method_type: str) -> dict[str, int]:
    counts = {}

    if method_type == "REBA":
        bands = {
            "1-3": lambda score: 1 <= score <= 3,
            "4-7": lambda score: 4 <= score <= 7,
            "8-10": lambda score: 8 <= score <= 10,
            "11-15": lambda score: 11 <= score <= 15,
        }
    else:
        bands = {
            "1-2": lambda score: 1 <= score <= 2,
            "3-4": lambda score: 3 <= score <= 4,
            "5-6": lambda score: 5 <= score <= 6,
            "7": lambda score: score >= 7,
        }

    for band_key, rule in bands.items():
        counts[band_key] = sum(1 for score in scores if rule(score))

    return counts


def _distribution_rows(report_data: dict, method_type: str, total_frames: int | None, extracted_scores: list[float]) -> list[dict]:
    score_summary = report_data.get("score_summary") if isinstance(report_data.get("score_summary"), dict) else {}
    structured_distribution = score_summary.get("score_distribution") or []

    if structured_distribution and isinstance(structured_distribution, list):
        rows = []

        for item in structured_distribution:
            if not isinstance(item, dict):
                continue

            score_range = _clean_text(item.get("score_range") or item.get("range") or "")
            risk_band = _clean_text(item.get("risk_band") or item.get("band") or "")
            interpretation = _clean_text(item.get("interpretation") or "")
            frames_display = _clean_text(item.get("frames_display") or "")

            frames_count = _to_int(item.get("frames_count") or item.get("count") or item.get("frames"))
            frames_percent = _to_int(item.get("frames_percent") or item.get("percent") or item.get("percentage"))

            if not frames_display:
                if frames_count is not None and total_frames:
                    frames_percent = round((frames_count / total_frames) * 100)
                    frames_display = f"{frames_percent}% ({frames_count})"
                elif frames_count is not None:
                    frames_display = f"({frames_count})"
                else:
                    frames_display = "Not available"

            if not score_range:
                continue

            lower_band = risk_band.lower()
            if "very" in lower_band or "immediate" in lower_band:
                css = "risk-very-high"
            elif "high" in lower_band or "soon" in lower_band:
                css = "risk-high"
            elif "medium" in lower_band or "investigation" in lower_band:
                css = "risk-medium"
            else:
                css = "risk-low"

            rows.append(
                {
                    "range": score_range,
                    "band": risk_band or "Not available",
                    "frames": frames_display,
                    "interpretation": interpretation or "Not available",
                    "css": css,
                }
            )

        if rows:
            return rows

    counts = _count_scores_by_band(extracted_scores, method_type) if extracted_scores else {}

    if method_type == "REBA":
        rows = [
            {
                "range": "1–3",
                "range_key": "1-3",
                "band": "Low (Scores 1–3)",
                "interpretation": "Low risk; may need attention",
                "css": "risk-low",
            },
            {
                "range": "4–7",
                "range_key": "4-7",
                "band": "Medium (Scores 4–7)",
                "interpretation": "Further investigation and changes recommended",
                "css": "risk-medium",
            },
            {
                "range": "8–10",
                "range_key": "8-10",
                "band": "High (Scores 8–10)",
                "interpretation": "Investigation and implement changes soon",
                "css": "risk-high",
            },
            {
                "range": "11–15",
                "range_key": "11-15",
                "band": "Very High (Scores 11–15)",
                "interpretation": "Implement changes immediately",
                "css": "risk-very-high",
            },
        ]
    else:
        rows = [
            {
                "range": "1–2",
                "range_key": "1-2",
                "band": "Acceptable (Scores 1–2)",
                "interpretation": "Acceptable if not maintained or repeated for long periods",
                "css": "risk-low",
            },
            {
                "range": "3–4",
                "range_key": "3-4",
                "band": "Further Investigation (Scores 3–4)",
                "interpretation": "Further investigation; changes may be needed",
                "css": "risk-medium",
            },
            {
                "range": "5–6",
                "range_key": "5-6",
                "band": "Changes Needed Soon (Scores 5–6)",
                "interpretation": "Investigation and changes needed soon",
                "css": "risk-high",
            },
            {
                "range": "7",
                "range_key": "7",
                "band": "Immediate Review (Score 7)",
                "interpretation": "Investigation and changes needed immediately",
                "css": "risk-very-high",
            },
        ]

    for row in rows:
        count = counts.get(row["range_key"]) if counts else None

        if count is None:
            row["frames"] = "Not available"
        elif total_frames and total_frames > 0:
            percent = round((count / total_frames) * 100)
            row["frames"] = f"{percent}% ({count})"
        else:
            row["frames"] = f"({count})"

    return rows


def _render_method_note(metadata: dict) -> str:
    method_type = _method_type(metadata.get("assessment_method", ""))

    if method_type == "REBA":
        text = (
            "REBA, or Rapid Entire Body Assessment, is a screening tool used to assess postural exposure "
            "across the neck, trunk, legs, upper arms, lower arms, wrists, force/load, coupling, and activity. "
            "The score helps identify whether further ergonomic investigation or task changes may be needed. "
            "REBA is not an injury prediction tool. It should be interpreted together with the video context, "
            "task frequency, duration, force, workstation layout, and worker feedback."
        )
    elif method_type == "RULA":
        text = (
            "RULA, or Rapid Upper Limb Assessment, is a screening tool used to assess postural exposure in "
            "the neck, trunk, upper arms, lower arms, wrists, muscle use, force/load, and activity. "
            "The score helps identify whether further ergonomic investigation or task changes may be needed. "
            "RULA is not an injury prediction tool. It should be interpreted together with the video context, "
            "task frequency, duration, force, workstation layout, and worker feedback."
        )
    else:
        text = (
            "REBA and RULA are ergonomic screening tools used to assess postural exposure and identify whether "
            "further ergonomic investigation or task changes may be needed. These tools are not injury prediction "
            "tools. They should be interpreted together with the video context, task frequency, duration, force, "
            "workstation layout, and worker feedback."
        )

    return f"""
<section class="method-note">
  <h2>How to read this report</h2>
  <p>{escape(text)}</p>
</section>
"""


def _render_summary_interpretation(report_data: dict, metadata: dict, summary: dict) -> str:
    method_type = summary["method_type"]
    average_score = summary["average_score"]
    overall_risk = summary["overall_risk"]

    score_summary = report_data.get("score_summary")
    existing_text = ""

    if isinstance(score_summary, dict):
        existing_text = _clean_text(score_summary.get("interpretation") or score_summary.get("Interpretation") or "")

    if existing_text:
        existing_text = existing_text.replace("{{SITE_NAME}}", metadata.get("site_location", "the reviewed task"))
        existing_text = existing_text.replace("{SITE_NAME}", metadata.get("site_location", "the reviewed task"))

        if method_type == "REBA" and average_score is not None and 4 <= average_score <= 7:
            existing_text = re.sub(
                r"\bmedium\s*[-–—]\s*high\b",
                "medium",
                existing_text,
                flags=re.IGNORECASE,
            )
            existing_text = re.sub(
                r"\bhigh risk\b",
                "medium risk",
                existing_text,
                flags=re.IGNORECASE,
            )

        return f"""
<h3>Interpretation</h3>
{_p(existing_text)}
"""

    if average_score is None:
        text = (
            "The available scoring data does not include a clear average score. The findings should be interpreted "
            "using the observed task context, visible postures, movement patterns, task frequency, and worker feedback."
        )
    elif method_type == "REBA":
        text = (
            f"The average REBA score is {_format_number(average_score)}, which corresponds to {overall_risk.lower()}. "
            "This indicates that the task should be reviewed for practical ergonomic improvements, especially where "
            "repeated postures, reach distance, trunk position, neck position, or forceful handling are present. "
            "REBA should be treated as a screening result rather than a prediction of injury."
        )
    elif method_type == "RULA":
        text = (
            f"The average RULA score is {_format_number(average_score)}, which indicates: {overall_risk}. "
            "This result should be used to guide further review of upper-limb posture, wrist position, neck/trunk posture, "
            "repetition, force, and workstation setup. RULA should be treated as a screening result rather than a prediction of injury."
        )
    else:
        text = (
            "The scoring results should be interpreted as screening findings that help identify where additional ergonomic "
            "review or task design improvements may be useful. They should be considered alongside video context, task "
            "frequency, duration, force, workstation layout, and worker feedback."
        )

    return f"""
<h3>Interpretation</h3>
<p>{escape(text)}</p>
"""


def _render_structured_summary(report_data: dict, metadata: dict) -> str:
    summary = _get_score_summary_data(report_data, metadata)
    method_type = summary["method_type"]
    total_frames = summary["total_frames"]
    average_score = summary["average_score"]
    overall_risk = summary["overall_risk"]
    extracted_scores = summary.get("extracted_scores", [])

    rows = _distribution_rows(report_data, method_type, total_frames, extracted_scores)

    table_html = f"""
<table class="summary-table">
  <tbody>
    <tr>
      <th>Total Frames Analyzed</th>
      <td>{escape(_format_number(total_frames))}</td>
    </tr>
    <tr>
      <th>{escape(_score_label(method_type))}</th>
      <td>{escape(_format_number(average_score))}</td>
    </tr>
    <tr>
      <th>Overall Risk Level</th>
      <td><strong>{escape(overall_risk)}</strong></td>
    </tr>
  </tbody>
</table>
"""

    distribution_html = """
<h3>Score Distribution</h3>
<table class="distribution-table">
  <thead>
    <tr>
      <th>Score Range</th>
      <th>Risk Band</th>
      <th>Frames (%)</th>
      <th>Interpretation</th>
    </tr>
  </thead>
  <tbody>
"""

    for row in rows:
        distribution_html += f"""
    <tr class="{row["css"]}">
      <td>{escape(row["range"])}</td>
      <td>{escape(row["band"])}</td>
      <td>{escape(row["frames"])}</td>
      <td>{escape(row["interpretation"])}</td>
    </tr>
"""

    distribution_html += """
  </tbody>
</table>
"""

    explanation = _render_summary_interpretation(report_data, metadata, summary)

    return table_html + distribution_html + explanation


def _render_heading_body_items(items) -> str:
    html = ""

    if not items:
        return html

    if isinstance(items, dict):
        items = [items]

    for item in items:
        if not isinstance(item, dict):
            html += _p(item)
            continue

        heading = _get_heading_value(item)
        body = _get_body_value(item)

        if heading:
            html += '<div class="subsection-block">\n'
            html += f"<h3>{escape(_clean_text(heading))}</h3>\n"
            html += _p(body)
            html += "\n</div>\n"
            continue

        if len(item) == 1:
            key, value = next(iter(item.items()))
            html += '<div class="subsection-block">\n'
            html += f"<h3>{escape(_clean_text(key))}</h3>\n"
            html += _p(value)
            html += "\n</div>\n"
            continue

        for key, value in item.items():
            key_lower = str(key).lower()

            if key_lower in {"heading", "module", "title"}:
                html += f"<h3>{escape(_clean_text(value))}</h3>\n"
            elif key_lower in {
                "body", "content", "details", "explanation", "description",
                "recommendation", "reason", "rationale", "paragraph", "paragraphs",
            }:
                html += _p(value)
            else:
                html += '<div class="subsection-block">\n'
                html += f"<h3>{escape(_clean_text(key))}</h3>\n"
                html += _p(value)
                html += "\n</div>\n"
    return html


def _validate_heading_body_list(report_data: dict, field_name: str, section_label: str) -> list[str]:
    errors = []
    items = report_data.get(field_name)

    if not isinstance(items, list) or not items:
        errors.append(f"{section_label} must be a non-empty list.")
        return errors

    for index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            errors.append(f"{section_label} item {index} must be an object with heading/content fields.")
            continue

        heading = _get_heading_value(item)
        body = _get_body_value(item)

        if not heading:
            errors.append(f"{section_label} item {index} is missing a heading.")
        if not body:
            errors.append(f"{section_label} item {index} is missing body/content text.")

    return errors


def validate_report_data(report_data: dict) -> None:
    errors = []

    assessment_overview = _clean_text(report_data.get("assessment_overview"))
    if not assessment_overview:
        errors.append("Section 1 assessment_overview is empty.")

    errors.extend(
        _validate_heading_body_list(
            report_data,
            "risk_exposure_analysis",
            "Section 3 risk_exposure_analysis",
        )
    )

    overall_observations = _clean_text(report_data.get("overall_observations"))
    if not overall_observations:
        errors.append("Section 4 overall_observations is empty.")

    errors.extend(
        _validate_heading_body_list(
            report_data,
            "recommendations",
            "Section 5 recommendations",
        )
    )

    training_videos = report_data.get("training_videos")
    if not isinstance(training_videos, list) or not training_videos:
        errors.append("Section 6 training_videos must be a non-empty list.")
    else:
        for index, item in enumerate(training_videos, start=1):
            if not isinstance(item, dict):
                errors.append(f"Section 6 training_videos item {index} must be an object.")
                continue

            module = item.get("module") or item.get("Module") or item.get("heading") or item.get("Heading")
            content = _get_body_value(item)

            if not _clean_text(module):
                errors.append(f"Section 6 training_videos item {index} is missing a module name.")
            if not content:
                errors.append(f"Section 6 training_videos item {index} is missing rationale/content.")

    if errors:
        message = "Report validation failed:\n" + "\n".join(f"- {error}" for error in errors)
        raise ValueError(message)


def build_html_report(report_data: dict, output_path: str | Path) -> Path:
    validate_report_data(report_data)

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = _get_cover_details(report_data)

    logo_path = Path("assets/vergo-logo.png").resolve()
    logo_src = logo_path.as_uri() if logo_path.exists() else ""

    if not logo_src:
        print("WARNING: assets/vergo-logo.png not found. Falling back to text logo.")

    logo_html = (
        f'<img class="brand-logo" src="{logo_src}" alt="Vergo logo">'
        if logo_src
        else '<div class="brand-mark">V</div>'
    )

    assessment_overview = _p(report_data.get("assessment_overview", ""))
    summary_body = _render_structured_summary(report_data, metadata)
    risk_body = _render_heading_body_items(report_data.get("risk_exposure_analysis", []))
    observations_body = _p(report_data.get("overall_observations", ""))
    recommendations_body = _render_heading_body_items(report_data.get("recommendations", []))
    training_body = _render_heading_body_items(report_data.get("training_videos", []))
    method_note = _render_method_note(metadata)

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Vergo Movement Analysis Risk Report</title>
  <style>
    :root {{
      --vergo-blue: #1f4e79;
      --vergo-blue-dark: #173a5c;
      --vergo-blue-light: #eaf2f8;
      --text: #111827;
      --muted: #5b6770;
      --border: #c9d7e5;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      font-family: Arial, Helvetica, sans-serif;
      color: var(--text);
      line-height: 1.42;
      margin: 44px;
      font-size: 11.2pt;
      background: #ffffff;
    }}

    .topbar {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 4px solid var(--vergo-blue);
      padding-bottom: 16px;
      margin-bottom: 0;
    }}

    .brand {{
      display: flex;
      align-items: center;
      gap: 14px;
    }}

    .brand-logo {{
      width: 135px;
      max-height: 64px;
      object-fit: contain;
      display: block;
    }}

    .brand-mark {{
      width: 48px;
      height: 48px;
      border-radius: 12px;
      background: var(--vergo-blue);
      color: white;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 13pt;
      letter-spacing: 0.5px;
    }}

    .report-label {{
      color: var(--muted);
      font-size: 10pt;
      text-transform: uppercase;
      letter-spacing: 1px;
      font-weight: 800;
      text-align: right;
      line-height: 1.35;
    }}

    .report-subtitle {{
      margin: 12px 0 16px 0;
      font-size: 10.5pt;
      line-height: 1.45;
      color: var(--muted);
      font-style: italic;
      max-width: 760px;
    }}

    .cover {{
      margin-bottom: 22px;
      padding: 18px 20px;
      border: 1px solid var(--border);
      border-left: 6px solid var(--vergo-blue);
      background: var(--vergo-blue-light);
      border-radius: 10px;
    }}

    .metadata {{
      display: grid;
      grid-template-columns: 170px 1fr;
      gap: 7px 16px;
      font-size: 10.8pt;
    }}

    .label {{
      font-weight: 700;
      color: var(--vergo-blue-dark);
    }}

    .method-note {{
      margin-bottom: 22px;
      padding: 14px 16px;
      border: 1px solid #d8e2ec;
      border-left: 5px solid var(--vergo-blue);
      background: #f8fbfd;
      border-radius: 8px;
    }}

    .method-note h2 {{
      margin-top: 0;
      font-size: 13.5pt;
      border-bottom: none;
      padding-bottom: 0;
      margin-bottom: 7px;
      color: var(--vergo-blue);
    }}

    .method-note p {{
      margin-bottom: 0;
      color: #374151;
      font-size: 10.2pt;
    }}

    h2 {{
      color: var(--vergo-blue);
      font-size: 15.5pt;
      border-bottom: 1.5px solid var(--vergo-blue);
      padding-bottom: 5px;
      margin-top: 26px;
      margin-bottom: 12px;
      page-break-after: avoid;
      break-after: avoid;
    }}

    h3 {{
      font-size: 12.2pt;
      margin-top: 20px;
      margin-bottom: 7px;
      font-weight: 800;
      color: #1f70b8;
      page-break-after: avoid;
      break-after: avoid;
    }}

    p {{
      margin-top: 0;
      margin-bottom: 10px;
    }}

    ul {{
      margin-top: 4px;
      margin-bottom: 14px;
      padding-left: 22px;
    }}

    li {{
      margin-bottom: 5px;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 8px 0 20px 0;
      font-size: 10.4pt;
    }}

    th, td {{
      border: 1px solid #b8c2cc;
      padding: 8px 10px;
      text-align: left;
      vertical-align: top;
    }}

    .summary-table th {{
      width: 34%;
      background: #d6eaf5;
      color: #1f70b8;
      font-weight: 800;
    }}

    .summary-table td {{
      background: #ffffff;
    }}

    .distribution-table thead th {{
      background: #2f78b7;
      color: #ffffff;
      font-weight: 800;
    }}

    .risk-low td {{
      background: #d9ead3;
    }}

    .risk-medium td {{
      background: #fff0b3;
    }}

    .risk-high td {{
      background: #f9d5bd;
    }}

    .risk-very-high td {{
      background: #efb8b8;
    }}

    .report-section {{
      margin-bottom: 18px;
      page-break-inside: auto;
      break-inside: auto;
    }}

    .subsection-block {{
      page-break-inside: avoid;
      break-inside: avoid;
      margin-bottom: 10px;
    }}

    .footer-note {{
      margin-top: 34px;
      padding-top: 10px;
      border-top: 1px solid #d1d5db;
      color: var(--muted);
      font-size: 9pt;
    }}

    .disclaimer-section {{
      page-break-before: auto;
      break-before: auto;
    }}

    @media print {{
      body {{
        margin: 0;
      }}

      .topbar,
      .report-subtitle,
      .cover,
      .method-note {{
        page-break-inside: avoid;
        break-inside: avoid;
      }}

      .subsection-block {{
        page-break-inside: avoid;
        break-inside: avoid;
      }}
    }}
  </style>
</head>

<body>
  <header class="topbar">
    <div class="brand">
      {logo_html}
    </div>
    <div class="report-label">
      Movement Analysis<br>
      Risk Report
    </div>
  </header>

  <p class="report-subtitle">
    Assessment of task-specific movement patterns to identify ergonomic risks and support injury prevention strategies.
  </p>

  <section class="cover">
    <div class="metadata">
      <div class="label">Task:</div><div>{escape(metadata.get("task_name", "Not specified"))}</div>
      <div class="label">Company:</div><div>{escape(metadata.get("client_name", "Not specified"))}</div>
      <div class="label">Site / Location:</div><div>{escape(metadata.get("site_location", "Not specified"))}</div>
      <div class="label">Assessment Date:</div><div>{escape(metadata.get("assessment_date", "Not specified"))}</div>
      <div class="label">Assessment Method:</div><div>{escape(metadata.get("assessment_method", "Not specified"))}</div>
      <div class="label">Video Duration:</div><div>{escape(metadata.get("video_duration", "Not specified"))}</div>
      <div class="label">Assessor:</div><div>{escape(metadata.get("assessor", "Not specified"))}</div>
    </div>
  </section>

  {method_note}

  {_section("Section 1 – Assessment Overview", assessment_overview)}
  {_section("Section 2 – Summary of Assessment Results", summary_body)}
  {_section("Section 3 – Task-Based Risk Exposure Analysis", risk_body)}
  {_section("Section 4 – Overall Observations", observations_body)}
  {_section("Section 5 – Overall Recommendations", recommendations_body)}
  {_section("Section 6 – Targeted Vergo Training Videos", training_body)}
  {_section("Section 7 – Disclaimer", _p(DISCLAIMER_TEXT), css_class="disclaimer-section")}

  <div class="footer-note">
    {escape(metadata.get("client_name", "Not specified"))} – {escape(metadata.get("task_name", "Not specified"))} | www.vergo.ai
  </div>
</body>
</html>
"""

    html = _cleanup_leaked_heading_content(html)
    html = _fix_leaked_heading_content_text(html)
    output_path.write_text(html, encoding="utf-8")
    print(f"HTML report saved to: {output_path}")
    return output_path

def _cleanup_leaked_heading_content(html: str) -> str:
    pattern = re.compile(
        r'<p>heading:\\s*(.*?)\\s*content:\\s*(.*?)</p>',
        re.IGNORECASE | re.DOTALL,
    )
    return pattern.sub(lambda m: f"<h3>{escape(_clean_text(m.group(1)))}</h3><p>{escape(_clean_text(m.group(2)))}</p>", html)



def _fix_leaked_heading_content_text(html: str) -> str:
    html = re.sub(
        r'heading:\s*Assessment Method Note\s*</p>\s*<p>\s*content:\s*',
        r'<strong>Assessment Method Note</strong></p><p>',
        html,
        flags=re.IGNORECASE,
    )
    html = re.sub(
        r'heading:\s*Assessment Method Note\s*<br\s*/?>\s*content:\s*',
        r'<strong>Assessment Method Note</strong><br>',
        html,
        flags=re.IGNORECASE,
    )
    html = html.replace("heading: Assessment Method Note", "Assessment Method Note")
    html = html.replace("content: Because this assessment used", "Because this assessment used")
    return html
