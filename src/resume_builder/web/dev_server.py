"""Development server entrypoint for Windows-friendly local previews."""

from __future__ import annotations

import asyncio
import sys

import uvicorn


def main() -> None:
    loop: str | type[asyncio.AbstractEventLoop] = "auto"
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        loop = asyncio.SelectorEventLoop

    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    uvicorn.run("resume_builder.web.app:app", host="127.0.0.1", port=port, loop=loop)


if __name__ == "__main__":
    main()
