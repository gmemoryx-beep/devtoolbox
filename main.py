import datetime
import hashlib
import random
import sqlite3
import string
import time
import urllib.parse
import uuid as uuid_mod
from pathlib import Path

import qrcode
import requests
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, JSONResponse, Response

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH = DATA_DIR / "stats.db"

app = FastAPI(title="DevToolBox API", version="1.0.0", docs_url="/docs", openapi_url="/openapi.json")

# ---------- 访问统计（轻量 SQLite） ----------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS hits (api TEXT, count INTEGER DEFAULT 0, PRIMARY KEY(api))")
    conn.commit()
    conn.close()

init_db()

def count_hit(api: str):
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.execute("INSERT INTO hits(api, count) VALUES(?,1) ON CONFLICT(api) DO UPDATE SET count=count+1", (api,))
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_hits():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT api, count FROM hits ORDER BY count DESC").fetchall()
    conn.close()
    return {k: v for k, v in rows}

# ---------- 工具函数 ----------
def _bad_request(msg: str):
    return JSONResponse({"error": msg}, status_code=400)

def _check_text(text: str, max_len: int = 2000, allow_empty: bool = False):
    if text is None:
        return False
    text = str(text).strip()
    if not allow_empty and not text:
        return False
    if len(text) > max_len:
        return False
    return True

# ---------- 首页 ----------
@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML

# ---------- API: IP 查询 ----------
@app.get("/api/ip")
async def api_ip(request: Request, detail: bool = Query(False, description="是否返回详细归属地信息")):
    count_hit("ip")
    client_ip = request.client.host if request.client else "unknown"
    # 若经反向代理，取 X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        client_ip = xff.split(",")[0].strip()
    if detail:
        try:
            r = requests.get(f"http://ip-api.com/json/{client_ip}?lang=zh-CN", timeout=5)
            data = r.json()
            return {"ip": client_ip, "country": data.get("country"), "region": data.get("regionName"),
                    "city": data.get("city"), "isp": data.get("isp"), "as": data.get("as")}
        except Exception:
            return {"ip": client_ip, "detail": "unavailable"}
    return {"ip": client_ip}

# ---------- API: 二维码 ----------
@app.get("/api/qrcode")
async def api_qrcode(text: str = Query(..., max_length=2000, description="二维码内容"),
                     size: int = Query(300, ge=100, le=1024, description="图片边长像素")):
    count_hit("qrcode")
    if not _check_text(text, allow_empty=False):
        raise HTTPException(status_code=400, detail="text 不能为空")
    try:
        qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M, border=2)
        qr.add_data(text)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        img = img.resize((size, size))
        import io
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return Response(content=buf.getvalue(), media_type="image/png",
                        headers={"Cache-Control": "public, max-age=3600"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"生成失败: {e}")

# ---------- API: 时间戳转换 ----------
@app.get("/api/time")
async def api_time(ts: int | None = Query(None, description="Unix 秒级时间戳，缺省为当前时间"),
                   tz: int = Query(8, ge=-12, le=14, description="时区偏移（小时）")):
    count_hit("time")
    now = ts if ts is not None else int(time.time())
    dt = datetime.datetime.utcfromtimestamp(now) + datetime.timedelta(hours=tz)
    result = {
        "timestamp": now,
        "iso": dt.isoformat(),
        "datetime": dt.strftime("%Y-%m-%d %H:%M:%S"),
        "weekday": "一二三四五六日"[dt.weekday()],
        "tz_offset": tz,
    }
    return result

# ---------- API: 天气 ----------
@app.get("/api/weather")
async def api_weather(city: str = Query(..., max_length=100, description="城市名，如 中山/guangzhou")):
    count_hit("weather")
    if not _check_text(city, max_len=100):
        raise HTTPException(status_code=400, detail="city 不能为空")
    try:
        r = requests.get(f"https://wttr.in/{urllib.parse.quote(city)}?format=j1", timeout=8)
        if r.status_code != 200:
            return {"error": f"查询失败(HTTP {r.status_code})", "hint": "可尝试英文城市名，如 beijing"}
        data = r.json()
        cur = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        result = {
            "city": area.get("areaName", [{}])[0].get("value", city),
            "region": area.get("region", [{}])[0].get("value", ""),
            "country": area.get("country", [{}])[0].get("value", ""),
            "temp_c": cur.get("temp_C"),
            "feels_like_c": cur.get("FeelsLikeC"),
            "humidity": cur.get("humidity"),
            "wind_kmh": cur.get("windspeedKmph"),
            "weather": cur.get("weatherDesc", [{}])[0].get("value", ""),
            "updated": cur.get("observation_time"),
        }
        return result
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"天气服务暂时不可用: {e}")

# ---------- API: 随机数/字符串/UUID ----------
@app.get("/api/rand")
async def api_rand(type: str = Query("int", description="int|str|uuid|color"),
                   min: int = Query(1, description="最小值"),
                   max: int = Query(100, description="最大值"),
                   length: int = Query(16, ge=1, le=128, description="字符串长度")):
    count_hit("rand")
    t = type.lower()
    if t == "int":
        if min > max:
            raise HTTPException(status_code=400, detail="min 不能大于 max")
        return {"type": "int", "value": random.randint(min, max)}
    if t == "str":
        return {"type": "str", "length": length,
                "value": "".join(random.choices(string.ascii_letters + string.digits, k=length))}
    if t == "uuid":
        return {"type": "uuid", "value": str(uuid_mod.uuid4())}
    if t == "color":
        return {"type": "color", "value": "#" + "".join(random.choices("0123456789abcdef", k=6))}
    raise HTTPException(status_code=400, detail="type 仅支持 int|str|uuid|color")

# ---------- API: Base64 ----------
@app.get("/api/base64")
async def api_base64(mode: str = Query("encode", description="encode|decode"), text: str = Query("")):
    count_hit("base64")
    if not _check_text(text, max_len=5000, allow_empty=True):
        raise HTTPException(status_code=400, detail="text 过长或为空")
    import base64
    try:
        if mode == "encode":
            return {"mode": "encode", "result": base64.b64encode(text.encode()).decode()}
        if mode == "decode":
            return {"mode": "decode", "result": base64.b64decode(text.encode()).decode(errors="replace")}
        raise HTTPException(status_code=400, detail="mode 仅支持 encode|decode")
    except Exception:
        raise HTTPException(status_code=400, detail="Base64 处理失败，请检查输入")

# ---------- API: URL 编解码 ----------
@app.get("/api/urlcode")
async def api_urlcode(mode: str = Query("encode", description="encode|decode"), text: str = Query("")):
    count_hit("urlcode")
    if not _check_text(text, max_len=5000, allow_empty=True):
        raise HTTPException(status_code=400, detail="text 过长或为空")
    if mode == "encode":
        return {"mode": "encode", "result": urllib.parse.quote(text)}
    if mode == "decode":
        return {"mode": "decode", "result": urllib.parse.unquote(text)}
    raise HTTPException(status_code=400, detail="mode 仅支持 encode|decode")

# ---------- API: 哈希 ----------
@app.get("/api/hash")
async def api_hash(algo: str = Query("md5", description="md5|sha1|sha256|sha512"), text: str = Query("")):
    count_hit("hash")
    if not _check_text(text, max_len=5000, allow_empty=True):
        raise HTTPException(status_code=400, detail="text 过长或为空")
    algos = {"md5": hashlib.md5, "sha1": hashlib.sha1, "sha256": hashlib.sha256, "sha512": hashlib.sha512}
    if algo.lower() not in algos:
        raise HTTPException(status_code=400, detail="algo 仅支持 md5|sha1|sha256|sha512")
    return {"algo": algo.lower(), "text_length": len(text), "result": algos[algo.lower()](text.encode()).hexdigest()}

# ---------- API: 服务状态与统计 ----------
@app.get("/api/status")
async def api_status():
    count_hit("status")
    return {
        "service": "DevToolBox API",
        "version": "1.0.0",
        "uptime_ok": True,
        "server_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_hits": sum(get_hits().values()),
        "api_stats": get_hits(),
        "endpoints": ["/api/ip", "/api/qrcode", "/api/time", "/api/weather", "/api/rand",
                      "/api/base64", "/api/urlcode", "/api/hash", "/api/status"],
    }

# ---------- 首页（单页工具站） ----------
INDEX_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>DevToolBox · 开发者工具箱</title>
<style>
:root{
  --bg:#f4f5f7; --card:#ffffff; --text:#2b2f36; --muted:#7a828e;
  --accent:#3d6b5f; --accent2:#8a9b8f; --border:#e4e8ec; --shadow:0 2px 12px rgba(0,0,0,.06);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;background:var(--bg);color:var(--text);min-height:100vh}
.header{background:linear-gradient(135deg,#3d6b5f 0%,#5d7f74 100%);color:#fff;padding:36px 20px 28px;text-align:center}
.header h1{font-size:26px;font-weight:700;letter-spacing:1px}
.header p{margin-top:8px;font-size:13px;opacity:.85}
.wrap{max-width:960px;margin:0 auto;padding:24px 16px 48px}
.tools{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}
.tool{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:18px;box-shadow:var(--shadow)}
.tool h3{font-size:15px;margin-bottom:12px;display:flex;align-items:center;gap:8px}
.tool h3 .dot{width:8px;height:8px;border-radius:50%;background:var(--accent)}
.tool label{display:block;font-size:12px;color:var(--muted);margin:8px 0 4px}
.tool input,.tool select{width:100%;padding:8px 10px;border:1px solid var(--border);border-radius:8px;font-size:13px;outline:none;background:#fafbfc}
.tool input:focus,.tool select:focus{border-color:var(--accent)}
.tool button{width:100%;margin-top:12px;padding:9px;border:none;border-radius:8px;background:var(--accent);color:#fff;font-size:14px;cursor:pointer;transition:.2s}
.tool button:hover{background:var(--accent2)}
.result{margin-top:12px;padding:10px;border-radius:8px;background:#f7f9f8;font-size:13px;word-break:break-all;min-height:20px;line-height:1.5}
.result img{max-width:100%;display:block;margin:0 auto}
.footer{text-align:center;color:var(--muted);font-size:12px;padding:20px}
.api-note{background:#eef4f1;border:1px solid #d5e4dd;border-radius:10px;padding:14px 16px;margin:20px 0;font-size:13px;color:#35574c;line-height:1.8}
.api-note code{background:#fff;padding:2px 6px;border-radius:4px;font-size:12px}
</style>
</head>
<body>
<div class="header">
  <h1>DevToolBox · 开发者工具箱</h1>
  <p>免费在线开发工具 · 全部为公开 API，可直接调用</p>
</div>
<div class="wrap">
  <div class="api-note">
    <b>开发者调用示例：</b><br>
    <code>/api/qrcode?text=hello</code> 生成二维码 ·
    <code>/api/ip?detail=true</code> 查 IP 归属地 ·
    <code>/api/rand?type=uuid</code> 随机 UUID ·
    <code>/api/weather?city=zhongshan</code> 天气 ·
    <code>/api/time</code> 当前时间戳 · 完整文档见 <code>/docs</code>
  </div>
  <div class="api-note" id="stats_bar">访问统计加载中…</div>
  <div class="tools">

    <div class="tool">
      <h3><span class="dot"></span>时间戳转换</h3>
      <label>输入 Unix 时间戳（秒）</label>
      <input id="ts_input" placeholder="例如 1730000000，留空为当前时间">
      <button onclick="tsConvert()">转换</button>
      <div class="result" id="ts_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>Base64 编解码</h3>
      <label>文本</label>
      <input id="b64_input" placeholder="输入内容">
      <select id="b64_mode"><option value="encode">编码</option><option value="decode">解码</option></select>
      <button onclick="b64Convert()">执行</button>
      <div class="result" id="b64_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>URL 编解码</h3>
      <label>文本</label>
      <input id="url_input" placeholder="输入内容">
      <select id="url_mode"><option value="encode">编码</option><option value="decode">解码</option></select>
      <button onclick="urlConvert()">执行</button>
      <div class="result" id="url_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>哈希计算</h3>
      <label>文本</label>
      <input id="hash_input" placeholder="输入内容">
      <select id="hash_algo"><option value="md5">MD5</option><option value="sha1">SHA-1</option><option value="sha256">SHA-256</option><option value="sha512">SHA-512</option></select>
      <button onclick="hashConvert()">计算</button>
      <div class="result" id="hash_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>二维码生成</h3>
      <label>内容</label>
      <input id="qr_input" placeholder="网址或文本" value="https://example.com">
      <button onclick="qrGenerate()">生成</button>
      <div class="result" id="qr_result">二维码将显示在这里</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>随机数 / UUID</h3>
      <label>范围（整数）</label>
      <div style="display:flex;gap:8px">
        <input id="rand_min" placeholder="min" value="1" style="flex:1">
        <input id="rand_max" placeholder="max" value="100" style="flex:1">
      </div>
      <button onclick="randInt()">随机整数</button>
      <button style="background:#5d7f74" onclick="randUuid()">随机 UUID</button>
      <div class="result" id="rand_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>IP 查询</h3>
      <button onclick="ipQuery()">查询我的 IP</button>
      <div class="result" id="ip_result">结果</div>
    </div>

    <div class="tool">
      <h3><span class="dot"></span>天气查询</h3>
      <label>城市（中文或拼音）</label>
      <input id="w_input" placeholder="例如 中山 或 zhongshan">
      <button onclick="weatherQuery()">查询</button>
      <div class="result" id="w_result">结果</div>
    </div>

  </div>
  <div class="tool" style="grid-column:1/-1;text-align:center">
    <h3 style="justify-content:center"><span class="dot"></span>支持项目</h3>
    <p style="font-size:13px;color:#7a828e;line-height:1.8">DevToolBox 免费开放，持续为开发者提供开箱即用的工具 API。<br>如果它帮到了你，欢迎赞助支持服务器的维护与持续升级。</p>
    <button style="max-width:260px;margin:12px auto 0;display:block" onclick="show('sponsor_note','赞助通道即将上线，敬请期待')">赞助支持</button>
    <div class="result" id="sponsor_note" style="text-align:center"></div>
  </div>
  <div class="footer">DevToolBox · 部署于私有服务器 · 数据仅用于匿名统计</div>
</div>
<script>
async function api(path){const r=await fetch(path);return r.json()}
async function apiText(path){const r=await fetch(path);return r.text()}
function show(id,txt){document.getElementById(id).textContent=txt}

async function tsConvert(){
  const v=document.getElementById('ts_input').value.trim();
  const r=await api('api/time'+(v?'?ts='+v:''));
  if(r.error) return show('ts_result','错误: '+r.error);
  show('ts_result','时间: '+r.datetime+'\n星期'+r.weekday+'\nISO: '+r.iso);
}
async function b64Convert(){
  const v=document.getElementById('b64_input').value;
  const m=document.getElementById('b64_mode').value;
  const r=await api('api/base64?mode='+m+'&text='+encodeURIComponent(v));
  if(r.error) return show('b64_result','错误: '+r.error);
  show('b64_result',r.result);
}
async function urlConvert(){
  const v=document.getElementById('url_input').value;
  const m=document.getElementById('url_mode').value;
  const r=await api('api/urlcode?mode='+m+'&text='+encodeURIComponent(v));
  if(r.error) return show('url_result','错误: '+r.error);
  show('url_result',r.result);
}
async function hashConvert(){
  const v=document.getElementById('hash_input').value;
  const a=document.getElementById('hash_algo').value;
  const r=await api('api/hash?algo='+a+'&text='+encodeURIComponent(v));
  if(r.error) return show('hash_result','错误: '+r.error);
  show('hash_result',r.algo.toUpperCase()+': '+r.result);
}
async function qrGenerate(){
  const v=document.getElementById('qr_input').value.trim()||'https://example.com';
  const url='api/qrcode?text='+encodeURIComponent(v)+'&size=300';
  const el=document.getElementById('qr_result');
  const img=new Image();
  img.onload=()=>{el.innerHTML='';el.appendChild(img)};
  img.onerror=()=>{el.textContent='生成失败'};
  img.src=url;
}
async function randInt(){
  const a=parseInt(document.getElementById('rand_min').value)||1;
  const b=parseInt(document.getElementById('rand_max').value)||100;
  const r=await api('api/rand?type=int&min='+a+'&max='+b);
  if(r.error) return show('rand_result','错误: '+r.error);
  show('rand_result','随机整数: '+r.value);
}
async function randUuid(){
  const r=await api('api/rand?type=uuid');
  if(r.error) return show('rand_result','错误: '+r.error);
  show('rand_result','UUID: '+r.value);
}
async function ipQuery(){
  const r=await api('api/ip?detail=true');
  if(r.error) return show('ip_result','错误: '+r.error);
  let s='IP: '+r.ip;
  if(r.city) s+='\n归属: '+[r.country,r.region,r.city].filter(Boolean).join(' ');
  if(r.isp) s+='\n运营商: '+r.isp;
  show('ip_result',s);
}
async function weatherQuery(){
  const v=document.getElementById('w_input').value.trim();
  if(!v) return show('w_result','请输入城市');
  const r=await api('api/weather?city='+encodeURIComponent(v));
  if(r.error) return show('w_result','错误: '+r.error);
  show('w_result',r.city+' '+r.region+'\n天气: '+r.weather+'\n温度: '+r.temp_c+'°C (体感 '+r.feels_like_c+'°C)\n湿度: '+r.humidity+'%  风速: '+r.wind_kmh+' km/h');
}
async function loadStats(){
  try{
    const r=await api('api/status');
    const el=document.getElementById('stats_bar');
    if(r && r.total_hits!==undefined){
      const top=Object.entries(r.api_stats||{}).sort(function(a,b){return b[1]-a[1]}).slice(0,3).map(function(x){return x[0]+'('+x[1]+')'}).join(' · ');
      el.innerHTML='<b>累计调用 '+r.total_hits+' 次</b> · 热门 API: '+top+' · 服务器时间: '+r.server_time;
    }
  }catch(e){}
}
loadStats();
</script>
</body>
</html>
"""
