"""Consume the AnySearch streaming (NDJSON) endpoint.

The regular /v1/search endpoint buffers the whole response. For long queries
AnySearch also offers /v1/search/stream, which emits one JSON object per line
as hits are found. You get the first result in ~200ms instead of waiting for
the full page. This is the pattern I use when results feed a TUI.

Note: this endpoint sends `text/event-stream`-ish NDJSON, NOT SSE `data:`
frames. So we iterate lines, not events. Easy to get wrong.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator

import requests
from dotenv import load_dotenv

load_dotenv()

STREAM_URL = "https://api.anysearch.dev/v1/search/stream"


def stream_results(
    query: str,
    top_k: int = 20,
    timeout: float = 30.0,
) -> Iterator[dict]:
    """Yield result dicts one at a time as AnySearch emits them.

    The connection is kept open until the server sends a terminating line
    `{"done": true}` or closes the socket. `timeout` here is the *read*
    timeout, so a slow server won't hang you forever mid-stream.
    """
    key = os.environ.get("ANYSEARCH_KEY")
    if not key:
        raise RuntimeError("ANYSEARCH_KEY is not set")

    with requests.post(
        STREAM_URL,
        headers={"Authorization": f"Bearer {key}", "Accept": "application/x-ndjson"},
        json={"query": query, "top_k": top_k},
        stream=True,
        timeout=(5.0, timeout),  # (connect, read)
    ) as resp:
        resp.raise_for_status()
        for raw_line in resp.iter_lines(decode_unicode=True):
            if not raw_line:
                continue  # keep-alive newlines are common; skip them
            try:
                event = json.loads(raw_line)
            except json.JSONDecodeError:
                # A truncated final line can happen if the server dies. Don't
                # blow up the whole consumer for it.
                print(f"[warn] skipping malformed line: {raw_line[:80]!r}")
                continue
            if event.get("done"):
                return
            yield event


def main() -> int:
    query = os.environ.get("QUERY", "asyncio task group example")
    count = 0
    for hit in stream_results(query):
        count += 1
        print(f"{count:>2}. {hit.get('title', '(untitled)')}  ->  {hit.get('url', '')}")
    print(f"\n{count} results streamed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
