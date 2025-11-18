import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure structured, security-aware logging (# NFR-BE-2 Security).

    Avoid logging sensitive payloads (passwords, JWTs, payment tokens). Routes
    and services should log only high-level events or error codes.
    """

    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        stream=sys.stdout,
    )

    # Reduce noisy default access logs and make sure we never dump request bodies.
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.error").setLevel(logging.WARNING)


# SECURITY: Never log entire auth/payment payloads – only reason codes or IDs.
