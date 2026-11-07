---
doc_id: fusion-finance/product-page
product: fusion-finance
class: app
entry: service
doc_type: product-page
title: { zh: "fusion-finance 产品页", en: "fusion-finance product page" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - README.md
  - fusion_finance/api/app.py
  - fusion_finance/config.py
---

# fusion-finance 产品页 / product page

## 一句话定位 / positioning

本地 AI 金融分析平台（macOS Apple Silicon），基于 fusion-mlx 离线推理，覆盖财务建模、财报分析、风险合规与报告生成。数据不出本机。
Local AI-powered financial analysis platform on Apple Silicon, built on fusion-mlx offline inference: financial modeling, statement analysis, risk & compliance, and report generation. Data stays on the machine.

## 它替用户免掉了什么 / what users no longer have to do

- 不再把财报/交易数据上传到云端 SaaS：建模、VaR、制裁筛查全部本地执行。
  No more uploading statements or trade data to cloud SaaS: modeling, VaR and sanctions screening all run locally.
- 不再手写 DCF/LBO/DDM/并购模型的表格公式：API 与 CLI 直接输出企业价值、目标价、敏感性矩阵与蒙特卡洛分布。
  No more hand-building DCF/LBO/DDM/merger spreadsheet formulas: the API and CLI return enterprise value, target price, sensitivity matrices and Monte Carlo distributions directly.
- 不再单独搭建 Copilot 聊天服务：`/api/v1/copilot/chat` 与 `/ws/copilot` 已内置于同一服务。
  No separate copilot chat service to stand up: `/api/v1/copilot/chat` and `/ws/copilot` ship inside the same service.
- 不再为审计合规单独记录操作日志：AuditTrail 自动记录操作并支持哈希链校验（`/api/v1/audit/verify-chain`）。
  No separate audit logging to bolt on: AuditTrail records operations automatically and supports hash-chain verification (`/api/v1/audit/verify-chain`).

## 约束与边界 / constraints and limits

- 依赖 fusion-mlx（或 fusion-gateway）在本地运行；LLM 不可用时纯数学端点（如 `/api/v1/modeling/dcf/calculate`）仍可用，AI 端点不可用。
  Requires local fusion-mlx (or fusion-gateway). When the LLM is unavailable, pure-math endpoints (e.g. `/api/v1/modeling/dcf/calculate`) still work while AI endpoints do not.
- 默认仅绑定 `127.0.0.1:11466`；对外暴露需显式设置 `FUSION_FINANCE_HOST` 并自行承担安全评估。
  Binds to `127.0.0.1:11466` by default; exposing it requires an explicit `FUSION_FINANCE_HOST` and your own security review.
- 行情数据为模拟数据源（mock），非实盘行情。
  Market quotes come from a simulated source (mock), not live exchange data.
- 上传体积、列表长度、模拟次数受 `FUSION_FINANCE_MAX_*` 环境变量上限约束。
  Upload size, list length and simulation count are capped by the `FUSION_FINANCE_MAX_*` environment variables.

## 入口 / entry points

| 入口 / entry | 说明 / description |
|---|---|
| REST API | `http://localhost:11466/api/v1/...`（见 docs/api-reference.md） |
| Web UI | `http://localhost:11466/ui`（Dashboard / Modeling / Risk / Copilot 四页） |
| CLI | `fusion-finance model dcf`、`statement analyze`、`risk kyc`、`report valuation`、`serve` |
| WebSocket / SSE | `/ws/copilot`（流式对话）、`/events`（事件流） |

## 用户与场景 / audience and scenarios

- 工程师：本地部署并集成到自有工作流（脚本、fusion-studio、CI）。
  Engineers: deploy locally and integrate into their own workflows (scripts, fusion-studio, CI).
- 金融分析使用者：通过 Web UI 或 API 完成估值、风控、合规筛查与报告导出。
  Finance users: run valuation, risk control, compliance screening and report export via the Web UI or API.
