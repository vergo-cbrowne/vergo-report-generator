from __future__ import annotations

from typing import Any


REBA_BANDS = [
    (1, 1, "Negligible", "No action required unless other task factors indicate concern."),
    (2, 3, "Low", "Change may be required, particularly if the task is frequent or sustained."),
    (4, 7, "Medium", "Further review is recommended. Practical improvements may reduce cumulative exposure."),
    (8, 10, "High", "Further investigation and changes should be prioritized."),
    (11, 15, "Very High", "Prompt changes are recommended."),
]


RULA_BANDS = [
    (1, 2, "Acceptable", "Acceptable if not maintained or repeated for long periods."),
    (3, 4, "Further Review", "Further investigation is recommended. Changes may be needed."),
    (5, 6, "Action Soon", "Investigation and changes are recommended soon."),
    (7, 7, "Action Now", "Investigation and changes are recommended promptly."),
]


SAFETY_MANAGER_INTERPRETATION = (
    "REBA and RULA scores should be used as ergonomic screening indicators, not as a standalone "
    "determination that a task is safe or unsafe. The score reflects the postures visible in the "
    "video sample and should be interpreted alongside task frequency, duration, force or load, "
    "repetition, recovery time, work pace, environmental conditions, worker variability, and whether "
    "the video reflects typical work. The purpose of this report is to support prevention by identifying "
    "practical opportunities to reduce cumulative strain. A score does not mean that injury is expected "
    "or inevitable."
)


def _safe_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(str(value).strip())
    except Exception:
        return None


def _collect_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_collect_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_collect_text(v) for v in value)
    if value is None:
        return ""
    return str(value)


def infer_method(report: dict[str, Any]) -> str:
    text = _collect_text(report).lower()

    if "rula" in text:
        return "RULA"

    if "reba" in text:
        return "REBA"

    return "REBA"


def band_for_score(method: str, score: float | None) -> tuple[str, str]:
    if score is None:
        return "Not specified", "Risk band could not be determined from the available score."

    bands = RULA_BANDS if method.upper() == "RULA" else REBA_BANDS

    for low, high, label, interpretation in bands:
        if low <= score <= high:
            return label, interpretation

    return "Not specified", "Risk band could not be determined from the available score."


def find_average_score(report: dict[str, Any]) -> float | None:
    """
    Look for common average score fields from AI output/report.json.
    """
    possible_keys = {
        "average_score",
        "average_reba_score",
        "average_rula_score",
        "avg_score",
        "mean_score",
        "valid_frame_average",
        "average_score_valid_frames",
    }

    def walk(value: Any) -> float | None:
        if isinstance(value, dict):
            for key, item in value.items():
                normalized = str(key).lower().replace(" ", "_").replace("-", "_")
                if normalized in possible_keys:
                    parsed = _safe_float(item)
                    if parsed is not None:
                        return parsed

            for item in value.values():
                found = walk(item)
                if found is not None:
                    return found

        elif isinstance(value, list):
            for item in value:
                found = walk(item)
                if found is not None:
                    return found

        return None

    return walk(report)


def normalize_assessment_method(report: dict[str, Any]) -> dict[str, Any]:
    cover = report.get("cover_details", {}) or {}

    method_text = str(
        cover.get("assessment_method")
        or cover.get("Assessment method")
        or cover.get("Assessment Method")
        or ""
    )

    if "rula" in method_text.lower():
        normalized = "RULA (Rapid Upper Limb Assessment)"
    elif "reba" in method_text.lower() or "template" in method_text.lower():
        normalized = "REBA (Rapid Entire Body Assessment)"
    else:
        normalized = method_text or "REBA (Rapid Entire Body Assessment)"

    cover["assessment_method"] = normalized
    cover["Assessment method"] = normalized
    cover["Assessment Method"] = normalized
    report["cover_details"] = cover

    return report


def add_safety_manager_interpretation(report: dict[str, Any]) -> dict[str, Any]:
    """
    Adds a plain-language interpretation block for safety managers.
    """
    method = infer_method(report)
    average_score = find_average_score(report)
    band, interpretation = band_for_score(method, average_score)

    score_text = "the available score"
    if average_score is not None:
        score_text = f"the average {method} score of {average_score:g}"

    report["safety_manager_interpretation"] = {
        "heading": "Safety Manager Interpretation",
        "content": (
            f"Based on {score_text}, this task falls in the {band} risk band. "
            f"{interpretation} "
            f"{SAFETY_MANAGER_INTERPRETATION}"
        ),
        "method": method,
        "average_score": "" if average_score is None else str(average_score),
        "risk_band": band,
    }

    return report


def normalize_risk_language(report: dict[str, Any]) -> dict[str, Any]:
    """
    Adds authoritative score interpretation fields.
    This does not try to rewrite every AI paragraph, but gives the HTML builder
    reliable fields to display and gives the prompt a safer structure going forward.
    """
    report = normalize_assessment_method(report)
    report = add_safety_manager_interpretation(report)
    return report
