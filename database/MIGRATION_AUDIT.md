# Database Migration Audit

## H1 — Audit Existing Migrations

### Objective

Review existing Alembic migrations against the current SQLAlchemy
database models and identify schema/model drift.

## Findings

### 1. Questions schema mismatch

The migration creates:

- `tags`
- Type: JSON

The current `Question` model defines:

- `tag`
- Type: String(50)

This is a schema/model mismatch.

### 2. Users migration coverage

The current `User` model defines the `users` table.

A corresponding table-creation migration was not found in the reviewed
Alembic migration chain.

### 3. Notifications migration coverage

The current `Notification` model defines the `notifications` table.

A corresponding table-creation migration was not found in the reviewed
Alembic migration chain.

### 4. Interview sessions constraints

The current `InterviewSession` model defines foreign-key and check
constraints that are not represented in the initial table-creation
migration.

## Migration Coverage Verified

The following model changes have corresponding migration coverage:

- Candidate demographics
- Candidate feature fields
- `interview_sessions.llm_usage`
- `practice_sessions`
- `system_settings`
- `interview_schedules`
- `interview_templates.version`

## Conclusion

Existing migrations were compared against the current database models.

Schema/model drift was identified in the areas documented above.

No schema changes were made as part of H1.

These findings should be considered when implementing subsequent
migration work.
