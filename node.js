// DevToolBox API 调用示例（Node.js，使用原生 fetch，Node 18+）
const BASE = "http://120.78.120.129/toolbox";

async function get(path, params = {}) {
  const url = new URL(BASE + path);
  Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, v));
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

// 示例：查 IP
async function ipDemo() {
  const data = await get("/api/ip", { detail: "true" });
  console.log("IP:", data.ip, data.city ? `归属: ${data.country} ${data.region} ${data.city}` : "");
}

// 示例：随机 UUID
async function uuidDemo() {
  const data = await get("/api/rand", { type: "uuid" });
  console.log("UUID:", data.value);
}

// 示例：天气
async function weatherDemo() {
  const data = await get("/api/weather", { city: "beijing" });
  console.log(`天气: ${data.city} ${data.weather} ${data.temp_c}°C`);
}

// 示例：二维码（返回图片 Buffer）
async function qrDemo() {
  const url = `${BASE}/api/qrcode?text=https://example.com&size=300`;
  const r = await fetch(url);
  const buf = Buffer.from(await r.arrayBuffer());
  require("fs").writeFileSync("qr.png", buf);
  console.log("二维码已保存: qr.png");
}

(async () => {
  await ipDemo();
  await uuidDemo();
  await weatherDemo();
  await qrDemo();
})().catch(console.error);
