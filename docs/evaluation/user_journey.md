# Persona walkthroughs and reviewed journey

## Method

Each of the 8 personas was walked through the five journey stages (account and profile, job description, generation, review, export) using one or more of its evaluation tasks. For each stage the persona was asked:

1. What would you do next, and is it clear how?
2. What information is missing for you to decide?
3. What would make you distrust or abandon the draft?

The walkthroughs were run by an AI model playing each persona. The findings are design input, not evidence about real applicants. Each one has a decision below; accepted changes are listed under Reviewed journey.

## Findings and decisions

| # | Persona (task) | Stage | Finding | Decision | Change |
|---|---|---|---|---|---|
| 1 | P1 (T01, T03) | Profile | New-grad postings use month windows ("Dec 2026 - Aug 2027"), but education stores only a year, so eligibility is always uncertain | Accept | Education records an expected graduation month |
| 2 | P1 | Export | Keeps losing track of which version went to which company | Accept | Versions can be marked "sent on" with a date |
| 3 | P2 (T06) | Generation | Fears "7 years" of operations will be counted as software experience | Accept | For years-of-experience requirements, the review panel shows which entries were counted and the computed total |
| 4 | P2 (T09) | Review | Wants operations history prominent for support roles and short elsewhere | Accept | Per-resume pin and hide controls for entries and bullets |
| 5 | P3 (T13) | Review | Sees Kubernetes "not found" and wonders whether ECS was considered | Accept | Not-found requirements show related evidence that was considered and why it did not count |
| 6 | P3 | JD | Pastes near-identical postings for similar roles | Defer | Duplicate detection is out of scope for the first release |
| 7 | P4 (T15) | Review | One-page overflow; wants control over what is cut | Accept | Overflow shows ranked removal candidates with the requirements each one covers |
| 8 | P4 (T16) | Generation | Wants the older Rails job moved above the current job for Rails roles | Reject | Reverse-chronological order is kept; emphasis comes from bullet selection. Reordering roles misleads readers about the timeline |
| 9 | P5 (T21) | JD | Wants to see gaps before spending time on a draft | Accept | Coverage preview after JD review, before generation |
| 10 | P5 | Generation | Unsure whether to lead with frontend or backend | Defer | A summary or headline section is out of scope; revisit in future scope |
| 11 | P6 (T24) | Review | Worried the AI will move or "tidy" her dates | Accept | Employers, titles, and dates are locked and visibly marked as not editable by AI |
| 12 | P6 (T27) | Review | Does not want comments about her career break | Accept | Date checks flag only invalid dates (end before start, future end), never gaps |
| 13 | P7 (T28) | Profile | Long forms are tiring; bullets are vague | Accept | Import is offered first; vague bullets get optional targeted questions ("What did you change on the website? Which tools did you use?") |
| 14 | P7 | Profile | No phone number | Accept | Warn, do not block; one contact method is enough |
| 15 | P8 (T31) | Review | Frustrated when "helped" is not upgraded to "led"; does not understand why | Accept | When a rewrite is blocked, the panel says which rule blocked it. Users can still edit wording themselves; edits are marked user-supplied and need confirmation |
| 16 | P8 (T32, T33) | Review | Many listed skills show "needs confirmation" | Accept | Listed-only skills are grouped with a prompt to add an example from experience or a project |
| 17 | P1, P3 (T05, T34) | JD | Job description contains instructions aimed at AI tools | Accept | Analysis ignores them and shows a warning that the posting contains instructions to AI tools |
| 18 | P6, P7 (T27, T29) | JD | Vague posting produces almost no requirements | Accept | Analysis says the posting lacks detail and suggests pasting a fuller description; generation falls back to the strongest overall content |
| 19 | P4 (T17) | Generation | Applying to a junior role; worried the tool will downplay experience | Accept | No change to titles or dates (covered by #11); selection can favour relevant bullets, but nothing is reworded to sound more junior |

## Reviewed journey

Accepted changes by stage:

- **A. Account and profile:** expected graduation month (#1); import first and optional questions for vague bullets (#13); warn on missing phone (#14).
- **B. Job description:** coverage preview (#9); warning for AI-directed instructions (#17); warning for postings that lack detail (#18).
- **C. Generation:** show how years of experience were counted (#3); locked employers, titles, and dates (#11, #19).
- **D. Review:** pin and hide (#4); related evidence for not-found requirements (#5); ranked overflow removals (#7); no gap commentary (#12); explain blocked rewrites (#15); grouped listed-only skills (#16).
- **E. Export:** "sent on" date for versions (#2).

Recovery paths checked for every stage: users can go back from generation to JD review and from review to profile editing without losing a draft; a failed job keeps the reviewed JD and profile revision; a failed export does not affect the approved revision.
