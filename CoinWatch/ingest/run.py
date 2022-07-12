#!/usr/bin/env python3
import asyncio
import json
from functools import partial

import ingest.settings
import websockets
from common import dependencies, settings
from common.services import CommandQueue, EventDispatcher, RemoteQueue
from ingest.services import CoinWatchService


def symbols_to_stream_names(symbols):
    """Map a symbol to a Binance stream name."""
    return list(f"{symbol}@aggTrade" for symbol in symbols)


def get_subscribe_payload(symbols):
    """Map a set of symbols to a subscribe payload."""
    return dict(
        method="SUBSCRIBE",
        params=symbols_to_stream_names(symbols),
        id=1,
    )


def get_unsubscribe_payload(symbols):
    """Map a set of symbols to an unsubscribe payload."""
    return dict(
        method="UNSUBSCRIBE",
        params=symbols_to_stream_names(symbols),
        id=312,
    )


class BinanceIngestor:
    """Stream trade data from binance in realtime.

    Stream is processed and added to the `prices` queue.
    """

    WEBSOCKET_URI = ingest.settings.BINANCE_WEBSOCKET_URI
    SYMBOL_PROVIDER = CoinWatchService
    REMOTE_QUEUE = RemoteQueue
    COMMAND_QUEUE = CommandQueue
    EVENT_DISPATCHER = EventDispatcher
    WEBSOCKET_CONNECTION_FACTORY = partial(
        websockets.connect, WEBSOCKET_URI
    )

    def __init__(self, websocket_uri=None):
        self.__connection_factory = self.WEBSOCKET_CONNECTION_FACTORY
        self.__ws = None
        self.__symbol_provider = self.SYMBOL_PROVIDER()
        self.__remote_queue = self.REMOTE_QUEUE()
        self.__command_queue = self.COMMAND_QUEUE()
        self.__event_dispatcher = self.EVENT_DISPATCHER()

    async def __send(self, data):
        """Send a payload to Binance.

        Params:
            data (dict): Payload to send to Binance.
                Payload must be json serializable.
        """
        payload = json.dumps(data)
        try:
            return await self.__ws.send(payload)
        except AttributeError:
            raise RuntimeError(
                f"{self.__class__.__name__} must be run before send is called."
            )

    async def subscribe(self, symbols):
        """Subscribe to a set of symbols."""
        payload = get_subscribe_payload(symbols)
        return await self.__send(payload)

    async def unsubscribe(self, symbols):
        """Subscribe to a set of symbols."""
        payload = get_unsubscribe_payload(symbols)
        return await self.__send(payload)

    async def get_events(self):
        """Get real time trade events from Binance.

        This is an async generator function that yields events.
        """
        async for event in self.__ws:
            try:
                yield json.loads(event)
            except Exception:
                print("Failed to parse:", event)

    async def get_commands(self):
        """Get commands sent to the ingest system.

        Async generator function that yield commands
        from the command queue.
        """
        while command := await self.__command_queue.pop():
            yield command

    async def handle_event(self, event):
        """Handle Binance websocket events."""
        if event.get("e") == "aggTrade":
            data = {
                "symbol": event["s"],
                "price": event["p"],
            }
            print("ingesting", data)
            # enqueue pricing events to the internal price queue.
            await self.__remote_queue.add(data)

    async def handle_command(self, command):
        """Handle internal commands sent to the ingest system."""
        if command.get("cmd") == "watch":
            # Command to watch a new symbol
            print("Handling Command:", command)
            symbol = command["symbol"].lower()
            await self.__symbol_provider.add_watched_symbol(symbol)
            await self.subscribe(symbol)
            await self.__event_dispatcher.dispatch(
                # Broadcast to the event queue that we have started watching.
                dict(
                    event="watched",
                    symbol=symbol,
                    price_target=command["price_target"],
                )
            )

    async def run(self):
        """Run the Binance price ingestion.

        This will block forever.  It does not handle graceful shutdowns.
        """
        async with self.__connection_factory() as ws:
            self.__ws = ws
            # setup some default symbols just to see thing working
            await self.__symbol_provider.add_default_watched_symbols()
            symbols = await self.__symbol_provider.get_watched_symbols()
            await self.subscribe(symbols)

            async def event_loop():
                try:
                    async for event in self.get_events():
                        if isinstance(event, dict):
                            await self.handle_event(event)
                finally:
                    await self.unsubscribe(symbols)

            async def command_loop():
                async for command in self.get_commands():
                    if isinstance(command, dict):
                        await self.handle_command(command)

            await asyncio.gather(event_loop(), command_loop())


async def start():
    """Start the app."""
    while not await dependencies.available():
        print("One or more dependency is not available...")
        await asyncio.sleep(settings.DEPENDENCY_RETRY_TIME)

    await BinanceIngestor().run()


def main():
    """Main entry point."""
    asyncio.run(start())
