import traceback, sys
import build_logger

LOGGER = build_logger.get_logger(__name__)


def log_exception(logger=None, limit=10):
    if logger is None:
        logger = LOGGER
    def decorate(func):
        print("decorating " + func.__name__)
        def function(*args, **kwargs):
            print(args, kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                extyp, value, tb = sys.exc_info()
                logger.critical("\n".join(traceback.format_exception(extyp, value, tb, limit=limit)))
                return None
        return function
    return decorate

def raise_log_exception(logger=None, limit=10):
    if logger is None:
        logger = LOGGER
    def decorate(func):
        print("decorating " + func.__name__)
        def function(*args, **kwargs):
            print(args, kwargs)
            try:
                return func(*args, **kwargs)
            except Exception as e:
                extyp, value, tb = sys.exc_info()
                logger.critical("\n".join(traceback.format_exception(extyp, value, tb, limit=limit)))
                raise e
        return function
    
    return decorate