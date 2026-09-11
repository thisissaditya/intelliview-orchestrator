import logging

SUPPORTED_LOCALES = {"en", "hi", "te"}

logger = logging.getLogger(__name__)


class User:
    """
    Represents a user who receives notifications.
    """

    def __init__(self, name, email, locale):

        if not isinstance(name, str) or not name.strip():
            raise ValueError("User name cannot be empty.")

        if not isinstance(email, str) or "@" not in email:
            raise ValueError("Invalid email address.")

        if not isinstance(locale, str) or not locale.strip():
            raise ValueError("Locale cannot be empty.")

        self.name = name.strip()
        self.email = email.strip()

        locale = locale.strip()

        if locale not in SUPPORTED_LOCALES:
            logger.warning("Unsupported locale '%s'. Falling back to English.", locale)
            self.locale = "en"
        else:
            self.locale = locale

        self.notification_preferences = {}

    def set_notification_preference(self, notification_type, enabled):
        """
        Enable or disable a notification type for the user.
        """
        if not isinstance(notification_type, str) or not notification_type.strip():
            raise ValueError("Notification type cannot be empty.")

        if not isinstance(enabled, bool):
            raise ValueError("Notification preference must be a boolean.")

        self.notification_preferences[notification_type.strip()] = enabled

    def is_notification_enabled(self, notification_type):
        """
        Returns whether the user has enabled the given notification type.
        Notifications are enabled by default.
        """
        return self.notification_preferences.get(notification_type, True)

    def __str__(self):
        return f"User(name='{self.name}', email='{self.email}', locale='{self.locale}')"
