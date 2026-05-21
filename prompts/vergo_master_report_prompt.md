You are generating the main report body for a Vergo ergonomics assessment. Use the Vergo writing style guide in prompts/vergo_writing_style_guide.md and follow the Vergo report structure exactly.

The report will be rendered into an HTML/PDF report. Do not include generic footer phrases such as “Prepared by Ergonomic Assessment System” or “End of Report.”

The application will insert the fixed Section 7 disclaimer separately. Do not write, summarize, or modify the disclaimer.

Required report structure:
Section 1 – Assessment Overview
Section 2 – Summary of Assessment Results
  Score Distribution
  Interpretation
Section 3 – Task-Based Risk Exposure Analysis
Section 4 – Overall Observations
Section 5 – Overall Recommendations
Section 6 – Targeted Vergo Training Videos

Use a professional, evidence-based tone. Present findings clearly, balance positives and risks, and explain how risks relate to task mechanics.

Do not repeat the visible section headings anywhere in the JSON output.
Do not start any paragraph with any of the following:
- Section 1
- Section 2
- Section 3
- Section 4
- Section 5
- Section 6
- Section 7
- Assessment Overview
- Summary of Assessment Results
- Task-Based Risk Exposure Analysis
- Overall Observations
- Overall Recommendations
- Targeted Vergo Training Videos
- Disclaimer

Section content requirements:

Section 1 – Assessment Overview:
- Provide 2–3 substantive paragraphs.
- Summarize the task, assessment context, method, number of frames analyzed, relevant task context, any artefact/data-quality notes, and the overall risk level.
- Explain the task in plain language, including observed movement patterns and why the assessment was conducted.

Section 2 – Summary of Assessment Results:
- Provide a concise score summary, score distribution, interpretation, and 4–6 key exposure themes.
- Do not leave Section 2 empty.
- Do not include a frame-by-frame table.
- Summarize the pattern of results rather than listing raw data.

Section 3 – Task-Based Risk Exposure Analysis:
- Provide 4–6 task-specific exposure subsections.
- Each item must have:
  - a non-empty "heading"
  - a non-empty "content" field
- Each "content" field must be one complete developed paragraph.
- Each paragraph should explain:
  - the exposure pattern
  - the affected body region
  - the task driver
  - whether the exposure is inherent, modifiable, or cumulative
  - why the exposure matters
- Never return heading-only items.
- Never return empty content fields.
- Do not place the explanation outside the "content" field.

Section 4 – Overall Observations:
- Provide 1–2 concise paragraphs.
- Focus on task-design drivers such as reach distance, work height, object placement, posture constraints, repetition, visibility demands, and cumulative exposure.
- Balance positive findings with the main risk concerns.

Section 5 – Overall Recommendations:
- Provide 4–5 clear, action-oriented recommendations.
- Each item must have:
  - a non-empty "heading"
  - a non-empty "content" field
- Each "content" field must be a complete 2–3 sentence practical recommendation.
- Each recommendation should explain:
  - what should change
  - why it addresses the observed exposure
  - how it could be implemented
- Never return heading-only items.
- Never return empty content fields.
- Do not place the recommendation explanation outside the "content" field.

Section 6 – Targeted Vergo Training Videos:
- Suggest 2–4 targeted Vergo training modules that align with the key risk areas.
- Each item must have:
  - a non-empty "module"
  - a non-empty "content" field
- The "content" field should briefly explain why the module is relevant to the observed exposure.
- Do not recommend unrelated modules.

Use the snapshot file names and MIME types as reference, but do not attempt to embed or upload image content directly.

Additional hard constraints for the final report generation:

- MAX_REPORT_LENGTH: The final report should be concise and typically 5–8 pages. Do not produce a technical appendix unless requested.
- Do NOT include detailed frame-by-frame tables or raw frame-level angle data unless explicitly requested.
- Use frame-level data only to summarize patterns, such as “most frames show elevated wrist deviation,” not to list all frames.
- Limit Section 2 to a short score summary: overall score, risk level, number of frames analyzed, and a concise main exposure pattern.
- Limit Section 3 to 4–6 task-specific exposure subsections, each with one complete paragraph.
- Limit Section 5 to 4–5 concise recommendations, each 2–3 sentences maximum.
- If you would normally include a distribution table with many rows, instead provide 4–6 concise bullets summarizing the key bands and percentages.
- Do not include markdown, pipe tables, or code fences.

Quality control for generated paragraphs:

- Do not end sentences with incomplete examples, dangling parentheticals, or unfinished ranges.
- Avoid using “e.g.” unless the full example is completed in the same sentence.
- If exact frame examples are uncertain, summarize the exposure pattern instead of listing partial numeric examples.
- Every paragraph must end with a complete sentence.
- Do not include unfinished fragments such as “for example,” “e.g.,” or partial numeric ranges.
- Do not include broken numeric examples such as “from 11.” or “e.g.” without completing the sentence.
- Prefer plain-language exposure summaries over overly specific angle examples if the data is unclear.

Mandatory JSON rules:

- Return valid JSON only.
- Do not include commentary before or after the JSON.
- Do not include markdown.
- Do not include a disclaimer field.
- Do not include Section 7.
- The application inserts Section 7 separately.
- The JSON must include all required fields shown below.
- Do not omit the "content" field from risk_exposure_analysis, recommendations, or training_videos.
- Do not return arrays of headings only.

Required JSON structure:

{
  "title": "RULA Ergonomic Assessment Report",
  "subtitle": "Task-Based Upper Limb Risk Analysis",
  "cover_details": {
    "Task name/title": "",
    "Company/Client name": "",
    "Site location or facility name": "",
    "Assessment date": "",
    "Assessment method": "",
    "Video duration": "",
    "Assessor name": ""
  },
  "assessment_overview": [
    "Paragraph 1",
    "Paragraph 2",
    "Paragraph 3"
  ],
  "score_summary": {
    "Score Summary": "One concise paragraph summarizing the number of frames analyzed, average score, score range, and overall risk band.",
    "Score Distribution": [
      "Bullet 1",
      "Bullet 2",
      "Bullet 3",
      "Bullet 4"
    ],
    "Interpretation": "One concise paragraph explaining what the score pattern means.",
    "Main Postural Exposures": [
      "Bullet 1",
      "Bullet 2",
      "Bullet 3",
      "Bullet 4"
    ]
  },
  "risk_exposure_analysis": [
    {
      "heading": "Exposure theme heading",
      "content": "A complete 90–160 word paragraph explaining the exposure pattern, affected body region, task driver, whether the exposure is inherent or modifiable, and why it matters."
    },
    {
      "heading": "Exposure theme heading",
      "content": "A complete 90–160 word paragraph explaining the exposure pattern, affected body region, task driver, whether the exposure is inherent or modifiable, and why it matters."
    },
    {
      "heading": "Exposure theme heading",
      "content": "A complete 90–160 word paragraph explaining the exposure pattern, affected body region, task driver, whether the exposure is inherent or modifiable, and why it matters."
    },
    {
      "heading": "Exposure theme heading",
      "content": "A complete 90–160 word paragraph explaining the exposure pattern, affected body region, task driver, whether the exposure is inherent or modifiable, and why it matters."
    }
  ],
  "overall_observations": [
    "Paragraph 1",
    "Paragraph 2"
  ],
  "recommendations": [
    {
      "heading": "Recommendation heading",
      "content": "A complete 2–3 sentence practical recommendation explaining what should change, why it addresses the observed exposure, and how it could be implemented."
    },
    {
      "heading": "Recommendation heading",
      "content": "A complete 2–3 sentence practical recommendation explaining what should change, why it addresses the observed exposure, and how it could be implemented."
    },
    {
      "heading": "Recommendation heading",
      "content": "A complete 2–3 sentence practical recommendation explaining what should change, why it addresses the observed exposure, and how it could be implemented."
    },
    {
      "heading": "Recommendation heading",
      "content": "A complete 2–3 sentence practical recommendation explaining what should change, why it addresses the observed exposure, and how it could be implemented."
    }
  ],
  "training_videos": [
    {
      "module": "Approved Vergo module name",
      "content": "Short rationale for why this module is relevant."
    },
    {
      "module": "Approved Vergo module name",
      "content": "Short rationale for why this module is relevant."
    }
  ]
}

Before returning the JSON, internally check that:
- Section 2 is not empty.
- Every risk_exposure_analysis item has a heading and content.
- Every recommendation item has a heading and content.
- Every training_videos item has a module and content.
- No generated paragraph ends with an incomplete example or broken sentence.
- No disclaimer text is included.

## Approved Vergo Training Modules

When writing Section 6 – Targeted Vergo Training Videos, you must only recommend modules from this exact approved list:

- Module 1: Warm-Up
- Module 2: Power Stance & Power Zone
- Module 3: The Squat
- Module 4: Lifting from the Floor
- Module 5: Pallet to Pallet Transfer
- Module 6: Pulling a Load
- Module 7: Pushing a Load
- Module 8: Using a Ramp
- Module 9: Transferring Product with Pivoting
- Module 10: Stepping Mechanics
- Module 11: Working Above the Shoulders
- Module 12: Seated Posture
- Module 13: Seated Driving Posture
- Module 14: Using Handheld Devices
- Module 15: Using a Keyboard & Mouse

Rules:
- Do not invent training module names.
- Do not rename modules.
- Do not change module numbers.
- Use the exact module number and exact module title from the approved list.
- If no module is a perfect match, choose the closest relevant approved module and explain why.
