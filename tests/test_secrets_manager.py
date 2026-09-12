from unittest.mock import MagicMock, patch

from scripts.secrets_manager import get_aws_secrets


@patch("scripts.secrets_manager.boto3.session.Session")
def test_get_aws_secrets(mock_session):
    mock_client = MagicMock()
    mock_client.get_secret_value.return_value = {
        "SecretString": '{"API_TOKEN": "test-token"}'
    }
    mock_session.return_value.client.return_value = mock_client

    get_aws_secrets.cache_clear()

    secrets = get_aws_secrets("test-secrets", "us-east-1")

    assert secrets == {"API_TOKEN": "test-token"}

    mock_client.get_secret_value.assert_called_once_with(SecretId="test-secrets")
