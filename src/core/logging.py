import logging

import structlog

SENSITIVE_KEY_PARTS = ("api_key", "authorization", "password", "secret", "token")


def redact_sensitive_values(_logger, _method, event_dict: dict) -> dict:
    for key in event_dict:
        if any(part in key.lower() for part in SENSITIVE_KEY_PARTS):
            event_dict[key] = "***"
    return event_dict


def configure_logging(level: int = logging.INFO) -> None:
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive_values,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )


def bind_run_id(run_id: str) -> None:
    structlog.contextvars.bind_contextvars(run_id=run_id)


def clear_run_id() -> None:
    structlog.contextvars.unbind_contextvars("run_id")


def get_logger(name: str = "harness"):
    return structlog.get_logger(name)
