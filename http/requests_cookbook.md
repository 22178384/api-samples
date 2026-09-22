# requests cookbook

Patterns I reach for constantly. This is `requests` 2.31-ish; older 2.25 versions
are missing a couple of the timeout behaviors below.

## 1. Always set a timeout

`requests` has **no default timeout**. A server that accepts the connection and
then stalls will hang your process forever. This bites everyone exactly once.

```python
import requests

# One float = applied to both connect and read.
r = requests.get("https://httpbin.org/delay/2", timeout=5.0)

# Tuple = (connect, read). Prefer this: fail fast on DNS/connect, allow a slow body.
r = requests.get("https://httpbin.org/delay/2", timeout=(2.0, 15.0))
```

If you see `requests.exceptions.ConnectTimeout` it's the connect phase;
`ReadTimeout` is the server not sending bytes in time.

## 2. Sessions for connection reuse

A bare `requests.get()` opens a new TCP connection (and does a new TLS
handshake) every call. For anything with more than a couple of requests, use a
`Session`. It also persists cookies and headers.

```python
with requests.Session() as s:
    s.headers.update({"User-Agent": "my-tool/1.2 (+https://example.com)"})
    for page in range(1, 6):
        r = s.get(f"https://api.example.com/items?page={page}", timeout=10)
        r.raise_for_status()
        ...
```

## 3. Retries that actually retry

`HTTPAdapter` + `Retry` is the only sane way. Mount it on the session so it
applies to every request.

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

retry = Retry(
    total=5,
    backoff_factor=0.5,          # sleeps 0, 0.5, 1, 2, 4s between attempts
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET", "HEAD", "OPTIONS", "POST"]),
    respect_retry_after_header=True,   # honor 429 Retry-After
)

s = requests.Session()
adapter = HTTPAdapter(max_retries=retry)
s.mount("https://", adapter)
s.mount("http://", adapter)
```

Gotcha: by default `Retry` does **not** retry POST (only idempotent verbs). If
your POST is idempotent (e.g. a search query) add it to `allowed_methods` like
above. Do NOT add non-idempotent POSTs or you'll double-charge someone.

## 4. Auth headers

```python
# Bearer token
s.headers["Authorization"] = f"Bearer {token}"

# Basic
s.auth = ("user", "pass")            # or requests.auth.HTTPBasicAuth(...)

# API key in a custom header (very common)
s.headers["X-API-Key"] = api_key
```

Never log the header dict wholesale. I've leaked a token into CI logs this way.

## 5. Streaming a big download

Don't `r.content` a 2GB file into RAM. Stream it and let it land on disk.

```python
with requests.get(url, stream=True, timeout=(5, 60)) as r:
    r.raise_for_status()
    with open("dump.bin", "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MiB
            f.write(chunk)
```

## 6. Error handling cheat sheet

```python
try:
    r = s.get(url, timeout=(3.05, 10))
    r.raise_for_status()
except requests.exceptions.ConnectTimeout:
    ...  # DNS or TCP handshake took too long
except requests.exceptions.ReadTimeout:
    ...  # connected, but body didn't arrive
except requests.exceptions.HTTPError as e:
    ...  # 4xx/5xx; e.response.status_code has the code
except requests.exceptions.RequestException as e:
    ...  # catch-all base class
```

## 7. JSON round-trip

```python
r = s.post(url, json={"q": "hello"}, timeout=10)   # sets Content-Type for you
data = r.json()                                    # raises if body isn't JSON
```

`r.json()` raises `requests.exceptions.JSONDecodeError` (2.27+) when the body
isn't JSON. Wrap it if the endpoint can return an HTML error page.

## 8. Debugging

When a request does something weird and you can't see why, bump the logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
# or, for one request:
resp = s.get(url, timeout=5)
print(resp.request.headers)   # what we actually sent
print(resp.request.body)
```
