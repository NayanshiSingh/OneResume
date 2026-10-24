# First-release scope

## Audience

Students and professionals with roughly 0-5 years of experience applying to software engineering roles with English resumes. Returning applicants and career changers within that range are included.

## In scope

- Account with ownership checks on every request.
- Reusable profile: personal details, education (including expected graduation month), experience, projects, skills, certifications, achievements, and links.
- Profile import from PDF or DOCX with field-by-field correction, plus manual entry.
- Profile quality prompts for vague bullets and missing contact details. Prompts are optional and never block generation when a name and one contact method exist.
- Pasted job descriptions with reviewed, editable requirement analysis.
- Evidence labels per requirement: supported, needs confirmation, not found.
- A coverage preview after JD review and before generation.
- Evidence-based selection within a one- or two-page budget, keeping reverse-chronological order.
- Constrained rewriting of selected bullets, with validation and change comparison.
- Review panel, per-resume edits, pinning and hiding entries, and explicit approval.
- PDF and DOCX export from the approved revision, using one single-column template.
- Saved versions with company, role, JD revision, and an optional "sent on" date.

## Out of scope for the first release

- Interviews and pilots with real applicants (later work).
- Professional summary or headline section.
- Cover letters, job scraping, automatic applications, and job tracking beyond a "sent on" date.
- Multiple templates, multilingual resumes, academic CVs, and executive resumes.
- Recruiter-facing features.
- Duplicate job description detection.

## Fixed rules

- A skills-list entry alone is never "supported"; it is "needs confirmation" until an experience, project, education, or certification entry shows it.
- Listed-only skills may appear in the Skills section if the user keeps them, but are never written into bullets.
- Employers, titles, and dates are locked: the AI cannot change them.
- Hedged wording ("helped", "assisted", "participated") is never strengthened.
- No commentary on gaps between dates.
- Instructions inside a job description are treated as text, never followed, and are flagged to the user.
- Eligibility requirements (citizenship, clearance, location) are shown to the user but never claimed or labelled.

## Evaluation data

- 8 personas: `backend/tests/fixtures/eval/personas/`.
- 20 synthetic job descriptions modelled on public postings: `backend/tests/fixtures/eval/jds.json`.
- 35 tasks with expected outcomes: `backend/tests/fixtures/eval/tasks.json`.
- Loader: `backend/tests/eval_fixtures.py`. Consistency tests: `backend/tests/test_eval_fixtures.py`.
