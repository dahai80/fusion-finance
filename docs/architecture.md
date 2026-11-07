---
doc_id: fusion-finance/architecture
product: fusion-finance
class: app
entry: service
doc_type: architecture
title: { zh: "fusion-finance 架构", en: "fusion-finance architecture" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - fusion_finance/api/app.py
  - fusion_finance/config.py
---

# 架构 / architecture

## 分层 / layers

```
CLI (fusion_finance/cli.py)              ── 直调领域引擎，无需服务在线
Web UI (fusion_finance/api/web/)         ── Jinja2 页面 + 静态资源，挂载于 /ui
FastAPI app (fusion_finance/api/app.py)  ── 路由 / 中间件（认证、限速、审计）/ SSE / WebSocket
领域引擎                                  ── modeling / statements / risk / report / copilot / chart / project / data / audit
fusion-core (MLXClient, config, proc)    ── HTTP 客户端、键链解析、进程标题
fusion-mlx / fusion-gateway              ── 本地 LLM 推理（默认 http://localhost:11432/v1）
```

## 关键决策 / key decisions

- **服务与 CLI 双入口**：CLI 直接调用领域引擎，离线纯数学能力不依赖网络；REST 服务为集成方与 Web UI 提供同一套引擎。
  Dual entry: the CLI drives the domain engines directly (offline, no network), while the REST service exposes the same engines to integrators and the Web UI.
- **AI 与纯数学端点分离**：同一能力（如 DCF）同时提供 AI 辅助与纯计算两个端点，LLM 不可用时纯数学路径不受影响。
  AI vs pure-math split: each capability (e.g. DCF) ships both an AI-assisted and a pure-calculation endpoint, so an unavailable LLM does not take down the deterministic path.
- **认证收敛到 fusion-core 键链**：MLX 客户端 key 解析委托 `fusion_core.config`，本仓库只保留自身服务 key（`FUSION_FINANCE_API_KEY` / 自动生成文件）。
  Auth consolidation: MLX client key resolution delegates to `fusion_core.config`; this repo only owns its own service key (`FUSION_FINANCE_API_KEY` / the auto-generated file).
- **默认回环绑定**：`127.0.0.1:11466` 起步，非回环绑定必须显式配置并触发安全告警检查。
  Loopback-by-default: binds `127.0.0.1:11466`; any non-loopback bind is explicit and runs the safety-check warnings.
- **端口注册自检**：start.sh 启动前核对 port-registry，防止端口漂移。
  Port registry self-check: start.sh verifies the registry before starting to prevent port drift.
- **零构建 Web UI**：服务端 Jinja2 渲染 + 原生 JS，无前端构建步骤、无新依赖。
  Zero-build Web UI: server-rendered Jinja2 plus vanilla JS, no frontend build step, no new dependencies.

## 数据流 / data flow

```
client ──X-API-Key──▶ middleware(auth, rate-limit, audit) ──▶ router (/api/v1/*)
    router ──▶ domain engine ──▶ SQLite/文件存储 (~/.fusion/finance/)
                    └──(AI 端点)──▶ MLXClient ──▶ fusion-gateway/ fusion-mlx
Web UI (/ui) ──同源 fetch + /ws/copilot──▶ 同一 FastAPI app
```

## 中间件链 / middleware chain

1. 请求日志与脱敏（敏感查询参数 redact，见 `fusion_finance/api/middleware.py`）。
   Request logging with sensitive-query redaction.
2. API key 校验（`x-api-key` 头或 `Authorization: Bearer`；`/ws/*` 接受 `api_key` 查询参数）。
   API key check (`x-api-key` header or `Authorization: Bearer`; `/ws/*` also accepts the `api_key` query parameter).
3. 限速（默认 100 请求/60 秒，`/ui` 豁免）。
   Rate limiting (100 req/60s default, `/ui` exempt).
4. 审计记录落 `~/.fusion/finance/audit/`（哈希链可校验）。
   Audit records to `~/.fusion/finance/audit/` (hash-chain verifiable).

## 边界与限制 / boundaries and limits

- 不含实时行情源：市场数据为模拟源。
  No live market feed: market data is simulated.
- 不含多租户：单用户本地服务，认证为单 key 模型。
  No multi-tenancy: single-user local service with a single-key auth model.
- 报告导出格式以 `/api/v1/report/formats` 返回为准。
  Export formats are whatever `/api/v1/report/formats` returns.
