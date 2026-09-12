# Docker Deployment

## Docker build steps

Run `docker build -t app .` from the project root.

## Docker Compose commands

`docker compose up -d` to start services.

`docker compose ps` to check running containers.

`docker compose logs` to check logs.

## Required environment variables

See `.env.example` for the full list.

## Production secrets management

Production API keys, tokens, passwords, and other sensitive values must not be stored in a plaintext `.env` file.

Production secrets are stored in AWS Secrets Manager using the secret:

`intelliview-secrets`

Region:

`us-east-1`

The production deployment retrieves secrets at deployment time using:

`scripts/deploy_with_secrets.py`

Only required sensitive values are injected into the production Docker Compose environment. Actual secret values are not stored in the repository.

GitHub Actions authenticates to AWS using GitHub OIDC and the IAM role configured by the deployment owner. The IAM role must have permission to retrieve the `intelliview-secrets` secret from AWS Secrets Manager.

## Production deployment

The production deployment uses:

`docker-compose.yml`

The production Compose configuration requires sensitive variables to be provided and does not use insecure default passwords or API tokens.

The deployment process is:

1. GitHub Actions checks out the repository.
2. GitHub Actions authenticates to AWS using OIDC.
3. The deployment script retrieves production secrets from AWS Secrets Manager.
4. Docker images are pulled.
5. The application is started using `docker-compose.yml`.
6. Running containers are checked.

The actual AWS IAM Role ARN and production secret values are configured by the deployment owner and are not stored in the repository.

## How deployment works after merging to main

Merging to main triggers the CI/CD pipeline which builds, pushes, and deploys the application using the production secrets from AWS Secrets Manager.

## Docker Hub image information

Images are published to the project's Docker Hub repository on merge.