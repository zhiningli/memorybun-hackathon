import logging
from .request_id import get_request_id

class CorrelationIdFilter(logging.Filter):
    def filter(self, record):
        record.correlation_id = get_request_id()
        return True
