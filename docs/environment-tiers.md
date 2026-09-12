# Environment Configuration Tiers

This document details the configuration requirements and behavioral differences across **Development**, **Staging**, and **Production** environments for the AI Interview Orchestrator application.

---

## Configuration Matrix Summary

| Area / Setting | Development | Staging | Production |
| :--- | :--- | :--- | :--- |
| **`ENVIRONMENT`** | `development` | `staging` | `production` |
| **Secrets Loading** | `.env` file (`pydantic-settings`) | Injected `.env` / Environment Vars | AWS Secrets Manager (`intelliview-secrets`) |
| **Database Connection** | Local Postgres (`POSTGRES_HOST=localhost`) | Managed Staging Postgres | Managed Production Postgres |
| **Database SSL Mode** | `DATABASE_SSLMODE=disable` | `DATABASE_SSLMODE=require` | `DATABASE_SSLMODE=require` / `verify-full` |
| **Redis / Celery** | Local Redis (`redis://localhost:6379/0`) | Managed Staging Redis | Managed Production Redis Cluster |
| **CORS Policy** | `CORS_ALLOW_ORIGINS=*` | Explicit domain origins | Restricted origin list |
| **`API_TOKEN` Validation** | Fallback allowed (`dev-token-change-me`) | Must be rotated token | **Strict check**: App throws `RuntimeError` if default |
| **`AUTO_SEED_DEMO_DATA`** | `false` (Default, optional `true`) | `false` | `false` |
| **`JSON_LOGGING`** | `true` (Default, optional `false`) | `true` | `true` |

---

## Detailed Environment Breakdown

### 1. Database Configuration
* **Development:**
  * Connects via individual host properties: `POSTGRES_HOST=localhost`, `POSTGRES_PORT=5432`, `POSTGRES_DB=ai_interview_db`, `POSTGRES_USER=postgres`.
  * `DATABASE_SSLMODE=disable`.
* **Staging:**
  * Host and credentials pointed to staging PostgreSQL database.
  * Enforces `DATABASE_SSLMODE=require`.
* **Production:**
  * Connects to managed production PostgreSQL instance via `DATABASE_URL` or explicit `POSTGRES_*` settings.
  * Enforces secure SSL mode (`DATABASE_SSLMODE=require` or `DATABASE_SSLMODE=verify-full`).

### 2. Redis & Celery Task Queue
* **Development:**
  * Uses local Redis endpoint (`redis://localhost:6379/0`).
  * Separate DB indices used for Celery broker (`/0`) and result backend (`/1`).
  * `WORKER_CONCURRENCY=4` (default).
* **Staging:**
  * Configured with staging Redis URI (`REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`).
* **Production:**
  * Dedicated, persistent Redis instance for task queuing and realtime caching.
  * `ENABLE_CELERY_BROKER=true` with scaled worker concurrency.

### 3. Secrets & API Tokens Handling
* **Development & Staging:**
  * Loaded via `pydantic-settings` from local `.env` file or process environment variables.
* **Production:**
  * Automatically fetches runtime overrides from AWS Secrets Manager using `aws_secret_name` (`intelliview-secrets`) and `aws_region` (`us-east-1`).
  * **Critical Validation:** Calling `validate_configuration()` in production raises a `RuntimeError` if `API_TOKEN` remains `"dev-token-change-me"`.

### 4. Feature Flags & Observability
* **`AUTO_SEED_DEMO_DATA`:** Default is `false` across all environments in `config.py`. Can be manually set to `true` in local `.env` for dataset seeding.
* **`JSON_LOGGING`:** Default is `true` (`1` in `.env.example`) to produce structured logs across environments.
* **`ENABLE_PROMETHEUS`:** Default is `true` for metric collection via Grafana/Prometheus integrations.
* **Real-time Tracking:** `REALTIME_ENABLED=true` and `MOMENT_TRACKING_ENABLED=true` active across environments.

### 5. Security & Risk Engine Configuration
* **Authentication:** Production environment requires non-default values for `JWT_SECRET_KEY`, `API_TOKEN`, and `SCREEN_LOCK_PIN`.
* **Risk Engine Factors:** `RISK_VIDEO_WEIGHT` (0.4), `RISK_AUDIO_WEIGHT` (0.3), and `RISK_EVALUATION_WEIGHT` (0.3) dictate anti-cheat scoring across all tiers.