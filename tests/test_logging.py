import logging

from app.core.logging import AccessLogQueryStringFilter, configure_logging


def access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %d',
        args=("127.0.0.1:1234", "GET", path, "1.1", 303),
        exc_info=None,
    )


def test_access_log_filter_removes_query_string() -> None:
    record = access_record("/api/v1/auth/google/callback?code=secret&state=value")

    assert AccessLogQueryStringFilter().filter(record)

    assert record.args[2] == "/api/v1/auth/google/callback"
    assert "secret" not in record.getMessage()
    assert "state" not in record.getMessage()


def test_access_log_filter_leaves_plain_path_unchanged() -> None:
    record = access_record("/api/v1/health/live")

    AccessLogQueryStringFilter().filter(record)

    assert record.args[2] == "/api/v1/health/live"


def test_configure_logging_installs_filter_once() -> None:
    logger = logging.getLogger("uvicorn.access")
    original_filters = list(logger.filters)
    logger.filters.clear()
    try:
        configure_logging("INFO")
        configure_logging("INFO")

        installed = [
            item for item in logger.filters if isinstance(item, AccessLogQueryStringFilter)
        ]
        assert len(installed) == 1
    finally:
        logger.filters[:] = original_filters
