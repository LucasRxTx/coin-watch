import argparse

parser = argparse.ArgumentParser(description="Start an application from CoinWatch.")
parser.add_argument("app", type=str, help="api, ingest, or watch")
args = parser.parse_args()


def run_api():
    from api.run import main as api_main

    api_main()


def run_ingest():
    from ingest.run import main as ingest_main

    ingest_main()


def run_watch():
    from watch.run import main as watch_main

    watch_main()


run_map = dict(
    api=run_api,
    ingest=run_ingest,
    watch=run_watch,
)

run_map[args.app]()
