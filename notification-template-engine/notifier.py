import logging
import random
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class TransientNotificationError(Exception):
    """Raised when notification delivery fails due to a transient error."""


class Notifier(ABC):
    """Abstract interface for notification delivery channels."""

    @abstractmethod
    def deliver(self, recipient: str, message: str) -> None:
        """Deliver a rendered notification message."""
        raise NotImplementedError


class ConsoleNotifier(Notifier):
    """Delivers notifications to the console with retry support."""

    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        jitter: float = 0.0,
    ) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be at least 1.")

        if base_delay < 0:
            raise ValueError("base_delay cannot be negative.")

        if not 0.0 <= jitter <= 0.5:
            raise ValueError("jitter must be between 0.0 and 0.5.")

        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.jitter = jitter

    def deliver(self, recipient: str, message: str) -> None:
        if not isinstance(recipient, str) or not recipient.strip():
            raise ValueError("Recipient cannot be empty.")

        if not isinstance(message, str) or not message.strip():
            raise ValueError("Message cannot be empty.")

        for attempt in range(1, self.max_attempts + 1):
            try:
                logger.debug(
                    "Notification delivery attempt=%d/%d",
                    attempt,
                    self.max_attempts,
                )

                self._deliver_once(recipient, message)

                logger.debug(
                    "Notification delivery succeeded on attempt=%d",
                    attempt,
                )
                return

            except TransientNotificationError as exc:
                if attempt == self.max_attempts:
                    logger.error(
                        "Notification delivery failed after %d attempts: %s",
                        self.max_attempts,
                        exc,
                        exc_info=True,
                    )
                    raise

                delay = self.base_delay * (2 ** (attempt - 1))

                if self.jitter:
                    delay *= 1 + random.uniform(-self.jitter, self.jitter)

                logger.debug(
                    "Notification retry attempt=%d/%d delay=%.2fs after error: %s",
                    attempt + 1,
                    self.max_attempts,
                    delay,
                    exc,
                )

                time.sleep(delay)

    def _deliver_once(self, recipient: str, message: str) -> None:
        """Perform one notification delivery attempt."""
        print(f"Notification for {recipient}")
        print(message)
