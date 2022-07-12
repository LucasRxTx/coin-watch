import asyncio
from collections import defaultdict

from common import dependencies, settings
from common.services import EventDispatcher, EventListenerBase, RemoteQueue


watched_symbols = defaultdict(set)
"""A map of symbols to a set of prices being watched."""


class EventListener(EventListenerBase):
    """Listen for specific system events."""
    channel = "events"
    events = {"watched", "price_above_target"}

    async def on_price_above_target(self, event):
        """Remove a price_price target from the watched prices.
        
        Can cause race condition.

        If message is inflight when another user wants to watch
        then it will be ignored since it is already in the set
        and then removed here, and the user may never
        be notified.

        Params:
            event (dict): A system event.
        """
        watched_symbols[event["symbol"]].discard(event["price_target"])

    async def on_watched(self, event):
        """Add a newly watched symbol to watched_symbols.
        
        Ingest has started watching a new symbol by user request.
        Add the symbol to watched_symbols and add the price target
        the user requested.
        """
        watched_symbols[event["symbol"]].add(event["price_target"])


class Watcher:
    """Watches price queue for when a symbol exceeds a price."""
    REMOTE_QUEUE = RemoteQueue
    EVENT_DISPATCHER = EventDispatcher

    def __init__(self):
        self.__queue = self.REMOTE_QUEUE()
        self.__event_dispatcher = self.EVENT_DISPATCHER()

    async def watch(self):
        """Listens to the `price` queue.
        
        Broadcasts `price_above_target` events when a price
        exceeds a watched symbols price_target.
        """
        while event := await self.__queue.pop():
            print("event", event)
            symbol = event["symbol"].lower()
            price = float(event["price"])
            for price_target in watched_symbols[symbol]:
                if price > price_target:
                    resp = await self.__event_dispatcher.dispatch(
                        {
                            "event": "price_above_target",
                            "symbol": symbol,
                            "current_price": str(price),
                            "price_target": price_target,
                        }
                    )
                    if not resp:
                        print("Event was ignored")


async def start():
    """Start the app."""
    while not await dependencies.available():
        print("One or more dependency is not available...")
        await asyncio.sleep(settings.DEPENDENCY_RETRY_TIME)

    await asyncio.gather(Watcher().watch(), EventListener().listen())


def main():
    """Main entry point."""
    asyncio.run(start())
