"""Run several AnySearch queries in one go and print the top hits.

The AnySearch HTTP API takes one query per request, so "batch" here just means
firing a handful of requests against a thread pool and stitching the results
together. That's the whole trick. I used to do this serially and wait ~8s for
six queries; with a pool of 4 it's under 2s.

Usage:
    export ANYSEARCH_KEY=YOUR_ANYSEARCH_KEY
    python anysearch/batch_search.py "python retry library" "httpx vs requests"
"""

from __future__ import annotations

import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://api.anysearch.dev/v1/search"
DEFAULT_TOP_K = 5
# AnySearch returns 429 if you go much above ~5 concurrent requests on the free
# tier. Learned that the annoying way.
MAX_WORKERS = 4


def search(query: str, top_k: int = DEFAULT_TOP_K, timeout: float = 10.0) -> dict:
    """Run a single AnySearch query and return the parsed JSON body.

    Raises requests.HTTPError on a non-2xx response. Callers that fan out
    should catch it per-future, otherwise one bad query kills the whole batch.
    """
    key = os.environ.get("ANYSEARCH_KEY")
    if not key:
        raise RuntimeError("ANYSEARCH_KEY is not set. Did you copy .env.example?")

    resp = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        json={"query": query, "top_k": top_k, "safe_search": True},
        timeout=timeout,
    )
    # Call raise_for_status() *after* checking for the key, so a 401 shows the
    # server's message rather than a bare "403" with no context.
    resp.raise_for_status()
    return resp.json()


def batch(queries: list[str], top_k: int = DEFAULT_TOP_K) -> dict[str, list[dict]]:
    """Search every query concurrently. Returns {query: [hit, ...]}.

    A query that errors out maps to an empty list; the error is printed to
    stderr so you can see which one failed without losing the rest.
    """
    results: dict[str, list[dict]] = {q: [] for q in queries}

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {pool.submit(search, q, top_k): q for q in queries}
        for fut in as_completed(futures):
            query = futures[fut]
            try:
                body = fut.result()
            except requests.HTTPError as exc:
                print(f"[warn] {query!r} failed: {exc}", file=sys.stderr)
                continue
            # The response shape is {"results": [{"title", "url", "snippet"}]}.
            results[query] = body.get("results", [])

    return results


def main(argv: list[str]) -> int:
    if not argv:
        print("usage: batch_search.py QUERY [QUERY ...]", file=sys.stderr)
        return 2

    for query, hits in batch(argv).items():
        print(f"\n=== {query} ({len(hits)} hits) ===")
        for i, hit in enumerate(hits, 1):
            print(f"{i}. {hit.get('title', '(no title)')}")
            print(f"   {hit.get('url', '')}")
            snippet = hit.get("snippet", "").strip()
            if snippet:
                # Collapse whitespace so the terminal doesn't wrap into a mess.
                print(f"   {' '.join(snippet.split())[:140]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
