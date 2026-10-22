# DevToolBox · 开发者工具箱

一个开箱即用的免费开发者工具 API 集合，部署于轻量云服务器，无需注册、无需鉴权，直接调用即可。

**在线体验**：http://120.78.120.129/toolbox/
**交互式 API 文档**：http://120.78.120.129/docs

## 功能一览

| API | 说明 | 示例 |
|---|---|---|
| `GET /api/ip` | 查询请求者 IP 及归属地 | `/api/ip?detail=true` |
| `GET /api/qrcode` | 生成二维码 PNG | `/api/qrcode?text=https://example.com&size=300` |
| `GET /api/time` | Unix 时间戳 ↔ 日期时间转换 | `/api/time` `/api/time?ts=1730000000` |
| `GET /api/weather` | 城市实时天气（温度/湿度/风力） | `/api/weather?city=beijing` |
| `GET /api/rand` | 随机整数 / 字符串 / UUID / 颜色 | `/api/rand?type=uuid` |
| `GET /api/base64` | Base64 编码 / 解码 | `/api/base64?mode=encode&text=hello` |
| `GET /api/urlcode` | URL 编码 / 解码 | `/api/urlcode?mode=decode&text=%E4%B8%AD` |
| `GET /api/hash` | MD5 / SHA-1 / SHA-256 / SHA-512 | `/api/hash?algo=sha256&text=hello` |
| `GET /api/status` | 服务状态与调用统计 | `/api/status` |

所有接口均返回标准 JSON（二维码接口返回 PNG 图片），支持 CORS，可直接在浏览器 / 小程序 / 服务端调用。

## 快速开始

```bash
# 查 IP 归属地
curl "http://120.78.120.129/toolbox/api/ip?detail=true"

# 生成二维码
curl -o qr.png "http://120.78.120.129/toolbox/api/qrcode?text=hello&size=300"

# 随机 UUID
curl "http://120.78.120.129/toolbox/api/rand?type=uuid"
```

## 技术栈

- 后端：Python + FastAPI + Uvicorn
- 部署：Docker 容器（`--restart unless-stopped` 无人值守）
- 存储：SQLite（仅匿名调用统计）
- 入口：Nginx 反向代理

## 本地部署

```bash
git clone https://github.com/gmemoryx-beep/devtoolbox.git
cd devtoolbox
docker build -t devtoolbox:1.0 .
docker run -d --name devtoolbox --restart unless-stopped -p 8088:8088 \
  -v $(pwd)/data:/app/app/data devtoolbox:1.0
```

## 支持项目

DevToolBox 完全免费开放。如果你觉得有用，欢迎赞助支持服务器的维护与升级（赞助通道筹备中）。

## 许可

本项目仅供学习与个人使用。数据源接口（天气、IP 归属地）归各数据源所有，请遵守其服务条款。
