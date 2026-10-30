import logging

# keep the bot's log lines out of the test output
logging.getLogger("jobbot").setLevel(logging.CRITICAL)
