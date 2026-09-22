"""最简 GraphQL 查询示例（用 requests）。"""

import json
import os

import requests


def gql(query: str, variables: dict | None = None) -> dict:
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables or {}},
        headers={"Authorization": f"Bearer {os.environ.get('GH_TOKEN', '')}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    q = "{ viewer { login } }"
    print(gql(q))
