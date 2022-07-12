import os

REDIS_URI = os.getenv("REDIS_URI", "redis://redis")
DEPENDENCY_RETRY_TIME = 1
