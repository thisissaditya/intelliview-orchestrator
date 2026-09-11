from notification_service import send_notification
from users import User

TEST_DATA = {
    "date": "10 July",
    "time": "5 PM",
}


def test_unsupported_locale_falls_back_to_english():
    user = User("Alex", "alex@gmail.com", "fr")

    assert user.locale == "en"

    message = send_notification(user, "interview_scheduled", TEST_DATA)

    assert "Hello Alex" in message


def test_validate_template_variables_valid():
    from template_loader import validate_template_variables

    template = "Hello {{name}}, Date: {{date}}, Time: {{time}}"
    variables = {"name": "Alice", "date": "12 August", "time": "3 PM"}
    assert validate_template_variables(template, variables) is True


def test_validate_template_variables_missing_raises_error():
    import pytest
    from template_loader import validate_template_variables

    template = "Hello {{name}}, Date: {{date}}, Time: {{time}}"
    incomplete_variables = {"name": "Alice", "time": "3 PM"}

    with pytest.raises(ValueError, match="Missing required template variable"):
        validate_template_variables(template, incomplete_variables)


def test_validate_template_variables_none_value_raises_error():
    import pytest
    from template_loader import validate_template_variables

    template = "Hello {{name}}, Date: {{date}}, Time: {{time}}"
    variables_with_none = {"name": "Alice", "date": None, "time": "3 PM"}

    with pytest.raises(ValueError, match="Missing required template variable"):
        validate_template_variables(template, variables_with_none)
