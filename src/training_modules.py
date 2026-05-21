from __future__ import annotations

from typing import Any


APPROVED_TRAINING_MODULES = {
    1: "Warm-Up",
    2: "Power Stance & Power Zone",
    3: "The Squat",
    4: "Lifting from the Floor",
    5: "Pallet to Pallet Transfer",
    6: "Pulling a Load",
    7: "Pushing a Load",
    8: "Using a Ramp",
    9: "Transferring Product with Pivoting",
    10: "Stepping Mechanics",
    11: "Working Above the Shoulders",
    12: "Seated Posture",
    13: "Seated Driving Posture",
    14: "Using Handheld Devices",
    15: "Using a Keyboard & Mouse",
}


MODULE_RULES = {
    11: {
        "keywords": [
            "overhead", "above shoulder", "above-shoulder", "ceiling", "raised arms",
            "upper arm elevation", "shoulder height", "ladder", "elevated position",
        ],
        "reason": "Relevant where the task involves overhead reaching, elevated arms, or work above shoulder height.",
    },
    7: {
        "keywords": [
            "push", "pushing", "cart", "loaded cart", "housekeeping cart", "utility cart",
            "forceful push", "manual push",
        ],
        "reason": "Relevant to safe body positioning, grip, and weight transfer while pushing a load.",
    },
    6: {
        "keywords": [
            "pull", "pulling", "drag", "dragging", "draw", "tug",
        ],
        "reason": "Relevant to safe body positioning and force control when pulling a load.",
    },
    8: {
        "keywords": [
            "ramp", "incline", "slope", "sloped", "down ramp", "up ramp",
        ],
        "reason": "Relevant where the worker moves equipment or materials on a ramp, incline, or sloped surface.",
    },
    4: {
        "keywords": [
            "lifting from the floor", "floor lift", "lift from floor", "floor-level lift",
            "picking up from floor", "low lift",
        ],
        "reason": "Relevant where the task involves lifting or retrieving materials from floor level.",
    },
    5: {
        "keywords": [
            "pallet", "pallet to pallet", "pallet transfer", "skid", "palletizing",
        ],
        "reason": "Relevant where the task involves transferring materials between pallets or similar surfaces.",
    },
    9: {
        "keywords": [
            "pivot", "pivoting", "transfer", "transferring product", "turning with load",
            "twisting with load", "rotate with load",
        ],
        "reason": "Relevant where the task involves transferring product while turning or pivoting.",
    },
    10: {
        "keywords": [
            "stepping", "step", "walking", "footing", "foot placement", "stride",
            "kneeling to standing", "standing to kneeling", "lower limb", "stairs",
        ],
        "reason": "Relevant to controlled stepping, foot placement, and lower-body mechanics during movement.",
    },
    12: {
        "keywords": [
            "seated", "sitting", "desk", "chair", "workstation", "table", "paper",
            "sorting", "marking", "document", "documents",
        ],
        "reason": "Relevant to seated or workstation-based tasks involving sustained neck, trunk, or upper limb postures.",
    },
    13: {
        "keywords": [
            "driving", "driver", "vehicle", "seatbelt", "cab", "forklift", "truck",
        ],
        "reason": "Relevant to posture and positioning during seated driving tasks.",
    },
    14: {
        "keywords": [
            "handheld", "hand held", "scanner", "scan gun", "phone", "tablet",
            "marker", "pen", "marking", "tool", "wrist", "wrist deviation",
            "hand", "grip", "repetitive hand",
        ],
        "reason": "Relevant to repetitive handheld tool use, wrist positioning, grip, and hand/arm posture.",
    },
    15: {
        "keywords": [
            "keyboard", "mouse", "computer", "typing", "data entry",
        ],
        "reason": "Relevant to keyboard and mouse use at computer workstations.",
    },
    3: {
        "keywords": [
            "squat", "squatting", "crouch", "crouching",
        ],
        "reason": "Relevant where a squat or crouched posture is used to access low materials.",
    },
    2: {
        "keywords": [
            "power zone", "reach", "reaching", "extended arm", "lower arm extension",
            "work area", "material placement", "neutral posture", "load handling",
            "manual handling", "arm posture", "sorting", "marking",
        ],
        "reason": "Relevant to keeping work close to the body and maintaining stronger, more neutral working postures.",
    },
    1: {
        "keywords": [
            "warm-up", "repetitive", "repetition", "microbreak", "neck", "shoulder",
            "upper limb", "wrist", "cumulative", "fatigue",
        ],
        "reason": "Relevant as general preparation for repetitive or sustained movement exposure.",
    },
}


def _collect_text(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_collect_text(item) for item in value.values())

    if isinstance(value, list):
        return " ".join(_collect_text(item) for item in value)

    if value is None:
        return ""

    return str(value)


def _score_modules(report: dict[str, Any]) -> list[int]:
    text = _collect_text(report).lower()

    scores: dict[int, int] = {}

    for module_number, rule in MODULE_RULES.items():
        score = 0

        for keyword in rule["keywords"]:
            if keyword.lower() in text:
                score += 1

        if score:
            scores[module_number] = score

    if not scores:
        return [2, 1]

    ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))
    selected = [module_number for module_number, _ in ordered[:3]]

    # Ensure a useful general module if only one was found.
    if len(selected) == 1 and selected[0] != 1:
        selected.append(1)

    return selected[:3]


def _module_item(module_number: int) -> dict[str, str]:
    title = APPROVED_TRAINING_MODULES[module_number]
    reason = MODULE_RULES[module_number]["reason"]

    return {
        "heading": f"Module {module_number}: {title}",
        "content": reason,
        "module_number": str(module_number),
        "module_title": title,
    }


def normalize_training_videos(report: dict[str, Any]) -> dict[str, Any]:
    """
    Force Section 6 training videos to use only the approved Vergo training library.
    This prevents invented modules such as 'Neutral Wrist and Arm Postures'.
    """
    if not isinstance(report, dict):
        return report

    selected_modules = _score_modules(report)
    normalized_items = [_module_item(module_number) for module_number in selected_modules]

    report["training_videos"] = normalized_items

    # Some prompt outputs may use alternate keys. Keep them aligned.
    report["targeted_training_videos"] = normalized_items
    report["targeted_vergo_training_videos"] = normalized_items

    return report
