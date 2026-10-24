"""Outgoing email.

Development has no mail server, so messages are written to the application
log. Replace send_email with a real provider before inviting external users.
"""

import logging

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> None:
    logger.info("Email to %s | %s\n%s", to, subject, body)


def send_password_reset(to: str, reset_link: str) -> None:
    send_email(
        to,
        "Reset your OneResume password",
        f"Use this link to choose a new password. It expires soon and works once.\n\n{reset_link}\n\n"
        "If you did not ask for this, you can ignore this email.",
    )
