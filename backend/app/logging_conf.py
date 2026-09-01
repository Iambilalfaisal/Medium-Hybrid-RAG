import logging
import sys

from app.utils.correlation import correlation_id_var


class CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = correlation_id_var.get()
        return True


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(correlation_id)s] %(name)s: %(message)s")
    )
    handler.addFilter(CorrelationFilter())

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]
