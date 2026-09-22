# requests 速查

```python
import requests

r = requests.get("https://api.github.com", timeout=10)
r.raise_for_status()
print(r.status_code, r.json())

# POST JSON
requests.post(url, json={"a": 1}, timeout=10)
# 带鉴权
requests.get(url, headers={"Authorization": "Bearer TOKEN"})
```
