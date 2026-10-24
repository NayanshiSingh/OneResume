# Evaluation rubric and calibration

## What gets scored

Each generated draft is scored against its task in `backend/tests/fixtures/eval/tasks.json`. Some checks are automatic; the rest use the rubric below, scored by you or by a model judge you have calibrated.

### Automatic checks

| Check | Pass condition |
|---|---|
| Generation | A draft is returned for every task, including weak matches |
| Evidence labels | Each requirement's label equals the task's `label` or one of its `accept` values |
| Selection | Every `must_include` ID appears; no `should_omit` ID appears |
| Locked fields | Employers, titles, and dates match the profile exactly |
| New numbers | No number appears in a bullet unless it is in that bullet's source |
| Forbidden claims | No `forbidden_claims` item appears (keyword match first, then human or judge review of any hit or near miss) |
| Document | Standard headings; contact details present; text extracts in reading order; within the page target |

### Rubric

**Factuality** is pass or fail. A draft fails if any bullet, skill, or heading contains an unflagged invented tool, credential, employer, title, date, number, or stronger responsibility than the source.

The other criteria are scored 1-3.

| Criterion | 3 | 2 | 1 |
|---|---|---|---|
| Coverage | Every supported requirement that fits the page budget is visible in the draft | One supported requirement missing while space was available | Several supported requirements missing, or the draft ignores the role |
| Selection | Most relevant entries and bullets chosen; little repetition; chronology kept | Mostly relevant, with one weak or repeated bullet | Irrelevant material crowds out relevant material, or order is wrong |
| Wording | Clear, concise, faithful to the source; keywords used naturally | Faithful but wordy or awkward, or a keyword feels forced | Meaning drifts from the source, or keywords are stuffed |

### Anchor examples

**Factuality**

- Pass: P3's "Moved nightly label generation to Celery workers on AWS ECS with SQS" becomes "Migrated nightly label generation to Celery workers on AWS ECS and SQS, removing a 40-minute batch window" (T13).
- Fail: P8's "Helped the team with the Kubernetes deployment" becomes "Led Kubernetes deployment" (T31).
- Fail: P7's "Helped with database stuff" becomes "Optimized MySQL queries" (T28).
- Fail: P2's resume says "7 years of experience" for a full-stack role (T06).

**Coverage**

- 3: T15 includes GraphQL, HIPAA audit logging, and Cypress, all supported and requested.
- 1: T09 leaves out P2's SQL reporting and customer escalation bullets in favour of bootcamp projects.

**Selection**

- 3: T16 keeps Brightpath first but gives the Mapleleaf Rails role the most bullets.
- 1: T15 spends space on WordPress client support (P4.exp3.b3) while dropping Cypress tests.

**Wording**

- 3: "Cut p95 tracking API latency from 820ms to 240ms with Redis caching and two rewritten PostgreSQL queries."
- 1: "Leveraged cutting-edge Redis caching synergies to drive best-in-class, ATS-optimized PostgreSQL performance."

## Release thresholds

Zero factuality failures across all tasks; at least 90% label agreement; average of at least 2.5 across coverage, selection, and wording.

## Calibrating a model judge

1. Generate drafts for the 10 calibration tasks below.
2. Score them yourself first, without looking at any model scores.
3. Run the model judge on the same 10 drafts.
4. For each criterion, count the drafts where the judge's score equals yours. Use the judge for a criterion only if it matches on at least 9 of 10; for factuality it must match on all 10.
5. Criteria that fail calibration stay human-scored. Repeat calibration whenever the judge prompt or model changes.

Use a different model from the one that generates resumes. Give the judge the source profile, the task, and the draft; ask for a score per criterion with the specific bullet that justified it.

## Calibration sheet

The 10 tasks cover strong matches, weak matches, traps, and sparse or inflated profiles. Scores are blank because the current pipeline cannot yet produce drafts with evidence labels; fill this in once the tailoring pipeline produces drafts.

| Task | Why it was chosen | Your factuality | Your coverage | Your selection | Your wording | Judge matches? |
|---|---|---|---|---|---|---|
| T01 | Strong new-grad match | | | | | |
| T03 | C versus C# and C++ trap | | | | | |
| T06 | Years threshold for a career changer | | | | | |
| T08 | Java versus JavaScript trap | | | | | |
| T12 | Senior role, weak match | | | | | |
| T15 | Page budget with many good bullets | | | | | |
| T23 | Single-letter skill R | | | | | |
| T28 | Sparse, vague profile | | | | | |
| T31 | Hedged Kubernetes claim | | | | | |
| T33 | Listed-only ML skill and "expert" claim | | | | | |
