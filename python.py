"""DevToolBox API 调用示例（Python 3，仅标准库，零依赖）"""
import json
import urllib.parse
import urllib.request

BASE = "http://120.78.120.129/toolbox"


def _get(path: str, params: dict | None = None) -> bytes:
    url = BASE + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=10) as resp:
        return resp.read()


def ip_info() -> dict:
    """查询本机公网 IP 及归属地"""
    return json.loads(_get("/api/ip", {"detail": "true"}))


def weather(city: str) -> dict:
    """查询城市天气"""
    return json.loads(_get("/api/weather", {"city": city}))


def random_uuid() -> str:
    """随机 UUID"""
    return json.loads(_get("/api/rand", {"type": "uuid"}))["value"]


def sha256(text: str) -> str:
    """SHA-256 哈希"""
    return json.loads(_get("/api/hash", {"algo": "sha256", "text": text}))["result"]


def qrcode(text: str, size: int = 300, out: str = "qr.png") -> None:
    """生成二维码并保存为图片"""
    data = _get("/api/qrcode", {"text": text, "size": size})
    with open(out, "wb") as f:
        f.write(data)
    print(f"二维码已保存: {out}")


if __name__ == "__main__":
    print("IP 信息:", ip_info())
    print("中山天气:", weather("zhongshan"))
    print("随机 UUID:", random_uuid())
    print("SHA-256(hello):", sha256("hello"))
    qrcode("https://example.com")
