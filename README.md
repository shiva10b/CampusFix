# CampusFix

CampusFix is a role-based college complaint and maintenance management system. It is being developed as a fourth-year CSE mini project using a beginner-friendly Django monolith.

## Current status

**Batches 1 through 6 are complete:** CampusFix supports the full internal workflow plus explainable priority scoring, private in-app notifications, Student feedback, real Administrator analytics, and operational reports/exports.

CSV/PDF exports, deployment, and external email/SMS/push integrations are intentionally reserved for later batches.

## Priority formula

- Urgency: Low 10, Medium 25, High 40.
- Category: Safety and Security 40; Electrical 30; Water and Plumbing 30; Furniture and Equipment 20; Wi-Fi and Network 15; Cleanliness 10; Other 10.
- Evidence image: 5 additional points.
- Level: Critical 70+, High 50–69, Medium 30–49, Low below 30.

The server calculates and explains priority automatically. Students cannot submit priority fields.

## Notifications, feedback, and analytics

- Workflow notifications are stored privately per recipient and deduplicated by event and user.
- Each user can open only their own Notification Centre and mark items read.
- Students can submit one 1–5 rating for their own Resolved or Closed complaint; feedback cannot be edited or deleted in Batch 5.
- Administrators receive feedback alerts and can view live status, category, priority, urgency, and rating analytics at `/analytics/`.
- Chart.js renders responsive charts while adjacent tables preserve accessible text summaries.

## Technology

- Python 3.12 or newer
- Django 6.1.1
- SQLite
- Django templates
- Bootstrap 5 and custom CSS
- Local media storage (configured for future uploads)

## Windows PowerShell setup

These steps are written for someone starting from a fresh Windows computer.

1. Install the latest Python 3.12+ release from [python.org](https://www.python.org/downloads/windows/). During installation, select **Add Python to PATH**.
2. Open this project folder in File Explorer.
3. Click the address bar, type `powershell`, and press Enter.
4. Create a private project environment:

   ```powershell
   py -m venv .venv
   ```

5. Allow the local activation script for this PowerShell window, then activate it:

   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   .\.venv\Scripts\Activate.ps1
   ```

6. Install the required packages:

   ```powershell
   py -m pip install --upgrade pip
   py -m pip install -r requirements.txt
   ```

7. Create your local settings file:

   ```powershell
   Copy-Item .env.example .env
   ```

   The provided development values are safe for local demonstration. Never publish the `.env` file.

8. Prepare the database:

   ```powershell
   py manage.py migrate
   ```

9. Start CampusFix:

   ```powershell
   py manage.py runserver
   ```

10. Open <http://127.0.0.1:8000/> in a browser. Stop the server with `Ctrl+C`.

## Local demonstration users

Create or safely refresh all three local demonstration accounts:

```powershell
.\.venv\Scripts\python.exe manage.py create_demo_users
```

| Role | Username | Password |
|---|---|---|
| Student | `student_demo` | `CampusFixStudent@2026` |
| Maintenance Staff | `staff_demo` | `CampusFixStaff@2026` |
| CampusFix Administrator | `admin_demo` | `CampusFixAdmin@2026` |

The command works only when `DEBUG=True`, can be run repeatedly without duplicates, and refreshes the passwords and safe fictional profile data. These credentials are strictly for local demonstration and must never be used in production. The administrator demo account also has local Django Admin access; ordinary CampusFix staff accounts do not.

## Complaint reference and demonstration data

Create or refresh the seven categories and seven campus locations:

```powershell
.\.venv\Scripts\python.exe manage.py create_reference_data
```

Create or refresh the demo users, reference data, and three submitted complaints for `student_demo`:

```powershell
.\.venv\Scripts\python.exe manage.py create_demo_complaints
```

Both commands are idempotent and refuse to run when `DEBUG=False`. Demo complaints remain Submitted; they do not fake assignment, progress, or resolution.

Prepare the complete Batch 4 workflow demonstration:

```powershell
.\.venv\Scripts\python.exe manage.py create_demo_workflow
```

This safely refreshes dependencies and prepares one Submitted ticket, one Assigned ticket for `staff_demo`, and one In Progress ticket for `staff_demo`. Repeated runs do not duplicate complaints or timeline events.

Prepare an additional Resolved ticket for feedback and analytics demonstrations:

```powershell
.\.venv\Scripts\python.exe manage.py create_demo_engagement
```

This command is DEBUG-only, idempotent, and preserves user-created records.

## Controlled complaint workflow

```text
Submitted -> Under Review -> Assigned -> In Progress -> Resolved -> Closed
          \----------------> Assigned
          \----------------> Rejected
Under Review ----------------> Rejected
```

- Administrators review, assign/reassign, reject with a reason, and close resolved tickets.
- Assigned Maintenance Staff can start work and resolve it with a meaningful note.
- Students have read-only access to their own current status and timeline.
- All assignment, reassignment, status, rejection, resolution, and closure actions use a centralized server-side workflow service and append permanent history.
- Complaint and history records are inspection-only in Django Admin; workflow changes use the CampusFix pages.

## Batch 6 reporting and exports

- `/reports/` is an Administrator-only operational report with all-time, 30-day, 90-day, and validated custom-date filtering.
- Status, category, priority, urgency, assigned-staff, and ticket/title/student search filters apply consistently to totals, tables, workload figures, feedback, print output, and CSV downloads.
- The complaint table is limited to 20 rows per page and keeps active filters while paging.
- `/reports/print/` provides a landscape print layout with generation time, filter summary, totals, and up to 500 filtered complaint rows.
- Complaint, staff-workload, and feedback CSV downloads are UTF-8 with a byte-order mark for spreadsheet compatibility. Exported values beginning with `=`, `+`, `-`, or `@` receive a leading apostrophe so spreadsheet software treats them as text instead of formulas.
- Reports contain operational account display names and institutional staff IDs only; passwords, email addresses, phone numbers, and authentication data are never exported.

Batch 6 introduces no database migration. It is a read-only reporting layer over the accepted complaint, assignment, priority, and feedback records.

## Batch 3 student workflow

- `/complaints/new/` accepts category, location, title, description, urgency, and one optional image.
- Genuine JPEG, PNG, and WebP files up to 5 MB are accepted and renamed with safe unique names.
- CampusFix assigns the logged-in Student, Submitted status, and an immutable ticket such as `CF-2026-00001`.
- `/complaints/` lists only the signed-in Student's tickets with search, status/category filters, and pagination.
- Ticket detail pages enforce ownership and return HTTP 403 for another Student's ticket.
- Student dashboard totals and recent tickets use real complaint records.

## Authentication and dashboard flow

- Public registration always creates a Student account; role selection is never exposed.
- Successful registration redirects to login with a confirmation message.
- Login accepts a safe local `next` destination or goes to `/dashboard/`; external redirects are rejected.
- `/dashboard/` sends each authenticated user to the correct Student, Maintenance Staff, or Administrator dashboard.
- Direct access to another role's dashboard returns a branded HTTP 403 page.
- Logout accepts POST requests only.
- Users can update permitted personal information and change their password without losing their session.
- CampusFix roles and Django Admin access are separate. A `STAFF` role does not grant `/admin/` access.

## Batch 2 manual test

1. Register a new student at <http://127.0.0.1:8000/register/> and confirm login works.
2. Try duplicate username, email, and student ID values and confirm field-specific errors appear.
3. Log into each demo account and confirm `/dashboard/` opens the correct dashboard.
4. While signed in, manually enter the other two dashboard URLs and confirm a 403 page appears.
5. Update the profile and confirm role, username, email, and institutional ID cannot be changed there.
6. Change the password and confirm the session remains signed in.
7. Confirm logout uses the navigation button and returns to the public landing page.
8. Log in as `admin_demo`, verify real user totals, then open Django Admin from the authorised link.
9. Run the reference/demo complaint commands, sign in as `student_demo`, and inspect the three tickets.
10. Submit a complaint with and without a valid image; try a non-image or file larger than 5 MB.
11. Sign in as another Student and confirm a copied ticket URL returns the branded 403 page.
12. As `admin_demo`, open `/management/complaints/`, review and assign a Submitted ticket.
13. As `staff_demo`, open `/work/`, start assigned work, then resolve it with a meaningful note.
14. As the Administrator, close the resolved ticket and confirm every step appears in the timeline.
15. Check each role's Notification Centre and verify unread counts/read controls.
16. Resolve a Student ticket, submit one feedback rating, and confirm duplicate feedback is refused.
17. As an Administrator, open `/analytics/`; confirm Students and Staff receive HTTP 403.
18. As an Administrator, open `/reports/`, combine filters, and confirm totals and complaint rows change together.
19. Download all three CSV files, open them in spreadsheet software, and confirm accented text, blank values, and column headers display correctly.
20. Open the print view, confirm the active filters and generation time, then inspect landscape print preview.
21. Confirm `/reports/` and every report download return HTTP 403 for Student and Maintenance Staff accounts.

## Production deployment preparation (Vercel + Neon)

CampusFix is configured for Vercel but this repository does not create or deploy any cloud resource. Local development remains unchanged: when `DATABASE_URL` is empty it uses `db.sqlite3`, and when `USE_S3_MEDIA=False` uploads remain in `media/`.

### 1. Create the production services

1. Create a Neon PostgreSQL project and copy its **pooled** connection string. Keep `sslmode=require` in the URL.
2. Create a private S3-compatible object-storage bucket for uploaded evidence images. Vercel's function filesystem is temporary and must not hold uploads.
3. Import the repository into Vercel only when ready to deploy. Vercel will use `api/index.py`, run the static collection command from `vercel.json`, and route all requests to Django.

Native Vercel Blob does not expose an S3-compatible API. The included storage configuration works without code changes with providers that supply S3-compatible credentials. Using native Vercel Blob would require a dedicated Django storage backend and should be treated as a separate integration.

### 2. Configure Vercel environment variables

Set secrets in **Vercel Project Settings**, never in `vercel.json`, source control, screenshots, or documentation. Use `.env.example` as the complete variable checklist.

Required production values:

```text
DJANGO_PRODUCTION=True
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<new-long-random-secret>
DJANGO_ALLOWED_HOSTS=<project>.vercel.app,your-domain.example
DJANGO_CSRF_TRUSTED_ORIGINS=https://<project>.vercel.app,https://your-domain.example
SITE_URL=https://your-domain.example
DATABASE_URL=<Neon-pooled-connection-string-with-sslmode=require>
```

For persistent images, also set:

```text
USE_S3_MEDIA=True
AWS_ACCESS_KEY_ID=<storage-access-key>
AWS_SECRET_ACCESS_KEY=<storage-secret-key>
AWS_STORAGE_BUCKET_NAME=<bucket-name>
AWS_S3_ENDPOINT_URL=<provider-S3-endpoint>
AWS_S3_REGION_NAME=<provider-region-if-required>
AWS_S3_CUSTOM_DOMAIN=<optional-media-CDN-domain>
AWS_QUERYSTRING_AUTH=True
```

Apply production variables to Production and the appropriate Preview environments. Vercel supplies `VERCEL_URL` automatically; CampusFix trusts that exact generated hostname while custom domains still remain explicit.

### 3. Prepare the production database and static files

Install the requirements and run migrations against Neon from a trusted administrative environment before serving production traffic:

```powershell
$env:DATABASE_URL = '<Neon pooled connection string>'
$env:DJANGO_PRODUCTION = 'True'
$env:DJANGO_DEBUG = 'False'
$env:DJANGO_SECRET_KEY = '<production secret>'
$env:DJANGO_ALLOWED_HOSTS = '<project>.vercel.app'
$env:DJANGO_CSRF_TRUSTED_ORIGINS = 'https://<project>.vercel.app'
$env:SITE_URL = 'https://<project>.vercel.app'
py manage.py migrate
py manage.py collectstatic --noinput
py manage.py check --deploy
```

Do not run the demo-data commands against production. **Never publish, reuse, or enable the documented demo passwords in production.** Create the first real administrator securely with `createsuperuser` while connected to Neon, then clear the temporary shell environment.

### 4. Production security checklist

- Keep `DJANGO_DEBUG=False`; production mode refuses to start with debug enabled or a missing production secret.
- Use HTTPS-only origins and exact hostnames. Do not use `*` for allowed hosts.
- Keep Neon, storage, and Django credentials only in Vercel's encrypted environment settings, and rotate any credential accidentally exposed.
- Verify the bucket is private when signed URLs are enabled, restrict credentials to that bucket, and enable provider-side encryption, backups, and lifecycle rules as appropriate.
- Test authentication, CSRF-protected forms, image upload/display, custom errors, reports, and exports on a Vercel preview before promoting it.
- HSTS defaults to one year with subdomains and preload in production. Confirm every subdomain is HTTPS-only before the first public deployment; tune the documented HSTS variables if necessary.

## Useful checks

Run these after making changes:

```powershell
py manage.py check
py manage.py test
```

To access Django Admin in future development, create a local administrator account:

```powershell
py manage.py createsuperuser
```

Then visit <http://127.0.0.1:8000/admin/>. This framework-level admin is available now; the custom CampusFix administrator dashboard is a later feature.

## Project layout

```text
campusfix/          Django project configuration and main URL routing
accounts/           Custom user model, roles, admin setup, tests, migrations
complaints/         Categories, locations, complaints, student workflow, commands, tests
core/               Public pages, health endpoint, 404 handler, tests
templates/          Shared and page-specific HTML templates
static/             Project CSS and future static assets
docs/               Scope, architecture, data design, plan, rubric mapping
manage.py           Django management entry point
requirements.txt    Reproducible Python dependencies
.env.example        Safe configuration example
```

## Security notes

- Keep `.env`, the SQLite database, uploaded media, and real secrets out of version control.
- The fallback secret key is only for local development. A production deployment must set a strong `DJANGO_SECRET_KEY` and turn off debug mode.
- Django's CSRF, session, password validation, clickjacking, and authentication middleware are enabled.
- Role permissions will be enforced server-side as each protected feature is added.
- Dashboard permissions are enforced by one reusable server-side role decorator.

## Documentation

- [Project scope](docs/PROJECT_SCOPE.md)
- [Architecture](docs/ARCHITECTURE.md)
- [Database design](docs/DATABASE_DESIGN.md)
- [Development plan](docs/DEVELOPMENT_PLAN.md)
- [Rubric mapping](docs/RUBRIC_MAPPING.md)
