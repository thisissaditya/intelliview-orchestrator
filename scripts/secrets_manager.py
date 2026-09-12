import json
from functools import lru_cache

import boto3
from botocore.exceptions import ClientError


@lru_cache(maxsize=1)
def get_aws_secrets(secret_name: str, region_name: str = "us-east-1") -> dict:
    """
    Retrieve a JSON-formatted secret from AWS Secrets Manager.

    The actual secret values remain in AWS Secrets Manager and are
    never stored in this source file.
    """
    session = boto3.session.Session()
    client = session.client(
        service_name="secretsmanager",
        region_name=region_name,
    )

    try:
        response = client.get_secret_value(SecretId=secret_name)

        if "SecretString" in response:
            return json.loads(response["SecretString"])

    except ClientError as exc:
        print(f"Error fetching secrets: {exc}")

    return {}
