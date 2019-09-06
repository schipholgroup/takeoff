import logging

root_logger = logging.getLogger()
for handler in root_logger.handlers:
    root_logger.removeHandler(handler)

logging.basicConfig(
    format="%(asctime)s %(levelname)s " "[%(module)s/%(funcName)s]: %(message)s",
    handlers=[logging.FileHandler("logs"), logging.StreamHandler()],
)

logging.getLogger().setLevel(logging.INFO)
