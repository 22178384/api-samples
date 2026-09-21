#!/usr/bin/env python3
"""AnySearch 搜索调用示例（可复用函数版）。

与 @c991china/anysearch-mcp-guide 配套：指南讲「怎么接」，本文件给「能跑的代码」。
用法：
    export ANYSEARCH_API_KEY=as_sk_xxxx
    python anysearch/search_example.py "Python 异步编程"
"""
import json
import os
import sys
import urllib.request

ENDPOINT = "https://api.anysearch.com/mcp"


def _rpc(payload: dict) -> dict:
    api_key = os.environ.get("ANYSEARCH_API_KEY")
    if not api_key:
        sys.exit("缺少环境变量 ANYSEARCH_API_KEY")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ENDPOINT,
        data=data,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = resp.read().decode("utf-8")
    if "data:" in raw:  # 兼容 SSE
        for line in raw.splitlines():
            if line.startswith("data:"):
                raw = line[5:].strip()
    return json.loads(raw)


def search(query: str, limit: int = 5) -> list:
    """返回搜索结果列表。"""
    _rpc({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2024-11-05", "capabilities": {},
        "clientInfo": {"name": "api-samples", "version": "1.0.0"}}})
    res = _rpc({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
        "name": "search", "arguments": {"query": query, "limit": limit}}})
    # 结果通常在 result.content 里，按文本提取
    content = res.get("result", {}).get("content", [])
    return [c.get("text", "") for c in content if c.get("type") == "text"]


if __name__ == "__main__":
    q = sys.argv[1] if len(sys.argv) > 1 else "Python 异步编程"
    for item in search(q):
        print(item)
