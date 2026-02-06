import os
import logging

LOG_LEVELS = {
    'CRITICAL': logging.CRITICAL,
    'ERROR': logging.ERROR,
    'WARNING': logging.WARNING,
    'INFO': logging.INFO,
    'DEBUG': logging.DEBUG,
    'NOTSET': logging.NOTSET,
}

env_log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
log_level = LOG_LEVELS.get(env_log_level, logging.INFO)