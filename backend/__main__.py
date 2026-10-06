"""Run CivicFlow with ``python -m backend``."""

import argparse
import logging

from .server import serve


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local CivicFlow application.")
    parser.add_argument("--host", default="127.0.0.1", help="Loopback bind address.")
    parser.add_argument(
        "--port", type=int, default=0,
        help="HTTP port; use 0 to let the operating system choose an available port.",
    )
    parser.add_argument("--log-level", default="INFO", choices=("DEBUG", "INFO", "WARNING", "ERROR"))
    arguments = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, arguments.log_level),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    serve(arguments.host, arguments.port)


if __name__ == "__main__":
    main()
