import pytest
from notification_service import send_notification
from template_loader import load_template
from users import User

TEST_DATA = {
    "date": "10 July",
    "time": "5 PM",
}


def test_load_html_template():
    template = load_template("en", "interview_scheduled", format="html")

    assert "<html" in template
    assert "{{name}}" in template


def test_render_html_notification():
    user = User("Vaishnavi", "vaish@gmail.com", "en")

    message = send_notification(user, "interview_scheduled", TEST_DATA, format="html")

    assert "<p>Hello Vaishnavi,</p>" in message
    assert "<p>Date: 10 July</p>" in message
    assert "<p>Time: 5 PM</p>" in message


def test_html_values_are_escaped():
    user = User("<script>alert('xss')</script>", "test@gmail.com", "en")

    message = send_notification(user, "interview_scheduled", TEST_DATA, format="html")

    assert "<script>" not in message
    assert "&lt;script&gt;" in message


def test_invalid_template_format_is_rejected():
    with pytest.raises(ValueError, match="Unsupported template format"):
        load_template("en", "interview_scheduled", format="pdf")
