import asyncio
import json

from common import dependencies


class RemoteQueue:
    """A LIFO queue implemented with redis.

    Items are added on the left, and poped from the right.

    To listen to another queue, subclass and override QUEUE_NAME.
    """

    QUEUE_NAME = "price"

    def __init__(self, redis=None):
        self.__redis = redis or dependencies.get_redis_connection()

    async def add(self, event):
        """Add an item to the queue.

        Params:
            event (dict): An event to enque.
        """
        event_serialized = json.dumps(event)
        await self.__redis.lpush(self.QUEUE_NAME, event_serialized)

    async def pop(self):
        """Pop a value from the queue.

        Blocks untill there is a value to return.
        """
        event_serialized = await self.__redis.brpop(self.QUEUE_NAME)
        return json.loads(event_serialized[1].decode("utf8"))


class CommandQueue(RemoteQueue):
    """A RemoteQueue for the `ingest_commands` queue.

    Queue is for sending commands the the ingest app.
    """

    QUEUE_NAME = "ingest_commands"


class EventDispatcher:
    """Broadcast an event to all subscribers.

    The `events` channel is used by all apps for broadcasting
    system events.
    """

    channel = "events"

    def __init__(self, redis=None):
        self.__redis = redis or dependencies.get_redis_connection()

    async def dispatch(self, data):
        """Publish data to the channel.

        Params:
            data (dict): Data to publish to the channel.
                Data must be json serializable.
        """
        return await self.__redis.publish(self.channel, json.dumps(data))


class EventListenerBase:
    """Listen to messages broadcast on a channel.

    To listen to more events, add the event you want to
    listen for to the events set, and a method called
    f"on_{event_name}" that takes an event as it's only
    argument.
    """

    channel = ""
    """Channel to listen too."""
    events = {}
    """A set of events that can be processed.
    
    There must be a matching on_event_name method added to
    the class or a NotImplementedError will be thrown when
    an event with that name is processed.
    """

    def __init__(self, redis=None):
        self.__redis = redis or dependencies.get_redis_connection()
        self.__pubsub = self.__redis.pubsub()

    async def __handle_events(self, channel):
        """Dispatch an event to a on_event_name handler.

        Event name must be in the events set in order to be
        dispatched to a handler.
        """
        while True:
            event_raw = await channel.get_message(
                ignore_subscribe_messages=True,
            )
            if event_raw:
                event = json.loads(event_raw["data"].decode("utf8"))
                print("Got Message:", event)
                if event["event"] in self.events:
                    try:
                        handler = getattr(self, f"on_{event['event']}")
                    except NotImplementedError:
                        print(f"`on_{event['event']}` not implemented")
                    await handler(event)
            else:
                await asyncio.sleep(1)

    async def listen(self):
        """Start listening to messages on a channel.

        Runs forever, and does not gracefully shutdown,
        timeout or retry.
        """
        async with self.__pubsub as pubsub:
            await pubsub.subscribe(self.channel)
            try:
                await self.__handle_events(pubsub)
            finally:
                await pubsub.unsubscribe(self.channel)
