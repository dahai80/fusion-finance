---
doc_id: fusion-finance/troubleshooting
product: fusion-finance
class: app
entry: service
doc_type: troubleshooting
title: { zh: "fusion-finance 故障排查", en: "fusion-finance troubleshooting" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - start.sh
  - fusion_finance/config.py
  - docs/get-started.md
---

# 故障排查 / troubleshooting

## 症状速查 / symptom index

| 症状 / symptom | 处理 / fix |
|---|---|
| `start.sh start` 报 "port 11466 not registered" | 端口未注册或被改动：核对 `~/fusion/architecture/port-registry.yaml`；独立部署用 `FUSION_SKIP_REGISTRY_CHECK=1` |
| `start.sh start` 报 "already running" | 先 `./start.sh status`；确认 PID 后决定 `restart` 或 `stop` |
| `curl` 返回 401/403 | 请求缺 `X-API-Key` 头；key 在 `~/.fusion/finance/api_key` |
| AI 端点报错而纯数学端点正常 | fusion-mlx 未运行或未加载模型；检查 `http://localhost:11432/v1` 可达性 |
| 429 Too Many Requests | 触发限速（默认 100 请求/60 秒），等待窗口重置或部署侧降低调用频率 |
| 413 / 上传失败 | 超过 50MB 上限；调大 `FUSION_FINANCE_MAX_UPLOAD_BYTES` 或压缩输入 |
| `/ui` 页面打开但接口 401 | 页面模板注入的 key 与当前 `~/.fusion/finance/api_key` 不一致（曾手动换 key）；重启服务重新注入 |
| WebSocket 连不上 | `/ws/*` 也接受 `api_key` 查询参数；浏览器无法自定义 WS 头 |

## 诊断步骤 / diagnosis steps

1. `./start.sh status` — 确认 PID 与端口监听。
   Confirm PID and port listening.
2. `./start.sh log [-f]` 或 `tail -100 .fusion-finance.log` — 看最近异常与 uvicorn 输出。
   Inspect recent exceptions and uvicorn output.
3. `curl http://localhost:11466/api/v1/ready` — 200 表示服务与依赖检查通过。
   200 means the service and its dependency checks pass.
4. `curl http://localhost:11466/api/v1/dashboard/status -H "X-API-Key: $KEY"` — 查看 MLX 连接状态。
   Inspect the MLX connection status.
5. `./start.sh doctor` — 一键健康检查。
   One-shot health check.
6. 测试基线：`pytest tests/`（仓库默认 asyncio_mode=auto）。用例失败先看 `tests/` 内同名模块。
   Test baseline: `pytest tests/` (asyncio_mode=auto by default). For a failing case, start with the matching module in `tests/`.

## 常见误区 / common pitfalls

- 用 `0.0.0.0` 绑定但关闭认证：`auth_safety_check` 会告警，属于高风险组合，不要在生产使用。
  Binding `0.0.0.0` with auth disabled: `auth_safety_check` warns; this is a high-risk combination, do not use in production.
- 手动删除 `~/.fusion/finance/api_key` 后旧客户端仍带旧 key：重启服务前所有请求会 401。
  After deleting `~/.fusion/finance/api_key`, old clients still send the old key: every request 401s until the service is restarted.
- CLI 与服务是两条独立路径：CLI 不需要服务在线；服务端点不接受 CLI 参数。
  The CLI and the service are independent paths: the CLI needs no running service, and the service does not accept CLI flags.

## 日志位置 / log locations

- 服务日志：`<repo>/.fusion-finance.log`（10MB 轮转，保留 3 份 `.log.1` ~ `.log.3`）。
  Service log: `<repo>/.fusion-finance.log` (rotated at 10MB, 3 kept).
- 审计日志：`~/.fusion/finance/audit/`（可用 `/api/v1/audit/verify-chain` 校验完整性）。
  Audit log: `~/.fusion/finance/audit/` (integrity verifiable via `/api/v1/audit/verify-chain`).

## 升级与回滚 / upgrade and rollback

- 升级依赖后先跑 `pytest tests/` 再 `./start.sh restart`；异常时 `git checkout` 回退到上一个 tag 并重启。
  After upgrading dependencies run `pytest tests/` before `./start.sh restart`; on regression, `git checkout` the previous tag and restart.
- 数据目录 `~/.fusion/finance/` 不随代码回滚，审计与项目数据保留。
  The data directory `~/.fusion/finance/` is not touched by code rollback; audit and project data are preserved.
