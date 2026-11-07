---
doc_id: fusion-finance/get-started
product: fusion-finance
class: app
entry: service
doc_type: get-started
title: { zh: "fusion-finance 快速上手", en: "fusion-finance quick start" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - README.md
  - start.sh
  - fusion_finance/config.py
---

# 快速上手 / quick start

前置条件 / prerequisites: macOS Apple Silicon, Python 3.12, fusion 仓库共享 venv (`source ~/fusion/.venv/bin/activate`)。

## 1. 安装 / install

```bash
cd ~/fusion/fusion-finance
source ~/fusion/.venv/bin/activate
pip install -e "."
```

## 2. 启动服务 / start the service

```bash
./start.sh start          # binds 127.0.0.1:11466
./start.sh status         # PID / port / log tail
```

服务启动后自动生成或读取 API key（`~/.fusion/finance/api_key`，权限 0600）。
On first start the service generates or reads its API key (`~/.fusion/finance/api_key`, mode 0600).

验证 / verify:

```bash
curl http://localhost:11466/api/v1/ready
```

## 3. 第一批调用 / first calls

免 key 的健康检查之外，业务端点需要 `X-API-Key` 头：
Beyond key-exempt health checks, business endpoints need the `X-API-Key` header:

```bash
KEY=$(cat ~/.fusion/finance/api_key)

# 纯 DCF 计算（无 AI，不依赖模型加载）
curl -s -X POST http://localhost:11466/api/v1/modeling/dcf/calculate \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140,160]}'

# VaR 计算
curl -s -X POST http://localhost:11466/api/v1/risk/var \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"returns":[0.01,-0.02,0.03],"portfolio_value":1000000}'
```

AI 端点（如 `/api/v1/copilot/chat`）需要 fusion-mlx 已在本地运行（默认对接 `http://localhost:11432/v1`）。
AI endpoints (e.g. `/api/v1/copilot/chat`) require fusion-mlx running locally (default base URL `http://localhost:11432/v1`).

## 4. CLI（无服务也可用）/ CLI (works without the service)

```bash
fusion-finance model dcf "Apple" 100 120 140 160
fusion-finance statement analyze "Apple" --revenue 1000
fusion-finance risk kyc "Company"
fusion-finance report valuation "Apple" -o ./reports
```

CLI 直接调用本地 Python 引擎；纯数学能力不需要启动任何服务。
The CLI drives the local Python engine; pure-math capabilities need no running service.

## 5. Web UI（可选）/ Web UI (optional)

浏览器打开 `http://localhost:11466/ui`：Dashboard（服务/MLX 状态、项目、筛选器）、Modeling（DCF/蒙特卡洛/敏感性）、Risk & Compliance（VaR/制裁筛查/压力测试）、Copilot（流式对话）。`/ui` 免 API key（由页面模板注入本地 key）。
Open `http://localhost:11466/ui` in a browser: Dashboard (service/MLX status, projects, screener), Modeling (DCF / Monte Carlo / sensitivity), Risk & Compliance (VaR / sanctions / stress tests), Copilot (streaming chat). `/ui` is exempt from the API-key middleware (the page template injects the local key).

## 6. 停止 / stop

```bash
./start.sh stop
```

## 约束 / limits

- 请求限速默认 100 次/60 秒（按客户端 key/地址聚合）。
  Rate limiting defaults to 100 requests per 60 seconds (aggregated per client key/address).
- 上传上限 50MB（`FUSION_FINANCE_MAX_UPLOAD_BYTES`）。
  Upload cap is 50MB (`FUSION_FINANCE_MAX_UPLOAD_BYTES`).
- `start.sh` 会核对 port-registry：端口未注册时拒绝启动（可用 `FUSION_SKIP_REGISTRY_CHECK=1` 跳过）。
  `start.sh` checks the port registry and refuses to start on an unregistered port (bypass with `FUSION_SKIP_REGISTRY_CHECK=1`).

更多内容见 / see also: docs/api-reference.md, docs/config-reference.md, docs/troubleshooting.md
