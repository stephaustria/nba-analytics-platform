import logging
import time

log = logging.getLogger("pipeline")


def retry(fn, attempts: int = 4, base: int = 3):
    """Call fn() politely, retrying with exponential backoff."""
    for attempt in range(1, attempts + 1):
        try:
            time.sleep(1)
            return fn()
        except Exception as exc:
            if attempt == attempts:
                raise
            wait = base * 2 ** attempt
            log.warning("call failed (%s); retrying in %ss", exc, wait)
            time.sleep(wait)