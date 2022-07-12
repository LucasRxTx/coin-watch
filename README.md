Coin Watch
===

Get notified when a crypto pair goes above your desired price.


## Quick Start

```shell
docker compose up --build
```

Connect to the web socket server on `ws://127.0.0.1:9090/ws`

send payload

```json
{
    "cmd": "watch",
    "symbol": "btcusdc",
    "price": 1.0
}
```

You will get a response on the web socket connection on the next trade to `Take profit on btcusdc`.


### Payload

`cmd` No need to change, watch is currently the only command.

`symbol` must be a lowercase coin pair available on Binance.

`price` can be any floating point number but INF is sure to cause issues.


## Contol Flow

- `ingest` subscribes to default symbols and starts streaming prices.
- `ingest` adds prices to an internal queue with the `symbol`, `current_price` and `price_target`.
- `watch` checks each added price to see if a there is a price watch.
- if `watch` finds the price of a symbol has gone over any requested threshold, it will publish a `price_above_target` event.
- `watch` listens to it's own `price_above_target` events to purge the price watch list of that price point.  This has a race condition edge case in multi-user environments.
- `api` listens to `price_above_target` events.  If there is an event, any users watching this symbol at this price will be notified to take profit.
- `api` waits for a user to connect to the websocket endpoint.
- when user sends a valid command to the `api` a `watch` command is published internally with the `symbol`, and `price_target`.
- `ingest` process the command queue for `watch` commands.
- `ingest` will subscribe to the symbol in the command.
- `ingest` publishes a `watched` event with the the `symbol`, and `price_target`.
- `watch` listens for `watched` messages and will add the `symbol`, and `price_target` to the watched list.


## Further development

- Error checking is very light, and things are sure to blow up if the happy path is not adheared to.
- There is no way for a user to stop watching, or unsubscribe from a symbol.
- Once a symbol is subscribed to the system will always be subscribed to that symbol untill redis restart.
- The control flow is confusing.
- Better documentation.
