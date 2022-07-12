import asyncio
import json
from collections import defaultdict

import uvicorn
from common import dependencies, settings
from common.services import CommandQueue, EventDispatcher, EventListenerBase
from fastapi import FastAPI, WebSocket

app = FastAPI()
clients = defaultdict(set)


class EventListener(EventListenerBase):
    """Listen to internal events."""

    channel = "events"
    events = {"price_above_target"}

    async def notify_client(self, client, event):
        await client.send_text(f"Take profit on {event['symbol']}")

    async def on_price_above_target(self, event):
        print("price above target")
        key = (event["symbol"], event["price_target"])
        clients_to_notify = clients[key]
        tasks = list(self.notify_client(client, event) for client in clients_to_notify)
        await asyncio.gather(*tasks)
        clients.pop(key)


@app.on_event("startup")
async def start_event_handler():
    """Make sure depencies are available and start background tasks.

    If the EventListener dies/disconnects/raises an exception for
    any reason, the background task will die and the app will
    be in a broken state.  Restart the container manually.
    """
    while not await dependencies.available():
        print("One or more dependency is not available...")
        await asyncio.sleep(settings.DEPENDENCY_RETRY_TIME)

    asyncio.create_task(EventListener().listen())


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Main websocket endpoint.

    Does not gracefully handle anything other than the happy path.
    """
    await websocket.accept()
    command_queue = CommandQueue()
    while True:
        data_raw = await websocket.receive_text()
        try:
            data = json.loads(data_raw)
        except Exception:
            await websocket.send_text(f"Message was not valid json: {data_raw}")
            continue

        if "cmd" in data and data["cmd"] == "watch":
            symbol = data["symbol"].lower()
            price = data["price"]
            clients[(symbol, price)].add(websocket)
            await command_queue.add(
                {"cmd": "watch", "symbol": symbol, "price_target": price}
            )

        await websocket.send_text(data_raw)


def main():
    """Start the Uvicorn server."""
    uvicorn.run(app, port=9090, host="0.0.0.0")
