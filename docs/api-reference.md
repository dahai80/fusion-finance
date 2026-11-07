---
doc_id: fusion-finance/api-reference
product: fusion-finance
class: app
entry: service
doc_type: api-reference
title: { zh: "fusion-finance REST API 参考", en: "fusion-finance REST API reference" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - fusion_finance/api/app.py
  - fusion_finance/api/routes
  - fusion_finance/api/middleware.py
---

# REST API 参考 / REST API reference

Base URL: `http://localhost:11466`。OpenAPI 文档：`/docs`。
OpenAPI docs are served at `/docs`.

## 认证与限速 / auth and rate limiting

- 除 `/api/v1/health`、`/api/v1/ready` 与 `/ui`、`/ui/*` 外，所有端点要求 `X-API-Key` 头（也接受 `Authorization: Bearer <key>`）。
  All endpoints except `/api/v1/health`, `/api/v1/ready` and `/ui`, `/ui/*` require the `X-API-Key` header (`Authorization: Bearer <key>` is also accepted).
- `/ws/*` 无法自定义浏览器头，额外接受 `api_key` 查询参数（审计日志中脱敏）。
  `/ws/*` additionally accepts an `api_key` query parameter because browsers cannot set custom headers on WebSocket (redacted in audit logs).
- 错误响应统一为 `{ "detail": "..." }`。
  Error responses are uniformly `{ "detail": "..." }`.
- 限速：默认 100 请求 / 60 秒，超限返回 429。
  Rate limit: 100 requests / 60 seconds by default; over-limit returns 429.

## 端点总览 / endpoint map

| 前缀 / prefix | 能力 / capability |
|---|---|
| `/api/v1` | 健康检查 `/`、就绪检查 `/ready` |
| `/api/v1/modeling` | DCF（AI/纯计算/批量/会话式）、comps、敏感性、蒙特卡洛、LBO、DDM、并购、APV、EVA、RI、组合优化、Black-Litterman、有效前沿、收益率曲线（Nelson-Siegel） |
| `/api/v1/statements` | AI 财报分析、纯指标计算、勾稽校验、筛选器、标准化、趋势分析、会计准则列表 |
| `/api/v1/risk` | AI KYC/信用/合规审查、VaR、蒙特卡洛 VaR、压力测试、制裁筛查（单个/批量）、实体关系图谱、UBO 解析 |
| `/api/v1/report` | 估值报告、PitchBook、AI 深度投研报告、导出（`/export/{fmt}`）、格式列表 |
| `/api/v1/copilot` | 对话 `/chat`、历史 `/history/{session_id}`、会话列表 `/sessions` |
| `/api/v1/chart` | K线、热力图、瀑布图、敏感性龙卷风图（SVG） |
| `/api/v1/project` | 项目 CRUD |
| `/api/v1/data` | CSV 导入、资产负债表平衡/完整性校验、缓存管理、模拟行情/OHLCV/技术指标 |
| `/api/v1/audit` | 审计记录、查询、统计、哈希链校验 `/verify-chain` |
| `/api/v1/dashboard` | 公司全景 `/company`、市场概览 `/market`、服务状态 `/status` |
| `/events` | SSE 事件流 |
| `/ws` | WebSocket（含 `/ws/copilot` 流式对话） |
| `/ui` | 内置 Web UI（Dashboard / Modeling / Risk / Copilot） |

## 典型请求 / typical requests

```bash
KEY=$(cat ~/.fusion/finance/api_key)

# 纯数学：DCF 计算（无 AI）
curl -s -X POST http://localhost:11466/api/v1/modeling/dcf/calculate \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140,160]}'

# AI 辅助 DCF
curl -s -X POST http://localhost:11466/api/v1/modeling/dcf \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140,160]}'

# 蒙特卡洛 VaR
curl -s -X POST http://localhost:11466/api/v1/risk/var/monte-carlo \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"portfolio_value":1000000,"expected_return":0.10,"volatility":0.20}'

# 批量制裁筛查
curl -s -X POST http://localhost:11466/api/v1/risk/sanctions/batch \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"names":["Acme Corp"]}'

# 导出估值报告
curl -s -X POST http://localhost:11466/api/v1/report/valuation \
  -H "X-API-Key: $KEY" -H "Content-Type: application/json" \
  -d '{"company":"Apple"}'
```

请求体字段以 `/docs` 的 Pydantic schema 为准；本页不逐一复制字段。
Request body fields follow the Pydantic schemas at `/docs`; this page does not duplicate them field by field.

## AI 与纯数学端点的区别 / AI vs pure-math endpoints

- AI 端点（summary 含 "AI"）依赖 fusion-mlx；模型未加载时返回错误而非降级结果。
  AI endpoints (summary prefixed "AI") depend on fusion-mlx; they return an error when the model is not loaded rather than a degraded result.
- 纯数学端点（summary 含 "纯数学"/"纯计算"/"纯逻辑"）不访问模型，可在无 MLX 时使用。
  Pure-math endpoints (summaries marked pure-calculation/pure-logic) never touch the model and work without MLX.

## 约束 / constraints

- 最大模拟次数 100000（`FUSION_FINANCE_MAX_SIMULATIONS`）；列表入参最长 10000 项（`FUSION_FINANCE_MAX_LIST_LENGTH`）。
  Max simulations 100000 (`FUSION_FINANCE_MAX_SIMULATIONS`); list inputs capped at 10000 items (`FUSION_FINANCE_MAX_LIST_LENGTH`).
- 请求体最大 50MB（`FUSION_FINANCE_MAX_UPLOAD_BYTES`）。
  Request body cap 50MB (`FUSION_FINANCE_MAX_UPLOAD_BYTES`).

Python 库层与 CLI 参考（`FinancialModelingEngine`、`ReportGenerator` 等）见 docs/api.md。
For the Python library layer and CLI (`FinancialModelingEngine`, `ReportGenerator`, etc.) see docs/api.md.
