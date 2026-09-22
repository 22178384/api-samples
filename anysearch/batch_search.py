"""批量搜索示例（概念代码，需配合真实 SDK）。"""

import os


def batch_search(queries):
    key = os.environ.get("ANYSEARCH_API_KEY", "")
    for q in queries:
        # 真实环境替换为官方 SDK 调用
        print(f"[mock] search({q!r}) key=***{key[-4:] if key else 'NONE'}")
    return len(queries)


if __name__ == "__main__":
    batch_search(["向量数据库", "GitHub API", "Python 异步"])
