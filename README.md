# api-samples

I keep rewriting the same HTTP boilerplate every time I start a project that talks
to a third-party API. Retry logic, timeouts, token refresh, pagination... so this
repo is where I dump the versions I've actually shipped, minus the stuff that's
specific to my employer.

Everything here is small and copy-pasteable. No frameworks, just `requests`,
`httpx` and the stdlib. Python 3.10+ (I use `match` in one or two places and
`str | None` type hints).

## What's in here

```
anysearch/     AnySearch search API: batch queries + streaming results
http/          requests cookbook (md) and an httpx async example
graphql/       a working GraphQL POST + notes on schema introspection
rest/          cursor + offset pagination against a list endpoint
auth/          OAuth2 authorization-code flow, token refresh included
openapi/       notes on reading an OpenAPI spec without crying
examples/      .env.example — copy to .env and fill in
```

## Setup

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install requests httpx python-dotenv
cp examples/.env.example .env    # then edit .env
```

I deliberately don't ship a `requirements.txt` with pinned versions, because
pinning `requests==2.28.1` in a samples repo ages badly. If you want pins, run
`pip freeze > requirements.txt` after install.

## Running the samples

Each file is standalone. Most read the key from the environment:

```bash
export ANYSEARCH_KEY=YOUR_ANYSEARCH_KEY
python anysearch/batch_search.py
```

`http/requests_cookbook.md` is prose, not code. Read it in your editor.

## Gotchas

- **`.env` is not loaded automatically.** I call `load_dotenv()` explicitly at
  the top of each script. If you forget, you'll get `KeyError: 'ANYSEARCH_KEY'`
  and wonder why.
- **`async_http.py` needs a running event loop.** Running it with `python
  async_http.py` works because I put an `asyncio.run()` at the bottom, but if you
  import the functions into a sync context you'll get
  `RuntimeError: no running event loop`.
- **The OAuth example never hits a real provider.** I left the endpoints as
  `https://auth.example.com/...` on purpose. Swap them for your provider's.
- On macOS the system Python is 3.9 and `httpx` latest wants 3.8+, so that's fine,
  but `str | None` annotations will blow up. Use a venv with 3.10+.

## Notes

These are samples, not a library. I won't be adding tests, and I'm not
maintaining backward compatibility — if I find a better pattern I'll just edit
the file. Fork it and make it yours.

Licensed MIT. See LICENSE.
