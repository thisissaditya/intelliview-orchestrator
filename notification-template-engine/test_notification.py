import unittest

from notification_service import send_notification
from users import User


class TestNotificationSystem(unittest.TestCase):
    def setUp(self):

        self.data = {"date": "10 July", "time": "5 PM"}

        self.events = [
            "interview_scheduled",
            "interview_reminder",
            "interview_cancelled",
            "interview_completed",
        ]

    # --------------------------
    # Valid Notification Tests
    # --------------------------

    def test_english_notification(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("Hello Vaishnavi", message)

    def test_hindi_notification(self):

        user = User("Jaya", "jaya@gmail.com", "hi")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("नमस्ते Jaya", message)

    def test_telugu_notification(self):

        user = User("Anushka", "anu@gmail.com", "te")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("హలో Anushka", message)

    # Locale Fallback

    def test_locale_fallback(self):

        user = User("Alex", "alex@gmail.com", "fr")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("Hello Alex", message)

    # Placeholder Replacement

    def test_placeholder_replacement(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("10 July", message)
        self.assertIn("5 PM", message)

    # Invalid Event

    def test_invalid_event(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        with self.assertRaises(ValueError):
            send_notification(user, "random_event", self.data)

    # Missing Date

    def test_missing_date(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        with self.assertRaises(ValueError):
            send_notification(user, "interview_scheduled", {"time": "5 PM"})

    # Missing Time

    def test_missing_time(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        with self.assertRaises(ValueError):
            send_notification(user, "interview_scheduled", {"date": "10 July"})

    # Invalid User

    def test_invalid_user(self):

        with self.assertRaises(ValueError):
            User("", "abc@gmail.com", "en")

    # Invalid Email

    def test_invalid_email(self):

        with self.assertRaises(ValueError):
            User("Vaishnavi", "wrongemail", "en")

    # Unicode Handling

    def test_unicode_name(self):

        user = User("वैष्णवी", "abc@gmail.com", "hi")

        message = send_notification(user, "interview_scheduled", self.data)

        self.assertIn("वैष्णवी", message)

    # Multiple Events

    def test_all_events(self):

        user = User("Vaishnavi", "abc@gmail.com", "en")

        for event in self.events:
            message = send_notification(user, event, self.data)

            self.assertIsInstance(message, str)

    # Notification Preferences

    def test_notification_can_be_disabled(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        user.set_notification_preference("interview_reminder", False)

        message = send_notification(user, "interview_reminder", self.data)

        self.assertIsNone(message)

    def test_notification_preferences_are_per_type(self):

        user = User("Vaishnavi", "vaish@gmail.com", "en")

        user.set_notification_preference("interview_reminder", False)

        # Disabled notification should not be sent
        disabled_message = send_notification(user, "interview_reminder", self.data)

        self.assertIsNone(disabled_message)

        # Other notification types should still be sent
        enabled_message = send_notification(user, "interview_scheduled", self.data)

        self.assertIsInstance(enabled_message, str)

    # Exception Handling

    def test_none_user(self):

        with self.assertRaises(ValueError):
            send_notification(None, "interview_scheduled", self.data)

    def test_unsupported_locale_defaults_to_english_at_user_level(self):

        with self.assertLogs("users", level="WARNING") as logs:
            user = User("Alex", "alex@gmail.com", "fr")

        self.assertEqual(user.locale, "en")
        self.assertTrue(
            any(
                "Unsupported locale 'fr'. Falling back to English." in message
                for message in logs.output
            )
        )


if __name__ == "__main__":
    unittest.main()
