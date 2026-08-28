import sys
import time
import datetime
import hmac
import hashlib
import logging
import json
from typing import Any, Dict, Optional

class FlushStreamHandler(logging.StreamHandler):
    def emit(self, record):
        super().emit(record)
        self.flush()

class ISTFormatter(logging.Formatter):
    """Formats timestamps in Indian Standard Time (IST / UTC+5:30)."""
    def formatTime(self, record, datefmt=None):
        ist = datetime.timezone(datetime.timedelta(hours=5, minutes=30))
        dt = datetime.datetime.fromtimestamp(record.created, ist)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.strftime("%Y-%m-%d %H:%M:%S")

def setup_logger(name: str = "DeltaBot", level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = FlushStreamHandler(sys.stdout)
        formatter = ISTFormatter(
            "[%(asctime)s IST] [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    return logger

logger = setup_logger()

def generate_delta_signature(
    secret: str,
    method: str,
    path: str,
    timestamp: str,
    query_string: str = "",
    payload: Optional[Any] = None
) -> str:
    """
    Generates HMAC-SHA256 signature for Delta Exchange API authentication.
    Signature string format: METHOD + TIMESTAMP + PATH + QUERY_STRING_OR_BODY
    """
    method = method.upper()
    body_str = ""
    if payload is not None:
        body_str = payload if isinstance(payload, str) else json.dumps(payload, separators=(',', ':'))
    elif query_string:
        if not query_string.startswith("?"):
            body_str = "?" + query_string
        else:
            body_str = query_string
            
    signature_data = f"{method}{timestamp}{path}{body_str}"
    
    signature = hmac.new(
        secret.strip().encode("utf-8"),
        signature_data.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    
    return signature
