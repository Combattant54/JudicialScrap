import logging, os

LOGS_DIR = "logs"
LOGS_FILE = os.path.join(LOGS_DIR, "logs.txt")
FORMAT = "%(levelname)s:[%(asctime)s]:%(name)s-%(lineno)s : %(msg)s"
formatter = logging.Formatter(FORMAT)

if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

with open(LOGS_FILE, "w") as f:
    pass
fh = logging.FileHandler(LOGS_FILE, mode="a")
fh.setLevel(logging.DEBUG)
fh.setFormatter(formatter)

sh = logging.StreamHandler()
sh.setLevel(logging.ERROR)
sh.setFormatter(formatter)

LOGGING_LEVEL = logging.DEBUG

loggers = []

def get_logger(name) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addHandler(fh)
    logger.addHandler(sh)
    logger.setLevel(LOGGING_LEVEL)
    loggers.append(logger)
    
    return logger

def set_level(level):
    global LOGGING_LEVEL
    try:
        map(lambda logger: logger.setLevel(level), loggers)
    except Exception as e:
        print(e)
        set_level(LOGGING_LEVEL)
    else:
        LOGGING_LEVEL = level