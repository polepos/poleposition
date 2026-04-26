import logging
import sys


class DefaultFieldsFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "app_name"):
            record.app_name = "-"
        if not hasattr(record, "environment"):
            record.environment = "-"
        if not hasattr(record, "request_id"):
            record.request_id = "-"
        return True


def setup_logging(log_level: str = "INFO") -> None:
    root_logger = logging.getLogger()

    if root_logger.handlers:
        root_logger.handlers.clear()

    root_logger.setLevel(log_level.upper())

    formatter = logging.Formatter(
        fmt=(
            "%(asctime)s | %(levelname)s | %(name)s | "
            "app=%(app_name)s env=%(environment)s request_id=%(request_id)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level.upper())
    handler.setFormatter(formatter)
    handler.addFilter(DefaultFieldsFilter())

    root_logger.addHandler(handler)

    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        named_logger = logging.getLogger(logger_name)
        named_logger.handlers.clear()
        named_logger.propagate = True
