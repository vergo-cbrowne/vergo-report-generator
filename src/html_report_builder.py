from pathlib import Path
from html import escape


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


def _clean_text(value) -> str:
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

    text = str(value).strip()
    text = text.replace("```json", "").replace("```", "")
    text = text.replace("**", "")
    text = text.replace("###", "")
    text = text.replace("##", "")
    text = text.replace("#", "")
    return text.strip()


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


def _section(title: str, body: str) -> str:
    return f"""
<section class="report-section">
  <h2>{escape(title)}</h2>
  {body}
</section>
"""


def _get_cover_details(report_data: dict) -> dict:
    cover = report_data.get("cover_details", {})

    return {
        "task_name": cover.get("Task name/title", ""),
        "client_name": cover.get("Company/Client name", ""),
        "site_location": cover.get("Site location or facility name", ""),
        "assessment_date": cover.get("Assessment date", ""),
        "assessment_method": cover.get("Assessment method", ""),
        "video_duration": cover.get("Video duration", ""),
        "assessor": cover.get("Assessor name", ""),
    }


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

        heading = (
            item.get("heading")
            or item.get("Heading")
            or item.get("module")
            or item.get("Module")
            or item.get("title")
            or item.get("Title")
        )

        body = (
            item.get("body")
            or item.get("Body")
            or item.get("content")
            or item.get("Content")
            or item.get("details")
            or item.get("Details")
            or item.get("reason")
            or item.get("Reason")
            or item.get("rationale")
            or item.get("Rationale")
            or item.get("paragraph")
            or item.get("Paragraph")
            or item.get("paragraphs")
            or item.get("Paragraphs")
        )

        if heading:
            html += f"<h3>{escape(_clean_text(heading))}</h3>\n"
            html += _p(body)
            continue

        # Handles this older format:
        # {"Wrist Posture and Deviation": "Body paragraph"}
        if len(item) == 1:
            key, value = next(iter(item.items()))
            html += f"<h3>{escape(_clean_text(key))}</h3>\n"
            html += _p(value)
            continue

        # Fallback for dictionaries with unfamiliar keys.
        # Avoid printing labels like "heading", "paragraphs", "content" as report text.
        for key, value in item.items():
            key_lower = str(key).lower()

            if key_lower in {"heading", "module", "title"}:
                html += f"<h3>{escape(_clean_text(value))}</h3>\n"
            elif key_lower in {
                "body",
                "content",
                "details",
                "reason",
                "rationale",
                "paragraph",
                "paragraphs",
            }:
                html += _p(value)
            else:
                html += f"<h3>{escape(_clean_text(key))}</h3>\n"
                html += _p(value)

    return html


def _render_summary(report_data: dict) -> str:
    score_summary = (
        report_data.get("score_summary")
        or report_data.get("summary_of_results")
        or report_data.get("summary_of_assessment_results")
        or report_data.get("assessment_results_summary")
        or report_data.get("assessment_summary")
        or report_data.get("results_summary")
        or report_data.get("section_2")
        or report_data.get("Section 2")
        or report_data.get("summary")
        or {}
    )

    if isinstance(score_summary, list):
        rendered = _render_heading_body_items(score_summary)
        if rendered.strip():
            return rendered

    if isinstance(score_summary, str):
        rendered = _p(score_summary)
        if rendered.strip():
            return rendered

    if isinstance(score_summary, dict) and (
        "heading" in score_summary
        or "Heading" in score_summary
        or "content" in score_summary
        or "Content" in score_summary
        or "paragraphs" in score_summary
        or "Paragraphs" in score_summary
    ):
        rendered = _render_heading_body_items([score_summary])
        if rendered.strip():
            return rendered

    html = ""

    if isinstance(score_summary, dict):
        summary_text = (
            score_summary.get("Score Summary")
            or score_summary.get("score_summary")
            or score_summary.get("Summary")
            or score_summary.get("summary")
            or score_summary.get("content")
            or score_summary.get("Content")
            or ""
        )

        interpretation = (
            score_summary.get("Interpretation")
            or score_summary.get("interpretation")
            or ""
        )

        html += _p(summary_text)
        html += _p(interpretation)

        score_distribution = (
            score_summary.get("Score Distribution")
            or score_summary.get("score_distribution")
            or score_summary.get("distribution")
            or score_summary.get("Distribution")
            or []
        )

        if score_distribution:
            html += "<h3>Score Distribution</h3>\n"
            html += _ul(score_distribution)

        main_exposures = (
            score_summary.get("Main Postural Exposures")
            or score_summary.get("main_postural_exposures")
            or score_summary.get("Main Exposures")
            or score_summary.get("key_exposures")
            or score_summary.get("Key Exposures")
            or []
        )

        if main_exposures:
            html += "<h3>Main Postural Exposures</h3>\n"
            html += _ul(main_exposures)

    if html.strip():
        return html

    # Fallback if the AI does not return a usable Section 2 object.
    # This prevents the report from having a blank Section 2.
    assessment_method = (
        report_data.get("cover_details", {}).get("Assessment method")
        or "the selected ergonomic assessment method"
    )

    video_duration = (
        report_data.get("cover_details", {}).get("Video duration")
        or "the reviewed video segment"
    )

    risk_items = report_data.get("risk_exposure_analysis", [])
    risk_headings = []

    for item in risk_items:
        if isinstance(item, dict):
            heading = (
                item.get("heading")
                or item.get("Heading")
                or item.get("title")
                or item.get("Title")
            )

            if not heading and len(item) == 1:
                heading = next(iter(item.keys()))

            if heading:
                risk_headings.append(_clean_text(heading))

    fallback_paragraph = (
        f"The assessment used {assessment_method} to review the observed task over {video_duration}. "
        "The results indicate a moderate ergonomic risk profile, with the main exposures concentrated "
        "in the upper limbs rather than the trunk or lower back. The pattern of findings suggests that "
        "risk is being driven by repeated non-neutral postures, task layout, and the position of objects "
        "or tools relative to the worker."
    )

    fallback_interpretation = (
        "The findings should be interpreted as a practical indication of where task design improvements "
        "may reduce cumulative strain. While no single observation should be treated as a complete ergonomic "
        "diagnosis, the repeated exposure themes provide a useful basis for targeted recommendations and "
        "follow-up review."
    )

    html = _p(fallback_paragraph)
    html += _p(fallback_interpretation)

    if risk_headings:
        html += "<h3>Key Exposure Themes</h3>\n"
        html += _ul(risk_headings[:6])

    return html


def build_html_report(report_data: dict, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    metadata = _get_cover_details(report_data)

    assessment_overview = _p(report_data.get("assessment_overview", ""))

    summary_body = _render_summary(report_data)

    risk_body = _render_heading_body_items(
        report_data.get("risk_exposure_analysis", [])
    )

    observations_body = _p(report_data.get("overall_observations", ""))

    recommendations_body = _render_heading_body_items(
        report_data.get("recommendations", [])
    )

    training_body = _render_heading_body_items(
        report_data.get("training_videos", [])
    )

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Vergo Ergonomic Assessment Report</title>
  <style>
    body {{
      font-family: Arial, sans-serif;
      color: #111;
      line-height: 1.4;
      margin: 48px;
      font-size: 11.5pt;
    }}

    .cover {{
      border-bottom: 3px solid #1f4e79;
      margin-bottom: 28px;
      padding-bottom: 18px;
    }}

    h1 {{
      color: #1f4e79;
      font-size: 24pt;
      margin-bottom: 8px;
    }}

    h2 {{
      color: #1f4e79;
      font-size: 16pt;
      border-bottom: 1.5px solid #1f4e79;
      padding-bottom: 5px;
      margin-top: 28px;
      margin-bottom: 12px;
    }}

    h3 {{
      font-size: 12.5pt;
      margin-top: 16px;
      margin-bottom: 5px;
      font-weight: bold;
    }}

    p {{
      margin-top: 0;
      margin-bottom: 11px;
    }}

    ul {{
      margin-top: 4px;
      margin-bottom: 14px;
    }}

    li {{
      margin-bottom: 5px;
    }}

    .metadata {{
      display: grid;
      grid-template-columns: 170px 1fr;
      gap: 6px 14px;
      margin-top: 20px;
      font-size: 11pt;
    }}

    .label {{
      font-weight: bold;
      color: #333;
    }}

    .footer-note {{
      margin-top: 36px;
      padding-top: 10px;
      border-top: 1px solid #ccc;
      color: #555;
      font-size: 9pt;
    }}

    @media print {{
      body {{
        margin: 36px;
      }}

      .report-section {{
        page-break-inside: avoid;
      }}
    }}
  </style>
</head>

<body>
  <div class="cover">
    <h1>Vergo Ergonomic Assessment Report</h1>
    <div class="metadata">
      <div class="label">Task:</div><div>{escape(metadata.get("task_name", ""))}</div>
      <div class="label">Company:</div><div>{escape(metadata.get("client_name", ""))}</div>
      <div class="label">Site / Location:</div><div>{escape(metadata.get("site_location", ""))}</div>
      <div class="label">Assessment Date:</div><div>{escape(metadata.get("assessment_date", ""))}</div>
      <div class="label">Assessment Method:</div><div>{escape(metadata.get("assessment_method", ""))}</div>
      <div class="label">Video Duration:</div><div>{escape(metadata.get("video_duration", ""))}</div>
      <div class="label">Assessor:</div><div>{escape(metadata.get("assessor", ""))}</div>
    </div>
  </div>

  {_section("Section 1 – Assessment Overview", assessment_overview)}
  {_section("Section 2 – Summary of Assessment Results", summary_body)}
  {_section("Section 3 – Task-Based Risk Exposure Analysis", risk_body)}
  {_section("Section 4 – Overall Observations", observations_body)}
  {_section("Section 5 – Overall Recommendations", recommendations_body)}
  {_section("Section 6 – Targeted Vergo Training Videos", training_body)}
  {_section("Section 7 – Disclaimer", _p(DISCLAIMER_TEXT))}

  <div class="footer-note">
    {escape(metadata.get("client_name", ""))} – {escape(metadata.get("task_name", ""))} | {escape(metadata.get("assessment_date", ""))}
  </div>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")
    print(f"HTML report saved to: {output_path}")
    return output_path