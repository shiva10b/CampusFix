# CampusFix Project Scope

## 1. Problem identification

College maintenance issues are often reported through conversations, calls, or scattered messages. These channels do not reliably preserve the issue, identify who owns it, show its current status, or measure the final response. Students may not know whether a complaint was received, while administrators and maintenance teams lack a shared, searchable record.

CampusFix will provide one accountable workflow for campus complaints. It will make reports traceable from submission through review, assignment, repair, resolution, closure, and feedback.

## 2. Objectives

1. Give students a simple, structured way to report campus problems.
2. Give administrators a central queue for reviewing, prioritising, and assigning complaints.
3. Give maintenance staff a clear work list and a way to record progress and resolution notes.
4. Provide a complete status timeline and in-application notifications.
5. Measure service using ratings, summary cards, charts, reports, and CSV export.
6. Protect data using authenticated, role-based access and secure Django defaults.
7. Remain easy to demonstrate locally without paid services or secret API keys.

## 3. Users and permissions

| Capability | Student | Maintenance staff | Administrator |
|---|:---:|:---:|:---:|
| Register and manage own account | Yes | Controlled | Controlled |
| Submit complaint | Yes | No | Optional support action |
| View own complaints | Yes | No | Yes, all |
| View assigned complaints | No | Yes | Yes, all |
| Review/reject/assign complaints | No | No | Yes |
| Update work progress | No | Yes, assigned only | Yes |
| Add resolution notes | No | Yes, assigned only | Yes |
| Close and rate resolved complaint | Yes, own only | No | Oversight |
| View analytics and export reports | No | Limited future view | Yes |

Exact authorisation will be enforced in server-side views, queries, and forms; hiding a button alone will never be treated as security.

## 4. Functional requirements

### Accounts and access

- Secure registration, login, and logout.
- Three roles: Student, Maintenance Staff, and Administrator.
- Role-specific pages, navigation, query access, and permitted actions.
- Administrator management of user activation and staff accounts.

### Complaints

- Student complaint creation with category, location, description, urgency, and optional image.
- Unique, human-readable ticket numbers.
- Statuses: Submitted, Under Review, Assigned, In Progress, Resolved, Closed, and Rejected.
- Rule-based priority score with visible inputs and understandable reasoning.
- Search, filtering, sorting, and pagination.

### Workflow and communication

- Administrator review, rejection, and staff assignment.
- Staff progress updates and resolution notes.
- Immutable-style complaint history showing important changes, actor, and time.
- In-application notifications for relevant status and assignment events.
- Student rating and feedback after resolution.

### Management information

- Administrator summary cards and Chart.js visualisations.
- Reports with useful date, status, category, priority, location, and assignee filters.
- CSV export.
- Realistic demonstration data.

## 5. Non-functional requirements

- **Usability:** clear language, consistent navigation, helpful validation, and responsive layouts.
- **Accessibility:** semantic structure, keyboard-friendly controls, labels, focus visibility, and sufficient contrast.
- **Security:** least-privilege role checks, CSRF protection, secure password hashing, input validation, safe uploads, and protected secrets.
- **Reliability:** database constraints, atomic workflow updates where appropriate, error pages, tests, and reproducible dependencies.
- **Performance:** indexed lookup fields, paginated lists, efficient ORM queries, and compressed/sensible image limits.
- **Maintainability:** modular Django apps, documented rules, reusable templates, migrations, and automated tests.
- **Portability:** local Windows operation with Python and SQLite; no paid account or cloud dependency.
- **Auditability:** preserve key complaint events, timestamps, actors, assignments, and status transitions.

## 6. Complaint lifecycle

```text
Submitted -> Under Review -> Assigned -> In Progress -> Resolved -> Closed
                         \-> Rejected
```

- **Submitted:** student has created a valid complaint.
- **Under Review:** an administrator is checking scope, duplication, urgency, and assignment needs.
- **Assigned:** a maintenance staff member owns the work.
- **In Progress:** active investigation or repair has started.
- **Resolved:** staff records the completed action and resolution notes.
- **Closed:** the outcome is final, normally after student confirmation/feedback or an administrator rule.
- **Rejected:** the administrator records a reason, such as invalid, duplicate, or out-of-scope.

Allowed transitions will be centralised and tested. Every important transition will create a history entry and may create a notification.

## 7. Scope by delivery status

### Completed through Batch 5

- Django project foundation and reusable `core` app.
- Custom user model with Student, Staff, and Admin roles.
- Useful Django Admin registration for the custom user.
- Responsive public landing page and shared layout.
- Static, media, template, timezone, environment, and database settings.
- Health-check endpoint and branded 404 page.
- Initial migration, focused tests, and project documentation.
- Public Student-only registration with strong validation and Django password rules.
- Secure login, safe redirects, POST-only logout, and authenticated navigation.
- Server-protected Student, Maintenance Staff, and Administrator dashboards.
- Real user counts on the administrator dashboard and honest empty complaint states.
- Profile editing for permitted personal information and session-preserving password changes.
- Extended account fields, improved Django Admin, branded 403 response, and local demo-user command.
- Complaint categories and campus locations managed through Django Admin.
- Student-only complaint submission with server-owned submitter/status/ticket fields.
- Optional validated image evidence and safe unique media filenames.
- Immutable readable ticket numbers, private ticket list/detail pages, search, filters, and pagination.
- Real Student dashboard complaint totals and recent-ticket section.
- Idempotent local reference-data and demo-complaint commands.
- Dedicated Administrator queue/detail pages with search, filters, review, assignment, reassignment, rejection, and closure.
- Private Maintenance Staff work queue and controlled start/resolution actions.
- Central lifecycle validation and permanent append-only complaint timeline.
- Existing-ticket history backfill and an idempotent workflow demonstration command.
- Live Student, Staff, and Administrator complaint counts.
- Automatic transparent priority score/level/explanation with safe existing-ticket backfill.
- Private deduplicated in-app notifications and unread controls.
- One-time Student feedback for owned Resolved/Closed complaints.
- Administrator-only live analytics with Chart.js and accessible tables.

### Explicitly not implemented through Batch 5

CSV/PDF reports, deployment, email/SMS/push notifications, external APIs, and AI features.

## 8. Out of scope

- Native mobile applications.
- External AI or machine-learning services.
- SMS, WhatsApp, or paid email services.
- Cloud deployment and distributed infrastructure for the mini-project version.
- Real-time GPS tracking or hardware integrations.
- React, Next.js, Docker, microservices, and unnecessary background infrastructure.
