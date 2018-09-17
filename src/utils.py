"""some utility function"""
import logging
import sys
from datetime import datetime
from functools import wraps

LOGGER = logging.getLogger(__name__)


def log_handler(*loggers, logname: str = ''):
    """[summary]

    Keyword Arguments:
        logname {str} -- [description] (default: {''})
    """

    formatter = logging.Formatter(
        '%(asctime)s %(filename)12s:L%(lineno)3s [%(levelname)8s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S')

    # stream handler
    shell_handler = logging.StreamHandler(sys.stdout)
    shell_handler.setLevel(logging.INFO)
    shell_handler.setFormatter(formatter)

    # file handler
    if logname:
        file_handler = logging.FileHandler(logname)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

    for logger in loggers:
        if logname:
            logger.addHandler(file_handler)
        logger.addHandler(shell_handler)
        logger.setLevel(logging.DEBUG)

def func_profile(func):
    """record the function processing time"""
    @wraps(func)
    def wrapped(*args, **kwargs):
        start_time = datetime.now()
        result = func(*args, **kwargs)
        cost_time = datetime.now() - start_time
        fullname = '{}.{}'.format(func.__module__, func.__name__)
        LOGGER.info('%s[kwargs=%s] completed in %s', fullname, kwargs, str(cost_time))
        return result
    return wrapped
