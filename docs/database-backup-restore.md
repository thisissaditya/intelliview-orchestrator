# Database Backup and Restore Procedure

## Purpose

This document describes the procedure for backing up and restoring the IntelliView PostgreSQL database during a database failure or recovery incident.

## Database Details

IntelliView uses PostgreSQL 15.

* Database: `ai_interview_db`
* Docker container: `ai-interview-postgres`
* Backup format: PostgreSQL Custom Format (`-Fc`)

Production credentials must be obtained securely from the deployment environment or managed database provider.

## Backup Procedure

### 1. Verify PostgreSQL

```powershell
docker compose ps postgres
```

The PostgreSQL service should be running and healthy.

### 2. Create the backup

```powershell
docker exec ai-interview-postgres pg_dump -U postgres -d ai_interview_db -Fc -f /tmp/ai_interview_db_backup.dump
```

The backup is created directly inside the PostgreSQL container.

**Important:** On Windows PowerShell, do not redirect the binary custom-format dump using `>`, because this can corrupt the backup archive.

### 3. Copy the backup to the host

```powershell
New-Item -ItemType Directory -Force .\backups
```

```powershell
docker cp ai-interview-postgres:/tmp/ai_interview_db_backup.dump .\backups\ai_interview_db_backup.dump
```

### 4. Validate the backup

```powershell
docker exec ai-interview-postgres pg_restore -l /tmp/ai_interview_db_backup.dump
```

A successful command confirms that the backup is a valid PostgreSQL archive.

## Restore Procedure

### 1. Create a temporary restore database

```powershell
docker exec ai-interview-postgres psql -U postgres -d postgres -c "CREATE DATABASE ai_interview_restore_test;"
```

### 2. Restore the backup

```powershell
docker exec ai-interview-postgres pg_restore -U postgres -d ai_interview_restore_test --no-owner /tmp/ai_interview_db_backup.dump
```

### 3. Verify the restored tables

```powershell
docker exec ai-interview-postgres psql -U postgres -d ai_interview_restore_test -c "\dt"
```

### 4. Verify the restored data

Compare the row counts between the original and restored databases.

The restored database should contain the same tables and corresponding data as the source database.

## End-to-End Test Result

The backup and restore procedure was tested successfully.

The PostgreSQL custom-format backup was successfully validated using `pg_restore`.

The backup was restored into a separate `ai_interview_restore_test` database without modifying the original `ai_interview_db` database.

The restored database contained all 9 application tables:

* candidates
* interview_schedules
* interview_sessions
* interview_templates
* notifications
* practice_sessions
* questions
* system_settings
* users

The source and restored databases were compared using row-count queries. All 9 tables contained 0 rows in the test environment, and the restored counts matched the source counts.

After verification, the temporary restore database was removed.

## Incident Recovery Notes

1. Verify that the database service is available.
2. Identify the required backup file.
3. Validate the backup archive.
4. Restore into a temporary database when possible.
5. Verify the restored schema and data.
6. Only perform production recovery after the recovery procedure has been reviewed and approved.
7. Preserve the original backup until recovery has been confirmed.

## Safety Notes

* Do not run `docker compose down -v` during database recovery because this can remove the persistent database volume.
* Do not commit production database dump files to Git.
* Store production backups securely according to the team's retention and access-control policies.
* Production credentials must never be stored in this documentation.
* The procedure was validated using the local PostgreSQL Docker environment as an end-to-end recovery test.
