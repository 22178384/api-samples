"""Concurrent HTTP with httpx.AsyncClient.

Same idea as anysearch/batch_search.py but without threads. I wrote this after
hitting ~200 threads on a fan-out job and watching the GIL + thread overhead eat
the gains. For pure I/O wait, async wins once you're past a few dozen requests.

Needs: pip install httpx
"""

from __future__ import annotations

import asyncio
import time

import httpx

BASE = "https://httpbin.org"
# Cap concurrency so we don't get banned / exhaust file descriptors. httpx
# keeps a connection pool per client; 20 is comfortable for most APIs.
CONCURRENCY = 20


async def fetch_one(client: httpx.AsyncClient, path: str) -> tuple[str, int, float]:
    """GET one path, return (path, status_code, elapsed_seconds).

    We don't raise on 4xx/5xx here. For a fan-out you usually want to count
    failures, not abort the whole gather() on the first one.
    """
    start = time.perf_counter()
    resp = await client.get(path)
    elapsed = time.perf_counter() - start
    return path, resp.status_code, elapsed


async def fetch_many(paths: list[str]) -> list[tuple[str, int, float]]:
    """Fetch every path concurrently under a semaphore.

    A plain asyncio.gather() would fire all requests at once. The semaphore is
    what actually bounds concurrency — the AsyncClient alone doesn't.
    """
    sem = asyncio.Semaphore(CONCURRENCY)

    async def guarded(client: httpx.AsyncClient, path: str):
        async with sem:
            return await fetch_one(client, path)

    # limits=... also caps the connection pool; keep it >= CONCURRENCY.
    limits = httpx.Limits(max_connections=CONCURRENCY, max_keepalive_connections=10)
    async with httpx.AsyncClient(
        base_url=BASE, timeout=httpx.Timeout(10.0, connect=3.0), limits=limits
    ) as client:
        tasks = [guarded(client, p) for p in paths]
        return await asyncio.gather(*tasks)


async def with_retry(
    client: httpx.AsyncClient, path: str, attempts: int = 3
) -> httpx.Response:
    """Retry a single request with exponential backoff.

    httpx has no built-in retry (httpx-retry exists but I don't want the dep
    here). This is the minimal version I keep re-writing.
    """
    last: Exception | None = None
    for i in range(attempts):
        try:
            resp = await client.get(path)
            if resp.status_code < 500 and resp.status_code != 429:
                return resp
            last = httpx.HTTPStatusError(
                f"server returned {resp.status_code}",
                request=resp.request,
                response=resp,
            )
        except httpx.TransportError as exc:  # timeouts, connection resets
            last = exc
        # backoff: 0.5s, 1s, 2s ... (skip the sleep after the final attempt)
        if i < attempts - 1:
            await asyncio.sleep(0.5 * (2**i))
    raise last  # type: ignore[misc]


async def main() -> None:
    paths = [f"/delay/{i % 3}" for i in range(30)]

    t0 = time.perf_counter()
    results = await fetch_many(paths)
    wall = time.perf_counter() - t0

    ok = sum(1 for _, code, _ in results if code == 200)
    slowest = max(r[2] for r in results)
    print(f"{len(results)} requests in {wall:.2f}s wall "
          f"(slowest single request {slowest:.2f}s, {ok} ok)")

    # Sanity check the retry helper on a flaky endpoint.
    async with httpx.AsyncClient(base_url=BASE, timeout=10) as client:
        resp = await with_retry(client, "/status/500")
        print(f"retry helper gave up with status {resp.status_code} as expected")


if __name__ == "__main__":
    asyncio.run(main())
