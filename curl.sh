# DevToolBox API 调用示例（curl）
BASE="http://120.78.120.129/toolbox"

# 1. 查 IP 归属地
curl "$BASE/api/ip?detail=true"

# 2. 生成二维码（保存为 PNG）
curl -o qr.png "$BASE/api/qrcode?text=https://example.com&size=300"

# 3. 当前时间戳
curl "$BASE/api/time"

# 4. 时间戳转日期
curl "$BASE/api/time?ts=1730000000&tz=8"

# 5. 天气（拼音或英文）
curl "$BASE/api/weather?city=zhongshan"

# 6. 随机 UUID
curl "$BASE/api/rand?type=uuid"

# 7. 随机整数
curl "$BASE/api/rand?type=int&min=1&max=100"

# 8. Base64 编码
curl "$BASE/api/base64?mode=encode&text=hello%20world"

# 9. SHA-256 哈希
curl "$BASE/api/hash?algo=sha256&text=hello"

# 10. 服务状态与统计
curl "$BASE/api/status"
