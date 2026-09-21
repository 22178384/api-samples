# curl 速查

## GET 带鉴权
    curl -s -H "Authorization: Bearer $TOKEN" https://api.example.com/me

## POST JSON
    curl -s -X POST https://api.example.com/x \
      -H "Content-Type: application/json" \
      -d '{"q":"hello"}'

## 跟随重定向 + 显示耗时
    curl -sL -w "time=%{time_total}\n" https://example.com

## 上传文件
    curl -s -F "file=@./a.png" https://example.com/upload

## 把响应格式化（需 jq）
    curl -s ... | jq .

## 保存响应到文件
    curl -s https://example.com -o out.html
