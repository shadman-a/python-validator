from __future__ import annotations

import argparse

from src.web.server import run

MAX_UPLOAD_MB = 25


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8787)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args()

    run(args.host, args.port, open_browser=not args.no_open)


if __name__ == "__main__":
    main()
