# CampusFix Development Plan

## Delivery approach

Work is divided into small, demonstrable batches. Each batch ends with migrations, system checks, automated tests, documentation updates, and a manual role-based walkthrough. Features are not presented as complete until their user journey and permissions work.

## Batch 1 - Planning and foundation (completed)

- Read and map the official mini-project rubric.
- Establish Django 6.1.1 project structure and dependencies.
- Configure SQLite, templates, static/media files, timezone, and environment variables.
- Create `core` and `accounts` apps.
- Add the custom user model with Student, Staff, and Admin roles before initial migrations.
- Register the user model in Django Admin.
- Build shared responsive layout, landing page, health check, and custom 404.
- Add documentation and focused foundation tests.

## Batch 2 - Authentication and role entry points (completed)

- Registration policy and student registration form.
- Login, logout, password validation, and messages.
- Administrator-controlled staff/account creation rules.
- Role-based dashboard shells and navigation.
- Permission-denied handling and access tests.
- Profile and password management, demo users, improved Admin, and expanded documentation/tests.

## Batch 3 - Complaint domain and student workflow (completed)

- Category, location, complaint, and event models.
- Human-readable ticket service.
- Complaint creation with safe optional image upload.
- Student complaint list/detail, search, sorting, filtering, and pagination.
- Initial priority scoring rules and clear explanation.

Completed except priority scoring, which remains intentionally deferred under the Batch 3 boundary. Implemented secure image evidence, reference/demo seed commands, private ticket tracking, and real dashboard counts.

## Batch 4 - Administration and maintenance workflow (completed)

- Administrator review, rejection with reason, and assignment/reassignment.
- Staff assigned-work queue, progress updates, and resolution notes.
- Enforced status-transition rules and timeline events.
- Permission and complete workflow tests.
- Permanent timeline, dashboard live counts, demo workflow data, and read-only Admin inspection.

## Batch 5 - Feedback and notifications

- In-application notifications and unread state.
- Student resolution review, closure, rating, and feedback.
- Edge cases for rejected, reassigned, reopened (if approved), and overdue work.

**Completed:** feedback, notifications, transparent priority scoring, and Administrator analytics. Reopening was not part of the approved lifecycle and remains excluded.

## Batch 6 - Analytics, reports, and demonstration data

- Admin summary cards and Chart.js charts.
- Report filters and CSV export.
- Realistic fictional seed data and repeatable seed command.
- Query optimisation and report accuracy tests.

## Batch 7 - Final quality and presentation

- Responsive/accessibility audit and interface polish.
- Expanded test suite and final security review.
- Final README, diagrams, screenshots, demonstration script, and presentation support.
- Rubric evidence checklist and clean-machine Windows setup verification.

## Definition of done for a feature

1. Behaviour and permission rules are documented.
2. Database changes include migrations.
3. The happy path and important failure/permission paths are tested.
4. Pages are usable on desktop and mobile.
5. Django system checks and the full test suite pass.
6. Documentation accurately labels completed and future work.

## Risks and mitigation

| Risk | Mitigation |
|---|---|
| Scope becomes too large | Keep batch boundaries and prioritise the complete core workflow |
| Role data leaks | Filter querysets and verify role plus ownership/assignment server-side |
| Invalid status jumps | Central transition map with tests and transactional updates |
| Unsafe uploads | Restrict type/size, rename files, and treat media as untrusted |
| Weak demonstration | Maintain realistic seed data and a repeatable role-by-role script |
| Last-minute integration errors | Run checks/tests at every batch and keep migrations committed |
| Documentation drifts from product | Update scope, plan, and rubric evidence in each batch |
# Batch 6 — completed

- Administrator-only operational reporting with validated filters and live totals.
- Paginated complaint table, staff workload report, and feedback report.
- UTF-8 complaint, workload, and feedback CSV exports with formula-injection protection.
- Filter-preserving, print-friendly complaint report.
- Responsive tables, visible keyboard focus, empty states, print CSS, automated role/filter/export tests, and regression verification.
- No Batch 7 or complaint-feature expansion was started.
