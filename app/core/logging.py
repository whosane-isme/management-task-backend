import logging


class AccessLogQueryStringFilter(logging.Filter):
    """Remove query strings before Uvicorn formats access-log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        if record.name != "uvicorn.access" or not isinstance(record.args, tuple):
            return True
        if len(record.args) < 3 or not isinstance(record.args[2], str):
            return True

        arguments = list(record.args)
        arguments[2] = arguments[2].partition("?")[0]
        record.args = tuple(arguments)
        return True


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    access_logger = logging.getLogger("uvicorn.access")
    if not any(isinstance(item, AccessLogQueryStringFilter) for item in access_logger.filters):
        access_logger.addFilter(AccessLogQueryStringFilter())
