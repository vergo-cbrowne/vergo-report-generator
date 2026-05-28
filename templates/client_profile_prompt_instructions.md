# Client Profile Prompt Instructions

When CLIENT PROFILE CONTEXT is available, use it to tailor the report to the client’s industry, operations, work environment, and practical safety priorities.

The client profile may help inform:
- the introduction
- task interpretation
- wording of ergonomic exposure findings
- examples of practical controls
- industry-specific recommendation language
- supervisor or safety-team focused recommendations

Do not invent company facts.

Only use facts from:
- CLIENT PROFILE CONTEXT
- task_context.txt or other task notes
- report.json
- status.json
- snapshots
- observed video evidence
- the approved Vergo report prompt

Observed task evidence takes priority over the client profile.

If the client profile is missing, incomplete, or not relevant to the observed task, keep the report general and rely on the observed task evidence.

Missing client profile context should not block report generation.
