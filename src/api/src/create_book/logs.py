import logging
from os import environ
from eliot import to_file
from eliot.stdlib import EliotHandler

handler = EliotHandler()

logging.getLogger("fastapi").setLevel(logging.INFO)
logging.getLogger("fastapi").addHandler(handler)

exiftool_logger = logging.getLogger("exiftool")
exiftool_logger.addHandler(handler)

logger = logging.Logger("wpd")
logger.addHandler(handler)

if environ.get("DEBUG"):
    to_file(open("eliot.log", "wb"))
