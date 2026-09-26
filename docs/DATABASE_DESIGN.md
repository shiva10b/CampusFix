# CampusFix Database Design

## 1. Design principles

- Use Django migrations as the source of truth.
- Keep stable choices, required fields, indexes, and constraints explicit.
- Record timestamps and responsible users for accountability.
- Preserve complaint history rather than overwriting all evidence of past states.
- Avoid storing derived values unless there is a clear audit or performance reason.

## 2. Implemented entity

### User (`accounts.User`) - implemented through Batch 2

Extends Django's `AbstractUser`, retaining secure password, username, email, names, activation, permission, and audit fields.

| Field | Purpose |
|---|---|
| inherited Django user fields | Identity, password hash, status, permissions, timestamps |
| `role` | `STUDENT`, `STAFF`, or `ADMIN`; defaults to `STUDENT` and is indexed |
| `email` | Required unique email address |
| `phone_number` | Optional contact number |
| `department` | Academic or operational department |
| `student_id` | Optional, unique when present; blank values are stored as `NULL` |
| `employee_id` | Optional, unique when present; blank values are stored as `NULL` |
| `date_joined` | Inherited account creation timestamp |
| `profile_updated_at` | Automatically updated profile timestamp |

The model was configured with `AUTH_USER_MODEL` before the initial migration so every future relationship can reference it safely.

Migration `0002` adds the Batch 2 profile fields, unique identifiers, unique email, profile timestamp, and custom user manager. The model normalises blank identifiers to `NULL`, allowing many users without an identifier while preventing duplicate non-empty values.

## 3. Implemented Batch 3 entities

### Category

Implemented as `ComplaintCategory`: unique name, description, active flag, and created/updated timestamps.

### Location

Implemented as `CampusLocation`: name, building/area, optional detail, active flag, timestamps, and a unique name/area constraint.

### Complaint

Implemented fields: immutable unique ticket number, Student, category, location, title, description, Low/Medium/High urgency, seven-value status structure, optional evidence image, and timestamps. Batch 3 creates only Submitted complaints. Assignment, priority, review, and resolution fields remain future work.
Batch 4 adds optional assigned Maintenance Staff and assignment timestamp. New Student submissions still always begin as Submitted and unassigned.
Batch 5 adds indexed priority score/level plus a stored human-readable explanation. Migration `0005` backfills existing tickets without changing ownership, ticket, status, assignment, or history.

### Notification

Recipient, title, short message, safe internal destination, type, read flag, timestamp, and unique deduplication key. Users access notifications only through recipient-filtered pages.

### ComplaintFeedback

One-to-one complaint relationship, submitting Student, validated 1–5 rating, optional comment up to 1,000 characters, and creation timestamp.

Important proposed constraints:

- unique ticket number;
- priority score within the defined range;
- student and category required;
- assigned staff required for assigned/in-progress states through application validation;
- sensible indexes on status, created time, category, assigned staff, and priority.

### ComplaintEvent

Implemented as `ComplaintHistory`: complaint, action type, previous/new status, actor, optional note, timestamp, chronological ordering, and complaint/time index. Application pages append entries; Django Admin cannot add, edit, or delete them. Migration `0003` safely backfills an initial Submitted entry for existing Batch 3 complaints.

## 4. Proposed entities for future batches

### Assignment

Complaint, assigned staff member, assigning administrator, assignment note, assigned time, and completion/end time. A separate record preserves reassignment history; `Complaint.assigned_to` can provide the current fast lookup.

### Feedback

One-to-one complaint link, student, rating, comment, and creation/update timestamps. Only the reporting student may provide feedback, and only after resolution.

### Notification

Recipient, complaint, event reference where relevant, title/message, read flag, and created/read timestamps.

## 5. Relationships

```text
User (Student) 1 ---- * Complaint
Category       1 ---- * Complaint
Location       1 ---- * Complaint
Complaint      1 ---- * ComplaintEvent
Complaint      1 ---- * Assignment * ---- 1 User (Maintenance Staff)
Complaint      1 ---- 0..1 Feedback
User           1 ---- * Notification * ---- 0..1 Complaint
User (Actor)   1 ---- * ComplaintEvent
```

All user foreign keys must reference `settings.AUTH_USER_MODEL`, never Django's concrete default user class.

## 6. Ticket numbering

Implemented tickets use `CF-{creation year}-{unique complaint primary key padded to at least five digits}`. The unique primary key avoids count-based races; the database also enforces ticket uniqueness. Once assigned, the ticket is preserved.

## 7. Priority scoring proposal

The score should remain explainable. A possible rule combines:

- student-selected urgency;
- category safety impact;
- location impact (for example, common area versus one room);
- age of unresolved complaint;
- administrator-confirmed escalation.

The stored explanation should show the contributing rules. Final weights will be agreed and documented before implementation; the system will not claim machine learning or hidden AI prioritisation.

## 8. Data retention and integrity

- Prefer deactivation of categories, locations, and users over deletion when referenced.
- Protect or restrict deletion of complaint-linked records.
- Preserve history and assignments for auditability.
- Use transactions for assignment and status changes that also create events/notifications.
- Use demonstration-only fictional records; do not include real personal or sensitive data.
