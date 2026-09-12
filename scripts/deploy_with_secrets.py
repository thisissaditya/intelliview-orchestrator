import os
import subprocess
import sys

from scripts.secrets_manager import get_aws_secrets

SECRET_NAME = os.getenv("AWS_SECRET_NAME", "intelliview-secrets")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Only sensitive values are injected from Secrets Manager.
SENSITIVE_KEYS = {
    "API_TOKEN",
    "POSTGRES_PASSWORD",
    "GRAFANA_PASSWORD",
    "GEMINI_API_KEY",
    "GROK_API_KEY",
    "JWT_SECRET_KEY",
    "SCREEN_LOCK_PIN",
}


def main() -> int:
    secrets = get_aws_secrets(SECRET_NAME, AWS_REGION)

    if not secrets:
        print("No production secrets were retrieved from AWS Secrets Manager.")
        return 1

    missing = sorted(key for key in SENSITIVE_KEYS if key not in secrets)

    if missing:
        print(
            "Required production secrets are missing from "
            f"AWS Secrets Manager: {', '.join(missing)}"
        )
        return 1

    environment = os.environ.copy()
    environment["ENVIRONMENT"] = "production"

    for key in SENSITIVE_KEYS:
        environment[key] = str(secrets[key])

    commands = [
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "pull",
        ],
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "up",
            "-d",
        ],
    ]

    print("Starting production deployment using AWS Secrets Manager secrets.")

    try:
        for command in commands:
            subprocess.run(
                command,
                env=environment,
                check=True,
            )
    except FileNotFoundError:
        print("Docker is not installed or is not available in PATH.")
        return 1
    except subprocess.CalledProcessError as exc:
        print(f"Production deployment failed with exit code {exc.returncode}.")
        return exc.returncode

    print("Production deployment completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
