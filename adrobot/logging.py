"""Application logging, without changing Uvicorn's logging configuration."""
import logging


def configure_logging():
    logger = logging.getLogger('adrobot')
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(name)s %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
