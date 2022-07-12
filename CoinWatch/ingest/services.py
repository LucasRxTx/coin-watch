from common import dependencies


class CoinWatchService:
    WATCHED_SYMBOLS_KEY = "watched_symbols"

    DEFAULT_WATCH_SYMBOLS = (
        "sandusdc",
        "btcusdc",
        "ethusdc",
    )

    def __init__(self, redis=None):
        self.__redis = redis or dependencies.get_redis_connection()

    async def get_watched_symbols(self):
        raw_data = await self.__redis.smembers(self.WATCHED_SYMBOLS_KEY)
        return set(raw_symbol.decode("utf8") for raw_symbol in raw_data)

    async def add_watched_symbols(self, symbols):
        for symbol in symbols:
            await self.add_watched_symbol(symbol)

    async def add_watched_symbol(self, symbol):
        await self.__redis.sadd(self.WATCHED_SYMBOLS_KEY, symbol)

    async def add_default_watched_symbols(self):
        await self.add_watched_symbols(self.DEFAULT_WATCH_SYMBOLS)
