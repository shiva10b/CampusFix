# Mini Project Rubric Mapping

## Source and interpretation

The preserved source is `Mini Project Rubrics.pdf` from Lloyd Institute of Engineering & Technology, Department of Computer Science & Engineering, session 2026-27. It defines two reviews worth 50 marks each (100 total) and five performance levels: Excellent (100%), Very Good (80%), Good (60%), Fair (40%), and Needs Improvement (20%).

This document maps CampusFix evidence to every criterion. It does not claim marks or claim that planned features already exist.

## Review 01 - Project Proposal (50 marks)

| Criterion | Marks | CampusFix evidence | Current state |
|---|---:|---|---|
| Problem Identification & Objective | 10 | Clear maintenance-reporting problem, six measurable objectives, users, boundaries, requirements, and lifecycle in `PROJECT_SCOPE.md` | Documented in Batch 1 |
| Literature Review | 10 | Planned comparison of manual registers, informal messaging, help-desk/ticketing patterns, and related academic systems; sources and gap analysis to be added before proposal review | Pending research deliverable |
| Proposed Methodology | 10 | Iterative batch plan, modular monolith, role matrix, lifecycle, testing strategy, definition of done, risks, and data design | Documented; implementation continues |
| Tools & Technologies | 10 | Python, Django, SQLite, templates, Bootstrap, later Chart.js, local media; selection rationale and reproducible dependency versions | Foundation implemented |
| Presentation & Response to Queries | 10 | Planned proposal deck, architecture/data diagrams, demo narrative, evidence checklist, and question preparation | Future presentation preparation |

### Literature review plan

Before Review 01, create a cited review that compares at least:

1. informal/manual campus complaint handling;
2. generic issue-tracking or help-desk systems;
3. published smart-campus or grievance-management approaches;
4. the gap CampusFix addresses: college-specific roles, transparent lifecycle, explainable priority, student feedback, and a locally demonstrable implementation.

Use credible academic or official sources, identify search terms and selection criteria, and summarise findings rather than copying text.

## Review 02 - Project Implementation (50 marks)

| Criterion | Marks | CampusFix evidence | Current state |
|---|---:|---|---|
| Project Progress | 15 | Five completed batches, safe priority migration, documentation, 78 tests, and truthful future boundaries | Batches 1–5 complete |
| Implementation / Working Demonstration | 10 | Full workflow plus priority, role-private notifications, Student feedback, and live analytics | Presentation-ready core system demonstrable |
| Technical Understanding | 10 | Deterministic scoring, event-linked notification deduplication, ownership checks, feedback constraints, database aggregation, accessible chart summaries, and tests | Batch 5 architecture documented and tested |
| Presentation & Response to Queries | 15 | Planned live role walkthrough, realistic demo data, diagrams, test evidence, limitations, and prepared technical questions | Future final-review preparation |

## Evidence to retain for reviews

- Original rubric PDF (must not be deleted or modified).
- Git history or dated batch snapshots showing progress.
- Requirements file and setup instructions.
- Database migrations and entity/relationship documentation.
- Passing test and system-check output.
- Role-by-role authentication demonstration and proof that cross-role dashboard access returns HTTP 403.
- Screenshots or a live demonstration for each role.
- Sample ticket lifecycle, timeline, notification, feedback, analytics, and CSV report after those features are implemented.
- Known limitations and ethical/security considerations.

## Likely presentation questions

- Why was Django selected over a separated frontend/backend?
- Why use a custom user model from the beginning?
- How are maintenance staff different from Django Admin staff?
- How does the system prevent one student from seeing another student's complaint?
- How are status transitions validated and audited?
- How is the priority score calculated and kept transparent?
- How are uploaded images validated?
- Why is SQLite acceptable for the demo, and what would change for deployment?
- Which tests prove the role workflow works?
- What is complete today, and what remains?

Answers should point to working code, tests, and documentation rather than unsupported claims.
