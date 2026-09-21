#!/usr/bin/env python3
"""GitHub REST API 示例：用标准库列出当前用户的公开仓库。

演示跨账号协作：本文件由 @c991china 提交 PR 到 @22178384/api-samples。
用法：
    export GH_TOKEN=ghp_xxx
    python github/rest_examples.py
"""
import json
import os
import sys
import urllib.request


def list_public_repos(per_page: int = 10) -> list:
    token = os.environ.get("GH_TOKEN")
    if not token:
        sys.exit("缺少环境变量 GH_TOKEN")
    url = f"https://api.github.com/user/repos?per_page={per_page}&type=owner"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        repos = json.loads(resp.read().decode("utf-8"))
    return [(r["name"], "public" if not r["private"] else "private", r["fork"]) for r in repos]


if __name__ == "__main__":
    for name, vis, fork in list_public_repos():
        print(f"{name}  [{vis}]  fork={fork}")
