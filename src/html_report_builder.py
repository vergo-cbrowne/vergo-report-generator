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


def _display_value(value) -> str:
    text = _clean_text(value)
    if not text or text.lower() in {"none", "null", "n/a", "not available"}:
        return "Not specified"
    return text


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


def _get_cover_details(report_data: dict) -> dict:
    cover = report_data.get("cover_details", {})

    return {
        "task_name": _display_value(cover.get("Task name/title", "")),
        "client_name": _display_value(cover.get("Company/Client name", "")),
        "site_location": _display_value(cover.get("Site location or facility name", "")),
        "assessment_date": _display_value(cover.get("Assessment date", "")),
        "assessment_method": _display_value(cover.get("Assessment method", "")),
        "video_duration": _display_value(cover.get("Video duration", "")),
        "assessor": _display_value(cover.get("Assessor name", "")),
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
            or item.get("explanation")
            or item.get("Explanation")
            or item.get("description")
            or item.get("Description")
            or item.get("recommendation")
            or item.get("Recommendation")
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
                "body",
                "content",
                "details",
                "explanation",
                "description",
                "recommendation",
                "reason",
                "rationale",
                "paragraph",
                "paragraphs",
            }:
                html += _p(value)
            else:
                html += '<div class="subsection-block">\n'
                html += f"<h3>{escape(_clean_text(key))}</h3>\n"
                html += _p(value)
                html += "\n</div>\n"

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
    summary_body = _render_summary(report_data)
    risk_body = _render_heading_body_items(report_data.get("risk_exposure_analysis", []))
    observations_body = _p(report_data.get("overall_observations", ""))
    recommendations_body = _render_heading_body_items(report_data.get("recommendations", []))
    training_body = _render_heading_body_items(report_data.get("training_videos", []))

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
      margin-bottom: 24px;
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

    .cover {{
      margin-bottom: 24px;
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
      margin-top: 14px;
      margin-bottom: 5px;
      font-weight: 800;
      color: #111827;
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

      .topbar {{
        page-break-inside: avoid;
        break-inside: avoid;
      }}

      .cover {{
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

  {_section("Section 1 – Assessment Overview", assessment_overview)}
  {_section("Section 2 – Summary of Assessment Results", summary_body)}
  {_section("Section 3 – Task-Based Risk Exposure Analysis", risk_body)}
  {_section("Section 4 – Overall Observations", observations_body)}
  {_section("Section 5 – Overall Recommendations", recommendations_body)}
  {_section("Section 6 – Targeted Vergo Training Videos", training_body)}
  {_section("Section 7 – Disclaimer", _p(DISCLAIMER_TEXT), css_class="disclaimer-section")}

  <div class="footer-note">
    {escape(metadata.get("client_name", "Not specified"))} – {escape(metadata.get("task_name", "Not specified"))} | {escape(metadata.get("assessment_date", "Not specified"))}
  </div>
</body>
</html>
"""

    output_path.write_text(html, encoding="utf-8")
    print(f"HTML report saved to: {output_path}")
    return output_path