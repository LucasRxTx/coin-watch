import aioredis
from common import settings


def get_redis_connection():
    """Get a connection to redis"""
    return aioredis.from_url(settings.REDIS_URI)


async def check_redis(retries=3, wait=1) -> bool:
    """Check that redis is available and accepting commands."""
    redis = get_redis_connection()
    try:
        await redis.ping()
    except Exception:
        if retries > 0:
            retries -= 1
            return check_redis(retries)
        return False
    else:
        return True


dependencies = (check_redis,)


async def available() -> bool:
    """Check that all dependencies are available."""
    results = []
    for check in dependencies:
        result = await check()
        results.append(result)

    return all(results)
