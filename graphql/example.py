"""Minimal GraphQL client with plain requests.

Everyone reaches for gql or sgqlc, and that's fine for big schemas. But GraphQL
over HTTP is just a POST with a {"query", "variables"} body, and sometimes you
don't want a codegen dependency. This is the raw version.

I point it at the Countries API because it's public and needs no key:
https://countries.trevorblades.com/
"""

from __future__ import annotations

import requests

ENDPOINT = "https://countries.trevorblades.com/"

# Note: GraphQL queries are strings. Multi-line f-strings get ugly, so we keep
# the query as a constant and pass values through `variables`. Never string-
# format user input into a query — that's the GraphQL injection footgun.
COUNTRY_QUERY = """
query CountryByCode($code: ID!) {
  country(code: $code) {
    name
    capital
    currency
    languages {
      name
    }
  }
}
"""

CONTINENTS_QUERY = """
query {
  continents {
    code
    name
  }
}
"""


def gql(query: str, variables: dict | None = None, timeout: float = 10.0) -> dict:
    """POST a query and return the `data` field.

    GraphQL always returns HTTP 200 for application-level errors, so you must
    inspect the body's `errors` array yourself. raise_for_status() alone will
    not catch a bad query.
    """
    payload = {"query": query, "variables": variables or {}}
    resp = requests.post(
        ENDPOINT,
        json=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        timeout=timeout,
    )
    resp.raise_for_status()

    body = resp.json()
    if body.get("errors"):
        # Each error looks like {"message": "...", "locations": [...], "path": [...]}
        msgs = "; ".join(e.get("message", "?") for e in body["errors"])
        raise RuntimeError(f"GraphQL errors: {msgs}")
    return body["data"]


def main() -> None:
    country = gql(COUNTRY_QUERY, {"code": "JP"})["country"]
    langs = ", ".join(l["name"] for l in country["languages"])
    print(f"{country['name']}  capital={country['capital']}  "
          f"currency={country['currency']}  langs={langs}")

    continents = gql(CONTINENTS_QUERY)["continents"]
    print(f"\n{len(continents)} continents:")
    for c in continents:
        print(f"  {c['code']}  {c['name']}")


if __name__ == "__main__":
    main()
