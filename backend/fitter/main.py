# -*- coding: utf-8 -*-
import asyncio
from fitter.aggregation.collector import Collector
from utils import setup_backend_logbook


def main():
    with setup_backend_logbook("fitter"):
        loop = asyncio.get_event_loop()
        extract_usage = Collector()
        loop.run_until_complete(asyncio.wait([extract_usage.start(), ]))
        loop.close()


if __name__ == "__main__":
    main()
