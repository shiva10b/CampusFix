# CampusFix Architecture

## 1. Architecture choice

CampusFix uses a modular Django monolith. One application process contains the web pages, business rules, authentication, and database access. This is appropriate for a mini project because it is simple to learn, run, test, demonstrate, and maintain while still supporting clear internal boundaries.

```text
Browser
  |
  | HTTP requests and Django-rendered HTML
  v
Django URL routing
  |
  +-- core app: public pages and health check
  +-- accounts app: custom users, roles, authentication foundation
  +-- complaints app: categories, locations, student submission/tracking
  +-- future notifications/reporting modules
  |
  v
Django ORM -> SQLite database
             Local media directory for uploaded images
```

## 2. Current components

- **`campusfix` project package:** settings, top-level URL routing, WSGI, and ASGI entry points.
- **`core` app:** landing page, health endpoint, custom 404 handler, and public-page tests.
- **`accounts` app:** custom `User`, registration/login/profile forms, central role decorator, dashboard routing, Django Admin configuration, demo-user command, migrations, and tests.
- **`complaints` app:** reference data, complaint/ticket/history models, secure Student forms, three role workflows, centralized transition services, Admin inspection, seed commands, migrations, and tests.
- **Batch 5 services:** deterministic priority calculation and deduplicated notification delivery; feedback and analytics query the existing complaint domain without replacing history.
- **Templates:** shared layout, landing page, account pages, three dashboard foundations, and branded 403/404 pages.
- **Static assets:** project-owned CSS. Bootstrap is loaded from its public CDN for styling; the application itself needs no external account or API key.
- **SQLite:** local development and demonstration database.
- **Environment pattern:** `.env` supplies secret and machine-specific values; `.env.example` documents safe placeholders.

## 3. Request flow

1. A browser sends a request.
2. Django URL configuration selects a view.
3. Middleware applies security, sessions, authentication, messages, CSRF, and clickjacking protection.
4. The view will validate role and ownership where the route is protected.
5. Business logic reads or changes data through Django models.
6. The view renders a template or returns a small JSON response, such as `/health/`.

## 4. Planned application boundaries

The later `complaints` app should own complaint categories, locations, complaint records, assignments, status events, feedback, and the priority service. Notifications may live in a small separate app if their logic becomes substantial. Reports should query existing domain data instead of duplicating it.

Business rules such as valid status transitions and priority calculation should be kept in named services or model methods, not scattered across templates. Views should coordinate input/output; forms should validate user input; templates should present data without deciding permissions.

Ticket numbers are created after the initial database insert from the complaint's unique primary key and creation year (`CF-YYYY-00001`). This avoids unsafe record counting, guarantees uniqueness through the primary key and unique database field, and never changes on later saves.

All Batch 4 state changes pass through `complaints.services`. Each operation locks the complaint inside a database transaction, verifies actor role and assignment ownership, checks the exact current state and required notes, updates the complaint, and appends a `ComplaintHistory` record. Templates and POST data do not decide permissions.

## 5. Role and permission design

The custom user stores one explicit role. Dashboard access already combines authentication and a reusable `role_required` decorator. Future complaint actions will additionally combine:

- authentication checks;
- role checks;
- object ownership or assignment checks;
- filtered querysets that prevent access to unrelated records;
- form validation for allowed status transitions.

Django `is_staff` controls access to the framework's Admin site and is separate from the CampusFix `STAFF` role. A maintenance staff user does not automatically receive Django Admin access. Superusers are normalised to the CampusFix `ADMIN` role by the custom manager/model.

## 6. Authentication flow

1. Public registration uses a fixed Student-only form and never accepts a role field.
2. Field validation normalises text and rejects duplicate username, email, and student ID values.
3. The account is created with Django's password hashing, then the student is redirected to login.
4. Login accepts only same-host `next` URLs and otherwise routes through `/dashboard/`.
5. The dashboard router selects a destination by the stored CampusFix role.
6. Each destination independently repeats the server-side role check and returns HTTP 403 on mismatch.
7. Logout is a CSRF-protected POST action.

## 7. Configuration

- Development defaults are intentionally convenient and non-secret.
- `.env` can override the secret key, debug mode, and allowed hosts.
- Uploaded files will live in `media/`; collected static files will live in `staticfiles/`.
- Time is stored with timezone awareness and presented using `Asia/Kolkata`.
- SQLite is adequate for a local academic demo; the ORM leaves a future path to PostgreSQL if deployment ever requires it.

## 8. Security design

- Use Django password hashing and password validators.
- Keep CSRF middleware and tokens on all unsafe HTML forms.
- Use POST for state changes and verify role, ownership, and current state server-side.
- Use ORM queries rather than handwritten SQL for ordinary data access.
- Restrict upload type and size, generate safe file names, and never execute uploaded content.
- Batch 3 image validation opens and verifies actual content with Pillow, permits only JPEG/PNG/WebP, limits size to 5 MB, and stores files below `media/complaint-evidence/` with UUID filenames.
- Avoid exposing media containing private data through an unprotected production web server.
- Keep secrets and real data out of Git.
- Turn off debug mode and set explicit hosts before any non-local deployment.
- Log important administrative and workflow actions without recording passwords or sensitive tokens.
- Avoid account enumeration by using a generic login failure message.
- Keep role and institutional identifiers outside the self-service profile form.

## 9. Testing strategy

- **Unit tests:** role helpers, priority rules, ticket generation, and transition rules.
- **Model tests:** defaults, constraints, relations, and validation.
- **Form tests:** valid/invalid inputs, upload rules, and tampering attempts.
- **View tests:** authentication, permissions, ownership, redirects, messages, filters, and pagination.
- **Workflow tests:** full complaint journeys for accepted, rejected, and resolved cases.
- **Report tests:** totals and CSV contents against known fixtures.
- **Manual tests:** keyboard navigation, small screens, readable errors, image upload, and realistic role journeys.

Batches 1 and 2 test public pages, error handling, registration constraints, login/logout, redirect safety, dashboard routing, cross-role denial, profile protection, password changes, real administrator counts, superuser role safety, and idempotent demo users.
# Batch 6 reporting

The `complaints.reports` module owns validated GET filters, filtered query construction, summary calculations, staff workload calculations, and spreadsheet-safe CSV serialization. Administrator-only views in `complaints.views` reuse that module for the HTML report, print view, and all exports so each output applies the same server-side access control and filtering rules. Reports are read-only and use related-object loading to avoid per-row database lookups.
