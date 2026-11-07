---
doc_id: fusion-finance/config-reference
product: fusion-finance
class: app
entry: service
doc_type: config-reference
title: { zh: "fusion-finance 配置参考", en: "fusion-finance config reference" }
audience: engineer
status: draft
version: 0.5.10
updated: 2026-11-07
owner: @dahai
source_of_truth:
  - fusion_finance/config.py
  - start.sh
---

# 配置参考 / config reference

配置全部通过环境变量与自动生成的本地文件，无配置服务器。
All configuration is via environment variables and auto-generated local files; there is no config server.

## 环境变量 / environment variables

| 变量 / variable | 默认值 / default | 说明 / description |
|---|---|---|
| `FUSION_FINANCE_HOST` | `127.0.0.1` | 服务绑定地址；改为非回环地址需自行承担安全评估 |
| `FUSION_FINANCE_PORT` | `11466` | 服务端口（start.sh 读取；端口需在 port-registry.yaml 注册） |
| `FUSION_FINANCE_LOG_LEVEL` | `INFO` | 日志级别 |
| `FUSION_FINANCE_API_KEY` | 自动生成 | 显式 API key；不设置则读取/生成 `~/.fusion/finance/api_key` |
| `FUSION_FINANCE_DISABLE_AUTH` | 未设置 | `1`/`true`/`yes` 时关闭 API key 校验（仅建议本机调试） |
| `FUSION_FINANCE_MAX_UPLOAD_BYTES` | `52428800`（50MB） | 请求体/上传上限 |
| `FUSION_FINANCE_MAX_LIST_LENGTH` | `10000` | 列表入参长度上限 |
| `FUSION_FINANCE_MAX_SIMULATIONS` | `100000` | 蒙特卡洛模拟次数上限 |
| `FUSION_REGISTRY` | `~/fusion/architecture/port-registry.yaml` | start.sh 端口注册表路径 |
| `FUSION_SKIP_REGISTRY_CHECK` | 未设置 | `1` 时跳过端口注册校验（独立部署用） |

## 上游依赖 / upstream dependencies

| 变量 / variable | 说明 / description |
|---|---|
| MLX base URL | 默认 `http://localhost:11432/v1`（fusion-gateway）；由 fusion-core 的 MLXClient 键链解析 |
| MLX API key | 经 fusion-core `fusion_core.config` 解析（`client_key()` / gateway 场景 `gateway_admin_key()`）；本仓库不再持有 legacy 别名链 |
| 默认模型 | `qwen3.5-9b` |

## 本地数据文件 / local data files

| 路径 / path | 用途 / purpose |
|---|---|
| `~/.fusion/finance/api_key` | 自动生成的 API key（0600；首次启动生成） |
| `~/.fusion/finance/audit/` | 审计日志与哈希链 |
| `~/.fusion/finance/projects/` | 项目数据 |
| `~/.fusion/finance/cache/` | 缓存（可通过 `/api/v1/data/cache` 管理） |
| `~/.fusion/finance/exports/` | 导出的报告 |
| `<repo>/.fusion-finance.pid` | start.sh PID 文件 |
| `<repo>/.fusion-finance.log` | start.sh 日志（10MB 轮转，保留 3 份） |

## 安全行为 / security behavior

- API key 缺失时用 `secrets.token_urlsafe(32)` 生成并写入 `~/.fusion/finance/api_key`，比较使用 `hmac.compare_digest`。
  When no key exists, one is generated with `secrets.token_urlsafe(32)` and written to `~/.fusion/finance/api_key`; comparison uses `hmac.compare_digest`.
- `auth_safety_check` 会在"关闭认证 + 非回环绑定"组合下发出警告。
  `auth_safety_check` warns on the combination of auth disabled plus a non-loopback bind.
- `/ui`、`/ui/*` 免 API key 与限速中间件；页面模板注入本地 key 供第一方 JS 调用。
  `/ui` and `/ui/*` are exempt from the API-key and rate-limit middleware; the page template injects the local key for first-party JS calls.

## 约束 / constraints

- 不提供配置文件热加载：改动环境变量后需重启服务。
  No hot reload: restart the service after changing environment variables.
- 端口必须与 `architecture/port-registry.yaml` 一致，否则 `start.sh` 拒绝启动。
  The port must match `architecture/port-registry.yaml`, otherwise `start.sh` refuses to start.
