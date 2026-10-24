# Assumptions register

Every assumption below shapes the first release but has not been checked with real applicants. The validation column describes later work with real applicants: interviews and a limited pilot.

Sources:

- **Persona:** came from the AI persona set or walkthroughs. Treat as a hypothesis.
- **Public guidance:** published career-office or recruiting guidance (links below). Describes common advice, not measured behaviour of this audience.
- **Product decision:** a deliberate choice made for the first release.

| ID | Assumption | Source | Confidence | Affects | How to validate later |
|---|---|---|---|---|---|
| A1 | Early-career software applicants have more relevant material than fits on one page, so selection is valuable | Persona (P1, P4) | Medium | Core value | Interviews: compare full history with submitted resumes |
| A2 | One page is the normal target for 0-5 years of experience | Public guidance [1][2] | Medium-high | Page budget, layout | Interviews: ask about page limits they use or are told |
| A3 | Applicants tailor mainly by choosing and reordering existing bullets, not by writing new content | Persona (P3, P4) | Medium | Selection before rewriting | Observe a real tailoring session |
| A4 | Applicants will review a draft if each change shows its source | Persona (P2, P6, P8) | Low | Review panel, approval | Pilot: measure review completion and reverted suggestions |
| A5 | Seeing evidence gaps before applying is useful rather than discouraging | Persona (P5) | Low | Coverage preview | Pilot: ask whether gap reports changed what they applied to |
| A6 | Employers use ATS mainly to store, search, and filter; a recruiter makes most decisions | Public guidance [2][3] | Medium | "Compatibility checks, not a pass guarantee" | Not directly testable by this product; keep the claim modest |
| A7 | Plain single-column text PDFs and DOCX are the safest formats | Public guidance [1][2] | Medium-high | Template choice | Text-extraction checks on exported files |
| A8 | Keywords help only when used naturally and backed by real experience | Public guidance [3] | Medium | Keyword coverage rules | Pilot feedback on suggested wording |
| A9 | A skills-list entry alone is not enough evidence to call a requirement supported | Product decision | High (as a rule) | Evidence labels | Pilot: how often users confirm listed-only skills |
| A10 | Graduation month matters for new-grad and internship postings, which use month windows | Persona (P1) and job postings [4] | Medium | Education data model | Interviews and JD sample review |
| A11 | Returning applicants do not want the tool to comment on career breaks | Persona (P6) | Medium | Date checks, warnings | Interviews with returning applicants |
| A12 | Vague profiles are better fixed by asking targeted questions than by AI guessing | Persona (P7) and product decision | High (as a rule) | Profile quality prompts | Pilot: question completion rate |
| A13 | Job descriptions may contain text that tries to instruct AI tools | Product decision | High | JD handling, safety tests | Keep injection cases in the evaluation set |
| A14 | Pasted text is enough for job descriptions in the first release | Product decision | Medium | JD input | Interviews: how applicants collect postings |
| A15 | Software engineering in English is a narrow enough first audience | Product decision | Medium | Scope, evaluation data | Interviews and pilot recruitment |

## Public sources

1. University of Texas at Dallas, Jonsson School: Technical resume best standards and practices. https://engineering.utdallas.edu/engage/students/technical-resume-best-standards-and-practices/
2. TechScreen: Software engineer resume guide 2026. https://techscreen.app/articles/software-engineer-resume-ats-guide-2026
3. Ohio State Engineering Career Services: Who or what is reading my resume? https://www.ecs.osu.edu/news/2026/01/who-or-what-reading-my-resume
4. Example of a month-window new-grad posting (Visa, graduating May 2026 - August 2027). https://visa.wd5.myworkdayjobs.com/en-US/Visa_Talent_Portal/job/SW-Engineer_REF085347W
