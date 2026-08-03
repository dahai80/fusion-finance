<div align="center">
  <h1>💰 Fusion-Finance</h1>
  <p><strong>本地 AI 金融分析平台 — macOS Apple Silicon 原生</strong></p>
  <p><em>100% 本地离线，数据不出境，基于 fusion-mlx。国内 Claude Financial 替代方案。</em></p>
  <p><a href="./README.md">English</a></p>
</div>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/macOS-Apple%20Silicon-brightgreen" alt="macOS">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="许可证">
  <img src="https://img.shields.io/badge/AI-MLX%20Native-orange" alt="MLX">
  <img src="https://img.shields.io/badge/离线优先-核心特性-important" alt="离线优先">
  <img src="https://img.shields.io/badge/测试-497%20通过-brightgreen" alt="测试">
  <img src="https://img.shields.io/badge/覆盖率-88%25-brightgreen" alt="覆盖率">
  <img src="https://img.shields.io/badge/API-FastAPI-blue" alt="API">
</p>

---

## 📋 产品简介

**Fusion-Finance** 是一款本地 AI 金融分析平台，基于 `fusion-mlx` 构建，**100% 本地离线，数据不出境**，是国内环境下 Claude Financial 的合规替代方案。

v0.5.0 新增：**自定义异常体系**（6类结构化错误响应）、**仪表盘聚合端点**（公司全景、市场概览、服务状态）、**Ruff 零告警**、**测试整合**、**fusion-studio GUI 集成**（FinanceBridge + 8 视图，PR [#87](https://github.com/dahai80/fusion-studio/pull/87)）。

### 与 Claude Financial 对比

| 能力 | Claude Financial | Fusion-Finance | 模块 |
|------|-----------------|----------------|------|
| **数据驻留** | ❌ 仅云端 | ✅ **100% 本地** | — |
| **国内可访问** | ❌ 被墙 | ✅ **完全可用** | — |
| DCF 估值 | ✅ | ✅ | `modeling/engine.py` |
| 可比公司分析 | ✅ | ✅ | `modeling/engine.py` |
| 敏感性分析 | ✅ | ✅ | `modeling/engine.py` |
| 蒙特卡洛模拟 | ✅ | ✅ | `modeling/engine.py` |
| **交互式 DCF** | ❌ | ✅ | `modeling/engine.py` |
| **情景管理器** | ❌ | ✅ | `modeling/scenarios.py` |
| **LBO 模型** | ✅ | ✅ | `modeling/advanced.py` |
| **DDM 模型** | ✅ | ✅ | `modeling/advanced.py` |
| **并购模型** | ✅ | ✅ | `modeling/advanced.py` |
| **APV / EVA / RI** | ❌ | ✅ | `modeling/valuation.py` |
| **投资组合优化** | ❌ | ✅ | `modeling/portfolio.py` |
| **Black-Litterman** | ❌ | ✅ | `modeling/portfolio.py` |
| **债券 / 收益率曲线** | ❌ | ✅ | `modeling/portfolio.py` |
| **技术指标** | ❌ | ✅ | `modeling/portfolio.py` |
| 财务指标 | ✅ | ✅ | `statements/analyzer.py` |
| 资产负债表校验 | ✅ | ✅ | `statements/analyzer.py` |
| **财报标准化** | ❌ | ✅ | `statements/normalizer.py` |
| **选股器** | ❌ | ✅ | `statements/screener.py` |
| KYC 尽调 | ✅ | ✅ | `risk/engine.py` |
| 信用评估 | ✅ | ✅ | `risk/engine.py` |
| 合规检查 | ✅ | ✅ | `risk/engine.py` |
| **制裁名单筛查** | ❌ | ✅ | `risk/sanctions.py` |
| **实体解析** | ❌ | ✅ | `risk/entity_resolution.py` |
| **VaR 计算** | ✅ | ✅ | `risk/advanced_risk.py` |
| **压力测试** | ✅ | ✅ | `risk/advanced_risk.py` |
| 估值报告 | ✅ | ✅ | `report/reports.py` |
| PitchBook | ✅ | ✅ | `report/reports.py` |
| 投研报告 | ✅ | ✅ | `report/reports.py` |
| **AI Copilot** | ❌ | ✅ | `api/routes/copilot.py` |
| **SVG 图表** | ❌ | ✅ | `api/routes/chart.py` |
| **项目管理** | ❌ | ✅ | `api/routes/project.py` |
| **行情模拟器** | ❌ | ✅ | `data/market_feed.py` |
| **计算缓存** | ❌ | ✅ | `data/cache.py` |
| **审计日志** | ✅ | ✅ | `utils/audit.py` |
| **授权** | 企业版 | ✅ **MIT（免费）** | — |

---

## 🚀 快速开始

```bash
# 安装
pip install -e "."

# CLI 使用
fusion-finance model dcf "公司A" 100 120 140 160
fusion-finance statement analyze "公司A" --revenue 1000
fusion-finance risk kyc "目标公司"
fusion-finance report valuation "公司A" -o ./reports

# 启动 API 服务
fusion-finance serve --port 8200
# 或使用 start.sh
./start.sh start
```

---

## 🌐 API 服务

### 启停命令

```bash
./start.sh start    # 启动（端口 8200）
./start.sh stop     # 停止
./start.sh restart  # 重启
./start.sh status   # 查看状态
./start.sh log      # 查看日志
```

### API 端点

| 前缀 | 模块 | 端点 |
|------|------|------|
| `/api/v1/` | 健康 | `GET /` 健康, `GET /ready` 就绪 |
| `/api/v1/modeling` | 建模 | DCF、可比、敏感性、蒙特卡洛、LBO、DDM、并购、APV、EVA、RI、组合、会话、情景 |
| `/api/v1/statements` | 财报 | 分析、指标、校验、选股、预设、标准化、趋势、准则 |
| `/api/v1/risk` | 风控 | KYC、信用、合规、VaR、压力测试 |
| `/api/v1/report` | 报告 | 估值、PitchBook、投研、导出、格式 |
| `/api/v1/copilot` | AI 助手 | 对话、历史、会话 |
| `/api/v1/chart` | 图表 | K线、热力图、瀑布图、龙卷风图 |
| `/api/v1/project` | 项目 | CRUD、快照、版本、差异、历史、导出 |
| `/api/v1/data` | 数据 | 导入、校验平衡、校验完整性、缓存 |
| `/api/v1/audit` | 审计 | 记录、查询、统计、文件统计 |
| `/api/v1/dashboard` | 仪表盘 | 公司全景、市场概览、服务状态 |
| `/ws` | WebSocket | `/ws/copilot` 流式对话, `/ws/modeling/progress` |
| `/events` | SSE | `/events/insights`, `/events/alerts` 流, `/events/publish` |

### API 示例

```bash
# 计算 DCF
curl -X POST http://localhost:8200/api/v1/modeling/dcf/calculate \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"wacc":0.10,"terminal_growth":0.03}'

# 成长策略选股
curl -X POST http://localhost:8200/api/v1/statements/screener \
  -H "Content-Type: application/json" \
  -d '{"filters":{"preset":"growth"},"limit":5}'

# A股财报标准化
curl -X POST http://localhost:8200/api/v1/statements/normalize \
  -H "Content-Type: application/json" \
  -d '{"data":{"营业收入":1000,"净利润":200},"standard":"A","company":"TestCo","period":"2024"}'

# 健康检查
curl http://localhost:8200/api/v1/

# 仪表盘：公司全景
curl -X POST http://localhost:8200/api/v1/dashboard/company \
  -H "Content-Type: application/json" \
  -d '{"company":"Apple","revenue":[100,120,140],"ebit_margin":[0.2,0.22,0.24],"wacc":0.10}'

# 仪表盘：市场概览
curl http://localhost:8200/api/v1/dashboard/market?preset=quality&limit=5

# 仪表盘：服务状态
curl http://localhost:8200/api/v1/dashboard/status

# AI 助手对话
curl -X POST http://localhost:8200/api/v1/copilot/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"分析Apple的DCF估值","session_id":"demo"}'
```

Swagger 文档：`http://localhost:8200/docs`

---

## 📖 模块详解

### 1. 财务建模 (`modeling/`)

| 组件 | 说明 |
|------|------|
| `DCFModel` | 现金流折现估值（含终值） |
| `CompsAnalysis` | 可比公司分析（同业倍数） |
| `InteractiveDCFSession` | 实时滑块驱动 DCF 重算 |
| `ScenarioManager` | 熊市/基准/牛市情景对比 |
| `LBOModel` | 杠杆收购模型（IRR/MOIC） |
| `DDMModel` | 股利贴现模型 |
| `MergerModel` | 并购增厚/稀释分析 |
| `APVModel` | 调整现值法 |
| `EVAModel` | 经济增加值 |
| `RIModel` | 剩余收益模型 |
| `PortfolioOptimizer` | 均值-方差投资组合优化 |
| `BlackLittermanOptimizer` | BL 后验收益 + 均值方差 |
| `Bond` | 债券定价与收益率计算 |
| `YieldCurve` | Nelson-Siegel 收益率曲线（随机搜索校准） |
| `TechnicalIndicators` | SMA、EMA、RSI、MACD、布林带 |

### 2. 财报分析 (`statements/`)

| 组件 | 说明 |
|------|------|
| `FinancialStatement` | 利润表、资产负债表、现金流量表数据 |
| `FinancialAnalysis` | 计算指标：利润率、ROE、ROA、负债率 |
| `calculate_metrics()` | 从原始数据计算财务比率 |
| `validate_balance_sheet()` | 校验资产 = 负债 + 权益 |
| `analyze_statements()` | AI 驱动深度财务分析 |
| `StatementNormalizer` | 多准则标准化（A股/港股/US GAAP），同比/环比，趋势分析 |
| `FinancialScreener` | 多维选股，4 个预设策略（价值/成长/红利/质量） |

### 3. 风控合规 (`risk/`)

| 组件 | 说明 |
|------|------|
| `KYCCheck` | KYC 尽职调查筛查 |
| `CreditAssessment` | 信用评分与评级 |
| `SanctionsEngine` | 制裁名单匹配（Levenshtein + 关键词 + 精确） |
| `EntityGraph` | 实体解析、UBO 追踪、PEP 扫描 |
| `VaRResult` | 风险价值计算（95%/99%） |
| `StressTestResult` | 压力测试情景定义 |
| `calculate_var()` | 历史收益率序列 VaR |
| `monte_carlo_var()` | 蒙特卡洛 VaR 模拟 |
| `stress_test_scenarios()` | 预定义压力测试情景 |

### 4. 报告生成 (`report/`)

| 组件 | 说明 |
|------|------|
| `ReportGenerator` | Markdown 报告生成 + AI 投研 |
| `ReportFormatter` | Jinja2 模板渲染 + 多格式导出 |
| 模板 | `valuation.html`、`pitchbook.html`、`research.html`、`board_material.html` |
| 导出格式 | HTML、PDF、PPTX、XLSX、JSON、Markdown |
| `save_report()` | 保存报告到文件 |

### 5. AI 助手 (`copilot/`)

| 组件 | 说明 |
|------|------|
| `CopilotEngine` | ReAct 循环引擎（最多 3 轮工具调用） |
| `ToolRegistry` | 18 个金融工具（DCF、可比、敏感性、VaR、BL、制裁、债券等） |
| `ConversationMemory` | 会话记忆（最多 50 条消息，100 个会话） |
| `chat()` | 完整助手对话（含工具执行） |
| `chat_stream()` | WebSocket 流式 AsyncIterator |
| 场景提示 | 5 个场景感知系统提示（建模、风控、报告、财报、数据） |
| 洞察提示 | 主动检测（估值告警、风险告警、数据告警） |

### 6. 图表渲染 (`chart/`)

| 组件 | 说明 |
|------|------|
| `ChartRenderer` | SVG 图表渲染引擎（门面） |
| `render_candlestick()` | K线（OHLCV）图（独立模块） |
| `render_heatmap()` | 敏感性矩阵热力图（独立模块） |
| `render_waterfall()` | 桥接/瀑布图（独立模块） |
| `render_sensitivity_tornado()` | 敏感性龙卷风图（独立模块） |

### 7. 数据适配 (`data/`)

| 组件 | 说明 |
|------|------|
| `DataAdapter` | 统一 CSV 导入 + 校验 + 缓存 |
| `CSVLoader` | CSV/TSV 加载（自动编码和分隔符检测） |
| `DataCache` | LRU 缓存（TTL 过期） |
| `DataValidator` | 行校验、资产负债校验、完整性评分 |
| `MarketFeedSimulator` | A股/港股模拟行情、OHLCV 生成 |
| `compute_cache` | 装饰器 LRU 缓存（TTL，用于耗时计算） |

### 8. 共享工具 (`utils/`)

| 组件 | 说明 |
|------|------|
| `AuditTrail` | JSONL 审计日志（结构化查询和统计） |
| `parse_json()` | 统一 JSON 解析（正则回退） |

### 9. 项目管理 (`project/`)

| 组件 | 说明 |
|------|------|
| `ProjectManager` | CRUD、快照、恢复分析项目 |
| `VersionControl` | SHA256 哈希、差异/补丁、拣选、历史摘要 |
| `ProjectExporter` | JSON/ZIP 导出和导入 |

### 10. API 中间件与 SSE (`api/`)

| 组件 | 说明 |
|------|------|
| `AuditMiddleware` | 自动记录每个请求到审计日志 |
| `RateLimitMiddleware` | 每 IP 滑动窗口限流 |
| `APIKeyMiddleware` | API 密钥认证（含豁免路径） |
| `EventBus` | 发布/订阅事件总线（SSE 流） |
| SSE 路由 | `/events/insights`、`/events/alerts`、`/events/publish` |

### 11. 配置 (`config.py`)

| 设置 | 默认值 | 环境变量 |
|------|--------|----------|
| 主机 | `0.0.0.0` | `FUSION_FINANCE_HOST` |
| 端口 | `8200` | `FUSION_FINANCE_PORT` |
| MLX 地址 | `http://localhost:11434/v1` | `FUSION_FINANCE_MLX_URL` |
| 模型 | `qwen3.5-9b` | `FUSION_FINANCE_MODEL` |
| 数据目录 | `~/.fusion/finance` | `FUSION_FINANCE_DATA_DIR` |

---

## 🏗️ 架构

```
┌───────────────────────────────────────────────────────────────┐
│                 CLI / API 服务                                  │
│   Click CLI (fusion-finance)  │  FastAPI (localhost:8200)     │
├───────────────────────────────────────────────────────────────┤
│               API 中间件与 SSE                                  │
│  AuditMiddleware │ RateLimitMiddleware │ APIKeyMiddleware      │
│  EventBus + SSE（洞察 / 告警流）                               │
├───────────────────────────────────────────────────────────────┤
│                    引擎层                                       │
│  FinancialModeling │ StatementAnalyzer │ RiskCompliance        │
│  AdvancedModeling  │ RiskModelingEngine │ ReportGenerator       │
│  ReportFormatter   │ ProjectManager     │ VersionControl        │
│  InteractiveDCF    │ ScenarioManager    │ CopilotEngine         │
│  ChartRenderer     │ DataAdapter        │ ConversationMemory    │
│  StatementNormalizer│ FinancialScreener │ Copilot Prompts       │
│  Chart Modules (4)                                            │
├───────────────────────────────────────────────────────────────┤
│                 AI 后端 (fusion-mlx)                            │
│  HTTP → http://localhost:11434/v1/chat/completions            │
│  MLXClient（重试 + httpx 回退）                                │
│  100% 本地，数据不上传                                          │
└───────────────────────────────────────────────────────────────┘
```

---

## 🔧 CLI 参考

```bash
fusion-finance [选项] 命令 [参数]

选项:
  --verbose, -v    详细输出
  --model, -m      fusion-mlx 模型名称
  --version        显示版本

命令:
  model dcf <公司> <营收...>           DCF 估值
  statement analyze <公司> [选项]      财务指标
  risk kyc <实体>                      KYC 筛查
  report valuation <公司> [选项]       生成估值报告
  serve [--host] [--port] [--reload]   启动 API 服务
```

---

## 🧪 运行测试

```bash
pip install -e ".[test]"
pytest tests/ -v                              # 全部测试（497 通过）
pytest tests/test_core.py -v                  # 核心测试
pytest tests/test_api.py -v                   # API 端点测试
pytest tests/test_coverage.py -v              # 高级模型测试
pytest tests/test_phase2.py -v                # 阶段 2：助手、图表、数据
pytest tests/test_phase3.py -v                # 阶段 3：报告模板、项目、审计
pytest tests/test_phase3plus.py -v            # 阶段 3+：提示、中间件、SSE、图表模块
pytest tests/test_phase5.py -v                # 阶段 5：BL、收益率曲线、制裁、实体、行情
pytest tests/test_integration.py -v           # 集成：WS、CLI、标准化、选股、情景、工具
pytest tests/ --cov=fusion_finance --cov-report=html
```

---

## 🔒 安全合规

- **100% 本地离线** — 零数据上传，零隐私泄露
- **无遥测** — 无埋点、无回传
- **数据主权** — 所有处理在本地完成
- **审计日志** — 完整操作记录
- **符合国内法规** — 无跨境数据传输

---

## 📄 开源协议

MIT License. 详见 [LICENSE](LICENSE)。

---

<p align="center">
  <strong>Fusion-Finance — 本地 AI 金融，数据不出境，合规无忧。</strong>
</p>
<p align="center">
  <sub>用 ❤️ 和 fusion-mlx 构建</sub>
</p>
