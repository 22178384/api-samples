"""Pagination helpers for list endpoints.

Two flavors show up in the wild and I got tired of writing both from scratch:

  * offset/limit  -> ?page=2&per_page=50   (or ?offset=50&limit=50)
  * cursor        -> ?after=<opaque>       (also called page tokens, keyset)

Both iterators below are lazy generators, so you can `for item in ...` and stop
early without fetching the rest. That matters on endpoints where page 40 is slow.

Targets the JSONPlaceholder-style shape: {"data": [...], "next_cursor": "..."}.
Swap the field names for your API; that's the only part that ever changes.
"""

from __future__ import annotations

from collections.abc import Iterator

import requests

TIMEOUT = (3.05, 20.0)


def iter_offset(
    session: requests.Session,
    url: str,
    per_page: int = 50,
    max_pages: int | None = None,
) -> Iterator[dict]:
    """Yield items from an offset/limit endpoint until a short page arrives.

    Stops when a page returns fewer than `per_page` items (the usual
    "you've hit the end" signal) or when `max_pages` is reached.

    Careful: if the underlying collection changes while you page, you can skip
    or duplicate rows. That's inherent to offset pagination; use the cursor
    version when the data is live.
    """
    page = 1
    while True:
        if max_pages is not None and page > max_pages:
            return
        resp = session.get(
            url,
            params={"page": page, "per_page": per_page},
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        items = resp.json().get("data", [])
        if not items:
            return
        yield from items
        if len(items) < per_page:
            return
        page += 1


def iter_cursor(
    session: requests.Session,
    url: str,
    limit: int = 50,
    max_items: int | None = None,
) -> Iterator[dict]:
    """Yield items following an opaque cursor until the server stops giving one.

    The cursor is opaque. Don't parse it, don't construct one by hand, don't
    assume it's a base64 id. Just pass it back verbatim.

    Safety valve: if the server keeps returning the same cursor forever (a real
    bug I've seen), the `seen` set breaks the loop instead of hanging.
    """
    cursor: str | None = None
    seen_cursors: set[str] = set()
    yielded = 0

    while True:
        params = {"limit": limit}
        if cursor:
            params["after"] = cursor

        resp = session.get(url, params=params, timeout=TIMEOUT)
        resp.raise_for_status()
        body = resp.json()

        items = body.get("data", [])
        for item in items:
            yield item
            yielded += 1
            if max_items is not None and yielded >= max_items:
                return

        cursor = body.get("next_cursor")
        if not cursor:
            return  # server said there's nothing after this page
        if cursor in seen_cursors:
            raise RuntimeError(f"cursor loop detected at {cursor!r}; aborting")
        seen_cursors.add(cursor)


def main() -> None:
    # Demo against a public paginated endpoint (no auth). It ignores our
    # per_page but still demonstrates the loop termination.
    with requests.Session() as s:
        n = 0
        for post in iter_offset(s, "https://jsonplaceholder.typicode.com/posts",
                                per_page=100, max_pages=1):
            n += 1
        print(f"offset iterator pulled {n} items (capped at 1 page)")

        titles = [p["title"] for p in iter_cursor(
            s, "https://jsonplaceholder.typicode.com/posts", limit=10, max_items=15)]
        print(f"cursor iterator pulled {len(titles)} items:")
        for t in titles[:3]:
            print(f"  - {t[:50]}")


if __name__ == "__main__":
    main()
