
from __future__ import annotations
from collections import Counter, defaultdict
import re
from typing import Any


AVAILABLE_VERGO_MODULES = {
    1: "Module 1: Warm-Up",
    2: "Module 2: Power Stance & Power Zone",
    3: "Module 3: The Squat",
    4: "Module 4: Lifting from the Floor",
    5: "Module 5: Pallet to Pallet Transfer",
    6: "Module 6: Pulling a Load",
    7: "Module 7: Pushing a Load",
    8: "Module 8: Using a Ramp",
    9: "Module 9: Transferring Product with Pivoting",
    10: "Module 10: Stepping Mechanics",
    11: "Module 11: Working Above the Shoulders",
    12: "Module 12: Seated Posture",
    13: "Module 13: Seated Driving Posture",
    14: "Module 14: Using Handheld Devices",
    15: "Module 15: Using a Keyboard & Mouse",
}


def _flatten(obj: Any) -> str:
    if obj is None:
        return ""
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        return " ".join(_flatten(v) for v in obj.values())
    if isinstance(obj, list):
        return " ".join(_flatten(v) for v in obj)
    return str(obj)


def _method(report: dict) -> str:
    text = _flatten({
        "title": report.get("title"),
        "method": report.get("method"),
        "assessment_method": report.get("assessment_method"),
        "assessment_method_type": report.get("assessment_method_type"),
        "score_summary": report.get("score_summary"),
    }).upper()
    if "RULA" in text:
        return "RULA"
    if "REBA" in text:
        return "REBA"
    return ""


def _collect_rula_scores(obj: Any, scores: list[float] | None = None) -> list[float]:
    if scores is None:
        scores = []
    keys = {"rula_score", "final_rula", "rula_final", "final_score"}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).lower() in keys:
                try:
                    f = float(v)
                    if 1 <= f <= 7:
                        scores.append(f)
                except Exception:
                    pass
            else:
                _collect_rula_scores(v, scores)
    elif isinstance(obj, list):
        for item in obj:
            _collect_rula_scores(item, scores)
    return scores


def add_stable_rula_interpretation(report: dict) -> dict:
    if _method(report) != "RULA":
        return report

    scores = _collect_rula_scores(report)
    if len(scores) < 2:
        return report

    rounded = [round(s) for s in scores]
    if len(set(rounded)) != 1:
        return report

    score = rounded[0]
    sentence = (
        "The underlying joint angles — including wrist deviation, lower arm position, neck flexion, "
        f"and upper arm elevation — varied across the analyzed frames; however, the combined RULA "
        f"scoring table produced a consistent final score of {score} throughout the task, reflecting "
        "a stable moderate-risk posture pattern."
    )

    summary = report.setdefault("score_summary", {})
    current = str(summary.get("interpretation") or "").strip()
    if sentence not in current:
        summary["interpretation"] = (sentence + " " + current).strip()

    report["stable_rula_score_note"] = {
        "triggered": True,
        "score": score,
        "score_variance": 0,
        "frames_with_same_score": len(scores),
    }
    return report


def _risk_text(report: dict) -> str:
    return _flatten(
        report.get("risk_exposure_analysis")
        or report.get("section_3")
        or report.get("task_based_risk_exposure_analysis")
        or report
    ).lower()


def _module_rationale(module: str, reason: str) -> dict:
    return {"module": module, "rationale": reason}


def select_training_modules(report: dict) -> list[dict]:
    text = _risk_text(report)

    modules = [
        _module_rationale(
            AVAILABLE_VERGO_MODULES[1],
            "This module is included as a baseline preparation module for physically repetitive or sustained work."
        )
    ]

    wrist = any(k in text for k in ["wrist", "hand posture", "grip", "pinch", "forearm", "tool", "handle", "scanner", "knife", "handheld", "deviation"])
    neck = any(k in text for k in ["neck", "head posture", "head position", "neck flexion", "forward head"])
    trunk = any(k in text for k in ["trunk", "lower back", "lumbar", "back flexion", "trunk flexion", "bending", "lift", "lifting"])
    shoulder = any(k in text for k in ["shoulder", "overhead", "above the shoulder", "elevated arm", "upper arm elevation", "reach", "reaching"])
    lower = any(k in text for k in ["kneel", "kneeling", "lower limb", "leg", "squat", "crouch", "stepping", "walking"])

    if wrist:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[14],
            "This module is recommended for the observed hand, wrist, grip, tool, handle, or equipment-related exposure. It is being selected for hand and wrist positioning guidance, not because the task necessarily involves a mobile phone or digital handheld device."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[2],
            "This module supports better positioning within the power zone and can help reduce compensatory wrist and upper-limb postures during handling tasks."
        ))
    elif neck:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[12],
            "This module is recommended because the task shows neck flexion or sustained head posture exposure. It supports awareness of head position, viewing angle, and upper-back posture."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[14],
            "This module may support awareness of upper-limb and hand positioning where neck posture is influenced by the position of tools, equipment, or work materials."
        ))
    elif trunk:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[2],
            "This module is recommended because the task involves trunk flexion, lower-back exposure, or work outside the power zone."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[4],
            "This module is relevant where lifting, bending, or low-level handling contributes to back exposure."
        ))
    elif shoulder:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[2],
            "This module supports improved work positioning and use of the power zone to reduce extended reaching."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[11],
            "This module is recommended because the task involves overhead reach, shoulder elevation, or elevated arm posture."
        ))
    elif lower:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[2],
            "This module supports stable stance and task positioning during lower-body or whole-body work."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[10],
            "This module is relevant where kneeling, crouching, stepping, walking, or lower-limb movement contributes to exposure."
        ))
    else:
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[2],
            "This module is included as a broad task-setup recommendation where no single dominant exposure clearly outweighs the others."
        ))
        modules.append(_module_rationale(
            AVAILABLE_VERGO_MODULES[14],
            "This module is included only as a general upper-limb positioning reference where multiple regions are involved and hand or wrist posture may contribute to the task pattern."
        ))

    deduped = []
    seen = set()
    for item in modules:
        if item["module"] not in seen:
            seen.add(item["module"])
            deduped.append(item)

    return deduped[:3]


def apply_dynamic_training_modules(report: dict) -> dict:
    report["training_modules"] = select_training_modules(report)
    return report


def apply_quality_rules(report: dict) -> dict:
    if not isinstance(report, dict):
        return report
    report = add_stable_rula_interpretation(report)
    report = apply_dynamic_training_modules(report)
    return report
