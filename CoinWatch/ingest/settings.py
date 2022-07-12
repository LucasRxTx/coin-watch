import os

REDIS_URI = os.getenv("REDIS_URI", "redis://redis")
DEPENDENCY_RETRY_TIME = int(os.getenv("DEPENDENCY_RETRY_TIME", "1"))
BINANCE_WEBSOCKET_URI = "wss://stream.binance.com:9443/ws/aggTrade"
