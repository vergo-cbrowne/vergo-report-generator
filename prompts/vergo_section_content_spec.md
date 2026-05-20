# Vergo Report Section Content Specification

This specification defines the required structure, length, detail level, and style for each section of a Vergo ergonomic assessment report. Generated content must match the professional consulting style and section-level detail found in the sample reports.

The Word template already contains the visible section headings for each section. Do not repeat these section headings in the JSON output or at the start of any paragraph.

---

## Cover / Front Matter

**Purpose**: Present the assessment task and key metadata without narrative.

**Required Fields**:
- Task name/title
- Company/Client name
- Site location or facility name
- Assessment date
- Assessment method (e.g., REBA, RULA)
- Video duration (if available)
- Assessor name (if available)

**Content Rules**:
- Do not generate extra narrative.
- Do not add section introductions.
- Preserve the template's existing title, subtitle, logo, and layout.
- Only populate the metadata fields above.

---

## Section 1 – Assessment Overview

**Purpose**: Introduce the assessed task, explain the assessment method, frame details, and context.

**Structure**:
- 2–3 substantive paragraphs
- No recommendations
- No detailed results yet

**Required Content**:
- What task was assessed
- REBA or RULA method used
- Frame count and video duration
- Relevant task context (load, frequency, equipment, environmental constraints, worker posture)
- Task-specific factors (e.g., cart design, handle height, ramp slope, kneeling posture, reach distance)
- Mention of excluded frames or artefacts if present
- Short statement of overall score and risk level where appropriate

**Length Guide**: 250–400 words total (roughly 90–150 words per paragraph)

**Style**:
- Factual and descriptive
- Ground in observed task details
- Avoid marketing language

**Example Paragraph Structure**:
1. **Paragraph 1**: Introduce the task, the method (REBA/RULA), and the assessment scope (frames analyzed, video duration).
2. **Paragraph 2**: Describe the key task conditions and context (equipment, environment, worker movement patterns).
3. **Paragraph 3** (if needed): Overall ergonomic impression and risk classification.

---

## Section 2 – Summary of Assessment Results

**Purpose**: Present quantitative summary and interpretation, not detailed results tables.

**Structure**:

### Subsection 2.1 – Score Summary
- Total frames analyzed
- Valid frames / Excluded frames (if applicable)
- Average REBA/RULA score
- Score range (if relevant)
- Overall risk level classification

**Format**: 1–2 concise paragraphs or a bulleted list.

### Subsection 2.2 – Score Distribution
- Brief description of score distribution (e.g., "60% of frames scored 6–7; 30% scored 8–9; 10% scored 10+").
- Do not include a full histogram or detailed frequency table.
- Mention the peak score and the prevalence of high-risk frames.

**Format**: 1 short paragraph or 2–3 bullets.

### Subsection 2.3 – Interpretation
- 1–2 paragraphs (150–250 words) explaining what the scores mean ergonomically.
- Explain the risk level (e.g., "a score of 8 indicates high risk requiring intervention").
- Connect the scores to real-world ergonomic hazard (e.g., "repetitive wrist deviation" or "sustained trunk flexion").
- Identify the primary postural drivers of the score.

### Subsection 2.4 – Main Postural Exposures
- 4–6 bullet points summarizing the key postural exposures driving the score.
- Use frame/angle data as supporting evidence only.
- Examples:
  - Wrist deviation >20° in 50% of frames (primary driver)
  - Trunk flexion 20–30° sustained throughout task
  - Arm abduction 45–60° during cart pushing
- Do not include a full table of joint angles or frame-by-frame measurements.

**Global Rules for Section 2**:
- Do not include frame-by-frame tables.
- Do not present raw data as technical appendix.
- Focus on synthesis and meaning, not volume of data.
- Avoid redundancy with Section 1.

---

## Section 3 – Task-Based Risk Exposure Analysis

**Purpose**: Provide the most detailed analysis by dissecting task-specific postural exposures and their ergonomic implications.

**Structure**:
- 4–6 task-specific exposure subsections
- Each subsection = 1 well-developed paragraph (90–160 words typical)
- Choose subsection headings based on the specific task observed
- Do not force the same headings every time

**Suggested Subsection Headings** (use when relevant):
- Wrist Posture and Deviation
- Lower Arm and Forearm Posture
- Upper Arms and Shoulders
- Neck and Head Posture
- Trunk and Spine Posture
- Legs and Footing
- Lower Limb Posture and Kneeling
- Duration and Cumulative Exposure
- Repetition and Task Frequency
- Hand Grip and Grasping
- Equipment or Environmental Constraints
- Load Handling and Force
- Vibration or Temperature Exposure
- Asymmetric or Twisted Postures

**Content Requirements for Each Subsection**:
1. **Opening statement**: Name the exposure and its prevalence (e.g., "Wrist deviation was present in 70% of frames").
2. **Detailed observation**: Describe the posture or movement in ergonomic terms (angles, duration, frequency, asymmetry).
3. **Measured evidence**: Include measured angles, frame references, or time duration only if they help explain the exposure (e.g., "exceeded 25° in 45 frames").
4. **Ergonomic implication**: Explain why this exposure matters (e.g., "Deviation >20° increases risk of carpal tunnel syndrome and tendon strain").
5. **Task-design driver**: If identifiable, note what feature of the task or equipment causes it (e.g., "caused by the handle height being below wrist height").

**Example Well-Developed Subsection** (100–150 words):
> **Wrist Posture and Deviation**
> 
> Sustained wrist deviation was a primary postural exposure throughout the task. Analysis of 100 frames revealed deviation >20° in 65 frames (65%), with a peak deviation of 35° observed during heavy load pushing. The deviation was predominantly radial (thumb-side) during the initial push phase and shifted to ulnar deviation during load adjustment. This degree of sustained deviation exceeds recommended limits and significantly increases the risk of overuse injuries to the wrist flexors and extensor carpi radialis longus. The deviation is driven by the cart handle height (currently 78 cm), which is below the worker's wrist height when standing with neutral shoulders, forcing the wrist into extension and radial deviation to grip the handle effectively.

**Global Rules for Section 3**:
- Do not list every frame or create a frame-by-frame inventory.
- Do not repeat Section 2's score summary.
- Do not include full biomechanical equations or research citations.
- Use measured data as supporting evidence, not as the primary content.
- Focus on the task-specific drivers and their ergonomic significance.
- This section should be 700–1200 words (4–6 subsections × 90–160 words each).

---

## Section 4 – Overall Observations

**Purpose**: Synthesize the overall ergonomic pattern and task-design drivers without repeating Section 3.

**Structure**:
- **Option A**: 2 concise paragraphs (200–300 words total)
- **Option B**: Short introductory paragraph (2–3 sentences) + 4–7 bullets (5–10 words each)
- Choose based on task complexity and observed patterns

**Required Content**:
- Overall ergonomic pattern of the task
- Primary task-design drivers (e.g., work height, reach distance, kneeling, cart design, slope, grip, task frequency, equipment constraints)
- Cross-postural insights (e.g., "the elevated work surface forces both trunk forward bending and shoulder elevation")
- Cumulative or synergistic effects if present
- Constraints that make the task inherently challenging (e.g., "cart weight and ramp slope together increase lower limb load")

**What NOT to Include**:
- Repetition of detailed exposure descriptions from Section 3
- Recommendations (reserve for Section 5)
- Statistical tables or frame counts
- New postural information not discussed in earlier sections

**Example – Paragraph Format** (Option A):
> The assessment identified a task structure that simultaneously constrains posture in multiple body regions. The combination of the low cart handle height and the need to push a loaded cart up a sloped ramp forces the worker into a forward trunk lean and elevated shoulders, while the handle position also dictates wrist extension and deviation. These postural constraints are not primarily due to worker technique but are inherent to the equipment and task geometry.
> 
> The primary ergonomic challenge is the mismatch between equipment dimensions and task demands. The cart height, handle angle, and ramp slope together create a scenario in which a neutral posture is biomechanically unachievable. Secondary factors, including the need to reposition loads during pushing and the frequency of uphill travel, further compound cumulative exposure and fatigue.

**Example – Bullets Format** (Option B):
> The task exhibits a clear pattern of multiple simultaneous postural constraints:
> - Low cart handle height forces wrist extension and deviation throughout pushing
> - Ramp incline necessitates sustained trunk forward bending and shoulder elevation
> - High cart load amplifies lower-limb load and increases force requirements
> - Task frequency (≥15 pushes/hour) compounds cumulative exposure
> - Equipment design, not worker technique, drives the observed postural pattern

**Length Guide**: 200–350 words total

---

## Section 5 – Overall Recommendations

**Purpose**: Provide specific, actionable, prioritized interventions based on the observed task.

**Structure**:
- 4–5 recommendations (do not exceed 5)
- Each recommendation has:
  - **Clear action-oriented heading** (not vague)
  - **One practical paragraph** (100–150 words typical)

**Heading Style** (Good Examples):
- Reorganise Cart Contents by Access Frequency
- Adjust Grip Position on the Roller Handle to Reduce Wrist Deviation
- Address Ramp Surface Traction and Slope Steepness
- Confirm Extension Pole Length is Set Appropriately
- Implement Two-Person Pushing During Peak Load Conditions
- Install Adjustable Workbench Height to Eliminate Reaching

**Heading Style** (Poor Examples – Avoid):
- Improve Posture
- Provide Ergonomic Training
- Use Better Equipment
- Consider Modifications

**Content Requirements for Each Recommendation**:
1. **Specific action**: Describe exactly what should be changed (not "improve," but "reduce handle height from 78 cm to 72 cm").
2. **Rationale**: Explain why this change matters (reference Section 3 findings).
3. **Expected benefit**: Briefly note the postural or load reduction (e.g., "will reduce wrist deviation to <15°").
4. **Implementation note** (optional): Add feasibility, cost, or timeline if relevant (e.g., "can be implemented immediately by adjusting the handle grip position").

**Example Well-Developed Recommendation** (100–150 words):
> **Adjust Cart Handle Height to Reduce Wrist and Shoulder Load**
> 
> Lower the cart handle from its current height of 78 cm to 70–72 cm. This adjustment will align the handle height with the worker's wrist when standing with neutral shoulders, eliminating the need for wrist extension and reducing the shoulder elevation required during pushing. Analysis of the current posture shows that wrist deviation and shoulder load are driven primarily by handle height rather than technique. Lowering the handle should reduce average wrist deviation from 25° to <15° and decrease shoulder elevation by approximately 10°. If the cart design does not allow height adjustment, consider adding a secondary grip strap or handle that positions the hand more neutrally. This intervention can be implemented immediately with minimal cost.

**Prioritization** (Optional):
- If five recommendations are provided, consider flagging the highest-impact changes (e.g., "**Priority 1**" or "**High Impact**").
- Typically, equipment/task-design changes have higher priority than training or postural cueing alone.

**Global Rules for Section 5**:
- Do not include recommendations that lack specificity (e.g., "provide training" without context).
- Do not recommend interventions not supported by Section 3 findings.
- Do not include more than 5 recommendations.
- Focus on actionable changes the employer/task designer can implement.
- Avoid training-only recommendations unless other controls cannot be modified.

---

## Section 6 – Targeted Vergo Training Videos

**Purpose**: Recommend 2–4 approved Vergo training modules relevant to the task and exposures.

**Structure**:
- 2–4 modules (do not exceed 4)
- Each module entry includes:
  - **Module name and number** (from approved Vergo training library)
  - **One short paragraph** (50–80 words) explaining why it applies

**Approved Vergo Training Modules**:
(Insert the list of approved Vergo modules available to your system. Examples below are hypothetical.)
- Module 1: Ergonomic Principles and Risk Factors
- Module 2: Wrist Health and Posture
- Module 3: Shoulder and Neck Health
- Module 4: Trunk Health and Spinal Mechanics
- Module 5: Lower Limb Posture and Kneeling
- Module 6: Load Handling and Force Reduction
- Module 7: Cart and Equipment Design
- Module 8: Cumulative Trauma and Repetition

**Content Requirements**:
1. **Module selection**: Choose modules that address the primary postural exposures from Section 3.
2. **Relevance paragraph**: Explain briefly why the module applies (e.g., "This task involves sustained wrist deviation, making Module 2 essential for understanding wrist health and how posture relates to tendon strain").
3. **Avoid boilerplate**: Do not use identical language for every module; tailor the rationale to the specific task.

**Example Module Entry** (50–80 words):
> **Module 2: Wrist Health and Posture**
> 
> This task demonstrates sustained wrist deviation as a primary exposure. Module 2 provides foundational knowledge on wrist biomechanics, the relationship between posture and tendon strain, and strategies to maintain neutral wrist position in pushing and gripping tasks. The module directly supports understanding of the handle-height adjustment recommendation and reinforces awareness of wrist risk factors.

**Global Rules for Section 6**:
- Only use approved Vergo modules.
- Do not invent or rename modules.
- Do not include modules unrelated to the task.
- Do not add module links or URLs (preserve in docx_builder formatting only).
- Maximum 4 modules.

---

## Section 7 – Disclaimer

**Purpose**: Include the exact Vergo legal disclaimer.

**Content**:
- Use the exact disclaimer text provided by Vergo.
- Do not alter, shorten, or paraphrase it.
- Do not add additional disclaimers or legal language.

**Placeholder**: `{{DISCLAIMER}}`

(The disclaimer text will be provided by the system during report generation and should be stored as a constant or configuration value.)

---

## Global Rules

### Report Length
- **Target**: 6–10 pages depending on task complexity
- **Maximum**: Do not exceed 12 pages
- **Minimum**: No fewer than 5 pages for substantive tasks
- Do not create 30+ page reports with extensive tabular appendices

### Formatting and Style
- **No markdown symbols**: Do not use #, ##, ###, pipe tables (|---|), or similar markdown syntax
- **No "End of Report"**: Do not include closing lines like "End of Report" or "Prepared by Ergonomic Assessment System"
- **Consulting style**: Write in the detailed but concise style of professional ergonomic consulting reports
- **Active voice**: Prefer "The assessment revealed…" over "It was found that…"
- **Specificity**: Always ground observations in measured data or task details, not generic statements

### Data Presentation
- Do not include frame-by-frame tables unless explicitly requested
- Do not present raw or unfiltered data
- Use measured values (angles, frame counts, duration) as supporting evidence, not as the primary content
- Summarize distributions instead of listing individual measurements

### Content Relationships
- **Section 1**: Introduce the task and method
- **Section 2**: Summarize quantitative results and interpretation
- **Section 3**: Analyze task-specific exposures in detail (do not repeat Sections 1–2)
- **Section 4**: Synthesize overall pattern and drivers (do not repeat Section 3)
- **Section 5**: Provide specific recommendations (supported by Sections 3–4)
- **Section 6**: Link training modules to primary exposures
- **Section 7**: Include exact disclaimer

### Exclusions
- Do not create research-oriented or academic-style reports
- Do not include citations to external studies unless task-specific
- Do not add executive summaries beyond the cover
- Do not include worker photographs or identification details
- Do not include company proprietary information unrelated to ergonomics

---

## Prompt Integration Notes

When integrating this specification into the AI prompt:

1. **Emphasize section purposes**: Clearly state what each section should and should not contain.
2. **Provide examples**: Include 1–2 exemplar paragraphs or sections from actual Vergo reports for each major section.
3. **Define constraints**: Specify word counts, paragraph counts, and bullet counts for each section.
4. **Clarify task-specificity**: Remind the AI that section headings in Section 3 and content examples should vary based on the task, not forced into a template.
5. **Enforce elimination of markdown**: Explicitly instruct the AI to avoid markdown symbols and focus on plain text formatting.

---

## Version History

- **2026-05-19**: Initial specification document created based on sample report analysis and user requirements.

