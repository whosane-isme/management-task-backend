from __future__ import annotations

import argparse

import uvicorn

from app.core.event_loop import compatible_event_loop_factory


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Management Task API")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8000, type=int)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        loop=compatible_event_loop_factory,
    )


if __name__ == "__main__":
    main()
